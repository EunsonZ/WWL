---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 入门到进阶
estimated_minutes: 55
topics:
  - linux
  - boot-process
  - kernel
  - initramfs
  - systemd
tags:
  - computer-science/linux
  - computer-science/linux-boot
  - computer-science/systemd
---

# 02 · 启动链：Kernel 与 systemd

按下电源键后，并不是“systemd 启动了 Linux”。更准确的顺序是：固件找到可启动程序，启动加载器把 Linux kernel 和必要的早期环境放进内存，kernel 建立内核世界并启动第一个用户空间进程，之后才轮到 systemd 组织服务、挂载点和登录环境。

这条链很长，但每一段的责任边界都很清楚。分清边界，才能根据现象判断故障发生在哪一层，而不是一看到“开不了机”就重装引导器或重建 initramfs。

## 本课目标

学完本课，你应该能够：

- 按顺序讲清 `固件 → 分区与启动文件 → bootloader → kernel → initramfs → PID 1 → systemd units`；
- 区分 BIOS 与 UEFI、GPT 与 ESP，知道它们不是同一层的同义词；
- 说明 kernel image、kernel modules、initramfs 各自解决什么问题；
- 解释 systemd 为什么通常是 PID 1，以及为什么 **systemd 不是 kernel**；
- 读懂 service、socket、timer、mount、target unit，以及“拉入依赖”和“规定顺序”的区别；
- 使用只读的 `systemctl`、`journalctl` 命令观察本机，不盲目停服务、改启动项或重建启动文件。

## 1. 先把整条链放进脑中

一台典型的 Arch Linux UEFI 主机大致经历以下过程：

```text
通电 / 复位
  ↓
UEFI 或传统 BIOS 固件：自检并选择启动路径
  ↓
启动加载器或 EFI 程序：选择启动项，装入 kernel、initramfs，传递 kernel command line
  ↓
Linux kernel：解压并初始化 CPU、内存、中断、设备和内核子系统
  ↓
initramfs 早期用户空间：kernel 执行 /init（已经是 PID 1），找到、解锁并组装根存储
  ↓
/init 挂载真正的根文件系统，通过 switch_root 执行真实系统的 init
  ↓
Arch 通常由 systemd 接续为 PID 1：建立 unit 依赖事务，推进到默认 target
  ↓
挂载、设备、服务、登录界面或图形桌面
```

这是一张责任图，不是严格的单线程时间轴。设备探测、模块加载和 unit 激活可能并行；UEFI 也可能通过 Linux 的 EFI stub 直接启动 kernel，而不经过传统意义上的独立 bootloader 菜单。排错时要问的是：“最后一个明确成功的阶段是什么？”

## 2. 固件层：BIOS 与 UEFI

### 传统 BIOS

BIOS 完成上电自检和基础硬件初始化后，按固件设定的磁盘顺序读取启动代码。在经典 MBR 路径中，磁盘开头能容纳的第一阶段代码很小，所以它通常继续找到并启动更完整的加载器代码。

BIOS 是**固件启动接口**；MBR 是一种**磁盘分区表与早期启动代码布局**。二者经常一起出现，但不能把“BIOS”直接等同于“MBR”。BIOS 也可以从 GPT 磁盘启动；例如 GRUB 在 BIOS + GPT 组合下通常需要一个很小的 BIOS boot partition 存放其嵌入代码。

### UEFI

UEFI 不再只依赖磁盘最开头的一小段机器码。它能理解一定的磁盘与文件系统结构，并启动一个 EFI 可执行文件。典型流程是：

1. UEFI 初始化启动所需硬件；
2. 读取 NVRAM 中的启动条目和 `BootOrder`；
3. 在指定的 EFI System Partition 中找到 EFI 程序；
4. 启动 systemd-boot、GRUB、其他 EFI boot manager，或直接启动带 EFI stub 的 Linux kernel / UKI。

若 NVRAM 条目丢失，一些固件还会尝试可移动介质的回退路径，例如 x86-64 常见的 `EFI/BOOT/BOOTX64.EFI`。Secure Boot 则可能在执行 EFI 程序前验证签名；它是否覆盖后续整条链，取决于实际签名、密钥和启动方案，不能只凭“Secure Boot 已开启”下结论。

## 3. 磁盘层：GPT 与 ESP 分别是什么

GPT（GUID Partition Table）描述一块磁盘上有哪些分区、各分区的类型与范围。它使用 GUID 标识分区类型和分区本身，并保存冗余的分区表信息。GPT 本身既不是文件系统，也不是 bootloader。

ESP（EFI System Partition）是供 UEFI 启动使用的特殊分区，通常使用 FAT 文件系统。里面放的是 UEFI 能读取的 EFI 可执行文件、启动项配置，以及某些方案中的 kernel、initramfs 或 Unified Kernel Image。ESP 也不是 `/boot` 的同义词：

- 有的系统把 ESP 直接挂载到 `/boot`；
- 有的挂载到 `/efi`，另设普通 `/boot`；
- 有的再使用 XBOOTLDR 分区存放 Linux 启动内容。

因此看到文档中的 `esp/EFI/...` 时，`esp` 是“ESP 实际挂载点”的占位符，不应机械替换成某个固定目录。修改启动文件前必须先用 `findmnt`、`lsblk` 和当前 bootloader 配置确认本机布局。

> [!note] 四个概念分属不同层
> BIOS / UEFI 是固件接口；MBR / GPT 是磁盘分区方案；ESP 是 UEFI 使用的分区；systemd-boot / GRUB 是启动加载或管理软件。常见组合不代表概念可以互换。

## 4. Bootloader：把选择变成可启动状态

bootloader 的核心工作是让 kernel 获得开始运行所需的材料：

- 选择哪个 kernel 或启动项；
- 把 kernel image 装入内存；
- 装入一个或多个外部 initramfs image；
- 传递 kernel command line，例如根设备标识、日志级别或 init 程序；
- 在多系统环境中提供选择，或链式启动另一个 EFI 程序。

boot manager 更强调“展示并选择 EFI 启动项”，bootloader 更强调“把操作系统 kernel 装起来”。实际工具可能兼具两种角色；日常讨论中也常把它们统称为启动加载器。

### Arch 中常见的两个选择：只做概览

| 工具 | 适用固件 | 直觉上的特点 | 需要记住的边界 |
| --- | --- | --- | --- |
| systemd-boot | 仅 UEFI | 结构较简单，读取 ESP / XBOOTLDR 上的条目，也能发现符合规范的 UKI | 只能启动其可访问分区上的 EFI 程序或启动内容，不负责 BIOS 启动 |
| GRUB | BIOS 与 UEFI | 功能和文件系统支持更广，适合较复杂的多启动与存储布局 | 安装位置、平台模块和生成的配置必须与实际固件模式、分区挂载一致 |

本课不提供安装或迁移命令。安装 bootloader 会写 ESP、NVRAM 或磁盘启动区域；照抄一条来自别人的命令，可能让当前系统和其他系统都无法启动。具体安装应在确认“当前以 BIOS 还是 UEFI 启动、ESP 挂载点、分区表、磁盘目标、是否加密、是否多系统”之后，逐项跟随 ArchWiki 的 [systemd-boot](https://wiki.archlinux.org/title/Systemd-boot) 或 [GRUB](https://wiki.archlinux.org/title/GRUB) 专页；完整实操留到后文的[[计算机知识/20-操作系统/01-Linux/12-ArchLinux安装实战|Arch Linux 安装实战]]。

## 5. Kernel image、modules 与 initramfs

这三个对象都可能参与启动，但角色不同。

### Kernel image：内核本体的可启动映像

Arch 的标准 kernel package 通常在 `/boot` 提供类似 `vmlinuz-linux` 的 kernel image。它包含编译进内核的核心能力与内置驱动。bootloader 装入并跳转到它之后，kernel 会解压自身，建立内存管理、调度、中断、VFS、设备模型等内核子系统，并解析 kernel command line。

kernel 运行在内核空间，提供系统调用、进程调度、内存和硬件抽象。它不是 systemd，也不负责读 `.service` 文件。

### Kernel modules：可按需装入的内核组件

并非每个驱动和功能都必须编译进 kernel image。可加载模块通常位于 `/usr/lib/modules/<kernel-release>/`，可以在启动中或运行时按需装入。模块仍然运行在**内核空间**，不是普通用户程序；错误或不受信任的模块可能影响整个系统。

module tree 必须与目标 kernel release 匹配。`uname -r` 显示的是**当前正在运行**的 kernel；`/boot` 中的映像和 `/usr/lib/modules/` 中的目录则可能还包含准备给下次启动或旧 kernel 使用的版本。升级后不重启时，这些集合不一定只有一个版本。

本节只说明它在启动链中的位置；built-in 驱动、可加载模块、firmware 与 udev 的完整设备链见 [[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]。

### Initramfs：启动早期的临时用户空间

initramfs 通常是压缩的 cpio archive。kernel 把它解包到内存中的临时根文件系统，并执行其中的 `/init`。它可以带上：

- 挂载真正根文件系统前必须用到的 kernel modules；
- udev、`modprobe`、文件系统检查或设备发现等用户空间工具；
- 解锁 LUKS、组装 LVM / RAID、发现网络根文件系统所需的程序与配置；
- 把真正根文件系统挂载好并执行 `switch_root` 所需的逻辑。

所以 initramfs 既**不是 kernel image**，也**不是完整的日常根文件系统**。它是一座临时桥梁：kernel 已经能运行，但真正的 `/` 还不可访问；initramfs 提供恰好足够的早期用户空间，把系统带到真实根文件系统。

一个关键的“先有鸡还是先有蛋”问题是：如果读取根文件系统需要某个存储控制器、加密或文件系统模块，而模块本来放在尚未挂载的 `/usr/lib/modules/`，该怎么办？答案就是把这批早期必需模块的副本及其工具放进 initramfs。切换到真正的 `/` 后，其余模块再从正常 module tree 按需加载。

### 三者如何配套

```text
kernel image
  ├─ 内置：启动最早阶段必须存在的核心能力
  ├─ 解包 initramfs，运行其 /init
  └─ 后续可加载与本 kernel release 匹配的 modules

initramfs
  ├─ 早期所需 modules 的副本
  ├─ 早期用户空间工具与配置
  └─ 找到真实根文件系统并 switch_root
```

kernel、initramfs、modules 不匹配，是升级后启动失败的常见方向之一；但在没有日志证据前，不要直接重建或删除其中任何一个。

## 6. Arch 的 mkinitcpio：生成桥梁，不是启动加载器

Arch 常用 `mkinitcpio` 根据 `/etc/mkinitcpio.conf`、hooks 和 kernel preset 生成 initramfs。kernel package 安装或升级时，pacman hooks 通常会按 preset 自动生成相应映像。复杂根设备（加密、LVM、RAID、特殊键盘或远程解锁等）可能需要额外 hooks、modules 或配置。

先理解三个边界：

- `mkinitcpio` **生成 initramfs**，不代替 kernel，也不等于 GRUB / systemd-boot；
- 生成成功只说明 archive 建出来了，不保证 bootloader 正在引用它，也不保证其中具备访问真实根设备的一切条件；
- `mkinitcpio -P` 会重建所有 preset 的映像，属于会改写启动关键文件的管理操作，不应当作为“试试看”的排错第一步。

只读观察可以从以下命令开始：

```bash
ls /etc/mkinitcpio.d/
lsinitcpio --analyze /boot/initramfs-linux.img
```

第二条中的文件名必须按本机实际情况调整。需要真正修改 hooks 或重建时，应先确认 ESP / `/boot` 已正确挂载、空间足够、bootloader 指向何处，并保留可启动的旧 kernel、fallback image 或 Arch 安装介质。具体做法以 ArchWiki 的 [mkinitcpio](https://wiki.archlinux.org/title/Mkinitcpio) 专页为准。

## 7. PID 1：从 kernel 进入用户空间

kernel 完成最低限度的初始化后，会启动第一个用户空间进程。这个进程得到 PID 1；PID 1 具有特殊责任，包括接收孤儿进程、回收已退出子进程，并作为系统启动与关闭的总协调者。

在 initramfs 阶段，第一个进程通常是 archive 中的 `/init`。它可能是一个脚本、一个小型 init，或 initrd 模式的 systemd。找到真正的根文件系统后，早期用户空间通过 `switch_root` 切换根，并执行真实系统的 init。Arch 的常规系统随后由 systemd 作为系统管理器继续以 PID 1 运行。

可以把边界记成：

```text
kernel 创建第一个用户进程 → 它是 PID 1
PID 1 组织用户空间 → Arch 常见实现是 systemd
```

因此：

- kernel 在 systemd 之前已经运行；
- 没有 systemd 的 Linux 仍然可以使用其他 init；
- systemd 崩溃不等于 kernel 本身消失，但 PID 1 故障通常会让整个用户空间无法正常继续；
- `systemctl` 是与 systemd 管理器通信的客户端工具，不是“控制 kernel 的总开关”。

## 8. systemd 的基本模型：unit 与事务

systemd 不只是“按顺序执行一串启动脚本”。它把需要管理的资源表示成 unit，再根据依赖关系把一次启动请求构造成一个 transaction（事务 / 作业集合）。这里的 transaction 是 systemd 为 units 计算出来的一组 jobs 及其依赖、顺序和冲突处理计划，不是“下载并安装一批软件包”的包管理事务；后者见[[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|pacman、apt、dnf 与 yum]]。没有顺序约束的 systemd jobs 可以并行。

unit 名称由实例名和类型后缀组成，例如：

- `sshd.service`：一个服务；
- `systemd-journald.socket`：一个套接字；
- `fstrim.timer`：一个定时器；
- `home.mount`：挂载点 `/home`；
- `multi-user.target`：一组启动目标或同步点。

unit 文件通常来自 `/usr/lib/systemd/system/`（软件包提供）和 `/etc/systemd/system/`（管理员配置与 override）；运行时生成内容还可能位于 `/run/systemd/system/`。不要为了改一行配置就复制并改写整个软件包 unit；通常应先用 `systemctl cat 名称` 看磁盘上的主 fragment 与 drop-in 来源文本，再用受控的 override 机制。真正编辑前应阅读对应 man page 并保留可恢复方案。

### service unit：管理进程生命周期

`.service` 描述如何启动、停止、重载一个服务，服务何时算启动成功，以及退出后是否重启。systemd 会跟踪该 unit 的进程，通常也会用 cgroup 把相关进程归在一起。

“服务已 enable”只表示它被接入未来的激活关系，并不表示当前正在运行；“服务 active”也不自动说明业务功能健康。要结合 status、日志、监听端口或应用自己的健康检查判断。

### socket unit：先监听，再按需启动服务

`.socket` 可以先由 systemd 创建并持有 Unix socket、TCP / UDP socket 或 FIFO。当连接或数据到达时，它触发对应 `.service`，并按协议把已建立或监听的文件描述符交给服务。这样客户端不必等待守护进程预先常驻，也能增加启动并行度。

并非任何 service 都能自动获得 socket activation；程序必须支持相应的文件描述符传递或由匹配的 socket/service 配置适配。

### timer unit：以时间触发其他 unit

`.timer` 通常激活同名 `.service`，可以表达：

- 相对于启动、上次激活等时间点的单调计时；
- 日历时间；
- 是否补做关机期间错过的日历任务等策略。

timer 不是 cron 语法的简单换皮：它仍然处在 unit 依赖、日志和资源管理体系中。查看 `systemctl list-timers` 不会修改定时器。

### mount unit：把挂载点纳入依赖图

`.mount` 表示一个挂载点，unit 名由路径转义得到，例如 `/home` 对应 `home.mount`。systemd 也会从 `/etc/fstab` 生成 mount units，并根据路径层级和设备关系加入依赖。

不要同时随意维护冲突的原生 `.mount` 和 `/etc/fstab` 条目。一个错误的关键挂载可能把启动带入 emergency mode；改 `/etc/fstab` 前应备份并用不会真正破坏数据的方式验证语法和目标设备。

### target unit：分组与同步点

`.target` 本身通常不运行守护进程，而是把一组 units 拉到一起，或作为启动顺序中的同步点。常见例子：

- `basic.target`：基本用户空间初始化已具备；
- `multi-user.target`：多用户、非图形化系统服务集合；
- `graphical.target`：在多用户系统之上加入图形登录相关内容；
- `rescue.target`、`emergency.target`：用于不同程度的恢复环境；
- `default.target`：本机默认启动目标，通常链接到图形或多用户 target。

target 不是 SysV runlevel 的一一复制。多个 targets 可以同时 active，依赖图也不是一根只能前后移动的“级别指针”。

## 9. 依赖关系：需要谁，与谁先谁后是两回事

这是读 systemd unit 最重要的一条：**需求依赖与顺序依赖彼此独立。**

| 指令 | 回答的问题 | 不自动保证什么 |
| --- | --- | --- |
| `Wants=bar.service` | 启动我时，也尝试把 `bar` 拉入事务 | `bar` 失败时我一定失败；以及谁先启动 |
| `Requires=bar.service` | 启动我时，也以更强关系拉入 `bar` | 单凭这一行仍不规定谁先谁后 |
| `After=bar.service` | 如果双方都要启动，我排在 `bar` 完成启动之后 | 不会单独把 `bar` 拉入事务 |
| `Before=bar.service` | 如果双方都要启动，我排在 `bar` 之前 | 不会单独把 `bar` 拉入事务 |

常见组合是：

```ini
[Unit]
Wants=network-online.target
After=network-online.target
```

第一行提出较弱的需求，第二行规定双方都被激活时的顺序。即使如此，“`network-online.target` 已到达”具体意味着什么，也取决于网络管理器及 wait-online 服务的实现，不能自动推导成“互联网一定可用”。

`[Install]` 中的 `WantedBy=` / `RequiredBy=` 主要供 `systemctl enable` 创建相应依赖链接使用，不是 unit 每次加载时直接执行的命令。`enable` 与 `start` 的差别必须记牢：

```text
start    改变当前运行状态，不自动承诺下次开机
enable   改变未来如何被依赖拉入，不保证现在立刻运行
disable  移除相应 enable 链接，不会自动停止当前进程
mask     阻止各种方式激活该 unit，影响很强，排错时不要盲用
```

## 10. 用 systemctl 安全观察

以下命令以读取状态为主，不会启停 unit：

```bash
systemctl status systemd-journald.service --no-pager
systemctl is-active systemd-journald.service
systemctl is-enabled systemd-journald.service
systemctl list-units --failed
systemctl get-default
systemctl list-dependencies default.target
systemctl cat systemd-journald.service
systemctl show -p Wants,Requires,Before,After systemd-journald.service
systemctl list-timers --all
```

几个容易混淆的管理动作：

- `systemctl daemon-reload`：让 systemd 重新读取 unit 文件和生成器结果；它不等同于重启所有服务；
- `systemctl reload foo.service`：请求 **foo 自己**重读业务配置，前提是该服务支持 reload；
- `systemctl restart foo.service`：停止再启动服务，会造成中断；
- `systemctl edit foo.service`：创建或编辑 override，是写操作；提交前必须知道如何验证和撤销；
- `systemctl mask`：可能让关键服务甚至启动流程不可用，不能把它当成普通 disable。

远程服务器上停止网络、SSH、存储或认证相关 unit，可能立即切断唯一管理通道。任何会改变状态的命令，都应先确认 unit 名称、影响范围、替代登录通道与回滚方法；本课练习不要求执行它们。

## 11. 用 journalctl 从本次启动向后追

systemd-journald 收集来自 kernel、服务、标准输出 / 标准错误等来源的结构化日志。`journalctl` 是查询客户端。常用只读查询：

```bash
journalctl -b --no-pager                 # 本次启动
journalctl -b -1 --no-pager              # 上一次启动；需要历史日志仍被保存
journalctl -k -b --no-pager              # 本次启动的 kernel 日志
journalctl -u systemd-journald.service -b --no-pager
journalctl -p warning -b --no-pager
journalctl --since "today" --no-pager
```

`-f` 会持续跟随新日志，需要按 `Ctrl-C` 退出。普通用户能看到哪些日志取决于权限。日志还可能包含用户名、路径、网络地址、命令参数甚至应用误写的秘密，分享前应人工审阅和脱敏。

如果 `journalctl -b -1` 没有结果，不一定说明上次启动“没有报错”：日志可能只保存在 `/run/log/journal/`，重启后就消失；也可能因为权限、轮转或存储策略不可见。持久化策略是单独的管理课题，不要为得到一条旧日志就盲目改 journald 配置。

## 12. 正常关机与重启

在 systemd 系统上，常见的受控操作是：

```bash
systemctl reboot
systemctl poweroff
```

它们会真正中断会话，**不要为了练习执行**，尤其不要在远程、多人使用、正在写数据或升级中的机器上运行。正常关闭时，systemd 会停止 units、终止剩余进程、卸载文件系统或尽量重新挂载为只读、关闭 swap 和存储设备，最后调用 kernel 完成 reboot / poweroff。

`shutdown` 是许多管理员熟悉的兼容入口：`shutdown -h now` 请求立即关机，`shutdown -r now` 请求立即重启；使用 `+分钟数` 可以预约，`shutdown -c` 可取消尚未执行的预约。它们同样会改变整台机器的状态，而且不同系统的授权与实现可能不同。真正使用前，应先通知其他用户、确认维护窗口和远程回连方案；不要把这些命令当作本课练习。systemd 系统中优先用 `systemctl poweroff` / `systemctl reboot` 表达意图，也便于与对应 targets 和关机事务保持一致。

直接断电会跳过这些步骤，可能丢失缓存中的数据或使文件系统、数据库处于不一致状态。只有机器完全失去响应、受控关机不可用，并且已评估数据风险时，才把强制断电作为最后手段。

## 13. 与 SysV init 的对照

传统 SysV init 和 systemd 都可以承担 PID 1 与系统初始化职责，但表达方式不同：

| 维度 | SysV init 常见方式 | systemd 常见方式 |
| --- | --- | --- |
| 服务定义 | `/etc/init.d/` 下的 shell scripts | 声明式 `.service` 等 unit files |
| 启动集合 | 数字 runlevels 与 `rcN.d` 中的 S/K 链接 | targets 与依赖图 |
| 顺序 | 主要由脚本编号和串行流程表达 | `Before=` / `After=`，无约束工作可并行 |
| 依赖 | 脚本约定或有限元数据 | `Wants=`、`Requires=` 等显式关系与隐式依赖 |
| 按需激活 | 通常由各守护进程或额外工具处理 | socket、timer、path、D-Bus 等 activation |
| 进程归属 | 常依赖 PID files 和脚本自行跟踪 | unit + cgroup 跟踪进程集合 |
| 日志 | syslog 与各应用自己的日志 | journal 可统一索引，也可与传统日志共存 |

某些发行版仍为旧 init scripts、`service` 命令或 runlevel 名称提供兼容层，但兼容不等于模型相同。`multi-user.target` 大致承接传统 runlevel 3 的常见意图，`graphical.target` 大致承接 runlevel 5 的常见意图，却不能据此假设所有 unit 都有唯一的数字级别。

## 14. 按“最后成功阶段”排错

| 现象 | 优先怀疑的层 | 先做的低风险检查 |
| --- | --- | --- |
| 看不到固件画面，磁盘也未识别 | 硬件 / 固件 | 固件是否识别磁盘，电源与设备状态；不要先改 Linux 文件 |
| UEFI 可见，但没有启动项或直接回固件 | NVRAM / ESP / EFI 程序 | 从固件确认启动项；用救援环境只读检查 ESP 和 EFI 文件是否存在 |
| 能看到 bootloader 菜单，但提示找不到 kernel / initramfs | bootloader 配置与实际 `/boot` / ESP 内容 | 核对条目路径、分区是否在更新时正确挂载、文件是否成对存在 |
| kernel 已输出，但提示找不到根设备、解密失败或掉入 initramfs shell | kernel command line / initramfs / 存储栈 | 记录完整报错，核对 `root=`、设备标识、必需模块与 hooks；不要直接格式化或重建分区 |
| 已找到根文件系统，但进入 emergency mode | `/etc/fstab`、关键 mount 或早期 units | `systemctl --failed`、`journalctl -xb`；检查最近一次明确变更 |
| 已能登录，单个服务失败 | 该 service 及其依赖 | `systemctl status`、`journalctl -u ... -b`、`systemctl cat`；避免无证据重装 bootloader |
| 关机长时间卡住 | 停止作业、忙碌挂载或设备 | 若最终安全恢复，在下一次启动看 `journalctl -b -1`；确认哪个 unit 等待超时 |

### 一条稳妥的恢复顺序

1. 拍下或抄下**第一条具体错误**，不要只记录最后一句“failed”；
2. 选择启动菜单中已知可用的旧 kernel、fallback initramfs 或救援项；
3. 若必须使用 Arch 安装介质，先确认磁盘、根分区、ESP 和挂载关系，再进入安装环境修复；
4. 修改配置前保存原文件副本，并一次只改变一个假设；
5. 只有证据指向 initramfs 时才按当前 preset 重建；只有证据指向 bootloader 时才更新其条目或安装；
6. 在离开救援环境前，确认 kernel image、initramfs、module tree、启动条目和实际挂载点彼此一致；
7. 保留安装介质和一个已知可用启动项，直到新配置至少完成一次冷启动和一次正常关机。

> [!warning] 不要把修复命令当成猜谜按钮
> `mkinitcpio -P`、重新生成 GRUB 配置、重装 systemd-boot、改 NVRAM、`systemctl mask`、改关键 mount 或强制关机都会改变系统状态。没有精确布局、错误证据和恢复通道时，本课不建议执行这些命令。

## 15. 练习：只读绘制本机启动链

本练习只读取信息，不修改启动项、不启停服务、不要求 `sudo`。若某条命令在非 Arch 或容器环境中不存在，记录“不适用”及原因，不要为了完成清单安装或改配置。

### A. 识别固件与启动材料

```bash
if test -d /sys/firmware/efi; then echo "本次从 UEFI 启动"; else echo "未发现 UEFI 运行时目录，可能是 BIOS 或受限环境"; fi
lsblk -f
findmnt /boot
findmnt /efi
cat /proc/cmdline
```

`findmnt` 某个路径无输出可能只是本机没把分区挂在那里，不要据此创建目录或重新挂载。根据输出画出：磁盘 → ESP（若有）→ 实际挂载点 → kernel command line。

### B. 对照 kernel、modules 与 initramfs

```bash
uname -r
ls -l /boot
ls -ld /usr/lib/modules/*
```

若本机存在 `/boot/initramfs-linux.img` 且安装了 `lsinitcpio`，再执行：

```bash
lsinitcpio --analyze /boot/initramfs-linux.img
```

回答：当前运行 kernel 的 release 是什么？`/boot` 是否还存在其他 kernel / initramfs？module 目录是否与当前或待启动 kernel 有对应关系？不要删除看似“多余”的版本。

### C. 观察 PID 1 与 unit 图

```bash
ps -p 1 -o pid,comm,args=
systemctl get-default
systemctl list-dependencies default.target
systemctl status systemd-journald.service --no-pager
systemctl show -p Wants,Requires,Before,After systemd-journald.service
```

在容器、WSL 或特殊 initramfs 中，PID 1 未必是 systemd，`systemctl` 也可能无法连接 system manager；这正是环境差异，不要强行把 systemd 启动起来。

### D. 用日志确认边界

```bash
journalctl -k -b --no-pager
journalctl -u systemd-journald.service -b --no-pager
systemctl list-units --failed
```

从输出中各找一个“kernel 层事件”和“service 层事件”，写下它为什么属于这一层。无需把完整日志粘贴进笔记，更不要分享未脱敏的日志。

## 成功标准

- 我能在不查答案的情况下画出从 firmware 到 default target 的启动链，并指出每次跨越内核空间 / 用户空间的位置；
- 我不会把 UEFI、GPT、ESP、bootloader 混为一谈，能解释本机 ESP 的实际挂载点不一定是 `/boot`；
- 我能用“本体、可加载组件、早期临时用户空间”分别解释 kernel image、modules、initramfs；
- 我知道 initramfs 的 `/init` 与真实根文件系统中的 systemd 可能先后承担 PID 1 阶段；
- 我能说明 `Wants=` / `Requires=` 不负责排序，`After=` / `Before=` 不负责把对方拉入事务；
- 我能区分 `start` 与 `enable`、`daemon-reload` 与 service `reload`，并知道 `mask` 风险更高；
- 给出一次启动失败现象时，我会先锁定最后成功阶段、读取相应日志，再选择恢复动作；
- 我没有为了练习执行 reboot、poweroff、重建 initramfs、重装 bootloader、修改 ESP / NVRAM 或停用关键服务。

## 参考与范围

本课只使用以下一手资料，重点建立通用心智模型；命令和默认值可能随 systemd、kernel 与 Arch package 更新，实施变更前应再核对当前版本的 man pages 与 ArchWiki：

- [ArchWiki：Arch boot process](https://wiki.archlinux.org/title/Arch_boot_process)
- [ArchWiki：mkinitcpio](https://wiki.archlinux.org/title/Mkinitcpio)
- [ArchWiki：systemd-boot](https://wiki.archlinux.org/title/Systemd-boot)
- [ArchWiki：GRUB](https://wiki.archlinux.org/title/GRUB)
- [systemd：Bootup](https://systemd.io/BOOTUP/)
- [systemd(1)](https://www.freedesktop.org/software/systemd/man/latest/systemd.html)
- [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.socket(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html)
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [systemd.mount(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.mount.html)
- [systemctl(1)](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [shutdown(8)](https://www.freedesktop.org/software/systemd/man/latest/shutdown.html)
- [journalctl(1)](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)
- [Linux kernel：The kernel’s command-line parameters](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [Linux kernel：Early userspace support](https://docs.kernel.org/driver-api/early-userspace/early_userspace_support.html)
- [Linux kernel：initramfs buffer format](https://docs.kernel.org/driver-api/early-userspace/buffer-format.html)

---

**上一篇**：[[计算机知识/20-操作系统/01-Linux/01-计算机系统与Linux分层|01 · 计算机系统与 Linux 分层]] · **下一篇**：[[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|03 · 目录结构、挂载与文件系统]] · **返回 MOC**：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

### 磁盘配置与 manager 属性的对照

假定原 unit 的 `TimeoutStartSec=30`，磁盘 drop-in 改为 `5`，尚未 `daemon-reload`：`systemctl cat UNIT_NAME` 可显示新的磁盘片段，`systemctl show -p TimeoutStartUSec UNIT_NAME` 仍可能显示已加载的旧值。`show` 的规范化属性与 `status` 的运行状态也须分别读；重新加载 unit 定义不等于重启既有进程或重新载入应用配置。修改与 reload 需另获该系统的操作授权，本轮只给对照接口，实际 systemd 为 `not_run`。见 [systemctl cat/show 文档](https://man7.org/linux/man-pages/man1/systemctl.1.html)。
