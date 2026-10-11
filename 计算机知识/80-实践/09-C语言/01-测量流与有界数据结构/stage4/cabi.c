#include "cabi.h"
#include "measure.h"
#include <limits.h>
#include <stddef.h>
#include <stdalign.h>
_Static_assert(sizeof(wwl_abi_stats_v1) <= UINT32_MAX, "ABI size must fit uint32_t");
uint32_t wwl_c_measure_v1(const uint16_t *codes, uint32_t n, double scale,
                         double offset, double interval, wwl_abi_stats_v1 *out,
                         uint32_t out_bytes) {
    if (!out || out_bytes != sizeof *out || (n && !codes)) return WWL_ABI_INVALID;
    if (n > MS_MAX_SAMPLES || (uintmax_t)n > SIZE_MAX / sizeof(uint16_t)) return WWL_ABI_LIMIT;
    /* This temporary descriptor BORROWS caller storage; never call destroy. */
    ms_samples samples = {(uint16_t *)codes,(size_t)n,ms_default_allocator()};
    ms_stats stats;
    ms_status status = ms_statistics(&samples,(ms_calibration){scale,offset,interval},&stats);
    if (status != MS_OK) return status == MS_EMPTY ? WWL_ABI_EMPTY : WWL_ABI_INVALID;
    wwl_abi_stats_v1 result = {WWL_ABI_VERSION,n,stats.sum_mv,stats.mean_mv,
                              stats.variance_mv2,stats.rms2_mv2};
    *out = result; return WWL_ABI_OK;
}
uint32_t wwl_c_layout_v1(uint32_t *words, uint32_t n) {
    if (!words || n != WWL_ABI_LAYOUT_WORDS) return WWL_ABI_INVALID;
    const uint32_t layout[WWL_ABI_LAYOUT_WORDS] = {WWL_ABI_VERSION,CHAR_BIT,
        sizeof(uint16_t),sizeof(uint32_t),sizeof(double),sizeof(wwl_abi_stats_v1),
        alignof(wwl_abi_stats_v1),offsetof(wwl_abi_stats_v1,n),
        offsetof(wwl_abi_stats_v1,mean_mv),offsetof(wwl_abi_stats_v1,rms2_mv2)};
    for (uint32_t i = 0; i < WWL_ABI_LAYOUT_WORDS; ++i) words[i] = layout[i];
    return WWL_ABI_OK;
}
