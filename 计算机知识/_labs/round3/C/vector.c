#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { int *data; size_t size, cap; } Vec;
static int fail_next = 0;
static void *test_realloc(void *p, size_t n) {
    if (fail_next) { fail_next = 0; return NULL; }
    return realloc(p, n);
}
/* Failure leaves the vector unchanged. No realloc(p, 0) ambiguity. */
static int reserve(Vec *v, size_t n) {
    if (n <= v->cap) return 1;
    if (n > SIZE_MAX / sizeof *v->data) return 0;
    int *tmp = test_realloc(v->data, n * sizeof *v->data);
    if (!tmp) return 0;
    v->data = tmp;
    v->cap = n;
    return 1;
}
static int push(Vec *v, int x) {
    if (v->size == v->cap) {
        size_t n;
        if (!v->cap) n = 4;
        else {
            if (v->cap > SIZE_MAX / 2) return 0;
            n = v->cap * 2;
        }
        if (!reserve(v, n)) return 0;
    }
    v->data[v->size++] = x;
    return 1;
}
int main(void) {
    Vec v = {0};
    for (int i=0;i<1000;i++) assert(push(&v, i));
    for (size_t i=0;i<v.size;i++) assert(v.data[i] == (int)i);
    int *old = v.data; size_t oldcap=v.cap;
    fail_next=1;
    assert(!reserve(&v, oldcap+1));
    assert(v.data == old && v.cap == oldcap && v.size == 1000);
    assert(!reserve(&v, SIZE_MAX));
    assert(v.data[999] == 999);
    free(v.data); v=(Vec){0};
    puts("PASS: vector growth, contents, overflow rejection, allocation failure atomicity");
    return 0;
}
