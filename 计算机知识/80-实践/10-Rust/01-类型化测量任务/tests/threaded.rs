#![cfg(feature = "threaded")]
use wwl_measurement::threaded::*;
use wwl_measurement::*;
#[test]
fn all_split_sizes_and_capacities_match_serial_exactly() {
    for capacity in [0, 1, 2, 16] {
        for size in 1..=5 {
            let config = TaskConfig::try_new(capacity, size, 4).unwrap();
            let mut batches = split_batch(parse_codes(["2", "4", "6", "8"]).unwrap(), config);
            batches.insert(0, Batch::default());
            batches.push(Batch::default());
            let output = process_threaded(batches, config).unwrap();
            assert_eq!(
                output.iter().map(|x| x.twice_mv()).collect::<Vec<_>>(),
                [2, 6, 10, 14]
            );
        }
    }
}
#[test]
fn empty_limit_sequence_and_batch_object_limits_are_distinct() {
    let config = TaskConfig::try_new(0, 2, 0).unwrap();
    assert!(process_threaded(vec![], config).unwrap().is_empty());
    assert!(matches!(
        process_threaded(vec![parse_codes(["2"]).unwrap()], config),
        Err(TaskError::Limit { limit: 0 })
    ));
    let independently_indexed = vec![
        parse_codes(["2", "4"]).unwrap(),
        parse_codes(["6", "8"]).unwrap(),
    ];
    assert!(matches!(
        process_threaded(independently_indexed, TaskConfig::default()),
        Err(TaskError::Sequence {
            expected: 2,
            actual: 0
        })
    ));
    let empty_batches = (0..1025).map(|_| Batch::default()).collect();
    assert!(matches!(
        process_threaded(empty_batches, TaskConfig::default()),
        Err(TaskError::BatchCountLimit {
            limit: 1024,
            actual: 1025
        })
    ));
}

#[test]
fn every_arbitrary_partition_preserves_indices_and_filter_state() {
    for mask in 0..8 {
        let mut remaining = parse_codes(["2", "4", "6", "8"]).unwrap();
        let mut batches = vec![Batch::default()];
        let mut previous = 0;
        for cut in 1..=3 {
            if mask & (1 << (cut - 1)) != 0 {
                let (left, right) = split_batch_at(remaining, cut - previous).unwrap();
                batches.push(left);
                batches.push(Batch::default());
                remaining = right;
                previous = cut;
            }
        }
        batches.push(remaining);
        batches.push(Batch::default());
        let result = process_threaded(batches, TaskConfig::try_new(1, 2, 4).unwrap()).unwrap();
        assert_eq!(
            result.iter().map(|x| x.twice_mv()).collect::<Vec<_>>(),
            [2, 6, 10, 14]
        );
    }
    assert!(matches!(
        split_batch_at(parse_codes(["2"]).unwrap(), 2),
        Err(TaskError::BatchBoundary { index: 2, len: 1 })
    ));
}

#[test]
fn public_suffix_report_retains_identity_and_batch_limit_names_resource() {
    let (_, suffix) = split_batch_at(parse_codes(["2", "4", "6", "8"]).unwrap(), 2).unwrap();
    assert_eq!(
        suffix
            .records()
            .iter()
            .map(|r| r.index.get())
            .collect::<Vec<_>>(),
        [2, 3]
    );
    let mut bytes = Vec::new();
    write_report(&mut bytes, &suffix).unwrap();
    let text = String::from_utf8(bytes).unwrap();
    assert!(text.contains("t=2 s filtered=3.0 mV"));
    assert!(text.contains("t=3 s filtered=7.0 mV"));
    assert!(!text.contains("t=0 s"));
    let error = process_threaded(
        (0..1025).map(|_| Batch::default()).collect(),
        TaskConfig::default(),
    )
    .unwrap_err();
    assert!(error.to_string().contains("1025 batch objects"));
    assert!(!error.to_string().contains("total samples"));
    let error = process_threaded(
        vec![parse_codes(["2"]).unwrap()],
        TaskConfig::try_new(1, 1, 0).unwrap(),
    )
    .unwrap_err();
    assert!(error.to_string().contains("0 total samples"));
}
