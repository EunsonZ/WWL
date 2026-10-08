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
