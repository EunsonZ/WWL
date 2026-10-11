---
type: deep-lesson
status: reviewed
updated: '2026-09-06'
review_round: 深化研究-02
tags:
- ai/deep-study
aliases: []
---

# Score、去噪、Flow Matching与CFG的联系

**先修与定位：** 需要[[AI/11-数学与统计桥梁/03-概率似然贝叶斯与信息论|条件期望]]与[[AI/11-数学与统计桥梁/02-矩阵微积分VJP与反向传播|梯度]]；连接原有DDPM与FlowMatching笔记。

## 先统一时间方向，避免同一个t代表相反过程

本页先用 $x_t=a_t x_0+\sigma_t\epsilon$ 描述数据 $x_0$ 加噪，$\epsilon\sim\mathcal N(0,I)$。对应上一课的 DDPM 记号，局部映射为 $a_t=\sqrt{\overline\alpha_t}$、$\sigma_t=\sqrt{1-\overline\alpha_t}$；这里的 $a_t$ 不是 DDPM 的单步 $\alpha_t=1-\beta_t$。稍后流匹配另用从噪声到数据的时间 $u$，避免把两种文献约定混为一谈。DDPM 将去噪预测与生成过程相连。[^S64]

给定 $x_0$，在 $\sigma_t>0$ 时，$x_t$ 的高斯条件密度梯度为

$$
\nabla_{x_t}\log q(x_t\mid x_0)=-\frac{x_t-a_t x_0}{\sigma_t^2}=-\epsilon/\sigma_t.
$$

所以在给定噪声等级下，预测噪声与预测条件 score 之间有直接换算。但生成真正需要的是边缘分布 $q_t(x_t)$ 的 score，而不是已知干净样本条件下的单条噪声。

## 平方误差最优预测为什么是条件均值

对随机目标 $Y$，平方损失满足

$$
\mathbb E[\|Y-f(X)\|^2\mid X]=\operatorname{tr}\operatorname{Cov}(Y\mid X)+\|\mathbb E[Y\mid X]-f(X)\|^2.
$$

因此最优噪声预测为 $\mathbb E[\epsilon\mid x_t,t]$。在适当可微和积分交换条件下，对条件 score 取后验平均得到边缘 score，于是 $s_\theta(x_t,t)\approx-\epsilon_\theta(x_t,t)/\sigma_t$。模型不是神奇地从每个含噪样本中唯一还原当初那一份噪声，而是在不确定性下估计条件均值。

把它与上一课的固定样本分开，再看一个可精算的随机模型。令 $X_0,\epsilon\overset{\mathrm{ind}}{\sim}\mathcal N(0,1)$，并令 $X_t=0.8X_0+0.6\epsilon$。此时

$$
\operatorname{Var}(X_t)=0.8^2+0.6^2=1,\qquad
\operatorname{Cov}(\epsilon,X_t)=0.6.
$$

由于 $(\epsilon,X_t)$ 联合高斯，$\mathbb E[\epsilon\mid X_t=x]=0.6x$。因此在 $X_t=1$ 时，噪声的最小均方误差预测是 $0.6$，不是上一课那次固定构造中预先选定的样本噪声 $-1$。同时 $X_t\sim\mathcal N(0,1)$，所以边缘 score 为 $\nabla_x\log q_t(x)=-x$；条件 score 经后验平均也给出同一结果：

$$
\mathbb E\!\left[\nabla_x\log q_t(x\mid X_0)\mid X_t=x\right]
=-\frac{\mathbb E[\epsilon\mid X_t=x]}{0.6}
=-x.
$$

预测 $x_0$、$\epsilon$ 或速度参数化可以互相代数转换，但训练时对不同时间的误差权重未必相同；在 $\sigma_t$ 很小的端点直接除法也可能不稳定。参数化、时间采样和 SNR 权重必须一起说明。

即使精确知道边缘 score，也须区分边缘分布与完整过程。[[数学/70-信号处理与多模态数学/03-高斯噪声扩散Score与ODE-SDE直觉#同边缘为什么不保证同路径关系|同一 Gaussian 热流的二时刻计算]]让 SDE 和概率流 ODE 都具有 $N(0,v_t)$ 边缘，却得到不同协方差核；其前一段从热方程推得前向速度 $-\kappa\partial_x\log p_t$，也解释了为何 score 向峰顶而前向 ODE 向外。该例只用声明的精确 Gaussian score；它不是从真实数据学得 score 的证据，也不认证近似网络或采样器恢复了真实分布。

## Flow Matching学习的是边缘速度场

取噪声 $z$ 与数据 $x$，定义一条条件直线路径 $x_u=(1-u)z+ux$，其条件速度为 $x-z$。回归目标可为

$$
\mathbb E\|v_\theta(x_u,u)-(x-z)\|^2.
$$

最优解是给定当前位置的条件速度平均 $\mathbb E[x-z\mid x_u,u]$。Flow Matching 研究以概率路径和向量场回归训练连续生成流。[^S65] 许多配对的直线可能在同一位置交汇，平均后的边缘速度场及其积分轨迹不必仍是每对样本的直线。**训练配对路径直，不等于模型采样轨迹处处直。**

生成通过求解常微分方程从噪声端前进。Euler、较高阶求解器、步数和时间网格会引入不同数值误差。减少步数是否保持质量必须测试，不能只靠训练损失判断。

## CFG不是无代价的条件强化

若模型能预测无条件与有条件 score，一种引导约定是

$$
s_{\rm guide}=s_{\rm uncond}+w(s_{\rm cond}-s_{\rm uncond}).
$$

这里 $w=1$ 对应条件预测，$w=0$ 对应无条件。其他文献可能把参数写成 $1+w$，比较前要对齐。CFG 通过组合条件与无条件预测控制生成倾向。[^S66]

在理想 score 下，它在固定时间可对应梯度 $\nabla\log[p_t(x\mid c)^w p_t(x)^{1-w}]$。但这不自动说明整条近似数值采样过程严格产生某个简单的最终幂次重加权分布。过强引导可能减少多样性并放大伪影，条件一致性、保真与多样性需要联合评估。

## 与语言生成的共同点和差异

它们都用可计算监督近似复杂分布，并在推理时依赖迭代、数值误差与条件约束。连续扩散的高斯微分结构不能直接搬到离散 token；[[AI/20-LLM/80-研究拓展/02-离散扩散语言模型与自回归对照|离散扩散语言模型]]使用自己的破坏与恢复过程。图像中的重构误差也不等于语言中的语义事实正确性。

自测：噪声预测训练 MSE 降低，是否必然让人类偏好提高？不必然。目标权重、采样器、引导强度、评测数据和感知指标都参与结果。先用[[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|代数实验]]检查参数化换算，再做独立生成评估。

与[[AI/45-机器人与具身智能/20-状态估计与LQG/05-从不完整读数到条件不确定性|不完整读数的条件不确定性]]相比，二者的 MSE 最优预测都可写成条件期望；这只说明“在已观测信息下取均方误差最优估计”的共同结构。Kalman 的线性动态、过程协方差和当前测量模型不是扩散采样的前提，扩散的人工加噪时间也不是机器人状态演化；不要由相同的条件期望符号推得可互用的动力学假设。

对一般先验，条件逆核/反向协方差的这一类公式不能只保留“混合分量之间”的不确定性：写成对应的标量噪声项与数据条件项时，形式是 $\widetilde\beta_t I+c_0^2\operatorname{Cov}(X_0\mid X_t)$（具体系数依所选正反向参数化而变）。最后一项依全后验协方差而定；对混合变量 $C$，全协方差按全方差公式分为 $\mathbb E[\operatorname{Cov}(X_0\mid X_t,C)\mid X_t]$（分量内）和 $\operatorname{Cov}(\mathbb E[X_0\mid X_t,C]\mid X_t)$（分量间）。与 V19 首步 DDPM 记号对齐，取 $\alpha_1=0.85$、$\beta_1=0.15$、$\widetilde\beta_1=0$、$c_0=1$ 及单高斯 $X_0\sim\mathcal N(0,1)$；由 $X_1=\sqrt{0.85}X_0+\sqrt{0.15}\epsilon$ 得 $\operatorname{Var}(X_0\mid X_1)=1-0.85=0.15$。此时分量间项为零而数据条件协方差项非零，故不能把额外不确定性误称为只有分量间方差。

## 来源与证据边界

本页的数值例与推导用于解释机制，不代表大型模型或真实业务上的实测效果。方法与接口依据如下，来源核验日期为 2026-09-06。

[^S64]: [Ho等：Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239)。2020；DDPM与去噪目标。
[^S65]: [Lipman等：Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747)。2022/2023；概率路径与向量场回归。
[^S66]: [Ho与Salimans：Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598)。2022；无分类器引导。

**返回与迁移：** [[AI/50-扩散模型/00-扩散模型-MOC|本主题课程地图]]；[[AI/00-开始/05-问题驱动知识图谱与难点导航|按问题跨主题继续]]。
