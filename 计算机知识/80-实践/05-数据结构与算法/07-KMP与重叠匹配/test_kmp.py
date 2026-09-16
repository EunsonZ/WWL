"""kmp 的前缀不变量、重叠命中和边界测试。"""

from __future__ import annotations

import unittest

from kmp import find_all_overlapping, prefix_lengths


class KmpTests(unittest.TestCase):
    def test_prefix_table_invariant_on_repeated_prefixes(self) -> None:
        self.assertEqual(prefix_lengths("ababaca"), [0, 0, 1, 2, 3, 0, 1])

    def test_full_match_fallback_preserves_overlapping_matches(self) -> None:
        self.assertEqual(find_all_overlapping("aaaaa", "aa"), [0, 1, 2, 3])
        self.assertEqual(find_all_overlapping("abababa", "aba"), [0, 2, 4])

    def test_empty_text_and_pattern_longer_than_text(self) -> None:
        self.assertEqual(find_all_overlapping("", "a"), [])
        self.assertEqual(find_all_overlapping("ab", "aba"), [])

    def test_empty_pattern_matches_every_text_boundary(self) -> None:
        self.assertEqual(find_all_overlapping("abc", ""), [0, 1, 2, 3])
        self.assertEqual(find_all_overlapping("", ""), [0])
        with self.assertRaises(TypeError):
            prefix_lengths(123)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
