"""Small, specification-first algorithms paired with independent oracles."""

from collections import OrderedDict, deque
from functools import lru_cache
from itertools import combinations


def _validate_vertices(n, edges):
    if n < 0:
        raise ValueError("n must be nonnegative")
    for u, v in edges:
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError("vertex outside 0..n-1")


def _components(n, edges, removed_vertex=None, removed_edge=None):
    graph = [[] for _ in range(n)]
    for edge_id, (u, v) in enumerate(edges):
        if edge_id == removed_edge or u == removed_vertex or v == removed_vertex:
            continue
        graph[u].append(v)
        graph[v].append(u)
    seen = set()
    count = 0
    for start in range(n):
        if start == removed_vertex or start in seen:
            continue
        count += 1
        stack = [start]
        seen.add(start)
        while stack:
            u = stack.pop()
            for v in graph[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
    return count


def bridges_and_articulations(n, edges):
    """Return bridge edge ids and articulation vertices of an undirected multigraph."""
    edges = list(edges)
    _validate_vertices(n, edges)
    graph = [[] for _ in range(n)]
    for edge_id, (u, v) in enumerate(edges):
        graph[u].append((v, edge_id))
        graph[v].append((u, edge_id))
    discovery = [-1] * n
    low = [0] * n
    bridges = set()
    articulations = set()
    clock = 0

    def dfs(u, parent_edge):
        nonlocal clock
        discovery[u] = low[u] = clock
        clock += 1
        children = 0
        for v, edge_id in graph[u]:
            if edge_id == parent_edge:
                continue
            if discovery[v] == -1:
                children += 1
                dfs(v, edge_id)
                low[u] = min(low[u], low[v])
                if low[v] > discovery[u]:
                    bridges.add(edge_id)
                if parent_edge is not None and low[v] >= discovery[u]:
                    articulations.add(u)
            else:
                low[u] = min(low[u], discovery[v])
        if parent_edge is None and children >= 2:
            articulations.add(u)

    for root in range(n):
        if discovery[root] == -1:
            dfs(root, None)
    return bridges, articulations


def brute_bridges_and_articulations(n, edges):
    """Definition oracle: delete one edge/vertex and recount components."""
    edges = list(edges)
    _validate_vertices(n, edges)
    base = _components(n, edges)
    bridges = {
        edge_id
        for edge_id in range(len(edges))
        if _components(n, edges, removed_edge=edge_id) > base
    }
    articulations = {
        v for v in range(n) if _components(n, edges, removed_vertex=v) > base
    }
    return bridges, articulations


def _bipartite_edges(left_size, right_size, edges):
    if left_size < 0 or right_size < 0:
        raise ValueError("side sizes must be nonnegative")
    clean = sorted(set(edges))
    for u, v in clean:
        if not (0 <= u < left_size and 0 <= v < right_size):
            raise ValueError("bipartite endpoint outside its side")
    return clean


def hopcroft_karp(left_size, right_size, edges, phase_distances=None):
    """Return a maximum matching as a set of (left, right) pairs."""
    edges = _bipartite_edges(left_size, right_size, edges)
    graph = [[] for _ in range(left_size)]
    for u, v in edges:
        graph[u].append(v)
    pair_left = [-1] * left_size
    pair_right = [-1] * right_size
    distance = [0] * left_size

    infinity = left_size + right_size + 1

    def bfs():
        queue = deque()
        dist_nil = infinity
        for u in range(left_size):
            if pair_left[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = -1
        while queue:
            u = queue.popleft()
            if distance[u] + 1 > dist_nil:
                continue
            for v in graph[u]:
                mate = pair_right[v]
                if mate == -1:
                    dist_nil = min(dist_nil, distance[u] + 1)
                elif distance[mate] == -1:
                    distance[mate] = distance[u] + 1
                    queue.append(mate)
        return dist_nil

    def dfs(u, dist_nil):
        for v in graph[u]:
            mate = pair_right[v]
            if mate == -1:
                if distance[u] + 1 != dist_nil:
                    continue
            elif distance[mate] != distance[u] + 1 or not dfs(mate, dist_nil):
                continue
            pair_left[u] = v
            pair_right[v] = u
            return True
        distance[u] = -1
        return False

    while True:
        dist_nil = bfs()
        if dist_nil == infinity:
            break
        if phase_distances is not None:
            phase_distances.append(dist_nil)
        for u in range(left_size):
            if pair_left[u] == -1:
                dfs(u, dist_nil)
    return {(u, v) for u, v in enumerate(pair_left) if v != -1}


def brute_matching_size(left_size, right_size, edges):
    """Definition oracle: enumerate every edge subset."""
    edges = _bipartite_edges(left_size, right_size, edges)
    best = 0
    for mask in range(1 << len(edges)):
        chosen = [edges[i] for i in range(len(edges)) if mask & (1 << i)]
        if len({u for u, _ in chosen}) == len(chosen) == len({v for _, v in chosen}):
            best = max(best, len(chosen))
    return best


def min_vertex_cover_from_matching(left_size, right_size, edges, matching):
    """Construct Kőnig's minimum cover from a maximum matching."""
    edges = _bipartite_edges(left_size, right_size, edges)
    matching = set(matching)
    mate_left = {u: v for u, v in matching}
    mate_right = {v: u for u, v in matching}
    graph = [[] for _ in range(left_size)]
    for u, v in edges:
        graph[u].append(v)
    seen_left = {u for u in range(left_size) if u not in mate_left}
    seen_right = set()
    queue = deque(seen_left)
    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if mate_left.get(u) == v or v in seen_right:
                continue
            seen_right.add(v)
            mate = mate_right.get(v)
            if mate is not None and mate not in seen_left:
                seen_left.add(mate)
                queue.append(mate)
    return ({u for u in range(left_size) if u not in seen_left}, seen_right)


def tree_max_weight_independent_set(weights, edges):
    """Return the maximum weight of an independent set in a tree."""
    n = len(weights)
    edges = list(edges)
    _validate_vertices(n, edges)
    if n == 0:
        if edges:
            raise ValueError("empty tree cannot have edges")
        return 0
    if len(edges) != n - 1 or _components(n, edges) != 1:
        raise ValueError("input must be a tree")
    graph = [[] for _ in range(n)]
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)

    def visit(u, parent):
        excluded, included = 0, weights[u]
        for v in graph[u]:
            if v == parent:
                continue
            child_excluded, child_included = visit(v, u)
            excluded += max(child_excluded, child_included)
            included += child_excluded
        return excluded, included

    return max(visit(0, -1))


def brute_max_weight_independent_set(weights, edges):
    edges = list(edges)
    n = len(weights)
    _validate_vertices(n, edges)
    best = 0
    for mask in range(1 << n):
        if all(not (mask >> u & 1 and mask >> v & 1) for u, v in edges):
            best = max(best, sum(weights[v] for v in range(n) if mask >> v & 1))
    return best


def fpt_vertex_cover(n, edges, k):
    """Return a vertex cover of size at most k, or None."""
    edges = tuple(sorted({tuple(sorted(edge)) for edge in edges}))
    _validate_vertices(n, edges)
    if any(u == v for u, v in edges):
        loops = {u for u, v in edges if u == v}
        if len(loops) > k:
            return None
        rest = tuple((u, v) for u, v in edges if u not in loops and v not in loops)
        tail = fpt_vertex_cover(n, rest, k - len(loops))
        return None if tail is None else loops | tail

    def search(remaining, budget):
        if not remaining:
            return set()
        if budget == 0:
            return None
        u, v = remaining[0]
        for chosen in (u, v):
            rest = tuple(edge for edge in remaining if chosen not in edge)
            answer = search(rest, budget - 1)
            if answer is not None:
                return {chosen} | answer
        return None

    return search(edges, k) if k >= 0 else None


def brute_vertex_cover_exists(n, edges, k):
    edges = list(edges)
    _validate_vertices(n, edges)
    for size in range(min(k, n) + 1):
        for chosen in combinations(range(n), size):
            cover = set(chosen)
            if all(u in cover or v in cover for u, v in edges):
                return True
    return False


def lru_faults(requests, capacity):
    if capacity < 0:
        raise ValueError("capacity must be nonnegative")
    cache = OrderedDict()
    faults = 0
    for page in requests:
        if page in cache:
            cache.move_to_end(page)
            continue
        faults += 1
        if capacity == 0:
            continue
        if len(cache) == capacity:
            cache.popitem(last=False)
        cache[page] = None
    return faults


def offline_optimal_faults(requests, capacity):
    """Exhaustive offline oracle over all legal evictions."""
    if capacity < 0:
        raise ValueError("capacity must be nonnegative")
    requests = tuple(requests)

    @lru_cache(maxsize=None)
    def solve(index, cache):
        if index == len(requests):
            return 0
        page = requests[index]
        present = set(cache)
        if page in present:
            return solve(index + 1, cache)
        if capacity == 0:
            return 1 + solve(index + 1, cache)
        if len(present) < capacity:
            return 1 + solve(index + 1, tuple(sorted(present | {page}, key=repr)))
        return 1 + min(
            solve(index + 1, tuple(sorted((present - {evicted}) | {page}, key=repr)))
            for evicted in present
        )

    return solve(0, ())
