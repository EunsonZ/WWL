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
fn main() -> Result<(), &'static str> {
    let tokens: Vec<String> = std::env::args().skip(1).collect();
    let codes: Vec<u16> = if tokens.is_empty() {
        vec![2, 4, 6, 8]
    } else {
        tokens
            .iter()
            .map(|s| s.parse::<u16>().map_err(|_| "not a u16"))
            .collect::<Result<_, _>>()?
    };
    let records = make_records(&codes)?;
    println!("{:?}", summary(&records));
    Ok(())
}
