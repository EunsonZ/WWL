"""Group B fixed, bounded experiments; stdlib inert import, existing model reuse."""
import argparse,csv,hashlib,json,math,numbers,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent

BRANCH_PARAMETER_ERROR='positive finite branch parameters required'

def positive_branch_real(value):
    """Reject type/nonfinite errors before loading or mutating acquisition state."""
    if isinstance(value,bool) or not isinstance(value,numbers.Real):
        raise ValueError(BRANCH_PARAMETER_ERROR)
    try:value=float(value)
    except (OverflowError,ValueError):raise ValueError(BRANCH_PARAMETER_ERROR) from None
    if not math.isfinite(value) or value<=0:raise ValueError(BRANCH_PARAMETER_ERROR)
    return value

def causal_butterworth_contract(*, cutoff_hz=80., sample_hz=1000., signal_hz=10., interferer_hz=990., interferer_input_vpk=.1):
    """Continuous-time model; the separate steady-state branch realizes it below."""
    cutoff_hz,sample_hz,signal_hz,interferer_hz,interferer_input_vpk=map(positive_branch_real,
        (cutoff_hz,sample_hz,signal_hz,interferer_hz,interferer_input_vpk))
    return {'kind':'causal_butterworth4_contract','injection_port':'filter_input_V',
            'input_components':[{'frequency_hz':signal_hz,'port':'sensor_before_G200'},
                                {'frequency_hz':interferer_hz,'amplitude_Vpk':interferer_input_vpk,'port':'filter_input_V'}],
            'transfer_function':'wc^4/[(s^2+2sin(pi/8)wc*s+wc^2)(s^2+2sin(3pi/8)wc*s+wc^2)]',
            'cutoff_hz':cutoff_hz,'sample_hz':sample_hz,'initial_state':'negative_infinity_sinusoidal_steady_state',
            'required_rows':['time_s','filter_state','filter_output_V','capture_ns','code','queue_status'],
            'acceptance_oracles':{'at_10Hz_fc80_magnitude':.999999970198,'at_10Hz_fc80_phase_rad':-.327352205869,
                                  '990Hz_output_Vpk_fc80':4.264019373e-6,'990Hz_output_Vpk_fc100':10.410203500e-6,
                                  'alias_hz_at_1kSps':10.}}

def causal_butterworth_steady_state(e, *, cutoff_hz=80., sample_hz=1000., signal_hz=10., interferer_hz=990., interferer_input_vpk=.1):
    """32 exact forced steady-state samples, not a zero-state or ZOH simulation.

    All four states have units V: [q1, q1_dot/wc, q2, q2_dot/wc].
    For each sine input Im(U exp(jwt)), solve the two continuous biquads.
    No Euler/Tustin step or finite warm-up substitutes for the declared past.
    """
    contract=causal_butterworth_contract(cutoff_hz=cutoff_hz,sample_hz=sample_hz,
        signal_hz=signal_hz,interferer_hz=interferer_hz,interferer_input_vpk=interferer_input_vpk)
    fc,fs=contract['cutoff_hz'],contract['sample_hz']
    # acquisition has an explicit 1 ms capture/scheduler contract; don't relabel it.
    if fs!=1000.:raise ValueError('steady-state acquisition requires sample_hz=1000')
    a1,a2=2*math.sin(math.pi/8),2*math.sin(3*math.pi/8)
    components=[]
    try:
        for f,amplitude,port in ((contract['input_components'][0]['frequency_hz'],.0005*200,'sensor_before_G200'),
                                 (contract['input_components'][1]['frequency_hz'],float(interferer_input_vpk),'filter_input_V')):
            r=f/fc;d1=complex(1-r*r,a1*r);d2=complex(1-r*r,a2*r)
            if not all(math.isfinite(z.real) and math.isfinite(z.imag) for z in (d1,d2)):
                raise ValueError('steady-state numeric domain exceeded')
            q1=amplitude/d1;q2=q1/d2
            states=(q1,1j*r*q1,q2,1j*r*q2)
            if not all(math.isfinite(z.real) and math.isfinite(z.imag) for z in states):
                raise ValueError('steady-state numeric domain exceeded')
            components.append((f,amplitude,port,states))
        rows=[]
        for n in range(32):
            t=n/fs;state=[0.]*4;input_v=0.
            for f,amplitude,port,phasors in components:
                angle=2*math.pi*f*t
                if not math.isfinite(angle):raise ValueError('steady-state numeric domain exceeded')
                sine,cosine=math.sin(angle),math.cos(angle)
                input_v+=amplitude*sine
                for k,z in enumerate(phasors):state[k]+=z.real*sine+z.imag*cosine
            rows.append({'index':n,'time_s':t,'filter_input_V':input_v,'filter_state':state,
                         'filter_output_V':state[2],'adc_input_V':1.65+state[2]})
    except (OverflowError,ZeroDivisionError):raise ValueError('steady-state numeric domain exceeded') from None
    # Validate ALL 32 voltages before acquisition creates a ring or filter state.
    voltages=[r['adc_input_V'] for r in rows]
    pipeline=acquisition(e,voltages)
    for row,sample in zip(rows,pipeline['samples']):
        ev=pipeline['events'][row['index']//4]
        row.update(capture_ns=sample['capture_ns'],code=sample['code'],queue_block=ev['block'],
                   queue_slot=ev['slot'],queue_status=ev['status'],finish_ns=sample['finish_ns'])
    response=[]
    for f,amplitude,port,states in components:
        z=states[2]/amplitude
        response.append({'frequency_hz':f,'port':port,'filter_input_Vpk':amplitude,
                         'gain_real':z.real,'gain_imag':z.imag,'magnitude':abs(z),
                         'phase_rad':math.atan2(z.imag,z.real),'output_Vpk':abs(states[2])})
    return {'kind':'ideal_G200_causal_butterworth4_steady_state','contract':contract,
            'state_order':['q1_V','q1_dot_over_wc_V','q2_V','q2_dot_over_wc_V'],
            'state_initial_V':rows[0]['filter_state'][:],'sensor_peak_V':.0005,'sensor_gain':200,
            'adc_reference_V':1.65,'method':'analytic_continuous_sinusoidal_steady_state',
            'window_s':[0.,.031],'response':response,'trajectory':rows,'pipeline':pipeline,
            'overrun':acquisition(e,voltages,cpu_ns=5000000),
            'not_run':['zero_initial_state','finite_A_GBW_time_domain','random_noise_bias_time_domain','physical_AFE']}

def load(vault,key):
    registry=json.loads((HERE/'pipeline-inputs.json').read_text())
    if type(key) is not str or key not in registry:raise ValueError('known model required')
    item=registry[key];p=Path(vault)/item['path'];body=p.read_bytes()
    if hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('model version drift: '+key)
    name='_jointB_'+key;old=sys.modules.get(name);mod=types.ModuleType(name);mod.__file__=str(p);sys.modules[name]=mod
    try:exec(compile(body,str(p),'exec'),mod.__dict__)
    finally:
        if old is None:sys.modules.pop(name,None)
        else:sys.modules[name]=old
    return mod

def acquisition(e,voltages,*,cpu_ns=2000000):
    if type(voltages) not in (list,tuple) or len(voltages)!=32:raise ValueError('exactly32 samples required')
    # Entire payload validated before the first state mutation.
    codes=[e.adc(x)['code'] for x in voltages];events=e.schedule(cpu_ns=cpu_ns)
    ring=e.OwnedRing();filt=e.CountFilter();rows=[]
    for ev in events:
        begin=ev['start_index']
        if ev['status']!='valid':
            # Never feed discarded blocks as contiguous valid samples.
            rows.append({'block':ev['block'],'status':'discard','start_index':begin});continue
        token=ring.publish(ev['slot'],codes[begin:begin+4]);payload=ring.take(token)
        filtered=filt.process(payload,begin,0)
        for j,(code,(fir,iir,valid)) in enumerate(zip(payload,filtered)):
            n=begin+j;rows.append({'index':n,'capture_ns':n*1000000,'finish_ns':ev['cpu_finish_ns'],'input_V':voltages[n],'code':code,'FIR_count':fir,'IIR_count':iir,'FIR_valid':valid,'output_deviation_V':iir*3.3/4096,'status':'CPU_result_only'})
        ring.release(token)
    return {'events':events,'samples':rows,'output_reference_V':1.65,'scale_V_per_count':3.3/4096}

def run(vault):
    e=load(vault,'embedded');h=load(vault,'hdl');rf=load(vault,'rf');pcb=load(vault,'pcb');b=load(vault,'budget')
    l09={'normal':h.directed(),'fault':h.directed(True),'finite_graph':h.enumerate_transitions(width=2),'actual_HDL':'not_run','actual_formal':'not_run'}
    delta=3.3/4096;values=[1.65+4*n*delta for n in range(32)]
    l10={'valid':acquisition(e,values),'overrun':acquisition(e,values,cpu_ns=5000000),'ADC_quantization_step_V':delta,'hardware':'not_run'}
    line=rf.lossless(250e-9,100e-12,.1)
    l12={'line':line,'open':rf.bounce(1,25,None,50,line['delay_s'],rounds=4),'matched':rf.bounce(1,25,50,50,line['delay_s'],rounds=4),'ideal_source_open':rf.bounce(1,0,None,50,line['delay_s'],rounds=4),'short_loop':pcb.loop(),'detour_loop':pcb.loop(inductance=20e-9),'decap':pcb.decap(),'field_and_board':'not_run'}
    cfg=b.Budget(peak=.0005,signal_hz=10,cutoff=100,fs=1000,bits=12,interferer_hz=990,acq=5e-6)
    budget=b.evaluate(cfg);sensor=[.0005*math.sin(2*math.pi*10*n*.001) for n in range(32)]
    # Time sequence is a DECLARED ideal G200 path. PSD/filter and swing budgets remain
    # distinct analytic checks, not a time-domain simulation of the complete analog AFE.
    output=[1.65+200*v for v in sensor]
    pipeline=acquisition(e,output)
    fast=acquisition(e,output,cpu_ns=5000000)
    from dataclasses import replace
    mismatch=b.evaluate(replace(cfg,fs=100000,interferer_hz=99000));redesign=b.evaluate(replace(cfg,cutoff=80))
    causal=causal_butterworth_steady_state(e)
    return {'version':'groupB-R2','synthetic':True,'L09':l09,'L10':l10,'L12':l12,'L13':{'sensor_input_V':sensor,'ideal_G200_contract':True,'not_full_analog_transient':True,'causal_dynamic_branch_contract':causal_butterworth_contract(),'causal_butterworth_steady_state':causal,'budget':budget,'cutoff80_redesign':redesign,'pipeline':pipeline,'overrun':fast,'mismatched_100kHz_analog_budget':mismatch,'local_supply_assumptions':{'V_V':3.3,'I_A':.005,'edge_s':5e-9,'decap':pcb.decap(),'loop_short':pcb.loop(),'loop_detour':pcb.loop(inductance=20e-9),'RC_charge_J':pcb.energy()},'not_run':['zero initial state causal filter','finite A/GBW and noise time trajectory','sensor hardware','ADC DMA cache driver','DAC/PWM','PCB extraction','thermal measurement']}}

def generate(output,vault):
    out=Path(output).resolve();root=Path(vault).resolve()
    if out==root or root in out.parents or out==HERE or HERE in out.parents:raise ValueError('output outside source/vault')
    if out.exists():raise FileExistsError('fresh output required')
    result=run(root);encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True,exist_ok=False);(out/'results.json').write_text(encoded)
    for card in ('L10','L13'):
        rows=result[card]['valid']['samples'] if card=='L10' else result[card]['pipeline']['samples']
        with (out/(card+'-pipeline.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    rows=result['L13']['causal_butterworth_steady_state']['trajectory']
    with (out/'L13-causal-butterworth-steady-state.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return out

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vault',required=True,type=Path);a=p.parse_args(argv);generate(a.output,a.vault)
if __name__=='__main__':main()
