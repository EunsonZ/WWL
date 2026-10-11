---
课程: "C++"
类型: "可运行高级分支"
stage: 4
aliases: []
sources:
  - https://timsong-cpp.github.io/cppwp/n4861/dcl.fct.def.coroutine
  - https://timsong-cpp.github.io/cppwp/n4861/coroutine.handle.resumption
prerequisites:
  - "[[计算机知识/10-编程语言/02-C++/10-系统课程/16-协程帧拥有暂停与取消]]"
---

# 单线程拥有报告协程：安装包消费者

本实验将既有 ReportSession 放入实际 C++20 协程：创建后初始挂起，第一次 resume 生成报告后 co_await 挂起，第二次 resume 才复制拥有文本并完成。解释见[[计算机知识/10-编程语言/02-C++/10-系统课程/16-协程帧拥有暂停与取消|第16讲]]；它从[[计算机知识/10-编程语言/02-C++/10-系统课程/14-有界任务关闭取消与性能证据|第14讲]]继续帧拥有责任，没有替换原线程队列。

| 文件 | 责任 |
| --- | --- |
| [owned_report_task.hpp](owned_report_task.hpp) | move-only owner、promise、initial/body/final挂起、终态保护、取消与拥有结果 |
| [consumer.cpp](consumer.cpp) | 调用方输入/设置先析构，挂起时移动 owner，结果在帧销毁后仍可使用 |
| [tests.cpp](tests.cpp) | 正常、解析失败、暂停后异常、取消、移动、析构与明确失败计数 |
| [CMakeLists.txt](CMakeLists.txt) | 独立 find_package，仅链接安装包 WWL::measurement |

## 干净安装和独立构建

在本目录执行。先在新的库外临时目录构建/安装已有组件，再配置本独立项目。不会写系统安装目录；BUILD_TESTING=OFF 只用于本次库构建，当前验证集中在新增协程消费者，旧库测试没有因此冒称重跑。

```bash
scratch=$(mktemp -d "${TMPDIR:-/tmp}/wwl-coroutine.XXXXXX")
cmake -S ../.. -B "$scratch/library-debug" -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=OFF
cmake --build "$scratch/library-debug" -j 4
cmake --install "$scratch/library-debug" --prefix "$scratch/install-debug"
cmake -S . -B "$scratch/consumer-debug" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_PREFIX_PATH="$scratch/install-debug"
cmake --build "$scratch/consumer-debug" -j 4
ctest --test-dir "$scratch/consumer-debug" --output-on-failure -V
cmake -S ../.. -B "$scratch/library-release" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build "$scratch/library-release" -j 4
cmake --install "$scratch/library-release" --prefix "$scratch/install-release"
cmake -S . -B "$scratch/consumer-release" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$scratch/install-release"
cmake --build "$scratch/consumer-release" -j 4
ctest --test-dir "$scratch/consumer-release" --output-on-failure -V
```

CMake 找到的 C++ 编译器必须支持 C++20 coroutine；需要固定编译器时，对库和消费者都传同一个 `-DCMAKE_CXX_COMPILER=/实际路径/clang++`。独立消费者不需要 WWL_CPP_LABS，因为该项只用于库构建。隔离库源码副本若不带原02/04实验目录，在库配置时传 `-DWWL_CPP_LABS=/实际库/计算机知识/80-实践/03-C++`；消费者依然只读安装后的公开头文件和库。

消费者应输出与[原变标定参考](../../data/report-calibrated-reference.txt)一致的完整报告，再输出 `consumer: owned result survives frame destruction`。测试输出 `coroutine contracts: live_frames=0 failures=0`，CTest两项均通过。任何检查失败返回非零，Release没有运行时assert。

## 接口和证据边界

make_owned_report 按值持有输入与设置，工厂返回时状态 created；异常发生在进入函数体以前可能直接从工厂抛出。resume 的 true 表示发生一次恢复，仍须检查 state。created/suspended 可取消并立即销毁帧；重复取消返回 false；completed/failed 不改写。take_report 仅能成功一次，返回拥有string并释放完成帧；failed时重抛保存的异常。default/moved-from owner 是empty，安全拒绝resume/cancel；析构或移动赋值会释放仍持有的帧。

所有操作和live_frames诊断限同一线程。没有暴露handle，没有外部回调注册，不能把本例当作多线程调度器。ReportSession、stream在函数体挂起时活着，正常co_return/异常退出时先清理；最终挂起保留promise和参数，等待owner回收。live_frames只数promise对象，不统计堆块/字节、PMR分配或全局泄漏；暂停后异常使用测试专用协程，不冒充普通allocator逐点故障。

作者2026-10-11运行环境：macOS arm64；Homebrew Clang23.1.0；libc++头宏230100，运行时`/usr/lib/libc++.1.dylib`（otool current version2200.27.0）；CMake4.4.3。Debug/Release各2/2，显式帧计数最终均0；C++20、无扩展、`-fno-fast-math -ffp-contract=off`。库在独立前缀重新构建和安装，数值实现只消费原真源。本记录不认证AppleClang、其他标准库、模块、动态库/跨编译器ABI、吞吐、全部资源故障或Obsidian显示。参考全文属于原数据文件，没有复制新的统计算法或参考文件。

返回[[计算机知识/80-实践/03-C++/05-测量分析组件/README|完整组件实践]]与[[计算机知识/10-编程语言/02-C++/10-系统课程/16-协程帧拥有暂停与取消|生命周期解释和迁移练习]]。
