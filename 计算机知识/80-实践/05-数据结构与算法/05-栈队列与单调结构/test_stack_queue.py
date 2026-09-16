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
