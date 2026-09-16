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
