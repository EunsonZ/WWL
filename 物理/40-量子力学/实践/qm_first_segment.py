#!/usr/bin/env python3
"""Recompute the explicitly finite model and exact free Gaussian; no solver/hardware."""
import cmath
import json
import math
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
H = 6.62607015e-34
HBAR = H / (2 * math.pi)
MASS = 1e-30
S = 1e-9
K0 = 1e9
T0 = 2 * MASS * S * S / HBAR
V0 = HBAR * K0 / MASS
OMEGA = 2 * math.pi * 1e6
TOL = 1e-12


def dagger(a):
    return [[a[j][i].conjugate() for j in range(len(a))] for i in range(len(a[0]))]


def mul(a, b):
    assert len(a[0]) == len(b)
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def add(a, b):
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def scale(c, a):
    return [[c * x for x in row] for row in a]


def trace(a):
    return sum(a[i][i] for i in range(len(a)))


def close(a, b, tol=TOL):
    if isinstance(a, list):
        assert len(a) == len(b)
        for aa, bb in zip(a, b):
            close(aa, bb, tol)
    else:
        assert abs(a - b) <= tol, (a, b, tol)


I = [[1, 0], [0, 1]]
Z = [[1, 0], [0, -1]]
X = [[0, 1], [1, 0]]
Y = [[0, -1j], [1j, 0]]
Q = scale(1 / math.sqrt(2), [[1, 1], [1, -1]])
PZ = [[1, 0], [0, 0]]
PX = scale(0.5, [[1, 1], [1, 1]])
PXM = scale(0.5, [[1, -1], [-1, 1]])
RC = PX
RM = scale(0.5, I)


def probability(rho, projector):
    z = trace(mul(rho, projector))
    assert abs(complex(z).imag) < TOL
    p = complex(z).real
    assert -TOL <= p <= 1 + TOL
    return p


def evolved(rho, t):
    u = [[cmath.exp(-0.5j * OMEGA * t), 0], [0, cmath.exp(0.5j * OMEGA * t)]]
    close(mul(dagger(u), u), I)
    rt = mul(mul(u, rho), dagger(u))
    close(trace(rt), 1)
    close(rt, dagger(rt))
    return rt


def gauss(x, t, k=K0):
    tau = t / T0
    v = HBAR * k / MASS
    return ((2 * math.pi * S * S) ** (-0.25) / cmath.sqrt(1 + 1j * tau)
            * cmath.exp(-(x - v * t) ** 2 / (4 * S * S * (1 + 1j * tau))
                        + 1j * k * x - 0.5j * HBAR * k * k * t / MASS))


def density(x, t, k=K0):
    return abs(gauss(x, t, k)) ** 2


def current(x, t, k=K0):
    psi = gauss(x, t, k)
    tau = t / T0
    v = HBAR * k / MASS
    derivative = psi * (-(x - v * t) / (2 * S * S * (1 + 1j * tau)) + 1j * k)
    return HBAR / MASS * (psi.conjugate() * derivative).imag


def rho_dimensionless(xi, tau):
    return S * density(xi * S, tau * T0)


def flow_dimensionless(xi, tau):
    return T0 * current(xi * S, tau * T0)


def trap(fn, left=-20.0, right=20.0, n=4000):
    step = (right - left) / n
    return step * (0.5 * (fn(left) + fn(right))
                   + sum(fn(left + i * step) for i in range(1, n)))


def interval_probability(a, b, tau):
    center = 2 * K0 * S * tau
    width = math.sqrt(1 + tau * tau)
    return 0.5 * (math.erf((b - center) / (math.sqrt(2) * width))
                  - math.erf((a - center) / (math.sqrt(2) * width)))


def svg_panel(title, description, panels, filename):
    extra_height = 180 if any('zoom' in p for p in panels) else 0
    canvas_height = 90 + 230 * len(panels) + extra_height
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="820" height="{canvas_height}" viewBox="0 0 820 {canvas_height}" role="img">',
             f'<title>{title}</title><desc>{description}</desc>',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="Arial, sans-serif" fill="#17212b" font-size="14">',
             f'<text x="30" y="28" font-size="19">{title}</text>']
    for panel_index, panel in enumerate(panels):
        x0, y0, width, height = 90, 70 + panel_index * 230, 660, 145
        xmin, xmax, ymin, ymax = panel["range"]
        tx = lambda x: x0 + (x - xmin) * width / (xmax - xmin)
        ty = lambda y: y0 + height - (y - ymin) * height / (ymax - ymin)
        parts.append(f'<path d="M{x0},{y0} V{y0+height} H{x0+width}" stroke="#17212b" fill="none"/>')
        for i in range(5):
            x = xmin + i * (xmax - xmin) / 4
            parts.append(f'<text x="{tx(x):.2f}" y="{y0+height+19}" text-anchor="middle">{x:g}</text>')
        for i in range(4):
            y = ymin + i * (ymax - ymin) / 3
            parts.append(f'<text x="{x0-10}" y="{ty(y)+5:.2f}" text-anchor="end">{y:.3g}</text>')
        parts.append(f'<text x="{x0}" y="{y0-14}">{panel["ylabel"]}</text>')
        parts.append(f'<text x="{x0+width}" y="{y0+height+40}" text-anchor="end">{panel["xlabel"]}</text>')
        if ymin < 0 < ymax:
            parts.append(f'<path d="M{x0},{ty(0):.2f} H{x0+width}" stroke="#596773" stroke-width="1.2" stroke-dasharray="3 3"/>')
        for index, (label, points) in enumerate(panel["curves"]):
            color = ["#1756a9", "#ab4700"][index]
            dash = '' if index == 0 else ' stroke-dasharray="7 5"'
            coords = ' '.join(f'{tx(x):.3f},{ty(y):.3f}' for x, y in points)
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.4"{dash}/>')
            yy = y0 + 10 + 20 * index
            parts.append(f'<path d="M{570},{yy} H{600}" stroke="{color}" stroke-width="2.4"{dash}/><text x="610" y="{yy+5}">{label}</text>')
        if 'zoom' in panel:
            zoom = panel['zoom']
            zx, zy, zw, zh = 105, y0 + height + 85, 310, 90
            za, zb, zc, zd = zoom['range']
            ztx = lambda x: zx + (x-za)*zw/(zb-za)
            zty = lambda y: zy + zh - (y-zc)*zh/(zd-zc)
            parts.append(f'<text x="{zx}" y="{zy-17}">Same t=t0 data: negative-tail zoom</text>')
            parts.append(f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" fill="none" stroke="#596773"/>')
            for x in [za, (za+zb)/2, zb]:
                parts.append(f'<text x="{ztx(x):.2f}" y="{zy+zh+19}" text-anchor="middle">{x:g}</text>')
            for y in [zc, (zc+zd)/2, zd]:
                parts.append(f'<text x="{zx-8}" y="{zty(y)+5:.2f}" text-anchor="end">{y:g}</text>')
            coords = ' '.join(f'{ztx(x):.3f},{zty(y):.3f}' for x, y in zoom['points'])
            parts.append(f'<polyline points="{coords}" fill="none" stroke="#ab4700" stroke-width="2.4" stroke-dasharray="7 5"/>')
            parts.append(f'<text x="{zx+zw}" y="{zy+zh+39}" text-anchor="end">x (nm)</text>')
            for index, line in enumerate(zoom['annotation']):
                parts.append(f'<text x="455" y="{zy+12+22*index}">{line}</text>')
    parts.append('</g></svg>')
    (ASSETS / filename).write_text('\n'.join(parts) + '\n', encoding='utf-8')


def main():
    ASSETS.mkdir(exist_ok=True)
    psi = scale(1 / math.sqrt(2), [[1], [1j]])
    phi = scale(1 / math.sqrt(2), [[1], [1]])
    a = [[0, 1j], [2, 0]]
    close(mul(dagger(psi), phi)[0][0], (1-1j)/2)
    close(mul(mul(dagger(psi), a), phi)[0][0], -0.5j)
    close(mul(dagger(mul(dagger(a), psi)), phi)[0][0], -0.5j)
    close(mul(dagger(Q), Q), I)
    close(mul(mul(dagger(Q), X), Q), Z)
    close(mul(mul(dagger(Q), RC), Q), [[1, 0], [0, 0]])
    close(mul(mul(dagger(Q), RM), Q), RM)
    close(add(mul(Z, X), scale(-1, mul(X, Z))), scale(2j, Y))
    measurements = []
    for label, rho, xplus, purity in [('coherent', RC, 1, 1), ('mixed', RM, 0.5, 0.5)]:
        close(probability(rho, PZ), 0.5)
        close(probability(rho, PX), xplus)
        close(trace(mul(rho, rho)), purity)
        measurements.append({'state': label, 'z_plus': 0.5, 'x_plus': xplus, 'purity': purity})
    times = [i * 1e-6 / 400 for i in range(401)]
    pc = [probability(evolved(RC, t), PX) for t in times]
    pm = [probability(evolved(RM, t), PX) for t in times]
    for t, c, m in zip(times, pc, pm):
        close(c, 0.5 * (1 + math.cos(OMEGA * t)))
        close(m, 0.5)
    after_x = add(mul(mul(PX, PZ), PX), mul(mul(PXM, PZ), PXM))
    close(after_x, RM)
    close(probability(after_x, PZ), 0.5)
    for theta in [0, math.pi/2, math.pi, -math.pi/2]:
        v = scale(1/math.sqrt(2), [[1], [cmath.exp(1j*theta)]])
        rho = mul(v, dagger(v))
        close(probability(rho, PX), (1+math.cos(theta))/2)
        close(probability(rho, scale(0.5, add(I, Y))), (1+math.sin(theta))/2)
    for eta in [0, 0.4, 1]:
        effect = scale(0.5, add(I, scale(eta, Z)))
        close(probability(PZ, effect), (1+eta)/2)

    gaussian_records = []
    for tau in [0, 0.5, 1]:
        norm = trap(lambda xi: rho_dimensionless(xi, tau))
        mean = trap(lambda xi: xi * rho_dimensionless(xi, tau))
        variance = trap(lambda xi: (xi-2*tau)**2 * rho_dimensionless(xi, tau))
        close(norm, 1, 1e-11)
        close(mean, 2*tau, 1e-11)
        close(variance, 1+tau*tau, 1e-11)
        gaussian_records.append({'t_over_t0': tau, 'norm_trapezoid': norm,
                                 'mean_over_s': mean, 'variance_over_s_squared': variance})
    for x in [-2*S, 0, 3*S]:
        close(S * density(x, 0, 0), S * density(x, 0, K0))
        close(T0 * current(x, 0, 0), 0)
        close(T0 * current(x, 0), T0 * V0 * density(x, 0))
    residuals = []
    delta_tau, delta_xi = 1e-5, 1e-4
    for xi in [-3, -1, 0, 2, 4]:
        tau = 0.7
        drho_dtau = (rho_dimensionless(xi, tau+delta_tau) - rho_dimensionless(xi, tau-delta_tau))/(2*delta_tau)
        dj_dxi = (flow_dimensionless(xi+delta_xi, tau) - flow_dimensionless(xi-delta_xi, tau))/(2*delta_xi)
        residuals.append(abs(drho_dtau + dj_dxi))
    assert max(residuals) < 1e-8
    tau = 0.5
    numerical_window_rate = (interval_probability(-1, 1, tau+delta_tau) - interval_probability(-1, 1, tau-delta_tau))/(2*delta_tau)
    boundary_rate = flow_dimensionless(-1, tau) - flow_dimensionless(1, tau)
    close(numerical_window_rate, boundary_rate, 1e-8)
    # Direct residual for i d_tau psi = -d_xi^2 psi, scaled by sqrt(S).
    schroedinger_residuals = []
    for xi in [-2, 0, 2, 4]:
        tau = 0.7
        fn = lambda u, v: math.sqrt(S) * gauss(u*S, v*T0)
        dt = (fn(xi, tau+delta_tau)-fn(xi, tau-delta_tau))/(2*delta_tau)
        dxx = (fn(xi+delta_xi, tau)-2*fn(xi, tau)+fn(xi-delta_xi, tau))/(delta_xi**2)
        schroedinger_residuals.append(abs(1j*dt + dxx))
    assert max(schroedinger_residuals) < 1e-7
    close(interval_probability(-1, 1, 0), math.erf(1/math.sqrt(2)))

    svg_panel('Same z distribution, different x prediction',
              'Closed two-state system; Omega=2*pi*1 MHz. Solid coherent state; dashed maximally mixed state.',
              [{'range': (0, 1, 0, 1), 'xlabel': 't (microseconds)', 'ylabel': 'P(x+) (dimensionless)',
                'curves': [('coherent', [(t*1e6, p) for t, p in zip(times, pc)]),
                           ('mixed', [(t*1e6, p) for t, p in zip(times, pm)])]}], 'two-state.svg')
    xs = [(-6 + i * 14/400) * 1e-9 for i in range(401)]
    curves_rho = [(label, [(x*1e9, density(x, t)*1e-9) for x in xs]) for label, t in [('t=0', 0), ('t=t0', T0)]]
    curves_j = [(label, [(x*1e9, current(x, t)/1e13) for x in xs]) for label, t in [('t=0', 0), ('t=t0', T0)]]
    tail_x, tail_y = min(curves_j[1][1], key=lambda point: point[1])
    svg_panel('Free Gaussian: density and probability flow',
              'One-dimensional full line, V=0, m=1e-30 kg, s=1 nm, k0=1 per nm. Density and flow have separate vertical scales. At t=t0, x less than -2 nm has a small negative flow from spreading, retained on the full axis and enlarged using the same data.',
              [{'range': (-6, 8, 0, 0.42), 'xlabel': 'x (nm)', 'ylabel': 'density (per nm)', 'curves': curves_rho},
               {'range': (-6, 8, -0.03, 4.5), 'xlabel': 'x (nm)', 'ylabel': 'probability flow (1e13 per second)', 'curves': curves_j,
                'zoom': {'range': (-3, -2, -0.003, 0),
                         'points': [(x,y) for x,y in curves_j[1][1] if -3 <= x <= -2],
                         'annotation': ['spread-induced negative tail',
                                        f'sampled min: {tail_y*1e13:.6g} per second',
                                        f'at x = {tail_x:.3f} nm, t = t0',
                                        'zoom y unit: 1e13 per second',
                                        'zero crossing: x = -2 nm']}}],
              'gaussian-current.svg')
    report = {'model': 'finite matrices and exact free Gaussian, no numerical time solver',
              'matrix_shape': [2, 2], 'ket_shape': [2, 1], 'ordered_basis': ['+z', '-z'],
              'dirac_inner_product': 'conjugate-linear first, linear second',
              'parameters_SI': {'h_J_s': H, 'hbar_J_s': HBAR, 'm_kg': MASS, 's_m': S, 'k0_per_m': K0,
                                't0_s': T0, 'v0_m_per_s': V0, 'Omega_rad_per_s': OMEGA},
              'matrix_absolute_tolerance': TOL, 'measurements': measurements,
              'coherent_quarter_period_probabilities': [pc[i] for i in [0, 100, 200, 300, 400]],
              'after_nonselective_x_z_plus': probability(after_x, PZ),
              'gaussian_quadrature': {'xi_range': [-20, 20], 'steps': 4000, 'records': gaussian_records},
              'continuity_finite_difference': {'delta_tau': delta_tau, 'delta_xi': delta_xi,
                                               'max_dimensionless_residual': max(residuals)},
              'schroedinger_max_dimensionless_residual': max(schroedinger_residuals),
              'window_rate_per_tau': {'finite_difference': numerical_window_rate, 'boundary_flow': boundary_rate},
              'energy_J': HBAR**2/(2*MASS)*(K0*K0+1/(4*S*S)),
              'probability_flow_negative_tail': {'time_s': T0, 'sampled_min_per_s': tail_y*1e13,
                                                  'sampled_min_x_nm': tail_x, 'exact_zero_crossing_x_nm': -2,
                                                  'main_y_range_in_1e13_per_s': [-0.03, 4.5],
                                                  'zoom_x_range_nm': [-3, -2], 'zoom_y_range_in_1e13_per_s': [-0.003, 0]},
              'not_tested': ['hardware', 'tomography', 'QND', 'open-system evolution', 'continuous-spectrum theorem',
                             'Obsidian rendering', 'learner understanding']}
    (ASSETS/'checks.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 't0_fs': T0*1e15,
                      'continuity_residual': max(residuals),
                      'schroedinger_residual': max(schroedinger_residuals),
                      'energy_J': report['energy_J']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
