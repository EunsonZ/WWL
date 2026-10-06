"""Small DC MNA oracle. SI inputs; no I/O or plotting on import.
R(name,p,n,ohm), I(name,p,n,A), V(name,p,n,V), G(name,p,n,cp,cn,S).
I/G arrow p -> n; V positive terminal p, branch current p -> n.
Every node other than literal '0' must occur in the netlist. Limited finite
teaching parameters; this is not SPICE, nonlinear/DC bias or hardware proof.
"""
import math
import numpy as np

def finite(x):
 if isinstance(x,bool) or not isinstance(x,(int,float)):raise ValueError('finite real required')
 try:y=float(x)
 except (OverflowError,ValueError):raise ValueError('finite real required') from None
 if not math.isfinite(y):raise ValueError('finite real required')
 return y

def solve(net):
 if not isinstance(net,(list,tuple)) or not net:raise ValueError('nonempty list/tuple network required')
 names=[];nodes=[];vs=[]
 for e in net:
  if not isinstance(e,(list,tuple)) or len(e)<1 or not isinstance(e[0],str):raise ValueError('element sequence required')
  if e[0] not in ('R','I','V','G') or len(e)!=(7 if e[0]=='G' else 5):raise ValueError('element shape/type')
  if not isinstance(e[1],str) or not e[1]:raise ValueError('element name string required')
  if e[1] in names:raise ValueError('duplicate element name')
  names.append(e[1]);finite(e[-1])
  if e[0]=='R' and e[-1]<=0:raise ValueError('positive resistance required')
  for node in (e[2:6] if e[0]=='G' else e[2:4]):
   if not isinstance(node,str) or not node:raise ValueError('node string required')
   if node!='0' and node not in nodes:nodes.append(node)
  if e[0]=='V':vs.append(e)
 n=len(nodes);ix={s:k for k,s in enumerate(nodes)};K=np.zeros((n+len(vs),n+len(vs)));rhs=np.zeros(n+len(vs))
 def q(node):
  z=np.zeros(n);k=ix.get(node)
  if k is not None:z[k]=1
  return z
 for e in net:
  d=q(e[2])-q(e[3]);v=finite(e[-1])
  if e[0]=='R':K[:n,:n]+=np.outer(d,d)/v
  elif e[0]=='I':rhs[:n]-=d*v
  elif e[0]=='G':K[:n,:n]+=v*np.outer(d,q(e[4])-q(e[5]))
  else:
   j=n+vs.index(e);K[:n,j]=d;K[j,:n]=d;rhs[j]=v
 x=np.linalg.solve(K,rhs)
 if not np.all(np.isfinite(x)):raise ValueError('nonfinite solve')
 volts={'0':0.,**dict(zip(nodes,x[:n]))};currents={};powers={}
 for e in net:
  v=volts[e[2]]-volts[e[3]]
  if e[0]=='R':i=v/e[-1]
  elif e[0]=='I':i=e[-1]
  elif e[0]=='G':i=e[-1]*(volts[e[4]]-volts[e[5]])
  else:i=x[n+vs.index(e)]
  currents[e[1]]=float(i);powers[e[1]]=float(v*i)
 return {'volts_V':volts,'currents_A':currents,'absorbed_W':powers,'residual':K@x-rhs,'matrix':K,'rhs':rhs}

def node_net(e=5):return [('V','E','s','0',e),('R','Rsa','s','a',1000),('R','Ra','a','0',1000),('R','Rab','a','b',1000),('R','Rb','b','0',1000)]
def supernode_net():return [('I','I','0','a',.002),('V','E','a','b',1),('R','Ra','a','0',1000),('R','Rb','b','0',2000)]
def mesh_net(supermesh=False):
 return [('V','E5','s','0',5),('V','E1','b','0',1),('R','R1','s','a',1000),('R','R2','a','b',2000)]+([('I','I','0','a',.001)] if supermesh else [('R','Rc','a','0',1000)])
def controlled_net(e=3,i=.0005,gm=.00025,load=None):
 net=[('V','E','s','0',e),('R','R1','s','a',1000),('R','R2','a','0',2000),('G','G','0','a','a','0',gm),('I','I','0','a',i)]
 if load is not None:net.append(('R','RL','a','0',load))
 return net

def bridge_net(delta=0,load=None,errors=(0,0,0,0)):
 delta=finite(delta)
 if len(errors)!=4:raise ValueError('four mismatches required')
 eps=[finite(e) for e in errors];rs=[1000*(1+v) for v in eps];rs[3]+=1000*delta
 if min(rs)<=0:raise ValueError('positive bridge arms required')
 net=[('V','E','s','0',5),('R','R1','s','a',rs[0]),('R','R2','a','0',rs[1]),('R','R3','s','b',rs[2]),('R','R4','b','0',rs[3])]
 if load is not None:net.append(('R','RL','b','a',load))
 return net

def bridge_exact(delta,load=None):
 d=finite(delta)
 if d<=-1:raise ValueError('delta must exceed -1')
 vo=5*d/(2*(2+d));rth=500+1000*(1+d)/(2+d)
 if load is not None:
  r=finite(load)
  if r<=0:raise ValueError('positive load required')
  vo*=r/(r+rth)
 return vo

def load_account(rl,e=5,rs=1000):
 r=finite(rl);e=finite(e);rs=finite(rs)
 if r<=0 or rs<=0:raise ValueError('positive resistances required')
 i=e/(rs+r)
 return {'I_A':i,'PL_W':i*i*r,'PRs_W':i*i*rs,'Pdelivered_W':e*i,'eta':None if e==0 else r/(rs+r)}
