"""graph_dataflow 的分区、DAG、固定种子和不动点测试。"""

from __future__ import annotations

import random
import unittest

from graph_dataflow import (
    condensation_graph,
    reaching_definitions,
    strongly_connected_components,
)


def _reachable(graph: dict[str, list[str]], source: str, target: str) -> bool:
    pending = [source]
    visited = {source}
    while pending:
        vertex = pending.pop()
        if vertex == target:
            return True
        for neighbor in graph.get(vertex, []):
            if neighbor not in visited:
                visited.add(neighbor)
                pending.append(neighbor)
    return False


def _is_acyclic(graph: dict[int, tuple[int, ...]]) -> bool:
    indegree = {vertex: 0 for vertex in graph}
    for targets in graph.values():
        for target in targets:
            indegree[target] += 1
    ready = [vertex for vertex, degree in indegree.items() if degree == 0]
    removed = 0
    while ready:
        vertex = ready.pop()
        removed += 1
        for target in graph[vertex]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return removed == len(graph)


class GraphDataflowTests(unittest.TestCase):
    def test_known_scc_partition_and_condensation_dag(self) -> None:
        graph = {
            "entry": ["a"],
            "a": ["b"],
            "b": ["a", "c"],
            "c": ["d"],
            "d": ["c", "exit"],
            "exit": [],
        }
        components, stats = strongly_connected_components(graph)
        self.assertEqual(
            components,
            [("a", "b"), ("c", "d"), ("entry",), ("exit",)],
        )
        self.assertEqual(stats.vertex_entries, 2 * len(graph))
        self.assertEqual(stats.edge_scans, 2 * sum(map(len, graph.values())))
        self.assertTrue(_is_acyclic(condensation_graph(graph, components)))

    def test_fixed_seed_scc_matches_mutual_reachability(self) -> None:
        rng = random.Random(20260904)
        vertices = [f"v{index}" for index in range(12)]
        graph = {
            source: [target for target in vertices if rng.random() < 0.18]
            for source in vertices
        }
        components, stats = strongly_connected_components(graph)
        actual = {frozenset(component) for component in components}

        remaining = set(vertices)
        expected: set[frozenset[str]] = set()
        while remaining:
            source = min(remaining)
            component = frozenset(
                target
                for target in remaining
                if _reachable(graph, source, target)
                and _reachable(graph, target, source)
            )
            expected.add(component)
            remaining.difference_update(component)

        unique_edges = sum(len(set(targets)) for targets in graph.values())
        self.assertEqual(actual, expected)
        self.assertEqual(stats.vertex_entries, 2 * len(vertices))
        self.assertEqual(stats.edge_scans, 2 * unique_edges)

    def test_worklist_reaches_loop_fixed_point(self) -> None:
        cfg = {
            "entry": ["loop"],
            "loop": ["body", "exit"],
            "body": ["loop"],
            "exit": [],
        }
        gen = {
            "entry": frozenset({"x@entry"}),
            "loop": frozenset(),
            "body": frozenset({"x@body"}),
            "exit": frozenset(),
        }
        kill = {
            "entry": frozenset({"x@body"}),
            "loop": frozenset(),
            "body": frozenset({"x@entry"}),
            "exit": frozenset(),
        }
        in_state, out_state, stats = reaching_definitions(cfg, gen, kill)

        self.assertEqual(in_state["loop"], frozenset({"x@entry", "x@body"}))
        self.assertEqual(out_state["body"], frozenset({"x@body"}))
        self.assertEqual(in_state["exit"], frozenset({"x@entry", "x@body"}))
        self.assertGreater(stats.state_changes, 0)
        self.assertLessEqual(stats.evaluations, 4 * len(cfg))
        self.assertGreater(stats.successor_enqueues, 0)

    def test_dataflow_contract_rejects_missing_block_facts(self) -> None:
        with self.assertRaises(ValueError):
            reaching_definitions(
                {"entry": ["exit"], "exit": []},
                {"entry": frozenset()},
                {"entry": frozenset()},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
