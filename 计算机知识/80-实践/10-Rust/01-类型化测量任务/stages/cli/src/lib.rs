use std::io::Read;
#[derive(Debug, Copy, Clone, PartialEq)]
pub struct AdcCode(u16);
impl TryFrom<u16> for AdcCode {
    type Error = &'static str;
    fn try_from(value: u16) -> Result<Self, Self::Error> {
        if value > 4095 {
            Err("code outside 0..4095")
        } else {
            Ok(Self(value))
        }
    }
}
#[derive(Debug, Copy, Clone, PartialEq)]
pub struct Millivolt(u16);
impl From<AdcCode> for Millivolt {
    fn from(value: AdcCode) -> Self {
        Self(value.0)
    }
}
impl Millivolt {
    pub fn get(self) -> u16 {
        self.0
    }
}
#[derive(Debug, PartialEq)]
pub struct Record {
    pub index: usize,
    pub voltage: Millivolt,
}
/// Owns all records; no input slice escapes.
pub fn make_records(codes: &[u16]) -> Result<Vec<Record>, &'static str> {
    if codes.len() > 1024 {
        return Err("too many samples");
    }
    codes
        .iter()
        .enumerate()
        .map(|(index, &code)| {
            Ok(Record {
                index,
                voltage: AdcCode::try_from(code)?.into(),
            })
        })
        .collect()
}
pub fn summary(records: &[Record]) -> Result<(u32, Option<f64>), &'static str> {
    if records.len() > 1024 {
        return Err("too many samples");
    }
    let sum: u32 = records.iter().map(|r| u32::from(r.voltage.get())).sum();
    Ok((
        sum,
        if records.is_empty() {
            None
        } else {
            Some(f64::from(sum) / records.len() as f64)
        },
    ))
}
#[cfg(test)]
mod typed_tests {
    use super::*;
    #[test]
    fn fixed_and_empty() {
        let records = make_records(&[2, 4, 6, 8]).unwrap();
        assert_eq!(summary(&records), Ok((20, Some(5.0))));
        assert_eq!(summary(&[]), Ok((0, None)));
    }
    #[test]
    fn range_and_owned_result() {
        assert!(make_records(&[2, 4096]).is_err());
        let records = {
            let input = [0, 4095];
            make_records(&input).unwrap()
        };
        assert_eq!(records[1].voltage.get(), 4095);
        assert!(make_records(&vec![0; 1025]).is_err());
    }
}

#[derive(Default)]
pub struct Fir2 {
    previous: u16,
}
impl Fir2 {
    /// Consume owned records; preserve previous across every batch.
    pub fn process(&mut self, records: Vec<Record>) -> Vec<u16> {
        records
            .into_iter()
            .map(|r| {
                let code = r.voltage.get();
                let twice_mv = self.previous + code;
                self.previous = code;
                twice_mv
            })
            .collect()
    }
}
pub fn process_queue(mut queue: std::collections::VecDeque<Vec<Record>>) -> Vec<u16> {
    let mut filter = Fir2::default();
    let mut output = Vec::new();
    while let Some(batch) = queue.pop_front() {
        output.extend(filter.process(batch));
    }
    output
}
#[cfg(test)]
mod library_tests {
    use super::*;
    #[test]
    fn all_single_boundaries_preserve_state() {
        for cut in 0..=4 {
            let mut left = make_records(&[2, 4, 6, 8]).unwrap();
            let right = left.split_off(cut);
            assert_eq!(process_queue([left, right].into()), [2, 6, 10, 14]);
        }
        let mut restarted = Fir2::default();
        let first = restarted.process(make_records(&[2, 4]).unwrap());
        let second = Fir2::default().process(make_records(&[6, 8]).unwrap());
        assert_eq!([first, second].concat(), [2, 6, 6, 14]);
    }
}

/// At most 6144 input bytes (1024 five-byte u16 tokens plus separators).
/// The bounded teaching reader rejects a longer payload before parsing.
pub fn read_codes<R: std::io::Read>(reader: R) -> std::io::Result<Vec<Record>> {
    let mut text = String::new();
    reader.take(6145).read_to_string(&mut text)?;
    if text.len() > 6144 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "input bytes exceed 6144",
        ));
    }
    let codes: Vec<u16> = text
        .split_whitespace()
        .map(|s| {
            s.parse()
                .map_err(|_| std::io::Error::new(std::io::ErrorKind::InvalidData, "not a u16"))
        })
        .collect::<Result<_, _>>()?;
    make_records(&codes).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
}
pub fn write_report<W: std::io::Write>(mut writer: W, records: &[Record]) -> std::io::Result<()> {
    let (sum, mean) =
        summary(records).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    writeln!(writer, "sum_mV={sum} mean_mV={mean:?}")?;
    writer.flush()
}
#[cfg(test)]
mod io_tests {
    use super::*;
    #[test]
    fn input_boundaries_and_report() {
        let records = read_codes(&b"2 4 6 8"[..]).unwrap();
        let mut bytes = Vec::new();
        write_report(&mut bytes, &records).unwrap();
        assert_eq!(
            String::from_utf8(bytes).unwrap(),
            "sum_mV=20 mean_mV=Some(5.0)\n"
        );
        assert!(read_codes(&b"2 4096"[..]).is_err());
        assert!(read_codes(&vec![b' '; 6145][..]).is_err());
        assert_eq!(summary(&read_codes(&b""[..]).unwrap()), Ok((0, None)));
    }
    #[test]
    fn io_faults_propagate() {
        struct Broken;
        impl std::io::Read for Broken {
            fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::ErrorKind::PermissionDenied.into())
            }
        }
        impl std::io::Write for Broken {
            fn write(&mut self, _: &[u8]) -> std::io::Result<usize> {
                Err(std::io::ErrorKind::BrokenPipe.into())
            }
            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }
        assert_eq!(
            read_codes(Broken).unwrap_err().kind(),
            std::io::ErrorKind::PermissionDenied
        );
        assert_eq!(
            write_report(Broken, &[]).unwrap_err().kind(),
            std::io::ErrorKind::BrokenPipe
        );
    }
}
