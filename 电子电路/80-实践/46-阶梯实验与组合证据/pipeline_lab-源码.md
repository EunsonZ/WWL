---
type: code-mirror
domain: electronics
stage: 3
aliases: []
sources: []
prerequisites: []
---
# pipeline_lab 源码镜像

真源为同目录 `pipeline_lab.py`；SHA256 `0a095babd306114c72bc77f1096b0a466d6a7e79c0528ed084c2e68af9586930`。改动需同步源码及此镜像。

```python
"""Group B fixed, bounded experiments; stdlib inert import, existing model reuse."""
import argparse,csv,hashlib,json,math,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent

def causal_butterworth_contract(*, cutoff_hz=80., sample_hz=1000., signal_hz=10., interferer_hz=990., interferer_input_vpk=.1):
    """Declared continuous-time branch contract; deliberately does not simulate it.

    A later accepted integrator must supply an initial-state convention and a
    converged state trajectory before this record may feed ``acquisition``.
    """
    if min(cutoff_hz,sample_hz,signal_hz,interferer_hz,interferer_input_vpk)<=0: raise ValueError('positive finite branch parameters required')
    wc=2*math.pi*cutoff_hz
    return {'kind':'causal_butterworth4_pending_trajectory','injection_port':'filter_input_V',
            'input_components':[{'frequency_hz':signal_hz,'port':'sensor_before_G200'},
                                {'frequency_hz':interferer_hz,'amplitude_Vpk':interferer_input_vpk,'port':'filter_input_V'}],
            'transfer_function':'wc^4/[(s^2+2sin(pi/8)wc*s+wc^2)(s^2+2sin(3pi/8)wc*s+wc^2)]',
            'cutoff_hz':cutoff_hz,'sample_hz':sample_hz,'initial_state':'must_choose_steady_state_or_zero_state',
            'required_rows':['time_s','filter_state','filter_output_V','capture_ns','code','queue_status'],
            'acceptance_oracles':{'at_10Hz_fc80_magnitude':.999999970198,'at_10Hz_fc80_phase_rad':-.327352205869,
                                  '990Hz_output_Vpk_fc80':4.264019373e-6,'990Hz_output_Vpk_fc100':10.410203500e-6,
                                  'alias_hz_at_1kSps':10.}}

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
    return {'version':'groupB-R1','synthetic':True,'L09':l09,'L10':l10,'L12':l12,'L13':{'sensor_input_V':sensor,'ideal_G200_contract':True,'not_full_analog_transient':True,'causal_dynamic_branch_contract':causal_butterworth_contract(),'budget':budget,'cutoff80_redesign':redesign,'pipeline':pipeline,'overrun':fast,'mismatched_100kHz_analog_budget':mismatch,'local_supply_assumptions':{'V_V':3.3,'I_A':.005,'edge_s':5e-9,'decap':pcb.decap(),'loop_short':pcb.loop(),'loop_detour':pcb.loop(inductance=20e-9),'RC_charge_J':pcb.energy()},'not_run':['causal filter trajectory','sensor hardware','ADC DMA cache driver','DAC/PWM','PCB extraction','thermal measurement']}}

def generate(output,vault):
    out=Path(output).resolve();root=Path(vault).resolve()
    if out==root or root in out.parents or out==HERE or HERE in out.parents:raise ValueError('output outside source/vault')
    if out.exists():raise FileExistsError('fresh output required')
    result=run(root);encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'
'
    out.mkdir(parents=True,exist_ok=False);(out/'results.json').write_text(encoded)
    for card in ('L10','L13'):
        rows=result[card]['valid']['samples'] if card=='L10' else result[card]['pipeline']['samples']
        with (out/(card+'-pipeline.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return out

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vault',required=True,type=Path);a=p.parse_args(argv);generate(a.output,a.vault)
if __name__=='__main__':main()
```
