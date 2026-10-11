---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# 网络更新与固定时延的规范代码镜像

返回 [[控制论/80-实践/05-混杂与网络/README|输入、输出与边界]]。源码加载同目录hybrid_lab.py仅复用SVG绘图函数，不运行该程序main。

<!-- code-sync: 控制论/80-实践/05-混杂与网络/network_lab.py -->

```python
#!/usr/bin/env python3
"""Finite serial ideal-network teaching model; no sockets or physical output."""
import os
for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'  # below task ceiling 4; no workers
import argparse
import cmath
import csv
import itertools
import json
import math
import platform
import resource
import runpy
import time
from fractions import Fraction as F
from pathlib import Path

# Shared SVG writer only. Its main does not run; numerical models below are separate.
plot=runpy.run_path(str(Path(__file__).with_name('hybrid_lab.py')))['plot']


def rk4_scalar(x,u,h,C,loss):
    def f(v):return (-loss*v+u)/C
    a=f(x);b=f(x+h*a/2);c=f(x+h*b/2);d=f(x+h*c)
    return x+h*(a+2*b+2*c+d)/6


def main():
    start=time.monotonic();parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();out=args.output_dir
    if out.exists():raise SystemExit('Output directory must be new; refusing overwrite')
    p=json.loads(Path(__file__).with_name('network-input.json').read_text())
    C=p['C_J_per_K'];loss=p['h_W_per_K'];K=p['K_W_per_K'];kap=K/loss
    a=F(p['a_numerator'],p['a_denominator']);T=-C/loss*math.log(float(a))
    assert C==10 and loss==1 and K==4 and a==F(9,10)
    assert 0<abs(p['x0_K'])<=2.5 and p['delay_steps']<=100
    for seq in p['sequences'].values():assert 1<=len(seq)<=20 and all(type(m)==int and 1<=m<=5 for m in seq)
    factors={m:5*a**m-4 for m in range(1,6)};rho=max(abs(factors[m]) for m in range(1,5))
    assert [factors[m] for m in range(1,6)]==[F(1,2),F(1,20),F(-71,200),F(-1439,2000),F(-20951,20000)]
    enum=[]
    for seq in itertools.product(range(1,5),repeat=4):
        x=F(1);product=F(1)
        for m in seq:
            u=-4*x
            for _ in range(m):x=a*x+(1-a)*u
            product*=factors[m]
            assert x==product
        assert abs(x)<=rho**4
        enum.append(('-'.join(map(str,seq)),str(x),str(rho**4)))
    rows=[];series=[];factor_error=0.;intersample_ratio=0.
    for idx,(name,seq) in enumerate(p['sequences'].items()):
        x=p['x0_K'];t=0.;curve=[]
        for j,m in enumerate(seq):
            u=-K*x;H=m*T
            for i in range(21):
                theta=H*i/20;v=math.exp(-loss*theta/C)*x+(1-math.exp(-loss*theta/C))*u/loss
                rows.append((name,j,t+theta,m,x,v,u,theta))
                curve.append((t+theta,v))
                if m<=4:
                    assert abs(v)<=abs(x)+1e-13
                    intersample_ratio=max(intersample_ratio,abs(v/x))
            end=math.exp(-loss*H/C)*x+(1-math.exp(-loss*H/C))*u/loss
            factor_error=max(factor_error,abs(end-float(factors[m])*x));x=end;t+=H
        if name!='mixed':series.append((name,curve,('#246ca1','#b33b32')[idx],('','7 4')[idx]))
    assert factor_error<1e-12
    # Fixed delay: compare augmented map against two independent held-input flows.
    da=p['delay_a'];DT=-C/loss*math.log(da);delay_rows=[];roots={};map_error=0.;delay_series=[]
    def held(x,u,t):return math.exp(-loss*t/C)*x+(1-math.exp(-loss*t/C))*u/loss
    for idx,frac in enumerate(p['delay_fractions']):
        assert 0<=frac<=1
        d=frac*DT;E=math.exp(-loss*(DT-d)/C)
        g00=da-kap*(1-E);g01=E-da;trace=g00;det=kap*g01
        root=cmath.sqrt(trace*trace-4*det)
        eigen=((trace+root)/2,(trace-root)/2)
        roots[str(frac)]={'trace':trace,'det':det,'root_moduli':[abs(v) for v in eigen],
                          'schur':[1-trace+det,1+trace+det,1-det]}
        x=p['x0_K'];old=-K*x;curve=[(0.,x)]
        for k in range(p['delay_steps']):
            new=-K*x
            next_two=held(held(x,old,d),new,DT-d)
            next_matrix=g00*x+g01*old/loss
            map_error=max(map_error,abs(next_two-next_matrix))
            delay_rows.append((frac,k,k*DT,x,old,new,next_two))
            x=next_two;old=new;curve.append(((k+1)*DT,x))
        delay_series.append((f'd/T={frac:g}',curve,('#246ca1','#23835f','#b33b32')[idx],('','2 4','7 4')[idx]))
    assert map_error<1e-12
    assert roots['0']['root_moduli'][0]<1 and max(roots['1']['root_moduli'])>1
    # Independent RK4 checks for fractional delay, exact event split at d=T/2.
    errors=[];d=DT/2;x0=p['x0_K'];old=1.25;new=-K*x0
    oracle=held(held(x0,old,d),new,DT-d)
    for n in (4,8,16):
        x=x0
        for u,dur in ((old,d),(new,DT-d)):
            for _ in range(n):x=rk4_scalar(x,u,dur/n,C,loss)
        errors.append(abs(x-oracle))
    assert errors[2]<errors[1]<errors[0] and errors[-1]<1e-9
    # A five-packet ordering fixture. Grouping by arrival time defines simultaneous handling.
    packets=sorted(p['packets'],key=lambda q:(q['arrival_s'],q['seq']))
    known={};packet_rows=[];accepted=[];current=-1
    for arrival,group in itertools.groupby(packets,key=lambda q:q['arrival_s']):
        batch=list(group)
        for msg in batch:
            assert isinstance(msg['seq'],int) and msg['seq']>=0
            assert 0<=msg['sample_s']<=arrival<=100 and math.isfinite(msg['sample_K'])
            payload=(msg['sample_s'],msg['sample_K'])
            if msg['seq'] in known:assert known[msg['seq']]==payload,'conflicting duplicate'
            known[msg['seq']]=payload
        latest=max(batch,key=lambda q:q['seq'])
        for msg in batch:
            ok=msg is latest and msg['seq']>current
            packet_rows.append((msg['seq'],msg['sample_s'],arrival,arrival-msg['sample_s'],ok,-K*msg['sample_K']))
        if latest['seq']>current:current=latest['seq'];accepted.append(current)
    assert accepted==[0,2,3]
    summary={'Ts_s':T,'allowed_gap_factors':{str(m):str(factors[m]) for m in range(1,6)},
             'rho_1_to_4':str(rho),'physical_decay_rate_per_s':-math.log(float(rho))/(4*T),
             'finite_sequences_checked':len(enum),'finite_sequence_length':4,'held_vs_factor_max_error_K':factor_error,
             'sampled_intersample_ratio_max':intersample_ratio,
             'delay_T_s':DT,'delay_stable_d_upper_s':DT+C/loss*math.log(.95),'delay_roots':roots,
             'two_flow_vs_augmented_max_error_K':map_error,'delay_rk4_errors_4_8_16':errors,
             'packet_accepted_sequences':accepted,
             'scope':'Exact finite checks; zero-delay fresh-success theorem and fixed-delay theorem are separate.'}
    assert time.monotonic()-start<60
    out.mkdir(parents=True)
    for filename,header,data in [('updates.csv',('case','success_j','t_s','gap_slots','X_j_K','x_t_K','held_u_W','age_s'),rows),
                                 ('enumeration.csv',('four_gap_sequence','final_exact_X','exact_rho_power4'),enum),
                                 ('delay.csv',('d_over_T','k','t_s','x_K','old_u_W','new_u_W','next_x_K'),delay_rows),
                                 ('packets.csv',('seq','sample_s','arrival_s','age_s','accepted','candidate_u_W'),packet_rows)]:
        with (out/filename).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(data)
    plot(out/'updates.svg','Fresh successes: four slots versus five','Thermal C=10 J/K; h=1 W/K; K=4 W/K; x0=0.5 K; held commands',series,'t (s)','x (K)',-1.,1.,60*T)
    lim=max(abs(row[3]) for row in delay_rows)+1
    plot(out/'delay.svg','Reliable sampling, fixed command delay','T=10 ln(10/7) s; K=4 W/K; old input is part of the state',delay_series,'t (s)','x at sample (K)',-lim,lim,DT*p['delay_steps'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    print('PASS: exact gap factors, 256 finite sequences, held flow, fixed-delay augmentation, RK4 refinement, packet ordering')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'python':platform.python_version(),'platform':platform.platform(),'serial':True,'thread_ceiling':4,'configured_numeric_threads':1,'elapsed_s':time.monotonic()-start,'peak_rss_raw':rss,'peak_rss_unit':'bytes' if platform.system()=='Darwin' else 'KiB'}))


if __name__=='__main__':main()
```
