//! A pending send borrows the owner; it cannot be consumed for finish yet.
//! ```compile_fail
//! use wwl_measurement::{asynchronous::AsyncTask, parse_codes, TaskConfig};
//! let mut task = AsyncTask::start(TaskConfig::default()).unwrap();
//! let sending = task.send(parse_codes(["2"]).unwrap());
//! let finishing = task.finish();
//! drop(sending);
//! drop(finishing);
//! ```
//! Tokio 1.52.3 adaptation. One owner retains the worker handle and sole sender.
//! Explicit finish/cancel waits for completion; dropping the owner requests abort
//! but cannot asynchronously observe completion. No external effects are performed.
use crate::{Batch, Fir2, HalfMillivolt, TaskConfig};
use std::fmt;
use tokio::{runtime::Handle, sync::mpsc, task::JoinHandle};

#[derive(Debug)]
pub enum AsyncError {
    NoRuntime,
    ZeroCapacity,
    Sequence { expected: usize, actual: usize },
    SampleLimit { limit: usize },
    BatchLimit,
    Closed,
    Join(tokio::task::JoinError),
}
impl fmt::Display for AsyncError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoRuntime => write!(f, "start requires an entered Tokio runtime"),
            Self::ZeroCapacity => write!(f, "async queue requires capacity 1..16"),
            Self::Sequence { expected, actual } => {
                write!(f, "expected sample index {expected}, got {actual}")
            }
            Self::SampleLimit { limit } => write!(f, "async task exceeds {limit} total samples"),
            Self::BatchLimit => write!(f, "async task exceeds 1024 batch objects"),
            Self::Closed => write!(f, "async receiver closed; finish observes worker cause"),
            Self::Join(e) => write!(f, "async worker completion: {e}"),
        }
    }
}
impl std::error::Error for AsyncError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Join(e) => Some(e),
            _ => None,
        }
    }
}
/// Owns a finite stream. Successful sends accept contiguous global sample indices.
/// Invalid batches are rejected before enqueue and leave counters unchanged.
/// Cancelling a pending send drops its batch and does not increment counters;
/// callers must retain/rebuild input if they intend to retry it.
pub struct AsyncTask {
    sender: Option<mpsc::Sender<Batch>>,
    handle: Option<JoinHandle<Vec<HalfMillivolt>>>,
    config: TaskConfig,
    samples: usize,
    batches: usize,
}
impl AsyncTask {
    pub fn start(config: TaskConfig) -> Result<Self, AsyncError> {
        if config.capacity() == 0 {
            return Err(AsyncError::ZeroCapacity);
        }
        let runtime = Handle::try_current().map_err(|_| AsyncError::NoRuntime)?;
        let (sender, mut receiver) = mpsc::channel::<Batch>(config.capacity());
        let handle = runtime.spawn(async move {
            let mut filter = Fir2::default();
            let mut output = Vec::new();
            while let Some(batch) = receiver.recv().await {
                output.extend(filter.process(batch));
            }
            output
        });
        Ok(Self {
            sender: Some(sender),
            handle: Some(handle),
            config,
            samples: 0,
            batches: 0,
        })
    }
    pub async fn send(&mut self, batch: Batch) -> Result<(), AsyncError> {
        if self.batches == crate::MAX_SAMPLES {
            return Err(AsyncError::BatchLimit);
        }
        let mut expected = self.samples;
        for record in batch.records() {
            if expected == self.config.max_samples() {
                return Err(AsyncError::SampleLimit {
                    limit: self.config.max_samples(),
                });
            }
            let actual = usize::from(record.index.get());
            if actual != expected {
                return Err(AsyncError::Sequence { expected, actual });
            }
            expected += 1;
        }
        self.sender
            .as_ref()
            .ok_or(AsyncError::Closed)?
            .send(batch)
            .await
            .map_err(|_| AsyncError::Closed)?;
        self.samples = expected;
        self.batches += 1;
        Ok(())
    }
    /// Drops the sole sender, then waits for EOF processing. Cancelling this
    /// finish future drops the owner, which requests abort but does not wait.
    pub async fn finish(mut self) -> Result<Vec<HalfMillivolt>, AsyncError> {
        self.sender.take();
        // Keep handle owned until await completes, including when future is dropped.
        let result = self.handle.as_mut().expect("owned handle").await;
        self.handle.take();
        result.map_err(AsyncError::Join)
    }
    /// Abort requests cancellation at a runtime scheduling point. Await confirms
    /// termination. If completion won the race, return its successful output.
    pub async fn cancel_and_wait(mut self) -> Result<Vec<HalfMillivolt>, AsyncError> {
        self.sender.take();
        self.handle.as_ref().expect("owned handle").abort();
        let result = self.handle.as_mut().expect("owned handle").await;
        self.handle.take();
        result.map_err(AsyncError::Join)
    }
}
impl Drop for AsyncTask {
    fn drop(&mut self) {
        if let Some(handle) = &self.handle {
            handle.abort();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{parse_codes, threaded::split_batch_at};
    use std::future::Future;
    fn runtime() -> tokio::runtime::Runtime {
        tokio::runtime::Builder::new_current_thread()
            .build()
            .unwrap()
    }
    #[test]
    fn every_boundary_and_duplicate_rejection() {
        runtime().block_on(async {
            for cut in 0..=4 {
                let (a, b) =
                    split_batch_at(parse_codes(["2", "4", "6", "8"]).unwrap(), cut).unwrap();
                let mut task = AsyncTask::start(TaskConfig::default()).unwrap();
                task.send(a).await.unwrap();
                task.send(b).await.unwrap();
                if cut != 0 {
                    assert!(matches!(
                        task.send(parse_codes(["2"]).unwrap()).await,
                        Err(AsyncError::Sequence { .. })
                    ));
                }
                assert_eq!(
                    task.finish()
                        .await
                        .unwrap()
                        .iter()
                        .map(|v| v.twice_mv())
                        .collect::<Vec<_>>(),
                    [2, 6, 10, 14]
                );
            }
            let mut task = AsyncTask::start(TaskConfig::default()).unwrap();
            let (_, suffix) = split_batch_at(parse_codes(["2", "4"]).unwrap(), 1).unwrap();
            assert!(matches!(
                task.send(suffix).await,
                Err(AsyncError::Sequence {
                    expected: 0,
                    actual: 1
                })
            ));
            assert!(task.finish().await.unwrap().is_empty());
        });
    }
    #[test]
    fn abort_observed_and_panic_source_retained() {
        runtime().block_on(async {
            let task = AsyncTask::start(TaskConfig::default()).unwrap();
            match task.cancel_and_wait().await {
                Err(AsyncError::Join(e)) => assert!(e.is_cancelled()),
                _ => panic!("abort must win before first poll"),
            }
            let mut task = AsyncTask::start(TaskConfig::default()).unwrap();
            let old = task.handle.take().unwrap();
            old.abort();
            assert!(old.await.unwrap_err().is_cancelled());
            task.handle = Some(tokio::spawn(async { panic!("injected worker panic") }));
            match task.finish().await {
                Err(AsyncError::Join(e)) => assert!(e.is_panic()),
                _ => panic!("panic lost"),
            }
        });
    }
    #[test]
    fn full_send_cancellation_changes_no_counter_and_closes() {
        runtime().block_on(async {
            let (tx, mut rx) = mpsc::channel::<Batch>(1);
            let (release, gate) = tokio::sync::oneshot::channel();
            let handle = tokio::spawn(async move {
                gate.await.unwrap();
                let mut fir = Fir2::default();
                let mut output = Vec::new();
                while let Some(batch) = rx.recv().await {
                    output.extend(fir.process(batch));
                }
                output
            });
            let mut task = AsyncTask {
                sender: Some(tx),
                handle: Some(handle),
                config: TaskConfig::default(),
                samples: 0,
                batches: 0,
            };
            let (a, b) = split_batch_at(parse_codes(["2", "4"]).unwrap(), 1).unwrap();
            task.send(a).await.unwrap();
            {
                let mut pending = Box::pin(task.send(b));
                std::future::poll_fn(|cx| {
                    assert!(pending.as_mut().poll(cx).is_pending());
                    std::task::Poll::Ready(())
                })
                .await;
            }
            assert_eq!((task.samples, task.batches), (1, 1));
            release.send(()).unwrap();
            assert_eq!(task.finish().await.unwrap()[0].twice_mv(), 2);
        });
    }
    #[test]
    fn cancellation_observation_does_not_undo_a_prior_effect() {
        runtime().block_on(async {
            use std::sync::{
                atomic::{AtomicUsize, Ordering},
                Arc,
            };
            let effect = Arc::new(AtomicUsize::new(0));
            let worker_effect = effect.clone();
            let (sender, mut receiver) = mpsc::channel::<Batch>(1);
            let (ack, observed) = tokio::sync::oneshot::channel();
            let handle = tokio::spawn(async move {
                let _batch = receiver.recv().await.unwrap();
                worker_effect.fetch_add(1, Ordering::SeqCst);
                ack.send(()).unwrap();
                std::future::pending::<()>().await;
                Vec::new()
            });
            let mut task = AsyncTask {
                sender: Some(sender),
                handle: Some(handle),
                config: TaskConfig::default(),
                samples: 0,
                batches: 0,
            };
            task.send(parse_codes(["2"]).unwrap()).await.unwrap();
            observed.await.unwrap();
            match task.cancel_and_wait().await {
                Err(AsyncError::Join(e)) => assert!(e.is_cancelled()),
                _ => panic!("expected cancellation"),
            }
            assert_eq!(effect.load(Ordering::SeqCst), 1);
        });
    }
    #[test]
    fn limits_empty_and_no_runtime() {
        assert!(matches!(
            AsyncTask::start(TaskConfig::default()),
            Err(AsyncError::NoRuntime)
        ));
        assert!(matches!(
            AsyncTask::start(TaskConfig::try_new(0, 1, 1).unwrap()),
            Err(AsyncError::ZeroCapacity)
        ));
        runtime().block_on(async {
            let mut task = AsyncTask::start(TaskConfig::try_new(1, 1, 0).unwrap()).unwrap();
            assert!(matches!(
                task.send(parse_codes(["2"]).unwrap()).await,
                Err(AsyncError::SampleLimit { limit: 0 })
            ));
            for _ in 0..1024 {
                task.send(parse_codes([] as [&str; 0]).unwrap())
                    .await
                    .unwrap();
            }
            assert!(matches!(
                task.send(parse_codes([] as [&str; 0]).unwrap()).await,
                Err(AsyncError::BatchLimit)
            ));
            assert!(task.finish().await.unwrap().is_empty());
        });
    }
}
