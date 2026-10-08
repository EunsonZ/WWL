"""retrieval_lab 的合同、边界与固定种子回归测试。"""

from __future__ import annotations

import unittest

from retrieval_lab import (
    BloomFilter,
    CountMinSketch,
    InvertedIndex,
    ReservoirSampler,
    ToyRandomHyperplaneLSH,
    approximate_deep_size_bytes,
    cosine_similarity,
    evaluate_toy_lsh,
    exact_cosine_search,
    recall_at_k,
)


class ProbabilisticStructureTests(unittest.TestCase):
    def test_bloom_has_no_false_negative_for_inserted_items(self) -> None:
        bloom = BloomFilter(size_bits=128, hash_count=3, seed=7)
        inserted = ["alpha", "beta", "gamma"]
        for item in inserted:
            bloom.add(item)
        self.assertTrue(all(item in bloom for item in inserted))
        self.assertEqual(bloom.storage_bytes, 16)
        self.assertGreaterEqual(bloom.estimated_false_positive_rate(), 0.0)
        self.assertLessEqual(bloom.estimated_false_positive_rate(), 1.0)

    def test_bloom_duplicate_insertions_do_not_raise_theoretical_fpr(self) -> None:
        bloom = BloomFilter(size_bits=4096, hash_count=4, seed=7)
        bloom.add("alpha")
        before_duplicate = bloom.estimated_false_positive_rate()
        bloom.add("alpha")
        self.assertEqual(bloom.insertion_calls, 2)
        self.assertEqual(bloom.distinct_items, 1)
        self.assertEqual(bloom.estimated_false_positive_rate(), before_duplicate)
        bloom.add("beta")
        self.assertEqual(bloom.distinct_items, 2)
        self.assertGreater(bloom.estimated_false_positive_rate(), before_duplicate)

    def test_count_min_never_underestimates_non_negative_stream(self) -> None:
        sketch = CountMinSketch.from_error_budget(0.1, 0.1, seed=11)
        truth = CounterLike()
        for item in ["red", "blue", "red", "green", "red", "blue"]:
            sketch.add(item)
            truth.add(item)
        for item in ["red", "blue", "green", "absent"]:
            self.assertGreaterEqual(sketch.estimate(item), truth[item])
        self.assertEqual(sketch.total_count, 6)
        self.assertEqual(sketch.counter_count, sketch.width * sketch.depth)

    def test_reservoir_is_bounded_and_reproducible(self) -> None:
        first = ReservoirSampler(capacity=4, seed=19)
        second = ReservoirSampler(capacity=4, seed=19)
        first.extend(range(100))
        second.extend(range(100))
        self.assertEqual(first.sample, second.sample)
        self.assertEqual(len(first.sample), 4)
        self.assertEqual(first.seen, 100)
        self.assertAlmostEqual(first.inclusion_probability, 0.04)

    def test_probability_structures_reject_broken_budgets(self) -> None:
        with self.assertRaises(ValueError):
            BloomFilter(0, 1)
        with self.assertRaises(ValueError):
            CountMinSketch.from_error_budget(0.0, 0.1)
        with self.assertRaises(ValueError):
            CountMinSketch(4, 2).add("x", -1)
        with self.assertRaises(ValueError):
            ReservoirSampler(-1)

    def test_count_min_accepts_subnormal_delta_without_reciprocal_overflow(self) -> None:
        sketch = CountMinSketch.from_error_budget(0.1, 1e-320)
        self.assertEqual((sketch.width, sketch.depth), (28, 737))
        sketch.add("red")
        self.assertEqual(sketch.estimate("red"), 1)


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vectors = {
            "public-a": (1.0, 0.0),
            "public-b": (0.8, 0.2),
            "private": (0.99, 0.01),
            "other": (-1.0, 0.0),
        }

    def test_inverted_postings_and_filter_before_top_k(self) -> None:
        index = InvertedIndex(
            {
                "public-a": "cache cache index",
                "public-b": "cache graph",
                "private": "cache cache cache secret",
            }
        )
        unfiltered = index.search("cache", k=1)
        filtered = index.search("cache", k=1, allowed_ids={"public-a", "public-b"})
        self.assertEqual(unfiltered[0][0], "private")
        self.assertEqual(filtered, [("public-a", 2)])

    def test_exact_cosine_is_oracle_and_honors_visibility(self) -> None:
        query = (1.0, 0.0)
        unfiltered = exact_cosine_search(self.vectors, query, k=2)
        filtered = exact_cosine_search(
            self.vectors, query, k=2, allowed_ids={"public-a", "public-b"}
        )
        self.assertEqual([item[0] for item in unfiltered], ["public-a", "private"])
        self.assertEqual([item[0] for item in filtered], ["public-a", "public-b"])
        self.assertAlmostEqual(cosine_similarity((1.0, 0.0), (2.0, 0.0)), 1.0)

    def test_toy_lsh_is_reproducible_but_evaluated_by_recall(self) -> None:
        query = (1.0, 0.0)
        first = ToyRandomHyperplaneLSH(self.vectors, num_planes=3, seed=7)
        second = ToyRandomHyperplaneLSH(self.vectors, num_planes=3, seed=7)
        found_first = first.search(query, k=3, allowed_ids={"public-a", "public-b"})
        found_second = second.search(query, k=3, allowed_ids={"public-a", "public-b"})
        truth = exact_cosine_search(
            self.vectors, query, k=3, allowed_ids={"public-a", "public-b"}
        )
        self.assertEqual(found_first, found_second)
        self.assertTrue(all(item[0] != "private" for item in found_first))
        self.assertGreaterEqual(recall_at_k(truth, found_first), 0.0)
        self.assertLessEqual(recall_at_k(truth, found_first), 1.0)

    def test_toy_lsh_uses_scale_invariant_finite_projection(self) -> None:
        vectors = {"same": (1.7e308, 1.7e308)}
        index = ToyRandomHyperplaneLSH(vectors, num_planes=1, seed=23)
        self.assertEqual(index._signature(vectors["same"]), index._signature((1.0, 1.0)))
        found = index.search((1.0, 1.0), k=1)
        self.assertEqual([document_id for document_id, _ in found], ["same"])
        self.assertAlmostEqual(found[0][1], 1.0)

    def test_report_labels_latency_and_memory_as_measurements(self) -> None:
        report = evaluate_toy_lsh(
            self.vectors,
            [(1.0, 0.0), (0.7, 0.3)],
            k=2,
            num_planes=3,
            seed=7,
            repeats=3,
        )
        self.assertGreaterEqual(report.recall_at_k, 0.0)
        self.assertLessEqual(report.recall_at_k, 1.0)
        self.assertGreaterEqual(report.exact_latency_ms, 0.0)
        self.assertGreaterEqual(report.approximate_latency_ms, 0.0)
        self.assertGreater(report.exact_storage_proxy_bytes, 0)
        self.assertGreater(report.approximate_storage_proxy_bytes, 0)
        self.assertGreater(approximate_deep_size_bytes(first := {"x": [1, 2]}), 0)
        self.assertEqual(first, {"x": [1, 2]})

    def test_vector_and_k_preconditions(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity((0.0, 0.0), (1.0, 0.0))
        with self.assertRaises(ValueError):
            exact_cosine_search(self.vectors, (1.0,), k=1)
        with self.assertRaises(ValueError):
            exact_cosine_search(self.vectors, (1.0, 0.0), k=0)


class CounterLike:
    """测试用精确计数器，避免把实现自身当 oracle。"""

    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def add(self, item: str) -> None:
        self.values[item] = self.values.get(item, 0) + 1

    def __getitem__(self, item: str) -> int:
        return self.values.get(item, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
