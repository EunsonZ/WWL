#include "fixed.h"
#include <stdio.h>
static int same(wwl_fixed_state a, wwl_fixed_state b) {
    return a.n==b.n && a.sum==b.sum && a.squares==b.squares && a.previous==b.previous;
}
int main(void) {
    uint16_t input[] = {2,4,6,8}; uint32_t expected[] = {2,6,10,14};
    for (unsigned partitions = 0; partitions < 8; ++partitions) {
        wwl_fixed_state state; wwl_fixed_init(&state); uint32_t output[4] = {0};
        size_t start = 0;
        for (size_t end = 1; end <= 4; ++end) {
            if (end == 4 || (partitions & (1U << (end-1)))) {
                if (wwl_fixed_block(&state,input+start,end-start,output+start,4-start) != WWL_FIXED_OK) return 1;
                start = end;
            }
        }
        for (size_t i = 0; i < 4; ++i) if (output[i] != expected[i]) return 1;
        if (state.n != 4 || state.sum != 20 || state.squares != 120) return 1;
        wwl_fixed_state before = state; uint16_t bad[] = {2,4096}; uint32_t preserved[] = {99,98};
        if (wwl_fixed_block(&state,bad,2,preserved,2) != WWL_FIXED_INVALID ||
            !same(state,before) || preserved[0] != 99 || preserved[1] != 98) return 1;
        if (wwl_fixed_block(&state,input,4,preserved,2) != WWL_FIXED_INVALID || !same(state,before)) return 1;
        if (wwl_fixed_block(&state,NULL,0,NULL,0) != WWL_FIXED_OK || !same(state,before)) return 1;
    }
    wwl_fixed_state state; wwl_fixed_init(&state); uint16_t code=4095; uint32_t output;
    for (uint32_t i = 0; i < WWL_FIXED_LIMIT; ++i)
        if (wwl_fixed_block(&state,&code,1,&output,1) != WWL_FIXED_OK) return 1;
    wwl_fixed_state before = state; output=99;
    if (wwl_fixed_block(&state,&code,1,&output,1) != WWL_FIXED_LIMIT_ERROR || !same(state,before) || output!=99) return 1;
    if (state.sum != UINT64_C(4193280) || state.squares != UINT64_C(17171481600)) return 1;
    puts("fixed_buffer=PASS partitions,precision,bad_code,capacity,limit,unchanged_failure"); return 0;
}
