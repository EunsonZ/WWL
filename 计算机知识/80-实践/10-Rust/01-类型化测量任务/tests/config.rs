use std::io::Cursor;
use wwl_measurement::*;
#[test]
fn config_defaults_ranges_duplicates_and_unknowns() {
    assert_eq!(parse_config("").unwrap(), TaskConfig::default());
    let c = parse_config("capacity=0\r\nbatch_size=1\r\nmax_samples=0\r\n").unwrap();
    assert_eq!((c.capacity(), c.batch_size(), c.max_samples()), (0, 1, 0));
    assert!(matches!(
        parse_config("capacity=17"),
        Err(ConfigError::Value { line: 1, .. })
    ));
    assert!(matches!(
        parse_config("batch_size=0"),
        Err(ConfigError::Value { .. })
    ));
    assert!(matches!(
        parse_config("max_samples=1025"),
        Err(ConfigError::Value { .. })
    ));
    assert!(matches!(
        parse_config("capacity=1\ncapacity=2"),
        Err(ConfigError::Duplicate { line: 2, .. })
    ));
    assert!(matches!(
        parse_config("worker_count=2"),
        Err(ConfigError::Unknown { line: 1, .. })
    ));
    for text in ["capacity=-1", "capacity= 1", "capacity=", "capacity=1\n\n"] {
        assert!(matches!(
            parse_config(text),
            Err(ConfigError::Syntax { .. })
        ));
    }
    assert!(matches!(
        parse_config("capacity=99999999999999999999999999999999999999999999"),
        Err(ConfigError::Value { .. })
    ));
}
#[test]
fn config_reader_caps_allocation_before_parsing() {
    assert!(read_config(Cursor::new(b"capacity=1\nbatch_size=2\nmax_samples=4\n")).is_ok());
    assert!(matches!(
        read_config(Cursor::new(vec![b'0'; 257])),
        Err(ConfigReadError::Config(ConfigError::TooLong))
    ));
    assert!(matches!(
        read_config(Cursor::new([0xff])),
        Err(ConfigReadError::Utf8)
    ));
}
#[test]
fn report_rejects_count_mismatch_before_writing() {
    let batch = parse_codes(["2"]).unwrap();
    let summary = summarize(batch.records()).unwrap();
    let mut bytes = Vec::new();
    assert!(write_summary_report(&mut bytes, &summary, &[]).is_err());
    assert!(bytes.is_empty());
}
