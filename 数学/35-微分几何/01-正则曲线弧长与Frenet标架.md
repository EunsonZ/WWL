---
type: lesson
stage: 1
aliases:
  - Frenet-Serret方程推导
sources:
  - https://www.maths.gla.ac.uk/~mpowell/M435-intro-chapter-1-geometry-of-curves.pdf
prerequisites:
  - "[[数学/15-微积分/10-参数曲线极坐标与空间曲线]]"
  - "[[数学/20-线性代数与几何/03-点积范数距离与余弦相似度]]"
---
# 正则曲线、弧长与Frenet标架

要比较两条空间轨迹的形状，先去掉走路速度带来的影响。已有 [[数学/15-微积分/10-参数曲线极坐标与空间曲线#参数是描述运动的方式，不是曲线本身|弧长主解释]] 说明：$r:I\to\mathbb R^3$ 正则表示 $r'(t)\ne0$，而 $ds/dt=v=\|r'\|>0$。本页假设 $r\in C^3$，固定增加的弧长方向；$d/ds=v^{-1}d/dt$。因此单位切向量 $T=r'/v$ 才是与速度无关的方向。

## 三个单位向量怎样一起转动

由 $T\cdot T=1$ 求导得到 $T_s\perp T$。在整个讨论区间上假设 $\kappa=\|T_s\|>0$，定义 $N=T_s/\kappa$ 和 $B=T\times N$。三个向量构成右手正交标架，分别指向前进、转弯和密切平面的法向。于是第一条式子已是定义：$T_s=\kappa N$。

对 $B\cdot B=1$、$B\cdot T=0$ 求导，得到 $B_s\perp B$，以及 $B_s\cdot T=-B\cdot T_s=0$。因此 $B_s$ 只能沿 $N$，本组**定义** $\tau=-B_s\cdot N$，故 $B_s=-\tau N$。再对 $N\cdot N=1,N\cdot T=0,N\cdot B=0$ 求导，分别得到 $N_s$ 没有 $N$ 分量、$T$ 分量为 $-\kappa$、$B$ 分量为 $\tau$。这就推出

$$
T_s=\kappa N,\qquad N_s=-\kappa T+\tau B,\qquad B_s=-\tau N.
$$

这些公式表达同一个正交标架的转动，并非三个互不相关的定义。写 $Q=[T\ N\ B]\in\mathbb R^{3\times3}$，则

$$
Q_s=Q\begin{pmatrix}0&-\kappa&0\\\kappa&0&-\tau\\0&\tau&0\end{pmatrix}.
$$

右侧矩阵反对称，代入 $(Q^TQ)_s$ 得0，解释了为何演化保持正交。数值算法未必精确保持这个性质。$\kappa,\tau$ 的单位都是长度的倒数，$T,N,B$ 无量纲。

## 从任意参数回到可计算公式

先求 $r''=v'T+v^2\kappa N$，从而 $r'\times r''=v^3\kappa B$，得到旧页中的曲率公式。继续求导，$r'''$ 的 $B$ 分量只有 $v^2\kappa N_t=v^3\kappa\tau B$，故

$$
\kappa=\frac{\|r'\times r''\|}{\|r'\|^3},\qquad
\tau=\frac{(r'\times r'')\cdot r'''}{\|r'\times r''\|^2}.
$$

分母非零需要 $v>0,\kappa>0$。不能在直线点先算出 $0/0$ 再称其挠率为0。

共用圆柱上的螺旋 $r(t)=(2\cos t,2\sin t,t)$ 有

$$
r'=(-2\sin t,2\cos t,1),\quad r''=(-2\cos t,-2\sin t,0),\quad
r'''=(2\sin t,-2\cos t,0).
$$

速率 $\sqrt5$，叉积 $(2\sin t,-2\cos t,4)$ 的模为 $2\sqrt5$；与 $r'''$ 点积为4，叉积模平方为20。因此 $s=\sqrt5t,\kappa=2/5,\tau=1/5$。实际标架为

$$
T=\frac{(-2\sin t,2\cos t,1)}{\sqrt5},\quad
N=(-\cos t,-\sin t,0),\quad
B=\frac{(\sin t,-\cos t,2)}{\sqrt5}.
$$

逐项求导并除以 $\sqrt5$ 可核对全部三式。这条螺旋同时也是 [[数学/35-微分几何/03-坐标变换联络与测地线#圆柱：展开后就能直接求解|圆柱测地线]]；空间曲率非零并不妨碍曲面上的切向加速度为零。

## 零挠率与零曲率要分别判断

若连通区间内始终 $\kappa>0$ 且 $\tau\equiv0$，则 $B_s=0$，$B$ 为常向量；$(r\cdot B)_s=T\cdot B=0$，所以整段曲线在固定平面内。反之平面曲线在 $\kappa>0$ 的区间内，其 $B$ 只能为固定平面法向的连续选择，故 $\tau=0$。单点 $\tau=0$ 不推出整段平面性。

若 $\kappa\equiv0$，$T_s=0$，单位速曲线是直线；这不依赖Frenet的 $N,B$ 存在。反例 $r(t)=(t,t^3,0)$ 始终正则，但 $t=0$ 时 $r'\times r''=0$；此处有清晰切线，Frenet主法向却不能照定义取值。另一个反例 $r(t)=(t^3,0,0)$ 在0参数不正则，几何点集仍是直线。

## 可复算练习

1. 把共用螺旋改为 $(2\cos t,2\sin t,0)$。求弧长和标架，说明能否使用挠率公式。
2. 证明标架演化的反对称矩阵保持 $Q^TQ=I$；若只知道 $\tau(s_0)=0$，上述平面性证明在哪一步失效？

> [!question]- 答案与检验
> 1. $s=2t,T=(-\sin t,\cos t,0),N=(-\cos t,-\sin t,0),B=(0,0,1)$；$\kappa=1/2,\tau=0$，曲率始终非零，挠率分母为16，因此合法。长度在 $0\le t\le\pi/2$ 上为 $\pi$。
> 2. 若 $Q_s=QA,A^T=-A$，则 $G=Q^TQ$ 满足 $G_s=A^TG+GA$；$G=I$ 满足该方程，线性ODE唯一性保持初值 $I$。只在一点挠率为零只能得到该点 $B_s=0$，不能积分成整个区间 $B$ 常值。几何结论需要区间条件。

来源核对：[Powell Part I](https://www.maths.gla.ac.uk/~mpowell/M435-intro-chapter-1-geometry-of-curves.pdf)，§2.1 pp.3–4 正则与弧长，§2.6–2.7 pp.10–12 标架。**该讲义定义挠率为 $B_s\cdot N$，与本组相反**；本组保持旧库三重积公式的符号，以上推导用于明确换号，不能直接拼接讲义的挠率方程。实验入口见 [[数学/35-微分几何/80-几何计算与测地线复算|解析公式与数值检验]]。
