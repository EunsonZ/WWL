---
type: practice
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 45
domain: computer-science
tags:
  - computer-science/cpp
  - computer-science/cmake
  - computer-science/debugging
---

# 构建与调试小项目

目标是把“编译通过”与“行为正确”拆开：`word_counter` 是可执行程序，`word_counter_tests` 是可重复的行为证据。它也连接 [[计算机知识/10-编程语言/02-C++/07-错误测试调试与Sanitizer|错误、测试、调试与 Sanitizer]] 与 [[计算机知识/30-计算机系统/00-计算机系统-MOC|计算机系统 MOC]]。

## 构建、测试与可观察输出

在本目录执行；构建目录是本课程唯一允许创建和删除的目标。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
./build/word_counter "Hello, hello! C++20; C++20."
```

CTest 必须报告一项通过；最后一行输出应包含 `hello: 2`、`c: 2` 与 `20: 2`。`std::map` 的键按字典序输出，因此它不是输入顺序的断言。测试使用显式条件与非零返回值，而不是可被 `NDEBUG` 移除的 `assert`，所以 Release 构建也会真正执行判定。CMake 在 MSVC 上使用 `/W4`，在 GNU/Clang 上使用 `-Wall -Wextra -Wpedantic`，不会把 GCC/Clang 参数直接交给 MSVC。

## 让调试器回答一个具体问题

下面命令有意访问不存在的键。它不是内存破坏练习：标准库会抛出 `std::out_of_range`，可让你观察调用栈和抛出点。

```sh
lldb -- ./build/word_counter "hello" --debug-fail
```

在 LLDB 中输入 `run`，停止后输入 `bt` 看调用链、`frame variable counts` 看局部容器。修复练习不是吞掉异常，而是在访问前用 `find` 或 `contains` 定义缺失键的业务语义。完成后不应把 `--debug-fail` 当作正常路径。

## 精确的伴随文件

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.24)
project(cpp_build_debug LANGUAGES CXX)

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

add_library(word_counter_lib word_counter.cpp)
target_include_directories(word_counter_lib PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
enable_project_warnings(word_counter_lib)

add_executable(word_counter main.cpp)
target_link_libraries(word_counter PRIVATE word_counter_lib)
enable_project_warnings(word_counter)

add_executable(word_counter_tests tests.cpp)
target_link_libraries(word_counter_tests PRIVATE word_counter_lib)
enable_project_warnings(word_counter_tests)

enable_testing()
add_test(NAME word_counter_tests COMMAND word_counter_tests)
```

## 用同一 target 对比静态与共享链接

`add_library(word_counter_lib ...)` 未写死库类型，因此可在第二个隔离构建树启用 CMake 的 `BUILD_SHARED_LIBS`：

```sh
cmake -S . -B build-shared -DCMAKE_BUILD_TYPE=Debug -DBUILD_SHARED_LIBS=ON
cmake --build build-shared
ctest --test-dir build-shared --output-on-failure
```

两个构建都应通过同一行为测试。然后用当前平台的产物/依赖查看工具，确认默认构建把库代码链接进可执行文件，而共享构建让可执行文件记录对动态库的运行时依赖；macOS 可查看 `otool -L build-shared/word_counter`，Linux 可查看 `ldd build-shared/word_counter`。这些工具显示的是当前产物事实，不是跨平台文件名保证。

成功标准：能从构建目录指出库产物、可执行产物和测试 target；能解释“头文件可见”解决编译期 API，而 `target_link_libraries` 建立链接依赖；能区分链接时未定义符号与启动时动态库缺失。这里直接暴露 C++ STL 类型只是同工具链教学例子，不是稳定插件 ABI；跨组件契约见 [[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与静态/动态链接]]。

<!-- code-sync: ./word_counter.hpp -->
```cpp
#pragma once

#include <cstddef>
#include <map>
#include <string>
#include <string_view>

std::map<std::string, std::size_t> count_words(std::string_view text);
```

<!-- code-sync: ./word_counter.cpp -->
```cpp
#include "word_counter.hpp"

#include <cctype>

std::map<std::string, std::size_t> count_words(std::string_view text) {
    std::map<std::string, std::size_t> counts;
    std::string word;

    for (unsigned char ch : text) {
        if (std::isalnum(ch) != 0) {
            word += static_cast<char>(std::tolower(ch));
            continue;
        }
        if (!word.empty()) {
            ++counts[word];
            word.clear();
        }
    }
    if (!word.empty()) {
        ++counts[word];
    }
    return counts;
}
```

<!-- code-sync: ./main.cpp -->
```cpp
#include "word_counter.hpp"

#include <iostream>
#include <string>

int main(int argc, char * argv[]) {
    const std::string text = argc > 1 ? argv[1] : "RAII makes ownership visible";
    const auto counts = count_words(text);

    for (const auto & [word, count] : counts) {
        std::cout << word << ": " << count << '\n';
    }

    if (argc > 2 && std::string(argv[2]) == "--debug-fail") {
        return counts.at("this-token-is-not-present");
    }
}
```

<!-- code-sync: ./tests.cpp -->
```cpp
#include "word_counter.hpp"

#include <iostream>

int main() {
    const auto counts = count_words("Hello, hello! C++20; C++20.");
    if (counts.at("hello") != 2 || counts.at("c") != 2 || counts.at("20") != 2 ||
        counts.size() != 3) {
        std::cerr << "word counter result did not match the expected table\n";
        return 1;
    }
}
```

## 恢复

若且仅若相应目录中存在 `CMakeCache.txt` 且当前目录为本项目根目录，可执行 `cmake --build build --target clean` 或 `cmake --build build-shared --target clean` 清理产物；需要删除构建树时，只删除这个项目内明确的 `build/` 或 `build-shared/`，随后重新运行配置命令。不要复制递归清理命令到上级目录。

上一站 [[计算机知识/80-实践/03-C++/00-C++实验室|C++ 实验室]]；下一站 [[计算机知识/80-实践/03-C++/02-RAII与张量缓冲区/README|RAII 与张量缓冲区]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/12-泛型推导容器算法与约束|C++ 深化：从类型推导到可维护的泛型接口]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
