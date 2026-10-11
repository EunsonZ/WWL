#include "cabi.h"
#include <climits>
#include <cstddef>
#include <cstdio>
#include <type_traits>
static_assert(std::is_standard_layout<wwl_abi_stats_v1>::value,"result must be standard layout");
static_assert(sizeof(wwl_abi_stats_v1) <= UINT32_MAX,"size field bound");
static bool unchanged(wwl_abi_stats_v1 a, wwl_abi_stats_v1 b) {
    return a.abi_version==b.abi_version && a.n==b.n && a.sum_mv==b.sum_mv &&
           a.mean_mv==b.mean_mv && a.descriptive_variance_mv2==b.descriptive_variance_mv2 &&
           a.rms2_mv2==b.rms2_mv2;
}
int main() {
    uint32_t layout[WWL_ABI_LAYOUT_WORDS] = {};
    const uint32_t expected[] = {WWL_ABI_VERSION,CHAR_BIT,sizeof(uint16_t),sizeof(uint32_t),
        sizeof(double),sizeof(wwl_abi_stats_v1),alignof(wwl_abi_stats_v1),
        offsetof(wwl_abi_stats_v1,n),offsetof(wwl_abi_stats_v1,mean_mv),offsetof(wwl_abi_stats_v1,rms2_mv2)};
    if (wwl_c_layout_v1(layout,WWL_ABI_LAYOUT_WORDS) != WWL_ABI_OK) return 1;
    for (uint32_t i=0;i<WWL_ABI_LAYOUT_WORDS;++i) if (layout[i] != expected[i]) return 1;
    const uint16_t codes[] = {2,4,6,8};
    wwl_abi_stats_v1 result = {};
    if (wwl_c_measure_v1(codes,4,1,0,1,&result,sizeof result) != WWL_ABI_OK ||
        result.abi_version!=1 || result.n!=4 || result.sum_mv!=20 || result.mean_mv!=5 ||
        result.descriptive_variance_mv2!=5 || result.rms2_mv2!=30) return 1;
    wwl_abi_stats_v1 before=result;
    const uint16_t bad[] = {4096};
    if (wwl_c_measure_v1(bad,1,1,0,1,&result,sizeof result) != WWL_ABI_INVALID || !unchanged(result,before)) return 1;
    if (wwl_c_measure_v1(codes,4,1,0,1,&result,sizeof result-1) != WWL_ABI_INVALID || !unchanged(result,before)) return 1;
    if (wwl_c_measure_v1(nullptr,0,1,0,1,&result,sizeof result) != WWL_ABI_EMPTY || !unchanged(result,before)) return 1;
    if (wwl_c_measure_v1(codes,1000001,1,0,1,&result,sizeof result) != WWL_ABI_LIMIT || !unchanged(result,before)) return 1;
    if (wwl_c_measure_v1(codes,4,0,0,1,&result,sizeof result) != WWL_ABI_INVALID || !unchanged(result,before)) return 1;
    if (wwl_c_measure_v1(codes,4,0.25,-1,0.5,&result,sizeof result) != WWL_ABI_OK ||
        result.sum_mv!=1 || result.mean_mv!=0.25 || result.descriptive_variance_mv2!=0.3125 || result.rms2_mv2!=0.375) return 1;
    std::printf("C_ABI=PASS C++consumer,layout,borrowed_input,errors,unchanged_output,units\n");
    std::printf("result_bytes=%u result_align=%u mean_offset=%u rms2_offset=%u\n",layout[5],layout[6],layout[8],layout[9]);
    return 0;
}
