import os
from pathlib import Path
import subprocess,json,numpy as np
r=Path(__file__).resolve().parent;out=r/'convergence-step5ps';out.mkdir(exist_ok=True);rows=[]
for name in ['wanted','blocker_only','wanted_with_blocker']:
 src=r/('mixer-'+name);dst=out/name;dst.mkdir(exist_ok=True);deck=(src/'mixer.cir').read_text().replace('tran 10p 1u 0 10p','tran 5p 1u 0 5p');(dst/'mixer.cir').write_text(deck)
 with (dst/'ngspice.log').open('w') as f:subprocess.run([os.environ.get('NGSPICE','ngspice'),'-b','mixer.cir'],cwd=dst,stdout=f,stderr=subprocess.STDOUT,check=True)
 assert 'aborted' not in (dst/'ngspice.log').read_text();data=np.loadtxt(dst/('waveform.txt' if (dst/'waveform.txt').exists() else 'waveform.txt.gz'),skiprows=1);assert data[-1,0]==1e-6;t=np.r_[.5e-6,data[(data[:,0]>.5e-6)&(data[:,0]<1e-6),0],1e-6];v=np.interp(t,data[:,0],data[:,3]-data[:,4]);p={}
 for freq in [10e6,30e6,50e6]:
  c=2*np.trapezoid(v*np.cos(2*np.pi*freq*t),t)/(t[-1]-t[0]);s=2*np.trapezoid(v*np.sin(2*np.pi*freq*t),t)/(t[-1]-t[0]);p[str(int(freq))]={'cos_V':float(c),'sin_V':float(s),'amplitude_V':float(np.hypot(c,s))}
 rows.append({'case':name,'rows':len(data),'projections':p})
(out/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
