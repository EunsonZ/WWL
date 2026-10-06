---
domain: "计算机知识"
type: "course"
stage: 5
prerequisites:
  - "[[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|GhidraRadare2与静态逆向]]"
sources:
  - "https://sourceware.org/gdb/current/onlinedocs/gdb.html/All_002dStop-Mode.html"
  - "https://sourceware.org/gdb/current/onlinedocs/gdb.html/Continuing-and-Stepping.html"
  - "https://sourceware.org/gdb/current/onlinedocs/gdb.html/Starting.html"
  - "https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html"
  - "https://man7.org/linux/man-pages/man1/strace.1.html"
content_status: "usable"
evidence_status: "partial"
---

# GDBGefStrace与动态观察

**先修关系：** [[计算机知识/Kali/06-取证逆向与检测/05-GhidraRadare2与静态逆向|GhidraRadare2与静态逆向]]。

## 动态观察会执行程序

GDB 是调试器，能暂停、单步并查看程序状态；strace 观察系统调用及信号；ltrace 偏向动态库调用。它们的观察层不同，不能把一次库调用机械视为一次系统调用。`run` 不是静态分析命令：它确实启动目标程序。[^s1][^s3]

以下只调试本包 `hello.c` 编译出的无害本地程序。不要把路径换成来源不明样本后继续执行，也不要附加到不属于自己的进程。

## 调试器、系统调用跟踪和业务日志是三种观察粒度

GDB 能在指令、函数和内存状态层观察执行；`strace` 观察用户态与内核之间的系统调用和信号；应用日志记录程序选择暴露的业务事件。这三种观察没有谁天然覆盖另外两种。GDB 的 all-stop 模式会在停止事件发生时停止其他线程，而恢复执行与调度控制又有自己的语义；暂停与单步会改变时间安排，不能把调试时的线程交错直接当成未调试运行的必然交错。[^v5-gdb-stop]

原创反例：应用先通过一次读取将多个记录放入用户态缓冲，再逐条解析。后面某条记录触发业务错误时，没有新的 `read` 系统调用，不等于没有读取该业务记录；它可能已经在缓冲里。反过来，一次 `write` 返回成功通常只是对应调用完成，是否完成远端接收、数据库提交或业务处理，要沿 [[计算机知识/Kali/01-系统与网络基础/06-TCPIP路由DNS与TLS|确认层级]] 继续找证据。

## 在 main 停下，解释控制流

```bash
gdb -nx -nh -iex 'set auto-load off' \
  "$HOME/kali-lab/output/hello"
```

`-nx -nh` 用于减少用户初始化文件的影响，关闭自动加载降低从分析文件旁边加载脚本的风险；它们不是完整沙盒。进入 GDB 后：

```text
set startup-with-shell off
set disable-randomization off
break main
run Ethan
info args
next
bt
continue
quit
```

`break main` 设置断点；`run Ethan` 启动进程并传入一项参数；`next` 在当前源代码层执行下一步；`bt` 查看调用栈。编译器优化、内联和符号缺失会使源码位置与机器指令不一一对应。地址在不同运行中变化是正常现象，不能照抄一次截图的地址到所有机器。GDB 某些平台默认改变地址随机化，本例显式保留正常随机化，避免把调试环境误当成生产行为。[^s1][^s2]

`print` 某些表达式可能调用程序函数，`set variable` 会修改状态；初学者先只读局部值，并区分“观测”与“干预”。检查寄存器时先明确架构和调用约定，不以单个数值推导通用结论。

## 补强：每一步到底执行了什么

`step` 按源码级步进入可调试函数；`next` 通常把当前源码行的函数调用作为一步执行；`stepi` 以机器指令为单位；`finish` 继续执行到当前函数返回。它们都会实际运行被调试程序，不是静态浏览。中途也可能因为信号或断点停止。缺少调试信息或经过优化时，“一行源码”与机器指令不是一一对应。[^v2-gdb-step]

学习时先固定一个问题。例如“为什么两个额外参数返回 2”：停在 `main`，读取 `argc`，观察比较分支，再看 `fputs` 和返回值。不要边调试边任意修改寄存器，否则你解释的是被改变后的运行。GDB 中调用目标函数、修改变量以及 `jump` 等操作都有副作用，应与只读观察分开记录。

## strace：把文件和网络行为落实到调用

```bash
strace -o "$HOME/kali-lab/output/hello.strace" \
  -e trace=%file,%network \
  "$HOME/kali-lab/output/hello" Ethan
```

该过滤显示文件和网络相关系统调用；动态链接器读取共享库也是正常文件访问。看到 `ENOENT` 不等于程序失败，程序可能正在尝试多个候选路径。反过来，没有网络调用只说明这个输入和这次运行路径下未观察到，不证明程序所有分支永不联网。`-f` 可跟踪派生进程，但应先了解范围和日志增长。[^s3]

ltrace 在不同链接方式、优化和平台下可能看不到预期库调用。GEF/Pwndbg 可增强 GDB 界面，但插件本身是会执行的代码；本包不自动安装，不以某插件截图作为原生 GDB 通用功能。需要时固定插件版本、审阅来源并保留无插件基线。

## 为什么 unfinished 不是一次失败调用

`strace` 在多线程或多进程交错时，可能将一个尚未返回的调用标为 `unfinished`，随后用 `resumed` 继续显示；它也区分尚未返回、结果无法获取和提前分离等状态。只抓取包含某个词的行，会破坏入口、返回值与线程身份的对应关系。[^v5-strace]

正确的阅读单位是同一执行上下文中的一次调用及其完成状态，而不是一行。若一条记录只有进入没有返回，当前证据只能支持“未在观察范围内看到完成”；它可能仍在等待、被信号改变流程、超出采集窗口或跟踪已结束。把它统一填成 `-1` 会制造不存在的错误。

复现性也要分层：同样输入稳定触发同样输出，是输入输出层面的复现；同样堆栈、访问地址和线程交错，是更强而不同的要求。一项并发问题在调试器下消失，应保留为观察条件变化，而不是据此宣布问题已修复。与 [[计算机知识/Kali/03-Web与API安全/12-现代API业务逻辑与并发边界|事务和并发边界]] 连接时，要先明确要复现的是状态不变量被破坏，而非必须重演完全相同的机器时序。

## 补强：strace 的失败返回不等于应用失败

程序可能先尝试一个不存在的配置文件，收到 `ENOENT` 后使用默认配置，最终正常返回。也可能关键文件打开失败，却被应用吞掉而返回 0。因此应先识别系统调用、参数、返回值和后续控制流，再结合进程退出状态解释。需要跟踪子进程时，明确记录是否启用了相应选项；只观察父进程不能否定子进程的文件或网络行为。[^v2-strace]

一个可复核记录至少包含编译命令、二进制哈希、输入参数、运行工作目录、环境差异、跟踪过滤条件、退出码和输出。去掉某类调用的过滤器也就去掉了观察机会，不能把过滤后的空结果写成“程序从不访问网络”。

断点暂停、ptrace 跟踪和检查器插桩都会改变时间与资源开销。并发错误可能在调试器下消失，也可能被暂停放大。单次未重现只说明该输入和运行条件下没有观察到；要进一步比较不插桩、插桩、不同输入和重复运行，且保留资源与时间边界。本轮是否实际运行 GDB、strace，以验收记录为准，不用成功编译代替调试器实测。

## 从“崩溃”到“漏洞”还需要哪些证据

崩溃可以来自程序缺陷、错误环境、资源不足或不合法使用。要报告安全影响，必须解释输入是否处于信任边界、如何到达故障、影响哪种安全属性及可复现条件；不能把一个信号名等同于可执行任意代码。此包不提供控制流劫持步骤。

> [!question] 自检
> 在 strace 里看到读配置失败，但程序输出正常，下一步是什么？先看返回值、后续替代路径和程序退出码，而非只搜索 `ENOENT` 就下结论。这与 [[计算机知识/Kali/00-导航与方法/06-命令阅读与故障定位|命令故障定位]] 是同一个证据问题。

## 来源与核验范围

[^v5-gdb-stop]: [GDB：All-Stop Mode](https://sourceware.org/gdb/current/onlinedocs/gdb.html/All_002dStop-Mode.html)；定位：停止与恢复多线程执行的语义。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^v5-strace]: [strace 手册](https://man7.org/linux/man-pages/man1/strace.1.html)；定位：DESCRIPTION；unfinished/resumed；status 筛选。v5 实际网页读取：2026-09-06。支持所引机制；本页数字案例为原创教学推演，不是工具实测。

[^s1]: [GNU GDB：Starting](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Starting.html)；定位：run / start / shell / ASLR 与调试环境。网页读取：2026-09-05。
[^s2]: [GNU GDB：Setting Breakpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html)；定位：break / info breakpoints / 执行位置。网页读取：2026-09-05。
[^s3]: [strace 项目手册](https://man7.org/linux/man-pages/man1/strace.1.html)；定位：-e / -o / -f / 跟踪与返回值。网页读取：2026-09-05。

来源支持所引机制，教学模型与实际运行证据分开记录。旧版命令和实验的运行情况见 [[计算机知识/Kali/90-来源与维护/05-v3深度审阅与变更记录|v3 历史验收]]；本轮来源、理论与静态检查见 [[计算机知识/Kali/90-来源与维护/06-v5深度研究与结构梳理记录|v5 研究与验收]]。本轮没有重跑旧实验或进行 Kali 工具、Obsidian 界面实测。

[^v2-gdb-step]: [GDB：Continuing and Stepping](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Continuing-and-Stepping.html)；定位：step、next、stepi、finish 的执行语义。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

[^v2-strace]: [strace 官方维护手册](https://man7.org/linux/man-pages/man1/strace.1.html)；定位：跟踪过滤、进程跟踪、退出状态与错误返回。本轮网页读取：2026-09-05；教学推演与本包实验另行标明。

---
**导航：** [[计算机知识/Kali/00-导航与方法/00-Kali知识地图|知识地图]] · [[计算机知识/Kali/00-导航与方法/05-常用工具覆盖矩阵|按任务查工具]]