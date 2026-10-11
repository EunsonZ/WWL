#!/usr/bin/env python3
"""Draw two SVGs from actual result snapshots; standard library, no resimulation."""
import argparse
import csv
import html
import json
import math
from pathlib import Path

COLORS=['#2563eb','#dc2626','#15803d','#7c3aed','#475569']

def read_csv(path):
    with path.open() as f:
        return [{k:float(v) if k!='material' else v for k,v in row.items()} for row in csv.DictReader(f)]

class Figure:
    def __init__(self,title,subtitle):
        self.parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="860" viewBox="0 0 1160 860">','<rect width="1160" height="860" fill="#fff"/>',f'<title>{html.escape(title)}</title>']
        self.text(580,30,title,22,'middle');self.text(580,55,subtitle,13,'middle','#475569')
    def text(self,x,y,t,size=12,anchor='start',color='#0f172a'):
        self.parts.append(f'<text x="{x:.4f}" y="{y:.4f}" font-family="Arial,sans-serif" font-size="{size}" text-anchor="{anchor}" fill="{color}">{html.escape(t)}</text>')
    def line(self,x1,y1,x2,y2,color='#cbd5e1',width=1,dash=''):
        self.parts.append(f'<line x1="{x1:.4f}" y1="{y1:.4f}" x2="{x2:.4f}" y2="{y2:.4f}" stroke="{color}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
    def panel(self,slot,title,xlabel,ylabel,series,xticks=None,xlabels=None):
        left=88+(slot%2)*566;top=105+(slot//2)*365;w=430;h=240
        xs=[x for s in series for x in s['x']];ys=[y for s in series for y in s['y']]
        if not xs or not all(math.isfinite(v) for v in xs+ys):raise ValueError('finite plot data required')
        xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        if xmin==xmax:xmin-=.5;xmax+=.5
        pad=(ymax-ymin)*.08 or max(abs(ymax)*.05,1e-6);ymin-=pad;ymax+=pad
        def px(x):return left+(x-xmin)/(xmax-xmin)*w
        def py(y):return top+h-(y-ymin)/(ymax-ymin)*h
        self.text(left,top-22,title,15);self.text(left,top-7,ylabel,11)
        for i in range(5):
            y=ymin+(ymax-ymin)*i/4;self.line(left,py(y),left+w,py(y),'#e2e8f0');self.text(left-8,py(y)+4,f'{y:.4g}',11,'end')
        ticks=xticks if xticks is not None else [xmin+(xmax-xmin)*i/4 for i in range(5)]
        for j,x in enumerate(ticks):
            self.line(px(x),top+h,px(x),top+h+4,'#64748b');self.text(px(x),top+h+18,xlabels[j] if xlabels else f'{x:g}',10,'middle')
        self.line(left,top,left,top+h,'#64748b');self.line(left,top+h,left+w,top+h,'#64748b')
        self.text(left+w/2,top+h+38,xlabel,12,'middle')
        if xmin<0<xmax:self.line(px(0),top,px(0),top+h,'#94a3b8',1,'3 4')
        for k,s in enumerate(series):
            color=s.get('color',COLORS[k%len(COLORS)]);points=' '.join(f'{px(x):.4f},{py(y):.4f}' for x,y in zip(s['x'],s['y']))
            self.parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{s.get("width",2)}"'+(f' stroke-dasharray="{s["dash"]}"' if s.get('dash') else '')+'/>')
            if len(s['x'])<=4:
                for x,y in zip(s['x'],s['y']):self.parts.append(f'<circle cx="{px(x):.4f}" cy="{py(y):.4f}" r="3" fill="{color}"/>')
            lx=left+(k%2)*218;ly=top+h+58+(k//2)*19
            self.line(lx,ly-4,lx+19,ly-4,color,2,s.get('dash',''));self.text(lx+25,ly,s['label'],11)
    def save(self,path):
        if path.exists():raise FileExistsError('refuse existing figure '+str(path))
        path.write_text('\n'.join(self.parts+['</svg>'])+'\n')

def series(rows,key,label,scale=1.,color=None,dash=''):
    return {'x':[r['x_m']*1e9 for r in rows],'y':[r[key]*scale for r in rows],'label':label,'color':color or COLORS[0],'dash':dash}

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);args=p.parse_args();root=args.results
    names=['space-and-current.svg','balance-and-changes.svg']
    if any((root/n).exists() for n in names):raise FileExistsError('both figures must be absent')
    report=json.loads((root/'results.json').read_text());fine=report['transport_input']['half_cells'][-1];main_name=f'forward_n{fine}'
    eq=read_csv(root/'equilibrium-profile.csv');prof=read_csv(root/(main_name+'-profile.csv'));edges=read_csv(root/(main_name+'-edges.csv'))
    mainV=report['cases'][main_name]['bias_V'];temp=report['base_input']['temperature_K']
    extent=report['base_input']['half_length_m']*1e9;space_ticks=[-extent,-extent/2,0,extent/2,extent]
    f=Figure('Biased heterojunction: bands, two chemical potentials, two currents',f'Synthetic A/B, {temp:g} K, fixed positive sheet; ideal zero-resistance interface; right V = {mainV*1e3:g} mV')
    f.panel(0,'Band edges: equilibrium and biased','x (nm)','Energy (eV; common reference)',[series(eq,'Ec_eV','Ec equilibrium',color=COLORS[4],dash='4 3'),series(eq,'Ev_eV','Ev equilibrium',color=COLORS[4],dash='4 3'),series(prof,'Ec_eV','Ec biased',color=COLORS[0]),series(prof,'Ev_eV','Ev biased',color=COLORS[1])],space_ticks)
    f.panel(1,'Quasi-Fermi levels: continuous at ideal interface','x (nm)','Energy (eV; same reference)',[series(prof,'Fn_eV','Fn',color=COLORS[0]),series(prof,'Fp_eV','Fp',color=COLORS[1])],space_ticks)
    s=[]
    for k,label,color in [('Jn_A_m-2','Jn',COLORS[0]),('Jp_A_m-2','Jp',COLORS[1]),('Jtotal_A_m-2','Jn + Jp',COLORS[2])]:s.append({'x':[r['x_mid_m']*1e9 for r in edges],'y':[r[k]*1e3 for r in edges],'label':label,'color':color})
    f.panel(2,'Conventional currents: +x is positive','x at edge midpoint (nm)','Current density (mA/m²)',s,space_ticks)
    f.panel(3,'Net bulk SRH: positive means recombination','x (nm)','U (10^21 m^-3 s^-1)',[series(prof,'U_m-3_s-1','Net U',1e-21,COLORS[3])],space_ticks)
    g=Figure('Current balance and changes of assumptions','Actual solved data; all cumulative integrals use the same node quadrature as continuity rows')
    q=1.602176634e-19;nodeU={}
    for r in prof:nodeU[r['x_m']]=nodeU.get(r['x_m'],0.)+r['U_m-3_s-1']*r['quadrature_weight_m']
    keys=sorted(nodeU);cumulative=[];cum=nodeU[keys[0]]
    for i in range(len(edges)):
        if i>0:cum+=nodeU[keys[i]]
        cumulative.append(q*cum*1e3)
    x=[r['x_mid_m']*1e9 for r in edges]
    g.panel(0,'One source, two opposite current changes','x at edge midpoint (nm)','Change or q integral (mA/m²)',[{'x':x,'y':cumulative,'label':'q cumulative integral U','color':COLORS[2],'width':4},{'x':x,'y':[(r['Jn_A_m-2']-edges[0]['Jn_A_m-2'])*1e3 for r in edges],'label':'Jn(x) - Jn(left)','color':COLORS[0],'dash':'8 4'},{'x':x,'y':[(edges[0]['Jp_A_m-2']-r['Jp_A_m-2'])*1e3 for r in edges],'label':'Jp(left) - Jp(x)','color':COLORS[1],'dash':'2 5'}],space_ticks)
    c=report['cases'][main_name];vals=[q*c['SRH_balances'][k]['U_integral_m-2_s-1'] for k in ('A','B')]
    # Zero main bias is legal; its exactly zero SRH budget has no logarithm.
    all_nonzero=all(v!=0 for v in vals)
    budgets=[math.log10(abs(v)) for v in vals] if all_nonzero else vals
    budget_label='log10(|q integral U| / (1 A/m²))' if all_nonzero else 'q integral U (A/m²; zero budget)'
    g.panel(1,'Separate A/B source budgets (very different scales)','Material',budget_label,[{'x':[0.,1.],'y':budgets,'label':'A = '+f'{vals[0]:.6g}'+' A/m²','color':COLORS[3]},{'x':[0.,1.],'y':budgets,'label':'B = '+f'{vals[1]:.6g}'+' A/m²','color':COLORS[3],'dash':'2 5'}],[0,1],['A (p-type)','B (n-type)'])
    biasnames=[main_name,'half_bias','equilibrium','reverse'];bc=sorted([report['cases'][k] for k in biasnames],key=lambda c:c['bias_V'])
    g.panel(2,'Re-solve after bias or mobility changes','Right contact V (mV)','Total current (mA/m²)',[{'x':[c['bias_V']*1e3 for c in bc],'y':[sum(c['contact_J_left_A_m-2'])*1e3 for c in bc],'label':'Original transport','color':COLORS[0]},{'x':[mainV*1e3,mainV*1e3],'y':[sum(report['cases'][main_name]['contact_J_left_A_m-2'])*1e3,sum(report['cases']['A_electron_mobility_half']['contact_J_left_A_m-2'])*1e3],'label':'A electron mobility / 2','color':COLORS[1]}],sorted(set(c['bias_V']*1e3 for c in bc)))
    grids=report['transport_input']['half_cells'];cases=[report['cases'][f'forward_n{n}'] for n in grids]
    ref=cases[-1]['phi0_V'];yy=[abs(c['phi0_V']-ref)*1e6 for c in cases]
    g.panel(3,'Refinement: interface potential vs finest grid','h (nm)','|phi0(h) - phi0(finest)| (µV)',[{'x':[c['h_m']*1e9 for c in cases],'y':yy,'label':f"Finest {cases[-1]['h_m']*1e9:g} nm is a comparison",'color':COLORS[2]}],sorted(c['h_m']*1e9 for c in cases))
    f.save(root/names[0]);g.save(root/names[1])

if __name__=='__main__':main()
