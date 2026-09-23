---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 100
topics: [C++, 错误处理, 测试, 调试, sanitizer]
tags: [computer-science/cpp]
---

# 07 · 错误、测试、调试与 Sanitizer

## 本课目标

让错误成为可复现证据。C++ 同时有返回值、`std::optional`、`std::expected`（取决于项目标准库支持）、异常、断言和进程终止等机制；选择由 API 的失败语义、调用边界和项目约定决定，而不是统一“禁用”或“滥用”异常。

## 可预期失败要进入类型或返回协议

<!-- code-sync: ./errors.cpp -->
```cpp
#include <charconv>
#include <iostream>
#include <optional>
#include <string_view>

std::optional<int> parse_nonnegative(std::string_view text) {
    int value = 0;
    const char* const begin = text.data();
    const char* const end = begin + text.size();
    const auto [next, error] = std::from_chars(begin, end, value);
    if (error != std::errc{} || next != end || value < 0) {
        return std::nullopt;
    }
    return value;
}

int main() {
    const auto valid = parse_nonnegative("42");
    if (!valid || *valid != 42 || parse_nonnegative("-1") || parse_nonnegative("42x")) {
        std::cerr << "parse contract failed\n";
        return 1;
    }
    std::cout << *valid << '\n';
}
```

`std::from_chars` 不分配、不抛异常，并用返回值报告解析停止位置和错误。这里要求整个输入都被消费且结果非负，所以 `42x` 也失败。测试分支显式返回非零，不依赖可能在 Release 中由 `NDEBUG` 关闭的 `assert`。`optional` 只表达“有值/无值”；若调用者需要区分空输入、格式错和越界，应使用项目约定的错误类型，或在 C++23 工具链可用时评估 `std::expected<T, E>`。

异常适合“当前层无法就地处理、但上层可能恢复”的失败，并依赖 RAII 在栈展开时释放已构造资源；它不应跨 C ABI、线程入口或明确禁用异常的模块边界逸出。析构函数应保持不抛。需要强异常保证时，先在临时对象中完成可能失败的工作，成功后再 `swap`/提交，使失败时原对象状态不变。

## 最小诊断闭环

```bash
cmake -S . -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug --target lifetime
lldb ./build-debug/lifetime
```

在支持 Clang/GCC sanitizer 的环境，单独创建一个诊断构建：

```bash
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer' \
  -DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address,undefined'
cmake --build build-asan
```

这些命令以单配置生成器为例。使用多配置生成器时，两处 `cmake --build` 都要加 `--config Debug`，`lldb` 的目标路径也要按该生成器的实际配置子目录调整。

ASan 主要捕捉越界、use-after-free 等地址错误；UBSan 检查一部分未定义行为。它们不会证明线程协议、算法正确性或所有平台行为。线程问题可另用 ThreadSanitizer，但其平台支持和组合限制要现场确认。

## 写测试前先定义契约

| 情况 | 合理证据 |
| --- | --- |
| 纯函数 | 输入—输出表、边界值、性质测试 |
| 资源封装 | 成功、构造失败、早返回、析构时机 |
| 并发逻辑 | 可控调度、小状态模型、race 检测与压力测试 |
| 性能改动 | 同输入、固定环境、基准分布和正确性回归 |

`assert` 表达开发期不变量，不应用于用户可触发且必须被可靠处理的输入错误（发布构建可能关闭断言）。日志应报告上下文而不打印密钥、模型私有路径或整段敏感输入。

## 练习与成功标准

先构建并运行 `errors`，再进入 [[计算机知识/80-实践/03-C++/01-构建与调试小项目/README|构建与调试小项目]]，为其中可独立测试的纯函数补负数、零、正数三类显式检查。先故意写错一个期望值，运行 `ctest --test-dir build --output-on-failure` 保留失败输出，再改正并重跑。成功标准：测试 target 在失败时返回非零、修复后返回零；你能区分“解析失败”与“程序缺陷”，说明为何 `optional` 没有携带失败原因，并能说明 sanitizer 报告的是哪类内存/未定义行为，而不是笼统地说“没有 bug”。

**上一站**：[[计算机知识/10-编程语言/02-C++/06-move语义与零拷贝|move 语义]] · **下一站**：[[计算机知识/10-编程语言/02-C++/08-线程锁与原子|线程、锁与原子]] · **返回**：[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/11-对象模型值类别与异常安全|C++ 深化：对象模型、值类别和异常安全]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/10-编程语言/02-C++/10-系统课程/05-多态错误处理与API建模|继承、组合、variant 与异常：怎样让非法状态更难表达]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
