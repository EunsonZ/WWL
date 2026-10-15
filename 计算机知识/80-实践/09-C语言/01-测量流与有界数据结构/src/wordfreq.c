#include "wordfreq.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
_Static_assert('A' == 65 && 'a' == 97 && 'Z' == 90 && 'z' == 122,
               "requires ASCII-compatible execution characters");
void wf_init(wf_table *t, ms_allocator a) {
    *t = (wf_table){0}; t->allocator = a;
}
void wf_destroy(wf_table *t) {
    for (size_t i = 0; i < WF_SLOTS; ++i)
        if (t->slots[i].key) t->allocator.release(t->slots[i].key, t->allocator.context);
    wf_init(t, t->allocator);
}
static size_t hash(const char *word) {
    uint32_t value = UINT32_C(5381);
    for (; *word; ++word) value = (uint32_t)((uint64_t)value * UINT64_C(33) + (unsigned char)*word);
    return (size_t)(value % WF_SLOTS);
}
static ms_status insert(wf_table *t, const char *word, size_t length) {
    size_t slot = hash(word);
    for (size_t probes = 0; probes < WF_SLOTS; ++probes) {
        wf_entry *e = &t->slots[slot];
        if (!e->key) {
            if (t->used == WF_MAX_KEYS) return MS_LIMIT;
            if (length == SIZE_MAX) return MS_LIMIT;
            char *copy = t->allocator.alloc(length + 1, t->allocator.context);
            if (!copy) return MS_NOMEM;
            memcpy(copy, word, length + 1);
            e->key = copy; e->count = 1; ++t->used; return MS_OK;
        }
        if (strcmp(e->key, word) == 0) {
            if (e->count == SIZE_MAX) return MS_LIMIT;
            ++e->count; return MS_OK;
        }
        slot = slot == WF_SLOTS - 1 ? 0 : slot + 1;
    }
    return MS_LIMIT;
}
ms_status wf_read(FILE *f, wf_table *out) {
    if (!f || !out || !out->allocator.alloc || !out->allocator.release || out->used)
        return MS_INVALID;
    for (size_t i = 0; i < WF_SLOTS; ++i) if (out->slots[i].key) return MS_INVALID;
    wf_table tmp; wf_init(&tmp, out->allocator);
    char word[WF_MAX_WORD + 1]; size_t length = 0; uint32_t bytes = 0; int c;
    ms_status status = MS_OK;
    while ((c = fgetc(f)) != EOF) {
        if (bytes == WF_MAX_BYTES) { status = MS_LIMIT; break; }
        ++bytes;
        if (c > 127) { status = MS_INVALID; break; }
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
            if (length == WF_MAX_WORD) { status = MS_LIMIT; break; }
            word[length++] = (char)(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
        } else if (length) {
            word[length] = '\0'; status = insert(&tmp, word, length); length = 0;
            if (status != MS_OK) break;
        }
    }
    if (status == MS_OK && ferror(f)) status = MS_IO;
    if (status == MS_OK && length) { word[length] = '\0'; status = insert(&tmp,word,length); }
    if (status != MS_OK) { wf_destroy(&tmp); return status; }
    *out = tmp; return MS_OK;
}
static int compare(const void *pa, const void *pb) {
    const wf_entry *a = *(const wf_entry *const *)pa;
    const wf_entry *b = *(const wf_entry *const *)pb;
    if (a->count != b->count) return a->count > b->count ? -1 : 1;
    return strcmp(a->key, b->key);
}
ms_status wf_report(const wf_table *t, ms_write_fn write, void *ctx) {
    if (!t || !write || t->used > WF_MAX_KEYS) return MS_INVALID;
    const wf_entry *view[WF_MAX_KEYS]; size_t n = 0;
    for (size_t i = 0; i < WF_SLOTS; ++i) {
        if (t->slots[i].key) {
            if (n == WF_MAX_KEYS) return MS_INVALID;
            view[n++] = &t->slots[i];
        }
    }
    if (n != t->used) return MS_INVALID;
    qsort(view, n, sizeof *view, compare);
    for (size_t i = 0; i < n; ++i) {
        char buffer[128]; int len = snprintf(buffer,sizeof buffer,"%s %zu\n",view[i]->key,view[i]->count);
        if (len < 0 || (size_t)len >= sizeof buffer || !write(buffer,(size_t)len,ctx)) return MS_IO;
    }
    return MS_OK;
}
