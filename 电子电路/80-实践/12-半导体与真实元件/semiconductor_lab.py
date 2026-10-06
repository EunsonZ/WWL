"""SI教学模型；导入无文件输出。不是器件保证或SPICE模型。"""
import math
import numbers
import argparse
import json
from pathlib import Path
K_B=1.380649e-23
Q_E=1.602176634e-19
EPS0=8.8541878128e-12

def real(value, name, positive=False, nonnegative=False):
    # 在float转换前拒绝complex（含0j）、bool、对象和数组/嵌套序列。
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f'{name} must be a real scalar, not bool/complex/object/array')
    value=float(value)
    if not math.isfinite(value): raise ValueError(f'{name} must be finite')
    if positive and value<=0: raise ValueError(f'{name} must be positive')
    if nonnegative and value<0: raise ValueError(f'{name} must be nonnegative')
    return value

def thermal_voltage(temperature):
    return K_B*real(temperature,'temperature',positive=True)/Q_E

def pn_dimensions(na,nd,ni,temperature,eps=11.7*EPS0,vd=0.):
    na=real(na,'na',positive=True);nd=real(nd,'nd',positive=True)
    ni=real(ni,'ni',positive=True);eps=real(eps,'eps',positive=True)
    vd=real(vd,'vd');vt=thermal_voltage(temperature)
    # log分开避免密度乘积溢出。
    vbi=vt*(math.log(na)+math.log(nd)-2*math.log(ni))
    if vbi<=0: raise ValueError('extrinsic junction requires positive built-in barrier')
    b=vbi-vd
    if b<=0: raise ValueError('depletion model requires positive remaining barrier')
    w=math.sqrt(2*eps*b/Q_E*(1/na+1/nd))
    if not math.isfinite(w) or w<=0: raise ValueError('unrepresentable depletion width')
    # Stable widths without summing densities.
    xp=w/(1+na/nd);xn=w-xp
    return dict(vbi=vbi,barrier=b,w=w,xp=xp,xn=xn,emax=-Q_E*na*xp/eps)

def pn_space(x,na,nd,ni,temperature,eps=11.7*EPS0):
    x=real(x,'x');d=pn_dimensions(na,nd,ni,temperature,eps)
    xp,xn,b=d['xp'],d['xn'],d['barrier'];na=float(na);nd=float(nd)
    if x<=-xp:rho=0.;e=0.;phi=0.
    elif x<0:rho=-Q_E*na;e=-Q_E*na*(x+xp)/eps;phi=Q_E*na*(x+xp)**2/(2*eps)
    elif x<xn:rho=Q_E*nd;e=Q_E*nd*(x-xn)/eps;phi=b-Q_E*nd*(xn-x)**2/(2*eps)
    else:rho=0.;e=0.;phi=b
    n=float(ni)**2/na*math.exp(phi/thermal_voltage(temperature))
    p=na*math.exp(-phi/thermal_voltage(temperature))
    return dict(rho=rho,e=e,phi=phi,n=n,p=p)

def diode_current(v,isat=1e-12,eta=1.,temperature=300.):
    v=real(v,'v');isat=real(isat,'isat',positive=True);eta=real(eta,'eta',positive=True)
    a=v/(eta*thermal_voltage(temperature))
    if a>700:raise ValueError('exponential range exceeded; choose a model/domain')
    result=isat*math.expm1(a)
    if not math.isfinite(result):raise ValueError('unrepresentable current')
    return result

def diode_load(vs,r,isat=1e-12,eta=1.,temperature=300.,max_iterations=200,voltage_tol=1e-12):
    vs=real(vs,'vs',nonnegative=True);r=real(r,'r',positive=True)
    real(isat,'isat',positive=True);real(eta,'eta',positive=True);thermal_voltage(temperature)
    voltage_tol=real(voltage_tol,'voltage_tol',positive=True)
    if isinstance(max_iterations,bool) or not isinstance(max_iterations,numbers.Integral) or max_iterations<1:
        raise ValueError('max_iterations must be a positive integer')
    if vs==0:return dict(v=0.,i=0.,iterations=0,residual_a=0.)
    # root lies below the voltage needed to pass vs/r in the diode.
    high=min(vs,eta*thermal_voltage(temperature)*(math.log1p(vs/(r*isat))))
    lo=0.
    for step in range(int(max_iterations)):
        mid=(lo+high)/2
        f=diode_current(mid,isat,eta,temperature)-(vs-mid)/r
        if high-lo<=voltage_tol:
            return dict(v=mid,i=(vs-mid)/r,iterations=step+1,residual_a=f)
        if mid==lo or mid==high:raise RuntimeError('bisection stagnated before tolerance')
        if f>0:high=mid
        else:lo=mid
    raise RuntimeError('bisection iteration budget exhausted')

def nonlinear_charge(v,c0=10e-6,vb=2.):
    v=real(v,'v');c0=real(c0,'c0',positive=True);vb=real(vb,'vb',positive=True)
    return c0*vb*math.atan(v/vb)

def nonlinear_capacitance(v,c0=10e-6,vb=2.):
    v=real(v,'v');c0=real(c0,'c0',positive=True);vb=real(vb,'vb',positive=True)
    return c0/(1+(v/vb)**2)

def storage_time(ifwd,irev,tau):
    ifwd=real(ifwd,'ifwd',nonnegative=True);irev=real(irev,'irev',positive=True);tau=real(tau,'tau',positive=True)
    return tau*math.log1p(ifwd/irev)

def saturation_temperature(temperature,is0=1e-12,t0=300.,eg_ev=1.12):
    t=real(temperature,'temperature',positive=True);t0=real(t0,'t0',positive=True)
    is0=real(is0,'is0',positive=True);eg=real(eg_ev,'eg_ev',positive=True)*Q_E
    logi=math.log(is0)+3*math.log(t/t0)-eg/K_B*(1/t-1/t0)
    if not -700<logi<700:raise ValueError('temperature model outside numeric range')
    return math.exp(logi)

def constant_current_voltage(i,temperature,is0=1e-12,t0=300.,eg_ev=1.12,eta=1.):
    i=real(i,'i',nonnegative=True);eta=real(eta,'eta',positive=True)
    return eta*thermal_voltage(temperature)*math.log1p(i/saturation_temperature(temperature,is0,t0,eg_ev))

def capacitor_impedance(frequency,c,esr,esl,rleak):
    # Explicit frequency-domain interface returns legal complex Z; physical parameters remain real.
    f=real(frequency,'frequency',nonnegative=True);c=real(c,'c',positive=True)
    esr=real(esr,'esr',nonnegative=True);esl=real(esl,'esl',nonnegative=True);rleak=real(rleak,'rleak',positive=True)
    w=2*math.pi*f
    return esr+1j*w*esl+1/(1/rleak+1j*w*c)

def results():
    na,nd,ni=1e22,2e22,1e16
    return {'parameter_class':'teaching; not fitted manufacturer devices','pn':pn_dimensions(na,nd,ni,300),
      'diode_load':diode_load(5,1000), 'charge_at_2v_c':nonlinear_charge(2),
      'capacitance_at_2v_f':nonlinear_capacitance(2), 'storage_s':storage_time(1e-3,1e-3,100e-9),
      'vf_300k_v':constant_current_voltage(1e-3,300),'vf_330k_v':constant_current_voltage(1e-3,330),
      'capacitor_srf_hz':1/(2*math.pi*math.sqrt(100e-9*1e-9)),
      'z_cap_1mhz_ohm':[capacitor_impedance(1e6,100e-9,.05,1e-9,1e9).real,capacitor_impedance(1e6,100e-9,.05,1e-9,1e9).imag]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    target=args.output.resolve();vault_root=Path(__file__).resolve().parents[3]
    if target.is_relative_to(vault_root): parser.error('--output must be outside the candidate/vault root')
    args.output=target;args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(results(),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
