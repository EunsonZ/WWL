"""Deterministic source drawings/data; explicit output only."""
from pathlib import Path
import argparse,json,csv,html
import network_lab as a

def build(output):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 import cairosvg
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 def L(x,y,u,v,color='#25344d',dash=False):return f'<path d="M{x},{y} L{u},{v}" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="5 4"' if dash else '')+'/>'
 def T(x,y,s,size=14):return f'<text x="{x}" y="{y}" font-size="{size}">{html.escape(s)}</text>'
 def D(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#25344d"/>'
 def R(x,y,s,h=False):
  if h:return L(x,y,x+10,y)+f'<rect x="{x+10}" y="{y-8}" width="40" height="16" fill="white" stroke="#25344d" stroke-width="2"/>'+L(x+50,y,x+60,y)+T(x+5,y-17,s)
  return L(x,y,x,y+10)+f'<rect x="{x-8}" y="{y+10}" width="16" height="40" fill="white" stroke="#25344d" stroke-width="2"/>'+L(x,y+50,x,y+60)+T(x+12,y+36,s)
 def S(x,y,s,current=False,dep=False,h=False):
  sh=(f'<path d="M{x},{y-21} L{x+21},{y} L{x},{y+21} L{x-21},{y} Z"' if dep else f'<circle cx="{x}" cy="{y}" r="21"')+' fill="white" stroke="#25344d" stroke-width="2"/>'
  if current:sh+=L(x,y+12,x,y-10)+f'<path d="M{x},{y-12} l-4,7 h8 Z" fill="#25344d"/>'
  elif h:sh+=T(x-14,y+5,'+')+T(x+7,y+5,'−')
  else:sh+=T(x-5,y-4,'+')+T(x-4,y+15,'−')
  return sh+T(x-22,y+42,s)
 def svg(name,b,height=430):
  s=f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}"><rect width="360" height="{height}" fill="white"/><g font-family="Arial,sans-serif" fill="#152236">{b}</g></svg>'
  (out/(name+'.svg')).write_text(s);cairosvg.svg2png(bytestring=s.encode(),write_to=str(out/(name+'.png')))
 # Nodes: real end-point connections, no ambiguous crossing.
 b=T(15,25,'Node model: all resistors 1 kΩ')+S(45,220,'E 5 V')+L(45,199,45,110)+L(45,110,90,110)+R(90,110,'Rsa',True)+L(150,110,190,110)+D(190,110)+T(180,90,'a')+R(190,160,'Ra')+L(190,110,190,160)+L(190,220,190,310)+R(220,110,'Rab',True)+L(190,110,220,110)+L(280,110,315,110)+D(315,110)+T(310,90,'b')+L(315,110,315,160)+R(315,160,'Rb')+L(315,220,315,310)+L(45,241,45,310)+L(45,310,315,310)+T(50,94,'s=5 V')+T(170,334,'0 V')+T(15,370,'a=2 V; b=1 V')+T(15,395,'3 mA in; 2+1 mA out at a')
 svg('nodes',b)
 b=T(15,25,'Supernode: E fixes a − b = 1 V')+S(40,200,'I 2 mA',True)+L(40,179,40,110)+L(40,110,125,110)+D(125,110)+T(112,86,'a')+L(125,110,159,110)+S(180,110,'E 1 V',h=True)+L(201,110,245,110)+D(245,110)+T(240,86,'b')+L(125,110,125,190)+R(125,190,'1 kΩ')+L(125,250,125,310)+L(245,110,245,190)+R(245,190,'2 kΩ')+L(245,250,245,310)+L(40,221,40,310)+L(40,310,245,310)+T(180,334,'0 V')+T(15,370,'a=5/3 V; b=2/3 V')+T(15,395,'E current a to b: 1/3 mA')
 svg('supernode',b)
 for supermesh in (False,True):
  b=T(15,25,'Shared source: i2 − i1 = 1 mA' if supermesh else 'Shared Rc=1 kΩ: ic = i1 − i2')+S(40,205,'E5 5 V')+S(320,205,'E1 1 V')+L(40,184,40,110)+L(40,110,65,110)+R(65,110,'R1 1 kΩ',True)+L(125,110,180,110)+D(180,110)+T(171,85,'a')+L(180,110,215,110)+R(215,110,'R2 2 kΩ',True)+L(275,110,320,110)+L(320,110,320,184)+L(40,226,40,310)+L(320,226,320,310)+L(40,310,320,310)
  if supermesh:b+=L(180,110,180,184)+S(180,205,'1 mA',True)+L(180,226,180,310)
  else:b+=L(180,110,180,175)+R(180,175,'Rc')+L(180,235,180,310)
  # clockwise loops, arrowheads drawn geometrically.
  for x in (70,230):b+=f'<path d="M{x},170 h45 v105 h-45 v-105" fill="none" stroke="#c15a18" stroke-width="2" stroke-dasharray="5 4"/><path d="M{x+45},205 l-4,-7 h8 Z" fill="#c15a18"/>'+T(x+6,298,'i1' if x==70 else 'i2')
  b+=T(15,350,'0 V bottom wire')+T(15,378,'i1=2/3 mA; i2=5/3 mA' if supermesh else 'i1=2.8 mA; i2=0.6 mA')+T(15,405,'a=13/3 V (source voltage recovered)' if supermesh else 'a=2.2 V; ic=2.2 mA downward')
  svg('supermesh' if supermesh else 'meshes',b)
 # VCCS topology: control a−0 is named, not represented by conducting wire.
 b=T(15,25,'VCCS control: va = v(a) − v(0)')+T(15,49,'gm=0.25 mS; R2=2 kΩ')+S(35,210,'E 3 V')+L(35,189,35,110)+L(35,110,70,110)+R(70,110,'R1 1 kΩ',True)+L(130,110,310,110)+D(165,110)+T(158,88,'a')+L(165,110,165,175)+R(165,175,'R2')+L(165,235,165,310)+L(245,110,245,189)+S(245,210,'gm va',True,True)+L(245,231,245,310)+L(310,110,310,189)+S(310,210,'I',True)+L(310,231,310,310)+L(35,231,35,310)+L(35,310,310,310)+T(280,276,'0.5 mA')+T(15,355,'Output port: a (+), 0 (−), open')+T(15,382,'va=2.8 V; igm=0.7 mA')+T(15,409,'Control label is not an extra wire.')
 svg('controlled',b,445)
 b=T(15,25,'V04 local view: test source at a–0')+T(15,48,'E=0; I=0; gm retained; R2=2 kΩ')+S(40,200,'Vt 1 V')+L(40,179,40,110)+L(40,110,295,110)+D(160,110)+T(152,87,'a')+L(120,110,120,160)+R(120,160,'R1 1 kΩ')+L(120,220,120,310)+L(220,110,220,160)+R(220,160,'R2')+L(220,220,220,310)+L(295,110,295,179)+S(295,200,'gm Vt',True,True)+L(295,221,295,310)+L(40,221,40,310)+L(40,310,295,310)+T(150,335,'0 V')+T(15,366,'It = 1 + 0.5 − 0.25 = 1.25 mA')+T(15,394,'Rth = 1 V / 1.25 mA = 800 Ω')
 svg('port-test',b)
 b=T(15,25,'Actual dissipating Rs model')+S(50,210,'E 5 V')+L(50,189,50,110)+L(50,110,110,110)+R(110,110,'Rs 1 kΩ',True)+L(170,110,270,110)+D(270,110)+T(273,92,'a (+)')+L(270,110,270,175)+R(270,175,'RL > 0')+L(270,235,270,310)+L(50,231,50,310)+L(50,310,270,310)+T(180,336,'0 (−)')+T(15,372,'Rs heat is included in this model.')+T(15,401,'Port-equivalent Rs alone ≠ real loss.')
 svg('power-circuit',b)
 b=T(15,25,'Bridge: vo = vb − va')+T(15,49,'Vs=5 V; nominal arms 1 kΩ')+S(35,235,'Vs 5 V')+L(35,214,35,90)+L(35,90,280,90)+L(35,256,35,380)+L(35,380,280,380)
 for x,top,bot,node in [(125,'R1','R2','a (−)'),(280,'R3','R4','b (+)')]:
  b+=L(x,90,x,120)+R(x,120,top)+L(x,180,x,235)+D(x,235)+T(x-10,216,node)+L(x,235,x,275)+R(x,275,bot)+L(x,335,x,380)
 b+=L(125,235,165,235)+R(165,235,'Rg optional',True)+L(225,235,280,235)+T(15,418,'R4=1000(1+δ) Ω; δ > −1')+T(15,445,'Readout connects b to a, not to 0.')
 svg('bridge',b,475)
 with plt.rc_context(fname=Path(__file__).with_name('matplotlibrc')):
  def save(fig,name):fig.savefig(out/(name+'.svg'),metadata={'Date':None});fig.savefig(out/(name+'.png'),dpi=150);plt.close(fig)
  fig,ax=plt.subplots(figsize=(4.25,4));i=np.linspace(0,3.5,200);ax.plot(i,2.8-.8*i,label='port: v=2.8−0.8 i(mA)')
  for rl in (.8,4):
   ax.plot(i,rl*i,label=f'RL={rl} kΩ');ip=2.8/(.8+rl);ax.scatter([ip],[rl*ip])
  ax.set(xlabel='outward load current (mA)',ylabel='port voltage (V)',ylim=(0,3),title='Load-line intersections');ax.legend(fontsize=9);save(fig,'load-line')
  r=np.logspace(-2,2,400);fig,axes=plt.subplots(2,1,figsize=(4.25,6));axes[0].semilogx(r,25*r/(1+r)**2);axes[0].scatter([1],[6.25]);axes[0].set(ylabel='load power (mW)',title='5 V source; actual Rs=1 kΩ');axes[1].semilogx(r,100*r/(1+r));axes[1].set(xlabel='RL / Rs (dimensionless)',ylabel='efficiency (%)');save(fig,'power-efficiency')
  ds=np.linspace(-.05,.05,301);fig,axes=plt.subplots(2,1,figsize=(4.25,6));axes[0].plot(ds,1000*np.array([a.bridge_exact(x) for x in ds]),label='open exact');axes[0].plot(ds,1250*ds,'--',label='linear');axes[0].plot(ds,1000*np.array([a.bridge_exact(x,10000) for x in ds]),label='loaded 10 kΩ');axes[0].set(ylabel='vo (mV)',title='5 V bridge: exact / small change');axes[0].legend(fontsize=9);axes[1].plot(ds,1e6*(1250e-3*ds-np.array([a.bridge_exact(x) for x in ds])));axes[1].set(xlabel='δ = ΔR / R (dimensionless)',ylabel='linear minus exact (µV)');save(fig,'bridge-sensitivity')
 names={'nodes':a.node_net(),'supernode':a.supernode_net(),'meshes':a.mesh_net(),'supermesh':a.mesh_net(True),'controlled':a.controlled_net(),'bridge_open':a.bridge_net(.01),'bridge_loaded':a.bridge_net(.01,10000)};data={'evidence':'analytic CPU model only; no hardware or SPICE','cases':{}}
 for name,net in names.items():
  d=a.solve(net);data['cases'][name]={'netlist':net,**{k:d[k] for k in ('volts_V','currents_A','absorbed_W')}}
 (out/'networks.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 with (out/'bridge-data.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['delta_fraction','open_V','loaded_10k_V','linear_V'])
  for x in [-.05,-.01,0,.01,.05]:w.writerow([x,a.bridge_exact(x),a.bridge_exact(x,10000),1.25*x])
 print('Generated 11 editable SVG/PNG and 2 unit data files')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();build(args.output)
