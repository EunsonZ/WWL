---
type: moc
stage: 2
status: ready
difficulty: 高中代数到进阶
estimated_minutes: 25
topics:
  - transformer
  - attention
  - rope
  - kv-cache
  - ffn
  - moe
  - model-family
  - multimodal-interface
  - llm-architecture
domain: artificial-intelligence
tags:
  - ai/llm/architecture
---

# LLM 架构 MOC

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 已有课程保持原路径。完成入门后，按以下机制深化入口继续；箭头表示推荐阅读次序，不表示后一个概念与前一个等价：[[AI/20-LLM/20-架构/10-注意力反向传播与Softmax竞争|注意力反向传播与Softmax竞争]] → [[AI/20-LLM/20-架构/11-RoPE相对位置缓存偏移与长度外推|RoPE相对位置缓存偏移与长度外推]] → [[AI/20-LLM/20-架构/12-MLA线性注意力与状态空间的记忆取舍|MLA线性注意力与状态空间的记忆取舍]] → [[AI/20-LLM/20-架构/13-MoE路由梯度负载均衡与通信成本|MoE路由梯度负载均衡与通信成本]]。


本模块回答一个具体问题：**一串 token 进入模型后，数据以什么 shape 穿过每一层，又怎样变成下一个 token 的 logits？** 你不需要先会大学高等数学；但要养成三个习惯：给轴命名、逐步检查 shape、把公式与内存和计算联系起来。

> [!abstract] 完成本模块后
> 你应该能：
>
> - 沿 decoder-only Transformer 追踪 `token ids → hidden states → logits`；
> - 解释 causal mask、缩放点积注意力、MHA/MQA/GQA 与 KV cache 的关系；
> - 说明 RoPE 把什么写入 query/key，以及“可计算更长位置”为何不等于“可靠长上下文”；
> - 面对陌生模型配置时，从 shape 和不变量开始阅读，而不是死记某个版本的参数表。

> [!prerequisite] 第一次看见 `B × T × D`？先补这一页
> 本模块把 shape 当成主语言。若还不能说清 batch、位置和特征三根轴，请先读 [[AI/10-机器学习与深度学习基础/03-张量形状广播与批处理|张量、shape、广播与批处理]]；若还不清楚“线性层—激活—表示”的分工，先读 [[AI/10-机器学习与深度学习基础/09-神经网络层激活函数与表示学习|神经网络、激活函数与表示学习]]。数学权威页是 [[数学/10-数学语言与基础/01-函数符号索引维度与Shape|函数、符号、索引、维度与 Shape]] 与 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]。

## 一张总地图

对典型 decoder-only LLM，可先把一次前向传播压缩成下面这条链：

`token ids (B×T) → embedding (B×T×D) → L 个 Transformer block → final norm → logits (B×T×V)`

每个 block 再拆成两条“读取并写回残差流”的支路：

1. 归一化 → Q/K/V 投影 → 对 Q/K 加位置信息 → causal attention → 输出投影 → 残差相加；
2. 归一化 → 逐位置前馈网络 → 残差相加。

这里最重要的不变量是：**block 的入口和出口通常都是 `B × T × D`。** 注意力会在 token 位置之间搬运信息，前馈网络会在每个位置内部变换特征；二者分工不同。

## 学习路线

| 顺序 | 页面 | 先回答的问题 | 完成标志 |
| ---: | --- | --- | --- |
| 1 | [[AI/20-LLM/20-架构/01-Transformer完整数据流\|Transformer 完整数据流]] | 每个张量从哪里来、到哪里去？ | 能为一组小尺寸写出全程 shape，并区分训练、prefill 与 decode |
| 2 | [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA\|注意力、MHA、MQA 与 GQA]] | token 怎样按内容读取过去？为什么要共享 K/V 头？ | 能算 score shape、KV cache 大小，并解释共享带来的收益与代价 |
| 3 | [[AI/20-LLM/20-架构/03-FFN归一化残差与SwiGLU\|FFN、归一化、残差与 SwiGLU]] | block 怎样逐位置变换特征并维持稳定的信息主干？ | 能沿残差路径说明 norm、FFN 与门控的 shape |
| 4 | [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文\|位置编码、RoPE 与上下文]] | 模型怎样知道先后与距离？怎样判断长上下文声明？ | 能解释相对位置结构，并给出超过训练长度时的证据清单 |
| 5 | [[AI/20-LLM/20-架构/05-Llama主线与模型家族比较\|Llama 主线与模型家族比较]] | 面对不同模型家族，哪些是共同骨架，哪些是可核对差异？ | 能从配置与权重 shape 比较，而不是背版本标签 |
| 6 | [[AI/20-LLM/20-架构/06-MoE架构与路由\|MoE 架构与路由]] | 稀疏专家怎样选择、计算与合并？ | 能区分总参数、激活参数、路由负载和通信成本 |
| 7 | [[AI/20-LLM/20-架构/07-编码器解码器与多模态接口\|编码器、解码器与多模态接口]] | causal decoder 与其他 Transformer 组织方式怎样连接？ | 能按 attention 可见性和接口 shape 区分架构 |

建议按 01–04 建立 block 主干，再读 05–07 扩展到模型家族、稀疏专家和多模态接口，最后回头对照实现。若还不能区分 token、条件概率与 logits，先回到 [[AI/20-LLM/10-原理/00-LLM原理-MOC|LLM 原理 MOC]]。缓存、带宽和内存层级从 [[计算机知识/30-计算机系统/04-缓存局部性带宽与延迟|缓存、局部性、带宽与延迟]] 进入；CUDA kernel、显存布局和融合优化统一从 [[计算机知识/40-并行与异构计算/01-CUDA/00-CUDA-MOC|CUDA MOC]] 进入。本模块只解释它们为何要处理这些 shape 和数据依赖。

## 全模块共用符号

| 符号 | 含义 | 常见约束 |
| --- | --- | --- |
| `B` | batch 中的序列数 | 正整数 |
| `T`、`T_q`、`T_k` | 序列长度、query 长度、key/value 长度 | causal self-attention 中训练时常有 `T_q=T_k=T` |
| `V` | 词表大小 | logits 最后一轴长度 |
| `D` | 模型隐藏维度 `d_model` | 残差流最后一轴长度 |
| `L` | Transformer block 数 | 不等于序列长度 |
| `H_q` | query 头数 | MHA/GQA/MQA 都可能大于 1 |
| `H_{kv}` | key/value 头数 | MHA 为 `H_q`，MQA 为 `1`，GQA 介于两者之间 |
| `D_h` | 每头维度 | 常见但非逻辑必需的关系是 `D=H_qD_h` |

符号只是本模块的约定。阅读论文或配置时必须重新核对作者的定义，尤其不要把 `d_k`、`head_dim`、`hidden_size` 和 `intermediate_size` 混成同一个量。

## 三条理解轨道

### 1. 语义轨：模型在做什么

- embedding 把离散 token id 变成连续特征；
- attention 让当前位置按内容读取允许访问的其他位置；
- 前馈网络在每个位置内部变换特征；
- residual stream 保存并累积各层写入的信息；
- 输出层把隐藏状态映回词表上的 logits。

### 2. Shape 轨：计算为什么成立

每遇到一个式子，依次问：

1. 输入有哪些轴，各轴是什么语义？
2. 哪一根轴被线性投影或求和？
3. 哪些轴会保留到输出？
4. 是否发生 reshape、transpose、broadcast 或拼接？
5. 输出能否写回 `B × T × D` 的残差流？

点积和相似性的几何直觉见 [[数学/20-线性代数与几何/03-点积范数距离与余弦相似度|点积、范数、距离与余弦相似度]]；softmax 的指数归一化和稳定算法见 [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]。

### 3. 工程轨：成本从哪里来

- 权重内存主要随层数和矩阵大小增长；
- full attention 的 score/权重在训练或 prefill 中含 `T_q × T_k`；
- 自回归 decode 的 KV cache 随 `L × T_k × H_{kv} × D_h` 线性增长；
- MQA/GQA 主要减少 K/V 投影与 cache/带宽，不会把所有注意力成本按同样比例消掉；
- 低精度只改变数值表示和字节数，不改变逻辑 shape。浮点边界见 [[数学/60-数值计算与量化/01-二进制浮点精度与数值稳定性|二进制浮点精度与数值稳定性]]。

## 读陌生架构的检查表

不要先问“它像哪一代模型”，先从可核对的结构开始：

- [ ] 是 encoder-only、encoder-decoder，还是 causal decoder-only？
- [ ] embedding 与输出权重是否共享？
- [ ] norm 位于子层之前还是之后，采用什么归一化定义？
- [ ] `H_q`、`H_{kv}`、`D_h` 分别是多少，能否整除并正确分组？
- [ ] 位置方法作用于哪里，位置编号和缩放配置是什么？
- [ ] attention 是 full、sliding-window、稀疏，还是混合形式？
- [ ] 前馈网络的激活、门控和中间维是什么？是否有 MoE 路由？
- [ ] KV cache 存什么、用什么 dtype、是否量化或分页？
- [ ] 训练长度、配置上限、服务端上限和经过评测的可靠长度是否被分开报告？

## 不要从架构图过度推断

同一张“Transformer block”示意图可能隐藏不同的 norm 顺序、bias、位置缩放、mask、cache 布局和精度。反过来，两个配置不同的模型也可能共享同一条高层数据流。可靠结论至少要标出证据层级：

1. **结构事实**：由配置、权重 shape 或源码直接确认；
2. **数学性质**：由明确假设下的公式推出；
3. **实现行为**：由当前内核、运行时和硬件确认；
4. **模型能力**：由与目标长度和任务匹配的评测支持。

公式成立不能替代模型能力评测，单个 benchmark 也不能证明所有输入都可靠。

## 综合练习：画一张不带品牌名的数据流

设 `B=2`、`T=4`、`D=8`、`H_q=2`、`D_h=4`、`V=100`。只画张量和箭头，不写任何具体模型名称：

1. 从 token ids 开始，标出 embedding、Q/K/V、attention scores、attention 输出和 logits 的 shape；
2. 在 score 矩阵上圈出位置 `t=2` 允许访问的列；
3. 写出将一次完整前向用于训练、prefill 和单步 decode 时，`T_q` 与 `T_k` 的区别；
4. 说明哪一步会在词表轴 `V` 上产生分数，哪一步会在过去位置轴 `T_k` 上产生权重。

### 成功标准

- [ ] 我没有把 token id 当成 `D` 维 embedding。
- [ ] 我能解释 score 的两根位置轴分别是 query 位置与 key 位置。
- [ ] 我知道 causal mask 禁止读未来，不等于替模型加入完整距离信息。
- [ ] 我能指出 GQA/MQA 改变 `H_{kv}`，而残差流仍保持 `B × T × D`。
- [ ] 对“上下文扩到原来的 8 倍”这类声明，我会索要训练方法、位置配置、长度分桶评测和资源代价，而不是只看配置值。

---

**返回**：[[AI/20-LLM/00-LLM-MOC|LLM MOC]] · **第一课**：[[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]]


## 补充专题与建议阅读顺序

[[AI/20-LLM/20-架构/08-MLA低秩缓存与位置解耦|MLA低秩缓存与位置解耦]]：补充机制、推导、小例与验证边界。

[[AI/20-LLM/20-架构/09-状态空间线性注意力与混合架构|状态空间线性注意力与混合架构]]：补充机制、推导、小例与验证边界。
