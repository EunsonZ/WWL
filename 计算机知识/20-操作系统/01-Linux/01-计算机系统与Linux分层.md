---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 45
topics:
  - 计算机系统
  - Linux
  - 内核
  - 用户空间
  - 系统调用
  - 进程
  - 虚拟内存
  - 文件描述符
tags:
  - computer-science/linux
  - computer-science/operating-system
---

# 计算机系统与 Linux 分层

## 本课目标

学完本课，你应该能够：

- 从 CPU、内存、存储和设备一直讲到固件、引导程序、内核、用户空间、服务与应用；
- 解释“Linux 严格说是内核”，并区分 Linux 内核、GNU/其他 userland 与发行版；
- 用“程序 → 库函数 → 系统调用 → 内核 → 硬件”模型理解用户态与内核态；
- 用自己的话说清进程、虚拟内存和文件描述符；
- 用 `uname`、`ps`、`lsblk`、`/proc` 和 `/sys` 观察一台 Linux 系统，同时知道这些视图的边界。

适用场景：你刚开始学 Linux，已经会打开终端和复制命令，但还不确定“我正在和系统的哪一层交互”。

> [!important] 本课命令的安全边界
> 下文命令都只读取当前状态，不需要 `sudo`。不要把“能用 `cat` 读”推广成“可以往里写”：`/proc/sys` 和 `/sys` 中有些节点可改变内核或设备状态。本课不使用 `dd`、`mkfs`、`fdisk`、`parted`、`mount` 等可能改变磁盘或挂载状态的命令。

## 1. 先分清两张图：启动顺序与运行时分层

“电脑怎样启动”是时间顺序，“程序怎样使用硬件”是运行时边界。它们有关，但不是同一张图。

### 启动链：谁先把谁带起来

```text
通电
  → 平台固件（例如 UEFI）初始化启动所需硬件并选择启动项
  → bootloader 把 Linux 内核和可选 initramfs 放入内存，传递启动参数
  → 内核初始化 CPU、内存管理和内核子系统；若有 initramfs，则解包它并执行 /init（PID 1）
  → initramfs 的早期用户空间找到并挂载真实根文件系统，再通过 switch_root 执行真实系统的 init
  → 真实系统的 init/服务管理器（Arch 通常为 systemd，仍是 PID 1）启动服务、登录界面或图形界面
  → 用户启动 shell 和其他应用
```

这是典型路径，不是唯一实现。如果访问真实根文件系统所需的驱动都已内置在内核中，而且启动参数足够，系统也可以不使用外部 initramfs：内核直接挂载真实根文件系统，再启动其中的 init。嵌入式设备、容器、虚拟机和不同架构还可以省略、替换或嵌套某些环节。例如，容器看到的 PID 1 可能只是其 PID namespace 中的第一个进程，并非整台主机最初的用户空间进程。

### 运行时分层：权限和接口在哪里

| 层次 | 主要角色 | 初学者可观察线索 |
| --- | --- | --- |
| shell 与应用 | 接受输入、实现业务、发起操作 | 当前 shell、命令行程序、图形应用 |
| init 与系统服务 | 组织用户空间的启动、监管长期进程 | `ps` 中的 PID 1 和服务进程 |
| userland（用户空间） | 库、GNU/其他工具、命令、桌面等 | `/bin`、`/usr`，以及各进程 |
| 系统调用边界 | 用户空间请求内核服务的基本接口 | `open`、`read`、`write`、`mmap` 等概念 |
| Linux 内核 | 调度、虚拟内存、文件系统、网络、驱动、权限检查 | `uname`、`/proc`、`/sys` |
| 硬件 | 实际执行、存储与输入输出 | CPU、RAM、磁盘、网卡、显卡等 |

固件和 bootloader 对“怎样启动”很关键，但系统启动完后，普通应用并不经由 bootloader 读文件或发网络包。此时应用通过系统调用请求内核，内核再管理设备。

## 2. 底层四件套：CPU、内存、存储和设备

### CPU：执行指令，也执行权限规则

CPU 从内存取指令并执行。操作系统依靠 CPU 提供的特权级、中断和内存保护机制，把普通程序与内核隔开。多核 CPU 可以同时运行多个执行流，内核调度器决定哪个可运行任务在哪个 CPU 上运行。

### 内存：当前工作集与地址映射

RAM 保存当前活跃的代码和数据，丢电后通常不保留。程序日常使用的却不是“某条 RAM 芯片的直接地址”，而是进程的虚拟地址。内核和 CPU 的内存管理硬件共同把虚拟页映射到物理页或文件等后备存储。

### 存储：持久保留字节

SSD、HDD、NVMe 设备等在断电后仍可保留数据。内核的块设备层把它们呈现给更上层；分区、文件系统和挂载点是不同概念：

- 设备是提供存储能力的对象；
- 分区是设备上的一段范围；
- 文件系统是组织目录、文件和元数据的格式与规则；
- 挂载是把某个文件系统接入当前目录树。

### 设备：不只是硬盘

键盘、鼠标、网卡、显卡、声卡、USB 控制器和传感器都是设备。驱动程序把特定设备的寄存器、中断、DMA 等细节转换为内核其他部分可使用的接口。驱动可以内置在内核中，也可以以内核模块形式加载。

## 3. 从固件到 init：启动时每层交付什么

### 固件（firmware）

这里的**平台固件**是主板或计算平台提供的启动环境，例如传统 BIOS 或 UEFI。以常见 UEFI 流程为例，它在通电后初始化足以继续启动的环境，根据启动项找到下一阶段程序。这一层不是 Linux 内核。

不要把平台固件与**设备固件**混为一谈。网卡、显卡、存储控制器等设备也可能运行自己的 firmware；有些已经保存在设备上，有些由 Linux 驱动从系统的 firmware 文件中加载。它们主要协助具体设备工作，不负责选择整台机器的操作系统启动项。设备 firmware、driver 与 kernel module 的关系见[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]。

### 引导程序（bootloader）

bootloader 负责选择并装载内核，通常还装载 initramfs，然后把控制权交给内核。它可以传递内核命令行，如根文件系统位置、控制台和调试选项。启动完成后，bootloader 通常不再参与普通应用的运行。

### Linux 内核

内核接手后建立中断、计时、调度和内存管理并初始化必要驱动。典型的 initramfs 路径中，内核先把 initramfs 解包为临时根并执行其中的 `/init`；这个第一用户空间进程是 PID 1。早期用户空间再发现、解锁或组装存储，挂载真实根文件系统，并通过 `switch_root` 执行真实系统的 init；Arch 通常在这里接续为 systemd，PID 仍为 1。如果系统不使用外部 initramfs，且内核已具备访问真实根所需的一切能力，内核也可以直接挂载真实根并启动其中的 init。内核命令行可在 `/proc/cmdline` 中观察，但不要仅凭某个参数猜测整个启动结果。

### init 与服务

init 是内核启动的用户空间起点。它的具体实现可以是 systemd、BusyBox init 或其他程序。它会组织网络、日志、定时任务、远程登录、图形登录等长期服务。内核提供机制，服务实现策略和功能；两者不应混为一层。

具体启动链、initramfs 与 systemd 将在[[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|下一课]]展开。

## 4. Linux 到底是什么

### 严格说：Linux 是内核

Linux 内核负责共享硬件资源并向用户空间提供系统调用。它本身不等于 shell、图形桌面、包管理器或用户正在运行的全部程序。

日常语境中，人们也常用“Linux”指整套系统。理解对话时可以接受这种简称，但分析技术问题时要追问：说的是内核，还是一个以 Linux 为内核的发行版？

### GNU 与其他 userland

userland（用户空间软件集合）包含 C 库、shell、命令行工具、系统服务、编译器、桌面和应用。许多常见发行版使用 GNU C Library、Bash、Coreutils 等 GNU 组件，因此“GNU/Linux”能准确强调 GNU 系统与 Linux 内核的组合。

但“以 Linux 为内核”并不保证 userland 全部来自 GNU。有的小型系统使用 BusyBox，Android 也有不同的用户空间组合。所以看到 Linux 内核版本，不能自动推断所有用户空间组件。

### 发行版（distribution）

发行版将 Linux 内核、用户空间工具、库、安装器、包管理、默认配置、更新与安全策略组装成可维护的产品。Ubuntu、Debian、Fedora 和 Arch Linux 的差异大量存在于这一层，而不是它们分别有一种完全无关的内核架构。

## 5. user mode 与 kernel mode：不是“普通用户与 root”

CPU 可以在不同特权级执行代码。在简化的 Linux 模型中：

- **user mode（用户态）**：应用和大多数系统服务所在的受限执行环境；
- **kernel mode（内核态）**：内核可以执行特权指令、管理页表、处理中断并访问设备的执行环境。

这是 CPU 执行权限边界，不是用户账号分类。root 启动的普通程序仍主要在用户态执行；当它发起系统调用、发生中断或异常时，CPU 才进入内核代码。反过来，普通账号的程序也可以通过被允许的系统调用请求内核服务。

这条边界带来隔离：一个普通进程不能任意读另一个进程的内存，也不能直接向任意硬件端口发指令。但它不是“绝对安全墙”：内核漏洞、错误驱动或过度授权的接口仍可能破坏隔离。

## 6. 系统调用：跨过边界的正门

系统调用（system call）是应用与 Linux 内核之间的基本接口。程序请求打开文件、读取数据、创建进程、映射内存或建立网络连接时，最终需要由内核完成受保护的部分。

```text
应用源代码
  → 语言运行时或 C 库封装（常见，但不是每次都必须）
  → 特定架构的系统调用入口
  → CPU 进入内核态
  → 内核检查参数、权限和当前状态，执行请求
  → 返回结果或错误，CPU 回到用户态
```

不要把“库函数”和“系统调用”当成同义词。例如，标准库函数可以只做用户空间计算，也可以缓冲多次操作后才调用内核；系统调用则是明确进入内核接口。Linux man-pages 中的第 2 章（如 `open(2)`）通常文档化系统调用，第 3 章通常文档化库函数。

## 7. 三个运行时核心概念

### 进程：不只是“一个 `.exe` 文件”

程序是代码和数据的静态表示；进程是正在运行的执行环境。一个进程通常包含：

- 进程标识符 PID 和父进程关系；
- 用户与组凭据、能力与其他安全状态；
- 虚拟地址空间；
- 打开的文件描述符；
- 当前目录、环境、信号处理和调度状态；
- 一个或多个执行线程。

同一个程序可以同时对应多个进程，而一个进程又可以包含多个共享资源的线程。`ps` 给出某一时刻的进程视图，不是永恒不变的清单。

### 虚拟内存：每个进程看到的地址空间

每个进程通常在自己的虚拟地址空间中运行。内核记录哪些范围有效、权限是可读/可写/可执行中的哪些，以及它们映射到匿名内存、可执行文件、共享库或其他文件的什么位置。

“进程有 1 GiB 虚拟映射”不等于“它现在独占 1 GiB 物理 RAM”。页可以按需分配，多个进程可共享只读库页，文件页可由页缓存支撑。`/proc/<PID>/maps` 展示映射区间，但它不能单独回答所有物理内存占用问题。

### 文件描述符：进程内的小整数句柄

文件描述符（file descriptor，FD）是某个进程内的非负整数，用来引用一个已打开的 I/O 对象。约定上：

- `0` 是标准输入 stdin；
- `1` 是标准输出 stdout；
- `2` 是标准错误 stderr。

FD 不是文件内容，也不是全局唯一编号。不同进程的 FD 3 可以指向完全不同的对象。管道、socket、终端、`eventfd` 等也可以通过 FD 使用，所以“文件描述符”中的“文件”比“磁盘上的普通文件”更广。

## 8. “一切皆文件”是好用比喻，不是字面定律

Unix/Linux 把许多资源塑造成可以用文件名、FD 和读写操作处理的接口：

- `/dev` 中的设备节点让程序通过文件接口与设备驱动交互；
- `/proc` 是伪文件系统，将进程、内核和部分系统信息暴露为文件树；
- `/sys` 的 sysfs 把内核对象、设备层次和属性暴露给用户空间；
- 管道和 socket 也可以获得 FD，参与统一的 I/O 组合。

但这些对象不都是磁盘上的普通文件；它们的语义也不都是“从头到尾读一串字节”。网络连接、进程创建、信号、计时器、内存映射和调度还有各自的系统调用与规则。部分文件式对象还需要 `ioctl` 等不是简单 `read`/`write` 的操作。

更准确的说法是：**Linux 尽量让很多资源共享文件系统命名和 FD/I/O 接口，但“一切”并非普通文件，也并非只靠一组读写语义。**

## 9. shell 是用户空间程序，终端也不是 shell

shell 是命令解释器和编程语言。Bash 是 GNU 的一种 shell，zsh、fish 等是其他实现。shell 可以：

- 解析命令、变量、引号、管道和重定向；
- 启动外部程序，或执行 `cd` 这类内建命令；
- 等待前台任务，管理作业，并收集退出状态。

终端模拟器是显示字符并转发键盘输入的应用；shell 是通常运行在其中的命令解释器；`ls`、`ps` 等则常是 shell 启动的独立程序。这三者都不是 Linux 内核。

## 10. 用五类线索观察当前系统

> [!note] 先预期“结果不一样”
> 下面的输出会因发行版、内核版本、硬件、权限、容器、WSL 和虚拟机而变。看到差异不等于命令失败；先问“我观察的是宿主机、虚拟机还是 namespace 中的视图？”。这些命令面向 Linux，不应直接用 macOS 输出作对照。

### 线索 A：`uname` 观察正在运行的内核

```bash
uname -srmo
```

常见字段包括内核名、发布号、机器硬件名和操作系统名。它告诉你“当前内核报告什么”，不能单独告诉你 Ubuntu/Fedora 等发行版的完整身份，也不能代替 CPU 和主板型号检测。

### 线索 B：`/proc` 观察进程与内核状态

```bash
sed -n '1,12p' /proc/cpuinfo
sed -n '1,12p' /proc/meminfo
printf 'current shell PID: %s\n' "$$"
sed -n '1,12p' "/proc/$$/status"
sed -n '1,12p' "/proc/$$/maps"
ls -l "/proc/$$/fd"
```

在 `/proc` 中，数字目录通常对应 PID。`/proc/$$` 指向当前 shell 进程，因为 shell 会把 `$$` 展开为自己的 PID。`status` 提供摘要，`maps` 显示虚拟内存映射，`fd` 目录中的符号链接对应该进程打开的 FD。

`/proc` 不是开机时生成后就不变的普通文件集；读取时常由内核生成当前视图。进程可能在你列出目录与继续读取之间退出，某些信息也会因权限或挂载选项而不可见。

### 线索 C：`/sys` 观察内核设备模型

```bash
ls /sys/class
ls /sys/class/block
ls /sys/devices/system/cpu
```

sysfs 通常挂载在 `/sys`，用目录和属性文件暴露内核对象与关系。`/sys/class/block` 是块设备的类视图，其中很多项是指向实际设备层次的符号链接。这是内核数据结构对用户空间的接口，不是硬盘上对应路径里真实存着同样的文本文件。

### 线索 D：`ps` 观察进程关系

```bash
ps -eo pid,ppid,user,stat,comm --sort=pid | head -n 25
ps -p 1 -o pid,ppid,user,stat,comm,args
```

关注 `PID`、`PPID`、`USER`、`STAT` 和 `COMMAND`。PID 1 在完整主机上通常是 init/服务管理器；在容器中它可能是一个普通应用或小型 init。`ps` 自己也是用户空间程序，它只是读取系统视图，不是“进程表就长在 ps 里”。

### 线索 E：`lsblk` 观察块设备树

```bash
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS
```

观察磁盘、分区、逻辑卷与挂载点之间的树状关系。空的 `FSTYPE` 不一定是错误；一个块设备可能是其他层的容器、交换区、未格式化区域，或当前用户无法获得更多信息。`lsblk` 也不表示“所有存储都已挂载”。

## 11. 练习：画出你当前 Linux 环境的分层快照

在 Linux 终端中完成以下练习。只复制本节和上一节中的只读命令，不要为了“看到更多”加 `sudo`。

1. 运行 `uname -srmo`，标出哪个字段是内核发布号，并写一句“这不能单独证明发行版是什么”。
2. 运行 `ps -p 1 -o pid,ppid,user,stat,comm,args`，记录 PID 1 的程序名，判断你是否可能处在容器中。不确定时标记“待核实”，不凭一条输出强行下结论。
3. 运行 `ls -l "/proc/$$/fd"`，找到 0、1、2，说明它们当前指向终端、管道还是其他对象。
4. 运行 `sed -n '1,12p' "/proc/$$/maps"`，找到权限列。至少识别一个可执行映射和一个可写映射；不要把映射范围总和当成独占 RAM。
5. 对照 `lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS` 和 `ls /sys/class/block`，写出一个两者都出现的块设备名，并区分设备、分区、文件系统与挂载点。
6. 用不超过 120 字的文字画出你的环境：“硬件/虚拟硬件 → 内核 → init/服务 → shell → 刚才运行的命令”。

如果某条命令因权限、最小化容器或缺少工具而失败，记录完整错误和环境类型，而不是立即提权。“能说明观察边界”也是练习结果。

## 常见误解检查表

| 误解 | 更准确的说法 |
| --- | --- |
| Linux 就是 Ubuntu | Ubuntu 是组装 Linux 内核、userland、配置和包管理等的发行版 |
| shell 是内核的命令界面 | shell 是用户空间的命令解释器，通过系统调用间接请求内核 |
| root 程序始终在内核态 | root 是操作系统凭据；root 的普通程序仍主要在用户态运行 |
| 系统调用就是任意函数调用 | 系统调用是用户空间进入 Linux 内核服务的受控接口 |
| 进程就是磁盘上的程序文件 | 进程是运行中的执行与资源环境，同一程序可有多个进程 |
| 虚拟地址空间大小就是实际占用 RAM | 虚拟映射、驻留物理页和独占页是不同指标 |
| FD 就是磁盘文件的编号 | FD 是进程内引用已打开 I/O 对象的整数句柄，对象也可以是管道、socket 或终端 |
| `/proc` 和 `/sys` 是普通磁盘文件夹 | 它们通常是内核提供的伪/内存文件系统接口，内容可随状态改变 |
| “一切皆文件”没有例外 | 它概括文件名、FD 和 I/O 接口的复用，不是所有对象都是普通文件 |

## 成功标准

- [ ] 能画出“硬件 → 固件 → bootloader → kernel → userspace → init/services → shell/apps”启动链，并说明它不等于运行时每次 I/O 的路径；
- [ ] 能区分 Linux 内核、GNU/其他 userland 和发行版；
- [ ] 能解释 user mode/kernel mode 是 CPU 特权边界，不是普通用户/root 的别名；
- [ ] 能画出一次系统调用的往返路径，并区分库函数与系统调用；
- [ ] 能用一个可观察例子分别说清进程、虚拟内存和文件描述符；
- [ ] 能解释“一切皆文件”的有用之处和边界；
- [ ] 能不用 `sudo` 完成练习，并不把容器或虚拟机里的视图误当成全部物理主机。

## 导航

- 课程入口：[[计算机知识/00-开始/00-计算机知识-首页|计算机知识首页]]
- 返回 MOC：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础]]
- 下一篇：[[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|启动链、Kernel 与 systemd]]

## 一手参考

- [Linux Kernel Documentation：用户向文档与用户空间 API](https://docs.kernel.org/)
- [Linux Kernel Documentation：内核命令行参数](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [Linux Kernel Documentation：Memory Management](https://docs.kernel.org/admin-guide/mm/index.html)
- [Linux Kernel Documentation：sysfs](https://docs.kernel.org/filesystems/sysfs.html)
- [Linux man-pages：`syscalls(2)`](https://man7.org/linux/man-pages/man2/syscalls.2.html)
- [Linux man-pages：`proc(5)`](https://man7.org/linux/man-pages/man5/procfs.5.html)
- [Linux man-pages：`proc_pid_fd(5)`](https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html)
- [Linux Kernel Documentation：Process Addresses](https://docs.kernel.org/mm/process_addrs.html)
- [GNU Project：GNU/Linux FAQ](https://www.gnu.org/gnu/gnu-linux-faq.html)
- [GNU Bash Manual：What is Bash?](https://www.gnu.org/software/bash/manual/html_node/What-is-Bash_003f.html)
- [GNU Coreutils Manual：`uname` invocation](https://www.gnu.org/software/coreutils/manual/html_node/uname-invocation.html)
- [procps-ng manual：`ps(1)`](https://man7.org/linux/man-pages/man1/ps.1.html)
- [util-linux manual：`lsblk(8)`](https://man7.org/linux/man-pages/man8/lsblk.8.html)


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/15-Shell文件进程与可靠脚本边界|Linux 深化：Shell、文件和可靠脚本的边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/20-操作系统/01-Linux/10-系统课程/02-文件描述符管道与进程控制|Linux 进程与文件描述符：用小实验理解共享状态]]
- [[计算机知识/20-操作系统/01-Linux/10-系统课程/03-权限身份与最小授权|Linux 权限：文件能不能删，为什么不只看文件写位]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
