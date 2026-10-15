---
type: lesson
domain: artificial-intelligence
content_status: draft
evidence_status: unreviewed
aliases:
- LQG分离原理
- 估计器控制器闭环极点
sources:
- https://ee363.stanford.edu/archive/lectures/lqg.pdf
- https://berkeley-me233.github.io/static/UCB_ME233_lecture_notes_2014_Spring.pdf
- https://underactuated.mit.edu/output_feedback.html
prerequisites:
- '[[AI/45-机器人与具身智能/20-状态估计与LQG/02-可检测性稳态滤波与误差诊断]]'
- '[[AI/45-机器人与具身智能/10-LQR与约束控制/02-无限时域稳定化解残差与极点]]'
---

# LQG 分离原理与闭环极点

**读者问题：** Kalman 给出状态估计，LQR 假设能看到状态。把真实状态替换成估计值，为什么有时仍是最优控制器？要回答两件不同的事：有限时域的 **LQG 最优性**，以及线性闭环的 **稳定性分离**。

## 先把问题条件写全

有限时域系统为

$$
x_{k+1}=Ax_k+Bu_k+w_k,\qquad y_k=Hx_k+r_k,
$$

其中 $x_0$ 是均值和协方差已知的 Gaussian；$w_k,r_k$ 是零均值 Gaussian，跨时间相互独立，也与 $x_0$ 独立，协方差已知；$u_k$ 只能由当前及过去的读数与输入决定。目标是

$$
J=\mathbb E\!\left[
x_N^\mathsf TQ_fx_N+
\sum_{k=0}^{N-1}
(x_k^\mathsf TQx_k+u_k^\mathsf TRu_k)
\right],
$$

其中 $Q,Q_f\succeq0$、$R\succ0$，输入没有盒约束、速率限制或逻辑约束。模型矩阵和噪声统计不随控制动作改变，传感器也不会因“主动探测”动作得到不同质量。这些条件排除了产生双重效应的情形。

[Stanford EE363 Lecture 10](https://ee363.stanford.edu/archive/lectures/lqg.pdf)从部分观测动态规划推导此问题；[MIT Underactuated Output Feedback](https://underactuated.mit.edu/output_feedback.html)也强调 LQG 中的估计—控制分离在一般输出反馈问题中并不成立。


用 [[AI/13-搜索推理与规划/20-部分可观测决策/01-有限模型belief与决策状态#相同均值为什么不保证相同动作|同均值、不同最优行动]] 检查本页条件边界，再进入 [[AI/13-搜索推理与规划/20-部分可观测决策/02-beliefBellman与独立策略树#三次机会：第二次测量只在某个分支值得买|主动观测的多步策略树]]。该有限例的非线性行动后果、离散终止选择及可选付费观测都与此处无约束线性Gaussian二次控制不同；本页误差分布不受控制改变的分离条件不能为它省去观测价值比较。返回本页时仍按上列条件解释均值控制，不将有限反例当成LQG推导错误。

## 条件期望把未知状态拆成“均值 + 误差”

令历史 $\mathcal Y_k=(y_0,\ldots,y_k,u_0,\ldots,u_{k-1})$，

$$
\hat x_k=\mathbb E[x_k\mid\mathcal Y_k],\qquad
e_k=x_k-\hat x_k,\qquad
\mathbb E[e_k\mid\mathcal Y_k]=0.
$$

对任意对称矩阵 $M$，

$$
\mathbb E[x_k^\mathsf TMx_k\mid\mathcal Y_k]
=\hat x_k^\mathsf TM\hat x_k+\operatorname{tr}(MP_k).
$$

交叉项消失，因为条件误差均值为零。在线性 Gaussian 模型中，Kalman 协方差递推不依赖实际读数，也不依赖当前选择的确定控制值。于是 Bellman 值函数可写为

$$
V_k(\mathcal Y_k)=\hat x_k^\mathsf TS_k\hat x_k+c_k,
$$

其中 $c_k$ 收集估计协方差和噪声带来的 trace 项。对 $u_k$ 做最小化时，$c_k$ 与 $u_k$ 无关，剩下的配方与全状态 LQR 完全相同：

$$
u_k^*=-K_k\hat x_k,
$$

$$
K_k=(R+B^\mathsf TS_{k+1}B)^{-1}B^\mathsf TS_{k+1}A.
$$

$S_k$ 仍按[[AI/45-机器人与具身智能/10-LQR与约束控制/01-从Bellman配方到Riccati递推|有限时域LQR的Riccati递推]]反向计算；$\hat x_k,P_k$ 按 Kalman 正向计算。控制增益不依赖 $H,W,R_{\text{measurement}}$，滤波增益也不依赖控制代价 $Q,R_{\text{control}}$。这就是“分别设计”的精确含义，并不是估计误差对代价没有影响；它仍通过 trace 项增加最优代价。

## 稳定性分离来自块三角结构

现在看时不变稳态实现。为避免索引歧义，固定一拍顺序：

1. 用 $y_k$ 把先验更新为后验 $\hat x_k$；
2. 施加 $u_k=-K\hat x_k$；
3. 预测到下一拍；下一次测量再以稳态当前增益 $L$ 更新。

令后验误差 $e_k=x_k-\hat x_k$，先忽略噪声以检查齐次稳定性。因为 $\hat x_k=x_k-e_k$，

$$
x_{k+1}=(A-BK)x_k+BK e_k,
$$

$$
e_{k+1}=(I-LH)A e_k.
$$

因此

$$
\begin{bmatrix}x_{k+1}\\e_{k+1}\end{bmatrix}
=
\underbrace{\begin{bmatrix}
A-BK&BK\\
0&(I-LH)A
\end{bmatrix}}_{A_{\mathrm{LQG}}}
\begin{bmatrix}x_k\\e_k\end{bmatrix}.
$$

块上三角矩阵的特征值是两个对角块特征值的并集：

$$
\operatorname{eig}(A_{\mathrm{LQG}})
=\operatorname{eig}(A-BK)\cup
\operatorname{eig}((I-LH)A).
$$

这证明了线性无约束闭环的稳定性可以分别检查。若使用“预测器形式”$\hat x_{k+1}^-=A\hat x_k^-+Bu_k+G(y_k-H\hat x_k^-)$，估计块写成 $A-GH$；$G=AL$ 对应另一时间坐标。先选时序再写极点，不能混用增益。

## 本例的两组极点

沿用控制代价

$$
Q=\operatorname{diag}(1,0.1),\qquad R_u=0.05,
$$

无限时域 LQR 稳定化增益为

$$
K=\begin{bmatrix}3.21775154&2.73329391\end{bmatrix}.
$$

上一课的稳态当前测量增益是

$$
L=\begin{bmatrix}0.43096685\\0.60347429\end{bmatrix}.
$$

控制块极点为

$$
0.694493\pm0.188084i,
$$

估计误差块极点为

$$
0.724169\pm0.211216i.
$$

直接构造 $4\times4$ 增广矩阵，得到的四个极点逐项等于这两个集合的并集，最大数值差小于 $10^{-12}$。

![[AI/45-机器人与具身智能/20-状态估计与LQG/assets/lqg-separation-poles.svg|620]]

*图：圆是控制块极点，方块是估计块极点，叉号是增广闭环极点。重合验证块三角谱；单位圆内只说明本线性齐次模型局部/全局线性稳定。*

## 无限时域设计条件要两边都满足

对离散时不变问题，常用条件链是：

- 控制端：$(A,B)$ 可稳定，且未被 $Q^{1/2}$ 看到的不稳定模态不存在，即 $(Q^{1/2},A)$ 可检测；$R_u\succ0$。这样选择 LQR 的稳定化 DARE 解，使 $A-BK$ 稳定。
- 估计端：$(H,A)$ 可检测，$(A,W^{1/2})$ 可稳定，且测量协方差正定。这样选择滤波 Riccati 的稳定化解，使相应误差块稳定。
- 组合端：实现使用同一线性模型和一致的更新时间索引，执行器实际施加 $-K\hat x$，没有饱和或额外非线性。

[UC Berkeley ME233 Lecture 6，PDF第69–73页（讲义第6-13至6-22页）](https://berkeley-me233.github.io/static/UCB_ME233_lecture_notes_2014_Spring.pdf)从条件均值与 trace 分解进入有限/稳态 LQG，并把分离后的闭环特征值分成 LQ 状态反馈与 Kalman 滤波两组；本页的后验误差坐标是同一分离结构的显式块三角写法。

“两个 Riccati 残差都很小”仍需配合两个对角块的极点检查；[[AI/45-机器人与具身智能/10-LQR与约束控制/02-无限时域稳定化解残差与极点|LQR课中的双根反例]]已经说明代数解不自动是稳定化解。

## 最优分离与稳定分离不要混淆

- **LQG 最优性**：在本页开头的线性 Gaussian、二次期望代价、无约束条件下，Kalman 条件均值加 LQR 是所有因果输出反馈策略中的最优策略。
- **线性稳定性分离**：只要某个状态反馈块和某个观测器误差块分别稳定，块三角组合也稳定。这里的观测器可以不是统计最优的 Kalman 滤波器。
- **性能与安全**：即使稳定，瞬态、方差、尾部概率、执行器峰值和状态约束仍可能不合格。

## 练习与完整答案

1. **估计器更慢会改变 LQR 极点吗？** 不改变 $A-BK$，但会把较慢的估计极点加入整个输出反馈闭环，真实状态瞬态会受上三角耦合 $BK e_k$ 影响。
2. **为什么 $BK$ 位于右上块？** 控制器使用 $\hat x=x-e$，所以 $-BK\hat x=-BKx+BK e$；估计误差像附加驱动一样进入真实状态。
3. **Gaussian 假设在稳定性块三角证明中出现了吗？** 没有。齐次线性观测器的极点分离是代数事实。Gaussian 假设用于 Kalman 条件分布和 LQG 最优性。
4. **传感动作能主动降低未来观测噪声时还能直接分离吗？** 一般不能。控制同时影响物理状态和未来信息，协方差项可能依赖动作，动态规划最小化不再只剩全状态 LQR 配方。

下一课：[[AI/45-机器人与具身智能/20-状态估计与LQG/04-偏置噪声设错饱和与安全边界|偏置、噪声设错、饱和与安全边界]]。
