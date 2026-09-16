---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 入门
estimated_minutes: 20
topics:
  - CUDA thread indexing
  - vector addition
tags:
  - computer-science/cuda
  - computer-science/lab
---

# 索引与 Vector Add

目标是把长度不是线程块整数倍的向量相加。全局索引为 `blockIdx.x * blockDim.x + threadIdx.x`，所以最后一个 block 必须检查 `i < n`；没有它会越界读写。CPU 版本是判定正确性的参考，而不是要被 GPU “加速”的部分。

## 运行与观察

完成实验室的配置与构建后，运行 `./build/01_vector_add`。预期是 `PASS: vector_add 1048576 elements`；如果显示 `SKIP`，检查的是当前环境，没有对源码作出正确性结论。把 `n` 改成 `1027` 后重新构建运行，确认尾部线程仍不会越界。

## 源码（含 CPU 参考与小测试）

<!-- code-sync: ./01_vector_add.cu -->
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

__global__ void vector_add(const float* a, const float* b, float* out, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) out[i] = a[i] + b[i];
}

std::vector<float> vector_add_cpu(const std::vector<float>& a,
                                  const std::vector<float>& b) {
  std::vector<float> out(a.size());
  for (size_t i = 0; i < a.size(); ++i) out[i] = a[i] + b[i];
  return out;
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 1 << 20;
  std::vector<float> a(n), b(n);
  for (int i = 0; i < n; ++i) {
    a[i] = static_cast<float>(i) * 0.25F;
    b[i] = -static_cast<float>(i % 31) * 0.5F;
  }
  const auto expected = vector_add_cpu(a, b);

  float *d_a = nullptr, *d_b = nullptr, *d_out = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_b, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_out, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), n * sizeof(float), cudaMemcpyHostToDevice));

  constexpr int threads = 256;
  vector_add<<<(n + threads - 1) / threads, threads>>>(d_a, d_b, d_out, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  std::vector<float> actual(n);
  CUDA_CHECK(cudaMemcpy(actual.data(), d_out, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaFree(d_a));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_out));

  for (int i = 0; i < n; ++i) {
    if (std::fabs(actual[i] - expected[i]) > 1e-6F) {
      std::cerr << "FAIL at " << i << ": got " << actual[i]
                << ", expected " << expected[i] << '\n';
      return EXIT_FAILURE;
    }
  }
  std::cout << "PASS: vector_add " << n << " elements\n";
}
```

## 练习与成功标准

把 block 大小从 256 改成 128 和 512，各运行一次。记录“结果是否仍 PASS”与“时间是否变化”；不要从单次变化断言哪个配置永远更快。成功标准是 CPU/GPU 每个元素差值不超过 `1e-6`，且 `n` 非整除时仍 PASS。

## 恢复

将 `n` 与 `threads` 恢复到源码中的值，并只删除本目录的 `build/` 重新配置即可。

---

**上一站**：[[计算机知识/80-实践/04-CUDA/00-CUDA实验室|CUDA 实验室]] · **下一站**：[[计算机知识/80-实践/04-CUDA/02-Coalescing与Reduction|Coalescing 与 Reduction]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
