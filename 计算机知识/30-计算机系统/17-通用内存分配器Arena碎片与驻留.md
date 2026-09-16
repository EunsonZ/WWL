---
type: lesson
domain: computer-science
stage: 17
status: ready
difficulty: 进阶
estimated_minutes: 90
topics:
  - 内存分配器
  - Arena
  - 碎片
  - 驻留集
  - allocator-cache
tags:
  - computer-science/systems
  - computer-science/memory
  - computer-science/performance
---

# 通用内存分配器、Arena、碎片与驻留

## 本课目标

学完后，你应该能够：

- 从语言对象一路追到 allocator、虚拟映射和物理驻留，解释每层维护的不同账本；
- 区分 **reserved、committed、resident、live 与 allocator cache**；
- 解释 arena、size class、线程缓存怎样减少分配成本，也怎样保留高水位；
- 分开诊断内存泄漏、内部碎片、外部碎片、分配器缓存与工作集增长；
- 设计不会依赖“free 后 RSS 必须立即下降”的正确性测试。

## 1. “分配了多少内存”没有单一答案

```text
语言/业务对象
  live requested bytes：仍在生命周期内、业务请求的字节
          │
          ▼
通用分配器 / runtime
  size class、chunk、arena、thread cache、元数据、对齐与空闲块
          │
          ▼
操作系统虚拟内存
  保留地址范围、提交/后备承诺、匿名或文件映射
          │
          ▼
主存与交换/压缩
  当前驻留页、共享页、可回收页、被换出的页
```

一次 `new`/`malloc` 可能只从线程缓存取出已有块，完全不进入内核；一次大分配可能建立独立映射；一次 `free` 可能只把块还给 size class，不取消映射。实现、版本、大小和平台都会改变路径。

## 2. 五个最容易混淆的口径

| 口径 | 本课中的含义 | 典型误解 |
| --- | --- | --- |
| Reserved | 为某用途保留的虚拟地址范围或容量；精确定义依 OS/API | “已经占用同样多物理 RAM” |
| Committed | OS 已为虚拟页提供某种后备承诺/可用性记账；Windows 术语最明确，Unix overcommit 语义不同 | “这些页现在都 resident” |
| Resident | 当前有物理主存支撑并计入某种驻留统计的页 | “全是该进程独占且不可回收” |
| Live | 程序/分配器视角仍被有效对象占用的请求 | “等于 allocator 从 OS 获得的总量” |
| Allocator cache | 已不 live、但分配器保留以供未来复用的块或 arena | “一定是泄漏”或“已经还给 OS” |

`reserved` 与 `committed` 在 Windows、Linux、macOS 上不是可随意互换的统一指标。Linux `mmap`、overcommit、实际 fault 与 cgroup charge 会共同影响可用性；macOS 还有压缩内存等机制。跨平台报告应保留工具原名与定义，不要强行翻译成一列数字。

## 3. Arena：用批量生命周期换取快速分配

最简单的 bump arena 持有一块连续存储和一个 cursor：

```text
arena 起点
│ object A │ pad │ object B │ object C │                未用尾部 │
^                         ^                                  ^
base                    cursor                            capacity
```

分配时对齐 cursor、前移并返回区间；单个对象通常不归还，整个阶段结束时一次 reset 或销毁 arena。这使热路径只有少量算术，元数据也集中，但代价是：

- 生命周期必须适合批量释放；
- 早已不用的对象在 reset 前仍占用 arena 容量；
- 峰值决定 arena 可能长期保留的 backing storage；
- 对齐 padding 与未使用尾部造成浪费；
- arena reset 只改变逻辑账本，不必清零、decommit 或取消底层映射。

因此“arena 的 `live_requested=0`”不等于 RSS 立即减少。配套 C++ 实验只验证容量、alignment、non-overlap 与 reset 账本；它明确不把 `std::vector` 容量叫作 OS commit。

## 4. 通用分配器为何使用 size class、span 与线程缓存

通用分配器要支持任意交错生命周期，常把请求向上归入 size class，再从 page/span/run 切出块。小块可以进入每线程缓存，减少全局锁和跨核争用；中央结构在缓存不足时补充，缓存过多时再批量回收。大块可能走独立映射路径。

假设请求 33 B，而 size class 给出 48 B：业务 `live` 是 33 B，块容量是 48 B，另有元数据和承载这个块的 page/span。只加总请求大小会漏掉内部碎片；只看 arena 总量又会把可复用空闲块当成 live。

这些名称不是稳定 ABI。glibc malloc、jemalloc、tcmalloc、语言 runtime 与 GPU framework 的结构、统计项和回收策略不同。分析前要确认进程实际链接/使用的 allocator 版本与配置。

## 5. 内部碎片与外部碎片

**内部碎片**是已分配块内部无法被当前请求利用的空间，常来自 size-class 向上取整、alignment 与对象布局。例如 33 B 请求得到 48 B 块，15 B 对当前对象不可用。

**外部碎片**是空闲空间存在但分布在不合适的块、span 或地址区间，无法满足某个更大/特定对齐请求。分配器可能有足够总空闲量，却仍需从 OS 获取新区域。

还有两个容易混进“碎片”的量：

- **元数据开销：**free list、bitmap、边界标记、arena 描述符；
- **未归还缓存：**可立即给同类未来请求复用，但尚未 decommit/unmap 的页。

诊断报告应分别列示，而不是用 `(RSS - live)` 全部命名为 fragmentation。差值还可能包含代码、栈、共享库、页表、JIT、文件页以及测量时刻变化。

## 6. 为什么 `free` 后 RSS 可能不下降

对象生命周期结束后，至少可能经历这些层级：

```text
live 对象 → allocator 空闲块 → 空闲 span/arena → 可回收或已归还 OS → 不再 resident
```

每个箭头都不是自动发生：

- 分配器保留块以加速下一次相同 size class 分配；
- 一个 span 中还有少量 live 块，整页不能归还；
- OS 接受 discard/decommit 提示，却延迟回收或保留虚拟映射；
- RSS 是采样快照，统计更新和共享归因有延迟；
- Linux、macOS、Windows 的 RSS/working set/commit 口径不同。

所以正确性测试应断言“释放后不可再访问、析构/所有权契约成立、allocator 统计符合其文档”，而不是断言“RSS 必须下降某个精确值”。若服务的峰值驻留影响容量，仍应做同负载的时间序列与稳定期观测。

## 7. 泄漏、缓存、碎片与真实工作集增长的诊断矩阵

| 现象 | 更直接的候选证据 | 不能只凭 |
| --- | --- | --- |
| Live 对象持续增长 | heap profile、对象/请求生命周期计数、所有权 trace | 单点 RSS |
| Allocator cache 高水位 | allocator 自身的 allocated/active/resident/mapped 等统计及版本定义 | “free 调了很多次” |
| 内部碎片 | 请求大小与实际 size class/usable size 分布 | 虚拟地址总量 |
| 外部碎片 | 空闲 span 分布、无法复用而新增映射的证据 | `RSS - live` 一个差值 |
| 工作集增长 | 同口径 RSS/PSS/working-set 时间序列与页面活动 | allocator live bytes |
| GPU 缓存保留 | 运行时的 allocated 与 reserved/cached 指标、设备工具 | 主机 RSS |

诊断顺序可以是：固定输入与并发 → 记录语言/allocator/OS/GPU 多层时间序列 → 在增长窗口获取 heap profile → 对照请求完成与 GC/trim/缓存回收事件 → 才判断是 leak、cache 还是 workload shift。

## 8. 线程缓存与 NUMA 的交叉影响

线程缓存减少共享锁，却可能让多个线程各自保留一组 size class 高水位；线程数增长时，总缓存上限也可能增长。若 arena 由一个 NUMA node 上的线程首次触碰，物理页位置还可能偏向该 node；任务后来迁移到另一 node 会产生远端访问。

这不是“关闭线程缓存”或“绑核”的自动理由。先区分 allocator contention、cache footprint 与 NUMA locality，再在已获授权、可恢复的环境中分别实验。默认配套实验只读 topology，不设置 affinity 或 NUMA policy。

## 9. GPU allocator 是另一个内存域

深度学习框架常缓存已释放的 GPU block，以避免频繁调用昂贵的设备分配 API。常见界面会区分 allocated/live tensor bytes 与 reserved/cached device bytes，但字段名称与语义依框架版本。

GPU reserved 不等于 CPU 虚拟地址 reserved；设备显存占用也不包含在进程 RSS。统一内存还可能在 CPU 主存与设备内存间迁移。报告必须写出“哪个设备、哪个 API、哪一层账本”，不能只写“内存占用 8 GB”。

## 10. 可恢复的容量实验

配套实验 [[计算机知识/80-实践/06-计算机系统/06-地址翻译分配器与拓扑观察/README|地址翻译、分配器与拓扑观察]] 固定 C++ arena 为 4 MiB，Python 匿名映射最多 8 MiB。它不会接受用户路径，不会制造交换压力，也不会调用 allocator trim、sysctl、NUMA policy 或 affinity 设置。

这类小实验能证明账本不变量和观测管线可运行，不能代表生产 allocator 的碎片率，也不能给出性能保证。生产结论需要真实版本、负载分布、稳定期与峰值证据。

## 练习

1. 一个服务有 100 MiB live 请求、140 MiB allocator active、220 MiB allocator mapped、260 MiB RSS。列出每个差值的多个候选来源，说明为什么不能直接宣布 160 MiB 泄漏。
2. 设计一个 arena 处理一批解析请求：哪些对象可同批 reset，哪些对象会逃逸？为逃逸对象选择独立所有权，避免 reset 后悬空引用。
3. 比较“每线程缓存 2 MiB、64 个线程”和“共享中央池”的空间与争用权衡；不要假设任一方案必胜。
4. 为一次内存增长事故写四层采样表：业务 live、allocator、OS resident/virtual、GPU。每层写明工具版本与采样周期。

## 成功标准

- 能用不同句子定义 reserved、committed、resident、live 与 allocator cache；
- 能解释内部碎片、外部碎片、元数据和缓存保留为何是四类不同开销；
- 不把 `free` 返回与 RSS 立即下降绑定成跨平台契约；
- 能为 arena 写出 alignment、non-overlap、capacity 和 reset 的正确性断言；
- GPU 内存与主机 RSS 始终分栏报告。

---

**上一站**：[[计算机知识/30-计算机系统/16-地址翻译TLB页表遍历与大页|地址翻译、TLB、页表遍历与大页]] · **下一站**：[[计算机知识/30-计算机系统/18-CPU拓扑缓存一致性NUMA与设备亲和性|CPU 拓扑、缓存一致性、NUMA 与设备亲和性]] · **实验**：[[计算机知识/80-实践/06-计算机系统/06-地址翻译分配器与拓扑观察/README|地址翻译、分配器与拓扑观察]] · **返回**：[[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/30-计算机系统/10-组成原理系统课程/07-一致性内存序NUMA与性能|一致性、内存序、NUMA 与性能：共享内存不是瞬时广播]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
