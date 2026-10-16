#!/usr/bin/env python3
"""Declared signed packets and linear capacitors; not a MOS/PDK simulator."""
import argparse
import csv
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import time

K_B=1.380649e-23


def require(ok,message):
    if not ok:raise ValueError(message)


def rational(v):
    require(type(v) is str and len(v)<=80,'bounded rational string required')
    try:q=F(v);f=float(q)
    except (ValueError,ZeroDivisionError,OverflowError) as e:raise ValueError('invalid finite rational') from e
    require(math.isfinite(f) and abs(f)<=1e15,'finite rational budget exceeded')
    return q


def load(path):
    c=json.loads(Path(path).read_text());require(type(c) is dict,'object required')
    expected={'Cs_F','Cf_F','CpA_F','CpB_F','CgA_F','CgB_F','Ccross_F','kappaA_F','kappaB_F',
              'clock_high_absolute_V','clock_low_absolute_V','Vcm_absolute_V','Vth_V','qoff_C','x_V','y0_V',
              'Cs_relative_mismatch','Cf_relative_mismatch','A0','tau_a_s','T2_s','TH_s','aperture_shift_s',
              'input_slope_V_per_s','T2_shift_s','sample_error_variance_V2','sample_error_correlation',
              'qoff_random_std_C','ota_single_PSD_V2_per_Hz','readout_step_V','linear_output_limit_V','tight_limit_probe_V',
              'rc_R_ohm','rc_C_F','temperature_K','rc_closed_s','rc_count','aperture_probe_early_V','aperture_probe_late_V'}
    require(set(c)==expected,'exact declared fields required')
    arrays={'x_V','aperture_shift_s','input_slope_V_per_s','T2_shift_s'}
    p={k:rational(v) for k,v in c.items() if k not in arrays|{'rc_count'}}
    require(all(type(c[k]) is list for k in arrays),'array fields required')
    n=len(c['x_V']);require(1<=n<=16 and all(len(c[k])==n for k in arrays),'equal arrays of length 1..16 required')
    for k in arrays:p[k]=[rational(v) for v in c[k]]
    require(type(c['rc_count']) is int and 2<=c['rc_count']<=16,'integer rc_count 2..16 required');p['rc_count']=c['rc_count']
    for k in ('Cs_F','Cf_F','A0','tau_a_s','T2_s','TH_s','readout_step_V','linear_output_limit_V','tight_limit_probe_V','rc_R_ohm','rc_C_F','temperature_K','rc_closed_s'):
        require(p[k]>0 and float(p[k])>0,'positive '+k+' required')
    for k in ('CpA_F','CpB_F','CgA_F','CgB_F','Ccross_F','kappaA_F','kappaB_F','sample_error_variance_V2','qoff_random_std_C','ota_single_PSD_V2_per_Hz'):
        require(p[k]>=0,'nonnegative '+k+' required')
    require(abs(p['Cs_relative_mismatch'])<=F(1,10) and abs(p['Cf_relative_mismatch'])<=F(1,10),'mismatch budget <=.1 required')
    require(abs(p['sample_error_correlation'])<1,'abs(correlation)<1 required')
    require(p['clock_high_absolute_V']>p['clock_low_absolute_V'],'clock high>low required')
    over=p['clock_high_absolute_V']-p['Vcm_absolute_V']-p['Vth_V']
    require(over>0 and all(-5<=x<=5 and x<over for x in p['x_V']),'sample range/positive synthetic overdrive required')
    for dt in p['T2_shift_s']:require(-p['T2_s']<dt<p['TH_s'],'window shift must preserve positive windows')
    for k in ('Cs_F','Cf_F') :require(1e-15<=float(p[k])<=1e-6,'capacitance budget 1fF..1uF required')
    for mismatch in (False,True):
        for cross in (False,True):
            cs,cf,la,lb=capacitances(p,mismatch,cross)
            require(la*lb-cs*cs>0,'floating two-node matrix must be positive definite')
    shifted=[x+s*t for x,s,t in zip(p['x_V'],p['input_slope_V_per_s'],p['aperture_shift_s'])]
    require(all(-5<=x<=5 and x<over for x in shifted),'aperture-shifted samples must preserve range/overdrive')
    return c,p


def capacitances(p,mismatch=False,cross=True):
    cs=p['Cs_F']*(1+p['Cs_relative_mismatch'] if mismatch else 1)
    cf=p['Cf_F']*(1+p['Cf_relative_mismatch'] if mismatch else 1)
    la=cs+p['CpA_F']+p['CgA_F'];lb=cs+p['CpB_F']+p['CgB_F']+(p['Ccross_F'] if cross else 0)
    return cs,cf,la,lb


def free_charge(A,B,gA,gB,p,cs,la,lb,cross):
    return la*A-cs*B-p['CgA_F']*gA,lb*B-cs*A-p['CgB_F']*gB-cross*gA


def solve(qA,qB,gA,gB,p,cs,la,lb,cross):
    ra=qA+p['CgA_F']*gA;rb=qB+p['CgB_F']*gB+cross*gA;det=la*lb-cs*cs
    require(det>0,'singular floating capacitance matrix')
    return (lb*ra+cs*rb)/det,(cs*ra+la*rb)/det


def edge_record(p,x,order,cross=True,mismatch=False,channel=True,feed=True):
    cs,cf,la,lb=capacitances(p,mismatch,cross)
    cx=p['Ccross_F'] if cross else F(0)
    hi=p['clock_high_absolute_V']-p['Vcm_absolute_V'];lo=p['clock_low_absolute_V']-p['Vcm_absolute_V']
    # For the no-feed comparison clocks stay high; this is an explicit mathematical toggle.
    end=lo if feed else hi
    qAch=-p['kappaA_F']*(hi-p['Vth_V']-x) if channel else F(0)
    qBch=-p['kappaB_F']*(hi-p['Vth_V']) if channel else F(0)
    A=x;B=F(0);gA=hi;gB=hi
    qA,qB=free_charge(A,B,gA,gB,p,cs,la,lb,cx)
    stages=[]
    def save(label):
        aa,bb=free_charge(A,B,gA,gB,p,cs,la,lb,cx)
        stages.append({'stage':label,'A_V':str(A),'B_V':str(B),'gA_relative_V':str(gA),'gB_relative_V':str(gB),'qA_free_C':str(aa),'qB_free_C':str(bb)})
    save('track_A=x_B=0')
    if order=='bottom_first':
        qB+=qBch;gB=end;B=(qB+cs*A+p['CgB_F']*gB+cx*gA)/lb
        qA,_=free_charge(A,B,gA,gB,p,cs,la,lb,cx);save('B_reference_opens_A_clamped')
        qA+=qAch;gA=end;A,B=solve(qA,qB,gA,gB,p,cs,la,lb,cx);save('A_input_opens_both_floating')
    else:
        require(order=='input_first','unknown order')
        qA+=qAch;gA=end;A=(qA+p['CgA_F']*gA)/la
        _,qB=free_charge(A,B,gA,gB,p,cs,la,lb,cx);save('A_input_opens_B_clamped')
        qB+=qBch;gB=end;A,B=solve(qA,qB,gA,gB,p,cs,la,lb,cx);save('B_reference_opens_both_floating')
    A=F(0);B=(qB+p['CgB_F']*gB+cx*gA)/lb;save('A_transfer_clamps_to_reference_B_floating')
    baseline=-p['CgB_F']*gB-cx*gA
    effective=qB-baseline
    return {'order':order,'x_V':str(x),'Cs_F':str(cs),'Cf_F':str(cf),'LA_F':str(la),'LB_F':str(lb),
            'qA_channel_C':str(qAch),'qB_channel_C':str(qBch),'clock_change_V':str(end-hi),
            'qB_transfer_baseline_C':str(baseline),'qB_transfer_effective_C':str(effective),
            'output_increment_before_off_V':str(-effective/cf),'stages':stages}


def sequence(p,order,cross=True,mismatch=False):
    y=p['y0_V'];rows=[]
    for i,x in enumerate(p['x_V']):
        d=edge_record(p,x,order,cross,mismatch);cf=F(d['Cf_F']);q=F(d['qB_transfer_effective_C'])
        old=y;mid=y-q/cf;y=mid-p['qoff_C']/cf
        rows.append({'n':i,'y_before_V':str(old),'qf_before_C':str(-cf*old),'qB_effective_C':str(q),
                     'y_transfer_V':str(mid),'qf_transfer_C':str(-cf*mid),'qoff_C':str(p['qoff_C']),
                     'y_after_off_V':str(y),'qf_after_off_C':str(-cf*y),'edge':d})
    return rows


def source_module(root):
    path=Path(root)/'电子电路/80-实践/48-两相开关电容积分器/finite_ota_budget.py'
    require(path.is_file(),'published finite OTA source missing')
    spec=importlib.util.spec_from_file_location('sc_existing_finite',path);mod=importlib.util.module_from_spec(spec)
    previous=sys.dont_write_bytecode
    try:sys.dont_write_bytecode=True;spec.loader.exec_module(mod)
    finally:sys.dont_write_bytecode=previous
    return mod,{'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def finite_parameters(p,old,mismatch,dt=0.):
    cs,cf,la,lb=map(float,capacitances(p,mismatch));A=float(p['A0']);alpha=lb/cf;ta=float(p['tau_a_s'])
    t2=float(p['T2_s'])+dt;th=float(p['TH_s'])-dt
    tau2=ta*(1+alpha)/(A+1+alpha);tau1=ta/(A+1)
    rho2=math.exp(-t2/tau2);rho1=math.exp(-th/tau1)
    M,Nunused,G2,G1=old.parameters({'A0':F(p['A0']),'alpha':F(lb)/F(cf),'rho1':rho1,'rho2':rho2})
    Gq=[M[0][0]/cf,M[1][0]/cf];Goff=[1/cf,-(1-rho1)*A/(A+1)/cf]
    return {'cs':cs,'cf':cf,'lb':lb,'alpha_load':alpha,'M':M,'Gq_per_C':Gq,'Goff_per_C':Goff,'G2':G2,'G1':G1,
            'tau2':tau2,'tau1':tau1,'rho2':rho2,'rho1':rho1,'f':(1-rho2)*A/(A+1+alpha)}


def finite_case(p,old,mismatch=False,channel=False,feed=False,off=False,clock=False):
    y=float(p['y0_V']);r=-(1+1/float(p['A0']))*y;rows=[]
    for n,xx in enumerate(p['x_V']):
        dt=float(p['T2_shift_s'][n]) if clock else 0.; fp=finite_parameters(p,old,mismatch,dt)
        x=xx+(p['input_slope_V_per_s'][n]*p['aperture_shift_s'][n] if clock else 0)
        d=edge_record(p,x,'bottom_first',True,mismatch,channel,feed)
        q=float(F(d['qB_transfer_effective_C']));qoff=float(p['qoff_C']) if off else 0.
        qnorm=r+q/fp['cf'];target2=-float(p['A0'])*qnorm/(float(p['A0'])+1+fp['alpha_load'])
        w=target2+fp['rho2']*(y-target2)
        rp=(qnorm-fp['alpha_load']*w)/(1+fp['alpha_load']);rn=rp+qoff/fp['cf']
        target1=-float(p['A0'])/(float(p['A0'])+1)*rn
        yn=target1+fp['rho1']*(w-target1)
        predicted=[sum(a*b for a,b in zip(row,[r,y]))+g*q+h*qoff for row,g,h in zip(fp['M'],fp['Gq_per_C'],fp['Goff_per_C'])]
        require(max(abs(predicted[0]-rn),abs(predicted[1]-yn))<2e-12*max(1,abs(yn),abs(rn)),'charge port/state disagreement')
        rows.append({'n':n,'sampled_x_V':float(x),'qB_effective_C':q,'qoff_C':qoff,'r_before_V':r,'y_before_V':y,
                     'target2_V':target2,'w_transfer_V':w,'r_after_off_V':rn,'y_next_V':yn,'window_shift_s':dt,
                     'within_linear_swing':max(abs(y),abs(w),abs(yn))<=float(p['linear_output_limit_V'])})
        r,y=rn,yn
    return rows


def selected_noise(p,old):
    # Linearization around plus_clock: actual deterministic window of each cycle.
    L=len(p['x_V']);fps=[finite_parameters(p,old,True,float(t)) for t in p['T2_shift_s']]
    A=float(p['A0']);ta=float(p['tau_a_s']);S=float(p['ota_single_PSD_V2_per_Hz'])
    def weight(v,j):
        for k in range(j+1,L):v=[sum(a*b for a,b in zip(row,v)) for row in fps[k]['M']]
        return v[1]
    eta=[weight([-fp['cs']*v for v in fp['Gq_per_C']],j) for j,fp in enumerate(fps)]
    qo=[weight(fp['Goff_per_C'][:],j) for j,fp in enumerate(fps)]
    g1=[weight(fp['G1'][:],j) for j,fp in enumerate(fps)];g2=[weight(fp['G2'][:],j) for j,fp in enumerate(fps)]
    var=float(p['sample_error_variance_V2']);corr=float(p['sample_error_correlation'])
    K=[[var*corr**abs(i-j) for j in range(L)] for i in range(L)]
    v_eta=sum(eta[i]*K[i][j]*eta[j] for i in range(L) for j in range(L))
    z1=[S*A*A*fp['tau1']/(4*ta*ta)*(1-fp['rho1']**2) for fp in fps]
    z2=[S*A*A*fp['tau2']/(4*ta*ta)*(1-fp['rho2']**2) for fp in fps]
    terms={'given_sample_port_V2':v_eta,'given_off_packet_V2':sum(v*v for v in qo)*float(p['qoff_random_std_C'])**2,
           'white_OTA_isolated_V2':sum(v*v*z for v,z in zip(g1,z1)),'white_OTA_transfer_V2':sum(v*v*z for v,z in zip(g2,z2))}
    return {'contract':'about plus_clock deterministic windows; deterministic initial; given eta covariance; off packets iid; disjoint white OTA innovations; all three source groups independent; NOT full hardware noise',
            'load_alpha':fps[0]['alpha_load'],'signal_Cs_over_Cf':fps[0]['cs']/fps[0]['cf'],'M_each_cycle':[fp['M'] for fp in fps],
            'Gq_per_C_each_cycle':[fp['Gq_per_C'] for fp in fps],'Goff_per_C_each_cycle':[fp['Goff_per_C'] for fp in fps],
            'eta_to_final_y':eta,'off_C_to_final_y':qo,'zeta1_to_final_y':g1,'zeta2_to_final_y':g2,
            'zeta1_variance_each_cycle_V2':z1,'zeta2_variance_each_cycle_V2':z2,'eta_covariance_V2':K,
            'terms':terms,'selected_total_V2':sum(terms.values())}


def rc_memory(p):
    R=float(p['rc_R_ohm']);C=float(p['rc_C_F']);T=float(p['temperature_K']);dt=float(p['rc_closed_s']);N=p['rc_count']
    tau=R*C;rho=math.exp(-dt/tau);eq=K_B*T/C
    K=[[eq*(rho**abs(i-j)-rho**(i+j+2)) for j in range(N)] for i in range(N)]
    stationary=[[eq*rho**abs(i-j) for j in range(N)] for i in range(N)]
    return {'tau_s':tau,'rho':rho,'equilibrium_V2':eq,'first_zero_initial_V2':eq*(1-rho*rho),
            'R_doubled_closed_halved_first_V2':eq*(1-math.exp(-dt/(2*tau))),
            'zero_initial_covariance_V2':K,'stationary_covariance_V2':stationary,
            'zero_initial_average_V2':sum(map(sum,K))/N**2,'stationary_average_V2':sum(map(sum,stationary))/N**2,
            'incorrect_independent_stationary_average_V2':eq/N}


def run(c,p,root):
    old,ref=source_module(root)
    seq={name:sequence(p,order,cross) for name,order,cross in [('bottom_first','bottom_first',True),('input_first','input_first',True),('bottom_first_no_cross','bottom_first',False)]}
    cases={}
    for name,kw in [('finite_nominal',{}),('finite_actual_caps',{'mismatch':True}),('plus_channel',{'mismatch':True,'channel':True}),
                    ('plus_feed',{'mismatch':True,'channel':True,'feed':True}),('plus_off',{'mismatch':True,'channel':True,'feed':True,'off':True}),
                    ('plus_clock',{'mismatch':True,'channel':True,'feed':True,'off':True,'clock':True})]:cases[name]=finite_case(p,old,**kw)
    ideal=[];y=p['y0_V']
    for x in p['x_V']:y+=p['Cs_F']/p['Cf_F']*x;ideal.append(float(y))
    prior=ideal;decomposition=[]
    for name,rows in cases.items():
        values=[t['y_next_V'] for t in rows];decomposition.append({'component_added':name,'delta_y_V':[v-u for v,u in zip(values,prior)]});prior=values
    final=cases['plus_clock'];step=float(p['readout_step_V'])
    readout=[{'n':n,'linear_prediction_V':row['y_next_V'],'rounded_readout_V':round(row['y_next_V']/step)*step,
              'quantization_error_V':round(row['y_next_V']/step)*step-row['y_next_V']} for n,row in enumerate(final)]
    # Aperture demonstration: B was released at early value; later A tracks a new value, qB stays fixed.
    cs,cf,la,lb=capacitances(p);early=p['aperture_probe_early_V'];late=p['aperture_probe_late_V']
    aperture={'early_x_V':str(early),'late_A_V':str(late),'signal_only_B_change_between_releases_V':str(cs*(late-early)/lb),
              'sampled_signal_charge_C':str(-cs*early),'ideal_signal_output_increment_V':str(cs*early/cf),
              'wrong_late_value_prediction_V':str(cs*late/cf)}
    overload={name:next((row['n'] for row in rows if max(abs(row['y_before_V']),abs(row['w_transfer_V']),abs(row['y_next_V']))>float(p['tight_limit_probe_V'])),None) for name,rows in cases.items()}
    return {'model':'given-charge-four-switch-bottom-sampling-v1','inputs':c,'published_source':ref,'relative_reference':'all A B s x y and Cp reference are relative to Vcm; gate inputs absolute then translated',
            'sequences':seq,'finite_cases':cases,'nominal_ideal_after_V':ideal,'controlled_telescope':decomposition,
            'selected_noise':selected_noise(p,old),'rc_memory':rc_memory(p),'readout':readout,'tight_swing_first_violation':overload,'aperture_probe':aperture}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--vault-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();start=time.monotonic()
    try:
        require(not args.out.exists(),'output must not exist');c,p=load(args.inputs);r=run(c,p,args.vault_root.resolve())
        r['environment']={'python':platform.python_version(),'platform':platform.platform()};r['elapsed_seconds']=time.monotonic()-start
        json_text=json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n';args.out.mkdir(parents=True);(args.out/'results.json').write_text(json_text)
        with (args.out/'edge-ledger.csv').open('w',newline='') as f:
            fields=['scheme','n','x_V','qB_effective_C','y_transfer_V','qoff_C','y_after_off_V'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
            for scheme,rows in r['sequences'].items():
                for row in rows:w.writerow({'scheme':scheme,'n':row['n'],'x_V':row['edge']['x_V'],**{k:row[k] for k in fields[3:]}})
        with (args.out/'budget.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['n','ideal_V']+list(r['finite_cases']))
            for n in range(len(p['x_V'])):w.writerow([n,r['nominal_ideal_after_V'][n]]+[rows[n]['y_next_V'] for rows in r['finite_cases'].values()])
        print(json.dumps({'out':str(args.out),'edge_rows':sum(map(len,r['sequences'].values())),'new_finite_rows':sum(map(len,r['finite_cases'].values())),
                          'selected_noise_V2':r['selected_noise']['selected_total_V2'],'seconds':r['elapsed_seconds']}))
    except (ValueError,TypeError,KeyError,OSError,OverflowError,ZeroDivisionError) as e:print('error: '+str(e),file=sys.stderr);return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
