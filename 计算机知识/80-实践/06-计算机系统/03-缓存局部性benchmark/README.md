---
type: lab
domain: computer-science
stage: 3
status: ready
difficulty: 进阶
estimated_minutes: 65
topics: [缓存, 局部性, benchmark, C++20]
tags: [computer-science/systems, computer-science/performance, computer-science/practice]
---

# 缓存局部性 benchmark

同一个线性 `vector<double>` 被解释为 row-major 矩阵：按行遍历连续读取，按列遍历以一整行为步长。两者做完全相同的求和，自测试先验证结果契约，Release 运行才提供当前机器的计时证据。理论见 [[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]]。

## 构建、测试与测量

```bash
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release
ctest --test-dir build-release --output-on-failure
./build-release/cache_locality
```

必须用 Release/优化构建来讨论性能；Debug 只适合调试。程序运行 7 轮，每轮交替先测 row/column 的顺序，并报告全部样本与中位数；这只减少顺序偏差，不能消除 CPU 频率、热限制、其他进程、预取、TLB、缓存热身和编译器可能只向量化某一种循环等混杂因素。

程序会输出编译器及版本和基于 `NDEBUG` 的构建线索。`NDEBUG/optimized-like` 不是“已证明开启所有优化”，但它能防止报告完全丢失构建上下文；进一步判断 SIMD 需查编译命令、向量化报告或反汇编。

默认命令会在本 README 所在目录创建精确的 `./build-release/`，它不会自动清理。完成后先用 `pwd` 确认仍在 `03-缓存局部性benchmark`，再只删除该目录：

```bash
cmake -E remove_directory ./build-release
```

如果不想在 Vault 中创建构建产物，并且本机 `/private/tmp` 存在且可写，可在子 shell 中创建唯一外部 Release 目录。`trap` 只清理 `mktemp` 刚返回的精确路径：

```bash
(
  lab_build_dir="$(mktemp -d /private/tmp/workwithllm-cache-locality.XXXXXX)" || exit 1
  trap 'cmake -E remove_directory "$lab_build_dir"' EXIT
  cmake -S . -B "$lab_build_dir" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$lab_build_dir"
  ctest --test-dir "$lab_build_dir" --output-on-failure
  "$lab_build_dir/cache_locality"
)
```

## 精确伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.20)
project(cache_locality_lab LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(cache_locality cache_locality.cpp)
if(MSVC)
  target_compile_options(cache_locality PRIVATE /W4 /permissive-)
else()
  target_compile_options(cache_locality PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(BUILD_TESTING)
  add_test(NAME cache_locality_self_test COMMAND cache_locality --self-test)
endif()
```

<!-- code-sync: ./cache_locality.cpp -->
```cpp
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

std::string compiler_description() {
#if defined(__clang__)
    return "Clang " + std::to_string(__clang_major__) + "." + std::to_string(__clang_minor__) + "." +
           std::to_string(__clang_patchlevel__);
#elif defined(__GNUC__)
    return "GCC " + std::to_string(__GNUC__) + "." + std::to_string(__GNUC_MINOR__) + "." +
           std::to_string(__GNUC_PATCHLEVEL__);
#elif defined(_MSC_VER)
    return "MSVC " + std::to_string(_MSC_VER);
#else
    return "unknown";
#endif
}

constexpr std::string_view build_mode() {
#if defined(NDEBUG)
    return "NDEBUG/optimized-like";
#else
    return "debug-like";
#endif
}

double sum_row_major(const std::vector<double>& matrix, std::size_t rows, std::size_t columns) {
    double sum = 0.0;
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t column = 0; column < columns; ++column) {
            sum += matrix[row * columns + column];
        }
    }
    return sum;
}

double sum_column_major(const std::vector<double>& matrix, std::size_t rows, std::size_t columns) {
    double sum = 0.0;
    for (std::size_t column = 0; column < columns; ++column) {
        for (std::size_t row = 0; row < rows; ++row) {
            sum += matrix[row * columns + column];
        }
    }
    return sum;
}

template <class Function>
std::pair<long long, double> measure_microseconds(Function&& function) {
    const auto start = std::chrono::steady_clock::now();
    const double checksum = function();
    const auto elapsed = std::chrono::steady_clock::now() - start;
    return {std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count(), checksum};
}

long long median(std::vector<long long> samples) {
    std::sort(samples.begin(), samples.end());
    return samples[samples.size() / 2];
}

bool self_test() {
    const std::vector<double> matrix{1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
    return sum_row_major(matrix, 2, 3) == 21.0 && sum_column_major(matrix, 2, 3) == 21.0;
}

int main(int argc, char* argv[]) {
    if (argc == 2 && std::string_view(argv[1]) == "--self-test") {
        const bool passed = self_test();
        std::cout << (passed ? "self-test passed\n" : "self-test failed\n");
        return passed ? 0 : 1;
    }

    constexpr std::size_t rows = 2048;
    constexpr std::size_t columns = 2048;
    constexpr int rounds = 7;
    std::vector<double> matrix(rows * columns);
    for (std::size_t index = 0; index < matrix.size(); ++index) {
        matrix[index] = static_cast<double>(index % 251U) / 251.0;
    }

    std::vector<long long> row_times;
    std::vector<long long> column_times;
    double checksum_guard = 0.0;
    for (int round = 0; round < rounds; ++round) {
        if (round % 2 == 0) {
            const auto row = measure_microseconds([&] { return sum_row_major(matrix, rows, columns); });
            const auto column =
                measure_microseconds([&] { return sum_column_major(matrix, rows, columns); });
            row_times.push_back(row.first);
            column_times.push_back(column.first);
            checksum_guard += row.second + column.second;
        } else {
            const auto column =
                measure_microseconds([&] { return sum_column_major(matrix, rows, columns); });
            const auto row = measure_microseconds([&] { return sum_row_major(matrix, rows, columns); });
            column_times.push_back(column.first);
            row_times.push_back(row.first);
            checksum_guard += row.second + column.second;
        }
    }

    const double expected = sum_row_major(matrix, rows, columns);
    const double observed = checksum_guard / (2.0 * rounds);
    if (std::abs(expected - observed) > std::abs(expected) * 1e-12) {
        std::cerr << "checksum mismatch\n";
        return 1;
    }

    std::cout << "compiler=" << compiler_description() << ", build_mode=" << build_mode() << '\n'
              << "layout=row-major, rows=" << rows << ", columns=" << columns
              << ", rounds=" << rounds << '\n'
              << "row_major_us=";
    for (const auto value : row_times) {
        std::cout << value << ' ';
    }
    std::cout << "median=" << median(row_times) << '\n' << "column_major_us=";
    for (const auto value : column_times) {
        std::cout << value << ' ';
    }
    std::cout << "median=" << median(column_times) << '\n' << "checksum=" << observed << '\n';
}
```

## 练习与证据要求

1. 将边长改为 256、1024、4096，每组重复整个程序至少 5 次。内存不足时减小，不通过交换压力制造“更明显”结果。
2. 保留 row-major 存储，仅更换遍历顺序；解释连续性、缓存行与预取可能如何共同作用。
3. 不要把“row 必须更快”写入 CTest。若本机结果反常，先检查 Release、输入规模、其他负载与样本分布，再用编译器向量化报告/反汇编判断两个循环是否生成了不同机器代码，必要时再用性能计数器获取更直接的缓存/TLB 证据。

成功标准：CTest 只验证两种遍历结果相等；benchmark 输出编译器/构建线索、完整样本、中位数与 checksum；报告包含平台、CPU、编译器与优化配置，并明确区分计时证据、机器代码证据与 cache/TLB 计数证据。

---

**上一站**：[[计算机知识/80-实践/06-计算机系统/02-虚拟内存mmap与页错误/README|虚拟内存、mmap 与页错误]] · **下一站**：[[计算机知识/80-实践/06-计算机系统/04-文件描述符pipe-dup与进程/README|文件描述符、pipe、dup 与进程]] · **进一步**：[[计算机知识/80-实践/03-C++/04-布局缓存与并行归约/README|布局、缓存与并行归约]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
