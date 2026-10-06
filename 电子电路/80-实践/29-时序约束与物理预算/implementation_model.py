"""Bounded teaching SI models; no STA/PDK claim. Import has no filesystem effects."""
import math
import argparse
import json
from pathlib import Path


def real(x,name,low=0.,high=1e6):
 if type(x) not in (int,float):raise ValueError(name+' must be a native real scalar')
 if not low<=x<=high or not math.isfinite(x):raise ValueError(name+' outside supported finite domain')
 return float(x)
def integer(x,name,low,high):
 if type(x) is not int or not low<=x<=high:raise ValueError(name+' outside integer domain')
 return x

def timing(period=10e-9,skew=.5e-9,cq_max=.8e-9,d_max=6e-9,setup=.7e-9,u_setup=.2e-9,cq_min=.15e-9,d_min=.25e-9,hold=.1e-9,u_hold=.05e-9,cycles=1):
 """Seconds. cycles changes setup relation only; caller owns valid enable protocol."""
 period=real(period,'period',1e-15,1);skew=real(skew,'skew',-1,1);cycles=integer(cycles,'cycles',1,16)
 z=[real(x,n,0,1) for x,n in zip([cq_max,d_max,setup,u_setup,cq_min,d_min,hold,u_hold],['cq_max','d_max','setup','u_setup','cq_min','d_min','hold','u_hold'])]
 cq_max,d_max,setup,u_setup,cq_min,d_min,hold,u_hold=z
 if cq_min>cq_max or d_min>d_max:raise ValueError('min must not exceed max')
 return {'setup_slack_s':cycles*period+skew-cq_max-d_max-setup-u_setup,'hold_slack_s':cq_min+d_min-skew-hold-u_hold,'setup_capture_s':cycles*period+skew,'hold_capture_s':skew}

def effort(load_ratio=64.,stages=3,g=1.,branch=1.,parasitic=1.):
 """Uniform g,b,p per stage; bounded continuous sizing approximation."""
 H=real(load_ratio,'H',1e-6,1e6);N=integer(stages,'N',1,16);g=real(g,'g',.01,100);branch=real(branch,'branch',1,100);p=real(parasitic,'p',0,100)
 logF=N*(math.log(g)+math.log(branch))+math.log(H);f=math.exp(logF/N);caps=[math.exp(i*(math.log(H)/N)) for i in range(N+1)]
 # Cin chain applies equal b/g assumption; offpath branch included in actual stage effort.
 return {'path_effort':math.exp(logF),'stage_effort':f,'delay_normalized':N*(f+p),'input_cap_relative':caps,'output_inverted':bool(N%2)}

def power(capacitance=20e-15,voltage=1.,frequency=1e8,rises_per_cycle=.2,short_peak=20e-6,short_width=.1e-9,changes_per_cycle=.4,leak_current=10e-9):
 C=real(capacitance,'C',1e-18,1e-3);V=real(voltage,'V',0,100);f=real(frequency,'f',0,1e12);a=real(rises_per_cycle,'rises',0,100);ip=real(short_peak,'peak',0,1);w=real(short_width,'width',0,1);changes=real(changes_per_cycle,'changes',0,100);il=real(leak_current,'leak',0,1)
 dyn=a*C*V*V*f;sc=changes*f*V*ip*w/2;leak=V*il
 return {'dynamic_W':dyn,'short_W':sc,'leak_W':leak,'total_W':dyn+sc+leak}

def elmore_tree(rd=100.,r1=200.,r2=300.,ca=20e-15,cb=30e-15):
 rd,r1,r2=[real(x,n,0,1e9) for x,n in [(rd,'rd'),(r1,'r1'),(r2,'r2')]];ca=real(ca,'ca',1e-18,1e-3);cb=real(cb,'cb',1e-18,1e-3)
 return {'a_first_moment_s':(rd+r1)*(ca+cb),'b_first_moment_s':(rd+r1)*(ca+cb)+r2*cb}

def supply(voltage=1.,current=.02,resistance=.5,width_m=1e-6,thickness_m=.2e-6):
 V=real(voltage,'V',0,100);I=real(current,'I',0,100);R=real(resistance,'R',0,1e6);w=real(width_m,'width',1e-12,1);t=real(thickness_m,'thickness',1e-12,1)
 drop=I*R
 if drop>V:raise ValueError('load-current assumption would imply negative local supply')
 return {'drop_V':drop,'local_V':V-drop,'current_density_A_m2':I/(w*t)}

def utilization(cell_area_m2=1200e-12,core_area_m2=2000e-12,blocked_m2=0.):
 c=real(cell_area_m2,'cellarea',0,1);a=real(core_area_m2,'corearea',1e-24,1);b=real(blocked_m2,'blocked',0,1)
 if b>=a:raise ValueError('no placeable area')
 return c/(a-b) # >1 is retained as infeasibility, not clamped pass.

POWER_ACTIONS=('quiesce','save','isolate','clock_off','power_off','power_on','clock_on','restore','release')
def power_sequence(actions=POWER_ACTIONS,power_good=True,reset_released=True):
 if type(actions) not in (list,tuple) or len(actions)>9:raise ValueError('bounded action sequence required')
 if type(power_good) is not bool or type(reset_released) is not bool:raise ValueError('external assumptions must be explicit bool')
 rows=[{'k':0,'on':True,'clock':True,'isolated':False,'saved':False,'restored':False}];state=dict(rows[0])
 for i,act in enumerate(actions):
  if type(act) is not str or act!=POWER_ACTIONS[i]:raise ValueError('unsupported order/action at index '+str(i))
  state=dict(state);state['k']=i+1;state['action']=act
  if act=='save':state['saved']=True
  if act=='isolate':state['isolated']=True
  if act=='clock_off':state['clock']=False
  if act=='power_off':state['on']=False
  if act=='power_on':
   if not power_good:raise ValueError('power_good not established; keep isolated')
   state['on']=True
  if act=='clock_on':state['clock']=True
  if act=='restore':state['restored']=True
  if act=='release':
   if not reset_released:raise ValueError('local reset release not established; keep isolated')
   state['isolated']=False
  rows.append(state)
 return rows

def bits(values,n,maxlen=4096):
 if type(values) not in (list,tuple) or not n<=len(values)<=maxlen:raise ValueError('bounded bit sequence required')
 for x in values:integer(x,'bit',0,1)
 return list(values)
def scan_shift(initial=(0,0,0),serial=(0,1,1)):
 q=bits(initial,3,3);serial=bits(serial,0);rows=[q.copy()];out=[]
 for si in serial:out.append(q[-1]);q=[si,*q[:-1]];rows.append(q.copy())
 return {'states':rows,'shifted_out_old':out}
NODES=('a','b','c','n','y','unused')
def logic(inputs,fault=None):
 a,b,c=bits(inputs,3,3)
 if fault is not None:
  if type(fault) not in (list,tuple) or len(fault)!=2 or type(fault[0]) is not str or fault[0] not in NODES:raise ValueError('unknown fault node')
  integer(fault[1],'stuck',0,1)
 def clamp(name,value):return fault[1] if fault is not None and fault[0]==name else value
 a=clamp('a',a);b=clamp('b',b);c=clamp('c',c);n=clamp('n',a&b);unused=clamp('unused',1-a);y=clamp('y',n|c)
 return y

def faults(patterns=None):
 if patterns is None:patterns=[[k>>2&1,k>>1&1,k&1] for k in range(8)]
 if type(patterns) not in (list,tuple) or not 1<=len(patterns)<=8:raise ValueError('1..8 input patterns required')
 patterns=[bits(p,3,3) for p in patterns];rows=[]
 for node in NODES:
  for stuck in [0,1]:
   ds=[p for p in patterns if logic(p)!=logic(p,(node,stuck))];rows.append({'node':node,'stuck':stuck,'detected_by':ds})
 detected=sum(bool(r['detected_by']) for r in rows)
 return {'faults':rows,'detected':detected,'raw_total':12,'raw_coverage':detected/12,'note':'single node SA, no equivalence collapse; not physical defect coverage'}

def lfsr(seed=1,steps=7):
 q=integer(seed,'seed',0,7);steps=integer(steps,'steps',0,4096);rows=[q]
 for _ in range(steps):q=((q<<1)&7)|(((q>>2)^(q>>0))&1);rows.append(q)
 return rows

def signature(response,initial=0):
 response=bits(response,0);q=integer(initial,'signatureinitial',0,7)
 for bit in response:
  feedback=(q>>2)^bit;q=((q<<1)&7)^(3 if feedback else 0)
 return q

def generate(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 params={'SI':'s/F/V/A/ohm/m/m2','period_s':10e-9,'skew_capture_minus_launch_s':.5e-9,'example':'pure teaching values, no technology-node claim'}
 result={'timing':timing(),'effort3':effort(),'power':power(),'elmore':elmore_tree(),'supply':supply(),'utilization':utilization(),'power_sequence':power_sequence(),'scan':scan_shift(),'faults':faults(),'lfsr':lfsr(),'signature_alias':[signature([0,0,0,0]),signature([1,0,1,1])]}
 for name,value in [('parameters.json',params),('results.json',result)]: (output/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)
if __name__=='__main__':main()
