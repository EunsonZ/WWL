#ifndef SV39_TRAPFRAME_H
#define SV39_TRAPFRAME_H

typedef unsigned long u64;
typedef signed long i64;

struct trapframe {
    u64 ra;
    u64 sp;
    u64 gp;
    u64 tp;
    u64 t0;
    u64 t1;
    u64 t2;
    u64 s0;
    u64 s1;
    u64 a0;
    u64 a1;
    u64 a2;
    u64 a3;
    u64 a4;
    u64 a5;
    u64 a6;
    u64 a7;
    u64 s2;
    u64 s3;
    u64 s4;
    u64 s5;
    u64 s6;
    u64 s7;
    u64 s8;
    u64 s9;
    u64 s10;
    u64 s11;
    u64 t3;
    u64 t4;
    u64 t5;
    u64 t6;
    u64 sepc;
    u64 scause;
    u64 stval;
};

#endif
