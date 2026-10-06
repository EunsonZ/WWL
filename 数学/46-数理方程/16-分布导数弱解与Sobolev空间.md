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

# 分布导数弱解与Sobolev空间

## 允许不可微解，不等于放弃方程

点热源、集中力和激波会产生不光滑对象。分布将函数对测试函数的作用作为基本信息：局部可积 $u$ 定义 $T_u(\varphi)=\int u\varphi$，测试函数取 $C_c^\infty(\Omega)$。一般分布是其上的连续线性泛函；连续性涉及所有阶导数在固定紧支集上的控制，不只是任意线性规则。

分布导数定义为 $\langle\partial_jT,\varphi\rangle=-\langle T,\partial_j\varphi\rangle$，这是将经典分部积分延伸为定义。Dirac 质量 $\delta_a(\varphi)=\varphi(a)$ 不是普通函数，却可以求导，$\delta_a'(\varphi)=-\varphi'(a)$。

## 两个完整的非光滑例子

Heaviside 阶跃 $H=1_{(0,\infty)}$ 满足
$$\langle H',\varphi\rangle=-\int_0^\infty\varphi'(x)dx=\varphi(0),$$
所以 $H'=\delta_0$。$|x|$ 的一阶弱导数为 $\operatorname{sgn}x$，再求导得 $|x|''=2\delta_0$。经典意义中“零点外二阶导数为零”没有捕捉到尖角；分布恰好记录它。

分布可以乘光滑函数，但一般不能任意相乘，例如 $\delta^2$ 没有标准分布定义。非线性 PDE 的弱形式须选择能让非线性项有意义的函数空间，不能只把所有量换成分布就结束。

## Sobolev 空间指定可容忍的粗糙程度

$W^{k,p}(\Omega)$ 是函数及所有不超过 $k$ 阶弱导数均在 $L^p$ 的空间；$H^k=W^{k,2}$。例如
$$\|u\|_{H^1}^2=\int_\Omega(|u|^2+|\nabla u|^2).$$
在有限区间，$|x|\in H^1$，阶跃函数不在 $H^1$，因为其导数含无法表示为 $L^2$ 函数的 Dirac 质量。函数的“跳跃”与“尖角”因此有不同能量代价。

$H_0^1(\Omega)$ 定义为 $C_c^\infty(\Omega)$ 在 $H^1$ 中的闭包。对有界 Lipschitz 域，它可理解为迹为零，而不是在每个边界点强行取零值。一般 $H^1$ 元素是几乎处处等价类，未必有处处定义的连续代表。迹定理提供了边界值的正确弱意义。

## 弱形式把一次导数留给解，一次交给测试函数

对 $-\Delta u=f$、零 Dirichlet 边界，求 $u\in H_0^1$，使
$$\int_\Omega\nabla u\cdot\nabla v=\langle f,v\rangle\quad\forall v\in H_0^1.$$
这里 $f$ 可属于对偶空间 $H^{-1}$，不必是普通函数。经典光滑解必满足此式；反向需要额外正则性才恢复经典二阶方程。仅用内部紧支测试函数定义分布解，并不会自动施加边界条件，边界必须通过空间或迹另行指定。

在一维，$H_0^1(0,L)$ 中 $u(x)=\int_0^xu'$，Cauchy–Schwarz 得 $|u(x)|\le\sqrt L\|u'\|_2$，进一步有 $\|u\|_2\le L\|u'\|_2$。这给出一条非最优但足够的 Poincaré 不等式，使梯度范数控制整个函数。

## 自测与解答

在 $(0,1)$ 上，$u=G(\cdot,1/2)$ 是否属于 $H_0^1$？验证它满足 $\int u'v'=v(1/2)$。

> [!question]- 解答
> 它连续、端点零，分段导数为 $1/2,-1/2$，平方可积，故属于 $H_0^1$。分段积分得
> $$\int_0^1u'v'=\tfrac12(v(1/2)-v(0))-\tfrac12(v(1)-v(1/2))=v(1/2).$$
> 一维 $H_0^1$ 的点值由上面的估计连续控制，因此这个点源属于 $H^{-1}$。高维点值连续性不同，不能无条件沿用这一结论。

## 继续学习

前一节：[[数学/46-数理方程/15-Green函数基本解与边界响应|Green函数基本解与边界响应]]。 下一节：[[数学/46-数理方程/17-变分原理Lax-Milgram与能量估计|变分原理Lax-Milgram与能量估计]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/16-数学分析/14-测度可测函数与Lebesgue积分|测度可测函数与Lebesgue积分]]：弱导数所在的 $L^p$ 与 Sobolev 空间以可测函数的几乎处处等价类为对象；因此 $L^2$ 范数为零不提供点值信息，而边界条件须由迹或 $H_0^1$ 闭包另行编码。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii：Partial Differential Equations，作者课程教材](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/contents.html)
- [Christian Clason：Introduction to Finite Element Methods，作者讲义记录](https://arxiv.org/abs/1709.08618)
