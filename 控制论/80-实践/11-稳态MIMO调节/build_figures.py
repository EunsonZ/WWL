#!/usr/bin/env python3
"""Draw continuous-time teaching traces from this run's CSV and parameter snapshot."""
from __future__ import annotations
import argparse
import csv
import html
import json
import math
from pathlib import Path

COLORS = ['#1768ac', '#cf4b27', '#237a57', '#9143a0', '#92682e', '#566470']


def number(value):
    from fractions import Fraction
    result = float(Fraction(str(value)))
    if not math.isfinite(result):
        raise ValueError('Nonfinite metadata')
    return result


def read_csv(path):
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        rows = [{k: float(v) for k,v in row.items()} for row in reader]
    if len(rows) < 2 or any(not math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError('Need finite multi-point CSV')
    if any(a['tau'] >= b['tau'] for a,b in zip(rows,rows[1:])):
        raise ValueError('Time must strictly increase')
    return rows


def curve(rows, key, label, dashed=False):
    get = key if callable(key) else lambda row: row[key]
    return {'label':label, 'dashed':dashed,
            'points':[(row['tau'], get(row)) for row in rows]}


def panel(curves, title, ylabel):
    return dict(curves=curves, title=title, ylabel=ylabel)


def svg_document(panels, title, time_scale_s):
    width, ph, header = 1000, 284, 72
    height = header + ph*len(panels) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#fff"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#24323e} .tick{font-size:12px}.label{font-size:14px}</style>',
           f'<text x="72" y="30" font-size="22">{html.escape(title)}</text>',
           f'<text x="72" y="52" font-size="13">Normalized continuous LTI; tau=t/({time_scale_s:g} s). CSV spacing is not controller sampling.</text>']
    for index,p in enumerate(panels):
        ox, oy, pw, plot_h = 82, header+index*ph+40, 870, 154
        allpoints = [point for c in p['curves'] for point in c['points']]
        tx0,tx1 = min(t for t,v in allpoints),max(t for t,v in allpoints)
        vy0,vy1 = min(v for t,v in allpoints),max(v for t,v in allpoints)
        span = max(vy1-vy0,.1)
        ymin,ymax = vy0-.09*span,vy1+.09*span
        project = lambda t,v: (ox+pw*(t-tx0)/(tx1-tx0),oy+plot_h*(ymax-v)/(ymax-ymin))
        out.append(f'<text x="{ox}" y="{oy-23}" font-size="16">{html.escape(p["title"])}</text>')
        out.append(f'<text x="12" y="{oy+18}" class="label">{html.escape(p["ylabel"])}</text>')
        for j in range(5):
            v = ymin+(ymax-ymin)*j/4
            py = project(tx0,v)[1]
            out.append(f'<path d="M {ox} {py:.3f} H {ox+pw}" stroke="#e2e7ed" fill="none"/>')
            out.append(f'<text x="{ox-8}" y="{py+4:.3f}" text-anchor="end" class="tick">{v:.3g}</text>')
        for j in range(6):
            t = tx0+(tx1-tx0)*j/5
            px = project(t,ymin)[0]
            out.append(f'<text x="{px:.3f}" y="{oy+plot_h+17}" text-anchor="middle" class="tick">{t:.3g}</text>')
        out.append(f'<rect x="{ox}" y="{oy}" width="{pw}" height="{plot_h}" stroke="#6d7985" fill="none"/>')
        out.append(f'<text x="{ox+pw}" y="{oy+plot_h+34}" text-anchor="end" class="label">tau</text>')
        patterns = ['', '8 4', '2 3', '10 3 2 3', '4 3 2 3', '1 3']
        if p['curves'][0]['dashed']:
            patterns[0], patterns[1] = patterns[1], patterns[0]
        for j,c in enumerate(p['curves']):
            color = COLORS[j%len(COLORS)]
            points = ' '.join(f'{px:.3f},{py:.3f}' for px,py in (project(t,v) for t,v in c['points']))
            dash = f' stroke-dasharray="{patterns[j]}"' if patterns[j] else ''
            out.append(f'<polyline data-label="{html.escape(c["label"],quote=True)}" points="{points}" stroke="{color}" stroke-width="1.8" fill="none"{dash}/>')
            lx = ox+(j%3)*285
            ly = oy+plot_h+51+(j//3)*18
            out.append(f'<path d="M {lx} {ly-4} h 23" stroke="{color}" stroke-width="2"{dash}/>')
            out.append(f'<text x="{lx+29}" y="{ly}" font-size="12">{html.escape(c["label"])}</text>')
    out.append('</svg>')
    return '\n'.join(out)+'\n'


def build(results):
    results = Path(results)
    targets = [results/'tracking.svg', results/'boundaries.svg']
    if any(p.exists() for p in targets):
        raise ValueError('Refusing to overwrite existing SVG')
    meta = json.loads((results/'summary.json').read_text())
    if meta['schema'] != 'wwl-mimo-regulation-results-1':
        raise ValueError('Unexpected results schema')
    names = ('disturbance','no_integral','slow_integral','fast_integral','sensor_bias','dc_zero','saturation')
    data = {name:read_csv(results/f'{name}.csv') for name in names}
    ref = [number(v) for v in meta['input_snapshot']['reference']]
    snap = meta['input_snapshot']
    norm_error = lambda row: max(abs(row['error1']),abs(row['error2']))
    tracking = [
        panel([curve(data['disturbance'],'y1','Integral y1'), curve(data['disturbance'],'y2','Integral y2'),
               curve(data['disturbance'],lambda row:ref[0],f'r1={ref[0]:g}',True),
               curve(data['disturbance'],lambda row:ref[1],f'r2={ref[1]:g}',True)],
              f'Unknown d starts at tau={number(snap["disturbance_switch_tau"]):g}; both targets retained','y'),
        panel([curve(data['no_integral'],'error1','No integral error1'),curve(data['no_integral'],'error2','No integral error2'),
               curve(data['disturbance'],'error1','Integral error1'),curve(data['disturbance'],'error2','Integral error2')],
              'Nominally calibrated feedforward leaves disturbance error','r-ym'),
        panel([curve(data[name],norm_error,f'kappa={meta["cases"][name]["matrices"]["Ki"][0][0]:g}')
               for name in ('slow_integral','disturbance','fast_integral')],
              'Integral gain changes transient; finite horizon is not exact settling','max|err|')]
    q0 = data['dc_zero'][0]['q_bad']
    boundaries = [
        panel([curve(data['dc_zero'],'q_bad','Actual q'),curve(data['dc_zero'],lambda row:q0+row['tau'],'q0+tau',True)],
              'Fixed bad output port: incompatible r=(1,0), d=0; q grows for every control law','q'),
        panel([curve(data['sensor_bias'],key,label,dash) for key,label,dash in
               [('y1','True y1',False),('ym1','Measured ym1',True),('y2','True y2',False),('ym2','Measured ym2',True)]],
              f'Sensor bias b={meta["cases"]["sensor_bias"]["bias"]}; measured target does not calibrate sensor','y,ym'),
        panel([curve(data['saturation'],'u_cmd1','Command u1'),curve(data['saturation'],'u_cmd2','Command u2')],
              'Command action: its own vertical scale keeps saturation visible','u_cmd'),
        panel([curve(data['saturation'],'u_actual1','Actual u1'),curve(data['saturation'],'u_actual2','Actual u2')],
              f'Actual inputs clipped at +/-{number(snap["input_limit"]):g}; observer receives actual action','u_act'),
        panel([curve(data['saturation'],'eta1','Integral eta1'),curve(data['saturation'],'eta2','Integral eta2')],
              ('Infeasible linear equilibrium: integral states in clipped dynamics; no antiwindup'
               if meta['cases']['saturation']['linear_equilibrium_exceeds_input_limit']
               else 'Linear equilibrium fits limit: clipped transient still requires separate analysis'), 'eta')]
    t0 = number(snap['time_scale_s'])
    documents = [svg_document(tracking,'MIMO constant regulation: memory and transient',t0),
                 svg_document(boundaries,'MIMO regulation boundaries: DC zero, bias and saturation',t0)]
    created = []
    try:
        for path,document in zip(targets,documents):
            with path.open('x') as handle:
                created.append(path)
                handle.write(document)
    except Exception:
        for path in created:
            path.unlink()
        raise
    return targets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    args = parser.parse_args()
    print('\n'.join(str(p) for p in build(args.results)))
