---
type: practice
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 55
domain: computer-science
tags:
  - computer-science/cpp
  - computer-science/raii
  - computer-science/memory
---

# RAII 与张量缓冲区

目标是把“资源”说具体：`TensorBuffer<T>` 唯一拥有连续的元素缓冲区；`std::vector<T>` 的构造、析构、异常路径与默认 move 操作共同管理这块内存。没有任何裸 `new`、`delete` 或跨函数的“记得释放”约定。语言背景见 [[计算机知识/10-编程语言/02-C++/04-栈堆RAII与智能指针|栈、堆、RAII 与智能指针]]；连续布局、缓存和带宽的背景见 [[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]。

## 构建与成功标准

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
./build/tensor_demo
```

测试必须确认 24 个元素、一次合法读写和一次越界异常；示例程序应打印 `elements=6, activation[1,2]=0.75`。测试用显式条件与非零返回值报告失败，因此不会在定义 `NDEBUG` 的 Release 构建中空过。接着把 `{2, 3}` 改成 `{2, 0}`，观察构造函数拒绝零维度；不要通过删除检查来“修复”错误。

## 读代码时要能回答的四件事

| 问题 | 代码中的证据 |
| --- | --- |
| 谁拥有元素？ | 成员 `data_`，其析构自动释放。 |
| 形状如何保存？ | 成员 `shape_`，构造时与元素计数一起检查。 |
| 如何从多维坐标到连续内存？ | `flat_index` 的逐轴 `offset = offset * extent + index`。 |
| 错误怎样保留因果？ | 秩不匹配和每一轴越界各自抛出明确异常。 |

这正是将来把主机端连续缓冲区交给设备 API 前应先验证的边界；设备并行版本从 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA 学习路线]] 开始。这里没有假装 `std::vector` 等同于 GPU 内存，也没有执行设备分配。

## 精确的伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.24)
project(raii_tensor_buffer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

function(enable_project_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(tensor_demo main.cpp)
enable_project_warnings(tensor_demo)

add_executable(tensor_tests tests.cpp)
enable_project_warnings(tensor_tests)

enable_testing()
add_test(NAME tensor_tests COMMAND tensor_tests)
```

<!-- code-sync: ./tensor_buffer.hpp -->
```cpp
#pragma once

#include <cstddef>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

template <class T>
class TensorBuffer {
public:
    explicit TensorBuffer(std::vector<std::size_t> shape)
        : shape_(std::move(shape)), data_(checked_element_count(shape_)) {}

    const std::vector<std::size_t> & shape() const noexcept { return shape_; }
    std::size_t size() const noexcept { return data_.size(); }

    T & at(const std::vector<std::size_t> & index) { return data_.at(flat_index(index)); }
    const T & at(const std::vector<std::size_t> & index) const { return data_.at(flat_index(index)); }

private:
    static std::size_t checked_element_count(const std::vector<std::size_t> & shape) {
        if (shape.empty()) {
            throw std::invalid_argument("tensor rank must be at least one");
        }
        std::size_t count = 1;
        for (const auto extent : shape) {
            if (extent == 0 || count > std::numeric_limits<std::size_t>::max() / extent) {
                throw std::invalid_argument("invalid or overflowing tensor shape");
            }
            count *= extent;
        }
        return count;
    }

    std::size_t flat_index(const std::vector<std::size_t> & index) const {
        if (index.size() != shape_.size()) {
            throw std::out_of_range("index rank does not match tensor rank");
        }
        std::size_t offset = 0;
        for (std::size_t axis = 0; axis < shape_.size(); ++axis) {
            if (index[axis] >= shape_[axis]) {
                throw std::out_of_range("tensor index is outside its shape");
            }
            offset = offset * shape_[axis] + index[axis];
        }
        return offset;
    }

    std::vector<std::size_t> shape_;
    std::vector<T> data_;
};
```

<!-- code-sync: ./main.cpp -->
```cpp
#include "tensor_buffer.hpp"

#include <iostream>

int main() {
    TensorBuffer<float> activation({2, 3});
    activation.at({1, 2}) = 0.75F;

    std::cout << "elements=" << activation.size()
              << ", activation[1,2]=" << activation.at({1, 2}) << '\n';
}
```

<!-- code-sync: ./tests.cpp -->
```cpp
#include "tensor_buffer.hpp"

#include <iostream>
#include <stdexcept>

int main() {
    TensorBuffer<int> tensor({2, 3, 4});
    if (tensor.size() != 24) {
        std::cerr << "tensor element count was not 24\n";
        return 1;
    }
    tensor.at({1, 2, 3}) = 42;
    if (tensor.at({1, 2, 3}) != 42) {
        std::cerr << "tensor read/write check failed\n";
        return 1;
    }

    bool caught = false;
    try {
        static_cast<void>(tensor.at({2, 0, 0}));
    } catch (const std::out_of_range &) {
        caught = true;
    }
    if (!caught) {
        std::cerr << "out-of-range tensor access did not throw\n";
        return 1;
    }
}
```

## 恢复

在本项目根目录确认 `build/CMakeCache.txt` 存在后，才可以清理这个项目的 `build/` 并重新配置；不要把清理目标改为 `03-C++` 或 Vault 根目录。源代码的错误实验可直接撤销，测试能证明不变量是否已经恢复。

上一站 [[计算机知识/80-实践/03-C++/01-构建与调试小项目/README|构建与调试小项目]]；下一站 [[计算机知识/80-实践/03-C++/03-llama.cpp-token概率与耗时trace/README|llama.cpp trace]]；返回 [[计算机知识/80-实践/03-C++/00-C++实验室|C++ 实验室]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/11-对象模型值类别与异常安全|C++ 深化：对象模型、值类别和异常安全]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
