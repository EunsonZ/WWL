#!/usr/bin/env python3
"""Standard-library, one-thread checks for the declared Coulomb/finite-block models.
Outputs are relative to this source, not the shell working directory. No renormalization.
"""
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'assets'
# NIST 2022 CODATA nominal values; uncertainty propagation is outside this exercise.
H = 6.62607015e-34  # J s, exact
E = 1.602176634e-19  # C, exact; also joules per eV
ME = 9.1093837139e-31  # kg
EPS0 = 8.8541878188e-12  # F/m
HBAR = H / (2 * math.pi)
G = E * E / (4 * math.pi * EPS0)  # J m; Z = 1
A0 = HBAR * HBAR / (ME * G)  # m; infinite nuclear mass
RY = ME * G * G / (2 * HBAR * HBAR)  # J
LIMIT = 60.0  # dimensionless radius rho = r/a
N = 8000  # Simpson panels; doubled for final reported integral


def simpson(f, lo, hi, panels):
    if panels <= 0 or panels % 2:
        raise ValueError('Simpson requires a positive even number of panels')
    d = (hi - lo) / panels
    return d / 3 * math.fsum(
        (1 if i in (0, panels) else 4 if i % 2 else 2) * f(lo + i * d)
        for i in range(panels + 1))


def radial(n, l, rho):
    if (n, l) == (1, 0):
        return 2 * rho * math.exp(-rho)
    if (n, l) == (2, 0):
        return rho * (2 - rho) * math.exp(-rho / 2) / (2 * math.sqrt(2))
    if (n, l) == (2, 1):
        return rho ** 2 * math.exp(-rho / 2) / (2 * math.sqrt(6))
    raise ValueError('Only the three declared radial functions are implemented')


def monomial_tail(power, decay, limit):
    """Exact positive tail integral of rho**power exp(-decay*rho)."""
    return (math.exp(-decay * limit) * math.factorial(power) / decay ** (power + 1)
            * math.fsum((decay * limit) ** k / math.factorial(k)
                        for k in range(power + 1)))


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def difference(a, b):
    return max(abs(x - y) for rowa, rowb in zip(a, b) for x, y in zip(rowa, rowb))


def scale(c, a):
    return [[c * x for x in row] for row in a]


def finite_projectors(delta, v):
    a = [[delta / 2, v], [v.conjugate(), -delta / 2]]
    r = math.hypot(delta / 2, abs(v))
    if r == 0:
        raise ValueError('Whole 2D block degenerate: signed projectors undefined')
    p = [[[((1 if i == j else 0) + sign * a[i][j] / r) / 2
           for j in range(2)] for i in range(2)] for sign in (1, -1)]
    zero = [[0, 0], [0, 0]]
    errors = {'A_square_residual_meV2': difference(mm(a, a), [[r * r, 0], [0, r * r]]),
              'projector_orthogonal_residual_dimensionless': difference(mm(p[0], p[1]), zero),
              'projector_idempotent_residual_dimensionless': 0.0,
              'eigen_residual_meV': 0.0}
    for sign, proj in zip((1, -1), p):
        errors['projector_idempotent_residual_dimensionless'] = max(
            errors['projector_idempotent_residual_dimensionless'], difference(mm(proj, proj), proj))
        errors['eigen_residual_meV'] = max(errors['eigen_residual_meV'],
                                          difference(mm(a, proj), scale(sign * r, proj)))
    return errors


def svg_start(title, subtitle, width, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{escape(title)}</title>',
            f'<desc>{escape(subtitle)}</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
            '<g font-family="Arial, sans-serif" fill="#182738">',
            f'<text x="70" y="34" font-size="22" font-weight="bold">{escape(title)}</text>',
            f'<text x="70" y="59" font-size="13">{escape(subtitle)}</text>']


def plot(parts, box, bounds, xticks, yticks, xlabel, ylabel, curves):
    left, top, width, height = box
    xmin, xmax, ymin, ymax = bounds
    def xy(x, y):
        return left + width * (x - xmin) / (xmax - xmin), top + height * (ymax - y) / (ymax - ymin)
    for x in xticks:
        px, _ = xy(x, ymin)
        parts += [f'<path d="M{px:.2f},{top}v{height}" stroke="#e4e9ee"/>',
                  f'<text x="{px:.2f}" y="{top+height+21}" text-anchor="middle" font-size="12">{x:g}</text>']
    for y in yticks:
        _, py = xy(xmin, y)
        parts += [f'<path d="M{left},{py:.2f}h{width}" stroke="#e4e9ee"/>',
                  f'<text x="{left-12}" y="{py+4:.2f}" text-anchor="end" font-size="12">{y:g}</text>']
    if ymin <= 0 <= ymax:
        _, py = xy(xmin, 0)
        parts.append(f'<path d="M{left},{py:.2f}h{width}" stroke="#697b8c" stroke-width="1.4"/>')
    parts += [f'<path d="M{left},{top}v{height}h{width}" fill="none" stroke="#182738"/>',
              f'<text x="{left+width/2}" y="{top+height+46}" text-anchor="middle" font-size="14">{escape(xlabel)}</text>',
              f'<text transform="translate({left-58},{top+height/2}) rotate(-90)" text-anchor="middle" font-size="14">{escape(ylabel)}</text>']
    for values, color, dash in curves:
        coords = [xy(x, y) for x, y in values]
        path = ' '.join(('M' if i == 0 else 'L') + f'{x:.2f},{y:.2f}' for i, (x, y) in enumerate(coords))
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.3"{(" stroke-dasharray=\"7 5\"" if dash else "")}/>')


def radial_plot():
    parts = svg_start('Which radius is most probable?',
                      'Point Coulomb, Z=1, infinite nucleus, no spin; rho = r/a; radial shell probability', 900, 520)
    styles = [('1s: n=1, l=0', (1, 0), '#1763a6'),
              ('2s: n=2, l=0', (2, 0), '#bd6031'),
              ('2p: n=2, l=1', (2, 1), '#3a8559')]
    plot(parts, (90, 115, 730, 300), (0, 18, 0, 0.58), range(0, 19, 3), [0, .1, .2, .3, .4, .5],
         'rho = r/a (dimensionless)', 'dP/d(rho) = |U|^2 (dimensionless)',
         [([(18 * i / 720, radial(*nl, 18 * i / 720) ** 2) for i in range(721)], color, False)
          for _, nl, color in styles])
    for i, (label, _, color) in enumerate(styles):
        x = 100 + i * 240
        parts += [f'<path d="M{x},88h30" stroke="{color}" stroke-width="3"/>',
                  f'<text x="{x+40}" y="93" font-size="14">{label}</text>']
    parts += ['<text x="90" y="489" font-size="13">1s shell density peaks at rho=1; local volume density peaks at r=0.</text>', '</g></svg>']
    return '\n'.join(parts) + '\n'


def near_plot():
    delta = 2.0  # meV, mathematical teaching model, not hydrogen fine structure
    qs = [1.5 * i / 600 for i in range(601)]
    exact = [(q, delta * math.sqrt(.25 + q * q)) for q in qs]
    second = [(q, delta * (.5 + q * q)) for q in qs]
    parts = svg_start('Small coupling relative to which gap?',
                      'Finite 2-state model; Delta=2 meV; q=|V|/Delta; E0 is a common energy shift', 900, 730)
    plot(parts, (95, 115, 720, 290), (0, 1.5, -6, 6), [0, .25, .5, .75, 1, 1.25, 1.5], [-6, -3, 0, 3, 6],
         'q = |V|/Delta (dimensionless)', 'E - E0 (meV)',
         [(exact, '#1763a6', False), ([(x, -y) for x, y in exact], '#1763a6', False),
          (second, '#bd6031', True), ([(x, -y) for x, y in second], '#bd6031', True)])
    for x, color, label, dash in [(115, '#1763a6', 'exact eigenvalues', False), (400, '#bd6031', 'nondegenerate second order', True)]:
        parts += [f'<path d="M{x},88h35" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="7 5"' if dash else '')+'/>',
                  f'<text x="{x+45}" y="93" font-size="14">{label}</text>']
    plot(parts, (95, 510, 720, 135), (0, 1.5, 0, 2.4), [0, .25, .5, .75, 1, 1.25, 1.5], [0, .8, 1.6, 2.4],
         'q = |V|/Delta (dimensionless)', 'Upper-branch error (meV)',
         [([(q, ap - ex) for (q, ap), (_, ex) in zip(second, exact)], '#8546a1', False)])
    parts += ['<text x="95" y="714" font-size="13">At Delta=0 use degenerate diagonalization; this q-axis is then undefined.</text>', '</g></svg>']
    return '\n'.join(parts) + '\n'


def main():
    report = {'model': {'Z': 1, 'mu_kg': ME, 'nuclear_mass': 'infinite', 'spin': False,
                        'coulomb_field': 'zero except for first-order n=2 Stark projection',
                        'constants': 'NIST 2022 CODATA nominal; no uncertainty propagation'},
              'scales': {'hbar_J_s': HBAR, 'g_J_m': G, 'a_m': A0, 'rydberg_J': RY,
                         'rydberg_eV': RY / E, 'E2_eV': -RY / (4 * E)},
              'integration': {'rho_max': LIMIT, 'panels_coarse': N, 'panels_fine': 2*N,
                              'renormalization': False}, 'radial': {}}
    for n, l, mean in [(1, 0, 1.5), (2, 0, 6.0), (2, 1, 5.0)]:
        prob = lambda rho: radial(n, l, rho) ** 2
        norm = simpson(prob, 0, LIMIT, 2*N)
        norm_coarse = simpson(prob, 0, LIMIT, N)
        avg = simpson(lambda rho: rho * prob(rho), 0, LIMIT, 2*N)
        avg_coarse = simpson(lambda rho: rho * prob(rho), 0, LIMIT, N)
        d = 1e-4
        residual = max(abs(-(radial(n,l,rho+d)-2*radial(n,l,rho)+radial(n,l,rho-d))/d**2
                           + (l*(l+1)/rho**2 - 2/rho + 1/n**2)*radial(n,l,rho))
                       for rho in [.3, .8, 1.7, 3.4, 6])
        if n == 1:
            tail_bound = 4 * monomial_tail(2, 2, LIMIT)
        elif l == 0:
            tail_bound = sum(c * monomial_tail(k,1,LIMIT) for k,c in [(4,1/8),(3,1/2),(2,1/2)])
        else:
            tail_bound = monomial_tail(4, 1, LIMIT)/24
        assert abs(norm-1) < 1e-8 and abs(avg-mean) < 1e-8
        assert abs(norm-norm_coarse) < 2e-8 and abs(avg-avg_coarse) < 2e-8
        assert residual < 1e-6 and tail_bound < 1e-18
        report['radial'][f'{n},{l}'] = {'norm': norm, 'mean_r_over_a': avg,
            'norm_coarse_fine_diff': abs(norm-norm_coarse), 'mean_coarse_fine_diff': abs(avg-avg_coarse),
            'tail_probability_bound': tail_bound, 'finite_difference_residual': residual,
            'fd_step_rho': d, 'fd_probe_rho': [.3,.8,1.7,3.4,6]}
    overlap = simpson(lambda rho: radial(1,0,rho)*radial(2,0,rho),0,LIMIT,2*N)
    dipole = simpson(lambda rho: rho*radial(2,0,rho)*radial(2,1,rho),0,LIMIT,2*N)
    angular = math.sqrt(3)/2 * simpson(lambda c: c*c,-1,1,400)
    assert abs(overlap) < 1e-8 and abs(dipole+3*math.sqrt(3)) < 1e-8
    assert abs(dipole*angular+3) < 1e-8
    z = [[0,-3,0,0],[-3,0,0,0],[0,0,0,0],[0,0,0,0]]
    states = [[1/math.sqrt(2),1/math.sqrt(2),0,0],
              [1/math.sqrt(2),-1/math.sqrt(2),0,0],[0,0,1,0],[0,0,0,1]]
    shifts = [-3,3,0,0]
    stark_res = max(abs(sum(z[i][j]*v[j] for j in range(4))-shift*v[i])
                    for v,shift in zip(states,shifts) for i in range(4))
    assert stark_res < 1e-14
    report['stark'] = {'s_radial_overlap_1s_2s': overlap, 'radial_dipole_over_a': dipole,
        'angular_dipole': angular, 'z_2s_2p0_over_a': dipole*angular,
        'eigen_residual_dimensionless': stark_res, 'field_V_per_m': 1000,
        'shift_abs_eV': 3*1000*A0, 'outside_level_gap_E3_E2_eV': 5*RY/(36*E),
        'ionization_rate_computed': False}
    cases=[]
    for q in [0,.1,.5,1,1.5]:
        delta=2.0
        v=delta*q*complex(.6,.8)
        r=math.hypot(delta/2,abs(v))
        approx=delta/2+abs(v)**2/delta
        err=abs(v)**4/(delta**2*(approx+r))
        residual=finite_projectors(delta,v)
        assert max(residual.values()) < 1e-13 and abs(approx-r-err) < 1e-14
        cases.append({'q':q,'delta_meV':delta,'V_meV_real_imag':[v.real,v.imag],
                      'exact_upper_offset_meV':r,'second_upper_offset_meV':approx,
                      'upper_absolute_error_meV':err,'upper_relative_error':err/r,
                      'residuals':residual})
    deg_res=finite_projectors(0,complex(6e-7,8e-7))
    assert max(deg_res.values()) < 1e-13
    report['near_degenerate']={'cases':cases,'delta_zero_V_abs_meV':1e-6,
                              'delta_zero_gap_meV':2e-6,'delta_zero_residuals':deg_res}
    report['variation']=[]
    for s in [.5,1,2]:  # b/a, spatial gradient form, not derivative of u alone
        prob=lambda rho: (2*rho*s**(-1.5)*math.exp(-rho/s))**2
        norm=simpson(prob,0,LIMIT,2*N)
        kin=simpson(lambda rho: prob(rho)/s**2,0,LIMIT,2*N)
        pot=simpson(lambda rho: -2*prob(rho)/rho if rho else 0,0,LIMIT,2*N)
        expected=1/s**2-2/s
        assert abs(norm-1)<1e-8 and abs(kin+pot-expected)<1e-8
        report['variation'].append({'b_over_a':s,'norm':norm,'kinetic_over_Ry':kin,
                                   'potential_over_Ry':pot,'total_over_Ry':kin+pot,
                                   'exact_trial_energy_over_Ry':expected,
                                   'ground_gap_over_Ry':(1/s-1)**2})
    report['checks_passed']=True
    OUT.mkdir(exist_ok=True)
    (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'hydrogen-radial.svg').write_text(radial_plot(),encoding='utf-8')
    (OUT/'near-degenerate.svg').write_text(near_plot(),encoding='utf-8')
    print(json.dumps({'checks_passed':True,'a_nm':A0*1e9,'rydberg_eV':RY/E,
                      'stark_z_over_a':dipole*angular,'output_dir':str(OUT)},ensure_ascii=False))


if __name__ == '__main__':
    main()
