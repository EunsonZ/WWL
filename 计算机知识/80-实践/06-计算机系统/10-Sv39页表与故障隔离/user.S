    .section .user.text, "ax"
    .align  4
    .globl  user_start
user_start:
    la      sp, user_stack_top
    li      s0, 0x1122334455667788
    li      s1, 0x8877665544332211

    # A real call/return proves that the U=1, X=1 alias is fetching code.
    call    user_exec_probe
    li      t0, 0x123
    bne     a2, t0, user_fail

    # Both addresses below are PC-relative. Because this code executes through
    # a fixed-offset alias, the linked physical symbols become low user VAs.
    la      t1, user_data_backing
    ld      t2, 0(t1)
    li      t3, 0x1111222233334444
    bne     t2, t3, user_fail
    li      t2, 0x5555666677778888
    sd      t2, 0(t1)
    ld      a0, 0(t1)
    li      a7, 1
    ecall
    bnez    a0, user_fail

    # S has now cleared W and fenced this VA. The store itself must trap.
    li      t2, 0xa5a5a5a5a5a5a5a5
    .globl  user_store_fault_insn
user_store_fault_insn:
    sd      t2, 0(t1)
    j       user_fail
    .globl  user_after_store_fault
user_after_store_fault:
    li      t0, -15
    bne     a0, t0, user_fail
    ld      t2, 0(t1)
    li      t3, 0x5555666677778888
    bne     t2, t3, user_fail
    li      a7, 2
    ecall
    bnez    a0, user_fail

    # This address is identity mapped only as an S page (PTE.U=0).
    li      t1, 0x80013000
    .globl  user_load_fault_insn
user_load_fault_insn:
    ld      a0, 0(t1)
    j       user_fail
    .globl  user_after_load_fault
user_after_load_fault:
    li      t0, -13
    bne     a0, t0, user_fail
    li      a7, 3
    ecall
    bnez    a0, user_fail

    # PTE.R=1 but PTE.X=0. The JALR executes; fetching its target must fault.
    la      t1, user_nx_target
    jalr    ra, t1, 0
    j       user_fail
    .globl  user_after_exec_fault
user_after_exec_fault:
    li      t0, -12
    bne     a0, t0, user_fail
    li      a7, 4
    ecall
    j       user_fail

user_exec_probe:
    li      a2, 0x123
    ret

user_fail:
    li      a7, 7
    ecall
    j       user_fail

    .section .user.data, "aw"
    .align  3
    .globl  user_data_backing
user_data_backing:
    .dword  0x1111222233334444

    .section .user.nx, "ax"
    .align  4
    .globl  user_nx_target
user_nx_target:
    li      a0, 99
    ret

    .section .kernel.secret, "aw"
    .align  3
    .globl  kernel_secret
kernel_secret:
    .dword  0xcafebabedeadbeef
