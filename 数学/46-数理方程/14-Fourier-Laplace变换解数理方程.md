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

# Fourier-Laplace变换解数理方程

## 变换把常系数微分变成乘法

本库采用
$$\widehat f(\xi)=\int_{\mathbb R^d}f(x)e^{-ix\cdot\xi}dx,\qquad f(x)=\frac1{(2\pi)^d}\int\widehat f(\xi)e^{ix\cdot\xi}d\xi.$$
先在 Schwartz 快速衰减光滑函数类中推导，积分、分部积分和逆变换均可控制；再通过稠密性与 Plancherel 扩展到 $L^2$。对应关系为 $\widehat{\partial_j f}=i\xi_j\widehat f$、$\widehat{-\Delta f}=|\xi|^2\widehat f$、$\widehat{f*g}=\widehat f\widehat g$，且 $\|f\|_2^2=(2\pi)^{-d}\|\widehat f\|_2^2$。

不同教材可能把 $2\pi$ 放到指数或均分到两边，必须整套一致。原库的离散 DFT、STFT 使用采样频率和不同归一化，与这里连续角频率不能直接混用。

## 热与波：同一个频率坐标，不同时间 ODE

热方程给 $\partial_t\widehat u=-\kappa|\xi|^2\widehat u$，所以 $\widehat u=e^{-\kappa|\xi|^2t}\widehat g$，逆变换得到热核。波动方程给
$$\widehat u_{tt}+c^2|\xi|^2\widehat u=0,$$
所以 $\widehat u=\cos(c|\xi|t)\widehat g+\sin(c|\xi|t)\widehat h/(c|\xi|)$，零频按连续极限 $t\widehat h(0)$ 理解。第一种压低高频，第二种保留振荡能量，频域中差异一眼可见。

## 算例：有质量项的静态方程

在全实线解 $-u''+a^2u=f$、$a>0$，取衰减响应。变换后 $\widehat u=\widehat f/(\xi^2+a^2)$，逆核为
$$G(x)=\frac{e^{-a|x|}}{2a},\qquad u=G*f.$$
$x\ne0$ 时满足齐次方程；$G'$ 在零点跳跃 $-1$，所以分布 $-G''$ 有一个正单位 $\delta$。这个局部跳跃检查能验证留数逆变换中的常数与符号。

## Laplace 变换适合初始时刻

定义 $U(s)=\int_0^\infty e^{-st}u(t)dt$，在函数指数增长受控、$\operatorname{Re}s$ 足够大时，分部积分给
$$\mathcal L(u')=sU-u(0),\quad\mathcal L(u'')=s^2U-su(0)-u'(0).$$
初值变成代数项，是它区别于纯时间 Fourier 变换的优势。外力分段或阶跃时，因果平移与卷积可方便表示，但仍需保留增长域与分支。

## 半线热方程的阶跃边界

$x>0$、$u_t=\kappa u_{xx}$，初值零，边界 $u(0,t)=1$，无穷远衰减。变换后 $\kappa U_{xx}=sU$，选 $\operatorname{Re}\sqrt{s/\kappa}>0$ 的衰减根，得到 $U=e^{-x\sqrt{s/\kappa}}/s$。逆变换为
$$u(x,t)=\operatorname{erfc}\left(\frac{x}{2\sqrt{\kappa t}}\right),\qquad\operatorname{erfc}(z)=\frac2{\sqrt\pi}\int_z^\infty e^{-r^2}dr\quad(z\ge0).$$
可以直接求导核验，无须盲信变换表。初始点 $(0,0)$ 数据不相容，所以不应要求在那里连续同时取得 0 与 1。

## 自测与解答

求 $u_t+au=f(t),u(0)=u_0$ 的 Laplace 解并逆回时域。

> [!question]- 解答
> $U=(u_0+F)/(s+a)$，所以 $u(t)=u_0e^{-at}+\int_0^te^{-a(t-r)}f(r)dr$。它与积分因子法一致；变换是另一种组织同一线性结构的方法，不是新的物理假设。

## 继续学习

前一节：[[数学/46-数理方程/13-Bessel-Legendre函数与正交展开|Bessel-Legendre函数与正交展开]]。 下一节：[[数学/46-数理方程/15-Green函数基本解与边界响应|Green函数基本解与边界响应]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/45-复变函数/09-留数计算实积分与围道选择|留数计算实积分与围道选择]]。建议比较定义、适用条件与所用范数，再迁移方法。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii：Partial Differential Equations，作者课程教材](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/contents.html)
