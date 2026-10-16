"""Small, standard-library recalculation for mixed diagnostic exercises.

No HAR training, archive access, plotting, network, or file writes.
Run from any directory with Python 3.10+. Output is a teaching calculation,
not independent review, a continuous supremum certificate, or learner evidence.
"""
from fractions import Fraction as F
import json
import math


def interpolate(nodes, values, x):
    """Newton divided differences and nested evaluation, exact for Fractions."""
    coefficients = list(values)
    for order in range(1, len(nodes)):
        for j in range(len(nodes) - 1, order - 1, -1):
            coefficients[j] = ((coefficients[j] - coefficients[j - 1]) /
                               (nodes[j] - nodes[j - order]))
    value = coefficients[-1]
    for j in range(len(nodes) - 2, -1, -1):
        value = coefficients[j] + (x - nodes[j]) * value
    return value


def lagrange(nodes, values, x):
    """Direct product formula: a second algebraic evaluation for short checks."""
    result = F(0)
    for j, y in enumerate(values):
        basis = F(1)
        for i, node in enumerate(nodes):
            if i != j:
                basis *= (x - node) / (nodes[j] - node)
        result += y * basis
    return result


def softmax(z, temperature):
    scaled = [v / temperature for v in z]
    shifted = [math.exp(v - max(scaled)) for v in scaled]
    return [v / sum(shifted) for v in shifted]


def main():
    report = {"scope": "new small calculations only; old grid/HAR values not rerun"}
    runge = lambda x: F(1) / (1 + 25 * x * x)
    query = F(9, 10)
    rows = []
    for n in (4, 8):
        nodes = [F(-1) + F(2 * j, n) for j in range(n + 1)]
        values = [runge(t) for t in nodes]
        p = interpolate(nodes, values, query)
        assert p == lagrange(nodes, values, query)
        assert all(interpolate(nodes, values, t) == y for t, y in zip(nodes, values))
        rows.append({"n": n, "x": str(query), "p_exact": str(p),
                     "f_exact": str(runge(query)), "abs_error": float(abs(p-runge(query)))})
    report["A"] = rows
    quadratic_nodes = [F(-1), F(-1, 2), F(0), F(1, 2), F(1)]
    quadratic_values = [x*x+1 for x in quadratic_nodes]
    report["C"] = [{"x": str(x), "p": str(interpolate(quadratic_nodes, quadratic_values, x)),
                     "q": str(x*x+1)} for x in (F(1, 4), F(9, 10), F(2))]
    assert all(row["p"] == row["q"] for row in report["C"])
    report["D"] = [{"h": h, "factor": 1-10*h, "step1": 1-10*h,
                     "step2": (1-10*h)**2, "exact1": math.exp(-10*h),
                     "exact2": math.exp(-20*h)} for h in (0.1, 0.25)]
    report["E_V2"] = {"independent3": str(F(9**3, 9**3+1)),
                         "one_source": str(F(9, 10)), "independent2": str(F(81, 82))}
    probabilities = {str(t): softmax([2.0, 0.0], t) for t in (1.0, 2.0)}
    report["F"] = {"probabilities": probabilities,
                    "nll_true_first": {t: -math.log(p[0]) for t,p in probabilities.items()},
                    "nll_true_second": {t: -math.log(p[1]) for t,p in probabilities.items()}}
    report["G"] = {"ratio_at_0.1": str(-25*F(1,10)**2),
                    "ratio_at_0.3": str(-25*F(3,10)**2),
                    "sum_at_0.1": str(runge(F(1,10))), "radius": "1/5"}
    # Iterate the matrix separately from its exact binomial formula.
    x, y = F(0), F(1)
    states = []
    for k in range(1, 7):
        x, y = F(4,5)*x + 8*y, F(4,5)*y
        expected = (8*k*F(4,5)**(k-1), F(4,5)**k)
        assert (x,y) == expected
        states.append({"k":k,"x":str(x),"y":str(y),"norm":math.hypot(float(x),float(y))})
    report["H"] = states
    report["V1"] = {"zero": [0.0]*5, "epsilon_1e-6": [(-1.5)**k * 1e-6 for k in range(5)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
