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
    raw_denominations = list(coins)
    if any(type(coin) is not int or coin <= 0 for coin in raw_denominations):
        raise ValueError("coins must be positive integers")
    denominations = sorted(set(raw_denominations))
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
