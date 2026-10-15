---
stage: 0
aliases: []
prerequisites:
  - "[[物理/50-半导体物理/09-三维晶格倒格子与紧束缚]]"
  - "[[物理/50-半导体物理/04-弛豫时间Hall符号与可辨识测量]]"
sources:
  - "https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/333aadd4c8c3174f76ef6819f846ddc1_lecture_8c.pdf"
  - "https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/5b96b61fa8e79d9c426d1b331c023af7_lecture_27b.pdf"
  - "https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/ab1f8e1036e814ac14c58209bc275ca5_lecture_28c.pdf"
---

# 声子、微观散射、Boltzmann 与 Hall 因子

## 为什么固定离子的能带不能独自决定迁移率

第 09 课的固定晶格给色散、群速度和曲率；第 04 课说明电导还需要动量弛豫，并保留了 $\tau_m$ 的微观缺口。现在让离子振动：键长改变 → 周期势扰动 → 电子在允许态之间转移 → 非平衡方向分布衰减。目标是在一张明确的教学模型中，从弹性和耦合参数推 $\tau(E,T)$、漂移迁移率及 Hall 因子，检查何时第 04 课的 $r_H=1$ 失效。

这条链包含几个层次的近似：谐振晶格、小扰动的量子转移率、准粒子/半经典输运、低场线性响应。下面逐个给条件；声子谱、散射时间与电子空穴复合寿命是不同对象，后者仍由第 05、06 课维护。

## 一条链的动力学完整求到谱

先取周期单原子链：$N$ 个质量 $M$ 的原子，间距 $a$，仅纵向位移 $u_l$；小位移的势能

$$U=\frac K2\sum_{l=0}^{N-1}(u_{l+1}-u_l)^2,\qquad u_N=u_0.$$

$u,a$ 用 m，$K>0$ 用 N/m=$\mathrm{kg/s^2}$，$M$ 用 kg。由 $M\ddot u_l=-\partial U/\partial u_l$ 得

$$M\ddot u_l=K(u_{l+1}+u_{l-1}-2u_l).$$

令 $u_l(t)=A e^{i(qla-\omega t)}$，取实部才是实际位移；周期边界给 $q=2\pi j/(Na)$，折回 $[-\pi/a,\pi/a)$。代入后

$$\omega^2(q)=\frac{4K}{M}\sin^2\frac{qa}{2},\qquad
\omega(q)=2\sqrt{K/M}\left|\sin\frac{qa}{2}\right|.$$

$\omega$ 是角频率 $\mathrm{rad/s}$，普通频率是 $\nu=\omega/(2\pi)$（Hz）。长波 $|qa|\ll1$ 时 $\omega\approx c_s|q|$，$c_s=a\sqrt{K/M}$ 为 m/s；区边群速度 $d\omega/dq$ 为零。$q=0$ 是所有原子同向移动，键长不变，故 $\omega=0$。这是平移自由度，不能将它代入有限频率谐振子的 $1/\sqrt\omega$ 归一并报告无穷振幅；固定质心或单独处理自由质心。自由周期链有 $N$ 个实正常坐标，其中一个是零模、其余 $N-1$ 为非零频率振动自由度。不同 $q$ 的简并不是多出原子。

完整链卡：$a=0.50$ nm、$M=5.0\times10^{-26}$ kg、$K=20$ N/m、$N=32$。得到 $c_s=10^4$ m/s、区边 $\omega=4.0\times10^{13}$ rad/s（约 6.366 THz），$q=0$ 必须严格零。它是教学弹簧链，没有硅的三维纵横声学或光学分支。

![[物理/80-实践/07-晶格声子与微观输运/assets/phonon-chain.svg]]

横轴 $qa/\pi$，纵轴 $\omega/(10^{12}\,\mathrm{rad/s})$，实线是离散链，虚线 $c_s|q|$ 只在长波有效；曲线可连续画，32 格卡的实际波矢仍离散。图的声速不是后面三维形变势卡指定的声速，两种模型不拼成真实材料。

三维每原胞 $s$ 原子有 $3s$ 个位移分量。以二阶力常数 $\Phi_{\alpha i,\beta j}(\mathbf R)$（N/m）展开势能，胞相位约定下的质量加权动力学矩阵为

$$D_{\alpha i,\beta j}(\mathbf q)=\frac1{\sqrt{M_\alpha M_\beta}}
\sum_{\mathbf R}\Phi_{\alpha i,\beta j}(\mathbf R)e^{i\mathbf q\cdot\mathbf R},\qquad D e_\lambda=\omega_\lambda^2 e_\lambda.$$

$D$ 单位 $\mathrm{s^{-2}}$；自伴性来自力常数的交换对称。均匀平移不改势能给声学求和规则 $\sum_{\mathbf R,\beta}\Phi_{\alpha i,\beta j}(\mathbf R)=0$。稳定、无外部钉扎的三维晶体在 $\mathbf q=0$ 有三条平移零模；其余通常是光学分支。负的 $\omega^2$ 表示该平衡结构在谐近似下不稳定或输入/约束有误，不能用绝对值悄悄修成稳定谱。仅有正本征值也未检查非谐温度效应。

## 从位移模式到电子转移矩阵元

对每个非零频率模式作谐振量子化，单模能级间隔 $\hbar\omega_{\mathbf q\lambda}$；声子是振动模式的能量量子，不是额外原子。平衡占据为 Bose 因子

$$N_{\mathbf q\lambda}=\frac1{\exp(\hbar\omega_{\mathbf q\lambda}/k_BT)-1}.$$

为得到可算的代表速率，另取三维各向同性单谷抛物电子带 $\varepsilon_{\mathbf k}=\hbar^2k^2/(2m^*)$、体积 $V$、密度 $\rho$；保留一支长波纵声学模式 $\omega_q=c_s q$。设电子带边只响应体积应变，形变势为 $D_A$（J）：

$$\delta V(\mathbf r)=D_A\nabla\cdot\mathbf u(\mathbf r),\qquad
\mathbf u(\mathbf r)=\sum_{\mathbf q\ne0}\sqrt{\frac{\hbar}{2\rho V\omega_q}}\hat{\mathbf q}
\left(a_{\mathbf q}e^{i\mathbf q\cdot\mathbf r}+a_{\mathbf q}^\dagger e^{-i\mathbf q\cdot\mathbf r}\right).$$

这里对所有非零 $\mathbf q$ 求和，$\mathbf u$ 自伴；选极化方向的相位可以改变矩阵元相位，不改变下面的模平方。前因子单位 m。对归一电子包络 $V^{-1/2}e^{i\mathbf k\cdot\mathbf r}$ 积分，导数提供 $q$，因此不含声子数的耦合幅值

$$|g_q|^2=D_A^2\frac{\hbar q}{2\rho V c_s},\qquad [g_q]=\mathrm J.$$

吸收的矩阵元平方乘 $N_q$，发射乘 $N_q+1$；即使 $T=0$ 没有热声子，满足能量和空态条件的电子仍可自发发射。均匀平移 $q=0$ 不产生体积应变，不能让零模贡献这个耦合。真实带边也可响应剪切、各向异性、谷间或光学位移；这张标量 LA 卡没有把这些机制归零为材料事实。

一般一阶振幅、有限时间sinc核到能量壳及DOS的条件由 [[物理/40-量子力学/17-含时微扰与黄金律的时间窗口#终态求和怎样产生能量壳和二倍圆周率|量子17的黄金律主解释]] 给出。本课将电子和声子数态合为初/终态，携带低总转移概率、密允许终态与长于相关时间且早于耗尽/有限回返的窗口，再用 $(2\pi/\hbar)|M_{fi}|^2\delta(E_f-E_i)$ 作待终态积分的核；吸收/发射的总能量差和占据因子继续由下式声明。窄带、阈值或极短开关时返回 [[物理/40-量子力学/17-含时微扰与黄金律的时间窗口#长时间是相对于相关时间，短时间是相对于耗尽和复现|一般时间窗]] 核有限时间积分；这里不由有限两态推出不可逆常率。

于是吸收与发射的态间速率分别是

$$W^{\rm abs}_{\mathbf k\to\mathbf k'}=\frac{2\pi}{\hbar}|g_q|^2N_q
\delta(\varepsilon_{\mathbf k'}-\varepsilon_{\mathbf k}-\hbar\omega_q),$$

$$W^{\rm em}_{\mathbf k\to\mathbf k'}=\frac{2\pi}{\hbar}|g_q|^2(N_q+1)
\delta(\varepsilon_{\mathbf k'}-\varepsilon_{\mathbf k}+\hbar\omega_q).$$

吸收有 $\mathbf k'=\mathbf k+\mathbf q+\mathbf G$，发射有 $\mathbf k'=\mathbf k-\mathbf q+\mathbf G$；$\mathbf G$ 是倒格矢。$\delta(E)$ 单位 $\mathrm{J^{-1}}$，所以积分/终态求和后为 $\mathrm{s^{-1}}$。本例保留 $\mathbf G=0$ 的带内长波散射；晶体动量只守恒到倒格矢，不能把 $\hbar\mathbf k$ 当电子自由机械动量在所有晶体过程严格守恒。低密度时终态近乎空，简并时还须 Pauli 阻塞。

## Boltzmann 近似保留的是分布的收支

半经典分布 $f(\mathbf r,\mathbf k,t)$ 是每个态的占据，$0\le f\le1$。准粒子寿命足够长、空间/外场在晶胞尺度缓变、碰撞相关时间短于宏观变化时，写

$$\partial_t f+\mathbf v\cdot\nabla_{\mathbf r}f+
\dot{\mathbf k}\cdot\nabla_{\mathbf k}f=C[f],\qquad
\hbar\dot{\mathbf k}=-q(\mathbf E+\mathbf v\times\mathbf B),\quad q>0.$$

碰撞项为

$$C[f]_{\mathbf k}=\sum_{\mathbf k'}\left[
W_{\mathbf k'\to\mathbf k}f_{\mathbf k'}(1-f_{\mathbf k})-
W_{\mathbf k\to\mathbf k'}f_{\mathbf k}(1-f_{\mathbf k'})\right].$$

交换求和指标即见 $\sum_{\mathbf k}C[f]_{\mathbf k}=0$：声子散射改变方向/能量，保留电子数；它不能代替 SRH 复合。热声子浴中的吸收/发射与 FD 分布满足详细平衡，平衡净碰撞项为零，而每秒仍有转移。强非热声子、高场加热、相干弹道或带间强混合时，要扩大分布/碰撞或量子输运对象。

对弹性、旋转对称的单能壳，方向的一阶球谐扰动是电流模式。将增益和损失都线性化，便出现

$$\tau_s^{-1}(\varepsilon)=\sum_{\mathbf k'}W_{\mathbf k\to\mathbf k'},\qquad
\tau_{\rm tr}^{-1}(\varepsilon)=\sum_{\mathbf k'}W_{\mathbf k\to\mathbf k'}(1-\cos\theta).$$

$\tau_s$ 是低密度准粒子出态寿命，$\tau_{\rm tr}$ 是电流模式的动量/输运寿命；第 04 课的角度权重由此接入。一般非弹性问题会耦合不同能量，不能无条件用 $(1-\cos\theta)$ 乘出一个局部 $\tau(E)$。

## 一种机制真正算出速率：LA 形变势

同时满足 $\hbar c_s q\ll k_BT$（相关模式近似等分配）、$\hbar c_s q\ll\varepsilon$（电子近似准弹性）、长波与弱耦合时，$N_q\approx k_BT/(\hbar c_s q)$。吸收加发射且忽略小声子能量后，

$$|g_q|^2(2N_q+1)\approx\frac{D_A^2k_BT}{\rho Vc_s^2}.$$

此近似矩阵元不依赖散射角，$\langle\cos\theta\rangle=0$，所以 **这张卡才有** $\tau_s=\tau_{\rm tr}$。散射保持自旋；一个初始自旋只能到同自旋的终态，因此用每自旋、单谷 DOS

$$g_1(\varepsilon)=\frac1{4\pi^2}\left(\frac{2m^*}{\hbar^2}\right)^{3/2}\sqrt\varepsilon.$$

以 $\sum_{\mathbf k'}\to V\int d^3k'/(2\pi)^3$，体积抵消，得到

$$\boxed{\frac1{\tau(\varepsilon,T)}=
\frac{2\pi}{\hbar}\frac{D_A^2k_BT}{\rho c_s^2}g_1(\varepsilon)
=\frac{D_A^2k_BT(2m^*)^{3/2}\sqrt\varepsilon}{2\pi\rho c_s^2\hbar^4}.}$$

其中 $D_A^2k_BT/(\rho c_s^2)$ 单位 $\mathrm{J^2m^3}$，乘 $g_1$ 为 J，再除 $\hbar$ 才是 $\mathrm{s^{-1}}$。态数和电导中的两自旋因子照常保留；散射率中误用含双自旋 DOS 会把本例速率多算两倍。

这给 $\tau\propto T^{-1}\varepsilon^{-1/2}$，不是输入固定经验 $\tau$。极低能量处准弹性条件失效，$\tau$ 的发散不能当材料零能电子真的无限寿命；后面的热积分将其作为近似模型的可积延拓，现实低温必须回到非弹性核/占据而非无限套用温度幂律。

## 从能量依赖寿命推迁移率与 Hall 因子

取均匀低场、各向同性单抛物带。记 $f_0'=\partial f_0/\partial\varepsilon<0$。线性 Boltzmann 解在 $B=0$ 为 $\delta f=q\tau(\varepsilon)\mathbf E\cdot\mathbf v f_0'$；电流 $\mathbf J=-qg_s\int\mathbf v\delta f\,d^3k/(2\pi)^3$。方向平均 $v_x^2=v^2/3=2\varepsilon/(3m^*)$ 给

$$\sigma=\frac{2q^2}{3m^*}\int_0^\infty\varepsilon g(\varepsilon)\tau(\varepsilon)(-f_0')d\varepsilon,
\qquad n=\int_0^\infty g(\varepsilon)f_0d\varepsilon,$$

$g=g_sg_1$。分部积分和 $g\propto\sqrt\varepsilon$ 得 $\int\varepsilon g(-f_0')d\varepsilon=3n/2$；边界项需为零。定义归一电流权重

$$\langle A\rangle_w=\frac{\int\varepsilon g(\varepsilon)(-f_0')A(\varepsilon)d\varepsilon}{3n/2},\qquad
\mu=\frac{\sigma}{qn}=\frac q{m^*}\langle\tau\rangle_w.$$

磁场 $B_z$ 在每个能量壳旋转一阶方向扰动；一次碰撞前转角为 $qB_z\tau/m^*$。对这个小参数展开到一阶，保留第 04 课的电子负号，得到

$$J_x=\frac{nq^2}{m^*}\langle\tau\rangle_w E_x+O(B^2),\qquad
J_y=\frac{nq^2}{m^*}\langle\tau\rangle_w E_y+
\frac{nq^3B_z}{(m^*)^2}\langle\tau^2\rangle_w E_x+O(B^2).$$

横向开路 $J_y=0$，遂有

$$R_H=\frac{E_y}{J_xB_z}=-\frac{r_H}{qn},\qquad
r_H=\frac{\langle\tau^2\rangle_w}{\langle\tau\rangle_w^2}\ge1,\qquad
\mu_H=|R_H|\sigma=r_H\mu.$$

不等式只对这个归一正权重、标量各向同性单带近似来自方差非负，不是所有真实材料 Hall 因子的下界。这里 $R_H$ 是 $B\to0$ 的经典弱场系数；若 $\tau$ 在尾端很大，对有限磁场还须检查贡献积分的能量区，不能仅用某一个平均 $\mu B$ 保证每态弱场。零温简并窄能窗可使平滑 $\tau(E)$ 的 $r_H\to1$，与非简并热分布不同。

非简并 MB 分布的权重 $w(\varepsilon)\propto\varepsilon^{3/2}e^{-\varepsilon/k_BT}$。若 $\tau=C\varepsilon^r$，以 $u=\varepsilon/k_BT$ 积分，

$$\langle\tau^j\rangle_w=C^j(k_BT)^{jr}\frac{\Gamma(5/2+jr)}{\Gamma(5/2)},\qquad
r_H=\frac{\Gamma(5/2)\Gamma(5/2+2r)}{\Gamma(5/2+r)^2}.$$

积分要求相关 Gamma 参数为正，且所用幂律在热权重能区适用。LA 模型 $r=-1/2$，于是

$$\mu=\frac q{m^*}\frac{\tau(k_BT,T)}{\Gamma(5/2)},\qquad
\mu\propto T^{-3/2},\qquad r_H=\frac{3\pi}8\approx1.17810.$$

这次 $T^{-3/2}$ 是由这张等分配、准弹性、MB 单带卡推得；第 04 课为了隔离浓度变化另指定的相同指数，不因此成为同一材料认证。$n_H=n/r_H\approx0.84883n$，$\mu_H\approx1.17810\mu$，直接按 $r_H=1$ 反推会有模型偏差。

## 完整有限卡，数值图与适用尺度一起交付

三维 LA 教学卡取 $m^*=0.20m_0$、$D_A=5.0$ eV、$\rho=5000\,\mathrm{kg/m^3}$、$c_s=5000$ m/s、$n=10^{21}\,\mathrm{m^{-3}}$、$T=150,300,600$ K；固定参数以隔离机制，不调用真实材料数据库。取长波截止 $q_D=2\pi/(1\,\mathrm{nm})$，同为教学输入。

在 $\varepsilon=k_BT$ 的电子壳上 $k=\sqrt{2m^*k_BT}/\hbar$；准弹性散射的最大转移 $q\le2k$。实践同时报告 $\hbar c_s(2k)/(k_BT)$ 与 $2k/q_D$，用它们判断等分配/准弹性与长波是否合理，而不是只报告一条平滑迁移率曲线。这些指标在一个代表能量处检查，不能证明整个热尾都无误；想量化真实误差需以完整非弹性核和具体色散比较。

| T（K） | $\tau(k_BT)$（ps） | 漂移 $\mu$（$\mathrm{m^2/(V\,s)}$） | $\hbar c_s2k/(k_BT)$ | $2k/q_D$ |
| --- | --- | --- | --- | --- |
| 150 | 7.30211 | 4.83063 | 0.13264 | 0.08292 |
| 300 | 2.58169 | 1.70789 | 0.09379 | 0.11726 |
| 600 | 0.912764 | 0.603829 | 0.06632 | 0.16583 |

这张弱散射卡在 300 K 给 $1/\tau(k_BT)=3.87344\times10^{11}\,\mathrm{s^{-1}}$，$R_H=-7.35310\times10^{-3}\,\mathrm{m^3/C}$；$\mu$ 较大反映只保留一种弱散射机制，不能当真实样品的预测。代表声子能量比约 0.094 支持近似的量级判断，并非 1% 误差保证。

![[物理/80-实践/07-晶格声子与微观输运/assets/mobility.svg]]

横轴 K，纵轴 $\mathrm{m^2/(V\,s)}$；实线漂移 $\mu$，虚线 $\mu_H$。同版 JSON 保留 $\tau(k_BT),1/\tau,r_H,R_H$ 和上述两个无量纲指标；固定 $n$ 的 $R_H$ 不随 T 变，而 $\sigma=qn\mu$ 随 T 变。固定 n 是本节实验设计，未重新求第 03 课的掺杂中性根。数值求积另以截断 $u\le40$、偶数区间积分核 Gamma 权重；离散收敛与截断误差属于数值层，不能遮住准弹性模型误差。

## 小角散射为何不能用同一种寿命

给一个具体对照机制：静止、稀疏、独立随机离化杂质，密度 $n_I$，线性屏蔽势的 Fourier 变换

$$U(Q)=\frac{Ze^2}{\epsilon_0\epsilon_r(Q^2+q_s^2)},\qquad [U]=\mathrm{J\,m^3}.$$

这里 $e=q>0$，$Z$ 为带符号电荷数但速率含 $Z^2$，$Q=|\mathbf k'-\mathbf k|$；$q_s>0$ 是给定的屏蔽波数，真实材料须与占据/介电模型一致求它。随机位置平均消去不同杂质的相干交叉项，低密度出态核 $W=(2\pi/\hbar)(n_I/V)|U(Q)|^2\delta(\varepsilon'-\varepsilon)$。Born 弱势、弹性单谷、抛物带近似下，令 $u=\cos\theta$、$Q^2=2k^2(1-u)$：

$$\frac1{\tau_s}=A_k\int_{-1}^1\frac{du}{[2k^2(1-u)+q_s^2]^2},\quad
\frac1{\tau_{\rm tr}}=A_k\int_{-1}^1\frac{(1-u)du}{[2k^2(1-u)+q_s^2]^2},$$

$$A_k=\frac{n_I m^* k}{2\pi\hbar^3}\left(\frac{Ze^2}{\epsilon_0\epsilon_r}\right)^2.$$

换元 $y=2k^2(1-u)+q_s^2$，上下限 $q_s^2,q_s^2+4k^2$，分别得到

$$\tau_s^{-1}=\frac{A_k}{2k^2}\left[\frac1{q_s^2}-\frac1{q_s^2+4k^2}\right],$$

$$\tau_{\rm tr}^{-1}=\frac{A_k}{4k^4}\left[\ln\left(1+\frac{4k^2}{q_s^2}\right)-\frac{4k^2}{q_s^2+4k^2}\right].$$

弱屏蔽 $q_s/k\ll1$ 时前向散射使 $\tau_{\rm tr}$ 远长于 $\tau_s$；强屏蔽 $q_s/k\gg1$ 时角核趋常数、两者之比趋 1。实践只给 $q_s/k=0.2,1,4$ 的**无量纲寿命比**，没有指定真实杂质卡或宣称低温实际迁移率。$q_s$ 随 n/T 变，不能把对数因子当永远固定并给普适 $T^{3/2}$。很强的杂质势、局域化、相关位置或非线性屏蔽也会破坏这个核。

上述三个无量纲输入分别给 $\tau_{\rm tr}/\tau_s\approx13.6565,1.97668,1.08021$；同一低密度角核中，短出态寿命与较长电流衰减时间可以同时成立。

独立机制若都在同一弹性一阶角模式下作用，可先相加 $1/\tau_{\rm tr}(E)$（Matthiessen 近似），**再**做电流/Hall 能量平均。一般 $\langle1/(\gamma_1+\gamma_2)\rangle$ 不等于从两个平均迁移率简单组合；非弹性、相干或互相改变屏蔽时还不能先机械相加。

## 撤去提示后还能选择模型吗

**半引导题。** LA 卡保持 n 和全部材料参数，将 T 从 300 K 加倍。预测 $\tau(k_BT)$、$\mu,\mu_H,R_H$；如果 $D_A$ 翻倍又怎样？

> [!question]- 解释性答案
> 温度加倍使代表能量也加倍，速率因 $T\sqrt\varepsilon$ 增为 $2^{3/2}$ 倍，$\tau$ 和两种迁移率降为 $2^{-3/2}$；$r_H$ 与固定 n 的 $R_H$ 不变。$D_A$ 翻倍则速率四倍、迁移率四分之一，Hall 因子仍不变。若同时发生杂质电离或本征激发，要先重新求 n/p，固定 n 的结论不能照搬。

**撤提示题。** 低温样品的谱线给很短出态寿命，却有很高漂移迁移率；升温后有人从 Hall 直接报 n，随后把迁移率幂律拟合得很好作为 LA 唯一机制的证据。还有人把链的 $q=0$ 代入 Bose 因子加进散射率，得出零模主导电阻。分别重建哪条链？

> [!question]- 解释性答案
> 先区分 $\tau_s$ 与 $\tau_{\rm tr}$ 并核小角核，谱线与电流可有不同权重。Hall 需单带、弱场、各向同性及 $r_H$；未知机制还影响 rH，不能直接报真实 n。幂律相同不足以唯一识别机制，需温区/占据/屏蔽、耦合参数、独立观测及误差比较。零模是刚体平移、应变为零，既非有限频率声子 oscillator，也不提供此形变势散射；先检查声学求和规则和耦合算子。

回 [[物理/50-半导体物理/04-弛豫时间Hall符号与可辨识测量#Hall 因子与双载流子会改变反推量|Hall 反推边界]]，携带本节具体 $r_H=3\pi/8$ 和屏蔽角核；回 [[电子电路/22-半导体与真实元件/01-能带载流子掺杂与输运#电场和浓度梯度，两种不同的推动|漂移扩散]] 时携带局部热化、低场和非简并条件；复算见 [[物理/80-实践/07-晶格声子与微观输运/README#声子到电流的独立检查|声子与微观输运接口]]。这给出微观输运的代表完整链，未完成一般多谷磁输运、光学/谷间非弹性机制或实际工艺校准。

本课推导对应 [MIT 6.730 L8](https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/333aadd4c8c3174f76ef6819f846ddc1_lecture_8c.pdf) 的谐矩阵/长波，[L27](https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/5b96b61fa8e79d9c426d1b331c023af7_lecture_27b.pdf) 的弱转移/占据收支，[L28](https://ocw.mit.edu/courses/6-730-physics-for-solid-state-applications-spring-2003/ab1f8e1036e814ac14c58209bc275ca5_lecture_28c.pdf) 的 LA 形变势/能量动量条件。Hall 热权重和屏蔽角积分在本页逐步给出，不把原讲义的真实硅例参数移植到教学卡。独立语义、数值与真实显示分别验收。
