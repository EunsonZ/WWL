    .section .text.start, "ax"
    .align  4
    .globl  _start
_start:
    # This experiment runs exactly one hart. Park any unexpected extra hart.
    csrr    t0, mhartid
    bnez    t0, .Lpark

    # The ELF loader normally zeroes .bss. Do it explicitly so the contract is
    # visible and does not depend on that convenience.
    la      t0, __bss_start
    la      t1, __bss_end
.Lzero_bss:
    bgeu    t0, t1, .Lbss_done
    sd      zero, 0(t0)
    addi    t0, t0, 8
    j       .Lzero_bss
.Lbss_done:
    la      sp, m_stack_top
    la      t0, machine_trap_entry
    csrw    mtvec, t0
    call    machine_banner

    # Let S/U execute, load, store, and fetch throughout the QEMU virt address
    # space. This is deliberately broad because the lab does not build page
    # tables; README.md states the resulting isolation limit.
    li      t0, -1
    csrw    pmpaddr0, t0
    li      t0, 0x0f              # TOR, read/write/execute
    csrw    pmpcfg0, t0

    # Delegate only the two U-mode synchronous exceptions used by the lab:
    # illegal instruction (2) and environment call from U-mode (8).
    li      t0, ((1 << 2) | (1 << 8))
    csrw    medeleg, t0
    csrw    mideleg, zero

    la      t0, supervisor_entry
    csrw    mepc, t0
    csrr    t0, mstatus
    li      t1, (3 << 11)
    not     t1, t1
    and     t0, t0, t1
    li      t1, (1 << 11)         # MPP = S
    or      t0, t0, t1
    csrw    mstatus, t0
    mret

supervisor_entry:
    la      sp, s_stack_top
    call    supervisor_main
    j       .Lfatal_return

    .globl  machine_trap_entry
machine_trap_entry:
    la      sp, m_stack_top
    call    machine_trap

.Lfatal_return:
    li      a0, 0x7f
    call    qemu_fail

.Lpark:
    wfi
    j       .Lpark
