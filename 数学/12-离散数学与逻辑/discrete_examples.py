"""有限教学模型的独立枚举对照。运行本文件无需第三方依赖。

此程序检查小实例，不能执行或证明通用停机判定。
所有计数使用Python整数。CLI只跑固定且很小的例子。
"""
from itertools import permutations, product
from math import comb, gcd


def nonnegative_integer(value, name):
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer, excluding bool")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def cover_count_inclusion(n, q):
    """长度n、q个带身份符号全部出现的精确容斥计数。"""
    nonnegative_integer(n, "n")
    nonnegative_integer(q, "q")
    if n == 0:
        return int(q == 0)
    if q == 0:
        return 0
    return sum((-1) ** j * comb(q, j) * (q-j) ** n for j in range(q+1))


def cover_count_enumerated(n, q):
    nonnegative_integer(n, "n")
    nonnegative_integer(q, "q")
    return sum(len(set(word)) == q for word in product(range(q), repeat=n))


def no_adjacent_count(n):
    nonnegative_integer(n, "n")
    if n == 0:
        return 1
    previous, current = 1, 2
    for _ in range(2, n+1):
        previous, current = current, previous+current
    return current


def no_adjacent_enumerated(n):
    nonnegative_integer(n, "n")
    return sum(all(not (word[i] == word[i+1] == 1)
                   for i in range(n-1))
               for word in product((0, 1), repeat=n))


def convolution_coefficient(factors, degree):
    """有限系数列乘积的degree次系数；缺失系数当0。"""
    nonnegative_integer(degree, "degree")
    coefficients = [1] + [0] * degree
    for factor in factors:
        if any(type(value) is not int for value in factor):
            raise TypeError("coefficients must be integers, excluding bool")
        updated = [0] * (degree+1)
        for i, a in enumerate(coefficients):
            for j, b in enumerate(factor[:degree+1-i]):
                updated[i+j] += a*b
        coefficients = updated
    return coefficients[degree]


def restricted_solutions(total):
    nonnegative_integer(total, "total")
    return [(a, b, total-a-b)
            for a in range(3) for b in range(0, total+1, 2)
            if total-a-b >= 1]


def restricted_coefficient(total):
    nonnegative_integer(total, "total")
    # 提取total次项不需要更高次系数，截断在此精确。
    return convolution_coefficient(
        [[1, 1, 1],
         [int(i % 2 == 0) for i in range(total+1)],
         [int(i >= 1) for i in range(total+1)]], total)


def euclid_trace(a, b):
    nonnegative_integer(a, "a")
    nonnegative_integer(b, "b")
    if a == b == 0:
        raise ValueError("this teaching contract excludes gcd(0, 0)")
    trace = [(a, b)]
    while b != 0:
        a, b = b, a % b
        trace.append((a, b))
    return a, trace


def topological_orders(vertices, edges):
    vertices, edges = tuple(vertices), tuple(edges)
    if len(set(vertices)) != len(vertices):
        raise ValueError("vertices must be distinct")
    known = set(vertices)
    if any(u not in known or v not in known for u, v in edges):
        raise ValueError("edge endpoint is not in vertices")
    result = []
    for order in permutations(vertices):
        positions = {v: i for i, v in enumerate(order)}
        if all(positions[u] < positions[v] for u, v in edges):
            result.append(order)
    return result


def hasse_cover_edges(values):
    values = tuple(values)
    if len(set(values)) != len(values):
        raise ValueError("values must be distinct")
    if any(type(v) is not int or v <= 0 for v in values):
        raise ValueError("divisibility poset requires positive integers")
    return [(a, b) for a in values for b in values
            if a != b and b % a == 0
            and not any(c not in (a, b) and c % a == 0 and b % c == 0
                        for c in values)]


def run_checks():
    # 公式对照直接串枚举，包括空串、空字母表、长度不足边界。
    for n in range(7):
        for q in range(5):
            assert cover_count_inclusion(n, q) == cover_count_enumerated(n, q)
    for n in range(11):
        assert no_adjacent_count(n) == no_adjacent_enumerated(n)
    for total in range(16):
        assert restricted_coefficient(total) == len(restricted_solutions(total))
    for a, b in product(range(21), repeat=2):
        if a == b == 0:
            continue
        answer, trace = euclid_trace(a, b)
        assert answer == gcd(a, b)
        assert all(gcd(x, y) == answer for x, y in trace)
        assert all(after[1] < before[1] for before, after in zip(trace, trace[1:]))
    expected_cover = {(1, 2), (1, 3), (2, 6), (3, 6), (6, 12)}
    assert set(hasse_cover_edges([1, 2, 3, 6, 12])) == expected_cover
    expected_extra = {(1, 2), (1, 3), (2, 4), (2, 6), (3, 6), (4, 12), (6, 12)}
    assert set(hasse_cover_edges([1, 2, 3, 4, 6, 12])) == expected_extra
    edges = [('A', 'B'), ('A', 'C'), ('B', 'D'), ('C', 'D')]
    assert topological_orders('ABCD', edges) == [tuple('ABCD'), tuple('ACBD')]
    assert topological_orders('ABCD', edges+[('D', 'A')]) == []
    assert topological_orders('ABCD', edges[1:]) == [
        tuple('ABCD'), tuple('ACBD'), tuple('BACD')]
    # 上一行删的是A→B，用明确集合另外检查练习中删A→C的结果。
    assert topological_orders('ABCD', [edges[0], *edges[2:]]) == [
        tuple('ABCD'), tuple('ACBD'), tuple('CABD')]
    for p, q, r in product((False, True), repeat=3):
        implies = lambda a, b: not a or b
        assert implies(implies(p, q) and implies(q, r), implies(p, r))
    permissions = [[True, False], [False, True]]
    assert all(any(row) for row in permissions)
    assert not any(all(permissions[u][a] for u in range(2)) for a in range(2))
    for bad in (-1, 0.5, True):
        try:
            no_adjacent_count(bad)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("invalid input accepted")
    for args in [(0, 0), (-1, 3), (True, 1)]:
        try:
            euclid_trace(*args)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError("invalid gcd input accepted")
    print('有限对照通过：覆盖计数35组；无相邻1计数11组；系数16组；gcd440组；图与逻辑对照。')
    print('五位码覆盖三种符号:', cover_count_inclusion(5, 3))
    print('受限解总和6:', restricted_solutions(6))
    print('无相邻1计数n=0..6:', [no_adjacent_count(n) for n in range(7)])
    print('Euclid(84,30):', euclid_trace(84, 30))
    print('任务DAG拓扑顺序:', [''.join(x) for x in topological_orders('ABCD', edges)])


if __name__ == '__main__':
    run_checks()
