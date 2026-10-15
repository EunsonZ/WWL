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
