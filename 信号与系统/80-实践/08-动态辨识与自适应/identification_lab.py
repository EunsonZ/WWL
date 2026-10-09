"""Finite FIR/ARX experiments with explicit initial information and time splits.
No device access, control actuation, package installation or hidden data.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import random


def solve(matrix, rhs):
    n = len(rhs)
    if not n or len(matrix) != n or any(len(r) != n for r in matrix):
        raise ValueError('nonempty square system required')
    a = [[float(v) for v in row]+[float(b)] for row, b in zip(matrix, rhs)]
    if any(not math.isfinite(v) for row in a for v in row):
        raise ValueError('finite system required')
    for j in range(n):
        pivot = max(range(j, n), key=lambda k: abs(a[k][j]))
        if abs(a[pivot][j]) < 1e-12: raise ValueError('unresolved numerical rank')
        a[j], a[pivot] = a[pivot], a[j]
        scale = a[j][j]
        a[j] = [v/scale for v in a[j]]
        for k in range(n):
            if k != j:
                v = a[k][j]
                a[k] = [x-v*y for x, y in zip(a[k], a[j])]
    return [r[-1] for r in a]


def dot(a, b):
    if len(a) != len(b): raise ValueError('aligned vector shapes required')
    return sum(x*y for x, y in zip(a, b))


def check_data(rows, target):
    if not rows or len(rows) != len(target) or not rows[0]:
        raise ValueError('aligned nonempty samples required')
    m = len(rows[0])
    if any(len(row) != m for row in rows): raise ValueError('fixed regressor dimension required')
    if any(not math.isfinite(v) for row in rows for v in row) or any(not math.isfinite(v) for v in target):
        raise ValueError('finite samples required')
    return m


def batch(rows, target, lam=1., prior=.01, theta0=None):
    m = check_data(rows, target)
    if not math.isfinite(lam) or not 0 < lam <= 1 or not math.isfinite(prior) or prior <= 0:
        raise ValueError('0 < lambda <= 1, positive initial information required')
    center = [0.]*m if theta0 is None else list(theta0)
    if len(center) != m or any(not math.isfinite(v) for v in center): raise ValueError('finite initial center required')
    n = len(rows)
    R = [[prior*lam**n*(1 if i == j else 0) for j in range(m)] for i in range(m)]
    b = [prior*lam**n*v for v in center]
    for k, (phi, y) in enumerate(zip(rows, target)):
        weight = lam**(n-1-k)
        for i in range(m):
            b[i] += weight*phi[i]*y
            for j in range(m): R[i][j] += weight*phi[i]*phi[j]
    return {'theta': solve(R, b), 'R': R, 'b': b, 'lambda': lam, 'R0': prior, 'theta0': center}


def rls(rows, target, lam=1., prior=.01, theta0=None):
    m = check_data(rows, target)
    if not math.isfinite(lam) or not 0 < lam <= 1 or not math.isfinite(prior) or prior <= 0:
        raise ValueError('0 < lambda <= 1, positive initial information required')
    theta = [0.]*m if theta0 is None else list(theta0)
    if len(theta) != m or any(not math.isfinite(v) for v in theta): raise ValueError('finite initial center required')
    P = [[(1/prior if i == j else 0.) for j in range(m)] for i in range(m)]
    trajectory = []
    for phi, y in zip(rows, target):
        z = [dot(row, phi) for row in P]
        den = lam+dot(phi, z)
        if den <= 0 or not math.isfinite(den): raise ArithmeticError('lost positive RLS denominator')
        gain = [v/den for v in z]
        error = y-dot(theta, phi)
        theta = [t+k*error for t, k in zip(theta, gain)]
        # phi^T P separately computed; does not silently assume floating symmetry.
        row_product = [sum(phi[i]*P[i][j] for i in range(m)) for j in range(m)]
        P = [[(P[i][j]-gain[i]*row_product[j])/lam for j in range(m)] for i in range(m)]
        if any(not math.isfinite(v) for v in theta): raise ArithmeticError('nonfinite RLS state')
        trajectory.append(theta[:])
    return {'theta': theta, 'inverse_information': P, 'trajectory': trajectory}


def lms(rows, target, mu=.02):
    m = check_data(rows, target)
    if not math.isfinite(mu) or mu <= 0: raise ValueError('positive step required')
    theta, trajectory = [0.]*m, []
    for phi, y in zip(rows, target):
        error = y-dot(phi, theta)
        theta = [t+mu*v*error for t, v in zip(theta, phi)]
        if any(not math.isfinite(v) for v in theta): raise ArithmeticError('nonfinite LMS state')
        trajectory.append(theta[:])
    return {'theta': theta, 'trajectory': trajectory, 'mu': mu}


def mse(actual, predicted):
    if not actual or len(actual) != len(predicted): raise ValueError('aligned nonempty sequences required')
    return sum((a-b)**2 for a, b in zip(actual, predicted))/len(actual)


def diagnostics(u, error, maxlag=8):
    if len(u) != len(error) or len(u) <= maxlag: raise ValueError('enough aligned residual samples required')
    n, um, em = len(u), sum(u)/len(u), sum(error)/len(error)
    auto = [sum((error[k]-em)*(error[k-lag]-em) for k in range(lag, n))/n for lag in range(maxlag+1)]
    cross = [sum((u[k-lag]-um)*(error[k]-em) for k in range(lag, n))/n for lag in range(maxlag+1)]
    return {'residual_mean': em, 'residual_covariance': auto, 'input_residual_covariance': cross,
            'denominator': n, 'lag_range': [0, maxlag], 'not_a_whiteness_proof': True}


def ar_predictions(theta, observed, inputs, start, free_initial=None):
    if len(theta) != 2 or len(observed) != len(inputs) or not 1 <= start < len(observed):
        raise ValueError('two-parameter aligned ARX history required')
    a, b = theta
    one = [a*observed[k-1]+b*inputs[k-1] for k in range(start, len(observed))]
    free, state = [], observed[start-1] if free_initial is None else free_initial
    for k in range(start, len(observed)):
        state = a*state+b*inputs[k-1]
        free.append(state)
    return {'one_step': one, 'free_run': free}


def experiments():
    rng = random.Random(180000)
    N = 4096
    u = [rng.choice([-1., 1.]) for _ in range(N)]
    y = [.5*u[k]-.25*(u[k-1] if k else 0.)+.05*rng.gauss(0, 1) for k in range(N)]
    ranges = {'train': (3, 1024), 'validation': (1024, 2048), 'test': (2048, 4096)}
    candidates = []
    for order in [1, 2, 3]:
        rows = [[u[k-j] for j in range(order)] for k in range(*ranges['train'])]
        estimated = batch(rows, y[ranges['train'][0]:ranges['train'][1]], prior=1e-6)
        val = [dot(estimated['theta'], [u[k-j] for j in range(order)]) for k in range(*ranges['validation'])]
        candidates.append({'order': order, 'fit': estimated,
                           'validation_mse': mse(y[1024:2048], val)})
    selected = min(candidates, key=lambda row: row['validation_mse'])
    order, theta = selected['order'], selected['fit']['theta']
    predictions = [dot(theta, [u[k-j] for j in range(order)]) for k in range(2048, 4096)]
    residual = [a-b for a, b in zip(y[2048:], predictions)]
    fir = {'splits': ranges, 'candidates': candidates, 'selected_order': order,
           'frozen_test_mse': mse(y[2048:], predictions), 'diagnostics': diagnostics(u[2048:], residual)}
    # Same physical x and external u; only the observation noise path changes.
    rng = random.Random(180100)
    ua = [rng.choice([-1., 1.]) for _ in range(6400)]
    state, physical, measured = 0., [], []
    for k in range(6400):
        state = .5*state+.25*(ua[k-1] if k else 0.)+math.sqrt(.75)*rng.gauss(0, 1)
        physical.append(state)
        measured.append(state+.5*rng.gauss(0, 1))
    ar = {}
    for name, obs in [('ideal_observation', physical), ('output_measurement_noise', measured)]:
        train_rows = [[obs[k-1], ua[k-1]] for k in range(256, 2304)]
        fit = batch(train_rows, obs[256:2304], prior=1e-6)
        a, b = fit['theta']
        predicted = ar_predictions([a, b], obs, ua, 2304)
        one, free = predicted['one_step'], predicted['free_run']
        effective = [obs[k]-.5*obs[k-1]-.25*ua[k-1] for k in range(2304, 6400)]
        ar[name] = {'fit': fit, 'one_step_mse': mse(obs[2304:], one), 'free_run_mse': mse(obs[2304:], free),
                    # Physical lag 0 pairs u[k] with e[k]. The predictor uses
                    # u[k-1], which appears at diagnostic lag 1, not lag 0.
                    'diagnostics': diagnostics(ua[2304:6400], [obs[k]-one[k-2304] for k in range(2304, 6400)]),
                    'lagged_output_times_true_error_mean': sum(obs[k-1]*effective[k-2304] for k in range(2304, 6400))/4096,
                    'true_error_covariance_prediction': 0. if name == 'ideal_observation' else -.125,
                    'population_a_prediction': .5 if name == 'ideal_observation' else 13/32}
    rng = random.Random(180200)
    ud = [rng.choice([-1., 1.]) for _ in range(2048)]
    hd = [.5 if k < 1024 else .5+.3*(k-1024)/1023 for k in range(2048)]
    yd = [hd[k]*ud[k]-.25*(ud[k-1] if k else 0.)+.05*rng.gauss(0, 1) for k in range(2048)]
    rowsd = [[ud[k], ud[k-1]] for k in range(1, 2048)]
    drift = {'RLS_lambda_1': rls(rowsd, yd[1:], lam=1.),
             'RLS_lambda_098': rls(rowsd, yd[1:], lam=.98), 'LMS_mu_002': lms(rowsd, yd[1:])}
    # Independent later validation at the final frozen physical parameters.
    rng = random.Random(180300)
    uh = [rng.choice([-1., 1.]) for _ in range(1024)]
    yh = [.8*uh[k]-.25*(uh[k-1] if k else 0.)+.05*rng.gauss(0, 1) for k in range(1024)]
    for result in drift.values():
        result['later_independent_mse'] = mse(yh[1:], [dot(result['theta'], [uh[k], uh[k-1]]) for k in range(1, 1024)])
    short_rows, short_y = [[1., 0.], [0., 1.], [1., 1.]], [.5, -.25, .25]
    short = {str(lam): {'batch': batch(short_rows, short_y, lam=lam, prior=1.),
                        'rls': rls(short_rows, short_y, lam=lam, prior=1.)} for lam in [1., .5]}
    report = {'fixed_seeds': [180000, 180100, 180200, 180300],
              'units': 'normalized by 1 V; parameters are dimensionless',
              'fir_order_validation': fir, 'same_physical_AR_two_noise_paths': ar,
              'AR_splits': {'burn': [0, 256], 'train': [256, 2304], 'test': [2304, 6400]},
              'drift': drift, 'short_batch_RLS': short,
              'not_certified': ['real device parameter', 'closed-loop stability', 'all LMS steps', 'real noise whiteness']}
    data = {'fir': zip(range(N), u, y),
            'ar': zip(range(6400), ua, physical, measured),
            'drift': zip(range(2048), ud, yd, hd),
            'later_validation': zip(range(1024), uh, yh)}
    return report, data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report, data = experiments()
    headers = {'fir': ['k', 'u', 'y'], 'ar': ['k', 'u', 'x', 'y_measured'],
               'drift': ['k', 'u', 'y', 'h0_true'], 'later_validation': ['k', 'u', 'y']}
    for name, rows in data.items():
        with (args.output/(name+'.csv')).open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(headers[name])
            writer.writerows(rows)
    (args.output/'results.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.output), 'selected_order': report['fir_order_validation']['selected_order'],
                      'AR': report['same_physical_AR_two_noise_paths']}, allow_nan=False))


if __name__ == '__main__':
    main()
