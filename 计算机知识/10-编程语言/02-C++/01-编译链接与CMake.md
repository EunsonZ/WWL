---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 70
topics: [C++, 编译, 链接, CMake]
tags: [computer-science/cpp]
---

# 01 · 编译、链接与 CMake

## 本课目标

把“编译失败”分成可检查的阶段：预处理展开文本，编译器把一个翻译单元变成目标文件，链接器解析跨文件符号并生成可执行文件或库。CMake 不替代编译器；它生成或驱动底层构建系统。

本课只讲“怎样调用并观察现成的 C++ 工具链”。若要继续追问词法、语法、语义分析、IR、优化和代码生成内部怎样工作，请进入 [[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]；两门课共享构建产物，但不重复维护同一套理论。

## 第一个 target

以下以知识库根目录为起点；先进入 `计算机知识/10-编程语言/02-C++/`，后续命令均在这个目录运行。先确认 CMake 与 C++ 编译器已安装并能从终端调用：

```bash
cd "计算机知识/10-编程语言/02-C++"
cmake --version
c++ --version
```

<!-- code-sync: ./toolchain.cpp -->
```cpp
#include <iostream>

int main() {
    std::cout << "C++ compiler, linker, and CMake agree.\n";
}
```

`toolchain.cpp` 是一个翻译单元。课程的 CMake 已把它声明为 `toolchain` target。先配置这个目录，再只构建并运行这个目标：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target toolchain
./build/toolchain
```

预期输出为 `C++ compiler, linker, and CMake agree.`。在单配置生成器下，编译器把翻译单元编成目标文件，链接器再生成 `build/toolchain` 可执行文件；多配置生成器通常把程序放在配置子目录，需在构建时加 `--config Debug`，并按生成器显示的路径运行。

若要单独观察编译器驱动同时编译和链接同一源码，可在本目录执行 `c++ -std=c++20 toolchain.cpp -o toolchain`，它生成 `toolchain` 可执行文件；运行 `./toolchain` 会得到相同输出。这条命令帮助辨认编译器驱动的职责，后续课程仍以 CMake target 管理项目。

同目录的课程级 `CMakeLists.txt` 声明全部示例 target、共同选项、测试及并发目标的线程依赖。先理解并成功构建 `toolchain`，再看其余目标如何复用同一构建配置：

<!-- code-sync: ./CMakeLists.txt -->
```cmake
cmake_minimum_required(VERSION 3.20)
project(cpp_learning_examples LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

function(enable_course_warnings target)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

# stl.cpp 已退役，保留笔记中的历史片段，不再创建缺失源码目标。
foreach(example IN ITEMS toolchain types_functions lifetime raii move errors concurrency layout)
  add_executable(${example} ${example}.cpp)
  enable_course_warnings(${example})
  if(BUILD_TESTING)
    add_test(NAME ${example} COMMAND ${example})
  endif()
endforeach()

find_package(Threads REQUIRED)
target_link_libraries(concurrency PRIVATE Threads::Threads)
```

如果 CMake 命令本身不存在，先回到当前平台经审阅的工具链安装说明；如果配置阶段找不到编译器，再记录 `cmake --system-information` 中的候选编译器路径。不要用修改系统默认编译器或全局 include/lib 路径的方式碰运气。

## 诊断顺序

1. **配置失败**：CMake 找不到编译器、依赖或生成器；读首次报错及 cache 中实际选到的工具。
2. **编译失败**：单个 `.cpp` 的类型、头文件或语法有问题；错误位置通常在源文件。
3. **链接失败**：声明存在但定义没有参与目标、库顺序错误、ABI 不兼容；检查 target 的源文件和 `target_link_libraries`。
4. **运行失败**：程序启动后才出现；用测试、调试器和 sanitizer，而不是继续改 CMake。

使用 Makefile 或 Ninja 生成器时，配置后打开 `build/compile_commands.json`，能看到每个翻译单元实际使用的编译器、标准、include 路径和选项；其他生成器会忽略 `CMAKE_EXPORT_COMPILE_COMMANDS`，因此文件缺失本身不表示配置失败（见 [CMake 官方说明](https://cmake.org/cmake/help/latest/variable/CMAKE_EXPORT_COMPILE_COMMANDS.html)）。`PUBLIC`、`PRIVATE`、`INTERFACE` 描述的是依赖使用要求怎样沿 target 图传播，不是源文件访问权限：一个库的公共头文件若依赖另一个库的头文件，相关 include/链接要求往往要公开传播；只影响本库实现的依赖应保持 `PRIVATE`。

> [!note] 单配置与多配置生成器
> `-DCMAKE_BUILD_TYPE=Debug` 对 Ninja/Unix Makefiles 这类单配置生成器生效；Visual Studio、Xcode 等多配置生成器通常在构建/测试时用 `--config Debug` 选择配置。判断方式是看 CMake 配置摘要和生成器，而不是假定所有平台产物都位于同一目录。

> [!warning] 不要用全局 include/lib 路径掩盖依赖
> CMake target 应显式声明自己的 `target_include_directories`、编译特性和链接依赖。能在你电脑上“偶然找到”的头文件，不是可复现构建。

## 练习与成功标准

在 `toolchain.cpp` 中将输出改成你的短消息，重新构建指定 target。若使用 Makefile 或 Ninja 生成器，再从 `build/compile_commands.json` 找到它的完整编译命令。成功标准：只改源文件时 CMake 自动只重编该 target；该文件存在时，命令包含 C++20 与本课 warning 选项；且删除 `build/` 后重新配置仍可完成。链接、加载与 ABI 的下一层解释见 [[计算机知识/30-计算机系统/03-ABI调用约定与静态动态链接|ABI、调用约定与静态/动态链接]]。

**上一站**：[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]] · **下一站**：[[计算机知识/10-编程语言/02-C++/02-语法类型与函数|语法、类型与函数]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/12-泛型推导容器算法与约束|C++ 深化：从类型推导到可维护的泛型接口]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
