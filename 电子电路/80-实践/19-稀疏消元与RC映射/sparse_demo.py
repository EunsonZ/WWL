"""Four-node, exactly rational SI teaching model. No general sparse solver claim."""
from fractions import Fraction as F
import argparse
import json
from pathlib import Path


Y = ((3, -1, -1, -1), (-1, 2, 0, 0), (-1, 0, 2, 0), (-1, 0, 0, 2))


def solve_order(rhs, order):
    """Eliminate named nodes in order, update RHS, and back-substitute.

    The immutable, grounded star has conductances in S. rhs is four rational
    currents in A. Output potentials are rational volts. Only this SPD model
    is supported; this does not select numerical pivots or benchmark sparse LU.
    """
    if len(rhs) != 4 or any(isinstance(x, bool) or not isinstance(x, (int, F)) for x in rhs):
        raise ValueError("rhs must contain four exact rational currents")
    if len(order) != 4 or any(type(i) is not int for i in order) or set(order) != set(range(4)):
        raise ValueError("order must be a permutation of four node indices")
    a = [[F(x) for x in row] for row in Y]
    b = [F(x) for x in rhs]
    active = list(range(4))
    stages, saved = [], []
    for k in order:
        remaining = [i for i in active if i != k]
        pivot = a[k][k]
        if pivot <= 0:
            raise ArithmeticError("fixed positive model lost positive pivot")
        saved.append((k, pivot, b[k], {j: a[k][j] for j in remaining}))
        fill = []
        for i in remaining:
            for j in remaining:
                old = a[i][j]
                a[i][j] -= a[i][k] * a[k][j] / pivot
                if i < j and not old and a[i][j]:
                    fill.append((i, j))
            b[i] -= a[i][k] * b[k] / pivot
        stages.append({"eliminated": k, "pivot_S": pivot,
                       "remaining": remaining[:], "fill_pairs": fill,
                       "matrix_S": [[a[i][j] for j in remaining] for i in remaining],
                       "rhs_A": [b[i] for i in remaining]})
        active = remaining
    volts = [F(0)] * 4
    for k, pivot, bk, row in reversed(saved):
        volts[k] = (bk - sum(akj * volts[j] for j, akj in row.items())) / pivot
    return volts, stages


def physical_star(rhs):
    """Independent KCL formula: each leaf satisfies 2*v_i-v_c=b_i."""
    if len(rhs) != 4:
        raise ValueError("four currents required")
    b = list(map(F, rhs))
    vc = (2*b[0] + sum(b[1:])) / 3
    return [vc] + [(vc+x)/2 for x in b[1:]]


def kcl_and_power(volts, rhs):
    """Original branch currents and source/dissipation identity, in SI."""
    vc, *leaves = volts
    branches = [vc-x for x in leaves]
    kcl = [sum(branches)] + [2*x-vc for x in leaves]
    dissipated = sum(i*i for i in branches) + sum(x*x for x in leaves)
    source = sum(v*i for v, i in zip(volts, rhs))
    return kcl, source, dissipated


def cases():
    output = {}
    for name, rhs in (("center", (1, 0, 0, 0)), ("leaf1", (0, 1, 0, 0))):
        center, stages = solve_order(rhs, (0, 1, 2, 3))
        leaves, leaf_stages = solve_order(rhs, (1, 2, 3, 0))
        direct = physical_star(rhs)
        kcl, src, diss = kcl_and_power(center, rhs)
        if center != leaves or center != direct or kcl != list(map(F, rhs)) or src != diss:
            raise ArithmeticError("independent exact cross-check failed")
        output[name] = {"rhs_A": rhs, "volts_V": center,
                        "source_W": src, "dissipation_W": diss,
                        "center_first": stages, "leaf_first": leaf_stages}
    return output


def generate(output):
    """Write exact model results to explicit output; no file write on import."""
    data = cases()
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=True)
    p = dest / "results.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n")
    return p


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="explicit directory outside vault")
    args = parser.parse_args(argv)
    generate(args.output)


if __name__ == "__main__":
    main()
