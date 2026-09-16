---
type: lesson
domain: mathematics
stage: 1
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[数学/40-微积分与优化/02-梯度方向导数与Jacobian]]"
difficulty: 进阶
estimated_minutes: 65
topics:
  - hessian
  - curvature
  - smoothness
  - learning-rate
tags:
  - mathematics/calculus
  - mathematics/optimization
  - mathematics/training-stability
---

# 曲率、Hessian 与学习率稳定性

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

## 本课目标

- 用二阶导数区分平坦、尖锐与负曲率方向；
- 从一维二次函数精确推出学习率为何会收敛、振荡或发散；
- 看懂 Hessian、方向曲率与 Hessian–vector product（HVP）的形状；
- 区分“一步有下降界”、“收敛到驻点”和“找到全局最优”。

## 直觉轨：梯度告诉你朝哪里走，曲率告诉你能走多远

梯度是当前点的坡度。但两条路可以在起点有相同坡度，其中一条很快变得平缓，另一条却立即急转。二阶导数描述“坡度改变得有多快”。

- 正且很大的曲率：像狭窄碗底，步子太大容易跨过中心反复振荡；
- 接近 0 的曲率：很平，梯度变化慢，训练可能进展缓慢；
- 负曲率：当前方向像山脊而不是碗底，驻点可能是鞍点或局部极大点。

## 1. 从一维二次函数得到精确稳定边界

设

$$
L(\theta)=\frac12\lambda\theta^2,
\qquad \lambda>0.
$$

一阶导数为 $L'(\theta)=\lambda\theta$，二阶导数为 $L''(\theta)=\lambda$。梯度下降一步：

$$
\theta_{t+1}=\theta_t-\eta\lambda\theta_t
=(1-\eta\lambda)\theta_t.
$$

重复 $t$ 步得

$$
\theta_t=(1-\eta\lambda)^t\theta_0.
$$

在 $\lambda>0$ 的本标量问题中，对所有初值都保证收敛到0，当且仅当下面的更新因子绝对值小于1。单独取初值 $\theta_0=0$ 时，迭代对任何有限学习率都保持为0，因此不能从这个特殊初值反推出稳定区间：

$$
|1-\eta\lambda|<1
\quad\Longleftrightarrow\quad
0<\eta<\frac{2}{\lambda}.
$$

| 学习率 | 更新因子 | 现象 |
| --- | --- | --- |
| $0<\eta<1/\lambda$ | $0<1-\eta\lambda<1$ | 同一侧单调接近 0 |
| $1/\lambda<\eta<2/\lambda$ | $-1<1-\eta\lambda<0$ | 在 0 两侧振荡，但幅度缩小 |
| $\eta=2/\lambda$ | $-1$ | 等幅振荡，损失不下降 |
| $\eta>2/\lambda$ | 绝对值大于 1 | 振荡发散 |

这是精确的二次函数结论，不是对任意神经网络的全局保证。当 $\lambda=0$ 时方向完全平坦；当 $\lambda<0$ 时，$\theta=0$ 是负曲率方向上的极大点，不能套用“正曲率碗底”的收敛结论。

## 2. Hessian 是多变量的二阶导数

对二阶可微的 $L:\mathbb R^p\to\mathbb R$，Hessian 定义为

$$
H(\theta)=\nabla^2L(\theta)\in\mathbb R^{p\times p},
\qquad
H_{ij}(\theta)=\frac{\partial^2L}{\partial\theta_i\partial\theta_j}
\in\mathbb R.
$$

例如 $L(\theta_1,\theta_2)=\theta_1^2+3\theta_1\theta_2+2\theta_2^2$，先求梯度 $(2\theta_1+3\theta_2,3\theta_1+4\theta_2)^\mathsf T$，再逐分量求导，得到 $H=\begin{pmatrix}2&3\\3&4\end{pmatrix}$。自检：$H_{12}=3$ 是标量，$Hv$ 是二维向量，$v^\mathsf THv$ 是标量；不能把其中任何一个的值域写成另一个的形状。

若二阶偏导在邻域内连续，混合偏导可交换，因而 $H=H^\mathsf T$。对任意单位方向 $v\in\mathbb R^p$，

$$
v^\mathsf THv
$$

是沿 $v$ 的二阶方向曲率。在驻点 $\nabla L=0$ 附近：

- $H$ 正定：二阶近似在所有方向向上，是严格局部极小的充分条件；
- $H$ 有正有负特征值：存在向上与向下方向，是鞍点；
- $H$ 只是半正定且有零特征值：二阶检验可能无法定论，需要高阶或邻域信息。

> [!warning] “梯度为 0”不等于“已经最优”
> 局部极小、局部极大、鞍点和某些平坦点都可以有零梯度。

## 3. 多维二次函数：最尖锐方向限制步长

设

$$
L(\theta)=\frac12\theta^\mathsf TA\theta,
$$

$A$ 为对称正定矩阵，特征值满足

$$
0<\lambda_{\min}\le\lambda_i\le\lambda_{\max}.
$$

在 $A$ 的正交特征向量基中，每个坐标独立按

$$
c_{i,t+1}=(1-\eta\lambda_i)c_{i,t}
$$

更新。所有方向同时收敛需要

$$
0<\eta<\frac{2}{\lambda_{\max}}.
$$

学习率必须顾及最尖锐的方向，但在平坦方向上又会前进得很慢。条件数

$$
\kappa=\frac{\lambda_{\max}}{\lambda_{\min}}
$$

大时，同一个全局步长很难同时适合所有方向。Momentum、自适应缩放、归一化和预条件的共同动机之一，就是减轻这种尺度不匹配；它们不等于精确 Newton 法，也不保证消除非凸性。

## 4. 二阶 Taylor 近似与下降引理

对小步 $\Delta$：

$$
L(\theta+\Delta)
\approx L(\theta)+\nabla L(\theta)^\mathsf T\Delta
+\frac12\Delta^\mathsf TH(\theta)\Delta.
$$

一阶项预测往哪里走，二阶项估计这个预测随步长变大会如何失真。

若在关心的区域上梯度是 $L_s$-Lipschitz：

$$
\lVert\nabla L(x)-\nabla L(y)\rVert_2
\le L_s\lVert x-y\rVert_2,
$$

则下降引理给出

$$
L(\theta-\eta g)
\le L(\theta)
-\eta\left(1-\frac{L_s\eta}{2}\right)\lVert g\rVert_2^2,
\qquad g=\nabla L(\theta).
$$

所以当 $0<\eta<2/L_s$ 且该光滑性界对这一步有效时，可保证损失不上升（非零梯度时严格下降）。这仍然不等于找到全局最优：非凸目标可以有多个极小、鞍点和学习率随位置改变的局部尺度。

## 5. HVP：不显式存储巨大 Hessian

对方向 $v\in\mathbb R^p$，Hessian–vector product 为

$$
Hv
=\left.\frac{\mathrm d}{\mathrm d\epsilon}
\nabla L(\theta+\epsilon v)\right|_{\epsilon=0}.
$$

它的结果形状是 $p$，而完整 Hessian 有 $p^2$ 个元素。自动微分可以通过梯度的 JVP/VJP 组合计算 HVP，不必实体化 $H$。中心差分也能做小规模核验：

$$
Hv\approx
\frac{\nabla L(\theta+\epsilon v)-
\nabla L(\theta-\epsilon v)}{2\epsilon}.
$$

$\epsilon$ 太大时截断误差大，太小时两个相近梯度相减会放大舍入误差。因此有限差分是核验工具，不是“越小步长越精确”。

## 6. 连接 LLM 训练与 CUDA

- 在 [[AI/20-LLM/30-训练/02-训练循环Checkpoint与复现|训练循环、Checkpoint 与复现]] 中，loss spike 可能意味着当前学习率跨过了某些尖锐方向的稳定区间；也可能来自数据、精度或实现错误，不能只凭曲率一个解释定论。
- 梯度裁剪限制输入优化器的梯度范数，但不改变目标的 Hessian，因而不是曲率问题的通用修复。
- 在 [[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|Reduction、Softmax 与 GEMM]] 中，HVP 与梯度一样最终分解为矩阵乘法、逐元素算子和归约；并行计算的舍入顺序可影响数值，但不改变形状契约。

## 练习与成功标准

设

$$
L(x,y)=\frac12x^2+\frac92y^2,
$$

则 $H=\operatorname{diag}(1,9)$。

1. 分别对 $\eta=0.1,0.2,0.25$ 写出 $x,y$ 坐标的更新因子。
2. 判断哪些学习率会使两个坐标都收敛。
3. 取 $v=(0,1)^\mathsf T$，计算 $v^\mathsf THv$并解释它为何是最尖锐方向的曲率。
4. 解释为何这道题能预测二次函数的精确稳定性，却不能单独证明 Transformer 训练会收敛。

**成功标准**：$\eta=0.1$ 的因子为 $(0.9,0.1)$，两方向收敛；$\eta=0.2$ 为 $(0.8,-0.8)$，仍收敛但 $y$ 振荡；$\eta=0.25$ 为 $(0.75,-1.25)$，$y$ 发散。得到共同边界 $0<\eta<2/9$，以及 $v^\mathsf THv=9$。

## 导航

- 上一站：[[数学/40-微积分与优化/05-初始化归一化与训练稳定性|初始化、归一化与训练稳定性]]
- 实验：[[数学/40-微积分与优化/80-梯度与反向传播检查实验|梯度与反向传播检查实验]]
- 返回：[[数学/40-微积分与优化/00-微积分与优化-MOC|微积分与优化 MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/15-微积分/11-多元极限偏导与全微分|多元极限偏导与全微分]]；[[数学/15-微积分/12-多元链式法则隐函数与约束优化|多元链式法则隐函数与约束优化]]；[[数学/20-线性代数与几何/17-矩阵范数条件数与数值稳定性|矩阵范数条件数与数值稳定性]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
