#include "fixed.h"
#include <limits.h>
#if CHAR_BIT != 8
#error "fixed example requires 8-bit bytes and exact-width integers"
#endif
void wwl_fixed_init(wwl_fixed_state *s) {
    s->n = 0; s->sum = 0; s->squares = 0; s->previous = 0;
}
uint32_t wwl_fixed_block(wwl_fixed_state *s, const uint16_t *input, size_t n,
                         uint32_t *output, size_t capacity) {
    if (!s || (n && (!input || !output)) || capacity < n) return WWL_FIXED_INVALID;
    if (s->n > WWL_FIXED_LIMIT || (uintmax_t)n > WWL_FIXED_LIMIT - s->n)
        return WWL_FIXED_LIMIT_ERROR;
    for (size_t i = 0; i < n; ++i) if (input[i] > UINT16_C(4095)) return WWL_FIXED_INVALID;
    /* No fallible operation remains after full validation. No malloc/stdio/libm. */
    for (size_t i = 0; i < n; ++i) {
        uint64_t x = input[i]; output[i] = (uint32_t)s->previous + (uint32_t)x;
        ++s->n; s->sum += x; s->squares += x*x; s->previous = (uint16_t)x;
    }
    return WWL_FIXED_OK;
}
