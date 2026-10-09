"""Business-function observations only; independent expected values live elsewhere."""
import sys,json,math
from pathlib import Path
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base/'snapshot'))
import identification_lab as lab
rows=[[1.,0.],[0.,1.],[1.,1.]];y=[.5,-.25,.25]
prefix=[]
for lam in [1.,.5]:
 for center in [[0.,0.],[1/3,-2/5]]:prefix.append({'lambda':lam,'center':center,'rls':lab.rls(rows,y,lam=lam,prior=1.,theta0=center),'batch_prefix':[lab.batch(rows[:n],y[:n],lam=lam,prior=1.,theta0=center) for n in range(1,4)]})
root=math.sqrt(2);initial=[1.,2.];truth=[-1.,-2.];lms=[]
for phi in [[root,0.],[-root,0.],[0.,root],[0.,-root]]:
 lms.append({'phi':phi,'theta':lab.lms([phi],[sum(x*y for x,y in zip(phi,truth))],mu=1.5)['theta']})
(base/'source-probes.json').write_text(json.dumps({'short_prefix':prefix,'LMS_iid_four_axis':lms,'impulse':lab.solve([[1,0],[0,1]],[.5,-.25])},indent=2)+'\n');print('Supplemental deterministic source observations saved; not independent oracle.')
