---
type: lesson
domain: mathematics
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[数学/20-线性代数与几何/01-向量矩阵与张量]]"
difficulty: 入门
stage: 1
estimated_minutes: 65
topics:
  - exponential
  - logarithm
  - softmax
  - logsumexp
  - log-softmax
  - temperature-sampling
  - numerical-stability
tags:
  - mathematics/information-theory
  - mathematics/numerical-stability
  - mathematics/lesson
---

# 指数、对数、Softmax 与 LogSumExp

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

## 本课目标

学完后，你应能：

- 从高中代数解释指数与对数为何成对出现；
- 把任意实数 logits 变成总和为 $1$ 的概率；
- 推导 Softmax 的平移不变性和“减最大值”稳定形式；
- 推导稳定 LogSumExp、log-softmax 与 one-hot 交叉熵；
- 推导温度对 Softmax 概率比的影响，并区分原始、温度后与最终采样分布；
- 识别溢出、下溢、`log(0)` 与“先算概率再取对数”的风险。

## 1. 指数：把加法差变成倍率

对任意实数 $a,b$：

$$
e^{a+b}=e^ae^b,
\qquad
\frac{e^a}{e^b}=e^{a-b}.
$$

所以分数相差 $a-b$，经过指数后会变成倍率 $e^{a-b}$。例如两个 logit 相差 $\ln 2$，指数权重恰好相差 $2$ 倍。

指数还有一个关键性质：

$$
e^z>0\quad\text{对所有实数 }z.
$$

这适合制造概率的非负权重，但 $e^z$ 本身还不是概率，因为所有权重之和通常不等于 $1$。

## 2. 对数：指数的反函数

若 $e^a=b$，则 $\ln b=a$。对数把乘法还原成加法：

以下恒等式在实数范围要求 $a>0$、$b>0$：

$$
\ln(ab)=\ln a+\ln b,
\qquad
\ln\frac ab=\ln a-\ln b.
$$

语言模型中，序列概率是许多条件概率的乘积，容易变得极小；log-prob 把它变成许多有限数的和：

$$
\ln\prod_{t=1}^{T}p_t=\sum_{t=1}^{T}\ln p_t.
$$

这里要求每个 $p_t>0$。若任一项为零，则序列概率为零；采用扩展实数约定时 log-prob 记为 $-\infty$，不能继续把它当作有限实数参与普通代数变形。

## 3. logits 是什么

设模型对 $K$ 个候选 token 输出实数向量：

$$
z=(z_1,\dots,z_K)\in\mathbb R^K.
$$

这些 $z_i$ 叫 logits。它们可以为负，也不要求总和为 $1$。绝对大小不是概率；重要的是差值。例如：

$$
z=(2,1,0)
$$

表示第一项比第二项多 $1$ 个 logit 单位，经指数后权重比为 $e:1$。

## 4. Softmax：指数化，再归一化

先令权重 $w_i=e^{z_i}>0$，再除以总和：

$$
q_i=\operatorname{softmax}(z)_i
=\frac{e^{z_i}}{\sum_{j=1}^{K}e^{z_j}}.
$$

它确实是概率分布，因为：

$$
q_i>0,
\qquad
\sum_iq_i=
\frac{\sum_i e^{z_i}}{\sum_j e^{z_j}}=1.
$$

任意两项的概率比为：

$$
\frac{q_i}{q_j}=e^{z_i-z_j}.
$$

所以 Softmax 保存的是 logit 差对应的相对倍率。

## 5. 平移不变性：所有 logits 加同一常数，概率不变

对任意常数 $c$：

$$
\begin{aligned}
\operatorname{softmax}(z+c)_i
&=\frac{e^{z_i+c}}{\sum_je^{z_j+c}}\\
&=\frac{e^ce^{z_i}}{e^c\sum_je^{z_j}}\\
&=\operatorname{softmax}(z)_i.
\end{aligned}
$$

这不是近似，而是精确代数恒等式。它允许我们为数值安全自由选择 $c$。

## 6. 为什么朴素 Softmax 会溢出

浮点数能表示的范围有限。数学上的 $e^{1000}$ 是有限正数，但常见双精度浮点无法容纳它，程序会溢出为错误或 `inf`。随后出现：

$$
\frac{\infty}{\infty},
$$

结果通常是 `nan`，不再是概率。

利用平移不变性，令：

$$
m=\max_jz_j,
\qquad
c=-m.
$$

得到稳定 Softmax：

$$
\boxed{
q_i=\frac{e^{z_i-m}}{\sum_je^{z_j-m}}
}.
$$

此时所有 $z_i-m\le0$，最大项指数为 $e^0=1$，不会发生正向指数溢出。很小的项可能下溢为 $0$，但这通常只是在有限精度中把“相对于最大项小到可忽略”的概率置零。

> [!warning] 减去平均值不够
> 平均值不能保证最大平移后 logit 不大于 $0$。减最大值才提供明确的上界。

## 7. LogSumExp：概率归一化器的对数

定义：

$$
\operatorname{LSE}(z)
=\log\sum_{j=1}^{K}e^{z_j}.
$$

直接计算仍可能先在 $e^{z_j}$ 溢出。令 $m=\max_jz_j$：

$$
\begin{aligned}
\operatorname{LSE}(z)
&=\log\sum_je^{z_j}\\
&=\log\sum_je^{m}e^{z_j-m}\\
&=\log\left(e^m\sum_je^{z_j-m}\right)\\
&=m+\log\sum_je^{z_j-m}.
\end{aligned}
$$

因此稳定形式是：

$$
\boxed{
\operatorname{LSE}(z)=m+\log\sum_je^{z_j-m}
}.
$$

还有一个直觉边界：

$$
m\le\operatorname{LSE}(z)\le m+\log K.
$$

证明很直接：平移后至少有一个指数为 $1$，至多有 $K$ 个指数各不超过 $1$。

## 8. log-softmax 与交叉熵的稳定形式

对 Softmax 取对数：

$$
\begin{aligned}
\log q_i
&=\log\frac{e^{z_i}}{\sum_je^{z_j}}\\
&=z_i-\log\sum_je^{z_j}\\
&=z_i-\operatorname{LSE}(z).
\end{aligned}
$$

所以：

$$
\boxed{\operatorname{logsoftmax}(z)_i=z_i-\operatorname{LSE}(z)}.
$$

若正确类别是 $y$，one-hot 交叉熵为：

$$
\begin{aligned}
\ell(z;y)
&=-\log q_y\\
&=\operatorname{LSE}(z)-z_y.
\end{aligned}
$$

这些是实数恒等式；浮点实现不能先形成带巨大偏移的 LSE 再相减。令 $a_i=z_i-m$、$s=\log\sum_j e^{a_j}$，直接计算 $\log q_i=a_i-s$、$\ell=s-a_y$。避免以下路径：

1. 先计算可能溢出或下溢的 Softmax；
2. 再对某个可能已经变成 $0$ 的概率取对数。

还要避免第三条路径：当 $z=(10^{16},10^{16})$ 时，binary64 的 $m+\log 2$ 舍入回 $m$；再算 $z_i-\operatorname{LSE}(z)$ 得到零，指数化后得到 $(1,1)$，损失也变成零。中心化路径保留 $a=(0,0)$ 和 $s=\log 2$，得到 $(0.5,0.5)$ 与 $\ell=\log 2$。LSE 单独的绝对误差很小，不代表把它接到消去式后仍稳定。

对于软目标分布 $P=(p_1,\dots,p_K)$，要求 $p_i\ge0$ 且 $\sum_i p_i=1$。实数恒等式是：

$$
H(P,Q)=-\sum_ip_i\log q_i
=-\sum_ip_i\bigl(z_i-\operatorname{LSE}(z)\bigr)
=\operatorname{LSE}(z)-\sum_ip_iz_i.
$$

浮点实现沿用中心化坐标：令 $a_i=z_i-m$、$s=\log\sum_j e^{a_j}$，则计算

$$
H(P,Q)=s-\sum_i p_i a_i.
$$

最后一步使用了目标分布归一化：$\operatorname{LSE}(z)=m+s$、$z_i=m+a_i$ 且 $\sum_i p_i=1$，公共偏移项才会抵消。不要在浮点中先形成带大偏移的 LSE 和加权 logit，再让两项相减。这里 $P$ 是目标分布，$Q=\operatorname{softmax}(z)$ 是模型分布。

## 9. 温度的 Softmax 代数连接

本节只说明温度怎样改变 Softmax 的概率比；温度、Top-k、Top-p 的完整定义、并列处理、过滤顺序与实验契约统一维护在 [[数学/30-概率与统计/04-温度Top-k与Top-p采样|温度、Top-k 与 Top-p 采样]]。

温度 $T>0$ 把 logits 变为 $z_i/T$：

$$
q_i(T)=\frac{e^{z_i/T}}{\sum_je^{z_j/T}}.
$$

概率比变为：

$$
\frac{q_i(T)}{q_j(T)}=e^{(z_i-z_j)/T}.
$$

- $0<T<1$：差值被放大，分布更尖锐，低熵候选更集中；
- $T=1$：原始 Softmax；
- $T>1$：差值被压缩，分布更平坦，通常熵更高；
- $T\to0^+$：趋近于只选择最大 logit（并列最大值需另行处理）；
- $T\to\infty$：有限 logits 下趋近均匀分布。

浮点计算先中心化，再除温度：$a_i=(z_i-m)/T$。这样 $(1000,999)$ 与 $T=10^{-308}$ 不会先在 $1000/T$ 处溢出。伴随实验使用有限 binary64、非空输入和有限正温度；无穷掩码不在其接口内。若极端异号使中心化本身溢出，或缩放后超范围，显式报错。指数下溢可得到零概率，log-prob 仍直接由 $a_i-s$ 计算。输入平移若已丢失原差值，算法无法恢复这些信息。

温度变换后的分布还可能继续经过候选截断、token 屏蔽或其他惩罚并重新归一化。因此“原始 Softmax”“温度后分布”和“最终实际采样分布”是不同层次；具体集合定义不在本页重复。

## 10. 从 logits 连接到训练与分布比较

### 10.1 next-token 训练

每个位置产生词表 logits $z$。正确 token 为 $y$ 时，交叉熵的实数恒等式是：

$$
\ell=\operatorname{LSE}(z)-z_y.
$$

浮点计算先取 $m=\max_i z_i$，再令 $a_i=z_i-m$、$s=\log\sum_i e^{a_i}$，直接计算 $\ell=s-a_y$。不要把单独算出的 $\operatorname{LSE}(z)$ 再减去 $z_y$ 称为稳定实现；大公共偏移会在这一步消去。若训练标签是软目标分布，使用上一节要求归一化的 $s-\sum_i p_i a_i$。完整的 NLL 与困惑度定义见 [[数学/30-概率与统计/03-似然负对数似然与困惑度|似然、负对数似然与困惑度]]；分布与样本角色见 [[数学/50-信息论/01-熵交叉熵KL散度与互信息#7. 与 next-token NLL 的关系|与 next-token NLL 的关系]]。

### 10.2 蒸馏

教师和学生分别对 logits 除以温度，再用 log-softmax 获得稳定 log-prob。教师概率提供权重 $P$，学生 log-prob 属于 $Q$。实现 KL 时必须核对库函数的参数方向，不能只凭参数名猜数学方向。

### 10.3 序列 log-prob 目标

需要比较序列时，应把各位置的目标 token log-softmax 求和形成序列 log-prob。长序列必须留在 log 空间；若把每个 token 概率先相乘，很快会下溢到 $0$。具体偏好目标属于应用算法页，本页只维护这一稳定计算原则。

### 10.4 分布漂移

从两组 logits 比较模型分布时，应直接用各自的 `log_softmax` 构造所需方向的 KL，并写清谁是 $P$、谁是 $Q$ 以及测量切片。大词表、低精度和极端 logits 都可能让“先 Softmax 再 log”的实现失真。数学方向与评测边界见 [[数学/50-信息论/01-熵交叉熵KL散度与互信息#9. 应用出口：偏好目标与模型分布比较|偏好目标与模型分布比较]]。

## 11. 常见错误清单

| 错误 | 后果 | 稳定做法 |
| --- | --- | --- |
| 直接算 `exp(1000)` | 溢出 | 先减最大 logit |
| Softmax 后再 `log` | 小概率可能已下溢为 0 | 直接用 log-softmax |
| 长序列概率逐项相乘 | 很快下溢为 0 | 累加 log-prob |
| 把 logits 当概率 | 可为负且不归一化 | 明确经过 Softmax |
| 温度后忘记重新归一化 | 总和不为 1 | 对 $z/T$ 做完整 Softmax |
| top-k/top-p 后不归一化 | 不是概率分布 | 在保留集合内重归一化 |
| 只写“KL”不写方向 | 含义不确定 | 始终写 $D_{\mathrm{KL}}(P\Vert Q)$ |

## 12. 练习

### 练习 1：平移

证明 $z=(1001,1000,999)$ 与 $z'=(1,0,-1)$ 的 Softmax 完全相同，并说明计算哪一个更安全。

### 练习 2：LSE 边界

对 $z=(2,1,0)$，用 $m\le\operatorname{LSE}(z)\le m+\log K$ 给出范围，再用稳定公式计算近似值。

### 练习 3：one-hot 交叉熵

给定 $z=(2,1,0)$，正确类别 $y=2$（从 0 开始编号），先写实数恒等式，再用 $m$、$a_i=z_i-m$ 和 $s=\log\sum_i e^{a_i}$ 计算损失。解释为什么它比 $y=0$ 时的损失大。

### 练习 3b：共同偏移下的消去

对 binary64 输入 $z=(10^{16},10^{16})$、$y=0$，比较先稳定计算 LSE 再算 $\operatorname{LSE}(z)-z_y$，与先令 $a_i=z_i-m$ 再算 $s-a_y$。写出两条路径的结果，并解释为什么中心化能避免运算中的大数相消；若两个本来不同的实数 logits 在输入转换时已舍入成同一 binary64 值，平移不变性还能否恢复它们的差值？

### 练习 4：温度

不用精确计算，判断对 $z=(2,1,0)$ 使用 $T=0.5$ 与 $T=2$ 时，最大项概率和分布熵相对 $T=1$ 如何变化。

### 练习 5：实现审查

阅读以下伪代码，指出至少两个风险：

```python
probabilities = [exp(x) / sum(exp(y) for y in logits) for x in logits]
sequence_probability = product(probabilities[target[t]] for t in positions)
loss = -log(sequence_probability)
```

## 13. 参考答案与成功标准

1. 两向量相差常数 $1000$，Softmax 平移不变；$z'$ 的指数不会溢出。
2. $2\le\operatorname{LSE}(z)\le2+\ln3$；稳定计算约为 $2.4076$。
3. $m=2$，所以 $a=(0,-1,-2)$，$s=\log(1+e^{-1}+e^{-2})\approx0.4076$。对 $y=2$，稳定损失为 $s-a_2=s+2\approx2.4076$；对 $y=0$ 则为 $s-a_0=s\approx0.4076$。正确项 logit 最小，模型给它的概率最小，所以惩罚最大。
3b. 单独的稳定 LSE 为 $m+\log2$，在 binary64 中舍入回 $m$；再减 $z_0=m$ 得到 0。中心化后 $a=(0,0)$、$s=\log2$，故 $s-a_0=\log2$，log-prob 均为 $-\log2$。中心化保住了当前已表示输入的差异计算，但不能恢复输入阶段已经丢失的信息：在 $10^{16}$ 附近，间距为 2，原本相差小于该间距的两个实数可能被舍入为同一浮点数；算法接收到相同值后无法知道原差。
4. $T=0.5$ 更尖锐，最大项概率上升、熵下降；$T=2$ 更平坦，最大项概率下降、熵上升。
5. 指数可能溢出、重复计算分母、序列概率乘积会下溢，最后可能发生 `log(0)`；应使用稳定 log-softmax 并累加目标 log-prob。

成功标准：能独立推导减最大值形式，并完成 [[数学/50-信息论/80-Softmax数值稳定性实验|Softmax 数值稳定性实验]]，看到稳定概率和为 $1$、平移不变与交叉熵等价的断言全部通过。

## 导航

- 上一站：[[数学/50-信息论/01-熵交叉熵KL散度与互信息|熵、交叉熵、KL 散度与互信息]]
- 下一站：[[数学/50-信息论/80-Softmax数值稳定性实验|Softmax 数值稳定性实验]]
- 返回：[[数学/50-信息论/00-信息论-MOC|信息论 MOC]]
- 相关：[[数学/40-微积分与优化/00-微积分与优化-MOC|微积分与优化 MOC]]
- 相关：[[数学/60-数值计算与量化/00-数值计算与量化-MOC|数值计算与量化 MOC]]


## 系统理论对照

本页保留应用问题与最小实验；更完整的对象定义、推导条件和反例见 [[数学/16-数学分析/10-反常积分与含参积分的极限交换|反常积分与含参积分的极限交换]]；[[数学/16-数学分析/15-收敛定理与Fubini-Tonelli|收敛定理与Fubini-Tonelli]]；[[数学/15-微积分/03-中值定理与导数应用单调凸性和优化|中值定理与导数应用单调凸性和优化]]。应用记号与标准教材不同时，以定义和矩阵形状对照，不仅比较字母。
