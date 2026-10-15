//! Caller-owned buffers and state; no allocation, retained pointers or callbacks.
//! ```compile_fail
//! use wwl_measurement::ffi::wwl_fir_process;
//! let mut previous=0_u16;
//! let input=[2_u16];
//! let mut output=[0_u16];
//! wwl_fir_process(&mut previous,input.as_ptr(),1,output.as_mut_ptr(),1);
//! ```
use crate::fixed_core::{FixedError, FixedFir, FIXED_MAX_SAMPLES};
#[repr(C)]
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct WwlResult {
    pub status: u32,
    pub position: u32,
    pub written: u32,
}
pub const OK: u32 = 0;
pub const BAD_POINTER: u32 = 1;
pub const OVERLAP: u32 = 2;
pub const INPUT_RANGE: u32 = 3;
pub const STATE_RANGE: u32 = 4;
pub const OUTPUT_CAPACITY: u32 = 5;
pub const INPUT_LIMIT: u32 = 6;
fn failed(status: u32, position: usize) -> WwlResult {
    WwlResult {
        status,
        position: position as u32,
        written: 0,
    }
}
fn region(ptr: *const u16, len: usize) -> Option<(usize, usize)> {
    if len == 0 {
        return Some((0, 0));
    }
    let begin = ptr as usize;
    if ptr.is_null() || begin % core::mem::align_of::<u16>() != 0 {
        return None;
    }
    Some((
        begin,
        begin.checked_add(len.checked_mul(core::mem::size_of::<u16>())?)?,
    ))
}
fn overlaps(a: (usize, usize), b: (usize, usize)) -> bool {
    a.0 < a.1 && b.0 < b.1 && a.0 < b.1 && b.0 < a.1
}
/// Updates caller-owned previous code and the first input_len output words.
/// Empty input accepts null input/output, but state must still be valid.
/// Any reported error leaves state/output unchanged.
///
/// # Safety
/// Null/misaligned/overlapping shapes are rejected without memory access. For
/// pointers that pass these checks, state points to one initialized writable
/// u16. Nonempty input/output point to
/// initialized readable/writable allocations of stated accessed lengths, with
/// output_capacity describing real writable storage. Accessed regions are
/// disjoint and obey shared/exclusive access; no racing access/free is allowed.
/// Address checks cannot prove allocation validity, lifetime or provenance.
/// C and Rust use compatible native target/ABI. No pointer is retained or freed.
#[no_mangle]
pub unsafe extern "C" fn wwl_fir_process(
    previous: *mut u16,
    input: *const u16,
    input_len: usize,
    output_twice_mv: *mut u16,
    output_capacity: usize,
) -> WwlResult {
    if input_len > FIXED_MAX_SAMPLES {
        return failed(INPUT_LIMIT, 0);
    }
    if output_capacity < input_len {
        return failed(OUTPUT_CAPACITY, 0);
    }
    let (Some(state_region), Some(input_region), Some(output_region)) = (
        region(previous, 1),
        region(input, input_len),
        region(output_twice_mv, input_len),
    ) else {
        return failed(BAD_POINTER, 0);
    };
    if overlaps(state_region, input_region)
        || overlaps(state_region, output_region)
        || overlaps(input_region, output_region)
    {
        return failed(OVERLAP, 0);
    }
    // SAFETY: caller provides valid initialized state; null/alignment/span checked.
    let state = unsafe { previous.read() };
    let mut filter = match FixedFir::from_previous(state) {
        Ok(value) => value,
        Err(_) => return failed(STATE_RANGE, 0),
    };
    let result = if input_len == 0 {
        filter.process_into(&[], &mut [])
    } else {
        // SAFETY: caller provides valid allocations for this bounded length;
        // aligned/nonnull/non-wrapping regions were checked disjoint before refs.
        let input_slice = unsafe { core::slice::from_raw_parts(input, input_len) };
        let output_slice = unsafe { core::slice::from_raw_parts_mut(output_twice_mv, input_len) };
        filter.process_into(input_slice, output_slice)
    };
    match result {
        Ok(written) => {
            // SAFETY: state remains valid/writable and disjoint for the call.
            unsafe {
                previous.write(filter.previous());
            }
            WwlResult {
                status: OK,
                position: 0,
                written: written as u32,
            }
        }
        Err(FixedError::Range { position, .. }) => failed(INPUT_RANGE, position),
        Err(FixedError::Capacity { .. }) => failed(OUTPUT_CAPACITY, 0),
        Err(FixedError::Limit { .. }) => failed(INPUT_LIMIT, 0),
        Err(FixedError::State { .. }) => failed(STATE_RANGE, 0),
    }
}
