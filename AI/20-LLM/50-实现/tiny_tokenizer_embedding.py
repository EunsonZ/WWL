from __future__ import annotations

try:
    import numpy as np
except ModuleNotFoundError:
    print("SKIP: 缺少 NumPy；本脚本不会自动下载依赖或模型。")
    raise SystemExit(77)


DEMO_TEXT = "小模型也能学习。小模型也能生成。"


class CharTokenizer:
    """为教学准备的确定性字符 tokenizer；0 号留给未知字符。"""

    def __init__(self, text: str) -> None:
        vocabulary = ["<unk>", *sorted(set(text))]
        self.token_to_id = {token: index for index, token in enumerate(vocabulary)}
        self.id_to_token = vocabulary

    @property
    def vocab_size(self) -> int:
        return len(self.id_to_token)

    def encode(self, text: str) -> list[int]:
        return [self.token_to_id.get(character, 0) for character in text]

    def decode(self, token_ids: list[int]) -> str:
        pieces: list[str] = []
        for token_id in token_ids:
            if not isinstance(token_id, (int, np.integer)) or isinstance(token_id, bool):
                raise TypeError("token ID 必须是整数")
            if not 0 <= token_id < self.vocab_size:
                raise ValueError("token ID 超出词表范围")
            token = self.id_to_token[token_id]
            pieces.append("�" if token == "<unk>" else token)
        return "".join(pieces)


class Embedding:
    """把整数 token id 查表为 d_model 维向量。"""

    def __init__(self, vocab_size: int, d_model: int, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.weight = rng.normal(0.0, 0.2, size=(vocab_size, d_model))

    def __call__(self, token_ids: np.ndarray) -> np.ndarray:
        if not np.issubdtype(token_ids.dtype, np.integer):
            raise TypeError("embedding 的索引必须是整数")
        if np.any(token_ids < 0) or np.any(token_ids >= self.weight.shape[0]):
            raise ValueError("embedding token ID 超出词表范围")
        return self.weight[token_ids]


def main() -> None:
    tokenizer = CharTokenizer(DEMO_TEXT)
    token_ids = tokenizer.encode("小模型")
    batch_ids = np.array([token_ids, token_ids], dtype=np.int64)
    embedding = Embedding(tokenizer.vocab_size, d_model=6, seed=7)
    vectors = embedding(batch_ids)

    print("词表:", tokenizer.id_to_token)
    print("token ids:", token_ids)
    print("embedding shape:", vectors.shape)
    print("第一个向量:", np.round(vectors[0, 0], 4).tolist())

    assert tokenizer.decode(token_ids) == "小模型"
    assert tokenizer.encode("未登录字符A")[-1] == 0
    assert vectors.shape == (2, 3, 6)  # [batch, sequence, d_model]
    np.testing.assert_array_equal(vectors[0], vectors[1])
    np.testing.assert_array_equal(vectors[0, 0], embedding.weight[token_ids[0]])
    print("断言通过：往返编码、未知字符和 embedding 查表均符合预期。")


if __name__ == "__main__":
    main()
