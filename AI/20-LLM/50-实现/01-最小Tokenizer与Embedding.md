---
type: lesson
status: ready
stage: 1
difficulty: 入门
estimated_minutes: 35
domain: artificial-intelligence
topics:
  - tokenizer
  - embedding
  - vocabulary
  - numpy
tags:
  - ai/llm/implementation
---

# 最小 Tokenizer 与 Embedding

<!-- deep-review-02 -->
> [!tip] 本轮深化：从当前概念继续追问
> 教学 tokenizer 的目的在于说明离散接口与参数查表，不代表其切分效率接近工业词表。比较 loss 时应固定分词协议，并核对向量几何。 深化与验证：[[AI/20-LLM/10-原理/07-语言模型目标分词粒度与评测可比性|语言模型目标分词粒度与评测可比性]]；[[AI/11-数学与统计桥梁/01-向量空间投影SVD与低秩|向量空间投影SVD与低秩]]。


## 目标与适用场景

把文本真正变成模型能计算的数字，并能逐轴解释 embedding 的输出。学完应能回答：token id 是不是词的含义、同一个 id 为什么总查到同一行、`[B,T,D]` 中每一轴是谁。

## 第一步：字符到整数

计算机不能直接对“模型”两个字做矩阵乘法。最小 tokenizer 建立两张互逆表：

- `token_to_id`：字符到整数，例如 `小 → 6`；
- `id_to_token`：整数回到字符，用于 decode；
- `0` 专门表示训练词表中没有的字符 `<unk>`。

本课按 Python 字符串的 Unicode **code point** 切分，并用 `sorted(set(text))` 固定顺序。这让同一段建表文本在不同次运行中得到相同 id，但不保证一个人眼字素（grapheme cluster）只有一个 ID：组合音标、某些 emoji 和 ZWJ 序列都可能拆成多个 code point。它很适合教学，却不等于生产 tokenizer：真实 LLM 常用 BPE、Unigram 等子词算法，还必须精确处理正规化、空格、字节回退、特殊 token 与版本兼容。文本和 token 的概念边界先见 [[AI/20-LLM/10-原理/01-文本Unicode-Token与词表|文本、Unicode、token 与词表]]。

> [!warning] ID 只是索引
> `6` 比 `4` 大，不表示“第 6 个 token 的语义更多”。ID 的工作只是指出 embedding 矩阵的哪一行。

## 第二步：整数到向量

若 embedding 权重 `E` 的 shape 是 `[V,D]`，其中 `V` 是词表大小、`D` 是模型宽度，那么一个 id `i` 的向量就是第 `i` 行：

$$
\operatorname{Embedding}(i)=E[i]
$$

批量 token id 为 `[B,T]` 时，NumPy 的高级索引一次查出 `[B,T,D]`。这不是 one-hot 乘法的唯一实现，但数值上可把查表理解为 one-hot 向量选择矩阵的一行。shape 规则见 [[数学/10-数学语言与基础/01-函数符号索引维度与Shape|函数、索引、维度与 shape]]，矩阵视角见 [[数学/20-线性代数与几何/02-矩阵乘法线性映射与Einsum|矩阵乘法与线性映射]]。

## 依赖与 CPU 运行

脚本要求 Python 3.10+ 和 NumPy，只使用 CPU，不联网，也不会下载模型。先在你自己的环境确认 `python3 -c "import numpy; print(numpy.__version__)"` 成功，再在 Vault 根目录运行：

```bash
python3 -B 'AI/20-LLM/50-实现/tiny_tokenizer_embedding.py'
```

`-B` 表示不生成 `__pycache__`。正常执行完成所有断言并以退出码 0 结束，记为 **PASS**。若没有 NumPy，脚本打印 `SKIP: 缺少 NumPy…`并以退出码 77 结束，记为 **SKIP**，不能算作功能通过。其他非 0 退出、traceback 或断言失败记为 **FAIL**。依赖安装应在你选定的虚拟环境中按 NumPy 官方说明完成，不要让课程脚本擅自改变环境。

## 完整可运行源码

ID 合同：tokenizer 解码和 embedding 查表只接受合法整数 ID，范围是 `[0,vocab_size)`。未知字符编码为 0；负索引明确拒绝，不借用 Python 的“从末尾取值”语义。自检：未知字符与 `-1` 为什么不是同一个事件？前者是定义好的 `<unk>`，后者是调用错误。

<!-- code-sync: ./tiny_tokenizer_embedding.py -->
~~~python
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
~~~

## 读输出，不只看“成功”

本轮固定 seed 的关键输出是：

```text
token ids: [6, 8, 4]
embedding shape: (2, 3, 6)
第一个向量: [-0.0065, 0.1769, -0.1167, -0.0223, 0.0221, 0.0128]
断言通过：往返编码、未知字符和 embedding 查表均符合预期。
```

`(2,3,6)` 应逐字读成：“2 条相同样本，每条 3 个 token，每个 token 是 6 维向量。”两条样本相同，所以断言要求 `vectors[0]` 与 `vectors[1]` 完全相同；第一个向量也必须正好等于 embedding 权重第 6 行。

## 训练时会改变什么

本页只初始化和查表，没有学习。完整训练时，embedding 的每一行都是参数；反向传播会给本批次用到的行产生梯度，优化器再更新它们。ID 没有变化，变化的是该行向量。梯度如何沿计算图返回，见 [[数学/40-微积分与优化/03-计算图反向传播与自动微分|计算图、反向传播与自动微分]]。

## 练习

1. 把输入改为 `"模型小"`，先写出预期 shape，再运行验证。
2. 编码 `"A"`，解释为什么得到 0，以及 decode 为什么显示替代字符。
3. 把 `d_model=6` 改为 8；列出哪些轴改变，哪些轴不变。
4. 思考：如果重新用另一段文本建词表，旧模型的 embedding 权重还能直接配合新 id 吗？为什么？

## 成功标准

- 只有脚本完成断言且退出码为 0 才记为 PASS；缺 NumPy 的退出码 77 是 SKIP，不是 PASS。
- 能区分字符、token、token id 和 embedding 向量。
- 能从 `[V,D]` 的权重解释 `[B,T] → [B,T,D]`。
- 能解释固定词表为何是模型文件兼容性的一部分。
- 能明确说出字符 tokenizer 与真实子词 tokenizer 的边界。

---

**上一站**：[[AI/20-LLM/50-实现/00-LLM实现-MOC|LLM 实现 MOC]] · **下一站**：[[AI/20-LLM/50-实现/02-从零实现Attention-RoPE与DecoderBlock|Attention、RoPE 与 DecoderBlock]] · **返回**：[[AI/20-LLM/00-LLM-MOC|LLM MOC]]
