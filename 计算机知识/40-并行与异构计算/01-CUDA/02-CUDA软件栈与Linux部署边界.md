---
type: lesson
domain: computer-science
stage: 2
status: ready
difficulty: 入门到中级
estimated_minutes: 75
verified_on: 2026-09-01
source: NVIDIA CUDA Installation Guide、CUDA Compatibility、Container Toolkit；ArchWiki
topics:
  - CUDA Driver
  - CUDA Runtime
  - CUDA Toolkit
  - Linux
  - 容器
  - Ubuntu
  - Arch Linux
tags:
  - computer-science/cuda
  - computer-science/linux
  - topic/deployment
---

# 02 · CUDA 软件栈与 Linux 部署边界

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/01-CPU与GPU异构执行模型|CPU 与 GPU 异构执行模型]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/03-Kernel与Grid-Block-Thread-Warp|Kernel 与执行层级]]

## 本课目标

学完后，你能：

1. 区分 host kernel driver、CUDA Driver API、Runtime API、Toolkit、数学库与框架；
2. 解释 Ubuntu 原生安装、Arch 发行版包和容器部署的不同支持边界；
3. 判断 `nvidia-smi`、`nvcc --version`、动态链接和实际程序各能证明什么；
4. 在不先卸载或混装的前提下，收集兼容性证据。

> [!warning] 本页默认只读
> 驱动安装/卸载会触及内核模块、图形桌面、Secure Boot、initramfs 和正在使用 GPU 的任务。不要把本页的层次图转换成“一键清理再重装”。真实变更前先保留可启动 kernel、远程/本地恢复入口和发行版包事务记录。

## 1. 六层不要混叫“CUDA”

```text
application / framework
  PyTorch, llama.cpp, your binary
        ↓
CUDA libraries
  cuBLAS, cuFFT, NCCL, ...
        ↓
CUDA Runtime API (cudart) 或直接使用 Driver API
        ↓
CUDA user-mode driver library (libcuda)
        ↓
NVIDIA host kernel driver + device nodes
        ↓
NVIDIA GPU

build/analysis side:
  CUDA Toolkit = nvcc + headers + development libraries + tools
```

| 层 | 主要职责 | 常见误解 |
| --- | --- | --- |
| host kernel driver | 控制设备、内存映射、中断等；由 host OS 管理 | 容器镜像能带来另一个可用内核驱动 |
| Driver API / `libcuda` | 用户态提交和管理 CUDA context/module | 与 `nvcc` 是同一个组件 |
| Runtime API / `cudart` | 更高层的设备、内存、stream、launch 接口 | 安装了 Python wheel 就一定有完整 Toolkit |
| Toolkit | 编译开发与分析工具、headers、库 | 每台只运行预编译程序的机器都必须装 `nvcc` |
| 数学/通信库 | 提供经过优化的领域算子 | 版本可与任意 runtime/driver 随意拼接 |
| 框架/backend | 选择、组合并调用下层实现 | 显示“CUDA available”就证明所有算子都在 GPU |

## 2. 版本问题要问完整句子

“CUDA 是什么版本？”至少可能指：

- host driver 宣称可支持到哪一代 CUDA 能力；
- `/usr/local` 或 `/opt` 中装了哪个 Toolkit；
- `nvcc` 来自哪个路径；
- 程序链接/携带了哪个 CUDA runtime 和库；
- Python 框架构建时面向哪个 CUDA 版本；
- 容器内用户态镜像基于哪个 Toolkit；
- 实际 GPU 的 compute capability 支持哪些指令/格式。

因此：

```bash
nvidia-smi
nvcc --version
command -v nvcc
```

三个结果回答不同问题。`nvidia-smi` 中的 `CUDA Version` 是驱动能力提示，不是“本机 Toolkit 安装版本”的充分证据；`nvcc --version` 也只证明当前 PATH 解析到的 compiler。最终仍要看程序加载的库、目标架构和运行结果。

## 3. 兼容性的两个方向

NVIDIA 文档把常见情况分为：

- **Backward compatibility**：较老 Toolkit 构建的应用通常可在较新的 driver 上运行；
- **Minor version compatibility**：CUDA 11 起，同一 major family 内，在满足最低 driver 等条件时可有限兼容，但新特性、PTX JIT 和目标架构等有附加条件；
- **Forward compatibility package**：特定数据中心 GPU/平台上的受控方案，不是消费者桌面“缺什么就装 `cuda-compat`”的通用补丁。

不要背一张会过期的最低驱动表。部署当天以目标 Toolkit 的 [Release Notes](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/) 与 [CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/) 为准，并记录 GPU、driver、Toolkit/runtime、目标架构和是否含 PTX。

## 4. Ubuntu 原生路径与 Arch 原生路径

截至 2026-09-01，NVIDIA CUDA Linux Installation Guide 的当前支持表列出具体 Ubuntu LTS 版本、kernel、GCC 和 glibc 组合；**Arch Linux 不在 NVIDIA 的 validated distribution table 中**。这形成两个不同支持模型：

| 项目 | Ubuntu（NVIDIA 列入目标版本时） | Arch Linux |
| --- | --- | --- |
| 支持来源 | NVIDIA 安装指南与 NVIDIA deb 仓库；也可使用 Ubuntu 自己的包，但版本/责任边界不同 | Arch 官方仓库与 ArchWiki 维护滚动组合；不是 NVIDIA 安装指南验证的发行版 |
| 更新模型 | LTS 基线相对稳定，按指南匹配 distro/version | kernel、compiler、driver、Toolkit 滚动更新，必须整体检查 |
| 常见路径 | NVIDIA 包按 deb 规则部署；具体 meta-package 随版本查指南 | Arch `cuda` 包当前把 Toolkit 放在 `/opt/cuda`；包名和环境方式以当日包元数据为准 |
| 故障责任 | 可对照 NVIDIA validated matrix | 先按 Arch 打包与滚动升级规则排查，再判断上游 CUDA 问题 |

### 只读盘点，不做安装

```bash
cat /etc/os-release
uname -r
lspci -Dnnk | grep -A3 -i -E 'vga|3d|nvidia'
command -v nvidia-smi
command -v nvcc
```

Ubuntu/Debian 系再查看已安装包：

```bash
dpkg-query -W 'nvidia*' 'cuda*' 2>/dev/null
apt policy cuda-toolkit nvidia-driver 2>/dev/null
```

Arch 再查看包数据库：

```bash
pacman -Q | grep -E '^(cuda|nvidia)'
pacman -Si cuda
```

这些查询可能因没有对应包而返回非零；它们不安装、不卸载。Arch 不支持 partial upgrade，背景见[[计算机知识/20-操作系统/01-Linux/08-pacman-apt-dnf与yum包管理|发行版包管理]]。驱动与内核模块证据链见[[计算机知识/20-操作系统/01-Linux/09-设备驱动内核模块与udev|设备驱动、内核模块与 udev]]。

## 5. Container 的正确边界

典型 GPU 容器分层是：

```text
host: GPU + NVIDIA kernel driver + compatible user-mode driver
  ↓ NVIDIA Container Toolkit 把设备和所需 driver 能力暴露给容器
container: CUDA runtime/Toolkit + libraries + application
```

容器解决用户态依赖打包与复现，不解决：

- host 没有 NVIDIA GPU；
- host driver 没加载或太旧；
- host 未配置 NVIDIA Container Toolkit/runtime；
- 镜像要求的 driver 能力高于 host；
- 程序未包含目标 GPU 可运行的 cubin/PTX，或依赖不兼容。

不要在普通 CUDA 容器里安装 host kernel driver。镜像 tag 中的 CUDA 版本描述容器用户态，不会升级 host driver。

容器、VM、namespace、cgroup 分别隔离什么，以及它们为何不能替代宿主驱动验收，见 [[计算机知识/20-操作系统/01-Linux/14-Linux开发容器与AI工作负载边界|Linux 开发、容器与 AI 工作负载边界]]。

## 6. 分层验收

| 检查层 | 证据 | 能证明 | 不能证明 |
| --- | --- | --- | --- |
| PCI/driver | `lspci -k`、内核日志、device nodes | 硬件被枚举、驱动可能绑定 | CUDA kernel 一定能运行 |
| 管理工具 | `nvidia-smi` | 管理库能与 driver/GPU 通信 | `nvcc` 存在；应用依赖兼容 |
| Toolkit | `command -v nvcc`、`nvcc --version` | 当前 compiler 路径与版本 | 当前 Python/容器实际使用它 |
| 动态链接 | loader/包元数据 | 二进制可能加载哪些库 | 数值正确或目标架构有效 |
| CUDA sample | `deviceQuery` 等 | runtime 与设备基本握手 | 真实应用性能与稳定性 |
| 应用 | 小型 correctness test | 特定路径可执行 | 所有 shape/dtype/backend 都正确 |

## 练习：画出两台机器的差异

场景 A：Ubuntu host 装 driver；容器带 Toolkit 与 PyTorch。场景 B：Arch host 用发行版 driver 与 `/opt/cuda`，本机编译原生程序。

分别写出：driver 在哪里更新、`nvcc` 在哪里、程序从哪里取得 runtime、谁负责兼容性、升级前要查什么。

### 成功标准

- 场景 A 不把 kernel driver 放进容器；
- 场景 B 不把 NVIDIA Ubuntu 仓库命令复制到 Arch；
- 两个场景都记录 host driver、用户态版本、GPU/compute capability 与实际程序验证。

## 核验来源

- [NVIDIA CUDA Installation Guide for Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [NVIDIA CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [NVIDIA Container Toolkit Architecture Overview](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/arch-overview.html)
- [ArchWiki：General-purpose computing on graphics processing units](https://wiki.archlinux.org/title/General-purpose_computing_on_graphics_processing_units)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/03-Kernel与Grid-Block-Thread-Warp|Kernel 与执行层级]] · **Linux 前置**：[[计算机知识/20-操作系统/01-Linux/13-ArchLinux安装后配置维护与安全|Arch 安装后维护与安全]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
