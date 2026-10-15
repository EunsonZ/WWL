//! Allocation-free FIR kernel shared by std and the no_std harness.
use core::fmt;
pub const FIXED_MAX_SAMPLES: usize = 1024;
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum FixedError {
    State { value: u16 },
    Limit { actual: usize },
    Capacity { needed: usize, available: usize },
    Range { position: usize, value: u16 },
}
impl fmt::Display for FixedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::State { value } => write!(f, "previous code {value} outside 0..4095"),
            Self::Limit { actual } => write!(f, "fixed call has {actual} samples; maximum 1024"),
            Self::Capacity { needed, available } => {
                write!(f, "output needs {needed} words; available {available}")
            }
            Self::Range { position, value } => {
                write!(f, "sample {position}: code {value} outside 0..4095")
            }
        }
    }
}
impl core::error::Error for FixedError {}
#[derive(Debug, Default, Copy, Clone, PartialEq, Eq)]
pub struct FixedFir {
    previous: u16,
}
impl FixedFir {
    pub fn from_previous(previous: u16) -> Result<Self, FixedError> {
        if previous > 4095 {
            return Err(FixedError::State { value: previous });
        }
        Ok(Self { previous })
    }
    pub fn previous(self) -> u16 {
        self.previous
    }
    /// Output words are twice mV. Any Err leaves both output and state unchanged.
    pub fn process_into(&mut self, input: &[u16], output: &mut [u16]) -> Result<usize, FixedError> {
        if input.len() > FIXED_MAX_SAMPLES {
            return Err(FixedError::Limit {
                actual: input.len(),
            });
        }
        if output.len() < input.len() {
            return Err(FixedError::Capacity {
                needed: input.len(),
                available: output.len(),
            });
        }
        for (i, &value) in input.iter().enumerate() {
            if value > 4095 {
                return Err(FixedError::Range {
                    position: i + 1,
                    value,
                });
            }
        }
        for (i, &value) in input.iter().enumerate() {
            output[i] = self.previous + value; // <=8190, fits u16
            self.previous = value;
        }
        Ok(input.len())
    }
}
