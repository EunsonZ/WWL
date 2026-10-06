"""Finite SI teaching cases, not a professional TCAD/PDK. Pure stdlib import."""
import argparse,json,math
from pathlib import Path
Q=1.602176634e-19
KB=1.380649e-23
EPS0=8.8541878128e-12

def real(value,name,lo,hi):
    if type(value) not in (int,float) or not lo<=value<=hi or not math.isfinite(value):
        raise ValueError(name+' must be a native finite real in the documented domain')
    return float(value)
def count(value,name,lo,hi):
    if type(value) is not int or not lo<=value<=hi:raise ValueError(name+' integer budget')
    return value
def vector(value,name,lo,hi,minimum=3):
    if type(value) not in (list,tuple) or not minimum<=len(value)<=257:raise ValueError(name+' vector budget')
    return [real(x,name,lo,hi) for x in value]
def new_output(output):
    p=Path(output).expanduser().resolve()
    # Portable main-vault marker guard; output must be a fresh directory outside a vault.
    if any((a/'AGENTS.md').is_file() and (a/'scripts/check_vault.py').is_file() for a in (p,*p.parents)):
        raise ValueError('output inside a vault is forbidden')
    if p.exists():raise ValueError('output must be a new directory')
    return p

def poisson(x,rho,epsilon=11.7*EPS0,left=0.,right=.1):
    """Vertex-centred finite volume, constant epsilon; rho[i] sampled C/m^3."""
    xs=vector(x,'x',0,1);rs=vector(rho,'rho',-1e7,1e7);e=real(epsilon,'epsilon',EPS0,100*EPS0)
    a=real(left,'left',-10,10);b=real(right,'right',-10,10)
    if len(xs)!=len(rs) or any(xs[i+1]-xs[i]<1e-12 for i in range(len(xs)-1)):raise ValueError('strict grid / shape')
    import numpy as np
    n=len(xs)-2;A=np.zeros((n,n));rhs=np.zeros(n)
    for k,i in enumerate(range(1,len(xs)-1)):
        hl=xs[i]-xs[i-1];hr=xs[i+1]-xs[i];w=(hl+hr)/2
        A[k,k]=e/hl+e/hr;rhs[k]=rs[i]*w
        if k:A[k,k-1]=-e/hl
        else:rhs[k]+=e*a/hl
        if k<n-1:A[k,k+1]=-e/hr
        else:rhs[k]+=e*b/hr
    phi=np.r_[a,np.linalg.solve(A,rhs),b];D=-e*np.diff(phi)/np.diff(xs)
    residual=[float(D[i]-D[i-1]-rs[i]*(xs[i+1]-xs[i-1])/2) for i in range(1,len(xs)-1)]
    return {'x_m':xs,'phi_V':phi.tolist(),'D_C_m2':D.tolist(),'balance_C_m2':residual}

def bernoulli(z):
    z=real(z,'dimensionless edge voltage',-80,80)
    if abs(z)<1e-5:return 1-z/2+z*z/12-z**4/720
    return z/math.expm1(z)
def sg_current(phi_left,phi_right,n_left,n_right,h,mu=.135,T=300.):
    pl=real(phi_left,'phi_left',-1,1);pr=real(phi_right,'phi_right',-1,1)
    nl=real(n_left,'n_left',1,1e26);nr=real(n_right,'n_right',1,1e26)
    h=real(h,'h',1e-12,1);mu=real(mu,'mu',1e-6,10);T=real(T,'T',250,400)
    vt=KB*T/Q;d=(pr-pl)/vt
    return Q*mu*vt/h*(nr*bernoulli(d)-nl*bernoulli(-d))
def transport(x,phi,n_left=1e21,n_right=1e21,mu=.135,T=300.):
    xs=vector(x,'x',0,1);ps=vector(phi,'phi',-1,1)
    if len(xs)!=len(ps) or any(xs[i+1]-xs[i]<1e-12 for i in range(len(xs)-1)):raise ValueError('strict grid / shape')
    nl=real(n_left,'n_left',1,1e26);nr=real(n_right,'n_right',1,1e26);mu=real(mu,'mu',1e-6,10);T=real(T,'T',250,400)
    vt=KB*T/Q
    # One shared J unknown enforces flux conservation, N-1 edge equations + 2 contacts.
    import numpy as np
    N=len(xs);A=np.zeros((N+1,N+1));b=np.zeros(N+1);scale=Q*mu*vt/(xs[-1]-xs[0])*max(nl,nr)
    for i in range(N-1):
        d=(ps[i+1]-ps[i])/vt;f=Q*mu*vt/(xs[i+1]-xs[i])/scale
        A[i,i]=-f*bernoulli(-d);A[i,i+1]=f*bernoulli(d);A[i,N]=-1
    A[N-1,0]=1;b[N-1]=nl;A[N,N-1]=1;b[N]=nr
    # Density scaled separately: coefficients above must multiply density ratios.
    A[:N-1,:N]*=max(nl,nr);b[N-1:]/=max(nl,nr)
    sol=np.linalg.solve(A,b);dens=sol[:N]*max(nl,nr)
    if not np.isfinite(sol).all() or (dens<=0).any():raise RuntimeError('nonpositive/invalid transport solution')
    currents=[sg_current(ps[i],ps[i+1],float(dens[i]),float(dens[i+1]),xs[i+1]-xs[i],mu,T) for i in range(N-1)]
    return {'n_m3':dens.tolist(),'J_A_m2':float(sol[N]*scale),'edge_J_A_m2':currents,'scope':'prescribed potential, not self-consistent biased DD'}

def equilibrium_case(cells=32,amplitude=.5,epsilon=11.7*EPS0,max_iterations=30,tolerance=1e-10):
    """Manufactured equilibrium PB: u*=a sin(pi s), phi=VT u, n/p=ni exp(+/-u)."""
    N=count(cells,'cells',4,128);a=real(amplitude,'amplitude',0,2);e=real(epsilon,'epsilon',EPS0,100*EPS0)
    budget=count(max_iterations,'max_iterations',1,60);tol=real(tolerance,'tolerance',1e-13,1e-5)
    import numpy as np
    L=1e-6;ni=1e16;vt=KB*300/Q;gamma=Q*ni*L*L/(e*vt);s=np.linspace(0,1,N+1);h=1/N
    exact=a*np.sin(np.pi*s);doping=2*np.sinh(exact)+(np.pi**2/gamma)*exact
    u=np.zeros(N+1);history=[]
    def residual(v):return (2*v[1:-1]-v[:-2]-v[2:])/(h*h)+gamma*(2*np.sinh(v[1:-1])-doping[1:-1])
    for it in range(budget):
        r=residual(u);norm=float(np.max(np.abs(r)));history.append(norm)
        if norm<=tol:
            return {'s':s.tolist(),'phi_V':(vt*u).tolist(),'n_m3':(ni*np.exp(u)).tolist(),'p_m3':(ni*np.exp(-u)).tolist(),'net_doping_m3':(ni*doping).tolist(),'max_error_V':float(np.max(np.abs(vt*(u-exact)))),'residual_scaled':norm,'residual_history':history,'iterations':it,'gamma':gamma}
        J=np.diag(2/h**2+gamma*2*np.cosh(u[1:-1]))+np.diag(np.full(N-2,-1/h**2),1)+np.diag(np.full(N-2,-1/h**2),-1)
        delta=np.linalg.solve(J,-r);accepted=False
        for backtrack in range(20):
            trial=u.copy();trial[1:-1]+=2.**(-backtrack)*delta
            if np.max(np.abs(trial))<=4 and np.max(np.abs(residual(trial)))<norm:u=trial;accepted=True;break
        if not accepted:raise RuntimeError('PB line search stagnation')
    raise RuntimeError('PB iteration budget exhausted')

def bar_conductance(mu=.135,density=1e21,area=1e-12,length=1e-6):
    mu=real(mu,'mu',1e-6,10);n=real(density,'density',1e16,1e25);A=real(area,'area',1e-18,1e-4);L=real(length,'length',1e-9,1)
    return Q*mu*n*A/L

def fit_origin(voltages,currents):
    v=vector(voltages,'voltage',-1,1,2);i=vector(currents,'current',-1,1,2)
    if len(v)!=len(i):raise ValueError('fit shape')
    scale=max(abs(x) for x in v)
    if scale<1e-9:raise ValueError('insufficient voltage excitation')
    den=math.fsum((x/scale)**2 for x in v);G=math.fsum((x/scale)*y for x,y in zip(v,i))/(scale*den)
    if not math.isfinite(G) or G<=0:raise ValueError('nonpositive conductance fit')
    res=[y-G*x for x,y in zip(v,i)]
    return {'G_S':G,'residual_A':res,'rms_residual_A':math.sqrt(math.fsum(x*x for x in res)/len(res)),'identifiable':'G only; mu and density not separated'}

def generate(output):
    out=new_output(output)
    x=[i*1e-6/16 for i in range(17)];constant=poisson(x,[1.]*17)
    manufactured=[]
    for N in [8,16,32,64]:manufactured.append({'cells':N,**equilibrium_case(N)})
    vt=KB*300/Q;potential=[vt*math.log(2)*i/16 for i in range(17)]
    G=bar_conductance();vs=[.01,.02,.04];Is=[G*v for v in vs]
    data={'scope':'CPU finite cases; no professional TCAD/SPICE/PDK run','constants_SI':{'q_C':Q,'k_J_K':KB,'eps0_F_m':EPS0},'fixed_charge_poisson':constant,'PB_mesh':manufactured,'transport':transport(x,potential),'compact_bar':{'V_V':vs,'I_A':Is,'G_S':G,'equivalent_G_S':bar_conductance(mu=.0675,density=2e21),'fit':fit_origin(vs,Is)}}
    out.mkdir(parents=True);(out/'results.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv);generate(args.output)
if __name__=='__main__':main()
