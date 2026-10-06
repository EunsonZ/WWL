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
difficulty: 高中起点
estimated_minutes: 65
topics:
  - sgd
  - momentum
  - adam
  - adamw
  - weight-decay
tags:
  - mathematics/optimization
  - mathematics/training
---

# SGD、Momentum、Adam 与 AdamW

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

## 本课目标

- 区分“梯度怎样算”和“优化器怎样使用梯度”；
- 写出四种优化器的状态、形状和更新顺序；
- 理解 Adam 的偏差修正与数值稳定项；
- 严格区分 L2 正则、耦合 weight decay 和 AdamW 的解耦衰减。

## 直觉轨：下山者的四种记忆

- **SGD**：只看眼前坡度走一步，没有跨步记忆。
- **Momentum**：记住过去的平均方向，减少狭长山谷里的左右摇摆。
- **Adam**：既记方向的一阶矩，又记每个坐标梯度平方的二阶原始矩，对不同坐标自适应缩放。
- **AdamW**：在 Adam 自适应步之外，单独把指定参数向零收缩。

优化器不改变当前梯度的数学定义；它改变从梯度到参数步长的映射。

## 统一问题与形状

设更新前参数 $\theta_{t-1}\in\mathbb{R}^{p}$，在第 $t$ 个小批次上计算随机梯度

$$
g_t=\nabla_\theta L_{B_t}(\theta_{t-1})\in\mathbb{R}^{p}.
$$

$g_t$ 只有在小批次按目标数据分布抽样，且样本权重与损失归一化同总体目标一致时，才可以视为总体目标梯度的无偏带噪估计。分层抽样、重要性抽样、非均匀采样或错误的归一化若没有相应权重修正，可以让估计产生偏差；“带噪”不自动等于“无偏”。下表使用逐元素运算：

| 优化器 | 持久状态 | 每项形状 |
| --- | --- | --- |
| SGD | 步数可选 | 无与参数同形状态 |
| Momentum | $m_t$ | 与 $\theta$ 相同 |
| Adam | $m_t,v_t,t$ | $m,v$ 与 $\theta$ 相同；$t$ 为标量 |
| AdamW | $m_t,v_t,t$ | 与 Adam 相同，另有超参数 $\lambda$ |

大型模型中，Adam 类优化器仅状态就常需约两份参数大小的存储（未计梯度、主权重副本与实现开销），因此优化器选择也影响显存。

## SGD

$$
\theta_t=\theta_{t-1}-\eta g_t,
$$

其中学习率 $\eta>0$。若 $L$ 在局部光滑且 $\eta$ 足够小，负梯度的一阶近似会降低损失；这不是每一步必降或全局收敛保证。

## Momentum

本课采用指数移动平均约定：

$$
m_t=\beta m_{t-1}+(1-\beta)g_t,
\qquad
\theta_t=\theta_{t-1}-\eta m_t,
$$

$m_0=0$，$0\le\beta<1$。有些库省略 $(1-\beta)$ 或把状态命名为 velocity，导致同名超参数的有效步长不同；比较实现前必须核对公式。

展开可见：

$$
m_t=(1-\beta)\sum_{i=1}^{t}\beta^{t-i}g_i,
$$

越近的梯度权重越大。初期因为从零开始，$m_t$ 偏小；经典 momentum 常不做偏差修正，但必须意识到该过渡期。

## Adam

Adam 同时维护一阶矩和梯度平方的二阶原始矩：

$$
\begin{aligned}
m_t&=\beta_1m_{t-1}+(1-\beta_1)g_t,\\
v_t&=\beta_2v_{t-1}+(1-\beta_2)g_t\odot g_t,\\
\hat m_t&=\frac{m_t}{1-\beta_1^t},\\
\hat v_t&=\frac{v_t}{1-\beta_2^t},\\
\theta_t&=\theta_{t-1}-\eta\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}.
\end{aligned}
$$

所有除法、平方和开方都逐元素进行。$m_0=v_0=0$ 使早期移动平均偏向零，$1-\beta^t$ 做偏差修正。$\epsilon$ 避免分母为零并影响极小梯度坐标的有效步长；不同实现可能把它放在根号内，不能在不核对实现时假定完全等价。

## L2 正则与 weight decay 的边界

先分清三个概念。

### 1. 目标中的 L2 正则

把目标定义为

$$
L_{\text{reg}}(\theta)=L_{\text{data}}(\theta)+\frac{\lambda}{2}\lVert\theta\rVert_2^2,
$$

则送入优化器的梯度为

$$
g_{\text{reg}}=\nabla L_{\text{data}}+\lambda\theta.
$$

这是对目标函数的定义。

### 2. SGD 中的耦合衰减

把 $g_{\text{reg}}$ 放入普通 SGD：

$$
\theta_t=(1-\eta\lambda)\theta_{t-1}-\eta\nabla L_{\text{data}}.
$$

因此在无 momentum 的 SGD 中，L2 正则与乘法式 weight decay 等价。

### 3. AdamW 的解耦衰减

若把 $\lambda\theta$ 混进 Adam 的梯度，它会被一阶、二阶矩共同自适应缩放，不再等价于统一乘上 $(1-\eta\lambda)$。AdamW 将收缩从梯度变换中分离：

$$
\theta_t=(1-\eta\lambda)\theta_{t-1}
-\eta\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon},
$$

其中 $m_t,v_t$ 仅由数据损失梯度（以及你明确加入的其他梯度项）更新。实现也可把两项按等价顺序写成一次原地更新，但语义必须是解耦。

> [!warning] 参数组边界
> weight decay 只作用于配置中被选中的参数。Transformer 实践中常对矩阵权重衰减，而不对 bias、LayerNorm/RMSNorm 的缩放与偏移衰减；这是常用经验，不是数学定理。共享权重、embedding、相对位置参数是否衰减需要显式决定并记录，不能只按名字碰运气。

## 一个坐标的一步 Adam

取 $g_1=2$、$m_0=v_0=0$、$\beta_1=0.9$、$\beta_2=0.999$：

$$
m_1=0.2,\quad v_1=0.004,\quad
\hat m_1=2,\quad\hat v_1=4.
$$

忽略 $\epsilon$，修正方向为 $\hat m_1/\sqrt{\hat v_1}=2/2=1$；未修正方向却为 $0.2/\sqrt{0.004}\approx3.16228$。分子虽然小，分母也小，不能仅由一阶矩推断更新缩小十倍。

对任意非零首步梯度 $g_1$，未修正方向为

$$
\frac{(1-\beta_1)g_1}{\sqrt{(1-\beta_2)g_1^2}}
=\frac{1-\beta_1}{\sqrt{1-\beta_2}}\operatorname{sign}(g_1).
$$

保留 epsilon 时，两者分别为 $(1-\beta_1)g_1/(\sqrt{1-\beta_2}|g_1|+\epsilon)$ 与 $g_1/(|g_1|+\epsilon)$。偏差修正针对零初始化的衰减权重总和；非平稳梯度下不能宣称它无偏估计了当前梯度分布。

自检：解释为什么两个矩都偏小却可能让归一化更新偏大，再把 $\beta_1=0.9,\beta_2=0.99$ 代入比较。检查点：忽略 epsilon 时比例变成 1；偏差影响取决于两项共同作用。[Adam 官方算法定义](https://docs.pytorch.org/docs/2.14/generated/torch.optim.Adam.html)。

## 训练循环的更新边界

一次正确的概念顺序是：前向 → 标量损失 → 清理旧梯度 → 反向累积当前梯度 → 可选梯度裁剪 → 优化器读取梯度并更新状态/参数 → 调度器按约定更新时间。梯度累积时要明确损失是求和还是平均；否则有效学习率会随累积步数改变。

## 练习与成功标准

设一维参数 $\theta=10$、数据梯度 $g=2$、$\eta=0.1$、$\lambda=0.01$。在第 2 题中，先只比较“解耦收缩 + 普通 SGD 数据步”；若改用标准第一步 AdamW，则另取 $m_0=v_0=0$、$\beta_1=0.9$、$\beta_2=0.999$ 并忽略很小的 $\epsilon$。

1. 计算一步无正则 SGD；
2. 计算一步解耦 decay 的普通 SGD 数据步，并另算上述标准第一步 AdamW；
3. 说明为何把 $g+\lambda\theta$ 送入 Adam 不等于统一收缩。

**成功标准**：得到普通 SGD 后 $9.8$；“解耦收缩 + 普通 SGD 数据步”为 $10(1-0.001)-0.2=9.79$；标准第一步 AdamW 的自适应方向约为 1，所以结果为 $10(1-0.001)-0.1=9.89$；并明确说出耦合项 $\lambda\theta$ 会进入 Adam 的 $m$、$v$，因坐标自适应缩放而破坏统一衰减。

上一站：[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]] · 下一站：[[数学/40-微积分与优化/05-初始化归一化与训练稳定性|初始化、归一化与训练稳定性]] · 返回：[[数学/40-微积分与优化/00-微积分与优化-MOC|微积分与优化 MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/15-微积分/11-多元极限偏导与全微分|多元极限偏导与全微分]]；[[数学/15-微积分/12-多元链式法则隐函数与约束优化|多元链式法则隐函数与约束优化]]；[[数学/20-线性代数与几何/17-矩阵范数条件数与数值稳定性|矩阵范数条件数与数值稳定性]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
