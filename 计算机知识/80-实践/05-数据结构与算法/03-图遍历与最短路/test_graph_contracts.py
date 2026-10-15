"""Regression contract for overflow, reachability, and direct graph inputs."""

from __future__ import annotations

import math
import unittest

import graph_algorithms as graph


class GraphContracts(unittest.TestCase):
    def test_overflow_unreachable_and_direct_input_validation(self) -> None:
        large_graph = graph.make_directed_graph(
            [("a", "b", 1e308), ("b", "c", 1e308)]
        )
        self.assertIn("c", graph.breadth_first_order(large_graph, "a"))
        with self.assertRaises(OverflowError):
            graph.dijkstra_distances(large_graph, "a")

        disconnected = {"a": [], "b": []}
        self.assertEqual(graph.dijkstra_distances(disconnected, "a")["b"], math.inf)
        for weight in (-1.0, math.nan, math.inf):
            with self.assertRaises(ValueError):
                graph.dijkstra_distances(
                    {"a": [("b", weight)], "b": []}, "a"
                )


if __name__ == "__main__":
    unittest.main()
