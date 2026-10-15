#include "sum.h"

#include <limits.h>

/* Reject a target where uint32_t would promote to a signed int before +=. */
#if UINT32_MAX <= INT_MAX
#error "sum_u32 needs uint32_t not representable by int"
#endif

uint32_t sum_u32(const uint32_t values[], size_t count) {
    uint32_t total = 0;
    for (size_t index = 0; index < count; ++index) {
        total += values[index];
    }
    return total;
}
