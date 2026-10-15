---
type: lesson
domain: computer-science
stage: 6
status: ready
difficulty: 中级
estimated_minutes: 85
verified_on: 2026-09-01
source: NVIDIA CUDA Programming Guide
topics:
  - CUDA stream
  - CUDA event
  - asynchronous execution
  - pinned memory
  - overlap
tags:
  - computer-science/cuda
  - computer-science/asynchronous
---

# 06 · Stream、Event 与异步流水线

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/05-同步原子操作与分支发散|同步、原子操作与分支发散]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/07-FP16-BF16-FP8与Tensor-Core|低精度与 Tensor Core]]

## 本课目标

学完后，你能：

1. 区分 host 异步、stream 内顺序、stream 间依赖与硬件真实并发；
2. 用 event 表达完成状态、计时和跨 stream 等待；
3. 解释 `cudaMemcpyAsync`、pinned host memory 与 copy/compute overlap 的条件；
4. 设计双缓冲 pipeline，并用时间线验证而不是凭 API 名推断重叠。

## 1. 异步提交不等于并发执行

当 host 调用 asynchronous API 后快速返回，只能说明 host 不必在该调用点等待。实际操作何时开始、是否与别的操作同时执行，取决于：

- 操作是否位于不同、可独立推进的 streams；
- 两操作之间是否存在 event/默认 stream/内存依赖；
- GPU 是否有可用 compute/copy engine 与资源；
- host memory 是否满足异步传输要求；
- kernel 是否已经占满相关执行资源；
- runtime/架构和具体 API 的语义。

```text
host: enqueue H2D → enqueue kernel → enqueue D2H → continue CPU work
stream:      H2D →        kernel →        D2H
```

同一 stream 是 in-order queue：后面的操作不会越过前面的依赖操作。多个 streams 允许 runtime 考虑并发，但不保证并发。

## 2. Event 是 device 工作进度标记

把 event record 到 stream，表示它在该 stream 之前的工作完成后才成为 complete：

```cpp
// API fragment, assumes valid stream and event handles
cudaEventRecord(ready, producer_stream);
cudaStreamWaitEvent(consumer_stream, ready, 0);
```

用途：

- host 用 `cudaEventQuery` 非阻塞查询；
- host 用 `cudaEventSynchronize` 等待精确事件；
- 一个 stream 用 `cudaStreamWaitEvent` 等另一个 stream 的数据依赖；
- timing-enabled events 测量 device timeline 上一段工作。

这比无条件 `cudaDeviceSynchronize()` 更精确：device-wide 等待会阻塞所有先前工作，容易抹平并发。

## 3. Pageable 与 pinned host memory

NVIDIA 当前 Programming Guide 明确指出：涉及 CPU memory 的传输若要真正异步并可与其他工作 overlap，host buffer 需要 page-locked/pinned。对 pageable memory 使用 `cudaMemcpyAsync` 可能仍能得到正确复制，但会退回同步行为，不能凭函数名假定重叠。

Pinned memory 的成本：

- 占用不可随意换出的物理内存；
- 分配/注册成本较高；
- 过量使用会影响系统；
- 适合复用的 staging buffer，不适合给每个小请求临时分配。

## 4. 双缓冲时间线

把数据切成 chunks，两个 streams 交替：

```text
time ─────────────────────────────────────────────▶
stream 0: H2D chunk0 | kernel0 | D2H chunk0
stream 1:        H2D chunk1 | kernel1 | D2H chunk1
host:     enqueue all work ── other work ── wait events
```

若 copy engines、compute resources 和数据依赖允许，中间阶段可能重叠。chunk 太小会被 launch/API overhead 主导；chunk 太大又失去 pipeline 机会，所以大小应测量。

## 5. 可运行样例

伴随文件 `stream_event_pipeline.cu` 使用两套 pinned host 区域、两个 non-blocking streams、每 stream 独立 device buffers 和完成 event。它证明正确性与依赖写法，不证明在任意 GPU 上一定 overlap。

<!-- code-sync: ./stream_event_pipeline.cu -->
```cpp
#include <cuda_runtime.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

#define CUDA_CHECK(call)                                                     \
  do {                                                                       \
    const cudaError_t error = (call);                                        \
    if (error != cudaSuccess) {                                              \
      std::fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                   cudaGetErrorString(error));                               \
      std::exit(EXIT_FAILURE);                                               \
    }                                                                        \
  } while (0)

__global__ void add(const float* a, const float* b, float* c, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) {
    c[i] = a[i] + b[i];
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


  constexpr int chunks = 2;
  constexpr int chunk_elements = 1 << 19;
  constexpr int total_elements = chunks * chunk_elements;
  constexpr std::size_t chunk_bytes = chunk_elements * sizeof(float);
  constexpr std::size_t total_bytes = total_elements * sizeof(float);

  float* h_a = nullptr;
  float* h_b = nullptr;
  float* h_c = nullptr;
  CUDA_CHECK(cudaMallocHost(&h_a, total_bytes));
  CUDA_CHECK(cudaMallocHost(&h_b, total_bytes));
  CUDA_CHECK(cudaMallocHost(&h_c, total_bytes));

  for (int i = 0; i < total_elements; ++i) {
    h_a[i] = static_cast<float>(i % 97);
    h_b[i] = 0.5F;
    h_c[i] = 0.0F;
  }

  cudaStream_t streams[chunks]{};
  cudaEvent_t done[chunks]{};
  float* d_a[chunks]{};
  float* d_b[chunks]{};
  float* d_c[chunks]{};

  constexpr int threads = 256;
  constexpr int blocks = (chunk_elements + threads - 1) / threads;

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaStreamCreateWithFlags(&streams[k], cudaStreamNonBlocking));
    CUDA_CHECK(cudaEventCreateWithFlags(&done[k], cudaEventDisableTiming));
    CUDA_CHECK(cudaMalloc(&d_a[k], chunk_bytes));
    CUDA_CHECK(cudaMalloc(&d_b[k], chunk_bytes));
    CUDA_CHECK(cudaMalloc(&d_c[k], chunk_bytes));
  }

  // Traditional cudaMalloc may synchronize the device. Finish every stream,
  // event and allocation before enqueueing either chunk so allocation cannot
  // serialize the two candidate pipelines between their submissions.
  for (int k = 0; k < chunks; ++k) {
    const int offset = k * chunk_elements;
    CUDA_CHECK(cudaMemcpyAsync(d_a[k], h_a + offset, chunk_bytes,
                               cudaMemcpyHostToDevice, streams[k]));
    CUDA_CHECK(cudaMemcpyAsync(d_b[k], h_b + offset, chunk_bytes,
                               cudaMemcpyHostToDevice, streams[k]));
    add<<<blocks, threads, 0, streams[k]>>>(d_a[k], d_b[k], d_c[k],
                                           chunk_elements);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaMemcpyAsync(h_c + offset, d_c[k], chunk_bytes,
                               cudaMemcpyDeviceToHost, streams[k]));
    CUDA_CHECK(cudaEventRecord(done[k], streams[k]));
  }

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaEventSynchronize(done[k]));
  }

  for (int i = 0; i < total_elements; ++i) {
    const float expected = h_a[i] + h_b[i];
    if (!std::isfinite(h_c[i]) || !std::isfinite(expected) ||
        std::fabs(h_c[i] - expected) > 1e-6F) {
      std::fprintf(stderr, "Mismatch at %d: got %f expected %f\n", i, h_c[i],
                   expected);
      return 1;
    }
  }

  for (int k = 0; k < chunks; ++k) {
    CUDA_CHECK(cudaFree(d_c[k]));
    CUDA_CHECK(cudaFree(d_b[k]));
    CUDA_CHECK(cudaFree(d_a[k]));
    CUDA_CHECK(cudaEventDestroy(done[k]));
    CUDA_CHECK(cudaStreamDestroy(streams[k]));
  }
  CUDA_CHECK(cudaFreeHost(h_c));
  CUDA_CHECK(cudaFreeHost(h_b));
  CUDA_CHECK(cudaFreeHost(h_a));

  std::puts("PASS: two-stream pipeline");
  return 0;
}
```

受支持环境中：

```bash
nvcc -std=c++17 -O2 -lineinfo stream_event_pipeline.cu -o stream_event_pipeline
./stream_event_pipeline
```

预期 `PASS: two-stream pipeline`。样例先完成全部传统 `cudaMalloc`，再提交两条 stream；这是为了避免分配调用夹在两条提交之间造成隐式同步，但仍不保证硬件 copy engine、kernel 资源和传输方向一定允许重叠。必须用 Nsight Systems 检查 timeline 是否真实 overlap；只看到 PASS 不能证明 overlap。当前写作环境无 `nvcc`/NVIDIA GPU，未编译、未运行、未采 profile。

> [!note] 失败路径与生产代码
> 样例的错误宏直接结束进程，便于把首个 CUDA 错误暴露出来；生产代码应使用 RAII 或集中 cleanup，确保长期进程中的 streams、events、pinned/device allocations 在异常路径释放。

## 6. 默认 stream 语义要现场确认

legacy default stream 与 blocking streams 可能有隐式同步；per-thread default stream 的行为不同。不要把来自某个编译选项或框架的默认语义带到另一个程序。为了可读依赖，教学和库代码优先显式传 stream，并记录构建设置。

## 练习：加入 producer/consumer 依赖

设计两个 kernels：stream A 生成 buffer，stream B 消费。要求 host 不做 device-wide synchronize。

### 成功标准

- 在 A 中 record event；B 用 `cudaStreamWaitEvent`；
- event 在 producer kernel 之后 record，而不是之前；
- B 的消费 kernel 在 wait 之后 enqueue；
- 最终只在 host 真正需要结果的位置等待完成 event；
- 用 timeline 检查无关工作仍可并发。

## 核验来源

- [CUDA Programming Guide：Asynchronous Execution](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/asynchronous-execution.html)
- [CUDA Runtime API：Stream Management](https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__STREAM.html)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/07-FP16-BF16-FP8与Tensor-Core|FP16、BF16、FP8 与 Tensor Core]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
