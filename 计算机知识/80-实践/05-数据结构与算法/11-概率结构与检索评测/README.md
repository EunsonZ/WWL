---
type: practice
stage: 4
status: ready
difficulty: 中级
estimated_minutes: 70
domain: computer-science
tags:
  - computer-science/probabilistic-data-structures
  - computer-science/information-retrieval
  - computer-science/vector-search
---

# 概率结构与检索评测

这个标准库实验把两篇稳定课的合同落成可运行例子：

- BloomFilter 展示“阳性只是可能，已插入项不应出现假阴性”的只增语义；理论 FPR 按不同键数而非重复 `add` 次数估计；
- CountMinSketch 展示非负流中的单向高估，并从 ε、δ 生成表尺寸；
- ReservoirSampler 展示不知道流长度时的固定容量样本；
- InvertedIndex 展示 postings、稳定 top-k 与过滤先于排名；
- exact_cosine_search 作为小数据集 oracle，ToyRandomHyperplaneLSH 只演示 ANN 可能漏召回；
- evaluate_toy_lsh 同时报告 recall@k、中位查询延迟与递归对象大小代理值。

这里的固定 seed 只让回归样例可重复。blake2b 分盐哈希、Python 伪随机数和一个 LSH 表都不是标准定理所要求哈希独立性的证明；toy LSH 也没有生产系统需要的多表/多探测、持久化、并发、增删、隔离、向量化或调参机制。

## 运行与观察

在 Vault 根目录运行：

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/11-概率结构与检索评测"
python3 -m unittest -v
python3 retrieval_lab.py
~~~

测试不要求某个未插入 Bloom 键一定返回阴性，因为假阳性正是合同允许的结果；它只检查所有已插入项可查回。测试也不硬编码延迟，因为 wall time 会随主机状态变化，只检查指标存在且非负。

Bloom 的理论近似式中的 $n$ 是**不同键数**。为使这个教学实现能在重复 `add` 时仍报告正确的 $n$，它额外保留以 `key-v1` 类型标签与字节编码表示的精确键集合，并分别公开 `insertion_calls` 与 `distinct_items`。这份集合不属于 Bloom filter 的生产实现：它会额外占用与输入规模线性相关的空间；这里保留它只是为了让公式的前提可观察。该键表示也与本实验的稳定哈希输入一致，不是通用对象序列化协议。

retrieval_lab.py 的直接输出是一个小数据集报告。请把它读成“本进程、这组数据、这个 seed 的观测”，而不是跨机器 SLA：

- recall_at_k：toy LSH 找回 exact top-k 的比例；
- exact_latency_ms / approximate_latency_ms：重复调用的中位 wall time；
- *_storage_proxy_bytes：递归 sys.getsizeof 的对象大小代理，不是 RSS、峰值分配或磁盘索引大小。

## 权限与事实边界

allowed_ids 在倒排和向量实现中先约束候选，再选择 top-k。实验中的集合参数只是已经由权威身份/ACL 层算出的授权域，**不是认证或授权实现**。生产系统仍需在结果返回前复核权限，隔离索引、缓存、日志与计时侧信道。

相似度、关键词命中与 ANN 图/桶只返回候选，不证明文档真实、最新或足以回答问题。RAG 输出必须保留来源与版本并做事实核验，不能把 recall@k 当答案正确率。

## 建议实验

实现边界：Bloom 与 Count-Min 的键只接受精确 `str` 或 `bytes`，字符串用 UTF-8，类型标签使 `"a"` 与 `b"a"` 不同；字节完全相同才属于同一个键。不自动做 Unicode 正规化，不接收字典、列表、整数或任意对象的 `repr`。自检：为什么两个打印相同的对象不一定是同一键，组合字符与预组字符是否相等？先确定应用的等价关系，再选择外部编码；这里不是通用序列化协议。

余弦基线对有限非零向量先分别按最大绝对值缩放，再求范数和归一化点积，避免大数平方溢出。`(1e200,0)` 与自身仍为 1，正交大向量为 0，零向量和 NaN 拒绝。`exact` 指穷举候选集合，不是任意精度运算；ANN 比较仍需要相同快照、过滤和距离定义。

1. 将 Bloom 的 size_bits 从 128 改为 16，在一个固定未插入键域上统计假阳性；分别记录理论近似与实测比例。
2. 将 CMS 的 width 逐步缩小，对一个重尾流记录 estimate - truth，确认非负更新下不会低估，但不要从单个 seed 推出概率定理。
3. 对 seed 0 到 99 分别运行 reservoir，统计每个输入项出现次数；这是有限次模拟，不是均匀性证明。
4. 对 toy LSH 改 num_planes，同时记录平均候选数、recall@k、p50/p95 延迟与对象大小。只报最快值会隐藏权衡。
5. 构造“私有文档全库得分第一、公开文档第二”的输入，确认 allowed_ids 下仍能返回公开 top-1；不要改成先取全库 top-1 再删除。
6. 为 exact 与 ANN 故意传不同过滤集合，观察 recall 数字为何失去可比语义，然后恢复相同快照、相同距离、相同 k 与相同过滤。

## 成功标准

- python3 -m unittest -v 全部通过；
- 能逐项说出 Bloom、CMS、reservoir 的错误合同与假设；
- 能解释 fixed seed 回归测试和概率保证不是同一证据；
- 能用 exact cosine 定义 toy ANN 的 recall@k oracle；
- 能解释延迟、内存、构建成本与召回必须共同评测；
- 能证明未授权 ID 不参与候选排名，并指出这仍不等于完整权限系统；
- 不把 toy LSH 或教学分词器描述为生产搜索组件。

恢复/清理：实验只写标准输出，运行测试可能产生本目录的 __pycache__/。确认精确路径后可删除该缓存；源文件用编辑器撤销或限定路径 Git diff 恢复，不执行仓库级清理。

相关课程：[[计算机知识/50-数据结构与算法/19-概率型数据结构流式摘要与误差合同|概率型数据结构、流式摘要与误差合同]]、[[计算机知识/50-数据结构与算法/20-倒排索引精确近邻与近似向量检索|倒排索引、精确近邻与近似向量检索]]、[[数学/30-概率与统计/05-统计估计置信度与模型评测|统计估计、置信度与模型评测]]、[[AI/20-LLM/70-工程应用与工具链/02-Embedding-Chunking与最小RAG|Embedding、Chunking 与最小 RAG]]。

<!-- code-sync: ./retrieval_lab.py -->
~~~python
"""概率型数据结构与检索评测的标准库教学实现。

本模块强调可观察的合同，不追求生产性能。固定种子只让一次实验可复现，
不把一个样例变成概率保证，也不让 toy LSH 变成生产级 ANN。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import math
import random
import re
import statistics
import sys
import time
from typing import TypeVar


T = TypeVar("T")
Vector = Sequence[float]
TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def key_payload(value: str | bytes) -> bytes:
    """key-v1：精确 str 的 UTF-8 或精确 bytes；类型标签区分两个域。"""
    if type(value) is str:
        return b'key-v1:str\0' + value.encode('utf-8')
    if type(value) is bytes:
        return b'key-v1:bytes\0' + value
    raise TypeError("keys must be str or bytes; arbitrary repr is not a key encoding")


def _stable_hash(value: str | bytes, salt: int) -> int:
    """在 key-v1 字节相等语义下跨进程稳定，不依赖 object repr。"""
    if type(salt) is not int:
        raise TypeError("salt must be an integer")
    payload = str(salt).encode('ascii') + b'\0' + key_payload(value)
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


class BloomFilter:
    """只增不删的 Bloom filter：阴性为确定未加入，阳性只是可能加入。

    ``_distinct_key_payloads`` 只为教学而存在：理论 FPR 的 ``n`` 是不同键数，
    而不是 ``add`` 的调用次数。生产 Bloom filter 不会维护这份精确集合，
    否则会牺牲它节省空间的目的。
    """

    def __init__(self, size_bits: int, hash_count: int, seed: int = 0) -> None:
        if type(size_bits) is not int or size_bits <= 0:
            raise ValueError("size_bits must be a positive integer")
        if type(hash_count) is not int or hash_count <= 0:
            raise ValueError("hash_count must be a positive integer")
        self.size_bits = size_bits
        self.hash_count = hash_count
        self.seed = seed
        self._bits = bytearray((size_bits + 7) // 8)
        self.insertion_calls = 0
        self._distinct_key_payloads: set[bytes] = set()

    @staticmethod
    def _key_payload(value: object) -> bytes:
        """与 _stable_hash 共享相同的类型域及规范编码。"""
        return key_payload(value)

    def _positions(self, value: object) -> tuple[int, ...]:
        return tuple(
            _stable_hash(value, self.seed + index) % self.size_bits
            for index in range(self.hash_count)
        )

    def add(self, value: object) -> None:
        for position in self._positions(value):
            self._bits[position // 8] |= 1 << (position % 8)
        self.insertion_calls += 1
        self._distinct_key_payloads.add(self._key_payload(value))

    @property
    def distinct_items(self) -> int:
        """仅供教学计量；生产 Bloom filter 通常无法精确得知这个值。"""
        return len(self._distinct_key_payloads)

    def __contains__(self, value: object) -> bool:
        return all(
            self._bits[position // 8] & (1 << (position % 8))
            for position in self._positions(value)
        )

    def estimated_false_positive_rate(self) -> float:
        """按不同键数估计的 FPR；独立均匀哈希近似，不是实测证明。"""
        exponent = -self.hash_count * self.distinct_items / self.size_bits
        return (1.0 - math.exp(exponent)) ** self.hash_count

    @property
    def storage_bytes(self) -> int:
        return len(self._bits)


class CountMinSketch:
    """只接受非负增量的 Count-Min sketch。"""

    def __init__(self, width: int, depth: int, seed: int = 0) -> None:
        if type(width) is not int or width <= 0:
            raise ValueError("width must be a positive integer")
        if type(depth) is not int or depth <= 0:
            raise ValueError("depth must be a positive integer")
        self.width = width
        self.depth = depth
        self.seed = seed
        self.total_count = 0
        self._rows = [[0] * width for _ in range(depth)]

    @classmethod
    def from_error_budget(
        cls, epsilon: float, delta: float, seed: int = 0
    ) -> "CountMinSketch":
        if not 0.0 < epsilon < 1.0:
            raise ValueError("epsilon must be between 0 and 1")
        if not 0.0 < delta < 1.0:
            raise ValueError("delta must be between 0 and 1")
        return cls(math.ceil(math.e / epsilon), math.ceil(-math.log(delta)), seed)

    def _columns(self, value: object) -> tuple[int, ...]:
        return tuple(
            _stable_hash(value, self.seed + row) % self.width
            for row in range(self.depth)
        )

    def add(self, value: object, count: int = 1) -> None:
        if type(count) is not int or count < 0:
            raise ValueError("count must be a non-negative integer")
        for row, column in enumerate(self._columns(value)):
            self._rows[row][column] += count
        self.total_count += count

    def estimate(self, value: object) -> int:
        return min(
            self._rows[row][column]
            for row, column in enumerate(self._columns(value))
        )

    @property
    def counter_count(self) -> int:
        return self.width * self.depth


class ReservoirSampler:
    """在不知道流总长度时保留至多 capacity 个项目。"""

    def __init__(self, capacity: int, seed: int = 0) -> None:
        if type(capacity) is not int or capacity < 0:
            raise ValueError("capacity must be a non-negative integer")
        self.capacity = capacity
        self.seen = 0
        self.sample: list[object] = []
        self._random = random.Random(seed)

    def add(self, value: object) -> None:
        self.seen += 1
        if len(self.sample) < self.capacity:
            self.sample.append(value)
            return
        if self.capacity == 0:
            return
        position = self._random.randrange(self.seen)
        if position < self.capacity:
            self.sample[position] = value

    def extend(self, values: Iterable[object]) -> None:
        for value in values:
            self.add(value)

    @property
    def inclusion_probability(self) -> float:
        if self.seen == 0:
            return 0.0
        return min(1.0, self.capacity / self.seen)


def tokenize(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return tuple(token.casefold() for token in TOKEN_RE.findall(text))


class InvertedIndex:
    """term -> postings 的内存索引，按词频求和并稳定地选 top-k。"""

    def __init__(self, documents: Mapping[str, str]) -> None:
        self.documents = dict(documents)
        if any(not isinstance(key, str) or not isinstance(text, str)
               for key, text in self.documents.items()):
            raise TypeError("document ids and texts must be str")
        self.postings: dict[str, dict[str, int]] = defaultdict(dict)
        for document_id, text in self.documents.items():
            for term, frequency in Counter(tokenize(text)).items():
                self.postings[term][document_id] = frequency

    def search(
        self,
        query: str,
        k: int,
        allowed_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        _validate_k(k)
        allowed = set(self.documents) if allowed_ids is None else set(allowed_ids)
        scores: Counter[str] = Counter()
        for term in tokenize(query):
            for document_id, frequency in self.postings.get(term, {}).items():
                if document_id in allowed:  # 权限/租户过滤先于 top-k。
                    scores[document_id] += frequency
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]


def cosine_similarity(left: Vector, right: Vector) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("vectors must be non-empty and have equal dimensions")
    if any(not math.isfinite(value) for value in (*left, *right)):
        raise ValueError("vectors must contain only finite values")
    left_scale, right_scale = max(map(abs, left)), max(map(abs, right))
    if left_scale == 0.0 or right_scale == 0.0:
        raise ValueError("cosine similarity is undefined for a zero vector")
    a = [value / left_scale for value in left]
    b = [value / right_scale for value in right]
    left_norm = math.sqrt(math.fsum(value * value for value in a))
    right_norm = math.sqrt(math.fsum(value * value for value in b))
    return math.fsum((x / left_norm) * (y / right_norm) for x, y in zip(a, b))


def exact_cosine_search(
    vectors: Mapping[str, Vector],
    query: Vector,
    k: int,
    allowed_ids: Iterable[str] | None = None,
) -> list[tuple[str, float]]:
    """过滤后穷举全部可见向量，作为小数据集精确基线。"""
    _validate_k(k)
    allowed = set(vectors) if allowed_ids is None else set(allowed_ids)
    scored = [
        (document_id, cosine_similarity(query, vector))
        for document_id, vector in vectors.items()
        if document_id in allowed
    ]
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:k]


class ToyRandomHyperplaneLSH:
    """只查同一随机超平面桶的 toy ANN；可能漏掉真实近邻。"""

    def __init__(
        self,
        vectors: Mapping[str, Vector],
        num_planes: int = 8,
        seed: int = 0,
    ) -> None:
        if not vectors:
            raise ValueError("vectors must not be empty")
        if type(num_planes) is not int or num_planes <= 0:
            raise ValueError("num_planes must be a positive integer")
        self.vectors = {key: tuple(vector) for key, vector in vectors.items()}
        dimensions = {len(vector) for vector in self.vectors.values()}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("all vectors must have one non-zero shared dimension")
        self.dimension = dimensions.pop()
        random_source = random.Random(seed)
        self.planes = tuple(
            tuple(random_source.gauss(0.0, 1.0) for _ in range(self.dimension))
            for _ in range(num_planes)
        )
        self.buckets: dict[tuple[bool, ...], list[str]] = defaultdict(list)
        for document_id, vector in self.vectors.items():
            cosine_similarity(vector, vector)  # 同时拒绝零向量。
            self.buckets[self._signature(vector)].append(document_id)

    def _signature(self, vector: Vector) -> tuple[bool, ...]:
        if len(vector) != self.dimension:
            raise ValueError("query dimension does not match index")
        scale = max(abs(value) for value in vector)
        if not math.isfinite(scale) or scale == 0.0:
            raise ValueError("vectors must be finite and non-zero")
        normalized = tuple(value / scale for value in vector)
        return tuple(
            math.fsum(value * weight for value, weight in zip(normalized, plane)) >= 0.0
            for plane in self.planes
        )

    def search(
        self,
        query: Vector,
        k: int,
        allowed_ids: Iterable[str] | None = None,
    ) -> list[tuple[str, float]]:
        _validate_k(k)
        cosine_similarity(query, query)
        allowed = set(self.vectors) if allowed_ids is None else set(allowed_ids)
        candidates = [
            document_id
            for document_id in self.buckets.get(self._signature(query), [])
            if document_id in allowed  # 先约束可见候选，再排名。
        ]
        scored = [
            (document_id, cosine_similarity(query, self.vectors[document_id]))
            for document_id in candidates
        ]
        return sorted(scored, key=lambda item: (-item[1], item[0]))[:k]


def recall_at_k(
    exact_results: Sequence[tuple[str, float]],
    approximate_results: Sequence[tuple[str, float]],
) -> float:
    """以精确 top-k 的实际结果数为分母；空真值集合定义为 1。"""
    exact_ids = {document_id for document_id, _ in exact_results}
    approximate_ids = {document_id for document_id, _ in approximate_results}
    if not exact_ids:
        return 1.0
    return len(exact_ids & approximate_ids) / len(exact_ids)


def median_latency_ms(action: Callable[[], object], repeats: int = 20) -> float:
    """同一进程内的粗粒度中位延迟；不是跨机器性能结论。"""
    if type(repeats) is not int or repeats <= 0:
        raise ValueError("repeats must be a positive integer")
    durations = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        action()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    return statistics.median(durations)


def approximate_deep_size_bytes(value: object) -> int:
    """递归 sys.getsizeof 的实验代理值，不等于进程 RSS 或磁盘索引大小。"""
    seen: set[int] = set()

    def visit(item: object) -> int:
        identity = id(item)
        if identity in seen:
            return 0
        seen.add(identity)
        size = sys.getsizeof(item)
        if isinstance(item, dict):
            return size + sum(visit(key) + visit(child) for key, child in item.items())
        if isinstance(item, (list, tuple, set, frozenset)):
            return size + sum(visit(child) for child in item)
        if hasattr(item, "__dict__"):
            return size + visit(vars(item))
        return size

    return visit(value)


@dataclass(frozen=True)
class RetrievalReport:
    recall_at_k: float
    exact_latency_ms: float
    approximate_latency_ms: float
    exact_storage_proxy_bytes: int
    approximate_storage_proxy_bytes: int


def evaluate_toy_lsh(
    vectors: Mapping[str, Vector],
    queries: Sequence[Vector],
    k: int,
    num_planes: int = 8,
    seed: int = 0,
    repeats: int = 20,
) -> RetrievalReport:
    """在同一快照、同一过滤集合、同一 k 下比较 exact 与 toy LSH。"""
    if not queries:
        raise ValueError("queries must not be empty")
    index = ToyRandomHyperplaneLSH(vectors, num_planes=num_planes, seed=seed)
    exact = [exact_cosine_search(vectors, query, k) for query in queries]
    approximate = [index.search(query, k) for query in queries]
    recalls = [recall_at_k(truth, found) for truth, found in zip(exact, approximate)]
    return RetrievalReport(
        recall_at_k=statistics.mean(recalls),
        exact_latency_ms=median_latency_ms(
            lambda: [exact_cosine_search(vectors, query, k) for query in queries],
            repeats,
        ),
        approximate_latency_ms=median_latency_ms(
            lambda: [index.search(query, k) for query in queries], repeats
        ),
        exact_storage_proxy_bytes=approximate_deep_size_bytes(dict(vectors)),
        approximate_storage_proxy_bytes=approximate_deep_size_bytes(index),
    )


def _validate_k(k: int) -> None:
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")


if __name__ == "__main__":
    demo_vectors = {
        "public-a": (1.0, 0.0),
        "public-b": (0.9, 0.1),
        "private": (0.99, 0.01),
        "other": (-1.0, 0.0),
    }
    demo_queries = [(1.0, 0.0), (0.8, 0.2)]
    print(evaluate_toy_lsh(demo_vectors, demo_queries, k=2, num_planes=3, seed=7))
~~~

<!-- code-sync: ./test_retrieval_lab.py -->
~~~python
"""retrieval_lab 的合同、边界与固定种子回归测试。"""

from __future__ import annotations

import unittest

from retrieval_lab import (
    BloomFilter,
    CountMinSketch,
    InvertedIndex,
    ReservoirSampler,
    ToyRandomHyperplaneLSH,
    approximate_deep_size_bytes,
    cosine_similarity,
    evaluate_toy_lsh,
    exact_cosine_search,
    recall_at_k,
)


class ProbabilisticStructureTests(unittest.TestCase):
    def test_bloom_has_no_false_negative_for_inserted_items(self) -> None:
        bloom = BloomFilter(size_bits=128, hash_count=3, seed=7)
        inserted = ["alpha", "beta", "gamma"]
        for item in inserted:
            bloom.add(item)
        self.assertTrue(all(item in bloom for item in inserted))
        self.assertEqual(bloom.storage_bytes, 16)
        self.assertGreaterEqual(bloom.estimated_false_positive_rate(), 0.0)
        self.assertLessEqual(bloom.estimated_false_positive_rate(), 1.0)

    def test_bloom_duplicate_insertions_do_not_raise_theoretical_fpr(self) -> None:
        bloom = BloomFilter(size_bits=4096, hash_count=4, seed=7)
        bloom.add("alpha")
        before_duplicate = bloom.estimated_false_positive_rate()
        bloom.add("alpha")
        self.assertEqual(bloom.insertion_calls, 2)
        self.assertEqual(bloom.distinct_items, 1)
        self.assertEqual(bloom.estimated_false_positive_rate(), before_duplicate)
        bloom.add("beta")
        self.assertEqual(bloom.distinct_items, 2)
        self.assertGreater(bloom.estimated_false_positive_rate(), before_duplicate)

    def test_count_min_never_underestimates_non_negative_stream(self) -> None:
        sketch = CountMinSketch.from_error_budget(0.1, 0.1, seed=11)
        truth = CounterLike()
        for item in ["red", "blue", "red", "green", "red", "blue"]:
            sketch.add(item)
            truth.add(item)
        for item in ["red", "blue", "green", "absent"]:
            self.assertGreaterEqual(sketch.estimate(item), truth[item])
        self.assertEqual(sketch.total_count, 6)
        self.assertEqual(sketch.counter_count, sketch.width * sketch.depth)

    def test_reservoir_is_bounded_and_reproducible(self) -> None:
        first = ReservoirSampler(capacity=4, seed=19)
        second = ReservoirSampler(capacity=4, seed=19)
        first.extend(range(100))
        second.extend(range(100))
        self.assertEqual(first.sample, second.sample)
        self.assertEqual(len(first.sample), 4)
        self.assertEqual(first.seen, 100)
        self.assertAlmostEqual(first.inclusion_probability, 0.04)

    def test_probability_structures_reject_broken_budgets(self) -> None:
        with self.assertRaises(ValueError):
            BloomFilter(0, 1)
        with self.assertRaises(ValueError):
            CountMinSketch.from_error_budget(0.0, 0.1)
        with self.assertRaises(ValueError):
            CountMinSketch(4, 2).add("x", -1)
        with self.assertRaises(ValueError):
            ReservoirSampler(-1)

    def test_count_min_accepts_subnormal_delta_without_reciprocal_overflow(self) -> None:
        sketch = CountMinSketch.from_error_budget(0.1, 1e-320)
        self.assertEqual((sketch.width, sketch.depth), (28, 737))
        sketch.add("red")
        self.assertEqual(sketch.estimate("red"), 1)


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vectors = {
            "public-a": (1.0, 0.0),
            "public-b": (0.8, 0.2),
            "private": (0.99, 0.01),
            "other": (-1.0, 0.0),
        }

    def test_inverted_postings_and_filter_before_top_k(self) -> None:
        index = InvertedIndex(
            {
                "public-a": "cache cache index",
                "public-b": "cache graph",
                "private": "cache cache cache secret",
            }
        )
        unfiltered = index.search("cache", k=1)
        filtered = index.search("cache", k=1, allowed_ids={"public-a", "public-b"})
        self.assertEqual(unfiltered[0][0], "private")
        self.assertEqual(filtered, [("public-a", 2)])

    def test_exact_cosine_is_oracle_and_honors_visibility(self) -> None:
        query = (1.0, 0.0)
        unfiltered = exact_cosine_search(self.vectors, query, k=2)
        filtered = exact_cosine_search(
            self.vectors, query, k=2, allowed_ids={"public-a", "public-b"}
        )
        self.assertEqual([item[0] for item in unfiltered], ["public-a", "private"])
        self.assertEqual([item[0] for item in filtered], ["public-a", "public-b"])
        self.assertAlmostEqual(cosine_similarity((1.0, 0.0), (2.0, 0.0)), 1.0)

    def test_toy_lsh_is_reproducible_but_evaluated_by_recall(self) -> None:
        query = (1.0, 0.0)
        first = ToyRandomHyperplaneLSH(self.vectors, num_planes=3, seed=7)
        second = ToyRandomHyperplaneLSH(self.vectors, num_planes=3, seed=7)
        found_first = first.search(query, k=3, allowed_ids={"public-a", "public-b"})
        found_second = second.search(query, k=3, allowed_ids={"public-a", "public-b"})
        truth = exact_cosine_search(
            self.vectors, query, k=3, allowed_ids={"public-a", "public-b"}
        )
        self.assertEqual(found_first, found_second)
        self.assertTrue(all(item[0] != "private" for item in found_first))
        self.assertGreaterEqual(recall_at_k(truth, found_first), 0.0)
        self.assertLessEqual(recall_at_k(truth, found_first), 1.0)

    def test_toy_lsh_uses_scale_invariant_finite_projection(self) -> None:
        vectors = {"same": (1.7e308, 1.7e308)}
        index = ToyRandomHyperplaneLSH(vectors, num_planes=1, seed=23)
        self.assertEqual(index._signature(vectors["same"]), index._signature((1.0, 1.0)))
        found = index.search((1.0, 1.0), k=1)
        self.assertEqual([document_id for document_id, _ in found], ["same"])
        self.assertAlmostEqual(found[0][1], 1.0)

    def test_report_labels_latency_and_memory_as_measurements(self) -> None:
        report = evaluate_toy_lsh(
            self.vectors,
            [(1.0, 0.0), (0.7, 0.3)],
            k=2,
            num_planes=3,
            seed=7,
            repeats=3,
        )
        self.assertGreaterEqual(report.recall_at_k, 0.0)
        self.assertLessEqual(report.recall_at_k, 1.0)
        self.assertGreaterEqual(report.exact_latency_ms, 0.0)
        self.assertGreaterEqual(report.approximate_latency_ms, 0.0)
        self.assertGreater(report.exact_storage_proxy_bytes, 0)
        self.assertGreater(report.approximate_storage_proxy_bytes, 0)
        self.assertGreater(approximate_deep_size_bytes(first := {"x": [1, 2]}), 0)
        self.assertEqual(first, {"x": [1, 2]})

    def test_vector_and_k_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity((0.0, 0.0), (1.0, 0.0))
        with self.assertRaises(ValueError):
            exact_cosine_search(self.vectors, (1.0,), k=1)
        with self.assertRaises(ValueError):
            exact_cosine_search(self.vectors, (1.0, 0.0), k=0)


class CounterLike:
    """测试用精确计数器，避免把实现自身当 oracle。"""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def add(self, item: str) -> None:
        self.values[item] = self.values.get(item, 0) + 1

    def __getitem__(self, item: str) -> int:
        return self.values.get(item, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]] 与 [[计算机知识/50-数据结构与算法/00-数据结构与算法-MOC|数据结构与算法 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/22-平衡树区间结构与结构扩展地图|数据结构深化：树旋转、区间聚合与扩展地图]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[计算机知识/80-实践/05-数据结构与算法/11-概率结构与检索评测/test_retrieval_contracts.py|test_retrieval_contracts.py]]：2 个检索反例，覆盖余弦的尺度与输入域、键类型的语义区分。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "计算机知识/80-实践/05-数据结构与算法/11-概率结构与检索评测/test_retrieval_contracts.py"
```
