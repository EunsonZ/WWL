"""Finite, frozen workload runner. Uses only a fresh external output directory."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
from dataclasses import replace,asdict
import numpy as np
import joint_ota as m


def checks(c,info,v,trace,common,swing,budget):
    margins={k:v['cuts'][k]['crossings'] for k in ('dm','cm')};r={'all_nominal_MOS_saturated':all(d['region']=='saturation' for d in info['devices']),'positive_region_margin':min(d['headroom_V'] for d in info['devices'])>=budget['minimum_headroom_V'],'gain':abs(v['H_DC'][0][0])>=budget['minimum_abs_DC_gain'],'dc_common_error':abs(common-c.reference)<=budget['maximum_dc_cm_error_V'],'internal_stability':all(z[0]<0 for z in v['roots']),'dm_margin':len(margins['dm'])==1 and margins['dm'][0]['phase_margin_deg']>=budget['minimum_dm_PM_deg'],'cm_margin':len(margins['cm'])==1 and margins['cm'][0]['phase_margin_deg']>=budget['minimum_cm_PM_deg'],'dm_noise':v['noise_dm_rms_V']<=budget['maximum_dm_noise_rms_V'],'cm_noise':v['noise_cm_rms_V']<=budget['maximum_cm_noise_rms_V'],'power':v['supply_power_W']<=budget['maximum_supply_power_W'],'settling':trace['settling_1pct_s'] is not None and trace['settling_1pct_s']<=budget['maximum_settling_1pct_s'],'slew':trace['average_10_90_slew_V_s'] is not None and trace['average_10_90_slew_V_s']>=budget['minimum_average_10_90_slew_V_s'],'step_common':trace['peak_cm_error_V']<=budget['maximum_step_cm_error_V'],'linear_swing':min(abs(z['Q'][0]-z['Q'][1]) for z in (swing[0],swing[-1]))>=budget['minimum_linear_output_differential_peak_V'] and all(z['relative_gain_error']<=budget['maximum_relative_DC_gain_error'] and z['all_saturation'] for z in swing)};return {'checks':{k:bool(ok) for k,ok in r.items()},'all_met':all(r.values()),'failed':[k for k,ok in r.items() if not ok]}


def execute(engine,out,name,deck):
    p=out/'spice'/name;p.mkdir(parents=True);(p/'input.cir').write_text(deck);start=time.monotonic();r=subprocess.run([str(engine),'-b','input.cir'],cwd=p,capture_output=True,text=True,timeout=30);(p/'stdout.txt').write_text(r.stdout);(p/'stderr.txt').write_text(r.stderr);(p/'command.json').write_text(json.dumps({'argv':[str(engine),'-b','input.cir'],'elapsed_seconds':time.monotonic()-start,'exit_code':r.returncode},indent=2)+'\n')
    if r.returncode or any(s in r.stderr.lower() for s in ('error:','fatal')):raise RuntimeError('spice_failed:'+name)
    return p


def run(spec_path,base_path,out,engine=None):
    if out.exists():raise FileExistsError('new_results_required')
    spec=json.loads(spec_path.read_text());base=m.load_base(base_path)
    if not (1<=len(spec['designs'])<=6 and len(spec['corner_inputs'])<=4 and 1<=len(spec['differential_DC_grid_V'])<=17 and 1<=len(spec['input_common_grid_V'])+len(spec['input_common_failure_V'])<=12 and 101<=spec['steps']['count']<=4001 and .0001<=spec['steps']['duration_s']<=.005):raise ValueError('workload_budget')
    if spec['input_version']!='ota-joint-v1' or spec['base_source_sha256']!=hashlib.sha256(base_path.read_bytes()).hexdigest() or len(spec['designs'])>6:raise ValueError('frozen_spec_source')
    noise=spec['noise'];steps=spec['steps']
    if spec['state_order']!=list(m.NAMES) or noise['single_sided'] is not True or noise['independent_sources'] is not True or noise['kB_J_K']!=m.KB or noise['gamma']!=2/3 or noise['mos_NLEV']!=2 or noise['mos_KF']!=0 or noise['frequency_Hz']!=[1,1e5] or noise['log_grid_count']!=401:raise ValueError('fixed_noise_state_contract')
    if steps['amplitudes_V']!=[.001,.06,.35] or steps['budget_amplitude_V']!=.06 or len(spec['differential_DC_failure_V'])>4:raise ValueError('fixed_step_contract')
    if any(type(v) not in (int,float) or not np.isfinite(v) or v<0 or v>1e9 for v in spec['budget'].values()):raise ValueError('finite_budget_values')
    out.mkdir(parents=True);default=m.Design(**spec['default']);configs={n:replace(default,**v) for n,v in spec['designs'].items()}
    for k,(V,T,P,delta) in enumerate(spec['corner_inputs']):configs['corner_'+str(k+1)]=replace(configs['balanced'],vdd=V,temperature_K=T,kp_scale=P*(T/300.15)**-1.5,threshold_shift=delta-.001*(T-300.15))
    result={'input_version':spec['input_version'],'source_sha256':{n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ['joint_ota.py','run_joint.py']},'spec_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),'base_source_sha256':spec['base_source_sha256'],'numpy':np.__version__,'cases':{},'spice_comparisons':{}}
    for name,c in configs.items():
        q,info=m.dc(c,base);lin=m.linear(q,c,base);swing=[];common=[]
        for ud in spec['differential_DC_grid_V']:
            x,diag=m.dc(c,base,ud=ud,guess=q);actual=x[0]-x[1];pred=lin['H_DC'][0][0]*ud;offset=lin['H_DC'][0][0]*0 if c.mismatch==1 else q[0]-q[1];swing.append(dict(ud=ud,Q=x.tolist(),all_saturation=all(d['region']=='saturation' for d in diag['devices']),relative_gain_error=0 if ud==0 else abs((actual-offset)/pred-1),devices=diag['devices']))
        for vic in spec['input_common_grid_V']+spec['input_common_failure_V']:
            x,diag=m.dc(replace(c,vic=vic),base,guess=q);common.append(dict(vic=vic,Q=x.tolist(),all_saturation=all(d['region']=='saturation' for d in diag['devices']),minimum_headroom=min(d['headroom_V'] for d in diag['devices'])))
        failure_swing=[]
        for ud in spec['differential_DC_failure_V']:
            x,diag=m.dc(c,base,ud=ud,guess=q);failure_swing.append(dict(ud=ud,Q=x.tolist(),all_saturation=all(d['region']=='saturation' for d in diag['devices']),minimum_headroom=min(d['headroom_V'] for d in diag['devices'])))
        amp=spec['steps']['budget_amplitude_V'];trace=m.step(c,base,-amp,amp,duration=spec['steps']['duration_s'],count=spec['steps']['count']);row={'configuration':asdict(c),'Q':q.tolist(),'DC':info,'linear':lin,'input_common':common,'swing':swing,'failure_swing':failure_swing,'step':trace};row['budget']=checks(c,info,lin,trace,(q[0]+q[1])/2,swing,spec['budget']);row['budget']['checks']['common_input_grid']=all(z['all_saturation'] and z['minimum_headroom']>=spec['budget']['minimum_headroom_V'] for z in common[:len(spec['input_common_grid_V'])]);row['budget']['failed']=[k for k,ok in row['budget']['checks'].items() if not ok];row['budget']['all_met']=not row['budget']['failed'];result['cases'][name]=row
    extra=[]
    for amp in [a for a in spec['steps']['amplitudes_V'] if a!=spec['steps']['budget_amplitude_V']]:extra.append(m.step(configs['balanced'],base,-amp,amp,duration=spec['steps']['duration_s'],count=spec['steps']['count']))
    result['balanced_other_amplitudes']=extra
    # Current-vs-geometry trade: only Iref changed, same circuit geometry/capacitors.
    c=replace(configs['balanced'],iref=25e-6);q,info=m.dc(c,base);result['half_bias']={'configuration':asdict(c),'Q':q.tolist(),'DC':info,'linear':m.linear(q,c,base)}
    if engine:
        result['engine_version']=subprocess.run([str(engine),'-v'],capture_output=True,text=True,check=True).stdout;result['engine_sha256']=hashlib.sha256(engine.read_bytes()).hexdigest()
        for name in configs:
            c=configs[name];p=execute(engine,out,name+'-op',m.deck(c,['op','wrdata operating.txt '+' '.join('v('+n+')' for n in m.NAMES)]));actual=np.loadtxt(p/'operating.txt',skiprows=1)[1:];result['spice_comparisons'][name+'_op_max_error_V']=float(max(abs(actual-result['cases'][name]['Q'])))
        for name in ['starting','dm_only','balanced','mismatch']:
            c=configs[name]
            individual=' '.join(['onoise_m'+str(k)+'_id' for k in range(1,12)]+['onoise_'+n+'_thermal' for n in ['rdp','rdm','rgp','rgm']])
            commands=['ac dec 80 1 100k','wrdata ac-dm.txt v(op) v(om)','alter VD AC=0','alter VCIN AC=1','ac dec 80 1 100k','wrdata ac-cm.txt v(op) v(om)','alter VD AC=1','alter VCIN AC=0','set sqrnoise','noise v(op,om) VD dec 80 1 100k 1','wrdata integrated-dm.txt onoise_total inoise_total','setplot previous','wrdata noise-dm.txt onoise_spectrum inoise_spectrum '+individual,'noise v(obs) VD dec 80 1 100k 1','wrdata integrated-cm.txt onoise_total','setplot previous','wrdata noise-cm.txt onoise_spectrum '+individual]
            execute(engine,out,name+'-ac-noise',m.deck(c,commands,extra=['BOBS obs 0 V={(v(op)+v(om))/2}']))
        c=configs['balanced'];commands=['alter VD AC=0'];extra=[]
        for i,n in enumerate(m.NAMES):extra.append('IP'+str(i)+' '+n+' 0 AC 0')
        for i in range(10):commands += ['alter IP'+str(i)+' AC=1','ac lin 1 1k 1k','wrdata node-'+str(i)+'.txt '+' '.join('v('+n+')' for n in m.NAMES),'alter IP'+str(i)+' AC=0']
        execute(engine,out,'balanced-Y',m.deck(c,commands,extra=extra))
        for amp in spec['steps']['amplitudes_V'][1:]:
            c=configs['balanced'];initial=np.array(result['cases']['balanced']['step']['initial']) if amp==.06 else np.array(result['balanced_other_amplitudes'][1]['initial']);p=execute(engine,out,'balanced-step-'+str(amp),m.deck(c,[f'tran .5u {spec["steps"]["duration_s"]:.16g} 0 .5u uic','wrdata transient.txt '+' '.join('v('+n+')' for n in m.NAMES)],ud=amp,initial=initial))
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--ngspice',type=Path);a=p.parse_args();r=run(a.spec,a.base,a.out,a.ngspice);print(json.dumps({n:v['budget'] for n,v in r['cases'].items()}))
if __name__=='__main__':main()
