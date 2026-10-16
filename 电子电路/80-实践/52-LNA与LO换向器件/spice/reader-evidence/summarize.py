from pathlib import Path
import json,re,math,numpy as np,hashlib
root=Path(__file__).resolve().parent;card=json.loads((root/'fixed-inputs.json').read_text());result={'canonical_sha256':hashlib.sha256((root/'fixed-inputs.json').read_bytes()).hexdigest(),'ngspice_version':'47','temperature_K':card['temperature_K'],'lna':{},'mixer':{}}
if (root/'interface.json').exists() and not ((root/'mixer-wanted/waveform.txt').exists() or (root/'mixer-wanted/waveform.txt.gz').exists()):
 import recompute_compact
 recompute_compact.main()
 raise SystemExit(0)
for rs in card['lna']['Rs_cases_ohm']:
 d=root/f'lna-Rs{rs}';log=(d/'ngspice.log').read_text();assert not re.search(r'Error|aborted|Timestep too small',log)
 def scalar(name):return float(re.search(re.escape(name)+r' = ([^\n]+)',log).group(1))
 op={name:scalar(name) for name in ['v(d)','v(g)','v(s)','@m1[id]','@m1[gm]','@m1[gds]','@m1[vdsat]','@m1[cgs]','@m1[cgd]','@m1[cgb]']};rows=[]
 for f in card['lna']['frequencies_Hz']:
  ac=np.loadtxt(d/f'ac-{f}.txt',skiprows=1);out=complex(ac[1],ac[2]);s=complex(ac[3],ac[4]);drain=complex(ac[5],ac[6]);text=(d/f'noise-{f}.raw').read_text();names=re.findall(r'^\s*\d+\s+(\w+)\s+[\w-]+$',text.split('Values:')[0],re.M);numbers=[float(x.split()[-1]) for x in text.split('Values:')[1].strip().splitlines()];noise=dict(zip(names,numbers));F=(noise['onoise_spectrum']/noise['onoise_rs'])**2
  rows.append({'frequency_Hz':f,'gain_out_over_generator_re_im':[out.real,out.imag],'gain_magnitude':abs(out),'transducer_gain_to_RL':4*rs/card['lna']['Rl_ohm']*abs(out)**2,'signal_output_power_W_for_card_available_input':card['lna']['signal_available_power_W']*4*rs/card['lna']['Rl_ohm']*abs(out)**2,'input_impedance_re_im':[(rs*s/(1-s)).real,(rs*s/(1-s)).imag],'noise_ASD_V_sqrtHz':noise,'F':F,'NF_dB':10*math.log10(F),'noise_power_sum_relative_error':(noise['onoise_spectrum']**2-(noise['onoise_rs']**2+noise['onoise_rd']**2+noise['onoise_m1_id']**2))/noise['onoise_spectrum']**2})
 result['lna'][str(rs)]={'op':op,'frequencies':rows}
c=card['mixer'];ron=1/(c['kp_A_per_V2']*c['W_m']/c['L_m']*(c['LO_high_V']-c['common_mode_V']-c['Vth_V']));reff=1/(1/c['load_diff_ohm']+1/(2*c['output_bias_each_ohm']));eta=reff/(reff+c['source_diff_ohm']+2*ron);gain=eta*2/math.pi;result['ideal_on_Ron_ohm']=ron;result['ideal_small_signal_IF_gain']=gain
FINAL_MIXER_CASES=('baseline','wanted','image','weak_LO','large_signal_0p1','large_signal_0p4','wanted_with_blocker','blocker_only')
for name in FINAL_MIXER_CASES:
 d=root/('mixer-'+name)
 cfg=json.loads((d/'configuration.json').read_text());log=(d/'ngspice.log').read_text();data=np.loadtxt(d/('waveform.txt' if (d/'waveform.txt').exists() else 'waveform.txt.gz'),skiprows=1);assert not re.search(r'Error|aborted|Timestep too small',log),d.name;assert abs(data[-1,0]-1e-6)<1e-16
 # 500ns to1us: five complete IF periods. Preserve nonuniform actual time.
 t=np.concatenate(([.5e-6],data[(data[:,0]>.5e-6)&(data[:,0]<1e-6),0],[1e-6]));v=np.interp(t,data[:,0],data[:,3]-data[:,4]);T=t[-1]-t[0];w=2*np.pi*c['IF_Hz'];cos=2*np.trapezoid(v*np.cos(w*t),t)/T;sin=2*np.trapezoid(v*np.sin(w*t),t)/T;amp=math.hypot(cos,sin);A=cfg['A_V_peak_differential'];g=None if A==0 else amp/A
 projections={}
 for frequency in [c['IF_Hz'],abs(c['blocker_Hz']-c['LO_Hz']),50e6]:
  ww=2*np.pi*frequency;cc=2*np.trapezoid(v*np.cos(ww*t),t)/T;ss=2*np.trapezoid(v*np.sin(ww*t),t)/T;projections[str(int(frequency))]={'cos_V':float(cc),'sin_V':float(ss),'amplitude_V':math.hypot(cc,ss)}
 common=np.interp(t,data[:,0],.5*(data[:,3]+data[:,4]));dc=float(np.trapezoid(v,t)/T)
 entry={'projections':projections,'DC_output_diff_V':dc,'common_mode_mean_V':float(np.trapezoid(common,t)/T),'common_mode_range_V':[float(common.min()),float(common.max())],'configuration':cfg,'data_rows':len(data),'final_time_s':float(data[-1,0]),'min_dt_s':float(np.diff(data[:,0]).min()),'max_dt_s':float(np.diff(data[:,0]).max()),'projection_window_s':[float(t[0]),float(t[-1])],'IF_cos_V':float(cos),'IF_sin_V':float(sin),'IF_amplitude_V':amp,'IF_gain':g,'transducer_gain_wanted_to_physical_RL':None if g is None else 4*c['source_diff_ohm']/c['load_diff_ohm']*g*g,'deviation_from_ideal_fraction':None if g is None else g/gain-1,'small_signal_3pct_pass':None if d.name not in ['mixer-wanted','mixer-image'] else abs(g/gain-1)<=.03,'output_diff_minmax_V':[float((data[:,3]-data[:,4]).min()),float((data[:,3]-data[:,4]).max())]}
 # Retain an exact subset of the same finite raw trajectory, no invented uniform sampling.
 chunk=data[(data[:,0]>=.9e-6)&(data[:,0]<=1e-6)];np.savetxt(d/'last-IF-cycle.txt',chunk,fmt='%.16e',header='time_s p_V n_V op_V on_V lop_V lon_V');result['mixer'][d.name]=entry
(root/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False));print(json.dumps(result,indent=2))
