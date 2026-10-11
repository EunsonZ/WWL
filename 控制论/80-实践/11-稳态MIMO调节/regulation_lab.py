#!/usr/bin/env python3
"""Fixed 3-state/2-port continuous regulation lab; no sampled controller claims."""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction
import json
import math
from pathlib import Path
import tempfile
import shutil
import numpy as np
from scipy.linalg import expm

CASE_NAMES = ('nominal', 'disturbance', 'slow_integral', 'fast_integral',
              'matched_parameter', 'sensor_bias', 'no_integral', 'dc_zero', 'saturation')


def scalar(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a numeric parameter')
    try:
        result = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError('Expected a finite number or rational string') from exc
    if not math.isfinite(result) or abs(result) > 1e4:
        raise ValueError('Parameter must be finite and bounded by 1e4')
    return result


def array(value, shape):
    raw = np.asarray(value, dtype=object)
    if raw.shape != shape:
        raise ValueError(f'Expected shape {shape}')
    return np.array([scalar(v) for v in raw.flat]).reshape(shape)


def load_card(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    card = json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if card.get('schema') != 'wwl-mimo-regulation-1':
        raise ValueError('Unknown input schema')
    for key, shape in [('B', (3, 2)), ('C', (2, 3)), ('C_bad', (2, 3)),
                       ('decay', (3,)), ('reference', (2,)), ('disturbance', (3,)),
                       ('bias', (2,)), ('x0', (3,)), ('hatx0', (3,)), ('eta0', (2,))]:
        array(card[key], shape)
    positive = ('time_scale_s', 'kappa', 'horizon_tau', 'dt_tau', 'input_limit',
                'slow_kappa_factor', 'fast_kappa_factor', 'matched_third_decay')
    for key in positive:
        if scalar(card[key]) <= 0:
            raise ValueError(f'{key} must be positive')
    if np.min(array(card['decay'], (3,))) <= 0 or scalar(card['k']) < 0 or scalar(card['ell']) < 0:
        raise ValueError('Decay must be positive; k and ell nonnegative')
    horizon, dt, switch = (scalar(card[k]) for k in
                           ('horizon_tau', 'dt_tau', 'disturbance_switch_tau'))
    if horizon > 120 or dt > .1 or horizon / dt > 50000 or not 0 < switch < horizon:
        raise ValueError('Require horizon<=120, dt<=.1, <=50000 steps and interior switch')
    for duration in (horizon, switch):
        if abs(duration / dt - round(duration / dt)) > 1e-8:
            raise ValueError('Horizon and disturbance switch must align with dt')
    # Fixed port counterexample uses its exact left-null identity; do not relabel a new plant.
    fixed = {'decay': [1, 2, 3], 'B': [[1, 0], [0, 1], [1, 1]],
             'C': [[1, 0, 1], [0, 1, 1]], 'C_bad': [[1, 0, -3], [0, 1, 0]]}
    for key, value in fixed.items():
        expected = np.asarray(value, dtype=float)
        if not np.array_equal(array(card[key], expected.shape), expected):
            raise ValueError('Fixed model ports/decay required; use matched_third_decay for the declared parameter case')
    return card


def exact_rank(matrix):
    """Gaussian elimination over rationals; never a floating threshold rank."""
    rows = [[Fraction(str(v)) for v in row] for row in matrix]
    if not rows or not rows[0]:
        return 0
    if len({len(row) for row in rows}) != 1:
        raise ValueError('Ragged rational matrix')
    pivot = 0
    for col in range(len(rows[0])):
        chosen = next((i for i in range(pivot, len(rows)) if rows[i][col]), None)
        if chosen is None:
            continue
        rows[pivot], rows[chosen] = rows[chosen], rows[pivot]
        divisor = rows[pivot][col]
        rows[pivot] = [v / divisor for v in rows[pivot]]
        for i in range(len(rows)):
            if i != pivot:
                factor = rows[i][col]
                rows[i] = [v - factor * w for v, w in zip(rows[i], rows[pivot])]
        pivot += 1
        if pivot == len(rows):
            break
    return pivot


def rational_diagnostics(card, bad=False):
    d = [Fraction(str(v)) for v in card['decay']]
    B = [[Fraction(str(v)) for v in row] for row in card['B']]
    C = [[Fraction(str(v)) for v in row] for row in card['C_bad' if bad else 'C']]
    A = [[-d[i] if i == j else Fraction(0) for j in range(3)] for i in range(3)]
    ctrb = [[B[i][j] * (-d[i]) ** power for power in range(3) for j in range(2)] for i in range(3)]
    obsv = [[C[j][i] * (-d[i]) ** power for i in range(3)] for power in range(3) for j in range(2)]
    R0 = [[-A[i][j] for j in range(3)] + [-B[i][j] for j in range(2)] for i in range(3)]
    R0 += [row + [Fraction(0), Fraction(0)] for row in C]
    G0 = [[sum(C[i][k] * B[k][j] / d[k] for k in range(3)) for j in range(2)] for i in range(2)]
    return {'controllability_rank': exact_rank(ctrb), 'observability_rank': exact_rank(obsv),
            'R0_rank': exact_rank(R0), 'R0_rows': 5, 'G0_rank': exact_rank(G0),
            'G0_rational': [[str(v) for v in row] for row in G0]}


def case_model(card, name):
    if name not in CASE_NAMES:
        raise ValueError('Unknown case')
    decay = array(card['decay'], (3,)).copy()
    if name == 'matched_parameter':
        decay[2] = scalar(card['matched_third_decay'])
    A = -np.diag(decay)
    B = array(card['B'], (3, 2))
    C = array(card['C_bad' if name == 'dc_zero' else 'C'], (2, 3))
    K = scalar(card['k']) * C
    L = scalar(card['ell']) * C.T
    kappa = scalar(card['kappa'])
    if name in ('slow_integral', 'fast_integral'):
        kappa *= scalar(card['slow_kappa_factor' if name == 'slow_integral' else 'fast_kappa_factor'])
    Ki = kappa * np.eye(2)
    r = np.array([1., 0.]) if name == 'dc_zero' else array(card['reference'], (2,))
    b = array(card['bias'], (2,)) if name == 'sensor_bias' else np.zeros(2)
    d = array(card['disturbance'], (3,)) if name in (
        'disturbance', 'slow_integral', 'fast_integral', 'matched_parameter', 'no_integral') else np.zeros(3)
    ff = np.zeros((2, 2))
    if name == 'no_integral':
        G0 = C @ np.linalg.solve(-A, B)
        U = np.linalg.solve(G0, np.eye(2))
        X = np.linalg.solve(-A, B @ U)
        ff = U + K @ X
        Ki = np.zeros((2, 2))
    # z=(x,hatx,eta); no-integral has only six active states, eta held at zero.
    F = np.block([[A, -B @ K, B @ Ki],
                  [L @ C, A - B @ K - L @ C, B @ Ki],
                  [-C, np.zeros((2, 3)), np.zeros((2, 2))]])
    if name == 'no_integral':
        F[6:, :] = 0
    active = F[:6, :6] if name == 'no_integral' else F
    if name != 'dc_zero' and np.max(np.linalg.eigvals(active).real) >= 0:
        raise ValueError('The actual active linear closed loop is not Hurwitz')
    return dict(name=name, A=A, B=B, C=C, K=K, L=L, Ki=Ki, r=r, b=b, d=d,
                ff=ff, F=F, active=active, kappa=kappa,
                limit=scalar(card['input_limit']) if name == 'saturation' else None,
                switch=scalar(card['disturbance_switch_tau']))


def forcing(model, disturbance):
    fr = model['ff'] @ model['r']
    return np.r_[disturbance + model['B'] @ fr,
                 model['L'] @ model['b'] + model['B'] @ fr,
                 np.zeros(2) if model['name'] == 'no_integral' else model['r'] - model['b']]


def outputs(model, z):
    x, hat, eta = z[:3], z[3:6], z[6:]
    y = model['C'] @ x
    ym = y + model['b']
    command = -model['K'] @ hat + model['Ki'] @ eta + model['ff'] @ model['r']
    actual = command if model['limit'] is None else np.clip(command, -model['limit'], model['limit'])
    return y, ym, command, actual


def rhs(model, z, disturbance):
    x, hat = z[:3], z[3:6]
    _, ym, _, actual = outputs(model, z)
    return np.r_[model['A'] @ x + model['B'] @ actual + disturbance,
                 model['A'] @ hat + model['B'] @ actual + model['L'] @ (ym - model['C'] @ hat),
                 np.zeros(2) if model['name'] == 'no_integral' else model['r'] - ym]


def affine_step(F, f, dt):
    block = np.zeros((9, 9))
    block[:8, :8], block[:8, 8] = F, f
    return expm(dt * block)


def simulate(card, name):
    model = case_model(card, name)
    dt, horizon = scalar(card['dt_tau']), scalar(card['horizon_tau'])
    z = np.r_[array(card['x0'], (3,)), array(card['hatx0'], (3,)), array(card['eta0'], (2,))]
    if name == 'no_integral':
        z[6:] = 0
    steps = int(round(horizon / dt))
    switch_step = int(round(model['switch'] / dt))
    transitions = [affine_step(model['F'], forcing(model, d), dt) for d in (np.zeros(3), model['d'])]
    records = []
    for i in range(steps + 1):
        t = i * dt
        d = np.zeros(3) if i < switch_step else model['d']
        y, ym, command, actual = outputs(model, z)
        error = model['r'] - ym
        q = -z[0] - z[1] + z[2] + z[6] + 2 * z[7]
        records.append([t, t * scalar(card['time_scale_s']), *z, *y, *ym, *error,
                        *command, *actual, *d, q])
        if i == steps:
            break
        if model['limit'] is None:
            z = (transitions[0 if i < switch_step else 1] @ np.r_[z, 1.])[:8]
        else:
            # Switching is grid-aligned. One step uses the right-continuous forcing at its start.
            a = rhs(model, z, d)
            b = rhs(model, z + dt * a / 2, d)
            c = rhs(model, z + dt * b / 2, d)
            e = rhs(model, z + dt * c, d)
            z = z + dt * (a + 2*b + 2*c + e) / 6
        if not np.all(np.isfinite(z)) or np.max(np.abs(z)) > 1e8:
            raise ValueError('State exceeded finite teaching-model budget')
    eig = np.linalg.eigvals(model['active'])
    info = {'case': name, 'method': 'RK4 actual clipped input' if model['limit'] else 'piecewise affine expm',
            'active_state_dimension': len(model['active']),
            'poles': [[float(v.real), float(v.imag)] for v in eig],
            'matrices': {k: model[k].tolist() for k in ('A','B','C','K','L','Ki','F','ff')},
            'reference': model['r'].tolist(), 'bias': model['b'].tolist(),
            'final_y': y.tolist(), 'final_ym': ym.tolist(), 'final_error_ym': error.tolist(),
            'final_estimation_error': (z[:3]-z[3:6]).tolist(),
            'max_abs_u_actual': np.max(np.abs(np.asarray(records)[:, 18:20]), axis=0).tolist()}
    if name != 'dc_zero':
        f = forcing(model, model['d'])
        steady = np.r_[np.linalg.solve(-model['active'], f[:6]), [0,0]] if name == 'no_integral' else np.linalg.solve(-model['F'], f)
        sy, sm, su, _ = outputs({**model, 'limit': None}, steady)
        info.update(linear_equilibrium=steady.tolist(), linear_equilibrium_y=sy.tolist(),
                    linear_equilibrium_ym=sm.tolist(), linear_equilibrium_u=su.tolist(),
                    linear_equilibrium_residual=float(np.max(np.abs(model['F'] @ steady + f))),
                    final_distance_to_linear_equilibrium=float(np.max(np.abs(z-steady))))
        if model['limit'] is not None:
            info['linear_equilibrium_exceeds_input_limit'] = bool(np.max(np.abs(su)) > model['limit'])
            info['linear_equilibrium_is_actual_saturated_equilibrium'] = not info['linear_equilibrium_exceeds_input_limit']
            info['actual_rhs_at_linear_equilibrium_max'] = float(np.max(np.abs(rhs(model, steady, model['d']))))
    else:
        q0 = records[0][-1]
        info['q_invariant_error'] = float(max(abs(row[-1]-q0-row[0]) for row in records))
        info['linear_equilibrium'] = None
    return records, info


HEADER = ['tau','time_s', 'x1','x2','x3','hatx1','hatx2','hatx3','eta1','eta2',
          'y1','y2','ym1','ym2','error1','error2','u_cmd1','u_cmd2','u_actual1','u_actual2',
          'd1','d2','d3','q_bad']


def run(input_path, output_path):
    output = Path(output_path)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Refusing a nonempty output directory')
    card = load_card(input_path)
    rows_and_info = [simulate(card, name) for name in CASE_NAMES]
    summary = {'schema':'wwl-mimo-regulation-results-1', 'input_snapshot':card,
               'state_order':['x1','x2','x3','hatx1','hatx2','hatx3','eta1','eta2'],
               'main_exact_ranks':rational_diagnostics(card),
               'bad_port_exact_ranks':rational_diagnostics(card, True),
               'cases':{name:info for name, (_,info) in zip(CASE_NAMES,rows_and_info)}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.mimo-regulation-', dir=output.parent))
    try:
        for name, (rows, _) in zip(CASE_NAMES, rows_and_info):
            with (temporary / f'{name}.csv').open('w', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(HEADER)
                writer.writerows(rows)
        (temporary / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
        if output.exists():
            if any(output.iterdir()):
                raise ValueError('Output became nonempty; refusing publication')
            output.rmdir()
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.inputs, args.out)
    print(json.dumps({'output':str(args.out), 'cases':list(result['cases'])}))
