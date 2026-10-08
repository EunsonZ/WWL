"""algorithms 的正例、边界和错误输入。"""

from __future__ import annotations

import unittest

from algorithms import first_index, first_index_checked, lis_length, merge_sort, min_coin_count


class AlgorithmsTests(unittest.TestCase):
    def test_sort_binary_search_and_dp_examples(self) -> None:
        self.assertEqual(merge_sort([5, 1, 4, 1]), [1, 1, 4, 5])
        self.assertEqual(first_index([1, 1, 4, 5], 1), 0)
        self.assertEqual(min_coin_count(11, [1, 5, 6]), 2)
        self.assertEqual(lis_length([10, 9, 2, 5, 3, 7, 101, 18]), 4)

    def test_empty_and_unreachable_boundaries(self) -> None:
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(first_index([], 2), -1)
        self.assertIsNone(min_coin_count(3, [2, 4]))
        self.assertEqual(lis_length([]), 0)

    def test_rejects_broken_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            first_index_checked([2, 1], 1)
        with self.assertRaises(ValueError):
            min_coin_count(-1, [1])
        with self.assertRaises(ValueError):
            min_coin_count(3, [0, 1])
        with self.assertRaises(TypeError):
            merge_sort([1, "2"])  # type: ignore[list-item]

    def test_coin_denominations_are_validated_before_deduplication(self) -> None:
        for coins in ([1, True], [True, 1], [1, 1.0], [1.0, 1]):
            with self.assertRaises(ValueError):
                min_coin_count(2, coins)
        self.assertEqual(min_coin_count(3, (coin for coin in [1, 1, 2])), 2)

    def test_checked_binary_search_separates_validation_from_logarithmic_core(self) -> None:
        self.assertEqual(first_index_checked([1, 1, 4, 5], 1), 0)
        self.assertEqual(first_index([1, 1, 4, 5], 5), 3)
        with self.assertRaises(TypeError):
            first_index_checked([1, "2"], 1)  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
