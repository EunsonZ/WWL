from pathlib import Path
import re,json,numpy as np
r=Path(__file__).resolve().parent;a=json.loads((r/'author-results.json').read_text());v=json.loads((r/'verification.json').read_text())
for name,case in a['cases'].items():
 text=(r/(name+'-op')/'ngspice.log').read_text();q=np.array([float(re.search(r'v\('+n+r'\) = ([^\n]+)',text).group(1)) for n in a['state_order']]);i=[0]+[float(re.search(r'@m'+str(k)+r'\[id\] = ([^\n]+)',text).group(1)) for k in range(1,12)];R=case['configuration']['detector_r'];i1=(q[0]-q[4])/R;i2=(q[1]-q[4])/R
 f=[i[1]-i[3]+i1,i[2]-i[4]+i2,-i[1]-i[2]+i[5],i[6]-case['configuration']['iref'],-i1-i2,-i[7]-i[8]+i[9],i[7]-i[10],i[8]-i[11]]
 v[name]['KCL_A_from_SPICE_printed_currents']=f;v[name]['max_KCL_A_from_SPICE_printed_currents']=max(abs(x) for x in f)
 print(name,max(abs(x) for x in f))
(r/'verification.json').write_text(json.dumps(v,indent=2))
