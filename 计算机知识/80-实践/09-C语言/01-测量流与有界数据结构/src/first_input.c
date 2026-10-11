#include <stdio.h>
_Static_assert('0' == 48 && '\n' == 10, "requires ASCII-compatible execution characters");
/* Stage 0: at most four lines, one ASCII unsigned code 0..4095 per line.
 * No sign or surrounding whitespace. EOF can terminate the last line. */
static int code_line(unsigned long *out) {
    unsigned long value = 0; unsigned digits = 0; int c;
    while ((c = fgetc(stdin)) != EOF && c != '\n') {
        if (c < '0' || c > '9' || ++digits > 4) return -1;
        value = value * 10 + (unsigned)(c - '0');
        if (value > 4095) return -1;
    }
    if (ferror(stdin)) return -1;
    if (!digits) return c == EOF ? 0 : -1;
    *out = value; return 1;
}
int main(void) {
    unsigned long sum = 0, n = 0, value = 0;
    int result;
    while ((result = code_line(&value)) == 1) {
        if (n == 4) { fputs("error=limit\n",stderr); return 1; }
        sum += value; ++n;
    }
    if (result < 0 || n == 0) { fputs("error=invalid_or_empty\n",stderr); return 1; }
    if (printf("n=%lu\nmean_mv=%.17g\n", n, (double)sum/(double)n) < 0 || fflush(stdout) != 0)
        return 1;
    return fclose(stdout) == 0 ? 0 : 1;
}
