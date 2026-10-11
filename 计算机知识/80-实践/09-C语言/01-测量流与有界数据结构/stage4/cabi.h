#ifndef WWL_CABI_V1_H
#define WWL_CABI_V1_H
#include <stdint.h>
#define WWL_ABI_OK UINT32_C(0)
#define WWL_ABI_INVALID UINT32_C(1)
#define WWL_ABI_LIMIT UINT32_C(2)
#define WWL_ABI_EMPTY UINT32_C(3)
#define WWL_ABI_VERSION UINT32_C(1)
#define WWL_ABI_LAYOUT_WORDS UINT32_C(10)
#ifdef __cplusplus
extern "C" {
#endif
/* Native ABI result, not a packed wire format. Caller owns out and codes.
 * No allocation, ownership transfer, callback, retained pointer or exception.
 * For an admissible n, codes[n] must be valid/aligned/readable. An over-limit n
 * is rejected before reading codes. out must denote one valid result
 * object; out_bytes must match sizeof(wwl_abi_stats_v1), and objects do not overlap.
 * Failure leaves out unchanged. All fields have the named physical units. */
typedef struct {
    uint32_t abi_version, n;
    double sum_mv, mean_mv, descriptive_variance_mv2, rms2_mv2;
} wwl_abi_stats_v1;
uint32_t wwl_c_measure_v1(const uint16_t *codes, uint32_t n, double scale_mv,
                         double offset_mv, double interval_s,
                         wwl_abi_stats_v1 *out, uint32_t out_bytes);
/* Native host layout: version, CHAR_BIT, sizeof(uint16_t), sizeof(uint32_t),
 * sizeof(double), sizeof(result), alignof(result), offsetof(n), offsetof(mean),
 * offsetof(rms2). Caller supplies exactly ten writable uint32_t values. */
uint32_t wwl_c_layout_v1(uint32_t *words, uint32_t n);
#ifdef __cplusplus
}
#endif
#endif
