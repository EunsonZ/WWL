#!/usr/bin/env python3
"""Fixed nominal observer/controller analysis. Only exact original N acceptance is proof."""
import argparse,csv,itertools,json,os,platform,sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parent / '.mpl-cache'))
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
VERTICES=list(itertools.product([-1,1],repeat=2))
def serial(M):return [[str(v) for v in row] for row in M.tolist()]
def numeric(M):return np.array(M,dtype=float)
def mat(v):return sp.Matrix([[sp.Rational(x) for x in row] for row in v])
def exact_pd(M):
    if M!=M.T:raise ValueError('Exact PD test needs symmetric matrix')
    minors=[M[:j,:j].det(method='domain-ge') for j in range(1,M.rows+1)]
    return {'positive_definite':all(x>0 for x in minors),'leading_principal_minors':[str(x) for x in minors]}
def finite_rational(v,key,positive=False,nonnegative=False):
    if isinstance(v,bool):raise ValueError(key+': bool not a number')
    try:q=sp.Rational(v)
    except Exception as exc:raise ValueError(key+': rational required') from exc
    if q.is_finite is not True or not np.isfinite(float(q)) or (positive and q<=0) or (nonnegative and q<0):raise ValueError(key+': invalid finite range')
    return q

def load_card(path):
    i=json.loads(path.read_text())
    if i.get('theta_box')!=[[-1,1],[-1,1]]:raise ValueError('Only [-1,1]^2 is supported')
    if i.get('dimensions')!={'x':2,'xhat':2,'xi':4,'w':2,'n':1,'d':3,'u':2,'z':4}:raise ValueError('Unsupported dimensions')
    shapes={'A0':(2,2),'A1':(2,2),'A2':(2,2),'B1':(2,2),'B2':(2,2),'Cz':(4,2),'Dzu':(4,2),'Dzw':(4,2),'H':(1,2),'L':(2,1),'controller_X':(2,2),'controller_Y':(2,2)}
    m={}
    for k,sh in shapes.items():
        v=i.get(k)
        if not isinstance(v,list) or len(v)!=sh[0] or any(not isinstance(row,list) or len(row)!=sh[1] for row in v):raise ValueError(k+': invalid shape')
        m[k]=sp.Matrix([[finite_rational(x,k) for x in row] for row in v])
    if m['Dzw']!=sp.zeros(4,2):raise ValueError('Nonzero Dzw unsupported')
    if not exact_pd(m['controller_X'])['positive_definite']:raise ValueError('controller_X must be symmetric PD')
    for k in ['solver_delta','exact_margin','storage_P_lower_bound']:i[k]=str(finite_rational(i[k],k,positive=True))
    i['rho']=str(finite_rational(i['rho'],'rho',nonnegative=True))
    den=i.get('rational_denominator')
    if isinstance(den,bool) or not isinstance(den,int) or not 1000<=den<=1000000000:raise ValueError('Invalid denominator')
    d=i['diagnostics']
    for k in ['t_end','noise_multiplier','saturation_limit','frequency_min','frequency_max']:d[k]=float(finite_rational(d[k],k,positive=True))
    for k,lo,hi in [('samples',11,5001),('parameter_grid_per_axis',2,15),('frequency_count',11,2001)]:
        v=d[k]
        if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:raise ValueError(k+': invalid integer')
    if d['frequency_min']>=d['frequency_max']:raise ValueError('frequency interval invalid')
    if len(d['outside_theta'])!=2:raise ValueError('outside_theta shape')
    d['outside_theta']=[float(finite_rational(x,'outside_theta')) for x in d['outside_theta']]
    return i,m

def model(i,m):
    K=m['controller_Y']*m['controller_X'].inv();L=m['L'];H=m['H'];rho=sp.Rational(i['rho'])
    # General B1/Cz/Dzu input cards are authoritative, preserving their 18 shapes.
    G=m['B1'].row_join(sp.zeros(2,1)).col_join(sp.zeros(2,2).row_join(rho*L))
    C=m['Cz'].row_join(m['Dzu']*K)
    def F(th):
        A=m['A0']+sp.Rational(str(th[0]))*m['A1']+sp.Rational(str(th[1]))*m['A2']
        return A.row_join(m['B2']*K).col_join((L*H).row_join(m['A0']+m['B2']*K-L*H))
    def N(th,P,eta):
        f=F(th);q=f.T*P+P*f+C.T*C
        return q.row_join(P*G).col_join((G.T*P).row_join(-eta*sp.eye(3)))
    return K,G,C,F,N

def exact_checks(P,eta,N,eps,floor):
    return {'P_minus_design_floor_I':exact_pd(P-floor*sp.eye(4)),'P_minus_margin_I':exact_pd(P-eps*sp.eye(4)),'vertices':[{'theta':list(th),'negative_N_minus_margin_I':exact_pd(-N(th,P,eta)-eps*sp.eye(7)),'largest_N_eigenvalue_diagnostic':float(np.linalg.eigvalsh(numeric(N(th,P,eta)))[-1])} for th in VERTICES]}
def accepted(checks):return checks['P_minus_design_floor_I']['positive_definite'] and checks['P_minus_margin_I']['positive_definite'] and all(v['negative_N_minus_margin_I']['positive_definite'] for v in checks['vertices'])
def solve(i,m,K,G,C,F,N):
    p=cp.Variable((4,4),symmetric=True);e=cp.Variable(nonneg=True);eps=float(sp.Rational(i['solver_delta']));gn=numeric(G);cn=numeric(C)
    cons=[p >> float(sp.Rational(i['storage_P_lower_bound']))*np.eye(4)]
    for th in VERTICES:
        f=numeric(F(th));n=cp.bmat([[f.T@p+p@f+cn.T@cn,p@gn],[gn.T@p,-e*np.eye(3)]])
        cons.append(n << -eps*np.eye(7))
    prob=cp.Problem(cp.Minimize(e),cons);prob.solve(solver='CLARABEL',tol_gap_abs=1e-9,tol_gap_rel=1e-9,tol_feas=1e-9,max_iter=200)
    if p.value is None or e.value is None:raise RuntimeError('No candidate for fixed K/L; no proof accepted')
    den=i['rational_denominator'];pr=sp.Matrix([[sp.Rational(round(float(x)*den),den) for x in row] for row in (p.value+p.value.T)/2]);margin=sp.Rational(i['exact_margin'])
    # eta slack is bounded and each candidate must pass exact ORIGINAL 7x7 N.
    for bump in range(11):
        eta=sp.Rational(round((float(e.value)*(1.03+0.01*bump)+.005)*den),den)
        checks=exact_checks(pr,eta,N,margin,sp.Rational(i['storage_P_lower_bound']))
        if accepted(checks):break
    else:raise RuntimeError('Rounded original-form certificate failed')
    c={'schema':'wwl-fixed-output-hinf-rational-v1','controller_X':serial(m['controller_X']),'controller_Y':serial(m['controller_Y']),'K':serial(K),'L':serial(m['L']),'P':serial(pr),'eta':str(eta),'gamma_numeric':float(sp.sqrt(eta)),'exact_margin':str(margin),'exact_checks':checks,'accepted':True,'acceptance':'Exact rational Sylvester checks on P-epsilon I4, P-design_floor I4 (conservative strict check) and -N_vertex-epsilon I7, same P/K/L/eta at four vertices. Convex-affine extension covers measurable theta(t) in box.','eta_rounding_slack_step':bump,'scope':'Fixed K/L convex analysis in P and eta; no joint output-feedback synthesis or exact optimum claim.'}
    solver={'status_diagnostic_only':prob.status,'eta_numerical_candidate':float(e.value),'P_numerical':p.value.tolist(),'solve_time_s':prob.solver_stats.solve_time,'iterations':prob.solver_stats.num_iters}
    return c,pr,eta,solver

def verify(i,m,c):
    K,G,C,F,N=model(i,m)
    if c.get('schema')!='wwl-fixed-output-hinf-rational-v1':raise ValueError('Unknown certificate schema')
    P=mat(c['P']);eta=finite_rational(c['eta'],'eta',positive=True);eps=finite_rational(c['exact_margin'],'exact_margin',positive=True)
    if P.shape!=(4,4) or P!=P.T or any(v.is_finite is not True for v in P):raise ValueError('Invalid P')
    for k,expected in [('K',K),('L',m['L']),('controller_X',m['controller_X']),('controller_Y',m['controller_Y'])]:
        if mat(c[k])!=expected:raise ValueError('Certificate/card mismatch '+k)
    if eps!=sp.Rational(i['exact_margin']):raise ValueError('Certificate/card margin mismatch')
    checks=exact_checks(P,eta,N,eps,sp.Rational(i['storage_P_lower_bound']))
    if not accepted(checks):raise ValueError('Original N exact check failed')
    return K,G,C,F,N,P,eta,checks

def build_figures(out,gamma):
    # Read persisted CSV for each figure so plots are tied to the delivered data.
    fq=np.genfromtxt(out/'frequency_grid.csv',delimiter=',',names=True);fig,ax=plt.subplots(figsize=(8,4.5));ax.semilogx(fq['omega'][1:],fq['largest_sigma_finite_grid'][1:],label='finite parameter/frequency grid');ax.axhline(gamma,color='red',ls='--',label='exact rational certificate gamma');ax.set(xlabel='normalized angular frequency',ylabel='largest singular value');ax.grid();ax.legend();fig.tight_layout();fig.savefig(out/'frequency_diagnostics.svg');plt.close(fig)
    with (out/'trajectories.csv').open() as f:data=list(csv.DictReader(f))
    def series(name,col):return np.array([float(r[col]) for r in data if r['scenario']==name])
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for name,style in zip(['zero_initial','measurement_removed','rho_amplified','outside_box','saturation'],['-','--',':','-.',(0,(3,1,1,1,1,1))]):
        t=series(name,'tau');xn=np.hypot(series(name,'x1'),series(name,'x2'));un=np.hypot(series(name,'u1'),series(name,'u2'))
        for ax,val in zip(axs.flat,[xn,un,series(name,'Ez'),series(name,'dissipation_slack')]):ax.plot(t,val,label=name,linestyle=style)
    for ax,y in zip(axs.flat,['state norm','applied control norm','accumulated z energy','eta Ed + V0 - Ez - V']):ax.set(xlabel='normalized time tau',ylabel=y);ax.grid();ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'scenario_diagnostics.svg');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for name,style,marker in zip(['zero_initial','nonzero_estimate','measurable_switch','noise_input_amplified'],['-','--',':','-.'],['o','s','^','x']):
        t=series(name,'tau');axs[0].plot(t,series(name,'Ez')+series(name,'V'),label=name+' Ez+V',linestyle=style,marker=marker,markevery=80,markersize=4);axs[0].plot(t,series(name,'eta_Ed_plus_V0'),ls=style,label=name+' budget',marker=marker,markevery=80,markersize=4,fillstyle='none',alpha=.7);axs[1].plot(t,series(name,'dissipation_slack'),label=name,linestyle=style,marker=marker,markevery=80,markersize=4)
    axs[0].set(ylabel='Ez+V and eta Ed+V0 (symlog, threshold=1)');axs[1].set(ylabel='dissipation slack (symlog, threshold=1)')
    for ax in axs:ax.set_yscale('symlog',linthresh=1)
    for ax in axs:ax.set(xlabel='normalized time tau');ax.grid();ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(out/'storage_diagnostics.svg');plt.close(fig)

def main():
    a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,default=ROOT/'inputs.json');a.add_argument('--outdir',type=Path);a.add_argument('--verify-only',action='store_true');a.add_argument('--certificate',type=Path);a.add_argument('--certificate-only',action='store_true');a.add_argument('--preflight',action='store_true');args=a.parse_args()
    versions={'python':sys.version,'platform':platform.platform(),**{x.__name__:x.__version__ for x in [np,scipy,sp,cp,clarabel,matplotlib]}}
    if args.preflight:print(json.dumps({'versions':versions,'solvers':cp.installed_solvers()}));return
    i,m=load_card(args.inputs);K,G,C,F,N=model(i,m)
    if args.verify_only:
        if args.certificate is None:raise ValueError('--certificate required')
        *_,P,eta,checks=verify(i,m,json.loads(args.certificate.read_text()))
        print(json.dumps({'verify_only':True,'accepted':True,'eta':str(eta),'gamma_numeric':float(sp.sqrt(eta)),'checks':checks},indent=2));return
    if args.outdir is None:raise ValueError('--outdir NEW nonexisting directory required')
    out=args.outdir
    # Refuse before solving if destination exists, including symlinks. No overwrite mode.
    if out.exists() or out.is_symlink():raise ValueError('outdir exists; choose a new disposable directory')
    if out.resolve()==args.inputs.resolve().parent or ROOT==out.resolve():raise ValueError('outdir must differ from source/input directory')
    c,P,eta,solver=solve(i,m,K,G,C,F,N)
    out.mkdir(parents=True,exist_ok=False)
    def dump(name,obj):(out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    dump('inputs.json',json.loads(args.inputs.read_text()));dump('certificate.json',c);dump('solver_output.json',solver);dump('environment.json',versions)
    print(json.dumps({'accepted':True,'eta':str(eta),'gamma_numeric':c['gamma_numeric'],'outdir':str(out)}),flush=True)
    if args.certificate_only:return
    diagnostics(i,m,K,G,C,F,N,P,eta,out,dump)

def diagnostics(i,m,K,G,C,F,N,P,eta,out,dump):
    cfg=i['diagnostics'];kn=numeric(K);pn=numeric(P);gn=numeric(G);cn=numeric(C);a0=numeric(m['A0']);a1=numeric(m['A1']);a2=numeric(m['A2']);b1=numeric(m['B1']);b2=numeric(m['B2']);h=numeric(m['H']);l=numeric(m['L']);rho=float(sp.Rational(i['rho']));cstate=numeric(m['Cz']);du=numeric(m['Dzu'])
    def fn(th,measurement=1.):return np.block([[a0+th[0]*a1+th[1]*a2,b2@kn],[measurement*l@h,a0+b2@kn-l@h]])
    omega=np.r_[0.,np.logspace(np.log10(cfg['frequency_min']),np.log10(cfg['frequency_max']),cfg['frequency_count'])]
    # All three disturbance directions enter the single SVD of a 4x3 transfer.
    rows=[];peak={'sigma':0.};grid=itertools.product(np.linspace(-1,1,cfg['parameter_grid_per_axis']),repeat=2)
    envelope=np.zeros(len(omega))
    for th in grid:
        f=fn(th)
        for j,w in enumerate(omega):
            t=cn@np.linalg.solve(1j*w*np.eye(4)-f,gn);sigma=float(np.linalg.svd(t,compute_uv=False)[0]);envelope[j]=max(envelope[j],sigma)
            if sigma>peak['sigma']:peak={'sigma':sigma,'theta':list(th),'omega':float(w)}
    with (out/'frequency_grid.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['omega','largest_sigma_finite_grid','certificate_gamma']);wr.writerows(zip(omega,envelope,itertools.repeat(float(sp.sqrt(eta)))))
    # Exact certificate diagnostics change the ACTUAL matrices, never the axis labels.
    variant=[]
    for name,th,measurement,rhomul in [('outside_box',cfg['outside_theta'],1,1),('measurement_removed',[1,-1],0,1),('rho_amplified',[0,0],1,cfg['noise_multiplier'])]:
        fs=F(th)
        if measurement==0:fs[2:4,0:2]=sp.zeros(2,2)
        gs=G.copy();gs[2:4,2:3]*=sp.Rational(str(rhomul));ns=(fs.T*P+P*fs+C.T*C).row_join(P*gs).col_join((gs.T*P).row_join(-eta*sp.eye(3)))
        chk=exact_pd(-ns);eig=np.linalg.eigvals(numeric(fs));vpeak={'sigma':0.}
        for w in omega:
            transfer=numeric(C)@np.linalg.solve(1j*w*np.eye(4)-numeric(fs),numeric(gs));_,sing,vh=np.linalg.svd(transfer,full_matrices=False)
            if float(sing[0])>vpeak['sigma']:
                direction=vh.conj().T[:,0];vpeak={'sigma':float(sing[0]),'omega':float(w),'right_input_direction_real':direction.real.tolist(),'right_input_direction_imag':direction.imag.tolist()}

        variant.append({'name':name,'theta':th,'measurement_multiplier':measurement,'rho_multiplier':rhomul,'same_certificate_negative_N':chk,'largest_N_eigenvalue_diagnostic':float(np.linalg.eigvalsh(numeric(ns))[-1]),'max_real_F_eigenvalue_diagnostic':float(max(eig.real)),'F_eigenvalues_real_imag':[[float(v.real),float(v.imag)] for v in eig],'frequency_lower_bound_observed':vpeak,'stable_frozen_frequency_bound_exceeds_gamma':bool(max(eig.real)<0 and vpeak['sigma']>float(sp.sqrt(eta))),'meaning':'Failure of this certificate does not alone prove instability or performance failure. F eigenvalues are frozen linear diagnostics.'})
    def disturbance(t,noise_factor=1.):return np.array([np.exp(-t)*np.sin(2*t),np.exp(-t)*np.cos(3*t),noise_factor*np.exp(-.6*t)*np.sin(8*t)])
    scenarios=[('zero_initial',np.zeros(4),'smooth',1,1,1,None,True),('nonzero_estimate',np.array([0,0,1,-.5]),'smooth',1,1,1,None,True),('measurable_switch',np.zeros(4),'switch',1,1,1,None,True),('measurement_removed',np.zeros(4),'smooth',0,1,1,None,False),('noise_input_amplified',np.zeros(4),'smooth',1,1,cfg['noise_multiplier'],None,True),('rho_amplified',np.zeros(4),'smooth',1,cfg['noise_multiplier'],1,None,False),('outside_box',np.zeros(4),'outside',1,1,1,None,False),('saturation',np.zeros(4),'smooth',1,1,1,cfg['saturation_limit'],False)]
    ts=np.linspace(0,cfg['t_end'],cfg['samples']);trajectory_rows=[];results=[]
    for name,xi0,thmode,measurement,rhomul,nmul,limit,applies in scenarios:
        def theta(t):
            if thmode=='outside':return cfg['outside_theta']
            if thmode=='switch':return (1 if int(t/.75)%2==0 else -1,1 if int(t/.5)%2==0 else -1)
            return (np.sin(.7*t),np.cos(1.1*t))
        def rhs(t,q):
            x=q[:2];xh=q[2:4];d=disturbance(t,nmul);th=theta(t);u_cmd=kn@xh;u=np.clip(u_cmd,-limit,limit) if limit is not None else u_cmd
            y=float((measurement*h@x).item())+rho*rhomul*d[2]
            dx=(a0+th[0]*a1+th[1]*a2)@x+b1@d[:2]+b2@u
            dxh=a0@xh+b2@u+l[:,0]*(y-float((h@xh).item()))
            z=cstate@x+du@u
            return np.r_[dx,dxh,d@d,z@z,x@x,u@u]
        if thmode=='switch':
            breaks=sorted(set([0.,cfg['t_end']]+[float(t) for t in np.arange(.25,cfg['t_end'],.25)]));state=np.r_[xi0,0.,0.,0.,0.];all_t=[];all_q=[]
            for start,end in zip(breaks[:-1],breaks[1:]):
                sol=solve_ivp(rhs,(start,end),state,dense_output=True,rtol=1e-9,atol=1e-11,max_step=.02)
                if not sol.success:raise RuntimeError(sol.message)
                idx=ts[(ts>=start)&(ts<end if end<cfg['t_end'] else ts<=end)]
                all_t.extend(idx);all_q.extend(sol.sol(idx).T);state=sol.y[:,-1]
            q=np.array(all_q).T
        else:
            sol=solve_ivp(rhs,(0,cfg['t_end']),np.r_[xi0,0.,0.,0.,0.],t_eval=ts,rtol=1e-9,atol=1e-11,max_step=.02)
            if not sol.success:raise RuntimeError(sol.message)
            q=sol.y
        v0=float(xi0@pn@xi0);storage=np.einsum('it,ij,jt->t',q[:4],pn,q[:4]);budget=float(eta)*q[4]+v0
        results.append({'name':name,'xi0':xi0.tolist(),'theta_mode':thmode,'measurement_multiplier':measurement,'rho_multiplier':rhomul,'noise_input_multiplier':nmul,'saturation_limit':limit,'certificate_applies':applies,'Ed':float(q[4,-1]),'Ez':float(q[5,-1]),'Ex':float(q[6,-1]),'Eu':float(q[7,-1]),'V0':v0,'V_end':float(storage[-1]),'eta_Ed_plus_V0':float(budget[-1]),'dissipation_slack_final':float(budget[-1]-q[5,-1]-storage[-1]),'minimum_dissipation_slack_on_samples':float(min(budget-q[5]-storage)),'energy_gain_on_finite_interval':float(np.sqrt(q[5,-1]/q[4,-1])),'scope':'Finite waveform/interval diagnostic; only exact original-model certificate supplies all-input guarantee.'})
        for j,t in enumerate(ts):
            d=disturbance(t,nmul);th=theta(t);uc=kn@q[2:4,j];u=np.clip(uc,-limit,limit) if limit is not None else uc;y=float((measurement*h@q[:2,j]).item())+rho*rhomul*d[2]
            trajectory_rows.append([name,t,*q[:4,j],*d,*th,y,*u,*uc,q[4,j],q[5,j],q[6,j],q[7,j],storage[j],budget[j],budget[j]-q[5,j]-storage[j]])
    with (out/'trajectories.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['scenario','tau','x1','x2','xhat1','xhat2','w1','w2','n','theta1','theta2','y','u1','u2','u_command1','u_command2','Ed','Ez','Ex','Eu','V','eta_Ed_plus_V0','dissipation_slack']);wr.writerows(trajectory_rows)
    build_figures(out,float(sp.sqrt(eta)))
    summary={'accepted_exact_certificate':True,'eta':str(eta),'gamma_numeric':float(sp.sqrt(eta)),'frequency_diagnostic':{'parameter_grid_per_axis':cfg['parameter_grid_per_axis'],'frequency_count':len(omega),'peak_observed':peak,'proof':False},'trajectory_diagnostics':results,'changed_model_certificate_diagnostics':variant,'K_numeric':kn.tolist(),'L_numeric':l.tolist(),'observer_nominal_eigenvalues':[str(v) for v in (m['A0']-m['L']*m['H']).eigenvals()],'runtime_scope':'Exact rational fixed-controller original-form certificate, finite frequency SVD, sample ODE; no physical output or human-learning evidence.'}
    dump('summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
