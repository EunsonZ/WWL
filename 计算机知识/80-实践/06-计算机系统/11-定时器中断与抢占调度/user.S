    .section .user0.text, "ax"
    .align  4
    .globl user0_start
user0_start:
    li      s0, 0x1111222233334444
    li      s2, 0
    li      a5, 0x13579bdf2468ace0
    li      t5, 0x0f1e2d3c4b5a6978
    li      t0, 0xa0a0b0b0c0c0d0d0
    sd      t0, -8(sp)
    sd      zero, -16(sp)
    .globl user0_hot_loop
user0_hot_loop:
    addi    s1, s1, 1
    ld      t0, -16(sp)
    addi    t0, t0, 1
    sd      t0, -16(sp)
    xor     t1, t1, s1
    add     t2, t2, t1
    j       user0_hot_loop
    .globl user0_hot_loop_end
user0_hot_loop_end:
    nop

    .globl user0_exit
user0_exit:
    li      a0, 0
    mv      a1, s1
    ld      a2, -16(sp)
    li      a7, 1
    .globl user0_exit_ecall
user0_exit_ecall:
    ecall
    li      a7, 7
    ecall

    .section .user.data, "aw"
    .align 3
user_shared_anchor:
    .dword 0

    .section .user1.text, "ax"
    .align  4
    .globl user1_start
user1_start:
    li      s0, 0x5555666677778888
    li      s2, 1
    li      a5, 0x02468ace13579bdf
    li      t5, 0x89abcdef01234567
    li      t0, 0xa1a1b1b1c1c1d1d1
    sd      t0, -8(sp)
    sd      zero, -16(sp)
    .globl user1_hot_loop
user1_hot_loop:
    addi    s1, s1, 1
    ld      t0, -16(sp)
    addi    t0, t0, 1
    sd      t0, -16(sp)
    xor     t1, t1, s1
    add     t2, t2, t1
    j       user1_hot_loop
    .globl user1_hot_loop_end
user1_hot_loop_end:
    nop

    .globl user1_exit
user1_exit:
    li      a0, 1
    mv      a1, s1
    ld      a2, -16(sp)
    li      a7, 1
    .globl user1_exit_ecall
user1_exit_ecall:
    ecall
    li      a7, 7
    ecall
