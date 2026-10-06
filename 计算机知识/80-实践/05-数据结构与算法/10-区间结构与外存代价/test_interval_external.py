"""interval_external 的边界语义、操作计数和固定种子测试。"""

from __future__ import annotations

import random
import unittest

from interval_external import FenwickTree, PagedSortedIndex, offline_range_add


class IntervalExternalTests(unittest.TestCase):
    def test_difference_array_uses_two_writes_per_update_and_one_scan(self) -> None:
        values, stats = offline_range_add(
            6,
            [(1, 5, 3), (2, 4, -1), (0, 0, 99)],
        )
        self.assertEqual(values, [0, 3, 2, 2, 3, 0])
        self.assertEqual(stats.boundary_writes, 6)
        self.assertEqual(stats.scan_steps, 6)

    def test_fenwick_queries_and_updates_have_logarithmic_touch_counts(self) -> None:
        size = 64
        tree = FenwickTree(range(size))
        tree.add(0, 7)
        update_writes = tree.stats.tree_writes
        self.assertEqual(tree.range_sum(0, size), sum(range(size)) + 7)
        self.assertLessEqual(update_writes, size.bit_length())
        self.assertLessEqual(tree.stats.tree_reads, 2 * size.bit_length())
        self.assertEqual(tree.range_sum(13, 13), 0)

    def test_fixed_seed_paged_index_matches_sorted_reference(self) -> None:
        rng = random.Random(20260904)
        keys = rng.sample(range(10_000), 256)
        ordered = sorted(keys)
        index = PagedSortedIndex(keys, page_size=16)

        target = ordered[123]
        found, point_stats = index.contains(target)
        self.assertTrue(found)
        self.assertEqual(point_stats.page_reads, 1)

        left, right = ordered[50], ordered[75]
        result, range_stats = index.range_query(left, right)
        self.assertEqual(result, ordered[50:75])
        self.assertEqual(range_stats.page_reads, 2)
        self.assertGreater(range_stats.key_comparisons, 0)

    def test_page_size_changes_transfers_not_query_result(self) -> None:
        keys = list(range(128))
        compact = PagedSortedIndex(keys, page_size=16)
        one_key_pages = PagedSortedIndex(keys, page_size=1)

        compact_result, compact_stats = compact.range_query(32, 96)
        sparse_result, sparse_stats = one_key_pages.range_query(32, 96)
        self.assertEqual(compact_result, sparse_result)
        self.assertEqual(compact_stats.page_reads, 4)
        self.assertEqual(sparse_stats.page_reads, 64)
        self.assertLess(compact_stats.page_reads, sparse_stats.page_reads)

    def test_invalid_ranges_are_rejected(self) -> None:
        with self.assertRaises(IndexError):
            offline_range_add(3, [(2, 4, 1)])
        with self.assertRaises(ValueError):
            PagedSortedIndex([1, 2], 0)
        with self.assertRaises(ValueError):
            PagedSortedIndex([1, 2], 1).range_query(2, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
