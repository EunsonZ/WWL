---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# MIMO鲁棒综合实验源码

返回 [[控制论/80-实践/09-MIMO鲁棒综合/README|复现说明]]。

<!-- code-sync: 控制论/80-实践/09-MIMO鲁棒综合/run_experiment.py -->

```python
#!/usr/bin/env python3
"""Synthesis is numerical; acceptance is exact rational Sylvester testing.
Frequency grids and trajectories are diagnostics, never uncertainty-set proofs.
"""
import argparse, itertools, json, platform, sys, os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".mpl-cache"))
import numpy as np
import scipy
from scipy.integrate import solve_ivp
import sympy as sp
import cvxpy as cp
import clarabel
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def dump(name,obj):
    (ROOT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def rational_matrix(values):
    return sp.Matrix([[sp.Rational(v) for v in row] for row in values])
def serial(M):
    return [[str(v) for v in row] for row in M.tolist()]
def numeric(M):
    return np.array(M,dtype=float)
def exact_pd(M):
    """Sylvester criterion, valid for real symmetric matrices; no tolerance."""
    if M!=M.T: raise ValueError("Exact positivity test requires a symmetric matrix")
    minors=[M[:i,:i].det(method='domain-ge') for i in range(1,M.rows+1)]
    pivots=[minors[0]]+[minors[i]/minors[i-1] if minors[i-1]!=0 else None for i in range(1,len(minors))]
    return {'positive_definite':all(v>0 for v in minors),
            'leading_principal_minors':[str(v) for v in minors],
            'ldl_pivots':[str(v) if v is not None else None for v in pivots],
            'minimum_ldl_pivot_numeric':min(float(v) for v in pivots if v is not None)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--verify-only',action='store_true');args=p.parse_args()
    versions={'python':sys.version,'platform':platform.platform(),**{m.__name__:m.__version__ for m in [np,scipy,sp,cp,clarabel,matplotlib]}}
    if args.preflight:
        print(json.dumps({'versions':versions,'solvers':cp.installed_solvers(),'exact_test':exact_pd(sp.Matrix([[2,1],[1,2]]))},indent=2));return
    inp=json.loads((ROOT/'inputs.json').read_text())
    if inp.get('theta_box') != [[-1,1],[-1,1]]: raise ValueError('Only theta_box=[[-1,1],[-1,1]] is supported')
    if inp.get('dimensions') != {'x':2,'w':2,'u':2,'z':4}: raise ValueError('Only dimensions x=2,w=2,u=2,z=4 are supported')
    shapes={'A0':(2,2),'A1':(2,2),'A2':(2,2),'B1':(2,2),'B2':(2,2),'Cz':(4,2),'Dzu':(4,2),'Dzw':(4,2)}
    mats={}
    for key,shape in shapes.items():
        values=inp.get(key)
        if not isinstance(values,list) or len(values)!=shape[0] or any(not isinstance(row,list) or len(row)!=shape[1] for row in values): raise ValueError(f'{key}: invalid matrix shape')
        M=rational_matrix(values)
        if any(v.is_finite is not True for v in M): raise ValueError(f'{key}: entries must be finite rational numbers')
        if not np.isfinite(numeric(M)).all(): raise ValueError(f'{key}: entries exceed finite floating range')
        mats[key]=M
    if mats['Dzw']!=sp.zeros(4,2): raise ValueError('Nonzero Dzw is unsupported by this fixed zero-feedthrough BRL')
    for key in ['solver_delta','exact_margin','synthesis_X_lower_bound']:
        if isinstance(inp[key],bool): raise ValueError(f'{key} must be a positive finite number, not bool')
        value=sp.Rational(inp[key])
        if value.is_finite is not True or value<=0 or not np.isfinite(float(value)): raise ValueError(f'{key} must be positive and finite')
    inp['solver_delta']=float(sp.Rational(inp['solver_delta']))
    den=inp.get('rational_denominator')
    if isinstance(den,bool) or not isinstance(den,int) or den<=0: raise ValueError('rational_denominator must be a positive integer')
    # Human-readable units/performance fields are labels; Cz/Dzu/B1 are authoritative.

    A0,A1,A2,B1,B2,C,D=[mats[k] for k in ['A0','A1','A2','B1','B2','Cz','Dzu']]
    vertices=list(itertools.product([-1,1],repeat=2))
    def exact_M(t,X,Y,eta):
        A=A0+t[0]*A1+t[1]*A2;F=A*X+B2*Y;H=C*X+D*Y
        return (F+F.T).row_join(B1).row_join(H.T).col_join(B1.T.row_join(-eta*sp.eye(2)).row_join(sp.zeros(2,4))).col_join(H.row_join(sp.zeros(4,2)).row_join(-sp.eye(4)))
    if args.verify_only:
        cert=json.loads((ROOT/'certificate.json').read_text())
        if cert.get('schema')!='wwl-mimo-hinf-rational-v1': raise ValueError('Unknown certificate schema')
        X=rational_matrix(cert['X']);Y=rational_matrix(cert['Y']);eta=sp.Rational(cert['eta'])
        if X.shape!=(2,2) or Y.shape!=(2,2) or X!=X.T: raise ValueError('Invalid certificate X/Y shape or X symmetry')
        if any(v.is_finite is not True for v in list(X)+list(Y)+[eta]) or eta<=0: raise ValueError('Certificate entries must be finite and eta positive')
        if rational_matrix(cert['P'])!=X.inv() or rational_matrix(cert['K'])!=Y*X.inv(): raise ValueError('Stored P/K differs from exact X/Y reconstruction')
    else:
        xv=cp.Variable((2,2),symmetric=True);yv=cp.Variable((2,2));ev=cp.Variable(nonneg=True);constraints=[xv >> float(sp.Rational(inp.get('synthesis_X_lower_bound',str(inp['solver_delta']))))*np.eye(2)]
        for t in vertices:
            A=numeric(A0+t[0]*A1+t[1]*A2);F=A@xv+numeric(B2)@yv;H=numeric(C)@xv+numeric(D)@yv
            M=cp.bmat([[F+F.T,numeric(B1),H.T],[numeric(B1).T,-ev*np.eye(2),np.zeros((2,4))],[H,np.zeros((4,2)),-np.eye(4)]])
            constraints.append(M << -inp['solver_delta']*np.eye(8))
        prob=cp.Problem(cp.Minimize(ev),constraints);prob.solve(solver='CLARABEL',tol_gap_abs=1e-9,tol_feas=1e-9,tol_gap_rel=1e-9,max_iter=200)
        if xv.value is None or yv.value is None or ev.value is None:raise RuntimeError('No numerical candidate; no certificate accepted')
        den=inp['rational_denominator'];X=sp.Matrix([[sp.Rational(round(float(v)*den),den) for v in row] for row in xv.value]);Y=sp.Matrix([[sp.Rational(round(float(v)*den),den) for v in row] for row in yv.value])
        eta=sp.Rational(round((float(ev.value)*1.03+.005)*den),den)
        dump('solver_output.json',{'status_diagnostic_only':prob.status,'eta_numerical_optimum':float(ev.value),'X_numerical':xv.value.tolist(),'Y_numerical':yv.value.tolist(),'iterations':prob.solver_stats.num_iters,'solve_time_s':prob.solver_stats.solve_time,'versions':versions})
    eps=sp.Rational(inp['exact_margin']);rounded_X=X
    repair_steps=0
    # Bounded rational rounding repair: no change is accepted without ALL exact checks.
    for repair_steps in range(1 if args.verify_only else 11):
        if not args.verify_only: X=rounded_X+sp.Rational(repair_steps,den)*sp.eye(2)
        checks={'X':exact_pd(X),'X_minus_margin_I':exact_pd(X-eps*sp.eye(2)), 'X_minus_design_bound_I':exact_pd(X-sp.Rational(inp['synthesis_X_lower_bound'])*sp.eye(2)), 'vertices':[]}
        for t in vertices:
            M=exact_M(t,X,Y,eta)
            checks['vertices'].append({'theta':list(t),'negative_M':exact_pd(-M),'negative_M_minus_margin_I':exact_pd(-M-eps*sp.eye(8)),'largest_M_eigenvalue_diagnostic':float(np.linalg.eigvalsh(numeric(M))[-1])})
        passed=checks['X_minus_margin_I']['positive_definite'] and checks['X_minus_design_bound_I']['positive_definite'] and all(v['negative_M_minus_margin_I']['positive_definite'] for v in checks['vertices'])
        if passed: break
    if not passed:raise RuntimeError('Rational certificate failed; reject candidate')
    K=Y*X.inv();P=X.inv()
    cert={'schema':'wwl-mimo-hinf-rational-v1','X':serial(X),'Y':serial(Y),'P':serial(P),'K':serial(K),'eta':str(eta),'X_diagonal_rounding_adjustment':str(sp.Rational(repair_steps,inp['rational_denominator'])) if not args.verify_only else cert.get('X_diagonal_rounding_adjustment','unknown'),'gamma_numeric':float(sp.sqrt(eta)),'exact_margin':str(eps),'exact_checks':checks,'accepted':passed,'acceptance':'Exact rational Sylvester criterion on X-epsilon I and -M_v-epsilon I at all four vertices; convex-affine extension requires the stated plant model.'}
    if args.verify_only:
        print(json.dumps({'verify_only':True,'accepted':passed,'eta':str(eta),'gamma_numeric':float(sp.sqrt(eta))},indent=2));return
    # Out-of-box test: same rational certificate; failed certificate is not proof of unstable plant.
    failures=[]
    for t in [(2,2),(5,5),(10,10),(-5,-5)]:
        result=exact_pd(-exact_M(t,X,Y,eta));eig=np.linalg.eigvalsh(numeric(exact_M(t,X,Y,eta)))
        if not result['positive_definite']:failures.append({'theta':list(t),'negative_M':result,'largest_M_eigenvalue_diagnostic':float(eig[-1]),'meaning':'This certificate fails outside the authorized uncertainty box; performance or stability is not decided by this failure.'})
    cert['outside_box_failures']=failures;dump('certificate.json',cert)
    kn=numeric(K);pn=numeric(P);b2=numeric(B2);h=numeric(C)+numeric(D)@kn
    omegas=np.r_[0.,np.logspace(-3,3,401)];curve=np.zeros(len(omegas));peak={'sigma':0.}
    for t in itertools.product(np.linspace(-1,1,7),repeat=2):
        acl=numeric(A0+t[0]*A1+t[1]*A2)+b2@kn
        for j,w in enumerate(omegas):
            T=h@np.linalg.solve(1j*w*np.eye(2)-acl,numeric(B1));sigma=float(np.linalg.svd(T,compute_uv=False)[0]);curve[j]=max(curve[j],sigma)
            if sigma>peak['sigma']:peak={'sigma':sigma,'theta':list(t),'omega':float(w)}
    def disturbance(t):return np.array([np.exp(-t)*np.sin(2*t),np.exp(-t)*np.cos(3*t)])
    rows=[];scenario_results=[];fig,axes=plt.subplots(2,2,figsize=(10,7))
    for name,x0,factor in [('zero_x0',np.zeros(2),1.),('nonzero_x0',np.array([1.,-.5]),1.),('high_gain',np.zeros(2),3.)]:
        k=factor*kn
        def rhs(t,q):
            th=(np.sin(.7*t),np.cos(1.1*t));A=numeric(A0+th[0]*A1+th[1]*A2);x=q[:2];w=disturbance(t);u=k@x
            z=numeric(C)@x+numeric(D)@u
            return np.r_[A@x+b2@u+numeric(B1)@w,w@w,z@z,x@x,u@u]
        ts=np.linspace(0,12,1201);sol=solve_ivp(rhs,(0,12),np.r_[x0,0.,0.,0.,0.],t_eval=ts,rtol=1e-9,atol=1e-11)
        if not sol.success:raise RuntimeError(sol.message)
        q=sol.y;v0=float(x0@pn@x0);vt=float(q[:2,-1]@pn@q[:2,-1]);budget=float(eta)*q[2,-1]+v0
        scenario_results.append({'name':name,'gain_multiplier':factor,'x0':x0.tolist(),'t_end':12.,'Ew':float(q[2,-1]),'Ez':float(q[3,-1]),'Ex':float(q[4,-1]),'Eu':float(q[5,-1]),'V0':v0,'V_end':vt,'eta_Ew_plus_V0':budget,'dissipation_slack':float(budget-q[3,-1]-vt),'certificate_applies_to_gain':factor==1.})
        for j,t in enumerate(ts):rows.append([name,t,*q[:,j],*disturbance(t)])
        if name != 'nonzero_x0':
            style='--' if name=='high_gain' else '-'
            axes[0,0].plot(ts,np.linalg.norm(q[:2],axis=0),label=name,ls=style);axes[0,1].plot(ts,np.linalg.norm(k@q[:2],axis=0),label=name,ls=style)
            axes[1,0].plot(ts,q[3],label=name,ls=style);axes[1,1].plot(ts,q[5],label=name,ls=style)
        else:
            bf,ba=plt.subplots(figsize=(7,4))
            storage=np.einsum('it,ij,jt->t',q[:2],pn,q[:2])
            ba.plot(ts,q[3]+storage,label='Ez(t) + V(x(t))')
            ba.plot(ts,float(eta)*q[2]+v0,ls='--',label='eta Ew(t) + V(x0)')
            ba.set(xlabel='normalized time tau',ylabel='nonzero initial-state energy budget');ba.legend();ba.grid();bf.tight_layout();bf.savefig(ROOT/'initial_storage_diagnostic.png',dpi=150);plt.close(bf)
    for ax,label in zip(axes.flat,['state norm','control norm','accumulated z energy','accumulated u energy']):ax.set(xlabel='normalized time tau',ylabel=label);ax.grid();ax.legend()
    fig.tight_layout();fig.savefig(ROOT/'scenario_diagnostics.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4));ax.semilogx(omegas[1:],curve[1:],label='finite 7 x 7 parameter-grid envelope');ax.axhline(float(sp.sqrt(eta)),color='red',ls='--',label='exact certificate gamma');ax.set(xlabel='normalized angular frequency',ylabel='largest singular value');ax.legend();ax.grid();fig.tight_layout();fig.savefig(ROOT/'frequency_diagnostics.png',dpi=150);plt.close(fig)
    import csv
    with (ROOT/'trajectories.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['scenario','tau','x1','x2','Ew','Ez','Ex','Eu','w1','w2']);writer.writerows(rows)
    with (ROOT/'frequency_grid.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['omega','largest_sigma_finite_grid']);writer.writerows(zip(omegas,curve))
    summary={'accepted_exact_certificate':passed,'K_numeric':numeric(K).tolist(),'eta':str(eta),'gamma_numeric':float(sp.sqrt(eta)),'frequency_diagnostic':{'parameter_grid_per_axis':7,'frequency_count':len(omegas),'peak_observed':peak,'proof':False},'trajectory_diagnostics':scenario_results,'outside_box_certificate_failure_count':len(failures),'runtime_scope':'Numerical synthesis, exact rational certificate verification, finite-grid frequency SVD and ODE simulation. No physical plant or human learning outcome tested.'}
    dump('summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
```
