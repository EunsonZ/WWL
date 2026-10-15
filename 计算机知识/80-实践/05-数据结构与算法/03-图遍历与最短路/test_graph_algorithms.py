"""graph_algorithms 的正例、边界和错误输入。"""

from __future__ import annotations

import math
import unittest

from graph_algorithms import breadth_first_order, dijkstra_distances, make_directed_graph


class GraphAlgorithmsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = make_directed_graph(
            [("A", "B", 4), ("A", "C", 1), ("C", "B", 2), ("B", "D", 1), ("C", "D", 5)]
        )
        self.graph["E"] = []

    def test_bfs_and_dijkstra_choose_different_questions(self) -> None:
        self.assertEqual(breadth_first_order(self.graph, "A"), ["A", "B", "C", "D"])
        distances = dijkstra_distances(self.graph, "A")
        self.assertEqual(distances["D"], 4.0)
        self.assertTrue(math.isinf(distances["E"]))

    def test_single_vertex_boundary(self) -> None:
        graph = make_directed_graph([])
        graph["solo"] = []
        self.assertEqual(breadth_first_order(graph, "solo"), ["solo"])
        self.assertEqual(dijkstra_distances(graph, "solo"), {"solo": 0.0})

    def test_rejects_missing_start_and_negative_weight(self) -> None:
        with self.assertRaises(KeyError):
            breadth_first_order(self.graph, "missing")
        with self.assertRaises(ValueError):
            make_directed_graph([("A", "B", -1)])
        with self.assertRaises(TypeError):
            make_directed_graph([(3, "B", 1)])  # type: ignore[list-item]


if __name__ == "__main__":
    unittest.main(verbosity=2)
