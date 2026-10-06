"""Finite positive-parameter teaching models; SI inputs, explicit common-frequency RMS."""
import math, cmath

def positive(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
        raise ValueError(f'{name} must be finite and positive')
    return float(value)

def rc(w,r=1000,c=1e-6,rs=0,rl=None):
    w=positive(w,'angular frequency');r=positive(r,'R');c=positive(c,'C')
    if isinstance(rs,bool) or not isinstance(rs,(int,float)) or not math.isfinite(rs) or rs<0:raise ValueError('Rs must be finite and nonnegative')
    g=0 if rl is None else 1/positive(rl,'RL')
    h=1/(1+(r+rs)*g+1j*w*(r+rs)*c)
    i=(1-h)/(r+rs);ic=1j*w*c*h;il=g*h
    return {'H':h,'I_A':i,'IC_A':ic,'IL_A':il,'tau_s':c/(1/(r+rs)+g),'K':1/(1+(r+rs)*g)}

def resonance(l=.01,c=1e-6,r=50,parallel=False):
    l=positive(l,'L');c=positive(c,'C');r=positive(r,'R');w0=1/math.sqrt(l*c)
    bw=1/(r*c) if parallel else r/l;q=w0/bw
    center=math.sqrt(w0*w0+(bw/2)**2)
    return {'w0_rad_s':w0,'Q':q,'bandwidth_rad_s':bw,'lo_rad_s':center-bw/2,'hi_rad_s':center+bw/2}

def series(w,l=.01,c=1e-6,r=50):
    positive(w,'angular frequency');positive(l,'L');positive(c,'C');positive(r,'R')
    z=r+1j*(w*l-1/(w*c));return {'Z_ohm':z,'HR':r/z,'HC':(1/(1j*w*c))/z,'HL':(1j*w*l)/z}

def parallel(w,l=.01,c=1e-6,r=200):
    positive(w,'angular frequency');positive(l,'L');positive(c,'C');positive(r,'R')
    return 1/(1/r+1j*(w*c-1/(w*l)))

def rc_step(t,v0=.4,tau=.001,k=1,input_v=1):
    if not math.isfinite(t) or t<0:raise ValueError('t must be finite and nonnegative')
    positive(tau,'tau');return k*input_v+(v0-k*input_v)*math.exp(-t/tau)

def inverse(q,case):
    if not math.isfinite(q):raise ValueError('q must be finite')
    if q<0:return 0.0
    if case=='distinct':return math.exp(-q)-math.exp(-2*q)
    if case=='repeated':return (1+2*q)*math.exp(-q)
    if case=='conjugate':return math.exp(-q)*math.cos(2*q)
    if case=='step':return .5-math.exp(-q)+.5*math.exp(-2*q)
    if case=='delay':return inverse(q-.5,'distinct')
    if case=='rhp_step':return 1-(1+2*q)*math.exp(-q)
    if case=='rhp_impulse':return (2*q-1)*math.exp(-q)
    raise ValueError('unknown inverse case')

def mid_integral(f,a,b,n=4000):
    if isinstance(n,bool) or not isinstance(n,int) or n<1:raise ValueError('n must be a positive integer')
    if not math.isfinite(a) or not math.isfinite(b) or b<a:raise ValueError('invalid bounds')
    dt=(b-a)/n;return dt*sum(f(a+(k+.5)*dt) for k in range(n))

def power_rc(n=4000):
    w=1000;I=rc(w)['I_A'];T=2*math.pi/w
    def pair(t):
        e=cmath.exp(1j*w*t);v=math.sqrt(2)*e.real;i=math.sqrt(2)*(I*e).real;vc=math.sqrt(2)*(rc(w)['H']*e).real
        return v,i,vc
    avg=mid_integral(lambda t:pair(t)[0]*pair(t)[1],0,T,n)/T
    pr=mid_integral(lambda t:pair(t)[1]**2*1000,0,T,n)/T
    pc=mid_integral(lambda t:pair(t)[2]*pair(t)[1],0,T,n)/T
    return {'P_network_W':avg,'P_resistor_W':pr,'P_capacitor_W':pc,'S_network_VA':I.conjugate()}
