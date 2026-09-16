---
type: practice
stage: 1
status: ready
difficulty: 入门到中级
estimated_minutes: 35
domain: computer-science
tags:
  - computer-science/stack
  - computer-science/queue
  - computer-science/monotonic-queue
---

# 栈、队列与单调结构

目标：用括号匹配观察后进先出的未匹配状态；用滑窗最大值观察只保留有竞争力候选的单调队列。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/05-栈队列与单调结构"
python3 --version
python3 -m unittest -v
~~~

预期为 `Ran 4 tests ... OK`。重复最大值会保留较新的下标，因而候选值严格递减。默认 `validate=False` 时只执行算法本身；测试在小输入上用 `validate=True` 全量扫描栈/队列不变量。全量验证可使滑窗路径达到 `O(nw)`，故它是调试证据，不属于默认 `O(n)` 算法的复杂度。恢复/清理：本实验不访问网络、不写用户文件，只可能生成同目录 `__pycache__/`；确认路径后才可删除它，源码恢复使用编辑器撤销或 Git diff。

## 不变量到可执行证据

- 括号栈只含尚未匹配的左括号 → `brackets_are_balanced(..., validate=True)` 的显式扫描 → `test_bracket_stack_invariant_on_nested_and_empty`。
- 队列下标都在当前窗口内，且对应值严格递减 → `sliding_window_maximum(..., validate=True)` 的显式扫描 → `test_window_deque_invariant_with_repeated_values`。
- 宽度必须对应至少一个完整窗口 → 参数拒绝 → `test_window_rejects_invalid_boundaries`。

相关稳定课：[[计算机知识/50-数据结构与算法/03-栈队列双端队列与单调结构|栈、队列与双端队列]]。

<!-- code-sync: ./stack_queue.py -->
~~~python
"""括号栈与滑动窗口最大值：只用 Python 标准库。"""

from __future__ import annotations

from collections import deque
from typing import Iterable


def brackets_are_balanced(text: str, *, validate: bool = False) -> bool:
    """忽略非括号字符；栈始终保存尚未匹配的左括号。"""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    partner = {")": "(", "]": "[", "}": "{"}
    opens = set(partner.values())
    pending: list[str] = []
    for character in text:
        if character in opens:
            pending.append(character)
        elif character in partner:
            if not pending or pending.pop() != partner[character]:
                return False
        if validate and not all(item in opens for item in pending):
            raise AssertionError("bracket stack contains a non-opening character")
    return not pending


def sliding_window_maximum(values: Iterable[int], width: int, *, validate: bool = False) -> list[int]:
    """返回每个窗口的最大值；队列保存当前窗口内、值严格递减的下标。"""
    items = list(values)
    if any(type(value) is not int for value in items):
        raise TypeError("values must contain int values only")
    if type(width) is not int or width <= 0 or width > len(items):
        raise ValueError("width must be between 1 and len(values)")

    candidates: deque[int] = deque()
    maxima: list[int] = []
    for index, value in enumerate(items):
        while candidates and candidates[0] <= index - width:
            candidates.popleft()
        while candidates and items[candidates[-1]] <= value:
            candidates.pop()
        candidates.append(index)
        if validate:
            snapshot = list(candidates)
            if not all(index - width < candidate <= index for candidate in snapshot):
                raise AssertionError("candidate index is outside the current window")
            if not all(items[left] > items[right] for left, right in zip(snapshot, snapshot[1:])):
                raise AssertionError("candidate values are not strictly decreasing")
        if index >= width - 1:
            maxima.append(items[candidates[0]])
    return maxima
~~~

<!-- code-sync: ./test_stack_queue.py -->
~~~python
"""stack_queue 的不变量、边界和失败输入测试。"""

from __future__ import annotations

import unittest

from stack_queue import brackets_are_balanced, sliding_window_maximum


class StackQueueTests(unittest.TestCase):
    def test_bracket_stack_invariant_on_nested_and_empty(self) -> None:
        self.assertTrue(brackets_are_balanced("function(a, [b, {c: 1}])", validate=True))
        self.assertTrue(brackets_are_balanced(""))

    def test_bracket_failure_examples(self) -> None:
        self.assertFalse(brackets_are_balanced("([)]"))
        self.assertFalse(brackets_are_balanced("(()"))

    def test_window_deque_invariant_with_repeated_values(self) -> None:
        self.assertEqual(
            sliding_window_maximum([1, 3, 3, 2, 5, 5, 1], 3, validate=True),
            [3, 3, 5, 5, 5],
        )

    def test_window_rejects_invalid_boundaries(self) -> None:
        with self.assertRaises(ValueError):
            sliding_window_maximum([], 1)
        with self.assertRaises(ValueError):
            sliding_window_maximum([1, 2], 3)
        with self.assertRaises(TypeError):
            sliding_window_maximum([1, "2"], 1)  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/21-动态结构不变量与摊还分析推演|数据结构深化：从不变量推到摊还代价]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
