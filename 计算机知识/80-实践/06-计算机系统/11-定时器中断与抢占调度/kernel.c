#include "trapframe.h"

typedef unsigned int u32;
typedef unsigned char u8;

extern char supervisor_trap_entry[];
extern void supervisor_return_to_user(struct trapframe *);
extern char user0_start[], user0_hot_loop[], user0_hot_loop_end[];
extern char user0_exit[], user0_exit_ecall[];
extern char user1_start[], user1_hot_loop[], user1_hot_loop_end[];
extern char user1_exit[], user1_exit_ecall[];
extern char root_page_table[], user_l1_page_table[], user_l0_page_table[];
extern char kernel_l1_page_table[], kernel_l0_page_table[];
extern char task0_stack_bottom[], task0_stack_top[];
extern char task1_stack_bottom[], task1_stack_top[];
extern char task0_trapframe[], task1_trapframe[];
extern char kernel_end[];

enum {
    PTE_V = 1UL << 0,
    PTE_R = 1UL << 1,
    PTE_W = 1UL << 2,
    PTE_X = 1UL << 3,
    PTE_U = 1UL << 4,
    PTE_A = 1UL << 6,
    PTE_D = 1UL << 7,
};

enum task_state {
    RUNNABLE = 0,
    EXIT_PENDING = 1,
    EXITED = 2,
};

struct scheduler_context {
    u64 id;
    struct trapframe *frame;
    u64 code_lo;
    u64 code_hi;
    u64 exit_pc;
    u64 exit_ecall_pc;
    u64 stack_top_va;
    u64 stack_top_pa;
    u64 register_canary;
    u64 caller_a5_canary;
    u64 caller_t5_canary;
    u64 stack_canary;
    u64 last_work;
    u64 last_stack_work;
    u64 preemptions;
    u64 switches;
    enum task_state state;
};

#define UART0 0x10000000UL
#define TEST_FINISHER 0x00100000UL
#define USER_ALIAS_DELTA 0x40010000UL
#define USER0_CODE_VA 0x40000000UL
#define USER_DATA_VA 0x40001000UL
#define USER1_CODE_VA 0x40002000UL
#define TASK0_STACK_VA 0x40003000UL
#define TASK1_STACK_VA 0x40004000UL
#define TIMEBASE_HZ 10000000UL
#define QUANTUM_TICKS 2000000UL
#define MIN_WORK 1000UL
#define SCAUSE_INTERRUPT (1UL << 63)
#define SCAUSE_STIMER (SCAUSE_INTERRUPT | 5UL)
#define SSTATUS_SIE (1UL << 1)
#define SSTATUS_SPIE (1UL << 5)
#define SSTATUS_SPP (1UL << 8)
#define SSTATUS_SUM (1UL << 18)
#define SSTATUS_MXR (1UL << 19)
#define SIE_STIE (1UL << 5)

static volatile u8 *const uart = (volatile u8 *)UART0;
static volatile u32 *const finisher = (volatile u32 *)TEST_FINISHER;
static struct scheduler_context tasks[2];
static u64 current_task;
static u64 timer_ticks;
static u64 exit_count;
static u64 trap_depth;

_Static_assert(sizeof(struct trapframe) == 280, "trapframe layout mismatch");

static inline u64 read_time(void) {
    u64 value;
    __asm__ volatile("csrr %0, 0xc01" : "=r"(value));
    return value;
}

static inline u64 read_satp(void) {
    u64 value;
    __asm__ volatile("csrr %0, satp" : "=r"(value));
    return value;
}

static inline u64 read_mcause(void) {
    u64 value;
    __asm__ volatile("csrr %0, mcause" : "=r"(value));
    return value;
}

static inline u64 read_mepc(void) {
    u64 value;
    __asm__ volatile("csrr %0, mepc" : "=r"(value));
    return value;
}

static inline u64 read_mtval(void) {
    u64 value;
    __asm__ volatile("csrr %0, mtval" : "=r"(value));
    return value;
}

static inline void write_stimecmp(u64 value) {
    __asm__ volatile("csrw 0x14d, %0" : : "r"(value) : "memory");
}

static void putc(char character) {
    *uart = (u8)character;
}

static void puts(const char *text) {
    while (*text != '\0') {
        putc(*text++);
    }
}

static void put_hex(u64 value) {
    static const char digits[] = "0123456789abcdef";
    puts("0x");
    for (int shift = 60; shift >= 0; shift -= 4) {
        putc(digits[(value >> shift) & 0xfUL]);
    }
}

static void put_uint(u64 value) {
    char buffer[24];
    int index = 0;
    if (value == 0) {
        putc('0');
        return;
    }
    while (value != 0) {
        buffer[index++] = (char)('0' + value % 10);
        value /= 10;
    }
    while (index != 0) {
        putc(buffer[--index]);
    }
}

__attribute__((noreturn)) void qemu_fail(u64 code) {
    puts("RESULT FAIL code=");
    put_hex(code);
    puts("\n");
    *finisher = (u32)(((code & 0xffffUL) << 16) | 0x3333UL);
    for (;;) {
        __asm__ volatile("wfi");
    }
}

__attribute__((noreturn)) static void qemu_pass(void) {
    puts("RESULT PASS\n");
    *finisher = 0x5555U;
    for (;;) {
        __asm__ volatile("wfi");
    }
}

void machine_banner(u64 menvcfg, u64 mcounteren, u64 mideleg, u64 mie) {
    if ((menvcfg & (1UL << 63)) == 0 ||
        (mcounteren & (1UL << 1)) == 0 ||
        (mideleg & (1UL << 5)) == 0 ||
        (mie & (1UL << 7)) != 0) {
        qemu_fail(0x10);
    }
    puts("MODE M: Sstc=1 STCE=1 mcounteren.TM=1 mideleg.STIP=1 MTIE=0\n");
}

__attribute__((noreturn)) void machine_trap(void) {
    puts("MACHINE TRAP mcause=");
    put_hex(read_mcause());
    puts(" mepc=");
    put_hex(read_mepc());
    puts(" mtval=");
    put_hex(read_mtval());
    puts("\n");
    qemu_fail(0x11);
}

static u64 pa_to_pte(u64 pa) {
    return (pa >> 12) << 10;
}

static u64 pte_to_pa(u64 pte) {
    return (pte >> 10) << 12;
}

static u64 pointer_pte(const volatile void *page) {
    return pa_to_pte((u64)page) | PTE_V;
}

static u64 leaf_pte(u64 pa, u64 flags) {
    if ((flags & PTE_W) != 0 && (flags & PTE_R) == 0) {
        qemu_fail(0x12);
    }
    return pa_to_pte(pa) | flags | PTE_V;
}

static void zero_page(volatile u64 *page) {
    for (u64 index = 0; index < 512; ++index) {
        page[index] = 0;
    }
}

static u64 user_va(const void *physical_symbol) {
    return (u64)physical_symbol - USER_ALIAS_DELTA;
}

static void build_page_tables(void) {
    volatile u64 *root = (volatile u64 *)root_page_table;
    volatile u64 *user_l1 = (volatile u64 *)user_l1_page_table;
    volatile u64 *user_l0 = (volatile u64 *)user_l0_page_table;
    volatile u64 *kernel_l1 = (volatile u64 *)kernel_l1_page_table;
    volatile u64 *kernel_l0 = (volatile u64 *)kernel_l0_page_table;
    zero_page(root);
    zero_page(user_l1);
    zero_page(user_l0);
    zero_page(kernel_l1);
    zero_page(kernel_l0);

    root[0] = leaf_pte(0, PTE_R | PTE_W | PTE_A | PTE_D);
    root[1] = pointer_pte(user_l1);
    user_l1[0] = pointer_pte(user_l0);
    user_l0[0] = leaf_pte(0x80010000UL, PTE_R | PTE_X | PTE_U | PTE_A);
    user_l0[1] = leaf_pte(0x80011000UL,
                          PTE_R | PTE_W | PTE_U | PTE_A | PTE_D);
    user_l0[2] = leaf_pte(0x80012000UL, PTE_R | PTE_X | PTE_U | PTE_A);
    user_l0[3] = leaf_pte(0x80013000UL,
                          PTE_R | PTE_W | PTE_U | PTE_A | PTE_D);
    user_l0[4] = leaf_pte(0x80014000UL,
                          PTE_R | PTE_W | PTE_U | PTE_A | PTE_D);

    root[2] = pointer_pte(kernel_l1);
    kernel_l1[0] = pointer_pte(kernel_l0);
    for (u64 pa = 0x80000000UL; pa < (u64)kernel_end; pa += 4096) {
        kernel_l0[(pa >> 12) & 0x1ffUL] =
            leaf_pte(pa, PTE_R | PTE_W | PTE_X | PTE_A | PTE_D);
    }
}

static void clear_frame(struct trapframe *frame) {
    volatile u64 *words = (volatile u64 *)frame;
    for (u64 index = 0; index < sizeof(*frame) / sizeof(u64); ++index) {
        words[index] = 0;
    }
}

static void initialize_tasks(u64 initial_status) {
    tasks[0] = (struct scheduler_context){
        .id = 0,
        .frame = (struct trapframe *)task0_trapframe,
        .code_lo = user_va(user0_hot_loop),
        .code_hi = user_va(user0_hot_loop_end),
        .exit_pc = user_va(user0_exit),
        .exit_ecall_pc = user_va(user0_exit_ecall),
        .stack_top_va = TASK0_STACK_VA + 4096,
        .stack_top_pa = (u64)task0_stack_top,
        .register_canary = 0x1111222233334444UL,
        .caller_a5_canary = 0x13579bdf2468ace0UL,
        .caller_t5_canary = 0x0f1e2d3c4b5a6978UL,
        .stack_canary = 0xa0a0b0b0c0c0d0d0UL,
        .state = RUNNABLE,
    };
    tasks[1] = (struct scheduler_context){
        .id = 1,
        .frame = (struct trapframe *)task1_trapframe,
        .code_lo = user_va(user1_hot_loop),
        .code_hi = user_va(user1_hot_loop_end),
        .exit_pc = user_va(user1_exit),
        .exit_ecall_pc = user_va(user1_exit_ecall),
        .stack_top_va = TASK1_STACK_VA + 4096,
        .stack_top_pa = (u64)task1_stack_top,
        .register_canary = 0x5555666677778888UL,
        .caller_a5_canary = 0x02468ace13579bdfUL,
        .caller_t5_canary = 0x89abcdef01234567UL,
        .stack_canary = 0xa1a1b1b1c1c1d1d1UL,
        .state = RUNNABLE,
    };
    for (u64 index = 0; index < 2; ++index) {
        clear_frame(tasks[index].frame);
        tasks[index].frame->sp = tasks[index].stack_top_va;
        tasks[index].frame->sepc = index == 0 ? user_va(user0_start)
                                              : user_va(user1_start);
        tasks[index].frame->sstatus = initial_status;
    }
}

static u64 arm_next_timer(void) {
    u64 now = read_time();
    write_stimecmp(now + QUANTUM_TICKS);
    return now;
}

static u64 physical_stack_word(const struct scheduler_context *task,
                               u64 bytes_below_top) {
    return *(volatile u64 *)(task->stack_top_pa - bytes_below_top);
}

static void validate_user_frame(struct scheduler_context *task,
                                const struct trapframe *tf, u64 code) {
    if (tf != task->frame ||
        tf->sp != task->stack_top_va ||
        tf->s0 != task->register_canary ||
        tf->s2 != task->id ||
        tf->a5 != task->caller_a5_canary ||
        tf->t5 != task->caller_t5_canary ||
        physical_stack_word(task, 8) != task->stack_canary ||
        (tf->sstatus & SSTATUS_SPP) != 0 ||
        (tf->sstatus & SSTATUS_SIE) != 0 ||
        (tf->sstatus & SSTATUS_SPIE) == 0) {
        qemu_fail(code);
    }
}

static struct trapframe *handle_timer(struct trapframe *tf) {
    u64 now = arm_next_timer();
    ++trap_depth;
    if (trap_depth != 1 || tf->scause != SCAUSE_STIMER || tf->stval != 0 ||
        current_task > 1 || tasks[current_task].state != RUNNABLE) {
        qemu_fail(0x20);
    }

    struct scheduler_context *from = &tasks[current_task];
    validate_user_frame(from, tf, 0x21);
    if (tf->sepc < from->code_lo || tf->sepc >= from->code_hi) {
        qemu_fail(0x25);
    }
    u64 interrupted_pc = tf->sepc;
    u64 stack_work = physical_stack_word(from, 16);
    if (tf->s1 <= from->last_work || stack_work <= from->last_stack_work ||
        tf->s1 < MIN_WORK || stack_work < MIN_WORK) {
        qemu_fail(0x22);
    }
    from->last_work = tf->s1;
    from->last_stack_work = stack_work;
    ++from->preemptions;
    ++from->switches;
    ++timer_ticks;
    if (from->preemptions > 3 || timer_ticks > 6) {
        qemu_fail(0x23);
    }
    if (from->preemptions == 3) {
        from->state = EXIT_PENDING;
        tf->sepc = from->exit_pc;
    }

    u64 next_id = 1 - current_task;
    struct scheduler_context *next = &tasks[next_id];
    if (next->state == EXITED || next_id == current_task) {
        qemu_fail(0x24);
    }

    puts("TICK n=");
    put_uint(timer_ticks);
    puts(" cause=");
    put_hex(tf->scause);
    puts(" now=");
    put_hex(now);
    puts(" deadline=");
    put_hex(now + QUANTUM_TICKS);
    puts(" from=");
    put_uint(current_task);
    puts(" to=");
    put_uint(next_id);
    puts(" sepc=");
    put_hex(interrupted_pc);
    puts(" sp=");
    put_hex(tf->sp);
    puts(" work=");
    put_hex(tf->s1);
    puts(" stack=");
    put_hex(stack_work);
    puts(" SPP=0 SPIE=1 depth=1\n");

    puts("SWITCH from_tf=");
    put_hex((u64)from->frame);
    puts(" to_tf=");
    put_hex((u64)next->frame);
    puts(" next_pc=");
    put_hex(next->frame->sepc);
    puts("\n");

    current_task = next_id;
    --trap_depth;
    return next->frame;
}

static struct trapframe *handle_exit(struct trapframe *tf) {
    if (current_task > 1) {
        qemu_fail(0x30);
    }
    struct scheduler_context *task = &tasks[current_task];
    validate_user_frame(task, tf, 0x31);
    u64 stack_work = physical_stack_word(task, 16);
    if (task->state != EXIT_PENDING || tf->a7 != 1 ||
        tf->a0 != current_task || tf->a1 != tf->s1 ||
        tf->a2 != stack_work || tf->sepc != task->exit_ecall_pc ||
        task->preemptions != 3 || tf->s1 < MIN_WORK ||
        stack_work < MIN_WORK || exit_count != current_task) {
        qemu_fail(0x32);
    }
    task->state = EXITED;
    ++exit_count;
    puts("EXIT task=");
    put_uint(current_task);
    puts(" work=");
    put_hex(tf->s1);
    puts(" stack=");
    put_hex(stack_work);
    puts(" preemptions=3 status=PASS\n");

    if (exit_count == 1) {
        current_task = 1;
        if (tasks[1].state != EXIT_PENDING) {
            qemu_fail(0x33);
        }
        return tasks[1].frame;
    }

    if (timer_ticks != 6 || tasks[0].preemptions != 3 ||
        tasks[1].preemptions != 3 || tasks[0].state != EXITED ||
        tasks[1].state != EXITED || tasks[0].switches != 3 ||
        tasks[1].switches != 3) {
        qemu_fail(0x34);
    }
    __asm__ volatile("csrw sie, zero" : : : "memory");
    write_stimecmp(~0UL);
    puts("SUMMARY ticks=6 task0_preemptions=3 task1_preemptions=3 "
         "switches=6 status=PASS\n");
    qemu_pass();
}

struct trapframe *supervisor_trap(struct trapframe *tf) {
    if (tf->scause == SCAUSE_STIMER) {
        return handle_timer(tf);
    }
    if (tf->scause == 8) {
        if (tf->a7 == 7) {
            qemu_fail(0x37);
        }
        return handle_exit(tf);
    }
    qemu_fail(0x3f);
}

__attribute__((noreturn)) void supervisor_main(void) {
    puts("MODE S: build Sv39 and two user contexts\n");
    build_page_tables();
    u64 root_ppn = (u64)root_page_table >> 12;
    u64 satp = (8UL << 60) | root_ppn;
    __asm__ volatile("fence rw, rw" : : : "memory");
    __asm__ volatile("csrw satp, %0" : : "r"(satp) : "memory");
    __asm__ volatile("sfence.vma zero, zero" : : : "memory");
    if (read_satp() != satp || pte_to_pa(((volatile u64 *)root_page_table)[1]) !=
                                   (u64)user_l1_page_table) {
        qemu_fail(0x40);
    }

    u64 status;
    __asm__ volatile("csrr %0, sstatus" : "=r"(status));
    status &= ~(SSTATUS_SPP | SSTATUS_SIE | SSTATUS_SUM | SSTATUS_MXR);
    status |= SSTATUS_SPIE;
    initialize_tasks(status);
    __asm__ volatile("csrw stvec, %0" : : "r"((u64)supervisor_trap_entry));
    __asm__ volatile("csrw sie, %0" : : "r"(SIE_STIE));
    current_task = 0;
    u64 now = arm_next_timer();

    puts("SATP mode=8 root_pa=");
    put_hex((u64)root_page_table);
    puts(" user0_code=0x0000000040000000 user1_code=0x0000000040002000\n");
    puts("TIMER source=Sstc timebase_hz=10000000 quantum_ticks=2000000 now=");
    put_hex(now);
    puts(" first_deadline=");
    put_hex(now + QUANTUM_TICKS);
    puts(" STIE=1 SPIE=1 SIE-before-sret=0\n");
    puts("TASK id=0 tf=0x000000008001a000 stack=[0x0000000040003000,"
         "0x0000000040004000) entry=0x0000000040000000\n");
    puts("TASK id=1 tf=0x000000008001b000 stack=[0x0000000040004000,"
         "0x0000000040005000) entry=0x0000000040002000\n");
    puts("MODE U: task=0 hot-loop-no-yield\n");
    supervisor_return_to_user(tasks[0].frame);
    __builtin_unreachable();
}
