#ifndef WWL_MEASUREMENT_ABI_H
#define WWL_MEASUREMENT_ABI_H
#include <stddef.h>
#include <stdint.h>
#if defined(_WIN32)
# if defined(WWL_ABI_BUILD)
#  define WWL_ABI_API __declspec(dllexport)
# else
#  define WWL_ABI_API __declspec(dllimport)
# endif
#else
# define WWL_ABI_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
#define WWL_ABI_VERSION_V1 UINT32_C(1)
#define WWL_ABI_MAX_INPUT_BYTES_V1 ((size_t)8192)
typedef uint32_t wwl_status;
#define WWL_OK UINT32_C(0)
#define WWL_INVALID_ARGUMENT UINT32_C(1)
#define WWL_VERSION_MISMATCH UINT32_C(2)
#define WWL_SIZE_MISMATCH UINT32_C(3)
#define WWL_BUFFER_TOO_SMALL UINT32_C(4)
#define WWL_OUT_OF_MEMORY UINT32_C(5)
#define WWL_LIMIT_EXCEEDED UINT32_C(6)
#define WWL_NOT_READY UINT32_C(7)
#define WWL_INTERNAL_ERROR UINT32_C(8)
typedef struct wwl_report_handle wwl_report_handle;
typedef struct wwl_report_settings_v1 {
    int32_t gain_uV_per_code; /* 1..1000 */
    int32_t offset_uV;       /* -1000000..1000000 */
    uint32_t interval_ms;    /* 1..86400000; relative sample times */
    uint32_t width;          /* 1..4096; only complete windows */
    uint32_t hop;            /* 1..4096 */
    uint32_t label_bytes;    /* 1..40, no terminating NUL included */
    char label[40];          /* ASCII letters, digits, '_' or '-' */
} wwl_report_settings_v1;
/* Diagnostic comparison with the caller's sizeof/_Alignof/offsetof.
   Native process ABI only; neither this nor settings is a wire format. */
typedef struct wwl_report_layout_v1 {
    uint32_t settings_size, settings_alignment;
    uint32_t gain_offset, offset_offset, interval_offset;
    uint32_t width_offset, hop_offset, label_bytes_offset, label_offset;
} wwl_report_layout_v1;
/* All pointers must designate valid live objects/buffers of the stated extent.
   Null is accepted only as documented. No overlapping input/output parameters.
   Calls on one handle are externally serialized, including destruction; the
   shared library stays loaded until all calls and handles have ended.
   The library uses its stable new/delete PMR resource, independently of any
   temporary process default PMR resource installed by a C++ host.
   Status codes contain no owning allocation. No exception crosses these calls. */
WWL_ABI_API wwl_status wwl_report_create_v1(uint32_t version, wwl_report_handle** out);
/* create requires out != NULL and *out == NULL; failure leaves *out unchanged.
   destroy(&h) deletes in the library and sets h=NULL; h==NULL is a successful
   no-op. destroy(NULL) is invalid. Copied aliases become invalid after destroy. */
WWL_ABI_API wwl_status wwl_report_destroy_v1(wwl_report_handle** handle);
/* version is checked first, then exact settings_size, before reading settings.
   Incompatible extensions require a new version/symbol, not ignored tail data.
   codes is a non-NUL-terminated byte span parsed by the existing ReportSession.
   codes==NULL is legal only with codes_bytes==0 (an empty batch).
   All input borrows end on return. Failure preserves the old report. */
WWL_ABI_API wwl_status wwl_report_replace_v1(
    wwl_report_handle* handle, uint32_t version, size_t settings_size,
    const wwl_report_settings_v1* settings, const char* codes, size_t codes_bytes);
/* required is mandatory. On NOT_READY it is zero; on OK/BUFFER_TOO_SMALL it
   includes the terminating NUL. Other failures leave it unchanged.
   output==NULL/capacity==0 queries size, returning BUFFER_TOO_SMALL for a report.
   output==NULL/capacity>0 is invalid. Short buffers are entirely untouched.
   Exact/large buffers receive text+NUL; bytes after that are untouched.
   The caller allocates/frees output. It survives replace and handle destruction. */
WWL_ABI_API wwl_status wwl_report_copy_text_v1(
    const wwl_report_handle* handle, char* output, size_t capacity, size_t* required);
/* version and exact layout_size are checked before any output access. */
WWL_ABI_API wwl_status wwl_report_get_layout_v1(
    uint32_t version, size_t layout_size, wwl_report_layout_v1* output);
#ifdef __cplusplus
}
#endif
#endif
