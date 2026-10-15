//! One owned finite stream, one receiver and one persistent FIR state.
//!
//! ```
//! use wwl_measurement::{parse_codes, TaskConfig};
//! use wwl_measurement::threaded::{split_batch, process_threaded};
//! let config = TaskConfig::try_new(1, 2, 4)?;
//! let batches = split_batch(parse_codes(["2","4","6","8"])? , config);
//! let output = process_threaded(batches, config)?;
//! assert_eq!(output.iter().map(|x|x.twice_mv()).collect::<Vec<_>>(), [2,6,10,14]);
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```
//! A thread cannot outlive the owner of a borrowed record view.
//! ```compile_fail
//! use wwl_measurement::parse_codes;
//! let batch = parse_codes(["2"]).unwrap();
//! let view = batch.records();
//! std::thread::spawn(move || println!("{}", view[0].voltage.get()));
//! ```
//! Standard receivers cannot be cloned into MPMC receivers.
//! ```compile_fail
//! let (_, rx) = std::sync::mpsc::sync_channel::<u8>(1);
//! let second = rx.clone();
//! ```
use crate::{Batch, Fir2, HalfMillivolt, TaskConfig};
use std::fmt;
use std::io;
use std::sync::mpsc::{self, Receiver, TrySendError};
use std::thread;
#[derive(Debug)]
pub enum TaskError {
    BatchCountLimit { limit: usize, actual: usize },
    BatchBoundary { index: usize, len: usize },
    Limit { limit: usize },
    Sequence { expected: usize, actual: usize },
    Spawn(io::Error),
    ChannelClosed { batch: usize },
    WorkerFailed { message: &'static str },
    WorkerPanicked,
}
impl fmt::Display for TaskError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BatchCountLimit { limit, actual } => write!(
                f,
                "task has {actual} batch objects; exceeds {limit} batch objects"
            ),
            Self::BatchBoundary { index, len } => {
                write!(f, "batch split index {index} exceeds length {len}")
            }
            Self::Limit { limit } => write!(f, "task exceeds {limit} total samples"),
            Self::Sequence { expected, actual } => {
                write!(f, "task sequence: expected index {expected}, got {actual}")
            }
            Self::Spawn(error) => write!(f, "spawn measurement worker: {error}"),
            Self::ChannelClosed { batch } => {
                write!(f, "worker receiver closed before batch {batch} was sent")
            }
            Self::WorkerFailed { message } => write!(f, "worker failed: {message}"),
            Self::WorkerPanicked => write!(
                f,
                "measurement worker panicked; joined; no successful result"
            ),
        }
    }
}
impl std::error::Error for TaskError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Spawn(error) => Some(error),
            _ => None,
        }
    }
}
/// Splits at any valid boundary without restarting sample identity.
pub fn split_batch_at(batch: Batch, index: usize) -> Result<(Batch, Batch), TaskError> {
    let mut records = batch.into_records();
    if index > records.len() {
        return Err(TaskError::BatchBoundary {
            index,
            len: records.len(),
        });
    }
    let right = records.split_off(index);
    Ok((Batch { records }, Batch { records: right }))
}
/// Consumes a single indexed sequence, preserving global indices across new batches.
pub fn split_batch(batch: Batch, config: TaskConfig) -> Vec<Batch> {
    let mut batches = Vec::new();
    let mut records = batch.into_records().into_iter();
    loop {
        let part: Vec<_> = records.by_ref().take(config.batch_size()).collect();
        if part.is_empty() {
            break;
        }
        batches.push(Batch { records: part });
    }
    batches
}
fn validate(batches: &[Batch], config: TaskConfig) -> Result<(), TaskError> {
    // Bound batch objects as well as records, including zero-record batches.
    if batches.len() > crate::MAX_SAMPLES {
        return Err(TaskError::BatchCountLimit {
            limit: crate::MAX_SAMPLES,
            actual: batches.len(),
        });
    }
    let mut expected = 0;
    for batch in batches {
        for record in batch.records() {
            if expected == config.max_samples() {
                return Err(TaskError::Limit {
                    limit: config.max_samples(),
                });
            }
            let actual = usize::from(record.index.get());
            if actual != expected {
                return Err(TaskError::Sequence { expected, actual });
            }
            expected += 1;
        }
    }
    Ok(())
}
fn worker(receiver: Receiver<Batch>) -> Result<Vec<HalfMillivolt>, TaskError> {
    let mut filter = Fir2::default();
    let mut output = Vec::new();
    for batch in receiver {
        output.extend(filter.process(batch));
    }
    Ok(output)
}
/// Validates before spawning; sends owned batches; closes the sole sender before
/// joining. On any failure, returns no partial output; already occurring external
/// effects would not be rolled back (this worker performs only pure computation).
pub fn process_threaded(
    batches: Vec<Batch>,
    config: TaskConfig,
) -> Result<Vec<HalfMillivolt>, TaskError> {
    run_owned(batches, config, worker, |_| {})
}
fn run_owned<F, H>(
    batches: Vec<Batch>,
    config: TaskConfig,
    work: F,
    mut on_full: H,
) -> Result<Vec<HalfMillivolt>, TaskError>
where
    F: FnOnce(Receiver<Batch>) -> Result<Vec<HalfMillivolt>, TaskError> + Send + 'static,
    H: FnMut(usize),
{
    validate(&batches, config)?;
    let (sender, receiver) = mpsc::sync_channel(config.capacity());
    let handle = thread::Builder::new()
        .name("measurement-worker".into())
        .spawn(move || work(receiver))
        .map_err(TaskError::Spawn)?;
    let mut send_failure = None;
    for (offset, batch) in batches.into_iter().enumerate() {
        let result = match sender.try_send(batch) {
            Ok(()) => Ok(()),
            Err(TrySendError::Full(batch)) => {
                on_full(offset + 1);
                sender.send(batch).map_err(|_| ())
            }
            Err(TrySendError::Disconnected(_batch)) => Err(()),
        };
        if result.is_err() {
            send_failure = Some(TaskError::ChannelClosed { batch: offset + 1 });
            break;
        }
    }
    drop(sender); // all sender ownership is local; worker can now observe EOF
    let joined = handle.join().map_err(|_| TaskError::WorkerPanicked)?;
    let output = joined?; // worker failure has priority over its consequential send error
    if let Some(error) = send_failure {
        return Err(error);
    }
    Ok(output)
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::{parse_codes, TaskConfig};
    use std::sync::mpsc::TryRecvError;
    fn two_batches() -> Vec<Batch> {
        split_batch(
            parse_codes(["2", "4", "6", "8"]).unwrap(),
            TaskConfig::default(),
        )
    }
    #[test]
    fn force_actual_full_branch_without_sleep() {
        let (release_tx, release_rx) = mpsc::channel();
        let (full_tx, full_rx) = mpsc::channel();
        let driver = thread::spawn(move || {
            run_owned(
                two_batches(),
                TaskConfig::try_new(1, 2, 4).unwrap(),
                move |rx| {
                    release_rx.recv().unwrap(); // cannot dequeue until test has observed Full
                    worker(rx)
                },
                move |batch| {
                    full_tx.send(batch).unwrap();
                },
            )
        });
        assert_eq!(full_rx.recv().unwrap(), 2);
        release_tx.send(()).unwrap();
        assert_eq!(driver.join().unwrap().unwrap().len(), 4);
    }

    #[test]
    fn force_full_then_failure_unblocks_and_joins() {
        let (release_tx, release_rx) = mpsc::channel();
        let (full_tx, full_rx) = mpsc::channel();
        let driver = thread::spawn(move || {
            run_owned(
                two_batches(),
                TaskConfig::try_new(1, 2, 4).unwrap(),
                move |rx| {
                    release_rx.recv().unwrap();
                    drop(rx);
                    Err(TaskError::WorkerFailed {
                        message: "failure while queue full",
                    })
                },
                move |batch| {
                    full_tx.send(batch).unwrap();
                },
            )
        });
        assert_eq!(full_rx.recv().unwrap(), 2);
        release_tx.send(()).unwrap();
        assert!(matches!(
            driver.join().unwrap(),
            Err(TaskError::WorkerFailed { .. })
        ));
    }
    #[test]
    fn worker_error_and_panic_are_joined_even_if_send_fails() {
        let config = TaskConfig::try_new(0, 2, 4).unwrap();
        let (dropped_tx, dropped_rx) = mpsc::channel();
        let result = run_owned(
            two_batches(),
            config,
            move |rx| {
                drop(rx);
                dropped_tx.send(()).unwrap();
                Err(TaskError::WorkerFailed {
                    message: "injected",
                })
            },
            |_| {},
        );
        assert!(matches!(
            result,
            Err(TaskError::WorkerFailed {
                message: "injected"
            })
        ));
        dropped_rx.recv().unwrap();
        let result = run_owned(
            two_batches(),
            config,
            |_rx| panic!("injected worker panic"),
            |_| {},
        );
        assert!(matches!(result, Err(TaskError::WorkerPanicked)));
    }
    #[test]
    fn receiver_early_success_still_does_not_make_send_failure_success() {
        let result = run_owned(
            two_batches(),
            TaskConfig::try_new(0, 2, 4).unwrap(),
            |rx| {
                drop(rx);
                Ok(Vec::new())
            },
            |_| {},
        );
        assert!(matches!(result, Err(TaskError::ChannelClosed { batch: 1 })));
    }
    #[test]
    fn retained_sender_keeps_empty_receiver_open_until_drop() {
        let (sender, receiver) = mpsc::sync_channel::<Batch>(1);
        let retained = sender.clone();
        drop(sender);
        assert!(matches!(receiver.try_recv(), Err(TryRecvError::Empty)));
        drop(retained);
        assert!(matches!(
            receiver.try_recv(),
            Err(TryRecvError::Disconnected)
        ));
    }
}
