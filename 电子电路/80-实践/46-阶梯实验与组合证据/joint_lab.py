"""Fixed finite composition of accepted teaching sources. Import is inert.
No SPICE, real-time, HDL or hardware execution is represented.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
import types
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARDS = ('L02', 'L04', 'L07', 'L11')


def real(x, name, low, high):
    if type(x) not in (int, float) or not low <= x <= high or not math.isfinite(x):
        raise ValueError(name + ' requires a finite Python real scalar within stated limits')
    return float(x)


@contextmanager
def model(vault, key):
    """Compile exact guarded source without writing a pycache or changing sys.path."""
    registry = json.loads((HERE/'inputs.json').read_text())
    info = registry['sources'][key]
    path = vault/info['path']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != info['sha256']:
        raise ValueError('accepted source byte drift: '+info['path'])
    name = '_wwl_joint_'+key
    previous = sys.modules.get(name)
    mod = types.ModuleType(name);mod.__file__ = str(path)
    sys.modules[name] = mod
    try:
        exec(compile(data, str(path), 'exec'), mod.__dict__)
        yield mod
    finally:
        if previous is None:sys.modules.pop(name, None)
        else:sys.modules[name] = previous


def mos_newton(device, start=3., lam=.02, iterations=24):
    """Only fixed vg1.5/vt.5/5V/2k toy; calls accepted device I and gds.
    Positive Jacobian, voltage bracket, finite damping, explicit failure.
    """
    v=real(start,'initial VD',0.,5.);lam=real(lam,'lambda',0.,.05)
    if type(iterations) is not int or not 1<=iterations<=64:raise ValueError('1..64 iterations')
    trace=[]
    for k in range(iterations):
        q=device.mos(1.5,v,vt0=.5,gamma=0.,lam=lam)
        f=(v-5.)/2000.+q['id'];j=1/2000.+q['gds']
        trace.append({'iteration':k,'vd_V':v,'residual_A':f,'jacobian_S':j,'region':q['region']})
        if abs(f)<=1e-13 and 2000*abs(f)<=1e-9:return dict(vd_V=v,id_A=q['id'],trace=trace)
        step=-f/j
        for exponent in range(25):
            trial=v+math.ldexp(step,-exponent)
            if trial==v:raise ArithmeticError('MOS Newton floating-point stagnation')
            if not 0<=trial<=5:continue
            ft=(trial-5)/2000+device.mos(1.5,trial,vt0=.5,gamma=0.,lam=lam)['id']
            if abs(ft)<abs(f):break
        else:raise ArithmeticError('MOS damping failed')
        trace[-1]['damping']=2.**(-exponent);v=trial
    raise ArithmeticError('MOS Newton finite budget exhausted')


def rc_card(vault):
    with model(vault,'rc') as m:
        circuit=m.RC();times=[k*.00025 for k in range(9)]
        states=circuit.simulate([1.]*8,.00025,v0=.4)
        h=complex(circuit.frequency([1/(2*math.pi*.001)])[0]);a,b=circuit.coefficients(.00025)
        zero=circuit.simulate([0.]*8,.00025,v0=.4)
        first=circuit.simulate([1.]*4,.00025,v0=.4)
        second=circuit.simulate([1.]*4,.00025,v0=float(first[-1]))
        loaded=m.RC(rs=200.,rl=10000.)
        z=complex(math.cos(.25),math.sin(.25));hz=b/(z-a)
        return {'parameters':{'R_ohm':1000.,'C_F':1e-6,'tau_s':circuit.tau,'T_s':.00025,'v0_V':.4,'step_V':1.},'s_pole_per_s':-1000.,'s_causal_ROC':'Re(s)>-1000/s','z_pole':a,'z_causal_ROC':'abs(z)>a','z_h0':0.,'z_h1':b,'fc_Hz':1/(2*math.pi*circuit.tau),'phasor_at_fc':{'real':h.real,'imag':h.imag,'magnitude':abs(h),'phase_rad':math.atan2(h.imag,h.real)},'discrete_at_Omega_025':{'real':hz.real,'imag':hz.imag,'extra_delay_phase_rad':-.25},'rows':[{'k':k,'t_s':times[k],'v_V':float(states[k]),'zero_input_V':float(zero[k]),'extra_register_V':0. if k==0 else float(states[k-1])} for k in range(9)],'block_continuity_error_V':max(abs(float(a)-float(b)) for a,b in zip(states[4:],second)),'loaded':{'K':loaded.gain,'tau_s':loaded.tau}}


def nonlinear_card(vault):
    with model(vault,'network') as n, model(vault,'transistor') as m:
        v,trace=n.diode_newton();vb,width=n.diode_bisection()
        q=mos_newton(m);bracket=m.bias(1.5,gamma=0.,lam=.02)
        pert=m.bias(1.505,gamma=0.,lam=.02)
        loaded_gain=m.source_gain(gm=bracket['gm'],gmb=0.,go=bracket['gds'],rd=2000.,rl=10000.,rsource=0.)
        return {'diode':{'thermal_V':.025,'Is_A':1e-12,'supply_V':5.,'R_ohm':1000.,'vd_V':v,'current_A':(5-v)/1000,'residual_A':n.diode_residual(v)[0],'trace':trace,'independent_bisection_V':vb,'bracket_halfwidth_V':width},'mos':{'parameters':{'vg_V':1.5,'vth_V':.5,'K_A_per_V2':.002,'lambda_per_V':.02,'vdd_V':5.,'rd_ohm':2000.,'source_body_V':0.},'newton':q,'independent_bias':bracket,'perturbed_vd_V':pert['vd'],'loaded_midband_gain':loaded_gain,'loading':'RL10k only through DC-blocking coupling capacitor; no change to DC Q'}}


def noise_card(vault):
    with model(vault,'budget') as b, model(vault,'converter') as adc:
        cfg=b.Budget();good=b.evaluate(cfg,n=4096);bad=b.evaluate(b.fail_case(),n=4096)
        from dataclasses import replace
        ib=b.evaluate(replace(cfg,ibminus1=10e-9),n=4096)
        transfer=replace(cfg,peak=.0005,source_r=20000.,signal_hz=2000.,bits=18,fsr=2.5,midpoint=1.25,driver_r=1000.,acq=.1e-6,temperature=330.)
        migrate=b.evaluate(transfer,n=4096);repair=b.evaluate(replace(transfer,acq=2e-6),n=4096)
        static=adc.quantize(1.65,bits=16,fsr=3.3)
        return {'good':good,'bad':bad,'bias_current_counterexample':ib,'transfer':migrate,'longer_acquisition':repair,'single_sided_units':'stage PSD V^2/Hz; frequency Hz; variance V^2','stage_output_PSD_at_1kHz_V2_per_Hz':list(b.noise_spectra(cfg,1000.)),'static_ADC_counterexample':static,'classification':{'random':['stage noise variances','allocated postfilter/ADC RMS','conditional uniform quantization RMS'],'deterministic':['DC absolute bound','specified single-tone alias peak','static acquisition residual','output envelope'],'no_double_count':'ADC allocated20uVrms already includes sampling/reference contributors; no extra kT/C term'}}


def buck_card(vault):
    with model(vault,'power') as p:
        cfg=p.Params()
        full=p.simulate(cfg,cycles=400,steps=32,initial=(.49,4.95),control_k=.01)
        avg=p.simulate(cfg,cycles=400,steps=32,initial=(.49,4.95),control_k=.01,average=True)
        fail=p.simulate(cfg,cycles=400,steps=32,initial=(.4,4.),control_k=.01)
        wrong=p.simulate(cfg,cycles=400,steps=32,initial=(.4,4.),control_k=.01,average=True)
        def status(rows):return {'mode_counts':{mode:sum(r['mode']==mode for r in rows) for mode in sorted(set(r['mode'] for r in rows))},'minimum_i_A':min(r['i_A'] for r in rows),'last_state':rows[-1]}
        summary=p.buck_summary(cfg);dcm=p.buck_summary(p.Params(r=100.))
        return {'parameters':{'vin_V':12.,'L_H':100e-6,'C_F':100e-6,'R_ohm':10.,'fs_Hz':100e3,'D':5/12,'cycles':400,'steps_per_interval':32,'K_per_V':.01},'steady_closed_form':summary,'dcm_R100':dcm,'valid_segmented':status(full),'valid_average':status(avg),'invalid_segmented':status(fail),'invalid_CCM_average':status(wrong),'maximum_pointwise_difference':{'i_A':max(abs(x['i_A']-y['i_A']) for x,y in zip(full,avg)),'v_V':max(abs(x['v_V']-y['v_V']) for x,y in zip(full,avg))},'losses_estimate':p.losses(cfg),'shared_thermal_at_20s_C':p.thermal(20.,p.losses(cfg)['total_W']),'sampled_rows':[dict(r,average_i_A=a['i_A'],average_v_V=a['v_V']) for r,a in zip(full[::16],avg[::16])],'initial_convention':'same numbers: segmented instantaneous cycle-start; average slow state; not matched cycle averages; finite differences are not a universal error bound'}


def run(vault, cards=CARDS):
    root=Path(vault).resolve()
    if not isinstance(cards,(tuple,list)) or not 1<=len(cards)<=4 or len(set(cards))!=len(cards) or any(k not in CARDS for k in cards):raise ValueError('one to four distinct implemented cards')
    functions={'L02':rc_card,'L04':nonlinear_card,'L07':noise_card,'L11':buck_card}
    return {'identity':'synthetic finite CPU composition, not SPICE/hardware','cards':{k:functions[k](root) for k in cards},'not_run':['SPICE','hardware','Obsidian client','human learning'],'source_guard':'inputs.json exact source bytes'}


def generate(output, vault, cards=CARDS):
    out=Path(output).resolve();root=Path(vault).resolve()
    if out==root or root in out.parents or out==HERE or HERE in out.parents:raise ValueError('new output must be outside vault and source subtree')
    if out.exists():raise FileExistsError('choose a new output directory')
    data=run(root,cards)  # complete numerical work and JSON encoding before writes
    encoded=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True,exist_ok=False);(out/'results.json').write_text(encoded)
    if 'L11' in data['cards']:
        rows=data['cards']['L11']['sampled_rows']
        with (out/'buck-sampled.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return data


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--vault',type=Path,required=True);p.add_argument('--cards',nargs='+',choices=CARDS,default=list(CARDS));a=p.parse_args(argv)
    generate(a.output,a.vault,a.cards)


if __name__=='__main__':main()
