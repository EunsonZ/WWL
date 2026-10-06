#include "trapframe.h"

typedef unsigned int u32;
typedef unsigned char u8;

extern char supervisor_trap_entry[];
extern char user_start[];
extern char user_store_fault_insn[];
extern char user_after_store_fault[];
extern char user_load_fault_insn[];
extern char user_after_load_fault[];
extern char user_after_exec_fault[];
extern char user_nx_target[];
extern char user_data_backing[];
extern char kernel_secret[];
extern char root_page_table[];
extern char user_l1_page_table[];
extern char user_l0_page_table[];
extern char kernel_l1_page_table[];
extern char kernel_l0_page_table[];
extern char trapframe_area[];
extern char kernel_end[];

enum {
    PTE_V = 1UL << 0,
    PTE_R = 1UL << 1,
    PTE_W = 1UL << 2,
    PTE_X = 1UL << 3,
    PTE_U = 1UL << 4,
    PTE_G = 1UL << 5,
    PTE_A = 1UL << 6,
    PTE_D = 1UL << 7,
};

enum stage {
    STAGE_ALIAS = 0,
    STAGE_EXPECT_STORE,
    STAGE_STORE_RETURNED,
    STAGE_EXPECT_LOAD,
    STAGE_LOAD_RETURNED,
    STAGE_EXPECT_EXEC,
    STAGE_EXEC_RETURNED,
};

#define UART0 0x10000000UL
#define TEST_FINISHER 0x00100000UL
#define USER_VA_BASE 0x40000000UL
#define USER_PA_BASE 0x80010000UL
#define USER_ALIAS_DELTA (USER_PA_BASE - USER_VA_BASE)
#define USER_DATA_VA 0x40001000UL
#define USER_NX_VA 0x40002000UL
#define USER_STACK_VA 0x40005000UL
#define KERNEL_SECRET_VA 0x80013000UL
#define DATA_INITIAL 0x1111222233334444UL
#define DATA_WRITTEN 0x5555666677778888UL
#define SECRET_VALUE 0xcafebabedeadbeefUL
#define CANARY_S0 0x1122334455667788UL
#define CANARY_S1 0x8877665544332211UL

static volatile u8 *const uart = (volatile u8 *)UART0;
static volatile u32 *const finisher = (volatile u32 *)TEST_FINISHER;
static enum stage current_stage = STAGE_ALIAS;

_Static_assert(sizeof(struct trapframe) == 272, "trap frame assembly/C mismatch");

static inline u64 csr_read_satp(void) {
    u64 value;
    __asm__ volatile("csrr %0, satp" : "=r"(value));
    return value;
}

static inline u64 csr_read_sstatus(void) {
    u64 value;
    __asm__ volatile("csrr %0, sstatus" : "=r"(value));
    return value;
}

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

void machine_banner(void) {
    puts("MODE M: boot hart=0 delegate=0x000000000000b100\n");
}

__attribute__((noreturn)) void machine_trap(void) {
    puts("MACHINE TRAP mcause=");
    put_hex(csr_read_mcause());
    puts(" mepc=");
    put_hex(csr_read_mepc());
    puts(" mtval=");
    put_hex(csr_read_mtval());
    puts("\n");
    qemu_fail(0xe0);
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
        qemu_fail(0xe1);
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

static void map_kernel_identity(volatile u64 *l0) {
    for (u64 pa = 0x80000000UL; pa < (u64)kernel_end; pa += 4096) {
        u64 index = (pa >> 12) & 0x1ffUL;
        l0[index] = leaf_pte(pa, PTE_R | PTE_W | PTE_X | PTE_A | PTE_D);
    }
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

    #define VPN2(va) (((u64)(va) >> 30) & 0x1ffUL)
    #define VPN1(va) (((u64)(va) >> 21) & 0x1ffUL)
    #define VPN0(va) (((u64)(va) >> 12) & 0x1ffUL)

    /* Root entry 0 is a naturally aligned 1 GiB U=0 MMIO leaf. */
    root[0] = leaf_pte(0, PTE_R | PTE_W | PTE_A | PTE_D);

    root[VPN2(USER_VA_BASE)] = pointer_pte(user_l1);
    user_l1[VPN1(USER_VA_BASE)] = pointer_pte(user_l0);
    user_l0[VPN0(USER_VA_BASE)] =
        leaf_pte(USER_PA_BASE, PTE_R | PTE_X | PTE_U | PTE_A);
    user_l0[VPN0(USER_DATA_VA)] =
        leaf_pte((u64)user_data_backing,
                 PTE_R | PTE_W | PTE_U | PTE_A | PTE_D);
    user_l0[VPN0(USER_NX_VA)] =
        leaf_pte((u64)user_nx_target, PTE_R | PTE_U | PTE_A);
    user_l0[VPN0(USER_STACK_VA)] =
        leaf_pte(0x80015000UL, PTE_R | PTE_W | PTE_U | PTE_A | PTE_D);

    root[VPN2(0x80000000UL)] = pointer_pte(kernel_l1);
    kernel_l1[VPN1(0x80000000UL)] = pointer_pte(kernel_l0);
    map_kernel_identity(kernel_l0);

    #undef VPN2
    #undef VPN1
    #undef VPN0
}

struct walk_result {
    u64 l2;
    u64 l1;
    u64 l0;
    u64 pa;
};

static struct walk_result walk(u64 va) {
    volatile u64 *level = (volatile u64 *)root_page_table;
    struct walk_result result;
    result.l2 = level[(va >> 30) & 0x1ffUL];
    level = (volatile u64 *)pte_to_pa(result.l2);
    result.l1 = level[(va >> 21) & 0x1ffUL];
    level = (volatile u64 *)pte_to_pa(result.l1);
    result.l0 = level[(va >> 12) & 0x1ffUL];
    result.pa = pte_to_pa(result.l0) | (va & 0xfffUL);
    return result;
}

static void print_walk(void) {
    struct walk_result value = walk(USER_DATA_VA);
    puts("WALK va=");
    put_hex(USER_DATA_VA);
    puts(" vpn2=1 vpn1=0 vpn0=1 offset=0 l2=");
    put_hex(value.l2);
    puts(" l1=");
    put_hex(value.l1);
    puts(" l0=");
    put_hex(value.l0);
    puts(" pa=");
    put_hex(value.pa);
    puts(" flags=VRWUAD\n");
}

static void require_canaries(const struct trapframe *tf, u64 code) {
    if (tf->s0 != CANARY_S0 || tf->s1 != CANARY_S1) {
        qemu_fail(code);
    }
}

static void print_fault(const char *kind, const struct trapframe *tf,
                        const char *action) {
    puts("FAULT kind=");
    puts(kind);
    puts(" scause=");
    put_uint(tf->scause);
    puts(" sepc=");
    put_hex(tf->sepc);
    puts(" stval=");
    put_hex(tf->stval);
    puts(" action=");
    puts(action);
    puts("\n");
}

static struct trapframe *handle_ecall(struct trapframe *tf) {
    if (tf->scause != 8 || (tf->sepc & 3UL) != 0) {
        qemu_fail(0x20);
    }
    require_canaries(tf, 0x21);
    puts("TRAP kind=ecall stage=");
    put_uint((u64)current_stage);
    puts(" scause=8 sepc=");
    put_hex(tf->sepc);
    puts("\n");

    if (tf->a7 == 1 && current_stage == STAGE_ALIAS) {
        volatile u64 *data = (volatile u64 *)user_data_backing;
        if (tf->a2 != 0x123 || *data != DATA_WRITTEN ||
            tf->sepc < USER_VA_BASE || tf->sepc >= USER_DATA_VA) {
            qemu_fail(0x22);
        }
        puts("ALIAS execute_va=");
        put_hex(USER_VA_BASE);
        puts(" data_va=");
        put_hex(USER_DATA_VA);
        puts(" data_pa=");
        put_hex((u64)user_data_backing);
        puts(" backing=");
        put_hex(*data);
        puts(" status=PASS\n");

        volatile u64 *user_l0 = (volatile u64 *)user_l0_page_table;
        u64 index = (USER_DATA_VA >> 12) & 0x1ffUL;
        u64 before = user_l0[index];
        user_l0[index] = before & ~PTE_W;
        __asm__ volatile("sfence.vma %0, zero" : : "r"(USER_DATA_VA) : "memory");
        puts("PTE UPDATE va=");
        put_hex(USER_DATA_VA);
        puts(" before=");
        put_hex(before);
        puts(" after=");
        put_hex(user_l0[index]);
        puts(" sfence.vma=address-asid-all\n");
        current_stage = STAGE_EXPECT_STORE;
        tf->a0 = 0;
        tf->sepc += 4;
        return tf;
    }

    if (tf->a7 == 2 && current_stage == STAGE_STORE_RETURNED) {
        if (*(volatile u64 *)user_data_backing != DATA_WRITTEN) {
            qemu_fail(0x23);
        }
        puts("CHECK store-denied=PASS backing=");
        put_hex(*(volatile u64 *)user_data_backing);
        puts("\n");
        current_stage = STAGE_EXPECT_LOAD;
        tf->a0 = 0;
        tf->sepc += 4;
        return tf;
    }

    if (tf->a7 == 3 && current_stage == STAGE_LOAD_RETURNED) {
        if (*(volatile u64 *)kernel_secret != SECRET_VALUE) {
            qemu_fail(0x24);
        }
        puts("CHECK load-u0-denied=PASS secret=");
        put_hex(*(volatile u64 *)kernel_secret);
        puts("\n");
        current_stage = STAGE_EXPECT_EXEC;
        tf->a0 = 0;
        tf->sepc += 4;
        return tf;
    }

    if (tf->a7 == 4 && current_stage == STAGE_EXEC_RETURNED) {
        puts("CHECK execute-nx-denied=PASS\n");
        qemu_pass();
    }

    qemu_fail(tf->a7 == 7 ? 0x27 : 0x26);
}

struct trapframe *supervisor_trap(struct trapframe *tf) {
    if (tf->scause == 8) {
        return handle_ecall(tf);
    }

    require_canaries(tf, 0x30);
    if (current_stage == STAGE_EXPECT_STORE && tf->scause == 15 &&
        tf->stval == USER_DATA_VA &&
        tf->sepc == user_va(user_store_fault_insn) &&
        *(volatile u64 *)user_data_backing == DATA_WRITTEN) {
        print_fault("store", tf, "redirect-explicit-label");
        tf->a0 = (u64)(i64)-15;
        tf->sepc = user_va(user_after_store_fault);
        current_stage = STAGE_STORE_RETURNED;
        return tf;
    }

    if (current_stage == STAGE_EXPECT_LOAD && tf->scause == 13 &&
        tf->stval == KERNEL_SECRET_VA &&
        tf->sepc == user_va(user_load_fault_insn) &&
        *(volatile u64 *)kernel_secret == SECRET_VALUE) {
        print_fault("load", tf, "redirect-explicit-label");
        tf->a0 = (u64)(i64)-13;
        tf->sepc = user_va(user_after_load_fault);
        current_stage = STAGE_LOAD_RETURNED;
        return tf;
    }

    if (current_stage == STAGE_EXPECT_EXEC && tf->scause == 12 &&
        tf->stval == USER_NX_VA && tf->sepc == USER_NX_VA) {
        print_fault("instruction", tf, "redirect-explicit-label");
        tf->a0 = (u64)(i64)-12;
        tf->sepc = user_va(user_after_exec_fault);
        current_stage = STAGE_EXEC_RETURNED;
        return tf;
    }

    puts("UNEXPECTED stage=");
    put_uint((u64)current_stage);
    puts(" scause=");
    put_uint(tf->scause);
    puts(" sepc=");
    put_hex(tf->sepc);
    puts(" stval=");
    put_hex(tf->stval);
    puts("\n");
    qemu_fail(0x3f);
}

__attribute__((noreturn)) void supervisor_main(void) {
    puts("MODE S: build Sv39 tables\n");
    build_page_tables();

    puts("PAGE_TABLE root_pa=");
    put_hex((u64)root_page_table);
    puts(" entries=512 bytes=4096 levels=3\n");
    print_walk();

    u64 root_ppn = (u64)root_page_table >> 12;
    u64 requested_satp = (8UL << 60) | root_ppn;
    __asm__ volatile("fence rw, rw" : : : "memory");
    __asm__ volatile("csrw satp, %0" : : "r"(requested_satp) : "memory");
    __asm__ volatile("sfence.vma zero, zero" : : : "memory");
    u64 readback = csr_read_satp();
    if ((readback >> 60) != 8 || (readback & ((1UL << 44) - 1)) != root_ppn) {
        qemu_fail(0x40);
    }
    puts("SATP readback=");
    put_hex(readback);
    puts(" mode=8 root_ppn=");
    put_hex(root_ppn);
    puts(" sfence.vma=global\n");

    u64 status = csr_read_sstatus();
    status &= ~((1UL << 8) | (1UL << 18) | (1UL << 19) | (1UL << 1));
    status |= 1UL << 5;
    __asm__ volatile("csrw sstatus, %0" : : "r"(status));
    __asm__ volatile("csrw stvec, %0" : : "r"((u64)supervisor_trap_entry));
    __asm__ volatile("csrw sscratch, %0" : : "r"((u64)trapframe_area));
    __asm__ volatile("csrw sepc, %0" : : "r"(USER_VA_BASE));
    puts("POLICY SUM=0 MXR=0 A=pre-set D=pre-set\n");
    puts("MODE U: entry_va=");
    put_hex(USER_VA_BASE);
    puts(" entry_pa=");
    put_hex(USER_PA_BASE);
    puts(" stack_va=0x0000000040005000\n");
    __asm__ volatile("sret");
    __builtin_unreachable();
}
