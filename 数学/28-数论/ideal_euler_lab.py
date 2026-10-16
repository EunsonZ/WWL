#!/usr/bin/env python3
"""Fixed exact experiments for lessons 05/06; standard library only.

Canonical source: ideal_euler_lab.py. No claim to prove a theorem by enumeration.
Run: python3 ideal_euler_lab.py --output-dir /tmp/ideal-euler-demo
"""
import argparse
from fractions import Fraction
from functools import reduce
from itertools import combinations
import json
from math import gcd, isqrt, log
from pathlib import Path


def integer(value, minimum, name):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def primes_up_to(bound):
    integer(bound, 0, "bound")
    flags = [True] * (bound + 1)
    for k in (0, 1):
        if k <= bound:
            flags[k] = False
    for p in range(2, isqrt(bound) + 1):
        if flags[p]:
            for n in range(p * p, bound + 1, p):
                flags[n] = False
    return [n for n, prime in enumerate(flags) if prime]


def require_prime(p):
    integer(p, 2, "p")
    if any(p % d == 0 for d in range(2, isqrt(p) + 1)):
        raise ValueError("p must be prime")


def mul(u, v):
    """R multiplication in basis (1, omega), with omega**2 = omega - 5."""
    a, b = u
    c, d = v
    return (a * c - 5 * b * d, a * d + b * c + b * d)


def norm(u):
    a, b = u
    return a * a + a * b + 5 * b * b


def lattice_index(columns):
    """Rank-two Z lattice index = gcd of all 2x2 minors; not a norm guess."""
    minors = [abs(a * d - b * c)
              for (a, b), (c, d) in combinations(columns, 2)]
    index = reduce(gcd, minors, 0)
    if not index:
        raise ValueError("columns must span a rank-two lattice")
    return index


def splitting(p):
    require_prime(p)
    roots = [r for r in range(p) if (r * r - r + 5) % p == 0]
    row = {"p": p, "roots": roots, "quotient_size": p * p}
    if len(roots) == 2:
        bases = [[(p, 0), (-r, 1)] for r in roots]
        columns = [mul(u, v) for u in bases[0] for v in bases[1]]
        index = lattice_index(columns)
        assert all(a % p == b % p == 0 for a, b in columns)
        assert index == p * p
        row.update(kind="split", e=[1, 1], f=[1, 1],
                   prime_ideal_norms=[lattice_index(b) for b in bases],
                   product_columns=columns, product_index=index)
    elif len(roots) == 0:
        row.update(kind="inert", e=[1], f=[2], prime_ideal_norms=[p * p])
    else:
        assert p == 19 and roots == [10]
        basis = [(p, 0), (-10, 1)]
        columns = [mul(u, v) for u in basis for v in basis]
        assert all(a % p == b % p == 0 for a, b in columns)
        assert lattice_index(columns) == p * p
        delta_columns = [(-1, 2), mul((-1, 2), (0, 1))]
        assert all((a + 10 * b) % 19 == 0 for a, b in delta_columns)
        assert lattice_index(delta_columns) == 19
        assert mul((-1, 2), (-1, 2)) == (-19, 0)
        row.update(kind="ramified", e=[2], f=[1], prime_ideal_norms=[19],
                   product_columns=columns, product_index=p * p,
                   delta_columns=delta_columns, delta_index=19)
    assert sum(e * f for e, f in zip(row["e"], row["f"])) == 2
    return row


def finite_quotient(p):
    require_prime(p)
    elements = [(a, b) for a in range(p) for b in range(p)]
    def residue(u):
        return tuple(x % p for x in u)
    units = [u for u in elements if any(residue(mul(u, v)) == (1, 0)
                                        for v in elements)]
    square_zero = [u for u in elements if u != (0, 0)
                   and residue(mul(u, u)) == (0, 0)]
    return {"p": p, "size": len(elements), "units": len(units),
            "nonzero_square_zero": square_zero,
            "is_field_by_inverse_scan": len(units) == p * p - 1}


def finite_product(bound, s):
    integer(bound, 2, "bound")
    integer(s, 1, "s")
    result = Fraction(1)
    for p in primes_up_to(bound):
        result *= Fraction(p ** s, p ** s - 1)
    return result


def prefix(n, s):
    integer(n, 1, "n")
    integer(s, 1, "s")
    return sum((Fraction(1, k ** s) for k in range(1, n + 1)), Fraction(0))


def enclosure(bound, s, n):
    integer(bound, 2, "bound")
    integer(s, 2, "s")  # exact-rational experiment subset of real s > 1 theorem
    integer(n, 1, "n")
    product, total = finite_product(bound, s), prefix(n, s)
    product_tail = Fraction(1, (s - 1) * bound ** (s - 1))
    sum_tail = Fraction(1, (s - 1) * n ** (s - 1))
    lower, upper = max(product, total), min(product + product_tail, total + sum_tail)
    assert lower <= upper
    return {"B": bound, "s": s, "N": n, "P_B": str(product),
            "product_upper": str(product + product_tail), "S_N": str(total),
            "sum_upper": str(total + sum_tail),
            "intersection_lower": str(lower), "intersection_upper": str(upper)}


def smooth_integers(bound, n):
    integer(bound, 2, "bound")
    integer(n, 1, "n")
    primes = primes_up_to(bound)
    answer = []
    for k in range(1, n + 1):
        remainder = k
        for p in primes:
            while remainder % p == 0:
                remainder //= p
        if remainder == 1:
            answer.append(k)
    return answer


def svg_frame(title, description, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="980" height="{height}" viewBox="0 0 980 {height}">',
            f'<title>{title}</title><desc>{description}</desc>',
            f'<rect width="980" height="{height}" fill="#f7fafc"/>',
            '<g font-family="sans-serif" fill="#172b4d">',
            f'<text x="35" y="42" font-size="23">{title}</text>']


def write_svgs(data, folder):
    folder.mkdir(parents=True, exist_ok=True)
    selected = {row["p"]: row for row in data["splitting"] if row["p"] in (2, 5, 19)}
    svg = svg_frame("One polynomial, three quotient rings",
                    "Exact roots of X squared minus X plus 5 at primes 2, 5, 19; prime ideals, not repeated labels.", 370)
    labels = {2: ["no root: irreducible", "F4; (2) prime", "e=1, f=2, norm=4"],
              5: ["roots 0, 1: distinct", "F5 x F5; P0 P1=(5)", "each e=1, f=1, norm=5"],
              19: ["root 10: repeated", "F19[e]/(e^2); P^2=(19)", "e=2, f=1, norm=19"]}
    for i, p in enumerate((2, 5, 19)):
        x = 30 + 320 * i
        row = selected[p]
        svg += [f'<rect x="{x}" y="72" width="295" height="240" rx="12" fill="#e3edf8" stroke="#50749b"/>',
                f'<text x="{x+17}" y="110" font-size="25">p = {p}</text>',
                f'<text x="{x+17}" y="145" font-size="16">roots = {row["roots"]}</text>']
        for j, label in enumerate(labels[p]):
            svg.append(f'<text x="{x+17}" y="{190+38*j}" font-size="16">{label}</text>')
    svg += ['<text x="35" y="346" font-size="16">A repeated root gives one prime ideal with exponent 2, not two distinct ideals.</text>', '</g></svg>']
    (folder / 'prime-splitting.svg').write_text('\n'.join(svg) + '\n')
    svg = svg_frame("Euler product: certified upper bounds are not errors",
                    "At s=2, blue segments show product P_B to P_B+1/B; orange stripe shows S_200 to S_200+1/200. Coordinates approximate exact rational JSON endpoints.", 430)
    def xcoord(value):
        return 170 + (float(Fraction(value)) - 1.54) * 3250
    rows = [r for r in data["enclosures"] if r["s"] == 2]
    left, right = xcoord(rows[0]["S_N"]), xcoord(rows[0]["sum_upper"])
    svg += [f'<rect x="{left:.3f}" y="75" width="{right-left:.3f}" height="270" fill="#fedba2"/>',
            '<text x="30" y="78" font-size="15">s=2, N=200</text>']
    for i, row in enumerate(rows):
        y = 117 + 64 * i
        a, b = xcoord(row["P_B"]), xcoord(row["product_upper"])
        svg += [f'<text x="30" y="{y+5}" font-size="18">B = {row["B"]}</text>',
                f'<line x1="{a:.3f}" x2="{b:.3f}" y1="{y}" y2="{y}" stroke="#215f9b" stroke-width="5"/>',
                f'<circle cx="{a:.3f}" cy="{y}" r="5" fill="#215f9b"/>',
                f'<text x="{a:.3f}" y="{y+24}" font-size="13">{float(Fraction(row["P_B"])):.6f} to {float(Fraction(row["product_upper"])):.6f}</text>']
    svg += ['<line x1="170" x2="900" y1="358" y2="358" stroke="#718096"/>']
    for value in (1.55, 1.60, 1.65, 1.70, 1.75):
        x = xcoord(str(value))
        svg += [f'<line x1="{x}" x2="{x}" y1="354" y2="364" stroke="#718096"/>',
                f'<text x="{x-15}" y="383" font-size="13">{value:.2f}</text>']
    svg += ['<text x="30" y="414" font-size="15">Orange: an independent sum-prefix enclosure. Exact endpoints are saved as fractions.</text>', '</g></svg>']
    (folder / 'euler-enclosure.svg').write_text('\n'.join(svg) + '\n')


def build_data():
    rows = [splitting(p) for p in primes_up_to(101)]
    nonzero_squares19 = sorted({r * r % 19 for r in range(1, 19)})
    for row in rows:
        p = row["p"]
        if p not in (2, 19):
            assert (row["kind"] == "split") == (p % 19 in nonzero_squares19)
    norm_checks = 0
    for a in range(-3, 4):
        for b in range(-3, 4):
            for c in range(-3, 4):
                for d in range(-3, 4):
                    assert norm(mul((a, b), (c, d))) == norm((a, b)) * norm((c, d))
                    norm_checks += 1
    quotients = [finite_quotient(p) for p in (2, 5, 19)]
    assert [q["units"] for q in quotients] == [3, 16, 342]
    assert [len(q["nonzero_square_zero"]) for q in quotients] == [0, 0, 18]
    enclosures = [enclosure(b, s, 200) for s in (2, 3) for b in (5, 10, 30, 100)]
    boundary = [{"B": b, "P_B_at_1": str(finite_product(b, 1)),
                 "H_B": str(prefix(b, 1))} for b in (5, 10, 30, 100)]
    assert all(Fraction(r["P_B_at_1"]) >= Fraction(r["H_B"]) for r in boundary)
    counts = []
    for x in (10, 100, 1000, 10000):
        count = len(primes_up_to(x))
        counts.append({"x": x, "pi_x": count, "pi_log_x_over_x_float": count * log(x) / x})
    assert [r["pi_x"] for r in counts] == [4, 25, 168, 1229]
    invalid = [lambda: splitting(1), lambda: splitting(9), lambda: splitting(True),
               lambda: enclosure(2.9, 2, 200), lambda: enclosure(5, 1, 200),
               lambda: enclosure(5, 2.0, 200), lambda: prefix(0, 2),
               lambda: finite_product(5, 0), lambda: lattice_index([(1, 1), (2, 2)])]
    for call in invalid:
        try:
            call()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input accepted")
    assert finite_product(5, 2) == Fraction(25, 16)
    assert prefix(5, 2) == Fraction(5269, 3600)
    return {"status": "PASS", "date": "2026-10-17", "integer_basis": ["1", "omega"],
            "relation": "omega^2=omega-5", "splitting": rows,
            "nonzero_squares_mod19": nonzero_squares19, "quotients": quotients,
            "norm_multiplicativity_finite_checks": norm_checks,
            "enclosures": enclosures, "boundary_s1": boundary,
            "smooth_B5_through30": smooth_integers(5, 30), "prime_counts": counts,
            "invalid_inputs_rejected": len(invalid),
            "limits": "Finite exact checks; not a proof of general ideal factorization, Euler convergence or PNT. No old labs rerun."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    data = build_data()
    results = args.output_dir / '实践结果'
    results.mkdir(parents=True, exist_ok=True)
    (results / 'ideal-euler-20261017.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    write_svgs(data, args.output_dir / 'assets')
    print(json.dumps({"status": data["status"], "primes": len(data["splitting"]),
                      "enclosures": len(data["enclosures"]), "counts": data["prime_counts"],
                      "invalid_rejected": data["invalid_inputs_rejected"]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
