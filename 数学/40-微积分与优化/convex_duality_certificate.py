"""Exact small certificates for lesson 08; no general optimization solver.

Python 3.10+, standard library for the default examples. No file/network writes.
Optional --qp-vault-root ROOT imports the existing LQR lab under ROOT and needs
its existing NumPy dependency. This mode reports floating residuals, not a
rigorous enclosure of roundoff. Main guard prevents import-time execution.
"""
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import argparse
import importlib.util
import json
import sys


def parametric(b):
    """min (x-2)^2 s.t. x<=b; all arithmetic here is rational."""
    b = F(b)
    x = min(F(2), b)
    lam = max(2 * (2-b), F(0))
    primal = (x-2)**2
    dual = lam*(2-b) - lam**2/4
    stationarity = 2*(x-2)+lam
    complementary = lam*(x-b)
    derivative = 2*(b-2) if b < 2 else F(0)
    assert x <= b and lam >= 0
    assert stationarity == complementary == 0
    assert primal == dual and derivative == -lam
    # One deliberately nonoptimal multiplier still produces a valid lower bound.
    trial_lam = F(1)
    trial_lower = trial_lam*(2-b)-trial_lam**2/4
    assert trial_lower <= primal
    return dict(b=b, x=x, multiplier=lam, primal=primal, dual=dual,
                derivative=derivative, stationarity=stationarity,
                complementary=complementary, trial_lower=trial_lower)


def degenerate(lam):
    """min x s.t. x^2<=0: finite lam>0 never attains the dual supremum."""
    lam = F(lam)
    if lam <= 0:
        raise ValueError('this finite certificate requires lambda > 0')
    minimizer = -1/(2*lam)
    lower = minimizer + lam*minimizer**2
    assert lower == -1/(4*lam) < 0
    return dict(multiplier=lam, lagrangian_minimizer=minimizer,
                lower=lower, primal_feasible_x=F(0), upper=F(0), gap=-lower)


def soft_threshold(v, threshold):
    v, threshold = F(v), F(threshold)
    if threshold < 0:
        raise ValueError('threshold must be nonnegative')
    return max(v-threshold, F(0)) if v >= 0 else min(v+threshold, F(0))


def prox_trace(step, updates):
    step = F(step)
    if step <= 0 or type(updates) is not int or updates < 0:
        raise ValueError('positive step and nonnegative integer updates required')
    x, rows = F(0), []
    dual_s = F(1)  # |s|<=1 implies |x| >= s*x for every real x.
    lower = 3*dual_s-dual_s**2/2
    for k in range(updates+1):
        value = (x-3)**2/2 + abs(x)
        nxt = soft_threshold(x-step*(x-3), step)
        next_value = (nxt-3)**2/2 + abs(nxt)
        mapping = (x-nxt)/step
        assert value >= lower
        descent_rhs = value-step*mapping**2/2
        if step <= 1:
            assert next_value <= descent_rhs
        rows.append(dict(k=k, x=x, objective=value, lower=lower,
                         gap=value-lower, gradient_mapping=mapping,
                         next_objective=next_value,
                         conservative_descent_holds=next_value <= descent_rhs))
        x = nxt
    return rows


def lp_certificate(y):
    """Three-vertex path. Enumerate all 8 covers independently of the dual."""
    if len(y) != 2:
        raise ValueError('exactly two edge budgets required')
    y = tuple(F(a) for a in y)
    weights = (F(2), F(3), F(2))
    loads = (y[0], y[0]+y[1], y[1])
    feasible = min(y) >= 0 and all(a <= b for a, b in zip(loads, weights))
    covers = [(bits, sum(w*z for w, z in zip(weights, bits)))
              for bits in product((0, 1), repeat=3)
              if bits[0]+bits[1] >= 1 and bits[1]+bits[2] >= 1]
    optimum = min(value for _, value in covers)
    upper = weights[0]+weights[1]  # cover {a,b}
    alleged_lower = sum(y)
    if feasible:
        assert alleged_lower <= optimum <= upper
    return dict(weights=weights, edge_budgets=y, vertex_loads=loads,
                dual_feasible=feasible, alleged_lower=alleged_lower,
                certified_lower=alleged_lower if feasible else None,
                upper=upper, exact_integer_optimum=optimum,
                all_covers=covers)


def svm_certificate():
    """Independent exact-rational check of the existing six-point example."""
    points = ((-1, -1), (-1, 1), (1, -1), (1, 1), (-2, 0), (2, 0))
    labels = (-1, -1, 1, 1, -1, 1)
    alpha = (F(1, 4),)*4+(F(0),)*2
    w, bias = (F(1), F(0)), F(0)
    margins = [y*(sum(a*b for a, b in zip(w, p))+bias)
               for y, p in zip(labels, points)]
    dual_w = tuple(sum(a*y*p[j] for a, y, p in zip(alpha, labels, points))
                   for j in range(2))
    equality = sum(a*y for a, y in zip(alpha, labels))
    complementary = [a*(1-m) for a, m in zip(alpha, margins)]
    primal = sum(v*v for v in w)/2
    dual = sum(alpha)-sum(v*v for v in dual_w)/2
    assert min(margins) >= 1 and min(alpha) >= 0 and equality == 0
    assert dual_w == w and all(v == 0 for v in complementary)
    assert primal == dual == F(1, 2)
    return dict(points=points, labels=labels, alpha=alpha, w=w, bias=bias,
                margins=margins, bias_equality=equality,
                stationary_difference=[a-b for a, b in zip(w, dual_w)],
                complementary=complementary, upper=primal, lower=dual,
                soft_C_one_tenth_feasible=max(alpha) <= F(1, 10))


def existing_qp_certificate(vault_root):
    """Reuse unchanged model/solver; calculate dual separately from KKT checker."""
    import numpy as np
    path = Path(vault_root)/'AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py'
    if not path.is_file():
        raise ValueError(f'existing QP source not found: {path}')
    name = 'wwl147_existing_lqr_lab'
    spec = importlib.util.spec_from_file_location(name, path)
    lab = importlib.util.module_from_spec(spec)
    sys.modules[name] = lab  # dataclass annotation resolution requires registration.
    spec.loader.exec_module(lab)
    _, _, _, _, _, problem, _ = lab.default_problem(dt=0.2, horizon=8, x0=(0.5, 0.0))
    lo, hi = np.full(8, -0.8), np.full(8, 0.8)
    solution = lab.solve_box_qp_active_set(problem.H, problem.f, lo, hi)
    if solution is None:
        raise AssertionError('fixed box problem must be feasible')
    clipped = np.clip(lab.direct_unconstrained(problem), lo, hi)
    result = {}
    for name, z in [('box_qp', solution.u), ('clipped', clipped)]:
        grad = 2*(problem.H@z+problem.f)
        alpha = np.where(np.abs(z-lo) <= 1e-10, np.maximum(grad, 0), 0)
        beta = np.where(np.abs(z-hi) <= 1e-10, np.maximum(-grad, 0), 0)
        d = 2*problem.f-alpha+beta
        dual = problem.constant+alpha@lo-beta@hi-0.25*d@np.linalg.solve(problem.H, d)
        primal = lab.stacked_objective(problem, z)
        primal_violation = max(0., float(np.max(lo-z)), float(np.max(z-hi)))
        residual = float(np.max(np.abs(grad-alpha+beta)))
        complementary = max(float(np.max(np.abs(alpha*(lo-z)))),
                            float(np.max(np.abs(beta*(z-hi)))))
        result[name] = dict(controls=z.tolist(), lower_multipliers=alpha.tolist(),
                           upper_multipliers=beta.tolist(), primal=float(primal),
                           dual=float(dual), gap=float(primal-dual),
                           primal_violation=primal_violation,
                           dual_violation=max(0., float(-np.min(alpha)), float(-np.min(beta))),
                           stationarity=residual, complementary=complementary)
        assert primal_violation < 1e-10 and primal >= dual-1e-9
        if name == 'box_qp':
            assert residual < 1e-9 and complementary < 1e-9 and abs(primal-dual) < 1e-9
    assert result['clipped']['primal'] > result['box_qp']['primal']
    return dict(arithmetic='floating; not an interval-certified bound',
                source=str(path), certificates=result)


def encode(value):
    if isinstance(value, F):
        return str(value)
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qp-vault-root', type=Path,
                        help='optionally verify the existing NumPy box-QP model in this vault')
    args = parser.parse_args()
    output = dict(parametric=[parametric(b) for b in (0, 1, 2, 3)],
                  degenerate=[degenerate(lam) for lam in (1, 10, 100)],
                  proximal_valid=prox_trace(F(1, 2), 6),
                  proximal_bad_step=prox_trace(F(3), 3),
                  lp_valid=lp_certificate((2, 1)),
                  lp_invalid=lp_certificate((2, 2)),
                  svm=svm_certificate())
    if args.qp_vault_root is not None:
        output['qp'] = existing_qp_certificate(args.qp_vault_root)
    print(json.dumps(output, ensure_ascii=False, indent=2, default=encode))


if __name__ == '__main__':
    main()
