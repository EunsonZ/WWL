"""用显式容量观察动态数组的摊还追加，不替代 Python list。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DynamicIntArray:
    """只保存 int 的教学数组；0 <= size <= capacity 是核心不变量。"""

    _capacity: int = 1
    _items: list[int | None] = field(default_factory=list)
    _size: int = 0
    resize_events: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if type(self._capacity) is not int or self._capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if self._items:
            raise ValueError("items are managed by DynamicIntArray")
        self._items = [None] * self._capacity
        self._check_invariant()

    def __len__(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return self._capacity

    def append(self, value: int) -> None:
        if type(value) is not int:
            raise TypeError("DynamicIntArray accepts int values only")
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._items[self._size] = value
        self._size += 1

    def get(self, index: int) -> int:
        if type(index) is not int:
            raise TypeError("index must be an int")
        if index < 0 or index >= self._size:
            raise IndexError("index is outside the logical array")
        value = self._items[index]
        assert value is not None
        return value

    def pop(self) -> int:
        if self._size == 0:
            raise IndexError("pop from an empty DynamicIntArray")
        self._size -= 1
        value = self._items[self._size]
        self._items[self._size] = None
        assert value is not None
        return value

    def values(self) -> list[int]:
        return [self.get(index) for index in range(self._size)]

    def validate(self) -> None:
        """显式扫描整个表示并检查不变量。

        该操作为 O(capacity)，故不放在 append/pop 的默认热路径上。
        """
        self._check_invariant()

    def _resize(self, new_capacity: int) -> None:
        assert new_capacity >= self._size
        old_capacity = self._capacity
        replacement: list[int | None] = [None] * new_capacity
        replacement[: self._size] = self._items[: self._size]
        self._items = replacement
        self._capacity = new_capacity
        self.resize_events.append((old_capacity, new_capacity))

    def _check_invariant(self) -> None:
        assert self._capacity >= 1
        assert 0 <= self._size <= self._capacity
        assert len(self._items) == self._capacity
        assert all(item is not None for item in self._items[: self._size])
        assert all(item is None for item in self._items[self._size :])


def append_trace(values: list[int]) -> tuple[list[int], list[tuple[int, int]]]:
    """返回逻辑内容与扩容轨迹，供课堂观察复制成本。"""
    array = DynamicIntArray()
    for value in values:
        array.append(value)
    return array.values(), array.resize_events
