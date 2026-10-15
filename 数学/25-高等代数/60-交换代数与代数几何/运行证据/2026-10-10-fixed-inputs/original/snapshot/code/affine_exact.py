"""Bounded rational polynomial certificates, no general Groebner solver.
Python 3.10+, standard library. Import has no I/O or computation.
"""
from fractions import Fraction
import argparse
import json

MAX_TERMS = 256
MAX_DEGREE = 64
MAX_BITS = 4096
MAX_STEPS = 2000


class Poly:
    def __init__(self, n, terms=None):
        if type(n) is not int or not 1 <= n <= 3:
            raise ValueError("variable count must be integer in 1..3")
        if terms is not None and type(terms) is not dict:
            raise ValueError("terms must be a dictionary")
        clean = {}
        for powers, coefficient in (terms or {}).items():
            if (type(powers) is not tuple or len(powers) != n or
                any(type(e) is not int or e < 0 for e in powers)):
                raise ValueError("invalid exponent tuple")
            if type(coefficient) not in (int, Fraction):
                raise ValueError("coefficient must be int or Fraction")
            q = Fraction(coefficient)
            if sum(powers) > MAX_DEGREE:
                raise ValueError("generated degree bound exceeded")
            if max(abs(q.numerator).bit_length(), q.denominator.bit_length()) > MAX_BITS:
                raise ValueError("coefficient bit bound exceeded")
            if q:
                clean[powers] = q
        if len(clean) > MAX_TERMS:
            raise ValueError("term bound exceeded")
        self.n, self.terms = n, clean

    @classmethod
    def constant(cls, n, c):
        return cls(n, {(0,) * n: c})

    @classmethod
    def variable(cls, n, i):
        if type(i) is not int or not 0 <= i < n:
            raise ValueError("invalid variable index")
        e = tuple(int(j == i) for j in range(n))
        return cls(n, {e: 1})

    def require_same(self, other):
        if not isinstance(other, Poly) or self.n != other.n:
            raise ValueError("polynomial variable counts differ")

    def __eq__(self, other):
        return isinstance(other, Poly) and self.n == other.n and self.terms == other.terms

    def __add__(self, other):
        self.require_same(other)
        d = dict(self.terms)
        for e, c in other.terms.items():
            d[e] = d.get(e, Fraction(0)) + c
        return Poly(self.n, d)

    def __neg__(self):
        return Poly(self.n, {e: -c for e, c in self.terms.items()})

    def __sub__(self, other):
        return self + (-other)

    def __mul__(self, other):
        self.require_same(other)
        d = {}
        for e, a in self.terms.items():
            for f, b in other.terms.items():
                g = tuple(i + j for i, j in zip(e, f))
                d[g] = d.get(g, Fraction(0)) + a * b
        return Poly(self.n, d)

    def power(self, e):
        if type(e) is not int or not 0 <= e <= 12:
            raise ValueError("power must be integer in 0..12")
        result = Poly.constant(self.n, 1)
        for _ in range(e):
            result = result * self
        return result

    def derivative(self, i):
        Poly.variable(self.n, i)  # validate index
        d = {}
        for e, c in self.terms.items():
            if e[i]:
                f = tuple(v - int(j == i) for j, v in enumerate(e))
                d[f] = c * e[i]
        return Poly(self.n, d)

    def evaluate(self, point):
        if (type(point) not in (tuple, list) or len(point) != self.n or
            any(type(c) not in (int, Fraction) for c in point)):
            raise ValueError("point must have rational coordinates")
        return sum((c * prod(Fraction(v) ** e for v, e in zip(point, powers))
                    for powers, c in self.terms.items()), Fraction(0))

    def substitute(self, images):
        if (type(images) not in (tuple, list) or len(images) != self.n or
            not images or any(not isinstance(q, Poly) for q in images)):
            raise ValueError("invalid substitution")
        m = images[0].n
        if any(q.n != m for q in images):
            raise ValueError("image variable counts differ")
        result = Poly.constant(m, 0)
        for e, c in self.terms.items():
            term = Poly.constant(m, c)
            for q, degree in zip(images, e):
                term = term * q.power(degree)
            result = result + term
        return result

    def homogenize(self):
        if self.n >= 3:
            raise ValueError("homogenization output limited to 3 variables")
        degree = max((sum(e) for e in self.terms), default=0)
        return Poly(self.n + 1, {e + (degree - sum(e),): c for e, c in self.terms.items()})

    def leading(self):
        if not self.terms:
            raise ValueError("zero polynomial has no leading term")
        e = max(self.terms)  # lexicographic order x > y > z
        return e, self.terms[e]

    def encode(self):
        return {"variables": self.n, "terms": [
            {"powers": list(e), "numerator": c.numerator, "denominator": c.denominator}
            for e, c in sorted(self.terms.items(), reverse=True)]}


def prod(values):
    result = Fraction(1)
    for v in values:
        result *= v
    return result


def divide(f, divisors):
    """Lex division certificate f=sum(q_i*g_i)+r; remainder depends on order."""
    if not isinstance(f, Poly) or type(divisors) not in (tuple, list):
        raise ValueError("invalid division inputs")
    if not 1 <= len(divisors) <= 8:
        raise ValueError("divisor count must be 1..8")
    for g in divisors:
        f.require_same(g)
        g.leading()  # reject zero divisor
    qs = [Poly.constant(f.n, 0) for _ in divisors]
    remainder = Poly.constant(f.n, 0)
    current = f
    steps = 0
    while current.terms:
        steps += 1
        if steps > MAX_STEPS:
            raise ValueError("division step bound exceeded")
        e, c = current.leading()
        for j, g in enumerate(divisors):
            a, b = g.leading()
            if all(i >= k for i, k in zip(e, a)):
                mon = Poly(f.n, {tuple(i-k for i, k in zip(e, a)): c / b})
                qs[j] = qs[j] + mon
                current = current - mon * g
                break
        else:
            mon = Poly(f.n, {e: c})
            remainder = remainder + mon
            current = current - mon
    return qs, remainder


def s_polynomial(f, g):
    f.require_same(g)
    e, a = f.leading()
    h, b = g.leading()
    lcm = tuple(max(i, j) for i, j in zip(e, h))
    m = Poly(f.n, {tuple(i-j for i, j in zip(lcm, e)): 1 / a})
    n = Poly(f.n, {tuple(i-j for i, j in zip(lcm, h)): 1 / b})
    return m * f - n * g


def rank(rows, ncols):
    if type(ncols) is not int or not 0 <= ncols <= 3:
        raise ValueError("invalid column count")
    if type(rows) is not list or len(rows) > 8:
        raise ValueError("invalid rows")
    if any(type(row) is not list or len(row) != ncols or
           any(type(v) not in (int, Fraction) for v in row) for row in rows):
        raise ValueError("ragged or non-rational matrix")
    a = [[Fraction(v) for v in row] for row in rows]
    r = 0
    for j in range(ncols):
        i = next((i for i in range(r, len(a)) if a[i][j]), None)
        if i is None:
            continue
        a[i], a[r] = a[r], a[i]
        scale = a[r][j]
        a[r] = [v / scale for v in a[r]]
        for i in range(len(a)):
            if i != r:
                scale = a[i][j]
                a[i] = [u - scale * v for u, v in zip(a[i], a[r])]
        r += 1
    return r


def decode(record):
    if type(record) is not dict or set(record) != {"variables", "terms"}:
        raise ValueError("invalid input polynomial fields")
    n, terms = record["variables"], record["terms"]
    if type(terms) is not list or len(terms) > 128:
        raise ValueError("invalid input term count")
    d = {}
    for t in terms:
        if type(t) is not dict or set(t) != {"powers", "numerator", "denominator"}:
            raise ValueError("invalid term fields")
        e, a, b = t["powers"], t["numerator"], t["denominator"]
        if type(e) is not list or any(type(v) is not int or not 0 <= v <= 12 for v in e):
            raise ValueError("invalid input exponents")
        if type(a) is not int or type(b) is not int or abs(a) > 10**6 or not 1 <= b <= 10**6:
            raise ValueError("invalid input rational")
        key = tuple(e)
        if key in d:
            raise ValueError("duplicate monomial")
        d[key] = Fraction(a, b)
    return Poly(n, d)


def fixed_report(data):
    if type(data) is not dict or set(data) != {"schema", "polynomials", "points"} or data["schema"] != "wwl-affine-fixed-v1":
        raise ValueError("invalid fixed input schema")
    expected = {"f": {(2, 0): 1, (0, 1): -1},
                "g": {(0, 2): 1, (1, 0): -1},
                "parabola": {(0, 1): 1, (2, 0): -1},
                "cusp": {(0, 2): 1, (3, 0): -1},
                "node": {(0, 2): 1, (2, 0): -1, (3, 0): -1},
                "axis": {(0, 1): 1}, "double_axis": {(0, 2): 1},
                "hyperbola": {(1, 1): 1, (0, 0): -1}}
    if type(data["polynomials"]) is not dict or set(data["polynomials"]) != set(expected):
        raise ValueError("invalid fixed polynomial names")
    ps = {name: decode(value) for name, value in data["polynomials"].items()}
    if any(ps[name] != Poly(2, terms) for name, terms in expected.items()):
        raise ValueError("CLI accepts only the published fixed polynomial set")
    if data["points"] != {"origin": [0, 0], "cusp_regular": [1, 1], "parabola_regular": [2, 4]}:
        raise ValueError("CLI accepts only fixed points")
    if any(type(v) is not int for point in data["points"].values() for v in point):
        raise ValueError("integer fixed points required")
    x, y = Poly.variable(2, 0), Poly.variable(2, 1)
    t = Poly.variable(1, 0)
    one = Poly.constant(1, 1)
    g1, g2 = x - y.power(2), y.power(4) - y
    certificates = {
        "g1_plus_g": g1 + ps["g"],
        "g2_minus_f_minus_x_plus_y2_times_g": g2 - ps["f"] - (x + y.power(2)) * ps["g"],
        "f_minus_x_plus_y2_times_g1_minus_g2": ps["f"] - (x + y.power(2)) * g1 - g2,
        "parabola_parameter": ps["parabola"].substitute([t, t.power(2)]),
        "cusp_parameter": ps["cusp"].substitute([t.power(2), t.power(3)]),
        "node_parameter": ps["node"].substitute([t.power(2) - one, t * (t.power(2) - one)]),
    }
    sp = s_polynomial(g1, g2)
    quotients, remainder = divide(sp, [g1, g2])
    jacobians = {}
    for name, pointname in [("axis", "origin"), ("double_axis", "origin"),
                            ("cusp", "origin"), ("cusp", "cusp_regular"),
                            ("node", "origin"), ("parabola", "parabola_regular")]:
        point = data["points"][pointname]
        row = [ps[name].derivative(i).evaluate(point) for i in range(2)]
        jacobians[name + "@" + pointname] = {"point": point, "row": [str(v) for v in row],
                                          "rank": rank([row], 2), "tangent_dimension": 2 - rank([row], 2)}
    return {"schema": "wwl-affine-report-v1", "domain": "Q", "order": "lex x>y",
            "inputs": {name: p.encode() for name, p in ps.items()},
            "basis": [g1.encode(), g2.encode()],
            "identities": {name: p.encode() for name, p in certificates.items()},
            "s_polynomial": sp.encode(), "s_quotients": [p.encode() for p in quotients],
            "s_remainder": remainder.encode(), "jacobians": jacobians,
            "homogeneous": {name: ps[name].homogenize().encode()
                            for name in ("parabola", "hyperbola", "cusp")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="published fixed-inputs.json")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as stream:
        data = json.load(stream)
    print(json.dumps(fixed_report(data), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
