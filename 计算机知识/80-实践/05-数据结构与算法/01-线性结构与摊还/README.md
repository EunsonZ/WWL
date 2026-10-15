---
type: practice
stage: 1
status: ready
difficulty: 入门
estimated_minutes: 35
domain: computer-science
tags:
  - computer-science/data-structures
  - computer-science/amortized-analysis
---

# 线性结构与摊还

目标：用一个刻意简化的 DynamicIntArray 看见容量翻倍、复制和逻辑长度的关系；它不是 Python list 的替代品。

## 运行、观察与成功标准

在本目录运行：

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/01-线性结构与摊还"
python3 -m unittest -v
~~~

观察 append_trace 的扩容轨迹：(1, 2) 到 (2, 4) 再到 (4, 8)。扩容那一次复制已有元素，但多数追加不复制。成功标准是测试通过，并能说出不变量：0 <= size <= capacity、有效槽非空、其余槽为 None。`validate()` 会显式扫描整个底层容器，成本为 `O(capacity)`；测试可在小输入每步调用它，但不应把它塞进默认 `append/pop` 热路径，否则会污染待观察的摊还复杂度。练习：新增 append 次数统计，说明它不能单独证明真实运行时间。

恢复/清理：本实验只可能产生同目录 __pycache__/；确认路径后可以删除该缓存，源码修改用编辑器撤销或 Git diff 恢复。不要把清理目标扩大到实践根目录。

相关稳定课：[[计算机知识/50-数据结构与算法/01-复杂度模型渐近分析与摊还分析|复杂度模型、渐近分析与摊还分析]]、[[计算机知识/50-数据结构与算法/02-数组动态数组链表与内存布局|数组、动态数组、链表与内存布局]]、[[计算机知识/50-数据结构与算法/03-栈队列双端队列与单调结构|栈、队列、双端队列与单调结构]]。

<!-- code-sync: ./dynamic_array.py -->
~~~python
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
~~~

<!-- code-sync: ./test_dynamic_array.py -->
~~~python
"""dynamic_array 的正例、边界和错误输入。"""

from __future__ import annotations

import unittest

from dynamic_array import DynamicIntArray, append_trace


class DynamicIntArrayTests(unittest.TestCase):
    def test_append_preserves_order_and_records_doubling(self) -> None:
        values, events = append_trace([3, 1, 4, 1, 5])
        self.assertEqual(values, [3, 1, 4, 1, 5])
        self.assertEqual(events, [(1, 2), (2, 4), (4, 8)])
        array = DynamicIntArray()
        for value in [3, 1, 4, 1, 5]:
            array.append(value)
            array.validate()

    def test_pop_and_empty_boundary(self) -> None:
        array = DynamicIntArray()
        array.append(9)
        self.assertEqual(array.pop(), 9)
        self.assertEqual(len(array), 0)
        array.validate()
        with self.assertRaises(IndexError):
            array.pop()
        with self.assertRaises(IndexError):
            array.get(0)

    def test_rejects_invalid_constructor_value_and_index(self) -> None:
        with self.assertRaises(ValueError):
            DynamicIntArray(0)
        array = DynamicIntArray()
        with self.assertRaises(TypeError):
            array.append(True)
        with self.assertRaises(TypeError):
            array.get("0")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]] 与 [[计算机知识/50-数据结构与算法/00-数据结构与算法-MOC|数据结构与算法 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/21-动态结构不变量与摊还分析推演|数据结构深化：从不变量推到摊还代价]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
