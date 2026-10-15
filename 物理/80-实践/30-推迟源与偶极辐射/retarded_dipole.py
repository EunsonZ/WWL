#!/usr/bin/env python3
"""Finite prescribed polarization source; standard library, one CPU thread.
Writes only to the requested output directory. Not a self-consistent antenna solver.
"""
from __future__ import annotations
import argparse
import cmath
import csv
import json
import math
from pathlib import Path

C = 299792458.0
EPS = 8.8541878128e-12
P0, FREQ, A, R, T = 1e-12, 1e8, 1e-3, 30.0, 20e-9


def simpson(fun, left, right, n=800):
    if n <= 0 or n % 2:
        raise ValueError('Simpson panel count must be positive and even')
    h = (right - left) / n
    return h / 3 * (fun(left) + fun(right) + sum(
        (4 if j % 2 else 2) * fun(left + j*h) for j in range(1, n)))


def form_factor(x):
    if abs(x) < .05:
        # Direct sin(x)-x*cos(x) loses significant digits near zero.
        return 1 - x*x/10 + x**4/280 - x**6/15120 + x**8/1330560
    return 3*(math.sin(x)-x*math.cos(x))/x**3


def sinc(x):
    return 1 if x == 0 else math.sin(x)/x


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def norm(v):
    return math.sqrt(sum(abs(z)**2 for z in v))


def fields(pos):
    """Complex peak fields at omega=c=epsilon=mu=p0=1, F=1, t=0."""
    r = norm(pos)
    n = tuple(x/r for x in pos)
    phase = cmath.exp(1j*r)/(4*math.pi)
    p, pd, pdd = (0, 0, 1), (0, 0, -1j), (0, 0, -1)
    pp = cross(n, cross(n, pdd))
    e = tuple(phase*((3*n[j]*n[2]-p[j])/r**3
                    - 1j*(3*n[j]*n[2]-p[j])/r**2 + pp[j]/r) for j in range(3))
    q, qq = cross(pd, n), cross(pdd, n)
    b = tuple(phase*(q[j]/r**2+qq[j]/r) for j in range(3))
    return e, b


def potentials(pos):
    r = norm(pos)
    phase = cmath.exp(1j*r)/(4*math.pi)
    return phase*(pos[2]/r)*(1/r**2-1j/r), (0j, 0j, -1j*phase/r)


def derivative(fun, p, axis, h):
    lo, hi = list(p), list(p)
    lo[axis] -= h
    hi[axis] += h
    return (fun(hi)-fun(lo))/(2*h)


def curl(fun, p, h):
    return tuple(derivative(lambda x: fun(x)[(j+2)%3], p, (j+1)%3, h)
                 - derivative(lambda x: fun(x)[(j+1)%3], p, (j+2)%3, h) for j in range(3))


def residual(h):
    p = (1.2, .7, 1.5)
    e, b = fields(p)
    _, avec = potentials(p)
    e_from_v = tuple(-derivative(lambda q: potentials(q)[0], p, j, h)+1j*avec[j]
                     for j in range(3))
    b_from_a = curl(lambda q: potentials(q)[1], p, h)
    ce, cb = curl(lambda q: fields(q)[0], p, h), curl(lambda q: fields(q)[1], p, h)
    de = sum(derivative(lambda q: fields(q)[0][j], p, j, h) for j in range(3))
    db = sum(derivative(lambda q: fields(q)[1][j], p, j, h) for j in range(3))
    return dict(potential_e=norm([e_from_v[j]-e[j] for j in range(3)])/norm(e),
                potential_b=norm([b_from_a[j]-b[j] for j in range(3)])/norm(b),
                faraday=norm([ce[j]-1j*b[j] for j in range(3)])/norm(b),
                ampere=norm([cb[j]+1j*e[j] for j in range(3)])/norm(e),
                div_e=abs(de)/norm(e), div_b=abs(db)/norm(b))


def svg_start(title, desc, w=940, h=430):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<title>{title}</title><desc>{desc}</desc>',
            '<rect width="100%" height="100%" fill="#fcfcfa"/>',
            '<g font-family="sans-serif" font-size="15" fill="#152b3b">',
            f'<text x="35" y="30" font-size="21">{title}</text>']


def line(x1, y1, x2, y2, color='#687987', extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" {extra}/>'


def poly(points, color):
    return '<polyline fill="none" stroke="'+color+'" stroke-width="3" points="' + ' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+'"/>'


def text(x,y,s,size=15):
    return f'<text x="{x}" y="{y}" font-size="{size}">{s}</text>'


def save_svg(path, parts):
    path.write_text('\n'.join(parts+['</g></svg>'])+'\n', encoding='utf-8')


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    assets = out/'assets'
    assets.mkdir(exist_ok=True)
    omega = 2*math.pi*FREQ
    k = omega/C
    x, y = k*A, k*R
    ff = form_factor(x)
    power = P0**2*omega**4/(12*math.pi*EPS*C**3)
    umax = P0**2*omega**4/(32*math.pi**2*EPS*C**3)
    integral = 2*math.pi*simpson(lambda t: math.sin(t)**3,0,math.pi)
    assert abs(integral-8*math.pi/3) < 2e-9
    for z in [0, x, .1, 1.2, 4.5, 7.0]:
        quad = 3*simpson(lambda u: u*u*sinc(z*u),0,1)
        assert abs(quad-form_factor(z)) < 2e-10
    # Independent double quadrature of the original 3D kernel: a=1, r=3, k=1.2.
    # Rotational symmetry performs only the azimuth integral analytically.
    krad, robs = 1.2, 3.0
    def shell(s):
        def angular(mu):
            distance = math.sqrt(robs**2+s*s-2*robs*s*mu)
            return cmath.exp(1j*krad*distance)/distance
        return 1.5*s*s*simpson(angular,-1,1,240)
    direct = simpson(shell,0,1,240)
    closed = form_factor(krad)*cmath.exp(1j*krad*robs)/robs
    kernel_error = abs(direct-closed)/abs(closed)
    assert kernel_error < 2e-9
    coarse, fine = residual(2e-4), residual(1e-4)
    assert max(fine.values()) < 2e-8
    # Analytic exterior average radial flux at finite kr: Re[(1+i/x-1/x^2)(1-i/x)]=1.
    flux_errors = []
    for z in [.1,1,10,y]:
        flux_errors.append(abs(((1+1j/z-1/z**2)*(1-1j/z)).real-1))
    assert max(flux_errors) < 1e-10
    report = dict(inputs=dict(c_m_per_s=C,epsilon_F_per_m=EPS,p_peak_C_m=P0,
                 frequency_Hz=FREQ,radius_m=A,observation_m=R,pulse_duration_s=T),
                 ka=x,kr=y,form_factor=ff,point_power_W=power,point_Umax_W_per_sr=umax,
                 finite_sphere_power_W=ff*ff*power,finite_sphere_relative_power_change=ff*ff-1,
                 equatorial_relative_complex_field_error=math.sqrt(y**-2+y**-4),
                 directionality=4*math.pi/integral,
                 window_30m_ns=[(R-A)/C*1e9,(T+(R+A)/C)*1e9],
                 window_60m_ns=[(60-A)/C*1e9,(T+(60+A)/C)*1e9],
                 original_kernel_quadrature_relative_error=kernel_error,
                 residual_step_2e_4=coarse,residual_step_1e_4=fine,
                 finite_radius_average_flux_max_error=max(flux_errors),
                 doubled_frequency_fixed_p_ratio=16*(form_factor(2*x)/ff)**2,
                 doubled_frequency_fixed_current_moment_ratio=4*(form_factor(2*x)/ff)**2)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    near = [(10**(-1+3*j/180),) for j in range(181)]
    near = [(z[0],math.sqrt(z[0]**-2+z[0]**-4)) for z in near]
    with (out/'near-far.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['kr','relative_complex_Etheta_error']); writer.writerows(near)
    rows = []
    for j in range(181):
        th = j*math.pi/180
        cum = .5-.75*math.cos(th)+.25*math.cos(th)**3
        rows.append((j, math.sin(th)**2,cum))
    with (out/'angular-power.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['theta_degree','normalized_power','cumulative_power_fraction']); writer.writerows(rows)
    s=svg_start('Far-field error in the complex equatorial electric field', '横轴 kr 与纵轴复场相对差均为对数尺度。曲线由 near-far.csv 生成；标出100 MHz、30 m。')
    def px(z): return 100+math.log10(z/.1)/3*740
    def py(v): return 345-(math.log10(v)+2)/4.1*270
    s += [line(100,70,100,345),line(100,345,850,345)]
    for z in [.1,1,10,100]:
        s += [line(px(z),70,px(z),345,'#dbe1e5'),text(px(z)-8,370,f'{z:g}')]
    for v in [.01,.1,1,10,100]:
        s += [line(100,py(v),850,py(v),'#dbe1e5'),text(40,py(v)+5,f'{v:g}')]
    s += [poly([(px(z),py(v)) for z,v in near],'#006b8f'),text(680,402,'kr (dimensionless)'),text(105,57,'|Eθ − Eθ,rad| / |Eθ,rad|')]
    ey=math.sqrt(y**-2+y**-4)
    s += [f'<circle cx="{px(y):.3f}" cy="{py(ey):.3f}" r="5" fill="#a54b00"/>',text(510,235,f'30 m: kr={y:.3f}, error={ey*100:.4f}%')]
    save_svg(assets/'near-far-error.svg',s)
    s=svg_start('Dipole angular power and cumulative solid-angle integral', '左：归一化功率 sin²θ；右：含sinθ面积权重的累计功率份额。数据来自 angular-power.csv。')
    for idx,(label,col) in enumerate([('Normalized power U/Umax',1),('Power fraction from north pole to θ',2)]):
        left=75+idx*465
        s += [text(left,68,label),line(left,90,left,340),line(left,340,left+365,340)]
        for deg in [0,90,180]: s += [text(left+deg/180*355-8,367,str(deg))]
        for v in [0,.5,1]: s += [text(left-34,340-v*230+5,str(v)),line(left,340-v*230,left+355,340-v*230,'#dbe1e5')]
        s += [poly([(left+d/180*355,340-row[col]*230) for row in rows for d in [row[0]]],'#006b8f' if idx==0 else '#a54b00'),text(left+215,401,'θ (degree)')]
    save_svg(assets/'angular-power.svg',s)
    first,last=report['window_30m_ns']
    s=svg_start('Finite pulse: which source events can reach the observer?', '空间切线的源区宽度放大。源活跃0至20 ns，观察点30 m；允许到达窗口100.065893至120.072564 ns。示意线的角度不用于测光速。')
    s += [line(110,355,850,355),line(110,355,110,65),text(65,62,'t (ns)'),text(777,402,'x (m)'),text(192,382,'center 0'),text(730,382,'observer 30')]
    yy=lambda t:355-t*2.2
    s += ['<rect x="190" y="311" width="50" height="44" fill="#d9edf3" stroke="#006b8f"/>',text(350,330,'Source active only during 0–20 ns'),text(125,240,'−a to +a (width enlarged)')]
    for ts in [0,20]:
        for xx,travel in [(190,(R+A)/C*1e9),(240,(R-A)/C*1e9)]: s.append(line(xx,yy(ts),750,yy(ts+travel),'#006b8f'))
    s += [line(750,yy(first),750,yy(last),'#a54b00','stroke-width="6"'),text(375,71,f'Arrival window: [{first:.6f}, {last:.6f}] ns'),text(385,102,'Edge lines: nearest / farthest source events'),text(325,405,'Inside the window, cancellation can still yield zero.')]
    for t in [0,20,100,120]: s += [text(65,yy(t)+5,str(t)),line(105,yy(t),115,yy(t))]
    save_svg(assets/'causal-window.svg',s)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    generate(parser.parse_args().out)
