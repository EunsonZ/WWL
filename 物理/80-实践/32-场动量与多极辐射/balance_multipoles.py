#!/usr/bin/env python3
"""Vacuum pulse momentum and multipole examples; Python stdlib, one thread.
Run in this directory: python3 balance_multipoles.py
CSV/SVG/JSON are derived outputs, not independent input data.
"""
from pathlib import Path
import cmath
import csv
import json
from html import escape
import math

ROOT = Path(__file__).resolve().parent
C = 299792458.0
EPS = 8.8541878128e-12
MU = 1 / (EPS * C**2)
PI = math.pi
E0, T = 1000.0, 1e-8
FREQ, P0, AM, AE, SEP, I0 = 1e8, 1e-12, .01, .001, .1, 1.0
OMEGA, K = 2 * PI * FREQ, 2 * PI * FREQ / C


def simpson(fn, lo, hi, n):
    if n <= 0 or n % 2:
        raise ValueError('Simpson n must be positive and even')
    h = (hi - lo) / n
    return h / 3 * sum((1 if i in (0, n) else 4 if i % 2 else 2) * fn(lo + i*h) for i in range(n+1))


def pulse(tau):
    return math.sin(PI*tau)**2 if 0 < tau < 1 else 0.0


def primitive(tau):
    u = min(1., max(0., tau))
    return 3*u/8 - math.sin(2*PI*u)/(4*PI) + math.sin(4*PI*u)/(32*PI)


def stored(tau, sign=-1, n=200):
    return simpson(lambda z: pulse(tau-z)**2 + sign*pulse(tau+z)**2, -.5, 0., n)


def stored_exact(tau, sign=-1):
    return primitive(tau+.5)-primitive(tau)+sign*(primitive(tau)-primitive(tau-.5))


def shape(x):
    if abs(x) < .1:
        return 1-x*x/10+x**4/280-x**6/15120+x**8/1330560
    return 3*(math.sin(x)-x*math.cos(x))/x**3


def loop_current(theta, n=128):
    # Periodic trapezoid of ORIGINAL closed-loop current with propagation phase.
    q = K*AM*math.sin(theta)
    return tuple(I0*AM*2*PI/n * sum(
        (-math.sin(2*PI*j/n) if axis == 0 else math.cos(2*PI*j/n))
        * cmath.exp(-1j*q*math.cos(2*PI*j/n)) for j in range(n)) for axis in (0, 1))


def loop_u(theta, n=128):
    jx, jy = loop_current(theta, n)
    transverse_sq = abs(jx)**2 * math.cos(theta)**2 + abs(jy)**2
    return OMEGA**2 * MU/(32*PI**2*C) * transverse_sq


PREF = OMEGA**4/(32*PI**2*EPS*C**3)
M0 = PI*AM**2*I0
PM = OMEGA**4*M0**2/(12*PI*EPS*C**5)
PP = OMEGA**4*P0**2/(12*PI*EPS*C**3)
PQ = OMEGA**6*P0**2*SEP**2/(60*PI*EPS*C**5)


def pair_u(theta, kd=K*SEP, finite_ball=True):
    fac = shape(K*AE)**2 if finite_ball else 1.
    return PREF*P0**2*fac*4*math.sin(theta)**2*math.sin(kd*math.cos(theta)/2)**2


def quad_u(theta, kd=K*SEP):
    return PREF*P0**2*kd**2*math.sin(theta)**2*math.cos(theta)**2


def total(fn, n=240):
    return 2*PI*simpson(lambda th: fn(th)*math.sin(th), 0, PI, n)


def matmul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def trans(a):
    return list(map(list, zip(*a)))


def stress_energy(e, cb):
    # Normalize epsilon0=1, c=1; cb is physical c*B, so no mixed units.
    u = .5*sum(x*x for x in e+cb)
    cross = [e[1]*cb[2]-e[2]*cb[1], e[2]*cb[0]-e[0]*cb[2], e[0]*cb[1]-e[1]*cb[0]]
    out = [[0.]*4 for _ in range(4)]
    out[0][0] = u
    for i in range(3):
        out[0][i+1] = out[i+1][0] = cross[i]
        for j in range(3):
            out[i+1][j+1] = (u if i == j else 0.)-e[i]*e[j]-cb[i]*cb[j]
    return out


def write_csv(name, header, rows):
    with (ROOT/name).open('w', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def svg_plot(name, title, rows, columns, labels, colors, x_label, y_label, ylim, notes):
    width, height = 1040, 590
    left, right, top, bottom = 95, 710, 85, 415
    xmin, xmax = rows[0][0], rows[-1][0]
    ymin, ymax = ylim
    sx = lambda x: left+(x-xmin)/(xmax-xmin)*(right-left)
    sy = lambda y: bottom-(y-ymin)/(ymax-ymin)*(bottom-top)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="1040" height="590" fill="#fafbf8"/>',
         '<g font-family="Arial,sans-serif" fill="#172b34">',
         f'<text x="40" y="39" font-size="24" font-weight="bold">{title}</text>']
    for j in range(6):
        y = ymin+(ymax-ymin)*j/5
        s += [f'<line x1="{left}" y1="{sy(y):.2f}" x2="{right}" y2="{sy(y):.2f}" stroke="#d7dedb"/>',
              f'<text x="{left-10}" y="{sy(y)+5:.2f}" font-size="14" text-anchor="end">{y:.2g}</text>']
    for j in range(7):
        x = xmin+(xmax-xmin)*j/6
        s.append(f'<text x="{sx(x):.2f}" y="440" text-anchor="middle" font-size="14">{x:.3g}</text>')
    s += [f'<path d="M{left} {top}V{bottom}H{right}" fill="none" stroke="#172b34"/>',
          f'<text x="400" y="470" text-anchor="middle" font-size="17">{x_label}</text>',
          f'<text transform="translate(25 255) rotate(-90)" text-anchor="middle" font-size="16">{y_label}</text>']
    for col, label, color in zip(columns, labels, colors):
        pts = ' '.join(f'{sx(r[0]):.2f},{sy(r[col]):.2f}' for r in rows)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        j = columns.index(col)
        s += [f'<line x1="745" y1="{100+j*44}" x2="777" y2="{100+j*44}" stroke="{color}" stroke-width="3"/>',
              f'<text x="787" y="{105+j*44}" font-size="15">{label}</text>']
    if name == 'multipole-patterns.svg':
        s += ['<ellipse cx="805" cy="290" rx="42" ry="20" fill="none" stroke="#167594" stroke-width="3"/>',
              '<path d="M844 282L852 290L840 294 M805 278V235L800 244M805 235L810 244" fill="none" stroke="#167594" stroke-width="2"/>',
              '<text x="790" y="327" font-size="15">loop: m +z</text>',
              '<circle cx="958" cy="253" r="14" fill="#f2dfc9" stroke="#c25530"/>',
              '<circle cx="958" cy="325" r="14" fill="#f2dfc9" stroke="#c25530"/>',
              '<path d="M958 266V231L953 240M958 231L963 240 M958 312V347L953 338M958 347L963 338" fill="none" stroke="#c25530" stroke-width="2"/>',
              '<text x="924" y="375" font-size="15">p+ = -p-</text>']
    for j, note in enumerate(notes):
        s.append(f'<text x="95" y="{510+j*24}" font-size="16">{escape(note)}</text>')
    s.append('</g></svg>')
    (ROOT/'assets'/name).write_text('\n'.join(s)+'\n')


def main():
    (ROOT/'assets').mkdir(exist_ok=True)
    pulse_rows, errors = [], {key: 0. for key in ['g_integral', 'h_integral', 'g_derivative', 'h_derivative']}
    for j in range(251):
        tau = -.75+j*.01
        incoming = pulse(tau+.5)**2+pulse(tau-.5)**2
        force = 2*pulse(tau)**2
        g = stored(tau)
        hstep = 1e-4
        dg = (stored(tau+hstep)-stored(tau-hstep))/(2*hstep)
        dh = (stored(tau+hstep, 1)-stored(tau-hstep, 1))/(2*hstep)
        errors['g_integral'] = max(errors['g_integral'], abs(g-stored_exact(tau)))
        errors['h_integral'] = max(errors['h_integral'], abs(stored(tau, 1)-stored_exact(tau, 1)))
        errors['g_derivative'] = max(errors['g_derivative'], abs(dg-(incoming-force)))
        errors['h_derivative'] = max(errors['h_derivative'], abs(dh-(pulse(tau+.5)**2-pulse(tau-.5)**2)))
        pulse_rows.append([tau, incoming, force, dg, g])
    assert errors['g_integral'] < 1e-9 and errors['h_integral'] < 1e-9
    assert errors['g_derivative'] < 2e-6 and errors['h_derivative'] < 2e-6
    pulse_num = simpson(lambda tau: pulse(tau)**2, 0., 1., 400)
    assert abs(pulse_num-3/8) < 1e-13
    beta, gamma = .6, 1.25
    lam = [[gamma,-gamma*beta,0,0],[-gamma*beta,gamma,0,0],[0,0,1,0],[0,0,0,1]]
    tensor = matmul(matmul(lam, stress_energy([0,1,0], [0,0,0])), trans(lam))
    fields = stress_energy([0,1.25,0], [0,0,-.75])
    tensor_err = max(abs(tensor[i][j]-fields[i][j]) for i in range(4) for j in range(4))
    assert tensor_err < 1e-14
    pm_exact = total(loop_u)
    pm_fine = total(lambda th: loop_u(th, 256), 480)
    pq_exact = total(pair_u)
    pq_fine = total(pair_u, 480)
    assert abs(pm_exact/pm_fine-1) < 2e-8
    assert abs(pq_exact/pq_fine-1) < 2e-8
    assert abs(total(quad_u)/PQ-1) < 2e-8
    loop_leading_num = total(lambda th: PREF*(M0/C)**2*math.sin(th)**2)
    assert abs(loop_leading_num/PM-1) < 2e-8
    qnorm2 = 24*SEP**2*P0**2
    assert abs(OMEGA**6*qnorm2/(1440*PI*EPS*C**5)/PQ-1) < 1e-14
    rows_raw = [[180*j/240, loop_u(PI*j/240), pair_u(PI*j/240), quad_u(PI*j/240)] for j in range(241)]
    maxes = [max(r[col] for r in rows_raw) for col in (1,2,3)]
    rows_plot = [[r[0]]+[r[i+1]/maxes[i] for i in range(3)] for r in rows_raw]
    sweep = []
    for j in range(1, 161):
        kd = .025*j
        exact = total(lambda th: pair_u(th, kd, False))
        leading = PREF*P0**2*kd**2*8*PI/15
        sweep.append([kd, exact/leading, 1.])
    recoil = total(lambda th: pair_u(th)*math.cos(th))
    assert abs(recoil/pq_exact) < 1e-13
    results = {
      'model': 'SI vacuum prescribed sources; peak harmonic phasors; plane pulse per area',
      'inputs': {'c_m_s':C,'epsilon0_F_m':EPS,'E0_V_m':E0,'T_s':T,'f_Hz':FREQ,'p0_C_m':P0,'loop_a_m':AM,'loop_I0_A':I0,'ball_a_m':AE,'pair_d_m':SEP},
      'pulse': {'ell_m':C*T/2,'incident_energy_J_m2':3/8*EPS*C*E0**2*T,'peak_pressure_Pa':2*EPS*E0**2,'impulse_N_s_m2':3/4*EPS*E0**2*T,'quadrature_integral_F2':pulse_num,'dimensionless_max_errors':errors,'early_tau':-.25,'early_incoming_normalized':.25,'early_mirror_pressure':0},
      'tensor': {'u_prime_over_u0':tensor[0][0]/.5,'Sx_prime_over_c_u0':tensor[0][1]/.5,'max_element_error_normalized':tensor_err},
      'multipoles': {'ka_loop':K*AM,'ka_ball':K*AE,'kd_pair':K*SEP,'single_electric_power_W':PP,'loop_m0_A_m2':M0,'loop_leading_power_W':PM,'loop_full_phase_far_power_W':pm_exact,'loop_exact_over_leading':pm_exact/PM,'loop_quadrature_refinement_relative':abs(pm_exact/pm_fine-1),'pair_quad_power_W':PQ,'pair_full_phase_far_power_W':pq_exact,'pair_exact_over_leading':pq_exact/PQ,'pair_quadrature_refinement_relative':abs(pq_exact/pq_fine-1),'pair_quad_over_single':PQ/PP,'pair_symmetric_z_recoil_over_P_div_c':recoil/pq_exact,'pair_exact_over_leading_at_kd_4_point_balls':sweep[-1][1]},
      'checks': 'assertions passed: pulse primitive/quadrature/time derivative; energy/momentum; tensor field vs boost; source-phase and whole-sphere quadrature refinement; quadrupole norm; parity recoil',
      'not_verified': ['finite beam or hardware', 'Obsidian rendering and learner comprehension', 'self-consistent feed and radiation reaction', 'general radiated angular momentum', 'finite-distance pair near-field matching']
    }
    write_csv('mirror-balance.csv', ['tau','incoming_over_eps_E02','pressure_over_eps_E02','dPfield_dt_over_eps_E02','Pfield_over_eps_E02_T'], pulse_rows)
    write_csv('multipole-angular.csv', ['theta_deg','loop_U_W_sr','pair_U_W_sr','quadrupole_U_W_sr'], rows_raw)
    write_csv('quadrupole-limit.csv', ['kd','pair_power_over_quad_power_point_balls','quad_reference'], sweep)
    svg_plot('mirror-balance.svg','A finite pulse: incoming momentum = mirror force + field storage',pulse_rows,[1,2,3],['Boundary input','Mirror pressure','Field change'],['#167594','#c25530','#7252a3'],'t / T','Force per area / (epsilon0 E0^2)',(-2.1,2.1),['Vacuum slab:  z = -cT/2  |   incoming --->   reflected <---   |  mirror z = 0', 'At t/T = -0.25 the boundary input is 0.25; the mirror force is still zero.'])
    svg_plot('multipole-patterns.svg','Same source integrals: magnetic dipole and electric quadrupole',rows_plot,[1,2,3],['Current loop','Opposite pair','Quad leading'],['#167594','#c25530','#7252a3'],'Polar observation angle theta (degrees)','Mean angular power / its own maximum',(0,1.05),['Sources: loop current in xy-plane (m along +z); pair at z = +/-d/2 with p+ = -p-.','Plotted quantity is POWER, not field amplitude. Total power uses 2 pi sin(theta) dtheta.'])
    svg_plot('quadrupole-limit.svg','When the source-phase expansion fails',sweep,[1,2],['Full phase / quad','Quad prediction'],['#167594','#c25530'],'k d  (pointlike balls; separation d)','Whole-sphere mean power ratio',(0,1.05),['Sweep isolates separation phase: ball radius tends to zero; no finite-r near fields.', 'Default finite-ball example: kd = 0.209585, ratio approximately 0.998432.'])
    (ROOT/'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
