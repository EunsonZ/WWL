---
domain: computer-science
type: explanation
prerequisites:
  - "[[计算机知识/80-实践/06-计算机系统/09-RISC-V特权态与系统调用/README|RISC-V 特权态与系统调用实验]]"
sources:
  - "RISC-V Privileged Architecture v20260120"
content_status: usable
evidence_status: partial
---

# 从 `ecall` 到 `sret` 的逐指令路径

## U 态交出的不是 C 函数调用

用户代码先令 `a0=41、a7=1`，再执行 `ecall`。编号和参数是本实验 ABI；`ecall` 指令本身不认识“加一”服务，也不按这个 ABI搬参数。它只令处理器按当前特权级生成环境调用异常。因为 M 态预先设置了 `medeleg[8]`，U 态环境调用进入 S 态：`scause=8`，`sepc` 指向那条尚需决定如何恢复的 `ecall`，`sstatus.SPP=0` 记录来源为 U 态，原 `SIE` 被复制到 `SPIE`，当前 `SIE` 被清零，然后 PC 取自 `stvec`。

这里有两份状态。CSR 中的 `sepc/scause/stval/sstatus` 是硬件 trap 状态；`a0/a7` 等通用寄存器仍保留用户值，但即将被入口代码和 C 编译器使用，所以软件必须先保存。把“硬件记录返回状态”写成“硬件自动保存全部上下文”会掩盖最关键的一段入口协议。

## `sscratch` 解决入口第一步的鸡生蛋问题

刚到 `supervisor_trap_entry` 时，`sp` 仍是用户栈。S 态不能在尚未检查的用户栈上调用 C，也不能随便占用某个用户寄存器来保存地址，因为那个寄存器本身也属于待恢复状态。实验在进入 U 态前把 trapframe 地址放进 `sscratch`，第一条入口操作是：

```asm
csrrw sp, sscratch, sp
```

执行后，`sp` 指向 trapframe，`sscratch` 保存原用户 `sp`。入口立即保存其余整数寄存器；保存 `t0` 后才用 `t0` 读出 `sscratch/sepc/scause/stval`。接着它把 trapframe 指针放进 C 的 `a0`，把 `sp` 改到 16 字节对齐的独立 S 栈顶，才调用 `supervisor_trap(tf)`。

| 层次 | 进入时已有 | 软件补充 | 用途 |
| --- | --- | --- | --- |
| 硬件 trap 状态 | `sepc/scause/stval/sstatus` | 无 | 识别原因和返回条件 |
| 入口 trapframe | 用户 `x1–x31` | 汇编保存 | C 可自由使用寄存器，返回时仍能恢复 |
| S 态调用栈 | 独立 `s_stack_top` | 汇编切换 | 遵守 C ABI 对齐，不在 U 栈运行内核 C |

## 分派层只把 `a7/a0` 当数据读

C 处理器先验证 trap 来源状态，再检查 `tf->scause`。值 8 才是 U 态环境调用。它先把保存的 `sepc` 增加 4，再读 `tf->a7` 选择服务。编号 1 读取进入时的 `tf->a0=41`，把 `tf->a0=42` 写回。这里的分派可以抽象为

$$
(n, x)=(\mathrm{tf.a7},\mathrm{tf.a0}),\qquad
\mathrm{tf.a0}\leftarrow D(n,x),
$$

其中本实验只有几个教学服务，`D(1,x)=x+1`；未知 `n` 返回 -38。真实 OS 还会验证用户指针、对象、权限和并发状态，本实验故意不把那些问题藏进这个最小分派器。

## 返回顺序为何几乎是入口的逆序

C 返回 trapframe 指针后，汇编先把更新后的 `tf->sepc` 写回 CSR，并把 trapframe 地址放回 `sscratch`，为下一次 trap 做准备。随后恢复全部整数寄存器，`a0` 取到 C 写入的 42；最后恢复用户 `sp` 并执行 `sret`。`sret` 根据 `SPP=0` 回到 U 态，并令 PC 取自已经前移的 `sepc`，因此 U 代码从 `ecall` 后一条指令继续。

这个实验还做了比“输出 42”更强的检查：返回后，U 代码在改动寄存器之前把 `ra/sp/gp/tp/t0–t6/s0–s11/a0–a7` 全部写入快照；下一次 `ecall` 让 S 态逐项核对预设值。只有 `a0` 预期变为 42。`CHECK registers=PASS` 因而同时约束了保存范围、偏移一致性、S 栈调用和恢复路径。

返回 [[计算机知识/80-实践/06-计算机系统/09-RISC-V特权态与系统调用/README|实验入口]]；下一步看 [[计算机知识/80-实践/06-计算机系统/09-RISC-V特权态与系统调用/02-系统调用与非法特权指令怎么分流|为什么未知系统调用与非法 CSR 不是一类错误]]。
