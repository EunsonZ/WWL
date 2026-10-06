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
        return cls(math.ceil(math.e / epsilon), math.ceil(math.log(1 / delta)), seed)

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
        return tuple(
            sum(value * weight for value, weight in zip(vector, plane)) >= 0.0
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
