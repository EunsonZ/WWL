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

# 变分原理Lax-Milgram与能量估计

## 能量最小化把 PDE 变成几何问题

对零 Dirichlet Poisson 问题，定义
$$J(v)=\frac12\int_\Omega|\nabla v|^2-\langle f,v\rangle,\qquad v\in H_0^1(\Omega).$$
沿 $v+\varepsilon w$ 求一阶变化，得到 $J'(v)w=\int\nabla v\cdot\nabla w-\langle f,w\rangle$，驻点恰为弱解。二次项非负且 Poincaré 控制零模，所以能量严格凸，驻点是唯一全局最小点。

## Lax–Milgram 的条件与意义

在实 Hilbert 空间 $V$ 上，若双线性型 $a$ 有界 $|a(u,v)|\le M\|u\|\|v\|$，且强制（coercive）$a(v,v)\ge\alpha\|v\|^2$、$\alpha>0$，那么对每个连续线性泛函 $F$，存在唯一 $u$ 使 $a(u,v)=F(v)$ 对所有 $v$ 成立，且
$$\|u\|\le\frac{\|F\|_{V^*}}\alpha.$$
它不要求对称。复 Hilbert 空间版本使用 sesquilinear 型与 $\operatorname{Re}a(v,v)$ 的正下界，需与内积约定保持一致。

一个可追踪证明借助 Riesz 表示将 $a$ 写成有界算子 $A$。强制性给出 $\|Av\|\ge\alpha\|v\|$，所以单射、值域闭。若某个 $w$ 与值域正交，则 $a(v,w)=0$ 对所有 $v$，取 $v=w$ 得 $w=0$，所以值域又稠密，因闭而等于全空间。于是可逆与误差界同时得到。

## 对称与非对称不能混同

若 $a$ 对称，$J(v)=a(v,v)/2-F(v)$ 的导数正是 $a(v,w)-F(w)$，可用能量最小化。若不对称，该导数只看到对称部分，因此一般不能把 Lax–Milgram 的解说成同一简单能量的极小点。输运项经常产生非对称形式，但定理仍可能适用。

对 $a(u,v)=\int A(x)\nabla u\cdot\nabla v+cuv$，有界系数、统一椭圆性与 $c\ge0$，加上有界域零值边界的 Poincaré，可给出强制性。Neumann 问题没有 Poincaré 的常数控制，需改用零均值空间并满足相容性。

## Galerkin 近似与 Céa 估计

取有限维子空间 $V_h\subset V$，求 $u_h\in V_h$ 使 $a(u_h,v_h)=F(v_h)$。与精确方程相减得到 Galerkin 正交 $a(u-u_h,v_h)=0$。对任意 $w_h\in V_h$，
$$\alpha\|u-u_h\|^2\le a(u-u_h,u-w_h)\le M\|u-u_h\|\|u-w_h\|,$$
所以
$$\|u-u_h\|\le\frac M\alpha\inf_{w_h\in V_h}\|u-w_h\|.$$
误差不超过子空间最佳逼近的固定倍数；算法能否好，先取决于空间能否表达真解。对称正定时用能量范数可以把常数改为 1。

## 反例与自测

$-u''-u=f$ 于 $(0,\pi)$、零边界，能否对所有 $f$ 使用同样的唯一性结论？

> [!question]- 解答
> 不能。$\sin x$ 是非零齐次解，双线性型在它上取值零，不强制。将方程与 $\sin x$ 积分配对得到必要条件 $\int_0^\pi f\sin x=0$。满足时还可加任意 $C\sin x$，不唯一；不满足时无解。这是共振，不是 Lax–Milgram 定理失效，而是前提未满足。

## 继续学习

前一节：[[数学/46-数理方程/16-分布导数弱解与Sobolev空间|分布导数弱解与Sobolev空间]]。 下一节：[[数学/46-数理方程/18-守恒律Burgers方程激波与熵条件|守恒律Burgers方程激波与熵条件]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/16-数学分析/17-函数空间范数完备性与紧性|函数空间范数完备性与紧性]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii：Partial Differential Equations，作者课程教材](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/contents.html)
- [Christian Clason：Introduction to Finite Element Methods，作者讲义记录](https://arxiv.org/abs/1709.08618)
