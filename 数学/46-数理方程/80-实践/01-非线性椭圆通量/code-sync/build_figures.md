---
type: code
stage: 3
aliases: []
sources: []
prerequisites: []
---

# 非线性椭圆图源

返回 [[数学/46-数理方程/80-实践/01-非线性椭圆通量/README|复现说明]]。

<!-- code-sync: 数学/46-数理方程/80-实践/01-非线性椭圆通量/build_figures.py -->

```python
#!/usr/bin/env python3
"""Render result CSV and its parameter snapshot as standalone SVG figures."""
from __future__ import annotations
import argparse
import csv
import html
import json
import math
from pathlib import Path
import tempfile
import shutil
import sys

COLORS=['#235789','#bf4e30','#39795d','#794b96','#866a13','#a43969','#267879','#4c566a']
DASH=['','9 4','3 4','9 3 2 3','12 4 3 4','2 3','14 4','5 3 1 3']

def read_csv(path):
    with path.open(newline='') as handle:
        return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(handle)]


def curve(label,x,y):
    if len(x)!=len(y) or not x or not all(math.isfinite(v) for v in x+y):
        raise ValueError('Nonfinite or empty curve')
    return label,x,y


def panel(parts,index,title,xlabel,ylabel,curves):
    top=78+index*340
    left,right=98,854
    ytop,ybottom=top+33,top+223
    xs=[v for _,x,_ in curves for v in x];ys=[v for _,_,y in curves for v in y]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
    if xmin==xmax:xmax=xmin+1
    if ymin==ymax:
        ymin-=max(1,abs(ymin))*.1;ymax+=max(1,abs(ymax))*.1
    pad=(ymax-ymin)*.06;ymin-=pad;ymax+=pad
    def project(x,y):
        return left+(x-xmin)/(xmax-xmin)*(right-left),ybottom-(y-ymin)/(ymax-ymin)*(ybottom-ytop)
    parts.append(f'<text x="98" y="{top+17}" font-size="17" font-weight="bold">{html.escape(title)}</text>')
    for k in range(5):
        y=ymin+(ymax-ymin)*k/4;_,py=project(xmin,y)
        x=xmin+(xmax-xmin)*k/4;px,_=project(x,ymin)
        parts.append(f'<path d="M {left} {py:.3f} H {right}" stroke="#d8dee5"/><text x="86" y="{py+4:.3f}" text-anchor="end" font-size="12">{y:.3g}</text>')
        parts.append(f'<text x="{px:.3f}" y="{ybottom+18}" text-anchor="middle" font-size="12">{x:.3g}</text>')
    parts.append(f'<path d="M {left} {ytop} V {ybottom} H {right}" fill="none" stroke="#404c59"/>')
    parts.append(f'<text x="476" y="{ybottom+38}" text-anchor="middle" font-size="13">{html.escape(xlabel)}</text><text transform="translate(24,{(ytop+ybottom)/2}) rotate(-90)" text-anchor="middle" font-size="13">{html.escape(ylabel)}</text>')
    for j,(label,x,y) in enumerate(curves):
        points=' '.join(f'{a:.3f},{b:.3f}' for a,b in (project(xx,yy) for xx,yy in zip(x,y)))
        dash=f' stroke-dasharray="{DASH[j]}"' if DASH[j] else ''
        parts.append(f'<polyline data-panel="{index}" data-curve="{j}" data-label="{html.escape(label,quote=True)}" data-xmin="{xmin:.17g}" data-xmax="{xmax:.17g}" data-ymin="{ymin:.17g}" data-ymax="{ymax:.17g}" data-left="{left}" data-right="{right}" data-top="{ytop}" data-bottom="{ybottom}" points="{points}" fill="none" stroke="{COLORS[j]}" stroke-width="2"{dash}/>')
        if len(x)==1:
            px,py=project(x[0],y[0])
            parts.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="9" fill="white" stroke="{COLORS[j]}"/><text x="{px:.3f}" y="{py+4:.3f}" text-anchor="middle" font-size="11" fill="{COLORS[j]}">{j+1}</text>')
            label=f'{j+1}: '+label
        lx=98+(j%3)*260;ly=ybottom+60+(j//3)*19
        parts.append(f'<path d="M {lx} {ly} h 24" stroke="{COLORS[j]}" stroke-width="2"{dash}/><text x="{lx+30}" y="{ly+4}" font-size="12">{html.escape(label)}</text>')


def document(title,subtitle,panels):
    height=95+340*len(panels)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>','<g font-family="sans-serif" fill="#26323d">',
           f'<text x="45" y="30" font-size="22" font-weight="bold">{html.escape(title)}</text>',
           f'<text x="45" y="55" font-size="13">{html.escape(subtitle)}</text>']
    for i,args in enumerate(panels):panel(parts,i,*args)
    return '\n'.join(parts+['</g></svg>'])+'\n'


def build(results):
    results=Path(results)
    names=['profiles.svg','convergence.svg']
    if any((results/name).exists() for name in names):
        raise ValueError('Refusing existing figure output')
    summary=json.loads((results/'summary.json').read_text())
    if summary.get('schema')!='wwl-elliptic-flux-results-1':raise ValueError('Wrong result schema')
    card=summary['input_snapshot'];ps=card['p_values'];ns=card['cells'];length=card['length'];source=card['source']
    if not 1<=len(ps)<=8 or not 1<=len(card['resonance_amplitudes'])<=8:raise ValueError('Curve budget exceeded')
    profiles=read_csv(results/'profiles.csv');edges=read_csv(results/'edges.csv');resonance=read_csv(results/'resonance.csv')
    def rows(p,n):return [r for r in profiles if r['p']==p and r['cells']==n]
    exact=[]
    for p in ps:
        rr=rows(p,max(ns));exact.append(curve(f'p={p:g} exact',[r['x'] for r in rr],[r['u_exact'] for r in rr]))
    chosen=max(ps);coarse=min(ns);fine=max(ns);compare=[]
    for n in sorted({coarse,fine}):
        rr=rows(chosen,n);compare.append(curve(f'p={chosen:g}, N={n} FEM',[r['x'] for r in rr],[r['u_h'] for r in rr]))
    rr=rows(chosen,fine);compare.append(curve(f'p={chosen:g} exact',[r['x'] for r in rr],[r['u_exact'] for r in rr]))
    er=[r for r in edges if r['p']==chosen and r['cells']==coarse]
    x=[];q=[]
    for r in er:x += [r['left'],r['right']];q += [r['q_h'],r['q_h']]
    fluxcurves=[curve(f'N={coarse} cell flux',x,q),curve('continuous q(x)',[r['x'] for r in rr],[r['q_exact'] for r in rr])]
    resoncurves=[]
    for a in card['resonance_amplitudes']:
        ar=[r for r in resonance if r['amplitude']==a]
        resoncurves.append(curve(f'A={a:g}',[r['x'] for r in ar],[r['u'] for r in ar]))
    subtitle=f'Normalized variables; L={length:g}, F={source:g}; production = discrete flux shooting'
    profiles_svg=document('Nonlinear elliptic profiles and a separate resonance',subtitle,[
        ('How p changes the exact constant-source profile','x','u',exact),
        ('Small algebraic residual does not make the curve exact','x','u',compare),
        ('Hat tests balance neighboring cell fluxes','x','q',fluxcurves),
        ('Different operator: -u second derivative - pi^2 u = 0, L=1','x','A sin(pi x)',resoncurves)])
    errorpanels=[]
    for key,label in [('l2_error_estimate','L2 function error'),('gradient_lp_error_estimate','Lp gradient error')]:
        cs=[]
        allpositive=all(info[key]>0 for info in summary['cases'])
        for p in ps:
            infos=sorted([v for v in summary['cases'] if v['p']==p],key=lambda v:v['cells'])
            cs.append(curve(f'p={p:g}',[math.log2(v['cells']) for v in infos],
                            [math.log10(v[key]) if allpositive else v[key] for v in infos]))
        errorpanels.append((label+' (quadrature estimate)','log2 N','log10 error' if allpositive else 'error (zero-safe linear scale)',cs))
    convergence_svg=document('Mesh changes function and gradient errors',subtitle+'; slopes are model-specific, not a general theorem',errorpanels)
    temp=Path(tempfile.mkdtemp(prefix='.elliptic-fig-',dir=results))
    try:
        for name,content in zip(names,[profiles_svg,convergence_svg]):(temp/name).write_text(content)
        if any((results/name).exists() for name in names):raise ValueError('Figure outputs changed')
        for name in names:(temp/name).rename(results/name)
    finally:shutil.rmtree(temp)
    return names

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=build(args.results)
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        sys.exit(2)
    print(json.dumps({'figures':result}))
```
