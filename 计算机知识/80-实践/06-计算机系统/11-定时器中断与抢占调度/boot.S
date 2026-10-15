    .section .text.start, "ax"
    .align  4
    .globl  _start
_start:
    csrr    t0, mhartid
    bnez    t0, .Lpark

    la      t0, __bss_start
    la      t1, __bss_end
.Lzero_bss:
    bgeu    t0, t1, .Lzero_runtime_begin
    sd      zero, 0(t0)
    addi    t0, t0, 8
    j       .Lzero_bss
.Lzero_runtime_begin:
    la      t0, __runtime_start
    la      t1, __runtime_end
.Lzero_runtime:
    bgeu    t0, t1, .Lzero_done
    sd      zero, 0(t0)
    addi    t0, t0, 8
    j       .Lzero_runtime
.Lzero_done:
    la      sp, m_stack_top
    la      t0, machine_trap_entry
    csrw    mtvec, t0

    li      t0, -1
    csrw    pmpaddr0, t0
    li      t0, 0x0f
    csrw    pmpcfg0, t0

    # Sstc: enable S-mode stimecmp, allow S time/timer CSR access, and
    # delegate supervisor timer interrupt (cause 5). MTIE remains disabled.
    li      t0, (1 << 63)
    csrs    0x30a, t0             # menvcfg.STCE
    li      t0, (1 << 1)
    csrs    mcounteren, t0        # mcounteren.TM
    li      t0, (1 << 5)
    csrw    mideleg, t0
    csrw    mie, zero
    li      t0, ((1 << 8) | (1 << 12) | (1 << 13) | (1 << 15))
    csrw    medeleg, t0

    csrr    a0, 0x30a
    csrr    a1, mcounteren
    csrr    a2, mideleg
    csrr    a3, mie
    call    machine_banner

    la      t0, supervisor_entry
    csrw    mepc, t0
    csrr    t0, mstatus
    li      t1, (3 << 11)
    not     t1, t1
    and     t0, t0, t1
    li      t1, (1 << 11)
    or      t0, t0, t1
    csrw    mstatus, t0
    mret

supervisor_entry:
    la      sp, s_stack_top
    call    supervisor_main
    li      a0, 0x7f
    call    qemu_fail

    .globl machine_trap_entry
machine_trap_entry:
    la      sp, m_stack_top
    call    machine_trap

.Lpark:
    wfi
    j       .Lpark
