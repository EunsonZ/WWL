"""Finite CPU teaching models. SI inputs; no hardware/SPICE claim or import writes."""
from dataclasses import dataclass, replace
import math

def real(x,name,lo,hi):
    if isinstance(x,bool) or not isinstance(x,(int,float)):
        raise TypeError(name+' must be a real Python int/float, not bool/complex/container')
    if not lo <= x <= hi or not math.isfinite(x): raise ValueError(name+' outside declared finite domain')
    return float(x)

def count(x,name,lo,hi):
    if isinstance(x,bool) or not isinstance(x,int): raise TypeError(name+' must be int')
    if not lo<=x<=hi: raise ValueError(name+' outside finite budget')
    return x

@dataclass(frozen=True)
class Params:
    vin: float=12.0
    l: float=100e-6
    c: float=100e-6
    r: float=10.0
    fs: float=100e3
    d: float=5/12
    def __post_init__(self):
        for name,lo,hi in [('vin',6,24),('l',50e-6,500e-6),('c',50e-6,500e-6),('r',2,200),('fs',50e3,200e3),('d',.05,.95)]:
            object.__setattr__(self,name,real(getattr(self,name),name,lo,hi))

def buck_summary(p):
    if not isinstance(p,Params): raise TypeError('Params required')
    v=p.vin*p.d; ripple=(p.vin-v)*p.d/(p.l*p.fs); critical=ripple/2; k=2*p.l*p.fs/p.r
    m=2/(1+math.sqrt(1+4*k/(p.d*p.d)))
    boundary_r=2*p.l*p.fs/(1-p.d)
    mode='CCM' if p.r<boundary_r else ('boundary' if p.r==boundary_r else 'DCM')
    used=v if mode!='DCM' else p.vin*m
    ip=(p.vin-used)*p.d/(p.l*p.fs); d2=(p.vin-used)*p.d/used
    return dict(v_ccm=v,delta_i_A=ripple,critical_A=critical,r_boundary_ohm=2*p.l*p.fs/(1-p.d),mode=mode,v_V=used,
                d2=d2 if mode=='DCM' else 1-p.d,d3=1-p.d-d2 if mode=='DCM' else 0,peak_dcm_A=ip,
                ripple_cap_ccm_V=ripple/(8*p.fs*p.c),energy_L_at_ccm_mean_J=.5*p.l*(v/p.r)**2,energy_C_ccm_J=.5*p.c*v*v)

def conversion(kind,d,k=None):
    d=real(d,'d',.05,.95)
    if kind not in ('buck','boost','inverting'): raise ValueError('unknown topology')
    if k is None:return {'buck':d,'boost':1/(1-d),'inverting':-d/(1-d)}[kind]
    k=real(k,'K=2Lf/R',.001,100)
    if kind=='buck':
        if k>=1-d:raise ValueError('not strictly DCM buck')
        return 2/(1+math.sqrt(1+4*k/d**2))
    if kind=='boost':
        if k>=d*(1-d)**2:raise ValueError('not strictly DCM boost')
        return (1+math.sqrt(1+4*d*d/k))/2
    if k>=(1-d)**2:raise ValueError('not strictly DCM inverting')
    return -d/math.sqrt(k)

def _rhs(p,x,q):
    i,v=x;return ((q*p.vin-v)/p.l,(i-v/p.r)/p.c)

def _rk4(p,x,h,q):
    def plus(a,b,scale):return tuple(u+scale*v for u,v in zip(a,b))
    a=_rhs(p,x,q);b=_rhs(p,plus(x,a,h/2),q);c=_rhs(p,plus(x,b,h/2),q);d=_rhs(p,plus(x,c,h),q)
    y=tuple(u+h*(v+2*w+2*z+t)/6 for u,v,w,z,t in zip(x,a,b,c,d))
    if not all(math.isfinite(v) and abs(v)<100 for v in y):raise ArithmeticError('state outside teaching envelope')
    return y

def _off_step(p,x,h):
    if x[0]<=0: return (0.,x[1]*math.exp(-h/(p.r*p.c))),'idle'
    trial=_rk4(p,x,h,0)
    if trial[0]>=0:return trial,'off'
    lo,hi=0.,h
    for _ in range(52):
        mid=lo+(hi-lo)/2
        if mid==lo or mid==hi:break
        if _rk4(p,x,mid,0)[0]>0:lo=mid
        else:hi=mid
    hit=_rk4(p,x,(lo+hi)/2,0)
    return (0.,hit[1]*math.exp(-(h-(lo+hi)/2)/(p.r*p.c))),'off+idle'

def simulate(p,cycles=300,steps=64,initial=None,average=False,control_k=0.0,reference=5.0):
    if not isinstance(p,Params):raise TypeError('Params required')
    cycles=count(cycles,'cycles',1,2000);steps=count(steps,'steps per interval',16,256)
    if not isinstance(average,bool):raise TypeError('average must be bool')
    gain=real(control_k,'control_k 1/V',0,.1);ref=real(reference,'reference V',1,20)
    if initial is None:x=(p.vin*p.d/p.r,p.vin*p.d)
    else:
        if not isinstance(initial,(tuple,list)) or len(initial)!=2:raise TypeError('initial=(i A,v V)')
        x=(real(initial[0],'initial i',0,10),real(initial[1],'initial v',0,p.vin))
    data=[dict(t_s=0.,i_A=x[0],v_V=x[1],mode='initial',d=p.d)];t=0.
    for _ in range(cycles):
        duty=max(.05,min(.95,p.d+gain*(ref-x[1])))
        for mode,span,q in [('on',duty/p.fs,1.),('off',(1-duty)/p.fs,0.)]:
            h=span/steps
            for __ in range(steps):
                if average:y=_rk4(p,x,h,duty);state='average'
                elif mode=='off':y,state=_off_step(p,x,h)
                else:
                    y=_rk4(p,x,h,1.);state='on'
                    if y[0]<-1e-12:raise ArithmeticError('reverse on-current outside diode teaching model')
                t+=h
                if t==data[-1]['t_s']:raise ArithmeticError('time stagnation')
                x=y;data.append(dict(t_s=t,i_A=x[0],v_V=x[1],mode=state,d=duty))
    return data

def buck_gvd(p,w):
    if not isinstance(p,Params):raise TypeError('Params required')
    w=real(w,'omega rad/s',0,1e7)
    s=complex(0,w);return p.vin/(1+s*p.l/p.r+s*s*p.l*p.c)

def boost_zero(p):
    if not isinstance(p,Params):raise TypeError('Params required')
    return p.r*(1-p.d)**2/p.l

def losses(p,ron=.05,dcr=.1,trtf=40e-9,qg=10e-9,vg=5.,vf=.4,coss=200e-12):
    ron=real(ron,'ron ohm',0,1);dcr=real(dcr,'dcr ohm',0,2);trtf=real(trtf,'tr+tf s',0,1e-6)
    qg=real(qg,'Qg C',0,1e-6);vg=real(vg,'drive V',0,20);vf=real(vf,'Vf V',0,2);coss=real(coss,'constant Coss F',0,1e-8)
    summary=buck_summary(p)
    if summary['mode']!='CCM':raise ValueError('loss account implemented only CCM')
    i=summary['v_V']/p.r;rip=summary['delta_i_A'];irms2=i*i+rip*rip/12
    parts=dict(mos_W=ron*p.d*irms2,copper_W=dcr*irms2,diode_W=vf*(1-p.d)*i,
               overlap_W=.5*p.vin*i*trtf*p.fs,gate_W=qg*vg*p.fs,coss_W=.5*coss*p.vin*p.vin*p.fs)
    total=sum(parts.values());po=summary['v_V']**2/p.r
    return dict(parts=parts,total_W=total,efficiency=po/(po+total),identity='illustrative loss estimate, ideal Q unchanged; not device extraction')

def thermal(t,power,rtheta=40.,cth=.5,ambient=25.):
    t=real(t,'time s',0,10000);power=real(power,'power W',0,20);rtheta=real(rtheta,'system Rth K/W',1,200)
    cth=real(cth,'Cth J/K',.01,100);ambient=real(ambient,'ambient C',-20,100)
    return ambient+power*rtheta*(-math.expm1(-t/(rtheta*cth)))

def magnetic_delta(v,dt,n,area):
    v=real(v,'winding V',-24,24);dt=real(dt,'interval s',0,1e-3);n=count(n,'turns',1,1000);area=real(area,'area m2',1e-6,1e-3)
    return v*dt/(n*area)

def pwm_phases(theta,m=.8,vdc=12.):
    theta=real(theta,'theta rad',-1e5,1e5);m=real(m,'modulation',0,1);vdc=real(vdc,'bus V',6,24)
    d=tuple(.5+.5*m*math.sin(theta-2*math.pi*k/3) for k in range(3));mean=sum(d)/3
    return dict(duty=d,phase_V=tuple(vdc*(u-mean) for u in d),line_V=(vdc*(d[0]-d[1]),vdc*(d[1]-d[2]),vdc*(d[2]-d[0])))

def state_matrices(p,kind='buck'):
    if not isinstance(p,Params):raise TypeError('Params required')
    if kind=='buck':return dict(Aon=((0.,-1/p.l),(1/p.c,-1/(p.r*p.c))),Aoff=((0.,-1/p.l),(1/p.c,-1/(p.r*p.c))),Bon=(1/p.l,0.),Boff=(0.,0.))
    if kind=='boost':return dict(Aon=((0.,0.),(0.,-1/(p.r*p.c))),Aoff=((0.,-1/p.l),(1/p.c,-1/(p.r*p.c))),Bon=(1/p.l,0.),Boff=(1/p.l,0.))
    raise ValueError('kind buck/boost')

def boost_gvd(p,w):
    if not isinstance(p,Params):raise TypeError('Params required')
    w=real(w,'omega rad/s',0,1e7);a=1-p.d;v=p.vin/a;i=v/(p.r*a);s=complex(0,w)
    return (v*a/(p.l*p.c)-i*s/p.c)/(s*s+s/(p.r*p.c)+a*a/(p.l*p.c))

def design_candidates():
    """Fixed 12-point teaching enumeration, not a continuous/global optimizer."""
    result=[]
    for inductance in (50e-6,100e-6,200e-6,400e-6):
        for frequency in (50e3,100e3,200e3):
            p=Params(l=inductance,fs=frequency);s=buck_summary(p)
            if s['mode']!='CCM':result.append(dict(l_H=p.l,fs_Hz=p.fs,feasible=False,reason='CCM model not valid'));continue
            power=losses(p)['total_W'];rise=40*power
            feasible=s['delta_i_A']<=.3 and s['ripple_cap_ccm_V']<=.01 and rise<=10
            result.append(dict(l_H=p.l,fs_Hz=p.fs,delta_i_A=s['delta_i_A'],delta_v_V=s['ripple_cap_ccm_V'],estimated_shared_rise_K=rise,loss_W=power,objective=power/1.,feasible=feasible))
    return result
