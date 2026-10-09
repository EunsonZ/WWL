---
type: lesson
domain: mathematics
stage: 4
aliases:
  - 二次变差与Itô公式
  - OU过程与耦合数值误差
sources:
  - https://www.math.uchicago.edu/~lawler/finbook.pdf
  - https://math.mit.edu/~nsun/s21-18676.html
prerequisites:
  - "[[数学/30-概率与统计/20-随机过程/01-一般条件期望与过滤]]"
  - "[[数学/30-概率与统计/20-随机过程/02-鞅与停止规则的条件]]"
  - "[[数学/16-数学分析/15-收敛定理与Fubini-Tonelli]]"
content_status: usable
evidence_status: partial
---
# Brownian二次变差与Itô公式

把平滑轨迹的平方求导，会得到 $d(x^2)=2x\,dx$。如果轨迹是Brownian运动，这条链式法则少了一项：$d(W_t^2)=2W_t\,dW_t+dt$。额外的 $dt$ 来自许多很小的随机增量平方累积后没有消失。先证明这个量，再定义积分，最后用OU过程把公式、数值路径和误差目标接在一起。

## Brownian模型和本课的证明边界

固定过滤 $(\mathcal F_t)_{t\ge0}$。标准Brownian运动 $W$ 满足：$W_0=0$；样本路径连续；$W_t$ 是 $\mathcal F_t$-可测；对 $s<t$，$W_t-W_s$ 独立于 $\mathcal F_s$ 且为 $N(0,t-s)$。标准单位下 $W$ 的量纲为时间的平方根。过滤若泄露未来，这个独立条件不再成立。

Brownian过程的存在与连续版本的构造是本课的外部输入，见 [Lawler §2.4–2.5](https://www.math.uchicago.edu/~lawler/finbook.pdf)；以下从上述性质出发证明二次变差、简单过程的Itô等距和一个明确光滑范围内的Itô公式。更一般连续半鞅、局部化与SDE存在唯一性不由一张模拟图认证。

## 二次变差：单步平方虽小，总和却留下时间

在固定 $[0,T]$ 上取确定分割 $0=t_0<\cdots<t_m=T$，网格宽 $|\Pi|=\max_i(t_{i+1}-t_i)$。设
$$Q_\Pi=\sum_{i=0}^{m-1}(W_{t_{i+1}}-W_{t_i})^2.$$
独立Gaussian增量给 $EQ_\Pi=T$。若 $Z\sim N(0,v)$，$EZ^4=3v^2$，故 $\operatorname{Var}(Z^2)=2v^2$，于是
$$E|Q_\Pi-T|^2=2\sum_i(\Delta t_i)^2\le2T|\Pi|\longrightarrow0.$$
这证明沿任意网格趋零的确定分割，$Q_\Pi\to T$ 于 $L^2$，从而依概率。沿二分网格 $|\Pi_n|=T2^{-n}$，Chebyshev概率界可求和，由第一Borel–Cantelli引理得 a.s. 收敛。不能把这句话无条件换成“所有事后选取的随机分割同时成立”。

连续且总变差有限的路径 $x$ 则满足
$$\sum_i(\Delta x_i)^2\le\max_i|\Delta x_i|\sum_i|\Delta x_i|\to0.$$
因此Brownian路径在 $T>0$ 上几乎必然不具有有限总变差。这已经解释为什么不能把它当普通光滑函数积分；更强的处处不可微结论需要另证。[Lawler §2.8，定理2.8.2](https://www.math.uchicago.edu/~lawler/finbook.pdf)可核对分割与收敛方式的条件。

## Itô积分从下注前确定的系数开始

简单过程取
$$H_t=\sum_{i=0}^{m-1}H_i1_{(t_i,t_{i+1}]}(t),$$
其中 $H_i$ 是 $\mathcal F_{t_i}$-可测且平方可积。定义
$$I(H)=\int_0^T H_t\,dW_t:=\sum_iH_i\Delta W_i.$$
这是左端可用信息的选择。独立增量使每项均值0；不同项的交叉期望也为0：若 $i<j$，把第 $j$ 项的增量对 $\mathcal F_{t_j}$ 条件平均，前面的乘积与 $H_j$ 已知，增量均值为0。各项平方期望为 $E(H_i^2)\Delta t_i$。各乘积由Cauchy–Schwarz可积；提出无界的过去系数时，可先截断再利用可积收敛通过极限。因此
$$EI(H)=0,\qquad E[I(H)^2]=E\int_0^T H_t^2dt.\tag{1}$$
这就是Itô等距。它既给误差控制，也确保“从更细简单过程取极限”不依赖具体逼近路径。

以范数 $\|H\|_{\mathcal H}^2=E\int_0^T H_t^2dt$ 完备化这些简单过程；若 $H^{(n)}$ 在该范数下趋于 $H$，(1)使 $I(H^{(n)})$ 在 $L^2(P)$ 中Cauchy，定义极限 $I(H)$。等距与均值0保留。将这个闭包识别为所有平方可积可预测过程的空间，涉及相应可预测 $\sigma$-代数与稠密性定理；本课明确使用闭包定义，只证明下面所需的过程确能逼近。

例如 $H_t=W_t$ 的左端阶梯逼近满足
$$E\int_0^T|W_t-W_{t_i(t)}|^2dt\le T|\Pi|,$$
所以 $\int W\,dW$ 已有定义。对有界连续函数 $g(t,x)$，$g(t_i,W_{t_i})\to g(t,W_t)$ 逐路径且有统一界，支配收敛也给所需范数逼近。固定上限的构造见 [Lawler §3.2](https://www.math.uchicago.edu/~lawler/finbook.pdf)；将各时刻积分选成同一连续鞅版本需额外的连续版本定理，本课引用这一标准扩张而不省略为“显然”。

## 先完整算出平方：链式法则丢掉了什么

每个有限分割都有精确代数恒等式
$$W_T^2=2\sum_iW_{t_i}\Delta W_i+Q_\Pi.$$
左端和依等距在 $L^2$ 中趋于Itô积分，二次变差也在 $L^2$ 中趋于 $T$，故
$$W_T^2=2\int_0^T W_t\,dW_t+T.\tag{2}$$
微分记号 $d(W_t^2)=2W_t\,dW_t+dt$ 就是这条积分恒等式。右端取期望给 $EW_T^2=T$，与Gaussian方差一致；若误用普通链式法则，会错误得到期望0。

若改用右端点，有限和满足 $\sum_iW_{t_{i+1}}\Delta W_i=\sum_iW_{t_i}\Delta W_i+Q_\Pi$，极限变成 $(W_T^2+T)/2$。不是程序精度差异，而是积分定义已经改变；右端系数还看到了本步增量。

## 一个有完整余项控制的Itô公式

设 $f\in C^{1,2}([0,T]\times\mathbb R)$，本节额外要求 $f_t,f_x,f_{xx}$ 都有界且一致连续。则对每个固定 $T$，
$$f(T,W_T)-f(0,0)=\int_0^T f_x(t,W_t)dW_t+\int_0^T\left(f_t+\frac12f_{xx}\right)(t,W_t)dt.\tag{3}$$
这些强于必要的条件让每个极限都可在本页检查。证明把每一步先沿空间、后沿时间分开：
$$f(t_{i+1},W_{t_{i+1}})-f(t_i,W_{t_i})=f_x(t_i,W_{t_i})\Delta W_i+\tfrac12f_{xx}(t_i,W_{t_i})(\Delta W_i)^2+f_t(t_i,W_{t_i})\Delta t_i+r_i.$$
空间Taylor余项的总绝对值不超过 $\tfrac12\omega(\max_i|\Delta W_i|)Q_\Pi$，其中 $\omega(\delta)\to0$ 是 $f_{xx}$ 的连续模。时间增量的误差不超过 $T\tilde\omega(|\Pi|+\max_i|\Delta W_i|)$，由 $f_t$ 一致连续得到。路径连续使最大增量趋0，$Q_\Pi$ 依概率有界，所以两份余项都依概率趋0。

一次项按Itô等距趋于第一个积分。二次项写成普通Riemann和加
$$D_\Pi=\sum_i A_i[(\Delta W_i)^2-\Delta t_i],\qquad A_i=f_{xx}(t_i,W_{t_i}).$$
$A_i$ 在增量前已知，中心化增量平方是鞅差；交叉期望为0，故
$$E D_\Pi^2\le2\|f_{xx}\|_\infty^2\sum_i(\Delta t_i)^2\to0.$$
剩下的Riemann和沿每条连续路径趋于 $\int f_{xx}(t,W_t)dt$，时间项同理。有限和两端相等，各项极限唯一，得到(3)。这把“$(dW)^2=dt$”落实为收敛证明；它不是对普通微分符号施加神秘代数。

一般 $C^{1,2}$ 函数可通过停在紧区域、局部化来推广；一般Itô过程 $dX_t=b_tdt+\sigma_t dW_t$ 的公式为
$$df(t,X_t)=\left(f_t+b_tf_x+\tfrac12\sigma_t^2 f_{xx}\right)dt+\sigma_tf_xdW_t.$$
此处取 $b$ 渐进可测、$\sigma$ 可预测，并要求几乎必然在每个有限时间区间上 $\int_0^T(|b_t|+\sigma_t^2)dt<\infty$。这些条件包含时间方向的可测性，不能仅由每个固定时刻的适应性代替。这个一般半鞅版本、局部化及相应积分存在是明确外部定理输入，见 [Lawler §3.3–3.4](https://www.math.uchicago.edu/~lawler/finbook.pdf)；本页完整证明的是上面有界导数的Brownian版本和无需有界导数的平方特例。

## OU过程：把均值回归与持续噪声放在同一式里

固定常数 $\kappa>0,\mu\in\mathbb R,\sigma\ge0$ 与确定初值 $x_0$，模型为
$$dX_t=\kappa(\mu-X_t)dt+\sigma dW_t.$$
若 $X$ 有量纲 $U$，则 $\kappa$ 为时间的倒数、$\sigma$ 为 $U/\sqrt{\text{时间}}$。令 $Z_t=e^{\kappa t}(X_t-\mu)$，确定可微因子与连续Itô过程的乘积规则无二次交叉项，得到 $dZ_t=\sigma e^{\kappa t}dW_t$。这里使用上节声明的一般过程乘积规则，导出的显式候选是
$$X_t=\mu+(x_0-\mu)e^{-\kappa t}+\sigma\int_0^t e^{-\kappa(t-s)}dW_s.\tag{4}$$
确定连续核可由简单过程逼近，积分已包含在(1)的构造中；反向应用乘积规则验证(4)满足SDE。若两个解使用同一Brownian路径与初值，差值满足 $dD_t=-\kappa D_tdt,D_0=0$，故相同，完成本模型的唯一性。

由均值0和等距，
$$EX_t=\mu+(x_0-\mu)e^{-\kappa t},\qquad\operatorname{Var}(X_t)=\frac{\sigma^2}{2\kappa}(1-e^{-2\kappa t}).$$
确定核的Gaussian线性和及其 $L^2$ 极限仍为Gaussian，所以(4)还给完整转移分布。长期分布为 $N(\mu,\sigma^2/(2\kappa))$；若初值直接取这个分布且独立于未来增量，可构造平稳OU，但相邻样本仍相关，协方差随间隔按 $e^{-\kappa h}$ 衰减。它不是状态每一步独立地重抽正态。

## 同一路噪声才能谈强误差

取 $h=T/m$、$a=1-\kappa h$，Euler–Maruyama为
$$X^h_{k+1}-\mu=a(X^h_k-\mu)+\sigma\Delta W_k.$$
强均方根误差是 $\{E|X_T^h-X_T|^2\}^{1/2}$，比较必须在同一Brownian路径下；弱误差指定函数 $g$，比较 $|Eg(X_T^h)-Eg(X_T)|$。两个独立模拟轨迹之间的距离混入了真实随机差异，不是强误差。

对本模型无需把高分辨率Euler当“真值”。每段精确更新可写
$$X_{(k+1)h}-\mu=e^{-\kappa h}(X_{kh}-\mu)+\sigma J_k,$$
其中
$$J_k=\int_{kh}^{(k+1)h}e^{-\kappa((k+1)h-s)}dW_s,\quad v_h=\operatorname{Var}(J_k)=\frac{1-e^{-2\kappa h}}{2\kappa},\quad c_h=\operatorname{Cov}(J_k,\Delta W_k)=\frac{1-e^{-\kappa h}}\kappa.$$
同一路噪声的联合Gaussian采样是
$$\Delta W_k=\sqrt h Z_{k,1},\qquad J_k=\frac{c_h}{h}\Delta W_k+\sqrt{v_h-c_h^2/h}\,Z_{k,2},$$
其中不同段及两个 $Z$ 均独立标准正态。剩余方差非负由Cauchy–Schwarz保证。跨两段合并时 $\Delta W_{2h}=\Delta W_{h,1}+\Delta W_{h,2}$、$J_{2h}=e^{-\kappa h}J_{h,1}+J_{h,2}$；所以可从最细段递归得到各粗网格的同一噪声。只重复使用相同随机种子，却让不同网格消耗不同随机数，并不保证这种耦合。

## 解析矩是实验的独立对照

在 $0<\kappa h<1$ 下，终点Euler的均值与方差为
$$m_h=\mu+(x_0-\mu)a^m,\qquad V_h=\sigma^2h\frac{1-a^{2m}}{1-a^2}.$$
与精确终点的协方差为
$$C_h=\sigma^2c_h\sum_{j=0}^{m-1}(ae^{-\kappa h})^j=\sigma^2c_h\frac{1-(ae^{-\kappa h})^m}{1-ae^{-\kappa h}}.$$
因此同一路径耦合的精确均方误差是
$$E|X_T^h-X_T|^2=(m_h-m_T)^2+V_h+V_T-2C_h.\tag{5}$$
这三个式子可从两种更新的加权增量和分别求均值、方差和交叉矩得到，不依赖程序递推的结果。弱误差取 $g(x)=x$ 与 $x^2$ 时，分别比较 $m_h-m_T$ 和 $(V_h+m_h^2)-(V_T+m_T^2)$；不要把带采样波动的弱误差绝对值拟合成保证阶数。

本例加性噪声的强误差为 $O(h)$：$a^j=e^{-\kappa jh}(1+O(h))$ 在 $jh\le T$ 上一致成立，所以Euler每段噪声核与连续指数核的差为 $O(h)$，等距给噪声误差平方 $O(h^2)$；确定均值误差也为 $O(h)$。上述两种弱矩误差同为 $O(h)$。这不能外推成任意乘性噪声Euler都有强阶1。

可复算输入固定 $\kappa=1,\mu=0,\sigma=1/2,x_0=1,T=1$，取 $h=1/8,1/16,1/32,1/64$；理论均值 $e^{-1}$、方差 $(1-e^{-2})/8$。实验需记录样本数、随机种子、共同最细网格、步长、解析(5)、Monte Carlo强误差及弱矩的标准误。本文给出实验接口与解析对照；实际执行结果由实验页另行记录，有限样本拟合不替代上述证明。

## 从扩散与金融应用返回时检查哪一步

[[数学/70-信号处理与多模态数学/03-高斯噪声扩散Score与ODE-SDE直觉#5. 反向 SDE：逆着噪声时间恢复结构|反向SDE]]需要时间反演、密度与score条件；本课的Itô公式只处理给定方向、给定概率律的过程，不能独自推出反向漂移。[[社会科学/30-金融市场与风险/06-远期衍生品无套利与期权#5. 连续模型与局部敏感度的边界|金融连续模型]]还需可交易资产、复制、自融资与测度选择；真实数据生成律和定价测度不是同一个默认对象。数学链式法则有效，不等于这些应用假设已成立。

## 改条件题与答案

1. 平方增量和为什么不能忽略？2. 改用右端点算 $\int W\,dW$，结果会怎样？3. 精确OU和Euler用了独立噪声，步长趋0但终点距离不消失，是否反驳收敛？

**答案。** 1：每段方差与 $\Delta t$ 同阶，总和趋于 $T$，而非0；这与光滑有限变差路径不同。2：多出二次变差 $T$，极限从 $(W_T^2-T)/2$ 变成 $(W_T^2+T)/2$，已经不是同一个Itô积分。3：不反驳；该距离包含两份独立随机终点的差，没有使用强收敛定义要求的共同噪声。应先固定耦合，再比较(5)；若只研究弱误差，则比较指定函数的期望。
