---
type: practice
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 50
domain: computer-science
tags:
  - computer-science/graphs
  - computer-science/compiler
  - computer-science/fixed-point
  - computer-science/testing
---

# 图分解与数据流不动点

目标：用 Kosaraju 算法将有向图分成 SCC，验证缩点后必为 DAG；再用去重工作列表求 CFG reaching-definitions 的最小不动点。实验保存边扫描、顶点进入、块求值、状态改变和重新入队计数，不用单次毫秒数代替复杂度证据。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/09-图分解与数据流不动点"
python3 --version
python3 -m unittest -v
~~~

预期 `Ran 4 tests ... OK`。成功证据包含：

- 手写环图得到预期 SCC 分区，凝聚图通过 Kahn 检查；
- 固定种子 `20260904` 生成的图与小型互相可达参考实现交叉验证；
- Kosaraju 的两遍 DFS 在去重邻接表上恰扫描 `2|E|` 条邻接记录、进入 `2|V|` 次顶点；
- 有回边的 CFG 收敛到 reaching-definitions 不动点，且确实观察到状态改变与后继重新入队。

本实验的图为内存中小图，递归 DFS 不代表已处理生产级深图的调用栈上限；数据流模型是有限定义集上的前向 may 分析，不是完整编译器。恢复/清理：实验不访问网络、不写用户数据，只可能生成同目录 `__pycache__/`；确认精确路径后才可删除，源码恢复使用编辑器撤销或 Git diff。

相关稳定课：[[计算机知识/50-数据结构与算法/17-强连通分量凝聚DAG与工作列表不动点|强连通分量、凝聚 DAG 与工作列表不动点]]。

<!-- code-sync: ./graph_dataflow.py -->
~~~python
"""SCC 分解与 CFG 前向 may 数据流的可重现操作计数实验。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import AbstractSet, Iterable, Mapping


Graph = Mapping[str, Iterable[str]]


@dataclass
class SCCStats:
    edge_scans: int = 0
    vertex_entries: int = 0


@dataclass
class WorklistStats:
    evaluations: int = 0
    state_changes: int = 0
    successor_enqueues: int = 0
    predecessor_unions: int = 0


def _normalize_graph(graph: Graph) -> dict[str, tuple[str, ...]]:
    vertices = set(graph)
    for neighbors in graph.values():
        vertices.update(neighbors)
    return {
        vertex: tuple(sorted(set(graph.get(vertex, ()))))
        for vertex in sorted(vertices)
    }


def strongly_connected_components(
    graph: Graph,
) -> tuple[list[tuple[str, ...]], SCCStats]:
    """Use Kosaraju's algorithm and return deterministic SCCs plus operation counts."""
    adjacency = _normalize_graph(graph)
    reverse = {vertex: [] for vertex in adjacency}
    for source, targets in adjacency.items():
        for target in targets:
            reverse[target].append(source)
    for targets in reverse.values():
        targets.sort()

    stats = SCCStats()
    visited: set[str] = set()
    finish_order: list[str] = []

    def finish(vertex: str) -> None:
        visited.add(vertex)
        stats.vertex_entries += 1
        for target in adjacency[vertex]:
            stats.edge_scans += 1
            if target not in visited:
                finish(target)
        finish_order.append(vertex)

    for vertex in adjacency:
        if vertex not in visited:
            finish(vertex)

    visited.clear()
    components: list[tuple[str, ...]] = []

    def collect(vertex: str, component: list[str]) -> None:
        visited.add(vertex)
        stats.vertex_entries += 1
        component.append(vertex)
        for source in reverse[vertex]:
            stats.edge_scans += 1
            if source not in visited:
                collect(source, component)

    for vertex in reversed(finish_order):
        if vertex not in visited:
            component: list[str] = []
            collect(vertex, component)
            components.append(tuple(sorted(component)))

    components.sort(key=lambda component: component[0])
    return components, stats


def condensation_graph(
    graph: Graph, components: Iterable[Iterable[str]]
) -> dict[int, tuple[int, ...]]:
    """Contract each supplied component and discard duplicate/self edges."""
    adjacency = _normalize_graph(graph)
    groups = [tuple(component) for component in components]
    owner: dict[str, int] = {}
    for component_id, component in enumerate(groups):
        for vertex in component:
            if vertex in owner:
                raise ValueError(f"vertex appears in multiple components: {vertex}")
            owner[vertex] = component_id
    if set(owner) != set(adjacency):
        raise ValueError("components must partition all graph vertices")

    condensed = {component_id: set() for component_id in range(len(groups))}
    for source, targets in adjacency.items():
        for target in targets:
            if owner[source] != owner[target]:
                condensed[owner[source]].add(owner[target])
    return {
        component_id: tuple(sorted(targets))
        for component_id, targets in condensed.items()
    }


def reaching_definitions(
    cfg: Graph,
    gen: Mapping[str, AbstractSet[str]],
    kill: Mapping[str, AbstractSet[str]],
) -> tuple[dict[str, frozenset[str]], dict[str, frozenset[str]], WorklistStats]:
    """Solve OUT = GEN union (IN - KILL) to the least fixed point."""
    adjacency = _normalize_graph(cfg)
    vertices = set(adjacency)
    if set(gen) != vertices or set(kill) != vertices:
        raise ValueError("gen and kill must define every CFG block exactly once")

    predecessors = {vertex: [] for vertex in adjacency}
    for source, targets in adjacency.items():
        for target in targets:
            predecessors[target].append(source)
    for sources in predecessors.values():
        sources.sort()

    in_state = {vertex: frozenset() for vertex in adjacency}
    out_state = {vertex: frozenset() for vertex in adjacency}
    queue = deque(adjacency)
    queued = set(adjacency)
    stats = WorklistStats()

    while queue:
        vertex = queue.popleft()
        queued.remove(vertex)
        stats.evaluations += 1

        incoming: set[str] = set()
        for source in predecessors[vertex]:
            stats.predecessor_unions += 1
            incoming.update(out_state[source])
        new_in = frozenset(incoming)
        new_out = frozenset(gen[vertex] | (new_in - kill[vertex]))

        if new_in != in_state[vertex] or new_out != out_state[vertex]:
            in_state[vertex] = new_in
            out_state[vertex] = new_out
            stats.state_changes += 1
            for target in adjacency[vertex]:
                if target not in queued:
                    queue.append(target)
                    queued.add(target)
                    stats.successor_enqueues += 1

    return in_state, out_state, stats
~~~

<!-- code-sync: ./test_graph_dataflow.py -->
~~~python
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
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/06-数据结构-课程地图|数据结构 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/22-平衡树区间结构与结构扩展地图|数据结构深化：树旋转、区间聚合与扩展地图]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
