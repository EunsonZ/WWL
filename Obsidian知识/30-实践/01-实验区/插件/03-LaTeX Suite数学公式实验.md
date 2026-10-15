---
type: plugin-lab
status: ready
plugin: Latex Suite
tags:
  - playground/plugin
  - playground/math
---

# LaTeX Suite：数学公式实验

Obsidian 使用 MathJax 渲染 LaTeX。即使关闭 Latex Suite，下面的公式仍然是可读的普通文本；插件主要帮助你更快输入 snippets、括号和常见结构。

## 行内公式

质能方程 `$E = mc^2$` 在段落中会显示为：$E = mc^2$。

尝试把下面的占位符改成勾股定理：

`$a^2 + b^2 = \square$`

## 独立公式

$$
\sum_{k=1}^{n} k = \frac{n(n+1)}{2}
$$

## 对齐公式

$$
\begin{aligned}
(x+1)^2 &= x^2 + 2x + 1 \\
(x-1)^2 &= x^2 - 2x + 1
\end{aligned}
$$

## 分段函数与矩阵

$$
f(x)=
\begin{cases}
x^2, & x \ge 0 \\
-x, & x < 0
\end{cases}
$$

$$
A =
\begin{bmatrix}
1 & 2 \\
3 & 4
\end{bmatrix}
$$

## 手动实验

- [ ] 不使用插件，手写一个 `$\frac{a}{b}$`
- [ ] 启用 Latex Suite 后，在设置中查看内置 snippet 的触发词，再输入同一公式
- [ ] 切换到源码模式，确认插件没有把公式变成封闭格式
- [ ] 在 [[Obsidian知识/30-实践/01-实验区/Markdown/03-数学练习场|数学练习场]] 完成自己的公式

> [!warning] 先理解再加速
> snippet 展开得快，不代表公式正确。先学会阅读 LaTeX 源文本，再把重复输入交给插件。

