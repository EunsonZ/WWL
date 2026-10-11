#include "measure.h"
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
static int number(const char *text, double *out) {
    if (!*text) return 0;
    char *end; errno = 0; double x = strtod(text, &end);
    if (*end || errno == ERANGE || !isfinite(x)) return 0;
    *out = x; return 1;
}
static int write_stdout(const char *p, size_t n, void *ctx) {
    return fwrite(p, 1, n, ctx) == n;
}
int main(int argc, char **argv) {
    if ((argc != 3 && argc != 6) || (strcmp(argv[1], "text") && strcmp(argv[1], "binary"))) {
        fputs("usage: measure text|binary FILE [SCALE_MV OFFSET_MV INTERVAL_S]\n", stderr); return 2;
    }
    ms_calibration c = {1, 0, 1};
    if (argc == 6 && (!number(argv[3], &c.scale_mv) || !number(argv[4], &c.offset_mv) ||
                      !number(argv[5], &c.interval_s))) {
        fputs("error=invalid\n",stderr); return 1;
    }
    FILE *input = fopen(argv[2], "rb");
    if (!input) { fputs("error=io\n",stderr); return 1; }
    ms_samples s; ms_samples_init(&s);
    ms_status status = strcmp(argv[1], "text") ?
        ms_read_binary(input, ms_default_allocator(), &s) :
        ms_read_text(input, ms_default_allocator(), &s);
    if (fclose(input) != 0 && status == MS_OK) status = MS_IO;
    if (status == MS_OK) status = ms_report(&s, c, write_stdout, stdout);
    if (fflush(stdout) != 0 && status == MS_OK) status = MS_IO;
    if (fclose(stdout) != 0 && status == MS_OK) status = MS_IO;
    ms_samples_destroy(&s);
    if (status != MS_OK) { fprintf(stderr,"error=%s\n",ms_status_name(status)); return 1; }
    return 0;
}
