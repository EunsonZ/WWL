"""Finite CPU teaching models; pure import, no dependencies, argv, plotting or I/O."""
import math

def real(v,name,lo,hi):
    if type(v) not in (int,float): raise ValueError(name+' requires Python real scalar, not bool/complex/object/container')
    try: x=float(v)
    except (OverflowError,ValueError): raise ValueError(name+' not representable') from None
    if not math.isfinite(x) or not lo<=x<=hi: raise ValueError(name+' outside teaching domain')
    return x

def integer(v,name,lo,hi):
    if type(v) is not int or not lo<=v<=hi: raise ValueError(name+' requires bounded integer')
    return v

def vector(x,name,lo,hi,minn,maxn):
    if type(x) not in (list,tuple) or not minn<=len(x)<=maxn: raise ValueError(name+' requires finite bounded flat list/tuple')
    return [real(v,name,lo,hi) for v in x]

def static_metrics(thresholds,vmin,vmax,bits):
    bits=integer(bits,'bits',2,8);vmin=real(vmin,'vmin',-1000,1000);vmax=real(vmax,'vmax',-1000,1000)
    span=vmax-vmin
    if not 1e-3<=span<=1000: raise ValueError('span outside .001..1000 V')
    m=2**bits; t=vector(thresholds,'thresholds',vmin,vmax,m-1,m-1)
    if any(t[i+1]<t[i] for i in range(len(t)-1)) or not t[-1]>t[0]: raise ValueError('ordered monotonic thresholds with positive endpoint span required')
    delta=span/m; fitted=(t[-1]-t[0])/(m-2)
    return {'delta_V':delta,'offset_V':t[0]-(vmin+delta),'endpoint_step_V':fitted,'gain_error_relative':fitted/delta-1,
            'raw_transition_inl_LSB':[(v-(vmin+(i+1)*delta))/delta for i,v in enumerate(t)],
            'endpoint_transition_inl_LSB':[(v-(t[0]+i*fitted))/delta for i,v in enumerate(t)],
            'internal_dnl_LSB':[(t[i+1]-t[i])/delta-1 for i in range(m-2)],
            'missing_internal_codes':[i+1 for i in range(m-2) if t[i+1]==t[i]]}

def one_sided_power(samples):
    x=vector(samples,'samples',-10,10,16,256);n=len(x)
    if n%2: raise ValueError('even N required')
    powers=[]
    for k in range(n//2+1):
        re=math.fsum(x[j]*math.cos(2*math.pi*k*j/n) for j in range(n))/n
        im=-math.fsum(x[j]*math.sin(2*math.pi*k*j/n) for j in range(n))/n
        powers.append((re*re+im*im)*(1 if k in (0,n//2) else 2))
    return powers

def coherent_metrics(samples,fundamental_bin,harmonic_orders=(2,3,4,5),fullscale_peak=1.0):
    fullscale_peak=real(fullscale_peak,'fullscale_peak',.01,10)
    n=len(samples) if type(samples) in (list,tuple) else 0
    m=integer(fundamental_bin,'fundamental_bin',1,max(1,n//2-1)); p=one_sided_power(samples)
    if max(abs(v) for v in samples)>fullscale_peak: raise ValueError('record exceeds declared rails')
    orders=vector(harmonic_orders,'harmonic orders',2,10,1,9)
    if any(int(h)!=h for h in orders): raise ValueError('integer harmonic orders required')
    bins=set()
    for h in orders:
        k=(int(h)*m)%n;k=min(k,n-k)
        if k in (0,m): raise ValueError('harmonic collides with DC/fundamental; change coherent record')
        bins.add(k)
    signal=p[m]
    if signal<1e-12: raise ValueError('fundamental below declared record power floor')
    residual=math.fsum(v for k,v in enumerate(p) if k not in (0,m))
    distortion=math.fsum(p[k] for k in bins)
    noise=math.fsum(v for k,v in enumerate(p) if k not in ({0,m}|bins))
    spur=max(v for k,v in enumerate(p) if k not in (0,m))
    floor=signal*1e-18
    ratio=lambda err: 10*math.log10(signal/err) if err>floor else None
    sinad=ratio(residual)
    return {'signal_V2':signal,'residual_V2':residual,'harmonic_V2':distortion,'nonharmonic_residual_V2':noise,'largest_spur_V2':spur,
            'SNR_dB':ratio(noise),'SINAD_dB':sinad,'SFDR_dBc':ratio(spur),'THD_dB':-ratio(distortion) if distortion>floor else None,
            'ENOB_from_SINAD':(sinad-1.76)/6.02 if sinad is not None else None,'ENOB_amplitude_normalized':(sinad-1.76+20*math.log10(fullscale_peak/math.sqrt(2*signal)))/6.02 if sinad is not None else None,'fullscale_peak_V':fullscale_peak,'harmonic_bins':sorted(bins),'analysis_floor_relative_power':1e-18,
            'floor_semantics':'None means below declared analysis floor, not physical zero noise; coherent rectangular record required'}

def band_variance(delta,osr,shaped=False):
    delta=real(delta,'delta',1e-6,10);osr=integer(osr,'osr',1,256)
    if type(shaped) is not bool: raise ValueError('shaped requires bool')
    a=math.pi/osr
    return delta*delta/(6*math.pi)*(a-math.sin(a)) if shaped else delta*delta/(12*osr)

def sigma_delta_dc(x,count):
    x=real(x,'x',-.95,.95);count=integer(count,'count',16,65536)
    v=0.;previous_y=1.;initial_e=1.;bits=[];states=[];errors=[]
    for _ in range(count):
        v+=x-previous_y; y=1. if v>=0 else -1.
        if not x-1-1e-10<=v<=x+1+1e-10: raise ValueError('state invariant failed')
        bits.append(y);states.append(v);errors.append(y-v);previous_y=y
    return {'bits':bits,'states':states,'errors':errors,'initial_e':initial_e,'mean':math.fsum(bits)/count}

def block_average(samples,m):
    x=vector(samples,'samples',-10,10,1,65536);m=integer(m,'m',1,256)
    if len(x)%m: raise ValueError('complete valid blocks required')
    return [math.fsum(x[i:i+m])/m for i in range(0,len(x),m)]

def zoh_normalized(f,fd):
    f=real(f,'f',0,1e9);fd=real(fd,'fd',1,1e9);r=f/fd
    if r>10000: raise ValueError('frequency ratio >10000')
    if r==0: return complex(1,0)
    a=math.pi*r;sinc=math.sin(a)/a
    return sinc*complex(math.cos(a),-math.sin(a))

def jitter_snr(fin,sigma):
    fin=real(fin,'fin',1,1e9);sigma=real(sigma,'sigma',1e-15,1e-6)
    x=2*math.pi*fin*sigma
    if x>.05: raise ValueError('small-jitter model requires 2*pi*fin*sigma<=.05')
    return -20*math.log10(x)

def sine_timing_error(amplitude,fin,t,dt):
    amplitude=real(amplitude,'amplitude',1e-6,10);fin=real(fin,'fin',1,1e9);t=real(t,'t',0,1);dt=real(dt,'dt',-1e-3,1e-3)
    if fin*t>1e6 or abs(fin*dt)>.01: raise ValueError('bounded phase/time perturbation required')
    theta=2*math.pi*fin*t;d=2*math.pi*fin*dt
    return 2*amplitude*math.cos(theta+d/2)*math.sin(d/2)

def phase_jitter(nodes,carrier):
    carrier=real(carrier,'carrier',1e3,1e9)
    if type(nodes) not in (list,tuple) or not 2<=len(nodes)<=16: raise ValueError('2..16 phase-noise nodes required')
    vals=[]
    for pair in nodes:
        if type(pair) not in (list,tuple) or len(pair)!=2: raise ValueError('nodes are [offset_Hz,L_dBc_per_Hz]')
        vals.append((real(pair[0],'offset',1,1e9),real(pair[1],'L',-220,-40)))
    areas=[]
    for (f1,l1),(f2,l2) in zip(vals,vals[1:]):
        if f2/f1<1.01: raise ValueError('strict offset ordering with >=1.01 ratio required')
        logr=math.log(f2/f1);alpha=(l2-l1)*math.log(10)/10/logr;q=alpha+1
        area=10**(l1/10)*f1*(logr if q==0 else math.expm1(q*logr)/q)
        areas.append(area)
    variance=2*math.fsum(areas)
    if not 0<variance<=.1: raise ValueError('small-angle phase variance must be <=.1 rad^2')
    return {'SSB_linear_areas':areas,'phase_variance_rad2':variance,'phase_rms_rad':math.sqrt(variance),'time_rms_s':math.sqrt(variance)/(2*math.pi*carrier),'integration_Hz':[vals[0][0],vals[-1][0]]}

def pll_coefficients(a,b):
    a=real(a,'a',.01,1e7);b=real(b,'b',1e-4,1e14);wn=math.sqrt(b);zeta=a/(2*wn)
    if not .05<=zeta<=10: raise ValueError('teaching damping .05..10 required')
    disc=a*a-4*b
    if disc>=0:
        q=-(a+math.sqrt(disc))/2;poles=(complex(q,0),complex(b/q,0))
    else:poles=(complex(-a/2,math.sqrt(-disc)/2),complex(-a/2,-math.sqrt(-disc)/2))
    wc=math.sqrt((a*a+math.sqrt(a**4+4*b*b))/2)
    return {'omega_n_rad_s':wn,'zeta':zeta,'poles':poles,'omega_c_rad_s':wc,'PM_rad':math.atan(a*wc/b)}

def pll_transfer(a,b,omega):
    pll_coefficients(a,b);omega=real(omega,'omega',0,1e9)
    den=complex(b-omega*omega,a*omega)
    return {'T':complex(b,a*omega)/den,'S':complex(-omega*omega,0)/den}
