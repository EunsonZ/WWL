"""M13 bounded SI teaching models. Import is inert; NumPy is loaded per call."""
import argparse
import json
import math
from numbers import Real, Complex
from pathlib import Path

KB=1.380649e-23
QE=1.602176634e-19

def real(x,lo=-1e100,hi=1e100):
    if isinstance(x,bool) or not isinstance(x,Real) or not math.isfinite(x) or not lo<=x<=hi:
        raise ValueError('finite real scalar outside documented range')
    return float(x)

def integer(x,lo,hi):
    if isinstance(x,bool) or not isinstance(x,int) or not lo<=x<=hi:raise ValueError('bounded integer required')
    return x

def cscalar(x):
    if isinstance(x,bool) or not isinstance(x,Complex):raise ValueError('finite numeric complex scalar required')
    z=complex(x)
    if not math.isfinite(z.real) or not math.isfinite(z.imag) or abs(z)>1e100:raise ValueError('complex outside range')
    return z

def thermal(r,t=300):return 4*KB*real(t,1,2000)*real(r,1e-3,1e12)
def shot(i,fano=1):return 2*QE*real(i,0,1)*real(fano,0,10)

def rc_band(r,c,t=300,low=0,high=None):
    r=real(r,1e-3,1e12);c=real(c,1e-15,1);t=real(t,1,2000);low=real(low,0,1e12)
    fc=1/(2*math.pi*r*c)
    if high is None:angle=math.atan2(fc,low)
    else:
        high=real(high,0,1e12)
        if high<=low:raise ValueError('ordered nonempty band required')
        # Difference-of-atan identity avoids cancellation for high-frequency bands.
        angle=math.atan2((high-low)/fc,1+(high/fc)*(low/fc))
    return {'fc_Hz':fc,'bandwidth_Hz':fc*angle,'variance_V2':4*KB*t*r*fc*angle}

def rc_state_variance(time,r,c,t=300,initial_variance=0):
    time=real(time,0,1e12);r=real(r,1e-3,1e12);c=real(c,1e-15,1);t=real(t,1,2000);v=real(initial_variance,0,1e12)
    z=-2*time/(r*c)
    return v*math.exp(z)+(KB*t/c)*(-math.expm1(z))

def white_flicker(white,d,low,high):
    w=real(white,0,1);d=real(d,0,1);lo=real(low,1e-12,1e12);hi=real(high,1e-12,1e12)
    if hi<=lo:raise ValueError('ordered positive band required')
    return w*(hi-lo)+d*math.log(hi/lo)

def ports(f,ri=10000,rf=90000,rp=2000,a0=100000,fp=10):
    f=real(f,0,1e12);ri=real(ri,1e-3,1e12);rf=real(rf,1e-3,1e12);rp=real(rp,1e-3,1e12);a0=real(a0,1,1e12);fp=real(fp,1e-9,1e9)
    k=rf/ri;n=1+k;d=1+n*(1+1j*f/fp)/a0
    return {'signal':-k/d,'en':n/d,'ip':-rp*n/d,'im':rf/d,'ri_noise':-k/d,'rf_noise':-1/d,'rp_noise':n/d}

def spectral_output(h,s):
    """Sij=E[Ni Nj*]; h is ROW. Output h S h^H, never h^H S h."""
    import numpy as np
    if not isinstance(h,(list,tuple)) or not 1<=len(h)<=8:raise ValueError('1..8 transfer coefficients required')
    hs=np.array([cscalar(v) for v in h],complex);n=len(h)
    if not isinstance(s,(list,tuple)) or len(s)!=n or any(not isinstance(row,(list,tuple)) or len(row)!=n for row in s):raise ValueError('square matching matrix required')
    a=np.array([[cscalar(v) for v in row] for row in s],complex)
    # Normalize each physical source by its own PSD scale before PSD check.
    diag=a.diagonal()
    if any(z.imag!=0 or z.real<0 for z in diag):raise ValueError('nonnegative real diagonal required')
    if not np.array_equal(a,a.conj().T):raise ValueError('Hermitian matrix required')
    d=diag.real;active=d>0
    for j in range(n):
        if d[j]==0 and (np.any(a[j]!=0) or np.any(a[:,j]!=0)):raise ValueError('zero diagonal must have zero cross spectra')
    if np.any(active):
        scale=np.sqrt(d[active]);corr=a[np.ix_(active,active)]/scale[:,None]/scale[None,:]
        if np.min(np.linalg.eigvalsh(corr)) < -1e-12:raise ValueError('matrix is not positive semidefinite')
    y=complex(hs@a@hs.conj());bound=float(np.sum(abs(hs[:,None]*a*hs.conj()[None,:])))
    if abs(y.imag)>1e-12*bound or y.real < -1e-12*bound:raise ArithmeticError('nonreal/negative output beyond roundoff')
    if not math.isfinite(y.real):raise ArithmeticError('nonfinite output')
    return max(0.,y.real)

def referred(psd,gain):
    s=real(psd,0,1e100);g=cscalar(gain)
    if abs(g)<1e-100:raise ValueError('signal transfer zero/too small; input equivalent undefined')
    result=s/abs(g)**2
    if not math.isfinite(result):raise ArithmeticError('nonfinite input equivalent')
    return result

def deembed(measured,instrument,uncorrelated=False):
    a=real(measured,0,1e6);b=real(instrument,0,1e6)
    if uncorrelated is not True:return {'status':'unknown_correlation','rms_V':None}
    if a<b:return {'status':'below_instrument_floor','rms_V':None}
    return {'status':'model_difference','rms_V':math.sqrt((a-b)*(a+b))}

def record(x):
    import numpy as np
    if isinstance(x,np.ndarray):
        if x.ndim!=1 or x.dtype.kind not in 'iuf':raise ValueError('real 1D record required before conversion')
        vals=x.tolist()
    elif isinstance(x,(list,tuple)):vals=x
    else:raise ValueError('real sequence required')
    if not 4<=len(vals)<=262144:raise ValueError('record length4..262144')
    return np.array([real(v,-1e6,1e6) for v in vals],float)

def window(n,kind):
    import numpy as np
    n=integer(n,4,262144)
    if kind=='rect':return np.ones(n)
    if kind=='hann':return .5-.5*np.cos(2*np.pi*np.arange(n)/n)
    raise ValueError('rect or periodic hann required')

def periodogram(x,fs,kind='rect',remove_mean=False,y=None):
    import numpy as np
    a=record(x);fs=real(fs,1e-6,1e9)
    if type(remove_mean) is not bool:raise ValueError('boolean mean option required')
    b=a if y is None else record(y)
    if len(a)!=len(b):raise ValueError('matching record lengths required')
    if remove_mean:a=a-a.mean();b=b-b.mean()
    w=window(len(a),kind);xa=np.fft.rfft(w*a);xb=np.fft.rfft(w*b);factor=np.ones(len(xa));factor[1:]=2
    if len(a)%2==0:factor[-1]=1
    norm=fs*float(w@w);p=factor*abs(xa)**2/norm;cross=factor*xa*xb.conj()/norm
    cg=float(w.mean());enbw=fs*float(w@w)/float(w.sum())**2;df=fs/len(a)
    return {'frequency_Hz':np.fft.rfftfreq(len(a),1/fs),'PSD_V2_per_Hz':p,'cross':cross,'bin_Hz':df,'area_V2':float(p.sum()*df),'weighted_mean_square_V2':float((w*a)@(w*a)/(w@w)),'coherent_gain':cg,'window_ENBW_Hz':enbw}

def average_periodogram(x,fs,segment=256,kind='hann'):
    import numpy as np
    a=record(x);segment=integer(segment,4,262144)
    if len(a)%segment or not 1<=len(a)//segment<=128:raise ValueError('exact 1..128 nonoverlapping complete segments required')
    rows=[periodogram(a[j:j+segment],fs,kind) for j in range(0,len(a),segment)]
    return {'frequency_Hz':rows[0]['frequency_Hz'],'PSD_V2_per_Hz':np.mean([r['PSD_V2_per_Hz'] for r in rows],axis=0),'segments':len(rows),'segment_samples':segment,'resolution_Hz':fs/segment,'window_ENBW_Hz':rows[0]['window_ENBW_Hz']}

def correlated_sample(rho,n=4096,seed=20261006):
    import numpy as np
    rho=real(rho,-1,1);n=integer(n,4,262144);seed=integer(seed,0,2**32-1)
    rng=np.random.default_rng(seed);u=rng.standard_normal(n);v=rng.standard_normal(n);x=2*u;y=3*(rho*u+math.sqrt(1-rho*rho)*v);z=x+y;theory=13+12*rho;alpha=.05
    radius=theory*math.sqrt(2/(n*alpha));sample=float(z@z/n)
    return {'rho':rho,'n':n,'seed':seed,'amplitude_unit':'uV; variance and covariance fields in uV^2','theoretical_variance_V2':theory*1e-12,'sample_mean_square_V2':sample*1e-12,'theoretical_variance':theory,'sample_mean_square':sample,'theory_centered_95pct_chebyshev_prediction_interval':[max(0,theory-radius),theory+radius],'interval_scope':'known-zero-mean iid Gaussian generation; conservative prediction interval for sample mean square, not estimated hardware CI','sample_covariance':np.cov(np.stack([x,y]),ddof=1).tolist()}

def results():
    p=ports(0);en=8e-9;ip=im=.3e-12
    terms={'en':abs(p['en'])**2*en**2,'ip':abs(p['ip'])**2*ip**2,'im':abs(p['im'])**2*im**2}
    for name,r in [('ri_noise',10000),('rf_noise',90000),('rp_noise',2000)]:terms[name]=abs(p[name])**2*thermal(r)
    total=math.fsum(terms.values())
    return {'thermal_2k_300K_V2_per_Hz':thermal(2000),'shot_1uA_A2_per_Hz':shot(1e-6),'opamp_DC_output_terms_V2_per_Hz':terms,'opamp_DC_output_ASD_V_per_sqrtHz':math.sqrt(total),'opamp_DC_signal_input_ASD_V_per_sqrtHz':math.sqrt(referred(total,p['signal'])),'rc_2k_10nF':rc_band(2000,1e-8),'rc_2k_10nF_0_to_fc':rc_band(2000,1e-8,high=1/(2*math.pi*2000*1e-8)),'samples':[correlated_sample(r) for r in (-.8,0,.8)],'deembed_5u_3u':deembed(5e-6,3e-6,True),'fft_four_microvolt_record':{k:periodogram([1e-6,3e-6,1e-6,3e-6],4)[k] for k in ('area_V2','coherent_gain','window_ENBW_Hz')}}

def generate(output):
    data=results();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n');return data

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args(argv);generate(args.output);return 0
if __name__=='__main__':raise SystemExit(main())
