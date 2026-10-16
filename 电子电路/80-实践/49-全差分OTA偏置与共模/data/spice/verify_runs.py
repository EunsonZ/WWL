import os
from pathlib import Path
import json,re,subprocess, numpy as np
import ota_model as m
r=Path(__file__).resolve().parent; a=json.loads((r/'author-results.json').read_text()); output={}
for name,case in a['cases'].items():
 log=(r/(name+'-op')/'ngspice.log').read_text()
 q=np.array([float(re.search(r'v\('+n+r'\) = ([^\n]+)',log).group(1)) for n in m.NAMES]); cfg=m.Config(**case['configuration'])
 currents=np.array([float(re.search(r'@m'+str(i)+r'\[id\] = ([^\n]+)',log).group(1)) for i in range(1,12)])
 expected=np.abs([d['Id_A'] for d in case['DC']['devices']]); f,j,fu,diag=m.circuit(q,cfg)
 output[name]={'max_Q_error_V':float(max(abs(q-np.array(case['Q_V'])))),'max_Id_error_A':float(max(abs(currents-expected))),'KCL_A_from_model_at_spice_Q':f.tolist(),'regions':[d['region'] for d in diag]}
nom=a['cases']['nominal'];j=np.array(nom['linear']['J_S']);b=np.array(nom['linear']['B_s_inv']);c=np.array(nom['linear']['capacitances_F']);fu=-c[:,None]*b
for channel,col in [('dm',0),('cm',1)]:
 data=np.loadtxt(r/'nominal-ac'/('ac-'+channel+'.txt'),skiprows=1);f=data[:,0];v=data[:,1::2]+1j*data[:,2::2]
 expected=np.array([np.linalg.solve(j+2j*np.pi*ff*np.diag(c),-fu[:,col])[[0,1,4,7]] for ff in f]);err=abs(v-expected)
 output['AC_'+channel]={'rows':len(f),'max_absolute_error':float(err.max()),'max_relative_error_above_1e-8':float((err[np.abs(expected)>1e-8]/abs(expected[np.abs(expected)>1e-8])).max())}
sp=np.loadtxt(r/'nominal-tran'/'transient.txt',skiprows=1); au=np.genfromtxt(r/'author-transient.csv',delimiter=',',names=True);print(au.dtype.names)
q=np.array(nom['Q_V']);output['transient']={'rows':len(sp),'final_time_s':float(sp[-1,0]),'final_delta_from_Q_V':(sp[-1,1:]-q).tolist()}
# 8 independent node-current injections: full impedance, including unobservable modes.
for name in ['nominal','small_control_cap']:
 case=a['cases'][name];orig=(r/(name+'-op.cir')).read_text();base=orig.split('.control')[0].replace('VD ud 0 DC 0 AC 1','VD ud 0 DC 0 AC 0');columns=[];freq=1000.
 for n in m.NAMES:
  d=r/('ymatrix-'+name+'-'+n);d.mkdir(exist_ok=True)
  deck=base+f'ITEST 0 {n} DC 0 AC 1\n.control\nset noaskquit\nset numdgt=15\nac lin 1 1000 1000\nset wr_vecnames\nset wr_singlescale\nwrdata response.txt '+' '.join('v('+k+')' for k in m.NAMES)+'\nquit\n.endc\n.end\n'
  (d/'probe.cir').write_text(deck)
  with (d/'ngspice.log').open('w') as log:p=subprocess.run([os.environ.get('NGSPICE', 'ngspice'),'-b','probe.cir'],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
  data=np.loadtxt(d/'response.txt',skiprows=1);columns.append(data[1::2]+1j*data[2::2])
 z=np.array(columns).T;y=np.linalg.inv(z);jj=y.real;cc=y.imag/(2*np.pi*freq);A=-np.linalg.solve(cc,jj);roots=np.linalg.eigvals(A)
 reference=np.array([complex(*x) for x in case['linear']['roots_s_inv']]);dist=[min(abs(x-reference)) for x in roots]
 output['Y_'+name]={'frequency_Hz':freq,'Z_condition':float(np.linalg.cond(z)),'J_S':jj.tolist(),'C_F':cc.tolist(),'roots_s_inv':[[float(x.real),float(x.imag)] for x in roots],'max_root_absolute_error_s_inv':float(max(dist)),'max_J_error_S':float(abs(jj-np.array(case['linear']['J_S'])).max()),'max_C_error_F':float(abs(cc-np.diag(case['linear']['capacitances_F'])).max())}
(r/'verification.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))
