---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 45
topics:
  - softmax
  - GEMM
  - tiling
  - numerical stability
tags:
  - computer-science/cuda
  - computer-science/lab
---

# 数值稳定 Softmax 与矩阵乘法

直接计算 `exp(x)` 时，大 logit 会溢出；稳定版本先令 `m = max(x)`，再计算 `exp(x - m)`。因为分子与分母同乘 `exp(-m)`，数学结果不变，却避免了危险的指数范围。本实验固定为 256 个元素、一个 block，目的是看清两次 block 内归约（先求最大值，再求指数和），不是替代生产级库。

本页包含两个刻意保持简单的程序：一个 block 内完成稳定 Softmax，另一个用 shared-memory tile 实现小型 GEMM。它们用来暴露归约、边界、同步和数据复用，不是生产性能实现。完整原理见[[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]]；实际项目应先以 cuBLAS/cuBLASLt 或框架算子为基线。

## 运行与观察

先运行 `./build/03_stable_softmax`。输入从 -80 延伸到约 79，用来观察宽 logit 范围下的归一化；这个默认最大值仍低于常见 `float` 的 `expf` 溢出阈值，所以它不单独证明朴素版一定溢出。预期输出为 PASS，并且所有输出有限、总和接近 1。将输入范围扩大后，先比较 CPU/GPU 误差，再检查是否仍满足归一化；不能以“没有崩溃”作为稳定性证明。

再运行 `./build/03_tiled_gemm`。它计算 `65×33 @ 33×67`，三个维度都故意不与 `16×16` tile 完全对齐，用零填充与边界判断覆盖最后的行、列和 K tile。PASS 只证明这个教学实现对这组输入接近 CPU reference；它不证明比 cuBLAS 快、走了 Tensor Core 或适合其他 shape/dtype。

## 源码（含 CPU 参考与小测试）

<!-- code-sync: ./03_stable_softmax.cu -->
```cpp
#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <vector>

#define CUDA_CHECK(call)                                                        \
  do {                                                                          \
    const cudaError_t status = (call);                                          \
    if (status != cudaSuccess) {                                                \
      std::cerr << #call << " failed: " << cudaGetErrorString(status)          \
                << '\n';                                                       \
      std::exit(EXIT_FAILURE);                                                  \
    }                                                                           \
  } while (0)

__global__ void stable_softmax(const float* in, float* out, int n) {
  extern __shared__ float cache[];
  const int tid = threadIdx.x;
  cache[tid] = tid < n ? in[tid] : -INFINITY;
  __syncthreads();
  for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] = fmaxf(cache[tid], cache[tid + stride]);
    __syncthreads();
  }
  const float maximum = cache[0];
  // Every warp must finish reading the reduction result before any writes reuse
  // the same shared buffer for exponentials.
  __syncthreads();
  const float value = tid < n ? expf(in[tid] - maximum) : 0.0F;
  cache[tid] = value;
  __syncthreads();
  for (int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] += cache[tid + stride];
    __syncthreads();
  }
  if (tid < n) out[tid] = value / cache[0];
}

std::vector<float> stable_softmax_cpu(const std::vector<float>& input) {
  const float maximum = *std::max_element(input.begin(), input.end());
  std::vector<float> output(input.size());
  float denominator = 0.0F;
  for (size_t i = 0; i < input.size(); ++i) {
    output[i] = std::exp(input[i] - maximum);
    denominator += output[i];
  }
  for (float& value : output) value /= denominator;
  return output;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 256;
  std::vector<float> input(n);
  for (int i = 0; i < n; ++i) input[i] = -80.0F + static_cast<float>(i) * 0.625F;
  const auto expected = stable_softmax_cpu(input);

  float *d_input = nullptr, *d_output = nullptr;
  CUDA_CHECK(cudaMalloc(&d_input, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_output, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_input, input.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  stable_softmax<<<1, 256, 256 * sizeof(float)>>>(d_input, d_output, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  std::vector<float> actual(n);
  CUDA_CHECK(cudaMemcpy(actual.data(), d_output, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaFree(d_input));
  CUDA_CHECK(cudaFree(d_output));

  const float sum = std::accumulate(actual.begin(), actual.end(), 0.0F);
  for (int i = 0; i < n; ++i) {
    if (!std::isfinite(actual[i]) || std::fabs(actual[i] - expected[i]) > 2e-5F) {
      std::cerr << "FAIL at " << i << ": got " << actual[i]
                << ", expected " << expected[i] << '\n';
      return EXIT_FAILURE;
    }
  }
  if (std::fabs(sum - 1.0F) > 1e-5F) {
    std::cerr << "FAIL: softmax sum is " << sum << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: stable softmax; sum=" << sum << '\n';
}
```

## Tiled GEMM 源码（含 CPU 参考与非整齐 shape）

<!-- code-sync: ./03_tiled_gemm.cu -->
```cpp
#include <cuda_runtime.h>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>

#define CUDA_CHECK(call)                                                        \
  do {                                                                          \
    const cudaError_t status = (call);                                          \
    if (status != cudaSuccess) {                                                \
      std::cerr << #call << " failed: " << cudaGetErrorString(status)          \
                << '\n';                                                       \
      std::exit(EXIT_FAILURE);                                                  \
    }                                                                           \
  } while (0)

constexpr int tile_size = 16;

__global__ void tiled_gemm(const float* a, const float* b, float* c,
                           int m, int n, int k) {
  __shared__ float a_tile[tile_size][tile_size];
  __shared__ float b_tile[tile_size][tile_size];

  const int row = blockIdx.y * tile_size + threadIdx.y;
  const int col = blockIdx.x * tile_size + threadIdx.x;
  float accumulator = 0.0F;

  for (int tile = 0; tile < (k + tile_size - 1) / tile_size; ++tile) {
    const int a_col = tile * tile_size + threadIdx.x;
    const int b_row = tile * tile_size + threadIdx.y;
    a_tile[threadIdx.y][threadIdx.x] =
        (row < m && a_col < k) ? a[row * k + a_col] : 0.0F;
    b_tile[threadIdx.y][threadIdx.x] =
        (b_row < k && col < n) ? b[b_row * n + col] : 0.0F;
    __syncthreads();

#pragma unroll
    for (int inner = 0; inner < tile_size; ++inner) {
      accumulator += a_tile[threadIdx.y][inner] *
                     b_tile[inner][threadIdx.x];
    }
    __syncthreads();
  }

  if (row < m && col < n) {
    c[row * n + col] = accumulator;
  }
}

std::vector<float> gemm_cpu(const std::vector<float>& a,
                            const std::vector<float>& b,
                            int m, int n, int k) {
  std::vector<float> c(static_cast<std::size_t>(m) * n, 0.0F);
  for (int row = 0; row < m; ++row) {
    for (int col = 0; col < n; ++col) {
      float accumulator = 0.0F;
      for (int inner = 0; inner < k; ++inner) {
        accumulator += a[row * k + inner] * b[inner * n + col];
      }
      c[row * n + col] = accumulator;
    }
  }
  return c;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  // Deliberately not multiples of tile_size: this exercises all edge guards.
  constexpr int m = 65;
  constexpr int n = 67;
  constexpr int k = 33;
  std::vector<float> a(static_cast<std::size_t>(m) * k);
  std::vector<float> b(static_cast<std::size_t>(k) * n);
  for (std::size_t i = 0; i < a.size(); ++i) {
    a[i] = static_cast<float>(static_cast<int>(i % 17) - 8) * 0.125F;
  }
  for (std::size_t i = 0; i < b.size(); ++i) {
    b[i] = static_cast<float>(static_cast<int>(i % 11) - 5) * 0.0625F;
  }
  const auto expected = gemm_cpu(a, b, m, n, k);
  std::vector<float> actual(static_cast<std::size_t>(m) * n, 0.0F);

  float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, a.size() * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_b, b.size() * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_c, actual.size() * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), a.size() * sizeof(float),
                        cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), b.size() * sizeof(float),
                        cudaMemcpyHostToDevice));

  const dim3 block(tile_size, tile_size);
  const dim3 grid((n + tile_size - 1) / tile_size,
                  (m + tile_size - 1) / tile_size);
  tiled_gemm<<<grid, block>>>(d_a, d_b, d_c, m, n, k);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());
  CUDA_CHECK(cudaMemcpy(actual.data(), d_c, actual.size() * sizeof(float),
                        cudaMemcpyDeviceToHost));

  CUDA_CHECK(cudaFree(d_c));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_a));

  float max_abs_error = 0.0F;
  for (std::size_t i = 0; i < actual.size(); ++i) {
    if (!std::isfinite(actual[i])) {
      std::cerr << "FAIL: non-finite GEMM result at " << i << '\n';
      return EXIT_FAILURE;
    }
    max_abs_error =
        std::fmax(max_abs_error, std::fabs(actual[i] - expected[i]));
  }
  if (max_abs_error > 1e-4F) {
    std::cerr << "FAIL: max absolute error " << max_abs_error << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: tiled GEMM " << m << 'x' << k << " @ " << k << 'x'
            << n << ", max-abs-error=" << max_abs_error << '\n';
}
```

这个 kernel 每个 block 负责一个 `16×16` 的 C tile。每轮 K tile 先让 threads 合并读取 A/B 到 shared memory，barrier 后反复复用；第二个 barrier 防止下一轮覆盖仍在读取的 tile。边界 threads 仍参加两个 barrier，只把越界 load 变成 0，因此不会出现条件 barrier 死锁。

## 练习与成功标准

在临时对照分支中把 Softmax 输入起点 `-80` 改成 `0`（使最大 logit 超过 150），再故意把 `in[tid] - maximum` 改为 `in[tid]` 观察非有限结果；完成后同时恢复输入和稳定表达式。对 GEMM，把 `m/n/k` 分别改成 `1`、`16`、`17` 的组合，确认边界仍通过；再与同 shape/dtype 的 cuBLAS 或框架结果比较，但不要在本课程环境中安装库。

成功标准是 Softmax 稳定版全部有限、总和误差小于 `1e-5`；GEMM 对非 tile 整倍数输入全部有限、最大绝对误差不超过 `1e-4`；两者都能解释为什么 GPU 与 CPU 不要求位级一致，并把 correctness、性能和 Tensor Core 路径分成三项证据。

## 恢复

恢复源码中减去 `maximum` 的表达式与 GEMM 的 `m/n/k`；用本目录的 `build/` 重新配置即可，不涉及任何系统软件。

---

**上一站**：[[计算机知识/80-实践/04-CUDA/02-Coalescing与Reduction|Coalescing 与 Reduction]] · **下一站**：[[计算机知识/80-实践/04-CUDA/04-Profiling与Offload观察|Profiling 与 Offload 观察]] · **返回**：[[计算机知识/80-实践/04-CUDA/00-CUDA实验室|CUDA 实验室]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
