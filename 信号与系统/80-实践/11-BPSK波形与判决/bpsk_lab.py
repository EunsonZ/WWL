#!/usr/bin/env python3
"""Finite real BPSK cell-average model. Python standard library only.

Physical amplitude coordinates use dt-weighted inner products; WGN cell averages
have covariance N0/(2*dt) I. Coarse cells average the SAME fine-cell realization.
This is not a point-sampled ADC or synchronization simulation.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate(c):
    keys = {'Eb_J', 'N0_J', 'T_s', 'grids', 'seeds', 'pi_plus',
            'n_symbols', 'fixed_noise_sqrtW'}
    require(type(c) is dict and set(c) == keys, 'unexpected/missing input fields')
    for key in ('Eb_J', 'N0_J', 'T_s'):
        require(number(c[key]) and 1e-15 <= c[key] <= 1, key + ' outside budget')
    require(0.1 <= c['Eb_J'] / c['N0_J'] <= 100, 'Eb/N0 outside budget')
    grids = c['grids']
    require(type(grids) is list and len(grids) == 2, 'two grids required')
    require(all(type(x) is int and 2 <= x <= 64 for x in grids), 'bad grid')
    require(grids[0] < grids[1] and grids[1] % grids[0] == 0,
            'grids must be increasing and nested')
    seeds = c['seeds']
    require(type(seeds) is list and 1 <= len(seeds) <= 4, 'bad seeds')
    require(all(type(x) is int and 0 <= x < 2**32 for x in seeds)
            and len(set(seeds)) == len(seeds), 'seeds must be distinct uint32')
    priors = c['pi_plus']
    require(type(priors) is list and 1 <= len(priors) <= 4, 'bad priors')
    require(all(number(x) and 0.05 <= x <= 0.95 for x in priors)
            and len(set(priors)) == len(priors), 'bad/duplicate prior')
    derived_seeds = [seed + j*1000000007
                     for j in range(len(priors)) for seed in seeds]
    require(len(set(derived_seeds)) == len(derived_seeds),
            'derived seeds collide across priors')
    count = c['n_symbols']
    require(type(count) is int and 10000 <= count <= 100000, 'bad symbol count')
    require(count * len(seeds) * len(priors) <= 800000, 'symbol budget exceeded')
    fixed = c['fixed_noise_sqrtW']
    require(type(fixed) is list and len(fixed) == grids[-1], 'fixed vector width')
    require(all(number(x) and abs(x) <= 1 for x in fixed), 'bad fixed vector')
    return c


def inner_amplitude(r, p, dt):
    require(len(r) == len(p) and len(r) > 0 and dt > 0, 'bad inner product')
    return dt * math.fsum(x * y for x, y in zip(r, p))


def coarsen(fine, grid):
    require(type(grid) is int and grid > 0 and len(fine) % grid == 0,
            'non-nested cells')
    width = len(fine) // grid
    return [math.fsum(fine[i:i + width]) / width
            for i in range(0, len(fine), width)]


def threshold(eb, n0, prior):
    require(eb > 0 and n0 > 0 and 0 < prior < 1, 'invalid density parameters')
    return n0 / (4 * math.sqrt(eb)) * math.log((1 - prior) / prior)


def q(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def theory(eb, n0, prior):
    a, sigma = math.sqrt(eb), math.sqrt(n0 / 2)
    gamma = threshold(eb, n0, prior)
    pp, pm = q((a - gamma) / sigma), q((a + gamma) / sigma)
    return {'threshold_sqrtJ': gamma, 'p_error_given_plus': pp,
            'p_error_given_minus': pm, 'p_error': prior * pp + (1 - prior) * pm}


def fixed_vectors(c):
    eb, n0, T = c['Eb_J'], c['N0_J'], c['T_s']
    a = math.sqrt(eb)
    fixed = c['fixed_noise_sqrtW']
    rows, checks = [], []
    for L in c['grids']:
        dt = T / L
        p = [1 / math.sqrt(T)] * L
        noise = coarsen(fixed, L)
        received = [a * z + w for z, w in zip(p, noise)]
        y = inner_amplitude(received, p, dt)
        signal_energy = inner_amplitude([a * z for z in p], [a * z for z in p], dt)
        var = dt**2 * math.fsum(z*z * n0 / (2*dt) for z in p)
        checks.append({'grid': L, 'dt_s': dt, 'fs_Hz': L / T,
                       'pulse_energy': inner_amplitude(p, p, dt),
                       'signal_energy_J': signal_energy,
                       'cell_noise_variance_W': n0 / (2*dt),
                       'projected_noise_variance_J': var,
                       'fixed_y_sqrtJ': y,
                       'wrong_fixed_cell_variance_W': 0.001,
                       'wrong_projected_variance_J': 0.001*T/L})
        for i, (pi, ni, ri) in enumerate(zip(p, noise, received)):
            rows.append([L, i, i*dt, (i+1)*dt, pi, a*pi, ni, ri])
    for row in checks:
        require(math.isclose(row['pulse_energy'], 1, abs_tol=1e-12), 'pulse energy')
        require(math.isclose(row['signal_energy_J'], eb, rel_tol=1e-12), 'signal energy')
        require(math.isclose(row['projected_noise_variance_J'], n0/2, rel_tol=1e-12),
                'projected covariance')
    require(math.isclose(checks[0]['fixed_y_sqrtJ'], checks[1]['fixed_y_sqrtJ'],
                         abs_tol=1e-12*a), 'fixed physical integral drift')
    return checks, rows


def mc_pair(c, seed, prior):
    """Generate high-resolution cells once; average for all nested grids.

    Seed identifies an independent RNG per prior. Within a pair, common random
    numbers make the grid invariant test exact, not a second independent trial.
    """
    rng = random.Random(seed)
    eb, n0, T = c['Eb_J'], c['N0_J'], c['T_s']
    hi, count = c['grids'][-1], c['n_symbols']
    dt_hi = T / hi
    a, p0 = math.sqrt(eb), 1 / math.sqrt(T)
    cell_sigma = math.sqrt(n0 / (2*dt_hi))
    target = theory(eb, n0, prior)
    gamma = target['threshold_sqrtJ']
    counts = {'plus': 0, 'minus': 0}
    errors = {L: {'plus': 0, 'minus': 0, 'zero_threshold': 0} for L in c['grids']}
    sumw = sumw2 = max_gap = sum0 = sum1 = sum01 = 0.0
    for _ in range(count):
        sign = 1 if rng.random() < prior else -1
        label = 'plus' if sign == 1 else 'minus'
        counts[label] += 1
        fine = [rng.gauss(0.0, cell_sigma) for _ in range(hi)]
        sum0 += fine[0]
        sum1 += fine[1]
        sum01 += fine[0] * fine[1]
        ys = []
        for L in c['grids']:
            noise = fine if L == hi else coarsen(fine, L)
            # Integrate amplitude samples. No dt-free array norm is used.
            y = (T / L) * math.fsum((sign*a*p0 + z)*p0 for z in noise)
            ys.append(y)
            errors[L][label] += (1 if y > gamma else -1) != sign
            errors[L]['zero_threshold'] += (1 if y > 0 else -1) != sign
        max_gap = max(max_gap, abs(ys[0] - ys[1]))
        w = ys[-1] - sign*a
        sumw += w
        sumw2 += w*w
    mean_w = sumw / count
    var_w = sumw2 / count - mean_w**2
    cross = sum01 / count - (sum0 / count) * (sum1 / count)
    noise_var = n0/2
    # Prespecified six-sigma diagnostic envelopes, not distribution-free guarantees.
    require(abs(mean_w) <= 6*math.sqrt(noise_var/count), 'MC noise mean')
    require(abs(var_w-noise_var) <= 6*noise_var*math.sqrt(2/count), 'MC projected variance')
    require(abs(cross) <= 6*cell_sigma**2/math.sqrt(count), 'MC adjacent-cell covariance')
    require(max_gap <= 1e-12*a, 'paired grid statistic mismatch')
    require(errors[c['grids'][0]] == errors[c['grids'][1]], 'paired grid decision mismatch')
    results = []
    for L in c['grids']:
        e = errors[L]
        row = {'seed': seed, 'pi_plus': prior, 'grid': L, 'n': count,
               'n_plus': counts['plus'], 'n_minus': counts['minus'],
               'errors_plus': e['plus'], 'errors_minus': e['minus'],
               'errors': e['plus'] + e['minus'],
               'ber': (e['plus'] + e['minus']) / count,
               'ber_plus': e['plus'] / counts['plus'],
               'ber_minus': e['minus'] / counts['minus'],
               'zero_threshold_errors': e['zero_threshold'],
               'zero_threshold_ber': e['zero_threshold']/count,
               'noise_mean_sqrtJ': mean_w, 'noise_variance_J': var_w,
               'fine_adjacent_noise_cov_W': cross, 'max_paired_y_gap_sqrtJ': max_gap,
               **target}
        for name, n, prob, observed in (
            ('plus', counts['plus'], target['p_error_given_plus'], e['plus']),
            ('minus', counts['minus'], target['p_error_given_minus'], e['minus']),
            ('overall', count, target['p_error'], row['errors']),
            ('zero_threshold', count, q(a/math.sqrt(n0/2)), e['zero_threshold'])):
            tolerance = 6*math.sqrt(n*prob*(1-prob)) + 2
            row['error_count_tolerance_'+name] = tolerance
            require(abs(observed-n*prob) <= tolerance, 'MC Bernoulli envelope '+name)
        results.append(row)
    return results


def run(c, output):
    validate(c)
    # Reject existing output; failed trials do not overwrite successful evidence.
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    checks, waves = fixed_vectors(c)
    mc = []
    for j, prior in enumerate(c['pi_plus']):
        for seed in c['seeds']:
            mc.extend(mc_pair(c, seed + j*1000000007, prior))
    result = {'model': 'real-antipodal-cell-average-AWGN', 'inputs': c,
              'environment': {'python': sys.version, 'platform': platform.platform(),
                              'processes': 1, 'threads': 1,
                              'executable': sys.executable,
                              'OMP_NUM_THREADS': os.environ.get('OMP_NUM_THREADS')},
              'fixed': checks, 'theory': [theory(c['Eb_J'], c['N0_J'], p)
                                         | {'pi_plus': p} for p in c['pi_plus']],
              'mc': mc, 'elapsed_s': time.monotonic()-started,
              'checks': 'PASS', 'frame': {'payload': '1101', 'crc': '001',
              'codeword': '1101001', 'symbols': [1, 1, -1, 1, -1, -1, 1],
              'duration_s': 7*c['T_s'], 'payload_rate_bit_s': 4/(7*c['T_s']),
              'frame_energy_J': 7*c['Eb_J'], 'extra_fec_rate': 1}}
    (output/'results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    with (output/'waveform.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['grid','cell','start_s','end_s','p_inv_sqrt_s','s_sqrt_W',
                    'noise_sqrt_W','received_sqrt_W'])
        w.writerows(waves)
    with (output/'mc.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(mc[0]))
        w.writeheader()
        w.writerows(mc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        c = json.loads(args.inputs.read_text())
        result = run(c, args.output)
    except (ValueError, OSError, ZeroDivisionError) as e:
        parser.exit(2, str(e)+'\n')
    print(json.dumps({'checks': result['checks'], 'elapsed_s': result['elapsed_s'],
                      'rows': len(result['mc']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
