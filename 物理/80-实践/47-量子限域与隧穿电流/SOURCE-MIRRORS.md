---
stage: 0
aliases: []
prerequisites:
  - "[[物理/80-实践/47-量子限域与隧穿电流/README]]"
sources: []
---

# 量子限域与隧穿电流的源码镜像

规范文件是相邻 Python 源码；以下仅提供可读镜像，修改规范源码时同步这里。课程方程、参数、运行及结果见 [[物理/80-实践/47-量子限域与隧穿电流/README#运行同一张参数卡|复建入口]]。

## 求解真源镜像

<!-- code-sync: 物理/80-实践/47-量子限域与隧穿电流/quantum_sheet_lab.py -->

```python
#!/usr/bin/env python3
"""Fixed separable hard-wall sheet + elastic rectangular barrier, SI outputs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

Q = 1.602176634e-19
HBAR = 1.054571817e-34
H = 2 * math.pi * HBAR
M0 = 9.1093837139e-31
KB = 1.380649e-23


def unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('duplicate input key: ' + k)
        out[k] = v
    return out


def read_card(path):
    raw = path.read_bytes()
    card = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    limits = {'mass_ratio': (.05, 1), 'well_nm': (4, 30),
              'barrier_eV': (0, 1), 'barrier_nm': (.1, 10),
              'temperature_K': (100, 600), 'mu_left_eV': (-.2, .4),
              'mu_right_eV': (-.2, .4), 'cutoff_eV': (.6, 2),
              'subbands': (2, 16), 'energy_steps': (80, 4000),
              'transverse_steps': (20, 512)}
    if not isinstance(card, dict) or set(card) != set(limits):
        raise ValueError('input must contain exactly the declared eleven keys')
    for k, (low, high) in limits.items():
        v = card[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
            raise ValueError('input outside finite domain: ' + k)
    for k in ['subbands', 'energy_steps', 'transverse_steps']:
        if type(card[k]) is not int or (k != 'subbands' and card[k] % 2):
            raise ValueError('integer/even quadrature grid required: ' + k)
    return card, raw


def softplus(x):
    return max(x, 0) + math.log1p(math.exp(-abs(x)))


def fermi(energy, mu, kt):
    x = (energy - mu) / kt
    if x >= 0:
        y = math.exp(-x)
        return y / (1 + y)
    return 1 / (1 + math.exp(x))


def levels(card):
    m = card['mass_ratio'] * M0
    e1 = HBAR**2 * math.pi**2 / (2 * m * (card['well_nm'] * 1e-9)**2 * Q)
    return [e1 * n * n for n in range(1, card['subbands'] + 1)]


def transmission(ex, card):
    v = card['barrier_eV']
    if v == 0:
        return 1.0
    if ex == 0:
        return 0.0
    c = 2 * card['mass_ratio'] * M0 * Q * (card['barrier_nm'] * 1e-9)**2 / HBAR**2
    d = ex - v
    if abs(d) < 1e-12:
        return 1 / (1 + c * v / 4)
    z = math.sqrt(c * abs(d))
    s = math.sin(z) if d > 0 else math.sinh(z)
    return 1 / (1 + v * v * s * s / (4 * ex * abs(d)))


def weights(n):
    return [1 if i in (0, n) else 4 if i % 2 else 2 for i in range(n + 1)]


def solve(card):
    ens = levels(card)
    kt = KB * card['temperature_K'] / Q
    gd = 2  # spin 2, valley 1; both ky signs integrated explicitly
    m = card['mass_ratio'] * M0
    dos = gd * m / (2 * math.pi * HBAR**2)
    rows = []
    for n, en in enumerate(ens, 1):
        nl = dos * Q * kt * softplus((card['mu_left_eV'] - en) / kt)
        nr = dos * Q * kt * softplus((card['mu_right_eV'] - en) / kt)
        rows.append({'n': n, 'edge_eV': en, 'left_sheet_m-2': nl,
                     'right_sheet_m-2': nr, 'left_charge_C_m-2': -Q * nl})
    nx, nu = card['energy_steps'], card['transverse_steps']
    xmax, umax = card['cutoff_eV'], math.sqrt(card['cutoff_eV'])
    wx, wu = weights(nx), weights(nu)
    ey = [(umax * j / nu)**2 for j in range(nu + 1)]
    # ky = sqrt(2*m*Q)/HBAR * u, Ex(J)=Q*Ex(eV).
    pref = gd * Q * Q * math.sqrt(2 * m * Q) / (math.pi * H * HBAR)
    spectra = []
    for i in range(nx + 1):
        ex = xmax * i / nx
        left, right = 0.0, 0.0
        for en in ens:
            left += sum(w * fermi(en + ex + e, card['mu_left_eV'], kt) for w, e in zip(wu, ey))
            right += sum(w * fermi(en + ex + e, card['mu_right_eV'], kt) for w, e in zip(wu, ey))
        sl = left * umax / (3 * nu)
        sr = right * umax / (3 * nu)
        t = transmission(ex, card)
        spectra.append({'Ex_eV': ex, 'transmission': t, 'supply_left_sqrt_eV': sl,
                        'supply_right_sqrt_eV': sr, 'forward_A_m_eV': pref * t * sl,
                        'return_A_m_eV': pref * t * sr,
                        'net_electron_A_m_eV': pref * t * (sl - sr)})
    def integrate(key):
        return sum(w * r[key] for w, r in zip(wx, spectra)) * xmax / (3 * nx)
    forward, backward = integrate('forward_A_m_eV'), integrate('return_A_m_eV')
    net = integrate('net_electron_A_m_eV')
    tail_en = ens[0] * (len(ens) + 1)**2
    # n^2 >= (N+1)^2+(2N+3)j: upper bound for every omitted subband.
    a = ens[0] * (2 * len(ens) + 3) / kt
    omitted = dos * Q * kt * math.exp((max(card['mu_left_eV'], card['mu_right_eV']) - tail_en) / kt) / (-math.expm1(-a))
    exp_sum = sum(math.exp((mu - en) / kt) for mu in [card['mu_left_eV'], card['mu_right_eV']] for en in ens)
    gaussian = math.sqrt(math.pi * kt) / 2
    cut_tail = pref * exp_sum * math.exp(-xmax / kt) * (kt * gaussian + kt * kt / (2 * umax))
    omitted_exp_sum = sum(math.exp((mu - tail_en) / kt) for mu in [card['mu_left_eV'], card['mu_right_eV']]) / (-math.expm1(-a))
    omitted_current = pref * omitted_exp_sum * kt * gaussian
    result = {'card': card, 'subband_rows': rows,
              'left_sheet_m-2': sum(r['left_sheet_m-2'] for r in rows),
              'right_sheet_m-2': sum(r['right_sheet_m-2'] for r in rows),
              'left_charge_C_m-2': -Q * sum(r['left_sheet_m-2'] for r in rows),
              'omitted_sheet_bound_m-2': omitted,
              'omitted_current_bound_A_m': omitted_current,
              'cutoff_current_bound_A_m': cut_tail,
              'forward_electron_A_m': forward, 'return_electron_A_m': backward,
              'net_electron_A_m': net, 'conventional_x_A_m': -net,
              'width_1um_current_A': -net * 1e-6,
              'WKB_zero_ex_leading_exponent': math.exp(-2 * math.sqrt(2 * m * Q * card['barrier_eV']) * card['barrier_nm'] * 1e-9 / HBAR)}
    return result, spectra


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--prototype', action='store_true', help='one coarse case only')
    args = ap.parse_args()
    card, input_raw = read_card(args.inputs)
    if args.out.exists() and (not args.out.is_dir() or any(args.out.iterdir())):
        raise ValueError('output must be absent or an empty directory')
    cases = {'default': card}
    if args.prototype:
        cases = {'prototype': dict(card, energy_steps=160, transverse_steps=32)}
    else:
        changes = {'equilibrium': {'mu_right_eV': card['mu_left_eV']},
                   'reverse': {'mu_left_eV': card['mu_right_eV'], 'mu_right_eV': card['mu_left_eV']},
                   'wide_barrier': {'barrier_nm': card['barrier_nm'] * 1.5},
                   'hot': {'temperature_K': min(600, card['temperature_K'] * 1.5)},
                   'wide_well': {'well_nm': min(30, card['well_nm'] * 1.5)},
                   'transparent': {'barrier_eV': 0},
                   'coarse': {'energy_steps': card['energy_steps'] // 2, 'transverse_steps': card['transverse_steps'] // 2},
                   'fine': {'energy_steps': card['energy_steps'] * 2, 'transverse_steps': card['transverse_steps'] * 2},
                   'tail': {'cutoff_eV': min(2, card['cutoff_eV'] * 1.5), 'subbands': min(16, card['subbands'] + 2)}}
        for label, delta in changes.items():
            cases[label] = dict(card, **delta)
    # Validate derived grids too, before any result is written.
    for c in cases.values():
        if c['energy_steps'] > 4000 or c['transverse_steps'] > 512 or c['barrier_nm'] > 10 or c['energy_steps'] % 2 or c['transverse_steps'] % 2:
            raise ValueError('derived case exceeds declared finite budget')
    outputs, report = {}, {}
    for label, c in cases.items():
        report[label], outputs[label] = solve(c)
    args.out.mkdir(parents=True, exist_ok=True)
    for label, rows in outputs.items():
        write_csv(args.out / (label + '-spectrum.csv'), rows)
    write_csv(args.out / 'subbands.csv', report[next(iter(report))]['subband_rows'])
    zrows = []
    base = cases[next(iter(cases))]
    for i in range(241):
        z = base['well_nm'] * i / 240
        row = {'z_nm': z}
        for n in range(1, min(3, base['subbands']) + 1):
            row['psi%d_nm-1-2' % n] = math.sqrt(2 / base['well_nm']) * math.sin(n * math.pi * z / base['well_nm'])
        zrows.append(row)
    write_csv(args.out / 'states.csv', zrows)
    snapshot = {'model': 'hard-wall-z,elastic-x-barrier,continuous-y,no-mode-mixing',
                'energy_reference': 'lead conduction floor 0 eV for both reservoirs',
                'degeneracy': {'spin': 2, 'valley': 1},
                'input_sha256': hashlib.sha256(input_raw).hexdigest(),
                'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'cases': report}
    (args.out / 'results.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v['net_electron_A_m'] for k, v in report.items()}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, OverflowError) as error:
        raise SystemExit(str(error))
```

## 图源镜像

<!-- code-sync: 物理/80-实践/47-量子限域与隧穿电流/build_figures.py -->

```python
#!/usr/bin/env python3
"""Render only saved results/CSV; never import or execute the solver."""
import argparse
import csv
import html
import json
import math
from pathlib import Path

COLORS = ['#195baf', '#bd4329', '#178568', '#885baf', '#8a6b13']


def read_csv(path):
    with path.open(newline='') as stream:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]


def panel(title, xlabel, ylabel, curves, x, y, xlim=None, ylim=None):
    width, height = 460, 210
    allx = [v for _, points, _ in curves for v, _ in points]
    ally = [v for _, points, _ in curves for _, v in points]
    xmin, xmax = xlim or (min(allx), max(allx))
    ymin, ymax = ylim or (min(0, min(ally)), max(ally) * 1.08)
    if ymax <= ymin:
        ymax = ymin + 1
    def px(v): return x + width * (v - xmin) / (xmax - xmin)
    def py(v): return y + height * (ymax - v) / (ymax - ymin)
    escape = html.escape
    out = [f'<text x="{x}" y="{y-32}" font-size="17">{escape(title)}</text>',
           f'<path d="M{x},{y}v{height}h{width}" fill="none" stroke="#354258"/>']
    for j in range(5):
        vx = xmin + j * (xmax - xmin) / 4
        vy = ymin + j * (ymax - ymin) / 4
        out += [f'<text x="{px(vx):.3f}" y="{y+height+18}" text-anchor="middle" font-size="11">{vx:.3g}</text>',
                f'<text x="{x-7}" y="{py(vy)+4:.3f}" text-anchor="end" font-size="11">{vy:.3g}</text>']
    out += [f'<text x="{x+width/2}" y="{y+height+38}" text-anchor="middle" font-size="13">{escape(xlabel)}</text>',
            f'<text transform="translate({x-70},{y+height/2}) rotate(-90)" text-anchor="middle" font-size="13">{escape(ylabel)}</text>']
    for index, (label, points, mapping) in enumerate(curves):
        color = COLORS[index % len(COLORS)]
        data = ' '.join(f'{px(a):.6f},{py(b):.6f}' for a, b in points)
        out.append(f'<polyline data-source="{escape(mapping,quote=True)}" points="{data}" fill="none" stroke="{color}" stroke-width="1.8"/>')
        out.append(f'<text x="{x+7}" y="{y+15+index*17}" fill="{color}" font-size="12">{escape(label)}</text>')
    return '\n'.join(out)


def svg(title, subtitle, panels):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="710" viewBox="0 0 1180 710">'
            '<rect width="1180" height="710" fill="#fff"/><g font-family="Arial, sans-serif" fill="#223044">'
            f'<text x="70" y="32" font-size="22">{html.escape(title)}</text>'
            f'<text x="70" y="56" font-size="13">{html.escape(subtitle)}</text>' + ''.join(panels) + '</g></svg>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results', type=Path, required=True)
    args = ap.parse_args()
    targets = [args.results / 'confinement.svg', args.results / 'supply-and-current.svg']
    if any(t.exists() for t in targets):
        raise ValueError('refuse to overwrite existing figures')
    report = json.loads((args.results / 'results.json').read_text())
    cases = report['cases']
    if 'default' not in cases:
        raise ValueError('full default results required, prototype is not a figure source')
    base = cases['default']; c = base['card']
    states = read_csv(args.results / 'states.csv')
    subs = read_csv(args.results / 'subbands.csv')
    sp = read_csv(args.results / 'default-spectrum.csv')
    curves = [(f'n={n}', [(r['z_nm'], r['psi%d_nm-1-2' % n]) for r in states], f'states.csv:z_nm,psi{n}_nm-1-2') for n in range(1,min(3,c['subbands'])+1)]
    p1 = panel('Normalized z envelopes', 'z (nm)', 'psi (nm^-1/2)', curves, 80, 120, ylim=(-1.12*math.sqrt(2/c['well_nm']),1.12*math.sqrt(2/c['well_nm'])))
    edge_curves = [(f'n={int(r["n"])}', [(0,r['edge_eV']),(c['well_nm'],r['edge_eV'])], f'subbands.csv:edge_eV,row-n={int(r["n"])}') for r in subs[:3]]
    edge_curves += [('mu L',[(0,c['mu_left_eV']),(c['well_nm'],c['mu_left_eV'])],'results.json:cases.default.card.mu_left_eV'), ('mu R',[(0,c['mu_right_eV']),(c['well_nm'],c['mu_right_eV'])],'results.json:cases.default.card.mu_right_eV')]
    p2 = panel('Subband edges and reservoir reference', 'z (nm)', 'energy (eV)', edge_curves, 660, 120)
    dens = [('left reservoir',[(r['n'],r['left_sheet_m-2']/1e16) for r in subs],'subbands.csv:n,left_sheet_m-2; scale=1e-16'),('right reservoir',[(r['n'],r['right_sheet_m-2']/1e16) for r in subs],'subbands.csv:n,right_sheet_m-2; scale=1e-16')]
    p3 = panel('FD sheet population by subband', 'subband n', 'n_s (10^16 m^-2)', dens, 80, 440)
    cut = [r for r in sp if r['Ex_eV'] <= .4]
    tcurves = [('exact flux T',[(r['Ex_eV'],r['transmission']) for r in cut],'default-spectrum.csv:Ex_eV,transmission; Ex<=0.4'),('zero Ex exponent',[(0,base['WKB_zero_ex_leading_exponent']),(.4,base['WKB_zero_ex_leading_exponent'])],'results.json:cases.default.WKB_zero_ex_leading_exponent')]
    p4 = panel('Finite barrier vs one exponent', 'longitudinal Ex (eV)', 'dimensionless', tcurves, 660, 440, ylim=(0,1.05))
    targets[0].write_text(svg('One card: confinement, population and transmission', f'm={c["mass_ratio"]} m0, Lz={c["well_nm"]} nm; barrier {c["barrier_eV"]} eV / {c["barrier_nm"]} nm', [p1,p2,p3,p4]))
    supply = [('left',[(r['Ex_eV'],r['supply_left_sqrt_eV']) for r in cut],'default-spectrum.csv:Ex_eV,supply_left_sqrt_eV; Ex<=0.4'),('right',[(r['Ex_eV'],r['supply_right_sqrt_eV']) for r in cut],'default-spectrum.csv:Ex_eV,supply_right_sqrt_eV; Ex<=0.4')]
    a1 = panel('Both reservoirs supply occupied modes', 'Ex (eV)', 'integral du f (sqrt(eV))', supply,80,120)
    currents = [('forward',[(r['Ex_eV'],r['forward_A_m_eV']) for r in cut],'default-spectrum.csv:Ex_eV,forward_A_m_eV; Ex<=0.4'),('return',[(r['Ex_eV'],r['return_A_m_eV']) for r in cut],'default-spectrum.csv:Ex_eV,return_A_m_eV; Ex<=0.4'),('net electron flow',[(r['Ex_eV'],r['net_electron_A_m_eV']) for r in cut],'default-spectrum.csv:Ex_eV,net_electron_A_m_eV; Ex<=0.4')]
    a2 = panel('T times supply: area gives A/m', 'Ex (eV)', 'spectral current (A m^-1 eV^-1)', currents,660,120)
    names = ['equilibrium','default','reverse','wide_barrier','hot','wide_well','transparent']
    pts = [(i,cases[k]['net_electron_A_m']) for i,k in enumerate(names)]
    a3 = panel('Actual changed-card currents', 'case index 0..6', 'electron current / width (A/m)', [('0 eq; 1 default; 2 reverse',pts,'results.json:cases.[equilibrium,default,reverse,wide_barrier,hot,wide_well,transparent].net_electron_A_m'),('3 wide barrier; 4 hot; 5 wide well; 6 T=1',[],'legend')],80,440)
    gridnames=['coarse','default','fine','tail']
    points=[(i,abs(cases[k]['net_electron_A_m']-base['net_electron_A_m'])) for i,k in enumerate(gridnames)]
    a4=panel('Quadrature and tail changes are different', '0 coarse; 1 base; 2 fine; 3 tail', '|K_case - K_base| (A/m)', [('same model / stated cutoffs',points,'results.json:cases.[coarse,default,fine,tail].net_electron_A_m; abs(case-default)')],660,440)
    targets[1].write_text(svg('Net current needs a full energy and mode supply', f'T={c["temperature_K"]} K; muL={c["mu_left_eV"]} eV, muR={c["mu_right_eV"]} eV; conventional x current is minus electron-flow current',[a1,a2,a3,a4]))
    print('wrote confinement.svg and supply-and-current.svg')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
```

