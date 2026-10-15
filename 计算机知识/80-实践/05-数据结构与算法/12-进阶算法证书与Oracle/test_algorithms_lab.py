import random
import unittest

from algorithms_lab import (
    bridges_and_articulations,
    brute_bridges_and_articulations,
    brute_matching_size,
    brute_max_weight_independent_set,
    brute_vertex_cover_exists,
    fpt_vertex_cover,
    hopcroft_karp,
    lru_faults,
    min_vertex_cover_from_matching,
    offline_optimal_faults,
    tree_max_weight_independent_set,
)


class GraphCertificatesTest(unittest.TestCase):
    def test_parallel_edge_is_not_a_bridge(self):
        edges = [(0, 1), (0, 1)]
        self.assertEqual(bridges_and_articulations(2, edges), (set(), set()))

    def test_low_link_matches_deletion_oracle(self):
        rng = random.Random(20260916)
        for n in range(1, 8):
            possible = [(u, v) for u in range(n) for v in range(u + 1, n)]
            for _ in range(80):
                edges = [edge for edge in possible if rng.random() < 0.3]
                if edges and rng.random() < 0.2:
                    edges.append(rng.choice(edges))
                self.assertEqual(
                    bridges_and_articulations(n, edges),
                    brute_bridges_and_articulations(n, edges),
                    (n, edges),
                )

    def test_matching_and_konig_certificate(self):
        rng = random.Random(14022015)
        for left_size in range(5):
            for right_size in range(5):
                possible = [(u, v) for u in range(left_size) for v in range(right_size)]
                for _ in range(35):
                    edges = [edge for edge in possible if rng.random() < 0.35]
                    matching = hopcroft_karp(left_size, right_size, edges)
                    self.assertEqual(len(matching), brute_matching_size(left_size, right_size, edges))
                    left_cover, right_cover = min_vertex_cover_from_matching(
                        left_size, right_size, edges, matching
                    )
                    self.assertEqual(len(left_cover) + len(right_cover), len(matching))
                    self.assertTrue(
                        all(u in left_cover or v in right_cover for u, v in edges),
                        (left_size, right_size, edges, matching, left_cover, right_cover),
                    )

    def test_hopcroft_karp_uses_only_shortest_paths_in_each_phase(self):
        edges = [(0, 0), (0, 1), (0, 2), (1, 0), (2, 1), (2, 2)]
        phase_distances = []
        matching = hopcroft_karp(4, 4, edges, phase_distances=phase_distances)
        self.assertEqual(len(matching), 3)
        self.assertEqual(phase_distances, [1, 2])


class StateAndParameterTest(unittest.TestCase):
    def test_tree_dp_matches_subset_oracle(self):
        rng = random.Random(15152015)
        for n in range(1, 11):
            for _ in range(50):
                edges = [(v, rng.randrange(v)) for v in range(1, n)]
                weights = [rng.randrange(10) for _ in range(n)]
                self.assertEqual(
                    tree_max_weight_independent_set(weights, edges),
                    brute_max_weight_independent_set(weights, edges),
                    (weights, edges),
                )

    def test_tree_contract_rejects_cycle(self):
        with self.assertRaises(ValueError):
            tree_max_weight_independent_set([1, 2, 3], [(0, 1), (1, 2), (2, 0)])

    def test_fpt_vertex_cover_matches_subset_oracle(self):
        rng = random.Random(18182015)
        for n in range(1, 9):
            possible = [(u, v) for u in range(n) for v in range(u + 1, n)]
            for _ in range(50):
                edges = [edge for edge in possible if rng.random() < 0.28]
                for k in range(4):
                    answer = fpt_vertex_cover(n, edges, k)
                    self.assertEqual(answer is not None, brute_vertex_cover_exists(n, edges, k))
                    if answer is not None:
                        self.assertLessEqual(len(answer), k)
                        self.assertTrue(all(u in answer or v in answer for u, v in edges))


class PagingTest(unittest.TestCase):
    def test_hand_trace(self):
        requests = "ABCABC"
        self.assertEqual(offline_optimal_faults(requests, 2), 4)
        self.assertEqual(lru_faults(requests, 2), 6)

    def test_online_cannot_beat_offline_oracle(self):
        rng = random.Random(20202015)
        alphabet = "ABCD"
        for length in range(9):
            for _ in range(80):
                requests = tuple(rng.choice(alphabet) for _ in range(length))
                for capacity in range(4):
                    self.assertGreaterEqual(
                        lru_faults(requests, capacity),
                        offline_optimal_faults(requests, capacity),
                        (requests, capacity),
                    )


if __name__ == "__main__":
    unittest.main()
