---
type: practice
stage: 1
status: ready
difficulty: 中级
estimated_minutes: 35
domain: computer-science
tags:
  - computer-science/backtracking
  - computer-science/pruning
  - computer-science/counterexample
---

# 回溯与安全剪枝

目标：寻找一个非负整数子集和，并把 `total > target` 剪枝严格限制在已验证的非负输入；负数输入要拒绝，同时保留错误算法的反例。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/08-回溯与安全剪枝"
python3 --version
python3 -m unittest -v
~~~

预期为 `Ran 4 tests ... OK`。`[8, -3]` 可组成 `5`，但若未验证非负性却在 `8 > 5` 时剪枝，就会错误地报告无解；正式函数因此拒绝负数。恢复/清理：本实验不访问网络、不写用户文件，只可能生成同目录 `__pycache__/`；确认路径后才可删除它，源码恢复使用编辑器撤销或 Git diff。

## 不变量到可执行证据

- 只有非负值时，递归路径都满足 `0 <= total <= target` → `subset_sum_nonnegative` 的 `assert` → `test_nonnegative_pruning_invariant_with_repeated_values`。
- 重复元素由不同下标区分，目标为零是合法空解 → 下标列表和终止条件 → `test_zero_target_and_unreachable_boundaries`。
- 负数会推翻单调的“超过目标即无解”推理 → 先拒绝、再保留错误实现作为反例 → `test_rejects_negative_values_before_using_pruning` 与 `test_unchecked_pruning_negative_counterexample_loses_solution`。

相关稳定课：[[计算机知识/50-数据结构与算法/14-回溯搜索剪枝与计算复杂性边界|回溯搜索、剪枝与计算复杂性边界]]。

<!-- code-sync: ./backtracking.py -->
~~~python
"""非负子集和的安全剪枝，以及违反前提时的反例。"""

from __future__ import annotations

from typing import Iterable


def subset_sum_nonnegative(values: Iterable[int], target: int) -> list[int] | None:
    """返回一个命中 target 的下标列表；只有验证非负后才可用 total > target 剪枝。"""
    items = list(values)
    if type(target) is not int or target < 0:
        raise ValueError("target must be a non-negative integer")
    if any(type(value) is not int for value in items):
        raise TypeError("values must contain int values only")
    if any(value < 0 for value in items):
        raise ValueError("negative values invalidate this pruning rule")

    def search(index: int, total: int, chosen: list[int]) -> list[int] | None:
        assert 0 <= total <= target
        if total == target:
            return chosen.copy()
        if index == len(items):
            return None
        value = items[index]
        if total + value <= target:
            with_current = search(index + 1, total + value, chosen + [index])
            if with_current is not None:
                return with_current
        return search(index + 1, total, chosen)

    return search(0, 0, [])


def unsafe_prune_without_nonnegative_validation(values: list[int], target: int) -> list[int] | None:
    """刻意不验证前提的错误版本；负数可把“超过 target”拉回目标。"""
    def search(index: int, total: int, chosen: list[int]) -> list[int] | None:
        if total == target:
            return chosen.copy()
        if index == len(values) or total > target:
            return None
        with_current = search(index + 1, total + values[index], chosen + [index])
        return with_current if with_current is not None else search(index + 1, total, chosen)

    return search(0, 0, [])
~~~

<!-- code-sync: ./test_backtracking.py -->
~~~python
"""backtracking 的非负不变量、边界、拒绝和负数反例。"""

from __future__ import annotations

import unittest

from backtracking import subset_sum_nonnegative, unsafe_prune_without_nonnegative_validation


class BacktrackingTests(unittest.TestCase):
    def test_nonnegative_pruning_invariant_with_repeated_values(self) -> None:
        self.assertEqual(subset_sum_nonnegative([2, 2, 3], 4), [0, 1])

    def test_zero_target_and_unreachable_boundaries(self) -> None:
        self.assertEqual(subset_sum_nonnegative([], 0), [])
        self.assertIsNone(subset_sum_nonnegative([4, 6], 5))

    def test_rejects_negative_values_before_using_pruning(self) -> None:
        with self.assertRaises(ValueError):
            subset_sum_nonnegative([8, -3], 5)
        with self.assertRaises(ValueError):
            subset_sum_nonnegative([1], -1)

    def test_unchecked_pruning_negative_counterexample_loses_solution(self) -> None:
        self.assertIsNone(unsafe_prune_without_nonnegative_validation([8, -3], 5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/22-平衡树区间结构与结构扩展地图|数据结构深化：树旋转、区间聚合与扩展地图]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
