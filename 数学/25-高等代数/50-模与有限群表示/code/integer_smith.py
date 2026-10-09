"""Exact, bounded teaching Smith form over Z. No third-party dependencies."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Matrix:
    rows: tuple
    ncols: int

    def __post_init__(self):
        if type(self.ncols) is not int or self.ncols < 0:
            raise ValueError("ncols must be a nonnegative integer")
        if not isinstance(self.rows, tuple):
            raise TypeError("rows must be a tuple of tuples")
        if any(not isinstance(r, tuple) or len(r) != self.ncols for r in self.rows):
            raise ValueError("ragged rows or wrong ncols")
        if any(type(x) is not int for r in self.rows for x in r):
            raise TypeError("entries must be Python integers, not floats or bools")

    @property
    def nrows(self):
        return len(self.rows)

    @property
    def shape(self):
        return self.nrows, self.ncols


def matrix(rows, ncols=None):
    rows = tuple(tuple(r) for r in rows)
    return Matrix(rows, (len(rows[0]) if rows else 0) if ncols is None else ncols)


def identity(n):
    return matrix([[int(i == j) for j in range(n)] for i in range(n)], n)


def multiply(a, b):
    if a.ncols != b.nrows:
        raise ValueError("incompatible multiplication shapes")
    return matrix([[sum(a.rows[i][k] * b.rows[k][j] for k in range(a.ncols))
                    for j in range(b.ncols)] for i in range(a.nrows)], b.ncols)


def determinant(a):
    if a.nrows != a.ncols:
        raise ValueError("determinant requires a square matrix")
    t = [[Fraction(x) for x in row] for row in a.rows]
    result = Fraction(1)
    for k in range(a.nrows):
        pivot = next((i for i in range(k, a.nrows) if t[i][k]), None)
        if pivot is None:
            return 0
        if pivot != k:
            t[pivot], t[k] = t[k], t[pivot]
            result = -result
        value = t[k][k]
        result *= value
        for i in range(k + 1, a.nrows):
            q = t[i][k] / value
            for j in range(k, a.ncols):
                t[i][j] -= q * t[k][j]
    if result.denominator != 1:
        raise ArithmeticError("integer determinant became noninteger")
    return int(result)


def inverse_unimodular(a):
    if a.nrows != a.ncols or abs(determinant(a)) != 1:
        raise ValueError("matrix must be square and unimodular")
    n = a.nrows
    t = [[Fraction(x) for x in a.rows[i]] +
         [Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    for k in range(n):
        pivot = next(i for i in range(k, n) if t[i][k])
        t[k], t[pivot] = t[pivot], t[k]
        q = t[k][k]
        t[k] = [x / q for x in t[k]]
        for i in range(n):
            if i != k:
                q = t[i][k]
                t[i] = [x - q * y for x, y in zip(t[i], t[k])]
    if any(x.denominator != 1 for row in t for x in row[n:]):
        raise ArithmeticError("unimodular inverse became noninteger")
    return matrix([[int(x) for x in row[n:]] for row in t], n)


@dataclass(frozen=True)
class Smith:
    U: Matrix
    D: Matrix
    V: Matrix
    rank: int

    @property
    def invariants(self):
        return tuple(self.D.rows[i][i] for i in range(self.rank))


def verify_smith(b, result):
    u, d, v, r = result.U, result.D, result.V, result.rank
    m, n = b.shape
    if u.shape != (m, m) or v.shape != (n, n) or d.shape != (m, n):
        raise ArithmeticError("wrong returned shapes")
    if type(r) is not int or not 0 <= r <= min(m, n):
        raise ArithmeticError("wrong rank")
    if abs(determinant(u)) != 1 or abs(determinant(v)) != 1:
        raise ArithmeticError("nonunimodular transform")
    if multiply(multiply(u, b), v) != d:
        raise ArithmeticError("UBV != D")
    for i in range(m):
        for j in range(n):
            if i == j and i < r:
                if d.rows[i][j] <= 0:
                    raise ArithmeticError("diagonal is not positive")
            elif d.rows[i][j] != 0:
                raise ArithmeticError("D is not diagonal")
    values = result.invariants
    if any(y % x for x, y in zip(values, values[1:])):
        raise ArithmeticError("divisibility chain failed")


def smith(b, max_ops=20000, max_bits=4096):
    """Return U,D,V with UBV=D; raise on declared teaching resource limits."""
    m, n = b.shape
    if max(m, n) > 8 or any(abs(x) > 10**6 for row in b.rows for x in row):
        raise ValueError("teaching input limit: at most 8x8, abs(entry) <= 10^6")
    if type(max_ops) is not int or max_ops < 1:
        raise ValueError("max_ops must be a positive integer")
    if type(max_bits) is not int or max_bits < 1:
        raise ValueError("max_bits must be a positive integer")
    d = [list(row) for row in b.rows]
    u = [list(row) for row in identity(m).rows]
    v = [list(row) for row in identity(n).rows]
    operations = 0

    def tick():
        nonlocal operations
        operations += 1
        if operations > max_ops or any(abs(x).bit_length() > max_bits
                                      for t in (d, u, v) for row in t for x in row):
            raise RuntimeError("resource limit; no certified partial form returned")

    def swap_rows(i, j):
        for t in (d, u):
            t[i], t[j] = t[j], t[i]
        tick()

    def swap_cols(i, j):
        for t in (d, v):
            for row in t:
                row[i], row[j] = row[j], row[i]
        tick()

    def add_row(dst, src, q):
        for t in (d, u):
            t[dst] = [x + q * y for x, y in zip(t[dst], t[src])]
        tick()

    def add_col(dst, src, q):
        for t in (d, v):
            for row in t:
                row[dst] += q * row[src]
        tick()

    rank = 0
    for k in range(min(m, n)):
        pos = next(((i, j) for i in range(k, m) for j in range(k, n) if d[i][j]), None)
        if pos is None:
            break
        swap_rows(k, pos[0])
        swap_cols(k, pos[1])
        while True:
            i = next((i for i in range(k + 1, m) if d[i][k]), None)
            if i is not None:
                add_row(i, k, -(d[i][k] // d[k][k]))
                if d[i][k]:
                    swap_rows(i, k)
                continue
            j = next((j for j in range(k + 1, n) if d[k][j]), None)
            if j is not None:
                add_col(j, k, -(d[k][j] // d[k][k]))
                if d[k][j]:
                    swap_cols(j, k)
                continue
            bad = next(((i, j) for i in range(k + 1, m) for j in range(k + 1, n)
                        if d[i][j] % d[k][k]), None)
            if bad is None:
                break
            add_row(k, bad[0], 1)
        if d[k][k] < 0:
            for t in (d, u):
                t[k] = [-x for x in t[k]]
            tick()
        rank += 1
    result = Smith(matrix(u, m), matrix(d, n), matrix(v, n), rank)
    verify_smith(b, result)
    return result


def kernel_image(b, result):
    verify_smith(b, result)
    r = result.rank
    kernel = matrix([row[r:] for row in result.V.rows], b.ncols - r)
    ui = inverse_unimodular(result.U)
    image = matrix([[ui.rows[i][j] * result.invariants[j] for j in range(r)]
                    for i in range(b.nrows)], r)
    return kernel, image


def homology(a, b):
    """A=d_k, B=d_(k+1); return integer kernel and boundary coordinates."""
    if a.ncols != b.nrows:
        raise ValueError("A and B have incompatible chain shapes")
    if any(x for row in multiply(a, b).rows for x in row):
        raise ValueError("AB must be exactly zero")
    sa = smith(a)
    k, _ = kernel_image(a, sa)
    vb = multiply(inverse_unimodular(sa.V), b)
    if any(x for row in vb.rows[:sa.rank] for x in row):
        raise ArithmeticError("boundary has a nonzero noncycle coordinate")
    c = matrix(vb.rows[sa.rank:], b.ncols)
    if multiply(k, c) != b:
        raise ArithmeticError("B != KC")
    sc = smith(c)
    reps = multiply(k, inverse_unimodular(sc.U))
    return {"K": k, "C": c, "smith_A": sa, "smith_C": sc,
            "torsion": tuple(x for x in sc.invariants if x > 1),
            "free_rank": a.ncols - sa.rank - sc.rank, "representatives": reps}
