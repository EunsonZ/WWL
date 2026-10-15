#include "wordfreq.h"
static int output(const char *p, size_t n, void *ctx) { return fwrite(p,1,n,ctx) == n; }
int main(int argc, char **argv) {
    if (argc != 2) { fputs("usage: wordfreq FILE\n",stderr); return 2; }
    FILE *f = fopen(argv[1],"rb");
    if (!f) { fputs("error=io\n",stderr); return 1; }
    wf_table t; wf_init(&t, ms_default_allocator()); ms_status status = wf_read(f,&t);
    if (fclose(f) != 0 && status == MS_OK) status = MS_IO;
    if (status == MS_OK) status = wf_report(&t,output,stdout);
    if (fflush(stdout) != 0 && status == MS_OK) status = MS_IO;
    if (fclose(stdout) != 0 && status == MS_OK) status = MS_IO;
    wf_destroy(&t);
    if (status != MS_OK) { fprintf(stderr,"error=%s\n",ms_status_name(status)); return 1; }
    return 0;
}
