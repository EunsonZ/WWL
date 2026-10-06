"""Bounded teaching models. Import uses only math; no plotting, argv or I/O."""
import math

def scalar(value, name, lo, hi):
    if type(value) not in (int, float):
        raise ValueError(name + " must be a real scalar, not bool/complex/container")
    try: v = float(value)
    except (OverflowError, ValueError): raise ValueError(name + " is not representable") from None
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(name + " outside teaching domain")
    return v

def triple_loop(k, omega, p=1.0):
    k=scalar(k,'k',0,100); omega=scalar(omega,'omega',-1e9,1e9); p=scalar(p,'p',1e-3,1e6)
    return k/(1+1j*omega/p)**3

def triple_poles(k, p=1.0):
    k=scalar(k,'k',0,100); p=scalar(p,'p',1e-3,1e6)
    q=k**(1/3)
    return (complex(p*(-1-q),0), complex(p*(-1+q/2),p*math.sqrt(3)*q/2), complex(p*(-1+q/2),-p*math.sqrt(3)*q/2))

def triple_routh(k):
    k=scalar(k,'k',0,100)
    return (1.0,3.0,(8-k)/3,1+k)

def injection(p, c, r=0.0, di=0.0, do=0.0, n=0.0):
    p=scalar(p,'p',0,100); c=scalar(c,'c',0,100)
    r,di,do,n=[scalar(v,name,-1e4,1e4) for v,name in zip((r,di,do,n),('r','di','do','n'))]
    s=1/(1+p*c); t=p*c*s
    y=t*r+p*s*di+s*do-t*n
    u=c*s*r-t*di-c*s*do-c*s*n
    return {'y':y,'u':u,'S':s,'T':t,'PS':p*s,'CS':c*s}

def lead_beta(rf, rg, cf, omega):
    rf=scalar(rf,'rf',1,1e7); rg=scalar(rg,'rg',1,1e7); cf=scalar(cf,'cf',1e-12,1e-3); omega=scalar(omega,'omega',0,1e9)
    return rg/(rf+rg)*(1+1j*omega*rf*cf)/(1+1j*omega*(rf*rg/(rf+rg))*cf)

def isolated_load(riso, rl, cl, omega):
    riso=scalar(riso,'riso',1,1e6); rl=scalar(rl,'rl',1,1e7); cl=scalar(cl,'cl',1e-12,1e-2); omega=scalar(omega,'omega',0,1e9)
    return rl/(riso+rl)/(1+1j*omega*(riso*rl/(riso+rl))*cl)

def wien_beta(r,c,omega):
    r=scalar(r,'r',1,1e7); c=scalar(c,'c',1e-12,1e-3); omega=scalar(omega,'omega',0,1e9)
    z=1j*omega*r*c
    return z/(z*z+3*z+1)

def radius(t, r0, mu, alpha):
    t=scalar(t,'t',0,100); r0=scalar(r0,'r0',0,100); mu=scalar(mu,'mu',-100,100); alpha=scalar(alpha,'alpha',1e-4,100)
    if r0!=0 and r0<1e-6: raise ValueError('nonzero r0 must be >=1e-6 V')
    if mu!=0 and abs(mu)<1e-6: raise ValueError('nonzero abs(mu) must be >=1e-6 /s')
    # Restrict time exponent before evaluating; no underflow disguised as exact state.
    if abs(mu*t)>100: raise ValueError('abs(mu*t) must be <=100')
    if r0==0: return 0.0
    if mu==0: return r0/math.sqrt(1+2*alpha*r0*r0*t)
    if mu>0:
        e=math.exp(-2*mu*t)
        return r0/math.sqrt(e+(alpha*r0*r0/mu)*(-math.expm1(-2*mu*t)))
    e=math.exp(2*mu*t)
    return r0*math.sqrt(e)/math.sqrt(1+(alpha*r0*r0/(-mu))*(-math.expm1(2*mu*t)))

def nested_poles(a,d,b,c):
    a=scalar(a,'a',1e-3,1e6); d=scalar(d,'d',1e-3,1e6); b=scalar(b,'b',-1e6,1e6); c=scalar(c,'c',-1e6,1e6)
    disc=complex((a-d)**2+4*b*c,0)**0.5
    return ((-a-d+disc)/2,(-a-d-disc)/2)

def delay_limit(k,p):
    k=scalar(k,'k',1.0001,100); p=scalar(p,'p',1e-3,1e6)
    x=math.sqrt(k*k-1); wc=p*x
    return {'omega_c':wc,'tau_critical':(math.pi-math.atan(x))/wc}

def delay_phase_crossings(p,tau,wmax,budget=100):
    p=scalar(p,'p',1e-3,1e6); tau=scalar(tau,'tau',1e-9,10); wmax=scalar(wmax,'wmax',1e-3,1e9)
    if type(budget) is not int or not 1<=budget<=1000: raise ValueError('budget integer 1..1000')
    theta=math.atan(wmax/p)+wmax*tau
    count=max(0,math.floor((theta/math.pi-1)/2)+1)
    if count>budget: raise ValueError('crossing budget exceeded; raise bound deliberately')
    roots=[]
    for m in range(count):
        target=(2*m+1)*math.pi; lo=0.0; hi=wmax
        for _ in range(80):
            mid=(lo+hi)/2
            if math.atan(mid/p)+mid*tau < target: lo=mid
            else: hi=mid
        w=(lo+hi)/2
        if abs(math.atan(w/p)+w*tau-target)>1e-10*max(1,target): raise ValueError('phase root resolution insufficient')
        roots.append(w)
    return roots

def robust_onepole(k,w):
    k=scalar(k,'k',0,100); w=scalar(w,'w',0,100)
    return w*k/(1+k)  # analytic H-infinity norm, not sampled maximum

def triple_step(k,t,p=1.0):
    """Zero-state unit step; t=0 or .01<=p*t<=20, .1<=K<=30."""
    k=scalar(k,'k',.1,30); t=scalar(t,'t',0,2e4); p=scalar(p,'p',1e-3,1e6)
    x=p*t
    if t==0: return 0.0
    if not .01<=x<=20: raise ValueError('step requires .01<=p*t<=20, or t=0')
    value=complex(k/(1+k),0)
    for z in triple_poles(k):
        # z is a normalized pole s/p; evaluate all terms at theta=p*t.
        residue=k/(z*3*(z+1)**2)
        value += residue*complex(math.cos(z.imag*x),math.sin(z.imag*x))*math.exp(z.real*x)
    if abs(value.imag)>1e-10*max(1,abs(value.real)): raise ValueError('conjugate residual failed')
    return value.real
