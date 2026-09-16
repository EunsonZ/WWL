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

# Laplace-Poisson方程与最大值原理

## Laplace 描述无源平衡，Poisson 加入体源

本课程统一采用 $-\Delta u=f$，以便零值边界下正源对应非负响应。某些教材用 $\Delta u=f$，其基本解和 Green 函数符号随之变化；不能从不同约定里各抄一个公式拼接。

对足够光滑函数与边界，Green 第一恒等式为
$$\int_\Omega\nabla u\cdot\nabla v=\int_{\partial\Omega}u\partial_n v-\int_\Omega u\Delta v.$$
它只是对 $u\nabla v$ 用散度定理。相减得到第二恒等式，后面用来导出表示公式与对称性。

## 平均值与最大值原理

调和函数 $\Delta u=0$ 的球面平均不随半径变化：对平均求导并用散度定理，导数正比于球内 $\Delta u$ 的积分，因此为零；半径趋零时平均趋向中心值。于是内部最大值若达到，周围平均不能由更小值组成，迫使函数局部恒定，再由连通性推广。

在有界连通域中，调和函数连续到闭包时，最大和最小值由边界控制。两个同 Dirichlet 数据的解之差调和且边界零，所以唯一。若 $-\Delta u=f\ge0$ 且边界非负，用最小值原理得 $u\ge0$；不能把“正源”误写成内部最大值不超过零。

## 完整算例：圆盘均匀源

单位圆盘上 $-\Delta u=1,u|_{r=1}=0$。径向方程为 $-(u''+u'/r)=1$，乘 $r$ 积分得 $ru'=-r^2/2+C$。中心正则性排除 $C/r$ 导数与对数奇性，得到
$$u(r)=\frac{1-r^2}{4}.$$
它非负、中心最大，边界零。直接用笛卡尔坐标 $\Delta(x^2+y^2)=4$ 也可检查。在 $d$ 维单位球，相应解为 $(1-r^2)/(2d)$，维数决定常数。

## Neumann 问题的两个限制

若 $-\Delta u=f,\partial_nu=g$，积分方程给出必要相容性
$$\int_\Omega f+\int_{\partial\Omega}g=0.$$
满足条件时也不能唯一确定常数，因为 $u+C$ 有同样 Laplacian 和法向导数。对连通的适当有界域，可附加 $\int_\Omega u=0$ 固定常数。若域不连通，每个连通分量都有自己的相容条件与常数自由度。

## 基本解的常数来自单位通量

对算子 $-\Delta$，在三维 $\Phi(x)=1/(4\pi|x|)$，二维 $\Phi(x)=-(1/2\pi)\log|x|$。它们离开原点都调和，但通过小球有
$$-\int_{\partial B_\varepsilon}\partial_n\Phi\,dS=1,$$
因此在分布意义满足 $-\Delta\Phi=\delta_0$。若只计算原点外 Laplacian 为零而宣布没有源，就遗漏了集中在奇点的单位质量。

## 自测与解答

在单位圆盘中，能否存在 $\Delta u=0$ 且外法向导数恒为 1 的光滑解？

> [!question]- 解答
> 不能。散度定理给 $0=\int_\Omega\Delta u=\int_{\partial\Omega}\partial_nu=2\pi$，矛盾。问题在边界数据不相容，不是解法选择错误。若法向导数恒零，则常函数都是解，体现常数不唯一。

## 继续学习

前一节：[[数学/46-数理方程/10-多维波动方程球面平均与传播|多维波动方程球面平均与传播]]。 下一节：[[数学/46-数理方程/12-分离变量在矩形圆盘与球域|分离变量在矩形圆盘与球域]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/45-复变函数/12-调和函数共轭函数与Poisson公式|调和函数共轭函数与Poisson公式]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii：Partial Differential Equations，作者课程教材](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/contents.html)
