"""Fixed AR(1) model: analytic predictions, separate fit/test and PSD repeats.
Standard library only. A report records observations; it is not a theorem or
real sensor certification. All means in this constructed model are known zero.
"""
import argparse
import cmath
import csv
import json
import math
from pathlib import Path
import random
import statistics


def solve(matrix, rhs):
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError('nonempty square system required')
    a = [[float(v) for v in row]+[float(y)] for row, y in zip(matrix, rhs)]
    if any(not math.isfinite(v) for row in a for v in row):
        raise ValueError('finite values required')
    for j in range(n):
        k = max(range(j, n), key=lambda i: abs(a[i][j]))
        if abs(a[k][j]) < 1e-12:
            raise ValueError('singular or unresolved numerical pivot')
        a[j], a[k] = a[k], a[j]
        pivot = a[j][j]
        a[j] = [v/pivot for v in a[j]]
        for i in range(n):
            if i != j:
                factor = a[i][j]
                a[i] = [x-factor*y for x, y in zip(a[i], a[j])]
    return [row[-1] for row in a]


def fit(rows, target):
    if not rows or len(rows) != len(target):
        raise ValueError('aligned nonempty rows and targets required')
    m = len(rows[0])
    if m == 0 or any(len(row) != m for row in rows):
        raise ValueError('consistent feature shape required')
    n = len(rows)
    R = [[sum(row[i]*row[j] for row in rows)/n for j in range(m)] for i in range(m)]
    p = [sum(row[i]*d for row, d in zip(rows, target))/n for i in range(m)]
    return {'weights': solve(R, p), 'R': R, 'p': p, 'known_mean': 0.}


def model(seed, size, rho_v=0.):
    if not isinstance(size, int) or isinstance(size, bool) or size < 2:
        raise ValueError('size integer >= 2 required')
    if not math.isfinite(rho_v) or abs(rho_v) >= 1:
        raise ValueError('stationary noise coefficient required')
    rng = random.Random(seed)
    state, noise = rng.gauss(0, 1), rng.gauss(0, 1)
    signal, observed = [], []
    for _ in range(size):
        state = .5*state+math.sqrt(.75)*rng.gauss(0, 1)
        noise = rho_v*noise+math.sqrt(1-rho_v*rho_v)*rng.gauss(0, 1)
        signal.append(state)
        observed.append(state+noise)
    return signal, observed


def loss(actual, predicted):
    if not actual or len(actual) != len(predicted):
        raise ValueError('aligned nonempty sequences required')
    return sum((a-b)**2 for a, b in zip(actual, predicted))/len(actual)


def causal_filter(x):
    r, gain = 2-math.sqrt(3), 2*math.sqrt(3)-3
    result, state = [], 0.
    for value in x:
        state = r*state+gain*value
        result.append(state)
    return result


def summarize(values):
    return {'mean': statistics.mean(values),
            'sample_std': statistics.stdev(values) if len(values) > 1 else None,
            'repetitions': len(values), 'values': values}


def experiments(repeats=16, train_size=4096, test_size=8192):
    if any(not isinstance(v, int) or isinstance(v, bool) for v in [repeats, train_size, test_size]):
        raise ValueError('integer resource sizes required')
    if not 1 <= repeats <= 64 or not 128 <= train_size <= 32768 or not 256 <= test_size <= 32768:
        raise ValueError('fixed lightweight experiment size range exceeded')
    r, root = 2-math.sqrt(3), math.sqrt(3)/4
    metrics = {name: [] for name in ['current', 'two_tap_theory', 'two_tap_fit',
                                    'three_tap_smoothing', 'causal_infinite',
                                    'bilateral_truncated', 'wrong_noise_old_weights',
                                    'correlated_noise_current']}
    moments = {name: [] for name in metrics}
    fits, first = [], None
    for rep in range(repeats):
        s_train, x_train = model(179000+rep, train_size)
        fitted = fit([[x_train[n], x_train[n-1]] for n in range(1, train_size)], s_train[1:])
        fits.append(fitted)
        s, x = model(179100+rep, test_size)
        z = causal_filter(x)
        times = range(128, test_size-32)
        truth = [s[n] for n in times]
        estimates = {
            'current': [.5*x[n] for n in times],
            'two_tap_theory': [(7*x[n]+2*x[n-1])/15 for n in times],
            'two_tap_fit': [sum(w*x[n-j] for j, w in enumerate(fitted['weights'])) for n in times],
            'three_tap_smoothing': [(x[n-1]+x[n+1])/8+7*x[n]/16 for n in times],
            'causal_infinite': [z[n] for n in times],
            'bilateral_truncated': [sum(root*r**abs(k)*x[n-k] for k in range(-32, 33)) for n in times]}
        for name, estimate in estimates.items():
            metrics[name].append(loss(truth, estimate))
            error = [a-b for a, b in zip(truth, estimate)]
            moments[name].append({'mean_error': sum(error)/len(error),
                'error_observation_moments': {
                    str(lag): sum(e*x[n-lag] for e, n in zip(error, times))/len(error)
                    for lag in [-1, 0, 1]}})
        sc, xc = model(179200+rep, test_size, rho_v=.5)
        changed_estimates = {
            'wrong_noise_old_weights': [(7*xc[n]+2*xc[n-1])/15 for n in range(1, test_size)],
            'correlated_noise_current': [.5*v for v in xc[1:]]}
        for name, estimate in changed_estimates.items():
            metrics[name].append(loss(sc[1:], estimate))
            error = [a-b for a, b in zip(sc[1:], estimate)]
            moments[name].append({'mean_error': sum(error)/len(error),
                'error_observation_moments': {
                    str(lag): sum(e*xc[n-lag] for e, n in zip(error, range(1, test_size)))/len(error)
                    for lag in [0, 1]}})
        if rep == 0:
            first = {'train': (s_train, x_train), 'test': (s, x),
                     'correlated_test': (sc, xc), 'test_times': list(times), 'estimates': estimates}
    # White Gaussian, rectangular window, internal bin: relative Var = 1,
    # independent K-segment average: relative Var = 1/K (not overlapping Welch).
    rng = random.Random(179300)
    groups = []
    N, bin_number, K = 64, 5, 8
    basis = [cmath.exp(-2j*math.pi*bin_number*n/N) for n in range(N)]
    for _ in range(128):
        groups.append([abs(sum(rng.gauss(0, 1)*phase for phase in basis))**2/N for _ in range(K)])
    singles, averages = [g[0] for g in groups], [sum(g)/K for g in groups]
    result = {'object': 'stationary AR1 latent voltage plus independent measurement noise',
              'units': {'samples': 'V', 'mse': 'V^2', 'time': 'sample index'},
              'fixed_inputs': {'repeats': repeats, 'train': train_size, 'test': test_size,
                               'seeds': [179000, 179100, 179200, 179300], 'bilateral_radius': 32,
                               'evaluation_start': 128, 'evaluation_stop': test_size-32},
              'analytic_predictions': {'current': .5, 'two_tap_theory': 7/15,
                                       'three_tap_smoothing': 7/16, 'causal_infinite': 2*math.sqrt(3)-3,
                                       'bilateral_infinite': root, 'wrong_noise_old_weights': 119/225,
                                       'correlated_noise_current': .5},
              'fits': fits, 'observed_mse': {name: summarize(v) for name, v in metrics.items()},
              'observed_error_moments': moments,
              'moment_convention': 'known zero model means; mean e*x[n-lag]; negative lag is future',
              'wrong_noise_moment_predictions': {'0': -1/15, '1': -7/30},
              'psd_independent_segments': {'N': N, 'bin': bin_number, 'K': K, 'groups': 128,
                   'segment_periodograms': groups,
                   'theory_mean': 1., 'theory_single_variance': 1., 'theory_average_variance': 1/K,
                   'single': summarize(singles), 'averages': summarize(averages),
                   'single_sample_variance': statistics.variance(singles),
                   'average_sample_variance': statistics.variance(averages)},
              'not_certified': ['real noise stationarity', 'ergodicity of sensor', 'hardware', 'human understanding']}
    return result, first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=16)
    parser.add_argument('--train', type=int, default=4096)
    parser.add_argument('--test', type=int, default=8192)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result, first = experiments(args.repeats, args.train, args.test)
    for name in ['train', 'test', 'correlated_test']:
        signal, observed = first[name]
        with (args.output/(name+'.csv')).open('w', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['n', 's_V', 'x_V'])
            writer.writerows((n, a, b) for n, (a, b) in enumerate(zip(signal, observed)))
    with (args.output/'estimates.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        names = list(first['estimates'])
        writer.writerow(['n']+names)
        writer.writerows([n]+[first['estimates'][key][i] for key in names] for i, n in enumerate(first['test_times']))
    (args.output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'output': str(args.output), 'observed_mse': result['observed_mse']}, allow_nan=False))


if __name__ == '__main__':
    main()
