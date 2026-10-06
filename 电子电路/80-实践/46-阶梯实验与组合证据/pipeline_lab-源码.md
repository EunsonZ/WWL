---
type: code-mirror
domain: electronics
stage: 3
aliases: []
sources: []
prerequisites: []
---
# pipeline_lab 源码镜像

真源为同目录 `pipeline_lab.py`；SHA256 `e9fe4245ee82feb98d82f8d09a10a9ee732405a85d0345ddfac4edc435602861`。改动需同步源码及此镜像。

```python
"""Group B fixed, bounded experiments; stdlib inert import, existing model reuse."""
import argparse,csv,hashlib,json,math,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent

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
    return {'version':'groupB-R1','synthetic':True,'L09':l09,'L10':l10,'L12':l12,'L13':{'sensor_input_V':sensor,'ideal_G200_contract':True,'not_full_analog_transient':True,'budget':budget,'cutoff80_redesign':redesign,'pipeline':pipeline,'overrun':fast,'mismatched_100kHz_analog_budget':mismatch,'local_supply_assumptions':{'V_V':3.3,'I_A':.005,'edge_s':5e-9,'decap':pcb.decap(),'loop_short':pcb.loop(),'loop_detour':pcb.loop(inductance=20e-9),'RC_charge_J':pcb.energy()},'not_run':['sensor hardware','ADC DMA cache driver','DAC/PWM','PCB extraction','thermal measurement']}}

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
    return out

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vault',required=True,type=Path);a=p.parse_args(argv);generate(a.output,a.vault)
if __name__=='__main__':main()
```
