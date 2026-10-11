#!/usr/bin/env python3
"""SI sheet-current pulse plus compatible initial free pulse; standard library.

All integrals are per transverse area. At z=0, integrate each one-sided
field separately; only the force on the sheet uses the mean magnetic field.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import time


def pulse(s):
    return math.sin(math.pi * s) ** 4 if 0.0 < s < 1.0 else 0.0


def static(zeta):
    return (1.0 - 4.0 * zeta * zeta) ** 3 if abs(zeta) < 0.5 else 0.0


def static_prime(zeta):
    return -24.0 * zeta * (1.0 - 4.0 * zeta * zeta) ** 2 if abs(zeta) < 0.5 else 0.0


def simpson(values, step):
    n = len(values) - 1
    if n <= 0 or n % 2:
        raise ValueError('Simpson needs a positive even interval count')
    return step / 3.0 * math.fsum(v * (1 if i in (0, n) else 4 if i % 2 else 2)
                                  for i, v in enumerate(values))


def field(zeta, tau, alpha, qratio, side=None):
    # components divided by E0, with magnetic component represented as c B/E0
    sign = side if zeta == 0.0 and side is not None else (1 if zeta >= 0.0 else -1)
    sourced = pulse(tau - abs(zeta))
    free = alpha * pulse(tau - zeta)
    return -sourced + free, qratio * static(zeta), -sign * sourced + free


def trace(p, alpha, nx, nt):
    length, qratio = p['control_half_length_in_cT'], p['static_Eq_V_per_m'] / p['wave_E0_V_per_m']
    dz = length / nx
    t0, t1 = p['tau_start'], p['tau_end']
    dt = (t1 - t0) / nt
    grids = [([(-length + i * dz) if side == -1 else i * dz for i in range(nx + 1)], side)
             for side in (-1, 1)]
    result = []
    for it in range(nt + 1):
        tau = t0 + it * dt
        sums = [0.0] * 6
        for zetas, side in grids:
            columns = [[] for _ in sums]
            for z in zetas:
                ex, ez, b = field(z, tau, alpha, qratio, side)
                esx, _, bs = field(z, tau, 0.0, qratio, side)
                hf = alpha * pulse(tau - z)
                # U/(eps E0^2 cT), Pz/(eps E0^2 T), Px likewise,
                # cross-U between sourced transverse and free field,
                # volume Fx/(eps E0^2), volume Fz/(eps E0^2).
                values = ((ex * ex + ez * ez + b * b) / 2.0,
                          ex * b, -ez * b, esx * hf + bs * hf,
                          qratio * static_prime(z) * ex,
                          qratio * static_prime(z) * ez)
                for col, val in zip(columns, values):
                    col.append(val)
            sums = [a + simpson(col, dz) for a, col in zip(sums, columns)]
        el, zl, bl = field(-length, tau, alpha, qratio)
        er, zr, br = field(length, tau, alpha, qratio)
        f = pulse(tau)
        # sheet K=2 E0/Z0 F; mean cB/E0 = alpha F.
        sheet_e = field(0.0, tau, alpha, qratio, 1)[0]
        sheet_b_avg = (field(0.0, tau, alpha, qratio, -1)[2] +
                       field(0.0, tau, alpha, qratio, 1)[2]) / 2.0
        source_to_field = -2.0 * f * sheet_e
        sheet_force_z = 2.0 * f * sheet_b_avg
        flux = er * br - el * bl
        stress_z = (zr * zr - er * er - br * br - zl * zl + el * el + bl * bl) / 2.0
        stress_x = er * zr - el * zl
        cross_flux = -2.0 * alpha * pulse(tau - length) ** 2
        result.append([tau, *sums[:4], flux, source_to_field, stress_z,
                       sums[4], sums[5] + sheet_force_z, stress_x, cross_flux])
    # independent time differences of spatially integrated stored fields
    rate_errors = [[], [], []]
    for i in range(2, nt - 1):
        derivative = lambda col: (result[i-2][col] - 8*result[i-1][col] +
                                  8*result[i+1][col] - result[i+2][col]) / (12*dt)
        rate_errors[0].append(derivative(1) + result[i][5] - result[i][6])
        rate_errors[1].append(derivative(2) - result[i][7] + result[i][9])
        rate_errors[2].append(derivative(3) - result[i][10] + result[i][8])
    integ = lambda col: simpson([r[col] for r in result], dt)
    errors = {
        'energy_integral_normalized': result[-1][1] - result[0][1] + integ(5) - integ(6),
        'momentum_z_integral_normalized': result[-1][2] - result[0][2] - integ(7) + integ(9),
        'momentum_x_integral_normalized': result[-1][3] - result[0][3] - integ(10) + integ(8),
        'cross_energy_integral_normalized': result[-1][4] - result[0][4] + integ(11) +
                                               2*alpha*simpson([pulse(r[0])**2 for r in result], dt),
        'energy_rate_max_normalized': max(map(abs, rate_errors[0])),
        'momentum_z_rate_max_normalized': max(map(abs, rate_errors[1])),
        'momentum_x_rate_max_normalized': max(map(abs, rate_errors[2])),
    }
    eps, E0, T, c = (p[k] for k in ('epsilon0_F_per_m', 'wave_E0_V_per_m', 'pulse_T_s', 'c_m_per_s'))
    energy_scale, momentum_scale = eps*E0*E0*c*T, eps*E0*E0*T
    summary = {'alpha': alpha, 'initial_control_energy_J_per_m2': result[0][1]*energy_scale,
               'final_control_energy_J_per_m2': result[-1][1]*energy_scale,
               'net_outward_energy_J_per_m2': integ(5)*energy_scale,
               'source_to_field_work_J_per_m2': integ(6)*energy_scale,
               'matter_work_J_per_m2': -integ(6)*energy_scale,
               'initial_field_momentum_z_N_s_per_m2': result[0][2]*momentum_scale,
               'stress_impulse_z_N_s_per_m2': integ(7)*momentum_scale,
               'matter_impulse_z_N_s_per_m2': integ(9)*momentum_scale,
               'matter_impulse_x_N_s_per_m2': integ(8)*momentum_scale,
               'cross_outward_energy_J_per_m2': integ(11)*energy_scale,
               'errors': errors}
    return result, summary


def local_checks(p):
    # Finite differences of fields away from the distributional current sheet.
    q = p['static_Eq_V_per_m'] / p['wave_E0_V_per_m']
    d = 1e-4
    maxwell, energy = [], []
    for z in (-0.31, 0.17, 0.67):
        for tau in (0.25, 0.6, 1.3, 2.4):
            ex, ez, b = field(z, tau, 1.0, q)
            zp, zm = field(z+d, tau, 1.0, q), field(z-d, tau, 1.0, q)
            tp, tm = field(z, tau+d, 1.0, q), field(z, tau-d, 1.0, q)
            ex_z, b_z, ez_z = ((zp[i]-zm[i])/(2*d) for i in (0, 2, 1))
            ex_t, b_t = ((tp[i]-tm[i])/(2*d) for i in (0, 2))
            maxwell.extend((ex_z+b_t, b_z+ex_t, ez_z-q*static_prime(z)))
            u = lambda v: (v[0]**2+v[1]**2+v[2]**2)/2
            s = lambda v: v[0]*v[2]
            energy.append((u(tp)-u(tm)+s(zp)-s(zm))/(2*d))
    f = pulse(0.5)
    left = field(0.0, 0.5, 1.0, q, -1)[2]
    right = field(0.0, 0.5, 1.0, q, 1)[2]
    return {'finite_difference_step_dimensionless': d,
            'away_from_sheet_Maxwell_max_normalized': max(map(abs,maxwell)),
            'away_from_sheet_Poynting_max_normalized': max(map(abs,energy)),
            'sheet_Ampere_jump_normalized': -(right-left)-2*f,
            'source_field_before_lightcone_at_zeta_0_67_tau_0_25': pulse(0.25-0.67),
            'charge_rho_C_per_m3_at_zeta_0_25': p['epsilon0_F_per_m']*p['static_Eq_V_per_m']/(p['c_m_per_s']*p['pulse_T_s'])*static_prime(0.25),
            'invalid_zero_E_Gauss_residual_at_zeta_0_25_normalized': -q*static_prime(0.25)}


def svg_plot(path, title, subtitle, panels, time_ns):
    colors = ['#1767aa', '#dc6825', '#7131a1', '#168058']
    width, height = 940, 160 + len(panels)*245
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<style>text{font-family:Arial, sans-serif;fill:#253342;font-size:15px}.title{font-size:22px;font-weight:bold}.small{font-size:13px}</style>',
             f'<text x="35" y="35" class="title">{title}</text>', f'<text x="35" y="62">{subtitle}</text>']
    for ip, (label, datasets) in enumerate(panels):
        ytop, x0, x1, plot_h = 125 + ip*245, 85, 885, 165
        xs = [x for _,xy in datasets for x,y in xy]
        ys = [y for _,xy in datasets for x,y in xy]
        xmin, xmax = min(xs), max(xs)
        lo, hi = min(0,min(ys)), max(0,max(ys))
        span = hi-lo or 1
        lo -= .08*span; hi += .12*span
        tx = lambda x: x0+(x-xmin)/(xmax-xmin)*(x1-x0)
        ty = lambda y: ytop+plot_h-(y-lo)/(hi-lo)*plot_h
        parts.append(f'<text x="35" y="{ytop-18}">{label}</text>')
        for j in range(5):
            y=lo+(hi-lo)*j/4
            parts.append(f'<line x1="{x0}" y1="{ty(y):.2f}" x2="{x1}" y2="{ty(y):.2f}" stroke="#e3e9ef"/>')
            parts.append(f'<text x="{x0-8}" y="{ty(y)+4:.2f}" text-anchor="end" class="small">{y:.3g}</text>')
        for j in range(6):
            x=xmin+(xmax-xmin)*j/5
            parts.append(f'<text x="{tx(x):.2f}" y="{ytop+plot_h+21}" text-anchor="middle" class="small">{x:.3g}</text>')
        parts.append(f'<line x1="{x0}" y1="{ty(0):.2f}" x2="{x1}" y2="{ty(0):.2f}" stroke="#667"/>')
        for j,(name,xy) in enumerate(datasets):
            pts=' '.join(f'{tx(x):.2f},{ty(y):.2f}' for x,y in xy)
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors[j]}" stroke-width="2"/>')
            parts.append(f'<text x="{x0+j*200}" y="{ytop+plot_h+46}" style="fill:{colors[j]}" class="small">{name}</text>')
    parts.append(f'<text x="885" y="{height-14}" text-anchor="end">time tau = t/T; T = {time_ns:g} ns</text></svg>')
    path.write_text('\n'.join(parts),encoding='utf8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    start=time.monotonic()
    p=json.loads(args.inputs.read_text())
    if any(not math.isfinite(float(p[k])) or p[k]<=0 for k in
           ('c_m_per_s','epsilon0_F_per_m','pulse_T_s','wave_E0_V_per_m','control_half_length_in_cT')):
        raise ValueError('positive finite scales required')
    nx,nt=p['space_intervals_per_half'],p['time_intervals']
    if not isinstance(nx,int) or not isinstance(nt,int) or nx%4 or nt%4 or nx<8 or nt<8 or nx>1000 or nt>5000:
        raise ValueError('grid counts must be multiples of 4: 8..1000 and 8..5000')
    if p['control_half_length_in_cT']<2 or p['tau_start']!=-1 or p['tau_end']<p['control_half_length_in_cT']+1:
        raise ValueError('control layer must contain the whole initial packet and wait for emission to leave')
    if not math.isfinite(p['static_Eq_V_per_m']) or not 1<=len(p['free_amplitudes'])<=8 or any(not math.isfinite(a) for a in p['free_amplitudes']):
        raise ValueError('finite charge scale and 1..8 finite free amplitudes required')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'assets').mkdir()
    w=p['epsilon0_F_per_m']*p['c_m_per_s']*p['wave_E0_V_per_m']**2*p['pulse_T_s']*35/128
    data,summaries,coarse={},{},{}
    header=['tau','U_over_epsE02cT','Pz_over_epsE02T','Px_over_epsE02T','Ucross_over_epsE02cT',
            'outward_S_over_epscE02','source_power_to_field_over_epscE02','net_stress_z_over_epsE02',
            'matter_force_x_over_epsE02','matter_force_z_over_epsE02','net_stress_x_over_epsE02','cross_outward_S_over_epscE02']
    for i,alpha in enumerate(p['free_amplitudes']):
        rows,summ=trace(p,alpha,nx,nt)
        _,cs=trace(p,alpha,nx//2,nt//2)
        name=f'case-{i}'
        data[name]=rows; summaries[name]=summ; coarse[name]=cs
        with (args.output/(name+'.csv')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(header);writer.writerows(rows)
        analytic_work=(2-2*alpha)*w
        summ['analytic_source_to_field_work_J_per_m2']=analytic_work
        summ['analytic_matter_impulse_z_N_s_per_m2']=2*alpha*w/p['c_m_per_s']
        summ['source_work_relative_to_one_pulse_error']=(summ['source_to_field_work_J_per_m2']-analytic_work)/w
        summ['coarse_to_fine_max_rate_error']={k:[cs['errors'][k],v] for k,v in summ['errors'].items() if '_rate_' in k}
    cases=[(f'alpha={summaries[k]["alpha"]:g}',[(r[0],r[1]) for r in rows]) for k,rows in data.items()]
    cross=[(f'alpha={summaries[k]["alpha"]:g}',[(r[0],r[4]) for r in rows]) for k,rows in data.items()]
    svg_plot(args.output/'assets'/'initial-superposition.svg','Same source, different compatible initial fields',
             'Fixed sheet K(t) and static rho(z); only free amplitude alpha changes.',
             [('Control energy U/(epsilon0 E0^2 cT), including static field',cases),('Interference energy U_cross/(epsilon0 E0^2 cT)',cross)],p['pulse_T_s']*1e9)
    # One actual case: nonzero source injection and nonzero sheet impulse.
    key=next((k for k in data if summaries[k]['alpha']==2),next(iter(data)))
    rows=data[key];dt=(p['tau_end']-p['tau_start'])/nt
    rates=[(rows[i+1][1]-rows[i-1][1])/(2*dt) for i in range(1,nt)]
    svg_plot(args.output/'assets'/'poynting-momentum.svg',f'Finite control layer; alpha={summaries[key]["alpha"]:g}',
             f'Layer -{p["control_half_length_in_cT"]:g} cT &lt; z &lt; {p["control_half_length_in_cT"]:g} cT; all curves use the same fields.',
             [('Energy rates / (epsilon0 c E0^2)',[
                 ('stored dU/dt',[(rows[i][0],rates[i-1]) for i in range(1,nt)]),
                 ('outward flux',[(r[0],r[5]) for r in rows]),
                 ('source to field',[(r[0],r[6]) for r in rows])]),
              ('z momentum rates / (epsilon0 E0^2)',[
                 ('net stress traction',[(r[0],r[7]) for r in rows]),
                 ('matter force',[(r[0],r[9]) for r in rows]),
                 ('stored dPz/dt',[(rows[i][0],(rows[i+1][2]-rows[i-1][2])/(2*dt)) for i in range(1,nt)])])],p['pulse_T_s']*1e9)
    result={'model':'vacuum, infinite plane symmetry, finite z control layer; all extensive values per area',
            'inputs':p,'derived_mu0_H_per_m':1/(p['epsilon0_F_per_m']*p['c_m_per_s']**2),
            'one_travelling_pulse_energy_J_per_m2':w,
            'local_checks':local_checks(p),'cases':summaries,'coarse_grid_cases':coarse,
            'elapsed_s':time.monotonic()-start,'execution':'author run, one process, Python standard library'}
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    for k,s in summaries.items():
        if max(abs(s['errors'][e]) for e in s['errors'] if '_integral_' in e)>2e-5:
            raise RuntimeError(f'integral residual above bound: {k}')
        if max(abs(v) for e,v in s['errors'].items() if '_rate_' in e)>1e-4:
            raise RuntimeError(f'differential residual above bound: {k}')
        if abs(s['source_work_relative_to_one_pulse_error'])>2e-8:
            raise RuntimeError(f'analytic pulse integral differs: {k}')
    if result['local_checks']['away_from_sheet_Maxwell_max_normalized']>2e-5 or result['local_checks']['away_from_sheet_Poynting_max_normalized']>2e-5:
        raise RuntimeError('local finite-difference Maxwell/Poynting residual above bound')
    print(json.dumps({'one_pulse_J_per_m2':w,'elapsed_s':result['elapsed_s'],'case_errors':{k:s['errors'] for k,s in summaries.items()}},indent=2))


if __name__=='__main__':
    main()
