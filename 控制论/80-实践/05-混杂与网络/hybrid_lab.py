#!/usr/bin/env python3
"""Finite serial CPU checks; no devices, no real-time guarantee, no installs."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'  # below the task ceiling of 4; no worker threads created
import argparse
import csv
import html
import json
import math
import platform
import resource
import time
from fractions import Fraction as F
from pathlib import Path


def plot(path, title, desc, series, xlabel, ylabel, ymin, ymax, xmax, guides=()):
    def xy(x, y):
        return 75 + 690*x/xmax, 350-270*(y-ymin)/(ymax-ymin)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="850" height="485" viewBox="0 0 850 485">',
           '<title>'+html.escape(title)+'</title><desc>'+html.escape(desc)+'</desc>',
           '<rect width="850" height="485" fill="white"/>',
           '<g font-family="sans-serif" font-size="13" fill="#172330">',
           '<text x="75" y="28" font-size="19">'+html.escape(title)+'</text>',
           '<text x="75" y="51">'+html.escape(desc)+'</text>']
    for j in range(6):
        x=xmax*j/5; px, _=xy(x, ymin)
        out += [f'<path d="M {px:.2f} 80 V 350" stroke="#e2e6ea"/>',f'<text x="{px:.2f}" y="371" text-anchor="middle">{x:.3g}</text>']
        y=ymin+(ymax-ymin)*j/5; _, py=xy(0,y)
        out += [f'<path d="M 75 {py:.2f} H 765" stroke="#e2e6ea"/>', f'<text x="65" y="{py+4:.2f}" text-anchor="end">{y:.3g}</text>']
    for y in guides:
        _, py=xy(0,y);out += [f'<path d="M 75 {py} H 765" stroke="#555" stroke-dasharray="3 5"/>']
    for j,(label,data,color,dash) in enumerate(series):
        pts=' '.join(f'{xy(x,y)[0]:.3f},{xy(x,y)[1]:.3f}' for x,y in data)
        out += [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                f'<path d="M 80 {414+j*21} H 114" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',
                f'<text x="122" y="{418+j*21}">{html.escape(label)}</text>']
    out += [f'<text x="420" y="397" text-anchor="middle">{html.escape(xlabel)}</text>',
            f'<text transform="translate(20 235) rotate(-90)" text-anchor="middle">{html.escape(ylabel)}</text>',
            '</g></svg>']
    path.write_text('\n'.join(out)+'\n', encoding='utf-8')


def mm(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def exact(z,c,q,t):
    a,b=z; e=math.exp(-t)
    return (e*(a+c*t*b), e*b) if q==1 else (e*a,e*(b+c*t*a))


def rk4(z,c,q,h):
    def f(v):
        a,b=v;return (-a+c*b,-b) if q==1 else (-a,-b+c*a)
    def add(v,w,s):return tuple(x+s*y for x,y in zip(v,w))
    k1=f(z);k2=f(add(z,k1,h/2));k3=f(add(z,k2,h/2));k4=f(add(z,k3,h))
    return tuple(x+h*(a+2*b+2*c+d)/6 for x,a,b,c,d in zip(z,k1,k2,k3,k4))


def main():
    start=time.monotonic()
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir
    if out.exists():raise SystemExit('Output directory must be new; refusing overwrite')
    cfg=json.loads(Path(__file__).with_name('hybrid-input.json').read_text())
    p=cfg['thermal'];C=p['C_J_per_K'];h=p['h_W_per_K'];U=p['U_W'];delta=p['delta_K']
    assert C>0 and h>0 and U>h*delta>0 and p['q0']==1 and p['x0_K']==0
    assert 0<p['end_s']<=100 and 0<cfg['switch_end']<=100
    for case in cfg['switch_cases']:
        assert 0<=case['c']<=4 and 0.5<=case['dwell']<=14
    def flow(x,q,t):return q*U/h+(x-q*U/h)*math.exp(-h*t/C)
    t=0.;x=p['x0_K'];q=p['q0'];events=[];rows=[];root_errors=[]
    while t<p['end_s']-1e-12:
        target=q*delta
        dt=C/h*math.log((q*U/h-x)/(q*U/h-target))
        lo=0.;hi=1.
        while q*(flow(x,q,hi)-target)<0:hi*=2
        for _ in range(60):
            mid=(lo+hi)/2
            if q*(flow(x,q,mid)-target)<0:lo=mid
            else:hi=mid
        root_errors.append(abs((lo+hi)/2-dt))
        dur=min(dt,p['end_s']-t)
        for j in range(51):
            s=dur*j/50;rows.append((t+s,flow(x,q,s),q,q*U,10+q*U))
        if dur<dt-1e-12:break
        t+=dt;x=target;events.append((len(events)+1,t,x,q,-q));q=-q
    assert max(root_errors)<1e-12
    assert max(abs(row[1]) for row in rows)<=delta+1e-12
    dwell=C/h*math.log((U/h+delta)/(U/h-delta))
    assert all(abs(events[j][1]-events[j-1][1]-dwell)<1e-12 for j in range(1,len(events)))
    A1=[[-1,4],[0,-1]];A2=[[-1,0],[4,-1]]
    P1=[[F(1,2),F(1)],[F(1),F(9,2)]];P2=[[F(9,2),F(1)],[F(1),F(1,2)]]
    for A,P in ((A1,P1),(A2,P2)):
        at=list(map(list,zip(*A)));m1=mm(at,P);m2=mm(P,A)
        assert [[m1[i][j]+m2[i][j] for j in range(2)] for i in range(2)]==[[-1,0],[0,-1]]
    small=(5-2*math.sqrt(5))/2;large=(5+2*math.sqrt(5))/2
    bound=large*math.log(large/small)
    z0=(1.,2+math.sqrt(5));norm=math.hypot(*z0);z0=tuple(v/norm for v in z0)
    rho=math.exp(-2)*(9+4*math.sqrt(5));z=z0
    eigen_errors=[]
    for n in range(1,13):
        z=exact(exact(z,4,1,1),4,2,1)
        eigen_errors.append(max(abs(z[i]/rho**n-z0[i]) for i in range(2)))
    assert max(eigen_errors)<1e-13
    refinement=[]
    for steps in (10,20,40):
        z=z0
        for q in (1,2):
            for _ in range(steps):z=rk4(z,4,q,1/steps)
        oracle=exact(exact(z0,4,1,1),4,2,1)
        refinement.append(max(abs(z[i]-oracle[i]) for i in range(2)))
    assert refinement[2]<refinement[1]<refinement[0] and refinement[-1]<2e-7
    swrows=[];series=[]
    for idx,case in enumerate(cfg['switch_cases']):
        z=z0;t=0.;q=1;curve=[]
        while t<cfg['switch_end']-1e-10:
            dur=min(case['dwell'],cfg['switch_end']-t)
            for j in range(21):
                s=dur*j/20;w=exact(z,case['c'],q,s);n=math.hypot(*w)
                swrows.append((case['name'],t+s,q,w[0],w[1],n));curve.append((t+s,math.log10(n)))
                if case['c']==1:assert n<=math.exp(-(t+s)/2)*(1+1e-12)
            z=exact(z,case['c'],q,dur);t+=dur;q=3-q
        series.append((case['name'],curve,('#b33b32','#246ca1','#23835f')[idx],('','7 4','2 4')[idx]))
    summary={'thermal_first_event_s':events[0][1],'thermal_dwell_s':dwell,'thermal_period_s':2*dwell,
             'thermal_events_count':len(events),'root_vs_log_max_error_s':max(root_errors),
             'switch_rho_c4_s1':rho,'switch_rho_c4_s2':math.exp(-4)*(33+8*math.sqrt(17)),
             'P_eigen_min':small,'P_eigen_max':large,'dwell_sufficient_bound_normalized':bound,
             'eigenvector_12cycles_scaled_error':max(eigen_errors),'rk4_two_segment_errors_10_20_40':refinement,
             'scope':'Finite deterministic checks only; general guarantees are proved in lesson 13.'}
    assert time.monotonic()-start<60
    out.mkdir(parents=True)
    for filename,header,data in [('thermal.csv',('t_s','x_K','q','u_W','P_W'),rows),('events.csv',('j','t_s','x_K','q_before','q_after'),events),('switching.csv',('case','tau','mode','z1','z2','norm2'),swrows)]:
        with (out/filename).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(data)
    ylim=1.2*delta
    plot(out/'thermostat.svg','Thermostat: continuous temperature, discrete mode',f'C={C:g} J/K; h={h:g} W/K; U={U:g} W; delta={delta:g} K; no delay/noise',
         [('x(t), exact event segments',[(r[0],r[1]) for r in rows],'#246ca1','')],'t (s)','x (K)',-ylim,ylim,p['end_s'],(-delta,delta))
    # Add event markers to the existing generated plot, using the same coordinates.
    svg=(out/'thermostat.svg').read_text();dots=''.join(f'<circle cx="{75+690*e[1]/p["end_s"]:.3f}" cy="{350-270*(e[2]+ylim)/(2*ylim):.3f}" r="3" fill="#b33b32"/>' for e in events)
    (out/'thermostat.svg').write_text(svg.replace('</svg>',dots+'</svg>'))
    plot(out/'switching.svg','Stable modes need a switching condition','Normalized z and time; same unit-norm initial state; exact matrix flows',series,'tau (dimensionless)','log10 norm(z) (dimensionless)',-23,12,cfg['switch_end'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    print('PASS: event roots, invariant band, exact Lyapunov identity, unstable product, common bound, RK4 refinement')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'serial':True,'thread_ceiling':4,'configured_numeric_threads':1,'elapsed_s':time.monotonic()-start,'peak_rss_raw':rss,'peak_rss_unit':'bytes' if platform.system()=='Darwin' else 'KiB'}))


if __name__=='__main__':main()
