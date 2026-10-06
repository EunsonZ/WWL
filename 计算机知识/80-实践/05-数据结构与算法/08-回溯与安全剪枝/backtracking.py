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
