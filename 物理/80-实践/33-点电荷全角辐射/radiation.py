#!/usr/bin/env python3
"""All-angle radiation of prescribed point-charge motion; standard library only."""
import argparse
import csv
import json
import math
from pathlib import Path


def simpson(f, lo, hi, n):
    if n < 2 or n % 2:
        raise ValueError("Simpson intervals must be positive and even")
    h = (hi-lo)/n
    return h/3 * math.fsum((1 if i in (0, n) else 4 if i % 2 else 2)*f(lo+i*h)
                           for i in range(n+1))


def cross(u, v):
    return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])


def angular(beta, ap, az, mu, phi):
    """Return |n x [(n-beta) x a]|^2 / kappa^5; acceleration in arbitrary common units."""
    sint = math.sqrt(max(0, 1-mu*mu))
    n = (sint*math.cos(phi), sint*math.sin(phi), mu)
    q = cross(n, cross((n[0], n[1], mu-beta), (ap, 0, az)))
    return math.fsum(v*v for v in q)/(1-beta*mu)**5


def sphere(beta, ap, az, nm, nphi, moment=False):
    # w is the rest-frame polar cosine used only as a quadrature variable.
    # The integrand remains the lab-frame cross product and lab dOmega measure.
    def at_w(w):
        mu = (w+beta)/(1+beta*w)
        jac = (1-beta*beta)/(1+beta*w)**2
        azim = math.fsum(angular(beta, ap, az, mu, 2*math.pi*j/nphi)
                        for j in range(nphi))*2*math.pi/nphi
        return azim*jac*(mu if moment else 1)
    return simpson(at_w, -1, 1, nm)


def oracle(beta, ap, az):
    g2 = 1/(1-beta*beta)
    return 8*math.pi/3*(g2**3*az*az+g2**2*ap*ap)


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def plot_svg(path, panels):
    # Plot polylines directly from the same arrays exported to CSV.
    colors = ["#176799", "#b14e16", "#6f4599"]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430">',
           '<rect width="1000" height="430" fill="white"/>',
           '<g font-family="sans-serif" font-size="14" fill="#202b36">']
    for panel_index, (title, xlabel, ylabel, curves, xmin, xmax, ymin, ymax) in enumerate(panels):
        left, top, width, height = 75+panel_index*495, 65, 390, 270
        sx = lambda x: left+(x-xmin)/(xmax-xmin)*width
        sy = lambda y: top+height-(y-ymin)/(ymax-ymin)*height
        svg.append(f'<text x="{left}" y="27">{title}</text>')
        for i in range(6):
            x = xmin+(xmax-xmin)*i/5
            y = ymin+(ymax-ymin)*i/5
            svg.append(f'<path d="M {sx(x):.2f} {top} V {top+height}" stroke="#e4e9ed"/>')
            svg.append(f'<path d="M {left} {sy(y):.2f} H {left+width}" stroke="#e4e9ed"/>')
            svg.append(f'<text x="{sx(x):.2f}" y="{top+height+22}" text-anchor="middle">{x:.2g}</text>')
            svg.append(f'<text x="{left-8}" y="{sy(y)+5:.2f}" text-anchor="end">{y:.2g}</text>')
        svg.append(f'<path d="M {left} {top} V {top+height} H {left+width}" fill="none" stroke="#333"/>')
        svg.append(f'<text x="{left+width/2}" y="{top+height+48}" text-anchor="middle">{xlabel}</text>')
        svg.append(f'<text x="{left}" y="48">{ylabel}</text>')
        for k, (label, xs, ys) in enumerate(curves):
            pts = ' '.join(f'{sx(x):.3f},{sy(y):.3f}' for x, y in zip(xs, ys))
            dash = '' if k == 0 else f' stroke-dasharray="{8 if k == 1 else 3} 4"'
            svg.append(f'<polyline points="{pts}" fill="none" stroke="{colors[k]}" stroke-width="2.3"{dash}/>')
            svg.append(f'<text x="{left+12}" y="{400+k*18}" fill="{colors[k]}">{label}</text>')
    svg.append('</g></svg>')
    path.write_text('\n'.join(svg), encoding='utf-8')


def run(config, out):
    for name in ("angle_intervals", "time_intervals"):
        if not isinstance(config[name], int) or config[name] < 2 or config[name] % 2:
            raise ValueError(name + " must be even and >= 2")
    if not isinstance(config['azimuth_nodes'], int) or config['azimuth_nodes'] < 4:
        raise ValueError('azimuth_nodes must be integer >=4')
    c, eps, q = (config[k] for k in ('c_m_s', 'epsilon0_F_m', 'q_C'))
    b, length = config['pulse_b'], config['pulse_L_m']
    if not (c > 0 and eps > 0 and q != 0 and length > 0 and 0 < b < 1):
        raise ValueError('invalid physical inputs')
    nm, np_, nt = config['angle_intervals'], config['azimuth_nodes'], config['time_intervals']
    cases = []
    for case in config['cases']:
        beta, ap, az = (case[k] for k in ('beta', 'a_perp', 'a_parallel'))
        if not 0 <= beta < 1 or ap*ap+az*az == 0:
            raise ValueError('nonzero acceleration and 0<=beta<1 required')
        exact = oracle(beta, ap, az)
        p1, p2 = sphere(beta, ap, az, nm, np_), sphere(beta, ap, az, 2*nm, 2*np_)
        mz = sphere(beta, ap, az, 2*nm, 2*np_, moment=True)
        cases.append(dict(case, integral=p2, oracle=exact,
                          rel_error=p2/exact-1, mesh_change=p2/p1-1,
                          z_momentum_residual=mz/exact-beta))
    tscale = length/c
    cpower = q*q/(16*math.pi**2*eps*c**3)
    def pulse(u, angles=False):
        vel = b*math.sin(math.pi*u)**2
        acc = c*b*math.pi/tscale*math.sin(2*math.pi*u)
        return cpower*(sphere(vel, 0, acc, nm, np_) if angles else oracle(vel, 0, acc))
    total1 = tscale*simpson(pulse, 0, 1, nt)
    total2 = tscale*simpson(pulse, 0, 1, 2*nt)
    allangle = tscale*simpson(lambda u:pulse(u, True), 0, 1, nt)
    nr = q*q*b*b*math.pi/(12*eps*c*tscale)
    wy = q*q*b*b/(32*eps*c*tscale)
    rows = [(i/400, pulse(i/400), pulse(i/400)/(1-b*b*math.sin(math.pi*i/400)**4)**(-3)) for i in range(401)]
    # Third column removes gamma^6, i.e. Larmor prediction on the same history.
    write_csv(out/'pulse.csv', ['source_time_over_T', 'P_Lienard_W', 'P_Larmor_W'], rows)
    angles = []
    for i in range(901):
        theta = math.pi*i/900
        angles.append((theta, *(angular(v, 0, 1, math.cos(theta), 0)/oracle(v, 0, 1) for v in (0, .6))))
    write_csv(out/'angles.csv', ['theta_rad', 'Uem_over_P_beta0_sr-1', 'Uem_over_P_beta0.6_sr-1'], angles)
    beta = .995
    gamma = 1/math.sqrt(1-beta*beta)
    beam = []
    for i in range(501):
        x = 3*i/500
        mu = math.cos(x/gamma)
        em = angular(beta, 0, 1, mu, 0)
        beam.append((x, em, em/(1-beta*mu)))
    emmax, arrmax = max(r[1] for r in beam), max(r[2] for r in beam)
    write_csv(out/'beam.csv', ['gamma_theta', 'Uem_over_Ca2', 'Uarr_over_Ca2'], beam)
    (out/'assets').mkdir()
    plot_svg(out/'assets/emission-angle.svg', [
        ('Emission per unit source time', 'theta (rad)', 'U_em / P (sr^-1)',
         [('beta = 0', [r[0] for r in angles], [r[1] for r in angles]),
          ('beta = 0.6', [r[0] for r in angles], [r[2] for r in angles])], 0, math.pi, 0, .7),
        ('Parallel acceleration, beta = 0.995', 'gamma * theta', 'Each curve / its own maximum',
         [('source time: kappa^-5', [r[0] for r in beam], [r[1]/emmax for r in beam]),
          ('arrival time: kappa^-6', [r[0] for r in beam], [r[2]/arrmax for r in beam])], 0, 3, 0, 1.05)])
    results = {'cases':cases, 'pulse':{'T_s':tscale, 'W_J':total2, 'W_full_angle_J':allangle,
        'time_mesh_relative_change':total2/total1-1, 'full_angle_relative_difference':allangle/total2-1,
        'W_NR_J':nr, 'relativistic_to_NR':total2/nr, 'W_y_J_sr':wy,
        'wrong_4pi_y_to_total':4*math.pi*wy/total2},
        'peak_gamma_theta':{'emission':gamma*math.acos((math.sqrt(1+15*beta*beta)-1)/(3*beta)),
        'arrival':gamma*math.acos((math.sqrt(1+24*beta*beta)-1)/(4*beta))}}
    assert max(abs(x['rel_error']) for x in cases) < 1e-9
    assert max(abs(x['z_momentum_residual']) for x in cases) < 1e-9
    assert abs(allangle/total2-1) < 1e-7
    assert abs(total2/total1-1) < 1e-7
    (out/'results.json').write_text(json.dumps(results, indent=2, allow_nan=False)+'\n')
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, default=Path(__file__).with_name('inputs.json'))
    p.add_argument('--output', type=Path, required=True, help='new, nonexisting output directory')
    args = p.parse_args()
    config = json.loads(args.inputs.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    print(json.dumps(run(config, args.output), indent=2, allow_nan=False))
