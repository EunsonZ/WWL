---
type: practice
stage: 1
status: ready
difficulty: 入门到中级
estimated_minutes: 40
domain: computer-science
tags:
  - computer-science/hash
  - computer-science/heap
  - computer-science/tree
---

# 哈希、堆与树

目标：在三个小问题中选择不同结构：字词计数用 dict、持续保留最大 k 个值用最小堆、保持键有序用二叉搜索树。

## 运行、观察与成功标准

在本目录运行：

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/02-哈希堆与树"
python3 -m unittest -v
~~~

观察 top_k 的堆从不超过 k 个元素；观察 BST 的中序遍历必为严格递增。BST 故意不平衡：递增插入会退化成链，不能把它当作工业索引。`validate()` 用上下界、节点身份与计数扫描整棵树；它能抓住深层越界、环和共享孩子，但是 `O(n)` 的显式教学验证，不是默认插入成本的一部分。成功标准：测试通过，能区分哈希的查找语义、堆的局部顺序和 BST 的全子树边界不变量。练习：为 BST 加 height，只做观察，先不要假装实现了平衡树。

恢复/清理：只会产生同目录 __pycache__/；确认目标后可删除它。用编辑器撤销或 Git diff 恢复源码，不删除其他实践目录。

相关稳定课：[[计算机知识/50-数据结构与算法/04-哈希表集合与冲突处理|哈希表、集合与冲突处理]]、[[计算机知识/50-数据结构与算法/05-树二叉搜索树堆与优先队列|树、二叉搜索树、堆与优先队列]]、[[计算机知识/50-数据结构与算法/06-平衡树B树Trie与索引结构|平衡树、B 树、Trie 与索引结构]]。

<!-- code-sync: ./structures.py -->
~~~python
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
~~~

<!-- code-sync: ./test_structures.py -->
~~~python
"""structures 的正例、边界和错误输入。"""

from __future__ import annotations

import unittest

from structures import BinarySearchTree, top_k, word_frequencies


class StructuresTests(unittest.TestCase):
    def test_hash_frequency_and_heap_top_k(self) -> None:
        self.assertEqual(word_frequencies(["red", "blue", "red"]), {"red": 2, "blue": 1})
        self.assertEqual(top_k([4, 1, 9, 3, 9, 2], 3), [9, 9, 4])

    def test_empty_and_duplicate_tree_boundary(self) -> None:
        self.assertEqual(top_k([], 2), [])
        tree = BinarySearchTree()
        for key in [5, 2, 8, 1, 3]:
            self.assertTrue(tree.insert(key))
            tree.validate()
        self.assertFalse(tree.insert(3))
        self.assertEqual(tree.inorder(), [1, 2, 3, 5, 8])
        self.assertTrue(tree.contains(8))
        self.assertFalse(tree.contains(4))
        self.assertEqual(len(tree), 5)

    def test_tree_validator_rejects_a_deep_global_order_violation(self) -> None:
        tree = BinarySearchTree()
        for key in [10, 5, 15, 7]:
            tree.insert(key)
        assert tree._root is not None and tree._root.left is not None
        assert tree._root.left.right is not None
        tree._root.left.right.key = 12
        with self.assertRaises(AssertionError):
            tree.validate()

    def test_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            top_k([1], -1)
        with self.assertRaises(TypeError):
            word_frequencies(["ok", 3])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            BinarySearchTree().insert(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]] 与 [[计算机知识/50-数据结构与算法/00-数据结构与算法-MOC|数据结构与算法 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/21-动态结构不变量与摊还分析推演|数据结构深化：从不变量推到摊还代价]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
