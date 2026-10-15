---
type: lesson
domain: computer-science
stage: 9
status: ready
difficulty: 中级到进阶
estimated_minutes: 95
verified_on: 2026-09-02
source: NVIDIA Nsight Systems、Nsight Compute、CUDA Best Practices documentation
topics:
  - Roofline
  - Nsight Systems
  - Nsight Compute
  - profiling
  - benchmarking
  - occupancy
tags:
  - computer-science/cuda
  - computer-science/performance
---

# 09 · Roofline 与 Nsight 性能方法

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/10-PyTorch扩展-Triton与llama.cpp后端|框架扩展与后端]]

## 本课目标

学完后，你能：

1. 建立可复现、先正确再计时的性能基线；
2. 用 Nsight Systems 看端到端 timeline，用 Nsight Compute 看单个 kernel；
3. 从 arithmetic intensity、memory bandwidth ceiling 和 compute ceiling 阅读 Roofline；
4. 避免把 occupancy、峰值 FLOPS、GPU utilization 或一次 profiler 结果当最终答案。

## 1. 先把“快”写成可测问题

一次可信比较至少固定：

- GPU 型号、power/clock 状态与是否共享；
- driver、Toolkit、library、framework 和 kernel build；
- input shape、dtype、layout、batch、随机种子与数值容差；
- warm-up、测量轮数、同步位置和统计量；
- 是否包含 H2D/D2H、预处理、编译/JIT、allocation；
- baseline 是 CPU、旧 kernel、供应商库还是端到端应用。

“kernel 从 1.0 ms 到 0.8 ms”与“请求延迟从 10 ms 到 9.8 ms”是两个不同成果。

## 2. 正确的计时边界

### CUDA Event

对单 stream 的 device 工作，timing-enabled CUDA events 可记录 device timeline。注意：

- event 要 record 在被测工作的同一依赖链；
- elapsed time 前要等 stop event 完成；
- event 时间不自动包含 host 前后处理；
- 多 streams 时必须明确 stop event 依赖哪些 streams。

### Host timer

端到端时间用 monotonic host clock，并在结果真正可消费处同步。若在 launch 后立刻停止 host timer，会只测到 enqueue 成本。

### Warm-up 与 JIT

首次运行可能包含 context 建立、module/JIT 编译、library autotune、memory pool growth 和 cache 冷启动。应分别报告 cold start 与 steady state，不能悄悄丢掉更差的那一类。

## 3. Nsight Systems 先看全局

Nsight Systems 回答“时间花在哪些 CPU/GPU 活动以及它们如何重叠”：

- CPU thread 是否卡在同步、锁或数据准备；
- kernel launches 是否被许多空隙分开；
- H2D/D2H 是否与 compute overlap；
- 多 streams 是否真有并行，还是被默认 stream/依赖串行化；
- framework 是否发出大量小 kernel；
- NVTX range 对应哪个模型层或请求阶段。

先看 timeline 决定要深入哪个 kernel。若端到端瓶颈是 CPU 输入流水线，直接对最醒目的 kernel 做指令级优化通常收益有限。

## 4. Nsight Compute 再看 kernel

Nsight Compute 面向单 kernel 的硬件指标和 source correlation，常见分析维度：

- launch configuration、waves、occupancy 与资源限制；
- achieved memory bandwidth、L1/L2/DRAM traffic；
- global load/store efficiency 与 shared conflicts；
- scheduler/warp stall reasons；
- instruction mix、Tensor Core/pipe utilization；
- Speed of Light / Roofline sections。

Profiler collection 可能 replay kernel、增加开销、改变 timing，某些 counters 还受 GPU/权限/架构限制。把 profile 数值当诊断证据，不把 profiled runtime 当无扰动生产延迟。

## 5. Roofline 的三个量

```text
arithmetic intensity = useful operations / bytes transferred
attainable performance ≤ min(
  peak compute performance,
  arithmetic intensity × memory bandwidth
)
```

Roofline 图：

- 横轴：arithmetic intensity，常以 FLOP/byte；
- 纵轴：achieved performance，常以 FLOP/s；
- 斜线：bandwidth ceiling；
- 横线：compute ceiling；
- ridge point：两条 ceiling 相交。

点在斜坡附近：更像 memory-bound，想提高 FLOP/s 通常要减少 bytes、增加数据复用或融合；点在平顶附近：更像 compute-bound，才更关注指令吞吐、Tensor Core、算法与占用。

### “Byte”取哪层必须说明

只用 DRAM bytes 的 Roofline 可能掩盖 L1/L2 瓶颈。Nsight Compute 支持 hierarchical rooflines，用 L1、L2、device memory 等不同 ceiling 分析 memory hierarchy。手算模型与 profiler 算法对 operations/traffic 的定义也可能不同，比较前先对齐定义。

## 6. Occupancy 是约束变量，不是分数

Occupancy 表示 active warps 相对硬件上限的比例，可帮助隐藏 latency，但更高不必然更快：

- 降低 register 使用以提高 occupancy，可能引入 spill；
- 使用更多 shared memory 可能降低 blocks/SM，却大幅减少 global traffic；
- compute-bound kernel 可能在较低 occupancy 已填满执行管线；
- memory-bound kernel 也可能受 bandwidth 饱和而非缺 warps 限制。

正确做法是找“限制 occupancy 的资源”和“性能是否对配置敏感”，而不是把 100% 当目标。

### 理论 occupancy、achieved occupancy 与 eligible warps 不是同一个量

- **理论 occupancy**：由 block size、register/shared-memory 用量和设备上限推导的可驻留比例；
- **achieved occupancy**：profile 期间实际观察到的 active warps 比例；
- **eligible warps / scheduler 状态**：某周期真正满足依赖、可以发射指令的 warps。

理论值高但 eligible warps 少，可能是长依赖链、memory latency 或 barrier；理论值低但执行管线已饱和，提升 occupancy 也不会加速。可先用 `nvcc --resource-usage` 或编译器的 ptxas resource report 记录每 kernel registers/shared memory，再用 Nsight Compute Occupancy Calculator 检查限制项。所有数值都要绑定具体 GPU、编译目标与 kernel variant，不能从源码行数或另一台 GPU 猜测。

## 7. 一个证据驱动循环

```text
定义真实输入与指标
  ↓
建立 correctness + baseline
  ↓
Systems 找端到端空洞/瓶颈
  ↓
Compute 深入一两个关键 kernels
  ↓
提出一个可证伪假设
  ↓
做一个最小变更
  ↓
重新验证数值、算子与端到端
```

示例假设：

- “transpose kernel 是 DRAM transaction 浪费” → 改访问/layout，检查 bytes 与时间；
- “softmax 被中间读写限制” → 融合，检查 DRAM bytes、register/spill 与整体时间；
- “GEMM 没走 Tensor Core” → 核对 dtype/layout/shape/algorithm，再检查 selected kernel 与数值；
- “多 streams 没 overlap” → Systems 查看依赖与 copy engine，而不是继续加 streams。

## 8. 工具命令的安全边界

示意命令，需在明确的项目输出目录执行：

```bash
nsys profile --trace=cuda,nvtx,osrt --output=timeline ./YOUR_PROGRAM
ncu --set roofline --output=kernel-report ./YOUR_PROGRAM
```

`YOUR_PROGRAM` 是文字占位符，不是本 Vault 中的可执行文件。Profiler 会运行目标程序并创建报告；若程序有写文件、发网络请求或大规模计算的副作用，profile 会重复或放大它。先用无外部副作用的小输入，选择版本化输出目录，并检查磁盘空间。不要对未知生产命令直接启用 replay-heavy collection。

## 练习：解释三个观测

1. kernel occupancy 从 50% 升到 90%，时间不变；
2. DRAM bandwidth 接近峰值，Roofline 点在斜坡附近；
3. kernel 变快 20%，端到端只快 1%。

### 成功标准

- 1：说明原瓶颈不一定是 latency hiding，也可能已达 compute/memory ceiling；检查 spill 和实测吞吐；
- 2：优先减少 traffic/增加复用/融合，而不是只提高算术峰值；
- 3：用 Amdahl 和 Systems timeline 找其余 95%+ 时间，不把算子优化夸成应用优化；
- 三者都保留 correctness、相同输入和多轮统计。

## 核验来源

- [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/)
- [Nsight Compute documentation](https://docs.nvidia.com/nsight-compute/)
- [Nsight Compute Profiling Guide：Roofline Charts](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#roofline-charts)
- [CUDA Programming Guide：Occupancy](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html)
- [CUDA Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/10-PyTorch扩展-Triton与llama.cpp后端|PyTorch 扩展、Triton 与 llama.cpp 后端]] · **系统基础**：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
