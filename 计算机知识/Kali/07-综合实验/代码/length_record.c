/* Original bounded stdin parser for a synthetic format; no networking or file writes.
 * Format: 'L', one unsigned length byte (0..32), exactly length payload bytes.
 * Success: decimal byte sum + newline, status 0. Invalid format: stderr, status 2.
 * I/O failure: stderr, status 3. A legal empty payload is NOT an empty file.
 */
#include <stdio.h>
#include <stddef.h>

int main(void) {
    unsigned char input[35];
    size_t count = fread(input, 1, sizeof input, stdin);
    if (ferror(stdin)) {
        fputs("input error\n", stderr);
        return 3;
    }
    if (count < 2 || input[0] != (unsigned char)'L') {
        fputs("invalid header\n", stderr);
        return 2;
    }
    size_t length = input[1];
    if (length > 32 || count != length + 2) {
        fputs("invalid length or trailing data\n", stderr);
        return 2;
    }
    unsigned int sum = 0;
    for (size_t i = 0; i < length; ++i) {
        sum += input[2 + i];
    }
    if (printf("%u\n", sum) < 0 || fflush(stdout) == EOF) {
        fputs("output error\n", stderr);
        return 3;
    }
    return 0;
}