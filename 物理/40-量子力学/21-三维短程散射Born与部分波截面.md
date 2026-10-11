---
type: concept
domain: physics
stage: 2
aliases:
  - 三维Born与部分波散射
sources:
  - https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/45dbd7038c3e969491eceeae86c44d42_MIT8_06S18ch7.pdf
  - https://quantummechanics.ucsd.edu/ph130a/130_notes/node228.html
  - https://quantummechanics.ucsd.edu/ph130a/130_notes/node229.html
prerequisites:
  - "[[物理/40-量子力学/03-连续波包概率流与算子边界]]"
  - "[[物理/40-量子力学/08-中心势径向方程与氢样谱]]"
  - "[[物理/40-量子力学/11-相对坐标接触势与一维散射]]"
---
# 三维短程散射：Born、部分波与截面

一维接触势给反射、透射的通量比。三维靶的散射粒子分布在不同方向，探测器还要指定它覆盖的球角；此时预测怎样成为面积？本页先由入射平面波和出射球波定义同一个幅度，再用两种方法求它：Born 保留一次势作用，部分波则把中心势化成独立径向匹配。球形吸引方阱让这两种方法在同一输入上可比，并在首个浅束缚态出现时暴露近似失效。

## 先固定相对运动与入射幅度

取两个可区分、无内部激发的非相对论粒子，质量 $m_1,m_2>0$，相互作用 $V(\mathbf r_1-\mathbf r_2)$。由 [[物理/40-量子力学/11-相对坐标接触势与一维散射#两体运动先分出中心与相对坐标|相对坐标分离]] 在三个方向分别得到

$$\mu=\frac{m_1m_2}{m_1+m_2},\quad
H_{\rm rel}=-\frac{\hbar^2}{2\mu}\Delta+V(\mathbf r),\qquad
E=\frac{\hbar^2k^2}{2\mu}>0.$$

$\mathbf r$ 和 $a$ 用 m，$\mu$ 用 kg，$k$ 用 $\mathrm{m^{-1}}$，$E,V$ 用 J。以下角度和截面在质心系的相对运动中定义。对固定不动的外势可直接用粒子质量；两个等质量粒子则用 $m/2$。实验室角度、反冲和相同粒子的交换计数需要另外变换，不直接套本页结果。

选实、有界、球外为零的势。它是自由三维算子的有界自伴扰动，域仍为 $H^2(\mathbb R^3)$；有限台阶处没有点势，径向解及其导数连续。采用 Dirac 第二位置线性内积。入射方向为 $+z$，远场定态写成

$$\psi_k(\mathbf r)=A\left[e^{ikz}+f_k(\Omega)\frac{e^{ikr}}r+o(r^{-1})\right].$$

选 $A$ 为 $\mathrm{m^{-3/2}}$，则 $\psi$ 也为 $\mathrm{m^{-3/2}}$，**$f$ 必须用 m**。这是指定入射密度标度的广义态；它不属于 $L^2$，不能把全空间积分设为1。可归一波包须另给动量谱和制备。本例可取 $A=a^{-3/2}$；$|A|^2=a^{-3}$ 是标度，不是某台实验仪器的真实束流密度。

概率流为 $\mathbf j=(\hbar/\mu)\operatorname{Im}(\psi^*\nabla\psi)$，单位 $\mathrm{m^{-2}s^{-1}}$。入射流密度和散射球波的领先径向流分别是

$$j_{\rm in}=\frac{\hbar k}{\mu}|A|^2,\qquad
j_{{\rm sc},r}=\frac{\hbar k}{\mu}|A|^2\frac{|f(\Omega)|^2}{r^2}+o(r^{-2}).$$

球面小块面积为 $r^2d\Omega$，$d\Omega=\sin\theta\,d\theta\,d\phi$ 是无量纲球角（惯用 sr）。该块散射流除以入射**单位面积流**，得到

$$\boxed{\frac{d\sigma}{d\Omega}=|f(\Omega)|^2},\qquad
\sigma=\int_{S^2}|f|^2d\Omega.$$

所以 $d\sigma/d\Omega$ 的 SI 量纲为 $\mathrm{m^2}$，常标作 $\mathrm{m^2/sr}$；$\sigma$ 为 $\mathrm{m^2}$。任意共同幅度 $A$、球半径和弹性速度全部消去。$\sigma$ 可以大于几何面积 $\pi a^2$，不是“碰中实体的概率”。

这里使用渐近分离的出射散射通道；总态的流还含入射与散射波的干涉，不能逐点把 $j_r-j_{{\rm in},r}$ 当正散射流。前向束中的干涉与消光由后文光学定理约束。实际有限屏幕、波包或束流计数需要它们各自的制备和探测模型。[MIT 8.06 Ch.7 §7.1](https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/45dbd7038c3e969491eceeae86c44d42_MIT8_06S18ch7.pdf) 给出此入射/出射约定及流到面积的接口。

## 出射 Green 函数把未知波放回势区

将定态方程改写为

$$(\Delta+k^2)\phi=\frac{2\mu}{\hbar^2}V\phi,\qquad \phi=\psi/A.$$

选出射 Helmholtz Green 函数

$$G_k^+(\mathbf r)=-\frac{e^{ik|\mathbf r|}}{4\pi|\mathbf r|},\qquad
(\Delta+k^2)G_k^+=\delta^{(3)}.$$

负号由 $\Delta(1/r)=-4\pi\delta^{(3)}$ 决定，$G$ 用 $\mathrm{m^{-1}}$。它满足出射辐射条件；若改入射 Green，就会改变要解的散射问题。固定入射平面波后，Lippmann–Schwinger 方程为

$$\phi(\mathbf r)=e^{ikz}
-\frac{\mu}{2\pi\hbar^2}\int
\frac{e^{ik|\mathbf r-\mathbf r'|}}{|\mathbf r-\mathbf r'|}
V(\mathbf r')\phi(\mathbf r')d^3r'.$$

积分核只在势的有限支撑上取未知 $\phi$。对远处观察方向 $\hat{\mathbf r}$，$|\mathbf r-\mathbf r'|=r-\hat{\mathbf r}\cdot\mathbf r'+O(a^2/r)$，所以

$$f(\mathbf k',\mathbf k)=-\frac{\mu}{2\pi\hbar^2}
\int e^{-i\mathbf k'\cdot\mathbf r'}V(\mathbf r')\phi(\mathbf r')d^3r',
\quad \mathbf k=k\hat z,\ \mathbf k'=k\hat{\mathbf r}.$$

此式单位为 $(\mathrm{J^{-1}m^{-2}})(\mathrm{J\,m^3})=\mathrm m$。这里 Fourier 积分**没有**另加 $(2\pi)^{-3/2}$；那些因子属于另一种平面波基的归一约定，不能再乘一次。[MIT Ch.7 §7.3及7.3.1](https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/45dbd7038c3e969491eceeae86c44d42_MIT8_06S18ch7.pdf) 的出射积分方程与 Born 迭代可按这个符号约定核对。

## Born 近似的收益与可检查条件

未知的势区波导致积分方程难解。将其替换为未受扰的入射波 $e^{i\mathbf k\cdot\mathbf r'}$，只保留第一次势作用，得到

$$f_B(\theta)=-\frac{\mu}{2\pi\hbar^2}
\int e^{-i\mathbf q\cdot\mathbf r}V(\mathbf r)d^3r,\qquad
\mathbf q=\mathbf k'-\mathbf k,\quad q=2k\sin(\theta/2).$$

收益是直接计算势的 Fourier 分量；代价是丢掉重复散射和共振的重求和。$E>W$ 或“粒子很快”并不是这里的一般误差证明。对中心势可先做球角积分 $\int e^{-iqr\cos\alpha}d\Omega=4\pi\sin(qr)/(qr)$：

$$f_B(q)=-\frac{2\mu}{\hbar^2}\int_0^a V(r)r^2\frac{\sin(qr)}{qr}dr.$$

选一个可完整解析的球形吸引方阱

$$V(r)=\begin{cases}-W,&0\le r<a,\\0,&r>a,\end{cases}\quad W\ge0,
\qquad E_a=\frac{\hbar^2}{2\mu a^2},\quad\eta=\frac W{E_a},\quad x=ka.$$

$W=0$ 是自由对照。$\eta,x$ 无量纲；$E=x^2E_a$。积分一次得到

$$\boxed{\frac{f_B(\theta)}a=\eta\frac{\sin y-y\cos y}{y^3}},\qquad
 y=2x\sin(\theta/2).$$

前向或 $x\to0$ 使用连续极限 $f_B/a\to\eta/3$，并非 $0/0$。可由级数 $1/3-y^2/30+y^4/840-\cdots$ 检查。低能 Born 总截面因此趋于 $4\pi a^2\eta^2/9$。

这个模型还能给一条**充分**的严格控制条件。把 LS 势区积分记作 $K$，在球内连续有界函数的上确界范数中，

$$\|K\|_\infty\le\frac{\mu W}{2\pi\hbar^2}
\sup_{|\mathbf r|\le a}\int_{|\mathbf r'|\le a}\frac{d^3r'}{|\mathbf r-\mathbf r'|}
=\frac{\mu Wa^2}{\hbar^2}=\frac\eta2=:c.$$

最后一个球积分在球内为 $2\pi(a^2-r^2/3)$，最大值在中心；核的 $1/|\mathbf r-\mathbf r'|$ 奇点局部可积。$c<1$ 时 Neumann 级数收敛，$\|\phi\|_\infty\le1/(1-c)$，故

$$\|\phi-e^{ikz}\|_\infty\le\frac c{1-c},\qquad
\boxed{|f-f_B|\le\frac{\eta a}{3}\frac c{1-c}}.$$

此推导适用于这个有限球阱的各个 $k>0$，是绝对幅度误差界；$\eta\ll1$ 比仅有 $c<1$ 更能保证小修正。在 Born 零点处，不能把它除以 $|f_B|$ 声称小相对误差。$\eta\ge2$ 时此充分保证失去，既不说明每个角度都错误，也不证明所有高能 Born 都错误；必须另算或另给有效条件。

## 部分波：固定入射幅，允许出射相位变化

中心势使不同 $l,m$ 不混合。沿用 [[物理/40-量子力学/08-中心势径向方程与氢样谱#分离角坐标时也要变换归一化|径向变换]]，球谐归一为 $\int|Y_{lm}|^2d\Omega=1$；沿 $z$ 的平面波只有 $m=0$：

$$e^{ikz}=\sum_{l=0}^\infty i^l(2l+1)j_l(kr)P_l(\cos\theta),\quad
Y_{l0}=\sqrt{\frac{2l+1}{4\pi}}P_l(\cos\theta).$$

这里 $\int_{-1}^1P_l(c)P_{l'}(c)dc=2\delta_{ll'}/(2l+1)$。所有 $l$ 共同组成入射平面波，不是一组额外等概率的制备。远处 $j_l(kr)\sim\sin(kr-l\pi/2)/(kr)$。把每个径向因子的入射系数保持不变，写

$$R_l(r)\sim\frac{S_l e^{i(kr-l\pi/2)}-e^{-i(kr-l\pi/2)}}{2ikr}.$$

实势、正则原点、单一弹性通道保持每个径向 Wronskian/流，因此 $|S_l|=1$。令 $S_l=e^{2i\delta_l}$，也可写 $R_l\sim e^{i\delta_l}\sin(kr-l\pi/2+\delta_l)/(kr)$。相移 $\delta_l$ 只由 $S_l$ 定义到模 $\pi$；整体枝跳不产生新物理散射。自由势 $S_l=1$。

减去自由平面波的出射部分，用 $i^le^{-il\pi/2}=1$，得到

$$\boxed{f(\theta)=\frac1{2ik}\sum_{l=0}^\infty(2l+1)(S_l-1)P_l(\cos\theta)
=\frac1k\sum_l(2l+1)e^{i\delta_l}\sin\delta_l P_l(\cos\theta)}.$$

先在幅度上相加，再取模平方；不能把各 $l$ 的强度在每个角度直接相加。全角积分利用 Legendre 正交性才消除交叉项：

$$\boxed{\sigma=\frac{4\pi}{k^2}\sum_l(2l+1)\sin^2\delta_l},\qquad
0\le\sigma_l\le\frac{4\pi}{k^2}(2l+1).$$

单位来自 $k^{-2}$；每个通道的上界来自酉性。同样，在前向 $P_l(1)=1$，$\operatorname{Im}(e^{i\delta_l}\sin\delta_l)=\sin^2\delta_l$，得单弹性光学定理

$$\sigma=\frac{4\pi}{k}\operatorname{Im}f(0).$$

一阶 Born 对实球势给实 $f_B$，却给非零 $|f_B|^2$：这不是精确光学定理的反例。总截面是势强的二阶量，前向虚部在二阶振幅才出现，不能要求一阶振幅已完成二阶酉性收支。归一及通道约定可对照 [UCSD 部分波原文](https://quantummechanics.ucsd.edu/ph130a/130_notes/node228.html)。

## 球阱的全部径向通道怎样匹配

方阱内部波数 $q_i=\sqrt{k^2+2\mu W/\hbar^2}$，$Q=q_i a=\sqrt{x^2+\eta}$。正则支为 $R_l=Cj_l(q_i r)$；外部写 $D[j_l(kr)\cos\delta_l-n_l(kr)\sin\delta_l]$，其中 $n_l\sim-\cos(kr-l\pi/2)/(kr)$。在 $a$ 匹配 $R_l,R_l'$ 给

$$\tan\delta_l=\frac{N_l}{D_l},\quad
N_l=xj_l'(x)j_l(Q)-Qj_l'(Q)j_l(x),\quad
D_l=xn_l'(x)j_l(Q)-Qj_l'(Q)n_l(x).$$

撇号只对无量纲自变量求导。原匹配可用对数导数解释，但 $j_l(Q)=0$ 时不能除以它；上述交叉乘积在这类点仍可用。程序直接计算

$$S_l=\frac{D_l+iN_l}{D_l-iN_l},$$

避免先求发散的 $\tan\delta_l$。按最大模缩放 $D_l,N_l$ 也不改变 $S_l$。这些解析匹配公式对每个通道成立；程序只取有限 $0\le l\le L$，比较 $L+4$ 的额外贡献作收敛指标，不能把这个比较冒充一般无限尾界。[UCSD 球阱原文](https://quantummechanics.ucsd.edu/ph130a/130_notes/node229.html) 给内部正则支与外部组合的匹配。

## 低能 s 波把浅束缚阈值接回来

$l=0$ 时 $u=rR$ 的内部正则解为 $C\sin(q_i r)$，外部为 $D\sin(kr+\delta_0)$。连续导数给

$$q_i\cot(q_i a)=k\cot(ka+\delta_0),\qquad
S_0=e^{-2ix}\frac{Q\cos Q+i x\sin Q}{Q\cos Q-i x\sin Q}.$$

无势时 $Q=x$，$S_0=1$；该式可独立于高 $l$ 的贝塞尔算法复算。s 波单独给各向同性的 $d\sigma_0/d\Omega=\sin^2\delta_0/k^2$。低能离心项压低高 $l$ 的势区到达；离阈且无相应高 $l$ 共振时，$\delta_l=O(k^{2l+1})$，常由 s 波主导。不能仅凭 $ka<1$ 保证 Born，因为 s 波本身可以强烈共振。

在零能令外部 $u\propto r-a_s$，与内部 $\sin(\sqrt\eta r/a)$ 匹配，得到散射长度

$$\boxed{\frac{a_s}{a}=1-\frac{\tan\sqrt\eta}{\sqrt\eta}},\qquad
\delta_0=-ka_s+O(k^3a^3)$$

（后一余项的系数在阈值附近不统一有界）。这里选择低能趋0的模 $\pi$ 代表；已有束缚态时连续选取的物理相移枝可以趋 $\pi$，但同一个 $S_0$ 和截面不变。弱阱展开 $a_s/a=-\eta/3-2\eta^2/15-\cdots$，所以 $f_0\to-a_s\approx\eta a/3$，与 Born 的低能 Fourier 结果接上。固定有限 $a_s$ 再令 $k\to0$，$\sigma\to4\pi a_s^2$；在 $k|a_s|$ 不小的近阈卡上不能继续用这个零能值。

若要看浅束缚态，令 $E_b=-w^2E_a$，内部 $z=q_ba$，外部 $u\propto e^{-wr/a}$。正则原点与边界匹配给

$$z^2+w^2=\eta,\qquad z\cot z=-w,\quad w>0.$$

首个 s 束缚态只在 $\sqrt\eta>\pi/2$ 才出现。$\eta=\pi^2/4$ 时 $w=0$，外部 $u$ 为常数、$R\propto1/r$，$\int|u|^2dr$ 发散；它是零能阈值解，不能计为归一束缚态。阈下 $a_s\to-\infty$，阈上 $a_s\to+\infty$。恰在阈值令 $k\to0$，s 波趋近 $\sin^2\delta_0=1$、$\sigma_0\sim4\pi/k^2$；先取固定非阈深度的零能极限，得到的是 $4\pi a_s^2$。这两个极限不能互换。

浅态使重复势作用不能忽略，Born 低能值却始终只是 $\eta a/3$；它没有这个阈值极点。阱深从阈下变阈上可给同样大的散射强度，却改变幅度实部与负能谱；只测一个角度的强度不足以恢复所有相位和束缚信息。

## 一个完整输入与图上的条件改变

教学参数 $a=1\,\mathrm{nm}$、$\mu=10^{-30}\,\mathrm{kg}$、$\hbar=1.054571817\times10^{-34}\,\mathrm{J\,s}$，故 $E_a\approx5.560608586\times10^{-21}\,\mathrm J$。完整弱阱例取 $\eta=0.09,x=0.1$，$W=0.09E_a$，$E=0.01E_a$，$k=10^8\,\mathrm{m^{-1}}$。此处 $E<W$，但充分参数 $c=0.045$ 很小；深度相对动能不是本低能条件的主判断。

手算 Born 前向 $f_B(0)=0.03a$；精确零能散射长度 $a_s/a=1-\tan0.3/0.3\approx-0.0311208320$。在有限 $x=0.1$ 由 $Q=\sqrt{0.10}$ 匹配求 $S_0$，再用上式求幅度和截面。CLI 全分波有限求和给

$$\sigma/a^2\approx0.0121181312,\quad
\sigma_B/a^2\approx0.0112645979,\quad
\sigma\approx1.21181312\times10^{-20}\,\mathrm{m^2}.$$

取 $A=a^{-3/2}$，入射流标度 $j_{\rm in}=\hbar x/(\mu a^4)\approx1.054571817\times10^{31}\,\mathrm{m^{-2}s^{-1}}$；乘 $d\sigma$ 才成为该球角内的散射流。这个任意标度并非已测粒子速率。

同卡图中保留五个条件，不把阈值卡称浅束缚：

| 卡 | $\eta$ | $ka$ | $\sigma/a^2$（有限分波） | $\sigma_B/a^2$ | $a_s/a$与负能状态 |
|---|---:|---:|---:|---:|---|
| weak | 0.09 | 0.1 | 0.0121181 | 0.0112646 | −0.0311208；无 s 束缚态 |
| moderate | 1 | 2 | 0.380216 | 0.373347 | −0.557408；角分布需多通道 |
| below | $(\pi/2-0.02)^2$ | 0.1 | 1104.73370 | 8.04359 | −31.2372；阈下无束缚态 |
| threshold | $\pi^2/4$ | 0.1 | 1253.49923 | 8.46662 | 散射长度极点；零能解不可归一 |
| above | $(\pi/2+0.02)^2$ | 0.1 | 1177.65020 | 8.90613 | +32.4266；$E_b/E_a\approx-0.000981148$ |

![[物理/80-实践/45-三维短程散射/assets/angular.svg]]

每窗固定自己的 $\eta,ka$；横轴角度 rad，纵轴为 $|f/a|^2$，乘 $a^2$ 恢复面积/sr。moderate 的 $\sigma_0/a^2\approx0.258380$ 仅占总量的一部分，只有 s 波的水平线不能解释其角分布。threshold 的有限 $ka=0.1$ 截面不是无穷大；单 s 通道上限此时为 $4\pi a^2/0.1^2$。

![[物理/80-实践/45-三维短程散射/assets/energy.svg]]

固定每卡阱深，改变 $ka$；两个坐标均为标明的 $\log_{10}$。弱阱低能趋于有限值，阈值卡低能增长；近阈卡应使用有限能匹配。Born 有时在某些高能点接近精确值，但这些点不认证一般高能误差定理。

![[物理/80-实践/45-三维短程散射/assets/depth.svg]]

上窗保持 $ka=0.1$ 只改深度，下窗单独画 s 束缚能/$E_a$，不给幅度、面积和能量共用一个纵轴。负能支只在阈上出现；上窗的近阈峰与下窗的新谱值来自同一势，却不是同一个观测量。三图和 CSV 来自 [[物理/80-实践/45-三维短程散射/README#复建同一输入与输出|同一规范源码、输入和结果]]。

## 先迁移，再核答案

**半引导题。** 保持弱阱的 $W,\mu,E$，把半径加倍。先写 $\eta,ka$ 如何变，再算 Born 的前向幅度和它对应的微分截面；是否还能只说“面积加四倍”？说明充分控制参数怎么变化。

**撤提示题一。** 两个模型在同一 $a,\mu,ka=0.1$，深度分别为 below 和 above。有人依据很大的近阈截面就判定两者都有束缚态，又把阈上 $4\pi a_s^2$ 作为这个有限能截面。指出可区分它们的预测，检查所用极限与酉性上界。

**撤提示题二。** 重新设计一组尺度：半径加倍、质量保持不变，同时使 $\eta,ka$ 保持 weak 卡的数值。需要怎样改 $W,E,k$？哪些无量纲图可复用，$f,\sigma,j_{\rm in}$ 各自怎样缩放？再解释为什么一阶 Born 的实前向幅不满足精确光学定理，并不意味着概率流的基本公理失效。

**撤提示题三。** 将吸引阱换成同强度的排斥球势。Born 幅度与 Born 强度有什么变化？能否据此推断精确强度和负能谱也都一样？这题要求解析迁移；本 CLI 只接受吸引阱 $W\ge0$。

答案在 [[物理/80-实践/45-三维短程散射/ANSWERS|迁移核对]]；先写所用对象、条件和单位再展开。阅读答案和模型走读不是已观察到的真人学习结果。

到这里可以停下：你已能把三维渐近波的流化为面积，用 Born 和正则径向匹配预测同一个有限球阱，并由浅束缚阈值判断近似与低能极限何时不能互换。需要重新核概率流时返回03，需要角通道和原点条件时返回08；11/12仍负责一维通量匹配。相同粒子的 $f(\theta)\pm f(\pi-\theta)$ 及探测计数、长程 Coulomb、非弹性/吸收/多通道、一般势与全部共振、多体散射和 QFT 均需新增各自条件。本页数值是有限输入的检验，解析推导承担本模型的一般结论；真实碰撞装置、实验截面、Obsidian与真人能力未被程序认证。
