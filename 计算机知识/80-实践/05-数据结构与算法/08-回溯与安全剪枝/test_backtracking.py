"""backtracking 的非负不变量、边界、拒绝和负数反例。"""

from __future__ import annotations

import unittest

from backtracking import subset_sum_nonnegative, unsafe_prune_without_nonnegative_validation


class BacktrackingTests(unittest.TestCase):
    def test_nonnegative_pruning_invariant_with_repeated_values(self) -> None:
        self.assertEqual(subset_sum_nonnegative([2, 2, 3], 4), [0, 1])

    def test_zero_target_and_unreachable_boundaries(self) -> None:
        self.assertEqual(subset_sum_nonnegative([], 0), [])
        self.assertIsNone(subset_sum_nonnegative([4, 6], 5))

    def test_rejects_negative_values_before_using_pruning(self) -> None:
        with self.assertRaises(ValueError):
            subset_sum_nonnegative([8, -3], 5)
        with self.assertRaises(ValueError):
            subset_sum_nonnegative([1], -1)

    def test_unchecked_pruning_negative_counterexample_loses_solution(self) -> None:
        self.assertIsNone(unsafe_prune_without_nonnegative_validation([8, -3], 5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
