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
先在 Schwartz 空间 $\mathcal S(\mathbb R^d)$ 中推导：它包含任意阶导数都比任意多项式倒数衰减更快的光滑函数。在第 $j$ 个变量分部积分，边界项消失，得到

$$\widehat{\partial_jf}=i\xi_j\widehat f,\qquad
\widehat{-\Delta f}=|\xi|^2\widehat f.$$

对 $f,g\in\mathcal S$，绝对可积允许交换二重积分，令 $x=y+z$ 将指数拆为两项，得 $\widehat{f*g}=\widehat f\widehat g$。这一步的交换积分与边界项是条件，不能删掉后把同样结论用于所有对象。

### 从光滑函数到有限能量：各层允许什么

| 对象 | Fourier 的意义 | 导数、Laplacian 与卷积的条件 |
|---|---|---|
| $\mathcal S$ | 普通绝对收敛积分、逆积分 | 导数恒等式和卷积恒等式在此直接成立 |
| $L^2$ | 由 $\mathcal S$ 稠密逼近定义的 $L^2$ 极限；未必有绝对收敛逐点积分 | Plancherel 与 $L^2$ 逆成立，但不自动拥有 $L^2$ 弱导数；也不自动允许任意 $L^2*L^2$ 使用 $L^2$ 卷积公式 |
| $H^1$ | $L^2$ 变换 | 每个弱导数在 $L^2$，$i\xi_j\widehat f\in L^2$，一阶导数公式在 $L^2$ 意义成立 |
| $H^2$ | $L^2$ 变换 | 所有二阶弱导数在 $L^2$，$\lvert\xi\rvert^2\widehat f\in L^2$，Laplacian 公式在 $L^2$ 意义成立 |
| 温和分布 $\mathcal S'$ | 对 Schwartz 测试函数的连续线性作用，经对偶定义变换 | 任意阶分布导数公式成立；不附带有限能量或逐点积分。任意两分布的乘积、卷积不能自动定义 |

当前归一化下 $\|f\|_2^2=(2\pi)^{-d}\|\widehat f\|_2^2$。$H^1,H^2$ 的频域条件可分别写成 $(1+|\xi|^2)^{1/2}\widehat f\in L^2$ 与 $(1+|\xi|^2)\widehat f\in L^2$；这是与通常弱导数范数等价的空间刻画，不能据此认定两种范数数值完全相等。[Melrose 18.155 Lecture 4，PDF 第 1 页 Sobolev 的频域定义与正整数阶说明](https://math.mit.edu/~rbm/18.155-F16/L4.pdf)。[Ivrii §5.2，Basic properties Theorem 2 与 Theorem 3；§5.1.A 的快速衰减推导](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/Chapter5/S5.2.html)。

温和分布的约定为 $\langle\widehat T,\varphi\rangle=\langle T,\widehat\varphi\rangle$，此处不作复共轭。于是导数的乘法恒等式在 $\mathcal S'$ 中保留。一般分布 $\mathcal D'$ 未必温和，不能都用 Fourier 变换。例如增长过快的普通函数未必对 Schwartz 函数可积。[Ivrii §11.2，Fourier transform Definition 4 与 Exercise 3；该书正变换常数不同，须转换到本页约定](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/Chapter11/S11.2.html)。

卷积另有明确的足够条件：$f,g\in L^1$ 时卷积在 $L^1$，恒等式由 Fubini 成立；$f\in L^1,g\in L^2$ 时 Young 不等式给 $f*g\in L^2$，恒等式在 $L^2$ 成立，因为 $\widehat f$ 有界。温和分布与 Schwartz 函数可卷积；一个温和分布有紧支集时也可与另一个温和分布卷积，频域乘法由相应光滑因子定义。这里不宣称任意两 $\mathcal S'$ 的卷积或乘积有意义。

### 反例：几乎处处经典导数为零，分布导数却不为零

令 $f=1_{[0,1]}\in L^1\cap L^2$。它在端点外经典导数为零；若据此变换“$f'=0$”，会漏掉跳跃。对紧支光滑 $\varphi$，

$$\langle f',\varphi\rangle=-\int_0^1\varphi'(x)dx=\varphi(0)-\varphi(1),
\qquad f'=\delta_0-\delta_1.$$

另一方面手算 $\widehat f(\xi)=(1-e^{-i\xi})/(i\xi)$，$\xi=0$ 按极限取 1，所以 $i\xi\widehat f=1-e^{-i\xi}$，恰是 $\delta_0-\delta_1$ 的变换。它不属于 $L^2(\mathbb R)$：$|1-e^{-i\xi}|^2$ 为非零周期函数，积分无限。因此 $f\notin H^1$，但分布导数恒等式仍成立。带着这个端点计算去 [[数学/46-数理方程/16-分布导数弱解与Sobolev空间#Sobolev 空间指定可容忍的粗糙程度|Sobolev 主解释]]，比较阶跃与尖角为什么有不同的一阶能量代价。

离散对应问题去 [[数学/70-信号处理与多模态数学/03-STFT窗覆盖与可逆重建|STFT 窗覆盖与可逆重建]]：有限复数 DFT 可逆恢复加窗帧，原记录恢复还要检查实际窗平方分母。音频与 PDE 两个入口共用这篇离散主解释。

不同教材可能把 $2\pi$ 放到指数或均分到两边，必须整套一致。原库的离散 DFT、STFT 使用采样频率和不同归一化，与这里连续角频率不能直接混用。

## 热与波：同一个频率坐标，不同时间 ODE

热方程给 $\partial_t\widehat u=-\kappa|\xi|^2\widehat u$，所以 $\widehat u=e^{-\kappa|\xi|^2t}\widehat g$，逆变换得到热核。波动方程给
$$\widehat u_{tt}+c^2|\xi|^2\widehat u=0,$$
所以 $\widehat u=\cos(c|\xi|t)\widehat g+\sin(c|\xi|t)\widehat h/(c|\xi|)$，乘子 $\sin(c|\xi|t)/(c|\xi|)$ 在零频按连续极限 $t$ 定义；$L^2$ 数据的 $\widehat h(0)$ 未必有点值，零测集上的赋值不影响 $L^2$ 解。第一种压低高频，第二种保留振荡能量，频域中差异一眼可见。上述热乘子对 $g\in L^2$ 定义 $L^2$ 解；波动乘子对 $g,h\in L^2$ 定义固定时刻的 $L^2$ 解，要谈标准有限能量则取 $g\in H^1,h\in L^2$。经典逐点 PDE 还需额外正则性。

## 算例：有质量项的静态方程

在全实线解 $-u''+a^2u=f$、$a>0$，取衰减响应。变换后 $\widehat u=\widehat f/(\xi^2+a^2)$，逆核为
$$G(x)=\frac{e^{-a|x|}}{2a},\qquad u=G*f.$$
$x\ne0$ 时满足齐次方程；$G'$ 在零点跳跃 $-1$，所以分布 $-G''$ 有一个正单位 $\delta$。这个局部跳跃检查能验证留数逆变换中的常数与符号。

## Laplace 变换适合初始时刻

定义普通右侧单边变换 $U(s)=\int_0^\infty e^{-st}u(t)dt$。一组便于核验的充分条件是：$u\in AC_{\mathrm{loc}}([0,\infty))$（每个有限区间绝对连续），右端迹 $u(0^+)$ 已定；对于所选复数 $s$，$e^{-st}u,e^{-st}u'$ 均绝对可积，且 $e^{-sR}u(R)\to0$。局部绝对连续使有限区间内 $u(R)-u(0^+)=\int_0^R u'$ 成立，分部积分给

$$\int_0^R e^{-st}u'(t)dt=e^{-sR}u(R)-u(0^+)+s\int_0^R e^{-st}u(t)dt.$$

此时才可令 $R\to\infty$，得到 $\mathcal L(u')=sU-u(0^+)$。二阶式还需 $u'\in AC_{\mathrm{loc}}$、$e^{-st}u''$ 绝对可积、$e^{-sR}u'(R)\to0$：

$$\mathcal L(u'')=s^2U-su(0^+)-u'(0^+).$$

工程中常用 $u,u'$（二阶还包括 $u''$）的指数阶界作为较强充分条件，取 $\operatorname{Re}s$ 大于这些增长指数。只说“$u$ 指数阶”不足以确保普通导数的绝对可积变换和全部边界项。公式在普通无跳变情形可简记为 $u(0)$。[J. Lebl，Notes on Diffy Qs §6.2.1 的有限边界项分部积分与导数表](https://www.jirka.org/diffyqs/html/transformsofders_section.html)。

例如 $u(t)=e^{at}$、$\operatorname{Re}s>a$ 时，$U=1/(s-a)$、$\mathcal L(u')=a/(s-a)=s/(s-a)-1$，直接积分与导数公式独立吻合；若选实数 $s=a$，远端边界项为 1，原积分也不收敛，不能继续套式。若 $u=H(t-b),b>0$，它不在包含跳点的区间上绝对连续；逐段经典导数为零却漏掉 $\delta_b$。分布方法或逐段积分补跳跃项可给 $\mathcal L(u')=e^{-sb}$，不能把上面的普通函数证明当作已经包含冲激。

初值变成代数项，是它区别于纯时间 Fourier 变换的优势。因果平移与卷积还需匹配可积性、增长域及支撑条件。$0^-$ 协议把原点跳跃/冲激也计入，可能产生 $u(0^-)$ 边界项；本节普通右侧积分采用 $0^+$，两者的对象和端点责任不同，下面 RC 段给出对应入口。

## 半线热方程的阶跃边界

$x>0$、$u_t=\kappa u_{xx}$，初值零，边界 $u(0,t)=1$，无穷远衰减。变换后 $\kappa U_{xx}=sU$，选 $\operatorname{Re}\sqrt{s/\kappa}>0$ 的衰减根，得到 $U=e^{-x\sqrt{s/\kappa}}/s$。逆变换为
$$u(x,t)=\operatorname{erfc}\left(\frac{x}{2\sqrt{\kappa t}}\right),\qquad\operatorname{erfc}(z)=\frac2{\sqrt\pi}\int_z^\infty e^{-r^2}dr\quad(z\ge0).$$
可以直接求导核验，无须盲信变换表。初始点 $(0,0)$ 数据不相容，所以不应要求在那里连续同时取得 0 与 1。

## 自测与解答

求 $u_t+au=f(t),u(0)=u_0$ 的 Laplace 解并逆回时域。

> [!question]- 解答
> $U=(u_0+F)/(s+a)$，所以 $u(t)=u_0e^{-at}+\int_0^te^{-a(t-r)}f(r)dr$。它与积分因子法一致；变换是另一种组织同一线性结构的方法，不是新的物理假设。


## 从本页初值公式回到电容电压

自测中的 $u_t+au=f(t)$ 可以对应一个真实变量的集总模型。为避免数学状态u与源电压同名，令本节数学状态 $u(t)=v_C(t)$，源另记 $v_s(t)$。理想源串R=1 kΩ驱动C=1 μF、输出跨电容，$\tau=RC=1$ ms，KCL给

$$\dot v_C+\frac1\tau v_C=\frac1\tau v_s,
\qquad a=1/\tau=1000\,\mathrm{s}^{-1},\quad
f=v_s/\tau\ (\mathrm{V/s}),\quad u_0=v_0\ (\mathrm V).$$

本页 $U(s)$ 对应电容电压变换 $V_C(s)$、单位V·s，$F(s)$对应 $(1/\tau)V_s(s)$、单位V；这使 $(u_0+F)/(s+a)$ 的量纲仍为V·s。把同一式重新排列得到

$$V_C(s)=\frac1{1+\tau s}V_s(s)+\frac{\tau v_0}{1+\tau s}.$$

首项是零状态传递函数H乘源变换，第二项来自初始储能，不能把有初值问题整体称为H。取 $v_s=1$ V、$v_0=0.4$ V，逆回得到 $v_C(t)=1\,\mathrm V-0.6\,\mathrm V\,e^{-t/\tau}$；t=τ时0.77927234 V，初始斜率600 V/s，可独立代回KCL。

携带上述状态、a、f的单位去[[电子电路/12-交流与变换域/09-传递函数零状态与初始响应#H的定义与初值项|电路H与初值项]]，读两项的量纲和共同收敛域，回来知道数学强迫项f不同于源电压本身。再去[[信号与系统/10-连续与离散系统/02-冲激卷积与零状态响应#非零初值的另一份责任|卷积和初态]]，用本页的积分因子解检查哪个核带1/τ。这里普通无冲激RC满足 $v(0^-)=v(0^+)$，与本页普通0到∞分部积分相容；原点有冲激时到[[电子电路/12-交流与变换域/07-微分性质与零时刻边界#0−协议还要把跳变面积放回来|0−与0+协议]]重新选边界项。带初值的单边求解不指定t<0整条历史，也不替代双边ROC的侧别条件。

## 条件迁移题与答案

1. $f\in L^2$ 能否直接断言 $\partial_jf\in L^2$？怎样添加条件？
2. 对 $1_{[0,1]}$，计算 $\xi=\pi$ 处的 $i\xi\widehat f$，再与分布导数核对。
3. $f\in L^1,g\in L^2$ 的卷积为什么允许使用频域乘法？任意两个温和分布呢？
4. $u=e^{2t}$，取 $s=3$，用直接积分与导数公式两次求 $\mathcal L(u')$；取 $s=2$ 是否仍可套式？
5. RC 的 $v_0\ne0$ 项属于传递函数吗？原点有冲激时先选什么？

> [!question]- 解答
> 1. 不能；取 $f\in H^1$（或明确指定这个方向的弱导数在 $L^2$），才有 $i\xi_j\widehat f\in L^2$。若只在 $\mathcal S'$ 中谈导数，可以保留恒等式但不附带有限导数能量。
> 2. $1-e^{-i\pi}=2$；$\widehat{\delta_0}-\widehat{\delta_1}=1-e^{-i\pi}=2$。把端点外导数零当成全导数会错误得到 0。
> 3. Young 给 $L^2$ 卷积，$\widehat f$ 有界且 $\widehat g\in L^2$，可由逼近延伸恒等式。任意两温和分布的乘积/卷积不自动定义，需额外条件。
> 4. 直接积分 $\int_0^\infty2e^{-t}dt=2$；$U(3)=1$，$3U-1=2$。$s=2$ 时 $U$ 发散且远端边界不消失。
> 5. 初态响应另加，不属于零状态 $H$；原点有冲激先指定 $0^-/0^+$ 协议并核对跳跃项及 ROC。

## 继续学习

前一节：[[数学/46-数理方程/13-Bessel-Legendre函数与正交展开|Bessel-Legendre函数与正交展开]]。 下一节：[[数学/46-数理方程/15-Green函数基本解与边界响应|Green函数基本解与边界响应]]。

课程地图：[[数学/46-数理方程/00-数理方程-MOC|数理方程课程地图]]；[[数学/90-资源/06-统一符号约定与定理条件索引|符号与条件索引]]。

## 跨学科连接

[[数学/45-复变函数/09-留数计算实积分与围道选择|留数计算实积分与围道选择]]：用留数求 Fourier 逆变换或静态 Green 核时，先选与指数符号相配的半平面并证明圆弧消失，再核对极点/分支与本页的变换归一化；Laplace 变换还须保留 $\operatorname{Re}s$ 的收敛域。

## 核验与延伸阅读

本页为独立编写的讲解、推导与算例；以下一手教材用于对照标准定义与课程范围，不是逐段译写。更具体的主题定位见 [[数学/90-资源/04-六科学术来源与阅读对照|学术来源对照]]。

- [Victor Ivrii §5.2：Fourier 属性、Plancherel、分部积分及卷积](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/Chapter5/S5.2.html)：已读 Basic properties 与 Convolution；本页另显式写出适用空间。
- [Victor Ivrii §11.2：温和分布 Fourier 与有条件的分布卷积](https://www.math.utoronto.ca/courses/apm346h1/20181/PDE-textbook/Chapter11/S11.2.html)：已读 Definition 4、Exercise 3、Convolution；原书变换常数须换算。
- [J. Lebl §6.2.1：Laplace 导数的分部积分](https://www.jirka.org/diffyqs/html/transformsofders_section.html)：已读导数推导与 Table 6.2；本文把可检查的局部绝对连续及无穷远条件直接写入推导。

- [Melrose 18.155 Lecture 4，PDF 第 1 页](https://math.mit.edu/~rbm/18.155-F16/L4.pdf)：已读 Fourier 在 $L^2$ 的延伸、$H^s$ 加权频域定义及正整数阶说明。
