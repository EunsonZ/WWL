"""Finite teaching model, SI, no import-time files/dependencies/argument parsing."""
import math
import numbers
from pathlib import Path
H=6.62607015e-34
C=299792458.0
Q=1.602176634e-19
KB=1.380649e-23

def real(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x,numbers.Real):
        raise ValueError(name+' must be a real scalar (not bool/complex)')
    x=float(x)
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(name+' outside documented finite domain')
    return x

def optical(power_w=100e-6,wavelength_m=850e-9,qe=.7,loss_db=10):
    p=real(power_w,'power_W',0,1); w=real(wavelength_m,'wavelength_m',200e-9,2000e-9)
    e=real(qe,'external_QE',0,1); l=real(loss_db,'passive_loss_dB',0,200)
    energy=H*C/w; received=p*10**(-l/10); r=e*Q/energy
    return dict(photon_J=energy,received_W=received,photon_s=received/energy,responsivity_A_W=r,photo_A=r*received)

def tia(f_hz,rf=1e5,ct=10e-12,cf=1e-12,a0=1e5,ft=10e6):
    f=real(f_hz,'frequency_Hz',0,1e9); r=real(rf,'RF_Ohm',1,1e9)
    t=real(ct,'CT_F',1e-15,1e-6); c=real(cf,'CF_F',0,1e-6)
    a=real(a0,'A0',1,1e9); b=real(ft,'fT_Hz',1,1e10)
    s=2j*math.pi*f; ag=a/(1+s/(2*math.pi*b/a))
    zf=r/(1+s*r*c); ng=1+s*t*zf
    return -zf*ag/(ag+ng),ag*ng/(ag+ng)

def output_psd(f_hz,photo_a,dark_a=1e-9,temp_k=300,en=5e-9,in_a=2e-15,rsh=1e9):
    p=real(photo_a,'photo_A',0,.1); d=real(dark_a,'dark_A',0,.1)
    t=real(temp_k,'temperature_K',1,1000); e=real(en,'en_V_sqrtHz',0,1e-3)
    i=real(in_a,'in_A_sqrtHz',0,1e-6); rs=real(rsh,'Rsh_Ohm',1,1e15)
    z,h=tia(f_hz)
    # Same independent Norton feedback source traverses Zt; never count its Thevenin form twice.
    si=2*Q*(p+d)+4*KB*t/1e5+4*KB*t/rs+i*i
    return abs(z)**2*si+abs(h)**2*e*e

def integrated_noise(photo_a,band_hz=100e3,panels=8192):
    b=real(band_hz,'band_Hz',1,10e6)
    if isinstance(panels,bool) or not isinstance(panels,int) or panels<16 or panels>65536 or panels%2:
        raise ValueError('panels must be even int in [16,65536]')
    # Validate all physical input before looping; finite Simpson budget.
    output_psd(0,photo_a)
    step=b/panels; total=output_psd(0,photo_a)+output_psd(b,photo_a)
    for k in range(1,panels): total+=(4 if k%2 else 2)*output_psd(k*step,photo_a)
    return math.sqrt(total*step/3)

def mzi(power_w,voltage_v,vpi=4,bias=math.pi/2,loss_db=10):
    p=real(power_w,'power_W',0,1); v=real(voltage_v,'voltage_V',-100,100)
    vp=real(vpi,'Vpi_V',1e-3,100); b=real(bias,'phase_bias_rad',-100,100)
    l=real(loss_db,'passive_loss_dB',0,200)
    phase=b+math.pi*v/vp; available=p*10**(-l/10)
    return available*(1+math.cos(phase))/2,available*(1-math.cos(phase))/2

def calibrate(powers_w,currents_a,dark_a):
    import numpy as np
    # Do not silently cast complex/object/bool arrays.
    p=np.asarray(powers_w); i=np.asarray(currents_a)
    if p.dtype.kind not in 'fi' or i.dtype.kind not in 'fi' or p.ndim!=1 or i.shape!=p.shape or not 3<=p.size<=10000:
        raise ValueError('3..10000 matching real numeric 1D samples')
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(i)) or np.any(p<0) or np.any(p>1) or np.any(abs(i)>.1):
        raise ValueError('samples outside finite physical calibration domain')
    d=real(dark_a,'dark_A',0,.1); scale=float(np.max(p))
    if scale==0: raise ValueError('nonzero optical excitation required')
    # Known independently measured dark; through-origin responsivity fit, not joint unknown gain/coupling.
    x=p/scale; denom=float(x@x); r=float(x@(i-d))/denom/scale
    if not 0<=r<=10: raise ValueError('unphysical fitted responsivity')
    residual=i-(d+r*p)
    return {'responsivity_A_W':r,'residual_RMS_A':float(np.sqrt(np.mean(residual**2))), 'samples':int(p.size)}

def fresh_output(output):
    p=Path(output).expanduser().resolve(); vault=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if p==vault or vault in p.parents or p.exists(): raise ValueError('output must be a fresh directory outside main vault')
    return p

def generate(output):
    import json
    p=fresh_output(output); o=optical(); zm,he=tia(100e3); pm,_=mzi(100e-6,0)
    r=o['responsivity_A_W']; dc=r*pm
    result={'parameters':{'source_W':100e-6,'wavelength_m':850e-9,'external_QE':.7,'loss_dB':10,'RF_Ohm':1e5,'CT_F':10e-12,'CF_F':1e-12,'A0':1e5,'fT_Hz':10e6,'band_Hz':100e3,'temperature_K':300,'dark_A':1e-9,'Rsh_Ohm':1e9,'en_V_sqrtHz':5e-9,'in_A_sqrtHz':2e-15,'Vpi_V':4,'phase_bias_rad':math.pi/2},'optical':o,'tia_100k':{'Zt_abs_Ohm':abs(zm),'He_abs':abs(he)},'unmodulated_output_DC_V':tia(0)[0].real*(o['photo_A']+1e-9),'noise_RMS_V':integrated_noise(o['photo_A']),'noise_refined_RMS_V':integrated_noise(o['photo_A'],panels=16384),'modulation':{'received_DC_W':pm,'photo_DC_A':dc,'optical_small_peak_W':100e-6*.1*.5*math.pi*.1/4,'output_small_peak_V':abs(zm)*r*100e-6*.1*.5*math.pi*.1/4,'noise_RMS_V':integrated_noise(dc)},'evidence':'CPU teaching prediction; no device/SPICE/EM/hardware measurement'}
    p.mkdir(parents=True)
    (p/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    with (p/'response.csv').open('w') as f:
        f.write('frequency_Hz,Zt_abs_Ohm,He_abs,output_PSD_V2_Hz\n')
        for k in range(101):
            freq=k*10000; z,h=tia(freq); f.write(f'{freq},{abs(z):.12g},{abs(h):.12g},{output_psd(freq,o["photo_A"]):.12g}\n')
    return result

def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try: generate(args.output)
    except ValueError as exc: parser.error(str(exc))
if __name__=='__main__': main()
