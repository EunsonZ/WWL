---
type: lesson
stage: 1
status: ready
difficulty: 入门到进阶
estimated_minutes: 35
topics:
  - ffn
  - swiglu
  - residual-connection
  - layernorm
  - rmsnorm
  - pre-norm
domain: artificial-intelligence
tags:
  - ai/llm/architecture
---

# FFN、归一化、残差与 SwiGLU

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> FFN 的逐位置性不表示输出缺少上下文，因为输入已被前层注意力混合。MoE 改变 FFN 的条件计算路径，还需分析路由梯度与通信。 深化与验证：[[AI/11-数学与统计桥梁/02-矩阵微积分VJP与反向传播|矩阵微积分VJP与反向传播]]；[[AI/20-LLM/20-架构/13-MoE路由梯度负载均衡与通信成本|MoE路由梯度负载均衡与通信成本]]。


一个 Transformer 块不只靠注意力。注意力负责让 token **读取别的位置**，FFN（前馈网络）负责让每个 token **独立地变换自己的特征**；残差连接让旧信息和梯度有短路；归一化控制各层输入的数值尺度。四者合起来，才形成可以反复堆叠的基本块。

## 学习目标

读完后，你应该能够：

1. 沿着 shape 写出 `Norm → Attention → Residual → Norm → FFN → Residual` 的数据流；
2. 区分普通 FFN、GLU 与 SwiGLU，而不是把 SwiGLU 误当成一种注意力；
3. 用公式说明 LayerNorm 与 RMSNorm 各自归一化了什么；
4. 解释 pre-norm、残差连接和数值稳定性之间的关系；
5. 根据张量 shape、激活值和残差分支定位常见实现错误。

## 1. 先建立直觉：每个 token 的“独立工作台”

设一批隐藏状态的 shape 是：

$$
X\in\mathbb{R}^{B\times T\times d_{model}}
$$

- $B$：batch 大小；
- $T$：序列长度；
- $d_{model}$：每个 token 的隐藏向量宽度。

注意力会混合不同位置的信息。FFN 则对每个位置使用**同一套参数**，但不在 FFN 内部让位置之间互相通信：

```text
位置 1 的向量 ──同一个 FFN──> 位置 1 的新向量
位置 2 的向量 ──同一个 FFN──> 位置 2 的新向量
位置 3 的向量 ──同一个 FFN──> 位置 3 的新向量
```

因此，FFN 也常被称为 position-wise FFN。它像一个对所有 token 共享的“小程序”：先把向量扩展到更宽的特征空间，做非线性选择，再压回 $d_{model}$。

## 2. 普通 FFN 的精确定义

忽略 batch 和序列维，只看单个 token 的行向量 $x\in\mathbb{R}^{d_{model}}$。两层 FFN 可以写成：

$$
\operatorname{FFN}(x)=\phi(xW_{up}+b_{up})W_{down}+b_{down}
$$

其中：

| 对象 | shape | 作用 |
| --- | --- | --- |
| $x$ | $[d_{model}]$ | 一个 token 的隐藏状态 |
| $W_{up}$ | $[d_{model},d_{ff}]$ | 扩展通道 |
| 中间激活 | $[d_{ff}]$ | 让模型在更宽空间组合特征 |
| $W_{down}$ | $[d_{ff},d_{model}]$ | 压回残差流宽度 |
| 输出 | $[d_{model}]$ | 可以与输入逐元素相加 |

$\phi$ 是非线性函数，例如 ReLU、GELU 或 SiLU。没有非线性时，两次线性映射可以合并成一次，网络表达力会明显受限。

对完整张量 $X$，矩阵只作用在最后一维，所以输入输出 shape 都是 $[B,T,d_{model}]$。这里涉及的向量、张量与线性映射可回看 [[数学/20-线性代数与几何/01-向量矩阵与张量|向量、矩阵与张量]] 和 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]。

## 3. 从 GLU 到 SwiGLU：一条内容支路加一扇门

GLU（Gated Linear Unit）的核心不是“多一层”，而是把中间表示拆成两条支路：

1. **value 支路**产生候选内容；
2. **gate 支路**产生逐元素门值；
3. 两者逐元素相乘，再投影回模型宽度。

一种常见的 SwiGLU 写法是：

$$
v=xW_v,\qquad g=\operatorname{SiLU}(xW_g)
$$

$$
\operatorname{SwiGLU}(x)=(v\odot g)W_{down}
$$

其中 $\odot$ 表示逐元素乘法，SiLU 定义为：

$$
\operatorname{SiLU}(z)=z\,\sigma(z)
$$

$\sigma$ 是 sigmoid。直觉上，$v$ 回答“候选特征是什么”，$g$ 回答“每个候选特征应通过多少”。门值不必落在 $[0,1]$：由于外面还有一个 $z$，SiLU 可以输出负值，也可能大于 1。

> [!note] 公式命名可能换位
> 不同论文和代码库可能把两条上投影称为 `gate_proj`、`up_proj`、$W_1$、$W_3$，相乘顺序也可能写反。逐元素乘法本身可交换；阅读实现时应以 **shape、激活函数加在哪一支、是否有 bias** 为准，而不是只背变量名。

### 普通 FFN 与 SwiGLU 的差别

| 维度 | 普通两层 FFN | SwiGLU |
| --- | --- | --- |
| 上投影 | 一条 | value 与 gate 两条 |
| 非线性 | 直接作用于中间向量 | 作用于 gate，再与 value 相乘 |
| 输出 shape | $[B,T,d_{model}]$ | $[B,T,d_{model}]$ |
| 参数/计算 | 取决于 $d_{ff}$ | 同一 $d_{ff}$ 下多一条上投影 |
| 实际公平比较 | 不能只比较同一 $d_{ff}$ | 应同时比较参数量、FLOPs 与质量 |

SwiGLU 常与较小的中间宽度搭配，以控制参数量和计算量。因此“它有三次线性映射”并不自动意味着某个真实模型一定更慢；实际速度还取决于精确宽度、融合算子、数据类型、硬件和批量。

## 4. 残差连接：保留旧路，再学习修正量

残差连接写成：

$$
y=x+F(x)
$$

$F(x)$ 可以是注意力子层或 FFN 子层。它让网络学习“在原表示上加什么修正”，而不是每层都从头重写表示。

残差相加要求两边 shape 完全一致。例如 $x$ 和 $F(x)$ 都必须是 $[B,T,d_{model}]$。FFN 可以在内部扩展到 $d_{ff}$，但加回残差前必须压回 $d_{model}$。

残差连接有三层直觉：

- **信息路径**：即使某个子层暂时学得不好，$x$ 仍可直接向后传；
- **优化路径**：反向传播存在较短的梯度通路；
- **表示路径**：每层在共享的残差流上添加增量。

它不保证训练永不发散，也不等于把两个概率相加。这里相加的是隐藏向量。

## 5. LayerNorm 与 RMSNorm

### 5.1 LayerNorm：减均值，再除标准差

对一个 token 的 $d=d_{model}$ 个分量：

$$
\mu=\frac{1}{d}\sum_{i=1}^{d}x_i,
\qquad
\sigma^2=\frac{1}{d}\sum_{i=1}^{d}(x_i-\mu)^2
$$

$$
\operatorname{LayerNorm}(x)_i=\gamma_i\frac{x_i-\mu}{\sqrt{\sigma^2+\epsilon}}+\beta_i
$$

它对每个 token 独立计算，不在 batch 或序列位置之间求均值。$\gamma$、$\beta$ 是可学习的缩放和平移。

### 5.2 RMSNorm：不减均值，只控制均方根尺度

$$
\operatorname{RMS}(x)=\sqrt{\frac{1}{d}\sum_{i=1}^{d}x_i^2+\epsilon}
$$

$$
\operatorname{RMSNorm}(x)_i=\gamma_i\frac{x_i}{\operatorname{RMS}(x)}
$$

RMSNorm 通常没有减均值步骤，也常不使用偏移 $\beta$。它控制向量尺度，但不会强制归一化后的分量均值为 0。

### 手算一个 RMSNorm

令 $x=(3,4)$，先忽略 $\epsilon$ 且令 $\gamma=(1,1)$：

$$
\operatorname{RMS}(x)=\sqrt{\frac{3^2+4^2}{2}}=\sqrt{12.5}\approx3.536
$$

所以：

$$
\operatorname{RMSNorm}(x)\approx(0.849,1.131)
$$

方向基本保留，整体尺度被拉到可控范围。归一化的优化背景见 [[数学/40-微积分与优化/05-初始化归一化与训练稳定性|初始化、归一化与训练稳定性]]；$\epsilon$、低精度累加和溢出问题见 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点、精度与数值稳定性]]。

## 6. Pre-norm：先归一化，再进入子层

现代 decoder block 常见的 pre-norm 数据流可以抽象为：

$$
u=x+\operatorname{Attention}(\operatorname{Norm}_1(x))
$$

$$
y=u+\operatorname{FFN}(\operatorname{Norm}_2(u))
$$

完整 shape 流如下：

```text
x [B,T,d_model]
 ├─ Norm ─ Attention ─ output projection [B,T,d_model] ─┐
 └───────────────────────────────────────────────────────+─> u
                                                        │
u [B,T,d_model]                                         │
 ├─ Norm ─ gate/up projections [B,T,d_ff]               │
 │          └─ SiLU(gate) ⊙ value [B,T,d_ff]            │
 │             └─ down projection [B,T,d_model] ────────┐
 └───────────────────────────────────────────────────────+─> y
```

pre-norm 的“pre”是相对子层而言：Norm 在 Attention/FFN 之前。与之相对，经典 post-norm 把 Norm 放在残差相加之后。二者都能构成 Transformer，但深层训练行为、初始化和最终输出归一化安排不同，不能只交换一行代码就假定 checkpoint 仍兼容。

## 7. 一个实际 shape 例子

假设：

- $B=2$；
- $T=4$；
- $d_{model}=8$；
- $d_{ff}=24$。

在 SwiGLU FFN 中：

| 步骤 | shape |
| --- | --- |
| 输入 `x` | `[2,4,8]` |
| `gate = x @ W_gate` | `[2,4,24]` |
| `value = x @ W_value` | `[2,4,24]` |
| `SiLU(gate) * value` | `[2,4,24]` |
| `hidden @ W_down` | `[2,4,8]` |
| `x + ffn_out` | `[2,4,8]` |

如果 `W_down` 错写成 `[24,16]`，矩阵乘法仍可能成功，但输出成为 `[2,4,16]`，无法与 `[2,4,8]` 的残差相加。shape 检查比“代码没有在前一行报错”更可靠。

## 8. 设计权衡

| 决策 | 得到什么 | 付出什么 |
| --- | --- | --- |
| 增大 $d_{ff}$ | 更宽的逐 token 变换空间 | 参数、计算和中间激活内存增加 |
| 使用门控 FFN | 内容与门控可形成乘性交互 | 多一条投影；算子实现更复杂 |
| 使用 RMSNorm | 省去中心化步骤，结构简洁 | 与 LayerNorm 行为不同，权重不能直接混用 |
| pre-norm | 为深层残差流提供直接路径 | 需配套最终 Norm、初始化与训练配置 |
| 低精度执行 | 节省带宽和显存，可能更快 | 归一化、累加、极端激活更易受数值误差影响 |

## 9. 常见失败模式

1. **残差维度不一致**：FFN 没有投影回 $d_{model}$，或误把 head 维当模型维。
2. **把 Norm 放错轴**：对 batch 或序列求统计量，而不是对每个 token 的最后一维归一化。
3. **把 RMSNorm 当 LayerNorm**：实现里偷偷减了均值，导致与 checkpoint 定义不一致。
4. **门和值接反后又错误加载权重**：数学上两支相乘可交换，但激活只在一支；权重映射必须与实现命名一致。
5. **忘记 $\epsilon$ 或在低精度直接求平方和**：接近零或极大输入可能产生除零、上溢、`NaN`。
6. **残差原地修改**：先覆盖 `x`，之后所谓 `x + F(x)` 已不是原输入。
7. **只看参数量判断速度**：实际瓶颈还包括内存带宽、kernel 融合、batch/sequence shape 与数据类型。
8. **擅自替换 Norm 或激活后继续加载旧权重**：结构名称相似不代表 checkpoint 语义兼容。

## 10. 练习：画出并核对一个 SwiGLU pre-norm 块

给定 $B=1,T=6,d_{model}=12,d_{ff}=32$，完成以下任务：

1. 写出两个上投影矩阵和一个下投影矩阵的 shape；
2. 从输入到第二次残差相加，逐步写出每个张量 shape；
3. 用一句话分别解释 residual、RMSNorm、SiLU gate 的作用；
4. 假设某 token 的全部分量都为 0，说明 $\epsilon$ 为什么必要；
5. 指出哪些步骤会混合 token 位置，哪些不会。

### 成功标准

- 两个上投影均把最后一维 `12 → 32`，下投影把 `32 → 12`；
- 两次残差相加前，两支都是 `[1,6,12]`；
- 能明确说出 FFN 和 token-wise Norm 不混合序列位置，Attention 才混合位置；
- 能说明没有 $\epsilon$ 时全零向量会造成除以 0；
- 没有把 SiLU 说成 softmax，也没有把隐藏向量相加说成概率相加。

## 11. 小结

- FFN 对每个 token 独立工作，通过扩展、非线性和压缩改造特征；
- SwiGLU 用 value 与 SiLU gate 的逐元素乘法形成门控；
- residual 保留原表示并添加修正，要求相加两边 shape 一致；
- LayerNorm 会中心化并缩放，RMSNorm 只按均方根缩放；
- pre-norm 的典型顺序是 `x + Sublayer(Norm(x))`；
- 模型能否正确加载取决于精确结构、shape、参数命名与数值约定，不能靠家族名猜测。

---

**先修**：[[数学/20-线性代数与几何/01-向量矩阵与张量|向量、矩阵与张量]] · [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]

**相关概念**：[[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]] · [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]] · [[数学/40-微积分与优化/05-初始化归一化与训练稳定性|初始化、归一化与训练稳定性]] · [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|数值稳定性]]

**下一站**：[[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]] · **返回**：[[AI/20-LLM/20-架构/00-LLM架构-MOC|LLM 架构 MOC]] · [[AI/20-LLM/00-LLM-MOC|LLM MOC]]
