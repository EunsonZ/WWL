"""Teaching structures; full implementations match the linked lessons."""
from __future__ import annotations
from dataclasses import dataclass

class AffineSumTree:
    def __init__(self, values):
        self.n = len(values)
        size = max(1, 4 * self.n)
        self.total = [0] * size
        self.tag = [(1, 0)] * size
        if self.n:
            self._build(1, 0, self.n, values)

    def _build(self, node, lo, hi, values):
        if hi - lo == 1:
            self.total[node] = values[lo]
            return
        mid = (lo + hi) // 2
        self._build(node * 2, lo, mid, values)
        self._build(node * 2 + 1, mid, hi, values)
        self._pull(node)

    def _pull(self, node):
        self.total[node] = self.total[node * 2] + self.total[node * 2 + 1]

    def _apply(self, node, length, a, b):
        self.total[node] = a * self.total[node] + b * length
        c, d = self.tag[node]
        self.tag[node] = (a * c, a * d + b)

    def _push(self, node, lo, hi):
        a, b = self.tag[node]
        if hi - lo > 1 and (a, b) != (1, 0):
            mid = (lo + hi) // 2
            self._apply(node * 2, mid - lo, a, b)
            self._apply(node * 2 + 1, hi - mid, a, b)
        self.tag[node] = (1, 0)

    def _check(self, left, right):
        if not (0 <= left <= right <= self.n):
            raise ValueError("invalid half-open interval")

    def update(self, left, right, a, b):
        self._check(left, right)
        if left < right:
            self._update(1, 0, self.n, left, right, a, b)

    def _update(self, node, lo, hi, left, right, a, b):
        if right <= lo or hi <= left:
            return
        if left <= lo and hi <= right:
            self._apply(node, hi - lo, a, b)
            return
        self._push(node, lo, hi)
        mid = (lo + hi) // 2
        self._update(node * 2, lo, mid, left, right, a, b)
        self._update(node * 2 + 1, mid, hi, left, right, a, b)
        self._pull(node)

    def query(self, left, right):
        self._check(left, right)
        if left == right:
            return 0
        return self._query(1, 0, self.n, left, right)

    def _query(self, node, lo, hi, left, right):
        if right <= lo or hi <= left:
            return 0
        if left <= lo and hi <= right:
            return self.total[node]
        self._push(node, lo, hi)
        mid = (lo + hi) // 2
        return (self._query(node * 2, lo, mid, left, right)
                + self._query(node * 2 + 1, mid, hi, left, right))

class RollbackDSU:
    def __init__(self, n):
        if n < 0:
            raise ValueError("negative size")
        self.parent = list(range(n))
        self.size = [1] * n
        self.history = []

    def find(self, x):
        if not 0 <= x < len(self.parent):
            raise IndexError(x)
        while self.parent[x] != x:
            x = self.parent[x]
        return x

    def snapshot(self):
        return len(self.history)

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.history.append((b, a, self.size[a]))
        self.parent[b] = a
        self.size[a] += self.size[b]
        return True

    def rollback(self, mark):
        if not 0 <= mark <= len(self.history):
            raise ValueError("invalid snapshot")
        while len(self.history) > mark:
            child, root, old_size = self.history.pop()
            self.parent[child] = child
            self.size[root] = old_size

@dataclass(frozen=True)
class Node:
    total: int
    lo: int
    hi: int
    left: Node | None = None
    right: Node | None = None


def build(values: list[int], lo: int = 0, hi: int | None = None) -> Node:
    if hi is None:
        hi = len(values)
    if not 0 <= lo < hi <= len(values):
        raise ValueError("nonempty valid interval required")
    if hi-lo == 1:
        return Node(values[lo], lo, hi)
    mid = (lo+hi)//2
    left, right = build(values, lo, mid), build(values, mid, hi)
    return Node(left.total+right.total, lo, hi, left, right)


def persistent_set(root: Node, index: int, value: int) -> Node:
    if not root.lo <= index < root.hi:
        raise IndexError(index)
    if root.hi-root.lo == 1:
        return Node(value, root.lo, root.hi)
    assert root.left is not None and root.right is not None
    left, right = root.left, root.right
    if index < left.hi:
        left = persistent_set(left, index, value)
    else:
        right = persistent_set(right, index, value)
    return Node(left.total+right.total, root.lo, root.hi, left, right)


def persistent_sum(root: Node, lo: int, hi: int) -> int:
    if not root.lo <= lo <= hi <= root.hi:
        raise ValueError("invalid query")
    def visit(node: Node) -> int:
        if hi <= node.lo or node.hi <= lo:
            return 0
        if lo <= node.lo and node.hi <= hi:
            return node.total
        assert node.left is not None and node.right is not None
        return visit(node.left)+visit(node.right)
    return visit(root)


def prefix_function(pattern: str) -> list[int]:
    pi = [0]*len(pattern)
    for i in range(1, len(pattern)):
        j = pi[i-1]
        while j and pattern[i] != pattern[j]:
            j = pi[j-1]
        if pattern[i] == pattern[j]:
            j += 1
        pi[i] = j
    return pi


def kmp(text: str, pattern: str) -> list[int]:
    if not pattern:
        return list(range(len(text)+1))
    pi, j, result = prefix_function(pattern), 0, []
    for i, ch in enumerate(text):
        while j and ch != pattern[j]:
            j = pi[j-1]
        if ch == pattern[j]:
            j += 1
        if j == len(pattern):
            result.append(i-j+1)
            j = pi[j-1]
    return result


def suffix_model(s: str) -> tuple[list[int], list[int]]:
    """Simple comparison model, not an efficient suffix-array algorithm."""
    sa = sorted(range(len(s)), key=lambda i: s[i:])
    lcp = [0]*len(s)
    for rank in range(1, len(s)):
        a,b = sa[rank-1],sa[rank]
        while a+lcp[rank]<len(s) and b+lcp[rank]<len(s) and s[a+lcp[rank]]==s[b+lcp[rank]]:
            lcp[rank] += 1
    return sa,lcp
