"""Finite distribution integration, no training library or external access.

All mathematical values except displayed logarithmic bounds use exact Fractions.
The input describes iid samples; the correlated rows section deliberately does not.
Only stdout is written. The caller records environment, hashes and raw output.
"""
import argparse
import json
import math
from fractions import Fraction as F
from pathlib import Path


def distribution(raw):
    rows = [(F(v['x']), F(v['y']), F(v['mass'])) for v in raw]
    if sum(p for _, _, p in rows) != 1 or any(p < 0 for _, _, p in rows):
        raise ValueError('Masses must be nonnegative and sum to one.')
    if any(abs(x) != 1 or abs(y) != 1 for x, y, _ in rows):
        raise ValueError('This finite model requires x,y in {-1,1}.')
    return rows


def risk(w, rows):
    return sum(p * (1-y*w*x)/2 for x, y, p in rows)


def output_from_count(k, n, lam):
    # Stationarity of 1/2 - tbar*w/2 + lambda*w^2/2, then project to [-1,1].
    tbar = F(2*k-n, n)
    w = max(F(-1), min(F(1), tbar/(2*lam)))
    return w, tbar


def integrate(n, lam, rows, shifted):
    q = sum(p for x, y, p in rows if x*y == 1)
    states = []
    totals = {name: F(0) for name in ('mass', 'weight', 'train', 'risk', 'shifted_risk')}
    for k in range(n+1):
        mass = F(math.comb(n, k)) * q**k * (1-q)**(n-k)
        w, tbar = output_from_count(k, n, lam)
        train = (1-w*tbar)/2
        true = risk(w, rows)
        shifted_true = risk(w, shifted)
        for name, value in [('mass', 1), ('weight', w), ('train', train),
                            ('risk', true), ('shifted_risk', shifted_true)]:
            totals[name] += mass*value
        states.append({'k': k, 'mass': mass, 'w': w, 'train': train, 'risk': true,
                       'gap': true-train, 'shifted_risk': shifted_true})
    replacement_max = F(0)
    for k in range(n):
        wk, _ = output_from_count(k, n, lam)
        wn, _ = output_from_count(k+1, n, lam)
        replacement_max = max(replacement_max, abs(wn-wk)/2)
    beta = F(1, 2)/(lam*n)  # G=1/2; replace-one beta=2 G^2/(lambda n).
    best_class_risk = min(risk(F(-1), rows), risk(F(1), rows))
    return {'n': n, 'lambda': lam, 'totals': totals,
            'expected_gap': totals['risk']-totals['train'],
            'expected_excess': totals['risk']-best_class_risk,
            'beta_upper': beta, 'actual_uniform_replace_one': replacement_max,
            'comparator_upper': beta+lam/2, 'states': states}


def growth(m):
    xs = list(range(m))
    # Half-integer cutoffs produce each distinct threshold pattern exactly once.
    cutoffs = [F(2*j-1, 2) for j in range(m+1)]
    thresholds = {tuple(int(F(x) >= t) for x in xs) for t in cutoffs}
    intervals = {tuple(0 for _ in xs)}
    for a in range(m):
        for b in range(a, m):
            intervals.add(tuple(int(a <= x <= b) for x in xs))
    return {'m': m, 'threshold': len(thresholds), 'interval': len(intervals),
            'all_labels': 2**m,
            'threshold_patterns': sorted(thresholds), 'interval_patterns': sorted(intervals),
            'sauer_d1': sum(math.comb(m, j) for j in range(min(1, m)+1)),
            'sauer_d2': sum(math.comb(m, j) for j in range(min(2, m)+1))}


def exact_scalar_rademacher(n):
    # |x_i|=1 in one dimension, signs*y or signs*x have the same distribution.
    return sum(F(math.comb(n, k), 2**n)*F(abs(2*k-n), n) for k in range(n+1))


def stringify(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: stringify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stringify(v) for v in value]
    return value


def calculate(cfg):
    rows, shifted = distribution(cfg['distribution']), distribution(cfg['shifted_distribution'])
    ns, lambdas = cfg['sample_sizes'], [F(x) for x in cfg['lambdas']]
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in ns):
        raise ValueError('Sample sizes must be positive integers.')
    if any(lam <= 0 for lam in lambdas):
        raise ValueError('Strong convex regularization requires lambda>0.')
    fc = cfg['finite_class']
    epsilon, eta = (F(cfg['erm_transfer'][key]) for key in ('uniform_epsilon', 'optimization_eta'))
    users = cfg['repeated_rows']['independent_users']
    copies = cfg['repeated_rows']['copies_per_user']
    if users < 1 or copies < 1:
        raise ValueError('Positive independent users and copies required.')
    repeated = []
    for lam in lambdas:
        summary = integrate(users, lam, rows, shifted)
        repeated.append({'lambda': lam, 'independent_units': users, 'row_count': users*copies,
                         'expected_train': summary['totals']['train'],
                         'expected_risk': summary['totals']['risk'],
                         'expected_gap': summary['expected_gap'],
                         'valid_beta_from_independent_units': summary['beta_upper'],
                         'invalid_beta_if_rows_assumed_iid': F(1,2)/(lam*users*copies)})
    return stringify({
        'schema': 'wwl-learning-theory-finite-v1', 'input': cfg,
        'model': {'G': F(1,2), 'C': 1, 'B': 1, 'r': 1,
                  'original_best_class_risk': min(risk(F(-1), rows), risk(F(1), rows))},
        'growth': [growth(m) for m in cfg['growth_sizes']],
        'finite_class_epsilon_float': math.sqrt(math.log(2*fc['M']/float(F(fc['delta'])))/(2*fc['n'])),
        'erm_transfer_bound': 2*epsilon+eta,
        'iid_integrals': [integrate(n, lam, rows, shifted) for n in ns for lam in lambdas],
        'repeated_rows': repeated,
        'rademacher': [{'n': n, 'scalar_fraction': exact_scalar_rademacher(n),
                        'upper_float': 1/math.sqrt(n)} for n in ns]
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('inputs.json'))
    args = parser.parse_args()
    config = json.loads(args.input.read_text(encoding='utf-8'))
    print(json.dumps(calculate(config), ensure_ascii=False, indent=2))
