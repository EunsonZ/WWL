#ifndef MEASURE_H
#define MEASURE_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
/* C17 hosted; requires 8-bit bytes, exact-width integers and ASCII-compatible
 * execution characters. Parser FILE inputs must be opened in binary mode. */
#define MS_MAX_SAMPLES UINT32_C(1000000)
#define MS_MAX_CODE UINT16_C(4095)
typedef enum { MS_OK, MS_NEED_MORE, MS_INVALID, MS_LIMIT, MS_TRUNCATED,
               MS_NOMEM, MS_IO, MS_EMPTY } ms_status;
typedef void *(*ms_alloc_fn)(size_t, void *);
typedef void (*ms_free_fn)(void *, void *);
typedef struct { ms_alloc_fn alloc; ms_free_fn release; void *context; } ms_allocator;
/* Owner: initialized empty, no shallow copies. On parser failure it is unchanged. */
typedef struct { uint16_t *data; size_t len; ms_allocator allocator; } ms_samples;
ms_allocator ms_default_allocator(void);
void ms_samples_init(ms_samples *s);
void ms_samples_destroy(ms_samples *s);
/* out must be initialized and empty. bytes must denote size readable bytes.
 * eof=0 keeps NEED_MORE even for a complete valid prefix; eof=1 turns
 * missing bytes into TRUNCATED and permits success on one complete frame.
 * One frame only: extra bytes are INVALID, even if they might be another frame. */
ms_status ms_decode(const unsigned char *bytes, size_t size, int eof,
                    ms_allocator allocator, ms_samples *out);
/* count and count codes, unsigned decimal tokens, ASCII whitespace only. */
ms_status ms_read_text(FILE *input, ms_allocator allocator, ms_samples *out);
ms_status ms_read_binary(FILE *input, ms_allocator allocator, ms_samples *out);
typedef struct { double scale_mv, offset_mv, interval_s; } ms_calibration;
typedef struct { size_t n; double sum_mv, mean_mv, variance_mv2, rms2_mv2; } ms_stats;
ms_status ms_statistics(const ms_samples *s, ms_calibration c, ms_stats *out);
/* Caller owns slots[capacity]; ring borrows it until the caller ends that lifetime. */
typedef struct { uint16_t *slots; size_t capacity, head, len; } ms_ring;
ms_status ms_ring_init(ms_ring *r, uint16_t *slots, size_t capacity);
ms_status ms_ring_push(ms_ring *r, uint16_t value);
ms_status ms_ring_get(const ms_ring *r, size_t index, uint16_t *out);
typedef struct { uint16_t slots[2]; ms_ring ring; } ms_fir;
/* ms_fir cannot be copied by value because ring.slots borrows its own array. */
ms_status ms_fir_init(ms_fir *f);
ms_status ms_fir_next(ms_fir *f, uint16_t code, ms_calibration c, double *out_mv);
typedef int (*ms_write_fn)(const char *, size_t, void *);
/* Callback returns nonzero only after accepting every byte; cannot roll back an
 * earlier successful write. Caller supplies fresh FIR state for each record. */
ms_status ms_report(const ms_samples *s, ms_calibration c, ms_write_fn write,
                    void *context);
const char *ms_status_name(ms_status status);
#endif
