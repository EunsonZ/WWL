"""哈希计数、最小堆的 top-k 与二叉搜索树不变量的小型演示。"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable


def word_frequencies(words: Iterable[str]) -> dict[str, int]:
    """用 dict 计数；调用者应自行决定大小写、分词等领域语义。"""
    counts: dict[str, int] = {}
    for word in words:
        if not isinstance(word, str):
            raise TypeError("words must contain str values")
        counts[word] = counts.get(word, 0) + 1
    return counts


def top_k(values: Iterable[int], k: int) -> list[int]:
    """维护大小最多为 k 的最小堆，返回从大到小的 k 个值。"""
    if type(k) is not int or k < 0:
        raise ValueError("k must be a non-negative integer")
    heap: list[int] = []
    for value in values:
        if type(value) is not int:
            raise TypeError("values must contain int values")
        if k == 0:
            continue
        if len(heap) < k:
            heapq.heappush(heap, value)
        elif value > heap[0]:
            heapq.heapreplace(heap, value)
        assert len(heap) <= k
    return sorted(heap, reverse=True)


@dataclass
class _Node:
    key: int
    left: _Node | None = None
    right: _Node | None = None


class BinarySearchTree:
    """不存重复键的 BST；它不做平衡，最坏情况仍可退化为链。"""

    def __init__(self) -> None:
        self._root: _Node | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def insert(self, key: int) -> bool:
        if type(key) is not int:
            raise TypeError("key must be an int")
        if self._root is None:
            self._root = _Node(key)
            self._size = 1
            return True
        node = self._root
        while True:
            if key == node.key:
                return False
            branch = "left" if key < node.key else "right"
            child = getattr(node, branch)
            if child is None:
                setattr(node, branch, _Node(key))
                self._size += 1
                return True
            node = child

    def contains(self, key: int) -> bool:
        if type(key) is not int:
            raise TypeError("key must be an int")
        node = self._root
        while node is not None:
            if key == node.key:
                return True
            node = node.left if key < node.key else node.right
        return False

    def inorder(self) -> list[int]:
        result: list[int] = []

        def visit(node: _Node | None) -> None:
            if node is None:
                return
            visit(node.left)
            result.append(node.key)
            visit(node.right)

        visit(self._root)
        return result

    def validate(self) -> None:
        """用上下界、节点身份和计数显式检查整棵树，成本 O(n)。"""
        seen: set[int] = set()

        def check(node: _Node | None, lower: int | None, upper: int | None) -> int:
            if node is None:
                return 0
            identity = id(node)
            if identity in seen:
                raise AssertionError("BST must not contain cycles or shared child nodes")
            seen.add(identity)
            if lower is not None and node.key <= lower:
                raise AssertionError("BST node violates its lower bound")
            if upper is not None and node.key >= upper:
                raise AssertionError("BST node violates its upper bound")
            return 1 + check(node.left, lower, node.key) + check(node.right, node.key, upper)

        if check(self._root, None, None) != self._size:
            raise AssertionError("BST size does not match its reachable node count")
