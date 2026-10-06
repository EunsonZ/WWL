---
type: lab
domain: computer-science
stage: 20
status: ready
difficulty: 进阶
estimated_minutes: 90
verified_on: 2026-09-02
topics:
  - CUDA
  - GPU
  - 性能分析
tags:
  - computer-science/cuda
  - computer-science/lab
---

# CUDA 实验室

这里是 CUDA 的可修改实验区：用小而完整的程序，把线程索引、内存访问、归约、数值稳定性与性能观察连成一条可验证的路线。每个 `.cu` 都内置 CPU 参考实现和小型正确性测试。只有实验已用 `nvcc` 编译成功、但运行时找不到可用 GPU 时，可执行文件才会以退出码 `77` 表示“跳过环境”；没有 `nvcc` 则根本不能完成 CUDA 配置与编译，不能记为 SKIP 或 PASS。

> [!warning] 实验边界
> - 本实验不安装 NVIDIA 驱动、不修改内核模块、不使用 `sudo`，也不建议在宿主机上为课程更换 CUDA 工具链。
> - 输入全部为合成数据；不要把模型权重、私有数据、token 或真实提示词复制进实验目录。
> - CUDA 容器仍共享宿主机 NVIDIA 驱动；容器里有 `nvcc` 并不代表宿主机已正确暴露 GPU。
> - 每个实验都先跑内置正确性检查，再谈性能；一次计时不能推出普遍结论。

> [!info] 当前验证层级（2026-09-02）
> 本次写作主机是 macOS arm64，PATH 中没有 `nvcc` 或 `nvidia-smi`，当前 Python 解释器也未安装 PyTorch。已完成 Vault/code-sync、源码静态审阅与 Python 语法检查；PyTorch probe 实际返回环境 `SKIP`。没有运行 CMake 配置、CUDA 编译、CTest、GPU correctness、Nsight profile 或真实 llama.cpp offload，后文 PASS 均是具备相应环境后的预期验收，不是本机实测结果。

## 先判断你处在哪一层

- **CUDA toolkit / `nvcc`**：用来编译 `.cu` 文件的开发工具与编译器。没有它时只能做源码与配置的静态检查，不能运行本页 CTest。
- **compute capability（计算能力）**：GPU 架构支持的指令与功能代际，例如官方规格中的 `8.6`；CMake 参数中写作 `86`。它不是 CUDA toolkit 版本或驱动版本。
- **GPU 对进程可见且可用**：运行时能通过驱动找到至少一块 CUDA 设备。容器内有 `nvcc` 不能证明这一点。
- **CTest SKIP**：程序已经编译且确实运行，但因找不到可用 GPU 返回 `77`。SKIP 不是算法测试通过，更不能用来代表“本机没有 `nvcc`”。

## 推荐顺序

1. [[计算机知识/80-实践/04-CUDA/01-索引与Vector-Add实验|索引与 Vector Add]]：理解一个线程对应一个元素、边界判断与 CPU/GPU 对照；
2. [[计算机知识/80-实践/04-CUDA/02-Coalescing与Reduction|Coalescing 与 Reduction]]：观察相邻访问和树形归约的关系；
3. [[计算机知识/80-实践/04-CUDA/03-Softmax与矩阵乘法实验|数值稳定 Softmax 与矩阵乘法]]：先减最大值完成 Softmax，再用非整齐 shape 观察 tiled GEMM；
4. [[计算机知识/80-实践/04-CUDA/04-Profiling与Offload观察|Profiling 与 Offload 观察]]：用 CUDA event、PyTorch 与已有 llama.cpp 程序验证“实际是否卸载”。

## 容器优先的最小环境

推荐使用组织已审阅的 CUDA 开发容器，并显式把当前实验目录挂进容器。宿主机需要已经安装兼容的 NVIDIA 驱动与 container runtime GPU 支持；二者都不是本实验要修改的对象。进入容器后，先用 `nvidia-smi` 和 `nvcc --version` 观察环境。构建前从目标 GPU 的官方规格或只读设备查询取得 compute capability，并在本目录显式传入 `-DCMAKE_CUDA_ARCHITECTURES=<已核验数值>`；例如官方规格是 `8.6` 时传 `86`，但不要把示例数值照搬到其他 GPU。只有构建机可见的 GPU 就是部署目标时才选择 `native`。随后执行 `cmake --build build` 与 `ctest --test-dir build --output-on-failure`。程序在运行时发现无可用设备会以 77 明确跳过，而不是把环境缺失报告成算法通过。

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.24)

project(cuda_labs LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)

if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES OR CMAKE_CUDA_ARCHITECTURES STREQUAL "")
  message(FATAL_ERROR
    "Set CMAKE_CUDA_ARCHITECTURES to the reviewed target compute capability; use native only when the build GPU is visible and is the deployment target.")
endif()

include(CTest)

function(add_cuda_lab target)
  add_executable(${target} ${target}.cu)
  set_target_properties(${target} PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON)
  target_compile_options(${target} PRIVATE
    $<$<COMPILE_LANGUAGE:CUDA>:--expt-relaxed-constexpr>)
  if(BUILD_TESTING)
    add_test(NAME ${target} COMMAND ${target})
    # 77 means the executable found no usable CUDA device; that is an
    # environment skip, not a failed correctness assertion.
    set_tests_properties(${target} PROPERTIES SKIP_RETURN_CODE 77)
  endif()
endfunction()

add_cuda_lab(01_vector_add)
add_cuda_lab(02_reduction)
add_cuda_lab(03_stable_softmax)
add_cuda_lab(03_tiled_gemm)
add_cuda_lab(04_profile_offload)
```

### Ubuntu 与 Arch：只记录差异，不在此处安装

Ubuntu 的 NVIDIA 驱动、容器运行时与 CUDA toolkit 常来自发行版包、NVIDIA 仓库或团队镜像；Arch 则更常以滚动包与较新的内核组合出现。两者的包名、内核 ABI、驱动与 toolkit 版本节奏不同，不能互抄安装命令。无论哪一个，先确认 `nvidia-smi` 能在宿主机工作，再用同一镜像验证容器内 GPU 可见；若版本不匹配或无 GPU，把下面实验保留为静态阅读，交由环境管理员处理。

## 每次实验的记录模板

目标、镜像标签或原生系统、GPU 型号与驱动、`nvcc` 版本、构建命令、正确性输出、计时命令、实际输出、改变了什么、如何清理构建目录。构建产物只会落在本目录的 `build/`，要重置时可删除这个精确目录；不要执行宽泛删除命令。

## 完成标准

- [ ] 我能解释 CPU 参考实现与 GPU 输出为何应该相同，以及浮点容差为何存在；
- [ ] 每个可运行实验都先通过内置 PASS，再记录性能；
- [ ] 我能区分“容器内有 CUDA 编译器”“GPU 对进程可见”和“模型层已卸载”这三件事；
- [ ] 无 `nvcc` 时，我只记录静态检查边界；已编译但无可用 GPU 时，我记录 CTest SKIP，没有把任一种环境缺失记成程序通过；
- [ ] 我没有安装驱动、改动系统 CUDA 或把敏感数据写入本目录。

---

**返回**：[[计算机知识/00-开始/00-计算机知识-首页|计算机知识首页]] · **下一站**：[[计算机知识/80-实践/04-CUDA/01-索引与Vector-Add实验|索引与 Vector Add]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
