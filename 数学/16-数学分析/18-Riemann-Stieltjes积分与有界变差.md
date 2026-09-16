---
type: lesson
domain: mathematics
course: 数学分析
level: undergraduate
revision: 2
reviewed: 2026-09-05
tags:
  - mathematics/analysis
  - mathematics/core
---

# Riemann-Stieltjes积分与有界变差

## 当累积量不再按长度增长

通常 $\int f(x)\,dx$ 按长度分配权重。Riemann–Stieltjes 积分 $\int f\,d\alpha$ 按累积函数 $\alpha$ 的增量加权，适合质量集中、概率分布和变差估计。分割和为
$$\sum_i f(\xi_i)\bigl(\alpha(x_i)-\alpha(x_{i-1})\bigr).$$
若 $\alpha$ 单调，且 $f$ 连续，则积分存在；更一般，连续 $f$ 对有界变差 $\alpha$ 也可积。两者都有跳跃时必须检查定义和端点约定，不能直接套用上述充分条件。

## 有界变差为什么是自然条件

定义
$$V_a^b(\alpha)=\sup_P\sum_i|\alpha(x_i)-\alpha(x_{i-1})|.$$
若它有限，所有带权和的绝对值由 $\|f\|_\infty V_a^b(\alpha)$ 控制。对连续 $f$，一致连续性使同一小区间里换标签带来的总误差最多为 $\omega_f(\|P\|)V_a^b(\alpha)$，趋于零。这说明可积性不是偶然。

有界变差函数可写成两个单调递增函数之差：令 $v(x)=V_a^x(\alpha)$，则 $(v+\alpha)/2$ 与 $(v-\alpha)/2$ 都单调。它有左右极限且几乎处处可微，但反过来“几乎处处导数存在”不保证有界变差。

## 跳跃、密度与奇异部分

若 $\alpha\in C^1$，积分退化为 $\int f\alpha'\,dx$。若 $\alpha$ 在内部点 $c$ 有单位跳跃、其他处常数，连续 $f$ 的积分为 $f(c)$。采用右连续分布函数和其 Lebesgue–Stieltjes 测度时，区间质量满足 $\mu((s,t])=\alpha(t)-\alpha(s)$，端点原子因此有明确归属。

概率的期望 $\mathbb E[g(X)]=\int g\,dF_X$ 可统一离散与连续情况。并不是每个无原子的分布都有密度：Cantor 分布函数连续、几乎处处导数为零，却从 $0$ 增到 $1$。所以 $\int\alpha'$ 未必恢复 $\alpha$ 的总增量。

## 绝对连续修复了什么

$\alpha$ 绝对连续的含义是：对任意 $\varepsilon>0$，存在 $\delta>0$，使任意有限组两两不交区间总长度小于 $\delta$ 时，总增量绝对值之和小于 $\varepsilon$。这比一致连续强，排除了变化集中在零测集上的现象。

在闭有限区间，绝对连续等价于存在 $g\in L^1$，使 $\alpha(x)=\alpha(a)+\int_a^x g$；且 $\alpha'=g$ 几乎处处。这是 Lebesgue 版微积分基本定理。证明依赖积分的绝对连续性与 Lebesgue 微分定理，作为本页的进阶依赖明确列出，而非声称由普通中值定理直接推出。

## 分部积分与算例

若 $f,g$ 连续且有界变差，
$$\int_a^b f\,dg+\int_a^b g\,df=f(b)g(b)-f(a)g(a).$$
它来自有限和的望远镜相消；连续性使交叉小增量的总误差趋零。有共同跳跃时需要额外跳跃项或改变左右值约定。

取 $\alpha(x)=x^2+1_{[1/2,1]}(x)$，$f(x)=x$，在 $[0,1]$ 上
$$\int_0^1 x\,d\alpha=\int_0^1 2x^2\,dx+\frac12=\frac76.$$
连续部分权重是 $2x$，跳跃贡献是跳跃高度乘以 $f(1/2)$，不能遗漏点质量。

## 自测与解答

证明 Lipschitz 函数绝对连续，并说明反向为什么不成立。

> [!question]- 解答
> 若 Lipschitz 常数为 $L$，不交区间总增量至多 $L$ 乘以总长度，取 $\delta=\varepsilon/L$（$L=0$ 单独显然）即可。
> $\sqrt x$ 在 $[0,1]$ 绝对连续，因为其导数 $1/(2\sqrt x)$ 可积并积分回原函数；但 $|\sqrt x-0|/x=1/\sqrt x$ 无界，所以不是 Lipschitz。这也连接了奇点可积性与正则性。

## 继续学习

前一节：[[数学/16-数学分析/17-函数空间范数完备性与紧性|函数空间范数完备性与紧性]]。

课程地图：[[数学/16-数学分析/00-数学分析-MOC|数学分析课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/46-数理方程/16-分布导数弱解与Sobolev空间|分布导数弱解与Sobolev空间]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Jiří Lebl：Basic Analysis I & II，作者开放教材](https://www.jirka.org/ra/html/ra.html)
- [Sheldon Axler：Measure, Integration & Real Analysis，作者开放教材](https://measure.axler.net/)
