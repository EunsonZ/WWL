---
type: lesson
domain: mathematics
course: 线性代数
level: undergraduate
revision: 2
reviewed: 2026-09-05
tags:
  - mathematics/linear
  - mathematics/core
---

# 分块矩阵Schur补与矩阵指数

## 分块不是装饰，而是先消去一组未知量

考虑
$$\begin{pmatrix}A&B\\C&D\end{pmatrix}\binom xy=\binom fg,$$
其中 $A$ 可逆。第一行给出 $x=A^{-1}(f-By)$，代入第二行得到
$$Sy=g-CA^{-1}f,\qquad S=D-CA^{-1}B.$$
$S$ 称 Schur 补。计算时的 $A^{-1}B$ 应通过解线性系统获得，不必显式求逆。它描述消去 $x$ 后留给 $y$ 的有效作用。

分块消元给出行列式关系 $\det M=\det A\det S$，以及在 $S$ 可逆时的逆矩阵
$$M^{-1}=\begin{pmatrix}A^{-1}+A^{-1}BS^{-1}CA^{-1}&-A^{-1}BS^{-1}\\-S^{-1}CA^{-1}&S^{-1}\end{pmatrix}.$$
公式的前提包括块大小相容、$A,S$ 可逆，不能在奇异情况下直接把逆改成伪逆并期待全部恒等式保留。

## 正定性的消元解释

若 $M=\begin{pmatrix}A&B\\B^*&D\end{pmatrix}$ 且 $A$ Hermitian 正定，令 $z=\begin{pmatrix}x\\y\end{pmatrix}$，配方得
$$z^*Mz=(x+A^{-1}By)^*A(x+A^{-1}By)+y^*(D-B^*A^{-1}B)y.$$
因此 $M$ 正定当且仅当 Schur 补正定。这连接了 Cholesky、约束优化、条件协方差和能量最小化。这里 $x,y$ 都是列向量，$z^*$ 是整个分块列向量的共轭转置。

## 矩阵指数不等于逐元素指数

定义 $e^{tA}=\sum_{k=0}^\infty t^kA^k/k!$。任意矩阵范数都可用标量指数支配，所以级数对有界 $t$ 一致收敛，逐项微分得 $(e^{tA})'=Ae^{tA}$，初值为 $I$。从而线性系统解为
$$x(t)=e^{tA}x_0+\int_0^t e^{(t-s)A}f(s)\,ds.$$
后一个积分就是有限维 Duhamel 原理，稍后会在热方程中再次出现。

若 $AB=BA$，可用级数重排证明 $e^{A+B}=e^Ae^B$；一般不交换时不成立。二维旋转生成元 $J=\begin{pmatrix}0&-1\\1&0\end{pmatrix}$ 满足 $J^2=-I$，所以
$$e^{tJ}=I\cos t+J\sin t,$$
这解释了正弦余弦为何自然出现在二阶振动方程中。

## 自测与解答

对 $M=\begin{pmatrix}2&1\\1&3\end{pmatrix}$ 计算 Schur 补，并用它解 $M(x,y)^T=(1,2)^T$。

> [!question]- 解答
> $A=2,B=C=1,D=3$，$S=3-1/2=5/2$。于是 $(5/2)y=2-1/2=3/2$，得 $y=3/5$，再由 $x=(1-y)/2=1/5$。行列式同时为 $2\cdot5/2=5$，提供第二个核验。

## 继续学习

前一节：[[数学/20-线性代数与几何/17-矩阵范数条件数与数值稳定性|矩阵范数条件数与数值稳定性]]。

课程地图：[[数学/20-线性代数与几何/00-线性代数与几何-MOC|线性代数课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/46-数理方程/02-高阶线性常微分方程与方程组|高阶线性常微分方程与方程组]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [MIT 18.06SC：Linear Algebra，课程资料](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- [Sheldon Axler：Linear Algebra Done Right，作者站点](https://linear.axler.net/)
