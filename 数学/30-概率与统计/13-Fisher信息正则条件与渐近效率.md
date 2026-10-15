---
type: lesson
domain: mathematics
stage: 3
aliases:
  - 信息下界为何需要正则条件
  - MLE的相合性与渐近效率
sources:
  - https://stat135.berkeley.edu/spring-2026/lectures/lecture-17.html
  - https://stat135.berkeley.edu/spring-2026/lectures/lecture-13.html
  - https://stat135.berkeley.edu/spring-2026/lectures/lecture-15.html
prerequisites:
  - "[[数学/30-概率与统计/12-充分统计量与估计效率]]"
  - "[[数学/30-概率与统计/08-中心极限定理与抽样分布]]"
content_status: usable
evidence_status: partial
---
# Fisher信息、正则条件与渐近效率

保存全部总数能降低估计方差，但还能低到哪里？“似然在真参数附近变化有多快”提供一种局部尺度。它在正则模型中给无偏方差下界，并解释最大似然估计的大样本尺度；支持随参数移动时，同一套求导却可能失效。

## Score 是数据对参数微小改变的读数

先考虑一维参数 $\theta$ 位于开区间，单个观测有共同测度下密度 $f_\theta(x)$。本节采用足够明确的一组条件：支持不随参数改变且密度在其上为正；关于参数可微；所用微分可移入归一化积分；score 平方可积。所需交换不是由“函数看起来光滑”自动得到，可由参数邻域中的可积支配函数等条件核实。

定义
$$s_\theta(X)=\partial_\theta\log f_\theta(X),\qquad I_1(\theta)=E_\theta[s_\theta(X)^2].$$
由 $\int f_\theta d\mu=1$ 的可交换求导，
$$E_\theta s_\theta=\int\partial_\theta f_\theta d\mu=0.$$
若还可将二阶导数移入积分，则用
$$\partial_\theta^2 f_\theta=f_\theta\{s_\theta^2+\partial_\theta^2\log f_\theta\}$$
得到 $I_1=-E_\theta\partial_\theta^2\log f_\theta$。前者是均方 score，后者是平均负曲率；等价性有条件，不能任取其中一个套模型。

对 iid 样本，$\ell_n=\sum_i\log f_\theta(X_i)$，$S_\theta=\ell_n'=\sum_i s_\theta(X_i)$。独立与零均值使交叉项消失，因此 $I_n=E S_\theta^2=nI_1$。相关样本不能只凭观察数乘 $n$；局部可识别性与 $0<I_1<\infty$ 也需要另外检查。

扩散模型的 score 对状态求导，本页对参数求导。[[数学/70-信号处理与多模态数学/03-高斯噪声扩散Score与ODE-SDE直觉#参数 score、状态 score 与单位改变|Gaussian 热流的两种 score]]用位置族 $p_t(x-\mu)$ 核出相反符号与相同平方信息 $1/v_t$，再用方差参数的信息 $1/(2v_t^2)$ 说明这种相等不能推广到任意参数。返回本页时先写明求导变量、参数单位和正则条件，再使用信息下界。

## Cramér–Rao 下界：关键是一个协方差

令 $U(X)$ 不含未知参数，$m(\theta)=E_\theta U$ 可微且 $U$ 方差有限；除上节条件外，再要求可在 $E_\theta U$ 中交换微分积分。则
$$m'(\theta)=\int U\,\partial_\theta p_\theta\,d\mu
=E_\theta[US_\theta]=\operatorname{Cov}_\theta(U,S_\theta).$$
Cauchy–Schwarz 给
$$[m'(\theta)]^2\le\operatorname{Var}_\theta(U)I_n(\theta),\qquad
\operatorname{Var}_\theta(U)\ge\frac{[m'(\theta)]^2}{I_n(\theta)}.$$
若 $U$ 无偏估计 $g(\theta)$，取 $m=g$。估计 $\theta$ 时下界为 $1/I_n$；有偏估计量则必须保留 $m'=1+b'$，且 MSE 还含 $b^2$。不能把无偏方差界当所有估计量的 MSE 界。

等号何时成立也来自 Cauchy–Schwarz：在给定参数下，中心化的 $U-m$ 必须 a.s. 为 score 的常数倍，具体为 $m'S_\theta/I_n$。信息界只是下界，不保证存在能达到它的估计量；上一课的 UMVU 也不必达到正则 Cramér–Rao 界。

参数若有单位，score 单位为参数单位的倒数，$I_n$ 为其平方，$1/I_n$ 才具有方差单位。对所讨论点满足 $h'(\theta)\ne0$、逆映射可微的光滑一一重参数 $\eta=h(\theta)$，有 $I_\eta=I_\theta(d\theta/d\eta)^2$；比较数值前必须固定参数坐标与目标。

## Bernoulli：同一个总数恰好达到下界

对 $0<\theta<1$，
$$s_\theta(X)=\frac{X-\theta}{\theta(1-\theta)},\quad
I_1(\theta)=\frac1{\theta(1-\theta)},\quad
S_\theta=\frac{S-n\theta}{\theta(1-\theta)}.$$
所以估计 $\theta$ 的无偏方差下界为 $\theta(1-\theta)/n$，样本均值 $S/n$ 正好达到；其中心化误差等于 $S_\theta/I_n$。这与 [[数学/30-概率与统计/12-充分统计量与估计效率#完备性为何让局部改进变成 UMVU|完备充分统计量的论证]] 是两条独立理由。

有限样本最大似然仍须查边界：在参数闭区间 $[0,1]$ 上，MLE 为 $S/n$，包括全0／全1时的端点；若坚持参数空间为 $(0,1)$，全0或全1样本只有边界上确界，没有区间内 MLE。下面的正则渐近推导固定真实 $\theta_0\in(0,1)$，这两类样本的概率 $(1-\theta_0)^n+\theta_0^n$ 随 $n$ 消失，不因此抹去它们的有限样本存在。

## 相合性：最大化前必须控制整条函数

对数似然每项的总体目标为 $M(\theta)=E_{\theta_0}\log f_\theta(X)$。先要求 $M(\theta_0)$ 与所比较的 $M(\theta)$ 均有限，例如 $E_{\theta_0}|\log f_\theta(X)|<\infty$；避免对两个负无穷作差。在此条件下，
$$M(\theta_0)-M(\theta)=D_{KL}(P_{\theta_0}\Vert P_\theta)\ge0.$$
可识别性使真参数成为唯一最大者，但**逐点大数定律不足以交换极限和 argmax**：一个随样本移动的窄尖峰可以逃过逐点比较。

一个可检查的充分版本是：在所选参数集合上，$M_n=\ell_n/n$ 满足 $\sup_\theta|M_n-M|\xrightarrow P0$；并且对每个 $\varepsilon>0$ 存在 $\delta_\varepsilon>0$ 使
$$M(\theta_0)-\sup_{|\theta-\theta_0|\ge\varepsilon}M(\theta)\ge\delta_\varepsilon.$$
设 $\hat\theta_n$ 可测且 $M_n(\hat\theta_n)\ge M_n(\theta_0)-o_P(1)$。当一致误差及优化误差分别小于 $\delta_\varepsilon/4$ 时，区间外任何点的经验目标至多为 $M(\theta_0)-3\delta_\varepsilon/4$，而 $\hat\theta_n$ 至少为 $M(\theta_0)-\delta_\varepsilon/2$，矛盾。因此 $P(|\hat\theta_n-\theta_0|\ge\varepsilon)\to0$。

这证明了所陈述条件下的相合性，不声称所有 MLE 都满足条件。紧参数集上对数密度的连续性与适当可积包络是一类可建立一致大数定律的路线；非紧空间、混合模型的似然爆高、不可识别与数值优化的错误极值须分别处理。Bernoulli 的 $S/n$ 相合已由方差／Chebyshev 直接证明，无须绕道假定整套一般正则性。

## 渐近正态：随机斜率除以稳定曲率

在相合基础上，再要求：真参数内点；以概率趋于1存在所选内点驻值 MLE；邻域二阶可微；$0<I_1(\theta_0)<\infty$ 且上述 score 身份成立；平均 Hessian 在该邻域有足够的局部一致控制，使位于 $\hat\theta_n,\theta_0$ 之间的 $\widetilde\theta_n$ 满足 $-\ell_n''(\widetilde\theta_n)/n\xrightarrow P I_1(\theta_0)$。例如二阶导的局部一致大数定律与其期望在真参数连续可提供最后条件。

均值定理给
$$0=\ell_n'(\hat\theta_n)=\ell_n'(\theta_0)+\ell_n''(\widetilde\theta_n)(\hat\theta_n-\theta_0),$$
所以
$$\sqrt n(\hat\theta_n-\theta_0)
=\frac{\ell_n'(\theta_0)/\sqrt n}{-\ell_n''(\widetilde\theta_n)/n}
\ \Rightarrow\ N(0,I_1(\theta_0)^{-1}).$$
分子是 iid 零均值 score 的 CLT，分母依概率趋于正数；Slutsky 完成最后一步。旧课 [[数学/30-概率与统计/08-中心极限定理与抽样分布|中心极限定理]] 提供分子所用极限定理，本文把条件写在应用位置，未证明所有可能模型的一致 Hessian 定理。

这里“渐近方差 $I_1^{-1}$”首先指归一化误差的**极限分布参数**。只从分布收敛，不能推出 $n\operatorname{Var}(\hat\theta_n)\to I_1^{-1}$，还需相应二阶矩的一致可积性等条件。正则局部渐近比较下的效率也不是对所有有偏／非正则估计量、所有参数逐点最优；有限样本偏差、参数边界和模型误设不能藏在“大样本”三个字里。

Bernoulli 在内点直接由样本均值 CLT 得 $\sqrt n(S/n-\theta_0)\Rightarrow N(0,\theta_0(1-\theta_0))$；其有限方差本来就等于 $\theta_0(1-\theta_0)/n$，此例不需要从弱收敛猜二阶矩。

## Uniform 的移动支持：不是定理被数据推翻

令 $X_i$ iid Uniform$(0,\theta)$，$\theta>0$。选密度版本 $f_\theta(x)=\theta^{-1}\mathbf1_{0<x\le\theta}$；端点版本不改变固定参数下的分布，但写 MLE 时必须交代所选似然版本。样本最大值 $M=\max_iX_i$ 给
$$p_\theta(x)=\theta^{-n}\mathbf1_{M\le\theta}\prod_i\mathbf1_{x_i>0}.$$
因子分解表明 $M$ 充分；在这个版本下似然于可行域 $\theta\ge M$ 递减，最大在 $\hat\theta=M$，**不是**通过内部 score 为0得到。若将密度端点写成严格 $x<\theta$，极大值改为趋近 $M$ 的上确界；统计实践中的最大值估计与下述分布计算不受此端点零测集改变影响。

只看支持内部的导数会得到单项 $s=-1/\theta$，均值显然不是0；$E s^2=1/\theta^2$ 而 $-E\partial_\theta^2\log f=-1/\theta^2$，两种“信息”已矛盾。原因可直接看归一化：
$$\frac d{d\theta}\int_0^\theta\frac1\theta dx=0,
\qquad \int_0^\theta\frac{\partial}{\partial\theta}\frac1\theta dx=-\frac1\theta.$$
移动上界的边界项 $1/\theta$ 被漏掉。共同支持、可交换求导、零均值 score、内点驻值 MLE这几个正则步骤都不能照搬，$I_n=nI_1$ 的零交叉项理由也随之失效。

改用真实分布：$0\le m\le\theta$ 时 $P(M\le m)=(m/\theta)^n$，求导并积分得
$$E M^r=\frac{n}{n+r}\theta^r\quad(r>0),\qquad
E M=\frac n{n+1}\theta,\quad
\operatorname{Var}(M)=\frac{n\theta^2}{(n+1)^2(n+2)}.$$
故 $\widetilde\theta=(n+1)M/n$ 无偏，方差为 $\theta^2/[n(n+2)]$，小于误套正则式得到的 $\theta^2/n$；没有违反 Cramér–Rao，因为其前提不成立。

它还相合：对 $0<\varepsilon<\theta$，$P(\theta-M>\varepsilon)=(1-\varepsilon/\theta)^n\to0$。正确极限尺度是 $n$，非 $\sqrt n$：对固定 $t\ge0$，当 $n>t$，
$$P\{n(\theta-M)/\theta>t\}=(1-t/n)^n\to e^{-t}.$$
极限为单侧指数分布。支持边缘携带的信息与平滑曲率不同，不能把全部 MLE 一概说成渐近正态。

## 改一个条件再判断

1. 在 Bernoulli 中取 $n=4,\theta=1/2$，信息量、无偏方差下界与 $X_1$ 的方差分别是多少？
2. 在 Uniform 中取 $n=4,\theta=1$，无偏修正是多少，方差是多少？它比错误下界小，究竟反驳什么？
3. 一个数值程序报“score近零”，是否足以宣布 MLE相合、渐近有效？

<details><summary>答案与核对</summary>

1. $I_n=16$，下界 $1/16$，$\operatorname{Var}(X_1)=1/4$；$S/4$达到下界。
2. 修正为 $5M/4$，方差 $1/24$；反驳的是忽略移动支持的套式，不是正则定理。Uniform 的最大似然点在样本约束边界。
3. 不足。还需极值／边界与全局目标比较、模型可识别、相合条件、正则局部曲率、抽样条件等。程序找驻点与统计极限定理是不同层证据。

</details>

## 来源与应用出口

[Berkeley Stat 135 Lecture 17](https://stat135.berkeley.edu/spring-2026/lectures/lecture-17.html)对应 score–协方差的信息下界；[Lecture 13](https://stat135.berkeley.edu/spring-2026/lectures/lecture-13.html)与[Lecture 15](https://stat135.berkeley.edu/spring-2026/lectures/lecture-15.html)对应最大似然的相合与渐近正态主题。本页独立写出一致目标／分离条件下的 argmax 证明和标量 score 展开，明确把一致大数定律与 CLT 作为相应输入；Uniform 的矩与极限由分布函数直接推导。

返回 [[数学/30-概率与统计/03-似然负对数似然与困惑度#为什么取负对数|NLL]]：最小化 NLL 只确定优化目标，不能自动认证模型正确或参数可识别。决定是否拒绝一个假设时，继续 [[数学/30-概率与统计/14-似然比最优检验与置换推断|固定误报下的最优检验]]。

在 [[数学/30-概率与统计/82-充分估计与停止规则精确复算|精确复算实验]] 中核对本文的有限样本量；解析推导给普遍结论，有限枚举与有理数计算检查具体实例。
