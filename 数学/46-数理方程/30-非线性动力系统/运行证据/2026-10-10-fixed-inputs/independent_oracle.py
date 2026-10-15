"""Independent finite oracle: no import of course expected values or check runners."""
from fractions import Fraction as F
from decimal import Decimal as D, localcontext
from math import sin, cos, exp, log, sqrt, hypot, pi
import json, sys, importlib.util
from pathlib import Path

def matmul(a,b):
    return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]

def exact_feedback(a):
    w=[[a,a],[a,a]];power=[[F(1),F(0)],[F(0),F(1)]];partial=[[F(0),F(0)],[F(0),F(0)]];rows=[]
    for k in range(7):
        rows.append([power[0][0],power[1][0]])
        partial=[[x+y for x,y in zip(r,s)] for r,s in zip(partial,power)]
        power=matmul(power,w)
    inverse=None
    if a<F(1,2):
        # Explicit two-by-two adjugate, rather than scalar-mode tail formula.
        m=[[1-a,-a],[-a,1-a]];det=m[0][0]*m[1][1]-m[0][1]*m[1][0]
        inverse=[[m[1][1]/det,-m[0][1]/det],[-m[1][0]/det,m[0][0]/det]]
        assert matmul(m,inverse)==[[1,0],[0,1]]
        # Matrix finite-series identity, checks increment vs cumulative semantics.
        identityminus=[[int(i==j)-power[i][j] for j in range(2)] for i in range(2)]
        assert matmul(m,partial)==identityminus
    return rows,None if inverse is None else [inverse[0][0],inverse[1][0]]

def distribution(n):
    # Probability-generating polynomial, computed by repeated convolution.
    c=[F(1)]
    for _ in range(n):
        nxt=[F(0)]*(len(c)+1)
        for k,v in enumerate(c):nxt[k]+=v*F(3,5);nxt[k+1]+=v*F(2,5)
        c=nxt
    ratios=[F(2)**(2*k-n) for k in range(n+1)]
    return c,ratios,sum(p*r for p,r in zip(c,ratios)),sum(p for p,r in zip(c,ratios) if r<1)

def radial(mu,alpha,r0,t):
    # u=r^-2 obeys an affine linear ODE; use 70-digit Decimal integrating factor.
    if r0==0:return D(0)
    with localcontext() as ctx:
        ctx.prec=70
        mu,alpha,r0,t=map(lambda x:D(str(x)),(mu,alpha,r0,t))
        u=(1/(r0*r0)-alpha/mu)*(-2*mu*t).exp()+alpha/mu
        return None if u<=0 else 1/u.sqrt()

def midpoint_pendulum(h,steps):
    theta,v=pi/2,0.
    for _ in range(steps):
        # Implicit midpoint fixed-point solve, independent of RK4 tableau.
        nt,nv=theta+h*v,v+h*(-sin(theta)-.5*v)
        for _ in range(6):
            nt,nv=theta+h*(v+nv)/2,v+h*(-sin((theta+nt)/2)-.5*(v+nv)/2)
        theta,v=nt,nv
    return (theta,v)

def run(source,report):
    spec=importlib.util.spec_from_file_location('bound_dynamics',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    observed=json.loads(Path(report).read_text());result={}
    for entry in observed['feedback']:
        a=F(entry['a']);rows,total=exact_feedback(a)
        assert [[F(x) for x in r] for r in entry['first_seven_increments']]==rows
        assert (None if entry['infinite_cumulative'] is None else list(map(F,entry['infinite_cumulative'])))==total
    result['feedback']={'a_2_5_cumulative':list(map(str,exact_feedback(F(2,5))[1])),'a_1_2_cumulative':None,'isolated_3_5':'3/5','joint_3_5':'6/5','method':'exact rational matrix powers, adjugate inverse and finite-series identity'}
    for entry in observed['nonnormal']:
        a,b=F(4,5),F(entry['coupling']);A=[[a,b],[F(0),a]];power=[[F(1),F(0)],[F(0),F(1)]]
        states=[]
        for row in entry['rows']:
            z=[power[0][1],power[1][1]];assert list(map(F,row['state']))==z;states.append(z);power=matmul(power,A)
        peak=max(z[0] for z in states);assert F(entry['first_component_peak'])==peak
        assert entry['first_component_peak_steps']==[i for i,z in enumerate(states) if z[0]==peak]
    result['nonnormal']={'k4':['2048/125','256/625'],'first_component_peak_steps':[4,5],'coupling_reduction_ratio':100,'warning':'Euclidean norm peak differs from first-component peak; fixed-coordinate mathematics only'}
    for row in observed['euler']:
        h=F(row['step_seconds']);factor=1-h
        assert F(row['factor'])==factor and list(map(F,row['states']))==[factor**k for k in range(7)]
        assert abs(row['exact_final']-exp(-6*float(h)))<1e-14
    result['euler']={'factors':['1/2','-1/2','-1','-2'],'continuous_model':'exp(-t) decreases for all t>=0; discrete numerical instability is not physical instability'}
    random=[]
    for row in observed['random_products']:
        n=row['n'];c,r,mean,below=distribution(n)
        assert F(row['mean_ratio'])==mean and F(row['probability_ratio_below_one'])==below
        assert [F(v['probability']) for v in row['count_distribution']]==c
        assert [F(v['growth_ratio']) for v in row['count_distribution']]==r
        assert sum(c)==1 and mean==F(11,10)**n
        typical_k=max(range(n+1),key=lambda i:c[i]);random.append({'n':n,'mean_exact':str(mean),'modal_up_count':typical_k,'modal_ratio':str(r[typical_k]),'below_one_probability':str(below)})
    result['random_products']={'polynomial_convolution':random,'scope':'finite exact distribution; does not experimentally prove SLLN or general random-process claims'}
    pend=observed['pendulum'];reference=midpoint_pendulum(1/3200,64000)
    errors=[hypot(*(x-y for x,y in zip(v['endpoint'],reference))) for v in pend['runs']]
    assert errors[-1]<2e-8 and errors[-1]<errors[0]
    defects=[]
    for theta,v in [(pi/2,0),(0,1),(pi/2,-2),(.4,-.7)]:
        field=mod.pendulum((theta,v));chain=sin(theta)*field[0]+v*field[1];assert abs(chain+.5*v*v)<1e-12;defects.append(chain+.5*v*v)
    result['pendulum']={'independent_integrator':'implicit midpoint h=1/3200,64000 steps,6 fixed-point iterations','reference_endpoint':reference,'RK4_endpoint_errors':errors,'V_derivative_defects':defects,'scope':'finite numerical refinement/chain-rule checks, not global LaSalle proof'}
    hopf=observed['hopf'];expected=float(radial(1,1,.25,1));assert abs(hopf['exact_endpoint'][0]-expected)<1e-14
    assert abs(hopf['radial_multiplier']-exp(-2))<1e-14
    checks=[]
    for pars in [(1,1,.25,1),(1,0,.25,1),(1,-1,.1,1),(1,-1,.1,log(101)/2-1e-4),(1e-6,1,.001,1e-6)]:
        ref=radial(*pars);got=mod.radial_exact(*pars);err=abs(got-float(ref));assert err<max(1e-12,abs(float(ref))*1e-11);checks.append({'input':pars,'oracle_decimal':str(ref),'actual':got,'absolute_error':err})
    assert all(mod.radial_exact(1,a,0,1)==0 for a in [-1,0,1])
    rejects=[]
    for pars in [(1,-1,.1,log(101)/2+1e-4),(0,1,1,1),(1,1,1e-9,1),(1,1,1,101),(float('nan'),1,1,1)]:
        try:mod.radial_exact(*pars)
        except (ValueError,ArithmeticError) as e:rejects.append({'input':list(map(str,pars)),'reason':str(e)})
        else:raise AssertionError(('must reject',pars))
    result['radial']={'cases':checks,'rejections':rejects,'return_derivative':exp(-2),'scope':'70-digit linearized reciprocal-square oracle; unsupported/unresolved requests do not establish physical blow-up'}
    return result

if __name__=='__main__':
    r=run(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False,indent=2))
