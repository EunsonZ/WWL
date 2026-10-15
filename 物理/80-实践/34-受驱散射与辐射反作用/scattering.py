#!/usr/bin/env python3
"""Finite classical scattering and reduction-of-order examples. Standard library only."""
import argparse
import csv
import json
import math
from pathlib import Path


def simpson(f, a, b, n):
    if n < 2 or n % 2:
        raise ValueError('even n>=2 required')
    h = (b-a)/n
    return h/3*math.fsum((1 if i in (0, n) else 4 if i % 2 else 2)*f(a+i*h) for i in range(n+1))


def csv_write(path, columns, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(columns)
        w.writerows(rows)


def svg_plot(path, panels):
    palette = ['#176799', '#ba561f', '#713e98']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430">',
           '<rect width="1000" height="430" fill="white"/>', '<g font-family="sans-serif" font-size="14" fill="#263747">']
    for j, (title, xlabel, ylabel, curves, bounds) in enumerate(panels):
        xmin, xmax, ymin, ymax = bounds
        left, top, width, height = 80+495*j, 65, 375, 265
        sx = lambda x: left+(x-xmin)*width/(xmax-xmin)
        sy = lambda y: top+height-(y-ymin)*height/(ymax-ymin)
        svg.append(f'<text x="{left}" y="25">{title}</text><text x="{left}" y="48">{ylabel}</text>')
        for k in range(5):
            x, y = xmin+k*(xmax-xmin)/4, ymin+k*(ymax-ymin)/4
            svg.append(f'<path d="M {sx(x):.2f} {top} V {top+height} M {left} {sy(y):.2f} H {left+width}" stroke="#e0e6eb"/>')
            svg.append(f'<text x="{sx(x):.2f}" y="{top+height+22}" text-anchor="middle">{x:.3g}</text>')
            svg.append(f'<text x="{left-8}" y="{sy(y)+5:.2f}" text-anchor="end">{y:.3g}</text>')
        svg.append(f'<path d="M {left} {top} V {top+height} H {left+width}" fill="none" stroke="#333"/>')
        svg.append(f'<text x="{left+width/2}" y="{top+height+48}" text-anchor="middle">{xlabel}</text>')
        for k, (label, xs, ys) in enumerate(curves):
            points = ' '.join(f'{sx(x):.3f},{sy(y):.3f}' for x, y in zip(xs, ys))
            dash = '' if k == 0 else ' stroke-dasharray="7 4"'
            svg.append(f'<polyline points="{points}" fill="none" stroke="{palette[k]}" stroke-width="2.1"{dash}/>')
            svg.append(f'<text x="{left+8}" y="{400+k*18}" fill="{palette[k]}">{label}</text>')
    svg.append('</g></svg>')
    path.write_text('\n'.join(svg), encoding='utf-8')


def envelope(u, duration):
    if not 0 < u < duration:
        return 0., 0., 0.
    k = math.pi/duration
    s, c = math.sin(k*u), math.cos(k*u)
    h, hp, hpp = s**4, 4*k*s**3*c, 4*k*k*(3*s*s*c*c-s**4)
    return (h*math.cos(u), hp*math.cos(u)-h*math.sin(u),
            hpp*math.cos(u)-2*hp*math.sin(u)-h*math.cos(u))


def oscillator(delta, amplitude, duration, end, dt):
    steps = round(end/dt)
    dt = end/steps
    # State: y=x*omega0/c, y'=v/c, drive work/(mc^2), radiated energy/(mc^2).
    def derivative(u, state):
        y, v, _, _ = state
        g, gp, _ = envelope(u, duration)
        a = amplitude*(g+delta*gp)-delta*v-y
        return [v, a, amplitude*g*v, delta*a*a]
    state = [0., 0., 0., 0.]
    rows, residual_max, remainder_identity = [], 0., 0.
    for i in range(steps+1):
        u = i*dt
        y, v, win, wrad = state
        g, gp, gpp = envelope(u, duration)
        a = derivative(u, state)[1]
        jerk = amplitude*(gp+delta*gpp)-delta*a-v
        e, es = (v*v+y*y)/2, -delta*v*a
        pin, prad = amplitude*g*v, delta*a*a
        dedt, desdt = v*(a+y), -delta*(a*a+v*jerk)
        res = pin-dedt-desdt-prad
        predicted_res = delta*delta*v*(amplitude*gpp-a)
        residual_max = max(residual_max, abs(res))
        remainder_identity = max(remainder_identity, abs(res-predicted_res))
        if i % max(1, steps//600) == 0 or i == steps:
            rows.append((u, y, v, pin, prad, e, es, win, wrad, win-e-es-wrad))
        if i == steps:
            break
        k1 = derivative(u, state)
        k2 = derivative(u+dt/2, [s+dt*k/2 for s, k in zip(state, k1)])
        k3 = derivative(u+dt/2, [s+dt*k/2 for s, k in zip(state, k2)])
        k4 = derivative(u+dt, [s+dt*k for s, k in zip(state, k3)])
        state = [s+dt*(a+2*b+2*c+d)/6 for s, a, b, c, d in zip(state,k1,k2,k3,k4)]
    return rows, {'delta':delta, 'actual_dt':dt, 'final_y':state[0], 'final_v':state[1],
                  'work':state[2], 'radiated_energy':state[3],
                  'balance_remainder':rows[-1][-1],
                  'max_instantaneous_remainder_over_A2':residual_max/amplitude**2,
                  'remainder_identity_error_over_A2':remainder_identity/amplitude**2,
                  'max_v_over_c':max(abs(row[2]) for row in rows)}


def run(cfg, out):
    c, eps, e, m = (cfg[k] for k in ('c_m_s','epsilon0_F_m','electron_charge_magnitude_C','electron_mass_kg'))
    w0, e0 = 2*math.pi*cfg['resonance_Hz'], cfg['E_peak_V_m']
    if min(c, eps, e, m, w0, e0) <= 0 or cfg['nonradiative_to_resonant_radiative_damping'] < 0:
        raise ValueError('physical constants and amplitudes positive; damping nonnegative')
    rq = e*e/(4*math.pi*eps*m*c*c)
    tau = 2*rq/(3*c)
    sigma_t = 8*math.pi*rq*rq/3
    gamma_nr = cfg['nonradiative_to_resonant_radiative_damping']*tau*w0*w0
    intensity = eps*c*e0*e0/2
    def response(w):
        damping = gamma_nr+tau*w*w
        x = (-e*e0/m)/complex(w0*w0-w*w, -damping*w)
        pin = (-e*e0)*w*x.imag/2
        psc = e*e*w**4*abs(x)**2/(12*math.pi*eps*c**3)
        pabs = m*gamma_nr*w*w*abs(x)**2/2
        return x, pin, psc, pabs
    x, pin, psc, pabs = response(w0)
    result = {'electron':{'r_m':rq, 'tau_s':tau, 'sigma_T_m2':sigma_t,
        'omega0_rad_s':w0, 'tau_omega0':tau*w0, 'Gamma_nr_s-1':gamma_nr,
        'X_abs_m':abs(x), 'v_peak_over_c':w0*abs(x)/c,
        'I_W_m2':intensity, 'P_in_W':pin,'P_sc_W':psc,'P_abs_W':pabs,
        'sigma_sc_m2':psc/intensity,'sigma_ext_m2':pin/intensity,
        'balance_relative_error':(pin-psc-pabs)/pin}}
    assert abs((pin-psc-pabs)/pin) < 1e-12
    broad = []
    for i in range(601):
        ratio = 10**(-2+4*i/600)
        _, _, ps, _ = response(w0*ratio)
        broad.append((ratio, ps/intensity/sigma_t))
    narrow = []
    for i in range(601):
        detuning = -8+16*i/600
        w = w0+detuning*tau*w0*w0
        _, pi, ps, pa = response(w)
        narrow.append((detuning, ps/intensity/sigma_t, pa/intensity/sigma_t, pi/intensity/sigma_t))
    csv_write(out/'spectrum.csv', ['omega_over_omega0','sigma_sc_over_sigmaT'], broad)
    csv_write(out/'resonance.csv', ['detuning_over_tau_omega0_sq','scattering_over_sigmaT','absorption_over_sigmaT','extinction_over_sigmaT'], narrow)
    gaussian, details = [], []
    nint = cfg['gaussian_intervals']
    for delta in cfg['gaussian_delta']:
        if not 0 < delta <= .1:
            raise ValueError('Gaussian example restricted to 0<delta<=0.1')
        errors = []
        for i in range(401):
            xg = -4+8*i/400
            f = math.exp(-xg*xg/2)
            future = simpson(lambda u: math.exp(-u-(xg+delta*u)**2/2), 0, 40, nint)
            ro = f-delta*xg*f
            gaussian.append((delta, xg, future, ro, abs(future-ro)))
            errors.append(abs(future-ro))
        error = max(errors)
        details.append({'delta':delta,'max_abs_error':error,'Taylor_bound':delta*delta,
                        'error_over_delta2':error/delta**2})
        assert error <= delta*delta+1e-7
    result['gaussian'] = details
    # One doubled quadrature check at the maximum-curvature point; tail <= exp(-40).
    d = cfg['gaussian_delta'][-1]
    gc = lambda n:simpson(lambda u:math.exp(-u-(d*u)**2/2),0,40,n)
    result['gaussian_quadrature_change_at_t0'] = abs(gc(2*nint)-gc(nint))
    assert result['gaussian_quadrature_change_at_t0'] < 1e-8
    csv_write(out/'gaussian.csv', ['delta','t_over_T','formal_no_runaway_a_over_a0','reduced_a_over_a0','absolute_difference'], gaussian)
    pulse_results, default_rows = [], None
    for delta in cfg['pulse_delta']:
        if not 0 < delta <= .1:
            raise ValueError('pulse delta restricted to (0,0.1]')
        args = (delta,cfg['pulse_drive'],cfg['pulse_duration'],cfg['pulse_end'])
        rows, coarse = oscillator(*args,cfg['pulse_dt'])
        rowsfine, fine = oscillator(*args,cfg['pulse_dt']/2)
        fine['work_mesh_change_over_A2'] = abs(coarse['work']-fine['work'])/cfg['pulse_drive']**2
        fine['remainder_mesh_change_over_A2'] = abs(coarse['balance_remainder']-fine['balance_remainder'])/cfg['pulse_drive']**2
        assert fine['remainder_identity_error_over_A2'] < 1e-9
        assert fine['work_mesh_change_over_A2'] < 1e-4
        pulse_results.append(fine)
        if delta == cfg['pulse_delta'][len(cfg['pulse_delta'])//2]:
            default_rows = rowsfine
    result['pulse'] = pulse_results
    csv_write(out/'pulse.csv', ['u_omega0_t','y_xomega0_over_c','v_over_c','P_in_over_mc2omega0','P_rad_over_mc2omega0','E_mech_over_mc2','E_Schott_over_mc2','W_in_over_mc2','W_rad_over_mc2','integral_remainder_over_mc2'],default_rows)
    (out/'assets').mkdir()
    svg_plot(out/'assets/scattering.svg', [
        ('One bound electron: broad sweep','log10(omega / omega0)','log10(sigma_sc / sigma_T)',
         [('fixed material damping',[math.log10(r[0]) for r in broad],[math.log10(r[1]) for r in broad])],(-2,2,-8.5,17)),
        ('Resolved resonance: same inputs','(omega - omega0) / (tau * omega0^2)','sigma_sc / sigma_sc(omega0)',
         [('scattering',[r[0] for r in narrow],[r[1]/(psc/intensity/sigma_t) for r in narrow])],(-8,8,0,1.05))])
    selected = [r for r in gaussian if r[0] == cfg['gaussian_delta'][0]]
    a2 = cfg['pulse_drive']**2
    svg_plot(out/'assets/reduction.svg', [
        ('Gaussian: formal branch vs reduction','t / T','acceleration / a0',
         [('future integral',[r[1] for r in selected],[r[2] for r in selected]),
          ('local first order',[r[1] for r in selected],[r[3] for r in selected])],(-4,4,0,1.1)),
        ('Causal initial-value pulse','omega0 * t','energy / (m c^2 A^2)',
         [('drive work',[r[0] for r in default_rows],[r[7]/a2 for r in default_rows]),
          ('mechanical + Schott + radiation',[r[0] for r in default_rows],[(r[5]+r[6]+r[8])/a2 for r in default_rows])],
         (0,cfg['pulse_end'],0,max(r[7]/a2 for r in default_rows)*1.12))])
    (out/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    ap.add_argument('--output', type=Path, required=True, help='new output directory; never overwrite a prior run')
    a = ap.parse_args()
    config = json.loads(a.inputs.read_text())
    a.output.mkdir(parents=True,exist_ok=False)
    print(json.dumps(run(config,a.output),indent=2,allow_nan=False))
