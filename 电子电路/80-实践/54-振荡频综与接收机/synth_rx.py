"""Finite edge-PFD/CP synthesizer and explicit matched RX, SI; no PDK claim."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import sys
import numpy as np
from scipy.integrate import quad

KB=1.380649e-23
TAU=2*math.pi

def load(path,name):
    before=sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode=True
        spec=importlib.util.spec_from_file_location(name,path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        return mod
    finally:sys.dont_write_bytecode=before

def real(x,name,lo,hi):
    if type(x) not in (int,float) or not math.isfinite(x) or not lo<=x<=hi:
        raise ValueError(name+' outside finite real budget (bool rejected)')
    return float(x)

def validate(c):
    if not isinstance(c,dict):raise ValueError('input object required')
    if c.get('schema')!='synth-rx-v1':raise ValueError('schema synth-rx-v1 required')
    p=c['pll']
    for k,lo,hi in [('reference_Hz',1e5,1e8),('Kv_Hz_per_V',1e5,1e8),('center_Hz',1e6,1e9),('Icp_A',1e-6,1e-3),('C_F',1e-10,1e-6),('center_voltage_V',.1,3),('duration_s',1e-5,.003)]:real(p[k],k,lo,hi)
    if type(p['N']) is not int or not 1<=p['N']<=100:raise ValueError('N integer 1..100')
    if p['reset']!='instantaneous simultaneous reset' or p['filter']!='series_RC_no_parallel_C':raise ValueError('only declared ideal PFD/filter supported')
    lim=p['tune_limits_V']
    if len(lim)!=2:raise ValueError('two tuning limits')
    for x in lim:real(x,'tune voltage',0,5)
    if not lim[0]<p['center_voltage_V']<lim[1]:raise ValueError('center within tuning interval')
    if p['center_Hz']+p['Kv_Hz_per_V']*(lim[0]-p['center_voltage_V'])<=0:raise ValueError('VCO must remain positive')
    if not 1<=len(p['designs'])<=6 or len({d['name'] for d in p['designs']})!=len(p['designs']):raise ValueError('unique finite designs')
    for d in p['designs']:
        if not isinstance(d['name'],str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,30}',d['name']):raise ValueError('safe ASCII design name')
        real(d['R_ohm'],'R',100,1e5)
    if not 1<=len(p['initials'])<=8:raise ValueError('finite initial conditions')
    for a in p['initials']:
        real(a['z_V'],'z',-2,5);real(a['feedback_phase_cycles'],'phase',0,.999999999)
        real(a['reference_Hz'],'case reference',1e5,1e8)
        if p['duration_s']*a['reference_Hz']<40:raise ValueError('at least 40 reference periods per trace')
    # Predict an upper bound before allocating event records.
    fmax=p['center_Hz']+p['Kv_Hz_per_V']*(lim[1]-p['center_voltage_V'])
    bound=sum(math.ceil((a['reference_Hz']+fmax/p['N'])*p['duration_s'])+4 for a in p['initials'])*len(p['designs'])
    if bound>500000:raise ValueError('total event budget exceeds 500000')
    n=c['noise'];f=n['integration_Hz']
    if len(f)!=2 or not 1<=f[0]<f[1]<=1e8:raise ValueError('noise integration Hz')
    if n['convention']!='single_sided_phase_PSD_rad2_per_Hz':raise ValueError('PSD convention')
    for k in ['reference_white','reference_flicker','vco_white','vco_inverse_square','vco_inverse_cube']:real(n[k],k,0,1e8)
    r=c['rx']
    if r['temperature_K']!=300.15 or r['reference_ohm']!=50:raise ValueError('RX fixed temperature/reference')
    if r['buffer']!={'available_gain':1,'F':2,'input_ohm':1000,'output_diff_ohm':50,'power_W':.001}:raise ValueError('fixed explicit unilateral buffer contract')
    for k,lo,hi in [('bandwidth_Hz',1e3,1e6),('wanted_W',1e-15,1e-7),('blocker_each_W',1e-10,1e-4),('IF_gain',1,1e4),('IF_F',1,100),('LNA_IIP3_W',1e-4,1),('IF_peak_budget_W_sqrt',1e-4,1)]:real(r[k],k,lo,hi)
    if len(r['preloss_cases'])>8:raise ValueError('finite attenuation cases')
    for v in r['preloss_cases']:real(v,'loss',1,100)
    bd=r['budgets']
    for key,low,high in [('NF_dB_max',0,100),('gain_dB_min',-100,100),('thermal_plus_RM_SNR_dB_min',-100,100),('C_to_IM3_dB_min',0,100),('power_W_max',1e-6,.1),('LO_jitter_s_max',1e-15,1e-8)]:real(bd[key],key,low,high)
    if not isinstance(r['preloss_cases'],list) or not r['preloss_cases']:raise ValueError('nonempty loss cases')
    if r['reference_ohm']!=50 or r['RF_Hz']!=110e6 or r['blocker_Hz']!=[130e6,150e6] or r['LO_Hz']!=100e6 or r['image_Hz']!=90e6:raise ValueError('fixed spectral port card')
    if p['N']*p['reference_Hz']!=r['LO_Hz']:raise ValueError('RX LO must equal N times nominal reference')
    zlock=p['center_voltage_V']+(p['N']*p['reference_Hz']-p['center_Hz'])/p['Kv_Hz_per_V']
    if any(not lim[0]<zlock-p['Icp_A']*d['R_ohm']<zlock+p['Icp_A']*d['R_ohm']<lim[1] for d in p['designs']):raise ValueError('locked CP pulses lack headroom: continuous NT/S invalid')
    if not n['integration_Hz'][1]<=p['reference_Hz']/10:raise ValueError('average PLL noise limited to fref/10')
    if not 100<=n['integration_Hz'][0]<n['integration_Hz'][1]<=1e6:raise ValueError('phase card integration within 100Hz..1MHz')
    if n['defined_offset_Hz']!=[100,80000000] or r['far_LO_model']!='declared_output_Sphi_equals_scale_times_free_VCO_above_1MHz_not_continuous_PLL_extrapolation':raise ValueError('fixed far-offset provenance')
    if not isinstance(r['far_LO_scale_cases'],list) or not 1<=len(r['far_LO_scale_cases'])<=8:raise ValueError('finite far LO variants')
    for scale in r['far_LO_scale_cases']:real(scale,'far LO scale',.01,100)
    for field in ('IF_power_W','PLL_control_power_W','LO_driver_power_W'):real(r[field],field,0,.1)
    if r['reciprocal_mixing_model']!='real_IF_two_sidebands_fundamental_LO_phase_only':raise ValueError('fixed real IF reduction')
    if r['phase_noise_source']!='separate_declared_teaching_card_not_extracted_from_LC':raise ValueError('phase noise provenance')
    return c

def phase_psd(n,f):
    return n['reference_white']+n['reference_flicker']/f,n['vco_white']+n['vco_inverse_square']/f**2+n['vco_inverse_cube']/f**3

def loop(p,R,f):
    s=1j*TAU*f;k=p['Icp_A']/(TAU)*TAU*p['Kv_Hz_per_V']/p['N']
    L=k*(R+1/(s*p['C_F']))/s
    T=L/(1+L);S=1/(1+L)
    return T,S

def spectrum(p,n,R):
    a=p['Icp_A']*p['Kv_Hz_per_V']*R/p['N'];b=p['Icp_A']*p['Kv_Hz_per_V']/(p['N']*p['C_F'])
    wc=math.sqrt((a*a+math.sqrt(a**4+4*b*b))/2)
    lo,hi=n['integration_Hz'];grid=np.geomspace(lo,hi,401)
    rows=[]
    for f in grid:
        T,S=loop(p,R,float(f));sr,sv=phase_psd(n,float(f))
        rows.append([float(f),float(p['N']**2*abs(T)**2*sr),float(abs(S)**2*sv),float(abs(T)),float(abs(S))])
    def contribution(logf,source):
        f=math.exp(logf);T,S=loop(p,R,f);sr,sv=phase_psd(n,f)
        return f*(p['N']**2*abs(T)**2*sr if source==0 else abs(S)**2*sv)
    var=[quad(contribution,math.log(lo),math.log(hi),args=(j,),epsabs=1e-16,epsrel=1e-10)[0] for j in [0,1]]
    return {'a_per_s':a,'b_per_s2':b,'roots_per_s':[[float(z.real),float(z.imag)] for z in np.roots([1,a,b])], 'unity_Hz':wc/TAU,'PM_deg':math.degrees(math.atan(a*wc/b)), 'delay_first_crossing_s':math.atan(a*wc/b)/wc,'phase_variance_parts_rad2':var,'phase_variance_rad2':sum(var),'jitter_s':math.sqrt(sum(var))/(TAU*p['N']*p['reference_Hz']),'grid_columns':['offset_Hz','reference_out_rad2_per_Hz','vco_out_rad2_per_Hz','abs_T','abs_S'],'grid':rows}

def hybrid(p,R,initial):
    """Exact charge and VCO phase integration between edges/clamp boundaries.

    Record post-event z, divided cycles, UP/DOWN state; zero-time simultaneous
    edges are consumed together. No reset delay/dead zone, no physical CP noise.
    """
    fref=initial['reference_Hz'];kv=p['Kv_Hz_per_V'];N=p['N'];I=p['Icp_A'];C=p['C_F'];v0=p['center_voltage_V'];fc=p['center_Hz'];lo,hi=p['tune_limits_V'];end=p['duration_s']
    t=0.;z=initial['z_V'];phase=initial['feedback_phase_cycles'];state=0;nr=1;nf=math.floor(phase)+1
    records=[[t,z,phase,state,'initial']];clamp_time=0.;guard=0
    while t<end:
        guard+=1
        if guard>100000:raise ValueError('per-trace event budget exceeded')
        rate=state*I/C;u=z+state*I*R
        # At a clamp boundary choose the side reached by time increasing.
        clipped=u<lo or u>hi or (u<=lo+1e-13 and rate<0) or (u>=hi-1e-13 and rate>0)
        ue=min(hi,max(lo,u));f=(fc+kv*(ue-v0))/N
        slope=0. if clipped else kv*rate/N
        boundary=math.inf
        if rate>0:
            threshold=lo if u<lo-1e-12 else hi
            if threshold>u+1e-12:boundary=(threshold-u)/rate
        elif rate<0:
            threshold=hi if u>hi+1e-12 else lo
            if threshold<u-1e-12:boundary=(threshold-u)/rate
        distance=nf-phase
        if distance<0 and distance>-1e-8:distance=0.
        disc=f*f+2*slope*distance
        feedback_dt=2*distance/(f+math.sqrt(disc)) if disc>=0 and f+math.sqrt(disc)>0 else math.inf
        ref_dt=nr/fref-t
        dt=min(ref_dt,feedback_dt,boundary,end-t)
        if dt< -1e-12:raise ArithmeticError('negative event time')
        dt=max(0.,dt)
        was_clipped=clipped
        z+=rate*dt;phase+=f*dt+.5*slope*dt*dt;t+=dt
        if was_clipped:clamp_time+=dt
        tol=1e-15
        ref=abs(dt-ref_dt)<tol;fb=abs(dt-feedback_dt)<tol;bc=abs(dt-boundary)<tol
        if fb:phase=float(nf);nf+=1
        if ref:nr+=1
        # PFD: set corresponding latch; both high reset instantaneously.
        up=(state==1) or ref;down=(state==-1) or fb
        state=0 if up==down else (1 if up else -1)
        tag='both' if ref and fb else ('ref' if ref else ('feedback' if fb else ('clamp' if bc else 'end')))
        records.append([t,z,phase,state,tag])
        if dt==0 and not (ref or fb):raise ArithmeticError('stalled event')
    # A finite locked-window test, no proof for other initial states.
    tail=[r for r in records if r[0]>=end-20/fref and r[4] in ('ref','both')]
    phase_errors=[r[2]-fref*r[0] for r in tail]
    # Integer phase turns are immaterial to edge lock, but retained as slips.
    residual=[v-round(v) for v in phase_errors]
    freqs=[N*(b[2]-a[2])/(b[0]-a[0]) for a,b in zip(tail,tail[1:])]
    locked=max(abs(x) for x in residual)<1e-3 and max(abs(v-N*fref) for v in freqs)<1000
    turns=[math.floor(r[2]-fref*r[0]+.5) for r in records]
    slip_changes=sum(abs(b-a) for a,b in zip(turns,turns[1:]))
    return {'initial':initial,'R_ohm':R,'columns':['t_s','capacitor_z_V','divided_cycles','PFD_state','event'], 'trace':records,'finite_lock_test':{'last_reference_periods':20,'phase_tolerance_cycles':.001,'frequency_tolerance_Hz':1000,'locked':bool(locked),'max_wrapped_phase_error_cycles':max(abs(x) for x in residual),'max_reference_period_average_frequency_error_Hz':max(abs(v-N*fref) for v in freqs)},'integer_error_crossings':slip_changes,'clamped_time_s':clamp_time,'final_capacitor_V':z,'event_coincidence_tolerance_s':1e-15,'target_Hz':N*fref,'tuning_Hz':[fc+kv*(lo-v0),fc+kv*(hi-v0)]}

def rx(c,vault,pll_spectra):
    """Specified unilateral matched abstraction; not a joined MOS netlist."""
    oldpath=vault/'电子电路/80-实践/52-LNA与LO换向器件/device_lab.py';old=load(oldpath,'rf_device_reused')
    card=json.loads((oldpath.parent/'fixed-inputs.json').read_text());l,m=card['lna'],card['mixer'];l=copy.deepcopy(l);m=copy.deepcopy(m)
    amp=load(vault/'电子电路/80-实践/14-偏置与基本放大/amp_lab.py','rf_amp_reused')
    wave=load(vault/'电子电路/80-实践/51-有源稳定与噪声匹配/active_match.py','rf_wave_reused')
    r=c['rx'];q=old.point(l,50,old.gate_for_id(l,50),amp)
    frequencies=[90e6,110e6,130e6,150e6]
    cases=[old.lna_case(l,50,f,q,card,wave) for f in frequencies]
    wanted=cases[1];mx=old.mixer_limit(m,r['temperature_K']);g1=wanted['G_T'];g2=r['buffer']['available_gain'];gmix=mx['G_conversion_into_RL'];fbuf=r['buffer']['F'];gIF=r['IF_gain'];fIF=r['IF_F'];kT=KB*r['temperature_K'];B=r['bandwidth_Hz']
    # Two specified RF bands, exact per-band old LNA PSD. Out-of-band spectra
    # are explicitly zero at this abstraction, not an unmodeled physical filter.
    n_lna=[sum(x['output_PSD_V2_per_Hz'].values())/l['Rl_ohm'] for x in cases[:2]]
    nbuffer=[g2*v+(fbuf-1)*g2*kT for v in n_lna]
    internal=(mx['on_switch_output_PSD_V2_per_Hz']+mx['bias_resistor_output_PSD_V2_per_Hz'])/m['load_diff_ohm']
    nout=gIF*(gmix*sum(nbuffer)+internal)+(fIF-1)*gIF*kT
    G=g1*g2*gmix*gIF;F=nout/(G*kT)
    # Finite, memoryless compression model: x has units sqrt(W), E[x²]=power.
    # Flat center-frequency gain is an explicit approximation for this stress test.
    fs=1.28e9;count=16384;t=np.arange(count)/fs
    aw=np.sqrt(2*r['wanted_W']);ab=np.sqrt(2*r['blocker_each_W'])
    w=aw*np.cos(TAU*r['RF_Hz']*t);b=ab*(np.cos(TAU*r['blocker_Hz'][0]*t)+np.cos(TAU*r['blocker_Hz'][1]*t))
    poly=np.sqrt(g1);a3=-2*poly/(3*r['LNA_IIP3_W'])
    conversion=np.sqrt(g2*gmix*gIF)*2*np.cos(TAU*r['LO_Hz']*t)
    basis=np.exp(-1j*TAU*(r['RF_Hz']-r['LO_Hz'])*t)
    def coeff(x):return complex(2*np.mean(x*basis))
    rows=[]
    for loss in r['preloss_cases']:
        def stress(x):
            z=x/math.sqrt(loss);return conversion*(poly*z+a3*z**3)
        cw,cb,cj=coeff(stress(w)),coeff(stress(b)),coeff(stress(w+b))
        # The full IF output before channel selection includes 30/50MHz blockers.
        full=stress(w+b);peak=float(max(abs(full)))
        rows.append({'preloss':loss,'gain':G/loss,'NF_dB':10*math.log10(loss*F),'thermal_output_W':nout*B,'wanted_output_W':r['wanted_W']*G/loss,'thermal_SNR_dB':10*math.log10(r['wanted_W']*G/loss/(nout*B)),'wanted_only_complex_sqrtW':[cw.real,cw.imag],'blocker_IM3_complex_sqrtW':[cb.real,cb.imag],'joint_complex_sqrtW':[cj.real,cj.imag],'wanted_increment_complex_sqrtW':[(cj-cb).real,(cj-cb).imag],'wanted_gain_ratio':abs(cj-cb)/abs(cw),'blocker_IM3_power_W':abs(cb)**2/2,'preselection_peak_sqrtW':peak,'preselection_peak_pass':peak<=r['IF_peak_budget_W_sqrt']})
    # Reciprocal mixing: BOTH real IF sidebands; narrow-band approximation.
    rec=[]
    for scale in r['far_LO_scale_cases']:
        contributions=[]
        for fb in r['blocker_Hz']:
            for delta in (fb-r['LO_Hz']-(r['RF_Hz']-r['LO_Hz']),fb-r['LO_Hz']+(r['RF_Hz']-r['LO_Hz'])):
                _,sv=phase_psd(c['noise'],delta)
                # Far-offset LO is an explicit output PSD card. Average PLL
                # NT/S is NOT extrapolated above the 10MHz PFD sampling rate.
                contributions.append(r['blocker_each_W']*G*scale*sv*.5*B)
        rec.append({'far_LO_scale':scale,'offsets_Hz':[20e6,40e6,40e6,60e6],'power_parts_W':contributions,'total_W':sum(contributions),'thermal_plus_reciprocal_SNR_dB':10*math.log10(r['wanted_W']*G/(nout*B+sum(contributions)))})
    for row in rows:
        signal=row['wanted_output_W'];loss=row['preloss']
        row['C_to_IM3_dB']=10*math.log10(signal/row['blocker_IM3_power_W'])
        row['thermal_plus_RM_SNR_dB_by_far_scale']=[10*math.log10(signal/(nout*B+v['total_W']/loss)) for v in rec]
        bd=r['budgets']
        row['budget_checks']={'NF':row['NF_dB']<=bd['NF_dB_max'],'gain':10*math.log10(row['gain'])>=bd['gain_dB_min'],'C_to_IM3':row['C_to_IM3_dB']>=bd['C_to_IM3_dB_min'],'IF_peak':row['preselection_peak_pass'],'thermal_RM_SNR_nominal':row['thermal_plus_RM_SNR_dB_by_far_scale'][0]>=bd['thermal_plus_RM_SNR_dB_min']}
    return {'reuse_source_sha256':{str(p.relative_to(vault)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [oldpath,vault/'电子电路/80-实践/14-偏置与基本放大/amp_lab.py',vault/'电子电路/80-实践/51-有源稳定与噪声匹配/active_match.py']},'Q':q,'LNA_Zin_ohm':[wanted['Zin_ohm'].real,wanted['Zin_ohm'].imag],'LNA_Gamma_in':[( (wanted['Zin_ohm']-50)/(wanted['Zin_ohm']+50) ).real,((wanted['Zin_ohm']-50)/(wanted['Zin_ohm']+50)).imag],'LNA_gain':g1,'LNA_F':wanted['F'],'LNA_power_W':l['vdd_V']*q['id'],'buffer':r['buffer'],'mixer_gain_into_RL':gmix,'mixer_internal_W_per_Hz':internal,'LNA_band_output_W_per_Hz':n_lna,'buffer_band_available_W_per_Hz':nbuffer,'IF_gain':gIF,'IF_F':fIF,'total_gain':G,'total_F':F,'total_NF_dB':10*math.log10(F),'output_PSD_W_per_Hz':nout,'stress':rows,'reciprocal_mixing':rec,'memoryless_stress':{'LNA_a1':poly,'LNA_a3_per_W':a3,'LNA_IIP3_W':r['LNA_IIP3_W'],'LNA_IP1dB_W':r['LNA_IIP3_W']*(1-10**(-1/20)),'sample_rate_Hz':fs,'samples':count,'waveform_columns':['t_s','input_joint_sqrtW','output_joint_sqrtW'],'waveform':[ [float(t[i]),float((w+b)[i]),float((conversion*(poly*(w+b)+a3*(w+b)**3))[i])] for i in range(count)]},'scope':'matched unilateral buffer + specified two RF noise bands + flat cubic stress; not MOS joined RX'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--vault-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    try:
        if a.out.exists() or a.out.is_symlink():raise ValueError('output must not exist')
        c=validate(json.loads(a.input.read_text()));p=c['pll'];spectra={d['name']:spectrum(p,c['noise'],d['R_ohm']) for d in p['designs']}
        dynamics={d['name']:[hybrid(p,d['R_ohm'],i) for i in p['initials']] for d in p['designs']}
        raw={}
        for name,traces in dynamics.items():
            for idx,trace in enumerate(traces):
                filename=f'raw/{name}-{idx}.json.gz';payload=json.dumps(trace.pop('trace'),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode();raw[filename]=gzip.compress(payload,mtime=0);trace['trace_file']=filename;trace['trace_rows']=len(json.loads(payload));trace['trace_uncompressed_sha256']=hashlib.sha256(payload).hexdigest()
        receiver=rx(c,a.vault_root,spectra);wave=receiver['memoryless_stress'].pop('waveform');raw['raw/rx-waveform.json.gz']=gzip.compress(json.dumps(wave,separators=(',',':')).encode(),mtime=0);receiver['memoryless_stress']['waveform_file']='raw/rx-waveform.json.gz'
        out={'input':c,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'environment':{'python':sys.version,'numpy':np.__version__},'PLL':spectra,'dynamics':dynamics,'RX':receiver}
        oscpath=Path(__file__).parent/'oscillator/summary.json';osc=json.loads(oscpath.read_text());r=c['rx'];power=receiver['LNA_power_W']+r['buffer']['power_W']+r['IF_power_W']+r['PLL_control_power_W']+r['LO_driver_power_W']+osc['nominal']['supply_mean_W']
        out['joint_budget']={'oscillator_summary_sha256':hashlib.sha256(oscpath.read_bytes()).hexdigest(),'power_W':power,'power_parts_W':{'LNA_VDD_actual_Q':receiver['LNA_power_W'],'LC_VDD_actual':osc['nominal']['supply_mean_W'],'buffer_declared':r['buffer']['power_W'],'IF_declared':r['IF_power_W'],'PFD_CP_divider_declared':r['PLL_control_power_W'],'LO_regenerator_declared':r['LO_driver_power_W']},'rows':[]}
        for name,sp in spectra.items():
            for row in receiver['stress']:
                for j,far in enumerate(receiver['reciprocal_mixing']):
                    checks=dict(row['budget_checks']);checks.pop('thermal_RM_SNR_nominal');checks.update({'thermal_RM_SNR':row['thermal_plus_RM_SNR_dB_by_far_scale'][j]>=r['budgets']['thermal_plus_RM_SNR_dB_min'],'LO_jitter':sp['jitter_s']<=r['budgets']['LO_jitter_s_max'],'power':power<=r['budgets']['power_W_max'],'three_finite_captures':all(x['finite_lock_test']['locked'] for x in dynamics[name][:3])})
                    out['joint_budget']['rows'].append({'PLL':name,'preloss':row['preloss'],'far_scale':far['far_LO_scale'],'checks':checks,'pass':all(checks.values())})
        data=json.dumps(out,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n';a.out.mkdir(parents=True);(a.out/'results.json').write_text(data)
        for name,payload in raw.items():
            target=a.out/name;target.parent.mkdir(exist_ok=True);target.write_bytes(payload)
        print(json.dumps({'status':'PASS','PLL_designs':len(spectra),'hybrid_traces':sum(map(len,dynamics.values())),'output':str(a.out/'results.json')}))
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as e:ap.exit(2,str(e)+'\n')
if __name__=='__main__':main()
