---
type: practice
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 55
domain: computer-science
tags:
  - computer-science/range-query
  - computer-science/storage
  - computer-science/performance
  - computer-science/testing
---

# 区间结构与外存代价

目标：用统一的左闭右开区间对比离线差分和在线 Fenwick 树，分别计数边界写入/扫描步和树槽读写；再用驻留 fence keys 指向有序数据页的两层玩具索引，把页读取数与键比较数分开。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/10-区间结构与外存代价"
python3 --version
python3 -m unittest -v
~~~

预期 `Ran 5 tests ... OK`。成功证据包含：

- `q` 次差分区间更新有 `2q` 次边界写入，最终恰扫描 `n` 个输出位置；
- Fenwick 树的点加和前缀/区间和结果正确，触及树槽数不超过对数量级上界；
- 固定种子 `20260904` 的 256 个唯一键与排序参考结果一致，单点命中只读 1 个数据页；
- 对键 `0..127` 查 `[32,96)`，每页 16 键时读 4 页，每页 1 键时读 64 页，但结果完全相同。

`PagedSortedIndex` 仅是 I/O 计数模型：它在构造时将键全部放在 Python 内存，不实际读写磁盘，不模拟 B+ 树分裂/合并、OS 页缓存、事务或崩溃恢复。因此页读计数只证明抽象布局差异，不是生产存储基准。恢复/清理：实验不访问网络、不写用户数据，只可能生成同目录 `__pycache__/`；确认精确路径后才可删除，源码恢复使用编辑器撤销或 Git diff。

相关稳定课：[[计算机知识/50-数据结构与算法/16-前缀聚合差分扫描线与区间数据结构|前缀聚合、差分、扫描线与区间数据结构]]、[[计算机知识/50-数据结构与算法/18-外存模型分块缓存感知与页式索引|外存模型、分块、缓存感知与页式索引]]。

<!-- code-sync: ./interval_external.py -->
~~~python
"""差分、Fenwick 树与页式有序索引的操作计数实验。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class DifferenceStats:
    boundary_writes: int = 0
    scan_steps: int = 0


@dataclass
class FenwickStats:
    tree_reads: int = 0
    tree_writes: int = 0


@dataclass
class QueryStats:
    page_reads: int = 0
    key_comparisons: int = 0


def offline_range_add(
    length: int, updates: Iterable[tuple[int, int, int]]
) -> tuple[list[int], DifferenceStats]:
    """Apply half-open [left, right) additions with one final prefix scan."""
    if length < 0:
        raise ValueError("length must be non-negative")
    difference = [0] * (length + 1)
    stats = DifferenceStats()
    for left, right, delta in updates:
        if not 0 <= left <= right <= length:
            raise IndexError("update must satisfy 0 <= left <= right <= length")
        difference[left] += delta
        difference[right] -= delta
        stats.boundary_writes += 2

    values: list[int] = []
    running = 0
    for index in range(length):
        running += difference[index]
        values.append(running)
        stats.scan_steps += 1
    return values, stats


class FenwickTree:
    """Point additions and half-open prefix/range sums with explicit counts."""

    def __init__(self, values: Iterable[int]) -> None:
        items = list(values)
        self._size = len(items)
        self._tree = [0] * (self._size + 1)
        self.stats = FenwickStats()
        for index, value in enumerate(items):
            self.add(index, value)
        self.reset_stats()

    def reset_stats(self) -> None:
        self.stats = FenwickStats()

    def add(self, index: int, delta: int) -> None:
        if not 0 <= index < self._size:
            raise IndexError("index out of range")
        cursor = index + 1
        while cursor <= self._size:
            self._tree[cursor] += delta
            self.stats.tree_writes += 1
            cursor += cursor & -cursor

    def prefix_sum(self, end: int) -> int:
        if not 0 <= end <= self._size:
            raise IndexError("end out of range")
        total = 0
        cursor = end
        while cursor > 0:
            total += self._tree[cursor]
            self.stats.tree_reads += 1
            cursor -= cursor & -cursor
        return total

    def range_sum(self, left: int, right: int) -> int:
        if not 0 <= left <= right <= self._size:
            raise IndexError("range must satisfy 0 <= left <= right <= size")
        return self.prefix_sum(right) - self.prefix_sum(left)


def _lower_bound(values: tuple[int, ...], target: int, stats: QueryStats) -> int:
    left, right = 0, len(values)
    while left < right:
        middle = (left + right) // 2
        stats.key_comparisons += 1
        if values[middle] < target:
            left = middle + 1
        else:
            right = middle
    return left


def _upper_bound(values: tuple[int, ...], target: int, stats: QueryStats) -> int:
    left, right = 0, len(values)
    while left < right:
        middle = (left + right) // 2
        stats.key_comparisons += 1
        if values[middle] <= target:
            left = middle + 1
        else:
            right = middle
    return left


class PagedSortedIndex:
    """Toy two-level index: resident fence keys point to sorted data pages."""

    def __init__(self, keys: Iterable[int], page_size: int) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        ordered = sorted(set(keys))
        self.pages = tuple(
            tuple(ordered[start : start + page_size])
            for start in range(0, len(ordered), page_size)
        )
        self.fence_keys = tuple(page[0] for page in self.pages)

    def contains(self, target: int) -> tuple[bool, QueryStats]:
        stats = QueryStats()
        page_index = _upper_bound(self.fence_keys, target, stats) - 1
        if page_index < 0:
            return False, stats
        page = self.pages[page_index]
        stats.page_reads += 1
        position = _lower_bound(page, target, stats)
        found = position < len(page) and page[position] == target
        if position < len(page):
            stats.key_comparisons += 1
        return found, stats

    def range_query(self, left: int, right: int) -> tuple[list[int], QueryStats]:
        """Return keys in the half-open interval [left, right)."""
        if left > right:
            raise ValueError("left must not exceed right")
        stats = QueryStats()
        if not self.pages or left == right:
            return [], stats

        first_page = max(0, _upper_bound(self.fence_keys, left, stats) - 1)
        after_last_page = _lower_bound(self.fence_keys, right, stats)
        results: list[int] = []
        for page_index in range(first_page, after_last_page):
            page = self.pages[page_index]
            stats.page_reads += 1
            for key in page:
                stats.key_comparisons += 1
                if key < left:
                    continue
                stats.key_comparisons += 1
                if key >= right:
                    break
                results.append(key)
        return results, stats
~~~

<!-- code-sync: ./test_interval_external.py -->
~~~python
"""interval_external 的边界语义、操作计数和固定种子测试。"""

from __future__ import annotations

import random
import unittest

from interval_external import FenwickTree, PagedSortedIndex, offline_range_add


class IntervalExternalTests(unittest.TestCase):
    def test_difference_array_uses_two_writes_per_update_and_one_scan(self) -> None:
        values, stats = offline_range_add(
            6,
            [(1, 5, 3), (2, 4, -1), (0, 0, 99)],
        )
        self.assertEqual(values, [0, 3, 2, 2, 3, 0])
        self.assertEqual(stats.boundary_writes, 6)
        self.assertEqual(stats.scan_steps, 6)

    def test_fenwick_queries_and_updates_have_logarithmic_touch_counts(self) -> None:
        size = 64
        tree = FenwickTree(range(size))
        tree.add(0, 7)
        update_writes = tree.stats.tree_writes
        self.assertEqual(tree.range_sum(0, size), sum(range(size)) + 7)
        self.assertLessEqual(update_writes, size.bit_length())
        self.assertLessEqual(tree.stats.tree_reads, 2 * size.bit_length())
        self.assertEqual(tree.range_sum(13, 13), 0)

    def test_fixed_seed_paged_index_matches_sorted_reference(self) -> None:
        rng = random.Random(20260904)
        keys = rng.sample(range(10_000), 256)
        ordered = sorted(keys)
        index = PagedSortedIndex(keys, page_size=16)

        target = ordered[123]
        found, point_stats = index.contains(target)
        self.assertTrue(found)
        self.assertEqual(point_stats.page_reads, 1)

        left, right = ordered[50], ordered[75]
        result, range_stats = index.range_query(left, right)
        self.assertEqual(result, ordered[50:75])
        self.assertEqual(range_stats.page_reads, 2)
        self.assertGreater(range_stats.key_comparisons, 0)

    def test_page_size_changes_transfers_not_query_result(self) -> None:
        keys = list(range(128))
        compact = PagedSortedIndex(keys, page_size=16)
        one_key_pages = PagedSortedIndex(keys, page_size=1)

        compact_result, compact_stats = compact.range_query(32, 96)
        sparse_result, sparse_stats = one_key_pages.range_query(32, 96)
        self.assertEqual(compact_result, sparse_result)
        self.assertEqual(compact_stats.page_reads, 4)
        self.assertEqual(sparse_stats.page_reads, 64)
        self.assertLess(compact_stats.page_reads, sparse_stats.page_reads)

    def test_invalid_ranges_are_rejected(self) -> None:
        with self.assertRaises(IndexError):
            offline_range_add(3, [(2, 4, 1)])
        with self.assertRaises(ValueError):
            PagedSortedIndex([1, 2], 0)
        with self.assertRaises(ValueError):
            PagedSortedIndex([1, 2], 1).range_query(2, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/22-平衡树区间结构与结构扩展地图|数据结构深化：树旋转、区间聚合与扩展地图]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
