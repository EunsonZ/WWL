import cmath,hashlib,importlib.util,itertools,json,math,pathlib,resource
import numpy as np
from scipy.integrate import quad
OUT=pathlib.Path(__file__).resolve().parent
SRC=OUT/'source-layout/信号与系统/80-实践/05-Fourier表示与FFT卷积/fourier_lab.py'
spec=importlib.util.spec_from_file_location('fourier_current',SRC);lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
raw=json.loads((OUT/'fourier-cli-output/results.json').read_text())
def unpack(x):
    if isinstance(x,dict) and set(x)=={'im','re'}:return complex(x['re'],x['im'])
    if isinstance(x,dict):return {k:unpack(v) for k,v in x.items()}
    if isinstance(x,list):return list(map(unpack,x))
    return x
data=unpack(raw);records=[]
def close(name,a,b):
    assert len(a)==len(b)
    error=max((abs(x-y)/(1+abs(y)) for x,y in zip(a,b)),default=0.)
    assert error<=2e-11,(name,error)
    records.append(dict(name=name,scaled_max_error=error))
def direct_dft(x):
    n=len(x);matrix=np.cos(-2*np.pi*np.outer(np.arange(n),np.arange(n))/n)+1j*np.sin(-2*np.pi*np.outer(np.arange(n),np.arange(n))/n)
    return (matrix@np.array(x)).tolist()
def convolve(x,h):
    out=[0j]*(len(x)+len(h)-1)
    for i,j in itertools.product(range(len(x)),range(len(h))):out[i+j]+=x[i]*h[j]
    return out
x=[1,2,1,0];close('fixed four DFT',data['four']['dft'],[4,-2j,0,2j]);close('fixed four FFT',data['four']['fft'],[4,-2j,0,2j]);close('DTFS scale',data['four']['dtfs'],[1,-.5j,0,.5j])
assert abs(data['four']['dtft_pi_over_four']-(1+math.sqrt(2))*(1-1j))<1e-13
close('even branch',lab.fft(x[::2]),[2,0]);close('odd branch',lab.fft(x[1::2]),[2,2])
expected={'symfull':([1,2,1,0],[1,1,1],[1,3,4,3,1,0]),'asymfull':([1,2,4],[1,2],[1,4,8,8]),'flipfull':([1,2,4],[2,1],[2,5,10,4])}
for name,(a,h,target) in expected.items():close(name,convolve(a,h),target);close(name+' FFT',lab.fft_linear_convolution(a,h),target)
for n,a,h in [(3,[1,2,4],[1,2]),(4,[1,2,4],[1,2]),(4,x,[1,1,1]),(8,x,[1,1,1])]:
    full=convolve(a,h);fold=[sum(full[j] for j in range(k,len(full),n)) for k in range(n)]
    close('DFT product n'+str(n),lab.frequency_convolution(a,h,n,not(n&n-1)),fold)
close('CNN real valid',lab.valid_correlation([1,2,4],[1,2]),[5,10])
S0=np.array([[0,0,0],[1,0,0],[0,1,0]]);C0=np.array([[1,2,0],[0,1,2],[0,0,1]])
Sp=np.array([[0,0,1],[1,0,0],[0,1,0]]);Cp=np.eye(3)+2*Sp.T;a=np.array([1,2,4])
assert not np.array_equal(C0@S0,S0@C0) and np.array_equal(Cp@Sp,Sp@Cp)
for name,mat in [('C0_S0',C0@S0),('S0_C0',S0@C0),('Cp_Sp',Cp@Sp),('Sp_Cp',Sp@Cp)]:close(name,data['boundary'][name],mat@a)
partitions=[];a=[1,-2,3,0,4,-1]
for m,h in [(1,[2]),(2,[1,2]),(4,[1,-1,2,.5]),(9,[1]*9)]:
    for cuts in itertools.product((0,1),repeat=5):
        indices=[0]+[i+1 for i,c in enumerate(cuts) if c]+[6];blocks=[a[i:j] for i,j in zip(indices,indices[1:])]
        stream=lab.OverlapAdd(h);output=[];offsets=[]
        for block in [[],*blocks,[]]:offsets.append(stream.consumed);output.extend(stream.push(block))
        output.extend(stream.flush());close('OLA m'+str(m)+' cuts'+str(cuts),output,convolve(a,h))
        assert stream.flush()==[]
        try:stream.push([])
        except ValueError:pass
        else:raise AssertionError('push after EOF')
        partitions.append(dict(kernel=h,cuts=list(cuts),blocks=blocks,offsets=offsets))
s=lab.OverlapAdd([1,2,3]);s.push([1]);before=s.snapshot
for bad in [[2,float('nan')],[True],[[1]],'12',None]:
    try:s.push(bad)
    except ValueError:pass
    else:raise AssertionError('invalid block accepted')
    assert s.snapshot==before
close('main OLA full',data['ola']['output'],[1,3,4,3,1,0]);assert [e['offset'] for e in data['ola']['events']]==[0,2,2,4]
for n in (1,2,4,8,16):
    a=[complex(3*k%7-2,5*k%11-4) for k in range(n)];close('complex FFT '+str(n),lab.fft(a),direct_dft(a));close('inverse '+str(n),lab.ifft(lab.fft(a)),a)
record=[math.cos(2*math.pi*1.25*n/4) for n in range(4)]
close('zero padding DTFT samples',data['window']['dft_n16'],direct_dft(record+[0]*12));close('old grid retained',data['window']['dft_n16'][::4],data['window']['dft_n4'])
# Finite continuous examples test normalization, not general convergence claims.
ctfs=[]
for k in (-2,-1,0,1,2):
    re=quad(lambda t:(1+2*math.cos(2*math.pi*t))*math.cos(2*math.pi*k*t),0,1,epsabs=1e-13)[0]
    im=quad(lambda t:-(1+2*math.cos(2*math.pi*t))*math.sin(2*math.pi*k*t),0,1,epsabs=1e-13)[0]
    e=1 if k in (-1,0,1) else 0;assert abs(complex(re,im)-e)<1e-12;ctfs.append(dict(k=k,coefficient=[re,im],expected=e))
close('CTFS sampling aliases N2',lab.dft([3,-1]),[2,4])
ctft=[]
for omega in (0.,1.,4.):
    value=quad(lambda t:math.exp(-t*t)*math.cos(omega*t),-10,10,epsabs=1e-13)[0];expected=math.sqrt(math.pi)*math.exp(-omega*omega/4)
    assert abs(value-expected)<1e-12;ctft.append(dict(omega_rad_per_s=omega,integrated_value=value,analytic_gaussian=expected,finite_integral_limits=[-10,10]))
output=dict(status='pass',source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),comparisons=records,OLA_partitions=partitions,continuous_examples=dict(CTFS_period_s=1,CTFS_coefficients=ctfs,CTFS_N2_DTFS=[1,2],CTFT_Gaussian=ctft),fixed_inputs=dict(four=x,asymmetric=[1,2,4],kernel=[1,2],tolerance_scaled=2e-11,units='samples/DFT coefficients V; CTFT integration uses seconds, spectrum V*s; theta rad/sample'),self_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limitations='Finite tests and quadrature do not prove general recovery/convergence or arbitrary streaming partitions; general claims require independent theory review')
(OUT/'fourier-independent.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='pass',comparisons=len(records),OLA_partitions=len(partitions),max_scaled_error=max(r['scaled_max_error'] for r in records)),indent=2))
