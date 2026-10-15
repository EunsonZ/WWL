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
