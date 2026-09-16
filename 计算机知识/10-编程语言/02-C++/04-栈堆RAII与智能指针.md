---
type: lesson
domain: computer-science
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 90
topics: [C++, RAII, 栈, 堆, 智能指针]
tags: [computer-science/cpp]
---

# 04 · 栈、堆、RAII 与智能指针

## 本课目标

掌握一个比“栈快、堆慢”更可靠的模型：自动存储期对象在离开作用域时析构；动态分配对象需要一个明确所有者；RAII 把文件、锁、内存等资源的获得与对象构造绑定，把释放与析构绑定。它同样适用于异常路径和早返回。

<!-- code-sync: ./raii.cpp -->
```cpp
#include <iostream>
#include <memory>

class FileLikeResource {
public:
    FileLikeResource() { std::cout << "acquire\n"; }
    ~FileLikeResource() { std::cout << "release\n"; }
    FileLikeResource(const FileLikeResource&) = delete;
    FileLikeResource& operator=(const FileLikeResource&) = delete;
};

int main() {
    auto value = std::make_unique<int>(42);
    FileLikeResource resource;
    std::cout << *value << "\n";
}
```

离开 `main` 时，析构顺序与构造相反：先 `resource` 输出 `release`，再销毁 `value`。`unique_ptr` 可移动、不可复制，恰好编码唯一所有权；不要因为“裸指针也能 new/delete”就把资源管理留给人工记忆。

## 选择规则

- 默认：把对象作为值成员或局部值；最少的所有权边界最容易读。
- 需要动态多态或延后创建、且只有一个拥有者：`std::unique_ptr<T>` 与 `std::make_unique`。
- 只有多个互不从属的组件必须共同延长对象寿命时才用 `std::shared_ptr<T>`；观察者用 `std::weak_ptr<T>` 避免环。
- 资源包装类应遵守 rule of zero（优先让成员管理资源）或明确删除/实现复制、移动操作；析构函数不应抛异常。

在 llama.cpp 这类以 C API 暴露句柄的工程里，RAII 常表现为 `unique_ptr<Handle, Deleter>` 或一个不可复制、可移动的 guard。关键不只是“最终调用 free”，还要遵守依赖销毁顺序：context/batch 等借用模型或后端状态的对象必须先释放，backend 最后关闭。把释放顺序编码进成员声明顺序和局部作用域，并对加载失败、早返回与异常路径分别测试。

## 练习与成功标准

为 `FileLikeResource` 加一个带名称的构造函数，再在局部块中创建它。成功标准：输出能证明局部块结束时立即释放资源；能解释为什么 `shared_ptr` 不能作为“所有东西都安全”的默认选择。

**上一站**：[[计算机知识/10-编程语言/02-C++/03-指针引用const与生命周期|生命周期]] · **下一站**：[[计算机知识/10-编程语言/02-C++/05-struct类模板与STL|struct、类、模板与 STL]] · **返回**：[[计算机知识/10-编程语言/02-C++/00-C++-MOC|C++ MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/02-C++-课程地图|C++ · 课程地图]]。进一步的机制推演与反例：[[计算机知识/10-编程语言/02-C++/11-对象模型值类别与异常安全|C++ 深化：对象模型、值类别和异常安全]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
