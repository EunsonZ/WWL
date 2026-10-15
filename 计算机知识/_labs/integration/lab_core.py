"""Small, deterministic reference implementations used by this knowledge folder.

These are teaching models, not production networking, operating-system or compiler
implementations. All state is local; the module performs no I/O on import.
"""
from __future__ import annotations
from collections import OrderedDict, deque
import heapq
import math
import re
from typing import Any, Callable, Iterable, Sequence, TypeVar

T = TypeVar('T')

def lower_bound(a: Sequence[T], x: T) -> int:
    """Return first i with a[i] >= x, or len(a); a must be sorted."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def merge_sort(a: Sequence[T], key: Callable[[T], Any] = lambda x: x) -> list[T]:
    """Stable merge sort; comparison keys must have a consistent total ordering."""
    if len(a) <= 1:
        return list(a)
    mid = len(a) // 2
    left, right = merge_sort(a[:mid], key), merge_sort(a[mid:], key)
    out: list[T] = []
    i = j = 0
    while i < len(left) and j < len(right):
        # Prefer the left element on ties: this is what preserves stability.
        if key(right[j]) < key(left[i]):
            out.append(right[j]); j += 1
        else:
            out.append(left[i]); i += 1
    return out + left[i:] + right[j:]


class UnionFind:
    def __init__(self, n: int):
        if n < 0:
            raise ValueError('negative size')
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

    def find(self, x: int) -> int:
        if not 0 <= x < len(self.parent):
            raise IndexError(x)
        while x != self.parent[x]:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1
        self.components -= 1
        return True


def _validate_graph(graph: Sequence[Sequence[tuple[int, int]]], source: int) -> None:
    if not 0 <= source < len(graph):
        raise ValueError('source outside graph')
    for edges in graph:
        for v, w in edges:
            if not 0 <= v < len(graph) or type(w) is not int:
                raise ValueError('invalid edge; this model uses integer weights')


def dijkstra(graph: Sequence[Sequence[tuple[int, int]]], source: int) -> list[float | int]:
    _validate_graph(graph, source)
    if any(w < 0 for edges in graph for _, w in edges):
        raise ValueError('Dijkstra requires nonnegative weights')
    dist: list[float | int] = [math.inf] * len(graph)
    dist[source] = 0
    heap = [(0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d != dist[u]:
            continue  # Stale entry, not a decrease-key implementation.
        for v, w in graph[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def bellman_ford(graph: Sequence[Sequence[tuple[int, int]]], source: int) -> list[float | int]:
    _validate_graph(graph, source)
    dist: list[float | int] = [math.inf] * len(graph)
    dist[source] = 0
    edges = [(u, v, w) for u, es in enumerate(graph) for v, w in es]
    for _ in range(len(graph) - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] != math.inf and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                changed = True
        if not changed:
            break
    if any(dist[u] != math.inf and dist[u] + w < dist[v] for u, v, w in edges):
        raise ValueError('reachable negative cycle')
    return dist


def knapsack01(items: Sequence[tuple[int, int]], capacity: int) -> int:
    if capacity < 0 or any(w <= 0 or v < 0 for w, v in items):
        raise ValueError('positive weights, nonnegative values and capacity required')
    dp = [0] * (capacity + 1)
    for weight, value in items:
        for room in range(capacity, weight - 1, -1):
            dp[room] = max(dp[room], dp[room - weight] + value)
    return dp[capacity]


def lru_misses(pages: Iterable[int], capacity: int) -> int:
    if capacity <= 0:
        raise ValueError('capacity must be positive')
    resident: OrderedDict[int, None] = OrderedDict()
    misses = 0
    for page in pages:
        if page in resident:
            resident.move_to_end(page)
        else:
            misses += 1
            if len(resident) == capacity:
                resident.popitem(last=False)
            resident[page] = None
    return misses


def cache_misses(addresses: Iterable[int], *, lines: int, ways: int, block_size: int) -> int:
    """Set-associative LRU model; ignores timing, writebacks, prefetch and coherence."""
    if min(lines, ways, block_size) <= 0 or lines % ways:
        raise ValueError('invalid cache geometry')
    sets = [OrderedDict() for _ in range(lines // ways)]
    misses = 0
    for addr in addresses:
        if addr < 0:
            raise ValueError('negative address')
        block = addr // block_size
        bucket = sets[block % len(sets)]
        tag = block // len(sets)
        if tag in bucket:
            bucket.move_to_end(tag)
        else:
            misses += 1
            if len(bucket) == ways:
                bucket.popitem(last=False)
            bucket[tag] = None
    return misses


def round_robin(bursts: Sequence[int], quantum: int) -> tuple[list[tuple[int, int, int]], list[int]]:
    """All jobs arrive at t=0; no I/O or context-switch cost in this model."""
    if quantum <= 0 or any(x < 0 for x in bursts):
        raise ValueError('invalid burst or quantum')
    remaining = list(bursts)
    q = deque(i for i, t in enumerate(bursts) if t)
    finished = [0] * len(bursts)
    trace: list[tuple[int, int, int]] = []
    now = 0
    while q:
        i = q.popleft()
        dt = min(quantum, remaining[i])
        trace.append((i, now, now + dt))
        now += dt
        remaining[i] -= dt
        if remaining[i]:
            q.append(i)
        else:
            finished[i] = now
    return trace, finished


def banker_safe_sequence(available: Sequence[int], allocation: Sequence[Sequence[int]], maximum: Sequence[Sequence[int]]) -> list[int] | None:
    n, m = len(allocation), len(available)
    if len(maximum) != n or any(len(row) != m for row in (*allocation, *maximum)):
        raise ValueError('inconsistent matrix shape')
    if any(x < 0 for x in available):
        raise ValueError('negative available resource')
    if any(a < 0 or a > mx for ar, mr in zip(allocation, maximum) for a, mx in zip(ar, mr)):
        raise ValueError('invalid allocation / maximum')
    work, done, order = list(available), set(), []
    while len(done) < n:
        for i in range(n):
            if i not in done and all(maximum[i][j] - allocation[i][j] <= work[j] for j in range(m)):
                work = [work[j] + allocation[i][j] for j in range(m)]
                done.add(i); order.append(i)
                break
        else:
            return None
    return order


def encode_frame(payload: bytes, limit: int = 4096) -> bytes:
    if not 0 <= len(payload) <= min(limit, 0xFFFFFFFF):
        raise ValueError('payload too large')
    return len(payload).to_bytes(4, 'big') + payload


class FrameParser:
    """Incremental length-prefix parser with a per-frame limit and terminal errors.

    The caller must also bound receive chunk sizes and downstream queues to bound
    total memory; a per-frame limit alone is not an entire backpressure system.
    """
    def __init__(self, limit: int = 4096):
        if not 0 <= limit <= 0xFFFFFFFF:
            raise ValueError('invalid limit')
        self.limit = limit
        self.buffer = bytearray()
        self.expected: int | None = None
        self.closed = False

    def feed(self, chunk: bytes) -> list[bytes]:
        if self.closed:
            raise RuntimeError('parser already finished or failed')
        self.buffer.extend(chunk)
        output: list[bytes] = []
        while True:
            if self.expected is None:
                if len(self.buffer) < 4:
                    break
                self.expected = int.from_bytes(self.buffer[:4], 'big')
                del self.buffer[:4]
                if self.expected > self.limit:
                    self.closed = True; self.buffer.clear()
                    raise ValueError('declared frame exceeds limit')
            if len(self.buffer) < self.expected:
                break
            output.append(bytes(self.buffer[:self.expected]))
            del self.buffer[:self.expected]
            self.expected = None
        return output

    def finish(self) -> None:
        if self.closed:
            raise RuntimeError('parser already finished or failed')
        self.closed = True
        if self.buffer or self.expected is not None:
            raise ValueError('truncated frame at EOF')


def parse_count(value: object) -> int:
    if isinstance(value, dict):
        value = value.get('value')
    if type(value) is not int or value < 0:
        raise ValueError('a nonnegative built-in int, excluding bool, is required')
    return value


# Tiny expression language: decimal nonnegative literals; unary minus; +, -, *;
# parentheses. Python arbitrary-precision integer semantics are deliberate here.
TOKEN = re.compile(r'\s*([0-9]+|[()+*\-])')
Node = tuple

def tokenize(source: str) -> list[str]:
    tokens, pos = [], 0
    while pos < len(source):
        if source[pos:].isspace():
            break
        m = TOKEN.match(source, pos)
        if not m:
            raise ValueError(f'unexpected character at offset {pos}')
        tokens.append(m.group(1)); pos = m.end()
    return tokens


def parse_expression(source: str) -> Node:
    tokens = tokenize(source)
    i = 0
    def expr(min_bp: int) -> Node:
        nonlocal i
        if i == len(tokens):
            raise ValueError('expression expected')
        token = tokens[i]; i += 1
        if token.isdecimal():
            left = ('const', int(token))
        elif token == '-':
            left = ('neg', expr(30))
        elif token == '(':
            left = expr(0)
            if i == len(tokens) or tokens[i] != ')':
                raise ValueError('closing parenthesis expected')
            i += 1
        else:
            raise ValueError('operand expected')
        powers = {'+': 10, '-': 10, '*': 20}
        ops = {'+': 'add', '-': 'sub', '*': 'mul'}
        while i < len(tokens) and tokens[i] in powers:
            operator = tokens[i]; bp = powers[operator]
            if bp < min_bp:
                break
            i += 1
            right = expr(bp + 1)
            left = (ops[operator], left, right)
        return left
    tree = expr(0)
    if i != len(tokens):
        raise ValueError('unexpected trailing token')
    return tree


def eval_ast(node: Node) -> int:
    if node[0] == 'const':
        return node[1]
    if node[0] == 'neg':
        return -eval_ast(node[1])
    a, b = eval_ast(node[1]), eval_ast(node[2])
    if node[0] == 'add': return a + b
    if node[0] == 'sub': return a - b
    if node[0] == 'mul': return a * b
    raise ValueError('unknown AST operator')


def compile_ast(node: Node) -> list[tuple]:
    if node[0] == 'const': return [('push', node[1])]
    if node[0] == 'neg': return compile_ast(node[1]) + [('neg',)]
    if node[0] not in {'add', 'sub', 'mul'}:
        raise ValueError('unknown AST operator')
    return compile_ast(node[1]) + compile_ast(node[2]) + [(node[0],)]


def run_bytecode(code: Sequence[tuple]) -> int:
    stack: list[int] = []
    for ins in code:
        op = ins[0]
        if op == 'push':
            stack.append(ins[1])
        elif op == 'neg':
            if not stack: raise ValueError('stack underflow')
            stack[-1] = -stack[-1]
        elif op in {'add', 'sub', 'mul'}:
            if len(stack) < 2: raise ValueError('stack underflow')
            b, a = stack.pop(), stack.pop()
            stack.append(a + b if op == 'add' else a - b if op == 'sub' else a * b)
        else:
            raise ValueError('unknown instruction')
    if len(stack) != 1:
        raise ValueError('expected exactly one final value')
    return stack[0]
