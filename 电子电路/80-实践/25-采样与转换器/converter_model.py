"""Bounded SI teaching models; no device, timing or noise validation claim."""
import argparse
import math
import json
from pathlib import Path


def real(x, lo=-100., hi=100.):
    if isinstance(x, bool) or type(x) not in (int, float):
        raise ValueError('Python real scalar required, not arrays/complex/bool')
    if not lo <= x <= hi or not math.isfinite(x):
        raise ValueError('outside documented finite computational domain')
    return float(x)


def integer(x, lo, hi):
    if isinstance(x, bool) or not isinstance(x, int) or not lo <= x <= hi:
        raise ValueError('integer outside supported domain')
    return x


def levels(bits=3, fsr=3.):
    n = 2**integer(bits, 1, 20)
    return n, real(fsr, .001, 100.) / n


def quantize(v, bits=3, fsr=3.):
    """Unipolar midrise bins; half-open interior, equality goes upper.
    Out-of-range finite input saturates; overload is explicitly returned.
    Reconstruction is bin center, NOT DAC lower-edge voltage.
    """
    n, delta = levels(bits, fsr); v = real(v)
    # Greatest *computed* lower-edge threshold <= v, same ties as DAC/SAR.
    # A fixed bits-step bisection avoids floor(v/delta) rounding inconsistencies.
    lower, upper = 0, n
    for _ in range(bits):
        trial = (lower + upper) // 2
        if v >= trial * delta:
            lower = trial
        else:
            upper = trial
    code = lower
    center = (code+.5)*delta
    return {'code': code, 'binary': format(code, f'0{bits}b'),
            'center_V': center, 'error_V': center-v,
            'overload': v < 0 or v > fsr, 'delta_V': delta}


def dac(code, bits=3, fsr=3.):
    n, delta = levels(bits, fsr)
    return integer(code, 0, n-1)*delta


def sar(v, bits=3, fsr=3.):
    """N comparisons against lower-edge DAC, comparator equality retains bit.
    Held input is bounded, n consecutive decisions, output valid after last.
    """
    v = real(v); levels(bits, fsr); code = 0; trace = []
    for bit in range(bits-1, -1, -1):
        trial = code | (1 << bit); threshold = dac(trial, bits, fsr)
        keep = v >= threshold
        if keep: code = trial
        trace.append({'decision': bits-bit, 'bit_index': bit, 'trial_code': trial,
                      'dac_V': threshold, 'keep': keep, 'retained_code': code})
    return {'code': code, 'trace': trace, 'overload': v < 0 or v > fsr}


def string_tap(resistors, code, fsr=3., load=math.inf):
    """Resistors ordered bottom-to-top, N taps0..N-1, top reference not a code.
    Finite load is from selected node to ground; ideal reference is low Z.
    """
    if not isinstance(resistors, (list, tuple)) or not 2 <= len(resistors) <= 256:
        raise ValueError('2..256 positive resistors required')
    r = [real(v, .001, 1e7) for v in resistors]
    k = integer(code, 0, len(r)-1); vref = real(fsr, .001, 100.)
    if not (type(load) is float and load == math.inf): real(load, .001, 1e9)
    rb, rt = sum(r[:k]), sum(r[k:]); vt = vref*rb/(rb+rt); rout = rb*rt/(rb+rt)
    return {'open_V': vt, 'rout_ohm': rout, 'loaded_V': vt if load==math.inf else vt*load/(load+rout)}


def r2r3(code, fsr=3., resistance=1000., load=math.inf):
    """Three nodes0(out),1,2; R between neighbors; bit branches2R;
    extra2R from node2 to ground. Solves actual tridiagonal KCL.
    """
    code = integer(code, 0, 7); vref = real(fsr, .001, 100.); r=real(resistance,.001,1e7)
    if not (type(load) is float and load == math.inf): real(load,.001,1e9)
    a=[[0.]*3 for _ in range(3)]; b=[0.]*3
    for j in range(3):
        a[j][j]+=.5; b[j]=.5*vref*((code>>(2-j))&1)
    a[2][2]+=.5
    for j in range(2):
        a[j][j]+=1; a[j+1][j+1]+=1; a[j][j+1]-=1; a[j+1][j]-=1
    if load!=math.inf:a[0][0]+=r/load
    for j in range(3):
        pivot=a[j][j]
        for k in range(j+1,3):
            f=a[k][j]/pivot
            for l in range(j,3):a[k][l]-=f*a[j][l]
            b[k]-=f*b[j]
    v=[0.]*3
    for j in range(2,-1,-1):v[j]=(b[j]-sum(a[j][k]*v[k] for k in range(j+1,3)))/a[j][j]
    return v


def cdac(code, vin=0., fsr=3., weights=(4.,2.,1.,1.)):
    """Top initially0, all bottomvin; then floating top, dummy bottom0.
    Top V=-vin+fsr*sum(Cbit*bit)/Ctotal by conserved top charge.
    """
    code=integer(code,0,7); vin=real(vin); ref=real(fsr,.001,100.)
    if not isinstance(weights,(list,tuple)) or len(weights)!=4:raise ValueError('4 positive relative capacitances')
    c=[real(v,.001,1e6) for v in weights]
    return -vin+ref*sum(c[j]*((code>>(2-j))&1) for j in range(3))/sum(c)


def current_dac(code, weights=(4.,2.,1.), unit_A=1e-6, load_ohm=1000.):
    """Ideal positive sources steered to output or dummy, RL to ground.
    No finite output-r/compliance claim: caller must separately verify rail.
    """
    code=integer(code,0,7)
    if not isinstance(weights,(list,tuple)) or len(weights)!=3:raise ValueError('3 relative current weights')
    w=[real(v,.001,1e6) for v in weights]; u=real(unit_A,1e-15,.1); r=real(load_ohm,.001,1e7)
    return sum(w[j]*((code>>(2-j))&1) for j in range(3))*u*r


def rc_state(target, initial, resistance, capacitance, time):
    target,initial=real(target),real(initial);r=real(resistance,.001,1e7);c=real(capacitance,1e-15,1e-3);t=real(time,0,10.)
    tau=r*c;w=-math.expm1(-t/tau)
    return initial*(1-w)+target*w


def rc_sine_error(peak_V, f_Hz, resistance, capacitance):
    a=real(peak_V,0,100.);f=real(f_Hz,0,1e9);r=real(resistance,.001,1e7);c=real(capacitance,1e-15,1e-3)
    x=2*math.pi*f*r*c
    return a*x/math.hypot(1,x) # difference from same-time unfiltered sine


def share(c1, v1, c2, v2):
    c1,c2=real(c1,1e-15,1e-3),real(c2,1e-15,1e-3);v1,v2=real(v1),real(v2)
    return (c1*v1+c2*v2)/(c1+c2)


def reference_cycle(vref=3., q_C=20e-12, capacitance=1e-6, resistance=10., period=10e-6, cycles=4):
    vref=real(vref,.001,100.);q=real(q_C,0,1e-3);c=real(capacitance,1e-15,1e-3);r=real(resistance,.001,1e7);T=real(period,1e-12,10.);n=integer(cycles,1,4096)
    if q/c>100:raise ValueError('charge step exceeds supported rail domain')
    v=vref; rows=[]
    for k in range(n):
        before=v; after=v-q/c;v=rc_state(vref,after,r,c,T)
        rows.append({'cycle':k,'before_V':before,'after_V':after,'next_before_V':v})
    return rows


def fold(f_Hz, fs_Hz):
    f=real(f_Hz,0,1e9);fs=real(fs_Hz,1e-3,1e9)
    return abs((f+fs/2)%fs-fs/2)


def delta_sigma(inputs, initial=0.):
    """Specific first-order normalized accumulator: v+=u, y=sign(v), v-=y.
    Supports |u|<=1, |initial|<=1; not a generic loop stability certificate.
    """
    if not isinstance(inputs,(list,tuple)) or not 1<=len(inputs)<=4096:raise ValueError('1..4096 samples')
    u=[real(x,-1.,1.) for x in inputs];v=real(initial,-1.,1.);states=[v];y=[]
    for x in u:
        q=v+x;out=1 if q>=0 else -1;v=q-out;y.append(out);states.append(v)
    return {'output':y,'state':states}


def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    pars={'bits':3,'range_V':[0,3],'fsr_V':3,'delta_V':.375,'sar_input_V':1.9,'sar_acquisition_us':2,'sar_decision_us':1,'sar_period_us':6,'R_ohm':1000,'Ctrack_F':20e-12,'U4_bits':16,'U4_fsr_V':3.3,'U4_failed_R_ohm':10000,'U4_C_F':20e-12,'U4_acq_s':.5e-6}
    data={'quantizer':[quantize(v) for v in [-.1,0,.375,1.9,3,3.1]],'sar':sar(1.9),'r2r_code5_nodes_V':r2r3(5),'string_mismatch_code4':string_tap([1000]*3+[1200]+[1000]*4,4),'current_mismatch_codes3_4_V':[current_dac(k,(2.9,2,1)) for k in [3,4]],'cdac_code5_top_V':cdac(5,1.9),'U4_failed_residual_V':3.3-rc_state(3.3,0,10000,20e-12,.5e-6),'U4_half_lsb_V':3.3/2**17,'reference_cycle':reference_cycle(),'delta_sigma_DC':delta_sigma([.25]*16)}
    for name,x in [('parameters.json',pars),('results.json',data)]: (output/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return data


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)

if __name__=='__main__':main()
