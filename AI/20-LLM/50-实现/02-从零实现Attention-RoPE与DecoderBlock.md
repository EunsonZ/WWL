---
type: lesson
status: ready
content_status: usable
evidence_status: partial
evidence_record: "[[Logs/2026-09-05_改造证据/内容审阅记录]]"
prerequisites:
  - "[[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA]]"
  - "[[AI/20-LLM/50-实现/01-最小Tokenizer与Embedding]]"
stage: 1
difficulty: 入门到进阶
estimated_minutes: 75
domain: artificial-intelligence
topics:
  - causal-self-attention
  - rope
  - decoder-block
  - kv-cache
  - numpy
tags:
  - ai/llm/implementation
---

# 从零实现 Attention、RoPE 与 DecoderBlock

> [!info] 历史证据已补入
> 原有证据字段保持其历史记录；所指 [[Logs/2026-09-05_改造证据/内容审阅记录|内容审阅记录]] 已从 WorkWithLLM 按原字节补入。其范围见 [[Logs/来源材料/WorkWithLLM/README|来源说明]]；本批未重新认证本页内容或提升证据等级。

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 实现对应的数学合同包括转置、Softmax 轴、位置偏移和掩码语义。把完整前向与缓存续写对齐，再用解析梯度和有限差分检查局部算子。 深化与验证：[[AI/20-LLM/20-架构/10-注意力反向传播与Softmax竞争|注意力反向传播与Softmax竞争]]；[[AI/20-LLM/20-架构/11-RoPE相对位置缓存偏移与长度外推|RoPE相对位置缓存偏移与长度外推]]。


## 目标与适用场景

把上一课的 `[B,T,D]` 向量送入一个真正可运行的 decoder block，并用断言验证两个核心性质：位置 `t` 看不到未来 token；整段计算与逐 token KV cache 计算得到相同 logits。适合第一次把 Transformer 结构图对应到数组运算。

## 先抓住四个问题

1. **我要找什么？** 当前 token 经线性映射得到 query（Q）。
2. **上下文里有什么索引？** 每个 token 得到 key（K）。
3. **真正要取回什么内容？** 每个 token 得到 value（V）。
4. **允许看谁？** causal mask 禁止位置 `t` 给 `t+1` 及更远位置分配权重。

单个 head 的缩放点积注意力是：

$$
\operatorname{Attention}(Q,K,V)
=\operatorname{softmax}\!\left(\frac{QK^\top}{\sqrt{D_h}}+M\right)V
$$

加性掩码 `M` 在允许位置为 0，在未来位置为 `−∞`；本脚本用布尔 `allowed` 配合 `np.where` 把对应 score 置为 `-np.inf`，softmax 后未来位置权重为 0。有限的“极小数”不能无条件代替屏蔽，原因与已有反例见下文。点积、转置和矩阵乘法的权威解释在 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法、线性映射与 Einsum]]，稳定 softmax 见 [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]。

## Shape 账本

先固定本次实际输入与模型：`tiny_decoder.py` 的 `main()` 使用同目录 tokenizer 的 `DEMO_TEXT="小模型也能学习。小模型也能生成。"` 建词表，再编码 prompt“小模型也能”。按源码的 `sorted(set(text))`，词表为 `[<unk>,。,也,习,型,学,小,成,模,生,能]`，共 `V=11` 项；prompt 的 IDs 为 `[[6,8,4,2,10]]`。这里没有 BOS、EOS 或 PAD，`<unk>` 的 ID 0 也不表示 padding。

本次采用 `B=1,T=5,D=8,H=2,Dh=4`、单层 block、FFN 中间宽度 16。上一课的 `2×3×6` 用重复“小模型”演示查表；现在改成一条五字前缀，用两个偶数维 head 演示 RoPE、因果读取和五次缓存前向。词表构造沿用上一课，但 embedding 的宽度与 seed 已换，不能复用上一课那张权重。架构页的 `B=2,T=4,D_ff=24,V=100` 是另一份纸上 shape 配置，这里使用真实字符表与脚本默认 `hidden_dim=16`；两页都保留 `D=H×Dh`、残差宽度不变、softmax 沿 key 轴、输出投向当前词表这几条关系。

每一步都应能对上：

| 对象 | 通式 shape | 本次完整前向 | 含义 |
| --- | --- | --- | --- |
| token ids | `[B,T]` | `[1,5]` | 每个位置一个整数 |
| embedding / block 输入、norm 后 | `[B,T,D]` | `[1,5,8]` | 每个 token 一个 D 维向量 |
| Q、K、V 分头后 | `[B,H,T,Dh]` | `[1,2,5,4]` | `D=H×Dh`；RoPE 不改形状 |
| `Q @ Kᵀ` | `[B,H,T,Tk]` | `[1,2,5,5]` | 每个 query 对每个 key 的分数 |
| attention 权重 | `[B,H,T,Tk]` | `[1,2,5,5]` | 最后一轴加和为 1 |
| heads 合并、输出投影与残差 | `[B,T,D]` | `[1,5,8]` | 回到残差支路的宽度 |
| FFN 的 gate、up 与逐元素乘积 | `[B,T,hidden_dim]` | `[1,5,16]` | 同一位置的两条特征投影 |
| FFN down、残差与最终 norm | `[B,T,D]` | `[1,5,8]` | 没有在 T 轴混合位置 |
| logits | `[B,T,V]` | `[1,5,11]` | 每个位置预测词表中下一 token 的分数 |

如果这些符号还不稳，可借读 [[数学/10-数学语言与基础/01-函数符号索引维度与Shape|函数、索引、维度与 shape]]，再回上表从实际 `[1,5]` 继续。

只跟位置 2 的“型”：ID 4 查 embedding 表的第 4 行得到 8 维向量；RMSNorm 后三个 `8×8` 投影各给 8 维，再拆成两头。每头的 4 维 Q/K 在位置 2 旋转，query 2 的 mask 行是 `[真,真,真,假,假]`，因此读的是“小、模、型”对应的 V，不能读“也、能”。两头输出合成 8 维，经输出投影和第一次残差，再走 `8→16` 的 gate/up、逐元素门控及 `16→8` 的 down 和第二次残差，最终 norm、`8×11` lm_head 得到 11 项 logits。这些 logits 预测位置 3 的 token；随机权重并不保证它把“也”排在第一。

## RoPE：旋转 Q 和 K，而不是“加位置编号”

RoPE 把每个 head 的相邻两维看成平面坐标 `(x,y)`，位置 `p` 决定旋转角：

$$
\begin{bmatrix}x'\\y'\end{bmatrix}
=
\begin{bmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{bmatrix}
\begin{bmatrix}x\\y\end{bmatrix}
$$

脚本对 Q、K 应用同一位置规则，不旋转 V。这样点积能携带相对位置信息。完整几何解释与频率构造见 [[数学/20-线性代数与几何/06-三角函数复数旋转与RoPE|三角函数、复数旋转与 RoPE]]；架构语境见 [[AI/20-LLM/20-架构/04-位置编码RoPE与上下文|位置编码、RoPE 与上下文]]。

> [!note] 教学布局边界
> 脚本使用“相邻偶/奇维成对”的最小布局。真实权重可能用不同的 rotary 维度、pairing/layout、基频或上下文缩放方案。旋转矩阵的几何不变，但数组排布必须与模型配置和权重一致；不能把本函数直接贴到任意模型中。

## 一个 DecoderBlock 还有什么

本实现采用接近 Llama 家族的骨架：

```text
x → RMSNorm → causal MHA → +x
  → RMSNorm → SwiGLU FFN  → +残差
```

- **RMSNorm** 把最后一轴按均方根缩放；教学版省略可学习的 scale。
- **SwiGLU FFN** 使用 `silu(gate(x)) * up(x)`，再由 `down` 投回 `D`。
- **残差** 保证 attention 和 FFN 的输出 shape 都必须回到 `[B,T,D]`。
- **lm_head** 把最终隐藏向量映射成 `[B,T,V]` logits。

完整组件顺序见 [[AI/20-LLM/20-架构/01-Transformer完整数据流|Transformer 完整数据流]]，MHA 与 MQA/GQA 的区别见 [[AI/20-LLM/20-架构/02-注意力MHA-MQA与GQA|注意力、MHA、MQA 与 GQA]]。

下面摘出真源 `DecoderBlock.forward` 的函数主体；变量 `values` 始终保存刚才的 `[1,5,8]` 残差流，缓存从 attention 支路返回：

```python
        attention_output, new_cache = self.attention.forward(
            rms_norm(values), start_pos=start_pos, cache=cache, use_cache=use_cache
        )
        values = values + attention_output
        values = values + self.feed_forward(rms_norm(values))
        return values, new_cache
```

改变 head 数时，也先检查这条链。保持 `D=8` 而令 `H=4`，`Dh=2`，Q/K/V 变为 `[1,4,5,2]`，scores 为 `[1,4,5,5]`，合头后仍是 `[1,5,8]`；每头仍可按相邻两维做 RoPE。若换成 `D=6,H=2`，每头 `Dh=3`，本脚本的全维两两旋转不成立，所以主动拒绝。换词表则必须让 tokenizer 的 ID 与 embedding 行、lm_head 列一致；不能把另一词表的同号 token 直接送入旧模型。下面的缓存规则始终针对同一模型配置与同一前缀。

## 从 prefill 到下一次 decode：cache 的时序

先用这张时序账本检查 cache 的 off-by-one。表里的 5、6 是**序列位置**，不是词表 ID；第一个新 token 的 ID 应从本模型的 11 个候选中选出。

| 阶段 | 输入位置 | 返回 logits 预测 | 返回后 cache 逻辑长度 |
| --- | ---: | --- | ---: |
| prefill `0..4` | 5 个 prompt token | 位置 4 之后的第一个新 token | 5 |
| 采样 | 不做 forward | 从上一行 logits 选出位置 5 的 token | 仍为 5 |
| decode `5` | 位置 5 的新 token | 位置 5 之后的 token 6 | 6 |

所以，采样后已经确定的完整序列长度（含 prompt）为 6，cache 仍只含已送入 forward 的前 5 项。最后采样的 token 要在下一次 decode 作为输入时才写入 cache；若此时决定停止，就不需要为它再做一次 forward。这是生成调用的状态账本；本页 `main()` 实际只比较原五个输入的整段前向与逐项缓存前向，不执行采样循环。

prefill 若开启 `use_cache=True`，返回的 K/V 各为 `[1,2,5,4]`，来自这一层 RMSNorm 后的投影，其中 K 已按 `0..4` 做过 RoPE，V 没有旋转。下一次输入新 ID 的 shape 是 `[1,1]`，embedding/norm 为 `[1,1,8]`；必须传入这份 cache 和 `start_pos=5`。新 Q/K/V 各为 `[1,2,1,4]`，Q/K 使用绝对位置 5；旧 K/V 与新项拼成 `[1,2,6,4]`，scores/weights 为 `[1,2,1,6]`，这行 query 可以读 key `0..5`。block 返回 `[1,1,8]`，lm_head 返回 `[1,1,11]`，更新后的 cache 长度才是 6。

位置与 mask 的关键两处直接来自 `CausalSelfAttention.forward`：

```python
        query_positions = np.arange(start_pos, start_pos + sequence)
        queries = apply_rope(self._split_heads(self.query(values)), query_positions)
        new_keys = apply_rope(self._split_heads(self.key(values)), query_positions)
        new_values = self._split_heads(self.value(values))
```

旧、新 K/V 拼接后，再用全部 key 的绝对位置比较：

```python
        key_positions = np.arange(keys.shape[2])
        allowed = key_positions[None, :] <= query_positions[:, None]
```

若在长度 5 的 cache 后一次输入两项，则 query 位置是 `[5,6]`、key 位置是 `0..6`，scores 为 `[1,2,2,7]`；第一行仍不能读第二个新 token，第二行才可读到它。这里比较的是绝对位置，不能把两行简单套进从零开始的 `2×7` 下三角。

cache 还带着**前缀身份**的要求：它必须由当前权重、当前配置和位置规则，按当前 batch 每条序列的同一 token 顺序生成。换了 prompt、调换 batch 行、更新了权重或改变位置规则，都不能仅因 K/V shape 相同就复用旧 cache。本脚本只保存两个数组，不保存 token IDs、模型身份或校验摘要；它能检查长度、shape、dtype 与有限性，前缀身份由调用者保证。Q 是本次读取请求，不作为未来步骤需要的历史 K/V 保存。多层模型则要为每层保存各自的 K/V，不能拿某一层的 cache 代替全部层。

## 依赖与 CPU 运行

当前实现只支持从零开始的前缀缓存。无缓存时 `start_pos` 必须为 0；有缓存时 K/V 均为 `[B,H,start_pos,Dh]`，与输入共用有限 float64 及相同 batch/head/维度。负位置、错误缓存形状和 dtype 在投影前报错。不能让无缓存 query 从 5 开始、key 却从 0 开始，否则长度 3 时第一项就会看见全部 key。

因果性自检应修改未来 token 并检查过去输出不变，再比较完整前向与逐 token 缓存前向；仅检查 mask 数组有三角形不够。这里的输入/缓存检查不构成对任意巨大激活数值都稳定的证明，随机教学权重上的 CPU 断言是它的实际证据范围。

屏蔽位置使用内部 `-inf`，不使用有限的 `-1e30`：若合法 self score 已小于 `-1e30`，有限“低分”反而会让未来位置胜出。每一行保留当前 query 对应的 key，因此没有全屏蔽行。支持域仍要求未屏蔽分数和输出有限；投影或累加溢出会拒绝。独立回归把 Q/K 设成相反投影，在有限大激活下比较单前缀与全量前向，验证的是未来位置确实不参与，而非仅掩码形状正确。

先完成上一课并保留同目录的 `tiny_tokenizer_embedding.py`。本页脚本要求 Python 3.10+、NumPy，只走 CPU：

```bash
python3 -B 'AI/20-LLM/50-实现/tiny_decoder.py'
```

它不联网、不下载模型。固定 seed 只用于得到可复现的随机权重，不表示模型经过训练。

正常环境中，所有数值断言完成且退出码为 0 才是 **PASS**。若 NumPy 不存在，脚本打印 `SKIP: 缺少 NumPy…`并返回 77，这是**未执行数值测试**，不是通过。其他非 0 退出、traceback 或断言失败是 **FAIL**。

## 完整可运行源码

<!-- code-sync: ./tiny_decoder.py -->
~~~python
from __future__ import annotations

import math

try:
    import numpy as np
except ModuleNotFoundError:
    print("SKIP: 缺少 NumPy；本脚本不会自动下载依赖或模型。")
    raise SystemExit(77)

from tiny_tokenizer_embedding import CharTokenizer, DEMO_TEXT, Embedding


KVCache = tuple[np.ndarray, np.ndarray]


def softmax(values: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = values - np.max(values, axis=axis, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.sum(exponentials, axis=axis, keepdims=True)


def rms_norm(values: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
    scale = np.sqrt(np.mean(values * values, axis=-1, keepdims=True) + epsilon)
    return values / scale


def silu(values: np.ndarray) -> np.ndarray:
    return values / (1.0 + np.exp(-values))


def apply_rope(values: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """对 [B, H, T, Dh] 的最后一轴成对旋转，Dh 必须是偶数。"""
    head_dim = values.shape[-1]
    if head_dim % 2 != 0:
        raise ValueError("RoPE 要求每个 head 的维度为偶数")
    inverse_frequencies = 1.0 / (
        10_000.0 ** (np.arange(0, head_dim, 2, dtype=np.float64) / head_dim)
    )
    angles = positions[:, None] * inverse_frequencies[None, :]
    cosines = np.cos(angles)[None, None, :, :]
    sines = np.sin(angles)[None, None, :, :]
    even = values[..., 0::2]
    odd = values[..., 1::2]
    rotated = np.empty_like(values)
    rotated[..., 0::2] = even * cosines - odd * sines
    rotated[..., 1::2] = even * sines + odd * cosines
    return rotated


class Linear:
    def __init__(self, input_dim: int, output_dim: int, rng: np.random.Generator) -> None:
        scale = 1.0 / math.sqrt(input_dim)
        self.weight = rng.normal(0.0, scale, size=(input_dim, output_dim))

    def __call__(self, values: np.ndarray) -> np.ndarray:
        return values @ self.weight


class CausalSelfAttention:
    def __init__(self, d_model: int, num_heads: int, rng: np.random.Generator) -> None:
        if d_model % num_heads != 0:
            raise ValueError("d_model 必须能被 num_heads 整除")
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        if self.head_dim % 2 != 0:
            raise ValueError("为了应用 RoPE，每个 head 的维度必须为偶数")
        self.query = Linear(d_model, d_model, rng)
        self.key = Linear(d_model, d_model, rng)
        self.value = Linear(d_model, d_model, rng)
        self.output = Linear(d_model, d_model, rng)
        self.last_attention_weights: np.ndarray | None = None

    def _split_heads(self, values: np.ndarray) -> np.ndarray:
        batch, sequence, d_model = values.shape
        reshaped = values.reshape(batch, sequence, self.num_heads, self.head_dim)
        return reshaped.transpose(0, 2, 1, 3)

    def _join_heads(self, values: np.ndarray) -> np.ndarray:
        batch, heads, sequence, head_dim = values.shape
        return values.transpose(0, 2, 1, 3).reshape(batch, sequence, heads * head_dim)

    def forward(
        self,
        values: np.ndarray,
        *,
        start_pos: int = 0,
        cache: KVCache | None = None,
        use_cache: bool = False,
    ) -> tuple[np.ndarray, KVCache | None]:
        if type(start_pos) is not int or start_pos < 0:
            raise ValueError("start_pos 必须是非负整数")
        if cache is None and start_pos != 0:
            raise ValueError("无缓存时仅支持 start_pos=0 的前缀")
        if (values.ndim != 3 or values.shape[0] == 0 or values.shape[1] == 0
                or values.shape[2] != self.num_heads * self.head_dim
                or values.dtype != np.float64 or not np.all(np.isfinite(values))):
            raise ValueError("values 必须是有限 float64 [B,T,d_model]，B/T 非空")
        if cache is not None:
            if not isinstance(cache, tuple) or len(cache) != 2:
                raise ValueError("cache 必须为 K/V 二元组")
            expected = (values.shape[0], self.num_heads, start_pos, self.head_dim)
            if any(not isinstance(item, np.ndarray) or item.shape != expected
                   or item.dtype != values.dtype or not np.all(np.isfinite(item))
                   for item in cache):
                raise ValueError("cache 的 batch/head/长度/维度/dtype 必须与当前前缀一致")
        sequence = values.shape[1]
        query_positions = np.arange(start_pos, start_pos + sequence)
        queries = apply_rope(self._split_heads(self.query(values)), query_positions)
        new_keys = apply_rope(self._split_heads(self.key(values)), query_positions)
        new_values = self._split_heads(self.value(values))

        if cache is None:
            keys, cached_values = new_keys, new_values
        else:
            old_keys, old_values = cache
            if old_keys.shape[2] != start_pos:
                raise ValueError("start_pos 必须等于 cache 中已有的 token 数")
            keys = np.concatenate([old_keys, new_keys], axis=2)
            cached_values = np.concatenate([old_values, new_values], axis=2)

        key_positions = np.arange(keys.shape[2])
        allowed = key_positions[None, :] <= query_positions[:, None]
        scores = queries @ keys.transpose(0, 1, 3, 2) / math.sqrt(self.head_dim)
        if not np.all(np.isfinite(scores)) or not np.all(np.isfinite(cached_values)):
            raise ValueError("投影或分数超出有限 float64 支持域")
        # A finite floor is not a mask: valid scores can be even smaller.
        # Every query has its own unmasked position, so no row is all -inf.
        scores = np.where(allowed[None, None, :, :], scores, -np.inf)
        weights = softmax(scores, axis=-1)
        self.last_attention_weights = weights
        attended = weights @ cached_values
        output = self.output(self._join_heads(attended))
        if not np.all(np.isfinite(output)):
            raise ValueError("Attention 输出超出有限 float64 支持域")
        new_cache = (keys, cached_values) if use_cache else None
        return output, new_cache


class FeedForward:
    def __init__(self, d_model: int, hidden_dim: int, rng: np.random.Generator) -> None:
        self.gate = Linear(d_model, hidden_dim, rng)
        self.up = Linear(d_model, hidden_dim, rng)
        self.down = Linear(hidden_dim, d_model, rng)

    def __call__(self, values: np.ndarray) -> np.ndarray:
        return self.down(silu(self.gate(values)) * self.up(values))


class DecoderBlock:
    def __init__(
        self, d_model: int, num_heads: int, hidden_dim: int, rng: np.random.Generator
    ) -> None:
        self.attention = CausalSelfAttention(d_model, num_heads, rng)
        self.feed_forward = FeedForward(d_model, hidden_dim, rng)

    def forward(
        self,
        values: np.ndarray,
        *,
        start_pos: int = 0,
        cache: KVCache | None = None,
        use_cache: bool = False,
    ) -> tuple[np.ndarray, KVCache | None]:
        attention_output, new_cache = self.attention.forward(
            rms_norm(values), start_pos=start_pos, cache=cache, use_cache=use_cache
        )
        values = values + attention_output
        values = values + self.feed_forward(rms_norm(values))
        return values, new_cache


class TinyDecoderLM:
    """单层、无偏置、NumPy CPU 教学模型。"""

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 8,
        num_heads: int = 2,
        hidden_dim: int = 16,
        seed: int = 11,
    ) -> None:
        self.embedding = Embedding(vocab_size, d_model, seed=seed)
        rng = np.random.default_rng(seed + 1)
        self.block = DecoderBlock(d_model, num_heads, hidden_dim, rng)
        self.lm_head = Linear(d_model, vocab_size, rng)

    def features(
        self,
        token_ids: np.ndarray,
        *,
        start_pos: int = 0,
        cache: KVCache | None = None,
        use_cache: bool = False,
    ) -> tuple[np.ndarray, KVCache | None]:
        values = self.embedding(token_ids)
        values, new_cache = self.block.forward(
            values, start_pos=start_pos, cache=cache, use_cache=use_cache
        )
        return rms_norm(values), new_cache

    def forward(
        self,
        token_ids: np.ndarray,
        *,
        start_pos: int = 0,
        cache: KVCache | None = None,
        use_cache: bool = False,
    ) -> tuple[np.ndarray, KVCache | None]:
        hidden, new_cache = self.features(
            token_ids, start_pos=start_pos, cache=cache, use_cache=use_cache
        )
        return self.lm_head(hidden), new_cache


def main() -> None:
    tokenizer = CharTokenizer(DEMO_TEXT)
    token_ids = np.array([tokenizer.encode("小模型也能")], dtype=np.int64)
    model = TinyDecoderLM(tokenizer.vocab_size)

    logits, _ = model.forward(token_ids)
    assert logits.shape == (1, 5, tokenizer.vocab_size)

    changed = token_ids.copy()
    changed[0, -1] = (changed[0, -1] + 1) % tokenizer.vocab_size
    changed_logits, _ = model.forward(changed)
    np.testing.assert_allclose(logits[:, :-1], changed_logits[:, :-1], atol=1e-12)

    full_logits, _ = model.forward(token_ids)
    full_weights = model.block.attention.last_attention_weights
    assert full_weights is not None
    np.testing.assert_allclose(full_weights.sum(axis=-1), 1.0, atol=1e-12)
    np.testing.assert_allclose(np.triu(full_weights[0, 0], k=1), 0.0, atol=1e-12)
    pieces: list[np.ndarray] = []
    cache: KVCache | None = None
    for position in range(token_ids.shape[1]):
        piece, cache = model.forward(
            token_ids[:, position : position + 1],
            start_pos=position,
            cache=cache,
            use_cache=True,
        )
        pieces.append(piece)
    cached_logits = np.concatenate(pieces, axis=1)
    # This is an absolute teaching contract, not NumPy's default mixed tolerance.
    np.testing.assert_allclose(full_logits, cached_logits, rtol=0.0, atol=1e-10)

    weights = model.block.attention.last_attention_weights
    assert weights is not None
    assert cache is not None and cache[0].shape == (1, 2, 5, 4)
    print("logits shape:", logits.shape)
    print("最后一步 attention 权重:", np.round(weights[0, 0, 0], 4).tolist())
    print("KV cache shape:", cache[0].shape)
    print("断言通过：因果性成立，整段前向与逐 token cache 前向一致。")


if __name__ == "__main__":
    main()
~~~

## 三个断言各证明什么

先对照前面的 [[#从 prefill 到下一次 decode：cache 的时序|cache 时序]]，再读 `main()` 中的三个断言。它们检查的是原五项输入，不是采样后多出的 token：

1. `logits.shape == (1,5,V)`：block 和 lm_head 没有丢失 batch 或序列轴。
2. 改掉最后一个 token 后，前四个位置 logits 仍相同：前面位置没有偷看未来。
3. 一次输入五个 token 与每次输入一个并复用 K/V，logits 在 `1e-10` 内一致：位置编号、mask 和 cache 拼接互相吻合。

注意，第三条证明的是这个小实现的**数值等价性**，不是速度基准。NumPy 的小数组、Python 循环和反复 `concatenate` 可能让 cached 版本反而更慢；生产引擎会预分配 cache 并使用融合 kernel。

## 与生产实现的边界

| 教学脚本 | 生产 LLM 常见做法 |
| --- | --- |
| 1 层、`D=8`、2 个 MHA heads | 数十层、更宽，并常用 GQA/MQA 减少 K/V |
| NumPy 默认 `float64` | BF16/FP16/FP8 或量化权重，配数值稳定策略 |
| 朴素 `T×T` attention 矩阵 | FlashAttention、融合算子、分块与专用后端 |
| RMSNorm 无可学习 scale | 每层有训练得到的 norm 参数 |
| 单 batch、无 padding | 变长请求、mask 组合、连续批处理 |
| cache 用 `concatenate` 增长 | 预分配、paged KV cache、显存/内存分层 |

脚本没有 dropout、偏置、权重加载、设备迁移、量化或并行，这些省略是为了隔离核心数据流，不是说生产模型不需要它们。

## 练习

1. 在纸上写出 `queries @ keys.transpose(...)` 两侧的 shape，解释结果为何是 `[B,H,T,Tk]`。
2. 暂时把 `allowed` 全改为真，观察“改变最后 token 不影响过去”的断言如何失败，再恢复。
3. 把 `num_heads` 改为 4。`Dh` 变成多少？为什么仍能做 RoPE？
4. 把 `d_model` 改为 6、`num_heads` 改为 2，解释脚本为什么主动拒绝这个组合。

## 成功标准

- 只有断言完成且退出码为 0 才记为 PASS；退出码 77 只说明缺 NumPy 而 SKIP。
- 能从 `[B,T,D]` 推到 Q/K/V、scores、weights 和输出的 shape。
- 能区分 causal mask 与 RoPE 的职责。
- 能沿代码指出两个 pre-norm、两个残差和 SwiGLU 的位置。
- 能说明 cache 保存 K/V 而不保存 Q 的原因：未来 query 还没出现，旧 K/V 会被后续 query 重用。

---

已经对齐完整前向与缓存前向后，下一问题是：怎样通过 next-token loss 更新读出层，生成循环怎样把选出的 ID 反馈到这里的 `start_pos/cache` 接口？下一课复用 `CharTokenizer` 类、单层模型结构和缓存接口，但训练文本改用“小模型会学习。小模型会生成。”、重新建词表并以 seed 23 初始化模型；本页的字符 ID 与随机权重不能直接当作它的输入和参数。它只训练 `lm_head`，其余组件固定；读到生成函数时，可返回本页时序账本核对选择 token 与送入 forward 的先后。

**上一站**：[[AI/20-LLM/50-实现/01-最小Tokenizer与Embedding|最小 Tokenizer 与 Embedding]] · **下一站**：[[AI/20-LLM/50-实现/03-训练循环Generation与KV-Cache实现|训练循环、Generation 与 KV Cache]] · **返回**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]]


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[AI/20-LLM/50-实现/test_tiny_numpy_contracts.py|test_tiny_numpy_contracts.py]]：因果性、cache、掩码下界、token ID 与采样边界；4 个 NumPy 反例。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "AI/20-LLM/50-实现/test_tiny_numpy_contracts.py"
```
