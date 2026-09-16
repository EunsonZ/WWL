---
type: lesson
stage: 1
status: ready
difficulty: 入门到进阶
estimated_minutes: 35
topics:
  - llama
  - model-family
  - architecture-comparison
  - model-card
  - checkpoint-compatibility
domain: artificial-intelligence
tags:
  - ai/llm/architecture
---

# Llama 主线与模型家族比较

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 家族名称是入口，不是机制解释。比较新模型应拆成注意力、状态、路由、数据与计算预算，并把作者报告结果与本地复现状态分开。 深化与验证：[[AI/20-LLM/20-架构/12-MLA线性注意力与状态空间的记忆取舍|MLA线性注意力与状态空间的记忆取舍]]；[[AI/20-LLM/80-研究拓展/03-从论文主张到可复现实验|从论文主张到可复现实验]]。


“Llama、Qwen、Mistral、Gemma 哪个架构更好？”不是一个可以只看品牌名回答的问题。同一家族会跨越多代、多个尺寸、dense/MoE、文本/多模态、基础/指令等变体。可靠比较的单位应是：**一个精确模型仓库与 revision，加上一组明确的架构维度**。

本页以 Llama-type decoder block 作为阅读主线，目的不是宣布某个家族永久领先，而是建立一张可复用的比较表。

> [!important] 版本与证据边界
> 本页只讲稳定的架构概念和核验方法。模型代际、层数、隐藏宽度、上下文、词表、GQA 分组、RoPE 配置、是否 MoE/多模态、聊天模板、权重可得性与许可都可能变化。实施前必须回到 [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]，再打开所选模型的官方模型卡，记录完整仓库 ID、revision/commit 与访问日期。

## 学习目标

读完后，你应该能够：

1. 画出一个 Llama-type decoder-only 模型的完整前向主线；
2. 把“模型家族”拆成 attention、位置编码、FFN、Norm、词表、上下文、dense/MoE 等可核验维度；
3. 解释为什么两个参数量接近的模型仍可能不兼容；
4. 区分架构事实、训练事实、产品/API 事实与评测结果；
5. 在不下载权重的情况下完成一份模型卡比较记录。

## 1. Llama-type 主线：逐 token 生成的 decoder-only 模型

先忽略代际差异，一个常见的 Llama-type 文本模型可以抽象成：

```text
token ids [B,T]
  └─ token embedding [B,T,d_model]
      └─ 重复 N 个 decoder block
          ├─ RMSNorm
          ├─ causal self-attention
          │   ├─ Q/K 施加 RoPE
          │   └─ 可采用 MHA / GQA 等头组织
          ├─ residual add
          ├─ RMSNorm
          ├─ SwiGLU FFN
          └─ residual add
      └─ final Norm
          └─ vocabulary projection [B,T,V]
              └─ logits → 下一个 token 的分布
```

这是**阅读主线**，不是所有带 “Llama” 名称权重的永久保证。一个精确 checkpoint 是否共享输入/输出 embedding、是否带 bias、采用哪种 GQA 分组、RoPE 变体和上下文配置，都要看该 checkpoint 的配置与模型卡。

### 单层的公式骨架

设第 $\ell$ 层输入为 $X_\ell\in\mathbb{R}^{B\times T\times d_{model}}$：

$$
U_\ell=X_\ell+\operatorname{CausalAttention}(\operatorname{RMSNorm}(X_\ell))
$$

$$
X_{\ell+1}=U_\ell+\operatorname{SwiGLU}(\operatorname{RMSNorm}(U_\ell))
$$

层数 $N$ 次重复后：

$$
\text{logits}=\operatorname{LMHead}(\operatorname{FinalNorm}(X_N))
$$

矩阵 shape 的基础见 [[数学/20-线性代数与几何/01-向量矩阵与张量|向量、矩阵与张量]] 与 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]。

## 2. 为什么 Llama 适合作为学习主线

它把现代 decoder-only LLM 的几个关键模块放在同一条清晰数据流中：

- 自回归 causal self-attention；
- RoPE 位置处理；
- 以 RMSNorm 和 pre-norm 组织残差块；
- 以 SwiGLU 作为逐 token FFN；
- 可通过 GQA 等设计调整 KV cache 与质量/计算的权衡。

这些模块能帮助阅读许多现代模型，但“使用相同模块名”不代表权重兼容。例如，两个模型都写 `RMSNorm + RoPE + SwiGLU`，只要词表、隐藏宽度、层数、头数、RoPE 参数或参数布局不同，checkpoint 就不能直接互换。

## 3. 比较模型家族时的稳定维度

### 3.1 结构维度

| 维度 | 要问的精确问题 | 为什么影响实现 |
| --- | --- | --- |
| 拓扑 | encoder-only、decoder-only、encoder-decoder，还是带视觉/音频编码器？ | 决定 attention mask、cross-attention 与生成方式 |
| dense / MoE | 每个 token 是否经过全部 FFN 参数，还是只路由到少数专家？ | 总参数、激活参数、通信与部署方式不同 |
| 层数与宽度 | $N$、$d_{model}$、$d_{ff}$ 分别是多少？ | 决定权重 shape、内存和计算 |
| attention 组织 | MHA、MQA、GQA？Q 头和 KV 头各多少？ | 影响投影 shape 与 KV cache |
| 位置方法 | RoPE、绝对位置、相对偏置或其他？参数是什么？ | 影响位置外推、实现和 checkpoint 读取 |
| FFN | GELU FFN、GLU、SwiGLU；bias 如何设置？ | 决定矩阵数量和参数映射 |
| Norm 与顺序 | LayerNorm/RMSNorm；pre-norm/post-norm；$\epsilon$？ | 影响数值与权重兼容 |
| embedding / LM head | 是否共享权重？词表大小与特殊 token？ | 影响参数量、tokenizer 和输出投影 |

### 3.2 行为与接口维度

| 维度 | 必须核验什么 | 不能从什么推断 |
| --- | --- | --- |
| tokenizer | tokenizer 文件、词表、特殊 token、Unicode/字节回退规则 | 不能从模型参数量推断 |
| chat template | system/user/assistant 的格式、终止 token、工具调用格式 | 不能只看家族名或 UI 标签 |
| 上下文 | 配置值、训练/评测范围、运行时是否修改 | 不能把“后端允许设置”当“模型已可靠训练” |
| 模态 | 文本、图像、音频等输入及其预处理器 | 不能因产品支持图片就假定任一权重支持 |
| 输出头 | 普通 LM、分类、embedding、视觉/动作等 | 不能因 base 名称相似就互换 |

### 3.3 训练、评测与许可维度

下面这些不属于“块结构”，但决定模型是否适合任务：

- 训练数据范围与截止信息；
- base、pretrained、instruct/chat 等训练阶段；
- 对齐方法、系统提示和安全策略；
- 评测任务、提示模板、采样参数和污染风险；
- 权重许可、可接受使用条款、地区/组织限制；
- 官方权重、社区转换、量化文件之间的来源链。

因此，架构相似不等于能力、语言覆盖、安全性、许可或部署成本相同。

## 4. Llama、Qwen、Mistral、Gemma：应怎样比较

这四个名称都是**模型家族入口**，不是单一不变配置。可长期保留的结论是比较方法，而不是一张很快过期的参数表。

| 家族入口 | 可作为起点的稳定认识 | 对具体模型必须重新核验 |
| --- | --- | --- |
| Llama | Meta 发布的模型系列；可作为现代 decoder-only 文本块的学习主线 | 代际、文本/多模态、层数、GQA、RoPE、上下文、模板、许可、gated 状态 |
| Qwen | Qwen Team 发布的模型系列，覆盖多种任务与变体 | 精确代际/尺寸、dense/MoE、文本/多模态、思考模式、tokenizer、模板、许可 |
| Mistral | Mistral 发布的模型系列，同时可能有开放权重与服务产品 | 精确型号、dense/MoE、attention/上下文策略、权重可得性、端点与许可 |
| Gemma | Google 发布的开放权重模型家族 | 精确代际/模态/尺寸、Norm/attention/embedding 细节、模板、下载条件与许可 |

> [!warning] 不把系列印象写成模型事实
> “某家族就是 MoE”“某家族一定用滑动窗口”“某家族上下文一定更长”“某家族一定开源”都可能因代际和型号而失真。应把它们改写成可核验问题，并把答案绑定到完整模型 ID 和 revision。

## 5. 一个不下载权重的实际比较例子

假设你准备在两个候选模型中选一个做本地推理。先建立如下记录，不填猜测值：

| 字段 | 候选 A | 候选 B | 证据位置 |
| --- | --- | --- | --- |
| 完整仓库 ID | 待填 | 待填 | 官方模型卡标题/URL |
| revision / commit | 待填 | 待填 | Hub 历史或发布记录 |
| 拓扑 | 待填 | 待填 | `config.json` + 模型卡 |
| 层数、$d_{model}$、$d_{ff}$ | 待填 | 待填 | 配置文件 |
| Q 头 / KV 头 | 待填 | 待填 | 配置文件 |
| 位置方法与参数 | 待填 | 待填 | 配置 + 官方说明 |
| Norm / FFN | 待填 | 待填 | 配置 + 架构文档 |
| dense / MoE | 待填 | 待填 | 配置 + 模型卡 |
| tokenizer / chat template | 待填 | 待填 | tokenizer 文件 + 模型卡 |
| 权重数据类型与总文件大小 | 待填 | 待填 | 仓库文件清单 |
| 许可与用途限制 | 待填 | 待填 | 许可原文 |
| 已验证运行时 | 待填 | 待填 | 后端固定版本的支持说明 |

先完成这张表，再比较显存、质量与延迟。否则“同为 7B/8B 附近”之类的粗标签会掩盖 KV cache、MoE、词表、量化和运行时支持差异。

## 6. 从配置到数据流：一次 shape 审核

假设某个**教学用虚构配置**写着：

```text
vocab_size = 32000
d_model = 4096
num_layers = 32
num_q_heads = 32
num_kv_heads = 8
d_ff = 11008
```

你可以得到：

1. token embedding 输出最后一维是 `4096`；
2. 若每个 Q 头维度为 `4096 / 32 = 128`，则 Q 有 32 个头；
3. K/V 只有 8 个头，说明多个 Q 头共享一组 K/V，属于 GQA 组织；
4. SwiGLU 中间支路最后一维为 `11008`，下投影必须回到 `4096`；
5. 经过 32 层后，LM head 把最后一维映射到 `32000` 个词表 logits。

这些数字只用来练习，**不代表任何真实模型**。真实配置必须来自固定 revision。

## 7. 家族比较中的四类混淆

### 7.1 把架构名当权重身份

“Llama-compatible”可能只表示某个运行时接口或配置类兼容，不证明权重来自 Meta，也不证明 tokenizer、模板、许可相同。

### 7.2 把参数量标签当内存结论

权重内存还受数据类型、量化、MoE 总参数、加载分片和运行时副本影响；运行内存还包括 KV cache、激活、临时缓冲和后端开销。

### 7.3 把上下文配置当能力证明

运行时接受较大的 `context_length`，不证明模型在该长度训练过、质量稳定，也不证明 RoPE 修改没有副作用。

### 7.4 把榜单分数当架构因果

分数可能同时受训练数据、对齐、提示模板、采样、污染、评测脚本和硬件影响。仅凭两张模型卡的分数，不能推出“因为使用 GQA/SwiGLU 所以更聪明”。

## 8. 设计权衡：没有单一总冠军

| 目标 | 需要优先观察 | 可能的代价 |
| --- | --- | --- |
| 降低 KV cache | KV 头数、head_dim、层数、上下文 | 质量与实现支持需实测 |
| 降低权重内存 | 参数量、dense/MoE、精度/量化 | 量化误差、转换兼容性 |
| 提高每 token 容量 | FFN 宽度、MoE 专家与激活专家数 | 计算、通信、负载不均 |
| 增长上下文 | 位置方法、训练范围、后端缓存策略 | 延迟、显存、长文本质量 |
| 支持多模态 | 编码器、projector/resampler、输入模板 | 额外权重、预处理和校准 |
| 方便部署 | 官方格式、后端支持、许可证、模板 | 可能牺牲模型选择空间 |

## 9. 常见失败模式

1. **只写“Qwen/Llama”不写完整型号**，导致后续无法复现。
2. **把社区量化仓库当官方原始权重**，丢失来源链和许可边界。
3. **模型与 tokenizer 混用**，shape 可能能加载，特殊 token 和输出却错误。
4. **聊天模板不匹配**，模型无法正确判断角色边界或停止位置。
5. **只凭文件名猜架构**，忽略 `config.json`、权重键名和运行时支持表。
6. **把 dense 与 MoE 的总参数直接比较**，没有记录每 token 激活专家数。
7. **把 API 产品与开放权重混为一谈**，错误推断可下载性、离线性或许可。
8. **用当前网页覆盖旧实验记录**，没有固定 revision 和核验日期。
9. **只验证成功加载**，未核对 tokenizer、模板、停止 token、最小生成和输出质量。

## 10. 练习：完成一份可审计的模型卡对比

从 Llama、Qwen、Mistral、Gemma 中任选两个**精确模型**。本练习不要求下载任何文件，也不要求运行模型。

1. 写下完整官方仓库 ID 和 revision/commit；
2. 用本页第 5 节的表记录至少 10 个字段；
3. 把每条信息标为“配置事实”“模型卡陈述”“你的推断”之一；
4. 列出至少 3 个仍未知、需要运行验证的问题；
5. 用 100 字以内说明你会为哪种任务选择哪一个，并明确选择依据与未知项。

### 成功标准

- 比较对象精确到仓库和 revision，而非只有家族名；
- 架构、训练/评测、许可、产品接口四类事实没有混写；
- 至少核对拓扑、attention、位置、FFN、Norm、tokenizer、模板、上下文、格式、许可；
- 所有推断都显式标注，没有把缺失字段自行补成“常识”；
- 最终结论能被新证据推翻或更新，而不是“某家族永远更好”。

## 11. 小结

- Llama-type 主线帮助理解现代 decoder-only block，但不是所有型号的完整配置；
- 家族比较应落到明确维度和固定 revision；
- 架构相似不等于 tokenizer、能力、许可、格式或权重兼容；
- Qwen、Mistral、Gemma 与 Llama 都包含会演化的系列，实施前必须回到官方模型卡；
- 一张保留未知项和证据位置的表，比一张很快过期的“品牌参数排名”更可靠。

---

**先修**：[[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]] · [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]] · [[AI/20-LLM/20-架构/03-FFN归一化残差与SwiGLU|FFN、归一化、残差与 SwiGLU]] · [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|RoPE 与上下文]]

**相关概念**：[[AI/20-LLM/20-架构/06-MoE架构与路由|MoE 架构与路由]] · [[AI/20-LLM/20-架构/07-编码器解码器与多模态接口|编码器、解码器与多模态接口]] · [[AI/90-资源/05-官方资料与版本核验记录|官方资料与版本核验记录]]

**返回**：[[AI/20-LLM/20-架构/00-LLM架构-MOC|LLM 架构 MOC]] · [[AI/20-LLM/00-LLM-MOC|LLM MOC]]
