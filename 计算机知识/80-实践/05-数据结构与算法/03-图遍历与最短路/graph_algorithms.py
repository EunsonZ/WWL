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
