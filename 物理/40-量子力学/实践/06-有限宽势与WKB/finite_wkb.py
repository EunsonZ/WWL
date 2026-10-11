"""Finite rectangular potential and local WKB diagnostics; standard library, one thread.
Run in a copy: outputs are placed next to this source, never in the working directory.
"""
import cmath
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
HBAR = 6.62607015e-34 / (2 * math.pi)
MASS = 1e-30
ELL = 1e-9
ESTAR = HBAR**2 / (2 * MASS * ELL**2)


def layer(e, v, width):
    """e=E/E*, v=V/E*, width=a/ell; derivative is d/d(x/ell)."""
    q2 = e - v
    if q2 > 0:
        q = math.sqrt(q2)
        c, s = math.cos(q * width), math.sin(q * width) / q
    elif q2 < 0:
        q = math.sqrt(-q2)
        c, s = math.cosh(q * width), math.sinh(q * width) / q
    else:
        c, s = 1.0, width
    return ((c, s), (-q2 * s, c))


def scatter(e, v, width):
    if e <= 0 or width <= 0:
        raise ValueError('Open exterior channel requires e>0, width>0')
    k = math.sqrt(e)
    mat = layer(e, v, width)
    c, s = mat[0]
    q2 = e - v
    den = 2j * k * c + (k * k + q2) * s
    r = (k * k - q2) * s / den
    tau = 2j * k / den
    t = tau * cmath.exp(-1j * k * width)
    return r, t, tau


def field(xi, e, v, width):
    k = math.sqrt(e)
    r, t, tau = scatter(e, v, width)
    if xi < 0:
        return cmath.exp(1j*k*xi)+r*cmath.exp(-1j*k*xi), 1j*k*(cmath.exp(1j*k*xi)-r*cmath.exp(-1j*k*xi))
    if xi > width:
        return t*cmath.exp(1j*k*xi), 1j*k*t*cmath.exp(1j*k*xi)
    p = layer(e, v, xi)
    y0, d0 = 1+r, 1j*k*(1-r)
    return p[0][0]*y0+p[0][1]*d0, p[1][0]*y0+p[1][1]*d0


def simpson(f, lo, hi, panels):
    if panels % 2:
        raise ValueError('even panels required')
    h = (hi-lo)/panels
    return h/3*(f(lo)+f(hi)+sum((4 if n%2 else 2)*f(lo+n*h) for n in range(1,panels)))


def pair(z):
    return [z.real, z.imag]


def svg_plot(path, title, desc, panels):
    """Each panel: ylabel, xmin,xmax,ymin,ymax, lines(label,color,dash,points)."""
    height = 85 + 245 * len(panels)
    bits = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}">',f'<title>{title}</title>',f'<desc>{desc}</desc>','<rect width="100%" height="100%" fill="white"/>','<g font-family="sans-serif" fill="#17212b">',f'<text x="60" y="30" font-size="20">{title}</text>']
    for n,(xlabel,ylabel,x0,x1,y0,y1,lines) in enumerate(panels):
        top=75+n*245
        px=lambda x:85+760*(x-x0)/(x1-x0)
        py=lambda y:top+150-150*(y-y0)/(y1-y0)
        bits.append(f'<path d="M85 {top} V{top+150} H845" fill="none" stroke="#333"/>')
        for j in range(5):
            x=x0+(x1-x0)*j/4
            y=y0+(y1-y0)*j/4
            bits += [f'<text x="{px(x):.1f}" y="{top+170}" font-size="12" text-anchor="middle">{x:.3g}</text>',f'<text x="76" y="{py(y)+4:.1f}" font-size="12" text-anchor="end">{y:.3g}</text>']
        bits += [f'<text x="465" y="{top+194}" text-anchor="middle" font-size="14">{xlabel}</text>',f'<text x="85" y="{top-12}" font-size="14">{ylabel}</text>']
        for j,(label,color,dash,pts) in enumerate(lines):
            poly=' '.join(f'{px(x):.3f},{py(y):.3f}' for x,y in pts if x0<=x<=x1 and y0<=y<=y1)
            bits += [f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',f'<text x="{95+j*245}" y="{top+220}" font-size="13" fill="{color}">{label}</text>']
    bits+=['</g></svg>']
    path.write_text('\n'.join(bits)+'\n')


def hermite(n, eta):
    if n == 0:
        return 1.0
    prev, cur = 1.0, 2*eta
    for j in range(1,n):
        prev, cur = cur, 2*eta*cur-2*j*prev
    return cur


def oscillator_exact(n, eta):
    return hermite(n,eta)*math.exp(-eta*eta/2)/(math.pi**0.25*math.sqrt(2**n*math.factorial(n)))


def oscillator_wkb(n, eta):
    e=n+0.5
    a=math.sqrt(2*e)
    if abs(eta)>=a:
        raise ValueError('interior WKB only; turning point excluded')
    k=math.sqrt(2*e-eta*eta)
    action=e*(math.pi/2-math.asin(eta/a))-eta*k/2
    return math.sqrt(2/math.pi)/math.sqrt(k)*math.sin(action+math.pi/4)


def wkb_outputs(assets):
    diagnostics=[]
    for n in [0,5,20]:
        e=n+0.5
        a=math.sqrt(2*e)
        # eta=a*sin(theta) removes square-root endpoint singularity.
        action=simpson(lambda theta:2*e*math.cos(theta)**2,-math.pi/2,math.pi/2,2000)
        assert abs(action-math.pi*e)<1e-12
        diag=[]
        for fraction in [0,0.5,0.9,0.99]:
            eta=fraction*a;d=2*e-eta*eta
            epsilon=abs(eta)/d**1.5
            chi=(4*e+3*eta*eta)/(4*d**3)
            diag.append(dict(eta_over_turning=fraction,epsilon=epsilon,relative_equation_residual=chi,exact=oscillator_exact(n,eta),wkb=oscillator_wkb(n,eta)))
        diagnostics.append(dict(n=n,energy_over_hbar_omega=e,action_over_hbar=action,exact_action=math.pi*e,points=diag))
    (assets/'wkb-checks.json').write_text(json.dumps(dict(model='harmonic oscillator, interior leading WKB, two simple turning points',diagnostics=diagnostics),indent=2)+'\n')
    panels=[]
    rows=[]
    for n in [0,20]:
        a=math.sqrt(2*n+1)
        exact=[];approx=[]
        for j in range(501):
            fraction=-0.99+1.98*j/500
            eta=a*fraction
            ex=oscillator_exact(n,eta);wb=oscillator_wkb(n,eta)
            exact.append((eta,ex));approx.append((eta,wb));rows.append((n,eta,fraction,ex,wb))
        panels.append(('eta = x / sqrt(hbar/(m omega))','U = sqrt(ell_ho) psi (dimensionless)',-a,a,-1.8,1.8,[(f'n={n} exact','#0072b2','',exact),(f'n={n} leading WKB','#d55e00','5,3',approx)]))
    with (assets/'wkb-oscillator.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['n','eta','eta_over_turning','exact_U','WKB_U']);wr.writerows(rows)
    svg_plot(assets/'wkb-oscillator.svg','Correct oscillator energies do not remove turning-point failure','Harmonic oscillator with eta=x/ell_ho, ell_ho=sqrt(hbar/(m omega)), E=(n+1/2) hbar omega. Curves use exact Hermite states and interior leading WKB at 0.99 of each turning coordinate; endpoints themselves are excluded. WKB diverges at turning points; exact states remain finite.',panels)
    return max(abs(d['action_over_hbar']-d['exact_action']) for d in diagnostics)


def main():
    assets=HERE/'assets'
    assets.mkdir(exist_ok=True)
    inputs=json.loads((HERE/'inputs.json').read_text())
    cases=[]
    maxres=0.0
    for cfg in inputs['scattering_cases']:
        e,v,a=cfg['e'],cfg['v'],cfg['width']
        r,t,tau=scatter(e,v,a)
        y0,d0=field(0,e,v,a)
        ya,da=field(a,e,v,a)
        k=math.sqrt(e)
        residual=max(abs(y0-(1+r)),abs(d0-1j*k*(1-r)),abs(ya-tau),abs(da-1j*k*tau),abs(abs(r)**2+abs(t)**2-1))
        currents=[(field(x,e,v,a)[0].conjugate()*field(x,e,v,a)[1]).imag/k for x in [-1,0.25*a,0.75*a,a+1]]
        residual=max(residual,*(abs(j-abs(t)**2) for j in currents))
        assert residual<1e-12
        maxres=max(maxres,residual)
        cases.append(dict(name=cfg['name'],e=e,v=v,width=a,r=pair(r),t=pair(t),tau=pair(tau),R=abs(r)**2,T=abs(t)**2,net_current_over_incident=currents,residual=residual))
    assert abs(cases[0]['T']-1/math.cosh(1)**2)<1e-13
    assert abs(cases[1]['T']-0.8)<1e-13
    assert abs(cases[2]['T']-1)<1e-13
    # Bound example: half width b=ell, z=w=pi/4, depth Vw/E*=pi^2/8.
    z=math.pi/4
    n2=1/(1+4/math.pi)
    inside=lambda xi: n2*math.cos(z*xi)**2
    interior=simpson(inside,-1,1,2000)
    exterior=n2*math.cos(z)**2/z
    norm=interior+exterior
    assert abs(norm-1)<1e-12
    well=dict(depth_over_Estar=math.pi**2/8,energy_over_Estar=-math.pi**2/16,z=z,w=z,normalization_N2_times_ell=n2,norm=norm,exterior_probability=exterior,matching_residual=abs(z*math.tan(z)-z))
    (assets/'checks.json').write_text(json.dumps(dict(model='real rectangular potential, constant mass, exterior V=0',hbar_J_s=HBAR,mass_kg=MASS,ell_m=ELL,E_star_J=ESTAR,scattering=cases,max_residual=maxres,bound_well=well),indent=2)+'\n')
    rows=[]
    for j in range(401):
        e=0.05+(20-0.05)*j/400
        rows.append((e,scatter(e,4,2)[1],scatter(e,-4,2)[1]))
    with (assets/'transmission.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['energy_over_Estar','barrier_T_v4_a2','well_T_vminus4_a2'])
        wr.writerows((e,abs(tb)**2,abs(tw)**2) for e,tb,tw in rows)
    svg_plot(assets/'finite-transmission.svg','Finite width a=2 ell: tunnelling and resonant transmission','Same constant-mass model; m=1e-30 kg, ell=1 nm, a=2 ell. Exterior V=0. Barrier V=4 E*, well V=-4 E*. E*=5.56060859e-21 J. T is a probability-current ratio.',[('E / E* (dimensionless)','T (current ratio)',0,20,0,1,[('Barrier V=+4E*','#0072b2','',[(e,abs(tb)**2) for e,tb,tw in rows]),('Well V=-4E*','#d55e00','5,3',[(e,abs(tw)**2) for e,tb,tw in rows])])])
    fields=[(x/100,*field(x/100,1,2,1)) for x in range(-150,251)]
    with (assets/'barrier-field.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['x_over_ell','real_phi','imag_phi','abs_phi_squared','current_over_incident'])
        wr.writerows((x,p.real,p.imag,abs(p)**2,(p.conjugate()*d).imag) for x,p,d in fields)
    svg_plot(assets/'barrier-field.svg','A finite forbidden region still carries net current','E=E*, V=2E*, a=ell=1 nm; phi=psi/A dimensionless, A=ell^-1/2. Real and imaginary amplitude must both be retained. Lower panel: V/E* and E/E*, separate from amplitude.',[('x / ell (dimensionless)','phi=psi/A (dimensionless)',-1.5,2.5,-1.5,1.5,[('Re phi','#0072b2','',[(x,p.real) for x,p,d in fields]),('Im phi','#d55e00','5,3',[(x,p.imag) for x,p,d in fields])]),('x / ell (dimensionless)','Energy / E* (dimensionless)',-1.5,2.5,0,2.3,[('V/E*','#111','',[(-1.5,0),(0,0),(0,2),(1,2),(1,0),(2.5,0)]),('E/E*=1','#009e73','5,3',[(-1.5,1),(2.5,1)])])])
    action_error=wkb_outputs(assets)
    print(json.dumps({'status':'PASS','max_residual':maxres,'bound_norm':norm,'case_count':len(cases),'max_WKB_action_quadrature_error':action_error}))

if __name__=='__main__':
    main()
