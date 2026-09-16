---
type: lesson
domain: computer-science
stage: 4
status: ready
difficulty: 中级
estimated_minutes: 75
verified_on: 2026-09-01
source: NVIDIA CUDA Programming Guide、Best Practices Guide
topics:
  - memory hierarchy
  - coalescing
  - shared memory
  - bank conflict
  - cache
tags:
  - computer-science/cuda
  - computer-science/memory
---

# 04 · 内存层级、合并访问与 Bank Conflict

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/03-Kernel与Grid-Block-Thread-Warp|Kernel 与执行层级]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/05-同步原子操作与分支发散|同步、原子操作与分支发散]]

## 本课目标

学完后，你能：

1. 按 scope、容量、延迟和可见性区分 register、local、shared、L1、L2、global、constant 等层；
2. 从一个 warp 的地址序列判断 global-memory 访问是否容易合并；
3. 解释 shared-memory bank conflict、broadcast 和 padding；
4. 用“减少流量、增加复用、保持正确性”而不是“shared 一定更快”指导优化。

## 1. 先按作用域理解层级

| 存储/缓存 | 逻辑作用域 | 典型用途 | 关键边界 |
| --- | --- | --- | --- |
| register | thread 私有 | 标量、索引、局部累加 | 数量有限；压力过高会降低并发或 spill |
| local memory | thread 私有地址空间 | 无法放入 register 的局部对象、spill | 名字叫 local，但通常驻留 device memory，经 cache 访问，不是片上私有 SRAM 的保证 |
| shared memory | block 共享 | tile、block 内协作、数据重排 | 显式分配；容量有限；需同步；存在 bank conflict |
| L1/cache | SM 附近缓存 | 缓解部分访存延迟与重复 | 行为、容量与配置随架构变化，不替代良好访问模式 |
| L2 | device 共享 | global 访问的共享缓存层 | 多 SM 共享；一致性与命中不能靠直觉假定 |
| global memory | device 级地址空间 | 大数组、跨 kernel 持久数据 | 高带宽但高延迟；访问事务效率重要 |
| constant memory | device 可读、host 写入的常量空间 | warp 内相同地址的只读参数 | 地址分散时会串行化；容量与缓存有上限 |

另外还有 texture/surface、managed/system memory 等专用或统一地址能力。学习主线先抓住：**谁能访问、存活多久、是否显式管理、实际流量走到哪层**。

### Register spill 不是“数组太大”这么简单

compiler 可能因动态索引、每 thread 资源过多或寄存器压力把值放到 local memory。观察应使用 compiler resource report 和 profiler，而不是看到一个局部变量就断言它在 register，也不能看到 spill 就盲目限制 register：减少每 thread register 可能增加 occupancy，却同时制造更多 memory traffic。

## 2. Coalescing 看的是 warp 地址集合

一个 warp 的 active threads 发出 global-memory 请求时，硬件把地址请求合并成必要的 memory transactions。理想情况通常是相邻 lane 访问相邻、自然对齐的数据：

```text
lane:     0   1   2   3   ...
address:  A   A+4 A+8 A+12 ...   (float)
```

坏的 stride 访问：

```text
lane:     0    1    2    3   ...
address:  A   A+S  A+2S A+3S ...
```

当 `S` 很大，一个 warp 可能触发许多事务却只使用其中少量字节。具体 segment/sector 和 cache 行为随 compute capability 变化，课程不把某代硬件的事务大小写成永久规则；判断方法保持不变：列出 active lane 的地址，结合元素大小、对齐和 profiler 的实际请求/吞吐。

## 3. 行优先矩阵的访问方向

对 C/C++ row-major 矩阵 `A[row * width + col]`：

- 若相邻 lane 改变 `col`，地址相邻，通常易于合并；
- 若相邻 lane 改变 `row` 而 `width` 很大，地址步长为一整行，通常浪费事务；
- transpose、GEMM 等常用 shared-memory tile 把 global 的合并读写与计算所需的另一种访问顺序连接起来。

这也解释了“逻辑上同一个矩阵”为什么 layout、stride 和 contiguous 状态会影响后端选择与速度。

## 4. Shared memory 负责显式复用与重排

典型 tile 流程：

```text
每个 thread 合并读取一个 global 元素
        ↓
写入 block 的 shared tile
        ↓ block barrier
threads 以计算需要的次序多次读取 tile
        ↓ block barrier，避免下一轮覆盖仍在读取的数据
加载下一个 tile
```

shared memory 只有在省下的 global traffic 或更好的访问模式大于装载、同步和资源成本时才有收益。一次只读一次、无复用的数据搬进 shared 可能更慢。

## 5. Bank conflict

shared memory 被划分为 banks。一个 warp 的不同 threads 同时访问不同 banks 时可并行服务；多个 threads 的地址落到同一个 bank 且不是可广播的同地址访问时，请求会拆分，形成 bank conflict。

经典 transpose tile：

```cpp
// kernel fragment, not a complete program
__shared__ float tile[32][32];
```

按行访问通常让相邻 lane 落到相邻 banks；按列访问 `tile[threadIdx.x][fixed_col]` 可能让大量 lane 映射到同一 bank。常见修正是 padding：

```cpp
// kernel fragment: the extra column changes the row stride
__shared__ float tile[32][33];
```

但不要把 `+1` 当万能公式：bank 数、bank width、元素类型、向量化访问和地址表达式都会影响映射。先列地址或看 profiler 的 shared-memory conflict 指标。

### 同地址 broadcast 不等于 conflict

若 warp 多个 threads 读取同一个 shared 地址，硬件可广播；“多个 lane 命中同一 bank”不是自动等于 N-way conflict。必须区分相同地址与同 bank 不同地址。

## 6. Array of Structures 与 Structure of Arrays

例如粒子：

```cpp
struct Particle { float x, y, z, mass; };
```

若 kernel 只读取所有 `x`，AoS 会以结构体 stride 访问；SoA 用独立 `x[]` 可让相邻 lane 读相邻 x。若每次都使用完整结构且布局/对齐合适，AoS 也可能合理。布局选择应由访问集合决定，而不是把 SoA 宣称为永远更快。

## 7. 与 CPU cache 的连接

GPU coalescing 与 CPU cache locality 都在回答“有多少传输字节被真正使用、数据能否复用”，但执行组和硬件机制不同。跨域基础见[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]]。

## 练习：手算两组地址

假设一个 warp 的 lane `t=0..31` 读取 `float`：

1. `a[base + t]`；
2. `a[base + 32*t]`。

再假设 shared bank 映射可简化为 `(word_index mod 32)`，比较：

3. `tile[t][0]`，其中 `tile[32][32]`；
4. `tile[t][0]`，其中 `tile[32][33]`。

### 成功标准

- 1 的地址连续；2 的地址跨度大，通常需要更多 global transactions；
- 简化模型下 3 的各行起点都映射 bank 0，4 的行起点依次轮转；
- 能说明真实硬件还要看架构、元素宽度、active mask、对齐与 profiler，手算只是诊断模型。

## 核验来源

- [CUDA Programming Guide：Understanding Memory](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/understanding-memory.html)
- [CUDA Best Practices Guide：Memory Optimizations](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/05-同步原子操作与分支发散|同步、原子操作与分支发散]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
