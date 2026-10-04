#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * Result contract: every function returns
 *     sum_{r,c} matrix[r * columns + c] (mod 2^32).
 * This candidate deliberately admits only implementations where uint32_t has
 * unsigned-int arithmetic and int cannot represent every uint32_t value.
 * The assertions below therefore rule out an integer-promotion path through a
 * signed int.  The examples do not use signed overflow as an optimization
 * technique.
 */

_Static_assert(UINT_MAX == UINT32_MAX, "this lab requires a 32-bit unsigned int");
_Static_assert(INT_MAX < UINT32_MAX, "this lab requires uint32_t not to promote to int");

typedef uint32_t (*sum_function)(const uint32_t *matrix, size_t rows, size_t columns);

/* Every caller must establish this before forming row*columns or allocating. */
static int checked_element_count(size_t rows, size_t columns, size_t *count) {
    if (columns != 0U && rows > SIZE_MAX / columns) {
        return 0;
    }
    const size_t elements = rows * columns;
    if (elements > SIZE_MAX / sizeof(uint32_t)) {
        return 0;
    }
    *count = elements;
    return 1;
}

static uint32_t sum_baseline(const uint32_t *matrix, size_t rows, size_t columns) {
    uint32_t total = 0U;
    for (size_t row = 0; row < rows; ++row) {
        for (size_t column = 0; column < columns; ++column) {
            total += matrix[row * columns + column];
        }
    }
    return total;
}

/* Same visit order as baseline; explicitly retain the row base. */
static uint32_t sum_row_base(const uint32_t *matrix, size_t rows, size_t columns) {
    uint32_t total = 0U;
    for (size_t row = 0; row < rows; ++row) {
        const uint32_t *cursor = matrix + row * columns;
        for (size_t column = 0; column < columns; ++column) {
            total += cursor[column];
        }
    }
    return total;
}

/* Same row-major visit order, but four independent accumulator chains. */
static uint32_t sum_four_accumulators(const uint32_t *matrix, size_t rows, size_t columns) {
    uint32_t total0 = 0U;
    uint32_t total1 = 0U;
    uint32_t total2 = 0U;
    uint32_t total3 = 0U;
    const size_t count = rows * columns;
    size_t index = 0U;
    for (; index + 3U < count; index += 4U) {
        total0 += matrix[index];
        total1 += matrix[index + 1U];
        total2 += matrix[index + 2U];
        total3 += matrix[index + 3U];
    }
    uint32_t total = total0 + total1 + total2 + total3;
    for (; index < count; ++index) {
        total += matrix[index];
    }
    return total;
}

/* Same mathematical result but a column-major visit order over row-major data. */
static uint32_t sum_column_visit(const uint32_t *matrix, size_t rows, size_t columns) {
    uint32_t total = 0U;
    for (size_t column = 0; column < columns; ++column) {
        for (size_t row = 0; row < rows; ++row) {
            total += matrix[row * columns + column];
        }
    }
    return total;
}

static int equal_for_case(const uint32_t *matrix, size_t rows, size_t columns) {
    size_t count = 0U;
    if (!checked_element_count(rows, columns, &count) || (count != 0U && matrix == NULL)) {
        return 0;
    }
    const uint32_t expected = sum_baseline(matrix, rows, columns);
    return sum_row_base(matrix, rows, columns) == expected &&
           sum_four_accumulators(matrix, rows, columns) == expected &&
           sum_column_visit(matrix, rows, columns) == expected;
}

static int self_test(void) {
    const uint32_t tiny[] = {UINT32_MAX, 1U, 7U, 9U, 11U, 13U};
    const uint32_t expected = 40U; /* UINT32_MAX + 1 is zero in the contract. */
    if (sum_baseline(tiny, 2U, 3U) != expected || !equal_for_case(tiny, 2U, 3U)) {
        return 0;
    }
    if (!equal_for_case(tiny, 0U, 3U) || !equal_for_case(tiny, 2U, 0U)) {
        return 0;
    }
    size_t count = 0U;
    if (checked_element_count(SIZE_MAX, 2U, &count) ||
        checked_element_count(SIZE_MAX / sizeof(uint32_t) + 1U, 1U, &count) ||
        !checked_element_count(5U, 7U, &count) || count != 35U ||
        equal_for_case(NULL, 1U, 1U)) {
        return 0;
    }

    uint32_t values[35];
    uint32_t state = UINT32_C(0xC0FFEE11);
    for (size_t index = 0; index < 35U; ++index) {
        state = state * UINT32_C(1664525) + UINT32_C(1013904223);
        values[index] = state;
    }
    for (size_t rows = 1U; rows <= 5U; ++rows) {
        for (size_t columns = 1U; columns <= 7U; ++columns) {
            if (!equal_for_case(values, rows, columns)) {
                return 0;
            }
        }
    }
    return 1;
}

static uint64_t monotonic_nanoseconds(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        return 0U;
    }
    return (uint64_t)now.tv_sec * UINT64_C(1000000000) + (uint64_t)now.tv_nsec;
}

static uint64_t measure(sum_function function, const uint32_t *matrix, size_t rows, size_t columns,
                        unsigned repetitions, volatile uint32_t *guard) {
    const uint64_t start = monotonic_nanoseconds();
    for (unsigned repeat = 0U; repeat < repetitions; ++repeat) {
        *guard ^= function(matrix, rows, columns);
    }
    const uint64_t finish = monotonic_nanoseconds();
    return finish >= start ? finish - start : 0U;
}

static const char *compiler_description(void) {
#if defined(__clang__)
    return "clang";
#elif defined(__GNUC__)
    return "gcc";
#else
    return "unknown-c-compiler";
#endif
}

static int run_benchmark(unsigned samples) {
    enum { rows = 769, columns = 773, repetitions = 64 };
    size_t count = 0U;
    if (!checked_element_count(rows, columns, &count)) {
        fprintf(stderr, "benchmark shape is not representable\n");
        return 1;
    }
    uint32_t *matrix = malloc(count * sizeof(*matrix));
    if (matrix == NULL) {
        fprintf(stderr, "allocation failed\n");
        return 1;
    }
    uint32_t state = UINT32_C(0x12345678);
    for (size_t index = 0U; index < count; ++index) {
        state = state * UINT32_C(1103515245) + UINT32_C(12345);
        matrix[index] = state;
    }
    if (!equal_for_case(matrix, rows, columns)) {
        fprintf(stderr, "result-contract failed before measurement\n");
        free(matrix);
        return 1;
    }

    const char *names[] = {"baseline", "row_base", "four_accumulators", "column_visit"};
    const sum_function functions[] = {sum_baseline, sum_row_base, sum_four_accumulators, sum_column_visit};
    volatile uint32_t guard = 0U;
    printf("compiler=%s, sizeof_uint32=%zu, NDEBUG=%s\n", compiler_description(), sizeof(uint32_t),
#ifdef NDEBUG
           "defined"
#else
           "not-defined"
#endif
    );
    printf("contract=uint32_t-sum-mod-2^32, layout=row-major, rows=%d, columns=%d, repetitions=%d, samples=%u\n",
           rows, columns, repetitions, samples);
    for (unsigned sample = 0U; sample < samples; ++sample) {
        printf("sample=%u", sample);
        for (size_t turn = 0U; turn < 4U; ++turn) {
            const size_t which = (turn + sample) % 4U;
            const uint64_t elapsed = measure(functions[which], matrix, rows, columns, repetitions, &guard);
            printf(" %s_ns=%" PRIu64, names[which], elapsed);
        }
        putchar('\n');
    }
    printf("guard=%" PRIu32 " (prevents an unused-result measurement)\n", guard);
    free(matrix);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        const int passed = self_test();
        puts(passed ? "self-test passed" : "self-test failed");
        return passed ? 0 : 1;
    }
    unsigned samples = 7U;
    if (argc == 3 && strcmp(argv[1], "--benchmark") == 0) {
        char *end = NULL;
        const unsigned long parsed = strtoul(argv[2], &end, 10);
        if (end == argv[2] || *end != '\0' || parsed == 0UL || parsed > 99UL) {
            fprintf(stderr, "samples must be an integer from 1 through 99\n");
            return 2;
        }
        samples = (unsigned)parsed;
    } else if (argc != 1) {
        fprintf(stderr, "usage: %s [--self-test | --benchmark SAMPLES]\n", argv[0]);
        return 2;
    }
    return run_benchmark(samples);
}
