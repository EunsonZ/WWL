---
type: lesson
domain: computer-science
stage: 18
status: ready
difficulty: 进阶
estimated_minutes: 95
topics:
  - CPU拓扑
  - 缓存一致性
  - NUMA
  - first-touch
  - affinity
  - IOMMU
tags:
  - computer-science/systems
  - computer-science/memory
  - computer-science/performance
  - computer-science/heterogeneous-computing
---

# CPU 拓扑、缓存一致性、NUMA 与设备亲和性

## 本课目标

学完后，你应该能够：

- 分清 logical CPU、physical core、package/socket 与 NUMA node；
- 解释缓存一致性解决“多个缓存副本最终如何协调”，而内存一致性模型解决“程序允许观察到什么顺序”；
- 用 first-touch 与调度迁移解释本地/远端内存访问，但不把它当跨平台强保证；
- 把线程、数据、GPU/NIC 与 PCIe/NUMA 路径放在同一亲和性图中；
- 在容器、虚拟机和异构设备环境中保留观测边界，不凭一个 CPU 数字推断整机拓扑。

## 1. 四个 CPU/内存层级不是同义词

| 层级 | 含义 | 常见关系与例外 |
| --- | --- | --- |
| Logical CPU | OS 可调度执行上下文，常对应 hardware thread | SMT 核心可暴露多个 logical CPU；配额/cpuset 可能只允许其中一部分 |
| Physical core | 共享一组核心执行资源的物理核心 | core 内 logical CPU 会竞争部分资源；具体共享项依微架构 |
| Package/socket | 一颗封装 CPU 或主板插槽层级 | 多 chiplet 封装仍可能有更细内部拓扑；package id 不等于性能距离 |
| NUMA node | 对一组 CPU/设备具有某种本地内存距离的 OS 拓扑域 | node 可跨内部组件；虚拟机/容器看到的 node 也可能是抽象视图 |

```text
Machine
├─ Package 0
│  ├─ NUMA node 0 ─ memory A
│  │  ├─ Core 0 ─ logical CPU 0, 1
│  │  └─ Core 1 ─ logical CPU 2, 3
│  └─ NUMA node 1 ─ memory B
└─ Package 1 ...
```

这是示意，不是“一个 socket 必有两个 node”或“每核必有两个线程”的断言。Apple Silicon、x86 server、Arm server、虚拟机和混合性能/能效核心的拓扑不能硬套一张图。

## 2. `os.cpu_count()` 不是“我能独占的物理核数”

语言运行时可能返回系统 logical CPU 数，也可能受到平台 API 影响。进程实际可运行集合还受 affinity、cpuset、容器配额、作业调度器和虚拟机 vCPU 限制：

```text
主机在线 logical CPUs
       ∩ cpuset / affinity 允许集合
       ∩ 容器或作业系统暴露视图
       + 时间配额与其他进程竞争
= 当前任务实际可利用的执行资源（仍会随时间变化）
```

CPU quota 甚至可能允许在多个 logical CPU 间迁移，却只给总时间份额。于是“能看到 32 个 CPU”不等于“拥有 32 核吞吐”。反过来，只读 sysfs 的 `cpu0..cpuN` 也可能包含 offline CPU；严谨工具还要检查 online/allowed 状态。

## 3. 缓存层级与共享边界

一个 core 的 logical CPU 常共享 L1/L2 的一部分或全部；多个 core 可能共享末级缓存的切片/目录。具体是 inclusive、exclusive、non-inclusive，容量如何切分、chiplet 间怎样连接，都依微架构。

对共享数据的关键不是“每核有一份永不变化的缓存”，而是硬件一致性协议维护缓存行状态与所有权。当一个核心写入某行，其他核心持有的副本必须失效、更新或按协议协调，才能让系统维持规定的一致性。

MESI/MOESI 名称适合建立直觉，但现代实现还有目录、snoop filter、互连与大量状态细节。不要从协议缩写推断具体延迟，也不要把它当成语言内存模型。

## 4. 缓存一致性不等于内存一致性/语言 happens-before

- **Cache coherence**主要约束同一缓存行/地址的副本如何协调；
- **Memory consistency model**约束多个地址的操作可按什么顺序被观察；
- **语言内存模型**规定数据竞争、atomic、fence、锁与 happens-before 的程序语义。

即使硬件缓存完全 coherent，没有同步的数据竞争仍可能在 C++ 中产生未定义行为。反之，正确使用 mutex/atomic 的程序由语言与库契约建立顺序，不能靠“这个 CPU 很强一致”替代同步。

详见 [[计算机知识/30-计算机系统/09-进程线程调度同步与IPC|进程、线程、调度、同步与 IPC]]。

## 5. 真共享、伪共享与只读共享

- **真共享：**多个线程读写同一逻辑变量，需要同步并转移最新值；
- **伪共享：**线程写不同变量，但变量落在同一 coherence granule/cache line，引发无谓所有权转移；
- **只读共享：**初始化完成后多核只读同一数据，通常不需要行所有权来回转移。

伪共享优化不能只靠“填充 64 字节”。真实 cache-line 大小、对象数组布局、编译器 alignment、工作集膨胀和访问比例都要观测。把每个对象扩大可能减少争用，也可能让缓存容量与带宽更差。

## 6. NUMA：访问距离不再完全对称

NUMA 系统中，每个处理器仍可访问整个共享地址空间，但访问本地 node 的内存通常更近；远端访问要经过 socket/chiplet 互连。**通常**不等于永久保证：内存控制器、interleave、迁移、自动 NUMA balancing、虚拟化和负载会改变路径。

NUMA 优化的基本对象是三者配对：

```text
执行线程在哪里运行
        ×
数据物理页位于哪个 node
        ×
设备挂在哪个 I/O/NUMA 路径
```

只固定线程却不移动/重新建立数据 locality，可能让线程稳定地远端访问；只把页面放在某 node，调度器又可能把线程迁走。

## 7. First-touch 是常见策略，不是语言保证

在许多 Linux NUMA 配置中，匿名页的物理位置常由首次写 fault 发生时的线程位置和当前 memory policy 决定，因此并行初始化常用于让各线程“first-touch 自己将处理的页”。

```text
主线程串行初始化全部数组
  → 页面可能偏向主线程所在 node
  → 后续其他 node 工作线程可能远端访问

工作线程并行初始化自己的连续分片
  → 在常见 first-touch 策略下，页面可能更接近未来使用者
```

必须保留限定词：显式 policy、interleave、huge page、页迁移、共享文件页、容器限制、虚拟机或非 Linux 平台都可能改变结论。一次 `memset` 的计时也不能直接证明页面 node；应使用获准的映射级 NUMA 统计或平台工具验证。

## 8. Affinity 是控制变量，也是风险

CPU affinity 限制线程/进程可在哪些 logical CPU 运行；NUMA memory policy 控制分配/绑定/交错倾向；两者不是同一个设置。合理实验可能固定位置以减少迁移噪声，但错误绑定会：

- 把多线程都挤到同一 core 的 SMT siblings；
- 破坏调度器负载均衡与能效策略；
- 让线程远离数据或设备；
- 在容器/作业系统中违反已分配 CPU 集；
- 留下难以发现的进程状态变化。

因此本课实验**只读** allowed CPU 与拓扑，不调用 `taskset`、`numactl --membind`、`sched_setaffinity` 或系统设置。若未来要做控制实验，应在专用进程中记录原集合、使用精确 PID、设置退出恢复，并得到明确授权。

## 9. 设备亲和性：GPU/NIC 也有拓扑位置

独立 GPU、NIC、NVMe 通过 PCIe root complex、switch 或 CPU I/O die 接入。多 socket 系统中，设备通常更接近某个 NUMA node。数据路径可能是：

```text
CPU thread → local/remote host memory → IOMMU/IOTLB → PCIe → GPU/NIC
GPU ↔ GPU：PCIe switch / peer-to-peer / NVLink 等（平台与许可依赖）
```

若生产者线程、host buffer 与 GPU 位于不同 node，可能增加互连流量；支持 GPUDirect/RDMA/P2P 也不等于当前传输必然走该路径。需要同时核对设备拓扑、驱动能力、IOMMU 模式、实际 API 和传输 trace。

IOMMU group 是隔离/直通粒度的重要线索，但 group 数量不是带宽或延迟指标。CPU 页表、GPU 页表和 IOMMU 页表仍是不同翻译域，详见 [[计算机知识/30-计算机系统/16-地址翻译TLB页表遍历与大页|地址翻译、TLB、页表遍历与大页]]。

## 10. 跨平台只读拓扑证据

### Linux

- `/sys/devices/system/cpu/cpu*/topology/` 可暴露 core/package 等 ID；
- `/sys/devices/system/node/node*/cpulist` 可暴露 node CPU 集；
- `/proc/self/status` 与 `sched_getaffinity` 可提供进程视角的一部分；
- `/sys/kernel/iommu_groups` 存在与可读性取决于内核、硬件、启动参数与容器视图。

### macOS

系统能报告 logical/physical CPU 数与硬件信息，但 Apple Silicon 的 performance/efficiency core、统一内存与 GPU 拓扑不应翻译成传统多 socket NUMA 图。缺少 Linux sysfs 时配套程序输出 `SKIP`，而不是猜测 node 数。

### Windows

Processor groups、NUMA nodes、processor sets 与 working set/commit 都有自己的 API 语义；超过单个 group 的机器尤其不能只用一个传统 affinity mask。应使用与目标 Windows 版本匹配的系统 API/文档。

### 容器与虚拟机

容器读取到的 `/sys` 可能是宿主拓扑，而 cgroup 只允许子集；虚拟机看到的是 hypervisor 暴露的 vCPU/vNUMA。任何报告都要同时记录“可见拓扑”和“进程允许集合”，不能声称发现了不可见的物理布线。

## 11. 证据强度与性能边界

| 观察 | 能证明 | 不能证明 |
| --- | --- | --- |
| logical/core/package/node ID | OS 当前暴露的拓扑关系 | 实际 cache capacity、互连延迟或独占资源 |
| allowed CPU 集合 | 当前进程可被调度到的 logical CPU 集 | 时间配额、无竞争吞吐、线程此刻所在 CPU |
| NUMA node cpulist | node 与 CPU 的 OS 映射 | 某个 buffer 的物理页真的在该 node |
| IOMMU groups | 可见的设备隔离分组 | DMA/IOTLB 命中、P2P 可用或传输性能 |
| 两组 benchmark 时间 | 当前条件下的端到端计时 | 单独归因于 NUMA、coherence 或 TLB |

“拓扑更近”是要验证的假设，不是性能保证。固件、频率、热限制、互连拥塞、内存通道、功耗策略、编译选项和调度都会改变结果。

## 12. 配套实验

[[计算机知识/80-实践/06-计算机系统/06-地址翻译分配器与拓扑观察/README|地址翻译、分配器与拓扑观察]] 会：

- 报告运行时 logical CPU 数；Linux 可用时只读 allowed CPU 集；
- 从可读 sysfs 汇总 logical/core/package/node；
- 只统计可见 IOMMU group 目录，不读取设备配置、不发起 DMA；
- 对缺失能力输出 `SKIP`；
- 不改变 affinity、NUMA policy、sysctl 或设备设置。

这些结果只验证观察程序和本机暴露视图，不能推出最优线程数、绑定策略或性能结论。

## 练习

1. 给定 2 sockets × 2 NUMA nodes/socket × 16 cores/node × 2 threads/core，计算 logical CPU、core、socket、node 数；再解释容器只允许 12 个 logical CPU 时哪些数字仍可能可见。
2. 画出两个线程写相邻计数器的 cache-line 所有权变化，再改成线程局部计数后归并；列出减少共享写带来的代价。
3. 一个数组由 node 0 主线程串行初始化，之后 node 1 线程处理。提出 first-touch 假设、需要读取的页面位置证据和一个可恢复的后续实验设计。
4. 为双 GPU 服务器画出 CPU package、NUMA memory、PCIe switch 与 GPU；说明仅知道 GPU 型号为什么不足以选择数据加载线程。

## 成功标准

- 能准确换算 logical CPU、core、package/socket 与 node，不把 SMT thread 当独立物理核；
- 能分别解释 cache coherence、硬件/语言内存顺序与同步；
- first-touch 结论始终带有 OS policy、首次写位置和页面级证据边界；
- 能同时考虑线程、数据、设备三个位置，而不是只做 CPU 绑核；
- 只读拓扑结果不会被包装成跨平台性能保证。

---

**上一站**：[[计算机知识/30-计算机系统/17-通用内存分配器Arena碎片与驻留|通用内存分配器、Arena、碎片与驻留]] · **下一站**：[[计算机知识/30-计算机系统/19-容器虚拟机Namespace-Cgroup与虚拟IO|容器、虚拟机、Namespace、Cgroup 与虚拟 I/O]] · **实验**：[[计算机知识/80-实践/06-计算机系统/06-地址翻译分配器与拓扑观察/README|地址翻译、分配器与拓扑观察]] · **相关**：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/30-计算机系统/10-组成原理系统课程/05-缓存地址划分与AMAT|缓存地址划分与 AMAT：从一次地址访问算起]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
