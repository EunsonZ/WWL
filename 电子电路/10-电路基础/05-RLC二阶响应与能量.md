---
stage: 1
aliases:
  - 二阶电路阻尼与能量交换
sources:
  - https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/resources/6002_l15/
  - https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/16_transint_rlc2/
prerequisites:
  - "[[电子电路/10-电路基础/03-电容电感初值与动态电路]]"
  - "[[电子电路/10-电路基础/04-同一RC从物理到离散实现]]"
---
# RLC 二阶响应与能量

上一课的理想 RC 阶跃从零开始单调上升，Euler 大步长却制造振荡。现在把电感放进真实模型：电压真的可以超过源电压，随后振铃。判断它是物理储能交换还是数值错误，需要查看方程、初值与能量余额，不能只看曲线“像不像稳定”。

高中补桥从“两个状态”进入：电容电压与电感电流都保存过去，导数是变化率，二阶导数是变化率还怎样变化。本科快进从特征根和能量式进入，核对串联拓扑；并联 RLC 的阻尼系数不同。两条入口共同完成初值改变后的迁移题。若需数学回补，读 [[数学/46-数理方程/02-高阶线性常微分方程与方程组#常系数与特征多项式|特征多项式]]，回来把根的单位和电路参数对应起来。

## 两个状态带来二阶方程

本课只取源 u、R、L、C 构成一个**串联回路**，输出为电容电压 v；电流 i 从源正端依次流过 R、L，进入电容正端并返回源负端。R≥0、L>0、C>0，都是常数理想集总元件。KVL 与电容关系给

$$u=Ri+L\dot i+v,\qquad i=C\dot v.$$

消去 i 得

$$LC\ddot v+RC\dot v+v=u.$$

每项单位都是 V，$LC$ 的单位为 $\mathrm s^2$，$RC$ 为 s。方程的二阶不是“电路有两个符号”，而是有两个独立储能状态。也可保留状态向量 $x=(v,i)^T$：

$$\frac d{dt}\begin{pmatrix}v\\i\end{pmatrix}
=\begin{pmatrix}0&1/C\\-1/L&-R/L\end{pmatrix}
\begin{pmatrix}v\\i\end{pmatrix}
+\begin{pmatrix}0\\1/L\end{pmatrix}u.$$

矩阵条目单位并非都相同，因为 v 和 i 具有不同单位；直接把 x 的欧氏范数当焦耳不成立。应使用储能加权量 $\tfrac12Cv^2+\tfrac12Li^2$。需要一般状态表示时，读 [[数学/46-数理方程/02-高阶线性常微分方程与方程组#高阶方程本质上是向量的一阶系统|高阶方程到系统]]，回来检查本页每一行的单位。

在无冲激切换下，$v(0^+)=v_0$、$i(0^+)=i_0$，所以 $\dot v(0^+)=i_0/C$。把 $v_0$ 和 $\dot v_0$ 都误设成零，相当于丢掉可能带来的初始电感电流。

## 特征根怎样决定阻尼

输入固定 U 后，特解 v=U，令 $y=v-U$，得

$$\ddot y+2\alpha\dot y+\omega_0^2y=0,
\quad \alpha=\frac R{2L},\quad\omega_0=\frac1{\sqrt{LC}},\quad
\zeta=\frac\alpha{\omega_0}=\frac R2\sqrt{\frac CL}.$$

$\alpha$ 和 $\omega_0$ 均为 $\mathrm s^{-1}$，$\omega_0$ 按 rad/s 表示，$\zeta$ 无量纲。代 $y=e^{st}$，根为 $s_{1,2}=-\alpha\pm\sqrt{\alpha^2-\omega_0^2}$。MIT 6.002 第 15 讲 PDF 第 6–10 页从 LC 状态到二阶解；MIT 6.071 二阶讲义随后区分串联/并联和三种阻尼。它们作为两种课程组织的参照，本页自行保留带 R 的推导与完整初值。[6.002 讲义](https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/34dd2fd3821b725a8b2191558673296b_6002_l15.pdf)、[6.071 二阶讲义](https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/a929d33896839a7bf1ca2631cd87e711_16_transint_rlc2.pdf)。

若 $0\le\zeta<1$，令 $\omega_d=\sqrt{\omega_0^2-\alpha^2}$，则

$$y=e^{-\alpha t}(A\cos\omega_dt+B\sin\omega_dt),
\quad A=v_0-U,\quad B=\frac{i_0/C+\alpha A}{\omega_d}.$$

若 $\zeta=1$，重根解是 $y=(A+Bt)e^{-\omega_0t}$，$A=v_0-U$、$B=i_0/C+\omega_0A$。若 $\zeta>1$，$y=Ae^{s_1t}+Be^{s_2t}$，常数由 $A+B=v_0-U$、$s_1A+s_2B=i_0/C$ 求出。三种形式都必须再代初值，不能只报“欠阻尼”就得到唯一波形。R=0 时根纯虚，自然响应不衰减；R>0 时自然根实部为负。

## 跟一遍：电容电压为何会超过 1 V

固定 L=10 mH、C=1 μF，$\omega_0=10000$ rad/s，临界电阻 $R_{\rm crit}=2\sqrt{L/C}=200$ Ω。取 R=50 Ω、U=1 V、$v_0=i_0=0$，则 $\alpha=2500\;\mathrm s^{-1}$、$\zeta=0.25$、$\omega_d\approx9682.458$ rad/s。

$$v(t)=1-e^{-2500t}\left[\cos(\omega_dt)+\frac{2500}{\omega_d}\sin(\omega_dt)\right]\;\mathrm V.$$

导数为 $\dot v=e^{-\alpha t}(\omega_0^2/\omega_d)\sin(\omega_dt)$ V/s；首次峰值在 $t_p=\pi/\omega_d\approx0.324462$ ms，峰值 $1+e^{-\alpha\pi/\omega_d}\approx1.444344$ V。在 v=1 V 附近电感电流仍可能为正，仍给电容增加电荷，因而越过终值。到峰值 i=0，电感电流随后的方向改变，使电容开始放电。用“电容电压不能瞬间跳变”否定这段有限时间的上升，是把连续性误读成最大值约束。

![[电子电路/80-实践/01-RC跨层/assets/rlc-response-energy.svg|425]]

上图是同一 L/C、零初值、1 V 阶跃，分别 R=50 Ω（欠阻尼）、200 Ω（临界）、400 Ω（过阻尼）的闭式曲线；下图是**实际总储能**，单位 μJ，包含持续输入源做功。图源同时计算电流并代回 KVL 与能量余额，数据可复算。临界情况下 $v=1-(1+\omega_0t)e^{-\omega_0t}$；过阻尼有一个更慢的根。对这个零初值电容阶跃，在非振铃解中临界响应比过阻尼快；不能扩写成任意初值、任意输出或任意设计目标下的“临界永远最优”。

## 能量是另一个独立检查

真实模型总储能为 $E=\tfrac12Cv^2+\tfrac12Li^2$。用两个状态方程求导：

$$\dot E=Cv\dot v+Li\dot i=vi+i(u-Ri-v)=ui-Ri^2.$$

输入为零时，$\dot E=-Ri^2\le0$，电容与电感可互相交换能量，总量只通过 R 损耗。R=0 时能量恒定，得到 LC 震荡；这不构成“任意有界输入都产生有界输出”的证明，无损网络被共振频率持续激励可以不断积累能量。R>0 的衰减也需要本课的固定无源元件条件；负电阻或主动反馈会改变能量式。

恒定 U 时还可定义相对平衡状态的储能

$$E_{\rm rel}=\tfrac12C(v-U)^2+\tfrac12Li^2,
\qquad \dot E_{\rm rel}=-Ri^2.$$

它与图中的实际 E 不同：实际 E 会因源供能上升、甚至超过最终电容能量；相对 E 始终非增。对欠阻尼峰值，电感能量为零，但电容储能约 $\tfrac12\,\mu\mathrm F\,(1.444344\,\mathrm V)^2\approx1.043065$ μJ，超过最终 0.5 μJ，因为此前源曾供能。只检查“总储能不得超过最终能量”会误判正确响应。

## 撤去假设后的反例

并联 RLC 的 KCL 导致电压自然方程 $\ddot v+(1/RC)\dot v+(1/LC)v=0$，所以 $\alpha=1/(2RC)$，R 增大反而减少阻尼。照搬串联 $R/(2L)$ 会给相反结论。串联 RLC 的输出若取电阻电压，也不是本页的电容低通；端口选择改变传递函数。

即使连续根实部为负，Euler 离散状态的根是 $1+T_ss$，仍须满足 $|1+T_ss|<1$。对欠阻尼根 $s=-\alpha\pm j\omega_d$，平方展开得 $1-2\alpha T_s+\omega_0^2T_s^2<1$，即 $0<T_s<2\alpha/\omega_0^2$。R=50 Ω 的上限为 50 μs；沿用 RC 的 0.25 ms 软件周期会不稳定。这个结果解释数值算法，不改变实体无源 RLC 的阻尼。对 R=0 的纯虚根，前向 Euler 任意正步长都会放大能量，连续 LC 则恒能；这是一份区分物理与数值的直接反例。

## 联合迁移题与等价答案

不看答案先求：把 L 和 C 同时改为 40 mH、4 μF，R=200 Ω，源仍为 1 V，但电容初值 0.5 V、电感初值按本页方向为 5 mA。求阻尼类别、完整电压、t=0 时实际能量变化率，并判断初值是否允许套用零状态阶跃公式。若源随后断开并由理想短路取代，写出可保证的能量结论。

可接受答案：$\omega_0=2500$ rad/s，$\alpha=2500\;\mathrm s^{-1}$，仍为临界阻尼。$A=-0.5$ V、$\dot v_0=i_0/C=1250$ V/s，故 $B=1250+2500(-0.5)=0$，$v=1-0.5e^{-2500t}$ V。实际能量初始变化率 $ui-Ri^2=0.005-200(0.005)^2=0$ W，此刻源供能与电阻耗能相等；相对储能变化率为 −5 mW。初值非零，零状态公式不能直接用。源由短路取代且切换无冲激时保留 v、i，随后 E 非增、R>0 的自然响应趋零。状态空间、重根解或等价的初值 ODE 解都合格；临界响应缺少 t 项并非错误，恰是本题初值选择造成的系数为零。

深化任务可在固定峰值、建立时间和损耗预算下比较 R，明确约束与输出位置；也可把寄生电感加入 U1 的 RC，提出能区分寄生振铃与步长错误的测量/收敛试验。回来检查初值、拓扑和能量边界。当前图只验证 CPU 解析模型，未运行 SPICE、实机、生产测试或真人陌生题。
