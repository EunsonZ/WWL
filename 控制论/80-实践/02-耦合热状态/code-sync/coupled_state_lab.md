---
type: reference
stage: 2
aliases: []
sources: []
prerequisites:
  - '[[控制论/80-实践/02-耦合热状态/README]]'
---

# coupled_state_lab 源码镜像

真源为[coupled_state_lab.py](../coupled_state_lab.py)，公式、固定输入与实际输出见[[控制论/80-实践/02-耦合热状态/README|复算说明]]。本块与源码逐字一致。

<!-- code-sync: ../coupled_state_lab.py -->
```python
"""Two-node thermal state-feedback/observer teaching lab, standard library.

Temperature deviations K, power deviations W, time s. Continuous controllers
are numerically integrated; the sampled-state case is explicitly separate.
"""
from __future__ import annotations
import argparse
import cmath
import csv
import json
import math
from pathlib import Path
import platform
import resource

A = [[-.2,.1],[.1,-.2]]
B = [[.1],[0.0]]
H = [[0.0,1.0]]
K = [[4.0,4.0]]
L = [[.9],[.6]]


def add(a,b): return [[x+y for x,y in zip(ar,br)] for ar,br in zip(a,b)]
def scale(a,s): return [[x*s for x in row] for row in a]
def transpose(a): return [list(row) for row in zip(*a)]
def mul(a,b): return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def eye(n): return [[float(i==j) for j in range(n)] for i in range(n)]
def mv(a,x): return [sum(v*w for v,w in zip(row,x)) for row in a]
def det2(a): return a[0][0]*a[1][1]-a[0][1]*a[1][0]
def poles2(a):
    t=a[0][0]+a[1][1]; d=det2(a)
    root=cmath.sqrt(t*t-4*d)
    return [(t+root)/2,(t-root)/2]

def expm(a,t):
    """Small dense scaling/squaring Taylor exponential, for fixed 2/4-D lab."""
    n=len(a)
    bound=abs(t)*max(sum(abs(v) for v in row) for row in a)
    squares=max(0,math.ceil(math.log2(bound))) if bound else 0
    z=scale(a,t/2**squares)
    result=eye(n); term=eye(n)
    for j in range(1,80):
        term=scale(mul(term,z),1/j)
        result=add(result,term)
        if max(abs(v) for row in term for v in row)<1e-17: break
    for _ in range(squares): result=mul(result,result)
    return result

def rk4(f,initial,dt,count):
    x=list(initial); rows=[x[:]]
    for _ in range(count):
        k1=f(x)
        k2=f([v+dt*w/2 for v,w in zip(x,k1)])
        k3=f([v+dt*w/2 for v,w in zip(x,k2)])
        k4=f([v+dt*w for v,w in zip(x,k3)])
        x=[v+dt*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(x,k1,k2,k3,k4)]
        rows.append(x[:])
    return rows

def sampled_plant(dt):
    plus=math.exp(-.1*dt); minus=math.exp(-.3*dt)
    ad=[[.5*(plus+minus),.5*(plus-minus)],
        [.5*(plus-minus),.5*(plus+minus)]]
    jp=-math.expm1(-.1*dt); jm=-math.expm1(-.3*dt)/3
    bd=[[.5*(jp+jm)],[.5*(jp-jm)]]
    return ad,bd

def svg(path,rows,dt):
    def points(index):
        return ' '.join(f'{70+640*k*dt/20:.3f},{95+210*(1.1-row[index])/1.3:.3f}' for k,row in enumerate(rows))
    text=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 380" role="img" aria-labelledby="title desc">',
          '<title id="title">Two-node output feedback: real and estimated temperatures</title>',
          '<desc id="desc">Continuous ideal controller, C=10 J/K each, h=kappa=1 W/K, K=[4,4] W/K, L=[0.9,0.6] per s. Initial x=[1,0] K, estimate=[0,0] K, no noise, no saturation. RK4 dt=0.05 s. Solid real x1, dashed estimated x1, dotted real x2. time in s and temperature deviations in K.</desc>',
          '<rect width="100%" height="100%" fill="white"/>',
          '<text x="70" y="24" font-size="17">Output feedback: one measured node, two states</text>',
          '<text x="70" y="45" font-size="12">solid x1; dashed estimate x1; dotted x2</text>',
          '<text x="10" y="75" font-size="14">x [K]</text>']
    for t in (0,5,10,15,20):
        px=70+640*t/20
        text.extend([f'<path d="M {px} 95 v 210" stroke="#ddd"/>',f'<text x="{px}" y="330" font-size="13" text-anchor="middle">{t}</text>'])
    for y in (-.2,0,.5,1):
        py=95+210*(1.1-y)/1.3
        text.extend([f'<path d="M 70 {py} h 640" stroke="#ddd"/>',f'<text x="60" y="{py+4}" font-size="13" text-anchor="end">{y}</text>'])
    for i,color,dash in ((0,'#222',''),(2,'#1767a2','8 4'),(1,'#ab4f00','2 3')):
        text.append(f'<polyline points="{points(i)}" fill="none" stroke="{color}" stroke-dasharray="{dash}" stroke-width="2"/>')
    text.extend(['<text x="380" y="365" font-size="14">time t [s]</text>','</svg>'])
    path.write_text('\n'.join(text)+'\n')

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    f=add(A,scale(mul(B,K),-1))
    e=add(A,scale(mul(L,H),-1))
    bk=mul(B,K)
    augmented=[f[0]+bk[0],f[1]+bk[1],[0,0]+e[0],[0,0]+e[1]]
    controllability=[[.1,-.02],[0,.01]]
    observability=[[0,1],[.1,-.2]]
    assert abs(det2(controllability)-.001)<1e-15
    assert abs(det2(observability)+.1)<1e-15
    assert sorted(round(p.real,10) for p in poles2(f))==[-.5,-.3]
    assert sorted(round(p.real,10) for p in poles2(e))==[-.6,-.4]
    # Integrate physical x/estimate coordinates, independently of block matrix.
    def output_feedback(state,bias=0):
        x=state[:2]; hat=state[2:]
        u=-sum(g*v for g,v in zip(K[0],hat))
        innovation=x[1]+bias-hat[1]
        return [sum(v*w for v,w in zip(row,x))+b[0]*u for row,b in zip(A,B)]+[
            sum(v*w for v,w in zip(row,hat))+b[0]*u+l[0]*innovation for row,b,l in zip(A,B,L)]
    errors=[]
    for dt in (.2,.1,.05):
        rows=rk4(output_feedback,[1,0,0,0],dt,round(20/dt))
        # Initial [x,e]=[1,0,1,0].
        z=mv(expm(augmented,20),[1,0,1,0])
        expected=z[:2]+[z[i]-z[i+2] for i in range(2)]
        errors.append(max(abs(v-w) for v,w in zip(rows[-1],expected)))
    assert errors[-1]<1e-9 and errors[-1]<errors[0]
    rows=rk4(output_feedback,[1,0,0,0],.05,400)
    biased=rk4(lambda state:output_feedback(state,.1),[0,0,0,0],.05,2000)
    assert abs(biased[-1][0]+.1)<1e-9 and abs(biased[-1][1]+.05)<1e-9
    # Full-state nominal reference r=.5 K, no estimator: independent 2-state RK4.
    def tracking(x):
        u=7.5-4*(x[0]+x[1])
        return [sum(v*w for v,w in zip(row,x))+b[0]*u for row,b in zip(A,B)]
    tracking_rows=rk4(tracking,[0,0],.05,400)
    tracking_error=max(max(abs(x[0]-(1+1.25*math.exp(-.3*k*.05)-2.25*math.exp(-.5*k*.05))),
                           abs(x[1]-(.5-1.25*math.exp(-.3*k*.05)+.75*math.exp(-.5*k*.05))))
                       for k,x in enumerate(tracking_rows))
    assert tracking_error<1e-8
    ad,bd=sampled_plant(1)
    digital=add(ad,scale(mul(bd,K),-1))
    digital6=add(sampled_plant(6)[0],scale(mul(sampled_plant(6)[1],K),-1))
    held_errors=[]
    expected_hold=[v+2.3*b[0] for v,b in zip(mv(ad,[.7,-.2]),bd)]
    for n in (1,2,4,8):
        held=rk4(lambda x:[sum(v*w for v,w in zip(row,x))+b[0]*2.3 for row,b in zip(A,B)], [.7,-.2],1/n,n)
        held_errors.append(max(abs(v-w) for v,w in zip(held[-1],expected_hold)))
    assert held_errors[-1]<1e-8 and all(held_errors[i+1]<held_errors[i] for i in range(3))
    d=[[0,1],[0,0]]; gain=[[0,0],[1,0]]
    result={'environment':{'python':platform.python_version(),'platform':platform.platform(),
                           'max_rss_raw':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
            'A_per_s':A,'B_K_per_Ws':B,'H':H,'K_W_per_K':K,'L_per_s':L,
            'rank_R_det':det2(controllability),'rank_O_det':det2(observability),
            'feedback_poles_per_s':[p.real for p in poles2(f)],
            'observer_poles_per_s':[p.real for p in poles2(e)],
            'output_feedback_augmented_per_s':augmented,
            'RK4_vs_expm_error_K_dt_0p2_0p1_0p05':errors,
            'tracking_RK4_vs_closed_form_max_error_K':tracking_error,
            'tracking_r_K':.5,'tracking_equilibrium_x_K':[1,.5],
            'tracking_equilibrium_u_W':1.5,'tracking_initial_u_W':7.5,
            'biased_observer_final_x_K':biased[-1][:2],
            'biased_observer_final_estimate_K':biased[-1][2:],
            'Ad_Ts1':ad,'Bd_Ts1_K_per_W':bd,
            'RK4_held_plant_errors_K_n_1_2_4_8':held_errors,
            'digital_feedback_poles_Ts1':[p.real for p in poles2(digital)],
            'digital_feedback_poles_Ts6':[p.real for p in poles2(digital6)],
            'digital_feedback_Ts_upper_bound_s':10*math.log(5/3),
            'matrix_order_DK':mul(d,gain),'matrix_order_KD':mul(gain,d)}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    with (out/'observer.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['t_s','x1_K','x2_K','hat_x1_K','hat_x2_K','command_u_W'])
        for k,state in enumerate(rows): writer.writerow([k*.05]+state+[-4*(state[2]+state[3])])
    svg(out/'observer.svg',rows,.05)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    run(parser.parse_args().output_dir)
```
