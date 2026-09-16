---
type: lesson
domain: computer-science
stage: 3
status: ready
difficulty: 入门到中级
estimated_minutes: 70
verified_on: 2026-09-02
source: NVIDIA CUDA Programming Guide
topics:
  - kernel
  - grid
  - block
  - thread
  - warp
  - SM
tags:
  - computer-science/cuda
  - computer-science/parallelism
---

# 03 · Kernel 与 Grid、Block、Thread、Warp

> 上一站：[[计算机知识/40-并行与异构计算/01-CUDA/02-CUDA软件栈与Linux部署边界|CUDA 软件栈与 Linux 部署边界]] ｜ 下一站：[[计算机知识/40-并行与异构计算/01-CUDA/04-内存层级合并访问与BankConflict|内存层级与访问模式]]

## 本课目标

学完后，你能：

1. 区分 source-level thread hierarchy 与 hardware scheduling hierarchy；
2. 推导一维与二维全局索引，并为非整除大小添加边界检查；
3. 解释 block 独立性、SM 调度与 warp 的关系；
4. 编译并验证一个带完整错误检查的 vector add。

## 1. 四个编程层级

```text
kernel launch
  grid
    block
      thread
```

- **kernel**：host 启动、device 上由许多 thread 执行的函数；
- **grid**：一次 launch 的全部 thread blocks；
- **block**：可共享 shared memory、可用 block 级 barrier 协作的一组 threads；
- **thread**：执行 kernel 程序的一条逻辑线程。

CUDA 用 `dim3` 让 grid 与 block 可有 x/y/z 维，但硬件最终仍按资源把 blocks 分配给 SM。一个 block 的 threads 在同一 SM 上执行；不同 blocks 的先后次序不保证，所以普通 kernel 不能依赖“block 0 必先于 block 1 完成”。

## 2. 一维索引

最常见的“一 thread 一元素”：

```cpp
const int i = blockIdx.x * blockDim.x + threadIdx.x;
if (i < n) {
  output[i] = input[i];
}
```

当 `threads = 256` 时，用向上取整计算 blocks：

```cpp
const int blocks = (n + threads - 1) / threads;
```

例如 `n=1000`，需要 4 blocks，共创建 1024 个逻辑 threads；最后 24 个必须被 `i < n` 拦住。多创建尾部 threads 通常比为每个长度设计特殊 block 形状简单。

> [!warning] 整数范围也是边界
> 巨大数组的元素数和字节数应使用足够宽的无符号类型，并在乘法前检查溢出。教学样例用 `int n=1000` 是受控小输入，不是大型生产索引的通用模板。

## 3. 二维索引

对 `height × width` 图像：

```cpp
const int x = blockIdx.x * blockDim.x + threadIdx.x;
const int y = blockIdx.y * blockDim.y + threadIdx.y;
if (x < width && y < height) {
  const int linear = y * width + x;
  output[linear] = input[linear];
}
```

launch 形状：

```cpp
dim3 block(16, 16);
dim3 grid((width + block.x - 1) / block.x,
          (height + block.y - 1) / block.y);
```

`16×16=256` 只是可读起点，不是普适最优值。寄存器、shared memory、访问模式、occupancy 和 GPU 架构会共同限制有效配置。

## 4. Warp 是执行细节，不是 launch 维度

NVIDIA GPU 把 threads 以 warp 为执行组；当前 CUDA 文档中 warp size 是 32，但健壮的查询/工具应从 device property 获取，不把别的硬件模型混进来。

几个边界：

- 你 launch 的是 grid/block/thread，不是“若干 warp”；
- warp 内 active threads 执行同一指令路径；分支可能让不同 lane 在不同路径上分时执行；
- block size 不是 warp size 的整数倍时，最后一个 warp 会有 inactive lanes；
- warp-level primitive 有明确 mask 和同步语义，不能凭“这些 threads 大概一起跑”省略要求。

### Residency 与 occupancy：同一个 block 会占住一组资源

block 被分派到某个 SM 后，它的 threads、register 配额和 shared-memory 配额共同占用该 SM 的资源；普通 block 不会执行到一半迁移到另一个 SM。一个 SM 能同时驻留多少 blocks/warps，至少受这些上限共同约束：

- 每 block 的 threads 与每 SM 可驻留 threads/warps；
- 每 thread 的 register 使用量经过分配粒度取整后，占用的 register file；
- 每 block 的静态与动态 shared memory；
- 每 SM 最大 resident blocks，以及架构特有的调度限制。

因此“256 threads/block”只是一项 launch 选择，不能单独推出 occupancy。理论 occupancy 表示 active warps 相对硬件上限的比例，可帮助隐藏延迟，但它不是性能分数：为了多驻留一个 block 而压低 registers，可能引发 local-memory spill；减少 shared memory 也可能失去更有价值的数据复用。先确认 kernel 能正确 launch，再用 compiler resource report、occupancy calculator 与 profiler 观察真实限制，完整方法见[[计算机知识/40-并行与异构计算/01-CUDA/09-Roofline与Nsight性能方法|Roofline、occupancy 与 Nsight]]。

## 5. 一个完整 vector add

伴随文件是本页代码的规范来源：`vector_add.cu`。

<!-- code-sync: ./vector_add.cu -->
```cpp
#include <cuda_runtime.h>

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

__global__ void vector_add(const float* a, const float* b, float* c, int n) {
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


  constexpr int n = 1000;
  const std::size_t bytes = n * sizeof(float);
  std::vector<float> a(n, 1.5F);
  std::vector<float> b(n, 2.0F);
  std::vector<float> c(n, 0.0F);

  float* d_a = nullptr;
  float* d_b = nullptr;
  float* d_c = nullptr;
  CUDA_CHECK(cudaMalloc(&d_a, bytes));
  CUDA_CHECK(cudaMalloc(&d_b, bytes));
  CUDA_CHECK(cudaMalloc(&d_c, bytes));
  CUDA_CHECK(cudaMemcpy(d_a, a.data(), bytes, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_b, b.data(), bytes, cudaMemcpyHostToDevice));

  constexpr int threads = 256;
  const int blocks = (n + threads - 1) / threads;
  vector_add<<<blocks, threads>>>(d_a, d_b, d_c, n);
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaMemcpy(c.data(), d_c, bytes, cudaMemcpyDeviceToHost));

  for (int i = 0; i < n; ++i) {
    if (std::fabs(c[i] - 3.5F) > 1e-6F) {
      std::fprintf(stderr, "Mismatch at %d: %f\n", i, c[i]);
      cudaFree(d_c);
      cudaFree(d_b);
      cudaFree(d_a);
      return 1;
    }
  }

  CUDA_CHECK(cudaFree(d_c));
  CUDA_CHECK(cudaFree(d_b));
  CUDA_CHECK(cudaFree(d_a));
  std::puts("PASS: vector_add");
  return 0;
}
```

在受支持的 Linux + Toolkit + NVIDIA GPU 环境中，可从本目录执行：

```bash
nvcc -std=c++17 -O2 -lineinfo vector_add.cu -o vector_add
./vector_add
```

预期为 `PASS: vector_add`。编译前先确认 `nvcc --version`、target GPU 和 release notes；输出二进制不要加入知识 Vault。

### 验证层次

1. `nvcc` 成功：host/device 源码能被当前 toolchain 编译；
2. 程序输出 PASS：该 GPU/driver/runtime 上此输入得到预期值；
3. 改成 `n=1, 255, 256, 257, 1000`：覆盖边界；
4. profiler/benchmark：才开始回答性能，不能从 PASS 推断快。

当前写作环境无 `nvcc` 和 NVIDIA GPU，因此这里只完成源文件存在、代码同步与静态审阅，未完成 1—4。

## 练习

1. 手算 `n=513, threads=256` 时 blocks、总 threads 和被边界拦住的数量。
2. 把 vector add 改成 SAXPY：`y[i] = a*x[i] + y[i]`。
3. 用 CPU 参考结果比较，而不是只看前 5 个元素。

### 成功标准

- 对 1 的答案是 3 blocks、768 threads、255 个尾部 threads；
- kernel 对所有非整除长度不越界；
- launch 后检查 `cudaGetLastError()`，在 host 消费结果前建立同步；同步 memcpy 已承担该样例的等待；
- 失败路径不会把“程序运行结束”误报为数值通过。

## 核验来源

- [CUDA Programming Guide：Programming Model](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/programming-model.html)
- [CUDA Programming Guide：Intro to CUDA C++](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html)

---

**返回**：[[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] · **继续**：[[计算机知识/40-并行与异构计算/01-CUDA/04-内存层级合并访问与BankConflict|内存层级、合并访问与 Bank Conflict]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
