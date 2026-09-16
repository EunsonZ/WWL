---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 25
topics:
  - profiling
  - PyTorch
  - llama.cpp
tags:
  - computer-science/cuda
  - computer-science/lab
---

# Profiling 与 Offload 观察

“程序启动了 GPU”并不等于“工作负载在 GPU 上”。这个实验先用 CUDA event 测量 kernel 区间（不把主机初始化和内存分配混入），再用 PyTorch 的设备与显存计数确认张量位置。对于 llama.cpp，只有其启动日志明确报告已卸载的层数、并且设备侧显存或 profiler 有相应活动，才能称作发生了 offload。

## 运行与观察

构建后运行 `./build/04_profile_offload`。它先 warm-up，再计时 100 次 SAXPY，并逐元素检查有限性与 CPU 参考值、报告最大绝对误差。不要把 event 时间和端到端墙钟时间混为一谈：前者主要覆盖 GPU 队列中的 kernel 区间，后者还会包含传输、同步与调度。

若当前 Python 环境已经安装 PyTorch（本实验不会安装），在本实践目录运行 `python3 04_torch_offload_probe.py`。它会明确显示 GPU 名称、运行前后已分配显存、矩阵乘法时间与有限性；无 PyTorch 或 CUDA 可见时以 `SKIP`/退出码 `77` 结束。

对于已经自行构建的 llama.cpp，可使用其当前版本支持的 GPU-layer 参数进行一次小模型、非敏感提示词的本地试验。不同版本参数名称与日志措辞会变；记录实际命令、启动日志中“offloaded layers”或同义字段，以及前后显存变化。不要仅依据 GPU 利用率短暂波动、也不要在这里下载模型或写入真实对话。

## CUDA event 源码（含 CPU 参考与小测试）

<!-- code-sync: ./04_profile_offload.cu -->
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

__global__ void saxpy(float a, const float* x, float* y, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) y[i] = a * x[i] + y[i];
}

void saxpy_cpu(float a, const std::vector<float>& x, std::vector<float>& y) {
  for (size_t i = 0; i < x.size(); ++i) y[i] = a * x[i] + y[i];
}

int main() {
  int device_count = 0;
  const cudaError_t availability = cudaGetDeviceCount(&device_count);
  if (availability != cudaSuccess || device_count == 0) {
    std::cout << "SKIP: no usable CUDA device\n";
    cudaGetLastError();
    return 77;
  }

  constexpr int n = 1 << 22;
  constexpr int threads = 256;
  constexpr int warmup = 10;
  constexpr int iterations = 100;
  std::vector<float> x(n, 1.5F), y(n, -2.0F), expected = y;
  for (int i = 0; i < warmup + iterations; ++i) saxpy_cpu(0.5F, x, expected);

  float *d_x = nullptr, *d_y = nullptr;
  CUDA_CHECK(cudaMalloc(&d_x, n * sizeof(float)));
  CUDA_CHECK(cudaMalloc(&d_y, n * sizeof(float)));
  CUDA_CHECK(cudaMemcpy(d_x, x.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_y, y.data(), n * sizeof(float), cudaMemcpyHostToDevice));
  for (int i = 0; i < warmup; ++i) saxpy<<<(n + threads - 1) / threads, threads>>>(0.5F, d_x, d_y, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  cudaEvent_t start, stop;
  CUDA_CHECK(cudaEventCreate(&start));
  CUDA_CHECK(cudaEventCreate(&stop));
  CUDA_CHECK(cudaEventRecord(start));
  for (int i = 0; i < iterations; ++i) saxpy<<<(n + threads - 1) / threads, threads>>>(0.5F, d_x, d_y, n);
  CUDA_CHECK(cudaEventRecord(stop));
  CUDA_CHECK(cudaEventSynchronize(stop));
  CUDA_CHECK(cudaGetLastError());
  float milliseconds = 0.0F;
  CUDA_CHECK(cudaEventElapsedTime(&milliseconds, start, stop));

  CUDA_CHECK(cudaMemcpy(y.data(), d_y, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA_CHECK(cudaEventDestroy(start));
  CUDA_CHECK(cudaEventDestroy(stop));
  CUDA_CHECK(cudaFree(d_x));
  CUDA_CHECK(cudaFree(d_y));
  float max_abs_error = 0.0F;
  for (int i = 0; i < n; ++i) {
    if (!std::isfinite(y[i])) {
      std::cerr << "FAIL: non-finite SAXPY result at " << i << '\n';
      return EXIT_FAILURE;
    }
    max_abs_error = std::fmax(max_abs_error, std::fabs(y[i] - expected[i]));
  }
  if (max_abs_error > 1e-4F) {
    std::cerr << "FAIL: max absolute error " << max_abs_error << '\n';
    return EXIT_FAILURE;
  }
  std::cout << "PASS: " << iterations << " SAXPY launches, average "
            << milliseconds / iterations << " ms, max-abs-error="
            << max_abs_error << "\n";
}
```

## PyTorch 检查源码

<!-- code-sync: ./04_torch_offload_probe.py -->
```python
"""A no-download PyTorch offload observation probe for an already installed torch."""

import sys
import time

try:
    import torch
except ImportError:
    print("SKIP: PyTorch is not installed in this interpreter")
    raise SystemExit(77)

if not torch.cuda.is_available():
    print("SKIP: PyTorch cannot see a CUDA device")
    raise SystemExit(77)

device = torch.device("cuda:0")
print(f"device={device}")
print(f"device-name={torch.cuda.get_device_name(device)}")
print(f"allocated-before={torch.cuda.memory_allocated(device)}")

torch.manual_seed(0)
left = torch.randn((1024, 1024), device=device)
right = torch.randn((1024, 1024), device=device)
warmup_result = left @ right  # keep first-use setup out of timed observation
torch.cuda.synchronize(device)
del warmup_result
start = time.perf_counter()
result = left @ right
torch.cuda.synchronize(device)
elapsed_ms = (time.perf_counter() - start) * 1_000
print(f"matmul-ms={elapsed_ms:.3f}")
print(f"allocated-after={torch.cuda.memory_allocated(device)}")
print(f"result-device={result.device}")
print(f"result-finite={torch.isfinite(result).all().item()}")

# A small, separate numerical check.  op/device discovery alone is not a
# correctness test, and a full 1024x1024 CPU reference is unnecessary here.
small_left = torch.randn((32, 48), dtype=torch.float32)
small_right = torch.randn((48, 24), dtype=torch.float32)
small_expected = small_left @ small_right
small_actual = small_left.to(device) @ small_right.to(device)
torch.testing.assert_close(
    small_actual.cpu(), small_expected, rtol=1e-4, atol=1e-5
)
print("reference-close=True")
```

## 成功标准与恢复

成功记录至少同时包含：CUDA 程序 PASS 与最大误差、PyTorch 的逻辑设备 `device=cuda:0`、可辨认但不作为契约的 `device-name=...`、结果位置 `result-device=cuda:0`、显存变化及 `reference-close=True`（若环境可用）、llama.cpp 的层卸载日志与显存/trace 证据（若已具备程序与模型）。任一层缺失时，将结论降级为“未验证 offload”。恢复只需删除本目录 `build/`，并撤销实验中对源码的局部参数改动。

---

**上一站**：[[计算机知识/80-实践/04-CUDA/03-Softmax与矩阵乘法实验|数值稳定 Softmax 与矩阵乘法]] · **返回**：[[计算机知识/80-实践/04-CUDA/00-CUDA实验室|CUDA 实验室]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
