---
domain: computer-science
type: explanation
topics:
  - RISC-V
  - Sstc
  - timer-interrupt
content_status: usable
evidence_status: partial
---

# Sstc 中断从 `time` 到 `sret`

## 先区分两种常见计时路径

RISC-V 内核常见的定时路径有两类：

1. 机器态计时器比较器先产生 machine timer interrupt，M 态软件再把事件桥接或注入给 S 态；
2. 实现 Sstc 扩展时，M 态允许 S 态访问 `stimecmp`，S 态直接设置 supervisor timer deadline。

本实验明确选择第二条。QEMU 命令行固定 `-cpu rv64,sstc=true`；M 态设置 `menvcfg.STCE=1` 与 `mcounteren.TM=1`，把 supervisor timer interrupt 委托给 S 态，并保持 `mie.MTIE=0`。因此日志里的 cause 5 来自 Sstc 的 supervisor timer 路径，不是 M 态软件临时伪造的 tick。

## 一个 tick 何时变成 pending

Sstc 的比较规则可以写成：

$$
\mathrm{STIP}=1
\quad\Longleftrightarrow\quad
\mathrm{time}\ge \mathrm{stimecmp}.
$$

每次安排新时间片时，代码先读 `time`，再写：

$$
\mathrm{stimecmp}_{next}
=\mathrm{time}_{now}+2{,}000{,}000.
$$

QEMU 9.2.4 `virt` 的设备树 timebase 是 10 MHz，所以名义上的 guest timer-domain 间隔为：

$$
\frac{2{,}000{,}000\ \mathrm{ticks}}
     {10{,}000{,}000\ \mathrm{ticks/s}}
=0.2\ \mathrm{s}.
$$

这里的 0.2 s 是 guest 架构时钟域的换算，不是宿主墙钟耗时保证。TCG 调度、宿主负载和暂停都会改变一次运行在现实中花多久；runner 的 `--timeout 10` 则是宿主墙钟的失败上限，两者用途不同。

比较条件成立后，最稳妥的清除方法是把 `stimecmp` 重写到未来。本实验在 handler 的最前部读取当前 `time` 并写入下一 deadline，然后才打印和选择任务。这样返回 U 态前 pending 条件已经解除；若 handler 先返回而 deadline 仍在过去，会立刻再次进入 trap，形成中断风暴。

## 四层使能要同时成立

定时器值到了，不代表处理器一定立刻陷入 S 态。这个实验逐层建立以下条件：

| 层 | 设置 | 作用 |
| --- | --- | --- |
| 扩展访问 | `menvcfg.STCE=1` | 允许较低特权级使用 Sstc 比较器 |
| 时间访问 | `mcounteren.TM=1` | 允许 S 态访问 `time`；它也是 U 态访问的上级门，但本实验没有给 U 态开放 `scounteren.TM` |
| 路由 | `mideleg.STIP=1` | supervisor timer interrupt 在 S 态处理 |
| 局部使能 | `sie.STIE=1` | 允许 supervisor timer interrupt |
| 全局使能 | U 态运行时 S 级中断有效 | 让 pending+enabled 的事件取得控制 |

M 态把 `mie` 清零，因此输出里的 `MTIE=0` 是有意的。实验没有走 machine timer cause 7；如果意外进入 M trap，机器态 handler 会打印 `MACHINE TRAP` 并以失败状态退出。处理器处于 U 态时，S 级中断属于更高特权级，按规范不依赖 `sstatus.SIE` 的当前值也可取得控制；本实验仍让 `sret` 按正常保存恢复规则把 SIE 设为 1，使下一次陷入时 `SPIE=1` 可被检查。

## `SIE/SPIE/SPP` 怎样跨一次 trap

初次返回 U 态前，S 态准备的 `sstatus` 满足：

- `SPP=0`：`sret` 的目标是 U 态；
- `SPIE=1`：`sret` 后把 SIE 恢复为 1；
- `SIE=0`：执行 `sret` 前 handler 本身不接收嵌套 S 中断。

`sret` 的关键效果可概括为：

$$
\begin{aligned}
\mathrm{mode}&\leftarrow\mathrm{SPP},
&\mathrm{SIE}&\leftarrow\mathrm{SPIE},\\
\mathrm{SPIE}&\leftarrow1,
&\mathrm{SPP}&\leftarrow0.
\end{aligned}
$$

U 态被 timer 打断时，硬件把 trap 前的 SIE 语义保存进 SPIE，并清 SIE；由于来源是 U 态，SPP 为 0。入口保存到 trapframe 的 `sstatus` 因而应表现为 `SPP=0、SPIE=1、SIE=0`。C handler 逐项核对，另用 `trap_depth==1` 拒绝嵌套或入口次序破坏。输出中的 `SPP=0 SPIE=1 depth=1` 不是注释，而是通过检查后才打印。

## `scause` 为什么是 `0x8000000000000005`

RV64 `scause` 的最高位区分 interrupt 与同步 exception，其余低位给出 cause code。本次值为：

$$
\mathtt{0x8000000000000005}
=(1\ll63)\mathbin{\vert}5.
$$

最高位 1 表示 interrupt，低位 5 表示 supervisor timer interrupt。普通 U 态 `ecall` 是同步 exception，`scause=8`；所以同一个入口可以先比较完整 timer 值，再比较 8，其他原因一律失败。两条路径还在 `sepc` 语义上不同：

- timer interrupt 在两条指令之间取得控制，`sepc` 是返回后继续的位置；无需 `+4`；
- U `ecall` 的 `sepc` 指向 `ecall` 本身，若要正常继续才需要明确推进或改写。

本实验在每个任务第三次被抢占时把保存的 `sepc` 改为该任务的受控退出桩。这是调度器明确改变下一执行点，不是把 timer interrupt 当成四字节异常指令跳过。

## 反汇编与 trace 怎样相互约束

实际 ELF 的关键反汇编片段包含：

```text
csrw    stimecmp, s2
...
csrw    sie, a1
rdtime  s0
csrw    stimecmp, s1
...
sret
```

两段 U 态热循环位于：

```text
0x80010088 <user0_hot_loop> ... 0x800100a4 <user0_hot_loop_end>
0x80012084 <user1_hot_loop> ... 0x800120a0 <user1_hot_loop_end>
```

运行时通过固定别名差值 `0x40010000` 执行，因此合法 U 态 PC 区间分别是 `[0x40000088,0x400000a4)` 与 `[0x40002084,0x400020a0)`。guest handler 自己拒绝区间外的 timer `sepc`，runner 又从 ELF 符号表独立计算并核对输出。一次运行中观测到的 `0x40000088` 和 `0x40002084` 正好落在两个热循环开头。

## 为什么这叫抢占

任务 A 和 B 的热循环只做：

```text
增加寄存器工作计数
加载栈上工作计数
增加并写回
做无副作用算术
跳回循环
```

循环内没有系统调用、`yield`、`wfi` 或对调度标志的轮询。任务不知道 deadline，也没有执行“该换人了”的分支。控制权来自外部 timer pending 条件，S 态在任意一次循环迭代边界取得控制并选择另一份上下文；这正是本实验所说的定时抢占。

这仍然不等于证明通用调度公平。严格交替和固定 0.2 s 名义时间片是为了让证据可复核；真实 OS 还要处理阻塞、优先级、动态任务、计时漂移、负载均衡和多核 timer/IPI。
