---
type: lesson
domain: mathematics
stage: 3
aliases:
  - 平稳分布不等于独立样本
  - Markov链通信常返与遍历
sources:
  - https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/2edaa8542469ce692226813a8bd1ec88_MIT18_445S15_lecture2.pdf
  - https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/5bd4774f613aa28bd111c36f3a3beeed_MIT18_445S15_lecture4.pdf
  - https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/06c09371501eb1d7dd4c7c72c74cef5b_MIT18_445S15_lecture20.pdf
prerequisites:
  - "[[数学/30-概率与统计/20-随机过程/01-一般条件期望与过滤]]"
  - "[[数学/30-概率与统计/07-概率不等式大数定律与收敛方式]]"
content_status: usable
evidence_status: partial
---
# Markov链与长期平均

跑一个随机算法很久，记录各状态出现比例，为什么有时能估计目标分布、有时永远卡在初始状态？“有平稳分布”“当前分布趋近它”“一条轨迹的时间平均趋近它”是三个命题。先在两个状态上把它们分开，再证明有限链的关键结论。

## 对象与通信：每行描述从哪里走到哪里

在有限状态集 $E$ 上，齐次Markov链满足
$$P(X_{n+1}=j\mid X_0,\ldots,X_n)=P_{X_n,j}.$$
矩阵 $P$ 每行非负且和为1。本页分布用行向量，故 $\mu_n=\mu_0P^n$；别与 [[AI/45-机器人与具身智能/02-Bayes滤波与Kalman状态估计#先预测，再用观测归一|Bayes滤波页]] 的列向量转移约定混用。Markov性质不是说相邻状态独立，而是给定当前状态后，过去不再额外改变下一步分布。

若某个 $n\ge0$ 有 $(P^n)_{ij}>0$，称 $i$ 可达 $j$；互相可达定义通信类。全体状态同属一类称不可约。一个通信类若没有通向外部的正概率转移，称闭类。状态 $i$ 的首次回返 $T_i^+=\inf\{n\ge1:X_n=i\}$：从 $i$ 出发回返概率为1叫常返，小于1叫暂留；常返且 $E_iT_i^+<\infty$ 叫正常返，否则为零常返。有正长度回返路径时，周期定义为 $\gcd\{n\ge1:(P^n)_{ii}>0\}$，本页有限不可约链均有这样的回返路径，且各状态周期相同；没有任何回路的暂留状态不在这个周期定义的适用范围内。

有限不可约链都正常返：对目标 $i$，从每个状态选一条正概率路径到 $i$，从 $i$ 本身选一条正长度回路。有限条路径有共同长度上界 $r$，路径概率有正下界 $\delta$。因此任意尚未到达的历史之后，接下来 $r$ 步内到达概率至少 $\delta$，尾概率按块不超过 $(1-\delta)^k$，期望有限。有限可约链的闭类同理；有出口的通信类可以沿正概率路径离开且不回返，其中状态是暂留的。可数无限状态时不能取这个有限的统一下界，例如整轴公平游走虽常返，平均回返时间无限；本课不把有限链定理直接扩张到无限链。

## 三条二状态链，三个不同答案

都从状态0开始。令经验占比为 $A_n(j)=n^{-1}\sum_{k=0}^{n-1}1_{X_k=j}$。

| 转移矩阵 | 平稳分布 $\pi P=\pi$ | 逐时分布 $\mu_n$ | 一条路径的时间占比 |
| --- | --- | --- | --- |
| $I$ | 任意 $(a,1-a)$ | 始终 $(1,0)$ | 始终 $(1,0)$ |
| $\begin{pmatrix}0&1\\1&0\end{pmatrix}$ | 唯一 $(1/2,1/2)$ | 偶数 $(1,0)$，奇数 $(0,1)$ | 趋于 $(1/2,1/2)$ |
| $\begin{pmatrix}3/4&1/4\\1/2&1/2\end{pmatrix}$ | 唯一 $(2/3,1/3)$ | $\pi+(1/3,-1/3)(1/4)^n$ | a.s. 趋于 $(2/3,1/3)$ |

第二条链周期2，每条路径交替跳动。即使把初始分布改成平稳分布，使每个时刻边缘分布都为 $(1/2,1/2)$，知道当前状态仍会完全确定下一状态，远非独立样本。第三条链第一步为 $(3/4,1/4)$，第二步为 $(11/16,5/16)$；由递推 $p_{n+1}=1/2+p_n/4$，减去不动点 $2/3$ 就得到表中公式。

## 平稳分布的存在唯一性不需要无周期

有限单纯形紧。任取初始分布 $\mu$，考虑Cesàro均值 $\bar\mu_n=n^{-1}\sum_{k=0}^{n-1}\mu P^k$。有
$$\bar\mu_nP-\bar\mu_n=\frac{\mu P^n-\mu}{n}\longrightarrow0.$$
取收敛子列，其极限 $\pi$ 就满足 $\pi P=\pi$。这证明任意有限链至少存在一个平稳分布，未证明每个 $\mu P^n$ 收敛。

若链不可约，则 $\pi_j=0$ 会由 $\pi_j=\sum_i\pi_iP_{ij}$ 迫使所有可一步进入 $j$ 的前驱也为零，沿路径反推至全部状态，与总和1矛盾。因此每个 $\pi_i>0$。

若 $\tilde\pi$ 也是平稳分布，令 $r_i=\tilde\pi_i/\pi_i$。平稳方程给
$$r_j=\sum_i\frac{\pi_iP_{ij}}{\pi_j}r_i,$$
右侧权重非负且和1。最大比值处只有所有正权前驱也取最大值才能相等；不可约性使最大值传遍全体。故 $r$ 常数，由总和1知常数为1，即唯一。[MIT Lecture2，slides3–6](https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/2edaa8542469ce692226813a8bd1ec88_MIT18_445S15_lecture2.pdf)可对照不可约、周期与平稳性的条件；本节的存在证明采用上述有限维紧性路线。

## 什么时候当前分布也收敛

一个可直接使用的条件是：存在整数 $r\ge1$，$Q=P^r$ 的所有元素都正。若状态数为 $d$，取 $\epsilon=d\min_{ij}Q_{ij}>0$，则 $\epsilon\le1$。设 $u$ 为均匀分布；当 $\epsilon<1$，每行可写
$$Q(i,\cdot)=\epsilon u+(1-\epsilon)R(i,\cdot),$$
其中 $R$ 是转移矩阵。因此总变差距离满足
$$\|\mu Q-\nu Q\|_{TV}\le(1-\epsilon)\|\mu-\nu\|_{TV}.$$
理由是共同的 $\epsilon u$ 相消，而随机矩阵不增总变差：对有符号行向量 $a$，$\sum_j|\sum_i a_iR_{ij}|\le\sum_i|a_i|\sum_jR_{ij}=\sum_i|a_i|$。迭代并取 $\nu=\pi$ 得几何收敛；剩余不足 $r$ 步也不增加距离。若 $\epsilon=1$，一步 $Q$ 已把所有分布送到 $u$。

有限不可约且无周期保证存在这样的 $r$；其中“不可约且回路长度最大公约数1 $\Rightarrow$ 足够大长度的所有路径均可达”是此处明确使用的有限链引理，完整图论／整数长度证明作为外部依赖，见上引Lecture2 slide4。收缩后续步骤已在本页证明；[Lecture4，slides3–4](https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/5bd4774f613aa28bd111c36f3a3beeed_MIT18_445S15_lecture4.pdf)给出相同范围的收敛定理。

## 为什么有周期也可以有时间平均

有限不可约链不要求无周期，就有对任意初始状态与实函数 $f:E\to\mathbb R$，
$$\frac1n\sum_{k=0}^{n-1}f(X_k)\longrightarrow\sum_j\pi_jf(j)\quad a.s.$$
以下把证明归结到独立回返段的强大数定律，而不是假装每一步独立。

选状态 $i$，先从它出发；连续回到 $i$ 的时刻把路径分成周期段。强Markov性质使各段独立同分布：在离散停时 $T$ 上，先按 $\{T=m\}$ 分解，在每个固定 $m$ 使用通常Markov条件，再求和即可验证未来有限路径只依赖 $X_T=i$。段长 $D$ 期望有限，段报酬 $R=\sum_{k=0}^{T_i^+-1}f(X_k)$ 满足 $|R|\le\|f\|_\infty D$，也可积。对独立的 $(D_l,R_l)$ 用强大数定律，完整段总报酬／总长度趋于 $ER/ED$。

核对这个比值：记一段内到状态 $j$ 的期望次数 $v_j=E_i\sum_{k=0}^{T_i^+-1}1_{X_k=j}$。可求和，因为次数总和期望为 $ED<\infty$。由Markov性质，$(vP)_j$ 等于该段从第1步到回返步的期望次数；初点和终点都为 $i$，所以 $vP=v$。归一化 $v/ED$ 是平稳分布，由唯一性等于 $\pi$，于是 $ER/ED=\pi f$；特别地 $v_i=1$，得到 $E_iT_i^+=1/\pi_i$。

剩余不完整段不会改变极限：有限 $ED$ 使 $\sum_lP(D_l>\eta l)<\infty$ 对每个 $\eta>0$ 成立，因此由第一Borel–Cantelli引理有 $D_l/l\to0$ a.s.；结合累计段长／段数趋于 $ED>0$，未完成段长度／总时间趋零，其报酬也同样可忽略。任意初始状态先到达 $i$ 的有限前段不影响极限。这里明确使用 iid 可积强大数定律与Borel–Cantelli作为概率极限输入；已有 [[数学/30-概率与统计/07-概率不等式大数定律与收敛方式|弱大数课]] 的有限方差Chebyshev证明本身没有证明这两条强结论。

## 回到MCMC：平稳也不会自动产生iid误差条

若链已平稳，$Y_k=f(X_k)$、$\gamma_h=\operatorname{Cov}(Y_0,Y_h)$，直接展开给
$$\operatorname{Var}\!\left(\frac1n\sum_{k=0}^{n-1}Y_k\right)=\frac1{n^2}\left[n\gamma_0+2\sum_{h=1}^{n-1}(n-h)\gamma_h\right].$$
只保留 $\gamma_0/n$ 就是在额外假定协方差项消失。第三条二状态链在平稳下取 $Y_k=1_{X_k=1}$，有 $\gamma_0=2/9$、$\gamma_h=(2/9)(1/4)^h$，因此 $n\operatorname{Var}(\bar Y_n)\to(2/9)(1+2/3)=10/27$，比iid值大 $5/3$ 倍。这个例子可由 $E[Y_h-1/3\mid X_0]=(1/4)^h(Y_0-1/3)$ 逐步验证。

回到 [[AI/10-机器学习与深度学习基础/20-贝叶斯学习概率图模型与近似推断#Monte Carlo：用样本近似期望|Monte Carlo应用]] 时，应分别说明目标平稳分布、不可约性／遍历条件、初始偏差与序列相关。链长或一张直方图没有单独证明这些条件。HMM的隐藏链若不可约，并不因此使带观测条件的后验采样器也满足相同转移性质；要检查真正运行的那个核。

## 连续时间的最小入口：Poisson等待时间

率 $\lambda>0$ 的Poisson过程 $N_t$ 从0开始，有独立平稳增量，$N_t-N_s\sim\operatorname{Poisson}(\lambda(t-s))$，$s<t$。率的单位是次数／时间。第一个等待时间 $T_1$ 满足
$$P(T_1>t)=P(N_t=0)=e^{-\lambda t},$$
故其密度 $\lambda e^{-\lambda t}$、均值 $1/\lambda$。条件于已经等过 $s$，再等 $t$ 的概率为 $e^{-\lambda(s+t)}/e^{-\lambda s}=e^{-\lambda t}$，这是无记忆性；并非所有等待时间分布都如此。

后续间隔独立同分布为指数分布，需要在到达停时重新开始的强Markov性质；本节只把该过程定理作为外部输入，见 [MIT Lecture20，slides4–5](https://ocw.mit.edu/courses/18-445-introduction-to-stochastic-processes-spring-2015/06c09371501eb1d7dd4c7c72c74cef5b_MIT18_445S15_lecture20.pdf)。于是 $T_k$ 是 $k$ 个指数间隔之和，$ET_k=k/\lambda$。取自然过滤 $\mathcal F_s=\sigma(N_u:0\le u\le s)$，独立增量还直接给 $E[N_t-\lambda t\mid\mathcal F_s]=N_s-\lambda s$，即补偿计数是鞅；原计数则有向上漂移。观测到聚集到达、率随时间或历史改变时，不能继续把固定率Poisson过程当成已证事实。

## 迁移题与答案

1. 周期交替链每隔两步保留一个样本，是否解决周期问题并得到独立样本？
2. 两个不相通的闭类各有平稳分布，单条路径能估计任意混合权重吗？
3. 从观测到的长期计数率相同，能否断定两套服务系统都符合Poisson等待假设？

**答案。** 1：不能。从状态0出发抽取偶数步只剩0，反而丢掉一半状态；改变采样方式要检查新核 $P^2$。2：不能。轨迹停留在进入的类中，类间权重来自初始分布或其他建模信息。3：不能。同均值率未规定独立增量或无记忆性，需检查完整时间依赖。三题都要求先分清边缘分布、路径依赖与目标平均。

连续噪声的另一支走向 [[数学/30-概率与统计/20-随机过程/04-Brownian二次变差与Ito公式|Brownian二次变差与Itô公式]]：Poisson跳跃和Brownian连续轨迹的积分规则不同，不可把两者的样本路径画成平滑曲线后套普通链式法则。
