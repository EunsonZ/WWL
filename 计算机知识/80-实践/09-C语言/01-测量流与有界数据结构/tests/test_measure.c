#include "measure.h"
#include "wordfreq.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef struct { size_t calls, fail, live; } allocation_log;
static void *test_alloc(size_t n, void *ctx) {
    allocation_log *log = ctx; ++log->calls;
    if (log->fail && log->calls == log->fail) return NULL;
    void *p = malloc(n); if (p) ++log->live; return p;
}
static void test_free(void *p, void *ctx) {
    allocation_log *log = ctx;
    if (p) { assert(log->live); --log->live; free(p); }
}
static ms_allocator allocator(allocation_log *log) {
    return (ms_allocator){test_alloc,test_free,log};
}
static FILE *input(const unsigned char *bytes, size_t n) {
    FILE *f = tmpfile(); assert(f);
    assert(fwrite(bytes,1,n,f) == n); assert(fflush(f) == 0); rewind(f); return f;
}
static ms_status text(const char *data, ms_samples *s, ms_allocator a) {
    FILE *f = input((const unsigned char *)data,strlen(data));
    ms_status status = ms_read_text(f,a,s); assert(fclose(f) == 0); return status;
}
static int fail_write(const char *p, size_t n, void *ctx) {
    (void)p; (void)n; size_t *left = ctx;
    if (!*left) return 0;
    --*left; return 1;
}
static void near(double a, double b) { assert(fabs(a-b) <= 1e-10 * fmax(1,fabs(b))); }
static const unsigned char frame[] = {0,0,0,4,0,2,0,4,0,6,0,8};
static void parsers(void) {
    allocation_log log = {0}; ms_allocator a = allocator(&log);
    ms_samples s; ms_samples_init(&s);
    for (size_t n = 0; n < sizeof frame; ++n) {
        assert(ms_decode(frame,n,0,a,&s) == MS_NEED_MORE);
        assert(ms_decode(frame,n,1,a,&s) == MS_TRUNCATED);
        assert(!s.data && !s.len && !log.live);
        FILE *f = input(frame,n);
        assert(ms_read_binary(f,a,&s) == MS_TRUNCATED); assert(fclose(f) == 0);
        assert(!s.data && !s.len && !log.live);
    }
    assert(ms_decode(frame,sizeof frame,0,a,&s) == MS_NEED_MORE);
    /* Start at an odd byte offset, no typed integer pointer casts. */
    unsigned char offset[sizeof frame+1]; memcpy(offset+1,frame,sizeof frame);
    assert(ms_decode(offset+1,sizeof frame,1,a,&s) == MS_OK);
    assert(s.len == 4 && s.data[0] == 2 && s.data[3] == 8);
    uint16_t *saved = s.data;
    assert(ms_decode(frame,sizeof frame,1,a,&s) == MS_INVALID && s.data == saved);
    ms_samples_destroy(&s); assert(!log.live);
    log.fail = log.calls + 1;
    assert(ms_decode(frame,sizeof frame,1,a,&s) == MS_NOMEM);
    assert(!s.data && !s.len && !log.live); log.fail = 0;
    unsigned char bad[sizeof frame+1]; memcpy(bad,frame,sizeof frame); bad[sizeof frame] = 0;
    assert(ms_decode(bad,sizeof bad,1,a,&s) == MS_INVALID);
    bad[4] = 16; assert(ms_decode(bad,sizeof frame,1,a,&s) == MS_INVALID);
    unsigned char huge[] = {0,15,66,65}; /* 1000001 */
    assert(ms_decode(huge,sizeof huge,1,a,&s) == MS_LIMIT);
    const char *bad_text[] = {"", "4 2 4 6", "1 -1", "1 4096", "1 2 extra", "1 2 3", "1 2x", "1 +2"};
    const ms_status expected[] = {MS_TRUNCATED,MS_TRUNCATED,MS_INVALID,MS_INVALID,
        MS_INVALID,MS_INVALID,MS_INVALID,MS_INVALID};
    for (size_t i = 0; i < sizeof expected/sizeof *expected; ++i) {
        assert(text(bad_text[i],&s,a) == expected[i]); assert(!s.data && !s.len && !log.live);
    }
    assert(text("1000001",&s,a) == MS_LIMIT);
    assert(text("4294967296",&s,a) == MS_LIMIT);
    assert(text("1 00000000001",&s,a) == MS_LIMIT);
    const unsigned char nul[] = {'1',' ','2',0}; FILE *f = input(nul,sizeof nul);
    assert(ms_read_text(f,a,&s) == MS_INVALID); assert(fclose(f) == 0); assert(!log.live);
    log.fail = log.calls+1;
    assert(text("4 2 4 6 8",&s,a) == MS_NOMEM); assert(!log.live && !s.data); log.fail = 0;
    assert(text("0",&s,a) == MS_OK && !s.data && !s.len);
    ms_stats stats = {0}; assert(ms_statistics(&s,(ms_calibration){1,0,1},&stats) == MS_EMPTY);
    assert(text("4\n2 4 6 8\n",&s,a) == MS_OK);
    assert(ms_statistics(&s,(ms_calibration){1,0,1},&stats) == MS_OK);
    near(stats.sum_mv,20); near(stats.mean_mv,5); near(stats.variance_mv2,5); near(stats.rms2_mv2,30);
    ms_stats old = stats;
    const ms_calibration bad_c[] = {{0,0,1},{-1,0,1},{INFINITY,0,1},{NAN,0,1},
        {1,1e9+1,1},{1,0,0},{1,0,INFINITY},{1e6+1,0,1},{1,0,1e6+1}};
    for (size_t i = 0; i < sizeof bad_c/sizeof *bad_c; ++i) {
        assert(ms_statistics(&s,bad_c[i],&stats) == MS_INVALID);
        assert(stats.n == old.n && stats.mean_mv == old.mean_mv);
    }
    assert(ms_statistics(&s,(ms_calibration){2,-3,0.5},&stats) == MS_OK);
    near(stats.sum_mv,28); near(stats.mean_mv,7); near(stats.variance_mv2,20); near(stats.rms2_mv2,69);
    for (size_t n = 0; n < 10; ++n) {
        size_t left = n; assert(ms_report(&s,(ms_calibration){1,0,1},fail_write,&left) == MS_IO);
        assert(s.data && s.len == 4 && log.live == 1);
    }
    ms_samples_destroy(&s); assert(!log.live);
    /* Reach the exact permitted integer bound without huge source fixtures. */
    uint16_t *large = malloc((size_t)MS_MAX_SAMPLES * sizeof *large); assert(large);
    for (size_t i = 0; i < MS_MAX_SAMPLES; ++i) large[i] = MS_MAX_CODE;
    ms_samples maximum = {large,MS_MAX_SAMPLES,ms_default_allocator()};
    assert(ms_statistics(&maximum,(ms_calibration){1,0,1},&stats) == MS_OK);
    near(stats.sum_mv,4095000000.0); near(stats.variance_mv2,0); near(stats.rms2_mv2,16769025);
    ms_samples_destroy(&maximum);
}
static void rings(void) {
    uint16_t slots[3]; ms_ring r;
    assert(ms_ring_init(&r,slots,0) == MS_INVALID);
    assert(ms_ring_init(&r,slots,3) == MS_OK); uint16_t value;
    assert(ms_ring_get(&r,0,&value) == MS_INVALID);
    for (uint16_t i = 1; i <= 8; ++i) {
        assert(ms_ring_push(&r,i) == MS_OK);
        assert(r.len == (i < 3 ? i : 3));
        for (size_t k = 0; k < r.len; ++k) {
            assert(ms_ring_get(&r,k,&value) == MS_OK);
            assert(value == (uint16_t)(i-r.len+1+k));
        }
    }
    size_t head = r.head;
    assert(ms_ring_push(&r,4096) == MS_INVALID && r.head == head);
    ms_fir f; assert(ms_fir_init(&f) == MS_OK);
    const uint16_t codes[] = {2,4,6,8}; const double expected[] = {1,3,5,7};
    /* Every partition of four points: boundaries do not initialize the ring. */
    for (unsigned mask = 0; mask < 8; ++mask) {
        assert(ms_fir_init(&f) == MS_OK);
        for (size_t i = 0; i < 4; ++i) {
            double y; assert(ms_fir_next(&f,codes[i],(ms_calibration){1,0,1},&y) == MS_OK);
            near(y,expected[i]);
            if (i < 3 && (mask & (1U << i))) assert(f.ring.len == 2);
        }
        assert(f.ring.len == 2);
    }
    head = f.ring.head; double y = 99;
    assert(ms_fir_next(&f,4096,(ms_calibration){1,0,1},&y) == MS_INVALID);
    assert(y == 99 && f.ring.head == head);
    assert(ms_fir_init(&f) == MS_OK);
    assert(ms_fir_next(&f,1,(ms_calibration){1,0,1},&y) == MS_OK); near(y,0.5);
    assert(ms_fir_init(&f) == MS_OK);
    assert(ms_fir_next(&f,2,(ms_calibration){2,-3,1},&y) == MS_OK); near(y,0.5);
    assert(ms_fir_next(&f,4,(ms_calibration){2,-3,1},&y) == MS_OK); near(y,3);
}
static void words(void) {
    const char *words = "Red blue RED. blue green red";
    allocation_log log = {0}; wf_table table; wf_init(&table,allocator(&log));
    for (size_t fail = 1; fail <= 3; ++fail) {
        log.calls = 0; log.fail = fail;
        FILE *f = input((const unsigned char *)words,strlen(words));
        assert(wf_read(f,&table) == MS_NOMEM); assert(fclose(f) == 0);
        assert(table.used == 0 && log.live == 0);
    }
    log.fail = 0; log.calls = 0;
    FILE *f = input((const unsigned char *)words,strlen(words));
    assert(wf_read(f,&table) == MS_OK && table.used == 3 && log.live == 3); assert(fclose(f) == 0);
    for (size_t count = 0; count < 3; ++count) {
        size_t left = count; assert(wf_report(&table,fail_write,&left) == MS_IO);
        assert(table.used == 3 && log.live == 3);
    }
    wf_destroy(&table); assert(!log.live);
    const unsigned char non_ascii[] = {'a',' ',0xc3,0xa9}; f = input(non_ascii,sizeof non_ascii);
    assert(wf_read(f,&table) == MS_INVALID); assert(fclose(f) == 0); assert(!log.live && !table.used);
    f = input((const unsigned char *)"",0); assert(wf_read(f,&table) == MS_OK); assert(fclose(f) == 0);
    wf_destroy(&table); assert(!log.live);
}
int main(void) { parsers(); rings(); words(); puts("C contract tests: PASS"); return 0; }
