---
type: practice
stage: 1
status: ready
difficulty: 入门到中级
estimated_minutes: 40
domain: computer-science
tags:
  - computer-science/graph
  - computer-science/shortest-path
---

# 图遍历与最短路

目标：用同一邻接表比较两个问题：BFS 找无权图的最少边层级，Dijkstra 找非负权图的最短距离。

## 运行、观察与成功标准

在本目录运行：

~~~sh
cd "计算机知识/80-实践/05-数据结构与算法/03-图遍历与最短路"
python3 -m unittest -v
~~~

观察 A 到 D：BFS 的先后次序不等于最小总权重，Dijkstra 给出 4.0。节点 E 没有从 A 可达，距离保留为 inf。正常算法热路径不在每次出堆后全量扫描 `distances`；小输入测试在算法返回后核对确切距离、不可达节点和拒绝边界，避免用教学验证污染 Dijkstra 的复杂度。成功标准：测试通过，能说出 Dijkstra 的非负有限权重前提和堆中旧距离可跳过的理由。练习：存储 predecessor 并重建路径；不要把负边交给 Dijkstra。

恢复/清理：只会产生本目录 __pycache__/；确认目录后可删除。源文件通过编辑器撤销或 Git diff 恢复，不删除图数据或其他课程内容。

浮点距离还有额外合同：非负且有限的边权不保证路径累加仍可表示。若处理到的松弛候选溢出，函数抛出 `OverflowError`，而不是把可达节点报告成 `inf`；这里采取保守的整次查询失败策略，即使该候选最后不会成为最短路，也不静默跳过。直接传入的邻接表同样检查节点和权重。

自检：A→B、B→C 各为 `1e308`，D 无入边。C 和 D 都得到 `inf` 为什么错误？检查点：C 可达但距离超出支持域，D 才是不可达；前者本实现拒绝计算，不能用同一状态表示。真实数学最短路与有限精度实现保证是两层。

相关稳定课：[[计算机知识/50-数据结构与算法/07-图的表示BFS-DFS与拓扑排序|图的表示、BFS、DFS 与拓扑排序]]、[[计算机知识/50-数据结构与算法/12-最短路最小生成树与并查集|最短路、最小生成树与并查集]]。

<!-- code-sync: ./graph_algorithms.py -->
~~~python
"""邻接表上的 BFS 与 Dijkstra；标签用 str，权重必须是非负有限数。"""

from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Iterable

Edge = tuple[str, str, float]
Graph = dict[str, list[tuple[str, float]]]


def make_directed_graph(edges: Iterable[Edge]) -> Graph:
    graph: Graph = {}
    for start, end, weight in edges:
        if not isinstance(start, str) or not isinstance(end, str):
            raise TypeError("node labels must be str")
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
            raise ValueError("weights must be finite non-negative numbers")
        graph.setdefault(start, []).append((end, float(weight)))
        graph.setdefault(end, [])
    return graph


def breadth_first_order(graph: Graph, start: str) -> list[str]:
    if start not in graph:
        raise KeyError("start node is absent from graph")
    visited = {start}
    queue: deque[str] = deque([start])
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor, _ in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order


def dijkstra_distances(graph: Graph, start: str) -> dict[str, float]:
    """不可达为 inf；任一处理到的候选距离溢出时保守拒绝整次计算。"""
    if start not in graph:
        raise KeyError("start node is absent from graph")
    for node, edges in graph.items():
        if not isinstance(node, str):
            raise TypeError("node labels must be str")
        for neighbor, weight in edges:
            if not isinstance(neighbor, str) or neighbor not in graph:
                raise ValueError("every edge endpoint must occur in graph")
            if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
                raise ValueError("weights must be finite non-negative numbers")
    distances = {node: math.inf for node in graph}
    distances[start] = 0.0
    frontier: list[tuple[float, str]] = [(0.0, start)]
    while frontier:
        distance, node = heapq.heappop(frontier)
        if distance != distances[node]:
            continue
        for neighbor, weight in graph[node]:
            candidate = distance + weight
            if not math.isfinite(candidate):
                raise OverflowError("candidate path length exceeds finite float range")
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heapq.heappush(frontier, (candidate, neighbor))
    return distances
~~~

<!-- code-sync: ./test_graph_algorithms.py -->
~~~python
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
~~~

返回 [[计算机知识/80-实践/05-数据结构与算法/00-数据结构与算法实践-MOC|数据结构与算法实践]] 与 [[计算机知识/50-数据结构与算法/00-数据结构与算法-MOC|数据结构与算法 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/11-算法设计-课程地图|算法设计 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/50-数据结构与算法/24-图算法网络流匹配与残量网络|算法设计深化：图算法、网络流与匹配]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。


## 双来源补充反例

从 WorkWithLLM 的既有测试提取并适配了 [[计算机知识/80-实践/05-数据结构与算法/03-图遍历与最短路/test_graph_contracts.py|test_graph_contracts.py]]：1 个图算法反例，区分溢出、不可达和直接调用的输入检查。 原实现保持不变，来源与运行结果见 [[Logs/2026-09-08_双来源知识增量导入/artifacts/imported-tests.json|13 个反例映射与验证分层]]。

从 WWL 根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "计算机知识/80-实践/05-数据结构与算法/03-图遍历与最短路/test_graph_contracts.py"
```
