#ifndef WWL_FIXED_H
#define WWL_FIXED_H
#include <stddef.h>
#include <stdint.h>
#define WWL_FIXED_LIMIT UINT32_C(1024)
#define WWL_FIXED_OK UINT32_C(0)
#define WWL_FIXED_INVALID UINT32_C(1)
#define WWL_FIXED_LIMIT_ERROR UINT32_C(2)
typedef struct { uint32_t n; uint64_t sum, squares; uint16_t previous; } wwl_fixed_state;
void wwl_fixed_init(wwl_fixed_state *state);
/* Caller owns initialized state and actual storage. Size/capacity checks happen
 * before access: for an accepted size, readable input[n] and writable output[n].
 * Input, output and state must not overlap; output_capacity>=n. No dynamic storage.
 * Failure leaves state and output unchanged. Output is 2*y in code units,
 * preserving half-code precision with scale=1 and physical zero offset. */
uint32_t wwl_fixed_block(wwl_fixed_state *state, const uint16_t *input, size_t n,
                         uint32_t *output, size_t output_capacity);
#endif
