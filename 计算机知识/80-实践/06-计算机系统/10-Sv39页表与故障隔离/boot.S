    .section .text.start, "ax"
    .align  4
    .globl  _start
_start:
    csrr    t0, mhartid
    bnez    t0, .Lpark

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

    # A single broad PMP TOR region allows the teaching S/U payload to access
    # RAM and virt MMIO. Sv39 remains the U/S permission boundary under test.
    li      t0, -1
    csrw    pmpaddr0, t0
    li      t0, 0x0f
    csrw    pmpcfg0, t0

    # U ecall plus instruction/load/store page faults are handled in S mode.
    li      t0, ((1 << 8) | (1 << 12) | (1 << 13) | (1 << 15))
    csrw    medeleg, t0
    csrw    mideleg, zero

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

    .globl  machine_trap_entry
machine_trap_entry:
    la      sp, m_stack_top
    call    machine_trap

.Lpark:
    wfi
    j       .Lpark
