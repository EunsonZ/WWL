"""Bounded real-parameter teaching models. Import has no I/O or heavy dependencies."""
import math
import cmath
import numbers


def real(x, name, lo, hi):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise ValueError(name + ': real scalar required (no bool/complex/container)')
    x = float(x)
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(name + ': outside finite supported interval')
    return x


def checked(z):
    if isinstance(z, complex):
        good = math.isfinite(z.real) and math.isfinite(z.imag)
    else:
        good = math.isfinite(z)
    if not good:
        raise ValueError('derived nonfinite output')
    return z


def bracket(fun, lo, hi):
    """Internal bounded bisection; no product sign test or endless float midpoint."""
    fl, fh = checked(fun(lo)), checked(fun(hi))
    if fl == 0: return lo
    if fh == 0: return hi
    if (fl > 0) == (fh > 0): raise ValueError('root not bracketed')
    for _ in range(200):
        mid = lo + (hi - lo) / 2
        if mid == lo or mid == hi: return mid
        fm = checked(fun(mid))
        if fm == 0: return mid
        if (fm > 0) == (fl > 0): lo, fl = mid, fm
        else: hi, fh = mid, fm
    raise ValueError('root iteration budget exhausted')


def tia(f, rf=1e6, ct=30e-12, cf=1e-12, a0=1e5, ft=10e6):
    f = real(f, 'f Hz', 0, 1e9)
    rf = real(rf, 'Rf ohm', 1, 1e9)
    ct = real(ct, 'CT F', 1e-15, 1e-9)
    cf = real(cf, 'CF F', 0, 1e-9)
    a0 = real(a0, 'A0', 1e3, 1e8)
    ft = real(ft, 'fT Hz', 1e3, 1e8)
    s = 2j * math.pi * f
    wp = 2 * math.pi * ft / a0
    a = a0 / (1 + s / wp)
    ng = (1 + s * rf * (ct + cf)) / (1 + s * rf * cf)
    z = -rf * a / ((1 + s * rf * cf) * (a + ng))
    hn = a * ng / (a + ng)
    return {'z_ohm': checked(z), 'noise_gain': checked(ng),
            'voltage_noise_transfer': checked(hn), 'loop': checked(a / ng)}


def tia_metrics(rf=1e6, ct=30e-12, cf=1e-12, a0=1e5, ft=10e6):
    tia(0, rf, ct, cf, a0, ft)  # all inputs before derived outputs
    fc = 10 ** bracket(lambda x: math.log10(abs(tia(10**x,rf,ct,cf,a0,ft)['loop'])), -6, 9)
    pm = 180 + math.degrees(cmath.phase(tia(fc,rf,ct,cf,a0,ft)['loop']))
    wp = 2 * math.pi * ft / a0
    c2, c1, c0 = rf*(ct+cf), 1+wp*rf*(ct+cf)+a0*wp*rf*cf, wp*(1+a0)
    d = cmath.sqrt(c1*c1-4*c2*c0)
    q = -.5 * (c1+d)  # stable quadratic roots: avoid subtracting near-equal numbers
    poles = (q/c2,c0/q)
    return {'cross_Hz': checked(fc), 'PM_deg': checked(pm), 'poles_rad_s': [checked(p) for p in poles],
            'denominator_s': [c2,c1,c0]}


def instrumentation(v1, v2, rf=1e4, rg=2e3, k1=10, k2=10, vref=2.5):
    v1=real(v1,'v1 V',0.5,4.5); v2=real(v2,'v2 V',0.5,4.5)
    rf=real(rf,'Rf ohm',100,1e6); rg=real(rg,'Rg ohm',100,1e6)
    k1=real(k1,'k1',0.1,100); k2=real(k2,'k2',0.1,100); vref=real(vref,'ref V',0.2,4.8)
    o1=v1+rf/rg*(v1-v2); o2=v2+rf/rg*(v2-v1)
    vo=(1+k1)*(k2*o2+vref)/(1+k2)-k1*o1
    g1=1+2*rf/rg
    ad=g1*((1+k1)*k2/(1+k2)+k1)/2; ac=(k2-k1)/(1+k2)
    cmrr=None if ac==0 else 20*math.log10(abs(ad/ac))
    return {'o1_V':checked(o1),'o2_V':checked(o2),'vo_V':checked(vo),'Ad':checked(ad),'Acm':checked(ac),
            'CMRR_dB':cmrr,'within_teaching_output_range':all(.2<=x<=4.8 for x in (o1,o2,vo))}


def thresholds(vlo=.1,vhi=4.9,vref=2.5,rref=1e4,rfb=2e4,rpull=None):
    vlo=real(vlo,'low V',0,.5); vhi=real(vhi,'high V',4,5)
    vref=real(vref,'ref V',1,4); rref=real(rref,'Rref ohm',100,1e6); rfb=real(rfb,'Rfb ohm',100,1e6)
    if rpull is not None:
        rpull=real(rpull,'Rpull ohm',100,1e6)
        # Released output, 5 V pullup and feedback chain to stiff reference.
        vhi=(5/rpull+vref/(rref+rfb))/(1/rpull+1/(rref+rfb))
    alpha=rref/(rref+rfb)
    low=(1-alpha)*vref+alpha*vlo; high=(1-alpha)*vref+alpha*vhi
    if not vlo < low < high < vhi: raise ValueError('no two accessible thresholds')
    return {'low_V':low,'high_V':high,'released_high_V':vhi,'alpha':alpha}


def oscillator(r=1e4,c=1e-8,delay=0,vlo=.1,vhi=4.9):
    r=real(r,'R ohm',100,1e6); c=real(c,'C F',1e-12,1e-5); delay=real(delay,'delay s',0,1e-3)
    th=thresholds(vlo,vhi)
    tau=r*c
    if delay > .1*tau: raise ValueError('delay model limited to 0..0.1 RC')
    lo,hi=th['low_V'],th['high_V']
    lower=vlo+(lo-vlo)*math.exp(-delay/tau); upper=vhi+(hi-vhi)*math.exp(-delay/tau)
    high=tau*math.log((vhi-lower)/(vhi-hi))+delay
    low=tau*math.log((upper-vlo)/(lo-vlo))+delay
    return {'tau_s':tau,'t_high_s':high,'t_low_s':low,'period_s':high+low,'frequency_Hz':1/(high+low),
            'cap_min_V':lower,'cap_max_V':upper,**th}


def prototype(kind):
    """Order 2; unity DC and common relative -3 dB angular corner = 1 rad/s."""
    if not isinstance(kind,str): raise ValueError('kind must be string enum')
    if kind == 'butterworth': a,b=math.sqrt(2),1.
    elif kind == 'bessel': a,b=3.,3.
    elif kind == 'chebyshev1':
        eps=math.sqrt(10**.1-1); alpha=math.asinh(1/eps)/2
        a=math.sqrt(2)*math.sinh(alpha); b=(math.sinh(alpha)**2+math.cosh(alpha)**2)/2
    else: raise ValueError('kind: butterworth/bessel/chebyshev1')
    t=(-(a*a-2*b)+math.sqrt((a*a-2*b)**2+4*b*b))/2
    scale=math.sqrt(t)
    return {'a':a/scale,'b':b/(scale*scale),'raw_corner':scale,'Q':math.sqrt(b)/a}


def prototype_response(kind, w):
    w=real(w,'normalized angular frequency',0,1e4); p=prototype(kind);a,b=p['a'],p['b']
    h=b/(b-w*w+1j*a*w)
    tau=a*(b+w*w)/((b-w*w)**2+a*a*w*w)
    return {'H':checked(h),'group_delay_normalized':checked(tau)}


def filter_model(kind,f,r1=1e4,r2=1e4,r3=1e4,c1=1e-8,c2=1e-8,k=1.585786437626905,a0=None,ft=1e6):
    """Defined nodes in README. Ideal or single-pole finite A; unloaded output."""
    f=real(f,'f Hz',0,1e8)
    r1=real(r1,'R1 ohm',100,1e6);r2=real(r2,'R2 ohm',100,1e6);r3=real(r3,'R3 ohm',100,1e6)
    c1=real(c1,'C1 F',1e-12,1e-5);c2=real(c2,'C2 F',1e-12,1e-5);k=real(k,'K',1,2.9)
    ft=real(ft,'fT Hz',1e3,1e8)
    if a0 is not None: a0=real(a0,'A0',1e3,1e8)
    if not isinstance(kind,str):raise ValueError('kind must be string enum')
    if kind not in ('sk','mfb'):raise ValueError('kind: sk/mfb')
    s=2j*math.pi*f
    if kind=='sk':
        p=r1*r2*c1*c2;B=c1*(r1+r2)+r1*c2;E=r1*c2;Bideal=B-E*k
        if Bideal<=0:raise ValueError('ideal SK damping not positive')
        h=k/(1+s*Bideal+s*s*p)
        coef=[p,Bideal,1.]
        if a0 is not None:
            wp=2*math.pi*ft/a0;d=wp*(a0+k)
            coef=[p*k,B*k+p*d,k+B*d-E*k*a0*wp,d]
            h=k*a0*wp/(((coef[0]*s+coef[1])*s+coef[2])*s+coef[3])
        w0=1/math.sqrt(p);q=math.sqrt(p)/Bideal;dc=k
    else:
        p=r2*r3*c1*c2;B=c1*(r2+r3+r2*r3/r1)
        coef=[p,B,1.];dc=-r2/r1;h=dc/(1+s*B+s*s*p)
        if a0 is not None:
            at=2*math.pi*ft;wp=at/a0;g=1/r1+1/r2+1/r3
            coef=[p/at,p+(p*wp+r2*r3*c1*g+r2*c2)/at,
                  B+(r2*r3*c1*wp*g+r2*wp*c2+r2/r1+1)/at,1+(r2/r1+1)/a0]
            h=dc/(((coef[0]*s+coef[1])*s+coef[2])*s+coef[3])
        w0=1/math.sqrt(p);q=math.sqrt(p)/B
    stable=all(x>0 for x in coef) and (len(coef)==3 or coef[1]*coef[2]>coef[0]*coef[3])
    return {'H':checked(h),'denominator':coef,'ideal_f0_Hz':w0/(2*math.pi),'ideal_Q':q,'ideal_DC_gain':dc,
            'model_internal_stable':stable}


def precision_dc(vin=2.52,vref=2.5,rf=190e3,rg=10e3,rs=2e3,vos=10e-6,ibplus=5e-9,ibminus=6e-9,a0=1e6):
    vin=real(vin,'vin V',0,5);vref=real(vref,'Vref V',0,5)
    rf=real(rf,'Rf ohm',100,1e6);rg=real(rg,'Rg ohm',100,1e6);rs=real(rs,'Rs ohm',0,1e6)
    vos=real(vos,'Vos V',-.001,.001);ibplus=real(ibplus,'Ib+ A',-1e-6,1e-6)
    ibminus=real(ibminus,'Ib- A',-1e-6,1e-6);a0=real(a0,'A0',1e3,1e8)
    n=1+rf/rg;req=rf*rg/(rf+rg);e=vos-ibplus*rs+ibminus*req
    vo=a0/(a0+n)*(n*vin-(n-1)*vref+n*e)
    ideal=n*vin-(n-1)*vref
    return {'noise_gain':n,'Req_ohm':req,'input_error_V':checked(e),'output_V':checked(vo),
            'ideal_zero_error_V':checked(ideal),'output_error_V':checked(vo-ideal),
            'within_teaching_swing':-4.8<=vo<=4.8}


def reference_budget(bounds_ppm, sigma_ppm=None, vref=2.5):
    vref=real(vref,'reference V',1,5)
    def inputs(values):
        if not isinstance(values,(tuple,list)) or not 1<=len(values)<=20:raise ValueError('1..20 scalar terms required')
        return [real(v,'ppm term',0,1e6) for v in values]
    bounds=inputs(bounds_ppm)
    result={'worst_ppm':sum(bounds),'worst_V':vref*sum(bounds)*1e-6}
    if sigma_ppm is not None:
        sigma=inputs(sigma_ppm)
        result['uncorrelated_sigma_ppm']=math.hypot(*sigma)
        result['uncorrelated_sigma_V']=vref*math.hypot(*sigma)*1e-6
    return result


def examples():
    return {'precision_dc':precision_dc(),'tia_cf1p':tia_metrics(),'tia_cf0':tia_metrics(cf=0),
      'ina_match':instrumentation(2.495,2.505),'ina_ratio_mismatch':instrumentation(2.7,2.7,k2=10.01),
      'pushpull_thresholds':thresholds(),'open_drain_thresholds':thresholds(rpull=1e4),
      'oscillator':oscillator(),'oscillator_delay1us':oscillator(delay=1e-6),
      'prototypes':{k:prototype(k) for k in ('butterworth','chebyshev1','bessel')},
      'sk':filter_model('sk',0,a0=1e5),'mfb':filter_model('mfb',0,c2=4.5e-8,a0=1e5),
      'ref_uncalibrated':reference_budget([500,375,20,40,2]),
      'ref_calibrated':reference_budget([375,20,40,2,10]),
      'reference_known_sigmas':reference_budget([500,375,20,40,2],[50,10,5,4,1])}


def generate(output):
    import json
    import csv
    from pathlib import Path
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    def default(z):
        if isinstance(z,complex):return {'real':z.real,'imag':z.imag}
        raise TypeError(type(z).__name__)
    (out/'results.json').write_text(json.dumps(examples(),ensure_ascii=False,indent=2,default=default,allow_nan=False)+'\n')
    with (out/'frequency.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['f_Hz','TIA_abs_ohm','noise_gain_abs','loop_phase_deg','SK_finite_abs','MFB_finite_abs'])
        for j in range(241):
            hz=10**(j/40);t=tia(hz)
            wr.writerow([hz,abs(t['z_ohm']),abs(t['noise_gain']),math.degrees(cmath.phase(t['loop'])),
                abs(filter_model('sk',hz,a0=1e5)['H']),abs(filter_model('mfb',hz,c2=4.5e-8,a0=1e5)['H'])])
    return out


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    args=p.parse_args();generate(args.output)

if __name__=='__main__':main()
