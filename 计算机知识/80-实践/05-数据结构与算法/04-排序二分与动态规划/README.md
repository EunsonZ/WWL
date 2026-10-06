---
type: practice
stage: 1
status: ready
difficulty: 入门到中级
estimated_minutes: 45
domain: computer-science
tags:
  - computer-science/sorting
  - computer-science/binary-search
  - computer-science/dynamic-programming
---

# 排序、二分与动态规划

目标：分别验证三个不同前提：归并排序输出有序副本；二分查找要求输入已经非递减；动态规划要求状态和子问题定义清楚。

## 运行、观察与成功标准

在本目录运行：

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/04-排序二分与动态规划"
python3 -m unittest -v
~~~

观察 `first_index` 在调用者保证“整数且非降序”时只执行 `O(log n)` 二分；`first_index_checked` 先线性验证元素类型与相邻顺序，总成本为 `O(n)`，并会拒绝乱序输入。前置条件的验证成本不能偷藏在 `O(log n)` 声明里。归并排序使用双游标线性合并，不使用 Python 列表的 `pop(0)`，也不在递归热路径调用 `sorted` 当 oracle。`min_coin_count` 的 None 是不可达状态，不是零枚硬币；最长递增子序列使用 O(n^2) 表格来展示状态。成功标准：测试通过，能指出二分的有序前提、验证成本和 DP 的状态含义。练习：把 LIS 改为返回一个实际序列，并为 predecessor 加测试。

恢复/清理：本实验只可能产生同目录 __pycache__/；确认路径后可删除。使用编辑器撤销或 Git diff 恢复，不执行仓库级清理。

相关稳定课：[[计算机知识/50-数据结构与算法/08-排序选择与稳定性|排序、选择与稳定性]]、[[计算机知识/50-数据结构与算法/09-二分查找分治与递归|二分查找、分治与递归]]、[[计算机知识/50-数据结构与算法/11-动态规划状态转移与空间优化|动态规划、状态转移与空间优化]]。

<!-- code-sync: ./algorithms.py -->
~~~python
"""排序、二分与动态规划的可读参考实现，不追求标准库级性能。"""

from __future__ import annotations

from typing import Iterable


def merge_sort(values: Iterable[int]) -> list[int]:
    items = list(values)
    if any(type(value) is not int for value in items):
        raise TypeError("merge_sort accepts int values only")
    if len(items) <= 1:
        return items
    middle = len(items) // 2
    left, right = merge_sort(items[:middle]), merge_sort(items[middle:])
    result: list[int] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] <= right[right_index]:
            result.append(left[left_index])
            left_index += 1
        else:
            result.append(right[right_index])
            right_index += 1
    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result


def first_index(sorted_values: list[int], target: int) -> int:
    """在调用者保证整数输入非降序的前提下，以 O(log n) 返回首次位置。"""
    if type(target) is not int:
        raise TypeError("target must be an int")
    low, high, answer = 0, len(sorted_values) - 1, -1
    while low <= high:
        middle = (low + high) // 2
        if sorted_values[middle] >= target:
            if sorted_values[middle] == target:
                answer = middle
            high = middle - 1
        else:
            low = middle + 1
    assert answer == -1 or sorted_values[answer] == target
    return answer


def first_index_checked(values: list[int], target: int) -> int:
    """以 O(n) 验证整数类型和非降序前提，再调用二分核心。"""
    if type(target) is not int or any(type(value) is not int for value in values):
        raise TypeError("values and target must be int")
    if any(left > right for left, right in zip(values, values[1:])):
        raise ValueError("binary search requires non-decreasing input")
    return first_index(values, target)


def min_coin_count(amount: int, coins: Iterable[int]) -> int | None:
    """完全背包 DP；返回 None 表示面额无法组成 amount。"""
    if type(amount) is not int or amount < 0:
        raise ValueError("amount must be a non-negative integer")
    denominations = sorted(set(coins))
    if any(type(coin) is not int or coin <= 0 for coin in denominations):
        raise ValueError("coins must be positive integers")
    best: list[int | None] = [0] + [None] * amount
    for subtotal in range(1, amount + 1):
        candidates = [best[subtotal - coin] for coin in denominations if coin <= subtotal]
        reachable = [count for count in candidates if count is not None]
        if reachable:
            best[subtotal] = min(reachable) + 1
    assert best[0] == 0
    return best[amount]


def lis_length(values: Iterable[int]) -> int:
    """O(n^2) DP，清楚展示“以当前位置结尾”的状态。"""
    items = list(values)
    if any(type(value) is not int for value in items):
        raise TypeError("lis_length accepts int values only")
    if not items:
        return 0
    lengths = [1] * len(items)
    for end in range(len(items)):
        for start in range(end):
            if items[start] < items[end]:
                lengths[end] = max(lengths[end], lengths[start] + 1)
        assert 1 <= lengths[end] <= end + 1
    return max(lengths)
~~~

<!-- code-sync: ./test_algorithms.py -->
~~~python
"""algorithms 的正例、边界和错误输入。"""

from __future__ import annotations

import unittest

from algorithms import first_index, first_index_checked, lis_length, merge_sort, min_coin_count


class AlgorithmsTests(unittest.TestCase):
    def test_sort_binary_search_and_dp_examples(self) -> None:
        self.assertEqual(merge_sort([5, 1, 4, 1]), [1, 1, 4, 5])
        self.assertEqual(first_index([1, 1, 4, 5], 1), 0)
        self.assertEqual(min_coin_count(11, [1, 5, 6]), 2)
        self.assertEqual(lis_length([10, 9, 2, 5, 3, 7, 101, 18]), 4)

    def test_empty_and_unreachable_boundaries(self) -> None:
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(first_index([], 2), -1)
        self.assertIsNone(min_coin_count(3, [2, 4]))
        self.assertEqual(lis_length([]), 0)

    def test_rejects_broken_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            first_index_checked([2, 1], 1)
        with self.assertRaises(ValueError):
            min_coin_count(-1, [1])
        with self.assertRaises(ValueError):
            min_coin_count(3, [0, 1])
        with self.assertRaises(TypeError):
            merge_sort([1, "2"])  # type: ignore[list-item]

    def test_checked_binary_search_separates_validation_from_logarithmic_core(self) -> None:
        self.assertEqual(first_index_checked([1, 1, 4, 5], 1), 0)
        self.assertEqual(first_index([1, 1, 4, 5], 5), 3)
        with self.assertRaises(TypeError):
            first_index_checked([1, "2"], 1)  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]] 与 [[计算机知识/50-数据结构与算法/00-数据结构与算法-MOC|数据结构与算法 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/11-算法设计-课程地图|算法设计 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/23-正确性证明反例与复杂度边界|算法设计深化：证明、反例与复杂度边界]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
