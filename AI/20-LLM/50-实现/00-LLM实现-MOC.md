---
type: moc
status: ready
stage: 1
difficulty: 入门到进阶
estimated_minutes: 15
domain: artificial-intelligence
topics:
  - llm-implementation
  - transformer
  - numpy
tags:
  - ai/llm/implementation
---

# LLM 实现 MOC

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 已有课程保持原路径。完成入门后，按以下机制深化入口继续；箭头表示推荐阅读次序，不表示后一个概念与前一个等价：[[AI/20-LLM/20-架构/10-注意力反向传播与Softmax竞争|注意力反向传播与Softmax竞争]] → [[AI/20-LLM/20-架构/11-RoPE相对位置缓存偏移与长度外推|RoPE相对位置缓存偏移与长度外推]] → [[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|变长批处理Packing与有效Token归一化]] → [[AI/80-实践/08-深层机制数值实验/00-数值实验导航与验收|数值实验导航与验收]]。


这一组页面把“预测下一个 token”变成一条可以在 CPU 上逐行运行的微型实现。它不是下载来的模型，也不隐藏在框架高级接口里：从字符到整数、从整数到向量、从 Q/K/V 到因果注意力，再到 loss、训练循环、生成与 KV cache，所有关键数组都能看到 shape，所有关键结论都有断言。

## 先看懂这条数据流

```text
文本
  → tokenizer: [字符] → [token id]
  → embedding: [B,T] → [B,T,D]
  → Q/K/V + RoPE + causal attention
  → RMSNorm + 残差 + SwiGLU FFN
  → hidden @ lm_head → logits [B,T,V]
  → 与“右移一位”的目标算交叉熵
  → 更新参数 / 选择下一个 token / 保存 K、V
```

轴的含义是：`B` 为批量，`T` 为序列长度，`D` 为模型宽度，`V` 为词表大小，`H` 为注意力头数。先不熟悉这些符号时，从 [[数学/10-数学语言与基础/01-函数符号索引维度与Shape|索引、维度与 shape]] 开始。

## 两段、六课贯通路线

前三课用可运行 NumPy 数组建立数值直觉，后三课用固定 commit 下的 llama.cpp/GGML 证据链建立系统直觉。两段的证明不能互换：NumPy 断言不证明生产 backend，C++ target 构建成功也不证明真实模型已推理。

| 顺序 | 页面 | 实际完成的东西 | 通过标志 |
| --- | --- | --- | --- |
| 1 | [[AI/20-LLM/50-实现/01-最小Tokenizer与Embedding\|最小 Tokenizer 与 Embedding]] | 固定词表、encode/decode、未知字符、向量查表 | 能解释 `[B,T] → [B,T,D]` |
| 2 | [[AI/20-LLM/50-实现/02-从零实现Attention-RoPE与DecoderBlock\|从零实现 Attention、RoPE 与 DecoderBlock]] | 数值稳定 softmax、MHA、因果 mask、RoPE、RMSNorm、SwiGLU、残差 | 改变未来 token 不会改变过去 logits |
| 3 | [[AI/20-LLM/50-实现/03-训练循环Generation与KV-Cache实现\|训练循环、Generation 与 KV Cache]] | next-token 数据、交叉熵、解析/数值梯度、SGD、贪心生成、最小 top-k 采样与 cache | loss 下降，cache 与非 cache 生成一致，采样候选受控 |
| 4 | [[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链\|llama.cpp 构建、后端与调用链]] | 版本冻结、GGUF 加载、batch/decode/sampler 与 CPU/CUDA offload | 能分层写出“已验证/未验证” |
| 5 | [[AI/20-LLM/50-实现/05-llama.cpp源码阅读与小型扩展\|llama.cpp 源码阅读与小型扩展]] | 从 target 和公共 API 收敛到请求、对象所有权与 trace 契约 | 调用链每条边都能回到固定源码 |
| 6 | [[AI/20-LLM/50-实现/06-GGML张量计算图分配器与Backend\|GGML 张量、计算图、分配器与 Backend]] | tensor/graph/buffer/scheduler、placement、copy 与同步 | 能画出一次 decode 的计算与内存边界 |

伴随源码使用单向依赖：`tiny_train_generate.py → tiny_decoder.py → tiny_tokenizer_embedding.py`。每个 Markdown 页中的 `code-sync` 代码块与同目录源文件逐字一致；源文件是规范来源。

表格本身就是建议顺序：先稳定数值语义，再进入多层实现、分配器和后端。需要只读 llama.cpp 时也可从第 4 课开始，但遇到 Q/K/V、RoPE、FFN 或 cache shape 应回跳到前三课。

## 运行边界

- 环境：Python 3.10+、NumPy，全部数组留在 CPU；本轮实测为 Python 3.14.7、NumPy 2.5.2。
- 数据：脚本内的短字符串；不联网、不下载模型、不下载数据。
- 规模：字符词表、单层 decoder、`D=8`、2 个注意力头，目标是可解释和可断言，不是生成高质量文本。
- 训练：第三课只训练输出投影 `lm_head`，其余层作为固定特征提取器。这是真实的梯度下降，但不是完整预训练；生产训练会用自动微分更新全部参数，并加入优化器状态、混合精度、分布式通信和 checkpoint。
- 推理：cache 是内存中的 NumPy 数组，没有分页、连续批处理、量化、设备后端或显存管理。

## 概念页与实现页怎样互相校验

- 完整架构顺序：[[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]]
- Q/K/V 与多头取舍：[[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]]
- 位置旋转：[[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|RoPE 与上下文]]
- 生成和 cache 的系统解释：[[AI/20-LLM/40-推理/01-生成循环Prefill-Decode与KV-Cache|生成循环、prefill、decode 与 KV cache]]
- 矩阵乘法权威页：[[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]
- Softmax 数值稳定性：[[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]
- 梯度与自动微分：[[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]

## 成功标准

- 能沿着一条 token 的 shape 从 `[B,T]` 追到 `[B,T,V]`。
- 能说明 causal mask 和 RoPE 分别解决“看见谁”与“位置在哪里”。
- 能区分 forward、loss、求梯度、更新参数这四个动作。
- 能说明 prefill 后保存了什么，以及 cache 为什么不保存 query。
- 能指出本实现至少三项与生产 LLM 的差异，不把“能运行”误称为“可用大模型”。

---

**返回**：[[AI/20-LLM/00-LLM-MOC|LLM MOC]] · **第一课**：[[AI/20-LLM/50-实现/01-最小Tokenizer与Embedding|最小 Tokenizer 与 Embedding]] · **综合实践**：[[AI/80-实践/01-微型Transformer预训练/00-微型Transformer预训练|微型 Transformer 预训练]]
