---
type: lesson
domain: mathematics
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 65
topics:
  - gaussian-noise
  - diffusion
  - score-function
  - ode
  - sde
tags:
  - mathematics/probability
  - mathematics/multimodal
---

# 高斯噪声、扩散、Score 与 ODE-SDE 直觉

## 本课目标

读完后，你应能：

1. 读懂“信号加高斯噪声”的重参数化公式；
2. 区分条件分布的 score 与混合后的边缘分布 score；
3. 用向量场理解 score 指向高概率区域的局部方向；
4. 区分 SDE 的随机路径与 probability flow ODE 的确定性路径。

> [!important] 第一阶段最低先修
> 学扩散模型时，最低要求是会读 $x_t=\alpha_t x_0+\sigma_t\epsilon$，知道 score 是对“当前状态”求对数密度梯度，并理解反向 SDE 与 probability flow ODE 可以在适当条件下共享边缘分布，但单条轨迹并不相同。随机微积分证明不是第一阶段要求。

## 1. 高斯噪声不是“随便抖一下”

一维标准高斯变量写作 $\epsilon\sim\mathcal N(0,1)$。在 $d$ 维中，常用

$$
\epsilon\sim\mathcal N(0,I),
$$

表示各坐标均值为 0、方差为 1，且在这个坐标系中彼此独立。给干净数据 $x_0$ 加噪的一种通用写法是：

$$
x_t=\alpha_t x_0+\sigma_t\epsilon.
$$

- $t$ 是噪声时间，不一定等于物理时间；
- $\alpha_t$ 控制保留多少原信号；
- $\sigma_t$ 控制加入多少噪声；
- $\epsilon$ 是本次随机抽到的噪声。

因此，在给定 $x_0$ 后：

$$
q(x_t\mid x_0)=\mathcal N(\alpha_t x_0,\sigma_t^2I).
$$

某些 variance-preserving 设计满足 $\alpha_t^2+\sigma_t^2=1$，但这不是所有扩散过程的普遍定义。具体调度必须单独说明。

### 数字例子

若 $x_0=3$、$\alpha_t=0.8$、$\sigma_t=0.6$，本次抽到 $\epsilon=-0.5$，则

$$
x_t=0.8\times3+0.6\times(-0.5)=2.1.
$$

同一个 $x_0$ 在同一时刻可以得到不同 $x_t$；扩散描述的是分布与随机过程，不是一条固定直线。

## 2. 前向扩散：逐步忘掉数据细节

离散时间过程可以写成 Markov 链：

$$
q(x_t\mid x_{t-1}).
$$

Markov 性表示：给定当前状态后，下一步不再需要更早历史。合理设计每一步的均值与方差后，多步结果可合并成上一节的闭式 $q(x_t\mid x_0)$，从而能直接抽取任意噪声时刻训练样本。

连续时间的前向过程常写为随机微分方程：

$$
\mathrm d x=f(x,t)\,\mathrm dt+g(t)\,\mathrm dW_t.
$$

- $f$ 是 drift，描述确定性漂移；
- $g$ 控制随机扰动强度；
- $W_t$ 是 Wiener 过程，$\mathrm dW_t$ 的尺度约为 $\sqrt{\mathrm dt}$，不能当成普通的 $\mathrm dt$。

直觉上，ODE 是“站在同一点、规则唯一地告诉你往哪里走”；SDE 则在规则之外，每个小步还抽一次随机扰动。

## 3. Score：对数密度的上坡方向

时刻 $t$ 的边缘密度为 $p_t(x)$。它的 score 定义为：

$$
s_t(x)=\nabla_x\log p_t(x).
$$

score 是一个与 $x$ 同形状的向量。它指向对数密度局部增长最快的方向；在密度峰顶附近，score 可能接近 0。使用 $\log p$ 不会改变上坡方向，并把概率密度的乘法结构转成加法结构。

对给定 $x_0$ 的高斯条件分布，精确 score 是：

$$
\nabla_{x_t}\log q(x_t\mid x_0)
=-\frac{x_t-\alpha_t x_0}{\sigma_t^2}
=-\frac{\epsilon}{\sigma_t}.
$$

这解释了为何预测噪声 $\epsilon$ 与预测条件 score 可以互相换算。

> [!warning] 条件 score 不等于直接知道真实边缘 score
> $-\epsilon/\sigma_t$ 使用了本次训练样本的 $x_0$ 与噪声。真正反向过程需要 $\nabla_x\log p_t(x)$，其中 $p_t$ 混合了所有可能的 $x_0$。在平方误差训练的理想最优点，模型学习的是与条件目标相关的条件期望，从而恢复边缘 score；不能把单个样本的噪声标签直接说成全局密度场。

## 4. 一维 score 的方向例子

若 $p(x)=\mathcal N(2,4)$，即均值 $\mu=2$、方差 $\sigma^2=4$，则

$$
\frac{\mathrm d}{\mathrm dx}\log p(x)
=-\frac{x-2}{4}.
$$

- $x=6$ 时 score 为 $-1$，指向左边的高密度区域；
- $x=0$ 时 score 为 $0.5$，指向右边；
- $x=2$ 时 score 为 0，位于密度峰顶。

score 只给局部方向与尺度，不直接给归一化常数，也不保证一步跳到最终样本。

## 5. 反向 SDE：逆着噪声时间恢复结构

在常见正则条件下，若把时间从 $T$ 向 0 积分，前向 SDE 的反向时间形式可写成：

$$
\mathrm d x=
\left[f(x,t)-g(t)^2\nabla_x\log p_t(x)\right]\mathrm dt
+g(t)\,\mathrm d\bar W_t,
$$

其中积分方向是从大 $t$ 到小 $t$，$\bar W_t$ 表示反向时间噪声。若把时间重新参数化成始终向前增加的变量，符号会相应改变；因此不能脱离积分方向死记正负号。

模型近似 score 后，就能把“纯噪声附近的样本”逐步推向数据的高密度区域，同时保留随机采样能力。

## 6. Probability flow ODE：相同边缘分布，不同路径

与上述前向 SDE 相关的 probability flow ODE 为：

$$
\mathrm d x=
\left[f(x,t)-\frac{1}{2}g(t)^2\nabla_x\log p_t(x)\right]\mathrm dt.
$$

它没有随机微分项。若 score 精确、正则条件成立并正确求解，ODE 与相应 SDE 在每个时刻可以具有相同的**边缘概率分布**。

这不表示两者逐样本轨迹相同：

- SDE 从同一点出发仍可因随机增量走出不同路径；
- ODE 给定初值后路径由向量场唯一决定（满足常见唯一性条件时）；
- 数值步长、近似 score 和求解器误差会让实际结果偏离理想结论。

## 7. 数值求解只看“小步近似”

ODE 的 Euler 小步为：

$$
x_{n+1}=x_n+h\,v(x_n,t_n).
$$

SDE 的 Euler–Maruyama 小步为：

$$
x_{n+1}=x_n+f(x_n,t_n)h+g(t_n)\sqrt{h}\,z_n,
\qquad z_n\sim\mathcal N(0,I).
$$

随机项随 $\sqrt h$ 缩放，是它与普通 ODE Euler 法的关键区别之一。第一阶段只需会读公式；稳定性、强/弱收敛阶和高阶采样器属于后续数值分析与模型课程。

## 练习

1. 令 $x_0=4$、$\alpha_t=0.5$、$\sigma_t=1$、$\epsilon=-2$，计算 $x_t$ 与条件 score。
2. 对 $p(x)=\mathcal N(-1,9)$，分别判断 $x=2$ 与 $x=-4$ 处 score 的方向。
3. 用自己的话解释“ODE 与 SDE 共享边缘分布”为什么不等于“每条轨迹相同”。
4. Euler–Maruyama 中若步长从 $h$ 变为 $h/4$，单步随机项的典型尺度变成原来的多少？

## 成功标准

- [ ] 得到 $x_t=0$，条件 score 为 $-\epsilon/\sigma_t=2$。
- [ ] 能算出 $x=2$ 处 score 为 $-1/3$、指向左，$x=-4$ 处为 $1/3$、指向右。
- [ ] 能明确区分“同一时刻的样本总体分布”与“某个初值对应的单条运动路径”。
- [ ] 得到随机项尺度变为原来的 $1/2$，而不是 $1/4$。

## 边界与下一步

本课没有展开 U-Net/Transformer 去噪网络、条件引导、训练权重、离散采样器或潜空间扩散。这些属于 [[AI/50-扩散模型/00-扩散模型-MOC|扩散模型 MOC（planned）]]。

- 上一课：[[数学/70-信号处理与多模态数学/02-采样定理波形STFT与Mel频谱|采样定理、波形、STFT 与 Mel 频谱]]
- 返回：[[数学/70-信号处理与多模态数学/00-信号处理与多模态数学-MOC|信号处理与多模态数学 MOC]]
- 动手验证：[[数学/70-信号处理与多模态数学/80-多模态数学最小实验|多模态数学最小实验]]
- 相关基础：[[数学/30-概率与统计/00-概率与统计-MOC|概率与统计 MOC]]、[[数学/40-微积分与优化/00-微积分与优化-MOC|微积分与优化 MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的定义、推导条件和反例见 [[数学/16-数学分析/13-Fourier级数正交展开与收敛|Fourier级数正交展开与收敛]]；[[数学/46-数理方程/14-Fourier-Laplace变换解数理方程|Fourier-Laplace变换解数理方程]]；[[数学/20-线性代数与几何/16-SVD的推导最优低秩与PCA|SVD的推导最优低秩与PCA]]。
