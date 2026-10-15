---
title: 三维短程散射规范源码镜像
stage: 0
aliases: []
sources: []
prerequisites:
  - "[[物理/80-实践/45-三维短程散射/README]]"
---
# 三维短程散射规范源码镜像

以同目录 `scattering.py` 为真源；本页只供阅读。Python 3.10+ 标准库，不依赖 NumPy/SciPy。

<!-- code-sync: 物理/80-实践/45-三维短程散射/scattering.py -->
```python
#!/usr/bin/env python3
"""Elastic distinguishable-particle scattering by a real attractive spherical well.
Python 3.10+, standard library only. Units are SI; x=ka, eta=2*mu*W*a*a/hbar**2.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import re
import sys

HBAR = 1.054571817e-34  # teaching precision, J s
COLORS = ['#0072b2', '#d55e00', '#009e73', '#cc79a7', '#805900', '#333333', '#56b4e9', '#777777']


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('numeric input outside declared domain')
    return float(value)


def keys(obj, expected):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError('unexpected or missing keys')


def validate(card):
    keys(card, ['units', 'radius_m', 'reduced_mass_kg', 'l_max', 'angle_points', 'scan_x', 'depth_scan_eta', 'depth_scan_x', 'cases'])
    if card['units'] != {'length': 'm', 'mass': 'kg', 'energy': 'J', 'angle': 'rad'}:
        raise ValueError('units must match SI declaration')
    number(card['radius_m'], 1e-12, 1e-6)
    number(card['reduced_mass_kg'], 1e-32, 1e-26)
    for field, low, high in [('l_max', 10, 24), ('angle_points', 31, 361)]:
        if type(card[field]) is not int or not low <= card[field] <= high:
            raise ValueError('integer grid outside declared domain')
    for field, low, high, count in [('scan_x', .03, 4., 161), ('depth_scan_eta', 0., 4., 241)]:
        values = card[field]
        if not isinstance(values, list) or not 2 <= len(values) <= count:
            raise ValueError('scan size outside declared domain')
        checked = [number(v, low, high) for v in values]
        if any(a >= b for a, b in zip(checked, checked[1:])):
            raise ValueError('scan must be strictly increasing')
    number(card['depth_scan_x'], .03, 4.)
    cases = card['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise ValueError('case count outside declared domain')
    names = set()
    for case in cases:
        keys(case, ['name', 'eta', 'x'])
        name = case['name']
        if not isinstance(name, str) or re.fullmatch(r'[A-Za-z0-9_-]{1,24}', name) is None or name in names:
            raise ValueError('case names must be unique ASCII identifiers')
        names.add(name)
        number(case['eta'], 0., 4.)
        number(case['x'], .03, 4.)
    return card


def spherical(z, maximum):
    """Stable j_l power series for 0<z<=sqrt(20); n_l upward recurrence."""
    js = []
    prefactor = 1.
    for ell in range(maximum + 2):
        if ell:
            prefactor *= z / (2 * ell + 1)
        term = 1.
        terms = [term]
        for m in range(1, 150):
            term *= -z*z / (2*m*(2*ell+2*m+1))
            terms.append(term)
            if abs(term) < 1e-18:
                break
        js.append(prefactor * math.fsum(terms))
    ns = [-math.cos(z)/z, -math.cos(z)/(z*z)-math.sin(z)/z]
    for ell in range(1, maximum + 1):
        ns.append((2*ell+1)*ns[-1]/z-ns[-2])
    jd = [ell*js[ell]/z-js[ell+1] for ell in range(maximum + 1)]
    nd = [ell*ns[ell]/z-ns[ell+1] for ell in range(maximum + 1)]
    return js, ns, jd, nd


def channels(x, eta, maximum):
    if eta == 0:
        return [1+0j] * (maximum+1)
    q = math.sqrt(x*x+eta)
    j, n, jp, np = spherical(x, maximum)
    ji, _, jip, _ = spherical(q, maximum)
    result = []
    for ell in range(maximum+1):
        numerator = x*jp[ell]*ji[ell]-q*jip[ell]*j[ell]
        denominator = x*np[ell]*ji[ell]-q*jip[ell]*n[ell]
        scale = max(abs(numerator), abs(denominator))
        if not scale:
            raise ValueError('degenerate numerical matching')
        numerator /= scale
        denominator /= scale
        result.append(complex(denominator, numerator)/complex(denominator, -numerator))
    return result


def legendre(c, maximum):
    values = [1., c]
    for ell in range(1, maximum):
        values.append(((2*ell+1)*c*values[-1]-ell*values[-2])/(ell+1))
    return values[:maximum+1]


def amplitude(c, x, s):
    p = legendre(c, len(s)-1)
    return sum((2*ell+1)*(value-1)*p[ell] for ell, value in enumerate(s))/(2j*x)


def born(c, x, eta):
    y = x*math.sqrt(max(0., 2*(1-c)))
    if y < .1:
        # (sin y-y cos y)/y^3, including forward limit
        return eta*(1/3-y*y/30+y**4/840-y**6/45360+y**8/3991680)
    return eta*(math.sin(y)-y*math.cos(y))/(y**3)


def gauss(n):
    nodes = []
    for i in range(1, n+1):
        z = math.cos(math.pi*(i-.25)/(n+.5))
        for _ in range(30):
            p = legendre(z, n)
            dp = n*(z*p[n]-p[n-1])/(z*z-1)
            step = p[n]/dp
            z -= step
            if abs(step) < 1e-15:
                break
        p = legendre(z, n)
        dp = n*(z*p[n]-p[n-1])/(z*z-1)
        nodes.append((z, 2/((1-z*z)*dp*dp)))
    return nodes


QUAD = gauss(64)


def bound(eta):
    """Stable shallow s root in kappa*a; threshold equality is binary64 equality."""
    t0 = math.pi/2
    excess = eta-t0*t0
    if excess <= 0:
        return None
    lo, hi = 0., math.sqrt(excess)
    for _ in range(90):
        w = (lo+hi)/2
        z = math.sqrt(eta-w*w)
        dz = (excess-w*w)/(z+t0)
        # z*cot(z)+w = w-z*tan(z-pi/2)
        if w-z*math.tan(dz) < 0:
            lo = w
        else:
            hi = w
    w = (lo+hi)/2
    return {'z': math.sqrt(eta-w*w), 'kappa_a': w, 'energy_over_Ea': -w*w}


def observables(x, eta, maximum):
    all_s = channels(x, eta, maximum+4)
    s = all_s[:maximum+1]
    sigma_l = [math.pi*(2*ell+1)*abs(value-1)**2/(x*x) for ell, value in enumerate(s)]
    sigma = math.fsum(sigma_l)
    sigma_extended = math.fsum(math.pi*(2*ell+1)*abs(value-1)**2/(x*x) for ell, value in enumerate(all_s))
    integrated = 2*math.pi*math.fsum(w*abs(amplitude(c,x,s))**2 for c,w in QUAD)
    born_total = 2*math.pi*math.fsum(w*born(c,x,eta)**2 for c,w in QUAD)
    forward = amplitude(1.,x,s)
    root = math.sqrt(eta)
    # threshold pole has no finite zero-energy scattering length
    excess = eta-(math.pi/2)**2
    at_pole = excess == 0
    if at_pole:
        scattering_length = None
    elif eta == 0:
        scattering_length = 0.
    elif abs(root-math.pi/2) < .05:
        dz = excess/(root+math.pi/2)
        scattering_length = 1+1/(root*math.tan(dz))
    else:
        scattering_length = 1-math.tan(root)/root
    return {'x':x, 'eta':eta, 'sigma_over_a2':sigma, 'sigma_s0_over_a2':sigma_l[0],
            'sigma_born_over_a2':born_total, 'sigma_angular_over_a2':integrated,
            'sigma_optical_over_a2':4*math.pi*forward.imag/x,
            'added_four_channels_over_a2':sigma_extended-sigma,
            'unitarity_residual':max(abs(abs(v)-1) for v in s),
            'scattering_length_over_a':scattering_length, 's_wave_bound':bound(eta),
            'forward_f_over_a':[forward.real,forward.imag],
            'channels':[{'ell':ell, 'S_re':v.real, 'S_im':v.imag,
                         'delta_mod_pi_rad':math.atan2(v.imag,v.real)/2,
                         'sigma_l_over_a2':sigma_l[ell]} for ell,v in enumerate(s)]}


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(path, title, subtitle, panels):
    width = 1120
    panel_heights = [max(330, 110+26*len(panel[2])) for panel in panels]
    height = 130+sum(panel_heights)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           f'<title>{html.escape(title)}</title><desc>{html.escape(subtitle)}</desc>',
           '<rect width="100%" height="100%" fill="white"/>',
           '<g font-family="Arial,sans-serif" fill="#222">',
           f'<text x="65" y="29" font-size="20">{html.escape(title)}</text>',
           f'<text x="65" y="53" font-size="13">{html.escape(subtitle)}</text>']
    for index,panel in enumerate(panels):
        xlabel,ylabel,curves = panel[:3]
        left, top, w, h = 95, 88+sum(panel_heights[:index]), 585, panel_heights[index]-100
        if len(panel) == 4:
            out.append(f'<text x="95" y="{top-10}" font-size="13">{html.escape(panel[3])}</text>')
        xs = [x for _,xy,_,_ in curves for x,y in xy]
        ys = [y for _,xy,_,_ in curves for x,y in xy]
        xmin,xmax=min(xs),max(xs)
        ymin,ymax=min(ys),max(ys)
        if ymax == ymin:
            ymax = ymin+1
        padding=(ymax-ymin)*.05
        ymin-=padding; ymax+=padding
        out.append(f'<rect x="{left}" y="{top}" width="{w}" height="{h}" fill="#fafafa" stroke="#333"/>')
        for t in range(6):
            xx=left+w*t/5; yy=top+h-h*t/5
            out += [f'<text x="{xx:.4f}" y="{top+h+20}" text-anchor="middle" font-size="12">{xmin+(xmax-xmin)*t/5:.3g}</text>',
                    f'<text x="{left-10}" y="{yy+4:.4f}" text-anchor="end" font-size="12">{ymin+(ymax-ymin)*t/5:.3g}</text>']
        out += [f'<text x="{left+w/2}" y="{top+h+47}" text-anchor="middle" font-size="14">{html.escape(xlabel)}</text>',
                f'<text transform="translate(23 {top+h/2}) rotate(-90)" text-anchor="middle" font-size="14">{html.escape(ylabel)}</text>']
        for cidx,(label,xy,color,dash) in enumerate(curves):
            pts=' '.join(f'{left+w*(x-xmin)/(xmax-xmin):.6f},{top+h-h*(y-ymin)/(ymax-ymin):.6f}' for x,y in xy)
            dashattr=f' stroke-dasharray="{dash}"' if dash else ''
            out.append(f'<polyline data-series="{html.escape(label)}" points="{pts}" fill="none" stroke="{color}" stroke-width="2"{dashattr}/>')
            ly=top+16+26*cidx
            out.append(f'<line x1="710" y1="{ly-4}" x2="738" y2="{ly-4}" stroke="{color}" stroke-width="2"{dashattr}/><text x="747" y="{ly}" font-size="12">{html.escape(label)}</text>')
    out.append('</g></svg>\n')
    path.write_text('\n'.join(out), encoding='utf-8')


def generate(card, output):
    a, mu = card['radius_m'], card['reduced_mass_kg']
    ea = HBAR**2/(2*mu*a*a)
    maximum=card['l_max']
    angular=[]; waves=[]; energy=[]; depth=[]; summaries=[]
    for case in card['cases']:
        name, eta, x=case['name'],case['eta'],case['x']
        obs=observables(x,eta,maximum)
        obs.update({'name':name,'W_J':eta*ea,'E_J':x*x*ea,'k_m_inv':x/a,
                    'sigma_m2':a*a*obs['sigma_over_a2'],
                    'amplitude_A_m_minus_3_over_2':a**(-1.5),
                    'incident_current_m_minus_2_s_minus_1':HBAR*x/(mu*a**4)})
        summaries.append(obs)
        s=[complex(c['S_re'],c['S_im']) for c in obs['channels']]
        for c in obs['channels']:
            waves.append({'case':name,'eta':eta,'x':x,**c,'sigma_l_m2':a*a*c['sigma_l_over_a2']})
        for i in range(card['angle_points']):
            theta=math.pi*i/(card['angle_points']-1)
            f=amplitude(math.cos(theta),x,s)
            fb=born(math.cos(theta),x,eta)
            angular.append({'case':name,'theta_rad':theta,'cos_theta':math.cos(theta),'f_re_over_a':f.real,'f_im_over_a':f.imag,'f_born_over_a':fb,
                            'dsigma_over_a2':abs(f)**2,'dsigma_born_over_a2':fb*fb,'dsigma_s0_over_a2':obs['sigma_s0_over_a2']/(4*math.pi),
                            'dsigma_m2':a*a*abs(f)**2,'dsigma_born_m2':a*a*fb*fb})
        for xx in card['scan_x']:
            point=observables(xx,eta,maximum)
            energy.append({'case':name,'eta':eta,'x':xx,'E_J':xx*xx*ea,**{field:point[field] for field in ['sigma_over_a2','sigma_s0_over_a2','sigma_born_over_a2','added_four_channels_over_a2']}})
    for eta in card['depth_scan_eta']:
        obs=observables(card['depth_scan_x'],eta,maximum)
        b=obs['s_wave_bound']
        depth.append({'eta':eta,'x':card['depth_scan_x'],'sigma_over_a2':obs['sigma_over_a2'],'sigma_s0_over_a2':obs['sigma_s0_over_a2'],
                      'sigma_born_over_a2':obs['sigma_born_over_a2'],'scattering_length_over_a':obs['scattering_length_over_a'],
                      'bound_energy_over_Ea':None if b is None else b['energy_over_Ea']})
    output.mkdir(parents=True, exist_ok=False)
    for filename,rows in [('angular.csv',angular),('partial-waves.csv',waves),('energy.csv',energy),('depth.csv',depth)]:
        write_csv(output/filename,rows)
    result={'inputs':card,'hbar_J_s':HBAR,'Ea_J':ea,'normalization':'A=a^(-3/2), generalized beam state; no L2 norm claimed',
            'angular_quadrature_order':64,'threshold_representation':'eta == (binary64 pi/2)^2 has no resolved side; shallow bound uses stable kappa variable','tail_statement':'L to L+4 convergence indicator only; no rigorous infinite tail certificate','cases':summaries}
    (output/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    angular_panels=[]
    for case in card['cases']:
        rows=[r for r in angular if r['case']==case['name']]
        curves=[]
        for key,label,color,dash in [('dsigma_over_a2','partial waves',COLORS[0],''),('dsigma_born_over_a2','Born',COLORS[1],'7 4'),('dsigma_s0_over_a2','s wave only',COLORS[2],'2 4')]:
            curves.append((f'{case["name"]}: {label}',[(r['theta_rad'],r[key]) for r in rows],color,dash))
        angular_panels.append(('theta (rad)', 'd sigma / d Omega / a^2',curves, f'{case["name"]}; eta={case["eta"]:.8g}; ka={case["x"]:.8g}'))
    plot(output/'angular.svg','Same potential: angular cross sections', f'a={a:.5g} m; mu={mu:.5g} kg; l=0..{maximum}; finite elastic spherical well',angular_panels)
    curves=[]
    for idx,case in enumerate(card['cases']):
        rows=[r for r in energy if r['case']==case['name']]
        for key,suffix,dash in [('sigma_over_a2','PW',''),('sigma_born_over_a2','Born','7 4')]:
            # zero potential has sigma=0; log plot omits it explicitly
            xy=[(math.log10(r['x']),math.log10(r[key])) for r in rows if r[key]>0]
            if xy:
                curves.append((f'{case["name"]} {suffix}',xy,COLORS[idx],dash))
    if curves:
        plot(output/'energy.svg','Change energy with depth fixed', 'log10 axes; sigma=0 free-potential series omitted; solid PW, dashed Born', [('log10(ka)', 'log10(sigma / a^2)',curves)])
    else:
        plot(output/'energy.svg','Free potential: zero cross section','All cases eta=0; linear axes used', [('ka', 'sigma / a^2',[('free',[(x,0.) for x in card['scan_x']],COLORS[0],'')])])
    dcurves=[('PW',[(r['eta'],r['sigma_over_a2']) for r in depth],COLORS[0],''),('Born',[(r['eta'],r['sigma_born_over_a2']) for r in depth],COLORS[1],'7 4')]
    bcurves=[('bound s energy',[(r['eta'],r['bound_energy_over_Ea']) for r in depth if r['bound_energy_over_Ea'] is not None],COLORS[2],'')]
    if len(bcurves[0][1])<2:
        bcurves=[('no resolved bound branch',[(r['eta'],0.) for r in depth],COLORS[2],'7 4')]
    plot(output/'depth.svg','Approach the first s-wave threshold',f'fixed ka={card["depth_scan_x"]:.5g}; eta threshold=pi^2/4; zero energy is not an L2 state',
         [('eta = 2 mu W a^2 / hbar^2','sigma / a^2',dcurves),('eta','bound energy / Ea',bcurves)])
    return {'output':str(output),'cases':len(summaries),'files':8,'max_unitarity_residual':max(c['unitarity_residual'] for c in summaries)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError('output path already exists')
        card=json.loads(args.inputs.read_text(encoding='utf-8'),object_pairs_hook=unique_object,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
        print(json.dumps(generate(validate(card),args.output),sort_keys=True))
        return 0
    except (ValueError,OSError,TypeError,OverflowError,ZeroDivisionError) as exc:
        print('input/output error: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    sys.exit(main())
```
