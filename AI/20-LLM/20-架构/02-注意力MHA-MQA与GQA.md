---
type: lesson
stage: 2
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum]]"
  - "[[数学/50-信息论/02-指数对数Softmax与LogSumExp]]"
difficulty: 高中代数到进阶
estimated_minutes: 75
topics:
  - attention
  - causal-mask
  - mha
  - mqa
  - gqa
  - kv-cache
domain: artificial-intelligence
tags:
  - ai/llm/architecture
---

# 注意力、MHA、MQA 与 GQA

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 注意力权重在同一行内竞争；共享 KV head 改变缓存与表示结构。参数、计算量、KV 字节数不能只根据 query head 数推断。 深化与验证：[[AI/20-LLM/20-架构/10-注意力反向传播与Softmax竞争|注意力反向传播与Softmax竞争]]；[[AI/20-LLM/40-推理/09-KV缓存分页滑窗与前缀复用|KV缓存分页滑窗与前缀复用]]。


注意力可以先理解成一次“按当前问题，从允许访问的历史记录中加权取回信息”。query 决定当前想找什么，key 用于匹配，value 是实际被混合的内容。这个类比能帮助入门，但不要把它当成数据库的精确键值查找：Q/K/V 都是训练学出的连续向量，一个位置通常会以不同权重混合多个 value。

> [!abstract] 本课目标
> 完成后你应该能：
>
> - 从单头缩放点积注意力推导 score 与输出的 shape；
> - 解释 scale 和 causal mask 的工程含义；
> - 用 `H_q` 与 `H_{kv}` 统一描述 MHA、MQA 和 GQA；
> - 估算每层/整模型 KV cache 元素数和字节数；
> - 判断“GQA 让注意力快几倍”之类说法遗漏了哪些成本与证据。

> [!prerequisite] 数学先修：点积、矩阵乘法、softmax
> 点积的精确定义和几何解释见 [[数学/20-线性代数与几何/03-点积范数距离与余弦相似度|点积、范数、距离与余弦相似度]]；批量矩阵乘法与 `einsum` 见 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]；softmax 的定义与稳定算法见 [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]。若需要区分“权重形式上构成离散分布”与“它是否能解释模型决策”，参见 [[数学/30-概率与统计/01-概率分布条件概率与贝叶斯关系|概率分布、条件概率与贝叶斯关系]]。本页只保留架构所需的 shape 和工程解释。

## 1. 单头注意力：匹配，再取值

先忽略 batch 和多头。设：

$$
Q\in\mathbb{R}^{T_q\times D_h},\qquad
K\in\mathbb{R}^{T_k\times D_h},\qquad
V\in\mathbb{R}^{T_k\times D_v}.
$$

`T_q` 个 query 分别与 `T_k` 个 key 做点积：

$$
S=\frac{QK^\mathsf{T}}{\sqrt{D_h}}
\in\mathbb{R}^{T_q\times T_k}.
$$

第 `i` 行是 query 位置 `i` 对所有 key 位置的分数。合入允许关系 `M` 后，沿 key 轴归一化：

$$
A_{i,:}=\operatorname{softmax}(S_{i,:}+M_{i,:}),
\qquad
A\in\mathbb{R}^{T_q\times T_k}.
$$

最后用每行权重混合 value：

$$
O=AV\in\mathbb{R}^{T_q\times D_v}.
$$

shape 检查把两个不同的求和说得很清楚：

- `QK^T` 沿特征轴 `D_h` 求和，保留 `T_q×T_k`；
- `AV` 沿 key/value 位置轴 `T_k` 求和，保留 `T_q×D_v`。

## 2. 为什么除以 `√D_h`

若先作一个简化假设：Q、K 各分量均值约为 0、方差约为 1，且不同分量近似独立，那么 `D_h` 项乘积相加后，点积的方差会随 `D_h` 增长，典型幅度约按 `√D_h` 增长。除以 `√D_h` 后，score 的典型尺度回到较稳定的量级。

工程意义是：若 score 随 head 维度变得过大，softmax 更容易饱和成接近 one-hot，较小权重及其梯度可能过早变得极小；低精度下还会加剧指数和归约的数值压力。

这个解释不是说真实训练中的 Q/K 永远独立同分布，也不是保证缩放后永不饱和。它说明默认尺度从哪里来；实际分布还受初始化、归一化、训练和位置变换影响。

## 3. masked causal attention 的精确定义

在 causal self-attention 中，从 0 开始编号时，query `i` 只允许读取 `j≤i`：

$$
M_{i,j}=
\begin{cases}
0,&j\le i,\\
-\infty,&j>i.
\end{cases}
$$

mask 必须在 softmax 归一化语义中生效。只在 softmax 后把未来项乘 0，会让剩余权重之和小于 1，除非再次归一化；即使再次归一化，也会做无用工作并更容易隐藏边界错误。

causal mask 只表达时间可见性。padding、打包样本的文档边界、局部窗口或特定稀疏模式是另外的约束，应组合后验证。任何仍要计算的 query 行都不应把全部 key 屏蔽，否则会出现全 `-∞` 行，softmax 可能产生 NaN。

这里的 masked softmax 可以理解为：先确定 query `i` 允许读取的 key 集合，只对集合内的有限分数归一化，集合外的权重为 0。例如分数为 `[2,1,0]`，中间项被屏蔽时，归一化的分母是 `exp(2)+exp(0)`，得到约 `[0.8808,0,0.1192]`。允许集合必须非空；全遮挡时，机械地减去行最大值会遇到 `-∞-(-∞)`。实现须明确拒绝该行、跳过对应 query，或采用业务约定的输出；若约定输出为零，它不构成一行归一化概率。

[[数学/50-信息论/80-Softmax数值稳定性实验|Softmax 数值稳定性实验]] 的规范函数只接受非空有限输入，会拒绝包含 `-inf` 的 logits。因此不能直接把这里的 `S+M` 送入该教学函数；它验证的是有限分数的稳定归一化，attention 的允许集合与全遮挡策略需要另外明确。

> [!warning] attention 权重不是可靠的因果解释
> `A` 确实是本层、本头用于混合 V 的权重，但模型还包含输出投影、残差、后续层和非线性。高 attention 权重不自动等于该 token 对最终答案的因果贡献最大，更不等于模型“理解了”某个关系。

## 4. 多头为什么不只是“重复 H 次”

多头允许不同子空间学习不同匹配与取值方式。用统一符号表示：

$$
Q\in\mathbb{R}^{B\times H_q\times T_q\times D_h},
$$

$$
K,V\in\mathbb{R}^{B\times H_{kv}\times T_k\times D_h}.
$$

为简化，本页让 V 的每头维度也等于 `D_h`。Q 投影权重可写成：

$$
W_Q\in\mathbb{R}^{D\times(H_qD_h)},
$$

K/V 投影权重分别为：

$$
W_K,W_V\in\mathbb{R}^{D\times(H_{kv}D_h)}.
$$

每个 query 头最终都要产生一份 `T_q×T_k` 权重和 `T_q×D_h` 输出。所有 query 头的输出拼接为 `B×T_q×(H_qD_h)`，再经输出投影回到 `B×T_q×D`。

## 5. 用 `H_q` 与 `H_kv` 统一 MHA、MQA、GQA

| 形式 | `H_{kv}` | 每个 query 头怎样取 K/V | 主要取舍 |
| --- | ---: | --- | --- |
| MHA | `H_{kv}=H_q` | 每个 query 头有自己的一组 K/V 头 | 表达自由度高；K/V 投影与 cache 最大 |
| MQA | `H_{kv}=1` | 所有 query 头共享一组 K/V | 最大限度减少 K/V cache/带宽；共享最强 |
| GQA | `1<H_{kv}<H_q` | 一组 query 头共享一个 K/V 头 | 在共享程度与表示能力之间折中 |

常见 GQA 要求 `H_q` 能被 `H_{kv}` 整除。令每组 query 头数：

$$
g=\frac{H_q}{H_{kv}}.
$$

若 query 头从 0 编号，一种常见连续分组是：

$$
\operatorname{kvHead}(h_q)=\left\lfloor\frac{h_q}{g}\right\rfloor.
$$

例如 `H_q=8, H_kv=2` 时，query 头 `0..3` 共享 K/V 头 0，query 头 `4..7` 共享 K/V 头 1。实现可通过广播或索引表达共享，**不必真的把 K/V 在内存中复制 4 份**。

> [!note] “Grouped” 说的是头的共享，不是 token 被分组
> GQA 仍让每个 query 头在允许的 key 位置上计算注意力。它没有自动把序列切成互不相见的小组，也不等于 sliding-window attention。

## 6. 参数量变化：只看 Q/K/V 投影

忽略 bias，Q/K/V 投影参数数目为：

$$
N_{QKV}=D D_h(H_q+2H_{kv}).
$$

Q 的部分 `D D_h H_q` 不因 MHA/MQA/GQA 改变；减少的是 K 和 V 的 `2D D_h H_{kv}`。输出投影、FFN、embedding 等参数也不随 `H_{kv}` 按相同比例变化。

因此，“把 K/V 头从 32 降到 8，整个模型参数变成四分之一”是错误结论。最多只能说 K/V 投影的相应部分变为四分之一，再结合全模型参数构成计算总比例。

## 7. KV cache：为什么头共享对 decode 特别重要

自回归生成时，过去 token 在每一层产生的 K/V 会被保存，下一步只计算新 token 的 Q/K/V。对 `B` 条序列、`L` 层、缓存长度 `T_k`，若每个元素占 `s` 字节，逻辑 KV cache 大小为：

$$
\text{elements}=2BLT_kH_{kv}D_h,
$$

$$
\text{bytes}=2BLT_kH_{kv}D_hs.
$$

前面的 `2` 来自 K 和 V 两份缓存。这个公式不包含页表、对齐、padding、量化元数据、临时工作区和运行时碎片，是真实显存的**基线估算**。

### 数值例：GQA 到底省了多少 cache

设：

- `B=1`、`L=24`、`T_k=4096`；
- `H_q=8`、`H_{kv}=2`、`D_h=64`；
- K/V 使用 2 字节元素。

则 GQA 的逻辑 cache 是：

$$
2\times1\times24\times4096\times2\times64\times2
=50{,}331{,}648\ \text{bytes}
=48\ \text{MiB}.
$$

同样条件下：

- MHA 的 `H_{kv}=8`，为 `192 MiB`；
- MQA 的 `H_{kv}=1`，为 `24 MiB`。

这只比较 KV cache。模型权重、激活、采样和运行时工作区另算。

### Cache 中的 K 已带位置吗

对常见 RoPE 路径，新 token 的 K 会应用对应位置旋转后进入后续 attention；cache 逻辑上必须保存以后能以同一位置语义参与点积的 K，以及对应 V。很多实现直接缓存旋转后的 K，但具体 kernel 也可能选择等价布局或延迟变换，不能脱离实现断言物理字节排列。

一旦改变 RoPE 缩放、位置编号、head 布局或相关精度配置，旧 cache 通常不能无条件复用；详见 [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]]。

## 8. Prefill 与 decode 的收益不同

### Prefill

prompt 整段进入时常有 `T_q=T_k=T`。每个 query 头仍要建立自己的 score 关系，所以减少 `H_{kv}` 不会把 `H_q×T×T` 这一逻辑关系直接降为 `H_{kv}×T×T`。共享 K/V 会减少 K/V 投影、读取和 cache 写入，但 full-attention 的主要长度成本仍存在。

### Decode

单步 decode 时 `T_q=1`、`T_k` 是当前可见历史。运行时反复从 cache 读取所有历史 K/V，常受内存带宽影响。把 `H_{kv}` 从 `H_q` 降低，能按头数比例减少这部分 cache 容量与读取量，因此 MQA/GQA 对 decode 往往特别有价值。

“往往”不等于固定加速倍数。端到端速度还受 batch、序列长度、kernel、量化、硬件、调度和其他层影响，必须实测 tokens/s、首 token 延迟、单 token 延迟与峰值内存。

## 9. MHA、MQA、GQA 不是单向优劣排名

头共享减少存储和带宽，但也减少不同 query 头拥有独立 K/V 表示的自由度。最终质量取决于训练方法、模型宽度、数据和任务，不能只由头数公式推出。

比较时至少报告：

- 参数和训练设置是否可比；
- `H_q`、`H_{kv}`、`D_h` 及总 `D`；
- prefill 与 decode 分开测量；
- batch、输入/输出长度、dtype、cache 量化和硬件；
- 质量指标及长短上下文分桶，而非只报一个平均分。

## 10. 数值与实现边界

- stable softmax 通常会先减去每行最大 score；
- mask 的极小值必须与当前 dtype 和融合 kernel 语义兼容；
- 低精度 cache 可减少带宽和容量，但会引入量化/舍入误差；
- 分块 attention 可以不保存完整 `T_q×T_k` 权重矩阵，却仍计算等价归一化；
- K/V 的 broadcast 是逻辑共享，不应误认为必然物理复制；
- 浮点归约顺序和混合精度可能让不同 kernel 的最后几位不同。完整边界见 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]。

硬件上的矩阵乘法、分块、融合与访存从 [[计算机知识/40-并行与异构计算/01-CUDA/08-Reduction-Softmax与GEMM|CUDA Reduction、Softmax 与 GEMM]] 继续；需要完整 CUDA 学习顺序时再返回该页的 MOC。

## 11. 常见失败模式

| 失败或误解 | 症状 | 修正 |
| --- | --- | --- |
| softmax 作用在 query 轴 | 每个 key 被 query 归一化，语义颠倒 | 对每个 query 的 key 分数，即最后 `T_k` 轴归一化 |
| 忘记 `1/√D_h` | 训练不稳或权重过早尖锐 | 核对 score 公式与实现；不要把 `D` 误代为 `D_h` |
| causal 条件写成 `j≥i` | 读到未来或只读未来 | 固定行=query、列=key，再验证 `j≤i` |
| GQA 分组不整除 | 错误 broadcast、head 对不上 | 核对 `H_q/H_{kv}` 和实现映射 |
| 物理复制共享 K/V | cache 节省消失、带宽异常 | 使用支持 GQA/MQA 的布局和 kernel |
| cache 长度或位置错一位 | 生成质量突然下降、重复或错位 | 同时记录 token 下标、position id、cache 写入位置 |
| 只算单层 cache | 显存估计严重偏低 | 乘上层数 `L`、batch `B` 和实际字节数 |
| 把 GQA 的 cache 比例当端到端加速比 | 预测远高于实测 | 分离投影、attention、FFN、输出层与调度成本 |
| 把 attention 权重当解释结论 | 对模型行为作过度因果归因 | 使用干预、消融等额外证据 |

## 12. 练习

### 练习 A：单头 shape

给定 `Q: 5×8`、`K: 7×8`、`V: 7×12`：

1. `QK^T`、softmax 权重和输出各是什么 shape？
2. 哪根轴被 `QK^T` 求和，哪根轴被 `AV` 求和？
3. 这是 self-attention 必须出现的 shape 吗？为什么？

### 练习 B：识别三种头共享

分别判断：

1. `H_q=16, H_{kv}=16`；
2. `H_q=16, H_{kv}=1`；
3. `H_q=16, H_{kv}=4`。

对第 3 种写出每个 K/V 头服务多少个 query 头。

### 练习 C：估算 cache

设 `B=2, L=32, T_k=8192, H_q=32, H_{kv}=8, D_h=128`，K/V 每元素 2 字节：

1. 算出 GQA 的逻辑 KV cache 字节数和 MiB/GiB；
2. 保持其他值不变，MHA cache 是它的几倍？
3. 列出至少三项公式未计入的运行时内存。

### 练习 D：审查一句宣传

有人说：“把 32 个 KV 头改成 8 个，所以模型推理必然快 4 倍，质量完全不变。”逐句指出哪些是 shape 可确认的事实，哪些需要性能实验，哪些需要质量评测。

<details>
<summary>核对要点</summary>

- 练习 A：`5×7`、`5×7`、`5×12`；分别沿特征轴 8、key/value 位置轴 7 求和。`T_q≠T_k` 完全可以出现在 cross-attention 或带 cache 的 decode 中。
- 练习 B：MHA、MQA、GQA；第 3 种每组 4 个 query 头。
- 练习 C：`2×2×32×8192×8×128×2 = 2,147,483,648` 字节，即 `2048 MiB = 2 GiB`；MHA 为 4 倍。未计入项可包括模型权重、临时工作区、页表/对齐、其他激活、采样状态和碎片。
- 练习 D：KV cache 与 K/V 投影的相应部分可按头数减少；端到端速度和质量都不是该比例的数学推论。

</details>

### 成功标准

- [ ] 我能从点积和加权求和分别写出 `T_q×T_k` 与 `T_q×D_h`。
- [ ] 我能用一个 `H_{kv}` 变量准确区分 MHA、MQA、GQA。
- [ ] 我能计算包含 `B`、`L`、K/V 两份和 dtype 字节数的 cache 基线。
- [ ] 我能解释 GQA 主要减少什么，而没有自动减少什么。
- [ ] 我能把公式性质、实现速度和模型质量分成三类证据。

---

**上一站**：[[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]] · **下一站**：[[AI/20-LLM/20-架构/03-FFN归一化残差与SwiGLU|FFN、归一化、残差与 SwiGLU]] · **相关**：[[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]] · **返回**：[[AI/20-LLM/20-架构/00-LLM架构-MOC|LLM 架构 MOC]]
