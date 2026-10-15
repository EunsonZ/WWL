#!/usr/bin/env python3
"""TE101 PEC-field perturbation for uniform, thick, normal conducting walls.
Only Python standard library. No finite-conductivity eigenmode or VNA model.
All input dimensions are SI; E/H phasors are peak amplitudes with exp(+i omega t).
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

C0 = 299792458.0
MU0 = 4 * math.pi * 1e-7  # approximate convention shared with lesson 07
EPS0 = 1 / (MU0 * C0**2)
FACE_NAMES = ('x0', 'xa', 'y0', 'yb', 'z0', 'zl')


def positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < sys.float_info.min:
        raise ValueError(f'{name} must be finite, positive and at least the minimum normal float')
    return float(value)


def integer(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in {lo}..{hi}')
    return value


def exact_keys(obj, keys, name):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError(f'{name} has missing or unknown fields')


def validate(inp):
    exact_keys(inp, ('base', 'variants', 'simpson_subintervals', 'decay_samples', 'sweep_samples'), 'input')
    exact_keys(inp['base'], ('a_m', 'b_m', 'length_m', 'sigma_S_per_m', 'wall_thickness_m', 'initial_energy_J'), 'base')
    for key, val in inp['base'].items():
        positive(val, key)
    n = integer(inp['simpson_subintervals'], 'simpson_subintervals', 8, 256)
    if n % 2:
        raise ValueError('Simpson requires even subintervals')
    integer(inp['decay_samples'], 'decay_samples', 3, 2001)
    integer(inp['sweep_samples'], 'sweep_samples', 3, 501)
    if not isinstance(inp['variants'], list) or len(inp['variants']) > 12:
        raise ValueError('variants must be a list with at most 12 cases')
    names = {'base'}
    for case in inp['variants']:
        exact_keys(case, ('name', 'sigma_ratio', 'all_dimensions_ratio', 'b_only_ratio'), 'variant')
        name = case['name']
        if not isinstance(name, str) or not name or not name.isascii() or not all(c.isalnum() or c == '_' for c in name) or name in names:
            raise ValueError('variant name must be unique ASCII letters/digits/underscores')
        names.add(name)
        for key in ('sigma_ratio', 'all_dimensions_ratio', 'b_only_ratio'):
            positive(case[key], key)


def transformed(base, sigma=1.0, scale=1.0, b_only=1.0):
    p = dict(base)
    for k in ('a_m', 'b_m', 'length_m', 'wall_thickness_m'):
        p[k] *= scale
    p['b_m'] *= b_only
    p['sigma_S_per_m'] *= sigma
    return p


def analytic(p):
    for name, value in p.items():
        positive(value, name)
    a, b, ell = p['a_m'], p['b_m'], p['length_m']
    if not b < min(a, ell):
        raise ValueError('this teaching model requires b < min(a, length): isolated lowest TE101')
    sigma, W = p['sigma_S_per_m'], p['initial_energy_J']
    kx, kz = math.pi/a, math.pi/ell
    K2 = kx*kx + kz*kz
    omega = C0 * math.sqrt(K2)
    delta = math.sqrt(2/(omega*MU0*sigma))
    Rs = 1/(sigma*delta)
    Ec = math.sqrt(8*W/(EPS0*a*b*ell))
    C = Ec/(omega*MU0)
    I = (C*C*kx*kx*b*ell/2, C*C*a*ell*K2/4, C*C*kz*kz*a*b/2)
    face_integrals = dict(zip(FACE_NAMES, (I[0], I[0], I[1], I[1], I[2], I[2])))
    face_power = {k: Rs*val/2 for k, val in face_integrals.items()}
    P = sum(face_power.values())
    Q = omega*W/P
    ky = math.pi/b
    competitors = {'TE011': C0*math.sqrt(ky*ky+kz*kz),
                   'TM110': C0*math.sqrt(kx*kx+ky*ky),
                   'TE201': C0*math.sqrt(4*kx*kx+kz*kz),
                   'TE102': C0*math.sqrt(kx*kx+4*kz*kz)}
    next_name = min(competitors, key=competitors.get)
    mode_gap = competitors[next_name]-omega
    gap_in_decay_rates = mode_gap/(omega/Q)
    eta = omega*EPS0/sigma
    d_ratio = delta/min(a, b, ell)
    t_ratio = p['wall_thickness_m']/delta
    # These named screening thresholds are a teaching choice, not rigorous error bounds.
    screens = {'good_conductor_eta_lt_1e-3': eta < 1e-3,
               'thin_skin_delta_over_min_dimension_lt_1e-3': d_ratio < 1e-3,
               'thick_wall_t_over_delta_gt_10': t_ratio > 10,
               'weak_loss_Q_gt_100': Q > 100,
               'mode_gap_in_energy_decay_rates_gt_10': gap_in_decay_rates > 10}
    result = {'parameters': p, 'omega_rad_per_s': omega, 'frequency_Hz': omega/(2*math.pi),
              'kx_per_m': kx, 'kz_per_m': kz, 'electric_peak_V_per_m': Ec,
              'delta_m': delta, 'surface_resistance_ohm': Rs,
              'face_Ht_squared_integrals_A2': face_integrals, 'face_power_W': face_power,
              'total_wall_power_W': P, 'Q_wall': Q, 'geometry_factor_ohm': Q*Rs,
              'energy_time_constant_s': Q/omega, 'amplitude_time_constant_s': 2*Q/omega,
              'energy_loss_per_period_fraction_leading_order': 2*math.pi/Q,
              'omega_epsilon_over_sigma': eta, 'delta_over_min_dimension': d_ratio,
              'wall_thickness_over_delta': t_ratio,
              'nearest_competing_PEC_mode': next_name,
              'nearest_competing_omega_rad_per_s': competitors[next_name],
              'mode_gap_rad_per_s': mode_gap,
              'mode_gap_over_energy_decay_rate': gap_in_decay_rates,
              'approximation_screens': screens}
    if not all(screens.values()):
        raise ValueError('case fails declared approximation screens; solve a more complete model')
    return result


def simpson2(fn, L1, L2, n):
    def weight(i):
        return 1 if i in (0, n) else 4 if i % 2 else 2
    return L1*L2/(9*n*n)*math.fsum(
        weight(i)*weight(j)*fn(L1*i/n, L2*j/n) for i in range(n+1) for j in range(n+1))


def quadrature(v, n):
    p = v['parameters']; a, b, ell = p['a_m'], p['b_m'], p['length_m']
    kx, kz, w = v['kx_per_m'], v['kz_per_m'], v['omega_rad_per_s']
    E = v['electric_peak_V_per_m']; C = E/(w*MU0)
    def field_squares(x, z):
        ey2 = (E*math.sin(kx*x)*math.sin(kz*z))**2
        hx2 = (C*kz*math.sin(kx*x)*math.cos(kz*z))**2
        hz2 = (C*kx*math.cos(kx*x)*math.sin(kz*z))**2
        return ey2, hx2, hz2
    # Restrict the actual vector fields to each face; exclude normal H.
    ix0 = simpson2(lambda y,z: field_squares(0,z)[2], b, ell, n)
    ixa = simpson2(lambda y,z: field_squares(a,z)[2], b, ell, n)
    iy = simpson2(lambda x,z: sum(field_squares(x,z)[1:]), a, ell, n)
    iz0 = simpson2(lambda x,y: field_squares(x,0)[1], a, b, n)
    izl = simpson2(lambda x,y: field_squares(x,ell)[1], a, b, n)
    faces = dict(zip(FACE_NAMES, (ix0, ixa, iy, iy, iz0, izl)))
    UE = EPS0*b/4 * simpson2(lambda x,z: field_squares(x,z)[0], a, ell, n)
    UH = MU0*b/4 * simpson2(lambda x,z: sum(field_squares(x,z)[1:]), a, ell, n)
    P = v['surface_resistance_ohm']/2 * sum(faces.values())
    return {'subintervals_per_direction': n, 'face_Ht_squared_integrals_A2': faces,
            'electric_time_average_energy_J': UE, 'magnetic_time_average_energy_J': UH,
            'total_wall_power_W': P, 'Q_wall': w*(UE+UH)/P,
            'face_relative_errors': {k: faces[k]/v['face_Ht_squared_integrals_A2'][k]-1 for k in faces},
            'total_energy_relative_error': (UE+UH)/p['initial_energy_J']-1,
            'power_relative_error': P/v['total_wall_power_W']-1}


def csv_write(path, keys, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def svg_start(title, desc, height=450):
    from html import escape
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {height}" role="img">',
            f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>',
            '<rect width="900" height="100%" fill="white"/>',
            '<g font-family="sans-serif" font-size="15" fill="#202020">',
            f'<text x="32" y="30" font-size="21">{escape(title)}</text>']


def line_chart(parts, box, xmin, xmax, ymin, ymax, series, xlabel, ylabel):
    x,y,width,height=box
    sx=lambda t:x+width*(t-xmin)/(xmax-xmin)
    sy=lambda t:y+height-height*(t-ymin)/(ymax-ymin)
    parts.append(f'<path d="M{x},{y} V{y+height} H{x+width}" fill="none" stroke="#222"/>')
    for i in range(5):
        tx=xmin+(xmax-xmin)*i/4; ty=ymin+(ymax-ymin)*i/4
        parts += [f'<text x="{sx(tx):.1f}" y="{y+height+23}" text-anchor="middle">{tx:.2g}</text>',
                  f'<text x="{x-8}" y="{sy(ty)+5:.1f}" text-anchor="end">{ty:.2g}</text>']
    parts += [f'<text x="{x+width/2}" y="{y+height+49}" text-anchor="middle">{xlabel}</text>',
              f'<text x="{x}" y="{y-17}">{ylabel}</text>']
    for index,(label,color,dash,points) in enumerate(series):
        data=' '.join(f'{sx(px):.3f},{sy(py):.3f}' for px,py in points)
        parts.append(f'<polyline points="{data}" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="{dash}"/>')
        ly=y+height+75+index*23
        parts += [f'<line x1="{x}" x2="{x+35}" y1="{ly-5}" y2="{ly-5}" stroke="{color}" stroke-width="3" stroke-dasharray="{dash}"/>',f'<text x="{x+44}" y="{ly}">{label}</text>']


def write_figures(out, cases, decay, sweep):
    base=cases['base']; q0=base['Q_wall']; tau=base['energy_time_constant_s']
    p=svg_start('TE101: loss on all six walls', 'Each bar is one wall. Peak H phasors use P=Rs integral |Ht|^2 /2. Areas are in mm^2; powers are in mW.', 490)
    maxp=max(base['face_power_W'].values())
    dims=base['parameters']; areas=(dims['b_m']*dims['length_m'],dims['a_m']*dims['length_m'],dims['a_m']*dims['b_m'])
    for i,name in enumerate(FACE_NAMES):
        power=base['face_power_W'][name]; y=72+i*54; length=530*power/maxp
        p += [f'<text x="30" y="{y+20}">{name}</text>',f'<rect x="95" y="{y}" width="{length:.3f}" height="27" fill="#246a88"/>',
              f'<text x="{110+length:.3f}" y="{y+20}">{1000*power:.6f} mW; {1e6*areas[i//2]:.0f} mm²</text>']
    p += [f'<text x="30" y="421">Sum = {1000*base["total_wall_power_W"]:.6f} mW; W0 = {1e9*dims["initial_energy_J"]:.6g} nJ</text>',
          '<text x="30" y="452">x0/xa: Hz; y0/yb: Hx and Hz; z0/zl: Hx. Two walls per pair.</text>','</g></svg>']
    (out/'wall-loss.svg').write_text('\n'.join(p)+'\n',encoding='utf-8')
    p=svg_start('Ringdown: energy and field amplitude', 'Slow envelopes only, not the GHz carrier. Lines are from decay.csv. Energy and amplitude have different e-folding times.', 510)
    for x,key,label in ((78,'energy_ratio','W(t)/W0'),(505,'amplitude_ratio','A(t)/A0')):
        series=[]
        for name,color,dash in (('base','#246a88',''),('sigma_quarter','#a74b18','7 4')):
            if name in cases:
                rows=[r for r in decay if r['case']==name]
                series.append((name,color,dash,[(r['time_s']*1e6,r[key]) for r in rows]))
        line_chart(p,(x,85,310,270),0,3*tau*1e6,0,1,series,'time (µs)',label)
    p += ['<text x="32" y="491">Peak phasors: A(t)/A0 = sqrt(W(t)/W0); oscillations are not drawn.</text>','</g></svg>']
    (out/'ringdown.svg').write_text('\n'.join(p)+'\n',encoding='utf-8')
    p=svg_start('Change a condition, then recompute Q', 'Same initial energy, uniform normal conductor. Left varies sigma; right compares uniform geometric scale with varying b alone. Points are from scaling.csv.', 535)
    series=[('sigma only: sqrt(r)','#246a88','',[(r['ratio'],r['Q_ratio']) for r in sweep if r['change']=='sigma'])]
    line_chart(p,(78,90,310,265),.25,4,0,2.2,series,'sigma / sigma0','Q / Q0')
    series=[]
    for change,label,color,dash in (('all_dimensions','all dimensions: sqrt(s)','#246a88',''),('b_only','b alone: saturates','#a74b18','7 4')):
        series.append((label,color,dash,[(r['ratio'],r['Q_ratio']) for r in sweep if r['change']==change]))
    line_chart(p,(505,90,310,265),.5,2,0,1.6,series,'dimension ratio s','Q / Q0')
    p += [f'<text x="32" y="510">Base Q = {q0:.6f}; all-dimension scaling also scales wall thickness.</text>','</g></svg>']
    (out/'q-scaling.svg').write_text('\n'.join(p)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    inp=json.loads(args.input.read_text(encoding='utf-8'))
    validate(inp)
    n=inp['simpson_subintervals']
    cases={'base':analytic(inp['base'])}
    for case in inp['variants']:
        cases[case['name']]=analytic(transformed(inp['base'],case['sigma_ratio'],case['all_dimensions_ratio'],case['b_only_ratio']))
    for v in cases.values():
        v['quadrature']=quadrature(v,n)
    tau=cases['base']['energy_time_constant_s']; decay=[]
    for name,v in cases.items():
        for i in range(inp['decay_samples']):
            t=3*tau*i/(inp['decay_samples']-1)
            energy=math.exp(-t/v['energy_time_constant_s'])
            decay.append({'case':name,'time_s':t,'energy_ratio':energy,'amplitude_ratio':math.sqrt(energy),
                          'energy_J':v['parameters']['initial_energy_J']*energy,'wall_power_W':v['total_wall_power_W']*energy})
    sweep=[]
    for change,lo,hi in (('sigma',.25,4),('all_dimensions',.5,2),('b_only',.5,1.5)):
        for i in range(inp['sweep_samples']):
            r=lo+(hi-lo)*i/(inp['sweep_samples']-1)
            v=analytic(transformed(inp['base'],sigma=r if change=='sigma' else 1,scale=r if change=='all_dimensions' else 1,b_only=r if change=='b_only' else 1))
            sweep.append({'change':change,'ratio':r,'frequency_Hz':v['frequency_Hz'],'Q_wall':v['Q_wall'],
                          'Q_ratio':v['Q_wall']/cases['base']['Q_wall'],'energy_time_constant_s':v['energy_time_constant_s']})
    result={'model':'TE101 fixed PEC mode, thick normal conductor, weak-loss surface perturbation',
            'phasors':'peak exp(+i omega t)', 'constants':{'c0_m_per_s':C0,'mu0_H_per_m_approx':MU0,'epsilon0_F_per_m_derived':EPS0},
            'input':inp,'cases':cases}
    # Validate all derived values before mkdir, including CSV-only data.
    for rows in (decay, sweep):
        for row in rows:
            for value in row.values():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    raise ValueError('derived CSV value is outside finite float range')
    serialized=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    # Never replace a reference directory.
    args.output_dir.mkdir(parents=True,exist_ok=False)
    out=args.output_dir
    (out/'values.json').write_text(serialized,encoding='utf-8')
    csv_write(out/'decay.csv',list(decay[0]),decay)
    csv_write(out/'scaling.csv',list(sweep[0]),sweep)
    write_figures(out,cases,decay,sweep)
    print(serialized,end='')


if __name__=='__main__':
    try:
        main()
    except (ValueError, OSError, ArithmeticError) as exc:
        raise SystemExit(f'input/output rejected: {exc}')
