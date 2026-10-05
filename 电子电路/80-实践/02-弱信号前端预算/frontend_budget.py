"""U4 deterministic teaching budget, SI units, one-sided PSD.
CPU models are not device selection, SPICE, bench or production acceptance.
Generation requires --output; importing never writes files.
"""
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import math
import json
import argparse

KB=1.380649e-23
QE=1.602176634e-19


def real(value, positive=False, nonnegative=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite real scalar required')
    if positive and value<=0 or nonnegative and value<0: raise ValueError('outside domain')
    return float(value)


def integer(value, lower, upper):
    if isinstance(value,bool) or not isinstance(value,int) or not lower<=value<=upper:
        raise ValueError('integer outside supported range')
    return value


def thermal_psd(resistance, temperature):
    return 4*KB*real(temperature,positive=True)*real(resistance,nonnegative=True)


def shot_psd(current):
    return 2*QE*real(current,nonnegative=True)


def rectangular_variance(white, flicker, low, high):
    white,flicker=real(white,nonnegative=True),real(flicker,nonnegative=True)
    low,high=real(low,positive=True),real(high,positive=True)
    if high<=low: raise ValueError('empty/reversed band')
    return white*(high-low)+flicker*math.log(high/low)


def correlated_psd(s1,s2,rho,h1=1.,h2=1.):
    s1,s2=real(s1,nonnegative=True),real(s2,nonnegative=True)
    rho,h1,h2=real(rho),real(h1),real(h2)
    if abs(rho)>1: raise ValueError('correlation violates PSD positivity')
    value=h1*h1*s1+h2*h2*s2+2*h1*h2*rho*math.sqrt(s1*s2)
    return max(0.,value)  # suppress roundoff only at exactly cancelling limit


def integrate_log(function, low, high, n=4096):
    low,high=real(low,positive=True),real(high,positive=True)
    n=integer(n,2,262144)
    if high<=low or n%2: raise ValueError('ordered band and even Simpson count required')
    lo,hi=math.log(low),math.log(high);step=(hi-lo)/n;total=0.
    for j in range(n+1):
        f=math.exp(lo+j*step);v=real(function(f),nonnegative=True)*f
        total+=(1 if j in (0,n) else 4 if j%2 else 2)*v
    return total*step/3


def butterworth_power(frequency, cutoff, order=4):
    f,fc=real(frequency,nonnegative=True),real(cutoff,positive=True)
    order=integer(order,1,12)
    return 1/(1+(f/fc)**(2*order))


def noninverting_dc(vin, vref, noise_gain, a0, vos=0.):
    vin,vref,vos=real(vin),real(vref),real(vos)
    ng,a0=real(noise_gain,positive=True),real(a0,positive=True)
    if ng<1: raise ValueError('resistive noninverting noise gain >=1')
    h=a0/(1+a0/ng)
    return h*(vin-(1-1/ng)*vref+vos)


def loop_metrics(t0, poles_hz):
    """SISO negative feedback L=T0/product(1+s/p), 1..3 stable real poles.
    No zeros/delay/hidden states/unstable cancellation; margins are for this model.
    Unique magnitude crossing. Null GM means no finite -180deg crossing.
    """
    t0=real(t0,positive=True)
    if not isinstance(poles_hz,(list,tuple)) or not 1<=len(poles_hz)<=3: raise ValueError('1..3 poles required')
    p=[real(x,positive=True) for x in poles_hz]
    def mag(f):return t0/math.prod(math.hypot(1,f/x) for x in p)
    wc=None;pm=None
    if t0>1:
        lo,hi=0.,max(p)
        while mag(hi)>1:hi*=2
        for _ in range(100):
            mid=(lo+hi)/2
            if mag(mid)>1:lo=mid
            else:hi=mid
        wc=(lo+hi)/2
        pm=180-math.degrees(sum(math.atan(wc/x) for x in p))
    gm=None;phase_cross=None
    if len(p)==3:
        lo,hi=0.,max(p)
        while sum(math.atan(hi/x) for x in p)<math.pi:hi*=2
        for _ in range(100):
            mid=(lo+hi)/2
            if sum(math.atan(mid/x) for x in p)<math.pi:lo=mid
            else:hi=mid
        phase_cross=(lo+hi)/2;gm=1/mag(phase_cross)
    # Routh-Hurwitz for positive coefficients, x=s/(2*pi*p0).
    inv=[p[0]/x for x in p]
    coefficients=[1.]
    for a in inv:
        new=[0.]*(len(coefficients)+1)
        for i,c in enumerate(coefficients):new[i]+=c;new[i+1]+=c*a
        coefficients=new
    coefficients[0]+=t0
    stable=True
    if len(p)==3:stable=coefficients[2]*coefficients[1]>coefficients[3]*coefficients[0]
    return {'crossover_hz':wc,'phase_margin_deg':pm,'gain_margin_ratio':gm,
            'phase_cross_hz':phase_cross,'stable':stable,'normalized_denominator_ascending':coefficients}


def settling_error(step, resistance, capacitance, time):
    step,r,c,t=real(step,nonnegative=True),real(resistance,positive=True),real(capacitance,positive=True),real(time,nonnegative=True)
    return step*math.exp(-t/(r*c))


def half_lsb(fsr,bits):
    return real(fsr,positive=True)/2**(integer(bits,1,32)+1)


def acquisition_error(step, resistance, capacitance, time, driver_fc, driver_sr):
    """Explicit teaching driver: dead-time step/SR, then two linear poles.
    Cascaded driver/RC step residual is exact for this assumed system.
    This is not a universal op-amp settling or actual SAR input model.
    """
    step=real(step,nonnegative=True);r=real(resistance,positive=True);c=real(capacitance,positive=True)
    t=real(time,nonnegative=True);fc=real(driver_fc,positive=True);sr=real(driver_sr,positive=True)
    if step==0:return 0.
    elapsed=t-step/sr
    if elapsed<=0:return step
    a,b=1/(2*math.pi*fc),r*c
    if abs(a-b)<=1e-8*max(a,b):
        tau=(a+b)/2;residual=(1+elapsed/tau)*math.exp(-elapsed/tau)
    else:residual=(a*math.exp(-elapsed/a)-b*math.exp(-elapsed/b))/(a-b)
    return step*max(0.,residual)


@dataclass(frozen=True)
class Budget:
    g1:float=20.;g2:float=10.;a0:float=1e6
    gbw1:float=20e6;gbw2:float=20e6;sr1:float=1e6;sr2:float=1e6
    midpoint:float=1.65;peak:float=.001;signal_hz:float=1000.
    source_r:float=2000.;r2:float=100.;req1:float=1000.;req2:float=2000.
    en1:float=8e-9;en2:float=12e-9;in1:float=.3e-12;in2:float=.5e-12
    corner1:float=20.;corner2:float=10.;temperature:float=300.
    # DC current absolute bounds (A), distinct from random ASD in1/in2.
    # sensor_dc is pure source/reference mismatch; Vos stays pure offset.
    ibplus1:float=0.;ibminus1:float=0.;ibplus2:float=0.;ibminus2:float=0.
    sensor_dc:float=10e-6;vos1:float=5e-6;vos2:float=10e-6;ref1:float=1e-6;ref2:float=5e-6
    cutoff:float=5000.;filter_order:int=4;fs:float=100e3
    interferer_hz:float=99000.;interferer_peak:float=.1;alias_limit:float=5e-6
    fsr:float=3.3;bits:int=16;acq:float=5e-6;driver_r:float=200.;sample_c:float=20e-12
    driver_fc:float=20e6;driver_sr:float=10e6
    postfilter_rms:float=30e-6;adc_rms:float=20e-6
    low_hz:float=.1;high_hz:float=1e6
    output_low:float=.5;output_high:float=2.8;cm_low:float=.5;cm_high:float=2.8
    noise_limit_input:float=2e-6;offset_limit_input:float=20e-6
    magnitude_error_limit:float=.01


def fail_case():
    return replace(Budget(),g1=1000.,g2=1.,a0=1e5,gbw1=1e6,
                   source_r=100e3,vos1=.2e-3,sensor_dc=.1e-3,
                   driver_r=10000.,acq=.5e-6,driver_sr=.5e6,fs=50000.,interferer_hz=49000.)


def validate(cfg):
    for k,v in asdict(cfg).items():
        if k in ('bits','filter_order'):integer(v,1,32 if k=='bits' else 12)
        else:real(v)
    for k in ['peak','g1','g2','a0','gbw1','gbw2','sr1','sr2','signal_hz','temperature','cutoff','fs','fsr','acq','driver_r','sample_c','driver_fc','driver_sr','low_hz','high_hz','noise_limit_input','offset_limit_input']:
        real(getattr(cfg,k),positive=True)
    for k in ['ibplus1','ibminus1','ibplus2','ibminus2','source_r','r2','req1','req2','en1','en2','in1','in2','corner1','corner2','sensor_dc','vos1','vos2','ref1','ref2','interferer_peak','alias_limit','postfilter_rms','adc_rms']:
        real(getattr(cfg,k),nonnegative=True)
    if cfg.g1<1 or cfg.g2<1 or cfg.high_hz<=cfg.low_hz or not 0<cfg.signal_hz<cfg.fs/2:
        raise ValueError('invalid gain/band or signal beyond Nyquist')
    if cfg.output_high<=cfg.output_low or cfg.cm_high<=cfg.cm_low or cfg.interferer_hz<=0 or not 0<cfg.magnitude_error_limit<1:
        raise ValueError('invalid range/specification')


def noise_spectra(cfg,frequency):
    f=real(frequency,positive=True)
    h1=cfg.a0/(1+cfg.a0/cfg.g1);h2=cfg.a0/(1+cfg.a0/cfg.g2)
    fc1=cfg.gbw1/cfg.a0*(1+cfg.a0/cfg.g1);fc2=cfg.gbw2/cfg.a0*(1+cfg.a0/cfg.g2)
    white1=thermal_psd(cfg.source_r+cfg.req1,cfg.temperature)+cfg.en1**2+cfg.in1**2*(cfg.source_r**2+cfg.req1**2)
    white2=thermal_psd(cfg.r2+cfg.req2,cfg.temperature)+cfg.en2**2+cfg.in2**2*(cfg.r2**2+cfg.req2**2)
    s1=white1+cfg.en1**2*cfg.corner1/f;s2=white2+cfg.en2**2*cfg.corner2/f
    power1=h1*h1/(1+(f/fc1)**2);power2=h2*h2/(1+(f/fc2)**2)
    filtered=butterworth_power(f,cfg.cutoff,cfg.filter_order)
    return power1*power2*s1*filtered,power2*s2*filtered


def evaluate(cfg,n=4096):
    validate(cfg)
    g=cfg.g1*cfg.g2
    h1=cfg.a0/(1+cfg.a0/cfg.g1);h2=cfg.a0/(1+cfg.a0/cfg.g2)
    fc1=cfg.gbw1/cfg.a0*(1+cfg.a0/cfg.g1);fc2=cfg.gbw2/cfg.a0*(1+cfg.a0/cfg.g2)
    center1=noninverting_dc(cfg.midpoint,cfg.midpoint,cfg.g1,cfg.a0)
    center=noninverting_dc(center1,cfg.midpoint,cfg.g2,cfg.a0)
    error1=h1*(cfg.sensor_dc+cfg.vos1+cfg.ibplus1*cfg.source_r+cfg.ibminus1*cfg.req1+(1-1/cfg.g1)*cfg.ref1)
    worst=h2*(error1+cfg.vos2+cfg.ibplus2*cfg.r2+cfg.ibminus2*cfg.req2+(1-1/cfg.g2)*cfg.ref2)
    amplitude=cfg.peak*g  # conservative nominal signal envelope for swing
    low,high=center-worst-amplitude,center+worst+amplitude
    magnitude=h1*h2/g/math.hypot(1,cfg.signal_hz/fc1)/math.hypot(1,cfg.signal_hz/fc2)*math.sqrt(butterworth_power(cfg.signal_hz,cfg.cutoff,cfg.filter_order))
    v1=integrate_log(lambda f:noise_spectra(cfg,f)[0],cfg.low_hz,cfg.high_hz,n)
    v2=integrate_log(lambda f:noise_spectra(cfg,f)[1],cfg.low_hz,cfg.high_hz,n)
    quant=cfg.fsr/2**cfg.bits/math.sqrt(12)
    total_variance=v1+v2+cfg.postfilter_rms**2+cfg.adc_rms**2+quant**2
    input_rms=math.sqrt(total_variance)/g
    folded=abs((cfg.interferer_hz+cfg.fs/2)%cfg.fs-cfg.fs/2)
    alias=cfg.interferer_peak*math.sqrt(butterworth_power(cfg.interferer_hz,cfg.cutoff,cfg.filter_order))
    eps=half_lsb(cfg.fsr,cfg.bits)
    rc_error=settling_error(cfg.fsr,cfg.driver_r,cfg.sample_c,cfg.acq)
    full_error=acquisition_error(cfg.fsr,cfg.driver_r,cfg.sample_c,cfg.acq,cfg.driver_fc,cfg.driver_sr)
    flags={
        'output_window':low>=cfg.output_low and high<=cfg.output_high,
        'adc_window':low>=0 and high<=cfg.fsr,
        'common_mode':cfg.midpoint-cfg.peak-cfg.sensor_dc>=cfg.cm_low and cfg.midpoint+cfg.peak+cfg.sensor_dc<=cfg.cm_high and center1-error1-cfg.peak*cfg.g1>=cfg.cm_low and center1+error1+cfg.peak*cfg.g1<=cfg.cm_high,
        'magnitude':1-magnitude<=cfg.magnitude_error_limit,
        'sine_sr':2*math.pi*cfg.signal_hz*cfg.peak*cfg.g1<=cfg.sr1 and 2*math.pi*cfg.signal_hz*amplitude<=cfg.sr2,
        'noise':input_rms<=cfg.noise_limit_input,
        'dc_offset':(abs(center-cfg.midpoint)+worst)/g<=cfg.offset_limit_input,
        'rc_acquisition':rc_error<=eps,'driver_acquisition':full_error<=eps,
        'antialias_tone':alias<=cfg.alias_limit}
    # Tail bound ignores amplifier low-pass and is thus conservative.
    w1=thermal_psd(cfg.source_r+cfg.req1,cfg.temperature)+cfg.en1**2+cfg.in1**2*(cfg.source_r**2+cfg.req1**2)
    w2=thermal_psd(cfg.r2+cfg.req2,cfg.temperature)+cfg.en2**2+cfg.in2**2*(cfg.r2**2+cfg.req2**2)
    flick1=cfg.en1**2*cfg.corner1;flick2=cfg.en2**2*cfg.corner2
    order=cfg.filter_order;fc=cfg.cutoff;hi=cfg.high_hz
    tail=(g*g*w1+cfg.g2**2*w2)*fc**(2*order)/((2*order-1)*hi**(2*order-1))+(g*g*flick1+cfg.g2**2*flick2)*fc**(2*order)/(2*order*hi**(2*order))
    return {'flags':flags,'teaching_budget_pass':all(flags.values()),'gain_nominal':g,
            'dc_center':center,'dc_uncertainty':worst,'output_envelope':[low,high],
            'offset_input_bound':(abs(center-cfg.midpoint)+worst)/g,
            'normalized_signal_magnitude':magnitude,'stage_variances_output':[v1,v2],
            'output_noise_rms':math.sqrt(total_variance),'input_noise_rms':input_rms,
            'quantization_rms':quant,'noise_tail_bound_V2':tail,
            'snr_db':20*math.log10(cfg.peak*magnitude/math.sqrt(2)/input_rms),
            'alias_fold_hz':folded,'alias_peak_adc_V':alias,'half_lsb_V':eps,
            'rc_error_V':rc_error,'driver_error_V':full_error,
            'model_scope':'Explicit DC Ib bounds at both inputs; independent noises; finite-A single-pole stages; specified fourth-order filter; lumped postfilter/ADC noises; defined acquisition model, not hardware validation'}


def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    good,bad=Budget(),fail_case()
    transfer=replace(good,peak=.0005,source_r=20000.,signal_hz=2000.,bits=18,fsr=2.5,midpoint=1.25,driver_r=1000.,acq=.1e-6,temperature=330.)
    data={'good':{'parameters':asdict(good),'result':evaluate(good)},'bad':{'parameters':asdict(bad),'result':evaluate(bad)},'transfer':{'parameters':asdict(transfer),'result':evaluate(transfer)},'loop_examples':{str(n):loop_metrics(20,[1000]*n) for n in [1,2,3]}}
    (output/'budget-results.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(generate(args.output),indent=2,allow_nan=False))
