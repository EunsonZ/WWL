---
type: lab
domain: computer-science
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 90
topics: [C++, AoS, SoA, 缓存, 并行归约, SIMD]
tags: [computer-knowledge/cpp, computer-science/performance]
---

# 布局、缓存与并行归约

这个实验把“连续布局更友好”“多线程可能更快”“循环可能 SIMD 化”分成三类证据：测试只验证数学契约；计时只描述本机这次运行；编译器报告或反汇编才说明是否生成向量指令。它不要求外部仓库、模型或 GPU。

## 构建、测试与运行

```bash
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release
ctest --test-dir build-release --output-on-failure
./build-release/layout_benchmark
```

多配置生成器在构建与测试时补 `--config Release`。成功标准：`layout_tests` 通过；benchmark 打印元素数、重复次数、线程数、三种耗时和 checksum；三种 checksum 相等。**不要**把 `parallel_soa_us` 必须最小写进测试：线程创建、核心数、频率、系统负载、工作规模和内存带宽都会改变排序。

## 三条路径比较什么

| 路径 | 数据布局/执行 | 能观察什么 | 不能直接证明什么 |
| --- | --- | --- | --- |
| `sum_aos` | `value` 与 `id` 交错，只读取 value | 不需要的 id 也可能占缓存/带宽 | AoS 在所有任务都更慢 |
| `sum_soa` | value 连续、单线程 | 热字段更紧凑，循环形状适合自动向量化 | 编译器一定生成 SIMD |
| `parallel_sum_soa` | 分块、线程局部和、最后归并 | 避免每个元素更新共享 atomic/锁 | 线程越多越快、浮点位级相同 |

这里用 `std::jthread` 把 join 责任绑定到对象生命周期；正常路径仍显式 join，若创建后续线程时抛异常，已创建的 jthread 也会在栈展开中安全加入。计算使用 `double` 累加 `float` 输入以减小误差，但并行分块仍会改变加法顺序。真实推理 kernel 要使用数学课程定义的容差比较，而不是把位级相同当作唯一正确性标准。参见 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]。

## 精确伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.20)
project(cpp_layout_cache_lab LANGUAGES CXX)

include(CTest)
find_package(Threads REQUIRED)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

function(enable_lab_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(layout_benchmark layout_benchmark.cpp)
target_link_libraries(layout_benchmark PRIVATE Threads::Threads)
enable_lab_warnings(layout_benchmark)

add_executable(layout_tests layout_tests.cpp)
target_link_libraries(layout_tests PRIVATE Threads::Threads)
enable_lab_warnings(layout_tests)

if(BUILD_TESTING)
  add_test(NAME layout_tests COMMAND layout_tests)
endif()
```

<!-- code-sync: ./layout_math.hpp -->
```cpp
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <span>
#include <stdexcept>
#include <thread>
#include <vector>

struct Sample {
    float value;
    std::uint32_t id;
};

inline double sum_aos(std::span<const Sample> samples) {
    double result = 0.0;
    for (const Sample& sample : samples) {
        result += sample.value;
    }
    return result;
}

inline double sum_soa(std::span<const float> values) {
    double result = 0.0;
    for (const float value : values) {
        result += value;
    }
    return result;
}

inline double parallel_sum_soa(std::span<const float> values, std::size_t worker_count) {
    if (worker_count == 0) {
        throw std::invalid_argument("worker_count must be positive");
    }
    if (values.empty()) {
        return 0.0;
    }

    worker_count = std::min(worker_count, values.size());
    std::vector<double> partials(worker_count, 0.0);
    std::vector<std::jthread> workers;
    workers.reserve(worker_count);

    const std::size_t base = values.size() / worker_count;
    const std::size_t remainder = values.size() % worker_count;

    for (std::size_t worker = 0; worker < worker_count; ++worker) {
        const std::size_t begin = worker * base + std::min(worker, remainder);
        const std::size_t end = begin + base + (worker < remainder ? 1U : 0U);
        workers.emplace_back([values, &partials, worker, begin, end] {
            partials[worker] = sum_soa(values.subspan(begin, end - begin));
        });
    }
    for (std::jthread& worker : workers) {
        worker.join();
    }
    return std::accumulate(partials.begin(), partials.end(), 0.0);
}
```

<!-- code-sync: ./layout_tests.cpp -->
```cpp
#include "layout_math.hpp"

#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>

int main() {
    const std::vector<Sample> aos{{1.0F, 10}, {2.0F, 11}, {3.0F, 12}, {4.0F, 13}};
    const std::vector<float> soa{1.0F, 2.0F, 3.0F, 4.0F};

    int failures = 0;
    const auto check = [&failures](bool condition, std::string_view name) {
        if (!condition) {
            std::cerr << "FAILED: " << name << '\n';
            ++failures;
        }
    };

    check(sum_aos(aos) == 10.0, "AoS sum");
    check(sum_soa(soa) == 10.0, "SoA sum");
    check(parallel_sum_soa(soa, 1) == 10.0, "one-worker reduction");
    check(parallel_sum_soa(soa, 3) == 10.0, "three-worker reduction");
    check(parallel_sum_soa({}, 2) == 0.0, "empty input");

    bool rejected_zero_workers = false;
    try {
        static_cast<void>(parallel_sum_soa(soa, 0));
    } catch (const std::invalid_argument&) {
        rejected_zero_workers = true;
    }
    check(rejected_zero_workers, "zero workers rejected");
    if (failures == 0) {
        std::cout << "layout and reduction tests passed\n";
    }
    return failures == 0 ? 0 : 1;
}
```

<!-- code-sync: ./layout_benchmark.cpp -->
```cpp
#include "layout_math.hpp"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <thread>
#include <utility>
#include <vector>

template <class Function>
std::pair<long long, double> measure_us(Function function, int repetitions) {
    const auto start = std::chrono::steady_clock::now();
    double checksum = 0.0;
    for (int repetition = 0; repetition < repetitions; ++repetition) {
        checksum += function();
    }
    const auto elapsed = std::chrono::steady_clock::now() - start;
    return {std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count(), checksum};
}

int main() {
    constexpr std::size_t element_count = 2'000'000;
    constexpr int repetitions = 8;
    std::vector<Sample> aos;
    std::vector<float> soa;
    aos.reserve(element_count);
    soa.reserve(element_count);
    for (std::size_t index = 0; index < element_count; ++index) {
        const float value = static_cast<float>(index % 17);
        aos.push_back({value, static_cast<std::uint32_t>(index)});
        soa.push_back(value);
    }

    const std::size_t workers = std::max(1U, std::thread::hardware_concurrency());
    const auto [aos_us, aos_checksum] = measure_us([&aos] { return sum_aos(aos); }, repetitions);
    const auto [soa_us, soa_checksum] = measure_us([&soa] { return sum_soa(soa); }, repetitions);
    const auto [parallel_us, parallel_checksum] =
        measure_us([&soa, workers] { return parallel_sum_soa(soa, workers); }, repetitions);

    std::cout << "elements=" << element_count << ", repetitions=" << repetitions
              << ", workers=" << workers << '\n'
              << "aos_us=" << aos_us << ", checksum=" << aos_checksum << '\n'
              << "soa_us=" << soa_us << ", checksum=" << soa_checksum << '\n'
              << "parallel_soa_us=" << parallel_us << ", checksum=" << parallel_checksum << '\n';
}
```

## 练习

1. 把 `Sample` 增加两个当前求和不使用的字段，固定输入与构建配置，重复运行至少五次。报告中位数，不只保留最快值。
2. 把工作规模分别改为 `1'000`、`1'000'000` 和 `20'000'000`，解释线程创建固定成本与内存带宽上限怎样改变结果；内存不足时缩小规模，不触发交换来假装测主存。
3. 用当前编译器的优化报告或反汇编确认 `sum_soa` 是否向量化；先记录编译器版本和 Release 选项。没有向量化也是有效结果，继续找循环依赖、浮点语义和成本模型证据。
4. 把并行实现错误地改成所有线程更新一个共享和，观察协议问题后恢复线程局部 partial。比较锁/原子争用和归约顺序，不把错误版本留在最终代码。

## 成功标准

- 测试验证 AoS、SoA、不同 worker 数、空输入与非法 worker 数；
- 计时结论包含机器、编译器、Release 选项、输入规模、线程数和多次分布；
- SIMD 结论有优化报告或反汇编证据，而不是由源码形状猜测；
- 能解释线程局部 partial 如何减少共享热点，以及浮点归约为何需要容差；
- 不把 CPU 线程/SIMD 结果外推为 CUDA 结果；GPU 路线进入 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]]。

## 恢复

只删除本实验自己的 `build-release/` 后重新配置；不要清理上级实验室、模型或外部源码目录。源码回到测试通过状态后再重新测量。

**上一站**：[[计算机知识/80-实践/03-C++/02-RAII与张量缓冲区/README|RAII 与张量缓冲区]] · **下一站**：[[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|llama.cpp token trace]] · **原理**：[[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] · [[计算机知识/30-计算机系统/05-并发并行SIMD与加速器|并发、并行、SIMD 与加速器]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/13-并发内存模型与系统接口审计|C++ 深化：并发、内存模型与系统接口审计]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
