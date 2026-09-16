---
type: lesson
domain: mathematics
course: 数理方程
level: undergraduate
revision: 2
reviewed: 2026-09-05
tags:
  - mathematics/pde
  - mathematics/core
---

# Fourier方法与Sturm-Liouville谱

## 分离变量的实质是找空间算子的特征向量

设 $u(x,t)=X(x)T(t)$，代入热方程得到 $T'/(\kappa T)=X''/X=-\lambda$。两边依赖不同变量，故在非零区域只能为常数；随后通过线性延拓处理零点。边界条件决定允许哪些 $X$，而时间方程决定每个模式怎样演化。不是任意选择一套正弦余弦都适合所有边界。

## 正则 Sturm–Liouville 问题

在有限区间 $[a,b]$ 上考虑
$$-(pX')'+qX=\lambda wX,$$
其中 $p\in C^1$ 且正，$q,w$ 实连续、$w>0$，配以实的分离齐次边界条件，使边界型 $[p(X'\overline Y-X\overline{Y'})]_a^b$ 为零。相应内积为 $\langle X,Y\rangle_w=\int_a^b wX\overline Y$。

将两个特征方程相乘、相减再积分得
$$(\lambda-\overline\mu)\int_a^b wX\overline Y=0,$$
先取 $Y=X$、$\mu=\lambda$，由于 $\int_a^b w|X|^2>0$，得 $\lambda=\overline\lambda$，即特征值实数。再对不同实特征值使用同一等式，得到加权正交。这些结论依赖**实系数、自伴边界和正权重**；对非自伴问题不能直接照搬。

## 能量商与谱性质

在 Dirichlet 条件下，分部积分得到
$$\lambda=\frac{\int_a^b(p|X'|^2+q|X|^2)dx}{\int_a^b w|X|^2dx}.$$
若 $q\ge0$，特征值正。一般 Robin 条件会贡献边界项，不能遗漏后还宣称同样非负。正则自伴问题的特征值离散趋于正无穷，特征函数在加权 $L^2$ 中完备；证明可经适当平移后的 Green 算子紧自伴谱定理实现。正交性上面已直接证明，完备性则是更深的存在理论，不是正交自动推出。

## 三种边界，三种频率

对 $-X''=\lambda X$ 于 $(0,L)$：双端 Dirichlet 给 $\lambda_n=(n\pi/L)^2$、$X_n=\sin(n\pi x/L)$，$n\ge1$；双端 Neumann 给常数零模式和余弦正模式，$n\ge1$；左 Dirichlet、右 Neumann 给 $((n+1/2)\pi/L)^2$，$n\ge0$。逐一检查 $\lambda<0$、$\lambda=0$、$\lambda>0$ 的 ODE 和边界，才能证明没有漏解。

![Sturm–Liouville 的前三个模式](../assets/figures/sturm-modes.svg)

*图：区间 $(0,1)$ 双端零值边界的前三个正弦特征函数；频率越高，空间曲率与特征值越大。*

## 非齐次项如何投影

若特征函数归一，写 $u=\sum a_n(t)X_n$、$f=\sum f_n(t)X_n$，则热方程给 $a_n'+\kappa\lambda_na_n=f_n$，波动方程给 $a_n''+c^2\lambda_na_n=f_n$。前者衰减，后者振荡，空间模态完全相同。数学分析的 Fourier 级数在这里成为求解器，正交投影的权重必须与算子一致。

## 自测与解答

在 $(0,\pi)$ 上展开常数 $g(x)=1$ 为正弦级数，并解释端点发生什么。

> [!question]- 解答
> $b_n=(2/\pi)\int_0^\pi\sin nx\,dx=2(1-(-1)^n)/(\pi n)$，仅奇数项非零。在内部级数为 1，端点每项都为零，所以级数端点值为零。这对应奇延拓的跳跃中点，说明 $L^2$ 展开不强制原函数与基函数在边界点一致。

## 继续学习

前一节：[[数学/46-数理方程/05-一阶偏微分方程与特征线|一阶偏微分方程与特征线]]。 下一节：[[数学/46-数理方程/07-热方程分离变量与扩散机制|热方程分离变量与扩散机制]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/16-数学分析/13-Fourier级数正交展开与收敛|Fourier级数正交展开与收敛]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii：Partial Differential Equations，作者课程教材](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/contents.html)
