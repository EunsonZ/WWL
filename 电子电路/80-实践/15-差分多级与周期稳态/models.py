"""Teaching models, SI units; no dependency imports or output during import."""
import math
import numbers

def real(x, name='value', positive=False, nonnegative=False):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise TypeError(name + ': finite real scalar required')
    x = float(x)
    if not math.isfinite(x): raise ValueError(name + ': nonfinite')
    if positive and x <= 0: raise ValueError(name + ': positive required')
    if nonnegative and x < 0: raise ValueError(name + ': nonnegative required')
    return x

def finite(x):
    if isinstance(x, complex):
        if not (math.isfinite(x.real) and math.isfinite(x.imag)): raise OverflowError('derived complex nonfinite')
    elif not math.isfinite(x): raise OverflowError('derived nonfinite')
    return x

def count(x, name):
    if isinstance(x, bool) or not isinstance(x, int): raise TypeError(name + ': integer required')
    if x <= 0 or x > 1000000: raise ValueError(name + ': budget outside 1..1000000')
    return x

def mos_steering(vd, tail, beta):
    vd=real(vd); tail=real(tail,positive=True); beta=real(beta,positive=True)
    limit=finite(math.sqrt(finite(2*tail/beta)))
    if abs(vd)>=limit: return (tail,0.) if vd>0 else (0.,tail)
    z=math.sqrt(max(0.,finite(tail/beta-vd*vd/4)))
    v=abs(vd)
    small_u=finite((limit-v)*(limit+v)/(2*(z+v/2)))
    small=finite(beta/2*small_u*small_u)
    large=finite(tail-small)
    return (large,small) if vd>=0 else (small,large)

def bjt_steering(vd, tail, vt):
    vd=real(vd); tail=real(tail,positive=True); vt=real(vt,positive=True)
    ratio=finite(abs(vd)/vt)
    e=math.exp(-ratio)
    small=finite(math.exp(math.log(tail)-ratio-math.log1p(e))); large=finite(tail-small)
    return (large,small) if vd>=0 else (small,large)

def differential(gm, rd, rt, ro=None, mismatch=0.):
    gm=real(gm,positive=True); rd=real(rd,positive=True); rt=real(rt,positive=True)
    # infinity is not an input convention: omit ro for the explicit ideal-ro model.
    if ro is None: go=0.
    else: go=finite(1/real(ro,positive=True))
    delta=real(mismatch)
    if abs(delta)>=1: raise ValueError('load mismatch magnitude must be below 1')
    gd=1/rd
    ad=finite(-gm/(gd+go))
    ac=finite(-gm/finite(gd+go+2*gd*rt*(gm+go)))
    if go and delta: raise ValueError('mismatch formula here requires ideal ro')
    return {'ad_differential':ad,'ad_single':finite(ad/2*(1+delta)),
            'ac_single':finite(ac*(1+delta)),'ad_single_nominal':ad/2,'ac_single_nominal':ac,
            'ac_differential':finite(2*delta*ac),
            'cmrr_single':finite(abs(ad/2/ac))}

def cascade(a1, rout1, rin2, a2, rout2, load):
    a1=real(a1); a2=real(a2)
    rout1=real(rout1,positive=True); rin2=real(rin2,positive=True)
    rout2=real(rout2,positive=True); load=real(load,positive=True)
    return finite(a1*finite(rin2/finite(rout1+rin2))*a2*finite(load/finite(rout2+load)))

def cascode(gm1,gm2,ro1,ro2,load):
    gm1=real(gm1,positive=True); gm2=real(gm2,positive=True)
    ro1=real(ro1,positive=True); ro2=real(ro2,positive=True); load=real(load,positive=True)
    rout=finite(ro1+ro2+finite(gm2*ro1*ro2))
    gme=finite(gm1*(gm2+1/ro2)/(gm2+1/ro1+1/ro2))
    gain=finite(-gme/(1/rout+1/load))
    return rout,gme,gain

def cgd_coefficients(rg,rout,gm,cgs,cgd,co):
    rg=real(rg,positive=True); rout=real(rout,positive=True); gm=real(gm,positive=True)
    cgs=real(cgs,positive=True); cgd=real(cgd,positive=True); co=real(co,nonnegative=True)
    b1=finite(rout*(co+cgd)+rg*(cgs+cgd)+gm*rg*rout*cgd)
    b2=finite(rg*rout*(cgs*co+cgd*(cgs+co)))
    if b2<=0: raise ArithmeticError('derived capacitance coefficient underflow')
    disc=finite(b1*b1-4*b2)
    if disc<0: raise ArithmeticError('real-pole model condition violated')
    slow=finite((b1+math.sqrt(disc))/2); fast=finite(b2/slow)
    if fast<=0: raise ArithmeticError('derived pole time underflow')
    return b1,b2,slow,fast,finite(gm/cgd)

def cgd_response_s(s,rg,rout,gm,cgs,cgd,co):
    if isinstance(s,bool) or not isinstance(s,numbers.Complex): raise TypeError('s: numeric complex scalar required')
    s=finite(complex(s))
    b1,b2,_,_,_=cgd_coefficients(rg,rout,gm,cgs,cgd,co)
    den=finite(1+b1*s+b2*s*s)
    if den==0: raise ZeroDivisionError('response evaluated on pole')
    return finite(-gm*rout*(1-s*cgd/gm)/den)

def class_b(vm,rail,load):
    vm=real(vm,nonnegative=True); rail=real(rail,positive=True); load=real(load,positive=True)
    if vm>rail: raise ValueError('ideal sine peak exceeds rail')
    pout=finite(vm*vm/finite(2*load)); pdc=finite(finite(2*rail*vm)/finite(math.pi*load))
    return pout,pdc,0. if vm==0 else finite(math.pi/4*(vm/rail))

def crossover(v,threshold):
    v=real(v); threshold=real(threshold,nonnegative=True)
    return math.copysign(max(abs(v)-threshold,0),v)

def harmonics(amplitude,threshold,steps=4096):
    amplitude=real(amplitude,positive=True); threshold=real(threshold,nonnegative=True); steps=count(steps,'steps')
    if steps<32: raise ValueError('at least 32 samples required')
    ans=[]
    for n in (1,3,5):
        ans.append(finite(2/steps*math.fsum(crossover(amplitude*math.sin(2*math.pi*k/steps),threshold)*math.sin(n*2*math.pi*k/steps) for k in range(steps))))
    return tuple(ans)

def thermal_idle(iq0,rail,re,kappa,theta):
    iq0=real(iq0,positive=True); rail=real(rail,positive=True); re=real(re,positive=True)
    kappa=real(kappa,positive=True); theta=real(theta,positive=True)
    loop=finite(theta*2*rail*kappa/re)
    if loop>=1: raise ValueError('thermal linear equilibrium not stable in this model')
    iq=finite(iq0/(1-loop)); power=finite(2*rail*iq)
    return iq,power,finite(theta*power),loop

def coupling(t,e0,amp,f,rs,rl,c,initial=None):
    t=real(t,nonnegative=True); e0=real(e0); amp=real(amp); f=real(f,positive=True)
    rs=real(rs,positive=True); rl=real(rl,positive=True); c=real(c,positive=True)
    tau=finite(c*finite(rs+rl)); w=finite(2*math.pi*f); x=finite(w*tau)
    if tau<=0: raise ValueError('coupling: time constant not representable')
    phase=finite(w*t); u=finite(t/tau)
    if not (1e-150<=x<=1e150 and phase<=1e12 and u<=1e6 and max(rs/rl,rl/rs)<=1e12):
        raise ValueError('coupling: outside documented dimensionless numerical domain')
    if t>0 and (phase==0 or u==0): raise ValueError('coupling: time coordinate underflow')
    den=finite(1+x*x)
    # Normalize dimensionless harmonic weights before multiplying amplitude.
    low=1/den; cross=x/den; high=x*x/den
    ac_periodic=finite(amp*(low*math.sin(phase)-cross*math.cos(phase)))
    if initial is None:
        # Load is an independent AC coordinate, not large-total subtraction.
        vc=finite(e0+ac_periodic)
        vb=finite(rl/(rs+rl)*amp*(high*math.sin(phase)+cross*math.cos(phase)))
        return vc,vb
    initial=real(initial)
    decay=math.exp(-u); one_minus=-math.expm1(-u)
    def scaled_decay(value):
        if value==0: return 0.
        if u<=700: return finite(value*decay)
        return finite(math.copysign(math.exp(math.log(abs(value))-u),value))
    if u<=.1 and abs(phase)<=.1:
        # Source-only startup convolution solves dy/du+y=A sin(xu), y(0)=0.
        # q[n+1]=u*(s[n]-q[n])/(n+1), s[n] is the nth sine term.
        # Fixed 40-term budget; no subtraction of the equal first-order terms.
        q=0.; sine_term=finite(amp*phase); terms=[]
        for n in range(1,40):
            forcing=sine_term if n%2 else 0.
            q=finite(u/(n+1)*(forcing-q)); terms.append(q)
            if n%2: sine_term=finite(-sine_term*phase*phase/((n+1)*(n+2)))
        ac_start=finite(math.fsum(terms))
    else:
        ac_start=finite(amp*(low*math.sin(phase)+cross*(2*math.sin(phase/2)**2-one_minus)))
    vc=finite(math.fsum((scaled_decay(initial),e0*one_minus,ac_start)))
    vb=finite(rl/(rs+rl)*math.fsum((scaled_decay(e0),-scaled_decay(initial),amp*math.sin(phase),-ac_start)))
    return vc,vb

def legacy_periodic(t,a,f,c):
    """Old 20/03 saturation candidate, not a switched-region device simulator."""
    t=real(t,nonnegative=True); a=real(a,nonnegative=True); f=real(f,positive=True); c=real(c,positive=True)
    if a>=1: raise ValueError('requires a<1 V')
    w=finite(2*math.pi*f); x=finite(w*c*12000); phase=finite(w*t)
    d1=finite(1+x*x); d2=finite(1+4*x*x)
    vc=finite(3-a*a-4*a/d1*(math.sin(phase)-x*math.cos(phase)) + a*a/d2*(math.cos(2*phase)+2*x*math.sin(2*phase)))
    vi=a*math.sin(phase); current=.001*(1+vi)**2
    vd=finite((5/2000+vc/10000-current)/(1/2000+1/10000))
    return vc,vd,finite(vd-(1+vi))

def periodic_rk4(a,f,c,steps=512,max_cycles=200,tol=1e-8):
    a=real(a,nonnegative=True); f=real(f,positive=True); c=real(c,positive=True)
    if a>.5: raise ValueError('RK4 supported amplitude is 0..0.5 V')
    steps=count(steps,'steps'); max_cycles=count(max_cycles,'max_cycles'); tol=real(tol,positive=True)
    if steps*max_cycles>1000000: raise ValueError('total step budget exceeds 1000000')
    tau=finite(c*12000); h=finite(1/(f*steps))
    if h/tau>.1: raise ValueError('step too large for RK4 evidence')
    omega=finite(2*math.pi*f)
    x=finite(omega*tau)
    if not (.1<=x<=10 and 512<=steps<=4096 and 1e-9<=tol<=1e-4):
        raise ValueError('RK4 supported domain: 0.1<=omega*tau<=10, 512..4096 steps, 1e-9..1e-4 V tolerance')
    # Analytic reference checks each returned sample; tolerance is sampled
    # state error, not one-cycle delta and not an all-time interval proof.
    contraction_loss=-math.expm1(-1/(f*tau))
    rounding_guard=finite(64*math.ulp(1.)*steps*8/contraction_loss)
    def rhs(t,v):
        return finite((5-2*(1+a*math.sin(omega*t))**2-v)/tau)
    vc=3.; previous=None
    for cycle in range(max_cycles):
        start=vc; points=[]
        for k in range(steps):
            t=k*h; points.append(vc)
            k1=rhs(t,vc); k2=rhs(t+h/2,vc+h*k1/2); k3=rhs(t+h/2,vc+h*k2/2); k4=rhs(t+h,vc+h*k3)
            vc=finite(vc+h/6*(k1+2*k2+2*k3+k4))
        residual=abs(vc-start)
        sampled_error=max(abs(v-legacy_periodic(k*h,a,f,c)[0]) for k,v in enumerate(points))
        estimate=finite(sampled_error+rounding_guard)
        if estimate<=tol: return points,cycle+1,estimate
        if previous is not None and residual>=previous and residual>tol: raise ArithmeticError('iteration stagnated')
        previous=residual
    raise RuntimeError('cycle budget exhausted before periodic closure')
