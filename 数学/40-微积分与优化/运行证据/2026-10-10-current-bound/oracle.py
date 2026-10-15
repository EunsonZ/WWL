"""Independent finite-case expectations; does not call certificate functions/solver."""
import importlib.util, io, json, pathlib, platform, resource, sys
from contextlib import redirect_stdout
from fractions import Fraction as F
import numpy as np
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[3]
data=json.loads((OUT/'default.stdout').read_text())
qpdata=json.loads((OUT/'qp.stdout').read_text())
assert data=={k:v for k,v in qpdata.items() if k!='qp'}
checks=[]
def eq(value, expected): assert F(value)==F(expected),(value,expected)
for row,b in zip(data['parametric'],range(4)):
    expected=[(0,4,4,-4),(1,2,1,-2),(2,0,0,0),(2,0,0,0)][b]
    for key,e in zip(('x','multiplier','primal','derivative'),expected):eq(row[key],e)
    eq(row['dual'],expected[2]);eq(row['stationarity'],0);eq(row['complementary'],0)
    eq(row['trial_lower'],F(7,4)-b)
checks.append('parameter cases exact analytic constrained minima and dual values')
for row,lam in zip(data['degenerate'],(1,10,100)):
    eq(row['lagrangian_minimizer'],-F(1,2*lam));eq(row['lower'],-F(1,4*lam));eq(row['gap'],F(1,4*lam));eq(row['upper'],0)
checks.append('finite degenerate dual quadratic minima exact')
for name,step in (('proximal_valid',F(1,2)),('proximal_bad_step',F(3))):
    x=F(0)
    for k,row in enumerate(data[name]):
        # Minimize piecewise quadratic of prox subproblem by candidates on each half-line.
        v=x-step*(x-3)
        candidates=(F(0),max(F(0),v-step),min(F(0),v+step))
        nxt=min(candidates,key=lambda z: (z-v)**2/(2*step)+abs(z))
        value=(x-3)**2/2+abs(x);nextvalue=(nxt-3)**2/2+abs(nxt)
        eq(row['x'],x);eq(row['objective'],value);eq(row['lower'],F(5,2));eq(row['gap'],value-F(5,2));eq(row['gradient_mapping'],(x-nxt)/step);eq(row['next_objective'],nextvalue)
        assert row['conservative_descent_holds']==(nextvalue<=value-(x-nxt)**2/(2*step))
        x=nxt
eq(data['proximal_valid'][-1]['gap'],F(1,2048))
assert [r['x'] for r in data['proximal_bad_step']]==['0','6','0','6']
checks.append('proximal updates independently minimize scalar piecewise quadratics; exact valid gap and bad-step cycle')
expectedcovers=[([0,1,0],3),([0,1,1],5),([1,0,1],4),([1,1,0],5),([1,1,1],7)]
for name,budgets in (('lp_valid',(2,1)),('lp_invalid',(2,2))):
    row=data[name];assert row['all_covers']==[[bits,str(cost)] for bits,cost in expectedcovers]
    eq(row['exact_integer_optimum'],3);assert row['dual_feasible']==(sum(budgets)<=3)
    assert row['certified_lower']==('3' if name=='lp_valid' else None)
checks.append('LP five feasible binary covers exhaust all eight assignments; optimum 3, invalid middle budget 4>3 rejected')
s=data['svm']; w=[sum(F(a)*y*p[j] for a,y,p in zip(s['alpha'],s['labels'],s['points'])) for j in range(2)]
assert w==[1,0];assert sum(F(a)*y for a,y in zip(s['alpha'],s['labels']))==0
margins=[y*(w[0]*p[0]+w[1]*p[1]+F(s['bias'])) for y,p in zip(s['labels'],s['points'])]
assert min(margins)==1;assert all(F(a)*(m-1)==0 for a,m in zip(s['alpha'],margins))
eq(s['upper'],F(1,2));eq(s['lower'],sum(map(F,s['alpha']))-sum(z*z for z in w)/2)
assert not s['soft_C_one_tenth_feasible'] and max(map(F,s['alpha']))>F(1,10)
checks.append('SVM rational margins, multiplier equality, complementarity and primal/dual 1/2')
# Rebuild full QP from rational double-integrator closed-form state responses.
n=8;dt=F(1,5);c=F(1,4);h=[[F(int(i==j),20) for j in range(n)] for i in range(n)];f=[F(0)]*n
for k in range(1,n+1):
    p=[dt*dt*(k-j-F(1,2)) if j<k else F(0) for j in range(n)]
    v=[dt if j<k else F(0) for j in range(n)]
    wp,wv=(F(8),F(2)) if k==n else (F(1),F(1,10))
    c+=wp/4
    for i in range(n):
        f[i]+=wp*p[i]/2
        for j in range(n):h[i][j]+=wp*p[i]*p[j]+wv*v[i]*v[j]
H=np.array(h,dtype=float);fv=np.array(f,dtype=float);lo=np.full(n,-.8);hi=-lo
assert c==4 and np.linalg.eigvalsh(H).min()>0
# Inspect actual API's fixed matrices, but never call its solver in this oracle.
labpath=ROOT/'AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py'
spec=importlib.util.spec_from_file_location('current_bound_lab',labpath);lab=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lab;spec.loader.exec_module(lab)
A,B,Q,R,Qf,problem,x0=lab.default_problem(dt=.2,horizon=8,x0=(.5,0.))
assert np.max(abs(problem.H-H))<1e-14 and np.max(abs(problem.f-fv))<1e-14 and abs(problem.constant-float(c))<1e-14
u=np.zeros(n)
for iteration in range(1,10001):
    before=u.copy()
    for i in range(n):u[i]=np.clip(-(fv[i]+H[i]@u-H[i,i]*u[i])/H[i,i],lo[i],hi[i])
    if max(abs(u-before))<1e-14:break
else:raise AssertionError('independent coordinate minimization did not converge')
records={}
for name,row in qpdata['qp']['certificates'].items():
    z=np.array(row['controls']);alpha=np.array(row['lower_multipliers']);beta=np.array(row['upper_multipliers'])
    # Direct physical rollout evaluates original running/terminal cost independently.
    pos,vel=.5,0.;objective=0.
    for acc in z:
        objective+=pos**2+.1*vel**2+.05*acc**2
        pos,vel=pos+.2*vel+.02*acc,vel+.2*acc
    objective+=8*pos**2+2*vel**2
    d=2*fv-alpha+beta;lagmin=np.linalg.solve(2*H,-d)
    dual=float(c)+lagmin@H@lagmin+d@lagmin+alpha@lo-beta@hi
    station=max(abs(2*(H@z+fv)-alpha+beta));complement=max(max(abs(alpha*(lo-z))),max(abs(beta*(z-hi))))
    pv=max(0.,max(lo-z),max(z-hi));dv=max(0.,-min(alpha),-min(beta))
    assert abs(objective-row['primal'])<1e-12 and abs(dual-row['dual'])<1e-12
    assert pv==dv==0 and complement<1e-12 and objective>=dual-1e-12
    assert abs(station-row['stationarity'])<1e-12
    if name=='box_qp': assert max(abs(z-u))<1e-10 and station<1e-10 and abs(objective-dual)<1e-10
    else: assert max(abs(z-np.clip(np.linalg.solve(H,-fv),lo,hi)))<1e-12 and station>1 and objective>qpdata['qp']['certificates']['box_qp']['primal']+.6
    records[name]=dict(physical_rollout_objective=objective,independent_lagrangian_minimum=dual,gap=objective-dual,stationarity=station,complementary=complement,primal_violation=pv,dual_violation=dv)
checks.append('QP rational mechanics rebuild matches current matrices; independent coordinate minimization, physical cost and Lagrangian minimum agree; clipped point is feasible but worse')
matrices=dict(parameters=dict(dt_s='.2',horizon=8,x0=['.5','0'],lower=['-.8']*8,upper=['.8']*8),actual_api_inputs={k:v.tolist() for k,v in dict(A=A,B=B,Q=Q,R=R,Qf=Qf,x0=x0,H=problem.H,f=problem.f,G=problem.G,M=problem.M).items()},constant=problem.constant,independent_rational_H=[[str(x) for x in row] for row in h],independent_rational_f=list(map(str,f)),independent_rational_constant=str(c))
(OUT/'fixed-inputs.json').write_text(json.dumps(matrices,indent=2)+'\n')
config=io.StringIO()
with redirect_stdout(config):np.show_config()
imports=[dict(module=name,path=str(pathlib.Path(m.__file__).resolve())) for name,m in list(sys.modules.items()) if getattr(m,'__file__',None) and str(pathlib.Path(m.__file__).resolve()).startswith(str(ROOT)) and '.venv-' not in str(m.__file__)]
result=dict(status='pass',checks=checks,coordinate_iterations=iteration,coordinate_solution=u.tolist(),qp_checks=records,environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),numpy=np.__version__,numpy_config=config.getvalue(),self_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),actual_imported_vault_modules=imports,limitation='Finite rational examples and floating current-QP residuals; does not prove general duality or strictly enclose floating roundoff')
(OUT/'independent-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
