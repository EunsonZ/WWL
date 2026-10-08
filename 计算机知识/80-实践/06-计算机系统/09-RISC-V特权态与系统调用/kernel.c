#include "trapframe.h"
#include "trapframe_offsets.h"

#define UART0_BASE       0x10000000UL
#define UART_THR         0
#define UART_LSR         5
#define UART_LSR_TX_IDLE 0x20
#define SIFIVE_TEST      0x00100000UL
#define FINISHER_FAIL    0x3333U
#define FINISHER_PASS    0x5555U

#define SSTATUS_SPP      (1UL << 8)
#define SSTATUS_SPIE     (1UL << 5)
#define SCAUSE_ILLEGAL   2UL
#define SCAUSE_U_ECALL   8UL
#define INSN_CSRR_A0_SSTATUS 0x10002573U

#define SYS_ADD_ONE          1UL
#define SYS_CHECK_REGISTERS  2UL
#define SYS_CHECK_UNKNOWN    3UL
#define SYS_CHECK_ILLEGAL    4UL
#define SYS_FINISH           5UL
#define SYS_FAIL             6UL

#define OFFSETOF(type, member) __builtin_offsetof(type, member)
#define CHECK_OFFSET(member, expected) \
    _Static_assert(OFFSETOF(struct trapframe, member) == (expected), \
                   "trapframe offset mismatch: " #member)

CHECK_OFFSET(ra, TF_RA);
CHECK_OFFSET(sp, TF_SP);
CHECK_OFFSET(gp, TF_GP);
CHECK_OFFSET(tp, TF_TP);
CHECK_OFFSET(t0, TF_T0);
CHECK_OFFSET(t1, TF_T1);
CHECK_OFFSET(t2, TF_T2);
CHECK_OFFSET(s0, TF_S0);
CHECK_OFFSET(s1, TF_S1);
CHECK_OFFSET(a0, TF_A0);
CHECK_OFFSET(a1, TF_A1);
CHECK_OFFSET(a2, TF_A2);
CHECK_OFFSET(a3, TF_A3);
CHECK_OFFSET(a4, TF_A4);
CHECK_OFFSET(a5, TF_A5);
CHECK_OFFSET(a6, TF_A6);
CHECK_OFFSET(a7, TF_A7);
CHECK_OFFSET(s2, TF_S2);
CHECK_OFFSET(s3, TF_S3);
CHECK_OFFSET(s4, TF_S4);
CHECK_OFFSET(s5, TF_S5);
CHECK_OFFSET(s6, TF_S6);
CHECK_OFFSET(s7, TF_S7);
CHECK_OFFSET(s8, TF_S8);
CHECK_OFFSET(s9, TF_S9);
CHECK_OFFSET(s10, TF_S10);
CHECK_OFFSET(s11, TF_S11);
CHECK_OFFSET(t3, TF_T3);
CHECK_OFFSET(t4, TF_T4);
CHECK_OFFSET(t5, TF_T5);
CHECK_OFFSET(t6, TF_T6);
CHECK_OFFSET(sepc, TF_SEPC);
CHECK_OFFSET(scause, TF_SCAUSE);
CHECK_OFFSET(stval, TF_STVAL);
_Static_assert(sizeof(struct trapframe) == TF_SIZE, "trapframe size mismatch");

extern char supervisor_trap_entry[];
extern char trapframe_area[];
extern char user_start[];
extern char user_stack_top[];
extern struct trapframe user_snapshot;

static volatile u64 normal_seen;
static volatile u64 registers_seen;
static volatile u64 unknown_seen;
static volatile u64 unknown_checked;
static volatile u64 illegal_seen;
static volatile u64 illegal_checked;

static inline u64 csr_read_mcause(void) {
    u64 value;
    __asm__ volatile("csrr %0, mcause" : "=r"(value));
    return value;
}

static inline u64 csr_read_mepc(void) {
    u64 value;
    __asm__ volatile("csrr %0, mepc" : "=r"(value));
    return value;
}

static inline u64 csr_read_mtval(void) {
    u64 value;
    __asm__ volatile("csrr %0, mtval" : "=r"(value));
    return value;
}

static inline u64 csr_read_sstatus(void) {
    u64 value;
    __asm__ volatile("csrr %0, sstatus" : "=r"(value));
    return value;
}

static inline void csr_write_satp(u64 value) {
    __asm__ volatile("csrw satp, %0" : : "r"(value) : "memory");
}

static inline void csr_write_stvec(u64 value) {
    __asm__ volatile("csrw stvec, %0" : : "r"(value) : "memory");
}

static inline void csr_write_sscratch(u64 value) {
    __asm__ volatile("csrw sscratch, %0" : : "r"(value) : "memory");
}

static inline void csr_write_sepc(u64 value) {
    __asm__ volatile("csrw sepc, %0" : : "r"(value) : "memory");
}

static inline void csr_write_sstatus(u64 value) {
    __asm__ volatile("csrw sstatus, %0" : : "r"(value) : "memory");
}

static void uart_putc(char ch) {
    volatile unsigned char *uart = (volatile unsigned char *)UART0_BASE;
    while ((uart[UART_LSR] & UART_LSR_TX_IDLE) == 0) {
    }
    uart[UART_THR] = (unsigned char)ch;
}

static void putstr(const char *text) {
    while (*text != '\0') {
        uart_putc(*text++);
    }
}

static void put_u64(u64 value) {
    char digits[21];
    unsigned int count = 0;
    if (value == 0) {
        uart_putc('0');
        return;
    }
    while (value != 0) {
        digits[count++] = (char)('0' + value % 10);
        value /= 10;
    }
    while (count != 0) {
        uart_putc(digits[--count]);
    }
}

static void put_i64(i64 value) {
    if (value < 0) {
        uart_putc('-');
        put_u64((u64)(-value));
    } else {
        put_u64((u64)value);
    }
}

static void put_hex(u64 value) {
    static const char hex[] = "0123456789abcdef";
    int shift;
    putstr("0x");
    for (shift = 60; shift >= 0; shift -= 4) {
        uart_putc(hex[(value >> (unsigned int)shift) & 0xf]);
    }
}

__attribute__((noreturn)) void qemu_fail(u64 code) {
    volatile unsigned int *finisher = (volatile unsigned int *)SIFIVE_TEST;
    *finisher = ((unsigned int)(code & 0xffffUL) << 16) | FINISHER_FAIL;
    for (;;) {
        __asm__ volatile("wfi");
    }
}

static __attribute__((noreturn)) void qemu_pass(void) {
    volatile unsigned int *finisher = (volatile unsigned int *)SIFIVE_TEST;
    *finisher = FINISHER_PASS;
    for (;;) {
        __asm__ volatile("wfi");
    }
}

void machine_banner(void) {
    putstr("MODE M: boot hart=0, delegate causes 2 and 8\n");
}

__attribute__((noreturn)) void machine_trap(void) {
    putstr("RESULT FAIL: unexpected M trap mcause=");
    put_hex(csr_read_mcause());
    putstr(" mepc=");
    put_hex(csr_read_mepc());
    putstr(" mtval=");
    put_hex(csr_read_mtval());
    uart_putc('\n');
    qemu_fail(0x10);
}

__attribute__((noreturn)) void supervisor_main(void) {
    u64 status;
    putstr("MODE S: stvec/sscratch installed, preparing sret\n");
    csr_write_satp(0);
    csr_write_stvec((u64)supervisor_trap_entry);
    csr_write_sscratch((u64)trapframe_area);
    csr_write_sepc((u64)user_start);
    status = csr_read_sstatus();
    status &= ~SSTATUS_SPP;
    status |= SSTATUS_SPIE;
    csr_write_sstatus(status);
    putstr("MODE U: entered by sret\n");
    __asm__ volatile("sret");
    qemu_fail(0x11);
}

static void print_trap(const char *kind, const struct trapframe *tf) {
    putstr("TRAP kind=");
    putstr(kind);
    putstr(" scause=");
    put_u64(tf->scause);
    putstr(" sepc=");
    put_hex(tf->sepc);
    putstr(" stval=");
    put_hex(tf->stval);
    putstr(" origin.SPP=0 saved.SPIE=1");
    uart_putc('\n');
}

static int register_snapshot_valid(void) {
    const struct trapframe *r = &user_snapshot;
    return r->ra == 101 && r->sp == (u64)user_stack_top && r->gp == 103 &&
           r->tp == 104 && r->t0 == 105 && r->t1 == 106 && r->t2 == 107 &&
           r->s0 == 108 && r->s1 == 109 && r->a0 == 42 && r->a1 == 111 &&
           r->a2 == 112 && r->a3 == 113 && r->a4 == 114 && r->a5 == 115 &&
           r->a6 == 116 && r->a7 == 1 && r->s2 == 118 && r->s3 == 119 &&
           r->s4 == 120 && r->s5 == 121 && r->s6 == 122 && r->s7 == 123 &&
           r->s8 == 124 && r->s9 == 125 && r->s10 == 126 && r->s11 == 127 &&
           r->t3 == 128 && r->t4 == 129 && r->t5 == 130 && r->t6 == 131;
}

static void fail_from_user(u64 code) {
    putstr("RESULT FAIL: user-check code=");
    put_u64(code);
    uart_putc('\n');
    qemu_fail(0x20 + code);
}

struct trapframe *supervisor_trap(struct trapframe *tf) {
    u64 number;
    i64 argument;

    if ((csr_read_sstatus() & (SSTATUS_SPP | SSTATUS_SPIE)) != SSTATUS_SPIE) {
        putstr("RESULT FAIL: expected trap entry SPP=0 and SPIE=1\n");
        qemu_fail(0x30);
    }

    if (tf->scause == SCAUSE_U_ECALL) {
        print_trap("ecall", tf);
        tf->sepc += 4;
        number = tf->a7;
        argument = (i64)tf->a0;

        if (number == SYS_ADD_ONE) {
            tf->a0 = (u64)(argument + 1);
            normal_seen = 1;
            putstr("SYSCALL number=1 arg0=");
            put_i64(argument);
            putstr(" return=");
            put_i64((i64)tf->a0);
            uart_putc('\n');
        } else if (number == SYS_CHECK_REGISTERS) {
            if (argument != 1 || normal_seen == 0 || !register_snapshot_valid()) {
                fail_from_user(0x41);
            }
            registers_seen = 1;
            tf->a0 = 0;
            putstr("CHECK registers=PASS\n");
        } else if (number == SYS_CHECK_UNKNOWN) {
            if (argument != 1 || unknown_seen == 0) {
                fail_from_user(0x42);
            }
            unknown_checked = 1;
            tf->a0 = 0;
            putstr("CHECK unknown-return=PASS\n");
        } else if (number == SYS_CHECK_ILLEGAL) {
            if (argument != 1 || illegal_seen == 0) {
                fail_from_user(0x43);
            }
            illegal_checked = 1;
            tf->a0 = 0;
            putstr("CHECK illegal-recovery=PASS\n");
        } else if (number == SYS_FINISH) {
            if (normal_seen && registers_seen && unknown_seen &&
                unknown_checked && illegal_seen && illegal_checked) {
                putstr("RESULT PASS\n");
                qemu_pass();
            }
            fail_from_user(0x44);
        } else if (number == SYS_FAIL) {
            fail_from_user((u64)argument);
        } else {
            unknown_seen = 1;
            tf->a0 = (u64)(i64)-38;
            putstr("SYSCALL number=");
            put_u64(number);
            putstr(" arg0=");
            put_i64(argument);
            putstr(" return=-38 status=unknown\n");
        }
        return tf;
    }

    if (tf->scause == SCAUSE_ILLEGAL) {
        unsigned int instruction = *(const volatile unsigned int *)tf->sepc;
        print_trap("illegal", tf);
        if (instruction != INSN_CSRR_A0_SSTATUS) {
            putstr("RESULT FAIL: illegal instruction was not CSR probe, insn=");
            put_hex(instruction);
            uart_putc('\n');
            qemu_fail(0x50);
        }
        illegal_seen = 1;
        tf->sepc += 4;
        tf->a0 = (u64)(i64)-2;
        putstr("ILLEGAL instruction=csrr-a0-sstatus action=skip return=-2\n");
        return tf;
    }

    putstr("RESULT FAIL: unexpected S trap scause=");
    put_hex(tf->scause);
    putstr(" sepc=");
    put_hex(tf->sepc);
    putstr(" stval=");
    put_hex(tf->stval);
    uart_putc('\n');
    qemu_fail(0x60);
}
