"""greedy_activity 的正确性边界和错误规则反例。"""

from __future__ import annotations

import unittest

from greedy_activity import select_by_earliest_finish, select_by_earliest_start_wrong


class GreedyActivityTests(unittest.TestCase):
    def test_earliest_finish_keeps_selected_schedule_compatible(self) -> None:
        activities = [(1, 4, "a"), (3, 5, "b"), (0, 6, "c"), (5, 7, "d"), (8, 9, "e")]
        self.assertEqual(
            select_by_earliest_finish(activities, validate=True),
            [(1, 4, "a"), (5, 7, "d"), (8, 9, "e")],
        )

    def test_empty_and_touching_boundaries(self) -> None:
        self.assertEqual(select_by_earliest_finish([]), [])
        self.assertEqual(select_by_earliest_finish([(0, 2, "a"), (2, 4, "b")]), [(0, 2, "a"), (2, 4, "b")])

    def test_earliest_start_counterexample_is_not_optimal(self) -> None:
        counterexample = [(0, 3, "long"), (1, 2, "short-a"), (2, 3, "short-b")]
        self.assertEqual(select_by_earliest_start_wrong(counterexample), [(0, 3, "long")])
        self.assertEqual(select_by_earliest_finish(counterexample), [(1, 2, "short-a"), (2, 3, "short-b")])

    def test_rejects_invalid_activity_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            select_by_earliest_finish([(3, 3, "instant")])
        with self.assertRaises(TypeError):
            select_by_earliest_finish([(1, 2, 3)])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
