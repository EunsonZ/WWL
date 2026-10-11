#include <stdio.h>
#include <stdlib.h>
#if (defined(__STDC_NO_THREADS__) && __STDC_NO_THREADS__) || \
    (defined(__STDC_NO_ATOMICS__) && __STDC_NO_ATOMICS__)
int main(void) { puts("bounded_queue=UNSUPPORTED_C11_THREADS_OR_ATOMICS"); return 77; }
#else
#include <threads.h>
#include <stdatomic.h>
#include "measure.h"
#define QUEUE_CAPACITY 2
#define RECORD_SIZE 64
/* main owns queue; worker contexts and input remain live through all joins. */
typedef struct {
    uint16_t slots[QUEUE_CAPACITY]; size_t head, length;
    int closed, cancelled;
    mtx_t mutex; cnd_t nonempty, nonfull;
    atomic_uint published, consumed; /* diagnostics, not queue predicates */
} queue;
typedef struct { queue *q; const uint16_t *input; size_t n; int inject_bad; } producer_context;
typedef struct { queue *q; uint16_t output[RECORD_SIZE]; double filtered[RECORD_SIZE]; size_t n; } consumer_context;
static void require_success(int result) {
    if (result != thrd_success) {
        fputs("fatal=C11 synchronization operation failed\n",stderr);
        /* No unsafe freeing/destroy while another worker may hold a reference. */
        _Exit(1);
    }
}
static int queue_init(queue *q) {
    q->head = 0; q->length = 0; q->closed = 0; q->cancelled = 0;
    atomic_init(&q->published,0); atomic_init(&q->consumed,0);
    if (mtx_init(&q->mutex,mtx_plain) != thrd_success) return 0;
    if (cnd_init(&q->nonempty) != thrd_success) { mtx_destroy(&q->mutex); return 0; }
    if (cnd_init(&q->nonfull) != thrd_success) {
        cnd_destroy(&q->nonempty); mtx_destroy(&q->mutex); return 0;
    }
    return 1;
}
static void queue_destroy(queue *q) {
    /* Caller proves that no worker or waiter remains. */
    cnd_destroy(&q->nonfull); cnd_destroy(&q->nonempty); mtx_destroy(&q->mutex);
}
static void queue_cancel(queue *q) {
    require_success(mtx_lock(&q->mutex)); q->cancelled = 1;
    require_success(cnd_broadcast(&q->nonempty)); require_success(cnd_broadcast(&q->nonfull));
    require_success(mtx_unlock(&q->mutex));
}
static void queue_close(queue *q) {
    require_success(mtx_lock(&q->mutex)); q->closed = 1;
    require_success(cnd_broadcast(&q->nonempty)); require_success(cnd_broadcast(&q->nonfull));
    require_success(mtx_unlock(&q->mutex));
}
static int queue_push(queue *q, uint16_t code) {
    require_success(mtx_lock(&q->mutex));
    while (q->length == QUEUE_CAPACITY && !q->cancelled && !q->closed)
        require_success(cnd_wait(&q->nonfull,&q->mutex));
    if (q->cancelled || q->closed) { require_success(mtx_unlock(&q->mutex)); return 0; }
    size_t index = q->head + q->length; /* <=3, this fixed queue */
    if (index >= QUEUE_CAPACITY) index -= QUEUE_CAPACITY;
    q->slots[index] = code; ++q->length;
    atomic_fetch_add_explicit(&q->published,1,memory_order_relaxed);
    require_success(cnd_signal(&q->nonempty)); require_success(mtx_unlock(&q->mutex)); return 1;
}
/* 1=value, 0=closed and drained, -1=cancelled: cancel discards the remaining queue. */
static int queue_pop(queue *q, uint16_t *code) {
    require_success(mtx_lock(&q->mutex));
    while (!q->length && !q->closed && !q->cancelled)
        require_success(cnd_wait(&q->nonempty,&q->mutex));
    if (q->cancelled) { require_success(mtx_unlock(&q->mutex)); return -1; }
    if (!q->length) { require_success(mtx_unlock(&q->mutex)); return 0; }
    *code = q->slots[q->head]; q->head = q->head == QUEUE_CAPACITY-1 ? 0 : q->head+1;
    --q->length; atomic_fetch_add_explicit(&q->consumed,1,memory_order_relaxed);
    require_success(cnd_signal(&q->nonfull)); require_success(mtx_unlock(&q->mutex)); return 1;
}
static int produce(void *argument) {
    producer_context *ctx = argument;
    for (size_t i = 0; i < ctx->n; ++i) {
        uint16_t code = ctx->inject_bad && i == 4 ? UINT16_C(4096) : ctx->input[i];
        if (code > MS_MAX_CODE) { queue_cancel(ctx->q); return 1; }
        if (!queue_push(ctx->q,code)) return 1;
    }
    queue_close(ctx->q); return 0;
}
static int consume(void *argument) {
    consumer_context *ctx = argument; ms_fir f;
    if (ms_fir_init(&f) != MS_OK) { queue_cancel(ctx->q); return 1; }
    uint16_t code; int result;
    while ((result = queue_pop(ctx->q,&code)) == 1) {
        if (ctx->n == RECORD_SIZE || ms_fir_next(&f,code,(ms_calibration){1,0,1},
                                                &ctx->filtered[ctx->n]) != MS_OK) {
            queue_cancel(ctx->q); return 1;
        }
        ctx->output[ctx->n++] = code;
    }
    return result == 0 ? 0 : 1;
}
static int one_record(int inject_bad, int inject_create_failure) {
    queue q;
    if (!queue_init(&q)) return 0;
    uint16_t input[RECORD_SIZE];
    for (size_t i = 0; i < RECORD_SIZE; ++i) input[i] = (uint16_t)(2*(i+1));
    producer_context producer = {&q,input,RECORD_SIZE,inject_bad};
    consumer_context consumer = {0}; consumer.q = &q;
    thrd_t producer_thread, consumer_thread;
    if (thrd_create(&consumer_thread,consume,&consumer) != thrd_success) {
        queue_destroy(&q); return 0;
    }
    int created = inject_create_failure ? thrd_error : thrd_create(&producer_thread,produce,&producer);
    if (created != thrd_success) {
        queue_cancel(&q); int consumer_code;
        require_success(thrd_join(consumer_thread,&consumer_code)); queue_destroy(&q);
        return inject_create_failure && consumer_code == 1;
    }
    int producer_code, consumer_code;
    require_success(thrd_join(producer_thread,&producer_code));
    require_success(thrd_join(consumer_thread,&consumer_code));
    unsigned published = atomic_load_explicit(&q.published,memory_order_relaxed);
    unsigned consumed = atomic_load_explicit(&q.consumed,memory_order_relaxed);
    queue_destroy(&q);
    if (inject_bad) return producer_code == 1 && consumer_code == 1 && published <= 4 && consumed <= published;
    if (producer_code || consumer_code || consumer.n != RECORD_SIZE ||
        published != RECORD_SIZE || consumed != RECORD_SIZE) return 0;
    for (size_t i = 0; i < RECORD_SIZE; ++i) {
        if (consumer.output[i] != input[i]) return 0;
        double previous = i ? input[i-1] : 0;
        if (consumer.filtered[i] != (previous + input[i])*0.5) return 0;
    }
    return 1;
}
int main(void) {
    /* At most main+one producer+one consumer=3 concurrent threads. */
    for (unsigned i = 0; i < 20; ++i)
        if (!one_record(0,0) || !one_record(1,0) || !one_record(0,1)) return 1;
    puts("bounded_queue=PASS normal,drain,cancel,create_failure,join,ordered_fir"); return 0;
}
#endif
