---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 入门到进阶
estimated_minutes: 45
topics:
  - Linux
  - 容器
  - cgroup
  - 开发环境
  - CUDA
  - AI 工程
tags:
  - computer-science/linux
  - computer-science/container
  - computer-science/development-environment
---

# Linux 开发、容器与 AI 工作负载边界

“在我的机器上能跑”可能只证明了某个 Python 环境、某个 C++ 二进制、一个容器或一张 GPU 的一小段链路。要可靠复现或排错，先把问题放回正确的边界：宿主 kernel 和驱动、用户空间依赖、进程隔离、数据挂载、网络监听、资源限制，分别由谁负责？

## 本课目标

- 区分原生进程、Python 虚拟环境、容器与虚拟机各自隔离什么、没有隔离什么；
- 解释 namespace、cgroup、kernel driver、用户态 runtime 和 AI 工作负载之间的顺序；
- 为 Python、C++、CUDA 或 AI 服务选择一组只读、可观察的证据；
- 知道何时停止：证据不足时不重装驱动、不追加全局 `PATH`、不授予特权容器，也不把端口直接暴露到网络。

> [!important] 本课不安装 runtime，也不运行容器
> 下面的观察命令不创建容器、不修改 cgroup、不改变网络、挂载或驱动。Docker、Podman 是容器工具/引擎；Kubernetes 是编排平台，由节点 kubelet 通过 CRI 接口调用 containerd、CRI-O 等运行时。见 [Kubernetes 概览](https://kubernetes.io/docs/concepts/overview/) 与 [节点容器运行时](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)；先理解边界，再根据所在平台的**官方文档**选择一个运行时学习。不要复制不明镜像、`curl | sh` 安装脚本、`--privileged`、host network/host PID 或把宿主敏感目录挂入容器的示例。

## 1. 四种“隔离”解决的不是同一个问题

| 层 | 典型对象 | 主要解决什么 | 它不自动保证什么 |
| --- | --- | --- | --- |
| 进程与用户 | 原生 Python/C++ 程序 | 每个进程的地址空间、UID/GID 和文件权限边界 | 依赖版本隔离、资源上限、网络最小暴露 |
| 语言环境 | Python `venv`、Conda 等 | Python 解释器/包版本的项目隔离 | kernel、系统库、GPU driver 或安全沙箱 |
| 容器 | 一个 runtime 创建的容器 | 通过 namespace 改变可见的进程、网络、挂载或用户视图；常结合 cgroup 记账/限制资源 | 独立 kernel、绝对安全、宿主数据不可见、GPU 一定可用 |
| 虚拟机 | 完整 guest OS | guest kernel 与宿主 kernel 的边界、独立启动链和虚拟硬件 | 自动具备正确驱动、备份或安全配置 |

容器不是轻量 VM：容器内进程仍由宿主 Linux kernel 调度和执行系统调用。cgroup 是 kernel 用来按层次组织进程并分配/限制资源的机制；它不是“容器专属功能”，systemd 也会用 cgroup 组织 unit，启动与服务关系见 [[计算机知识/20-操作系统/01-Linux/02-启动链Kernel与systemd|启动链、Kernel 与 systemd]]。namespace 与 cgroup 一起能形成很有价值的隔离和资源治理，但安全强度取决于运行时、内核、权限、挂载、设备与网络配置。

## 2. 一张工作负载边界图

```text
项目代码与依赖
  ├─ Python：解释器 + venv/包锁定
  ├─ C++：编译器 + 头文件/库 + 链接产物
  └─ AI：模型、tokenizer、配置、缓存、checkpoint
              ↓
进程或容器运行时
  ├─ PID / mount / network / user namespace（可选、依 runtime 而异）
  └─ cgroup：CPU、内存、I/O、PID 等资源的组织与限制
              ↓
进程可见的用户空间
  ├─ 原生进程：宿主环境中的 libc、解释器、应用库与 runtime
  └─ 容器进程：镜像内的 libc、解释器、应用库与 CUDA runtime
              ↓
容器集成：设备节点、挂载视图与兼容的 user-mode driver library
              ↓
宿主 Linux kernel：调度、内存、VFS、网络栈与 kernel-mode driver
              ↓
CPU、存储、网卡、GPU 等硬件
```

图中的“挂载视图”是 mount namespace 让进程看到的文件系统树，不等于容器拥有一套独立宿主文件系统。箭头也不能倒过来推理。例如：Python 能 `import torch`，只证明当前解释器找到了包；它不证明 NVIDIA 内核驱动、GPU runtime、设备权限、显存容量、模型格式或一次真实推理都已通过。反过来，`lspci` 看见 GPU 也不证明项目的 Python/C++ 依赖正确。

## 3. 开发工具链：只在自己的作用域解决自己的问题

### Python：项目依赖不等于系统软件

Python 项目应把解释器版本、依赖约束、激活方式和可复现命令记录在项目内；先用项目的环境验证，再改全局配置。`venv` 不负责安装内核、编译 NVIDIA 驱动、管理 systemd service 或隔离宿主文件。具体模型见 [[计算机知识/10-编程语言/01-Python/09-venv与虚拟环境原理|venv 与虚拟环境原理]]，系统包与 Python 包的责任分界见 [[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|包管理课程]]。

### C++：编译成功不等于可部署

C++ 的源代码、编译器、头文件、链接库和最终二进制是不同证据。构建机上的 `PATH` 或 `CXX` 只能影响选择哪个工具，不能消除 ABI、动态库、CPU 指令集或目标系统差异。应先在项目记录里写清工具链与构建类型，再检查目标系统实际加载到的库。基础调用链见 [[计算机知识/10-编程语言/02-C++/01-编译链接与CMake|编译、链接与 CMake]]。

### GPU 与 CUDA：至少跨三层验收

CUDA 类工作负载通常要分别确认：

1. **硬件/内核层**：设备被枚举，正确 driver 绑定，firmware 或 kernel 日志没有已知阻断错误；
2. **用户态层**：CUDA runtime、项目依赖与所选编译/运行路径兼容；
3. **工作负载层**：一个最小程序或模型操作成功，然后才把它升级为真实数据、显存和吞吐测试。

驱动更新、kernel 切换、DKMS、Secure Boot、容器 GPU 设备直通都会改变这一链路，不能用“再装一次”代替定位。先完成 [[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]] 的只读证据，再进入 [[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]。

## 4. 只读建立你的运行边界证据

在当前 Linux、VM 或容器中运行；缺失工具或不同输出是环境事实，不要为了让页面示例一致而安装软件或提升权限。

```bash
uname -r
ps -p 1 -o pid,comm,args=
findmnt -T /
cat /proc/1/cgroup
test -r /sys/fs/cgroup/cgroup.controllers && cat /sys/fs/cgroup/cgroup.controllers
```

按行写下结论：正在使用哪个 kernel？此视图中的 PID 1 是谁？根目录来自什么挂载？PID 1 隶属哪些 cgroup hierarchy？若存在 cgroup v2 控制器文件，当前 kernel 在这个 hierarchy 暴露了哪些可用 controller？不要把 `/proc/1/cgroup` 的单行路径、控制器列表或“看到 Docker 字样”当作安全证明；它们只是诊断线索。cgroup v1/v2、混合 hierarchy 和 rootless runtime 的具体输出会不同。

再用与现象对应的课程补齐证据，不要把所有命令一次性跑完：

| 现象 | 先看 | 仍不能证明什么 |
| --- | --- | --- |
| `python` / `cmake` / `nvcc` 找不到 | `command -v`、`type -a`、项目文档 | 添加一个目录后项目一定正确 |
| 服务端口从某处连不上 | 对应网络视图的 `ss -lnt`、`ip route`、最小时间窗口日志 | 防火墙、DNS、代理、认证与外部入口已经正确 |
| 模型下载或 checkpoint 写入失败 | `findmnt -T <实际路径>`、`df -hT <实际路径>`、`df -ih <实际路径>` | 删除缓存一定安全，或宿主与容器在同一存储卷 |
| GPU 库加载或计算失败 | 硬件/driver 日志、用户态 runtime 版本、最小程序 | GPU 已被正确共享给容器，或真实模型能跑 |

网络、存储和日志的逐层方法见 [[计算机知识/20-操作系统/01-Linux/10-网络存储日志与故障排查|网络、存储、日志与故障排查]]；环境变量的继承与 PATH 解析见 [[计算机知识/20-操作系统/01-Linux/07-环境变量Shell启动与PATH|环境变量、Shell 启动与 PATH]]。

## 5. 资源与故障：把“被限制”与“程序坏了”分开

内存不足、PID 上限、CPU/I/O 配额、磁盘/inode 耗尽和 GPU 显存不足都可能表现为崩溃、变慢或服务不响应。首先记录时间、退出码、可复现命令、实际数据路径、同一 cgroup/容器的资源限制以及日志中的 OOM 或错误线索；然后只改变一个经证据支持的变量。

不要把宿主 OOM、cgroup memory limit、Python `MemoryError`、GPU OOM 和磁盘满归为同一种“内存不够”。它们的所有者和恢复手段不同：有时应缩小 batch、清理**已确认可重建**的项目缓存、调低并发或增加经批准的资源；有时必须先备份或修复存储/服务配置。永久提高资源限制、关闭限制、清 journal、删除模型/卷或重启生产服务，都不是这节课的练习动作。

## 6. AI 服务的最低安全边界

启动本地模型服务前，先回答：谁能访问它、它监听在哪个地址、是否需要认证、模型/日志/缓存放在哪里、哪些目录可写、用哪个非特权账户运行、发生升级或崩溃后怎样恢复。默认绑定 loopback 或 Unix socket 能缩小暴露面，但仍需要按使用场景验证；绑定 `0.0.0.0` 或在容器发布端口之前，必须有明确的网络、认证、TLS 和审计设计。

模型、提示、请求体和日志可能含敏感信息。容器镜像、卷和 build context 也可能意外携带 `.env`、SSH 密钥或缓存；在构建或共享前使用 allowlist 思维，避免把整个家目录、仓库或 Docker socket 交给运行时。私有服务的认证/TLS/许可证边界见 [[AI/20-LLM/70-工程应用与工具链/05-私有部署认证TLS与边界|私有部署认证、TLS 与边界]]；硬件、量化与真实模型验收分层见 [[AI/20-LLM/40-推理/04-推理显存量化与硬件路线|推理显存、量化与硬件路线]]。

## 练习：写一个不执行部署的工作负载计划

任选一个目标，例如“本地 Python API”“C++ CLI”或“GPU 模型推理”，在下面模板中填空；不安装、不启动、不暴露任何服务。

```text
目标与成功标准：
代码/依赖来源及版本记录：
执行环境：原生进程 / venv / 容器 / VM（选择理由）：
宿主 kernel 与驱动证据：
实际数据、缓存与日志路径，以及挂载/备份关系：
监听地址、认证与允许访问者：
资源预算：CPU / 内存 / 磁盘与 inode / GPU 显存：
最小只读证据：
最小可回退变更（若需要）：
恢复或停止方式：
```

## 完成标准

- [ ] 我能解释 venv、容器和 VM 各自隔离的对象，并指出它们不替代的系统层；
- [ ] 我能画出一次 AI/GPU 工作负载从项目依赖到宿主 driver 的链路，且不把任一单点检测当成全链路通过；
- [ ] 我能使用只读命令描述当前 PID 1、根挂载和 cgroup 线索，并知道它们不是安全证明；
- [ ] 我会把端口、认证、数据卷、日志、资源预算和恢复写入计划，而不以 `--privileged` 或 host 挂载换取“先跑起来”；
- [ ] 我能将问题分别交给 Python 环境、C++ 工具链、CUDA 部署、网络/存储日志或 AI 服务安全页面，而不是混成一个“Linux 配置问题”。

## 一手参考

- [Linux kernel documentation：Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)：cgroup 的层级、controller、资源分配与用户可见接口；本课不包含对接口文件的写操作。
- [Linux kernel documentation：Namespaces](https://docs.kernel.org/admin-guide/namespaces/index.html)：namespace 的类型、隔离对象与内核视角。
- [systemd.resource-control(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)：systemd unit 与 cgroup 资源控制的关系；不要把该文档的配置键直接用于未知服务。
- [NVIDIA Container Toolkit Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)：当且仅当你已选择 NVIDIA 官方容器工具链时，用于现场核验支持矩阵和安装步骤；具体版本和发行版步骤会变化。

---

**上一课**：[[计算机知识/20-操作系统/01-Linux/13-ArchLinux安装后配置维护与安全|13 · Arch Linux 安装后配置、维护与安全]] · **返回 MOC**：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础 MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]] · [[AI/20-LLM/40-推理/04-推理显存量化与硬件路线|AI 推理硬件路线]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/20-操作系统/01-Linux/10-系统课程/02-文件描述符管道与进程控制|Linux 进程与文件描述符：用小实验理解共享状态]]
- [[计算机知识/20-操作系统/01-Linux/10-系统课程/03-权限身份与最小授权|Linux 权限：文件能不能删，为什么不只看文件写位]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
