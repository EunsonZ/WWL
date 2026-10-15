#ifndef WWL_MEASUREMENT_H
#define WWL_MEASUREMENT_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { uint32_t status, position, written; } WwlResult;
enum { WWL_OK=0, WWL_BAD_POINTER=1, WWL_OVERLAP=2, WWL_INPUT_RANGE=3,
       WWL_STATE_RANGE=4, WWL_OUTPUT_CAPACITY=5, WWL_INPUT_LIMIT=6 };
/* Caller owns all allocations/state. No retained pointers or free function.
   Accessed regions are initialized, aligned, valid, mutually disjoint, non-racing.
   n<=1024, capacity>=n; state initialized in 0..4095; same native target/ABI.
   Empty input allows NULL input/output. Output is TWICE mV.
   Reported errors preserve output/state. Address checks do not prove lifetime. */
WwlResult wwl_fir_process(uint16_t *previous, const uint16_t *input, size_t n,
                         uint16_t *output_twice_mv, size_t output_capacity);
#ifdef __cplusplus
}
#endif
#endif
