"""Bounded SI teaching models. Pure import: stdlib only, no I/O/argv/dependencies."""
import math
import cmath

def real(x,name,lo,hi):
    if type(x) not in (int,float): raise ValueError(name+' requires Python real scalar')
    try:x=float(x)
    except (OverflowError,ValueError):raise ValueError(name+' is not representable') from None
    if not math.isfinite(x) or not lo<=x<=hi:raise ValueError(name+' outside teaching range')
    return x

def integer(x,name,lo,hi):
    if type(x) is not int or not lo<=x<=hi:raise ValueError(name+' requires bounded integer')
    return x

def phasor(x,name,limit=1e6):
    if type(x) not in (int,float,complex):raise ValueError(name+' requires finite scalar phasor')
    try:x=complex(x)
    except (OverflowError,ValueError):raise ValueError(name+' is not representable') from None
    if not math.isfinite(x.real) or not math.isfinite(x.imag) or abs(x)>limit:raise ValueError(name+' outside phasor range')
    return x

def lossless(lprime,cprime,length):
    lprime=real(lprime,'Lprime',1e-9,1e-3);cprime=real(cprime,'Cprime',1e-13,1e-6);length=real(length,'length',1e-4,100)
    speed=1/math.sqrt(lprime*cprime)
    if not 1e5<=speed<=3e8:raise ValueError('speed outside model medium range')
    return {'Z0_ohm':math.sqrt(lprime/cprime),'speed_m_s':speed,'delay_s':length/speed}

def rlcg(r,l,g,c,frequency):
    r=real(r,'Rprime',0,1000);l=real(l,'Lprime',1e-9,1e-3);g=real(g,'Gprime',0,.1);c=real(c,'Cprime',1e-13,1e-6);f=real(frequency,'frequency',1,1e10)
    a=complex(r,2*math.pi*f*l);b=complex(g,2*math.pi*f*c)
    gamma=cmath.sqrt(a*b);z= a/gamma
    return {'gamma_per_m':gamma,'Zc_ohm':z}

def reflection(load,z0):
    z0=real(z0,'z0',1,1000)
    if load is None:return complex(1)
    z=phasor(load,'load')
    if z.real<0:raise ValueError('passive load required')
    return (z-z0)/(z+z0)

def bounce(vs,zs,zl,z0,delay,rounds=8):
    vs=real(vs,'Vs',-10,10);zs=real(zs,'Zs',0,1000);z0=real(z0,'Z0',1,1000);delay=real(delay,'delay',1e-12,1e-3);rounds=integer(rounds,'rounds',1,24)
    if zl is not None:zl=real(zl,'Zl',0,1000)
    gl=reflection(zl,z0).real;gs=(zs-z0)/(zs+z0);a=vs*z0/(zs+z0);source=a;load=0.;events=[{'time_s':0.,'end':'source','increment_V':a,'total_V':source}];waves=[]
    for k in range(rounds):
        f=a*(gs*gl)**k;b=gl*f;waves.extend([{'t0_s':2*k*delay,'t1_s':(2*k+1)*delay,'x0':0,'x1':1,'amplitude_V':f},{'t0_s':(2*k+1)*delay,'t1_s':(2*k+2)*delay,'x0':1,'x1':0,'amplitude_V':b}])
        dl=(1+gl)*f;load+=dl;events.append({'time_s':(2*k+1)*delay,'end':'load','increment_V':dl,'total_V':load})
        ds=(1+gs)*b;source+=ds;events.append({'time_s':(2*k+2)*delay,'end':'source','increment_V':ds,'total_V':source})
    return {'Gamma_L':gl,'Gamma_S':gs,'launch_V':a,'events':events,'waves':waves,'finite_rounds':rounds,'steady_state_claim':False}

def input_impedance(load,z0,theta):
    theta=real(theta,'theta_rad',-100,100);gamma=reflection(load,z0)*cmath.exp(-2j*theta)
    if abs(1-gamma)<1e-10:raise ValueError('input impedance pole; use reflection coordinate')
    return z0*(1+gamma)/(1-gamma)

def power_waves(v,i,zref):
    zref=real(zref,'real reference ohm',1,1000);v=phasor(v,'V rms');i=phasor(i,'I rms',1000)
    a=(v+zref*i)/(2*math.sqrt(zref));b=(v-zref*i)/(2*math.sqrt(zref))
    # RMS port power: avoid subtracting nearly equal large wave powers.
    net=math.fsum((v.real*i.real,v.imag*i.imag))
    return {'a_sqrtW':a,'b_sqrtW':b,'net_W':net}

def friis_noise(stages):
    if type(stages) not in (list,tuple) or not 1<=len(stages)<=8:raise ValueError('1..8 [power gain, noise factor] stages')
    terms=[];product=1.
    for idx,row in enumerate(stages):
        if type(row) not in (list,tuple) or len(row)!=2:raise ValueError('stage shape')
        gain=real(row[0],'power gain',.001,1e4);factor=real(row[1],'noise factor',1,1e4)
        terms.append(factor if idx==0 else (factor-1)/product);product*=gain
    factor=math.fsum(terms)
    return {'factor':factor,'NF_dB':10*math.log10(factor),'power_gain':product,'terms':terms}

def cubic_output(x,a1,a3):
    x=real(x,'x V',-1,1);a1=real(a1,'a1 V/V',.1,100);a3=real(a3,'a3 V^-2',-100,0)
    return a1*x+a3*x**3

def cubic_metrics(a1,a3,resistance=50):
    a1=real(a1,'a1',.1,100);a3=real(a3,'a3',-100,-1e-4);r=real(resistance,'R',1,1000)
    ai=math.sqrt(4*a1/(3*abs(a3)));ac=math.sqrt(4*a1*(1-10**(-1/20))/(3*abs(a3)))
    return {'IIP3_peak_V':ai,'IIP3_W_per_tone':ai**2/(2*r),'IP1dB_peak_V_single_tone':ac,'IP1dB_W':ac**2/(2*r),'extrapolated_IP3_not_valid_drive':True}

def iq_image(gain,phase_error):
    gain=real(gain,'Q gain',.5,1.5);phase_error=real(phase_error,'phase rad',-.5,.5)
    # I'=I; Q'=g*(cos(e) Q + sin(e) I); z'=alpha z+beta z*
    alpha=(1+gain*cmath.exp(1j*phase_error))/2;beta=(1-gain*cmath.exp(-1j*phase_error))/2
    return {'alpha':alpha,'beta':beta,'image_power_ratio':abs(beta)**2/abs(alpha)**2,'IRR_dB':None if beta==0 else 20*math.log10(abs(alpha)/abs(beta))}

def differential_skew(amplitude,frequency,tau_plus,tau_minus):
    a=real(amplitude,'leg peak V',1e-6,10);f=real(frequency,'frequency',1,1e10);tp=real(tau_plus,'delay+',0,1e-6);tm=real(tau_minus,'delay-',0,1e-6)
    if f*max(tp,tm)>1000:raise ValueError('phase budget')
    vp=a*cmath.exp(-2j*math.pi*f*tp);vm=-a*cmath.exp(-2j*math.pi*f*tm)
    return {'Vdiff_peak':vp-vm,'Vcommon_peak':(vp+vm)/2}

def eye_record(bits,ui,tau,samples_per_ui=32):
    if type(bits) not in (list,tuple) or not 16<=len(bits)<=128 or any(type(b) is not int or b not in (-1,1) for b in bits):raise ValueError('16..128 binary +/-1 sequence')
    ui=real(ui,'UI s',1e-12,1e-6);tau=real(tau,'tau s',1e-14,1e-5);s=integer(samples_per_ui,'samples/UI',16,128)
    if not .05<=tau/ui<=2:raise ValueError('tau/UI .05..2')
    y=0.;decay=math.exp(-ui/(s*tau));record=[]
    for b in bits:
        for _ in range(s):y=b+(y-b)*decay;record.append(y)
    return {'samples_V':record,'sample_times_s':[(k+1)*ui/s for k in range(len(record))],'initial_V':0.,'samples_per_ui':s,'UI_s':ui,'tau_s':tau}

def isi_margin(taps):
    if type(taps) not in (list,tuple) or not 1<=len(taps)<=8:raise ValueError('1..8 symbol taps')
    h=[real(v,'tap',-10,10) for v in taps]
    if h[0]<=0:raise ValueError('positive main cursor')
    worst=math.fsum(abs(v) for v in h[1:])
    return {'half_opening_V':h[0]-worst,'vertical_opening_V':2*(h[0]-worst),'positive_margin':h[0]>worst}

def pdn_impedance(frequency,branches,source_r=.1,source_l=1e-8):
    f=real(frequency,'frequency Hz',1,1e10);rs=real(source_r,'source R',1e-4,10);ls=real(source_l,'source L',1e-12,1e-4)
    if type(branches) not in (list,tuple) or not 1<=len(branches)<=8:raise ValueError('1..8 [C,ESR,ESL] branches')
    w=2*math.pi*f;zs=complex(rs,w*ls);ys=[1/zs];zslist=[]
    for row in branches:
        if type(row) not in (list,tuple) or len(row)!=3:raise ValueError('branch shape')
        c=real(row[0],'C F',1e-12,1e-2);r=real(row[1],'ESR ohm',1e-4,10);l=real(row[2],'ESL H',1e-12,1e-6)
        z=complex(r,w*l-1/(w*c));zslist.append(z);ys.append(1/z)
    return {'Z_ohm':1/sum(ys),'branch_Z_ohm':zslist,'source_Z_ohm':zs}

def dipole_pattern(theta,phi):
    theta=real(theta,'theta rad',0,math.pi);phi=real(phi,'phi rad',-2*math.pi,2*math.pi)
    u=math.sin(theta)**2
    return {'normalized_power':u,'directivity':1.5*u,'power_radius_xyz':(u*math.sin(theta)*math.cos(phi),u*math.sin(theta)*math.sin(phi),u*math.cos(theta))}

def friis_link(pt,gt,gr,frequency,distance,polarization=1,tx_acceptance=1,rx_acceptance=1):
    pt=real(pt,'Pt incident feed W',1e-9,1e3);gt=real(gt,'Gt',.01,1e4);gr=real(gr,'Gr',.01,1e4);f=real(frequency,'frequency',1e6,1e11);r=real(distance,'distance',.01,1e6)
    pol=real(polarization,'polarization factor',0,1);tx=real(tx_acceptance,'tx acceptance',0,1);rx=real(rx_acceptance,'rx acceptance',0,1)
    wavelength=299792458/f
    if r<10*wavelength:raise ValueError('teaching far-field requires r>=10 wavelengths; physical aperture check still caller responsibility')
    return {'received_W':pt*tx*gt*gr*(wavelength/(4*math.pi*r))**2*pol*rx,'wavelength_m':wavelength,'extra_conditions':'free-space far field, linear reciprocal antennas; aperture far-field and obstructions must be checked separately'}
