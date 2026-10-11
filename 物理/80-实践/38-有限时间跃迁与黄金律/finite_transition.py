#!/usr/bin/env python3
"""Finite, closed star Hamiltonian and first-order time-window comparisons.

No ODE approximation: the finite Hamiltonian uses numpy.linalg.eigh.
Frequency coordinates are rad/us, time is us, and radians are dimensionless.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import numpy as np


def sinc(x):
    """sin(x)/x, including its continuous value at zero."""
    return np.sinc(np.asarray(x) / np.pi)


def real_number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a real number')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must lie in [{low}, {high}]')
    return float(value)


def integer(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    return value


def validate(data):
    if data['time_unit'] != 'us' or data['angular_frequency_unit'] != 'rad/us':
        raise ValueError('supported units are us and rad/us')
    samples = integer(data['samples'], 21, 1001, 'samples')
    grid = integer(data['continuum_grid'], 1001, 64001, 'continuum_grid')
    if grid % 2 != 1:
        raise ValueError('continuum_grid must be odd')
    cases = data['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise ValueError('cases must contain 1..8 entries')
    seen = set()
    for c in cases:
        name = c['name']
        if not isinstance(name, str) or not name or len(name) > 40 or name in seen:
            raise ValueError('case names must be unique strings of length 1..40')
        seen.add(name)
        c['B'] = real_number(c['B'], 0.001, 20, 'B')
        c['gamma'] = real_number(c['gamma'], 0.000001, 2, 'gamma')
        c['t_max'] = real_number(c['t_max'], 0.001, 200, 't_max')
        integer(c['N'], 2, 400, 'N')
    two = data['two_state']
    two['g'] = real_number(two['g'], 0.000001, 2, 'g')
    two['t_max'] = real_number(two['t_max'], 0.001, 200, 'two_state.t_max')
    if not isinstance(two['detunings'], list) or not 1 <= len(two['detunings']) <= 4:
        raise ValueError('provide 1..4 detunings')
    two['detunings'] = [real_number(d, -20, 20, 'detuning') for d in two['detunings']]
    if not isinstance(data['kernel_times'], list) or not 1 <= len(data['kernel_times']) <= 4:
        raise ValueError('provide 1..4 kernel times')
    data['kernel_times'] = [real_number(t, 0.01, 20, 'kernel_time') for t in data['kernel_times']]
    return samples, grid


def continuum(t, B, J, grid):
    # ∫_{-B}^{B} J t² sinc²(delta*t/2) ddelta, trapezoid quadrature.
    delta = np.linspace(-B, B, grid)
    return np.array([J * ti**2 * np.trapezoid(sinc(delta * ti / 2)**2, delta)
                     for ti in t])


def star(c, samples, grid):
    B, N, gamma = c['B'], c['N'], c['gamma']
    spacing = 2 * B / N
    J = gamma / (2 * np.pi)
    g = math.sqrt(J * spacing)
    delta = -B + (np.arange(N) + 0.5) * spacing
    # Ordered basis (|i>, |1>, ..., |N>); no final-final couplings.
    H = np.diag(np.concatenate(([0.0], delta)))
    H[0, 1:] = g
    H[1:, 0] = g
    eigenvalues, Q = np.linalg.eigh(H)
    t = np.linspace(0, c['t_max'], samples)
    # Survival amplitude <i|exp(-i H t)|i> = sum_a |Q_ia|² exp(-i lambda_a t).
    weights = Q[0, :]**2
    survival = weights @ np.exp(-1j * eigenvalues[:, None] * t[None, :])
    exact = 1 - abs(survival)**2
    first = g**2 * t**2 * np.sum(sinc(delta[:, None] * t[None, :] / 2)**2, axis=0)
    cont = continuum(t, B, J, grid)
    cont_coarse = continuum(t, B, J, (grid + 1) // 2)
    golden = gamma * t
    residual = np.max(abs(H @ Q - Q * eigenvalues[None, :]))
    orthogonal = np.max(abs(Q.T @ Q - np.eye(N + 1)))
    # This finite model also gives an exact finite-dimensional norm check.
    probe_t = [0.0, c['t_max'] / 2, c['t_max']]
    norms = []
    for ti in probe_t:
        psi = Q @ (np.exp(-1j * eigenvalues * ti) * Q[0, :])
        norms.append(float(abs(np.vdot(psi, psi) - 1)))
    metrics = {
        **c, 'spacing_rad_per_us': spacing, 'J_per_us': J,
        'g_rad_per_us': g, 't_rephase_us': 2 * math.pi / spacing,
        'B_t_max': B * c['t_max'], 'gamma_t_max': gamma * c['t_max'],
        'V_norm_rad_per_us': math.sqrt(2 * B * J),
        'eigen_residual_rad_per_us': float(residual),
        'orthogonality_residual': float(orthogonal), 'norm_error_probes': max(norms),
        'continuum_refinement_max_abs': float(max(abs(cont - cont_coarse))),
        'exact_vs_first_max_abs': float(max(abs(exact - first))),
        'first_vs_continuum_max_abs': float(max(abs(first - cont))),
        'continuum_vs_golden_max_abs': float(max(abs(cont - golden))),
        'end': {k: float(v[-1]) for k, v in zip(
            ('exact', 'first_discrete', 'first_continuum', 'golden'), (exact, first, cont, golden))}}
    return t, (exact, first, cont, golden), metrics


def csv_write(path, header, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def plot(path, panels, title, desc):
    # Same arrays that are saved to CSV; no smoothing, clipping or fitting.
    w, ph, left, right, top, bottom = 940, 260, 80, 22, 45, 48
    height = ph * len(panels)
    colors = ['#175ca4', '#bc4f00', '#197548', '#75479d']
    dash = ['', '8 4', '3 3', '10 3 2 3']
    esc = html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {height}" role="img">',
           f'<title>{esc(title)}</title><desc>{esc(desc)}</desc>',
           '<rect width="100%" height="100%" fill="white"/>',
           '<style>text{font-family:Arial,sans-serif;font-size:13px;fill:#222}</style>']
    for p, (x, series, labels, subtitle, xlabel, ylabel) in enumerate(panels):
        y0, y1 = p * ph + top, (p + 1) * ph - bottom
        x0, x1 = left, w - right
        xmax = float(x[-1]); xmin = float(x[0])
        ymax = max(0.001, float(max(np.max(y) for y in series))) * 1.07
        def xx(v): return x0 + (float(v) - xmin) / (xmax - xmin) * (x1 - x0)
        def yy(v): return y1 - float(v) / ymax * (y1 - y0)
        out.append(f'<text x="{x0}" y="{p*ph+20}" font-weight="bold">{esc(subtitle)}</text>')
        for j in range(5):
            xt = xmin + (xmax - xmin) * j / 4
            out.append(f'<line x1="{xx(xt):.3f}" y1="{y0}" x2="{xx(xt):.3f}" y2="{y1}" stroke="#e5e5e5"/>')
            out.append(f'<text x="{xx(xt):.3f}" y="{y1+18}" text-anchor="middle">{xt:.4g}</text>')
            yt = ymax * j / 4
            out.append(f'<line x1="{x0}" y1="{yy(yt):.3f}" x2="{x1}" y2="{yy(yt):.3f}" stroke="#e5e5e5"/>')
            out.append(f'<text x="{x0-8}" y="{yy(yt)+4:.3f}" text-anchor="end">{yt:.3g}</text>')
        out.append(f'<path d="M{x0},{y0} V{y1} H{x1}" fill="none" stroke="#333"/>')
        out.append(f'<text x="{(x0+x1)/2}" y="{y1+38}" text-anchor="middle">{esc(xlabel)}</text>')
        out.append(f'<text transform="translate(20,{(y0+y1)/2}) rotate(-90)" text-anchor="middle">{esc(ylabel)}</text>')
        for j, (y, label) in enumerate(zip(series, labels)):
            pts = ' '.join(f'{xx(a):.3f},{yy(b):.3f}' for a, b in zip(x, y))
            out.append(f'<polyline points="{pts}" fill="none" stroke="{colors[j]}" stroke-width="2" stroke-dasharray="{dash[j]}"/>')
            lx = x0 + j * (x1 - x0) / len(series)
            out.append(f'<line x1="{lx}" y1="{y0-10}" x2="{lx+25}" y2="{y0-10}" stroke="{colors[j]}" stroke-width="2" stroke-dasharray="{dash[j]}"/>')
            out.append(f'<text x="{lx+30}" y="{y0-6}">{esc(label)}</text>')
    out.append('</svg>')
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('assets'))
    args = parser.parse_args()
    try:
        data = json.loads(args.inputs.read_text(encoding='utf-8'))
        samples, grid = validate(data)
    except (ValueError, KeyError, TypeError) as e:
        parser.error(str(e))
    args.output.mkdir(parents=True, exist_ok=True)
    all_rows, metrics, panels = [], [], []
    labels = ['exact finite', '1st discrete', '1st continuum', 'Gamma t']
    for c in data['cases']:
        t, curves, m = star(c, samples, grid)
        metrics.append(m)
        all_rows.extend((c['name'], float(ti), *(float(y[k]) for y in curves)) for k, ti in enumerate(t))
        subtitle = f"{c['name']}: B={c['B']:g} rad/us, N={c['N']}, Gamma={c['gamma']:g} /us"
        panels.append((t, curves, labels, subtitle, 'time t (us)', 'exit probability / approximation'))
    csv_write(args.output / 'band.csv', ['case', 't_us', 'exact', 'first_discrete', 'first_continuum', 'golden'], all_rows)
    plot(args.output / 'band.svg', panels, 'Finite band versus golden rule',
         'Closed finite star Hamiltonian, initial i state, sudden constant coupling. Solid exact, dashed first order; Gamma t may exceed one. All coordinates are from band.csv.')
    t = np.linspace(0, data['two_state']['t_max'], samples)
    g = data['two_state']['g']
    rows, panels = [], []
    for d in data['two_state']['detunings']:
        omega = math.hypot(d, 2 * g)
        exact = (2*g/omega)**2 * np.sin(omega*t/2)**2
        first = g**2 * t**2 * sinc(d*t/2)**2
        rows.extend((d, float(ti), float(e), float(a)) for ti,e,a in zip(t,exact,first))
        panels.append((t, (exact, first), ('exact two-state', '1st order'),
                       f'delta={d:g} rad/us, g={g:g} rad/us; closed 2-state', 'time t (us)', 'exit probability / approximation'))
    csv_write(args.output / 'two-state.csv', ['delta_rad_per_us', 't_us', 'exact', 'first'], rows)
    plot(args.output / 'two-state.svg', panels, 'Two-state secular failure',
         'Initial i; H/hbar=[[0,g],[g,delta]]. Exact analytic Rabi solution and first-order result. The resonant approximation is not a constant rate.')
    delta = np.linspace(-12, 12, 1201)
    curves = [ti/(2*np.pi)*sinc(delta*ti/2)**2 for ti in data['kernel_times']]
    csv_write(args.output / 'kernel.csv', ['delta_rad_per_us', *(f'K_t{ti:g}_us' for ti in data['kernel_times'])],
              ((float(d), *(float(y[k]) for y in curves)) for k,d in enumerate(delta)))
    plot(args.output / 'kernel.svg', [(delta, curves, [f't={ti:g} us' for ti in data['kernel_times']],
         'K_delta = t/(2 pi) sinc^2(delta t/2); integral over all delta = 1', 'detuning delta (rad/us)', 'K_delta (us)')],
         'Finite-time kernel narrows', 'Normalized angular-frequency kernel. Truncated plotting domain [-12,12] rad/us does not contain the complete kernel area. Longer time narrows the main lobe and raises its peak.')
    report = {'model': 'finite-closed-star-v1', 'inputs': data, 'cases': metrics,
              'method': 'Hermitian diagonalization for finite model; trap refinement for continuum first-order integral',
              'not_proved': ['irreversibility', 'general unbounded-Hamiltonian theorem', 'hardware validation', 'learner understanding']}
    (args.output / 'results.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'cases': len(metrics), 'outputs': 7, 'max_eigen_residual': max(m['eigen_residual_rad_per_us'] for m in metrics),
          'max_continuum_refinement': max(m['continuum_refinement_max_abs'] for m in metrics)}, allow_nan=False))


if __name__ == '__main__':
    main()
