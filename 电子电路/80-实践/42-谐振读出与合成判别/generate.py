"""Required new external output; lazy dependencies and no import work."""
from pathlib import Path
import math,json,random
import models as m

def generate(output):
 output=Path(output).expanduser().resolve();candidate=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file());main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
 if output.exists() or main==output or main in output.parents or candidate==output or candidate in output.parents:raise ValueError('new external output required')
 from matplotlib.figure import Figure
 from matplotlib.backends.backend_agg import FigureCanvasAgg
 import matplotlib,cairosvg
 output.mkdir(parents=True);assets=output/'assets';assets.mkdir()
 def text(x,y,s,n=16):return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{n}" fill="#182333" stroke="none">{s}</text>'
 def box(x,y,w,h,label):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>'+text(x+8,y+h/2+5,label)
 def line(x,y,a,b):return f'<path d="M{x},{y} L{a},{b}"/>'
 body=text(18,28,'Electronic measurement chain (concept)',18)
 items=[('RF probe / pulse',70),('loss / thermal bath',145),('resonator: state label +/-',220),('directional routing / isolation',295),('low-noise gain G1 then G2',370),('IQ mixer + LO / LPF',445),('ADC times / calibration',520),('integrate / threshold / report',595)]
 for label,y in items:
  body+=box(30,y,385,45,label)
  if y<595:body+=line(220,y+45,220,y+75)+f'<path d="M214,{y+67} L220,{y+75} L226,{y+67}"/>'
 body+=text(18,680,'Arrows: signal flow, not device pin wiring',15)+text(18,708,'No realized quantum device or fidelity claim',15)
 head='<svg xmlns="http://www.w3.org/2000/svg" width="450" height="735" viewBox="0 0 450 735"><rect width="450" height="735" fill="white"/><g fill="none" stroke="#182333" stroke-width="2">'
 (assets/'chain.svg').write_text(head+body+'</g></svg>')
 k=2*math.pi*5e6;eta=.8;drive=math.sqrt(1e-17);dt=1e-8;N=1024;stop=600;lo=50;hi=550;windowN=hi-lo
 chain=m.quantum_chain();gain=chain['power_gain'];voltage_scale=math.sqrt(2*50*gain);sigma=math.sqrt(50*chain['output_energy_per_Hz_J']/dt);sigma_mean=sigma/math.sqrt(windowN)
 traces=[];mus=[]
 for state in (-1,1):
  a=0;v=[];energy=[]
  for n in range(N):
   a,b=m.cavity_step(a,drive if n<stop else 0,dt,k,eta,state*k/4);v.append(voltage_scale*b);energy.append(abs(a)**2)
  traces.append(v);mus.append(m.mean_complex(v[lo:hi]))
 calamp=1e-4;mat,off=m.fit_iq(m.iq_forward(0),m.iq_forward(calamp),m.iq_forward(1j*calamp),calamp)
 rng=random.Random(7)
 def trial(mu):
  # This exactly draws the mean of independent equal-variance Gaussian samples;
  # no noisy waveform or quantum trajectory is claimed.
  z=mu+complex(rng.gauss(0,sigma_mean),rng.gauss(0,sigma_mean));measured=m.iq_forward(z);return m.iq_inverse(measured,mat,off),measured
 train=[[trial(mu)[0] for _ in range(80)] for mu in mus];fitted=[m.mean_complex(v) for v in train]
 test=[[trial(mu) for _ in range(200)] for mu in mus];errors=[sum(m.classify(v[0],*fitted)!=label for v in group) for label,group in enumerate(test)]
 def serial(z):return [z.real,z.imag]
 params=dict(kappa_rad_s=k,external_fraction=eta,conditional_detuning_rad_s=[-k/4,k/4],probe_power_W=1e-17,carrier_Hz=6e9,fs_Hz=1/dt,N=N,pulse_samples=stop,window_samples=[lo,hi],power_gain=gain,reference_ohm=50,noise_model='matched symmetrized amplifier chain plus ideal heterodyne output-added .5 quanta; iid classical Gaussian mean trials',seed=7,training_per_class=80,test_per_class=200,calibration_axis_peak_V=calamp)
 with matplotlib.rc_context({'font.size':10,'svg.hashsalt':'f07-r1','axes.grid':True}):
  def plot(name,fn):
   fig=Figure(figsize=(4.5,6),layout='constrained');FigureCanvasAgg(fig);fn(fig);fig.savefig(assets/(name+'.svg'),metadata={'Date':None})
  def reson(fig):
   a,b=fig.subplots(2,1);det=[k*(-2+4*i/240) for i in range(241)];r=[m.reflection(k,eta,d) for d in det];a.plot([d/k for d in det],[abs(z)**2 for z in r]);a.set(xlabel='Detuning / kappa',ylabel='Reflected power fraction',title='One-port passive resonator')
   b.plot([z.real for z in r],[z.imag for z in r]);b.set(xlabel='Re reflection',ylabel='Im reflection',aspect='equal');b.plot([m.reflection(k,eta,-k/4).real,m.reflection(k,eta,k/4).real],[m.reflection(k,eta,-k/4).imag,m.reflection(k,eta,k/4).imag],'o')
  plot('resonator-iq',reson)
  def pulse(fig):
   a,b=fig.subplots(2,1);time=[(i+1)*dt*1e6 for i in range(N)]
   for j,v in enumerate(traces):
    style='-' if j==0 else '--';a.plot(time,[z.real*1e6 for z in v],style,label=f'label {j}: I');a.plot(time,[z.imag*1e6 for z in v],':' if j==0 else '-.',label=f'label {j}: Q')
   a.axvspan(lo*dt*1e6,hi*dt*1e6,color='gray',alpha=.15);a.set(xlabel='Interval-end time (us)',ylabel='Peak-envelope voltage (uV)',title='Pulse / persistent resonator state');a.legend(fontsize=8)
   b.plot(time,[abs(v-w)*1e6 for v,w in zip(*traces)]);b.set(xlabel='Interval-end time (us)',ylabel='Centroid separation (uV)');b.axvline(stop*dt*1e6,color='black',linestyle='--')
  plot('pulse-timing',pulse)
  def thermal(fig):
   a,b=fig.subplots(2,1);temps=[.01]+[10**(-2+math.log10(300/.01)*i/240) for i in range(1,240)]+[300.]
   a.loglog(temps,[m.sym_noise(6e9,t)/(m.H*6e9) for t in temps],label='sym q = n + 1/2');a.loglog(temps,[m.KB*t/(m.H*6e9) for t in temps],'--',label='classical kT/hf');a.set(xlabel='Temperature (K)',ylabel='Energy per Hz / hf',title='6 GHz: declared spectral convention');a.legend(fontsize=8)
   eff=[.1+.9*i/90 for i in range(91)];b.plot(eff,[m.quantum_chain(loss_efficiency=v)['source_referred_sym_quanta'] for v in eff]);b.set(xlabel='Preamp power efficiency',ylabel='Source-referred sym quanta')
  plot('thermal-budget',thermal)
  def clouds(fig):
   a,b=fig.subplots(2,1)
   for label,group in enumerate(test):
    a.scatter([v[1].real*1e6 for v in group],[v[1].imag*1e6 for v in group],s=9,marker='o' if label==0 else 'x',label=f'label {label}');b.scatter([v[0].real*1e6 for v in group],[v[0].imag*1e6 for v in group],s=9,marker='o' if label==0 else 'x',label=f'label {label}')
   a.set(xlabel='Measured I (uV)',ylabel='Measured Q (uV)',title='Synthetic affine IQ calibration');b.set(xlabel='Corrected I (uV)',ylabel='Corrected Q (uV)');a.legend(fontsize=8);b.legend(fontsize=8)
   for axis in (a,b):axis.set(xlim=(-12,12),ylim=(-15,15),aspect='equal')
   middle=(fitted[0]+fitted[1])/2;dv=fitted[1]-fitted[0];direction=1j*dv/abs(dv);pts=[middle+v*direction for v in (-15e-6,15e-6)];b.plot([p.real*1e6 for p in pts],[p.imag*1e6 for p in pts],'k--')
  plot('calibration-classification',clouds)
 for p in assets.glob('*.svg'):
  for w in (360,425):cairosvg.svg2png(url=str(p),write_to=str(p.with_name(p.stem+f'-{w}.png')),output_width=w)
 result=dict(parameters=params,chain=chain,thermal_n_20mK=m.occupation(),hf_over_kB_K=m.H*6e9/m.KB,sigma_each_sample_IQ_V=sigma,sigma_mean_IQ_V=sigma_mean,ideal_means_V=[serial(z) for z in mus],fitted_train_means_V=[serial(z) for z in fitted],analytic_equal_prior_error=m.gaussian_error(*mus,sigma_mean),heldout_errors=errors,heldout_total=400,heldout_error_fraction=sum(errors)/400,estimated_IQ_matrix=mat,estimated_IQ_offset_V=off,classification_status='synthetic classical observation labels only; not device fidelity')
 (output/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');(output/'data.json').write_text(json.dumps(dict(parameters=params,traces_V=[[serial(z) for z in v] for v in traces],heldout_V=[[[*serial(v[0]),*serial(v[1])] for v in g] for g in test]),separators=(',',':'))+'\n')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();generate(args.output)
