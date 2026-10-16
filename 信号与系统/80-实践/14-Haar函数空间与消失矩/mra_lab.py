#!/usr/bin/env python3
"""Analytic finite Haar projections; reuse published analysis/synthesis, no cascade claim."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import time


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(x):
    return type(x) in (int, float) and math.isfinite(x)


def validate(c):
    require(type(c) is dict, 'input must be an object')
    levels = c.get('levels')
    require(type(levels) is list and 1 <= len(levels) <= 13 and
            all(type(j) is int and -6 <= j <= 8 for j in levels) and
            len(set(levels)) == len(levels), 'distinct integer levels in [-6,8] required')
    J = c.get('finest_level')
    require(type(J) is int and 1 <= J <= 8, 'finest_level integer in [1,8] required')
    signals = c.get('signals')
    require(type(signals) is list and 1 <= len(signals) <= 8, '1..8 signals required')
    names = []
    for s in signals:
        require(type(s) is dict and type(s.get('name')) is str and s['name'] and
                s['name'].isascii() and s['name'].replace('_', '').isalnum(), 'ASCII signal name required')
        names.append(s['name'])
        segs = s.get('segments')
        require(type(segs) is list and 1 <= len(segs) <= 16, '1..16 segments required')
        last = -math.inf
        for seg in segs:
            require(type(seg) is list and len(seg) == 3, 'segment [left,right,coefficients] required')
            a, b, p = seg
            require(number(a) and number(b) and -2 <= a < b <= 2 and a >= last,
                    'ordered disjoint segments within [-2,2] required')
            require(type(p) is list and 1 <= len(p) <= 3 and
                    all(number(v) and abs(v) <= 10000 for v in p), 'finite degree<=2 coefficients required')
            last = b
    require(len(set(names)) == len(names), 'distinct signal names required')
    n = c.get('filter_input_length')
    require(type(n) is int and 8 <= n <= 64 and n % 2 == 0, 'even filter_input_length in [8,64] required')
    degrees = c.get('polynomial_degrees')
    require(type(degrees) is list and all(type(q) is int for q in degrees) and
            degrees == [0, 1, 2], 'polynomial_degrees must be integer [0,1,2]')


def load_module(path, name):
    path = Path(path).resolve()
    require(path.is_file(), 'published source missing: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def primitive(p, a, b):
    return math.fsum(v * (b ** (r + 1) - a ** (r + 1)) / (r + 1) for r, v in enumerate(p))


def square(p):
    q = [0.] * (2 * len(p) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(p):
            q[i + j] += a * b
    return q


def integral(segs, a, b, squared=False):
    return math.fsum(primitive(square(p) if squared else p, max(a, l), min(b, r))
                     for l, r, p in segs if max(a, l) < min(b, r))


def projection(segs, j):
    width = 2. ** (-j)
    first = math.floor(segs[0][0] / width)
    stop = math.ceil(segs[-1][1] / width)
    cells = []
    for k in range(first, stop):
        a, b = k * width, (k + 1) * width
        area = integral(segs, a, b)
        c = area / math.sqrt(width)
        value = area / width
        # Direct residual integration, including uncovered zero segments.
        err = integral(segs, a, b, True) - 2 * value * area + value * value * width
        cells.append({'k': k, 'left': a, 'right': b, 'coefficient': c,
                      'value': value, 'error_squared': err})
    norm = integral(segs, segs[0][0], segs[-1][1], True)
    kept = math.fsum(t['coefficient'] ** 2 for t in cells)
    error = math.fsum(t['error_squared'] for t in cells)
    tol = 2e-11 * max(1., norm)
    require(error >= -tol and abs(norm - kept - error) < tol, 'projection energy/residual disagreement')
    return {'level': j, 'input_norm_squared': norm, 'projection_norm_squared': kept,
            'error_squared': error, 'cells': cells}


def bridge(segs, J, bank, resample):
    # Use a fixed enclosing [-2,2) dyadic block: no periodic/odd extension ambiguity.
    indices = range(-2 * 2 ** J, 2 * 2 ** J)
    width = 2. ** (-J)
    fine = [integral(segs, k * width, (k + 1) * width) / math.sqrt(width) for k in indices]
    cur = fine
    details = []
    levels = []
    largest = 0.
    for j in range(J - 1, -1, -1):
        packet = bank.analysis(cur, 'zero', resample)
        c = list(map(float, packet['a']))
        d = list(map(float, packet['d']))
        direct_c, direct_d = [], []
        for k in range(-2 * 2 ** j, 2 * 2 ** j):
            a = k * 2. ** (-j)
            mid = a + 2. ** (-j - 1)
            b = a + 2. ** (-j)
            direct_c.append(2. ** (j / 2) * integral(segs, a, b))
            direct_d.append(2. ** (j / 2) * (integral(segs, a, mid) - integral(segs, mid, b)))
        delta = max(abs(x - y) for x, y in zip(c + d, direct_c + direct_d))
        largest = max(largest, delta)
        details.append(d)
        levels.append({'level': j, 'c': c, 'd': d, 'direct_c': direct_c,
                       'direct_d': direct_d, 'max_coefficient_difference': delta})
        cur = c
    base = cur
    for d in reversed(details):
        cur = list(map(float, bank.synthesis(cur, d, resample)))
    restoration = max(abs(x - y) for x, y in zip(cur, fine))
    fine_energy = math.fsum(x*x for x in fine)
    hierarchy_energy = math.fsum(x*x for x in base) + math.fsum(x*x for d in details for x in d)
    tol = 2e-11 * max(1., math.sqrt(fine_energy))
    require(largest < tol and restoration < tol and
            abs(fine_energy - hierarchy_energy) < 2e-11 * max(1., fine_energy), 'published bridge mismatch')
    return {'coordinate_block': [-2, 2], 'finest_level': J, 'fine_coefficients': fine,
            'base_c0': base, 'levels_descending': levels,
            'max_coefficient_difference': largest, 'max_restoration_difference': restoration,
            'fine_projection_energy': fine_energy, 'hierarchy_energy': hierarchy_energy}


def filters(n, source):
    root = math.sqrt(3)
    haar = [1/math.sqrt(2)]*2
    db2 = [(1+root)/(4*math.sqrt(2)), (3+root)/(4*math.sqrt(2)),
           (3-root)/(4*math.sqrt(2)), (1-root)/(4*math.sqrt(2))]
    sparse = [1/math.sqrt(2), 0., 0., 1/math.sqrt(2)]
    reports = []
    for name, h in [('haar', haar), ('db2_mask', db2), ('sparse_qmf', sparse)]:
        g = [(-1)**r * h[len(h)-1-r] for r in range(len(h))]
        corr = {str(m): math.fsum(h[r]*h[r-2*m] for r in range(len(h)) if 0 <= r-2*m < len(h))
                for m in range(-2, 3)}
        moments = [math.fsum(r**q*g[r] for r in range(len(g))) for q in range(3)]
        polynomials = []
        for q in range(3):
            x = [float(t**q) for t in range(n)]
            all_y = list(map(float, source.offline(x, list(reversed(g)), factor=2, phase=1)))
            start = (len(g)-2)//2
            count = (n-len(g))//2+1
            direct = [math.fsum(g[r] * (2*m+r)**q for r in range(len(g))) for m in range(count)]
            interior = all_y[start:start+count]
            require(max(abs(a-b) for a,b in zip(direct, interior)) < 2e-10, 'filter correlation alignment drift')
            polynomials.append({'degree': q, 'input': x, 'full_zero_extended_output': all_y,
                                'interior_output_slice': [start, start+count],
                                'direct_interior': direct, 'source_interior': interior})
        reports.append({'name': name, 'h': h, 'g': g, 'sum_h': sum(h),
                        'even_lag_correlation': corr, 'g_discrete_moments_0_1_2': moments,
                        'polynomials': polynomials})
    return reports


def run(c, bank_path, resample_path, output):
    validate(c)
    bank = load_module(bank_path, 'wwl_published_haar')
    resample = load_module(resample_path, 'wwl_published_resample')
    start = time.perf_counter()
    rows = []
    signals = []
    for s in c['signals']:
        records = [projection(s['segments'], j) for j in c['levels']]
        b = bridge(s['segments'], c['finest_level'], bank, resample)
        signals.append({'name': s['name'], 'segments': s['segments'], 'projections': records, 'bridge': b})
        for p in records:
            rows.append([s['name'], p['level'], p['input_norm_squared'], p['projection_norm_squared'], p['error_squared']])
    report = {'model': 'dimensionless tau; analytic piecewise polynomial cell integrals; zero outside segments',
              'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                              'numpy': str(resample.np.__version__),
                              'threads': {k: os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')},
                              'published_sources': [{'path': str(Path(p).resolve()), 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                                                    for p in (bank_path, resample_path)]},
              'inputs': c, 'signals': signals, 'filters': filters(c['filter_input_length'], resample),
              'sparse_refinement': {'support': [0,3], 'height': 1/3, 'integral': 1.,
                                    'norm_squared': 1/3, 'integer_shift_1_inner_product': 2/9,
                                    'integer_shift_2_inner_product': 1/9},
              'elapsed_seconds': time.perf_counter()-start}
    output = Path(output)
    require(not output.exists(), 'output must not exist')
    output.mkdir(parents=True)
    (output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    with (output/'projections.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['signal','level','input_norm_squared','projection_norm_squared','error_squared'])
        writer.writerows(rows)
    return report


def main():
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--haar-source', type=Path, default=here/'13-Haar分析合成与边界/filterbank_lab.py')
    parser.add_argument('--resample-source', type=Path, default=here/'02-流式音频重采样/resample_lab.py')
    a = parser.parse_args()
    try:
        r = run(json.loads(a.inputs.read_text()), a.haar_source, a.resample_source, a.output)
    except (ValueError, KeyError, OSError, TypeError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps({'signals': len(r['signals']), 'projection_rows': sum(len(s['projections']) for s in r['signals']),
                      'elapsed_seconds': r['elapsed_seconds']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
