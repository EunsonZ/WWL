---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 50
verified_on: 2026-09-01
source: NVIDIA CUDA Programming Guide
topics:
  - CPU
  - GPU
  - 异构计算
  - 并行性
  - 数据移动
tags:
  - computer-science/cuda
  - computer-science/heterogeneous-computing
---

# 01 · CPU 与 GPU 异构执行模型

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]]

## 本课目标

学完后，你能：

1. 用 latency、throughput、并行度和数据移动解释 CPU/GPU 分工；
2. 把 host 控制流、device kernel、内存传输和同步画成时间线；
3. 识别“GPU 算得快，但端到端反而慢”的常见原因；
4. 用工作量、算术强度、批量和复用判断一个任务是否值得 offload。

> [!tip] 先记住四个词
> - **latency（延迟）**：一次请求从开始到得到结果要等多久；
> - **throughput（吞吐量）**：单位时间内能完成多少工作；
> - **data movement（数据移动）**：数据在 CPU 内存、GPU 显存或设备之间搬运的时间与带宽成本；
> - **offload（卸载）**：把适合并行的一段计算及其数据交给 GPU 执行，而不是让整个程序“自动变快”。

## 1. 两类处理器优化目标不同

现代 CPU 通常用复杂控制、缓存、分支预测和较少的强大执行核心，追求单线程延迟、通用性与快速响应。GPU 把更多晶体管预算投入大量算术执行资源与吞吐，适合让许多相似工作同时在不同数据上进行。

这不是“CPU 串行、GPU 并行”的绝对二分：

- CPU 有多核、SIMD 和并发任务；
- GPU 也会串行执行单个 thread 内的指令，并受依赖、资源和调度限制；
- 真正问题是某个任务能否提供足够多、足够规则且相对独立的工作，并让数据移动成本被计算收益摊薄。

| 维度 | CPU 常见优势 | GPU 常见优势 |
| --- | --- | --- |
| 控制流 | 复杂分支、低延迟、少量任务 | 大量相似控制流 |
| 并行规模 | 少量强线程 | 大量轻量 thread |
| 内存访问 | 大缓存、复杂访问容忍度较强 | 规则、合并、复用充分时高带宽 |
| 启动 | 普通函数调用成本低 | kernel launch 有固定提交成本 |
| 任务类型 | 解析、调度、I/O、串行尾部 | 数据并行、矩阵/张量、批处理 |

## 2. Host 与 device 是合作关系

CUDA 程序通常同时包含：

```text
host code on CPU
  ├─ 分配/准备 host 数据
  ├─ 建立 device allocation
  ├─ 复制或映射数据
  ├─ launch kernel
  ├─ 继续 host 工作或等待
  ├─ 取回/消费结果
  └─ 释放资源

device kernel on GPU
  └─ 大量 thread 对各自数据片执行同一 kernel 程序
```

kernel launch 通常相对 host 异步：launch 返回只说明工作已提交，不说明 GPU 已完成。随后 host 若立即读取依赖结果，就需要正确同步。[[计算机知识/40-并行与异构计算/01-CUDA/06-Stream-Event与异步流水线|Stream 与 Event]]会展开这一点。

## 3. 端到端成本模型

先用一个粗略模型思考：

```text
T_total = T_prepare + T_H2D + T_launch + T_kernel + T_D2H + T_sync
```

这个等式不是 profiler 的精确分解，却能防止只盯 `T_kernel`：

- 数据规模很小时，launch 和同步固定成本可能占主导；
- 每个元素只做一次加法，却来回跨 PCIe 搬运，传输可能比计算贵；
- 多个小 kernel 频繁往返，可能被 launch latency 和中间同步切碎；
- 数据若能长期留在 device、被多个 kernel 重用，offload 更有机会获益；
- unified/managed memory 简化地址管理，但迁移与缺页仍是成本，不是“零拷贝魔法”。

### 一个对比

任务 A：对 100 个整数各加 1，然后立刻在 CPU 打印。GPU 需要准备、传输、启动、同步和取回，通常不划算。

任务 B：对大型张量连续执行数十个算子，数据始终留在 GPU，最后只取回小结果。固定成本被大量工作和复用摭薄，GPU 更合适。

## 4. 找并行性，而不是只找循环

循环能否并行，取决于迭代间依赖：

```text
可直接数据并行： y[i] = a * x[i] + y[i]
需要归约：       sum += x[i]
有前缀依赖：     y[i] = y[i-1] + x[i]
```

- 第一类每个输出元素独立，天然适合“一 thread 一元素”；
- 第二类要把许多局部结果合并，需树形 reduction 或库算法；
- 第三类不是简单把每轮发给一个 thread，通常要改写为 scan 等并行算法。

GPU 编程的重要技能不是把 `for` 机械翻译成 kernel，而是重构数据依赖。

## 5. Amdahl、瓶颈与端到端目标

如果程序只有一部分可加速，总加速受未加速部分限制。即使 kernel 本身快 100 倍，预处理、数据加载、CPU 尾部和同步若占大头，端到端收益仍有限。

因此测量至少要有两层：

1. **算子层**：kernel 自身时间、吞吐、访存；
2. **应用层**：从真实输入进入到结果可消费的总时间和资源成本。

不要用 GPU utilization 单一数字替代这两层。

## 练习：为任务做 offload 决策

对下面三项分别写出“并行单位、输入是否已在 GPU、需要搬多少数据、结果在哪里消费、可能的固定成本”：

1. 对 4 KB 日志做正则匹配；
2. 对 4096×4096 矩阵相乘，输入已在 GPU；
3. 每次只生成一个 token 的模型推理，但权重常驻 GPU。

### 成功标准

- 不以“有循环”作为唯一判断；
- 能指出 1 很可能受启动/传输与控制流限制；
- 能指出 2 具有高数据复用与算术强度，但应优先调用成熟 GEMM 库；
- 能指出 3 的并行规模、KV cache、batch、memory bandwidth 和 CPU/GPU 同步都会影响结果，不能只看模型参数量。

## 核验来源

- [CUDA Programming Guide：Programming Model](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html)
- [CUDA Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]] · **相关**：[[计算机知识/30-计算机系统/05-并发并行SIMD与加速器|并发、并行、SIMD 与加速器]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
