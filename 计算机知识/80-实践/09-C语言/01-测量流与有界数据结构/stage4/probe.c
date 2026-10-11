#include <stdio.h>
#if defined(__STDC_NO_THREADS__) && __STDC_NO_THREADS__
#define HAVE_THREADS 0
#else
#define HAVE_THREADS 1
#include <threads.h>
#endif
#if defined(__STDC_NO_ATOMICS__) && __STDC_NO_ATOMICS__
#define HAVE_ATOMICS 0
#else
#define HAVE_ATOMICS 1
#include <stdatomic.h>
#endif
#if HAVE_THREADS && HAVE_ATOMICS
static int increment(void *context) {
    atomic_uint *n = context;
    atomic_fetch_add_explicit(n,1,memory_order_relaxed); return 0;
}
#endif
int main(void) {
    printf("threads_macro=%d\natomics_macro=%d\n",HAVE_THREADS,HAVE_ATOMICS);
#if HAVE_ATOMICS
    atomic_uint n; atomic_init(&n,0);
    atomic_fetch_add_explicit(&n,1,memory_order_relaxed);
    if (atomic_load(&n) != 1) return 1;
    printf("atomic_uint_lock_free=%d\natomic_local_increment=PASS\n",atomic_is_lock_free(&n));
#endif
#if HAVE_THREADS && HAVE_ATOMICS
    atomic_store(&n,0);
    thrd_t worker;
    if (thrd_create(&worker,increment,&n) != thrd_success) return 1;
    int code;
    if (thrd_join(worker,&code) != thrd_success || code != 0 || atomic_load(&n) != 1) return 1;
    puts("create_join_increment=PASS");
    return 0;
#else
    puts("create_join_increment=UNSUPPORTED"); return 77;
#endif
}
