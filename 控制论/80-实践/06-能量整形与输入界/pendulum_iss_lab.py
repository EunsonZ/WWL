#!/usr/bin/env python3
"""Finite pendulum checks with SI conversion; serial standard library only."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[_key] = '1'
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


def certificate(p):
    k, c, ep, r = p['kappa'], p['gamma'] + p['kd'], p['epsilon'], p['r_rad']
    require(k > 0 and c > 0 and 0 < ep < c and 0 < r < math.pi / 2,
            'require kappa>0, c>epsilon>0 and 0<r<pi/2')
    s = math.sin(r) / r
    low = k * s + ep * c
    high = k + ep * c
    c1 = (low + 1 - math.hypot(low - 1, 2 * ep)) / 4
    c2 = (high + 1 + math.hypot(high - 1, 2 * ep)) / 4
    require(c1 > 0, 'lower comparison matrix must be positive definite')
    q = min(c - ep, ep * k * s)
    alpha, beta = q / (2 * c2), (1 + ep**2) / (2 * q)
    torque_norm = math.hypot(1 + k, p['kd'])
    h = p['h']
    require(h > 0 and h < c1 * r**2, 'h must be inside the local angle domain')
    require(p['a_max'] > 0 and torque_norm * math.sqrt(h / c1) < p['a_max'],
            'actuator limit does not protect the proposed sublevel set')
    threshold = math.sqrt(alpha * h / beta)
    require(0 <= p['d_max'] < threshold, 'd_max must be below the strict input threshold')
    return dict(c=c, s=s, c1=c1, c2=c2, q=q, alpha=alpha, beta=beta,
                torque_norm=torque_norm, radius=math.sqrt(h / c1),
                torque_bound=torque_norm * math.sqrt(h / c1), d_threshold=threshold,
                ultimate_radius=p['d_max'] * math.sqrt(beta / (alpha * c1)))


def energy(e, v, p, cert):
    H = v**2 / 2 + p['kappa'] * (1 - math.cos(e))
    W = H + p['epsilon'] * e * v + p['epsilon'] * cert['c'] * e**2 / 2
    return H, W


def disturbance(case, tau, switch):
    return case['d'] * ((-1)**int(math.floor((tau + 1e-12) / switch))
                        if case['disturbance'] == 'square' else 1)


def control(z, p, case):
    e, v = z
    raw = -(1 + p['kappa']) * math.sin(e) - p['kd'] * v
    applied = max(-case['a_max'], min(case['a_max'], raw))
    return raw, applied


def rhs(z, d, p, case):
    e, v = z
    _, a = control(z, p, case)
    # theta=pi+e; -sin(theta)=sin(e). This is the actual saturated plant.
    return v, math.sin(e) - p['gamma'] * v + a + d


def rk4(z, step, d, p, case):
    def shifted(z0, slope, scale):
        return tuple(a + scale*b for a, b in zip(z0, slope))
    k1 = rhs(z, d, p, case)
    k2 = rhs(shifted(z, k1, step / 2), d, p, case)
    k3 = rhs(shifted(z, k2, step / 2), d, p, case)
    k4 = rhs(shifted(z, k3, step), d, p, case)
    return tuple(x + step*(a + 2*b + 2*c + f)/6
                 for x, a, b, c, f in zip(z, k1, k2, k3, k4))


def integrate(cfg, case, substeps):
    p, grid, init = cfg['design'], cfg['integration'], cfg['initial']
    dt = grid['base_step_tau']
    n = round(grid['end_tau'] / dt)
    z = (init['e_rad'], init['v_scaled'])
    states = [z]
    for i in range(n):
        d = disturbance(case, (i + 0.5)*dt, grid['switch_interval_tau'])
        for _ in range(substeps):
            z = rk4(z, dt / substeps, d, p, case)
        states.append(z)
    return states


def plot(path, title, desc, panels):
    """Each panel owns axes and legend; all input pairs come from exported rows."""
    width, ph = 940, 355
    output = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{80+ph*len(panels)}" viewBox="0 0 {width} {80+ph*len(panels)}">',
              '<title>'+html.escape(title)+'</title><desc>'+html.escape(desc)+'</desc>',
              '<rect width="100%" height="100%" fill="white"/>',
              '<g font-family="sans-serif" font-size="13" fill="#132d40">',
              '<text x="85" y="29" font-size="21">'+html.escape(title)+'</text>',
              '<text x="85" y="54">'+html.escape(desc)+'</text>']
    colors = ['#126c9b', '#b24b08', '#7b3b99', '#286b30', '#444444']
    for index, panel in enumerate(panels):
        title0, xlabel, ylabel, xmin, xmax, ymin, ymax, series, guides = panel
        top = 80 + index*ph
        def xy(x, y):
            return 85 + 770*(x-xmin)/(xmax-xmin), top+235-200*(y-ymin)/(ymax-ymin)
        output.append(f'<text x="85" y="{top+15}" font-size="16">{html.escape(title0)}</text>')
        for j in range(6):
            x = xmin+(xmax-xmin)*j/5
            y = ymin+(ymax-ymin)*j/5
            px, _ = xy(x, ymin)
            _, py = xy(xmin, y)
            output += [f'<path d="M {px:.2f} {top+35} V {top+235}" stroke="#dfe5eb"/>',
                       f'<text x="{px:.2f}" y="{top+255}" text-anchor="middle">{x:.3g}</text>',
                       f'<path d="M 85 {py:.2f} H 855" stroke="#dfe5eb"/>',
                       f'<text x="74" y="{py+4:.2f}" text-anchor="end">{y:.3g}</text>']
        for y, label in guides:
            _, py = xy(xmin, y)
            output += [f'<path d="M 85 {py:.2f} H 855" stroke="#666" stroke-dasharray="3 5"/>',
                       f'<text x="850" y="{py-4:.2f}" text-anchor="end" font-size="11">{html.escape(label)}</text>']
        for j, (label, pairs, dash) in enumerate(series):
            pts = ' '.join(f'{xy(x,y)[0]:.3f},{xy(x,y)[1]:.3f}' for x,y in pairs)
            color = colors[j % len(colors)]
            output += [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                       f'<path d="M {85+(j%2)*395} {top+306+(j//2)*20} h 30" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                       f'<text x="{122+(j%2)*395}" y="{top+310+(j//2)*20}">{html.escape(label)}</text>']
        output += [f'<text x="470" y="{top+282}" text-anchor="middle">{html.escape(xlabel)}</text>',
                   f'<text transform="translate(22 {top+145}) rotate(-90)" text-anchor="middle">{html.escape(ylabel)}</text>']
    output.append('</g></svg>')
    path.write_text('\n'.join(output)+'\n', encoding='utf-8')


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('input.json'))
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), 'output directory must be new; refusing overwrite')
    cfg = json.loads(args.input.read_text(encoding='utf-8'))
    p, phys, grid = cfg['design'], cfg['physical'], cfg['integration']
    require(all(math.isfinite(x) for x in list(p.values())+list(phys.values())+
                list(grid.values())+list(cfg['initial'].values())), 'parameters must be finite')
    require(all(0 < x <= 100 for x in phys.values()), 'physical scales must be positive and <=100')
    require(0 < p['gamma'] <= 10 and 0 <= p['kd'] <= 10 and 0 < p['kappa'] <= 10,
            'bounded physical damping and gains required')
    require(0 < grid['end_tau'] <= 60 and 0.002 <= grid['base_step_tau'] <= 0.05,
            'require end_tau<=60 and 0.002<=base_step_tau<=0.05')
    dt, end, switch = grid['base_step_tau'], grid['end_tau'], grid['switch_interval_tau']
    require(switch >= dt and abs(end/dt-round(end/dt)) < 1e-9 and
            abs(switch/dt-round(switch/dt)) < 1e-9,
            'endpoint and disturbance switch times must align with the base grid')
    cert = certificate(p)
    require(1 <= len(cfg['cases']) <= 6, 'use 1..6 finite cases')
    require(len({case['name'] for case in cfg['cases']}) == len(cfg['cases']), 'case names must be unique')
    require([case['name'] for case in cfg['cases']] ==
            ['zero', 'constant', 'square', 'small_actuator', 'large_disturbance'],
            'this plotting lab requires the five declared comparison cases')
    H0, W0 = energy(cfg['initial']['e_rad'], cfg['initial']['v_scaled'], p, cert)
    require(abs(cfg['initial']['e_rad']) < p['r_rad'] and W0 <= p['h'], 'initial state outside certificate')
    omega = math.sqrt(phys['g_m_per_s2']/phys['l_m'])
    E0 = phys['m_kg']*phys['g_m_per_s2']*phys['l_m']
    summary = {'certificate': cert, 'initial_W': W0, 'omega_rad_per_s': omega,
               'energy_scale_J': E0, 'torque_scale_Nm': E0,
               'physical_damping_Nm_s_per_rad': p['gamma']*phys['m_kg']*phys['l_m']**2*omega,
               'cases': {}, 'scope': 'five finite trajectories; the general proof is in lesson 15'}
    rows, saved, error_rows = [], {}, []
    for case in cfg['cases']:
        require(type(case['certified']) is bool, 'certified must be a JSON boolean')
        require(case['disturbance'] in ('constant', 'square') and
                math.isfinite(case['d']) and abs(case['d']) <= 4 and
                math.isfinite(case['a_max']) and 0 < case['a_max'] <= 10, 'invalid finite case')
        if case['certified']:
            require(abs(case['d']) <= p['d_max'] and case['a_max'] >= p['a_max'],
                    'a case marked certified violates the protected input/actuator limits')
        routes = [integrate(cfg, case, n) for n in (1, 2, 4, 8)]
        require(time.monotonic()-start < 60, 'finite CPU budget exhausted')
        # Common base-grid states: finest route is an error reference, not exact truth.
        errors = [max(math.hypot(a[0]-b[0], a[1]-b[1]) for a,b in zip(route,routes[3]))
                  for route in routes[:3]]
        for sub, err in zip((1,2,4), errors):
            error_rows.append([case['name'], dt/sub, dt/8, err])
        if case['certified']:
            require(errors[1] <= errors[0]+1e-12 and errors[2] <= errors[1]+1e-12,
                    'smooth protected step-refinement errors did not decrease')
        else:
            require(errors[2] < 1e-4, 'saturated refined trajectory error exceeds finite tolerance')
        data = []
        identity_error = inequality_excess = 0.0
        for i, (e,v) in enumerate(routes[2]):
            tau = i*dt
            d = disturbance(case, tau, switch)
            raw, actual = control((e,v), p, case)
            de, dv = rhs((e,v), d, p, case)
            H,W = energy(e,v,p,cert)
            ep,c = p['epsilon'],cert['c']
            direct = (p['kappa']*math.sin(e)+ep*v+ep*c*e)*de+(v+ep*e)*dv
            factored = -(c-ep)*v*v-ep*p['kappa']*e*math.sin(e)+(v+ep*e)*(d+actual-raw)
            identity_error = max(identity_error,abs(direct-factored))
            envelope = math.exp(-cert['alpha']*tau)*W0 + cert['beta']/cert['alpha']*case['d']**2*(1-math.exp(-cert['alpha']*tau))
            if case['certified']:
                inequality_excess = max(inequality_excess, direct+cert['alpha']*W-cert['beta']*d*d)
                require(abs(actual-raw) < 1e-12 and W <= p['h']+1e-10 and abs(e)<p['r_rad'],
                        'finite protected trajectory violated a certificate condition')
                require(W <= envelope+2e-8, 'finite comparison envelope violated')
            record = [case['name'], tau, tau/omega, e, v, omega*v, d,
                      E0*raw, E0*actual, H, W, envelope if case['certified'] else '', math.hypot(e,v),
                      direct, actual-raw, case['certified']]
            rows.append(record)
            data.append(record)
        require(identity_error < 1e-9 and inequality_excess < 1e-10, 'finite derivative identity/inequality check failed')
        saved[case['name']] = data
        first_exit = next((z[2] for z in data if abs(z[3]) >= p['r_rad']), None)
        summary['cases'][case['name']] = dict(final_e_rad=data[-1][3], final_v_scaled=data[-1][4],
            max_W=max(z[10] for z in data), max_abs_raw_Nm=max(abs(z[7]) for z in data),
            max_abs_applied_Nm=max(abs(z[8]) for z in data),
            saturated_export_rows=sum(abs(z[14])>1e-12 for z in data), first_export_angle_exit_s=first_exit,
            derivative_identity_max_error=identity_error, certified_inequality_max_excess=inequality_excess if case['certified'] else None,
            step_errors=errors, certificate_applies=case['certified'])
    args.output_dir.mkdir(parents=True)
    with (args.output_dir/'trajectories.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['case','tau','t_s','e_rad','v_scaled','theta_dot_rad_per_s',
            'd_scaled','raw_torque_Nm','applied_torque_Nm','H_scaled','W_scaled','comparison_W',
            'rho_scaled','dW_dtau','saturation_residual_scaled','certificate_applies']);writer.writerows(rows)
    with (args.output_dir/'step-errors.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['case','step_tau','reference_step_tau','max_scaled_state_difference']);writer.writerows(error_rows)
    def series(name, col):
        return [(z[2],z[col]) for z in saved[name]]
    cases = {case['name']: case for case in cfg['cases']}
    dc, ds = cases['constant']['d'], cases['square']['d']
    small = cases['small_actuator']
    nominal=[(f'zero case: d={cases["zero"]["d"]:g}',series('zero',3),''),
             (f'constant d={dc:g}',series('constant',3),'7 3'),
             (f'square +/-{abs(ds):g}',series('square',3),'2 3')]
    equilibrium_guide = [(math.asin(dc/p['kappa']),'constant equilibrium')] if abs(dc)<p['kappa'] else []
    plot(args.output_dir/'nominal.svg','Upright regulation: the same initial state',
         f'Exact model; continuous feedback; e=theta-pi; initial (e,v)=({cfg["initial"]["e_rad"]:g},{cfg["initial"]["v_scaled"]:g}).',
         [('No disturbance, constant load, switching load','physical time t (s)','angle error e (rad)',0,end/omega,min(-.12,min(z[3] for name in ('zero','constant','square') for z in saved[name])*1.1),
           max(.34,max(z[3] for name in ('zero','constant','square') for z in saved[name])*1.1),nominal,equilibrium_guide)])
    plot(args.output_dir/'certificate.svg','A strict local certificate and its comparison bound',
         f'W is dimensionless, not physical stored energy. Dashed envelope uses |d|<={abs(dc):g}.',
         [('Constant disturbance: W <= comparison <= h','physical time t (s)','dimensionless W',0,end/omega,0,p['h']*1.125,
           [('W: actual trajectory',series('constant',10),''),('comparison bound',series('constant',11),'7 3')],[(p['h'],f'h={p["h"]:g}')])])
    plot(args.output_dir/'failures.svg','Why the domain and actuator assumptions matter',
         'Same initial state; actual saturated plant. These cases are outside the certificate.',
         [(f'Actuator limit={small["a_max"]:g}; disturbance={small["d"]:g}','physical time t (s)','angle error e (rad)',0,end/omega,0,max(4,max(z[3] for z in saved['small_actuator'])*1.03),
           [('small actuator',series('small_actuator',3),'')],[(p['r_rad'],f'r={p["r_rad"]:g} rad')]),
          (f'External load d={cases["large_disturbance"]["d"]:g}; actuator limit={cases["large_disturbance"]["a_max"]:g}','physical time t (s)','unwrapped angle error e (rad)',0,end/omega,0,max(z[3] for z in saved['large_disturbance'])*1.03,
           [('large disturbance',series('large_disturbance',3),'')],[(p['r_rad'],f'r={p["r_rad"]:g} rad')])])
    plot(args.output_dir/'torque.svg','Commanded torque and applied torque differ after saturation',
         f'Reduced actuator case; actual plant uses applied torque; m={phys["m_kg"]:g} kg, l={phys["l_m"]:g} m, g={phys["g_m_per_s2"]:g} m/s^2.',
         [('Controller still requests the same law','physical time t (s)','torque (N m)',0,end/omega,
           min(z[7] for z in saved['small_actuator'])*1.03,max(2,max(z[7] for z in saved['small_actuator'])*1.03),
           [('command',series('small_actuator',7),''),('applied',series('small_actuator',8),'7 3')],
           []),
          ('Applied torque detail and the hardware limits','physical time t (s)','applied torque (N m)',
           0,end/omega,-1.2*E0*small['a_max'],1.2*E0*small['a_max'],
           [('applied torque',series('small_actuator',8),'')],
           [(E0*small['a_max'],'+limit'),(-E0*small['a_max'],'-limit')])])
    (args.output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    elapsed=time.monotonic()-start
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes=rss if platform.system()=='Darwin' else rss*1024
    print(json.dumps({'status':'PASS','python':platform.python_version(),'platform':platform.platform(),
                      'elapsed_s':elapsed,'observed_peak_rss_bytes':rss_bytes,
                      'rows':len(rows),'certificate':cert,'cases':summary['cases']},indent=2,allow_nan=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit('Input/output check failed: '+str(exc))
