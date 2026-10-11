use std::collections::VecDeque;
use std::io::{self, Cursor, Write};
use wwl_measurement::*;

#[test]
fn fixed_units_and_classification() {
    let batch = parse_codes(["2", "4", "6", "8"]).unwrap();
    let summary = summarize(batch.records()).unwrap();
    assert_eq!(
        (summary.count, summary.sum_mv, summary.mean_mv),
        (4, 20, Some(5.0))
    );
    assert_eq!(
        summary.levels.into_iter().collect::<Vec<_>>(),
        vec![(Level::Low, 1), (Level::Normal, 2), (Level::High, 1)]
    );
    assert_eq!(batch.records()[3].index.get(), 3);
}
#[test]
fn boundaries_and_empty_are_explicit() {
    assert!(parse_codes(["0", "4095"]).is_ok());
    assert!(matches!(
        parse_codes(["4096"]),
        Err(InputError::Range {
            position: 1,
            value: 4096
        })
    ));
    for token in ["", "-1", "+1", " 2", "65536", "x"] {
        assert!(matches!(
            parse_codes([token]),
            Err(InputError::Syntax { position: 1, .. })
        ));
    }
    assert_eq!(
        summarize(parse_codes(Vec::<String>::new()).unwrap().records())
            .unwrap()
            .mean_mv,
        None
    );
    assert!(parse_codes(std::iter::repeat("4095").take(MAX_SAMPLES)).is_ok());
    assert!(matches!(
        parse_codes(std::iter::repeat("0").take(MAX_SAMPLES + 1)),
        Err(InputError::TooMany { .. })
    ));
    assert_eq!(
        summarize(
            parse_codes(std::iter::repeat("4095").take(MAX_SAMPLES))
                .unwrap()
                .records()
        )
        .unwrap()
        .sum_mv,
        4_193_280
    );
}
#[test]
fn every_split_preserves_state_and_reset_is_counterexample() {
    let texts = ["2", "4", "6", "8"];
    for split in 0..=4 {
        let mut queue = VecDeque::from([
            parse_codes(&texts[..split]).unwrap(),
            parse_codes(&texts[split..]).unwrap(),
        ]);
        let output = drain_batches(&mut queue, &mut Fir2::default());
        assert_eq!(
            output.iter().map(|x| x.twice_mv()).collect::<Vec<_>>(),
            [2, 6, 10, 14]
        );
        assert!(queue.is_empty());
    }
    let mut output = Fir2::default().process(parse_codes(["2", "4"]).unwrap());
    output.extend(Fir2::default().process(parse_codes(["6", "8"]).unwrap()));
    assert_eq!(
        output.iter().map(|x| x.twice_mv()).collect::<Vec<_>>(),
        [2, 6, 6, 14]
    );
    assert_eq!(
        Fir2::default().process(parse_codes(["1"]).unwrap())[0].twice_mv(),
        1
    );
}
#[test]
fn borrowed_then_mutated_and_strong_failure() {
    let mut batch = parse_codes(["2"]).unwrap();
    let view = batch.records();
    assert_eq!(view[0].voltage.get(), 2); // last use; borrowing ends
    batch.push_code(AdcCode::try_from(4).unwrap()).unwrap();
    while batch.records().len() < MAX_SAMPLES {
        batch.push_code(AdcCode::try_from(0).unwrap()).unwrap();
    }
    let before = summarize(batch.records()).unwrap();
    assert!(batch.push_code(AdcCode::try_from(8).unwrap()).is_err());
    assert_eq!(summarize(batch.records()).unwrap(), before);
}
#[test]
fn bounded_io_and_crlf() {
    let batch = read_codes(Cursor::new(b"2\r\n4\n6\n8")).unwrap();
    assert_eq!(summarize(batch.records()).unwrap().sum_mv, 20);
    assert!(matches!(
        read_codes(Cursor::new(vec![b'2'; 65])),
        Err(ReadError::LineTooLong { line: 1 })
    ));
    assert!(matches!(
        read_codes(Cursor::new([0xff, b'\n'])),
        Err(ReadError::Utf8 { line: 1 })
    ));
    assert!(matches!(
        read_codes(Cursor::new(b"2\n\n")),
        Err(ReadError::Input(InputError::Syntax { position: 2, .. }))
    ));
}
struct Broken;
impl io::Read for Broken {
    fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
        Err(io::Error::other("injected read failure"))
    }
}
impl io::BufRead for Broken {
    fn fill_buf(&mut self) -> io::Result<&[u8]> {
        Err(io::Error::other("injected read failure"))
    }
    fn consume(&mut self, _: usize) {}
}
impl Write for Broken {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err(io::Error::other("injected write failure"))
    }
    fn flush(&mut self) -> io::Result<()> {
        Err(io::Error::other("injected flush failure"))
    }
}
#[test]
fn io_errors_are_observable() {
    assert!(matches!(
        read_codes(Broken),
        Err(ReadError::Io { line: 1, .. })
    ));
    let batch = parse_codes(["2"]).unwrap();
    assert!(write_report(Broken, &batch).is_err());
    let mut bytes = Vec::new();
    write_report(&mut bytes, &batch).unwrap();
    assert!(String::from_utf8(bytes)
        .unwrap()
        .contains("filtered=1.0 mV"));
}

// Generates named tests; a function cannot introduce these item names.
macro_rules! level_cases {
    ($( $name:ident : $code:expr => $expected:expr ),* $(,)?) => {
        $(#[test] fn $name() {
            let raw = $code;
            let value = Millivolt::from(AdcCode::try_from(raw).unwrap());
            assert_eq!(classify(value), $expected);
        })*
    };
}
level_cases! { at_low_end: 3_u16 => Level::Low, at_normal_start: 4_u16 => Level::Normal,
at_normal_end: 6_u16 => Level::Normal, at_high_start: 7_u16 => Level::High, }
struct FlushBroken(Vec<u8>);
impl Write for FlushBroken {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.0.extend_from_slice(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Err(io::Error::other("injected flush failure"))
    }
}
#[test]
fn flush_failure_follows_partial_external_output() {
    let batch = parse_codes(["2"]).unwrap();
    let mut writer = FlushBroken(Vec::new());
    assert!(write_report(&mut writer, &batch).is_err());
    assert!(!writer.0.is_empty()); // Result::Err cannot retract already written bytes
}
#[test]
fn summary_rejects_oversize_slice_and_copy_is_independent() {
    let batch = parse_codes(["2"]).unwrap();
    let record = batch.records()[0];
    assert!(summarize(&vec![record; MAX_SAMPLES + 1]).is_err());
    let copied = batch.records().to_vec();
    let moved = batch.into_records();
    assert_eq!(copied, moved);
}
