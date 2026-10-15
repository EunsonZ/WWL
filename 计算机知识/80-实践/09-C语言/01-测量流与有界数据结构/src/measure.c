#include "measure.h"
#include <limits.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#if CHAR_BIT != 8
#error "The teaching wire format requires CHAR_BIT == 8"
#endif
_Static_assert('0' == 48 && ' ' == 32 && '\n' == 10, "requires ASCII-compatible execution characters");
_Static_assert(UINT16_MAX == 65535, "requires uint16_t");
_Static_assert(UINT32_MAX == 4294967295U, "requires uint32_t");
static void *default_alloc(size_t n, void *ctx) { (void)ctx; return malloc(n); }
static void default_free(void *p, void *ctx) { (void)ctx; free(p); }
ms_allocator ms_default_allocator(void) {
    ms_allocator a = {default_alloc, default_free, NULL}; return a;
}
void ms_samples_init(ms_samples *s) {
    s->data = NULL; s->len = 0; s->allocator = ms_default_allocator();
}
void ms_samples_destroy(ms_samples *s) {
    if (s->data) s->allocator.release(s->data, s->allocator.context);
    ms_samples_init(s);
}
static int ready(ms_allocator a, const ms_samples *s) {
    return a.alloc && a.release && s && !s->data && s->len == 0;
}
static ms_status storage(uint32_t count, ms_allocator a, ms_samples *out) {
    if (count > MS_MAX_SAMPLES) return MS_LIMIT;
    if ((uintmax_t)count > (uintmax_t)SIZE_MAX / sizeof(uint16_t)) return MS_LIMIT;
    ms_samples tmp; ms_samples_init(&tmp); tmp.allocator = a;
    if (count) {
        tmp.data = a.alloc((size_t)count * sizeof(uint16_t), a.context);
        if (!tmp.data) return MS_NOMEM;
    }
    tmp.len = (size_t)count; *out = tmp; return MS_OK;
}
static uint32_t be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}
static uint16_t be16(const unsigned char *p) {
    return (uint16_t)(((uint32_t)p[0] << 8) | (uint32_t)p[1]);
}
ms_status ms_decode(const unsigned char *bytes, size_t size, int eof,
                    ms_allocator a, ms_samples *out) {
    if (!ready(a, out) || (!bytes && size)) return MS_INVALID;
    if (size < 4) return eof ? MS_TRUNCATED : MS_NEED_MORE;
    uint32_t count = be32(bytes);
    if (count > MS_MAX_SAMPLES || (uintmax_t)count > ((uintmax_t)SIZE_MAX - 4) / 2)
        return MS_LIMIT;
    size_t required = 4 + 2 * (size_t)count;
    if (size < required) return eof ? MS_TRUNCATED : MS_NEED_MORE;
    if (size != required) return MS_INVALID;
    /* Validate first: no allocation and no partial owner on malformed input. */
    for (size_t i = 0; i < (size_t)count; ++i)
        if (be16(bytes + 4 + 2 * i) > MS_MAX_CODE) return MS_INVALID;
    if (!eof) return MS_NEED_MORE;
    ms_samples tmp; ms_samples_init(&tmp);
    ms_status status = storage(count, a, &tmp);
    if (status != MS_OK) return status;
    for (size_t i = 0; i < tmp.len; ++i) tmp.data[i] = be16(bytes + 4 + 2 * i);
    *out = tmp; return MS_OK;
}
static int space(int c) { return c == ' ' || c == '\t' || c == '\n' ||
    c == '\r' || c == '\f' || c == '\v'; }
/* At most 10 decimal digits. LIMIT prevents overflow before multiplication. */
typedef struct { FILE *file; uint32_t bytes; int limit; } text_reader;
static int text_get(text_reader *r) {
    int c = fgetc(r->file);
    if (c != EOF && r->bytes == 16777216) { r->limit = 1; return EOF; }
    if (c != EOF) ++r->bytes;
    return c;
}
static ms_status token(text_reader *r, uint32_t *out, int *ended) {
    int c;
    do { c = text_get(r); } while (c != EOF && space(c));
    if (c == EOF) { *ended = 1; return r->limit ? MS_LIMIT : (ferror(r->file) ? MS_IO : MS_OK); }
    *ended = 0; uint32_t value = 0; size_t digits = 0;
    do {
        if (c < '0' || c > '9') return MS_INVALID;
        unsigned digit = (unsigned)(c - '0');
        if (++digits > 10 || value > (UINT32_MAX - digit) / 10) return MS_LIMIT;
        value = value * 10 + digit; c = text_get(r);
    } while (c != EOF && !space(c));
    if (r->limit) return MS_LIMIT;
    if (c == EOF && ferror(r->file)) return MS_IO;
    *out = value; return MS_OK;
}
ms_status ms_read_text(FILE *f, ms_allocator a, ms_samples *out) {
    if (!f || !ready(a, out)) return MS_INVALID;
    text_reader r = {f, 0, 0};
    uint32_t count = 0, value = 0; int ended = 0;
    ms_status status = token(&r, &count, &ended);
    if (status != MS_OK) return status;
    if (ended) return MS_TRUNCATED;
    ms_samples tmp; ms_samples_init(&tmp);
    status = storage(count, a, &tmp);
    if (status != MS_OK) return status;
    for (size_t i = 0; i < tmp.len; ++i) {
        status = token(&r, &value, &ended);
        if (status != MS_OK || ended || value > MS_MAX_CODE) {
            if (status == MS_OK) status = ended ? MS_TRUNCATED : MS_INVALID;
            ms_samples_destroy(&tmp); return status;
        }
        tmp.data[i] = (uint16_t)value;
    }
    /* After samples only whitespace is permitted: token EOF is success. */
    status = token(&r, &value, &ended);
    if (status != MS_OK || !ended) {
        ms_samples_destroy(&tmp); return status == MS_OK ? MS_INVALID : status;
    }
    *out = tmp; return MS_OK;
}
static ms_status read_exact(FILE *f, unsigned char *p, size_t n) {
    return fread(p, 1, n, f) == n ? MS_OK : (ferror(f) ? MS_IO : MS_TRUNCATED);
}
ms_status ms_read_binary(FILE *f, ms_allocator a, ms_samples *out) {
    if (!f || !ready(a, out)) return MS_INVALID;
    unsigned char bytes[4]; ms_status status = read_exact(f, bytes, 4);
    if (status != MS_OK) return status;
    uint32_t count = be32(bytes);
    if (count > MS_MAX_SAMPLES || (uintmax_t)count > ((uintmax_t)SIZE_MAX - 4) / 2)
        return MS_LIMIT;
    ms_samples tmp; ms_samples_init(&tmp); status = storage(count, a, &tmp);
    if (status != MS_OK) return status;
    for (size_t i = 0; i < tmp.len; ++i) {
        status = read_exact(f, bytes, 2);
        if (status != MS_OK || be16(bytes) > MS_MAX_CODE) {
            if (status == MS_OK) status = MS_INVALID;
            ms_samples_destroy(&tmp); return status;
        }
        tmp.data[i] = be16(bytes);
    }
    int extra = fgetc(f);
    if (extra != EOF || ferror(f)) {
        ms_samples_destroy(&tmp); return ferror(f) ? MS_IO : MS_INVALID;
    }
    *out = tmp; return MS_OK;
}
static int calibration_valid(ms_calibration c) {
    return isfinite(c.scale_mv) && c.scale_mv > 0 && c.scale_mv <= 1e6 &&
           isfinite(c.offset_mv) && fabs(c.offset_mv) <= 1e9 &&
           isfinite(c.interval_s) && c.interval_s > 0 && c.interval_s <= 1e6;
}
ms_status ms_statistics(const ms_samples *s, ms_calibration c, ms_stats *out) {
    if (!s || !out || !calibration_valid(c) || (s->len && !s->data)) return MS_INVALID;
    if (s->len > MS_MAX_SAMPLES) return MS_LIMIT;
    if (!s->len) return MS_EMPTY;
    uint64_t sum = 0, squares = 0;
    for (size_t i = 0; i < s->len; ++i) {
        uint64_t x = s->data[i]; if (x > MS_MAX_CODE) return MS_INVALID;
        sum += x; squares += x * x;
    }
    uint64_t n = (uint64_t)s->len;
    /* n*squares <= 4095^2*10^12 < UINT64_MAX; sum^2 has the same bound. */
    double mean_code = (double)sum / (double)n;
    double variance_code = (double)(n * squares - sum * sum) /
                           ((double)n * (double)n);
    ms_stats result = {s->len, c.scale_mv * (double)sum + c.offset_mv * (double)n,
        c.scale_mv * mean_code + c.offset_mv,
        c.scale_mv * c.scale_mv * variance_code, 0};
    result.rms2_mv2 = result.mean_mv * result.mean_mv + result.variance_mv2;
    *out = result; return MS_OK;
}
ms_status ms_ring_init(ms_ring *r, uint16_t *slots, size_t capacity) {
    if (!r || !slots || !capacity) return MS_INVALID;
    *r = (ms_ring){slots, capacity, 0, 0}; return MS_OK;
}
static size_t next_index(size_t i, size_t capacity) { return i == capacity - 1 ? 0 : i + 1; }
static int ring_valid(const ms_ring *r) {
    return r && r->slots && r->capacity && r->head < r->capacity && r->len <= r->capacity;
}
ms_status ms_ring_push(ms_ring *r, uint16_t value) {
    if (!ring_valid(r) || value > MS_MAX_CODE) return MS_INVALID;
    if (r->len == r->capacity) {
        r->slots[r->head] = value; r->head = next_index(r->head, r->capacity);
    } else {
        /* Equivalent to (head+len)%capacity without overflowing head+len. */
        size_t remaining = r->capacity - r->head;
        size_t at = r->len >= remaining ? r->len - remaining : r->head + r->len;
        r->slots[at] = value; ++r->len;
    }
    return MS_OK;
}
ms_status ms_ring_get(const ms_ring *r, size_t index, uint16_t *out) {
    if (!ring_valid(r) || !out || index >= r->len) return MS_INVALID;
    size_t remaining = r->capacity - r->head;
    size_t at = index >= remaining ? index - remaining : r->head + index;
    *out = r->slots[at]; return MS_OK;
}
ms_status ms_fir_init(ms_fir *f) {
    if (!f) return MS_INVALID;
    ms_status status = ms_ring_init(&f->ring, f->slots, 2);
    if (status == MS_OK) status = ms_ring_push(&f->ring, 0);
    return status;
}
ms_status ms_fir_next(ms_fir *f, uint16_t code, ms_calibration c, double *out) {
    if (!f || !out || !calibration_valid(c) || code > MS_MAX_CODE ||
        !ring_valid(&f->ring) || f->ring.capacity != 2 || !f->ring.len) return MS_INVALID;
    uint16_t previous = 0;
    ms_status status = ms_ring_get(&f->ring, f->ring.len - 1, &previous);
    if (status != MS_OK) return status;
    uint32_t pair = (uint32_t)previous + (uint32_t)code; /* <=8190 */
    /* Initial previous physical measurement is 0, not offset_mv. */
    double value = f->ring.len == 1 ? (c.scale_mv * code + c.offset_mv) * 0.5 :
                   c.scale_mv * ((double)pair * 0.5) + c.offset_mv;
    status = ms_ring_push(&f->ring, code);
    if (status == MS_OK) *out = value;
    return status;
}
const char *ms_status_name(ms_status s) {
    static const char *const names[] = {"ok","need_more","invalid","limit",
        "truncated","nomem","io","empty"};
    return (unsigned)s < sizeof names / sizeof names[0] ? names[s] : "unknown";
}
static ms_status line(ms_write_fn write, void *ctx, const char *label, double value) {
    char buffer[128]; int n = snprintf(buffer, sizeof buffer, "%s=%.17g\n", label, value);
    if (n < 0 || (size_t)n >= sizeof buffer) return MS_IO;
    return write(buffer, (size_t)n, ctx) ? MS_OK : MS_IO;
}
ms_status ms_report(const ms_samples *s, ms_calibration c, ms_write_fn write, void *ctx) {
    if (!write) return MS_INVALID;
    ms_stats stats; ms_status status = ms_statistics(s, c, &stats);
    if (status != MS_OK) return status;
    char buffer[128]; int n = snprintf(buffer, sizeof buffer, "n=%zu\n", stats.n);
    if (n < 0 || (size_t)n >= sizeof buffer || !write(buffer,(size_t)n,ctx)) return MS_IO;
    if ((status = line(write, ctx, "interval_s", c.interval_s)) != MS_OK ||
        (status = line(write, ctx, "sum_mv", stats.sum_mv)) != MS_OK ||
        (status = line(write, ctx, "mean_mv", stats.mean_mv)) != MS_OK ||
        (status = line(write, ctx, "descriptive_variance_mv2", stats.variance_mv2)) != MS_OK ||
        (status = line(write, ctx, "rms2_mv2", stats.rms2_mv2)) != MS_OK) return status;
    ms_fir f; status = ms_fir_init(&f); if (status != MS_OK) return status;
    for (size_t i = 0; i < s->len; ++i) {
        double value; status = ms_fir_next(&f, s->data[i], c, &value);
        if (status != MS_OK) return status;
        n = snprintf(buffer, sizeof buffer, "fir_mv[%zu]=%.17g\n", i, value);
        if (n < 0 || (size_t)n >= sizeof buffer || !write(buffer,(size_t)n,ctx)) return MS_IO;
    }
    return MS_OK;
}
