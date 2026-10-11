use std::process::Command;
#[test]
fn public_cli_fixed_and_invalid_have_distinct_status() {
    let ok = Command::new(env!("CARGO_BIN_EXE_wwl-measurement"))
        .output()
        .unwrap();
    assert!(ok.status.success());
    let text = String::from_utf8(ok.stdout).unwrap();
    assert!(text.contains("sum=20 mV\nmean=5.000 mV"));
    let bad = Command::new(env!("CARGO_BIN_EXE_wwl-measurement"))
        .args(["--codes", "2", "4096"])
        .output()
        .unwrap();
    assert_eq!(bad.status.code(), Some(2));
    assert!(bad.stdout.is_empty());
    assert!(String::from_utf8(bad.stderr)
        .unwrap()
        .contains("sample 2: code 4096 outside 0..4095"));
}

#[test]
fn configuration_errors_have_no_partial_report() {
    let bin = env!("CARGO_BIN_EXE_wwl-measurement");
    for args in [
        vec!["--config", "fixtures/invalid.conf"],
        vec![
            "--config",
            "fixtures/task.conf",
            "--codes",
            "2",
            "4",
            "6",
            "8",
            "10",
        ],
    ] {
        let result = Command::new(bin).args(args).output().unwrap();
        assert_eq!(result.status.code(), Some(2));
        assert!(result.stdout.is_empty());
    }
}
#[test]
fn feature_gate_or_threaded_report_is_observable() {
    let result = Command::new(env!("CARGO_BIN_EXE_wwl-measurement"))
        .args(["--config", "fixtures/task.conf", "--threaded"])
        .output()
        .unwrap();
    #[cfg(feature = "threaded")]
    {
        assert!(result.status.success());
        assert!(String::from_utf8(result.stdout)
            .unwrap()
            .contains("filtered=7.0 mV"));
    }
    #[cfg(not(feature = "threaded"))]
    {
        assert_eq!(result.status.code(), Some(2));
        assert!(String::from_utf8(result.stderr)
            .unwrap()
            .contains("requires build feature"));
        assert!(result.stdout.is_empty());
    }
}
