#ifndef WORDFREQ_H
#define WORDFREQ_H
#include "measure.h"
#define WF_SLOTS 521
#define WF_MAX_KEYS 256
#define WF_MAX_WORD 63
#define WF_MAX_BYTES 1048576
typedef struct { char *key; size_t count; } wf_entry;
typedef struct { wf_entry slots[WF_SLOTS]; size_t used; ms_allocator allocator; } wf_table;
void wf_init(wf_table *table, ms_allocator allocator);
void wf_destroy(wf_table *table);
/* Whole-read transaction: failure frees temporary keys and leaves table unchanged.
 * table must be initialized empty; non-ASCII is INVALID, no Unicode tokenization. */
ms_status wf_read(FILE *f, wf_table *table);
/* Fixed slot addresses: view borrows records, no insertion during output. */
ms_status wf_report(const wf_table *table, ms_write_fn write, void *context);
#endif
