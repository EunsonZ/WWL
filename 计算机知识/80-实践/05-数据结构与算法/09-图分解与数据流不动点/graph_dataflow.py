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
    materialized = {vertex: tuple(neighbors) for vertex, neighbors in graph.items()}
    vertices = set(materialized)
    for neighbors in materialized.values():
        vertices.update(neighbors)
    return {
        vertex: tuple(sorted(set(materialized.get(vertex, ()))))
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
