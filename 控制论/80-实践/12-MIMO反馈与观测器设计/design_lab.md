---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# MIMO 设计程序镜像

规范源码见 [design_lab.py](design_lab.py)，此页只保留同字节镜像。

<!-- code-sync: 控制论/80-实践/12-MIMO反馈与观测器设计/design_lab.py -->

```python
#!/usr/bin/env python3
"""Finite continuous LTI MIMO CARE feedback and dual-CARE observer design."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import numpy as np
from scipy.linalg import solve_continuous_are, expm


def number(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)):raise ValueError('Expected finite number')
    try:v=float(v)
    except OverflowError as e:raise ValueError('Numeric overflow') from e
    if not math.isfinite(v):raise ValueError('Nonfinite number')
    return v


def matrix(v,rows,cols,budget=1000):
    if not isinstance(v,list) or len(v)!=rows or any(not isinstance(r,list) or len(r)!=cols for r in v):
        raise ValueError('Incorrect matrix shape')
    a=np.array([[number(x) for x in r] for r in v],float)
    if np.max(np.abs(a))>budget:raise ValueError('Matrix budget exceeded')
    return a


def vector(v,n,positive=False):
    if not isinstance(v,list) or len(v)!=n:raise ValueError('Incorrect vector shape')
    a=np.array([number(x) for x in v])
    if np.max(np.abs(a))>1000 or (positive and np.min(a)<1e-3):raise ValueError('Vector/scale budget exceeded')
    return a


def pd(a):
    if np.linalg.norm(a-a.T,'fro')>1e-12*max(1.,np.linalg.norm(a,'fro')):raise ValueError('Weight must be symmetric')
    values=np.linalg.eigvalsh(a)
    if values[0]<1e-8 or values[-1]/values[0]>1e6:raise ValueError('Require positive definite, well-scaled weights')


def load_card(path):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    card=json.loads(Path(path).read_text(),object_pairs_hook=unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if not isinstance(card,dict) or set(card)!={'schema','time_scale_s','horizon_tau','output_dt_tau','cases'}:
        raise ValueError('Unexpected card shape or fields')
    if card['schema']!='wwl-mimo-care-1':raise ValueError('Wrong schema')
    t0,horizon,dt=map(number,[card['time_scale_s'],card['horizon_tau'],card['output_dt_tau']])
    if not .1<=t0<=10 or not .1<=horizon<=30 or not .005<=dt<=.2:raise ValueError('Time budget exceeded')
    steps=round(horizon/dt)
    if steps>6000 or abs(steps*dt-horizon)>1e-9:raise ValueError('Horizon must align with output spacing')
    if not isinstance(card['cases'],list) or not 1<=len(card['cases'])<=8:raise ValueError('Require 1..8 cases')
    names=set()
    for c in card['cases']:
        keys={'name','A','B','C','D','Q','R','W','V','x0','hat0','state_scale','input_scale','output_scale'}
        if not isinstance(c,dict) or set(c)!=keys:raise ValueError('Unexpected case fields')
        if not isinstance(c['name'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,35}',c['name']) or c['name'] in names:
            raise ValueError('Case names must be distinct safe identifiers')
        names.add(c['name'])
        if not isinstance(c['A'],list):raise ValueError('A must be a square array')
        n=len(c['A'])
        if not 2<=n<=6 or not isinstance(c['B'],list) or not c['B'] or not isinstance(c['B'][0],list):
            raise ValueError('Executable n budget 2..6')
        m=len(c['B'][0]);p=len(c['C']) if isinstance(c['C'],list) else 0
        if not 1<=m<=4 or not 1<=p<=4:raise ValueError('Port budget 1..4')
        for k,r,s in [('A',n,n),('B',n,m),('C',p,n),('D',p,m)]:matrix(c[k],r,s,20)
        for k,r in [('Q',n),('R',m),('W',n),('V',p)]:pd(matrix(c[k],r,r))
        for k,r,positive in [('x0',n,False),('hat0',n,False),('state_scale',n,True),('input_scale',m,True),('output_scale',p,True)]:
            vector(c[k],r,positive)
    return card


def rank(a):
    s=np.linalg.svd(a,compute_uv=False)
    return int(np.sum(s>1e-8*max(1.,s[0])))


def pbh(a,b,c):
    n=len(a);checks=[]
    for lam in np.linalg.eigvals(a):
        if lam.real < -1e-9:continue
        controllable=rank(np.hstack([lam*np.eye(n)-a,b]))==n
        observable=rank(np.vstack([lam*np.eye(n)-a,c]))==n
        checks.append({'lambda':[float(lam.real),float(lam.imag)],'control_full_rank':controllable,'observation_full_rank':observable})
    return {'stabilizable_numerical':all(v['control_full_rank'] for v in checks),
            'detectable_numerical':all(v['observation_full_rank'] for v in checks),
            'unstable_pbh_checks':checks,
            'controllability_rank_numerical':rank(np.hstack([np.linalg.matrix_power(a,i)@b for i in range(n)])),
            'observability_rank_numerical':rank(np.vstack([c@np.linalg.matrix_power(a,i) for i in range(n)])),
            'rank_relative_tolerance':1e-8,'closed_half_plane_tolerance':1e-9}


def poles(a):
    return [[float(v.real),float(v.imag)] for v in sorted(np.linalg.eigvals(a),key=lambda z:(z.real,z.imag))]


def design(a,b,c,q,r,w,v):
    """General positive-definite-weight algorithm; numerical candidates, not intervals."""
    P=solve_continuous_are(a,b,q,r)
    S=solve_continuous_are(a.T,c.T,w,v)
    K=np.linalg.solve(r,b.T@P)
    L=np.linalg.solve(v,c@S).T
    F=a-b@K;E=a-L@c
    resP=a.T@P+P@a-P@b@K+q
    resS=a@S+S@a.T-L@c@S+w
    relP=np.linalg.norm(resP,'fro')/(1+np.linalg.norm(a.T@P,'fro')+np.linalg.norm(P@a,'fro')+np.linalg.norm(P@b@K,'fro')+np.linalg.norm(q,'fro'))
    relS=np.linalg.norm(resS,'fro')/(1+np.linalg.norm(a@S,'fro')+np.linalg.norm(S@a.T,'fro')+np.linalg.norm(L@c@S,'fro')+np.linalg.norm(w,'fro'))
    for X in [P,S]:
        if not np.all(np.isfinite(X)) or np.linalg.norm(X-X.T,'fro')>1e-9 or np.linalg.eigvalsh(X)[0]<=0:
            raise ValueError('CARE did not produce a positive definite symmetric candidate')
    if max(relP,relS)>1e-9 or max(np.linalg.eigvals(F).real)>=-1e-9 or max(np.linalg.eigvals(E).real)>=-1e-9:
        raise ValueError('CARE residual or stabilizing-branch acceptance failed')
    n=len(a);M=np.block([[a,-b@K],[L@c,a-b@K-L@c]])
    T=np.block([[np.eye(n),np.zeros((n,n))],[np.eye(n),-np.eye(n)]])
    ME=np.block([[F,b@K],[np.zeros((n,n)),E]])
    info={'P':P.tolist(),'S':S.tolist(),'K':K.tolist(),'L':L.tolist(),'state_feedback_matrix':F.tolist(),
          'observer_error_matrix':E.tolist(),'physical_state_closed_loop':M.tolist(),'error_state_closed_loop':ME.tolist(),
          'care_P_residual_fro':float(np.linalg.norm(resP,'fro')),'care_S_residual_fro':float(np.linalg.norm(resS,'fro')),
          'care_P_relative_residual':float(relP),'care_S_relative_residual':float(relS),
          'P_min_eigenvalue':float(np.linalg.eigvalsh(P)[0]),'S_min_eigenvalue':float(np.linalg.eigvalsh(S)[0]),
          'feedback_lyapunov_identity_residual':float(np.linalg.norm(F.T@P+P@F+q+K.T@r@K,'fro')),
          'observer_lyapunov_identity_residual':float(np.linalg.norm(E@S+S@E.T+w+L@v@L.T,'fro')),
          'separation_transform_residual':float(np.linalg.norm(T@M@T-ME,'fro')),
          'open_loop_poles':poles(a),'feedback_poles':poles(F),'observer_poles':poles(E),'complete_poles':poles(M)}
    return K,L,M,info


def solve_case(c,card):
    a,b,C,D=[np.array(c[k],float) for k in ['A','B','C','D']]
    n,m,p=len(a),b.shape[1],C.shape[0]
    q,r,w,v=[np.array(c[k],float) for k in ['Q','R','W','V']]
    x0,hat0=np.array(c['x0'],float),np.array(c['hat0'],float)
    sx,su,sy=[np.array(c[k],float) for k in ['state_scale','input_scale','output_scale']]
    info={'name':c['name'],'n':n,'m':m,'p':p,**pbh(a,b,C)}
    tau=np.arange(round(card['horizon_tau']/card['output_dt_tau'])+1)*card['output_dt_tau']
    rows=[]
    if not info['stabilizable_numerical'] or not info['detectable_numerical']:
        info['status']='design_declined_by_numerical_pbh';info['open_loop_poles']=poles(a)
        info['trajectory_kind']='zero_input_open_loop_only';info['file']='open_loop_'+c['name']+'.csv'
        header=['tau','time_s']+[f'x_raw{i+1}' for i in range(n)]+[f'y_raw{i+1}' for i in range(p)]+['norm_x_display']
        for t in tau:
            x=expm(a*t)@x0;y=C@x
            rows.append([t,card['time_scale_s']*t,*x,*y,np.linalg.norm(sx*x)])
    else:
        K,L,M,details=design(a,b,C,q,r,w,v);info.update(details)
        info['status']='numerical_stabilizing_design';info['trajectory_kind']='complete_continuous_observer_feedback'
        info['file']=c['name']+'.csv'
        header=['tau','time_s']+[f'x_raw{i+1}' for i in range(n)]+[f'hat_raw{i+1}' for i in range(n)]+[f'e_raw{i+1}' for i in range(n)]+[f'u_raw{i+1}' for i in range(m)]+[f'y_raw{i+1}' for i in range(p)]+[f'innovation{i+1}' for i in range(p)]+['norm_x_display','norm_e_display','norm_u_display']
        for t in tau:
            z=expm(M*t)@np.concatenate([x0,hat0]);x,hat=z[:n],z[n:];e=x-hat
            u=-K@hat;y=C@x+D@u;innovation=y-C@hat-D@u
            rows.append([t,card['time_scale_s']*t,*x,*hat,*e,*u,*y,*innovation,np.linalg.norm(sx*x),np.linalg.norm(sx*e),np.linalg.norm(su*u)])
        info['K_common_coordinates']=(su[:,None]*K/sx[None,:]).tolist()
        info['L_common_coordinates']=(sx[:,None]*L/sy[None,:]).tolist()
        info['max_display_state_norm']=float(max(row[-3] for row in rows))
        info['max_display_error_norm']=float(max(row[-2] for row in rows))
        info['max_display_action_norm']=float(max(row[-1] for row in rows))
        info['final_display_state_norm']=float(rows[-1][-3]);info['final_display_error_norm']=float(rows[-1][-2])
    if not np.all(np.isfinite(np.array(rows,float))):raise ValueError('Nonfinite trajectory; finite numerical budget exceeded')
    return header,rows,info


def run(inputs,out):
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError('Refusing nonempty output')
    card=load_card(inputs);entries=[];infos=[]
    for c in card['cases']:
        header,rows,info=solve_case(c,card);entries.append((info['file'],header,rows));infos.append(info)
    summary={'schema':'wwl-mimo-care-results-1','input_snapshot':card,'cases':infos,
             'numerical_diagnostics_are_interval_certificates':False,
             'observer_weights_are_statistical_covariances':False,
             'output_spacing_is_digital_control_sampling':False}
    out.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.mimo-design-',dir=out.parent))
    try:
        for name,header,rows in entries:
            with (temporary/name).open('w',newline='') as handle:
                writer=csv.writer(handle);writer.writerow(header);writer.writerows(rows)
        (temporary/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        if out.exists():
            if any(out.iterdir()):raise ValueError('Output changed before publication')
            out.rmdir()
        temporary.rename(out)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try: result=run(args.inputs,args.out)
    except (ValueError,OSError,TypeError,np.linalg.LinAlgError) as exc:
        print(f'error: {exc}',file=sys.stderr);sys.exit(2)
    print(json.dumps({'output':str(args.out),'cases':len(result['cases'])}))
```
