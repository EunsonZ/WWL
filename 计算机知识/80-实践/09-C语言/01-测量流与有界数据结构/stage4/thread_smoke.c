/* Direct header/type/link/runtime probe: no feature macro is undefined.
 * Intentionally includes threads.h on unsupported targets to capture the
 * actual header diagnostic separately from the guarded production stub. */
#include <threads.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { mtx_t lock; cnd_t ready; int value; atomic_uint done; } state;
static void required(int code) {
    if (code != thrd_success) { fputs("thread_smoke=synchronization_failure\n",stderr); _Exit(1); }
}
static int publish(void *context) {
    state *s=context;
    required(mtx_lock(&s->lock)); s->value=42;
    required(cnd_signal(&s->ready)); required(mtx_unlock(&s->lock));
    atomic_store_explicit(&s->done,1,memory_order_relaxed); return 7;
}
int main(void) {
    state s; s.value=0; atomic_init(&s.done,0);
    if (mtx_init(&s.lock,mtx_plain) != thrd_success) return 1;
    if (cnd_init(&s.ready) != thrd_success) { mtx_destroy(&s.lock); return 1; }
    /* Hold the mutex before creation: worker cannot publish until cnd_wait
     * releases it, so at least one wait executes on the successful path. */
    required(mtx_lock(&s.lock));
    thrd_t worker;
    if (thrd_create(&worker,publish,&s) != thrd_success) {
        required(mtx_unlock(&s.lock));
        cnd_destroy(&s.ready); mtx_destroy(&s.lock); return 1;
    }
    while (!s.value) required(cnd_wait(&s.ready,&s.lock));
    int value=s.value; required(mtx_unlock(&s.lock));
    int returned; required(thrd_join(worker,&returned));
    unsigned done=atomic_load_explicit(&s.done,memory_order_relaxed);
    cnd_destroy(&s.ready); mtx_destroy(&s.lock);
    if (value != 42 || returned != 7 || done != 1) return 1;
    puts("thread_smoke=PASS mutex,condition,join,atomic"); return 0;
}
