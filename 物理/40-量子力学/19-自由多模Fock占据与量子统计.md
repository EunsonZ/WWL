---
title: 自由多模Fock占据与量子统计
aliases:
  - 自由多模量子统计
  - 正则与巨正则占据
stage: 0
sources:
  - https://ocw.mit.edu/courses/8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013/7f26f530bdda5d69c399057bd4b1bd28_MIT8_333F13_Lec22.pdf
  - https://ocw.mit.edu/courses/8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013/97bfdfb93240e2f48984629ad0c037de_MIT8_333F13_Lec23.pdf
prerequisites:
  - "[[物理/40-量子力学/05-谐振子能谱与幅度占据]]"
  - "[[物理/40-量子力学/10-张量积纠缠偏迹与交换对称]]"
---

# 自由多模Fock占据与量子统计

四个模式里放两个相同粒子，为什么不能把每个模式都独立套上 Bose 或 Fermi 平均数？关键在于准备条件：**严格固定总粒子数**会把模式占据约束在一个子空间；与储库交换粒子、只固定平均数的巨正则态，才在自由能量模式中分解。两者即使同有平均粒子数 2，也能有不同的能量占据、数涨落与跨模相关。

本课从交换对称构造占据基，再在同一个有限模式谱上完整比较两种准备。[[物理/40-量子力学/05-谐振子能谱与幅度占据#平均幅与占据分别问了什么|单谐振子的 Fock 与热态]]给过一个梯子的例子；[[物理/40-量子力学/10-张量积纠缠偏迹与交换对称#交换的是全部粒子标签|交换对称]]解释了相同粒子的物理空间。本课把它们接到多模式计数，不把粒子编号当成可独立操作的地址。

## 模式完整后，交换对称怎样变成占据数

取单粒子空间 $\mathcal h=\operatorname{span}\{|a\rangle:a=1,\ldots,M\}$。一个模式是**完整的单粒子态**，包括空间、轨道与必要的内态标签。两个相同能量、不同自旋的态是两个模式；“同一能级”不意味着“同一态”。

固定 $N$ 个相同粒子的空间为

$$
\mathcal H_N^B=\operatorname{Sym}^N\mathcal h,\qquad
\mathcal H_N^F=\wedge^N\mathcal h.
$$

对 boson，占据元组 $\mathbf n=(n_1,\ldots,n_M)$ 满足 $n_a\ge0$、$\sum_a n_a=N$。将含 $n_a$ 个 $|a\rangle$ 的乘积态所有**不同**排列相加，共 $W=N!/\prod_a n_a!$ 项；每项系数 $1/\sqrt W$，得到一个归一化对称态 $|\mathbf n\rangle$。这一个态的统计权重只有一次，不能再乘 $W$。对于 fermion，一个完整模式重复出现时反对称和为零，因此 $n_a\in\{0,1\}$；$N$ 个不同模式的排列带奇偶符号，以 $1/\sqrt{N!}$ 归一化。两种占据基的维数是

$$
 d_N^B=\binom{M+N-1}{N},\qquad d_N^F=\binom MN\quad(0\le N\le M).
$$

Fock 空间把各个 $N$ 扇区直和：$\mathcal F_B=\bigoplus_{N\ge0}\mathcal H_N^B$，$\mathcal F_F=\bigoplus_{N=0}^M\mathcal H_N^F$。**有限模式数不使 boson 的完整 Fock 空间有限维**；但固定 $N$ 的 boson 扇区有限维。fermion 的完整 Fock 维数为 $2^M$。

boson 升降算符在有限占据支撑的公共定义域上满足

$$
 b_a|\mathbf n\rangle=\sqrt{n_a}|\mathbf n-\mathbf e_a\rangle,
 \quad [b_a,b_b^\dagger]=\delta_{ab}I,
 \quad n_a=b_a^\dagger b_a.
$$

fermion 固定模式顺序，用 $|\mathbf n\rangle=(c_1^\dagger)^{n_1}\cdots(c_M^\dagger)^{n_M}|0\rangle$。$c_a$ 除去一个占据时带 $(-1)^{\sum_{b<a}n_b}$，因而 $\{c_a,c_b^\dagger\}=\delta_{ab}I$、$\{c_a,c_b\}=0$。这个顺序约定控制振幅符号；本课的对角占据概率不依赖重排的整体基相位。[[物理/40-量子力学/14-角动量相加与两自旋耦合|两自旋耦合]]及 [[物理/40-量子力学/15-CG变换重耦合与相位约定|CG 基变换]]讨论内态耦合，不能替代相同粒子全部自由度的交换对称。

## 自由的对象，以及热态从哪里来

本课“自由”指没有粒子间相互作用、保持粒子数的二次哈密顿量

$$
 H=\sum_{ab}h_{ab}d_a^\dagger d_b,\qquad h=h^\dagger,
 \quad \hat N=\sum_a d_a^\dagger d_a.
$$

有限单粒子 Hermitian 矩阵 $h$ 可由酉变换对角化，新模式保持 CCR 或 CAR，于是

$$
 H=\sum_a\varepsilon_a\hat n_a,\qquad [H,\hat N]=0.
$$

以下均在这些**能量模式**中讨论独立性；换到一般混合模式，态未必仍具有同样的占据乘积分解。四次相互作用、配对项、材料自洽谱不在模型中。

能量用 eV，$T$ 用 K，$\theta=k_BT$，$\beta=1/\theta$；$k_B=1.380649\times10^{-23}/(1.602176634\times10^{-19})\,\mathrm{eV/K}$。真空能量取零。对谐振子量子可另外加常数真空项；它不会改变固定谱的归一化概率，但不能把原子粒子数与振子激发数不加说明地互换。

热平衡态是**制备假设**：与合适的热浴或粒子储库达到平衡，并以指定的能量、粒子约束描述。闭合自由 $H$ 的酉演化本身不会把任意态变成 Gibbs 态。[[物理/40-量子力学/18-有限环境与约化态退相干#从矩阵恢复相干、布居、能量与纯度|有限环境纯退相干]]保持系统布居，不能用局部相干衰减证明这里的温度或化学势准备已经实现。

## 固定 N：每个占据态一次，模式会相关

令 $\Pi_N$ 投影到合法 $N$ 扇区，正则态为

$$
 \rho_N=\frac{\Pi_Ne^{-\beta H}\Pi_N}{Z_N},\quad
 Z_N=\sum_{\mathbf n:\sum n_a=N}e^{-\beta\sum_a\varepsilon_an_a},\quad
 P_N(\mathbf n)=Z_N^{-1}e^{-\beta E_{\mathbf n}}.
$$

和式限于对应统计的合法元组；没有额外 $N!/\prod n_a!$。这不是区分粒子的 Maxwell–Boltzmann 多项式样本。均值与协方差由完整概率逐项求：

$$
 m_a=\sum_{\mathbf n}P_N(\mathbf n)n_a,\qquad
 C_{ab}=\langle(n_a-m_a)(n_b-m_b)\rangle.
$$

虽然 $H$ 没有相互作用，固定数约束仍给

$$
 \operatorname{Var}(\hat N)=\sum_{ab}C_{ab}=0,\qquad
 \sum_b C_{ab}=\operatorname{Cov}(n_a,N)=0.
$$

因此一个模式的正方差必须由同行的跨模协方差抵消。跨模相关不能直接叫相互作用或强关联的证据，也不能仅凭相关就判定纠缠。这里的热态在占据基中对角。

## 巨正则：何时才出现 BE 与 FD

允许粒子数变化时，

$$
 \rho_{GC}=\Xi^{-1}e^{-\beta(H-\mu\hat N)},\quad
 \Xi=\operatorname{Tr}_{\mathcal F}e^{-\beta(H-\mu\hat N)}.
$$

能量模式的各 $\hat n_a$ 对易，且去掉固定总数约束后各自求和，因此 $P_{GC}(\mathbf n)=\prod_a p_a(n_a)$。

对 boson，记 $q_a=e^{-\beta(\varepsilon_a-\mu)}$。几何级数要求每个 $q_a<1$，即有限模式中 **$\mu<\varepsilon_{\min}$**：

$$
 \Xi_B=\prod_a(1-q_a)^{-1},\quad
 p_a(n)=(1-q_a)q_a^n,\quad
 \langle n_a\rangle=\frac{q_a}{1-q_a}
 =\frac1{e^{\beta(\varepsilon_a-\mu)}-1},
 \quad \operatorname{Var}(n_a)=m_a(1+m_a).
$$

均值由 $q\partial_q\log\sum_nq^n$ 得到，方差由 $(q\partial_q)^2\log\sum_nq^n$ 得到。对 fermion，仅 $n=0,1$：

$$
 \Xi_F=\prod_a(1+e^{-\beta(\varepsilon_a-\mu)}),\quad
 p_a(1)=m_a=\frac1{e^{\beta(\varepsilon_a-\mu)}+1},\quad
 \operatorname{Var}(n_a)=m_a(1-m_a).
$$

两者均有 $C_{ab}=\delta_{ab}\operatorname{Var}(n_a)$、$\operatorname{Var}(N)=\sum_a\operatorname{Var}(n_a)$。BE 增强与 Pauli 排除体现在**每个模式**的分布，不在一个未经说明的“能级只能放一个粒子”的规则里。若能级简并度 $g$，它含 $g$ 个完整模式，fermion 可总共占据 $0,\ldots,g$；独立同分布时该能级总占据为二项分布，均值 $gm$、方差 $gm(1-m)$。

上述固定数约束、巨正则因子化与均值公式分别对应 [MIT 8.333 L22 的占据基计数](https://ocw.mit.edu/courses/8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013/7f26f530bdda5d69c399057bd4b1bd28_MIT8_333F13_Lec22.pdf) 和 [L23 VII.C、印刷 144–145 页](https://ocw.mit.edu/courses/8-333-statistical-mechanics-i-statistical-mechanics-of-particles-fall-2013/97bfdfb93240e2f48984629ad0c037de_MIT8_333F13_Lec23.pdf)。下面的四模式数例与有限截断界在本页独立推出，不用连续气体公式代替它们。

给定 $T>0$ 和目标平均数 $\bar N$，$\partial_\mu\langle N\rangle=\beta\operatorname{Var}(N)>0$。boson 从 $\mu\to-\infty$ 的 0 增至 $\mu\to\varepsilon_{\min}^{-}$ 的无穷，因此任意有限 $\bar N>0$ 有唯一有限根。fermion 从 0 增至 $M$，故只有 $0<\bar N<M$ 有有限根。固定 $N=0$ 或 $N=M$ 的 fermion 正则态完全合法，但匹配其均值只在 $\mu\to\mp\infty$ 极限；实践的**两系综有限根比较入口**拒绝这些端点。

当粒子数本来不守恒并可在平衡中生成消失，如通常的平衡光子、声子，不能把 $\mu$ 当自由调粒子数的旋钮，常用 $\mu=0$；具体模式谱和零频边界仍需另定。本课数例是数守恒粒子的储库模型。

## 四个模式、两个粒子：先预测再算

取模式 $(L_\alpha,L_\beta,U_\alpha,U_\beta)$，能量 $(0,0,\Delta,\Delta)$，$\Delta=0.04\,\mathrm{eV}$。$\alpha,\beta$ 为正交内态；fermion 可解释为两个自旋分量，boson 例只取合法的两种内部或偏振态，不能把基本自旋 $1/2$ 粒子改叫 boson。严格固定 $N=2$；对比同谱、同温、$\langle N\rangle=2$ 的 GC。取 $T=\Delta/(k_B\ln4)=334.8356149173282\,\mathrm K$，故 $q=e^{-\beta\Delta}=1/4$。

**先预测。** 正则 $N$ 图只有一根尖峰，GC 有 $N\ne2$ 的概率。正则跨模协方差不能全为零；GC 能量模式之间为零。升温时上层平均占据增大，但相同平均总数不能保证上层均值一样。只有条件化到恰好 $N=2$，GC 才应恢复完整正则概率。

令 $K=n_{U_\alpha}+n_{U_\beta}$。boson 每层两个模式放 $r$ 粒子有 $r+1$ 种占据，故 $K=0,1,2$ 的态数 $(3,4,3)$；fermion 为 $\binom2K\binom2{2-K}$，态数 $(1,4,1)$。乘上 $q^K$：

| 统计 | $Z_2$ | 正则 $P(K=0,1,2)$ | 正则 $\langle K\rangle$ | 每个下层、上层模式均值 |
|---|---|---|---|---|
| boson | $3+4q+3q^2=67/16$ | $(48,16,3)/67$ | $22/67$ | $56/67,\ 11/67$ |
| fermion | $1+4q+q^2=33/16$ | $(16,16,1)/33$ | $6/11$ | $8/11,\ 3/11$ |

总态数分别 10 和 6。表里的简并计数来自**不同占据态**合并，不能对每一个占据态再乘排列数。

匹配平均总数的 GC fermion 由谱对称得 $\mu=\Delta/2=0.02\,\mathrm{eV}$，每个下层模式 $m_L=2/3$、上层 $m_U=1/3$，$\langle K\rangle=2/3$，$\operatorname{Var}(N)=8/9$。GC boson 令 $z=e^{\beta\mu}$，

$$
 \frac{2z}{1-z}+\frac{2qz}{1-qz}=2
 \ \Rightarrow\ z=\frac{5-\sqrt{13}}3,
 \quad \mu=-0.0221053522983\,\mathrm{eV}.
$$

其每模式 $m_L\approx0.8685170918213$、$m_U\approx0.1314829081787$，$\langle K\rangle\approx0.2629658163573$，$\operatorname{Var}(N)\approx3.543219387858$。GC 和正则甚至单模式均值也有差别；这不是算法误差，而是有限系统中不同约束的后果。

但对恰好 $N$ 条件化，

$$
 P_{GC}(\mathbf n\mid\sum n_a=N)
 =\frac{e^{-\beta E_{\mathbf n}}e^{\beta\mu N}}
 {\sum_{\sum n=N}e^{-\beta E_{\mathbf n}}e^{\beta\mu N}}
 =P_N(\mathbf n).
$$

这是同 $H,T$ 的**完整概率恒等式**；仅匹配一阶均值没有这个保证。图与 CSV 的入口在 [[物理/80-实践/41-自由多模量子统计/README#复算入口与输出|复算实践]]。

![[物理/80-实践/41-自由多模量子统计/assets/number.svg]]

![[物理/80-实践/41-自由多模量子统计/assets/covariance.svg]]

## Bose 数截断：画完尾巴之前，先说明换了什么对象

本课不把每个 boson 梯子截成有限矩阵后称精确 CCR。如果单模保留 $n=0,\ldots,J$，截断算符满足

$$
 [b_J,b_J^\dagger]=I-(J+1)|J\rangle\langle J|.
$$

其迹为零；任何有限维矩阵的交换子迹都为零，因此不能精确等于迹为 $J+1$ 的 $I$。固定 $N$ 扇区也不在单个 $b_a$ 的作用下封闭：它把态送到另一个数扇区。枚举固定 $N$ 的合法概率无需假装这些有限矩阵满足完整 CCR。

实践的 GC 均值和方差来自**无截断解析分布**；仅展示总粒子数 $S=\sum_an_a\le C$ 的概率。独立模式卷积可精确求这个范围的 $P(S=s)$，不必枚举 $(C+1)^M$ 个多模盒子。令

$$
 W=\sum_{s=0}^CP(s),\quad \delta=1-W,
 \quad R_j=\sum_{s=0}^Cs^jP(s)\ (j=1,2).
$$

丢弃的一二阶数矩为 $\langle S\rangle-R_1$、$\langle S^2\rangle-R_2$。小概率尾可以携带更显著的二阶矩，不能仅报归一化近似 1。若将剩余概率重归一化为 $P(s)/W$，对象已变为 **GC 条件在 $S\le C$ 的态**，其均值 $R_1/W$、方差 $R_2/W-(R_1/W)^2$；它与前节恰好固定 $N$ 的条件化不同。

另给可检查的上界。取 $\ell=\lfloor C/M\rfloor+1$；$S>C$ 时至少一个 $n_a\ge\ell$。几何分布的无记忆性给 $P(n_a\ge\ell)=q_a^\ell$，且在此事件下 $S$ 的分布是原来的 $S+\ell$。用非负随机变量的联合界，令 $A=\sum_aq_a^\ell$：

$$
 \delta\le A,\quad
 \mathbb E[S\,1_{S>C}]\le(\ell+\mathbb E S)A,\quad
 \mathbb E[S^2\,1_{S>C}]
 \le\big[\operatorname{Var}(S)+(\mathbb ES+\ell)^2\big]A.
$$

界可宽松甚至大于 1，不是尾概率等式。默认 $C=16$ 的 boson 基准丢弃质量约 $2.98526\times10^{-5}$，但丢弃二阶矩约 $9.68230\times10^{-3}$；图里重归一化曲线接近原曲线不能证明涨落完全相同。浮点卷积末端会有微小舍入残差，JSON 同时保留未夹零的残差与解析界；这不是对物理上负尾质量的许可。fermion 总数支撑 $0,\ldots,M$ 全部枚举，尾严格为零。

## 改变条件，检验哪条解释能迁移

![[物理/80-实践/41-自由多模量子统计/assets/thermal.svg]]

温度图保持每例的谱与目标 $N$，每个温度重新匹配 GC 的 $\mu$。正则曲线始终 $\operatorname{Var}(N)=0$；GC 的数涨落不能因为拟合平均数就消失。默认另含同温能隙加倍、同谱 $N=3$，完整输入、概率与答案见 [[物理/80-实践/41-自由多模量子统计/ANSWERS#改变温度能隙与粒子数|迁移题答案]]。

**半引导题。** 同温将 $\Delta$ 加倍，$q$ 从 $1/4$ 变为 $1/16$。先在表的多项式中替换 $q$，预测上层占据；再比较 GC 拟合均值后的上层占据。两者是否因此成为同一态？

**撤提示题。** 将目标改为 $N=3$，或将四模式 fermion 固定为 $N=4$。哪种有有限 GC 化学势根？为何拒绝后一个比较不意味着其正则态不存在？若给每个能级两个内态，哪个约束作用于能级总数、哪个作用于单个完整模式？

**反例题。** 两个制备都平均有两个粒子，观测到的总数方差分别 0 和 $8/9$；能否把差别叫相互作用？若只看总数均值，遗漏了哪些可测条件？若 $\rho_N$ 是对角混态，交换反对称是否足以把它叫 Bell 纠缠？

本模型只有有限个给定模式及理想平衡制备，没有热力学极限、相变或真实材料谱认证。要讨论 Bose 凝聚，需另外给出模式数、体积与粒子数的极限和低能谱；一个有限 GC 模式均值变大不是这套条件的替代。

## 返回态密度与半导体占据时，带走哪一个量

[[物理/50-半导体物理/02-带边有效质量与一二三维态密度#先数 k 格点，再改变变量|态密度]]先数完整单粒子态，含已声明的自旋与谷简并；再乘本课 FD 的**单模式平均占据**，得到 $\sum_af(\varepsilon_a)$，连续极限才写为 $\int g(E)f(E)\,dE$。若 $g(E)$ 已含两自旋，不再额外乘 2。这个接口只需要均值，不说明完整多体态或总数分布。

[[物理/50-半导体物理/03-温度占据电中性与杂质电离#化学势不能与掺杂浓度各自指定|化学势与电中性]]通过带谱、载流子与杂质电荷求共同的 $E_F$，不是在本课四个模式中硬指定 $\langle N\rangle$ 的同一道根问题。杂质电离权重还含特定电荷构型的简并比，不能把它们当自由电子完整模式的同一种 Pauli 计数。返回半导体页时，用本课解释 FD 的来源与每态占据边界；DOS 积分、杂质模型及真实材料条件由其主解释负责。
