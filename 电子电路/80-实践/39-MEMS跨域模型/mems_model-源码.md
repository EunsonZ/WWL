---
stage: 1
aliases: []
sources: []
prerequisites: []
---
# mems_model 真源镜像

<!-- code-sync: 电子电路/80-实践/39-MEMS跨域模型/mems_model.py -->
```python
"""Finite-domain teaching models, SI throughout; no optional imports or I/O."""
import math
from numbers import Real

KB = 1.380649e-23
EPS = 8.8541878128e-12
G0 = 9.80665

def real(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, Real):
        raise ValueError(name + ' must be real, not bool/complex/text')
    try:
        v = float(v)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(name + " cannot convert to finite real") from exc
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(name + ' outside finite teaching domain')
    return v

def mechanics(m=9.32e-10, f0=1000., zeta=.7):
    m=real(m,'m',1e-12,1e-3); f0=real(f0,'f0',1.,1e6); zeta=real(zeta,'zeta',0.,10.)
    w=2*math.pi*f0
    return {'m':m,'w0':w,'k':m*w*w,'b':2*zeta*m*w,'zeta':zeta}

def displacement(a, f=0., m=9.32e-10, f0=1000., zeta=.7, feedback=0.):
    p=mechanics(m,f0,zeta); a=real(a,'a',-1e5,1e5); f=real(f,'f',0.,1e7)
    feedback=real(feedback,'feedback N/m',0.,1e9); w=2*math.pi*f
    d=complex(p['k']+feedback-p['m']*w*w,p['b']*w)
    if d == 0: raise ValueError('undamped resonance has no finite steady response')
    result=-p['m']*a/d
    if not (math.isfinite(result.real) and math.isfinite(result.imag)):
        raise ValueError('displacement result exceeds finite complex output')
    return result

def state_rhs(x, velocity, a, force=0., m=9.32e-10, f0=1000., zeta=.7):
    p=mechanics(m,f0,zeta); x=real(x,'x',-1.,1.); velocity=real(velocity,'velocity',-1e4,1e4)
    a=real(a,'a',-1e5,1e5); force=real(force,'force',-1e3,1e3)
    return velocity, (-p['b']*velocity-p['k']*x-p['m']*a+force)/p['m']

def capacitors(x, gap=2e-6, area=4e-8, parasitic=0.):
    gap=real(gap,'gap',1e-9,1e-2); area=real(area,'area',1e-14,1e-2)
    x=real(x,'x',-1.,1.); parasitic=real(parasitic,'equal parasitic',0.,1e-3)
    if abs(x)>=gap: raise ValueError('gap contact: |x| must be < gap')
    cp=EPS*area/(gap-x); cm=EPS*area/(gap+x)
    return {'plus':cp+parasitic,'minus':cm+parasitic,'difference':cp-cm,
            'ratio':(cp-cm)/(cp+cm+2*parasitic)}

def bridge(delta, supply=1.):
    delta=real(delta,'delta',-.95,.95); supply=real(supply,'supply',0.,20.)
    # s-a: R(1+delta); a-0: R(1-delta); s-b opposite; b-0 opposite.
    va=supply*(1-delta)/2; vb=supply*(1+delta)/2
    return {'va':va,'vb':vb,'vo':vb-va,'common':supply/2}

def beam_strain(x, length=200e-6, thickness=2e-6):
    x=real(x,'tip displacement',-1.,1.); length=real(length,'length',1e-6,.1)
    thickness=real(thickness,'thickness',1e-9,.01)
    if thickness/length>.1 or abs(x)/length>.05:
        raise ValueError('slender small-deflection beam domain exceeded')
    return 3*thickness*x/(2*length*length)

def thermal(temperature=300., bandwidth=100., m=9.32e-10, f0=1000., zeta=.7):
    p=mechanics(m,f0,zeta); temperature=real(temperature,'T',1.,2000.)
    bandwidth=real(bandwidth,'rectangular input-equivalent bandwidth',0.,1e6)
    sf=4*KB*temperature*p['b']; sa=sf/(p['m']*p['m'])
    return {'force_psd':sf,'accel_asd':math.sqrt(sa),'accel_rms':math.sqrt(sa*bandwidth),
            'equilibrium_x_variance':KB*temperature/p['k']}

def calibrate(y, scale, bias=0., cross=0., transverse=0.):
    y=real(y,'y V',-100.,100.); scale=real(scale,'scale V/(m/s2)',-100.,100.)
    if scale==0: raise ValueError('zero scale cannot be inverted')
    bias=real(bias,'bias V',-100.,100.); cross=real(cross,'cross V/(m/s2)',-100.,100.)
    transverse=real(transverse,'transverse m/s2',-1e5,1e5)
    result=(y-bias-cross*transverse)/scale
    if not math.isfinite(result): raise ValueError("calibration result exceeds finite output")
    return result

def feedback_static(a, gain, force_limit, m=9.32e-10, f0=1000., zeta=.7):
    p=mechanics(m,f0,zeta); a=real(a,'a',-1e5,1e5)
    gain=real(gain,'K N/m',0.,1e9); limit=real(force_limit,'Fmax N',0.,1e3)
    x=-p['m']*a/(p['k']+gain)
    force=max(-limit,min(limit,-gain*x))
    saturated=abs(gain*x)>limit
    if saturated: x=(force-p['m']*a)/p['k']
    return {'x':x,'force':force,'estimate':force/p['m'],'saturated':saturated}

def vibration_bias(amplitude, quadratic):
    amplitude=real(amplitude,'peak a m/s2',0.,1e5)
    quadratic=real(quadratic,'q s2/m',-100.,100.)
    return quadratic*amplitude*amplitude/2
```
