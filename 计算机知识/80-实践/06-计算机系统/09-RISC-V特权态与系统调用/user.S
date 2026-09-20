#include "trapframe_offsets.h"

    .section .text, "ax"
    .align  4
    .globl  user_start
user_start:
    la      sp, user_stack_top

    # Assign every observable integer register (except sp/a0/a7, which have
    # protocol values) a distinct x-register-number sentinel.
    li      ra, 101
    li      gp, 103
    li      tp, 104
    li      t0, 105
    li      t1, 106
    li      t2, 107
    li      s0, 108
    li      s1, 109
    li      a1, 111
    li      a2, 112
    li      a3, 113
    li      a4, 114
    li      a5, 115
    li      a6, 116
    li      s2, 118
    li      s3, 119
    li      s4, 120
    li      s5, 121
    li      s6, 122
    li      s7, 123
    li      s8, 124
    li      s9, 125
    li      s10, 126
    li      s11, 127
    li      t3, 128
    li      t4, 129
    li      t5, 130
    li      t6, 131
    li      a0, 41
    li      a7, 1
    ecall

    # Snapshot the returned register file before using any register for a
    # comparison. Preserve t6 temporarily before reusing it as the base.
    sd      t6, -8(sp)
    la      t6, user_snapshot
    sd      ra, TF_RA(t6)
    sd      sp, TF_SP(t6)
    sd      gp, TF_GP(t6)
    sd      tp, TF_TP(t6)
    sd      t0, TF_T0(t6)
    sd      t1, TF_T1(t6)
    sd      t2, TF_T2(t6)
    sd      s0, TF_S0(t6)
    sd      s1, TF_S1(t6)
    sd      a0, TF_A0(t6)
    sd      a1, TF_A1(t6)
    sd      a2, TF_A2(t6)
    sd      a3, TF_A3(t6)
    sd      a4, TF_A4(t6)
    sd      a5, TF_A5(t6)
    sd      a6, TF_A6(t6)
    sd      a7, TF_A7(t6)
    sd      s2, TF_S2(t6)
    sd      s3, TF_S3(t6)
    sd      s4, TF_S4(t6)
    sd      s5, TF_S5(t6)
    sd      s6, TF_S6(t6)
    sd      s7, TF_S7(t6)
    sd      s8, TF_S8(t6)
    sd      s9, TF_S9(t6)
    sd      s10, TF_S10(t6)
    sd      s11, TF_S11(t6)
    sd      t3, TF_T3(t6)
    sd      t4, TF_T4(t6)
    sd      t5, TF_T5(t6)
    ld      t5, -8(sp)
    sd      t5, TF_T6(t6)

    li      a0, 1
    li      a7, 2
    ecall

    # Unknown number: this is still scause=8 and reaches the syscall
    # dispatcher. Only the dispatch result is an error.
    li      a0, 7
    li      a7, 99
    ecall
    li      t6, -38
    bne     a0, t6, .Lfail_unknown
    li      a0, 1
    li      a7, 3
    ecall

    # sstatus is an S-mode CSR. Reading it in U mode is not an ecall; it raises
    # illegal-instruction scause=2. The handler skips this known 4-byte probe.
    csrr    a0, sstatus
    li      t6, -2
    bne     a0, t6, .Lfail_illegal
    li      a0, 1
    li      a7, 4
    ecall

    li      a0, 0
    li      a7, 5
    ecall
    j       .Lfail_returned

.Lfail_normal:
    li      a0, 1
    j       .Lreport_fail
.Lfail_register:
    li      a0, 2
    j       .Lreport_fail
.Lfail_unknown:
    li      a0, 3
    j       .Lreport_fail
.Lfail_illegal:
    li      a0, 4
    j       .Lreport_fail
.Lfail_returned:
    li      a0, 5
.Lreport_fail:
    li      a7, 6
    ecall
    j       .Lfail_returned

    .section .bss, "aw", @nobits
    .balign 16
    .globl  user_snapshot
user_snapshot:
    .skip   TF_SIZE
