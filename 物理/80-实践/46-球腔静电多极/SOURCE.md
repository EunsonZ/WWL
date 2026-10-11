---
type: lab
domain: 物理
stage: 3
aliases:
  - 球腔静电多极规范源码镜像
sources: []
prerequisites:
  - "[[物理/80-实践/46-球腔静电多极/README]]"
---

# 球腔静电多极规范源码镜像

真源见 [[物理/80-实践/46-球腔静电多极/README|实践入口]] 中的规范Python文件。本页提供全文静态阅读镜像；修改真源后同步，不在围栏内另建行为版本。

<!-- code-sync: 物理/80-实践/46-球腔静电多极/sphere_multipole.py -->

```python
#!/usr/bin/env python3
"""Grounded spherical cavity: SI source, Legendre separation, image oracle.
Standard library only. Output must be a new empty directory.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

C0 = 299792458.0
MU0_APPROX = 4 * math.pi * 1e-7
EPS0 = 1 / (MU0_APPROX * C0**2)


def load(path):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError('duplicate input key')
            d[k] = v
        return d
    d = json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                   parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    expected = {'a_m', 'b_over_a', 'q_C', 'epsilon_r', 'orders', 'sample_r_over_a',
                'angle_samples', 'surface_panels', 'outer_radius_m'}
    if not isinstance(d, dict) or set(d) != expected:
        raise ValueError('input keys do not match the finite card')
    for k in ('a_m', 'b_over_a', 'q_C', 'epsilon_r', 'sample_r_over_a', 'outer_radius_m'):
        if isinstance(d[k], bool) or not isinstance(d[k], (int, float)) or not math.isfinite(d[k]):
            raise ValueError('finite real SI inputs required')
    if not 1e-4 <= d['a_m'] <= 1 or not 0.05 <= d['b_over_a'] <= 0.85:
        raise ValueError('finite card requires 0.1mm..1m and 0.05<=b/a<=0.85')
    if not 1e-12 <= abs(d['q_C']) <= 1e-6 or not 1 <= d['epsilon_r'] <= 100:
        raise ValueError('charge or positive dielectric outside finite card')
    if not d['b_over_a'] + 0.02 <= d['sample_r_over_a'] <= 0.98:
        raise ValueError('sample shell must be strictly outside source sphere')
    if not d['a_m'] < d['outer_radius_m'] <= 2:
        raise ValueError('floating migration outer radius must exceed a')
    for k, lo, hi in (('angle_samples', 61, 721), ('surface_panels', 512, 32768)):
        if type(d[k]) is not int or not lo <= d[k] <= hi:
            raise ValueError('integer sampling bounds violated')
    if d['surface_panels'] % 2:
        raise ValueError('Simpson panels must be even')
    if not isinstance(d['orders'], list) or not d['orders'] or len(d['orders']) > 12:
        raise ValueError('orders must be a nonempty bounded list')
    if any(type(n) is not int or not 0 <= n <= 128 for n in d['orders']):
        raise ValueError('orders must be integers 0..128')
    if sorted(set(d['orders'])) != d['orders']:
        raise ValueError('orders must be unique and increasing')
    return d


def legendre(n, u):
    p, dp = [1.0], [0.0]
    if n:
        p.append(u)
        dp.append(1.0)
    for l in range(1, n):
        p.append(((2*l+1)*u*p[l]-l*p[l-1])/(l+1))
        dp.append(((2*l+1)*(p[l]+u*dp[l])-l*dp[l-1])/(l+1))
    return p, dp


def scales(d):
    a = d['a_m']
    eps = d['epsilon_r'] * EPS0
    return d['q_C'] / (4*math.pi*eps*a), eps


def exact(d, rho, theta):
    """Two distances, no Legendre recursion; dimensionless image avoids huge a/b."""
    beta = d['b_over_a']
    u, s = math.cos(theta), math.sin(theta)
    ds = math.sqrt((rho-beta)**2 + 2*rho*beta*(1-u))
    di = math.sqrt((1-beta*rho)**2 + 2*beta*rho*(1-u))
    if ds == 0:
        raise ValueError('point source is singular')
    v, _ = scales(d)
    er = v/d['a_m']*((rho-beta*u)/ds**3 - (beta*beta*rho-beta*u)/di**3)
    et = v/d['a_m']*beta*s*(1/ds**3-1/di**3)
    return v*(1/ds-1/di), er, et


def separated(d, rho, theta, order, region='outer'):
    beta = d['b_over_a']
    if rho <= 0 or rho > 1:
        raise ValueError('separated evaluation requires 0<r<=a')
    if region == 'outer' and not rho > beta:
        raise ValueError('outer source expansion requires r>b')
    if region == 'inner' and not rho < beta:
        raise ValueError('inner source expansion requires r<b')
    if region not in ('outer', 'inner'):
        raise ValueError('unknown radial branch')
    p, dp = legendre(order, math.cos(theta))
    vals, radial, angular = [], [], []
    for l in range(order+1):
        if region == 'outer':
            f = beta**l*(rho**(-l-1)-rho**l)
            neg_df = beta**l*((l+1)*rho**(-l-2) + (l*rho**(l-1) if l else 0))
        else:
            c = beta**(-l-1)-beta**l
            f = rho**l*c
            neg_df = -l*rho**(l-1)*c if l else 0
        vals.append(f*p[l])
        radial.append(neg_df*p[l])
        angular.append(f*dp[l])
    v, _ = scales(d)
    return (v*math.fsum(vals), v/d['a_m']*math.fsum(radial),
            v/(d['a_m']*rho)*math.sin(theta)*math.fsum(angular))


def tail_linear(t, m, offset):
    return t**m*((m+offset)/(1-t)+t/(1-t)**2)


def tail_quadratic(t, m):
    return 0.5*t**m*(m*(m+1)/(1-t)+(2*m+1)*t/(1-t)**2+t*(1+t)/(1-t)**3)


def bounds(d, rho, order):
    beta = d['b_over_a']
    if not beta < rho <= 1:
        raise ValueError('outer error bound requires b<r<=a')
    t, h, m = beta/rho, beta*rho, order+1
    v = abs(scales(d)[0])
    vb = v*(t**m/(rho*(1-t)) + h**m/(1-h))
    rb = v/d['a_m']*(tail_linear(t,m,1)/rho**2 + tail_linear(h,m,0)/rho)
    tb = v/(d['a_m']*rho)*(tail_quadratic(t,m)/rho+tail_quadratic(h,m))
    return vb, rb, tb


def sigma(d, u):
    beta, a = d['b_over_a'], d['a_m']
    return -d['q_C']/(4*math.pi*a*a)*(1-beta*beta)/(1+beta*beta-2*beta*u)**1.5


def simpson(f, n):
    step = 2/n
    return step/3*math.fsum((1 if i in (0,n) else (4 if i % 2 else 2))*f(-1+i*step)
                          for i in range(n+1))


def write_csv(path, header, rows):
    with path.open('w', newline='') as out:
        w = csv.writer(out)
        w.writerow(header)
        w.writerows(rows)


def plot(path, title, xlabel, ylabel, curves, log=False):
    w,h = 820,450
    left,top,right,bottom = 95,65,790,350
    allxy = [(x, math.log10(max(y,1e-14)) if log else y) for _,_,xy in curves for x,y in xy]
    xs,ys = zip(*allxy)
    xmin,xmax,ymin,ymax = min(xs),max(xs),min(ys),max(ys)
    if xmin == xmax:
        xmin, xmax = xmin-0.5, xmax+0.5
    pad = max((ymax-ymin)*0.06, 1e-9)
    ymin,ymax = ymin-pad,ymax+pad
    def point(x,y):
        y = math.log10(max(y,1e-14)) if log else y
        return left+(right-left)*(x-xmin)/(xmax-xmin), bottom-(bottom-top)*(y-ymin)/(ymax-ymin)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<g font-family="Arial,sans-serif" font-size="14" fill="#182636">',
         f'<text x="30" y="28" font-size="20">{escape(title)}</text>']
    for i in range(6):
        x = xmin+(xmax-xmin)*i/5
        px,_ = point(x,ymin)
        y = ymin+(ymax-ymin)*i/5
        py = bottom-(bottom-top)*i/5
        s += [f'<path d="M {px} {top} V {bottom}" stroke="#e0e5eb"/>',
              f'<path d="M {left} {py} H {right}" stroke="#e0e5eb"/>',
              f'<text x="{px}" y="375" text-anchor="middle">{x:.3g}</text>',
              f'<text x="87" y="{py+5}" text-anchor="end">{y:.3g}</text>']
    s += [f'<path d="M {left} {top} V {bottom} H {right}" fill="none" stroke="#182636"/>',
          f'<text x="435" y="402" text-anchor="middle">{escape(xlabel)}</text>',
          f'<text x="18" y="205" transform="rotate(-90 18 205)" text-anchor="middle">{escape(ylabel)}</text>']
    for i,(label,color,xy) in enumerate(curves):
        pts=' '.join(f'{x:.3f},{y:.3f}' for x,y in (point(x,y) for x,y in xy))
        if len(xy) == 1:
            px,py=point(*xy[0])
            s.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="3.5" fill="{color}"/>')
        s += [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>',
              f'<text x="{105+(i%3)*235}" y="{425+(i//3)*17}" fill="{color}">{escape(label)}</text>']
    path.write_text('\n'.join(s+['</g></svg>'])+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    try:
        d=load(args.input)
        if args.output_dir.exists():
            raise ValueError('output directory must not already exist')
        angles=[math.pi*i/(d['angle_samples']-1) for i in range(d['angle_samples'])]
        rho=d['sample_r_over_a']
        fields=[]
        summaries=[]
        for n in d['orders']:
            vb,rb,tb=bounds(d,rho,n)
            errors=[]
            for th in angles:
                ex=exact(d,rho,th)
                se=separated(d,rho,th,n)
                ev,er=abs(se[0]-ex[0]),abs(se[1]-ex[1])
                fields.append([n,rho*d['a_m'],th*180/math.pi,*ex,*se,ev,er,vb,rb,tb])
                errors.append((ev,er,abs(se[2]-ex[2])))
            summaries.append([n,max(v[0] for v in errors),vb,max(v[1] for v in errors),rb,
                              max(v[2] for v in errors),tb])
        n=d['surface_panels'];a=d['a_m'];beta=d['b_over_a']
        surface=[]
        surface_bound=abs(d['q_C'])/(4*math.pi*a*a)*tail_linear(beta,33,0)*2 + abs(d['q_C'])/(4*math.pi*a*a)*beta**33/(1-beta)
        for th in angles:
            p,_=legendre(32,math.cos(th))
            truncated=-d['q_C']/(4*math.pi*a*a)*math.fsum((2*l+1)*beta**l*p[l] for l in range(33))
            surface.append([th*180/math.pi,sigma(d,math.cos(th)),exact(d,1,th)[1],truncated,surface_bound])
        moments=[]
        for panels in (n//2,n):
            for l in range(3):
                m=2*math.pi*a**(l+2)*simpson(lambda u:sigma(d,u)*legendre(l,u)[0][l],panels)
                target=-d['q_C']*(beta*a)**l
                moments.append([panels,l,m,target,m-target])
        invalid=[]
        for rh in (beta,0.5*beta):
            try:
                separated(d,rh,math.pi/2,16)
            except ValueError:
                invalid.append({'r_over_a':rh,'outer_rejected':True})
        v,_=scales(d)
        probe=exact(d,rho,math.pi/2)
        nearwall=abs(d['q_C'])/(4*math.pi*a*a)*(1+beta)/(1-beta)**2
        force=d['q_C']**2/(4*math.pi*scales(d)[1])*a*(beta*a)/(a*a-(beta*a)**2)**2
        energy=-d['q_C']**2/(8*math.pi*scales(d)[1])*a/(a*a-(beta*a)**2)
        data={'model':'grounded spherical cavity; constant positive dielectric; point-source self-energy excluded',
              'input':d,'epsilon0_F_per_m':EPS0,'potential_scale_V':v,'probe_equator':dict(zip(('phi_V','Er_V_per_m','Etheta_V_per_m'),probe)),
              'source_moments_C_m_power':[d['q_C']*(beta*a)**l for l in range(3)],
              'image':{'q_C':-d['q_C']/beta,'z_m':a/beta,'physical_surface_Q_C':-d['q_C']},
              'sigma_near_C_per_m2':sigma(d,1),'sigma_far_C_per_m2':sigma(d,-1),
              'max_abs_sigma_C_per_m2':nearwall,'reaction_force_z_N':force,'reaction_energy_J':energy,
              'floating_neutral':{'outer_charge_C':d['q_C'],'shell_potential_V':d['q_C']/(4*math.pi*EPS0*d['outer_radius_m']),
                                  'inside_field_unchanged':True,'outside_phi_rule':'q/(4*pi*epsilon0*r)'},
              'inner_probe':{'r_over_a':beta/2,'image':exact(d,beta/2,math.pi/2),
                             'inner_L64':separated(d,beta/2,math.pi/2,64,'inner')},
              'invalid_outer_evaluations':invalid,
              'bounds_cover_all_angles':all(row[1]<=row[2]+1e-10 and row[3]<=row[4]+1e-8 and row[5]<=row[6]+1e-8 for row in summaries)}
        if not data['bounds_cover_all_angles']:
            raise ValueError('computed error exceeds analytic tail bound')
        args.output_dir.mkdir(parents=True)
        write_csv(args.output_dir/'fields.csv',['L','r_m','theta_deg','phi_exact_V','Er_exact_V_per_m','Etheta_exact_V_per_m',
                  'phi_L_V','Er_L_V_per_m','Etheta_L_V_per_m','phi_error_V','Er_error_V_per_m','phi_bound_V','Er_bound_V_per_m','Etheta_bound_V_per_m'],fields)
        write_csv(args.output_dir/'convergence.csv',['L','max_phi_error_V','phi_bound_V','max_Er_error_V_per_m','Er_bound_V_per_m','max_Etheta_error_V_per_m','Etheta_bound_V_per_m'],summaries)
        write_csv(args.output_dir/'surface.csv',['theta_deg','sigma_C_per_m2','Er_wall_V_per_m','sigma_L32_C_per_m2','sigma_L32_bound_C_per_m2'],surface)
        write_csv(args.output_dir/'moments.csv',['panels','l','surface_moment_C_m_power','expected_C_m_power','error_C_m_power'],moments)
        (args.output_dir/'results.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
        colors=['#1763a6','#d17a00','#20915c','#8752ae']
        curves=[('image exact','#111111',[(th*180/math.pi,exact(d,rho,th)[0]) for th in angles])]
        for n,col in zip(d['orders'][:3],colors):
            curves.append((f'L={n}',col,[(th*180/math.pi,separated(d,rho,th,n)[0]) for th in angles]))
        plot(args.output_dir/'potential.svg',f'Grounded cavity: b/a={beta:g}, r/a={rho:g}','theta (degree)','potential (V)',curves)
        plot(args.output_dir/'convergence.svg',f'Outer expansion error: b/a={beta:g}, r/a={rho:g}','highest degree L','log10(error / unit); unit: V or V/m',[
             ('max phi error (V)',colors[0],[(x[0],x[1]) for x in summaries]),
             ('phi bound (V)',colors[1],[(x[0],x[2]) for x in summaries]),
             ('max Er error (V/m)',colors[2],[(x[0],x[3]) for x in summaries]),
             ('Er bound (V/m)',colors[3],[(x[0],x[4]) for x in summaries])],True)
        plot(args.output_dir/'surface.svg',f'Inner wall free charge: b/a={beta:g}','theta (degree)','surface charge (nC/m^2)',[
             ('exact induced sigma',colors[0],[(x[0],x[1]*1e9) for x in surface])])
        source_x=180+115*beta
        image_x=min(700,180+115/beta)
        image_note='Image marker compressed; position label is exact.' if 180+115/beta>700 else 'Image is outside the solved cavity.'
        geometry=f'''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="330" viewBox="0 0 820 330">
<rect width="820" height="330" fill="white"/>
<g font-family="Arial,sans-serif" font-size="16" fill="#182636">
<text x="25" y="30" font-size="21">Point source in a grounded spherical cavity</text>
<circle cx="180" cy="165" r="115" fill="#edf5ff" stroke="#52677e" stroke-width="9"/>
<circle cx="180" cy="165" r="{115*beta}" fill="none" stroke="#1763a6" stroke-dasharray="5 4"/>
<path d="M 45 165 H 770" stroke="#566575"/>
<text x="774" y="160">+z</text><text x="160" y="188">O</text>
<circle cx="{source_x}" cy="165" r="6" fill="#d34c36"/>
<text x="{source_x-10}" y="148">q</text><text x="{source_x-4}" y="210">b</text>
<circle cx="{image_x}" cy="165" r="6" fill="none" stroke="#d34c36" stroke-width="2"/>
<text x="{image_x-35}" y="138">image q* = -q a/b</text>
<text x="{image_x-35}" y="197">z* = a^2/b</text>
<text x="352" y="240">{image_note}</text>
<text x="352" y="263">It is not a physical electrode charge.</text>
<text x="32" y="313">Blue disk r &lt; a: physical domain; dashed r=b: outer series requires r &gt; b.</text>
<text x="65" y="62">wall phi=0</text><text x="260" y="100">r=a</text>
</g></svg>'''
        (args.output_dir/'geometry.svg').write_text(geometry+'\n')
        print(json.dumps({'outputs':9,'probe_equator':data['probe_equator'],'bounds_cover_all_angles':True},allow_nan=False))
    except (ValueError, OSError, OverflowError, ZeroDivisionError) as exc:
        ap.exit(2,f'error: {exc}\n')


if __name__=='__main__':
    main()
```
