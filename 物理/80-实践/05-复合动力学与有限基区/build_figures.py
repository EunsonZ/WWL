"""Small accessible SVGs from the single JSON teaching run. No plotting dependency."""
import json
import math
from html import escape
from pathlib import Path

ROOT=Path(__file__).parent
R=json.loads((ROOT/'assets/results.json').read_text())
COLORS=['#075985','#b45309','#6d28d9','#166534']

def svg(title,description,width=980,height=600):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{escape(title)}</title><desc>{escape(description)}</desc>',
            '<rect width="100%" height="100%" fill="#fff"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#172033;font-size:14px}.grid{stroke:#dce3ec;stroke-width:1}.axis{stroke:#24324a;stroke-width:1.2}</style>',
            f'<text x="30" y="30" style="font-size:20px;font-weight:bold">{escape(title)}</text>']

def panel(parts,box,xrange,yrange,xlabel,ylabel,xticks,yticks):
    x,y,w,h=box;xlo,xhi=xrange;ylo,yhi=yrange
    def coords(a,b):return x+(a-xlo)/(xhi-xlo)*w,y+h-(b-ylo)/(yhi-ylo)*h
    for t in xticks:
        xx,_=coords(t,ylo);parts.append(f'<line class="grid" x1="{xx}" y1="{y}" x2="{xx}" y2="{y+h}"/>')
        parts.append(f'<text x="{xx}" y="{y+h+21}" text-anchor="middle">{t:g}</text>')
    for t in yticks:
        _,yy=coords(xlo,t);parts.append(f'<line class="grid" x1="{x}" y1="{yy}" x2="{x+w}" y2="{yy}"/>')
        parts.append(f'<text x="{x-9}" y="{yy+5}" text-anchor="end">{t:g}</text>')
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" class="axis"/>')
    parts.append(f'<text x="{x+w/2}" y="{y+h+46}" text-anchor="middle">{escape(xlabel)}</text>')
    parts.append(f'<text x="{x}" y="{y-13}">{escape(ylabel)}</text>')
    return coords

def curve(parts,coords,points,color,dash=None):
    pts=' '.join(f'{x:.3f},{y:.3f}' for x,y in (coords(a,b) for a,b in points))
    pattern=f' stroke-dasharray="{dash}"' if dash else ''
    parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5"{pattern} points="{pts}"/>')

def legend(parts,x,y,items):
    for i,(color,dash,label) in enumerate(items):
        yy=y+24*i;pattern=f' stroke-dasharray="{dash}"' if dash else ''
        parts.append(f'<line x1="{x}" x2="{x+32}" y1="{yy}" y2="{yy}" stroke="{color}" stroke-width="2.5"{pattern}/><text x="{x+41}" y="{yy+5}">{escape(label)}</text>')

def save(parts,name):
    parts.append('</svg>');(ROOT/'assets'/name).write_text('\n'.join(parts)+'\n')

p=svg('Injection changes the rate and the decay','Same synthetic model; density in SI, time in nanoseconds. The constant exponentials are predictions to test, not fitted measurements.',980,590)
a=panel(p,(75,100,360,300),(16,25),(-2.5,3.2),'log10(delta / 1 m^-3)','log10(lifetime / 1 ns)',[16,18,20,22,24,25],[-2,-1,0,1,2,3])
for key,color,dash in [('tau_secant_s',COLORS[0],None),('tau_differential_s',COLORS[1],'8 5')]:
    curve(p,a,[(math.log10(s['delta_m3']),math.log10(s[key]*1e9)) for s in R['rate_sweep']],color,dash)
legend(p,80,476,[(COLORS[0],None,'secant delta/U'),(COLORS[1],'8 5','differential 1/(dU/ddelta)')])
b=panel(p,(535,100,365,300),(0,20),(0,1),'time after pump off / ns','delta(t) / delta(0)',[0,5,10,15,20],[0,.25,.5,.75,1])
curve(p,b,[(s['t_s']*1e9,s['delta_m3']/1e24) for s in R['decay']],COLORS[0])
initial=R['states'][-1]['tau_secant_s']
curve(p,b,[(s['t_s']*1e9,math.exp(-s['t_s']/initial)) for s in R['decay']],COLORS[1],'8 5')
curve(p,b,[(s['t_s']*1e9,math.exp(-s['t_s']/R['linear_tau_s'])) for s in R['decay']],COLORS[2],'2 5')
legend(p,540,476,[(COLORS[0],None,'nonlinear SRH + radiative + Auger'),(COLORS[1],'8 5','fixed initial secant lifetime'),(COLORS[2],'2 5','fixed low-injection lifetime')])
p.append('<text x="30" y="565">Fixed effective coefficients; high injection does not authorize a real silicon prediction.</text>')
save(p,'injection-decay.svg')

p=svg('The same base: density, particle flux and bulk loss','All three panels share x/L. Fn is positive particle flow to the right; conventional electron current has the opposite sign.',980,790)
items=[('None',COLORS[0],None,'absorbing u(L)=0'),('0.0',COLORS[1],'8 5','reflecting beta=0'),('1.0',COLORS[2],'2 5','finite contact beta=1')]
for row,key,label,limit,ticks in [(0,'delta_m3','u/u0',1.05,[0,.5,1]),(1,'Fn_m2_s','Fn/F*',1.4,[0,.5,1]),(2,'cumulative_bulk_m2_s','cumulative bulk loss / F*',.85,[0,.4,.8])]:
    c=panel(p,(80,90+205*row,630,135),(0,1),(0,limit),'x/L',label,[0,.25,.5,.75,1],ticks)
    for name,color,dash,_ in items:
        rows=R['base_profiles'][name];scale=1e18 if key=='delta_m3' else rows[0]['flux_scale_m2_s']
        curve(p,c,[(s['x_m']/R['Ln_m'],s[key]/scale) for s in rows],color,dash)
legend(p,740,140,[(color,dash,label) for _,color,dash,label in items])
p.append(f'<text x="30" y="745">L = Ln = {R["Ln_m"]*1e6:.4f} um; D = 0.003 m^2/s; bulk tau = {R["linear_tau_s"]*1e9:.3f} ns.</text>')
p.append('<text x="30" y="771">At every x: Fn(x) + cumulative bulk loss = Fn(0). No full-device Poisson solve.</text>')
save(p,'base-conservation.svg')

p=svg('Boundary loss changes the observed decay','A prepared nonnegative two-sine initial state with both ends absorbing. This is distinct from switching off the previous injected steady state.',980,560)
c=panel(p,(90,100,700,285),(0,200),(0,1),'time / ns','local u(L/4,t) / amplitude a',[0,50,100,150,200],[0,.25,.5,.75,1])
curve(p,c,[(s['t_s']*1e9,s['delta_m3']/1e18) for s in R['two_mode_quarter']],COLORS[0])
curve(p,c,[(s['t_s']*1e9,math.sin(math.pi/4)*math.exp(-s['t_s']/R['fundamental_tau_s'])) for s in R['two_mode_quarter']],COLORS[1],'8 5')
u0=math.sin(math.pi/4)+.25
curve(p,c,[(s['t_s']*1e9,u0*math.exp(-s['t_s']/R['linear_tau_s'])) for s in R['two_mode_quarter']],COLORS[2],'2 5')
legend(p,90,456,[(COLORS[0],None,'prepared two-mode local concentration'),(COLORS[1],'8 5','only the first spatial mode'),(COLORS[2],'2 5','same initial value, bulk-only exponential')])
p.append(f'<text x="30" y="545">Bulk tau {R["linear_tau_s"]*1e9:.3f} ns; first spatial mode {R["fundamental_tau_s"]*1e9:.3f} ns; no measured waveform.</text>')
save(p,'spatial-decay.svg')
