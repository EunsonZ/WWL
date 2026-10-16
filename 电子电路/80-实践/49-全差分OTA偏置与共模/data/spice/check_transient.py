import os
import json,subprocess
from pathlib import Path
import numpy as np
import ota_model as m
r=Path(__file__).resolve().parent;v=json.loads((r/'verification.json').read_text());a=json.loads((r/'author-results.json').read_text());s=np.loadtxt(r/'nominal-tran'/'transient.txt',skiprows=1);au=np.genfromtxt(r/'author-transient.csv',delimiter=',',names=True);t=au['time_s'];mask=(t>=s[0,0])&(t<=s[-1,0]);ref=np.array([au[k][mask] for k in m.NAMES]).T;interp=np.array([np.interp(t[mask],s[:,0],s[:,i+1]) for i in range(8)]).T
v['transient']['comparison_to_author_Radau']={'method':'ngspice trajectory linearly interpolated to author sample times, excluding t=0 before first ngspice row','samples':int(mask.sum()),'max_absolute_V':float(abs(ref-interp).max()),'per_node_max_V':abs(ref-interp).max(axis=0).tolist()}
case=a['cases']['small_control_cap'];cfg=m.Config(**case['configuration']);q=np.array(case['Q_V']);delta=np.array(a['transient_initial_perturbation_V']);d=r/'smallcap-tran';d.mkdir(exist_ok=True);(d/'smallcap-tran.cir').write_text(m.netlist(cfg,analysis='tran',initial=q+delta))
with (d/'ngspice.log').open('w') as log:subprocess.run([os.environ.get('NGSPICE', 'ngspice'),'-b','smallcap-tran.cir'],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
s=np.loadtxt(d/'transient.txt',skiprows=1);v['smallcap_finite_perturbation']={'rows':len(s),'final_time_s':float(s[-1,0]),'final_Q_delta_V':(s[-1,1:]-q).tolist(),'max_Q_delta_V':abs(s[:,1:]-q).max(axis=0).tolist(),'range_op_V':[float(min(s[:,1])),float(max(s[:,1]))],'range_om_V':[float(min(s[:,2])),float(max(s[:,2]))]}
(r/'verification.json').write_text(json.dumps(v,indent=2));print(json.dumps({k:v[k] for k in ['transient','smallcap_finite_perturbation']},indent=2))
