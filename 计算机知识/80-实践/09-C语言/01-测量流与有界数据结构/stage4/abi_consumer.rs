use std::mem::{align_of, offset_of, size_of};
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq)]
struct Stats {
    abi_version: u32,
    n: u32,
    sum_mv: f64,
    mean_mv: f64,
    descriptive_variance_mv2: f64,
    rms2_mv2: f64,
}
extern "C" {
    fn wwl_c_measure_v1(codes: *const u16, n: u32, scale: f64, offset: f64,
        interval: f64, out: *mut Stats, out_bytes: u32) -> u32;
    fn wwl_c_layout_v1(words: *mut u32, n: u32) -> u32;
}
fn main() {
    let mut layout = [0_u32; 10];
    // SAFETY: C writes exactly 10 u32 into this live/aligned caller array.
    assert_eq!(unsafe { wwl_c_layout_v1(layout.as_mut_ptr(), 10) }, 0);
    let expected = [1, 8, size_of::<u16>() as u32, size_of::<u32>() as u32,
        size_of::<f64>() as u32, size_of::<Stats>() as u32, align_of::<Stats>() as u32,
        offset_of!(Stats, n) as u32, offset_of!(Stats, mean_mv) as u32,
        offset_of!(Stats, rms2_mv2) as u32];
    assert_eq!(layout, expected);
    let codes = [2_u16, 4, 6, 8];
    let mut result = Stats { abi_version: 0, n: 0, sum_mv: 0.0, mean_mv: 0.0,
        descriptive_variance_mv2: 0.0, rms2_mv2: 0.0 };
    // SAFETY: codes has four readable u16; result is separate live writable repr(C)
    // storage. No pointer is retained or freed, and C does not call back into Rust.
    let status = unsafe { wwl_c_measure_v1(codes.as_ptr(), 4, 1.0, 0.0, 1.0,
        &mut result, size_of::<Stats>() as u32) };
    assert_eq!(status, 0);
    assert_eq!((result.abi_version, result.n), (1, 4));
    assert_eq!((result.sum_mv, result.mean_mv, result.descriptive_variance_mv2, result.rms2_mv2),
        (20.0, 5.0, 5.0, 30.0));
    let before = result;
    let bad = [4096_u16];
    // Each tuple carries a real pointer plus its admissible extent, or a count
    // rejected before reading. No fake valid range is ever dereferenced.
    let cases = [
        (bad.as_ptr(), 1, 1.0, 0.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1.0, 0.0, 1.0, size_of::<Stats>() as u32 - 1, 1),
        (std::ptr::null(), 0, 1.0, 0.0, 1.0, size_of::<Stats>() as u32, 3),
        (codes.as_ptr(), 1_000_001, 1.0, 0.0, 1.0, size_of::<Stats>() as u32, 2),
        (std::ptr::null(), 1, 1.0, 0.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 0.0, 0.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, f64::NAN, 0.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1.0, f64::INFINITY, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1.0, 0.0, f64::NAN, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1_000_001.0, 0.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1.0, 1_000_000_001.0, 1.0, size_of::<Stats>() as u32, 1),
        (codes.as_ptr(), 4, 1.0, 0.0, 0.0, size_of::<Stats>() as u32, 1),
    ];
    for (pointer, n, scale, offset, interval, bytes, expected_status) in cases {
        // SAFETY: admissible nonnull ranges are real arrays; invalid pointer/count
        // pairs and wrong sizes are documented early rejects. result remains a
        // valid separate object, and C retains/frees no caller storage.
        let got = unsafe { wwl_c_measure_v1(pointer, n, scale, offset, interval,
            &mut result, bytes) };
        assert_eq!(got, expected_status);
        assert_eq!(result, before); // all six fields, checked after every call
    }
    // Null out is an explicit INVALID path; no output storage is accessed.
    assert_eq!(unsafe { wwl_c_measure_v1(codes.as_ptr(), 4, 1.0, 0.0, 1.0,
        std::ptr::null_mut(), size_of::<Stats>() as u32) }, 1);
    let saved_layout = layout;
    // Ten real slots exist even when the wrong logical length is supplied.
    assert_eq!(unsafe { wwl_c_layout_v1(layout.as_mut_ptr(), 9) }, 1);
    assert_eq!(layout, saved_layout);
    assert_eq!(unsafe { wwl_c_layout_v1(std::ptr::null_mut(), 10) }, 1);
    println!("C_ABI_RUST=PASS repr_C,layout,12_error_cases,all_fields_unchanged,null_output,layout_rejection");
    // Any assert panic is in this Rust caller AFTER C has returned, not across C.
}
