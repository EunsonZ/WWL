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
