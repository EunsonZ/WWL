---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# MIMO 设计图源镜像

规范源码见 [build_figures.py](build_figures.py)，此页只保留同字节镜像。

<!-- code-sync: 控制论/80-实践/12-MIMO反馈与观测器设计/build_figures.py -->

```python
#!/usr/bin/env python3
"""Draw continuous MIMO design trajectories from CSV and the same summary snapshot."""
from __future__ import annotations
import argparse
import csv
import html
import json
import math
from pathlib import Path
import re
import sys

COLORS=['#1f618d','#ad5000','#237044','#773fa0','#a32946','#006c72','#67530d','#444444']
DASH=['','10 4','3 4','10 3 2 3','14 4 4 4','2 3 2 3 9 3','16 3 2 3 2 3','5 2 1 2']


def finite(value):
    v=float(value)
    if not math.isfinite(v):raise ValueError('Nonfinite plot value')
    return v


def load(results):
    summary=json.loads((results/'summary.json').read_text())
    if summary.get('schema')!='wwl-mimo-care-results-1':raise ValueError('Wrong summary schema')
    card=summary['input_snapshot'];cases=summary['cases']
    if not isinstance(cases,list) or not 1<=len(cases)<=8:raise ValueError('Require 1..8 cases')
    snapshots={c['name']:c for c in card['cases']}
    if len(snapshots)!=len(cases) or set(snapshots)!={c['name'] for c in cases}:raise ValueError('Case snapshot mismatch')
    data={}
    for c in cases:
        filename=c['file']
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,45}\.csv',filename):raise ValueError('Unsafe CSV filename')
        with (results/filename).open(newline='') as handle:
            reader=csv.DictReader(handle);rows=[{k:finite(v) for k,v in row.items()} for row in reader]
        if len(rows)<2 or any(rows[i]['tau']>=rows[i+1]['tau'] for i in range(len(rows)-1)):
            raise ValueError('Require at least two strictly increasing time samples')
        data[c['name']]=rows
    return summary,snapshots,data


def curve(label,rows,key,factor=1.):
    return {'label':label,'points':[(r['tau'],r[key]*factor) for r in rows]}


def figure(title,subtitle,panels):
    width=960;left=82;right=28;plot_width=width-left-right
    heights=[270+24*math.ceil(len(p['curves'])/2) for p in panels]
    height=90+sum(heights)+20
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#222} .grid{stroke:#ddd;stroke-width:1}</style>',
         f'<text x="30" y="30" font-size="22">{html.escape(title)}</text>',
         f'<text x="30" y="56" font-size="14">{html.escape(subtitle)}</text>']
    top=90
    for panel_index,(panel,ph) in enumerate(zip(panels,heights)):
        curves=panel['curves'];ptop=top+32;plot_height=160
        svg.append(f'<text x="30" y="{top+12}" font-size="17">{html.escape(panel["title"])}</text>')
        if not curves:
            svg.append(f'<text x="{left}" y="{ptop+70}" font-size="15">{html.escape(panel.get("empty","No curves for this card"))}</text>')
            top+=ph;continue
        points=[v for c in curves for v in c['points']]
        xmin=min(v[0] for v in points);xmax=max(v[0] for v in points)
        ymin=min(0.,min(v[1] for v in points));ymax=max(v[1] for v in points)
        if ymax-ymin<1e-14:ymax=ymin+1.
        pad=.08*(ymax-ymin);ymin-=pad;ymax+=pad
        if not all(math.isfinite(v) for v in [xmin,xmax,ymin,ymax]) or xmax<=xmin:raise ValueError('Invalid plot extent')
        def px(t):return left+(t-xmin)/(xmax-xmin)*plot_width
        def py(v):return ptop+plot_height-(v-ymin)/(ymax-ymin)*plot_height
        for j in range(5):
            t=xmin+j*(xmax-xmin)/4;y=ymin+j*(ymax-ymin)/4
            xt=px(t);yt=py(y)
            svg.extend([f'<line class="grid" x1="{xt:.3f}" y1="{ptop}" x2="{xt:.3f}" y2="{ptop+plot_height}"/>',
                        f'<line class="grid" x1="{left}" y1="{yt:.3f}" x2="{left+plot_width}" y2="{yt:.3f}"/>',
                        f'<text x="{xt:.3f}" y="{ptop+plot_height+18}" text-anchor="middle" font-size="12">{t:.3g}</text>',
                        f'<text x="{left-8}" y="{yt+4:.3f}" text-anchor="end" font-size="12">{y:.4g}</text>'])
        svg.append(f'<text x="{left+plot_width/2}" y="{ptop+plot_height+37}" text-anchor="middle" font-size="13">tau = t / t0</text>')
        for i,c in enumerate(curves):
            color=COLORS[i%8];dash=DASH[i%8];attr=f' stroke-dasharray="{dash}"' if dash else ''
            coords=' '.join(f'{px(t):.3f},{py(v):.3f}' for t,v in c['points'])
            label=html.escape(c['label'],quote=True)
            svg.append(f'<polyline data-panel="{panel_index}" data-curve="{i}" data-label="{label}" fill="none" stroke="{color}" stroke-width="2"{attr} points="{coords}"/>')
            lx=left+(i%2)*425;ly=ptop+plot_height+64+(i//2)*24
            svg.append(f'<line x1="{lx}" y1="{ly-4}" x2="{lx+34}" y2="{ly-4}" stroke="{color}" stroke-width="2"{attr}/>')
            svg.append(f'<text x="{lx+43}" y="{ly}" font-size="13">{label}</text>')
        top+=ph
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'


def build(results):
    results=Path(results);targets=[results/'design.svg',results/'boundaries.svg']
    if any(p.exists() for p in targets):raise ValueError('Refusing existing figure outputs')
    summary,snapshots,data=load(results)
    accepted=[c for c in summary['cases'] if c['status']=='numerical_stabilizing_design']
    declined=[c for c in summary['cases'] if c['status']=='design_declined_by_numerical_pbh']
    if len(accepted)+len(declined)!=len(summary['cases']):raise ValueError('Unknown result status')
    t0=finite(summary['input_snapshot']['time_scale_s'])
    subtitle=f'Continuous trajectories; t0 = {t0:g} s; norms restored with the card display scales'
    design=[]
    for title,key in [('Actual state norm','norm_x_display'),('Estimation error norm','norm_e_display'),('Actual action norm','norm_u_display')]:
        design.append({'title':title,'curves':[curve(c['name'],data[c['name']],key) for c in accepted],
                       'empty':'No stabilizing design accepted in this card'})
    boundary=[]
    if accepted:
        c=accepted[0];n=c['n'];rows=data[c['name']];scale=finite(snapshots[c['name']]['state_scale'][n-1])
        boundary.append({'title':f'{c["name"]}: last state coordinate and its estimate, in display units',
                         'curves':[curve('actual last coordinate',rows,f'x_raw{n}',scale),curve('estimated last coordinate',rows,f'hat_raw{n}',scale)]})
    else:boundary.append({'title':'State / estimate comparison','curves':[],'empty':'No observer-feedback trajectory in this card'})
    boundary.append({'title':'Declined models: zero-input open loop, no designed K or L',
                     'curves':[curve(c['name'],data[c['name']],'norm_x_display') for c in declined],
                     'empty':'No model was declined by the numerical PBH screen in this card'})
    texts=[figure('MIMO feedback and observer design',subtitle,design),
           figure('Port conditions and hidden motion',f'All curves read from this run CSV; t0 = {t0:g} s',boundary)]
    made=[]
    try:
        for path,content in zip(targets,texts):
            with path.open('x') as handle:handle.write(content)
            made.append(path)
    except Exception:
        for path in made:path.unlink()
        raise
    return targets

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,required=True)
    args=parser.parse_args()
    try: outputs=build(args.results)
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f'error: {exc}',file=sys.stderr);sys.exit(2)
    print(json.dumps({'figures':[str(p) for p in outputs]}))
```
