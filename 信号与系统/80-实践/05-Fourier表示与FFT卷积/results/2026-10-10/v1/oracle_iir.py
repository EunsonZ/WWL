import cmath,hashlib,importlib.util,json,math,pathlib,resource
from decimal import Decimal,localcontext
from fractions import Fraction
import mpmath as mp
import numpy as np
import scipy
from scipy import signal
OUT=pathlib.Path(__file__).resolve().parent;SRC=OUT/'source-layout/信号与系统/80-实践/06-IIR规格与实现/iir_lab.py'
specmod=importlib.util.spec_from_file_location('iir_current',SRC);lab=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(lab)
raw=json.loads((OUT/'iir-cli-output/results.json').read_text());spec=raw['design'];sections=np.asarray(spec['sections']);poles=np.array([complex(z['re'],z['im']) for z in spec['poles']]);mp.mp.dps=80
orders=[]
for fs,fp,name in [(48000,6000,'design'),(96000,6000,'migration_96k'),(48000,5000,'migration_5k')]:
    ratio=mp.tan(mp.pi*8000/fs)/mp.tan(mp.pi*fp/fs);target=(mp.mpf(1000000)-1)/((mp.mpf(100)/99)**2-1)
    n=1
    while ratio**(2*n)<target:n+=1
    d=raw[name];assert d['order']==n and n in (27,30,17)
    orders.append(dict(fs_hz=fs,fp_hz=fp,fsb_hz=8000,minimum_order=n,N_minus1_ratio_power=str(ratio**(2*(n-1))),N_ratio_power=str(ratio**(2*n)),target=str(target),feasible_cutoff_rad_per_s=d['wc_bounds']))
assert [r['minimum_order'] for r in orders]==[27,30,17]
prewarp=2/mp.mpf('.00025')*mp.tan(mp.pi/4);assert abs(prewarp-8000)<mp.mpf('1e-70')
z,p,k=signal.butter(27,spec['wc'],analog=True,output='zpk');zd,pd,kd=signal.bilinear_zpk(z,p,k,fs=48000)
rooterror=max(min(abs(a-b) for b in pd) for a in poles);assert rooterror<1e-14
theta=np.linspace(0,math.pi,4097);scipy_response=signal.freqz_zpk(zd,pd,kd,worN=theta)[1];current_response=signal.sosfreqz(sections,worN=theta)[1]
freqerror=float(np.max(abs(scipy_response-current_response)));assert freqerror<1e-12
rounded=sections.astype(np.float32).astype(np.float64)
radii=[float(np.max(abs(np.roots(row[3:])))) for row in rounded]
assert max(radii)<1 and np.max(abs(np.asarray(raw['binary32_section_radii'])-radii))<1e-12
# Independently evaluate all cells by NumPy arrays and external sosfreqz;
# multiply explicit derivative products rather than library prefix/suffix code.
band_results={};worst_samples=[];epsilon=np.finfo(np.float64).eps
for model,sos in [('binary64_sos',sections),('binary32_sos',rounded)]:
    band_results[model]={}
    for band,start,end in [('pass',0.,math.pi/4),('stop',math.pi/3,math.pi)]:
        n=65536;width=(end-start)/n;half=width/2;centers=start+(np.arange(n)+.5)*width;q=np.exp(-1j*centers)
        B=sos[:,0,None]+sos[:,1,None]*q+sos[:,2,None]*q*q
        A=1+sos[:,4,None]*q+sos[:,5,None]*q*q
        Bd=(abs(sos[:,1])+2*abs(sos[:,2]))[:,None];Ad=(abs(sos[:,4])+2*abs(sos[:,5]))[:,None]
        U=abs(B)+Bd*half;V=abs(A)-Ad*half;assert np.min(V)>0
        M=U/V;L=Bd/V+U*Ad/(V*V)
        derivative=np.zeros(n)
        for i in range(len(sos)):derivative+=L[i]*np.prod(np.delete(M,i,axis=0),axis=0)
        amplitude=abs(signal.sosfreqz(sos,worN=centers)[1]);margin=derivative*half;lower=np.maximum(0.,amplitude-margin);upper=amplitude+margin
        result=dict(lower=float(np.min(lower)),upper=float(np.max(upper)),max_cell_margin=float(np.max(margin)),minimum_denominator_cell_lower=float(np.min(V)),minimum_numerator_cell_upper=float(np.min(U)),minimum_center_denominator=float(np.min(abs(A))),grid_intervals=n,halfwidth_rad_per_sample=half)
        original=raw['coefficient_band_bounds'][model][band]
        for key in ('lower','upper','max_cell_margin'):assert abs(result[key]-original[key])<1e-11,(model,band,key)
        indices=sorted(set([0,n-1,int(np.argmin(lower)),int(np.argmax(upper)),int(np.argmax(margin))]))
        checks=[]
        for index in indices:
            t=float(centers[index]);tm=mp.mpf(t);hm=mp.mpf(half);qm=mp.exp(-mp.j*tm);center=mp.mpc(1);mf=[];ld=[];vmin=mp.inf
            for row in sos:
                b0,b1,b2,a0,a1,a2=[mp.mpf(float(v)) for v in row]
                num=b0+b1*qm+b2*qm*qm;den=1+a1*qm+a2*qm*qm
                up=abs(num)+(abs(b1)+2*abs(b2))*hm;vd=abs(den)-(abs(a1)+2*abs(a2))*hm;vmin=min(vmin,vd)
                mf.append(up/vd);ld.append((abs(b1)+2*abs(b2))/vd+up*(abs(a1)+2*abs(a2))/vd**2);center*=num/den
            deriv=sum(ld[i]*mp.fprod(mf[:i]+mf[i+1:]) for i in range(len(mf)))
            hp_lower=max(mp.mpf(0),abs(center)-deriv*hm);hp_upper=abs(center)+deriv*hm
            row=dict(index=index,theta_rad_per_sample=t,mpmath_precision_decimal_digits=80,high_precision_lower=str(hp_lower),high_precision_upper=str(hp_upper),high_precision_denominator_lower=str(vmin),float_lower=float(lower[index]),float_upper=float(upper[index]),abs_float_vs_high_precision_lower=float(abs(mp.mpf(float(lower[index]))-hp_lower)),abs_float_vs_high_precision_upper=float(abs(mp.mpf(float(upper[index]))-hp_upper)))
            checks.append(row)
        result['high_precision_selected_cells']=checks
        result['selected_max_float_error']=max(max(c['abs_float_vs_high_precision_lower'],c['abs_float_vs_high_precision_upper']) for c in checks)
        band_results[model][band]=result
    r=band_results[model];r['contract_slacks']={'pass_lower_above_0.99':r['pass']['lower']-.99,'pass_upper_below_1.01':1.01-r['pass']['upper'],'stop_upper_below_0.001':.001-r['stop']['upper']}
    assert min(r['contract_slacks'].values())>0
# Independent phase derivative from external SciPy response, poles and global delay bound.
edge=math.pi/4;grid=np.linspace(0,edge,32769);delays=.5*np.sum((1-abs(poles)**2)[:,None]/abs(1-poles[:,None]*np.exp(-1j*grid))**2,axis=0)
distances=[]
for pole in poles:
    angle=float(np.angle(pole));closest=min(edge,max(0.,angle));distances.append(abs(1-pole*cmath.exp(-1j*closest)))
K=float(np.sum((1-abs(poles)**2)*abs(poles)/np.asarray(distances)**4));delayupper=float(np.max(delays)+K*edge/(2*32768))
assert delayupper<=96 and abs(delayupper-raw['delay']['upper_samples'])<1e-11
phase_checks=[]
for t in (0.,.1,.4,.78):
    v=signal.sosfreqz(sections,worN=[t-1e-6,t+1e-6])[1];numeric=-np.angle(v[1]/v[0])/(2e-6);analytic=.5*sum((1-abs(p)**2)/abs(1-p*cmath.exp(-1j*t))**2 for p in poles)
    assert abs(numeric-analytic)<2e-7;phase_checks.append(dict(theta=t,phase_difference_delay_samples=float(numeric),pole_formula_delay_samples=float(analytic)))
# Independent direct-I Decimal cascades with histories, not transposed internal states.
x=[.6*math.cos(2*math.pi*1000*n/48000)+.3*math.cos(2*math.pi*10000*n/48000) for n in range(12000)]
with localcontext() as ctx:
    ctx.prec=80;values=list(map(Decimal.from_float,x))
    for row in sections:
        b0,b1,b2,a0,a1,a2=[Decimal.from_float(float(v)) for v in row];history_x=[Decimal(0),Decimal(0)];history_y=[Decimal(0),Decimal(0)];output=[]
        for u in values:
            y=b0*u+b1*history_x[0]+b2*history_x[1]-a1*history_y[0]-a2*history_y[1]
            output.append(y);history_x=[u,history_x[0]];history_y=[y,history_y[0]]
        values=output
reference=np.array([float(v) for v in values]);assert max(abs(np.array([float(v) for v in lab.decimal_sos(sections.tolist(),x)])-reference))<1e-14
def f32(v):
    result=np.float32(v)
    if not np.isfinite(result):raise ArithmeticError('binary32 range exceeded')
    return result
trajectories={};metrics={}
for label,sos in [('ascending',sections),('descending',sections[::-1])]:
    coefficients=sos.astype(np.float32);state=np.zeros((len(sos),2),np.float32);statepeak=np.zeros(len(sos));outputpeak=np.zeros(len(sos));ys=[]
    for original in x:
        u=f32(original)
        for i,row in enumerate(coefficients):
            b0,b1,b2,a0,a1,a2=row;y=f32(f32(b0*u)+state[i,0]);s1=f32(f32(state[i,1]+f32(b1*u))-f32(a1*y));s2=f32(f32(b2*u)-f32(a2*y));state[i]=[s1,s2];statepeak[i]=max(statepeak[i],abs(s1),abs(s2));outputpeak[i]=max(outputpeak[i],abs(y));u=y
        ys.append(float(u))
    actual=lab.float_sos(sos.tolist(),x);assert actual['status']=='complete' and np.array_equal(np.asarray(actual['output']),ys)
    error=float(np.max(abs(np.asarray(ys)-reference)));scaled=float(np.max(abs(np.asarray(ys)-reference)/(1+abs(reference))))
    assert abs(error-raw['precision'][label]['max_abs_error_v'])<1e-13 and abs(scaled-raw['precision'][label]['max_scaled_error_v'])<1e-13
    for i,m in enumerate(actual['section_metrics']):assert m['peak_state']==statepeak[i] and m['peak_output']==outputpeak[i]
    trajectories[label]=ys;metrics[label]=dict(samples=len(ys),max_abs_error_v=error,max_scaled_error_v=scaled,state_peaks_v=statepeak.tolist(),output_peaks_v=outputpeak.tolist(),bitwise_matches_current=True)
# Expanded direct binary32: preserve finite prefix and first overflowing sample.
directb=np.asarray([float(Decimal(v)) for v in raw['direct_coefficients']['b']],np.float32);directa=np.asarray([float(Decimal(v)) for v in raw['direct_coefficients']['a']],np.float32);state=np.zeros(27,np.float32);direct=[];first=None
with np.errstate(over='ignore',invalid='ignore'):
    for n,original in enumerate(x):
        try:
            u=f32(original);y=f32(f32(directb[0]*u)+state[0]);new=[]
            for i in range(27):new.append(f32(f32((state[i+1] if i<26 else 0.)+f32(directb[i+1]*u))-f32(directa[i+1]*y)))
        except ArithmeticError:first=n;break
        state=np.array(new,np.float32);direct.append(float(y))
assert first==raw['precision']['direct']['first_sample']==425 and len(direct)==425
currentdirect=lab.float_structure(directb.astype(float).tolist(),directa.astype(float).tolist(),x);assert currentdirect['output']==direct
# Exact integer fixed-point storage oracle, Fraction tie-to-even, all 20 samples.
fixed={}
for label,b0s in [('fixed_high_first',[64,1]),('fixed_low_first',[1,64])]:
    states=[[0,0],[0,0]];events=[];outputs=[];sats=[0,0];peaks=[0,0];accums=[]
    for n in range(20):
        u=32;intermediate=[]
        for i,b0 in enumerate(b0s):
            old=states[i][:]
            def storage(acc):
                assert -(1<<23)<=acc<(1<<23);rawcode=round(Fraction(acc,16));clipped=max(-128,min(127,rawcode));sats[i]+=int(clipped!=rawcode);accums.append(dict(n=n,stage=i,accumulator=acc,raw_code=rawcode,stored_code=clipped));return clipped
            y=storage(b0*u+16*old[0]);states[i]=[storage(8*y+16*old[1]),storage(0)];peaks[i]=max(peaks[i],abs(y),*map(abs,states[i]));intermediate.append(y);u=y
        outputs.append(u);events.append(dict(n=n,intermediate_codes=intermediate,states=[s[:] for s in states]))
    assert raw[label]['events']==events and raw[label]['output_codes']==outputs and raw[label]['saturations']==sats and raw[label]['peak_codes']==peaks
    fixed[label]=dict(outputs=outputs,saturations=sats,events=events,stores=accums,units='integer code times 1/16 V',W=8,F=4,accumulator_bits=24,input_v=2)
assert fixed['fixed_high_first']['outputs'][-1]==16 and fixed['fixed_low_first']['outputs'][-1]==32 and sum(fixed['fixed_low_first']['saturations'])==0
assert round(Fraction(3,4))==1
badroot=max(np.roots([1,-1.9802,.9801]));assert badroot>1
allpassdc=(1-mp.mpf('.99')**2)/(1-mp.mpf('.99'))**2;assert abs(allpassdc-199)<mp.mpf('1e-70')
(OUT/'iir-trajectories-and-inputs.json').write_text(json.dumps(dict(input_formula='.6cos(2π1000n/48000)+.3cos(2π10000n/48000)',n_range=[0,11999],input_v=x,independent_Decimal80_reference_v=reference.tolist(),binary32_outputs_v=trajectories,direct_binary32_finite_prefix_v=direct,direct_first_failure_sample=first,fixed_point=fixed),indent=2)+'\n')
result=dict(status='pass',source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),orders=orders,prewarp_rad_per_s=str(prewarp),external_scipy_root_max_error=rooterror,external_frequency_4097_max_complex_error=freqerror,binary32_section_radii=radii,continuous_band_model_recalculation=band_results,delay=dict(max_grid_samples=float(np.max(delays)),global_derivative_bound=K,minimum_pole_denominator_distance=float(min(distances)),upper_samples=delayupper,budget_samples=96,phase_checks=phase_checks),trajectories=metrics,direct_binary32=dict(first_failure_sample=first,finite_prefix_samples=len(direct),prefix_bitwise_matches_current=True),fixed_point_20_sample_matches=True,unstable_perturbed_denominator_root=float(badroot),allpass_dc_samples=str(allpassdc),allpass_dc_ms=float(allpassdc/48000*1000),environment=dict(numpy=np.__version__,scipy=scipy.__version__,mpmath=mp.__version__,float64_epsilon=epsilon,self_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),arithmetic_boundary='Exact-real local quotient/product inequality independently evaluated in binary64; selected extreme cells cross-checked at 80 decimal digits. Selected error is not a certified bound over all cells and transcendental evaluations have no outward rounding enclosure, so this is numerical evidence rather than strict machine-certified continuous-band proof.',scope='Finite current coefficient/model/trajectory checks; no actual audio/DSP chip, all-input state bound, deadline or learner claim')
(OUT/'iir-independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status='pass',orders=[r['minimum_order'] for r in orders],delay_upper=delayupper,continuous_model_slacks={k:v['contract_slacks'] for k,v in band_results.items()},direct_first_failure=first,trajectory_metrics=metrics),indent=2))
