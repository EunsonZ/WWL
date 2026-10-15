"""Finite, synthetic bench models; SI units. No patient or compliance model.
Domain guards deliberately bound the teaching calculation, not physics.
Imports use standard library only; no files, argv, plotting, or caches.
"""
import math
import numbers
K_B = 1.380649e-23

def real(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise ValueError(name + ' must be a real scalar')
    try:
        x = float(x)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(name + ' outside declared finite teaching domain') from exc
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(name + ' outside declared finite teaching domain')
    return x

def randles(f, rs=5000., rct=100000., cdl=1e-6):
    """Z [ohm], f Hz 0..100k, Rs 100..100k, Rct 1k..10M, C 1n..100u F."""
    f=real(f,'f',0,1e5);rs=real(rs,'rs',100,1e5)
    rct=real(rct,'rct',1e3,1e7);cdl=real(cdl,'cdl',1e-9,1e-4)
    return rs+rct/(1+1j*2*math.pi*f*rct*cdl)

def readout(f, electrode1=(5000.,100000.,1e-6), electrode2=(6000.,100000.,1e-6), rin=1e7, cin=100e-12, ad=100., cmrr_db=100.):
    """Hd,Hc [V/V], T1,T2, Zparallel1,2 [ohm]. CMRR is nominal same-output gain ratio.
    AC/AD is positive real and constant in this illustrative amplifier model.
    """
    f=real(f,'f',0,1e5);rin=real(rin,'rin',1e5,1e9);cin=real(cin,'cin',1e-12,1e-8)
    ad=real(ad,'ad',1,1000);cmrr_db=real(cmrr_db,'cmrr_db',20,140)
    for e in (electrode1,electrode2):
        if not isinstance(e,(tuple,list)) or len(e)!=3: raise ValueError('electrode must be three real scalars')
    z1=randles(f,*electrode1);z2=randles(f,*electrode2)
    yi=1/rin+1j*2*math.pi*f*cin
    t1=1/(1+z1*yi);t2=1/(1+z2*yi)
    p1=z1*t1;p2=z2*t2;ac=ad*10**(-cmrr_db/20)
    hd=ad*(t1+t2)/2+ac*(t1-t2)/4
    hc=ad*(t1-t2)+ac*(t1+t2)/2
    return hd,hc,t1,t2,p1,p2

def noise_psd(f, electrode1=(5000.,100000.,1e-6), electrode2=(6000.,100000.,1e-6), rin=1e7, cin=100e-12, ad=100., cmrr_db=100., temperature=300., en=20e-9, current_asd=1e-12):
    """Single-sided output PSD V^2/Hz. Independent equilibrium passive electrode model,
    Rin thermal current sources, two independent input-current sources, one differential en.
    No excess/interface 1/f/motion or correlated noise is asserted by this function.
    """
    temperature=real(temperature,'temperature',250,350);en=real(en,'en',0,1e-6)
    current_asd=real(current_asd,'current_asd',0,1e-9)
    hd,hc,t1,t2,p1,p2=readout(f,electrode1,electrode2,rin,cin,ad,cmrr_db)
    ac=ad*10**(-cmrr_db/20);a1=ad+ac/2;a2=-ad+ac/2
    z1=randles(f,*electrode1);z2=randles(f,*electrode2)
    electrode=4*K_B*temperature*(abs(a1*t1)**2*z1.real+abs(a2*t2)**2*z2.real)
    current=(current_asd**2+4*K_B*temperature/rin)*(abs(a1*p1)**2+abs(a2*p2)**2)
    voltage=(ad*en)**2
    return dict(electrode=electrode,current=current,voltage=voltage,total=electrode+current+voltage)

def integrate_noise(fl=1., fh=100., intervals=1024, **kwargs):
    """Uniform-frequency composite Simpson, finite 2..8192 even intervals. Returns V RMS.
    Compare N and 2N; difference is an estimate, not an all-domain error certificate.
    """
    fl=real(fl,'fl',.1,1e4);fh=real(fh,'fh',.2,1e5)
    if fh<=fl: raise ValueError('fh must exceed fl')
    if isinstance(intervals,bool) or not isinstance(intervals,int) or intervals<2 or intervals>8192 or intervals%2:raise ValueError('finite even intervals required')
    step=(fh-fl)/intervals
    terms=[noise_psd(fl+i*step,**kwargs)['total']*(1 if i in (0,intervals) else 4 if i%2 else 2) for i in range(intervals+1)]
    return math.sqrt(math.fsum(terms)*step/3)

def barrier_current(f, capacitance, rms_voltage):
    """Ideal sinusoidal displacement-current RMS [A]; not a permissible leakage limit."""
    f=real(f,'f',0,1e6);capacitance=real(capacitance,'capacitance',1e-13,1e-8);rms_voltage=real(rms_voltage,'rms_voltage',0,10)
    return 2*math.pi*f*capacitance*rms_voltage

def adc_budget(span=2., bits=16, gain=100., signal_peak=100e-6, offset=0., artifact_peak=0.):
    """Symmetric +/-span/2 rails; worst-case peak sum. q/sqrt(12) is conditional, not SINAD."""
    span=real(span,'span',.5,10);gain=real(gain,'gain',1,1000)
    if isinstance(bits,bool) or not isinstance(bits,int) or not 8<=bits<=24:raise ValueError('bits 8..24 required')
    signal_peak=real(signal_peak,'signal_peak',0,.1);offset=real(offset,'offset',-.5,.5);artifact_peak=real(artifact_peak,'artifact_peak',0,.5)
    peak=gain*(signal_peak+abs(offset)+artifact_peak);q=span/(2**bits)
    return dict(output_peak=peak,headroom=span/2-peak,input_lsb=q/gain,conditional_input_quant_rms=q/(math.sqrt(12)*gain))

def rc_hold(samples, fs=1000., fc=100., initial=0.):
    """Exact piecewise-constant drive of y'=2pi fc(x-y); returns interval-end y[n].
    State kept across the sequence; each provided x[n] acts during [n/fs,(n+1)/fs).
    """
    fs=real(fs,'fs',100,1e5);fc=real(fc,'fc',.1,fs/4);y=real(initial,'initial',-10,10)
    if not isinstance(samples,(tuple,list)) or not 1<=len(samples)<=10000:raise ValueError('finite flat sequence required')
    x=[real(v,'sample',-10,10) for v in samples];b=-math.expm1(-2*math.pi*fc/fs)
    out=[]
    for v in x:
        y+=(v-y)*b;out.append(y)
    return out

def tone(samples, fs, frequency):
    """Finite complex tone projection (2/N sum x[n] exp(-j2pi fn/fs)), V peak.
    Not an arbitrary spectral estimator: tests use integer non-DC non-Nyquist cycles.
    """
    fs=real(fs,'fs',100,1e5);frequency=real(frequency,'frequency',.1,fs/2-.01)
    if not isinstance(samples,(tuple,list)) or not 4<=len(samples)<=10000:raise ValueError('finite sequence required')
    x=[real(v,'sample',-10,10) for v in samples]
    w=2*math.pi*frequency/fs;n=len(x)
    return complex(2*math.fsum(v*math.cos(w*i) for i,v in enumerate(x))/n,-2*math.fsum(v*math.sin(w*i) for i,v in enumerate(x))/n)
