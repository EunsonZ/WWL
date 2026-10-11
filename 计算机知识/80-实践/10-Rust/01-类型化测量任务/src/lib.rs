//! A bounded measurement component: 1 mV/code, zero offset, 1 second/sample.
//!
//! ```
//! use wwl_measurement::{parse_codes, summarize};
//! let batch = parse_codes(["2", "4", "6", "8"])?;
//! assert_eq!(summarize(batch.records())?.sum_mv, 20);
//! # Ok::<(), wwl_measurement::InputError>(())
//! ```
//! Units cannot be substituted merely because both use integers.
//! ```compile_fail
//! use wwl_measurement::{AdcCode, Millivolt};
//! let code = AdcCode::try_from(2_u16).unwrap();
//! let voltage: Millivolt = code;
//! ```
//! A borrowed view cannot survive a conflicting mutation.
//! ```compile_fail
//! use wwl_measurement::{parse_codes, Record};
//! let mut batch = parse_codes(["2"]).unwrap();
//! let view = batch.records();
//! batch.push_code(4_u16.try_into().unwrap()).unwrap();
//! println!("{}", view[0].voltage.get());
//! ```
//! Moving a batch transfers its ownership.
//! ```compile_fail
//! use wwl_measurement::parse_codes;
//! let batch = parse_codes(["2"]).unwrap();
//! let records = batch.into_records();
//! println!("{}", batch.records().len());
//! ```
mod config;
#[cfg(feature = "ffi")]
pub mod ffi;
#[cfg(feature = "fixed")]
pub mod fixed_core;
pub use config::{parse_config, read_config, ConfigError, ConfigReadError, TaskConfig};
#[cfg(feature = "threaded")]
pub mod threaded;

use std::collections::{BTreeMap, VecDeque};
use std::fmt;
use std::io::{self, BufRead, Read, Write};

pub const MAX_SAMPLES: usize = 1024;
/// Maximum bytes per line, including an optional line ending.
pub const MAX_LINE_BYTES: usize = 64;

#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct AdcCode(u16);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InputError {
    Syntax { position: usize, text: String },
    Range { position: usize, value: u16 },
    TooMany { limit: usize },
}
impl fmt::Display for InputError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Syntax { position, text } => write!(
                f,
                "sample {position}: expected ASCII integer 0..4095, got {text:?}"
            ),
            Self::Range { position, value } => {
                write!(f, "sample {position}: code {value} outside 0..4095")
            }
            Self::TooMany { limit } => write!(f, "input exceeds {limit} samples"),
        }
    }
}
impl std::error::Error for InputError {}
impl TryFrom<u16> for AdcCode {
    type Error = InputError;
    fn try_from(value: u16) -> Result<Self, Self::Error> {
        if value <= 4095 {
            Ok(Self(value))
        } else {
            Err(InputError::Range { position: 0, value })
        }
    }
}
impl AdcCode {
    pub fn get(self) -> u16 {
        self.0
    }
}

#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct Millivolt(u16);
impl Millivolt {
    pub fn get(self) -> u16 {
        self.0
    }
}
impl From<AdcCode> for Millivolt {
    fn from(code: AdcCode) -> Self {
        Self(code.0)
    }
}
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct SampleIndex(u16);
impl SampleIndex {
    /// Zero-based position within one Batch. In the single-batch CLI only,
    /// its number also equals elapsed seconds for the fixed calibration.
    pub fn get(self) -> u16 {
        self.0
    }
}
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct Record {
    pub index: SampleIndex,
    pub voltage: Millivolt,
}

/// Owns a finite sequence. No borrowed input text survives parsing.
#[derive(Debug, Default)]
pub struct Batch {
    records: Vec<Record>,
}
impl Batch {
    pub fn records(&self) -> &[Record] {
        &self.records
    }
    pub fn into_records(self) -> Vec<Record> {
        self.records
    }
    /// On error the existing batch is unchanged.
    pub fn push_code(&mut self, code: AdcCode) -> Result<(), InputError> {
        if self.records.len() == MAX_SAMPLES {
            return Err(InputError::TooMany { limit: MAX_SAMPLES });
        }
        let index = SampleIndex(self.records.len() as u16);
        self.records.push(Record {
            index,
            voltage: code.into(),
        });
        Ok(())
    }
}
/// Tokens are bounded to 64 bytes, ASCII digits only; empty input is valid.
/// A failure drops the local candidate batch and returns no partial output.
pub fn parse_codes<I, S>(tokens: I) -> Result<Batch, InputError>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
{
    let mut batch = Batch::default();
    for token in tokens {
        if batch.records.len() == MAX_SAMPLES {
            return Err(InputError::TooMany { limit: MAX_SAMPLES });
        }
        let text = token.as_ref();
        let position = batch.records.len() + 1;
        let syntax = || InputError::Syntax {
            position,
            text: text.chars().take(MAX_LINE_BYTES).collect(),
        };
        if text.is_empty()
            || text.len() > MAX_LINE_BYTES
            || !text.bytes().all(|b| b.is_ascii_digit())
        {
            return Err(syntax());
        }
        let raw = text.parse::<u16>().map_err(|_| syntax())?;
        let code = AdcCode::try_from(raw).map_err(|_| InputError::Range {
            position,
            value: raw,
        })?;
        batch.push_code(code)?;
    }
    Ok(batch)
}
#[derive(Debug)]
pub enum ReadError {
    Io { line: usize, source: io::Error },
    LineTooLong { line: usize },
    Utf8 { line: usize },
    Input(InputError),
}
impl fmt::Display for ReadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io { line, source } => write!(f, "line {line}: I/O: {source}"),
            Self::LineTooLong { line } => write!(
                f,
                "line {line}: exceeds {MAX_LINE_BYTES} bytes including newline"
            ),
            Self::Utf8 { line } => write!(f, "line {line}: invalid UTF-8"),
            Self::Input(error) => error.fmt(f),
        }
    }
}
impl std::error::Error for ReadError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            Self::Input(error) => Some(error),
            _ => None,
        }
    }
}
/// One token per line; strips only LF and the immediately preceding CR.
/// Reading is capped before allocation can grow with an unbounded line.
pub fn read_codes<R: BufRead>(mut reader: R) -> Result<Batch, ReadError> {
    let mut tokens = Vec::new();
    loop {
        let line = tokens.len() + 1;
        let mut bytes = Vec::new();
        let count = Read::take(&mut reader, (MAX_LINE_BYTES + 1) as u64)
            .read_until(b'\n', &mut bytes)
            .map_err(|source| ReadError::Io { line, source })?;
        if count == 0 {
            break;
        }
        if tokens.len() == MAX_SAMPLES {
            return Err(ReadError::Input(InputError::TooMany { limit: MAX_SAMPLES }));
        }
        if count > MAX_LINE_BYTES {
            return Err(ReadError::LineTooLong { line });
        }
        if bytes.last() == Some(&b'\n') {
            bytes.pop();
            if bytes.last() == Some(&b'\r') {
                bytes.pop();
            }
        }
        tokens.push(String::from_utf8(bytes).map_err(|_| ReadError::Utf8 { line })?);
    }
    parse_codes(tokens).map_err(ReadError::Input)
}
#[derive(Debug, Copy, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    Low,
    Normal,
    High,
}
pub fn classify(voltage: Millivolt) -> Level {
    match voltage.get() {
        0..=3 => Level::Low,
        4..=6 => Level::Normal,
        _ => Level::High,
    }
}
#[derive(Debug, PartialEq)]
pub struct Summary {
    pub count: usize,
    pub sum_mv: u64,
    pub mean_mv: Option<f64>,
    pub levels: BTreeMap<Level, usize>,
}
/// Borrowing leaves the caller's records available; length is checked before summing.
pub fn summarize(records: &[Record]) -> Result<Summary, InputError> {
    if records.len() > MAX_SAMPLES {
        return Err(InputError::TooMany { limit: MAX_SAMPLES });
    }
    let mut levels = BTreeMap::new();
    let mut sum_mv = 0_u64;
    for record in records {
        sum_mv += u64::from(record.voltage.get());
        *levels.entry(classify(record.voltage)).or_insert(0) += 1;
    }
    Ok(Summary {
        count: records.len(),
        sum_mv,
        mean_mv: if records.is_empty() {
            None
        } else {
            Some(sum_mv as f64 / records.len() as f64)
        },
        levels,
    })
}
/// Twice the voltage in mV, preserving half-mV results without integer truncation.
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct HalfMillivolt(u16);
impl HalfMillivolt {
    pub fn twice_mv(self) -> u16 {
        self.0
    }
}
#[derive(Debug, Default)]
pub struct Fir2 {
    previous: u16,
}
impl Fir2 {
    pub fn step(&mut self, voltage: Millivolt) -> HalfMillivolt {
        let current = voltage.get();
        let result = HalfMillivolt(self.previous + current); // <=8190, fits u16
        self.previous = current;
        result
    }
    /// Consumes the owned batch but retains state in this processor.
    pub fn process(&mut self, batch: Batch) -> Vec<HalfMillivolt> {
        batch
            .into_records()
            .into_iter()
            .map(|r| self.step(r.voltage))
            .collect()
    }
}
/// FIFO ownership exercise; queue order preserves one stream's FIR dependence.
pub fn drain_batches(queue: &mut VecDeque<Batch>, filter: &mut Fir2) -> Vec<HalfMillivolt> {
    let mut output = Vec::new();
    while let Some(batch) = queue.pop_front() {
        output.extend(filter.process(batch));
    }
    output
}
/// Output order and each original record index are preserved, including suffix
/// batches. FIR is restarted for this standalone report; flushing is explicit
/// and failure is propagated.
pub fn write_report<W: Write>(writer: W, batch: &Batch) -> io::Result<()> {
    let summary = summarize(batch.records())
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidInput, error))?;
    let mut filter = Fir2::default();
    let output: Vec<_> = batch
        .records()
        .iter()
        .map(|r| filter.step(r.voltage))
        .collect();
    write_report_indexed(
        writer,
        &summary,
        &output,
        batch.records().iter().map(|r| usize::from(r.index.get())),
    )
}
/// Writes a precomputed owned-task report. Output positions are the validated
/// stream indices, not independently parsed batch-local indices.
pub fn write_summary_report<W: Write>(
    writer: W,
    summary: &Summary,
    filtered: &[HalfMillivolt],
) -> io::Result<()> {
    write_report_indexed(writer, summary, filtered, 0..filtered.len())
}
fn write_report_indexed<W: Write, I: IntoIterator<Item = usize>>(
    mut writer: W,
    summary: &Summary,
    filtered: &[HalfMillivolt],
    indices: I,
) -> io::Result<()> {
    if summary.count != filtered.len() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "summary/filter count mismatch",
        ));
    }
    writeln!(writer, "count={} sum={} mV", summary.count, summary.sum_mv)?;
    match summary.mean_mv {
        Some(mean) => writeln!(writer, "mean={mean:.3} mV")?,
        None => writeln!(writer, "mean=undefined (empty input)")?,
    }
    for (level, count) in &summary.levels {
        writeln!(writer, "{level:?}={count}")?;
    }
    for (index, value) in indices.into_iter().zip(filtered.iter()) {
        writeln!(
            writer,
            "t={index} s filtered={:.1} mV",
            f64::from(value.twice_mv()) / 2.0
        )?;
    }
    writer.flush()
}

#[cfg(test)]
mod report_index_tests {
    use super::*;
    #[test]
    fn standalone_report_preserves_original_indices() {
        let original = parse_codes(["2", "4", "6", "8"]).unwrap();
        let batch = Batch {
            records: original.into_records().into_iter().skip(2).collect(),
        };
        let mut bytes = Vec::new();
        write_report(&mut bytes, &batch).unwrap();
        let text = String::from_utf8(bytes).unwrap();
        assert!(text.contains("t=2 s filtered=3.0 mV"));
        assert!(text.contains("t=3 s filtered=7.0 mV"));
        assert!(!text.contains("t=0 s"));
    }
}
