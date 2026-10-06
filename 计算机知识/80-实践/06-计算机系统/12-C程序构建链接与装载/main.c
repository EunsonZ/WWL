#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

#include "sum.h"

int main(void) {
    const uint32_t values[] = {7U, 11U, 23U, 59U};
    const uint32_t total = sum_u32(values, sizeof(values) / sizeof(values[0]));
    printf("sum=%" PRIu32 "\n", total);
    return total == 100U ? 0 : 1;
}
