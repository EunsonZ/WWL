---
type: lesson
status: ready
stage: 1
difficulty: 入门到进阶
estimated_minutes: 70
domain: artificial-intelligence
topics:
  - next-token-training
  - gradient-checking
  - generation
  - kv-cache
  - numpy
tags:
  - ai/llm/implementation
---

# 训练循环、Generation 与 KV Cache 实现

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 训练窗口、生成状态与 KV 生命周期使用不同的计数。损失标签不能看未来，缓存 query 却必须带已处理长度；两种偏移应分别记录。 深化与验证：[[AI/12-PyTorch/05-变长批处理Packing与有效Token归一化|变长批处理Packing与有效Token归一化]]；[[AI/20-LLM/40-推理/09-KV缓存分页滑窗与前缀复用|KV缓存分页滑窗与前缀复用]]。


## 目标与适用场景

把上一课的随机 decoder 接到完整的 next-token 闭环：构造右移目标，算 forward 和交叉熵，验证解析梯度，执行梯度下降，再用同一模型比较普通生成与 KV cache 生成。另外用一个最小函数跑通“温度 → top-k → 概率抽样”，让采样不只停留在概念页。本页的目标是看清每个动作的边界，不是用短文本训练一个实用模型。

## 训练样本为什么要右移一位

输入序列若是：

```text
小 模 型 会
```

对应目标就是：

```text
模 型 会 学
```

因此同一窗口中，每个位置都在预测它右边的 token。模型输出 logits `[B,T,V]`，目标是整数 `[B,T]`；softmax 把最后一轴变成概率，交叉熵只取正确 token 的负对数概率再求平均。原理语境见 [[AI/20-LLM/10-原理/02-自回归建模Logits损失与困惑度|自回归、logits、损失与困惑度]]，指数平移的数值理由见 [[数学/50-信息论/02-指数对数Softmax与LogSumExp|指数、对数、Softmax 与 LogSumExp]]。

## 本课训练什么、不训练什么

为让高中代数和 NumPy 就能审计梯度，本脚本把 embedding、attention、FFN 当作固定特征提取器，只更新最后的 `lm_head.weight [D,V]`。设隐藏向量为 `H`，则：

$$
\text{logits}=HW
$$

若已知 loss 对 logits 的梯度 `G`，矩阵乘法的反向结果就是：

$$
\frac{\partial L}{\partial W}=H^\top G
$$

这是真实的 forward、交叉熵、解析梯度和 SGD，不是预先写死 loss；但它只是“训练线性读出层”，不是完整 LLM 预训练。生产训练通过自动微分把梯度继续传过 decoder、attention 和 embedding，并通常使用 AdamW、学习率调度、混合精度、梯度累积、分布式训练与 checkpoint。反向传播的权威页是 [[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]。

## 为什么还要数值梯度检查

解析公式写错时，loss 仍可能偶然下降。梯度检查选择一个权重 `w`，分别计算 `L(w+ε)` 和 `L(w-ε)`：

$$
\frac{\partial L}{\partial w}\approx\frac{L(w+\varepsilon)-L(w-\varepsilon)}{2\varepsilon}
$$

脚本把这个数值结果与解析梯度同一元素比较，要求相对误差小于 `1e-5`。它很慢，只适合小模型和抽查；生产训练不会每一步对全部参数做有限差分。

## Generation：同一个 forward，反复取最后位置

贪心生成每轮做三件事：

1. forward 得到最后位置的 logits；
2. `argmax` 选分数最高的 token；
3. 把新 token 追加到输入，再预测下一个。

主生成循环不含温度、top-k、top-p、重复惩罚或停止 token，所以它只证明 greedy 生成控制流成立。更完整的推理语义见 [[AI/20-LLM/40-推理/01-生成循环Prefill-Decode与KV-Cache|生成循环、prefill、decode 与 KV cache]]。

## 从 greedy 到最小可复现采样

`sample_from_logits` 只接收一维词表 logits，按明确顺序执行：

```text
logits / temperature
  → 只保留 top-k 的 token IDs
  → 减去候选最大 logit
  → exp 并归一化
  → 使用调用者传入的 RNG 抽样
```

把 RNG 从函数外传入，可以看出 seed 属于请求状态，而不是模型权重。主函数用两个同 seed RNG 断言单步抽样一致，并断言 `top_k=2` 不会选到被过滤的 token 0。

> [!warning] 这仍不是通用 sampler chain
> 本函数没有 top-p、min-p、重复惩罚、硬约束、EOS 或跨步历史；`argpartition` 遇到边界并列时的候选细节也不应当成跨平台协议。生产实验需固定处理器顺序、引擎版本和 RNG 状态，语义见 [[AI/20-LLM/40-推理/02-采样停止条件与生成控制|采样、停止条件与生成控制]]。

## KV cache：prefill 一次，以后只送新 token

没有 cache 时，每轮把越来越长的全部前缀重新送过模型，旧 token 的 K/V 被重复计算。cache 路径分两段：

- **prefill**：一次处理 prompt，保存每层的 K/V；
- **decode**：每次只计算新 token 的 Q/K/V，把新 K/V 追加到 cache，让新 Q 对全部 K 做注意力。

本脚本的单层 cache shape 是 `[B,H,Tcache,Dh]`，分别存一份 K 和 V。它用断言要求 cache 与非 cache 产生完全相同的 token 序列；同时检查最终 cache 长度。位置 `start_pos` 必须等于已有 cache 长度，否则 RoPE 位置会错位，脚本主动报错。

## 依赖与 CPU 运行

保留同目录的前两份源码，然后在 Vault 根目录运行：

```bash
python3 -B 'AI/20-LLM/50-实现/tiny_train_generate.py'
```

要求 Python 3.10+、NumPy，全部在 CPU 上完成；不下载模型或数据。本轮 Python 3.14.7、NumPy 2.5.2 实测约十秒。不同 CPU 的时间可变，但固定 seed 下断言和关键数值应可复现。

完成梯度、loss、生成与 cache 断言并以退出码 0 结束才是 **PASS**。若 NumPy 不存在，脚本打印 `SKIP: 缺少 NumPy…`并以退出码 77 结束，这表示没有运行训练/生成验证，不能记为通过。其他非 0 退出、traceback 或断言失败是 **FAIL**。

## 完整可运行源码

采样接口使用非空有限 float64 logits 与有限正温度，先减最大值再除温度；`[1000,999]`、`T=1e-308` 应合法选择第一项。中心化或缩放超出可表示范围时显式报错。top-k 的并列值按 token ID 升序确定保留项；固定 RNG 种子才给可重复采样。自检：解释为何“温度大于 0”不足以保证先做 `logits/T` 不溢出。

<!-- code-sync: ./tiny_train_generate.py -->
~~~python
from __future__ import annotations

try:
    import numpy as np
except ModuleNotFoundError:
    print("SKIP: 缺少 NumPy；本脚本不会自动下载依赖或模型。")
    raise SystemExit(77)

from tiny_decoder import KVCache, TinyDecoderLM
from tiny_tokenizer_embedding import CharTokenizer


TRAIN_TEXT = "小模型会学习。小模型会生成。" * 12


def make_next_token_batch(
    token_ids: list[int], context_length: int
) -> tuple[np.ndarray, np.ndarray]:
    inputs: list[list[int]] = []
    targets: list[list[int]] = []
    for start in range(len(token_ids) - context_length):
        inputs.append(token_ids[start : start + context_length])
        targets.append(token_ids[start + 1 : start + context_length + 1])
    return np.array(inputs, dtype=np.int64), np.array(targets, dtype=np.int64)


def cross_entropy_with_gradient(
    logits: np.ndarray, targets: np.ndarray
) -> tuple[float, np.ndarray]:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    log_normalizer = np.log(np.sum(np.exp(shifted), axis=-1, keepdims=True))
    log_probabilities = shifted - log_normalizer
    probabilities = np.exp(log_probabilities)
    flat_probabilities = probabilities.reshape(-1, probabilities.shape[-1])
    flat_log_probabilities = log_probabilities.reshape(-1, log_probabilities.shape[-1])
    flat_targets = targets.reshape(-1)
    row_indices = np.arange(flat_targets.size)
    loss = -flat_log_probabilities[row_indices, flat_targets].mean()
    gradient = flat_probabilities.copy()
    gradient[row_indices, flat_targets] -= 1.0
    gradient /= flat_targets.size
    return float(loss), gradient.reshape(logits.shape)


def head_loss_and_gradient(
    model: TinyDecoderLM, inputs: np.ndarray, targets: np.ndarray
) -> tuple[float, np.ndarray]:
    hidden, _ = model.features(inputs)
    logits = model.lm_head(hidden)
    loss, logits_gradient = cross_entropy_with_gradient(logits, targets)
    flat_hidden = hidden.reshape(-1, hidden.shape[-1])
    flat_gradient = logits_gradient.reshape(-1, logits_gradient.shape[-1])
    weight_gradient = flat_hidden.T @ flat_gradient
    return loss, weight_gradient


def gradient_check(
    model: TinyDecoderLM, inputs: np.ndarray, targets: np.ndarray
) -> float:
    _, analytic_gradient = head_loss_and_gradient(model, inputs, targets)
    row, column = 0, 0
    original = model.lm_head.weight[row, column]
    epsilon = 1e-5

    model.lm_head.weight[row, column] = original + epsilon
    plus_loss, _ = head_loss_and_gradient(model, inputs, targets)
    model.lm_head.weight[row, column] = original - epsilon
    minus_loss, _ = head_loss_and_gradient(model, inputs, targets)
    model.lm_head.weight[row, column] = original

    numeric_gradient = (plus_loss - minus_loss) / (2.0 * epsilon)
    relative_error = abs(numeric_gradient - analytic_gradient[row, column]) / max(
        1e-8, abs(numeric_gradient) + abs(analytic_gradient[row, column])
    )
    print(
        "gradient check:",
        f"analytic={analytic_gradient[row, column]:.8f}",
        f"numeric={numeric_gradient:.8f}",
        f"relative_error={relative_error:.2e}",
    )
    assert relative_error < 1e-5
    return relative_error


def train_output_head(
    model: TinyDecoderLM,
    inputs: np.ndarray,
    targets: np.ndarray,
    steps: int = 160,
    learning_rate: float = 0.8,
) -> tuple[float, float]:
    initial_loss, _ = head_loss_and_gradient(model, inputs, targets)
    for step in range(steps):
        loss, gradient = head_loss_and_gradient(model, inputs, targets)
        model.lm_head.weight -= learning_rate * gradient
        if step in {0, 39, 79, 119, steps - 1}:
            print(f"step={step + 1:3d}, loss={loss:.4f}")
    final_loss, _ = head_loss_and_gradient(model, inputs, targets)
    assert final_loss < initial_loss * 0.45
    return initial_loss, final_loss


def sample_from_logits(
    logits: np.ndarray,
    rng: np.random.Generator,
    *,
    temperature: float = 1.0,
    top_k: int | None = None,
) -> int:
    """float64 中先中心化再缩放；top-k 并列按 token ID 升序选择。"""
    logits = np.asarray(logits, dtype=np.float64)
    if logits.ndim != 1 or logits.size == 0 or not np.all(np.isfinite(logits)):
        raise ValueError("logits 必须是非空有限的一维数组")
    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("采样温度必须有限且大于 0；greedy 请显式使用 argmax")
    with np.errstate(over='ignore', invalid='ignore'):
        scaled = (logits - np.max(logits)) / temperature
    if not np.all(np.isfinite(scaled)):
        raise ValueError("中心化或温度缩放超出 float64 支持域")
    candidate_ids = np.arange(logits.size)
    if top_k is not None:
        if type(top_k) is not int or not 1 <= top_k <= scaled.size:
            raise ValueError("top_k 必须在 1 到词表大小之间")
        candidate_ids = np.argsort(-scaled, kind='stable')[:top_k]
    candidate_logits = scaled[candidate_ids]
    shifted = candidate_logits - np.max(candidate_logits)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum()
    return int(rng.choice(candidate_ids, p=probabilities))


def generate_without_cache(
    model: TinyDecoderLM, prompt_ids: list[int], new_tokens: int
) -> list[int]:
    generated = prompt_ids.copy()
    for _ in range(new_tokens):
        logits, _ = model.forward(np.array([generated], dtype=np.int64))
        generated.append(int(np.argmax(logits[0, -1])))
    return generated


def generate_with_cache(
    model: TinyDecoderLM, prompt_ids: list[int], new_tokens: int
) -> tuple[list[int], KVCache]:
    generated = prompt_ids.copy()
    logits, cache = model.forward(
        np.array([prompt_ids], dtype=np.int64), start_pos=0, use_cache=True
    )
    assert cache is not None
    for step in range(new_tokens):
        next_token = int(np.argmax(logits[0, -1]))
        generated.append(next_token)
        if step + 1 < new_tokens:
            one_token = np.array([next_token], dtype=np.int64).reshape(1, 1)
            logits, cache = model.forward(
                one_token,
                start_pos=len(generated) - 1,
                cache=cache,
                use_cache=True,
            )
            assert cache is not None
    return generated, cache


def main() -> None:
    tokenizer = CharTokenizer(TRAIN_TEXT)
    inputs, targets = make_next_token_batch(tokenizer.encode(TRAIN_TEXT), context_length=8)
    model = TinyDecoderLM(tokenizer.vocab_size, seed=23)

    gradient_check(model, inputs[:4], targets[:4])
    initial_loss, final_loss = train_output_head(model, inputs, targets)
    print(f"loss: {initial_loss:.4f} -> {final_loss:.4f}")

    toy_logits = np.array([0.0, 1.0, 2.0])
    sampled_a = sample_from_logits(toy_logits, np.random.default_rng(7), top_k=2)
    sampled_b = sample_from_logits(toy_logits, np.random.default_rng(7), top_k=2)
    assert sampled_a == sampled_b and sampled_a in {1, 2}

    prompt_ids = tokenizer.encode("小模型")
    without_cache = generate_without_cache(model, prompt_ids, new_tokens=12)
    with_cache, cache = generate_with_cache(model, prompt_ids, new_tokens=12)
    assert without_cache == with_cache
    assert cache[0].shape[2] == len(with_cache) - 1

    print("生成结果:", tokenizer.decode(with_cache))
    print("最终 K/V shape:", cache[0].shape, cache[1].shape)
    print("断言通过：loss 下降、梯度检查通过、cache 与非 cache 生成一致。")


if __name__ == "__main__":
    main()
~~~

## 实测输出怎样判读

固定 seed 下，本轮得到：

```text
gradient check: analytic=0.02904148 numeric=0.02904148 relative_error=3.09e-10
step=  1, loss=2.6139
step= 40, loss=1.0471
step= 80, loss=0.9070
step=120, loss=0.8329
step=160, loss=0.7833
loss: 2.6139 -> 0.7822
生成结果: 小模型会学习会学习习习习。。小
最终 K/V shape: (1, 2, 14, 4) (1, 2, 14, 4)
断言通过：loss 下降、梯度检查通过、cache 与非 cache 生成一致。
```

不要用生成文字是否自然作为主要验收。训练语料只有两个短句的重复，decoder 主体还是随机冻结的，且主生成路径使用贪心选择；合理验收是解析梯度与数值梯度一致、loss 明显下降、两条生成路径一致、cache 轴符合 `[B,H,Tcache,Dh]`，以及同 seed 的最小 top-k 采样断言通过。

这里 cache 长度是 14 而最终 token 总数是 15，因为最后选出的 token 已追加到结果，但无需再 forward 来预测下一个 token，所以它尚未写入 cache。这是生成循环的边界，不是少缓存了已用于计算的 token。

## 与生产训练和推理的边界

- **训练范围**：只更新输出头；生产预训练更新全部层。
- **优化器**：普通全批量 SGD；生产常用 AdamW、调度、梯度裁剪和混合精度。
- **数据**：脚本常量、字符 token；生产要处理大规模语料治理、切分、shuffle、packing 与分布式加载。
- **梯度检查**：这里只抽一个标量做中心差分；生产主要依赖自动微分、单元测试、数值监控和小规模对照。
- **生成策略**：主路径贪心且固定长度；独立 helper 只演示温度与 top-k 单步采样。生产要处理 EOS、复合 sampler chain、约束解码和错误恢复。
- **cache 管理**：单层 NumPy 数组不断拼接；生产需要每层 cache、预分配或分页、连续批处理、量化与回收策略。
- **性能结论**：本脚本只验证语义等价，不能用来比较 cache 的真实加速倍数。

## 练习

1. 把 `context_length` 从 8 改成 4，先预测 inputs/targets 的第二轴，再运行。
2. 把学习率临时改成 8.0，观察 loss 是否稳定下降；恢复后解释学习率过大的后果。
3. 把 `gradient_check` 的 `row,column` 改为另一个合法位置，确认相对误差仍小。
4. 在 `generate_with_cache` 中故意把 `start_pos` 少 1，读懂主动抛出的错误后恢复。
5. 解释为何完整模型有 `L` 层时要保存 `L` 组 K/V，而不是只存最后一层。
6. 对 logits `[0,1,2]` 把 `temperature` 从 1 改为 2，先说明 top-k 候选 ID 是否改变，再运行多个 seed 观察抽样频率。

## 成功标准

- 只有全部断言完成且退出码为 0 才记为 PASS；缺 NumPy 的 77 是 SKIP，不能写成 loss/cache 已验证。
- 能从连续 token 构造右移一位的 inputs 与 targets。
- 能区分 forward、loss、求梯度和参数更新，知道它们不会自动互相替代。
- 能解释有限差分为何只适合验证，而不适合训练大模型。
- 能手工追踪 prefill 后第一次 decode 的 `start_pos` 与 cache 长度。
- 能说出 cache 省掉的是旧 token 的 K/V 重算，但新 query 仍需读取旧 K 做注意力。
- 能指出温度缩放、top-k 候选、稳定 softmax 和 RNG 抽样的精确顺序。

---

**上一站**：[[AI/20-LLM/50-实现/02-从零实现Attention-RoPE与DecoderBlock|Attention、RoPE 与 DecoderBlock]] · **下一站**：[[AI/20-LLM/50-实现/04-llama.cpp构建后端与调用链|llama.cpp 构建、后端与调用链]] · **概念解释**：[[AI/20-LLM/40-推理/01-生成循环Prefill-Decode与KV-Cache|生成、prefill、decode 与 KV cache]] · **返回**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]] · **总 MOC**：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
