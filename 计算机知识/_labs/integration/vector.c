/* C11: failure-atomic integer vector. Controlled allocator failure is intentional. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

typedef struct { int *data; size_t len, cap; } Vec;
static bool fail_next_allocation = false;
static void *test_realloc(void *p, size_t n) {
    if (fail_next_allocation) { fail_next_allocation = false; return NULL; }
    return realloc(p, n);
}
static bool reserve(Vec *v, size_t need) {
    if (need <= v->cap) return true;
    size_t cap = v->cap ? v->cap : 4;
    while (cap < need) {
        if (cap > SIZE_MAX / 2) { cap = need; break; }
        cap *= 2;
    }
    if (cap > SIZE_MAX / sizeof *v->data) return false;
    int *candidate = test_realloc(v->data, cap * sizeof *v->data);
    if (!candidate) return false;
    v->data = candidate; v->cap = cap;
    return true;
}
static bool push(Vec *v, int value) {
    if (v->len == SIZE_MAX || !reserve(v, v->len + 1)) return false;
    v->data[v->len++] = value;
    return true;
}
int main(void) {
    Vec v = {0};
    for (int i = 0; i < 4; ++i) assert(push(&v, i));
    int *old = v.data; size_t old_cap = v.cap;
    fail_next_allocation = true;
    assert(!push(&v, 99));
    assert(v.data == old && v.len == 4 && v.cap == old_cap);
    for (size_t i = 0; i < v.len; ++i) assert(v.data[i] == (int)i);
    for (int i = 4; i < 200; ++i) assert(push(&v, i));
    assert(v.len == 200 && v.len <= v.cap);
    assert(!reserve(&v, SIZE_MAX));
    for (size_t i = 0; i < v.len; ++i) assert(v.data[i] == (int)i);
    free(v.data); v = (Vec){0};
    assert(v.data == NULL && v.len == 0 && v.cap == 0);
    return 0;
}
