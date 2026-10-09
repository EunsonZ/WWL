"""Exact finite certificates for the specified topology models.

No general Smith algorithm or general cup-product inference is provided.
Rational ranks compute Betti numbers only; torsion is checked separately by
the one-relation integer certificates supplied in the lessons.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path


def matrix(value, rows, cols):
    if len(value) != rows or any(len(row) != cols for row in value):
        raise ValueError("matrix shape does not match declared chain dimensions")
    if any(type(x) is not int for row in value for x in row):
        raise TypeError("chain matrices require exact integer entries")
    return value


def product(a, b, output_cols):
    inner = len(b)
    matrix(a, len(a), inner)
    matrix(b, inner, output_cols)
    return [[sum(row[k] * b[k][j] for k in range(inner))
             for j in range(output_cols)] for row in a]


def rank_q(a, cols):
    matrix(a, len(a), cols)
    work = [[Fraction(x) for x in row] for row in a]
    rank = 0
    for col in range(cols):
        pivot = next((i for i in range(rank, len(work)) if work[i][col]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        leading = work[rank][col]
        work[rank] = [x / leading for x in work[rank]]
        for i in range(len(work)):
            if i != rank:
                scale = work[i][col]
                work[i] = [x - scale * y for x, y in zip(work[i], work[rank])]
        rank += 1
        if rank == len(work):
            break
    return rank


def finite_chain(name, dimensions, d1, d2):
    if len(dimensions) != 3 or any(type(n) is not int or n < 0 for n in dimensions):
        raise ValueError("dimensions must be three nonnegative integers")
    n0, n1, n2 = dimensions
    matrix(d1, n0, n1)
    matrix(d2, n1, n2)
    square = product(d1, d2, n2)
    if any(x for row in square for x in row):
        raise ValueError("adjacent boundaries do not compose to zero")
    r1, r2 = rank_q(d1, n1), rank_q(d2, n2)
    betti = [n0 - r1, n1 - r1 - r2, n2 - r2]
    chi = n0 - n1 + n2
    if chi != betti[0] - betti[1] + betti[2]:
        raise AssertionError("Euler certificate failed")
    return {"name": name, "dimensions": dimensions, "d1": d1, "d2": d2,
            "d1_d2": square, "betti_Q": betti, "chi": chi}


def cup_on_fundamental(x, y, orientation=1):
    """AW on t1=[00,10,11], t2=[00,01,11], z=t1-t2.

    Edge coordinate order is a,b,c. Inputs must be integer cocycles.
    The return value is an integer pairing with orientation*z.
    """
    if len(x) != 3 or len(y) != 3:
        raise ValueError("a,b,c coordinates are required")
    if any(type(v) is not int for v in (*x, *y, orientation)):
        raise TypeError("integer cochains and orientation required")
    if orientation not in (-1, 1):
        raise ValueError("orientation must be +1 or -1")
    if x[0] + x[1] != x[2] or y[0] + y[1] != y[2]:
        raise ValueError("input cochains must be cocycles")
    return orientation * (x[0] * y[1] - x[1] * y[0])


def one_relation_integer(m):
    """Certified complex Z --m--> Z --0--> Z, not a Smith routine."""
    if type(m) is not int:
        raise TypeError("integer attaching degree required")
    # U=[sign(m)] and V=[1] certify U*[m]*V=[abs(m)].
    u = -1 if m < 0 else 1
    diagonal = u * m
    if diagonal != abs(m):
        raise AssertionError("one-by-one integer certificate failed")
    return {"degree": m, "U": [[u]], "V": [[1]], "D": [[diagonal]],
            "H1_free_rank": int(m == 0),
            "H1_torsion_factors": [abs(m)] if abs(m) > 1 else [],
            "H2_free_rank": int(m == 0)}


def fixed_report():
    d1_triangle = [[-1, 0, -1], [1, -1, 0], [0, 1, 1]]
    z = [[1], [1], [-1]]
    models = [
        finite_chain("triangle_boundary", [3, 3, 0], d1_triangle, [[], [], []]),
        finite_chain("triangle_filled", [3, 3, 1], d1_triangle, z),
        finite_chain("S1", [1, 1, 0], [[0]], [[]]),
        finite_chain("T2_minimal", [1, 2, 1], [[0, 0]], [[0], [0]]),
        finite_chain("RP2", [1, 1, 1], [[0]], [[2]]),
        finite_chain("wedge_S1_S1_S2", [1, 2, 1], [[0, 0]], [[0], [0]]),
        finite_chain("T2_two_triangles", [1, 3, 2], [[0, 0, 0]],
                     [[1, 1], [1, 1], [-1, -1]]),
    ]
    # The torus quotient c=a+b: Q is onto with a,b as a section.
    # Solving Q(v)=0 gives v=(-t,-t,t), the boundary relation up to sign.
    q = [[1, 0, 1], [0, 1, 1]]
    relation = [[1], [1], [-1]]
    if product(q, relation, 1) != [[0], [0]]:
        raise AssertionError("torus integer relation certificate failed")
    torus_d2 = models[-1]["d2"]
    if product(torus_d2, [[1], [-1]], 1) != [[0], [0], [0]]:
        raise AssertionError("torus fundamental chain is not a cycle")
    x, y = (1, 0, 1), (0, 1, 1)
    cup = {"xy_on_z": cup_on_fundamental(x, y),
           "yx_on_z": cup_on_fundamental(y, x),
           "xx_on_z": cup_on_fundamental(x, x),
           "yy_on_z": cup_on_fundamental(y, y),
           "reverse_orientation_xy": cup_on_fundamental(x, y, -1)}
    circle = {"sheets": 5, "start": 1, "winding": 7,
              "endpoint": (1 + 7) % 5, "closed": 7 % 5 == 0}
    torus_cover = {"index": 6, "start": [1, 2], "winding": [5, -4],
                   "endpoint": [(1 + 5) % 2, (2 - 4) % 3],
                   "closed": 5 % 2 == 0 and (-4) % 3 == 0}
    return {"schema": "wwl-topology154-finite-v1", "models": models,
            "one_relation_integer": [one_relation_integer(m) for m in (0, 1, 2, -2, 3)],
            "RP2_F2_d2": [[2 % 2]], "RP2_F2_betti": [1, 1 - int(2 % 2 != 0), 1 - int(2 % 2 != 0)],
            "torus_cup": cup, "circle_cover": circle, "torus_cover": torus_cover,
            "scope": "Fixed finite certificates only; no classification or general homology proof."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="create this NEW directory and write report.json; never overwrite")
    args = parser.parse_args()
    report = fixed_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "report.json").write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
