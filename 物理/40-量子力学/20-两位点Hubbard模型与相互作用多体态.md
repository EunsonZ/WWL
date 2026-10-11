---
title: 两位点Hubbard模型与相互作用多体态
aliases:
  - Hubbard双位点的双占据与自旋
stage: 0
sources:
  - https://arxiv.org/pdf/1502.02194
  - https://www.cond-mat.de/events/correl21/manuscripts/burke.pdf
  - https://arxiv.org/html/quant-ph/9605038
prerequisites:
  - "[[物理/40-量子力学/10-张量积纠缠偏迹与交换对称]]"
  - "[[物理/40-量子力学/14-角动量相加与两自旋耦合]]"
  - "[[物理/40-量子力学/19-自由多模Fock占据与量子统计]]"
---

# 两位点Hubbard模型与相互作用多体态

两个电子平均各占一个位置，是否说明电荷不再涨落？排斥使双占据很少时，两个局域自旋是否一定接近 singlet？这两问分别需要电荷代价 $U$ 与交换能隙 $J$：**大排斥抑制电荷涨落，但自旋被 singlet 锁定还需要温度小于更低的交换尺度。** 一个精确可算的双位点能把这两个尺度分开。

[[物理/40-量子力学/19-自由多模Fock占据与量子统计#自由的对象，以及热态从哪里来|自由多模]]把保持数的二次 $H$ 对角化为独立模式；本课加入 $U n_{i\uparrow}n_{i\downarrow}$，同一位置两个不同自旋模式的占据会改变彼此的能量。我们仍完整求解固定 $N=2$ 的六维空间，不以单粒子 FD 均值代替多体态。[[物理/40-量子力学/14-角动量相加与两自旋耦合#交换耦合的两能级与有限时间预测|两自旋交换谱]]在这里得到一个低能来源；但完整双位点还允许空位与双占据，空间不是从一开始就只有四个自旋态。

## 四个完整模式，六个合法占据态

每个位置只有一个空间轨道、两个自旋模式，模式顺序固定为

$$
 (1\uparrow,1\downarrow,2\uparrow,2\downarrow)=(0,1,2,3),\qquad
 |\mathbf n\rangle=(c_0^\dagger)^{n_0}\cdots(c_3^\dagger)^{n_3}|0\rangle.
$$

CAR 为 $\{c_a,c_b^\dagger\}=\delta_{ab}I$、$\{c_a,c_b\}=0$；湮灭模式 $a$ 时带 $(-1)^{\sum_{b<a}n_b}$。算符右侧先作用，全部矩阵列为输入态、行为输出态。固定 $\sum n_a=2$，按所占模式对的升序排列：

| 序号 | 所占模式 | 态名 | 两位置占据 |
|---|---|---|---|
| 0 | $(0,1)$ | $D_1=c_{1\uparrow}^\dagger c_{1\downarrow}^\dagger|0\rangle$ | $(2,0)$ |
| 1 | $(0,2)$ | $T_+=|\uparrow,\uparrow\rangle$ | $(1,1)$ |
| 2 | $(0,3)$ | $A=|\uparrow,\downarrow\rangle$ | $(1,1)$ |
| 3 | $(1,2)$ | $B=|\downarrow,\uparrow\rangle$ | $(1,1)$ |
| 4 | $(1,3)$ | $T_-=|\downarrow,\downarrow\rangle$ | $(1,1)$ |
| 5 | $(2,3)$ | $D_2=c_{2\uparrow}^\dagger c_{2\downarrow}^\dagger|0\rangle$ | $(0,2)$ |

共 $\binom42=6$ 个态，每态计一次。一个位置容纳反向自旋不违反 Pauli，它们是不同的完整模式；禁止的是同一完整模式的重复占据。单个 $c_a$ 会离开 $N=2$ 扇区，不能把其六维投影当成满足完整 CAR 的四个湮灭算符；实践先按完整占据规则作用，再把保持 $N$ 的双线性项限制到六维。

## 跳跃与排斥怎样给出矩阵符号

只取对称、无磁场、无位点偏置的 Hubbard 模型：

$$
 H=-t\sum_{\sigma=\uparrow,\downarrow}
 (c_{1\sigma}^\dagger c_{2\sigma}+c_{2\sigma}^\dagger c_{1\sigma})
 +U\sum_{i=1}^2n_{i\uparrow}n_{i\downarrow},
 \quad t>0,\ U\ge0.
$$

这里 $t$ 是**跳跃能量参数**，不是时间；$t,U$ 用 eV。总数守恒，完整四模式 Fock 维数16，本课固定两粒子的物理空间只有上述六维。短程排斥只罚双占据；真实材料轨道、长程 Coulomb、额外轨道与磁场均没有输入。

一个符号检查足以暴露常见错误：对 $D_1$，$c_{2\uparrow}^\dagger c_{1\uparrow}$ 将 $c_{1\downarrow}^\dagger$ 移到正确顺序时给负号，故乘 $-t$ 后为 $+tB$；$c_{2\downarrow}^\dagger c_{1\downarrow}$ 则给 $-tA$。因此 $H D_1=UD_1-tA+tB$，$H D_2=UD_2-tA+tB$。在上表顺序：

$$
 H=\begin{pmatrix}
 U&0&-t&t&0&0\\
 0&0&0&0&0&0\\
 -t&0&0&0&0&-t\\
 t&0&0&0&0&t\\
 0&0&0&0&0&0\\
 0&0&-t&t&0&U
 \end{pmatrix}.
$$

把 $A,B$ 的名字当作可区分粒子的任意顺序、忽略 CAR，会把 singlet/triplet 与跳跃相连的块弄反。

模型对象与对称基态公式对应 [Carrascal 等式(22)/(36)及 Appendix A](https://arxiv.org/pdf/1502.02194)；论文以 $E/(2t),U/(2t)$ 为无量纲量，而本课图用 $E/t,U/t$。本文六基符号、有限温度概率与下文相关量独立推导。[Burke–Kozlowski §1.2](https://www.cond-mat.de/events/correl21/manuscripts/burke.pdf) 将给定双位点参数与真实材料建模区别开来；我们沿用该模型边界，不承接其 DFT 或广延体系结论。

## 三重态不跳到双占据，单态会混合

定义

$$
 |S\rangle=\frac{A-B}{\sqrt2},\quad
 |T_0\rangle=\frac{A+B}{\sqrt2},\quad
 |D_\pm\rangle=\frac{D_1\pm D_2}{\sqrt2}.
$$

$T_+,T_0,T_-$ 构成总自旋1的三重态，每态能量0。$S,D_+,D_-$ 都是总自旋0；一个位置上的同轨道反向自旋双占据也是 singlet。$D_-$ 能量为 $U$，与其余态不混合。在 $(S,D_+)$ 中

$$
 H_S=\begin{pmatrix}0&-2t\\-2t&U\end{pmatrix},\qquad
 R=\sqrt{U^2+16t^2},\qquad E_\pm=\frac{U\pm R}{2}.
$$

六个本征态是三个能量0的 triplet、能量 $U$ 的 $D_-$、能量 $E_-$ 与 $E_+$ 的两个混合 singlet。对 $t>0$，$E_-<0$ 为唯一基态；取实正系数

$$
 |g\rangle=a|S\rangle+b|D_+\rangle,
 \quad a^2=\frac{1+U/R}{2},\quad b^2=d=\frac{1-U/R}{2},\quad a,b\ge0.
$$

上态可取 $|e\rangle=-b|S\rangle+a|D_+\rangle$。$a^2+b^2=1$、两向量正交；改变本征态整体相位不改概率。大 $U$ 数值相减不稳时，用等价式

$$
 E_-=-\frac{8t^2}{U+R},\qquad d=\frac{8t^2}{R(R+U)}.
$$

## 双占据与自旋是两个观测，平均位置数看不出来

令

$$
 D=\sum_i n_{i\uparrow}n_{i\downarrow},\quad n_i=n_{i\uparrow}+n_{i\downarrow},
 \quad \mathbf s_i=\mathbf S_i/\hbar
 =\frac12\sum_{\sigma\sigma'}c_{i\sigma}^\dagger\boldsymbol\sigma_{\sigma\sigma'}c_{i\sigma'}.
$$

$D$ 是总双占据数，本课 $N=2$ 时只取0或1，等于“有一个双占据位置”的概率；**每个位置**的双占据均值是 $\langle D\rangle/2$。$\mathbf s_i$ 无量纲，空位与双占据位置自旋为0，单占据时是自旋 $1/2$。

基态给

$$
 \langle D\rangle_g=d,\quad
 \langle\mathbf s_1\cdot\mathbf s_2\rangle_g=-\frac34(1-d),
 \quad\langle n_1\rangle=\langle n_2\rangle=1.
$$

位置平均数对所有 $U$ 一样，不能辨别双占据。由于 $n_1+n_2=2$ 且位点对称，

$$
 \operatorname{Var}(n_1)=\langle D\rangle,
 \quad C_{12}^{n}=\langle n_1n_2\rangle-\langle n_1\rangle\langle n_2\rangle=-\langle D\rangle.
$$

这些式也对本课有限温度正则态成立。负电荷相关在 $U=0$ 已存在，来自固定数和波函数，不能单凭它证明排斥，更不能直接证明纠缠。为了让 $\langle D\rangle$ 的定义可检查，注意 $\partial_U E_- =d$；有限温度自由能 $F=-k_BT\log Z_2$ 也有 $\partial_UF=\langle D\rangle$。但 $[H,D]\ne0$，不能把 $\partial_U\langle D\rangle$ 随手改写为经典的 $-\beta\operatorname{Var}(D)$。

## U 为零回到自由填充，有限 U 的纯态不再是独立轨道填充

$U=0$ 时，一个自旋的跳跃矩阵有 bonding/antibonding 模式

$$
 b_\sigma^\dagger=(c_{1\sigma}^\dagger+c_{2\sigma}^\dagger)/\sqrt2,
 \quad f_\sigma^\dagger=(c_{1\sigma}^\dagger-c_{2\sigma}^\dagger)/\sqrt2,
 \quad\varepsilon_b=-t,\ \varepsilon_f=t.
$$

两个电子填两个 bonding 自旋轨道：$|g\rangle=b_\uparrow^\dagger b_\downarrow^\dagger|0\rangle=(S+D_+)/\sqrt2$，$E_g=-2t$、$D=1/2$、自旋点积 $-3/8$。四模式固定两粒子的自由谱为 $-2t,0,0,0,0,2t$，与六维解完全一致。这是 [[物理/40-量子力学/19-自由多模Fock占据与量子统计#固定 N：每个占据态一次，模式会相关|固定数自由统计]] 的具体谱；即使 $U=0$，固定 $N$ 的有限温度制备也不因此成为 GC 独立 FD 乘积。

有限 $U>0$，相互作用为四次项，单粒子酉变换不能按19的步骤将**这个相互作用模型**化成独立单粒子能量和。基态可写成两个双填充行列式的叠加：

$$
 |g\rangle=\frac{a+b}{\sqrt2}|b_\uparrow b_\downarrow\rangle
 +\frac{b-a}{\sqrt2}|f_\uparrow f_\downarrow\rangle.
$$

每个自旋的一体矩阵 $\gamma_{i\sigma,j\sigma'}=\langle c_{i\sigma}^\dagger c_{j\sigma'}\rangle$ 为

$$
 \gamma_\sigma=\begin{pmatrix}1/2&2t/R\\2t/R&1/2\end{pmatrix},\qquad
 n_b=\frac12+\frac{2t}{R},\quad n_f=\frac12-\frac{2t}{R}.
$$

对纯固定数 Slater 态，$\gamma$ 是已填轨道的投影，满足 $\gamma^2=\gamma$；这里有限 $U>0$ 的自然占据严格介于0和1，所以这个纯基态不是单个 Slater 行列式。不能只拟合这几个均值就宣布获得完整独立 FD 态：独立分数占据的热乘积会是另一混态，并带总数涨落，而 $|g\rangle$ 仍纯且固定两粒子。本课没有计算 GC；若另加 GC，须对16维全部 $N$ 扇区求 $\Xi$，不能把六维 $Z_2$ 改名为它。

## 大 U 的交换尺度为何更小，以及误差有多大

跳跃将单占据 singlet 暂时带到代价 $U$ 的双占据，再跳回；triplet 因符号抵消没有这条通道。精确 singlet–triplet 能隙是

$$
 \Delta_{ST}=0-E_- =\frac{8t^2}{R+U}
 =\frac{4t^2}{U}-\frac{16t^4}{U^3}+O(t^6/U^5).
$$

当 $t/U\ll1$ 时，在低能单占据空间得到

$$
 H_{\rm spin}=J_2\left(\mathbf s_1\cdot\mathbf s_2-\frac14I\right),
 \qquad J_2=4t^2/U>0.
$$

它让 triplet 为0、singlet 为 $-J_2$；与14的 $g\mathbf s_1\cdot\mathbf s_2$ 只差共同能量平移，不改变该低能空间中的能隙。此模型的代价是漏掉双占据幅度与高能态；不能在整个六维空间直接替换 $H$。相对能隙误差有精确恒等式

$$
 \frac{J_2-\Delta_{ST}}{\Delta_{ST}}
 =\frac{R-U}{2U}=\frac{\Delta_{ST}}{U}
 \le4(t/U)^2,\qquad U>0.
$$

$U/t=4$ 时 $J_2$ 高估能隙约20.71%，并不很精确；$U/t=20$ 时约0.9902%。基态双占据 $d=4(t/U)^2+O((t/U)^4)$，虽小仍非零。

有限温度使用自旋近似还须 $k_BT\ll U$ 以压低高能双占据，若要求接近纯 singlet，更需 $k_BT\ll\Delta_{ST}\approx J_2$。当 $J_2\ll k_BT\ll U$，电荷几乎不动，自旋却可接近四态混合。仅把 $U$ 增大而保持 $t,T$，$J_2$ 反而减小，不能保证热态更接近 singlet。

## 六态正则温度，完整密度矩阵先于平均量

温度 $T>0$ 是热平衡制备条件，$\beta=1/(k_BT)$。闭合酉演化不会自行证明这种准备；[[物理/40-量子力学/18-有限环境与约化态退相干#从矩阵恢复相干、布居、能量与纯度|纯退相干]]也不能替代能量平衡。固定 $N=2$：

$$
 Z_2=e^{-\beta E_-}+e^{-\beta E_+}+e^{-\beta U}+3,
 \quad \rho_2=\sum_{\lambda=1}^6w_\lambda|\lambda\rangle\langle\lambda|,
 \quad w_\lambda=e^{-\beta E_\lambda}/Z_2.
$$

记 $w_-,w_+,w_D$ 为三个 singlet 的**各态**概率，$w_T=1/Z_2$ 是**一个** triplet 的概率；总 triplet 权重 $3w_T$。则

$$
 \langle D\rangle=w_-d+w_+(1-d)+w_D,
$$

$$
 \langle\mathbf s_1\cdot\mathbf s_2\rangle
 =-\frac34\big[w_-(1-d)+w_+d\big]+\frac34w_T.
$$

每个 triplet 点积 $1/4$，乘三个态才给后一项。$\operatorname{Tr}\rho_2^2=w_-^2+w_+^2+w_D^2+3w_T^2$；总数方差仍为0。源码输出完整 $6\times6$ 的 $\rho,H,D,\mathbf s_1\cdot\mathbf s_2$ 及 $4\times4$ 一体矩阵，不只报均值。

$T\to\infty$ 的固定数极限为 $\rho_2\to I_6/6$，有 $D\to1/3$、自旋点积趋0、$C_{12}^n\to-1/3$、纯度 $1/6$。该非零电荷相关不是低温磁性。升温也不保证双占据单调增加：低温先激发的 triplet 没有双占据，可先降低 $D$；高能 singlet 与 $D_-$ 随后参与，才向高温 $1/3$ 靠近，具体走势由完整权重决定。$T\to0$ 且 $t>0$ 则回到唯一基态。

## 相关不等于纠缠，先说明留下的是哪两个子系统

两个可寻址位置上的粒子数与局域自旋可观测，但电子编号不是操作地址。完整局域空间含 $|0\rangle,|\uparrow\rangle,|\downarrow\rangle,|\uparrow\downarrow\rangle$；六维固定总数空间嵌在两个局域四态空间内。fermion 的局部奇偶/粒子数操作限制需要声明，不能直接把单位置混合度全部叫可用的自旋纠缠。[[物理/40-量子力学/10-张量积纠缠偏迹与交换对称#相同局部混态怎样隐藏不同联合概率|局部混态不决定联合态]]的边界在这里仍成立。

一个明确可检查的实验条件是先分别测两位置粒子数，**只保留每处一个粒子**的结果。投影 $P_{11}$ 的成功概率 $p_{11}=1-\langle D\rangle$；保留后的两个局域自旋空间是 $\mathbb C^2\otimes\mathbb C^2$。因本模型 SU(2) 不变，条件态为

$$
 \rho_{11}=p_S|S\rangle\langle S|+\frac{1-p_S}{3}\Pi_T,
 \quad p_S=\frac{w_-(1-d)+w_+d}{1-\langle D\rangle}.
$$

其自旋点积 $1/4-p_S$，所以负值只说明 $p_S>1/4$。直接对第二自旋做部分转置，特征值为三重 $(1+2p_S)/6$ 及 $(1-2p_S)/2$。在这**两个二维自旋**上，PPT 是可分充要条件，故

$$
 \rho_{11}\text{ 纠缠}\ \Longleftrightarrow\ p_S>1/2.
$$

该充分性限于 $2\times2$，依据 [Horodecki 等 Theorem 3](https://arxiv.org/html/quant-ph/9605038)；不能搬到未条件化的两个四态位置空间。$1/4<p_S\le1/2$ 给负自旋相关但可分的明确反例。在纯基态下，无论 $U\ge0$，条件态都是 singlet，成功概率 $1-d$；这项后选择改变了状态，不说明任意温度完整 fermion 态的纠缠。真实实现还需位置数测量、局部自旋测量及其操作许可；模型复算没有验证设备或样品。

## t 为零不是唯一 singlet 的连续替身

本课输入要求 $t>0$。边界 $t=0,U>0$ 时，四个单占据态全为0能，两个双占据态能量 $U$；低温正则极限为四单占据的等权混合，自旋点积0。若同时 $U=0$，六态全部简并，任意正温 $\rho_2=I_6/6$。不能在这些简并点继续指定“唯一纯 singlet 基态”。

固定 $U>0$，先让 $T\to0$、再让 $t\to0^+$，得到 singlet；先令 $t=0$、再降温则得到四态混合。固定正温让 $t\to0^+$ 时，精确极限仍含热双占据：$Z_2=4+2e^{-\beta U}$、$\langle D\rangle=2e^{-\beta U}/Z_2$、自旋点积0；只有再令 $T\to0$，或采用 $k_BT\ll U$ 的近似，才回到四单占据等权态。这个次序区别来自能隙 $\Delta_{ST}\to0$，不是有限双位点相变。单独基态能量连续不意味着制备的密度矩阵极限与所有条件都可交换。

## 先预测再复算，随后改变 U、跳跃与温度

默认卡有 $t=0.01\,\mathrm{eV}$，$U=0,0.04,0.20\,\mathrm{eV}$ 的比较及 $T=5,30,300\,\mathrm K$ 的不同准备，另有同 $U,T$ 将跳跃减半。先写：$U$ 增大时基态双占据怎样变；固定正温时自旋是否单调趋 singlet；同 $U$ 将 $t$ 减半，对电荷概率和交换隙哪个影响更快。

![[物理/80-实践/43-两位点Hubbard有限温度/assets/spectrum.svg]]

![[物理/80-实践/43-两位点Hubbard有限温度/assets/correlation.svg]]

![[物理/80-实践/43-两位点Hubbard有限温度/assets/thermal.svg]]

复算 [[物理/80-实践/43-两位点Hubbard有限温度/README#复算入口与输出|源码和固定卡]] 后，用 CSV 与本页六态概率同时核；图中的自旋条件态门槛必须携带投影的定义。

**半引导题。** $U/t=4$ 时，精确能隙与 $4t^2/U$ 差多少？改 $U/t=20$ 后，是否只因排斥大就能在 30 K 用纯 singlet 代替热态？

**撤提示题。** 固定 $U=0.04\,\mathrm{eV},T=5\,\mathrm K$，把 $t=0.01$ 改为 $0.005\,\mathrm{eV}$。根据完整谱判断双占据、能隙及条件自旋态，不能只替换一个比例。若研究者只报告 $\langle n_1\rangle=\langle n_2\rangle=1$，这些制备是否被区分？

**反例题。** 构造 $p_S=0.4$ 的上述条件自旋态：负点积是多少，PPT 最小特征值是多少？这证明了哪条判断失效，而没有证明完整四态位置空间的什么结论？检查答案见 [[物理/80-实践/43-两位点Hubbard有限温度/ANSWERS|可核答案]]。

这组精确有限模型解释相互作用带来的双占据代价、混合行列式和低能交换，不代表一般强关联算法、热力学极限、Mott 相变、磁长程序或真实材料参数已验证。返回 [[物理/40-量子力学/19-自由多模Fock占据与量子统计#巨正则：何时才出现 BE 与 FD|自由 FD 因子化条件]] 时，应带回“二次 $H$、能量模式、GC 制备”三个条件；返回14时，应带回低能单占据、$t/U$ 与温度尺度。更广课程范围继续由 [[物理/40-量子力学/00-量子力学-MOC#全课仍要完成的六阶段|课程地图]] 保留。
