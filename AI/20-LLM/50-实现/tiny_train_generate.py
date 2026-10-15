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
