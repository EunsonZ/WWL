---
type: lesson
domain: computer-science
stage: 7
status: ready
difficulty: 中级
estimated_minutes: 80
verified_on: 2026-09-01
source: NVIDIA CUDA Programming Guide、CUDA Math API、cuBLAS documentation
topics:
  - FP16
  - BF16
  - FP8
  - Tensor Core
  - mixed precision
  - numerical stability
tags:
  - computer-science/cuda
  - computer-science/numerical-computing
---

# 07 · FP16、BF16、FP8 与 Tensor Core

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/06-Stream-Event与异步流水线|Stream、Event 与异步流水线]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]]

## 本课目标

学完后，你能：

1. 从 exponent、significand 和 dynamic range 区分 FP16、BF16 与常见 FP8 编码；
2. 区分 input/storage dtype、compute dtype、accumulation dtype 与 output dtype；
3. 解释 Tensor Core 是特定矩阵/张量运算路径，不是“用了 half 就自动加速”；
4. 为低精度实验设计误差、溢出、下溢、缩放和硬件能力验证。

完整数学定义与误差分析以[[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]为权威页；本课聚焦 CUDA 计算与部署边界。

## 1. 精度与范围是两条轴

| 格式 | 常见直觉 | 主要取舍 |
| --- | --- | --- |
| FP32 | 通用训练/计算基线 | 较大内存与带宽成本；仍有舍入、溢出和非结合性 |
| FP16 / binary16 | 更多 significand 精度于 BF16，但 exponent 较窄 | 小值易下溢、大值易溢出，常配 loss scaling/FP32 accumulate |
| BF16 | exponent 范围接近 FP32，significand 更短 | 动态范围较宽，但舍入误差通常大于 FP16 |
| FP8 E4M3 类 | 更多精度、较小范围的取向 | 具体 special values 与变体语义须查 API/硬件 |
| FP8 E5M2 类 | 更多 exponent、较少 significand | 范围更大但精度更粗 |

CUDA 当前文档提供 `__half`、`__nv_bfloat16` 与 FP8 相关类型/API，但类型可声明不等于当前 GPU 对所有操作有原生高吞吐支持。compute capability、Toolkit headers、编译目标和具体 library 路径必须一起核对。

## 2. 四个 dtype 不要缩成一个名字

矩阵乘常见管线：

```text
A storage/input dtype ─┐
                      ├─ multiply/compute mode → accumulation dtype → output dtype
B storage/input dtype ─┘
```

例如输入以 FP16 存储、乘法走低精度、累加到 FP32、最后写回 FP16。若只说“这是 FP16 GEMM”，无法判断精度与性能。

记录实验时至少写：

- A/B/C/D data type；
- compute type 与 accumulation type；
- math mode/algorithm；
- transpose/layout 与 shape；
- GPU 型号、compute capability、driver/Toolkit/library；
- 是否允许 TF32、reduced-precision reduction 或 fast-math；
- reference dtype、容差和误差统计。

## 3. Tensor Core 的位置

Tensor Cores 面向特定矩阵 multiply-accumulate 和相关张量运算。能否使用及吞吐取决于：

- GPU architecture / compute capability；
- 输入、compute、accumulation dtype 组合；
- shape、alignment、layout 与 leading dimension；
- library/kernel 实现和 algorithm selection；
- 稀疏、block-scaled 等特殊路径的附加条件。

调用 cuBLAS/PyTorch 并不保证某次 shape 选择 Tensor Core kernel；反过来，一个 kernel 使用 Tensor Core 指令也不保证端到端更快，memory traffic、转换、launch 和小 shape 可能主导。

## 4. TF32 不等于 FP16/BF16

TensorFloat-32 是 NVIDIA Tensor Core 计算模式中的一种格式/路径，通常以 FP32 范围配合较短 significand 进行矩阵计算，并可用 FP32 累加。它不是一个用于普遍存储张量的普通 C++ 标量替代品，也不应只写成“FP32 一样精确”。框架默认是否允许 TF32 会演进，实验必须显式记录设置。

## 5. Mixed precision 的稳定性策略

### FP32 accumulation

大量乘加或 reduction 中，小误差会累积。把输入/乘法降精度但用 FP32 accumulator，常能改善结果；这不恢复输入量化时已经丢失的信息。

### Scaling

- 训练中的 loss scaling 把很小 gradient 放大，避免 FP16 下溢，再在更新前缩回；
- FP8 常需要 per-tensor/per-channel/block scaling 和 amax 历史等策略；
- scale 选得太小会 overflow，太大会让有效值挤在少量量化级别。

### 稳定公式

softmax 应先减最大值，归约可使用分块、pairwise 或更高精度 accumulator。格式选择不能替代稳定算法。

## 6. “更快”需要三层证据

1. **硬件路径**：profiler 或反汇编/库日志证明目标指令/kernel 被选择；
2. **算子性能**：warm-up 后对相同 shape/layout 测量时间与吞吐；
3. **应用质量**：任务指标、误差分布、异常值和可重复性满足要求。

只测第 2 层可能得到快但错误的结果；只看第 1 层也可能忽略转换和端到端开销。

## 练习：设计 dtype 实验矩阵

选择一个 `M×K` 乘 `K×N`，比较：

- FP32 input/compute/output；
- FP16 input + FP32 accumulate + FP16 output；
- BF16 input + FP32 accumulate；
- 目标 GPU 支持时再加入两种 FP8 配置。

输入至少包括均匀随机、小量级、接近格式上限、跨多个数量级和含异常值五组。

### 成功标准

- 记录 input/compute/accumulation/output 四类 dtype；
- 用 FP64 或高可信实现做 reference，并报告 max absolute、max relative、RMSE/任务指标；
- 单独报告 NaN、Inf、underflow/zero 数量；
- 不在硬件不支持时把 software emulation 的性能当 Tensor Core 性能；
- 不能通过放宽容差掩盖系统性错误。

## 核验来源

- [CUDA Programming Guide：Floating-Point Computation](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/mathematical-functions.html)
- [CUDA Math API](https://docs.nvidia.com/cuda/cuda-math-api/)
- [cuBLAS documentation](https://docs.nvidia.com/cuda/cublas/)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
