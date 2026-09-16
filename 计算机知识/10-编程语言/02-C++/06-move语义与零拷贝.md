---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 85
topics: [C++, move, 值类别, 性能, 零拷贝]
tags: [computer-science/cpp]
---

# 06 · move 语义与零拷贝

## 本课目标

把性能讨论变成可验证的问题：数据何时复制、谁拥有缓冲区、对象能否安全转移、传递后旧对象还能作什么。`std::move` 不移动字节；它允许目标构造函数或赋值运算符把源当成可被转移的右值。

<!-- code-sync: ./move.cpp -->
```cpp
#include <iostream>
#include <string>
#include <utility>

class Packet {
public:
    explicit Packet(std::string bytes) : bytes_(std::move(bytes)) {}
    std::size_t size() const { return bytes_.size(); }

private:
    std::string bytes_;
};

int main() {
    std::string payload(1'000, 'x');
    Packet packet(std::move(payload));
    std::cout << packet.size() << "\n";
}
```

`payload` 在移动后仍是有效对象，但内容处于未指定状态；只能对它执行有定义的操作（析构、重新赋值、查询满足其前置条件的操作），不要假定它为空或仍有 1,000 个字符。传值再移动常是清楚的所有权入口：调用者可复制传入左值，或显式移动右值。

返回局部对象的值通常让编译器进行返回值消除（copy elision），无需手写 `std::move(local)`；后者反而可能妨碍消除。容器在重新分配时通常更愿意搬迁 `noexcept` 的移动构造，因为若移动中途抛出，旧容器状态难以保持；资源包装类应让移动操作真实、廉价且在可保证时标为 `noexcept`。不要为了“看起来高性能”给可能抛出的操作错误标注 `noexcept`，否则异常会触发终止。

## “零拷贝”检查表

1. 标出每个缓冲区的拥有者和生命周期。
2. 查明传递的是值、`span`/`string_view`、指针还是智能指针。
3. 用 profiler、分配器统计或基准测试确认复制/分配，而不是只凭 `std::move` 判断。
4. 对借用 view 写出失效点；性能优化不能引入悬垂访问。
5. 分别记录 host 内部传递、文件映射、页驻留与 host-device 传输；每层的“零拷贝”不是同一个承诺。

在 `llama.cpp` 中，模型文件映射、张量 view、后端缓冲区和设备复制各自有不同边界；不要把“CPU 少一次复制”推论成“GPU 没有传输”。

## 练习与成功标准

先把 `Packet packet(std::move(payload))` 改成 `Packet packet(payload)`，再改回；另写一个返回局部 `Packet` 的工厂函数，不对返回表达式手写 `std::move`。成功标准：两种构造写法都可运行，但能解释前者给出转移许可、后者要求保留 `payload` 内容；能说明 copy elision 与移动的区别；不会在移动后打印 `payload` 来断言实现细节。

**上一站**：[[计算机知识/10-编程语言/02-C++/05-struct类模板与STL|模板与 STL]] · **下一站**：[[计算机知识/10-编程语言/02-C++/07-错误测试调试与Sanitizer|错误、测试、调试与 Sanitizer]] · **返回**：[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/11-对象模型值类别与异常安全|C++ 深化：对象模型、值类别和异常安全]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
