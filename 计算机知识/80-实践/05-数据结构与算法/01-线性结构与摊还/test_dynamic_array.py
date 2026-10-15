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
