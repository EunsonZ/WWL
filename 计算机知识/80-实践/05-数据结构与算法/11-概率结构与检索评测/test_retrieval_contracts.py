"""Regression contracts for retrieval numerics and key encoding."""

from __future__ import annotations

import math
from pathlib import Path
import subprocess
import sys
import unittest

import retrieval_lab as retrieval


class RetrievalContracts(unittest.TestCase):
    def test_cosine_scale_and_domain(self) -> None:
        for vector in ([1e200, 1e200], [1e-200, 0.0]):
            self.assertAlmostEqual(retrieval.cosine_similarity(vector, vector), 1.0)
        self.assertAlmostEqual(
            retrieval.cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0
        )
        self.assertAlmostEqual(
            retrieval.cosine_similarity([1.0, 2.0], [-2.0, -4.0]), -1.0
        )
        for vector in ([0.0, 0.0], [math.nan, 1.0], [math.inf, 1.0]):
            with self.assertRaises(ValueError):
                retrieval.cosine_similarity(vector, [1.0, 0.0])

    def test_key_v1_semantics_and_cross_process_stability(self) -> None:
        bloom = retrieval.BloomFilter(1024, 3)
        for key in ("中文", b"abc", "abc"):
            bloom.add(key)
            self.assertIn(key, bloom)
        self.assertEqual(bloom.distinct_items, 3)

        for key in ({"a": 1}, ["x"], 1):
            with self.assertRaises(TypeError):
                bloom.add(key)
            with self.assertRaises(TypeError):
                retrieval.CountMinSketch(10, 3).add(key)

        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from retrieval_lab import _stable_hash; "
            "print(_stable_hash('中文', 3))"
        )
        module_directory = str(Path(__file__).resolve().parent)
        observed = int(
            subprocess.check_output(
                [sys.executable, "-B", "-c", code, module_directory], text=True
            )
        )
        self.assertEqual(observed, retrieval._stable_hash("中文", 3))


if __name__ == "__main__":
    unittest.main()
