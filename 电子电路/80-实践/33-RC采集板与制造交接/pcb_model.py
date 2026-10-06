"""Finite real SI models and bounded teaching-coordinate checks; pure import."""
import argparse,json,math
from pathlib import Path

def real(x,n,lo,hi):
 if type(x) not in (int,float) or not lo<=x<=hi or not math.isfinite(x):raise ValueError(n+' requires native finite real in supported domain')
 return float(x)
def rc(t,source=1.,initial=.4,r=1000.,c=1e-6,load=10000.,probe=None):
 t=real(t,'t',0,100);u=real(source,'source',0,3.3);v0=real(initial,'initial',0,3.3);r=real(r,'r',1,1e9);c=real(c,'c',1e-12,1e-2);rl=real(load,'load',1,1e12)
 if probe is not None:rp=real(probe,'probe',1,1e12);rl=rl*rp/(rl+rp)
 k=rl/(r+rl);tau=(r*rl/(r+rl))*c;z=t/tau;rise=-math.expm1(-z);v=v0*math.exp(-z)+(k*u)*rise
 return {'voltage_V':v,'gain':k,'tau_s':tau,'pole_Hz':1/(2*math.pi*tau),'load_eff_ohm':rl}
def sharing(external_C=1e-6,internal_C=20e-12,external_V=2.,internal_V=0.):
 a=real(external_C,'external_C',1e-12,1e-2);b=real(internal_C,'internal_C',1e-15,1e-3);v=real(external_V,'external_V',0,3.3);w=real(internal_V,'internal_V',0,3.3)
 dv=(w-v)*(b/(a+b));return {'shared_V':v+dv,'external_jump_V':dv,'charge_transfer_C':a*dv}
def coupling(c_victim=1e-6,c_cross=1e-12,edge_V=3.3):
 c=real(c_victim,'victimC',1e-12,1e-2);x=real(c_cross,'crossC',1e-15,1e-6);v=real(edge_V,'edge',-3.3,3.3)
 return {'charge_C':x*v,'step_V':v*(x/(c+x))}
def loop(frequency=1e8,inductance=2e-9,delta_I=.005,edge_s=5e-9,resistance=.05):
 f=real(frequency,'f',0,1e9);l=real(inductance,'L',0,1e-3);di=real(delta_I,'dI',-1,1);dt=real(edge_s,'edge',1e-12,1);r=real(resistance,'R',0,1e6)
 return {'reactance_ohm':2*math.pi*f*l,'slope_drop_V':l*di/dt,'resistive_step_V':r*di}
def decap(frequency=1e8,c=1e-7,esr=.05,esl=2e-9,delta_I=.005,duration=5e-9):
 f=real(frequency,'f',1,1e9);c=real(c,'C',1e-12,1e-2);r=real(esr,'ESR',0,1e6);l=real(esl,'ESL',1e-15,1e-3);i=real(delta_I,'I',-1,1);t=real(duration,'duration',1e-12,1)
 w=2*math.pi*f;x=w*l-1/(w*c)
 return {'real_ohm':r,'imag_ohm':x,'magnitude_ohm':math.hypot(r,x),'resonance_Hz':1/(2*math.pi*math.sqrt(l*c)),'charge_drop_V':i*t/c,'ESR_step_V':i*r}
def energy(voltage=3.3,capacitances=(1e-6,1e-7,1e-6)):
 v=real(voltage,'V',0,3.3)
 if type(capacitances) not in (list,tuple) or not 1<=len(capacitances)<=32:raise ValueError('1..32 capacitors required')
 cs=[real(c,'C',1e-15,1e-2) for c in capacitances];return sum(cs)*v*v/2

def geometry(board):
 """Point/orthogonal centerline plus rectangular pad clearance, assumed unfilled GND plane.
 Not KiCad ERC/DRC or electromagnetic extraction. Strict bounded input, no hidden cast.
 """
 if type(board) is not dict:raise ValueError('native board dict')
 pads=board.get('pads');routes=board.get('front_paths');vias=board.get('ground_vias')
 if type(pads) is not list or not 1<=len(pads)<=128 or type(routes) is not dict or len(routes)>8 or type(vias) is not list or len(vias)>64:raise ValueError('bounded board collections')
 pp=[]
 for p in pads:
  if type(p) is not dict or any(type(p.get(k)) is not str for k in ['ref','pin','net']):raise ValueError('pad labels required')
  x=real(p.get('x_mm'),'padx',.5,39.5);y=real(p.get('y_mm'),'pady',.5,29.5);pp.append((p['ref'],p['pin'],p['net'],x,y))
 vv=[]
 for v in vias:
  if type(v) is not dict or v.get('net')!='GND':raise ValueError('GND via only')
  vv.append((real(v.get('x_mm'),'viax',.5,39.5),real(v.get('y_mm'),'viay',.5,29.5)))
 seg=[]
 for net,paths in routes.items():
  if type(net) is not str or type(paths) is not list or len(paths)>64:raise ValueError('route labels/budget')
  for path in paths:
   if type(path) not in (list,tuple) or not 2<=len(path)<=64:raise ValueError('bounded route')
   points=[]
   for p in path:
    if type(p) not in (list,tuple) or len(p)!=2:raise ValueError('xy pair')
    points.append((real(p[0],'x',.5,39.5),real(p[1],'y',.5,29.5)))
   for a,b in zip(points,points[1:]):
    if a==b or (a[0]!=b[0] and a[1]!=b[1]):raise ValueError('nonzero orthogonal segments only')
    seg.append((net,a,b))
 if len(seg)>512:raise ValueError('segment budget')
 def on(p,a,b):return min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
 violations=[]
 for j,(n,a,b) in enumerate(seg):
  for m,c,d in seg[j+1:]:
   if n==m:continue
   if max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])):violations.append('foreign centerline crossing '+n+'/'+m)
  hw=.25 if n=='VDD' else .125
  for ref,pin,pn,x,y in pp:
   if pn==n:continue
   px,py=(.85,.85) if ref.startswith('J') else (.75,.75) if ref.startswith('TP') else (.6,.7)
   ex=px+.25+hw;ey=py+.25+hw
   if ((a[1]==b[1] and y-ey<a[1]<y+ey and max(min(a[0],b[0]),x-ex)<min(max(a[0],b[0]),x+ex)) or (a[0]==b[0] and x-ex<a[0]<x+ex and max(min(a[1],b[1]),y-ey)<min(max(a[1],b[1]),y+ey))):violations.append('foreign pad clearance '+n+'/'+ref+'.'+pin)
 # Connectivity uses every pad/route/via junction lying on each finite segment.
 disconnected=[]
 for net in sorted({p[2] for p in pp}):
  nodes={(p[3],p[4]) for p in pp if p[2]==net}|{q for n,a,b in seg if n==net for q in (a,b)}
  if net=='GND':nodes|=set(vv)
  adj={p:set() for p in nodes}
  for n,a,b in seg:
   if n==net:
    q=[p for p in nodes if on(p,a,b)]
    for p in q:adj[p].update(q)
  if net=='GND':
   anchors=set(vv)|{(x,y) for ref,pin,n,x,y in pp if n=='GND' and ref.startswith('J')}
   for p in anchors:adj[p].update(anchors)
  seed=next((x,y) for ref,pin,n,x,y in pp if n==net);seen={seed};queue=[seed]
  for _ in range(len(nodes)):
   if not queue:break
   for q in adj[queue.pop()]:
    if q not in seen:seen.add(q);queue.append(q)
  for ref,pin,n,x,y in pp:
   if n==net and (x,y) not in seen:disconnected.append(ref+'.'+pin)
 return {'pad_count':len(pp),'front_segments':len(seg),'via_count':len(vv),'violations':violations,'disconnected_pads':disconnected,'ground_scope':'assumed rectangular B.Cu plane anchors; actual zone fill not_run','claim':'finite CPU geometry only, not ERC/DRC/field/physical proof'}

def generate(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 board=json.loads(Path(__file__).with_name('board.json').read_text())
 result={'rc_samples':[{'t_s':t,**rc(t)} for t in [0,.00025,.001,.005]],'probe':rc(100,probe=1e6),'sharing':sharing(),'coupling':coupling(),'loop_short':loop(),'loop_detour':loop(inductance=20e-9),'decap':decap(),'energy_J':energy(),'geometry':geometry(board)}
 (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)
if __name__=='__main__':main()
