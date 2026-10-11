---
type: reference
domain: physics
stage: 2
aliases: []
sources: []
prerequisites:
  - "[[物理/80-实践/40-有限环境退相干/README]]"
---
# 有限环境退相干完整源码

代码真源为 [finite_decoherence.py](finite_decoherence.py)，输入与运行边界见 [[物理/80-实践/40-有限环境退相干/README|复算入口]]。下块按源码原字节镜像，修改实现时同步；不要把本页代码围栏作为另一个独立实现。全部曲线是定义的有限模型数值，没有真实硬件采样。

<!-- code-sync: ./finite_decoherence.py -->

```python
#!/usr/bin/env python3
"""Exact finite longitudinal-spin model and a resonant exchange counterexample.

Times: us; angular frequencies: rad/us; energy outputs: J.
The first tensor factor (system) is the slow index. NumPy is the only dependency.
No integration, fit, stochastic bath reset, or Markov equation is used.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
from pathlib import Path
import re

import numpy as np

HBAR_J_S = 6.62607015e-34 / (2 * math.pi)
ENERGY_SCALE = HBAR_J_S * 1e6  # (rad/us) times this factor gives J.
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1., -1.]).astype(complex)
COLORS = ['#185a9d', '#d06813', '#753b96', '#257548', '#a02836', '#525252',
          '#007e84', '#8c6820', '#bf5390', '#244b76', '#7c6ab5', '#46773c']
STYLES = ['', '9 4', '3 3', '10 3 2 3']


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key')
        obj[key] = value
    return obj


def keys(obj, expected, where):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f'{where}: expected keys {sorted(expected)}')


def number(x, where, limit=100.):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f'{where}: must be a finite real number')
    if abs(x) > limit or not math.isfinite(x):
        raise ValueError(f'{where}: outside finite magnitude limit {limit}')
    return float(x)


def bloch(v, where):
    if not isinstance(v, list) or len(v) != 3:
        raise ValueError(f'{where}: expected three Bloch coordinates')
    a = np.array([number(x, where, 1.) for x in v])
    if np.dot(a, a) > 1. + 1e-12:
        raise ValueError(f'{where}: Bloch norm must be at most one')
    return a


def validate(data):
    keys(data, ['units', 'samples', 't_max', 'dephasing_cases', 'exchange'], 'input')
    if data['units'] != {'time': 'us', 'angular_frequency': 'rad/us', 'energy': 'J'}:
        raise ValueError('units: require us, rad/us, J')
    n = data['samples']
    if isinstance(n, bool) or not isinstance(n, int) or not 21 <= n <= 1001:
        raise ValueError('samples: integer 21..1001')
    if not 0 < number(data['t_max'], 't_max', 1000.) <= 1000:
        raise ValueError('t_max: positive, at most 1000 us')
    cases = data['dephasing_cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 12:
        raise ValueError('dephasing_cases: require 1..12 cases')
    names = set()
    for case in cases:
        keys(case, ['name', 'omega_s', 'g', 'omega_bath', 'system_bloch', 'bath_bloch'], 'case')
        name = case['name']
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}', name) or name in names:
            raise ValueError('case.name: unique ASCII label, 1..40 characters')
        names.add(name)
        number(case['omega_s'], 'omega_s')
        g = case['g']
        if not isinstance(g, list) or not 1 <= len(g) <= 6:
            raise ValueError('g: require 1..6 spins')
        for x in g:
            number(x, 'g')
        w = case['omega_bath']
        if not isinstance(w, list) or len(w) != len(g):
            raise ValueError('omega_bath: same length as g')
        for x in w:
            number(x, 'omega_bath')
        bloch(case['system_bloch'], 'system_bloch')
        r = case['bath_bloch']
        if not isinstance(r, list) or len(r) != len(g):
            raise ValueError('bath_bloch: same length as g')
        for x in r:
            bloch(x, 'bath_bloch')
    keys(data['exchange'], ['omega', 'kappa'], 'exchange')
    if number(data['exchange']['omega'], 'exchange.omega') <= 0:
        raise ValueError('exchange.omega: positive')
    if number(data['exchange']['kappa'], 'exchange.kappa') == 0:
        raise ValueError('exchange.kappa: nonzero')
    return data


def density(v):
    return (I2 + v[0]*X + v[1]*Y + v[2]*Z) / 2


def product(items):
    out = np.ones((1, 1), dtype=complex)
    for item in items:
        out = np.kron(out, item)
    return out


def embed(local, position, count):
    return product([local if i == position else I2 for i in range(count)])


def reduced_system(rho, d):
    # rho axes: system ket, bath ket, system bra, bath bra.
    return np.trace(rho.reshape(2, d, 2, d), axis1=1, axis2=3)


def entropy_from_radius(radius):
    # Clipping is solely for endpoint roundoff in eigenvalues, never curve data.
    vals = np.clip(np.array([(1+radius)/2, (1-radius)/2]), 0., 1.)
    terms = np.zeros_like(vals)
    np.log2(vals, out=terms, where=vals > 0)
    return -np.sum(vals * terms, axis=0)


def curve(case, times):
    g = np.array(case['g'])
    rz = np.array(case['bath_bloch'])[:, 2]
    L = np.prod(np.cos(times[:, None]*g) - 1j*rz*np.sin(times[:, None]*g), axis=1)
    sx, sy, sz = case['system_bloch']
    p = (1+sz)/2
    c = (sx-1j*sy)/2
    off = c*np.exp(-1j*case['omega_s']*times)*L
    purity = p*p + (1-p)**2 + 2*np.abs(off)**2
    radius = np.sqrt(sz*sz + 4*np.abs(off)**2)
    global_purity = (1+sx*sx+sy*sy+sz*sz)/2
    for r in case['bath_bloch']:
        global_purity *= (1+sum(x*x for x in r))/2
    return {'t_us': times, 'L_re': L.real, 'L_im': L.imag, 'L_abs': np.abs(L),
            'rho00': np.full_like(times, p), 'rho01_re': off.real, 'rho01_im': off.imag,
            'p_x_plus': .5+off.real, 'p_y_plus': .5-off.imag, 'purity': purity,
            'local_entropy_bits': entropy_from_radius(radius),
            'energy_s_J': np.full_like(times, ENERGY_SCALE*case['omega_s']*sz/2),
            'global_purity': np.full_like(times, global_purity)}


def complex_pairs(a):
    return np.stack((a.real, a.imag), axis=-1).tolist()


def full_checks(case, checkpoints):
    n = len(case['g'])
    d = 2**n
    count = n+1
    h_s = case['omega_s']/2 * embed(Z, 0, count)
    h_e = sum((w/2*embed(Z, k+1, count) for k, w in enumerate(case['omega_bath'])),
              np.zeros_like(h_s))
    h_int = sum((g/2*embed(Z, 0, count) @ embed(Z, k+1, count)
                 for k, g in enumerate(case['g'])), np.zeros_like(h_s))
    h = h_s + h_e + h_int
    rho0 = product([density(case['system_bloch'])] + [density(v) for v in case['bath_bloch']])
    ev, q = np.linalg.eigh(h)
    base_energies = [float(np.trace(rho0 @ x).real) for x in (h_s, h_e, h_int, h)]
    base_purity = float(np.trace(rho0 @ rho0).real)
    rows = []
    for t in checkpoints:
        u = (q*np.exp(-1j*ev*t)) @ q.conj().T
        rho = u @ rho0 @ u.conj().T
        red = reduced_system(rho, d)
        expected = curve(case, np.array([t]))
        analytic = np.array([[expected['rho00'][0], expected['rho01_re'][0]+1j*expected['rho01_im'][0]],
                             [expected['rho01_re'][0]-1j*expected['rho01_im'][0], 1-expected['rho00'][0]]])
        # Partial transpose on the system: swap system ket and bra axes.
        pt = rho.reshape(2, d, 2, d).transpose(2, 1, 0, 3).reshape(2*d, 2*d)
        pt_eig = np.linalg.eigvalsh(pt)
        energies = [float(np.trace(rho @ x).real) for x in (h_s, h_e, h_int, h)]
        rows.append({'t_us': float(t), 'rho_s_complex_pairs': complex_pairs(red),
                     'analytic_rho_max_error': float(np.max(np.abs(red-analytic))),
                     'unitary_max_error': float(np.max(np.abs(u.conj().T @ u-np.eye(2*d)))),
                     'trace_error': float(abs(np.trace(rho)-1)),
                     'hermiticity_max_error': float(np.max(np.abs(rho-rho.conj().T))),
                     'rho_min_eigenvalue': float(np.linalg.eigvalsh(rho)[0]),
                     'global_purity': float(np.trace(rho @ rho).real),
                     'global_purity_error': float(abs(np.trace(rho @ rho).real-base_purity)),
                     'energies_over_hbar_rad_per_us': energies,
                     'energy_conservation_max_error_rad_per_us': float(np.max(np.abs(np.array(energies)-base_energies))),
                     'partial_transpose_negativity': float(-np.minimum(pt_eig, 0).sum())})
    return {'dimension': 2*d, 'hamiltonian_unit': 'rad/us',
            'energy_order': ['system', 'bath', 'interaction', 'total'],
            'initial_global_purity': base_purity,
            'eigen_residual_max_rad_per_us': float(np.max(np.abs(h @ q-q*ev))),
            'initial_system_and_bath_pure': all(abs(sum(x*x for x in v)-1) < 1e-12
                                               for v in [case['system_bloch']] + case['bath_bloch']),
            'bath_diagonal_in_z': all(v[0] == 0 and v[1] == 0 for v in case['bath_bloch']),
            'full_checks': rows}


def exchange_curve(card, times):
    w, k = card['omega'], card['kappa']
    p = np.cos(k*times)**2
    return {'t_us': times, 'rho00': p, 'rho11': 1-p, 'rho01_abs': np.zeros_like(times),
            'purity': p*p+(1-p)**2, 'energy_s_J': ENERGY_SCALE*w*(p-.5),
            'energy_bath_J': -ENERGY_SCALE*w*(p-.5)}


def exchange_checks(card, checkpoints):
    w, k = card['omega'], card['kappa']
    h_s = w/2*np.kron(Z, I2)
    h_e = w/2*np.kron(I2, Z)
    sp = (X+1j*Y)/2
    sm = sp.conj().T
    h = h_s+h_e+k*(np.kron(sp, sm)+np.kron(sm, sp))
    ev, q = np.linalg.eigh(h)
    psi0 = np.array([0, 1, 0, 0], dtype=complex)
    rows = []
    for t in checkpoints:
        psi = q @ (np.exp(-1j*ev*t)*(q.conj().T @ psi0))
        rho = np.outer(psi, psi.conj())
        red = reduced_system(rho, 2)
        expected = np.diag([math.cos(k*t)**2, math.sin(k*t)**2])
        rows.append({'t_us': float(t), 'state_complex_pairs': complex_pairs(psi),
                     'rho_s_complex_pairs': complex_pairs(red),
                     'rho_max_error': float(np.max(np.abs(red-expected))),
                     'norm_error': float(abs(np.vdot(psi, psi)-1)),
                     'bare_energy_sum_error_rad_per_us': float(abs(np.trace(rho @ (h_s+h_e))))})
    return {'basis': ['00', '01', '10', '11'], 'initial_basis': '01',
            'h_over_hbar_complex_pairs': complex_pairs(h), 'full_checks': rows}


def write_csv(path, records):
    # Standard CSV CRLF rows; Markdown/source mirror files retain LF.
    fields = list(records[0])
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def records(name, values):
    return [dict(case=name, **{key: float(column[i]) for key, column in values.items()})
            for i in range(len(values['t_us']))]


def svg_text(x, y, s, size=13, anchor='start', fill='#222'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{fill}">{html.escape(str(s))}</text>'


def figure(path, title, description, panels):
    width, panel_height = 1060, 330
    height = 90 + panel_height*len(panels)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             f'<title>{html.escape(title)}</title><desc>{html.escape(description)}</desc>',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="sans-serif">', svg_text(35, 29, title, 19)]
    for idx, panel in enumerate(panels):
        top = 70 + idx*panel_height
        x0, y0, pw, ph = 95, top+35, 665, 215
        series = panel['series']
        xmax = max(float(s['x'][-1]) for s in series)
        ymin, ymax = panel['ylim']
        parts.append(svg_text(35, top+8, panel['title'], 14))
        for j in range(6):
            x = x0+pw*j/5
            y = y0+ph*(1-j/5)
            parts.append(f'<path d="M {x:.3f} {y0} V {y0+ph}" stroke="#e4e4e4"/>')
            parts.append(f'<path d="M {x0} {y:.3f} H {x0+pw}" stroke="#e4e4e4"/>')
            parts.append(svg_text(x, y0+ph+20, f'{xmax*j/5:.3g}', 12, 'middle'))
            parts.append(svg_text(x0-12, y+4, f'{ymin+(ymax-ymin)*j/5:.3g}', 12, 'end'))
        parts += [f'<path d="M {x0} {y0} V {y0+ph} H {x0+pw}" fill="none" stroke="#333"/>',
                  svg_text(x0+pw/2, y0+ph+43, 'time t (us)', 13, 'middle'),
                  svg_text(x0, y0-12, panel['ylabel'], 12)]
        for j, s in enumerate(series):
            color = COLORS[j % len(COLORS)]
            dash = STYLES[j % len(STYLES)]
            xy = [(x0+pw*float(x)/xmax, y0+ph*(ymax-float(y))/(ymax-ymin)) for x, y in zip(s['x'], s['y'])]
            if not all(math.isfinite(x) and math.isfinite(y) for x, y in xy):
                raise ValueError('nonfinite SVG coordinate')
            coords = ' '.join(f'{x:.4f},{y:.4f}' for x, y in xy)
            style = f' stroke-dasharray="{dash}"' if dash else ''
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"{style}/>')
            ly = y0+8+j*20
            parts.append(f'<path d="M 790 {ly} H 825" stroke="{color}" stroke-width="2"{style}/>')
            parts.append(svg_text(833, ly+4, s['label'], 11))
    parts += ['</g>', '</svg>']
    path.write_text('\n'.join(parts)+'\n', encoding='utf-8')


def series(values, field, label, factor=1.):
    return {'x': values['t_us'], 'y': values[field]*factor, 'label': label}


def figures(output, cases, curves, exchange, exchange_values):
    first = cases[0]
    c0 = curves[first['name']]
    distinct, seen = [], set()
    for c in cases:
        signature = (tuple(c['g']), tuple(v[2] for v in c['bath_bloch']))
        if signature not in seen:
            seen.add(signature)
            distinct.append(series(curves[c['name']], 'L_abs', c['name']))
    info = f"first: {first['name']}; N={len(first['g'])}; g={first['g']} rad/us; omega_s={first['omega_s']:g} rad/us"
    figure(output/'coherence.svg', 'Finite bath: contrast and transverse Born probabilities', info,
           [{'title': 'Contrast depends on g and bath z polarization; repeated conditions share a curve',
             'ylabel': '|L| (dimensionless)', 'ylim': (0., 1.), 'series': distinct},
            {'title': info, 'ylabel': 'Born probability (dimensionless)', 'ylim': (0., 1.),
             'series': [series(c0, 'p_x_plus', 'P(x+) '+first['name']), series(c0, 'p_y_plus', 'P(y+) '+first['name'])]}])
    pair = cases[:2]
    corr = [series(curves[c['name']], 'global_purity', 'global purity '+c['name']) for c in pair]
    corr.append(series(c0, 'local_entropy_bits', 'local entropy '+first['name']))
    secondary = cases[2:4] or pair
    figure(output/'correlations.svg', 'Local entropy needs a global-state condition to mean entanglement',
           'Top: first cases global purity and first case local entropy. Bottom: next two cases local contrast.',
           [{'title': 'Local entropy is entanglement entropy only when the total state is pure',
             'ylabel': 'purity (dimensionless) / entropy (bits)', 'ylim': (0., 1.), 'series': corr},
            {'title': 'Contrast alone does not determine global purity or separability',
             'ylabel': '|L| (dimensionless)', 'ylim': (0., 1.),
             'series': [series(curves[c['name']], 'L_abs', c['name']) for c in secondary]}])
    energy_case = max(cases, key=lambda c: abs(c['omega_s']*c['system_bloch'][2]))
    ce = curves[energy_case['name']]
    ep = [series(ce, 'energy_s_J', energy_case['name'], 1/ENERGY_SCALE),
          series(exchange_values, 'energy_s_J', 'resonant exchange', 1/ENERGY_SCALE)]
    energy_limit = max(.1, abs(exchange['omega'])/2, abs(energy_case['omega_s']*energy_case['system_bloch'][2]/2))*1.08
    figure(output/'energy.svg', 'Longitudinal dephasing preserves energy; exchange changes populations',
           f"Exchange: initial |01>, omega={exchange['omega']:g}, kappa={exchange['kappa']:g} rad/us. Dephasing: {energy_case['name']}.",
           [{'title': f"Dephasing {energy_case['name']} versus resonant exchange, kappa={exchange['kappa']:g} rad/us",
             'ylabel': 'P(system 0) (dimensionless)', 'ylim': (0., 1.),
             'series': [series(ce, 'rho00', energy_case['name']), series(exchange_values, 'rho00', 'resonant exchange')]},
            {'title': 'Energy CSV stores J; plotted energy is divided by hbar times 1e6',
             'ylabel': 'E_S / (hbar x 1e6) (rad/us)', 'ylim': (-energy_limit, energy_limit), 'series': ep}])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('assets'))
    args = parser.parse_args()
    try:
        with args.inputs.open(encoding='utf-8') as f:
            data = validate(json.load(f, object_pairs_hook=unique_object,
                                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite JSON constant'))))
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    outputs = ['dephasing.csv', 'exchange.csv', 'results.json', 'coherence.svg', 'correlations.svg', 'energy.svg']
    if any((args.output/name).exists() for name in outputs):
        parser.error('output contains a generated target; use a new directory to preserve prior results')
    times = np.linspace(0., data['t_max'], data['samples'])
    checkpoints = [0., data['t_max']/16, data['t_max']/4, data['t_max']/2, data['t_max']]
    curves = {c['name']: curve(c, times) for c in data['dephasing_cases']}
    checks = {c['name']: full_checks(c, checkpoints) for c in data['dephasing_cases']}
    ex = exchange_curve(data['exchange'], times)
    report = {'model': 'finite-longitudinal-spin-bath', 'inputs': data,
              'hbar_J_s': HBAR_J_S, 'energy_scale_J_per_rad_per_us': ENERGY_SCALE,
              'basis_index': 'system*2**N + sum(b[k]*2**(N-1-k))',
              'numeric_method': 'analytic product on grid; full Hermitian eig/unitary and partial trace at five points',
              'negativity_boundary': 'positive detects entanglement; zero alone does not prove separability',
              'dephasing': checks, 'exchange': exchange_checks(data['exchange'], checkpoints)}
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output/'dephasing.csv', [r for c in data['dephasing_cases'] for r in records(c['name'], curves[c['name']])])
    write_csv(args.output/'exchange.csv', records('resonant_exchange', ex))
    figures(args.output, data['dephasing_cases'], curves, data['exchange'], ex)
    (args.output/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'files': outputs, 'cases': len(checks),
                      'max_analytic_rho_error': max(r['analytic_rho_max_error'] for c in checks.values() for r in c['full_checks'])},
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
```
