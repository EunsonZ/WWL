---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# 无源端口与互联实验源码

返回 [[控制论/80-实践/08-无源端口与互联/README|复现说明]]。

<!-- code-sync: 控制论/80-实践/08-无源端口与互联/passivity_lab.py -->

```python
#!/usr/bin/env python3
"""SI port interconnection: RK4, independent closed forms, energy ledgers and SVG."""
import argparse
import csv
import html
import json
import math
import platform
import resource
import time
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    p = json.loads(path.read_text(), object_pairs_hook=unique)
    keys = {'mass_kg', 'damping_N_s_per_m', 'stiffness_N_per_m', 'q0_m', 'v0_m_per_s',
            'hidden_mass_kg', 'hidden_stiffness_N_per_m', 'hidden_q0_m',
            'inductance_H', 'capacitance_F', 'resistance_ohm', 'vc0_V', 'i0_A',
            'duration_s', 'sample_s', 'substep_s'}
    require(isinstance(p, dict) and set(p) == keys, 'unexpected input fields')
    require(all(finite(value) for value in p.values()), 'all parameters must be finite numbers')
    for key in ('mass_kg', 'stiffness_N_per_m', 'hidden_mass_kg', 'hidden_stiffness_N_per_m',
                'inductance_H', 'capacitance_F', 'duration_s', 'sample_s', 'substep_s'):
        require(p[key] > 0, key + ' must be positive')
    require(p['damping_N_s_per_m'] >= 0 and p['resistance_ohm'] >= 0, 'loss must be nonnegative')
    require(p['duration_s'] <= 20, 'finite duration must not exceed 20 s')
    require(p['duration_s'] / p['substep_s'] <= 200000, 'too many substeps')
    require(abs(p['duration_s'] / p['sample_s'] - round(p['duration_s'] / p['sample_s'])) < 1e-9,
            'duration must align to samples')
    require(abs(p['sample_s'] / p['substep_s'] - round(p['sample_s'] / p['substep_s'])) < 1e-9,
            'samples must align to substeps')
    require(p['substep_s'] <= p['sample_s'] / 4, 'use at least four substeps per sample')
    return p


def exact(q0, v0, mass, damping, stiffness, sign, t):
    """exp(A*t) from (A+alpha*I)^2=(alpha^2-sign*k/m)*I, not RK4."""
    alpha = damping / (2 * mass)
    delta = alpha * alpha - sign * stiffness / mass
    if abs(delta) < 1e-14:
        c, s = 1.0, t
    elif delta > 0:
        w = math.sqrt(delta)
        c, s = math.cosh(w * t), math.sinh(w * t) / w
    else:
        w = math.sqrt(-delta)
        c, s = math.cos(w * t), math.sin(w * t) / w
    a = math.exp(-alpha * t)
    return (a * ((c + alpha * s) * q0 + s * v0),
            a * (-sign * stiffness / mass * s * q0 + (c - alpha * s) * v0))


def rk4(rhs, state, h):
    a = rhs(state)
    b = rhs([x + h * y / 2 for x, y in zip(state, a)])
    c = rhs([x + h * y / 2 for x, y in zip(state, b)])
    d = rhs([x + h * y for x, y in zip(state, c)])
    result = [x + h * (aa + 2 * bb + 2 * cc + dd) / 6
              for x, aa, bb, cc, dd in zip(state, a, b, c, d)]
    require(all(math.isfinite(x) for x in result), 'nonfinite trajectory')
    return result


def mechanical(p, case, h):
    m, k = p['mass_kg'], p['stiffness_N_per_m']
    b = 0.0 if case == 'lossless' else p['damping_N_s_per_m']
    sign = -1 if case == 'reversed' else 1
    mh, kh = p['hidden_mass_kg'], p['hidden_stiffness_N_per_m']
    hidden = case == 'hidden'
    z0 = p['hidden_q0_m'] if hidden else 0.0
    state = [p['q0_m'], p['v0_m_per_s'], z0, 0.0, 0.0, 0.0]
    initial = k * state[0] ** 2 / 2 + m * state[1] ** 2 / 2 + kh * z0 ** 2 / 2
    def rhs(s):
        q, v, z, w, _, _ = s
        return [v, (-b * v - sign * k * q) / m, w, -kh / mh * z,
                b * v * v, (1 - sign) * k * q * v]
    count = round(p['duration_s'] / p['sample_s'])
    inner = round(p['sample_s'] / h)
    rows = []
    for sample in range(count + 1):
        t = sample * p['sample_s']
        q, v, z, w, loss, active = state
        h1, h2, hh = m * v * v / 2, k * q * q / 2, mh * w * w / 2 + kh * z * z / 2
        total = h1 + h2 + hh
        qa, va = exact(p['q0_m'], p['v0_m_per_s'], m, b, k, sign, t)
        za, wa = exact(z0, 0, mh, 0, kh, 1, t)
        u1, y2 = -sign * k * q, k * q
        p1, p2, dissip = u1 * v, v * y2, b * v * v
        rows.append({'case': case, 't_s': t, 'q_m': q, 'v_m_per_s': v, 'hidden_q_m': z,
                     'hidden_v_m_per_s': w, 'mass_storage_J': h1, 'spring_storage_J': h2,
                     'hidden_storage_J': hh, 'total_storage_J': total, 'loss_integral_J': loss,
                     'connection_supply_integral_J': active, 'mass_supply_W': p1,
                     'spring_supply_W': p2, 'connection_supply_W': p1 + p2, 'loss_W': dissip,
                     'storage_dot_W': p1 + p2 - dissip,
                     'balance_residual_J': total + loss - active - initial,
                     'analytic_q_m': qa, 'analytic_v_m_per_s': va,
                     'analytic_hidden_q_m': za, 'analytic_hidden_v_m_per_s': wa})
        if sample < count:
            for _ in range(inner):
                state = rk4(rhs, state, h)
    return rows


def electrical(p, h):
    L, C, R = p['inductance_H'], p['capacitance_F'], p['resistance_ohm']
    state = [p['vc0_V'], p['i0_A'], 0.0]
    initial = C * state[0] ** 2 / 2 + L * state[1] ** 2 / 2
    def rhs(s):
        vc, i, _ = s
        return [i / C, (-R * i - vc) / L, R * i * i]
    rows = []
    for sample in range(round(p['duration_s'] / p['sample_s']) + 1):
        t = sample * p['sample_s']
        vc, i, loss = state
        # vc''+(R/L)vc'+(1/LC)vc=0; its derivative is i/C.
        vca, derivative = exact(p['vc0_V'], p['i0_A'] / C, L * C, R * C, 1, 1, t)
        h1, h2 = L * i * i / 2, C * vc * vc / 2
        rows.append({'t_s': t, 'vc_V': vc, 'i_A': i, 'inductor_storage_J': h1,
                     'capacitor_storage_J': h2, 'total_storage_J': h1 + h2,
                     'loss_integral_J': loss, 'inductor_supply_W': -vc * i,
                     'capacitor_supply_W': i * vc, 'loss_W': R * i * i,
                     'balance_residual_J': h1 + h2 + loss - initial,
                     'analytic_vc_V': vca, 'analytic_i_A': C * derivative})
        if sample < round(p['duration_s'] / p['sample_s']):
            for _ in range(round(p['sample_s'] / h)):
                state = rk4(rhs, state, h)
    return rows


def csv_write(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def svg(path, title, panels, duration, subtitle):
    width, height = 920, 110 + 295 * len(panels)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="sans-serif" font-size="14" fill="#182332">',
             f'<text x="24" y="28" font-size="20">{html.escape(title)}</text>',
             f'<text x="24" y="52">{html.escape(subtitle)}</text>']
    for index, (ylabel, lines) in enumerate(panels):
        top, left, plotw, ploth = 92 + index * 295, 100, 770, 178
        values = [y for _, _, _, points in lines for _, y in points]
        low, high = min(0, min(values)), max(0, max(values))
        pad = (high - low) * .08 if high > low else 1.0
        low, high = low - pad, high + pad
        def point(t, y):
            return left + plotw * t / duration, top + ploth * (high - y) / (high - low)
        parts.append(f'<text x="{left}" y="{top - 12}">{html.escape(ylabel)}</text>')
        for tick in range(5):
            value = low + (high - low) * tick / 4
            _, py = point(0, value)
            parts.append(f'<path d="M{left} {py:.3f}h{plotw}" stroke="#d9dfe6"/>')
            parts.append(f'<text x="{left - 12}" y="{py + 5:.3f}" text-anchor="end">{value:.4g}</text>')
        for tick in range(7):
            t = duration * tick / 6
            px, _ = point(t, 0)
            parts.append(f'<text x="{px:.3f}" y="{top + ploth + 20}" text-anchor="middle">{t:.3g}</text>')
        parts.append(f'<path d="M{left} {top}v{ploth}h{plotw}" stroke="#182332" fill="none"/>')
        parts.append(f'<text x="{left + plotw}" y="{top + ploth + 40}" text-anchor="end">time t (s)</text>')
        for line_index, (label, color, dash, points) in enumerate(lines):
            coords = ' '.join(f'{a:.3f},{b:.3f}' for a, b in (point(t, y) for t, y in points))
            dashed = f' stroke-dasharray="{dash}"' if dash else ''
            parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.8"{dashed} points="{coords}"/>')
            lx = left + (line_index % 3) * 250
            ly = top + ploth + 62 + (line_index // 3) * 21
            parts.append(f'<path d="M{lx} {ly - 4}h25" stroke="{color}" stroke-width="2"{dashed}/>')
            parts.append(f'<text x="{lx + 31}" y="{ly}">{html.escape(label)}</text>')
    parts.append('</g></svg>')
    path.write_text('\n'.join(parts) + '\n')


def series(rows, field):
    return [(r['t_s'], r[field]) for r in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    p = load(args.input)
    require(not args.output_dir.exists(), 'output directory must not already exist')
    h = p['substep_s']
    cases = {name: mechanical(p, name, h) for name in ('nominal', 'lossless', 'reversed', 'hidden')}
    circuit = electrical(p, h)
    errors = []
    for step in (p['sample_s'], p['sample_s'] / 2, h, h / 2):
        for name, base in cases.items():
            rows = mechanical(p, name, step)
            errors.append({'case': name, 'substep_s': step,
                           'max_q_closed_form_error_m': max(abs(r['q_m'] - r['analytic_q_m']) for r in rows),
                           'max_v_closed_form_error_m_per_s': max(abs(r['v_m_per_s'] - r['analytic_v_m_per_s']) for r in rows),
                           'max_balance_error_J': max(abs(r['balance_residual_J']) for r in rows),
                           'max_q_difference_from_export_m': max(abs(a['q_m'] - b['q_m']) for a, b in zip(rows, base))})
    summary = {'parameters': p, 'cases': {}, 'circuit': {}}
    for name, rows in cases.items():
        fields = ('q_m', 'v_m_per_s', 'hidden_q_m', 'hidden_v_m_per_s', 'total_storage_J',
                  'hidden_storage_J', 'loss_integral_J', 'connection_supply_integral_J')
        summary['cases'][name] = {'rows': len(rows), 'final': {key: rows[-1][key] for key in fields},
                                  'max_balance_error_J': max(abs(r['balance_residual_J']) for r in rows),
                                  'max_q_closed_form_error_m': max(abs(r['q_m'] - r['analytic_q_m']) for r in rows),
                                  'max_v_closed_form_error_m_per_s': max(abs(r['v_m_per_s'] - r['analytic_v_m_per_s']) for r in rows),
                                  'max_internal_supply_sum_W': max(abs(r['connection_supply_W']) for r in rows)}
    summary['circuit'] = {'rows': len(circuit), 'final': circuit[-1],
                          'max_vc_closed_form_error_V': max(abs(r['vc_V'] - r['analytic_vc_V']) for r in circuit),
                          'max_i_closed_form_error_A': max(abs(r['i_A'] - r['analytic_i_A']) for r in circuit),
                          'max_balance_error_J': max(abs(r['balance_residual_J']) for r in circuit)}
    # This optional relation is a dimensional model match, not a coupling of the two objects.
    if (p['mass_kg'], p['stiffness_N_per_m'], p['damping_N_s_per_m'], p['inductance_H'],
        p['capacitance_F'], p['resistance_ohm'], p['vc0_V'], p['i0_A']) == (
            2, 8, 2, 2, .125, 2, 8 * p['q0_m'], p['v0_m_per_s']):
        summary['si_model_match'] = {
            'max_vc_over_8_minus_q_m': max(abs(e['vc_V'] / 8 - m['q_m']) for e, m in zip(circuit, cases['nominal'])),
            'max_i_numeric_minus_v_m_per_s': max(abs(e['i_A'] - m['v_m_per_s']) for e, m in zip(circuit, cases['nominal']))}
    require(all(entry['max_balance_error_J'] < 1e-5 * max(1, cases[entry['case']][-1]['total_storage_J'])
                for entry in errors if entry['substep_s'] == h), 'energy ledger check failed at export step')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    csv_write(args.output_dir / 'mechanical.csv', [r for rows in cases.values() for r in rows])
    csv_write(args.output_dir / 'electrical.csv', circuit)
    csv_write(args.output_dir / 'step-errors.csv', errors)
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    nominal = cases['nominal']
    svg(args.output_dir / 'energy.svg', 'Passive negative feedback: where the energy goes', [
        ('Energy (J)', [('mass H1', '#005b96', '', series(nominal, 'mass_storage_J')),
                        ('spring H2', '#b34b00', '6 3', series(nominal, 'spring_storage_J')),
                        ('total H', '#503b8c', '', series(nominal, 'total_storage_J')),
                        ('dissipated Eb', '#168048', '2 3', series(nominal, 'loss_integral_J'))]),
        ('Power (W)', [('mass port supply', '#005b96', '', series(nominal, 'mass_supply_W')),
                      ('spring port supply', '#b34b00', '6 3', series(nominal, 'spring_supply_W')),
                      ('damping loss', '#168048', '2 3', series(nominal, 'loss_W'))])],
        p['duration_s'], 'SI model, zero external force; port supplies cancel; RK4 from input.json')
    svg(args.output_dir / 'failures.svg', 'Change one condition: loss, wiring or hidden motion', [
        ('Displacement (m)', [('nominal q', '#005b96', '', series(cases['nominal'], 'q_m')),
                             ('lossless q', '#168048', '6 3', series(cases['lossless'], 'q_m')),
                             ('hidden z', '#503b8c', '9 3 2 3', series(cases['hidden'], 'hidden_q_m'))]),
        ('Stored energy (J)', [(name + ' total H', color, dash, series(cases[name], 'total_storage_J'))
                               for name, color, dash in [('nominal', '#005b96', ''), ('lossless', '#168048', '6 3'),
                                                         ('hidden', '#503b8c', '9 3 2 3')]]),
        ('Reversed displacement (m)', [('reversed q', '#b34b00', '', series(cases['reversed'], 'q_m'))]),
        ('Reversed energy ledger (J)', [('stored H', '#b34b00', '', series(cases['reversed'], 'total_storage_J')),
                                       ('connection supplied', '#005b96', '6 3', series(cases['reversed'], 'connection_supply_integral_J')),
                                       ('dissipated Eb', '#168048', '2 3', series(cases['reversed'], 'loss_integral_J'))])],
        p['duration_s'], 'Same visible initial state; reversed connection supplies active power; each panel uses its own scale')
    print(json.dumps({'status': 'PASS', 'outputs': 6, 'mechanical_rows': sum(len(r) for r in cases.values()),
                      'electrical_rows': len(circuit), 'python': platform.python_version(),
                      'platform': platform.platform(), 'elapsed_s': time.perf_counter() - started,
                      'observed_peak_rss_native': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
                     indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
```
