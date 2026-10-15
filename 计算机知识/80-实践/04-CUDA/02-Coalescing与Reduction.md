---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 25
topics:
  - coalescing
  - reduction
tags:
  - computer-science/cuda
  - computer-science/lab
---

# Coalescing 与 Reduction

同一 warp 的相邻线程读相邻地址通常更容易合并为高效内存事务；这叫 coalescing。它不是“连续就必然快”的魔法：缓存、对齐、访问复用、数据类型与 GPU 架构都会影响结果。下面的归约将每个 block 的两个元素/线程先放入 shared memory，再用树形相加生成部分和；CPU 的 `accumulate` 是数值对照。

## 运行与观察

运行 `./build/02_reduction`。它先验证多阶段归约，再保留了一次 stride 为 1 的访问作为 profile 目标。用性能分析器分别将 `strided_read` 的最后一个参数改为 1 和 32，比较时间、全局加载效率与带宽；不要只看总程序时间。可用已有环境的 Nsight Systems 或 Compute 工具，但本实验不安装它们。

## 源码（含 CPU 参考与小测试）

<!-- code-sync: ./02_reduction.cu -->
```cpp
#include <cuda_runtime.h>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <utility>
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

__global__ void reduce_sum(const float* in, float* partial, int n) {
  extern __shared__ float cache[];
  const unsigned int tid = threadIdx.x;
  const unsigned int i = blockIdx.x * (blockDim.x * 2) + tid;
  float value = 0.0F;
  if (i < static_cast<unsigned int>(n)) value += in[i];
  if (i + blockDim.x < static_cast<unsigned int>(n)) value += in[i + blockDim.x];
  cache[tid] = value;
  __syncthreads();
  for (unsigned int stride = blockDim.x / 2; stride > 0; stride >>= 1) {
    if (tid < stride) cache[tid] += cache[tid + stride];
    __syncthreads();
  }
  if (tid == 0) partial[blockIdx.x] = cache[0];
}

// Adjacent threads read adjacent elements when stride is 1.  Raising stride
// demonstrates a less coalesced access pattern without changing correctness.
__global__ void strided_read(const float* in, float* out, int n, int stride) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) out[i] = in[(i * stride) % n];
}

float sum_cpu(const std::vector<float>& values) {
  return std::accumulate(values.begin(), values.end(), 0.0F);
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = (1 << 20) + 37;
  constexpr int threads = 256;
  std::vector<float> host(n);
  for (int i = 0; i < n; ++i) host[i] = static_cast<float>((i % 13) - 6) * 0.125F;
  const float expected = sum_cpu(host);

  float *d_current = nullptr, *d_next = nullptr, *d_probe = nullptr;
  CUDA_CHECK(cudaMalloc(&d_current, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_next, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_probe, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_current, host.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_probe, host.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  // This is a correctness-first multi-stage reduction, not a vendor-tuned kernel.
  int current_n = n;
  while (current_n > 1) {
    const int blocks = (current_n + threads * 2 - 1) / (threads * 2);
    reduce_sum<<<blocks, threads, threads * sizeof(float)>>>(d_current, d_next, current_n);
    CUDA_CHECK(cudaGetLastError());
    std::swap(d_current, d_next);
    current_n = blocks;
  }
  float actual = 0.0F;
  CUDA_CHECK(cudaMemcpy(&actual, d_current, sizeof(float), cudaMemcpyDeviceToHost));

  // Keep this launch in the experiment: profile stride 1 and 32 separately.
  strided_read<<<(n + threads - 1) / threads, threads>>>(d_probe, d_next, n, 1);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());
  CUDA_CHECK(cudaFree(d_current));
  CUDA_CHECK(cudaFree(d_next));
  CUDA_CHECK(cudaFree(d_probe));

  if (!std::isfinite(actual) || !std::isfinite(expected) ||
      std::fabs(actual - expected) > 1e-2F) {
    std::cerr << "FAIL: got " << actual << ", expected " << expected << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: reduction result " << actual << '\n';
}
```

## 练习与成功标准

尝试把输入长度改为一个奇数，并在两个 stride 下记录 profiler 指标。成功标准是归约值仍接近 CPU 值（这里允许 `1e-2` 浮点累计误差），且报告中区分了“正确性通过”和“特定设备上的一次性能观察”。

## 恢复

恢复源码中的 `n` 与 stride，或仅删掉本目录 `build/` 后重新配置；不需要改动系统驱动。

---

**上一站**：[[计算机知识/80-实践/04-CUDA/01-索引与Vector-Add实验|索引与 Vector Add]] · **下一站**：[[计算机知识/80-实践/04-CUDA/03-Softmax与矩阵乘法实验|数值稳定 Softmax 与矩阵乘法]] · **返回**：[[计算机知识/80-实践/04-CUDA/00-CUDA实验室|CUDA 实验室]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
