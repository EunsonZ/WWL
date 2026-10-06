---
type: lesson
stage: 1
status: ready
difficulty: 入门到进阶
estimated_minutes: 40
topics:
  - mixture-of-experts
  - sparse-routing
  - capacity-factor
  - load-balancing
  - expert-parallelism
domain: artificial-intelligence
tags:
  - ai/llm/architecture
---

# MoE 架构与路由

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> top-k 的离散索引和选中 gate 的连续权重有不同梯度性质；top-1 若只在选中集合内重归一化，会出现 gate 恒为 1 的特殊情况。负载和通信需单独核验。 深化与验证：[[AI/20-LLM/20-架构/13-MoE路由梯度负载均衡与通信成本|MoE路由梯度负载均衡与通信成本]]；[[AI/12-PyTorch/08-DDP全局目标通信与分片边界|DDP全局目标通信与分片边界]]。


MoE（Mixture of Experts，混合专家）试图同时得到两件事：模型保存许多参数，但每个 token 只激活其中一小部分。它的关键不是“多个模型投票”，而是**路由器为每个 token 选择少数 FFN 专家**。

这能扩大总参数容量，却引入新的难题：专家负载不均、token 超出容量、设备间通信、路由不稳定，以及“总参数”和“每 token 激活参数”容易被混淆。

## 学习目标

读完后，你应该能够：

1. 区分 dense FFN 与稀疏 MoE FFN；
2. 从 router logits、softmax、top-$k$ 到专家加权输出，写出完整数据流；
3. 根据 token 数、专家数、top-$k$ 与 capacity factor 计算专家容量；
4. 解释负载均衡辅助目标为何必要，以及它不能保证什么；
5. 区分总参数、激活参数、计算量、显存占用与通信成本。

## 1. 直觉：八位老师，不是每道题都找八位

假设有 8 个 FFN 专家。dense 模型每个 token 经过同一个 FFN；稀疏 MoE 可以让路由器为每个 token 选 top-2 专家：

```text
token A ──router──> 专家 1 + 专家 6 ──加权合并──> 输出 A
token B ──router──> 专家 3 + 专家 6 ──加权合并──> 输出 B
token C ──router──> 专家 1 + 专家 4 ──加权合并──> 输出 C
```

专家不是预先贴好“数学”“中文”“代码”标签的人工角色。训练可能形成某些统计分工，但不能仅凭专家编号或几个样本给它赋予稳定语义。

## 2. MoE 放在 Transformer 的哪里

常见做法是把部分或全部 decoder block 中的 dense FFN 替换成 MoE 层，而 attention 仍然照常执行：

```text
hidden states
  ├─ causal self-attention
  ├─ residual
  └─ MoE layer
      ├─ router
      ├─ dispatch：按专家重排 token
      ├─ selected expert FFNs
      ├─ combine：按路由权重合并
      └─ residual
```

因此 MoE 主要改变的是逐 token 非线性变换与系统通信，不会自动把 causal attention 变成双向 attention。

## 3. 路由的精确定义

设一个 token 的隐藏向量是 $h\in\mathbb{R}^{d_{model}}$，共有 $E$ 个专家。一个简单的线性路由器计算：

$$
z=hW_r+b_r,\qquad z\in\mathbb{R}^{E}
$$

$z_e$ 是第 $e$ 个专家的 router logit。经过 softmax：

$$
p_e=\frac{\exp(z_e)}{\sum_{j=1}^{E}\exp(z_j)}
$$

然后取概率最大的 $k$ 个专家集合 $S(h)=\operatorname{TopK}(p,k)$。一种常见输出写法是：

$$
y=\sum_{e\in S(h)}\tilde p_e\,E_e(h)
$$

其中 $E_e$ 是第 $e$ 个专家 FFN，$\tilde p_e$ 是选中专家的组合权重。它可能是在 top-$k$ 内重新归一化后的概率，也可能遵循其他实现约定；必须查看精确模型实现。

概率与 softmax 的前置概念可回看 [[数学/30-概率与统计/01-概率分布条件概率与贝叶斯关系|概率分布、条件概率与贝叶斯关系]]。这里的 $p_e$ 是**路由权重**，不是“专家答案正确的概率”。

### 完整 shape 流

把 batch 和序列展平成 $N=B\times T$ 个 token：

| 步骤 | shape | 说明 |
| --- | --- | --- |
| hidden | `[N,d_model]` | 进入 MoE 的 token |
| router logits | `[N,E]` | 每 token 对每专家的分数 |
| top-k indices | `[N,k]` | 每 token 选中的专家编号 |
| top-k weights | `[N,k]` | 合并权重 |
| dispatch buffers | 每专家约 `[capacity,d_model]` | 按专家重排后的输入 |
| expert outputs | 每专家约 `[capacity,d_model]` | 专家 FFN 输出 |
| combined output | `[N,d_model]` | 恢复 token 顺序并加权 |

矩阵与 shape 基础见 [[数学/20-线性代数与几何/01-向量矩阵与张量|向量、矩阵与张量]] 和 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]。

## 4. Top-1 与 Top-2：稀疏程度的权衡

- **top-1**：每 token 只运行一个专家；计算更少，路由决定更脆弱。
- **top-2**：每 token 运行两个专家并合并；冗余和表达能力可能更好，但专家计算与通信更多。
- **更大的 $k$**：逐渐接近 dense mixture，稀疏计算优势下降。

$k$ 不是越大越好。比较 MoE 时至少同时记录 $E$、$k$、专家宽度、共享专家、MoE 层频率和容量策略。

## 5. 专家容量与 token overflow

如果所有 token 都涌向同一个专家，硬件负载会严重失衡。许多实现为每个专家分配有限容量。一种常见近似是：

$$
C=\left\lceil c\cdot\frac{N\cdot k}{E}\right\rceil
$$

其中：

- $N$：本次路由组中的 token 数；
- $k$：每 token 选择专家数；
- $E$：专家数；
- $c$：capacity factor；
- $C$：每个专家最多接收的 token assignment 数。

### 实际计算例子

设 $N=8$、$E=4$、$k=2$、$c=1.25$：

$$
C=\left\lceil1.25\times\frac{8\times2}{4}\right\rceil
=\lceil5\rceil=5
$$

一共有 $8\times2=16$ 次 token→专家分配，每个专家预留 5 个槽位。如果专家 0 收到 8 次分配，就有 3 次超过容量。

overflow 的处理因实现而异：

- 丢弃该专家分支；
- 改派到下一候选专家；
- 采用 dropless/动态容量策略；
- 跨设备或跨批次重新组织。

这些选择会改变质量、吞吐、内存和确定性，不能只凭“capacity factor=1.25”推断完整行为。

## 6. 为什么需要负载均衡

如果路由器早期偏爱少数专家，就可能形成正反馈：热门专家得到更多训练信号，冷门专家更难学会有用特征，最终出现 expert collapse。

常见训练目标会增加辅助项，鼓励：

- 每个专家收到的 token 数更均衡；
- 路由概率质量不要长期集中在少数专家；
- router logits 不要无限增大；
- 某些模型还包含共享专家、噪声或其他正则化。

抽象地写，总损失可能是：

$$
L=L_{task}+\lambda_{balance}L_{balance}+\lambda_zL_z
$$

其中 $L_{task}$ 是语言建模损失，$L_{balance}$ 鼓励负载均衡，$L_z$ 可用于约束 router logits 的尺度。不同模型的精确公式不同，不能把某篇论文的辅助损失直接当成所有 MoE 的定义。

> [!note] “均衡”不等于每个 token 随机分配
> 目标通常是在一批 token 的统计上避免严重拥塞，同时仍让路由器根据 token 表示做有用选择。若强制每个专家永远接收完全相同数量，也可能损害路由表达力。

## 7. 稀疏计算不等于低内存

MoE 最容易被误解的地方，是把几个不同量混成一个“参数量”：

| 量 | 含义 | MoE 中的典型变化 |
| --- | --- | --- |
| 总参数 | checkpoint 中全部专家和共享模块的参数 | 可以很大 |
| 每 token 激活参数 | 一个 token 实际经过的专家参数 | 仅为 top-$k$ 专家及共享部分 |
| 权重显存/内存 | 为运行保存的参数 | 通常仍需容纳全部或分片专家 |
| 每 token FLOPs | 前向实际乘加量 | 受 $k$、专家宽度和共享专家影响 |
| 通信量 | token dispatch/combine 跨设备搬运 | expert parallel 时可能成为瓶颈 |
| KV cache | attention 的 K/V 缓存 | 不因 FFN 改成 MoE 而自动减少 |

所以“总参数很大但每 token 计算较小”可以同时成立；“只激活两个专家”并不意味着单卡只需保存两个专家。

## 8. 设备上的真实数据流

当专家分布在多张设备上时，MoE 层常需要：

1. 本地计算 router logits 与 top-$k$；
2. 按目标专家整理 token；
3. all-to-all 或等价通信把 token 发到专家所在设备；
4. 各设备运行本地专家 FFN；
5. 把输出发回原 token 所在设备；
6. 按原顺序和路由权重合并。

这意味着 MoE 的理论 FLOPs 优势可能被网络互连、负载不均、小批量、padding 和 kernel 启动开销抵消。服务系统还要考虑不同请求的 token 同时路由时能否凑成高效批次。

## 9. 训练与推理的权衡

| 方面 | 可能收益 | 新成本/风险 |
| --- | --- | --- |
| 模型容量 | 增加专家可扩大总参数空间 | checkpoint、内存和分片更大 |
| 每 token 计算 | 只运行 top-$k$ 专家 | router、dispatch、combine 有开销 |
| 专业化 | 不同专家可学习不同统计模式 | 专家语义不稳定，可能 collapse |
| 多设备扩展 | expert parallel 提供新的并行维度 | all-to-all 通信与慢专家拖尾 |
| 推理吞吐 | 大批量时可能摊薄路由成本 | 小批量、长尾路由可能利用率差 |
| 训练稳定性 | 可配合辅助目标控制负载 | 增加超参数和损失权衡 |

## 10. 常见失败模式

1. **路由塌缩**：大量 token 都选择少数专家。
2. **容量溢出**：热门专家超出槽位，token 被丢弃或改派。
3. **负载看似均衡但无用**：只优化计数，专家没有学到有效差异。
4. **路由 logits 数值不稳**：softmax 上溢、低精度误差或 logits 过大。
5. **训练/推理路由规则不一致**：top-$k$、重归一化、overflow 策略不同。
6. **忘记 padding/mask**：padding token 占用专家容量，扭曲负载统计。
7. **分布式死锁或 shape 错位**：dispatch 数量和返回顺序在设备间不一致。
8. **只报总参数**：让人误以为每 token 计算等于全部专家，或反过来误以为内存只需激活专家。
9. **给专家强行命名**：用少量观察把专家 3 宣称为“代码专家”，忽略层、token 和训练过程的变化。
10. **把 MoE 当能力保证**：架构容量不自动保证训练数据、对齐、推理质量或安全性。

## 11. 练习：手工完成一次 top-2 路由

有 6 个 token、3 个专家，路由概率如下：

| token | 专家 0 | 专家 1 | 专家 2 |
| --- | ---: | ---: | ---: |
| A | 0.70 | 0.20 | 0.10 |
| B | 0.60 | 0.30 | 0.10 |
| C | 0.05 | 0.80 | 0.15 |
| D | 0.40 | 0.35 | 0.25 |
| E | 0.15 | 0.25 | 0.60 |
| F | 0.50 | 0.45 | 0.05 |

任务：

1. 为每个 token 选择 top-2 专家；
2. 统计每位专家收到的 assignment 数；
3. 令 capacity factor $c=1.0$，计算每专家容量；
4. 找出溢出专家，并比较“丢弃最后到达分支”和“改派下一专家”的差别；
5. 说明哪两个指标能帮助发现路由塌缩。

### 成功标准

- 共得到 $6\times2=12$ 次分配，没有把 token 数和 assignment 数混淆；
- 计算出 $C=\lceil1.0\times12/3\rceil=4$；
- 能算出专家 0、1、2 的负载分别为 4、6、2，并指出专家 1 溢出 2 次分配；
- 能说明丢弃会损失某些专家贡献，改派会增加规则和计算复杂性；
- 至少提出“每专家 token/assignment 数分布”和“平均路由概率/熵或 top-1 占比”等可观察量。

## 12. 小结

- MoE 常用稀疏专家替换 dense FFN，attention 结构并不会因此自动改变；
- router 产生专家分数，top-$k$ 选择少数专家，combine 恢复 token 顺序并加权；
- capacity 与 load balancing 是可运行 MoE 的核心，而不是附属细节；
- 总参数、激活参数、权重内存、FLOPs、KV cache 和通信必须分开报告；
- 专家数、top-$k$、共享专家、容量与路由损失都是具体模型的版本事实，需回到 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]] 和精确模型卡核验。

---

**先修**：[[AI/20-LLM/20-架构/03-FFN归一化残差与SwiGLU|FFN、归一化、残差与 SwiGLU]] · [[数学/30-概率与统计/01-概率分布条件概率与贝叶斯关系|概率分布与条件概率]] · [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法与线性映射]]

**相关概念**：[[AI/20-LLM/20-架构/05-Llama主线与模型家族比较|Llama 主线与模型家族比较]] · [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]] · [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|数值稳定性]]

**上一站**：[[AI/20-LLM/20-架构/05-Llama主线与模型家族比较|Llama 主线与模型家族比较]] · **下一站**：[[AI/20-LLM/20-架构/07-编码器解码器与多模态接口|编码器、解码器与多模态接口]] · **返回**：[[AI/20-LLM/20-架构/00-LLM架构-MOC|LLM 架构 MOC]] · [[AI/20-LLM/00-LLM-MOC|LLM MOC]]
