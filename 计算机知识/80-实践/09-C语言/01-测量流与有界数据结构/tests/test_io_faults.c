/* macOS/BSD hosted experiment; funopen is not ISO C17. Production sources
 * are unchanged. The included CLI redirects only its stream factories/owners. */
#include "measure.h"
#include "wordfreq.h"
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#if !defined(__APPLE__)
int main(void) { puts("stdio_faults=UNSUPPORTED_HOST_FUNOPEN"); return 77; }
#else
typedef struct {
    const unsigned char *data; size_t n, pos, fail_at;
    int read_failed, close_fail, closes, write_fail, writes;
    unsigned char written[1024]; size_t used;
} stream;
static int cookie_read(void *ctx, char *dst, int capacity) {
    stream *s=ctx;
    if (s->pos == s->fail_at) { s->read_failed=1; errno=EIO; return -1; }
    size_t available=s->n-s->pos;
    if (s->fail_at < s->n && available > s->fail_at-s->pos) available=s->fail_at-s->pos;
    size_t take=(size_t)capacity < available ? (size_t)capacity : available;
    memcpy(dst,s->data+s->pos,take); s->pos+=take; return (int)take;
}
static int cookie_write(void *ctx, const char *src, int n) {
    stream *s=ctx; ++s->writes;
    if (s->write_fail && s->writes >= s->write_fail) { errno=EIO; return -1; }
    assert((size_t)n <= sizeof s->written-s->used);
    memcpy(s->written+s->used,src,(size_t)n); s->used+=(size_t)n; return n;
}
static int cookie_close(void *ctx) {
    stream *s=ctx; ++s->closes;
    if (s->close_fail) { errno=EIO; return -1; } return 0;
}
static FILE *reader(stream *s) {
    FILE *f=funopen(s,cookie_read,NULL,NULL,cookie_close); assert(f); return f;
}
typedef struct { size_t allocs, frees, live; } ledger;
static ledger memory;
static void *allocate(size_t n, void *ctx) {
    ledger *m=ctx; void *p=malloc(n); assert(p); ++m->allocs; ++m->live; return p;
}
static void release(void *p, void *ctx) {
    ledger *m=ctx; assert(p && m->live); ++m->frees; --m->live; free(p);
}
static ms_allocator monitored(void) { return (ms_allocator){allocate,release,&memory}; }
static FILE *cli_output, *cli_error;
static stream cli_input;
static FILE *open_input(const char *path, const char *mode) {
    assert(!strcmp(path,"fixture") && !strcmp(mode,"rb")); return reader(&cli_input);
}
#undef stdout
#undef stderr
#define stdout cli_output
#define stderr cli_error
#define fopen open_input
#define ms_default_allocator monitored
#define main included_measure_main
#include "../src/main.c"
#undef main
#undef ms_default_allocator
#undef fopen
#undef stderr
#undef stdout
static const unsigned char text[]="4 2 4 6 8";
static const unsigned char binary[]={0,0,0,4,0,2,0,4,0,6,0,8};
static stream input_case(const unsigned char *data, size_t n, size_t failure) {
    stream s={0}; s.data=data; s.n=n; s.fail_at=failure; return s;
}
static void parser_faults(void) {
    /* Before header/count, after allocation, and after complete valid record
     * while confirming EOF. These must be IO, never normal EOF/TRUNCATED. */
    const size_t text_at[]={0,4,sizeof text-1};
    const size_t binary_at[]={0,5,sizeof binary};
    for (unsigned kind=0;kind<2;++kind) for (unsigned k=0;k<3;++k) {
        stream s=kind ? input_case(binary,sizeof binary,binary_at[k]) :
                        input_case(text,sizeof text-1,text_at[k]);
        FILE *f=reader(&s); ms_samples out; ms_samples_init(&out);
        size_t prior=memory.allocs;
        ms_status status=kind ? ms_read_binary(f,monitored(),&out) : ms_read_text(f,monitored(),&out);
        assert(status==MS_IO && ferror(f) && s.read_failed);
        assert(!out.data && !out.len && !memory.live);
        if (k) assert(memory.allocs > prior);
        assert(fclose(f)==0 && s.closes==1);
        ms_samples_destroy(&out);
    }
    const unsigned char words[]="red blue ";
    stream s=input_case(words,sizeof words-1,sizeof words-1); FILE *f=reader(&s);
    wf_table table; wf_init(&table,monitored()); size_t prior=memory.allocs;
    assert(wf_read(f,&table)==MS_IO && ferror(f));
    assert(memory.allocs > prior && !memory.live && !table.used);
    assert(fclose(f)==0 && s.closes==1); wf_destroy(&table);
    puts("read_faults=PASS text/binary/header/partial/EOF,wordfreq,empty_owner,live_zero");
}
static void cli_case(const char *label, const unsigned char *data, size_t n,
                     size_t read_failure, int input_close_failure,
                     int write_failure, int output_close_failure,
                     int unbuffered, const char *error, int output_kind) {
    /* output_kind: 0 empty, 1 complete, 2 nonempty strict prefix. */
    const char *expected="n=4\ninterval_s=1\nsum_mv=20\nmean_mv=5\ndescriptive_variance_mv2=5\nrms2_mv2=30\nfir_mv[0]=1\nfir_mv[1]=3\nfir_mv[2]=5\nfir_mv[3]=7\n";
    cli_input=input_case(data,n,read_failure); cli_input.close_fail=input_close_failure;
    stream output={0}; output.write_fail=write_failure; output.close_fail=output_close_failure;
    cli_output=funopen(&output,NULL,cookie_write,NULL,cookie_close); assert(cli_output);
    char buffer[512]; assert(setvbuf(cli_output,unbuffered ? NULL : buffer,
                                   unbuffered ? _IONBF : _IOFBF,sizeof buffer)==0);
    cli_error=tmpfile(); assert(cli_error);
    char *args[]={"measure","text","fixture",NULL}; size_t before=memory.allocs;
    int result=included_measure_main(3,args);
    assert(result==1 && cli_input.closes==1 && output.closes==1 && !memory.live);
    if (output_kind==0) assert(!output.used);
    else if (output_kind==1) assert(output.used==strlen(expected) && !memcmp(output.written,expected,output.used));
    else assert(output.used && output.used<strlen(expected) && !memcmp(output.written,expected,output.used));
    rewind(cli_error); char diagnostic[128]={0}; size_t got=fread(diagnostic,1,sizeof diagnostic-1,cli_error);
    assert(got==strlen(error) && !strcmp(diagnostic,error)); assert(fclose(cli_error)==0);
    assert(memory.allocs > before);
    printf("cli_fault=%s PASS exit=1 diagnostic=%s allocations_released=%zu output_bytes=%zu input_closed=1 output_closed=1\n",
           label,ms_status_name(!strcmp(error,"error=invalid\n") ? MS_INVALID : MS_IO),memory.allocs-before,output.used);
}
int main(void) {
    parser_faults();
    cli_case("read",text,sizeof text-1,4,0,0,0,0,"error=io\n",0);
    cli_case("input_close",text,sizeof text-1,SIZE_MAX,1,0,0,0,"error=io\n",0);
    const unsigned char bad[]="1 4096";
    cli_case("parse_then_close",bad,sizeof bad-1,SIZE_MAX,1,0,0,0,"error=invalid\n",0);
    cli_case("output_write",text,sizeof text-1,SIZE_MAX,0,2,0,1,"error=io\n",2);
    cli_case("output_flush",text,sizeof text-1,SIZE_MAX,0,1,0,0,"error=io\n",0);
    cli_case("output_close_only",text,sizeof text-1,SIZE_MAX,0,0,1,0,"error=io\n",1);
    assert(memory.allocs==memory.frees && !memory.live);
    puts("stdio_faults=PASS controlled_FILE,real_parser_and_CLI,cleanup,error_precedence"); return 0;
}
#endif
