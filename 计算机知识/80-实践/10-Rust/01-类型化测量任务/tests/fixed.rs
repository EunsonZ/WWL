#![cfg(feature = "fixed")]
use wwl_measurement::fixed_core::*;
use wwl_measurement::{parse_codes, Fir2};
#[test]
fn fixed_matches_owned_kernel_across_arbitrary_partitions() {
    for mask in 0..8 {
        let input = [2, 4, 6, 8];
        let mut output = [99; 4];
        let mut filter = FixedFir::default();
        let mut begin = 0;
        for end in 1..=4 {
            if end == 4 || mask & (1 << (end - 1)) != 0 {
                filter
                    .process_into(&input[begin..end], &mut output[begin..end])
                    .unwrap();
                begin = end;
            }
        }
        let owned = Fir2::default().process(parse_codes(["2", "4", "6", "8"]).unwrap());
        assert_eq!(
            output,
            owned
                .iter()
                .map(|x| x.twice_mv())
                .collect::<Vec<_>>()
                .as_slice()
        );
    }
}
#[test]
fn prevalidation_preserves_state_and_output_on_all_errors() {
    let mut f = FixedFir::from_previous(8).unwrap();
    let mut out = [99; 2];
    assert_eq!(
        f.process_into(&[2, 4096], &mut out),
        Err(FixedError::Range {
            position: 2,
            value: 4096
        })
    );
    assert_eq!((f.previous(), out), (8, [99; 2]));
    assert!(matches!(
        f.process_into(&[2, 4], &mut out[..1]),
        Err(FixedError::Capacity { .. })
    ));
    assert_eq!(f.previous(), 8);
    assert!(matches!(
        f.process_into(&[0; 1025], &mut [0; 1025]),
        Err(FixedError::Limit { actual: 1025 })
    ));
    assert_eq!(f.previous(), 8);
    assert!(FixedFir::from_previous(4096).is_err());
    for code in 0..=4095 {
        let mut f = FixedFir::from_previous(code).unwrap();
        let mut out = [0];
        f.process_into(&[code], &mut out).unwrap();
        assert_eq!(out[0], 2 * code);
    }
}
#[cfg(feature = "ffi")]
#[test]
fn ffi_layout_and_defensive_error_paths() {
    use wwl_measurement::ffi::*;
    assert_eq!(
        (
            std::mem::size_of::<WwlResult>(),
            std::mem::align_of::<WwlResult>()
        ),
        (12, 4)
    );
    assert_eq!(
        (
            std::mem::offset_of!(WwlResult, position),
            std::mem::offset_of!(WwlResult, written)
        ),
        (4, 8)
    );
    let mut prev = 0;
    let input = [2, 4, 6, 8];
    let mut output = [99; 4];
    // All accessed allocations are valid and disjoint. Rejected shape cases below
    // return before dereference or constructing any overlapping references.
    unsafe {
        let r = wwl_fir_process(&mut prev, input.as_ptr(), 4, output.as_mut_ptr(), 4);
        assert_eq!(
            (r.status, r.written, prev, output),
            (OK, 4, 8, [2, 6, 10, 14])
        );
        assert_eq!(
            wwl_fir_process(&mut prev, std::ptr::null(), 0, std::ptr::null_mut(), 0).status,
            OK
        );
        assert_eq!(
            wwl_fir_process(
                std::ptr::null_mut(),
                input.as_ptr(),
                4,
                output.as_mut_ptr(),
                4
            )
            .status,
            BAD_POINTER
        );
        assert_eq!(
            wwl_fir_process(&mut prev, input.as_ptr(), 1025, output.as_mut_ptr(), 4).status,
            INPUT_LIMIT
        );
        assert_eq!(
            wwl_fir_process(&mut prev, input.as_ptr(), 4, output.as_mut_ptr(), 3).status,
            OUTPUT_CAPACITY
        );
        let ptr = output.as_mut_ptr();
        assert_eq!(wwl_fir_process(&mut prev, ptr, 4, ptr, 4).status, OVERLAP);
        let bad = [2, 4096];
        let saved = output;
        let old = prev;
        let r = wwl_fir_process(&mut prev, bad.as_ptr(), 2, output.as_mut_ptr(), 4);
        assert_eq!((r.status, r.position, r.written), (INPUT_RANGE, 2, 0));
        assert_eq!((prev, output), (old, saved));
        prev = 4096;
        assert_eq!(
            wwl_fir_process(&mut prev, input.as_ptr(), 4, output.as_mut_ptr(), 4).status,
            STATE_RANGE
        );
        assert_eq!((prev, output), (4096, saved));
    }
}
