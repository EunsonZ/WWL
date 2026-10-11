---
type: reference
domain: 物理
stage: 4
aliases: []
sources:
  - https://www.feynmanlectures.caltech.edu/I_31.html
  - https://www.feynmanlectures.caltech.edu/I_32.html
  - https://farside.ph.utexas.edu/teaching/jk1/lectures/node68.html
  - https://math.mit.edu/~stevenj/papers/Welters14.pdf
prerequisites:
  - "[[物理/20-电磁学/12-Lorentz介质色散储能与群速]]"
---

# Lorentz介质源码与来源

`lorentz_medium.py` 是计算真源，本页逐字镜像同一全文。输入、CSV与SVG都从该源码生成；复建命令和资源上界见 [[物理/80-实践/44-Lorentz介质色散/README|实践入口]]。源码只求指定合成局域模型，不拟合真实介质、不做空间前沿测试。

## 来源转换与适用范围

- [Feynman I31 §31.2–31.4](https://www.feynmanlectures.caltech.edu/I_31.html) 与 [I32 式(32.15)](https://www.feynmanlectures.caltech.edu/I_32.html)：实际读取了正时间受驱分母与衰减符号；I31 的折射率近似限低密度，本实践不用其近似折射率替代指定本构的平方根。
- [Fitzpatrick，Form of Dielectric Constant，式(779)–(784)](https://farside.ph.utexas.edu/teaching/jk1/lectures/node68.html)：对照宏观介电常数与振子响应，转换负时间号；本卡没有额外声明真实原子密度或局域场修正。
- [Welters–Avniel–Johnson，PRA 90, 023847，§II A 式(1)–(4)、§II C](https://math.mit.edu/~stevenj/papers/Welters14.pdf#page=2)：实际读透明窗中的能流与Brillouin储能条件。原文为Gaussian单位和负时间相量；本页采用SI正时间峰值，由振子动势能直接推出1/4系数，再由独立k频率导数核速度等式。论文的更广泛定理没有变成本卡已经计算的一般介质范围。

零初值Green核、实时能量恒等式、单共振本构的正储能权重和透明体波速度恒等式均在主正文给出本模型推导。脉冲是外加局域E的因果响应；RK4全状态积分和内部网格加密是数值实现。不同路线核算另使用有限五频解析响应、Green卷积样点与独立功热积分，数值签收不代表真人已理解或真实材料已经测量。

## 完整代码镜像

<!-- code-sync: 物理/80-实践/44-Lorentz介质色散/lorentz_medium.py -->
```python
#!/usr/bin/env python3
"""Synthetic local Lorentz medium; +i omega t, peak phasors, SI.
Python 3.10+, standard library only. This is not a propagation/front solver.
"""
import argparse
import cmath
import csv
import html
import json
import math
from pathlib import Path
import time

EPS0 = 8.8541878128e-12
C = 299792458.0
MU0 = 1.0 / (EPS0 * C * C)
KEYS = {'f0_hz', 'strength', 'Epeak_V_m', 'main_ratio', 'area_m2',
        'length_m', 'loss_gamma_ratio', 'sweep_intervals',
        'sweep_points_per_band', 'loss_interval', 'pulse_duration_tau',
        'pulse_final_tau', 'pulse_drive_ratio', 'pulse_steps'}


def pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError('duplicate JSON key')
        out[key] = value
    return out


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(name + ': finite number required')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(name + ': outside finite allowed range')
    return float(value)


def integer(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(name + ': bounded integer required')
    return value


def interval(value, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(name + ': [low, high] required')
    lo = number(value[0], .05, 4., name)
    hi = number(value[1], .05, 4., name)
    if lo >= hi:
        raise ValueError(name + ': increasing endpoints required')
    return [lo, hi]


def validate(raw):
    if not isinstance(raw, dict) or set(raw) != KEYS:
        raise ValueError('input keys must exactly match documented card')
    p = dict(raw)
    for key, lo, hi in [('f0_hz', 1e3, 1e15), ('strength', .01, 2.),
                        ('Epeak_V_m', .001, 1e6), ('main_ratio', .05, 4.),
                        ('area_m2', 1e-12, 1.), ('length_m', 1e-9, 1.),
                        ('loss_gamma_ratio', .001, .4),
                        ('pulse_duration_tau', 5., 100.),
                        ('pulse_final_tau', 10., 200.),
                        ('pulse_drive_ratio', .05, 4.)]:
        p[key] = number(raw[key], lo, hi, key)
    p['pulse_steps'] = integer(raw['pulse_steps'], 1000, 40000, 'pulse_steps')
    p['sweep_points_per_band'] = integer(raw['sweep_points_per_band'], 11, 401,
                                         'sweep_points_per_band')
    if not isinstance(raw['sweep_intervals'], list) or len(raw['sweep_intervals']) != 2:
        raise ValueError('sweep_intervals: two intervals required')
    p['sweep_intervals'] = [interval(v, 'sweep_intervals') for v in raw['sweep_intervals']]
    if p['sweep_intervals'][0][1] >= p['sweep_intervals'][1][0]:
        raise ValueError('sweep intervals must be disjoint and ordered')
    p['loss_interval'] = interval(raw['loss_interval'], 'loss_interval')
    if p['pulse_final_tau'] < p['pulse_duration_tau'] + 5:
        raise ValueError('pulse_final_tau must exceed duration by at least 5')
    if p['pulse_final_tau'] / p['pulse_steps'] > .02:
        raise ValueError('pulse time step exceeds .02')
    # Entire transparent intervals, not only sample nodes, must be outside gap.
    edge = math.sqrt(1 + p['strength'])
    for lo, hi in p['sweep_intervals']:
        if not (hi <= .98 or lo >= edge + .02):
            raise ValueError('transparent interval crosses resonance/gap or margin')
    x = p['main_ratio']
    if not (x <= .98 or x >= edge + .02):
        raise ValueError('main frequency outside transparent propagating band')
    return p


def transparent(p, x, band=0):
    s, e = p['strength'], p['Epeak_V_m']
    er = 1 + s / (1 - x*x)
    n = math.sqrt(er)
    nx = s*x / (n*(1-x*x)**2)
    ng = n + x*nx
    weight = 1 + s*(1+x*x)/(1-x*x)**2
    ue = EPS0*e*e/4
    uh = ue*er
    uk = ue*s*x*x/(1-x*x)**2
    uv = ue*s/(1-x*x)**2
    total = ue + uh + uk + uv
    flux = EPS0*C*n*e*e/2
    brillouin = ue*weight + uh
    r = (1-n)/(1+n)
    t = 2/(1+n)
    dx = min(1e-5, abs(x-1)*1e-4, abs(x-math.sqrt(1+s))*1e-4)
    def kval(z):
        return z*math.sqrt(1+s/(1-z*z))
    fd = C / ((kval(x+dx)-kval(x-dx))/(2*dx))
    return dict(band=band, ratio=x, frequency_hz=x*p['f0_hz'], epsr=er, n=n,
                group_index=ng, phase_speed_m_s=C/n, group_speed_m_s=C/ng,
                group_fd_m_s=fd, energy_speed_m_s=flux/total,
                electric_J_m3=ue, magnetic_J_m3=uh, kinetic_J_m3=uk,
                potential_J_m3=uv, stored_J_m3=total, brillouin_J_m3=brillouin,
                flux_W_m2=flux, control_power_W=flux*p['area_m2'],
                control_energy_J=total*p['area_m2']*p['length_m'], R=r*r,T=n*t*t)


def lossy(p, x):
    g, s, e = p['loss_gamma_ratio'], p['strength'], p['Epeak_V_m']
    chi = s / complex(1-x*x, g*x)
    er = 1 + chi
    n = cmath.sqrt(er)  # principal root: positive real, negative imaginary
    w0 = 2*math.pi*p['f0_hz']
    p2 = (EPS0*e*abs(chi))**2
    q1 = -w0*x*EPS0*er.imag*e*e/2
    q2 = g*w0*(w0*x)**2*p2/(2*EPS0*s*w0*w0)
    return dict(ratio=x, eps_real=er.real, eps_imag=er.imag,
                n_real=n.real, n_imag=n.imag,
                amplitude_attenuation_m1=-w0*x*n.imag/C,
                heat_from_eps_W_m3=q1, heat_from_osc_W_m3=q2)


def drive(tau, p):
    duration = p['pulse_duration_tau']
    if tau <= 0 or tau >= duration:
        return 0.
    return math.sin(math.pi*tau/duration)**4 * math.cos(
        p['pulse_drive_ratio']*(tau-duration/2))


def pulse(p, g, steps):
    dt = p['pulse_final_tau']/steps
    s = p['strength']
    state = [0., 0., 0., 0.]  # p, p', work, heat; all dimensionless
    records = []
    worst = 0.
    def rhs(t, y):
        a, v, _, _ = y
        e = drive(t, p)
        return [v, s*e-g*v-a, e*v, g*v*v/s]
    for j in range(steps+1):
        tau = j*dt
        a, v, work, heat = state
        kinetic, potential = v*v/(2*s), a*a/(2*s)
        stored = kinetic + potential
        residual = work-stored-heat
        worst = max(worst, abs(residual))
        records.append(dict(gamma_ratio=g, tau=tau,
                            time_s=tau/(2*math.pi*p['f0_hz']), drive=drive(tau,p),
                            polarization_scaled=a, velocity_scaled=v,
                            kinetic_scaled=kinetic, potential_scaled=potential,
                            stored_scaled=stored, work_scaled=work, heat_scaled=heat,
                            balance_scaled=residual))
        if j == steps:
            break
        k1 = rhs(tau, state)
        k2 = rhs(tau+dt/2, [a+dt*b/2 for a,b in zip(state,k1)])
        k3 = rhs(tau+dt/2, [a+dt*b/2 for a,b in zip(state,k2)])
        k4 = rhs(tau+dt, [a+dt*b for a,b in zip(state,k3)])
        state = [a+dt*(b+2*c+2*d+e)/6 for a,b,c,d,e in zip(state,k1,k2,k3,k4)]
    return records, dict(gamma_ratio=g, dtau=dt, final=records[-1],
                        max_absolute_balance_scaled=worst)


def write_csv(path, records):
    with path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


COLORS = ['#1764a0', '#bd4931', '#217447', '#7b51a1', '#4e545a']


def svg_start(title, description, width=1080, height=760):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<title>'+html.escape(title)+'</title><desc>'+html.escape(description)+'</desc>',
            '<rect width="100%" height="100%" fill="#fff"/>',
            '<g font-family="Arial, sans-serif" font-size="15" fill="#222">',
            f'<text x="40" y="35" font-size="22">{html.escape(title)}</text>']


def panel(out, box, xs, series, labels, title, xlabel, ylabel, ylimits=None):
    left, top, width, height = box
    xmin,xmax = min(xs),max(xs)
    ys = [v for seq in series for v in seq]
    ymin,ymax = ylimits if ylimits else (min(0., min(ys)), max(ys)*1.08)
    if ymax <= ymin:
        ymax = ymin+1.
    def X(x): return left+width*(x-xmin)/(xmax-xmin)
    def Y(y): return top+height-height*(y-ymin)/(ymax-ymin)
    out.append(f'<text x="{left}" y="{top-20}" font-size="17">{html.escape(title)}</text>')
    for j in range(5):
        y = ymin+(ymax-ymin)*j/4
        yp = Y(y)
        out.append(f'<path d="M {left} {yp:.3f} H {left+width}" stroke="#ddd" fill="none"/>')
        out.append(f'<text x="{left-8}" y="{yp+5:.3f}" text-anchor="end">{y:.3g}</text>')
        x=xmin+(xmax-xmin)*j/4
        out.append(f'<text x="{X(x):.3f}" y="{top+height+22}" text-anchor="middle">{x:.3g}</text>')
    out.append(f'<path d="M {left} {top} V {top+height} H {left+width}" stroke="#444" fill="none"/>')
    for index, (seq,label) in enumerate(zip(series,labels)):
        points=' '.join(f'{X(x):.3f},{Y(y):.3f}' for x,y in zip(xs,seq))
        color=COLORS[index%len(COLORS)]
        dash=' stroke-dasharray="6 4"' if index == 1 else ''
        out.append(f'<polyline points="{points}" stroke="{color}" stroke-width="2"{dash} fill="none"/>')
        ly=top+height+67+index*22
        out.append(f'<path d="M {left} {ly-5} h 25" stroke="{color}" stroke-width="2"{dash}/>')
        out.append(f'<text x="{left+32}" y="{ly}">{html.escape(label)}</text>')
    out.append(f'<text x="{left+width/2}" y="{top+height+45}" text-anchor="middle">{html.escape(xlabel)}</text>')
    out.append(f'<text x="{left}" y="{top-42}">{html.escape(ylabel)}</text>')


def plots(outdir, p, sweep, losses, pulses):
    title=f'Lorentz bulk: s={p["strength"]:g}, f0={p["f0_hz"]/1e9:g} GHz, gamma=0'
    out=svg_start(title,'Separate transparent propagating bands; no curve connects the resonance gap.',height=870)
    for b in range(2):
        rows=[r for r in sweep if r['band']==b]
        x=[r['ratio'] for r in rows]
        panel(out,(85+515*b,110,385,205),x,
              [[r['n'] for r in rows]],['n'],f'Transparent band {b+1}','omega / omega0','refractive index n')
        panel(out,(85+515*b,555,385,170),x,
              [[r['group_speed_m_s']/C for r in rows],
               [r['energy_speed_m_s']/C for r in rows],
               [r['phase_speed_m_s']/C for r in rows]],
              ['group / c','energy / c (overlaps group)','phase / c'],
              'Same branch, material parameters fixed','omega / omega0','speed / c')
    out.extend(['</g></svg>'])
    (outdir/'dispersion.svg').write_text('\n'.join(out)+'\n',encoding='utf-8')
    out=svg_start('Where is the energy stored?','Peak E fixed in each sweep. Field and oscillator energies add once. Halfspace R/T is interface flux.',height=920)
    for b in range(2):
        rows=[r for r in sweep if r['band']==b]
        x=[r['ratio'] for r in rows]
        panel(out,(85+515*b,110,385,205),x,
              [[r[key]/(EPS0*p['Epeak_V_m']**2) for r in rows]
               for key in ['electric_J_m3','magnetic_J_m3','kinetic_J_m3','potential_J_m3']],
              ['vacuum electric','magnetic','oscillator kinetic','oscillator potential'],
              f'Band {b+1}: Epeak={p["Epeak_V_m"]:g} V/m',
              'omega / omega0','energy / (eps0 Epeak^2)')
        panel(out,(85+515*b,600,385,170),x,[[r['R'] for r in rows],[r['T'] for r in rows]],
              ['R: reflected flux','T: transmitted flux'],
              'Vacuum to transparent halfspace','omega / omega0','flux ratio',(0,1.05))
    out.extend(['</g></svg>'])
    (outdir/'storage-interface.svg').write_text('\n'.join(out)+'\n',encoding='utf-8')
    out=svg_start('Causal local pulse: prescribed E, zero initial state',
                  'Local oscillator only, not a Maxwell propagation or front simulation. Work=stored+heat. Plotted records from RK4.',height=925)
    for b,(g,rows) in enumerate(pulses):
        # Decimation selects existing samples; it does not create new values.
        stride=max(1,(len(rows)-1)//1000)
        take=rows[::stride]
        if take[-1] is not rows[-1]: take.append(rows[-1])
        x=[r['tau'] for r in take]
        panel(out,(85+515*b,110,385,205),x,
              [[r['drive'] for r in take],[r['polarization_scaled'] for r in take]],
              ['E / Epeak','P / (eps0 Epeak)'],f'gamma / omega0 = {g:g}',
              'tau = omega0 t','dimensionless response',
              (min(-1.,min(r['polarization_scaled'] for r in take))*1.08,
               max(1.,max(r['polarization_scaled'] for r in take))*1.08))
        panel(out,(85+515*b,595,385,190),x,
              [[r[key] for r in take] for key in ['work_scaled','stored_scaled','heat_scaled']],
              ['work from external field','oscillator stored','dissipated heat'],
              'Energy ledger; envelope ends at tau='+str(p['pulse_duration_tau']),
              'tau = omega0 t','energy / (eps0 Epeak^2)')
    out.extend(['</g></svg>'])
    (outdir/'pulse-budget.svg').write_text('\n'.join(out)+'\n',encoding='utf-8')


def run(p, outdir):
    started=time.monotonic()
    sweep=[]
    count=p['sweep_points_per_band']
    for b,(lo,hi) in enumerate(p['sweep_intervals']):
        sweep.extend(transparent(p,lo+(hi-lo)*j/(count-1),b) for j in range(count))
    lo,hi=p['loss_interval']
    losses=[lossy(p,lo+(hi-lo)*j/400) for j in range(401)]
    pulses=[]
    summaries=[]
    for g in [0.,p['loss_gamma_ratio']]:
        rows,base=pulse(p,g,p['pulse_steps'])
        fine,fsummary=pulse(p,g,2*p['pulse_steps'])
        base['refined_max_absolute_balance_scaled']=fsummary['max_absolute_balance_scaled']
        base['final_refinement_absolute_state_difference']=max(
            abs(rows[-1][key]-fine[-1][key]) for key in
            ['polarization_scaled','velocity_scaled','work_scaled','heat_scaled'])
        pulses.append((g,rows))
        summaries.append(base)
    main=transparent(p,p['main_ratio'])
    result=dict(model='local scalar Lorentz; +i omega t; peak phasors; SI',
                scope='transparent prepared plane wave + externally driven local zero-state pulse',
                input=p, constants=dict(eps0_F_m=EPS0,c_m_s=C,mu0_H_m=MU0),
                main=main, pulse=summaries,
                diagnostics=dict(max_R_T_residual=max(abs(r['R']+r['T']-1) for r in sweep),
                                 max_Brillouin_relative_difference=max(abs(r['stored_J_m3']/r['brillouin_J_m3']-1) for r in sweep),
                                 max_group_energy_relative_difference=max(abs(r['group_speed_m_s']/r['energy_speed_m_s']-1) for r in sweep),
                                 max_group_fd_relative_difference=max(abs(r['group_fd_m_s']/r['group_speed_m_s']-1) for r in sweep),
                                 max_loss_identity_relative_difference=max(abs(r['heat_from_eps_W_m3']/r['heat_from_osc_W_m3']-1) for r in losses)),
                elapsed_s=time.monotonic()-started)
    # No output directory is created until all validation/calculation succeeded.
    outdir.mkdir(parents=False,exist_ok=False)
    write_csv(outdir/'transparent.csv',sweep)
    write_csv(outdir/'lossy.csv',losses)
    write_csv(outdir/'pulse.csv',[r for _,rows in pulses for r in rows])
    plots(outdir,p,sweep,losses,pulses)
    (outdir/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError('output must be a new directory; old output preserved')
        with args.input.open(encoding='utf-8') as f:
            raw=json.load(f,object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        p=validate(raw)
        result=run(p,args.out)
    except (ValueError,OSError,OverflowError,ZeroDivisionError) as error:
        parser.exit(2,'refused: '+str(error)+'\n')
    print(json.dumps(dict(output=str(args.out),main=result['main'],
                          diagnostics=result['diagnostics']),indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
```
