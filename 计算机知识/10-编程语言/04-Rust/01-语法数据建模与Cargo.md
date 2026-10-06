---
type: lesson
domain: computer-science
status: expanded
revision_date: 2026-09-06
tags: [computer-science, revision-2]
---

# Rust：从表达式与枚举建立可靠的数据模型

> 阅读定位：基础示例兼容 Rust 2021 edition；不把 edition 等同于编译器版本。返回 [[计算机知识/00-开始/课程地图/03-Rust-课程地图|Rust · 课程地图]]；全域入口 [[计算机知识/00-开始/全局导航/00-总学习地图|计算机知识库 · 总学习地图]]。

## 先学如何表达状态

Rust 的 `let` 默认不可变，要重新赋值写 `mut`；遮蔽创建新绑定，不等于修改旧对象。代码块和 `if` 可以产生值，末尾分号常把最后的表达式变为语句。函数参数类型写在接口上，让实现细节和调用约定分离。

结构体描述同时存在的字段，枚举描述互斥的状态。一个加载结果不应同时拥有 `loading=true`、有效数据和错误字符串而让调用者猜优先级；可用 `enum Load<T> { Pending, Ready(T), Failed(String) }`。模式匹配让每种状态的处理显式化。

```rust
#[derive(Debug, PartialEq)]
enum Level { Low, Normal, High }

fn classify(n: i32) -> Level {
    match n {
        i32::MIN..=9 => Level::Low,
        10..=20 => Level::Normal,
        _ => Level::High,
    }
}

fn main() {
    assert_eq!(classify(15), Level::Normal);
}
```

这个例子的边界是 9/10、20/21，不是随便选几组中间值。`match` 的穷尽检查保障状态覆盖，不保障每个分支的业务含义正确。`if let` 适合只关心一种形态；`let ... else` 可把不满足条件的路径尽早退出。

## 数字、文本和集合

固定宽度整数、`usize`、浮点、布尔、字符、元组和数组分别表达不同约束。不要依赖溢出在调试与发布构建中的偶然表现，业务需要时显式用 `checked_*`、`wrapping_*` 或 `saturating_*`。数组长度是类型的一部分；`Vec<T>` 动态增长；切片表达一段连续元素的借用。

`String` 拥有 UTF-8 数据，`&str` 借用 UTF-8 字符串切片，不能按任意字节下标取得“第几个字符”。`chars()` 遍历 Unicode 标量值，不等于用户感知字素簇。`Option<T>` 区分存在与不存在，`Result<T,E>` 区分成功与失败，不应用一个神秘数字同时承担合法值和错误。

## Cargo 与模块

package 由 `Cargo.toml` 描述，可以包含库和二进制 crate；crate 是编译单元，module 用于组织名字和可见性。`use` 简化路径，`pub` 决定可见性。依赖版本范围、锁文件、feature 和 target 是不同维度。edition 主要控制语言兼容规则，不等于编译器发行版本；教程用 2021 edition 的基础语法避免不必要的工具链要求。

基础闭环是 `cargo check` 检查、`cargo test` 测试、`cargo fmt` 格式化、适当运行 `cargo clippy`。工具成功不能证明接口设计正确。练习把 `classify` 放进库，在二进制中调用，为边界写测试，并说明哪些名字是公共 API。

## 把知识接起来

[[计算机知识/10-编程语言/04-Rust/02-所有权借用与生命周期推演|Rust：所有权、借用和生命周期的逐步推演]]；[[计算机知识/10-编程语言/05-TypeScript/02-联合类型收窄与运行时验证|TypeScript：联合类型、收窄与输入边界]]；[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。

## 规范与进一步核对

参见 [[计算机知识/90-资源/10-本轮权威资料与版本边界#Rust|Rust原始资料]]。正文中的例题是本库的教学构造；一般模型不自动等于某一实现。

<!-- ROUND3 BRIDGE -->
## 进一步推演与交叉核验

本页主题的补充机制、反例和练习：

- [[计算机知识/10-编程语言/04-Rust/10-系统课程/08-集合宏工程与生态全景|Rust 的课程闭环：集合、宏、no_std 与可维护项目]]

阅读时对照两页的版本、模型与接口前提；教学简化模型不覆盖具体实现的全部行为。
<!-- END ROUND3 BRIDGE -->
