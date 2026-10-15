"""Finite-A voltage-feedback teaching model. Import: standard library, no writes."""
import argparse
import json
import math
import numbers
from pathlib import Path

LIMITS={'r':(1e-3,1e12),'c':(1e-15,1.0),'a0':(1.0,1e12),'fp':(1e-9,1e9),'f':(0.0,1e12),'t':(0.0,1e12),'v':(-1e6,1e6)}

def scalar(x,kind):
    if isinstance(x,bool) or not isinstance(x,numbers.Real):raise ValueError(f'{kind}: real scalar required')
    try:x=float(x)
    except (OverflowError,ValueError) as exc:raise ValueError('invalid scalar') from exc
    lo,hi=LIMITS[kind]
    if not math.isfinite(x) or not lo<=x<=hi:raise ValueError(f'{kind} outside documented computational range {lo}..{hi}')
    return x


def checked(z):
    if isinstance(z,complex):good=math.isfinite(z.real) and math.isfinite(z.imag)
    else:good=math.isfinite(z)
    if not good:raise ArithmeticError('nonfinite model output')
    return z


def inverse_a(f=0.0,a0=1e5,fp=10.0):
    f=scalar(f,'f');a0=scalar(a0,'a0');fp=scalar(fp,'fp')
    return complex(1/a0,(f/fp)/a0)


def closed_noninv(rg=1e4,rf=9e4,f=0.0,a0=1e5,fp=10.0):
    rg=scalar(rg,'r');rf=scalar(rf,'r');n=1+rf/rg
    return checked(n/(1+n*inverse_a(f,a0,fp)))


def closed_inv(ri=1e4,rf=9e4,f=0.0,a0=1e5,fp=10.0):
    ri=scalar(ri,'r');rf=scalar(rf,'r');k=rf/ri
    return checked(-k/(1+(1+k)*inverse_a(f,a0,fp)))


def summer(values,resistors,rf=9e4,a0=1e5):
    if not isinstance(values,(list,tuple)) or not isinstance(resistors,(list,tuple)) or not 1<=len(values)<=8 or len(values)!=len(resistors):raise ValueError('1..8 matched explicit input branches required')
    vs=[scalar(x,'v') for x in values];rs=[scalar(x,'r') for x in resistors];rf=scalar(rf,'r');a0=scalar(a0,'a0')
    weights=[rf/r for r in rs];n=1+math.fsum(weights)
    return checked(-math.fsum(w*v for w,v in zip(weights,vs))/(1+n/a0))


def difference(v1,v2,r1=1e4,rf=9e4,r3=1e4,r4=9e4,a0=1e5):
    v1=scalar(v1,'v');v2=scalar(v2,'v');r1=scalar(r1,'r');rf=scalar(rf,'r');r3=scalar(r3,'r');r4=scalar(r4,'r');a0=scalar(a0,'a0')
    a=rf/r1;p=v2*(r4/(r3+r4));n=1+a
    return checked((n*p-a*v1)/(1+n/a0))


def integrate_transfer(f,ri=1e4,cf=1e-7,rf=1e6,a0=1e5,fp=10.0):
    f=scalar(f,'f');ri=scalar(ri,'r');cf=scalar(cf,'c');rf=scalar(rf,'r')
    yin=1/ri;yf=complex(1/rf,2*math.pi*f*cf)
    return checked(-yin/(yf+(yin+yf)*inverse_a(f,a0,fp)))


def differentiate_transfer(f,ri=1e3,ci=1e-7,rf=1e4,cf=1e-9,a0=1e5,fp=10.0):
    f=scalar(f,'f');ri=scalar(ri,'r');ci=scalar(ci,'c');rf=scalar(rf,'r');cf=scalar(cf,'c');s=complex(0,2*math.pi*f)
    # Admittance avoids division by s at DC, also keeps input capacitor open exactly.
    yin=s*ci/(1+s*ri*ci);yf=1/rf+s*cf
    return checked(-yin/(yf+(yin+yf)*inverse_a(f,a0,fp)))


def reactive_noise_gain(f,mode):
    f=scalar(f,'f');s=complex(0,2*math.pi*f)
    if mode=='integrator':yin=1/1e4;yf=1/1e6+s*1e-7
    elif mode=='differentiator':yin=s*1e-7/(1+s*1e3*1e-7);yf=1/1e4+s*1e-9
    else:raise ValueError('unknown mode')
    return checked(1+yin/yf)


def integrator_state(t,u=1e-3,initial=0.2,ri=1e4,cf=1e-7,rf=None):
    t=scalar(t,'t');u=scalar(u,'v');initial=scalar(initial,'v');ri=scalar(ri,'r');cf=scalar(cf,'c')
    # Ideal op-amp state model, separate from frequency finite-A zero-state model.
    if rf is None:return checked(initial-u*(t/(ri*cf)))
    rf=scalar(rf,'r');tau=rf*cf;decay=math.exp(-t/tau)
    return checked(initial*decay-(rf/ri)*u*(-math.expm1(-t/tau)))


def derivative_peak(amplitude,f,rf=1e4,c=1e-7):
    amplitude=scalar(amplitude,'v');f=scalar(f,'f');rf=scalar(rf,'r');c=scalar(c,'c')
    return checked(abs(amplitude)*(2*math.pi*f)*rf*c)


def results():
    a0=1e5;fp=10.0;h=closed_noninv();inv=closed_inv();out=float(inv.real)*.02;vm=-out/a0
    cm=difference(2,2,r4=90900);d=difference(-.5,.5,r4=90900)
    rows=[]
    for f in (0,1,10,100,1000,10000,100000,1000000):
        hi=integrate_transfer(f);hd=differentiate_transfer(f)
        rows.append({'f_Hz':f,'integrator':{'re':hi.real,'im':hi.imag,'mag':abs(hi)},'differentiator':{'re':hd.real,'im':hd.imag,'mag':abs(hd)}})
    return {'model':'A0=100000 fp=10Hz; input currents=0; output r=0; resistor load=10k; supply +/-5V, teaching linear output +/-4V/common mode +/-3V',
            'parameters':{'a0':a0,'fp_Hz':fp,'fT_approx_Hz':a0*fp,'Rg_Ri_ohm':10000,'Rf_ohm':90000},
            'noninv_DC':h.real,'inv_DC':inv.real,'inv_20mV':{'out_V':out,'minus_V':vm,'input_A':(.02-vm)/10000,'output_A':out/10000+(out-vm)/90000},
            'summer_V':summer([.02,-.01],[1e4,2e4]),'difference_200_210mV_V':difference(.2,.21),
            'mismatch_1percent':{'equal_input_2V_output_V':cm,'common_gain':cm/2,'differential_gain':d,'CMRR_dB':20*math.log10(abs(d/(cm/2)))},
            'leak_low_Hz':1/(2*math.pi*1e6*1e-7),'derivative_corners_Hz':[1/(2*math.pi*1e3*1e-7),1/(2*math.pi*1e4*1e-9)],
            'frequency_samples':rows,'ideal_integrator_at_4p2s_V':integrator_state(4.2),'leak_at_0p1s_V':integrator_state(.1,rf=1e6),
            'execution':'CPU explicit models only, not SPICE/hardware'}


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args(argv)
    payload=results() # all calculations before filesystem mutation
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (args.output/'parameters.json').write_text(json.dumps({'scalar_limits':LIMITS,'model':payload['model'],'parameters':payload['parameters']},indent=2,allow_nan=False)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
