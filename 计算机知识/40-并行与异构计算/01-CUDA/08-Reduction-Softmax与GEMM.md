---
type: lesson
domain: computer-science
stage: 8
status: ready
difficulty: 中级到进阶
estimated_minutes: 100
verified_on: 2026-09-01
source: NVIDIA CUDA Programming Guide、CCCL/CUB、cuBLAS documentation
topics:
  - reduction
  - softmax
  - GEMM
  - tiling
  - numerical stability
tags:
  - computer-science/cuda
  - computer-science/kernels
  - computer-science/linear-algebra
---

# 08 · Reduction、Softmax 与 GEMM

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/07-FP16-BF16-FP8与Tensor-Core|低精度与 Tensor Core]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/09-Roofline与Nsight性能方法|Roofline 与 Nsight 性能方法]]

## 本课目标

学完后，你能：

1. 把 reduction 写成 thread → warp → block → grid 的分层合并；
2. 解释稳定 softmax 的 max 与 sum 两次归约及融合机会；
3. 从数据复用解释 tiled GEMM，而不是只记住模板；
4. 判断何时应调用 CUB/cuBLAS 等成熟库，何时才值得自定义 kernel。

数学权威入口：

- [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]；
- [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]；
- [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]；
- [[数学/30-概率与统计/04-温度Top-k与Top-p采样|温度、Top-k 与 Top-p 采样]]。

## 1. Reduction：从 N 个值到一个或少量值

sum、max、min、norm、histogram 的共同难点是许多输入要合并。串行写法：

```text
acc = identity
for x in input:
    acc = combine(acc, x)
```

并行树形思路：

```text
每 thread 处理若干元素
      ↓
warp 内合并
      ↓
block 内合并
      ↓
每 block 写一个 partial
      ↓
第二个 kernel 或库 primitive 继续归约
```

combine 应满足算法需要的结合性质，但 floating-point addition 并非数学上的严格结合：树形顺序改变舍入。正确性测试要用合理误差标准并记录 accumulator dtype，而不是要求与串行 FP32 逐 bit 相同。

### 为什么不让每个元素 atomicAdd 一个 global sum

它可能数值上可接受，却把所有 threads 引向一个争用热点。分层归约把 global atomic/写次数显著减少，并让数据在 register/shared 中就地合并。

## 2. 一个教学用 block reduction

伴随 `reduction.cu` 每个 block 读取最多 `2×256` 个元素，在 shared memory 中树形归约，host 最后合并 block partials。生产规模通常在 GPU 继续第二阶段，或直接使用 CUB/CCCL；本例保留 host final step，让层级可见。

<!-- code-sync: ./reduction.cu -->
```cpp
#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <vector>

#define CUDA_CHECK(call)                                                     \
  do {                                                                       \
    const cudaError_t error = (call);                                        \
    if (error != cudaSuccess) {                                              \
      std::fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                   cudaGetErrorString(error));                               \
      return 1;                                                              \
    }                                                                        \
  } while (0)

template <int block_size>
__global__ void reduce_sum(const float* input, float* partial, int n) {
  __shared__ float tile[block_size];
  const int lane = threadIdx.x;
  const int first = blockIdx.x * (2 * block_size) + lane;

  float local = 0.0F;
  if (first < n) {
    local += input[first];
  }
  const int second = first + block_size;
  if (second < n) {
    local += input[second];
  }
  tile[lane] = local;
  __syncthreads();

  for (int stride = block_size / 2; stride > 0; stride /= 2) {
    if (lane < stride) {
      tile[lane] += tile[lane + stride];
    }
    __syncthreads();
  }

  if (lane == 0) {
    partial[blockIdx.x] = tile[0];
  }
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::puts("SKIP: no usable CUDA device");
    cudaGetLastError();
    return 77;
  }


  constexpr int n = (1 << 20) + 3;
  constexpr int threads = 256;
  const int blocks = (n + 2 * threads - 1) / (2 * threads);

  std::vector<float> input(n);
  double expected = 0.0;
  for (int i = 0; i < n; ++i) {
    input[i] = static_cast<float>((i % 13) - 6);
    expected += input[i];
  }
  std::vector<float> partial(blocks, 0.0F);

  float* d_input = nullptr;
  float* d_partial = nullptr;
  CUDA_CHECK(cudaMalloc(&d_input, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_partial, blocks * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_input, input.data(), n * sizeof(float),
                        cudaMemcpyHostToDevice));

  reduce_sum<threads><<<blocks, threads>>>(d_input, d_partial, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaMemcpy(partial.data(), d_partial, blocks * sizeof(float),
                        cudaMemcpyDeviceToHost));

  double result = 0.0;
  for (const float value : partial) {
    result += value;
  }

  CUDA_CHECK(cudaFree(d_partial));
  CUDA_CHECK(cudaFree(d_input));
  if (std::fabs(result - expected) > 1e-6) {
    std::fprintf(stderr, "Mismatch: got %.9f expected %.9f\n", result,
                 expected);
    return 1;
  }
  std::printf("PASS: reduction result %.1f from %d block partials\n", result,
              blocks);
  return 0;
}
```

受支持环境中：

```bash
nvcc -std=c++17 -O2 -lineinfo reduction.cu -o reduction
./reduction
```

当前写作环境无 `nvcc`/NVIDIA GPU，只完成代码同步和静态审阅，未编译运行。样例输入是小整数，规避了复杂舍入；扩展到实数时必须改用误差指标和多种归约顺序验证。

## 3. Softmax 是多阶段归约

对一行 logits `x_i`，稳定 softmax：

```text
m = max_i(x_i)
s = sum_i(exp(x_i - m))
y_i = exp(x_i - m) / s
```

为什么先减 max：直接 `exp(x_i)` 可能 overflow；减去最大值后，最大 exponent 为 1，同时数学结果不变。

GPU 实现需要：

1. 对一行做 max reduction；
2. 计算 exponent 并做 sum reduction；
3. 归一化写回；
4. 处理 mask、非整齐列数、`-inf`、NaN、空行和 dtype；
5. 决定一行映射到一个 warp、block 或多个 blocks。

融合能减少中间 global reads/writes 和 launch 次数，但大 row 可能装不进 register/shared；强行单 block 会限制并行度。Triton 官方 fused-softmax 教程展示了 power-of-two tile + mask 的一种实现，不是所有 shape 的唯一最优解。

## 4. GEMM：复用决定算术强度

`C[M,N] = A[M,K] × B[K,N]` 的朴素“一 thread 一个 C 元素”会反复从 global 读取 A 行和 B 列。分块 GEMM：

```text
选择 C 的 M_tile × N_tile
for each K_tile:
  合并读取 A_tile 与 B_tile
  在 shared/register 中复用
  每 thread 更新自己的 accumulator fragment
写回 C tile
```

每个加载的 A/B 元素被多个乘加复用，arithmetic intensity 上升。进一步优化还包括 register tiling、双缓冲、async copy、vectorized access、swizzle、Tensor Core MMA 和 epilogue fusion。

但 GEMM 优化空间巨大且依赖架构/shape/dtype/layout。生产代码优先使用 cuBLAS/cuBLASLt 或框架已选择的成熟 backend；自写 kernel 的合理理由包括特殊布局、融合 epilogue、极端 shape、研究或教学，并必须与库基线比较。

## 5. 三个算子的共同框架

| 算子 | 主要并行模式 | 主要风险 | 常见成熟实现 |
| --- | --- | --- | --- |
| reduction | 层级树形合并 | 同步、争用、舍入顺序 | CCCL/CUB DeviceReduce |
| softmax | max reduction + exp + sum reduction + normalize | overflow、mask、row shape、融合资源 | 框架/attention kernel、Triton 教程 |
| GEMM | 2D/3D tiling + K reduction | layout、复用、寄存器/shared、低精度误差 | cuBLAS/cuBLASLt |

若要在同一模型数据流中定位 Q/K/V、attention score、softmax 与前馈 GEMM，见 [[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]]。

## 练习：为三个 shape 选策略

1. reduction：1 亿 FP32 元素；
2. softmax：batch 很大、每行 128 列；
3. GEMM：`M=1, N=4096, K=4096` 的矩阵向量形状。

### 成功标准

- reduction 不让 host 合并海量 partial，也不让每元素争同一 atomic；
- short-row softmax 考虑一个 warp/block 处理多行并融合读写；
- `M=1` 不套用只对方阵有效的 tile 假设，先比较 GEMV/专用库路径；
- 三者都先建立 correctness/reference，再以真实 shape benchmark。

## 核验来源

- [CUDA Programming Guide：Writing SIMT Kernels](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html)
- [CCCL / CUB documentation](https://nvidia.github.io/cccl/unstable/cub/index.html)
- [cuBLAS documentation](https://docs.nvidia.com/cuda/cublas/)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/09-Roofline与Nsight性能方法|Roofline 与 Nsight 性能方法]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
