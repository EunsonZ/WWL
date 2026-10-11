//! Strict task configuration, independent of the threaded feature.
//! Fields cannot be bypassed by constructing unchecked configuration values.
//! ```compile_fail
//! use wwl_measurement::TaskConfig;
//! let config = TaskConfig { capacity: 17, batch_size: 0, max_samples: 9999 };
//! ```
use crate::MAX_SAMPLES;
use std::fmt;
use std::io::{self, Read};
pub const MAX_CONFIG_BYTES: usize = 256;
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct TaskConfig {
    capacity: usize,
    batch_size: usize,
    max_samples: usize,
}
impl Default for TaskConfig {
    fn default() -> Self {
        Self {
            capacity: 2,
            batch_size: 2,
            max_samples: MAX_SAMPLES,
        }
    }
}
impl TaskConfig {
    pub fn try_new(
        capacity: usize,
        batch_size: usize,
        max_samples: usize,
    ) -> Result<Self, ConfigError> {
        for (key, value, valid) in [
            ("capacity", capacity, capacity <= 16),
            (
                "batch_size",
                batch_size,
                (1..=MAX_SAMPLES).contains(&batch_size),
            ),
            ("max_samples", max_samples, max_samples <= MAX_SAMPLES),
        ] {
            if !valid {
                return Err(ConfigError::Value {
                    line: 0,
                    key: key.into(),
                    value: value.to_string(),
                });
            }
        }
        Ok(Self {
            capacity,
            batch_size,
            max_samples,
        })
    }
    pub fn capacity(self) -> usize {
        self.capacity
    }
    pub fn batch_size(self) -> usize {
        self.batch_size
    }
    pub fn max_samples(self) -> usize {
        self.max_samples
    }
}
#[derive(Debug, PartialEq, Eq)]
pub enum ConfigError {
    Syntax {
        line: usize,
    },
    Unknown {
        line: usize,
        key: String,
    },
    Duplicate {
        line: usize,
        key: String,
    },
    Value {
        line: usize,
        key: String,
        value: String,
    },
    TooLong,
}
impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Syntax { line } => write!(f,"config line {line}: expected key=ASCII-digits without whitespace"),
            Self::Unknown { line,key } => write!(f,"config line {line}: unknown key {key:?}"),
            Self::Duplicate { line,key } => write!(f,"config line {line}: duplicate key {key:?}"),
            Self::Value { line,key,value } => write!(f,"config line {line}: invalid {key}={value}; capacity 0..16, batch_size 1..1024, max_samples 0..1024"),
            Self::TooLong => write!(f,"config exceeds {MAX_CONFIG_BYTES} bytes"),
        }
    }
}
impl std::error::Error for ConfigError {}
pub fn parse_config(text: &str) -> Result<TaskConfig, ConfigError> {
    if text.len() > MAX_CONFIG_BYTES {
        return Err(ConfigError::TooLong);
    }
    let mut config = TaskConfig::default();
    let mut seen = [false; 3];
    for (offset, line_text) in text.lines().enumerate() {
        let line = offset + 1;
        let (key, value) = line_text
            .split_once('=')
            .ok_or(ConfigError::Syntax { line })?;
        let slot = match key {
            "capacity" => 0,
            "batch_size" => 1,
            "max_samples" => 2,
            _ => {
                return Err(ConfigError::Unknown {
                    line,
                    key: key.into(),
                })
            }
        };
        if seen[slot] {
            return Err(ConfigError::Duplicate {
                line,
                key: key.into(),
            });
        }
        if value.is_empty() || !value.bytes().all(|b| b.is_ascii_digit()) {
            return Err(ConfigError::Syntax { line });
        }
        let invalid = || ConfigError::Value {
            line,
            key: key.into(),
            value: value.into(),
        };
        let number = value.parse::<usize>().map_err(|_| invalid())?;
        match slot {
            0 if number <= 16 => config.capacity = number,
            1 if (1..=MAX_SAMPLES).contains(&number) => config.batch_size = number,
            2 if number <= MAX_SAMPLES => config.max_samples = number,
            _ => return Err(invalid()),
        }
        seen[slot] = true;
    }
    Ok(config)
}
#[derive(Debug)]
pub enum ConfigReadError {
    Io(io::Error),
    Utf8,
    Config(ConfigError),
}
impl fmt::Display for ConfigReadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(error) => write!(f, "config I/O: {error}"),
            Self::Utf8 => write!(f, "config is not UTF-8"),
            Self::Config(error) => error.fmt(f),
        }
    }
}
impl std::error::Error for ConfigReadError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Config(error) => Some(error),
            _ => None,
        }
    }
}
pub fn read_config<R: Read>(reader: R) -> Result<TaskConfig, ConfigReadError> {
    let mut bytes = Vec::new();
    reader
        .take((MAX_CONFIG_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(ConfigReadError::Io)?;
    if bytes.len() > MAX_CONFIG_BYTES {
        return Err(ConfigReadError::Config(ConfigError::TooLong));
    }
    let text = String::from_utf8(bytes).map_err(|_| ConfigReadError::Utf8)?;
    parse_config(&text).map_err(ConfigReadError::Config)
}
