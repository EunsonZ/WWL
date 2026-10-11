#!/usr/bin/env python3
"""Exact finite Bernoulli retraining laws and SVG; standard library, no simulation.

All published moments and plot coordinates consume the same enumerated laws.
The script is a calculator, not an independent proof checker.
"""
import argparse
from collections import defaultdict
import csv
from fractions import Fraction as F
from html import escape
import json
from math import comb, lcm
from pathlib import Path
import sys


def read_input(path):
    def unique(pairs):
        d = {}
        for key, value in pairs:
            if key in d:
                raise ValueError('duplicate input key')
            d[key] = value
        return d
    def integer(x, low, high):
        if type(x) is not int or not low <= x <= high:
            raise ValueError(f'expected integer in {low}..{high}')
        return x
    cfg = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite input')))
    keys = {'theta0', 'steps', 'snapshot_steps', 'fixed_batch_sizes', 'threshold', 'growth_first_batch'}
    if type(cfg) is not dict or set(cfg) != keys:
        raise ValueError('input keys differ from the six documented fields')
    if type(cfg['theta0']) is not str or len(cfg['theta0']) > 32:
        raise ValueError('theta0 must be a short rational string')
    theta0 = F(cfg['theta0'])
    if not 0 <= theta0 <= 1 or theta0.denominator > 1024:
        raise ValueError('theta0 outside [0,1] or denominator exceeds 1024')
    steps = integer(cfg['steps'], 1, 8)
    if type(cfg['snapshot_steps']) is not list or not cfg['snapshot_steps']:
        raise ValueError('snapshot_steps must be nonempty list')
    snapshots = [integer(t, 1, steps) for t in cfg['snapshot_steps']]
    if snapshots != sorted(set(snapshots)):
        raise ValueError('snapshot_steps must be increasing and distinct')
    if type(cfg['fixed_batch_sizes']) is not list or not cfg['fixed_batch_sizes']:
        raise ValueError('fixed_batch_sizes must be nonempty list')
    ms = [integer(m, 1, 8) for m in cfg['fixed_batch_sizes']]
    if ms != sorted(set(ms)) or 1 not in ms:
        raise ValueError('fixed_batch_sizes must be increasing, distinct, and contain 1')
    integer(cfg['growth_first_batch'], 1, 4)
    if type(cfg['threshold']) is not str or len(cfg['threshold']) > 32:
        raise ValueError('threshold must be a short rational string')
    threshold = F(cfg['threshold'])
    if not 0 < threshold < F(1, 2):
        raise ValueError('threshold must lie strictly between 0 and 1/2')
    return cfg, theta0, threshold


def new_batch_laws(theta0, batches):
    """Integer counts on a common rational grid, with total 2**draws."""
    counts = {theta0.numerator: 1}
    grid_den = theta0.denominator
    total = 1
    yield [(theta0, F(1))]
    for m in batches:
        new_den = lcm(2 * grid_den, 2 * m)
        old_scale = new_den // (2 * grid_den)
        innovation_scale = new_den // (2 * m)
        choices = [(k * innovation_scale, comb(m, k)) for k in range(m + 1)]
        nxt = defaultdict(int)
        for old, count in counts.items():
            for increment, multiplicity in choices:
                nxt[old * old_scale + increment] += count * multiplicity
        counts, grid_den, total = dict(nxt), new_den, total * (2 ** m)
        yield [(F(k, grid_den), F(n, total)) for k, n in sorted(counts.items())]


def reused_laws(theta0, m, steps, frozen=False):
    yield [(theta0, F(1))]
    for t in range(1, steps + 1):
        points = []
        for k in range(m + 1):
            c = F(k, m)
            theta = (theta0 + c) / 2 if frozen else theta0 / (2 ** t) + (1 - F(1, 2 ** t)) * c
            points.append((theta, F(comb(m, k), 2 ** m)))
        yield points


def measures(law, threshold):
    mu = sum((x * p for x, p in law), F(0))
    var = sum(((x - mu) ** 2 * p for x, p in law), F(0))
    mse = sum(((x - F(1, 2)) ** 2 * p for x, p in law), F(0))
    # Enumerate an independent fresh deployment B, not the old training sample.
    risk = sum((p / 2 * (x - (x / 2 + F(b, 2))) ** 2
                for x, p in law for b in (0, 1)), F(0))
    tail = sum((p for x, p in law if abs(x - F(1, 2)) > threshold), F(0))
    return {'mean': mu, 'variance': var, 'mse_to_half': mse,
            'fresh_deployment_risk': risk, 'tail_probability': tail,
            'total_mass': sum((p for x, p in law), F(0)), 'support_count': len(law)}


def svg(laws, rows, snapshots):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="650" viewBox="0 0 1060 650" role="img" aria-labelledby="title desc">',
           '<title id="title">Exact finite batch retraining: atoms, mean, and variance</title>',
           '<desc id="desc">Four panels show exact probability masses at selected rounds. Two lower panels show the ensemble mean and parameter variance of the same m=1 process. The horizontal dashed lines are the population fixed point one half and limiting variance one twelfth. These are not sample paths or confidence intervals.</desc>',
           '<rect width="1060" height="650" fill="#fff"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#172033} .axis{stroke:#384357;stroke-width:1} .grid{stroke:#e4e8ee;stroke-width:1} .atom{stroke:#007e91;stroke-width:1} .limit{stroke:#9b3e18;stroke-width:2;stroke-dasharray:7 5}</style>']
    def text(x, y, s, size=14, anchor='start'):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(s)}</text>')
    def line(x1, y1, x2, y2, cls):
        out.append(f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}" class="{cls}"/>')
    text(30, 30, 'Same exact law: the mean settles, the parameter distribution does not', 20)
    text(30, 55, 'm=1; theta0=' + str(laws[0][0][0]) + '; new independent fair Bernoulli every round', 15)
    # Each atom panel has its own labeled mass scale; density is not plotted as mass.
    for i, t in enumerate(snapshots):
        col, row = i % 4, i // 4
        if row:
            raise ValueError('SVG supports at most four selected snapshots')
        x0, y0, w, h = 55 + col * 250, 120, 205, 150
        law = laws[t]
        ymax = float(max(p for _, p in law)) * 1.2
        fx = lambda x: x0 + w * float(x)
        fy = lambda y: y0 + h * (1 - float(y) / ymax)
        text(x0, y0 - 28, f't={t}: {len(law)} atoms', 15)
        text(x0, y0 - 10, 'vertical axis: point probability', 12)
        for value in (0, F(1, 2), 1):
            line(fx(value), y0, fx(value), y0 + h, 'grid')
            text(fx(value), y0 + h + 20, str(value), 12, 'middle')
        peak = max(p for _, p in law)
        text(x0 - 8, fy(peak) + 4, str(peak), 11, 'end')
        text(x0 - 8, y0 + h + 4, '0', 11, 'end')
        for x, p in law:
            line(fx(x), fy(0), fx(x), fy(p), 'atom')
        line(fx(F(1, 2)), y0, fx(F(1, 2)), y0 + h, 'limit')
        line(x0, y0 + h, x0 + w, y0 + h, 'axis')
        line(x0, y0, x0, y0 + h, 'axis')
        text(x0 + w / 2, y0 + h + 43, 'parameter theta (dimensionless)', 12, 'middle')
    steps = len(laws) - 1
    # All legal initial means are in [0,1]; keep the default scale when possible.
    mean_ylim = 1.1 if max(row['mean'] for row in rows) > F(1, 2) else .6
    for index, (key, ylim, title, limiting, label) in enumerate([
            ('mean', mean_ylim, 'Ensemble mean, not one trajectory', F(1, 2), 'mean: parameter units'),
            ('variance', .10, 'Parameter variance, not a mean confidence interval', F(1, 12), 'variance: parameter units squared')]):
        x0, y0, w, h = 75 + index * 510, 415, 415, 150
        fx = lambda t: x0 + w * t / steps
        fy = lambda v: y0 + h * (1 - float(v) / ylim)
        text(x0, y0 - 37, title, 15)
        text(x0, y0 - 17, label, 13)
        y_ticks = ((0, .5, 1) if mean_ylim > .6 else (0, .25, .5)) if key == 'mean' else (0, .04, .08)
        for v in y_ticks:
            line(x0, fy(v), x0 + w, fy(v), 'grid')
            text(x0 - 10, fy(v) + 4, f'{v:g}', 12, 'end')
        for t in range(steps + 1):
            text(fx(t), y0 + h + 20, str(t), 12, 'middle')
        line(x0, fy(limiting), x0 + w, fy(limiting), 'limit')
        text(x0 + w, fy(limiting) - 6, 'limit=' + str(limiting), 12, 'end')
        pts = ' '.join(f'{fx(t):.4f},{fy(rows[t][key]):.4f}' for t in range(steps + 1))
        out.append(f'<polyline points="{pts}" fill="none" stroke="#007e91" stroke-width="2.5"/>')
        for t in range(steps + 1):
            out.append(f'<circle cx="{fx(t):.4f}" cy="{fy(rows[t][key]):.4f}" r="3.2" fill="#007e91"/>')
        line(x0, y0 + h, x0 + w, y0 + h, 'axis')
        line(x0, y0, x0, y0 + h, 'axis')
        text(x0 + w / 2, y0 + h + 45, 'completed retraining rounds t', 13, 'middle')
    text(30, 635, 'Top: discrete probability mass. Bottom: exact moments. Dashed lines: population fixed point / limiting variance.', 13)
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument('--input', type=Path, default=here / 'input.json')
    parser.add_argument('--output', type=Path, default=here / 'results')
    args = parser.parse_args()
    cfg, theta0, threshold = read_input(args.input)
    if len(cfg['snapshot_steps']) > 4:
        raise ValueError('at most four snapshots for this figure')
    if args.output.exists():
        raise ValueError('output directory already exists; choose a new path')
    steps = cfg['steps']
    scenarios = {}
    for m in cfg['fixed_batch_sizes']:
        batches = [m] * steps
        scenarios[f'new_fixed_m{m}'] = (list(new_batch_laws(theta0, batches)), batches)
        scenarios[f'reused_bits_m{m}'] = (list(reused_laws(theta0, m, steps)), [m] + [0] * (steps - 1))
        scenarios[f'frozen_observations_m{m}'] = (list(reused_laws(theta0, m, steps, frozen=True)), [m] + [0] * (steps - 1))
    growing = [cfg['growth_first_batch'] * (2 ** t) for t in range(steps)]
    scenarios['new_growing_batch'] = (list(new_batch_laws(theta0, growing)), growing)
    rows = []
    report = {'schema': 'wwl-finite-batch-retraining-v1', 'input': cfg,
              'method': 'enumerate exact Bernoulli counts; no Monte Carlo or real deployment',
              'risk': 'independent fresh B at the current deployed parameter', 'scenarios': {}}
    for name, (laws, batches) in scenarios.items():
        result = []
        for t, law in enumerate(laws):
            q = measures(law, threshold)
            row = {'scenario': name, 't': t, 'new_draws_this_update': batches[t - 1] if t else 0, **q}
            rows.append(row)
            result.append({k: str(v) if isinstance(v, F) else v for k, v in row.items()})
        report['scenarios'][name] = result
    base_laws = scenarios['new_fixed_m1'][0]
    base_rows = [measures(law, threshold) for law in base_laws]
    graphic = svg(base_laws, base_rows, cfg['snapshot_steps'])
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / 'moments.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.output / 'atoms.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['scenario', 't', 'theta', 'probability'])
        for t in cfg['snapshot_steps']:
            writer.writerows(('new_fixed_m1', t, x, p) for x, p in base_laws[t])
    (args.output / 'metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'batch-retrain.svg').write_text(graphic, encoding='utf-8')
    print(f'exact calculation wrote {len(rows)} moment rows and {sum(len(base_laws[t]) for t in cfg["snapshot_steps"])} selected atoms to {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ZeroDivisionError, json.JSONDecodeError) as exc:
        print(f'refused: {exc}', file=sys.stderr)
        sys.exit(2)
