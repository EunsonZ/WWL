"""Deterministic local scientific views, explicit --output, no import side effects."""
from pathlib import Path
import math,json,csv,argparse
import core_lab as a

def build(output):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import numpy as np
 import cairosvg
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 with plt.rc_context(fname=Path(__file__).with_name('matplotlibrc')):
  def rows(n):return plt.subplots(n,1,figsize=(4.25,3*n),squeeze=False)
  def save(fig,name):fig.savefig(out/(name+'.svg'),metadata={'Date':None});fig.savefig(out/(name+'.png'),dpi=150);plt.close(fig)
  t=np.linspace(0,.006,401);ds=[a.rc_account(x) for x in t]
  fig,axes=rows(2)
  for key,label in [('p_source_abs_W','source absorbed'),('p_R_W','resistor absorbed'),('p_C_W','capacitor absorbed')]:axes[0,0].plot(t*1000,[d[key]*1000 for d in ds],label=label)
  axes[0,0].set(xlabel='time (ms)',ylabel='power (mW)',title='RC · sum of all absorbed powers = 0');axes[0,0].legend()
  for key,label in [('source_delivered_J','source delivered'),('R_loss_J','resistor loss'),('C_delta_J','stored-energy change')]:axes[1,0].plot(t*1000,[d[key]*1e6 for d in ds],label=label)
  axes[1,0].set(xlabel='time (ms)',ylabel='energy since t=0 (μJ)',title='0.6 μJ = 0.18 μJ + 0.42 μJ');axes[1,0].legend()
  for ax in axes.flat:ax.grid(alpha=.2)
  fig.suptitle('R=1 kΩ; C=1 μF; U=1 V; v0=0.4 V');save(fig,'energy-ledger')
  fig,axes=rows(2);f=np.logspace(0,6,401);h=np.array([a.probe_h(x) for x in f]);axes[0,0].semilogx(f,abs(h));axes[0,0].scatter([1e4],[abs(a.probe_h(1e4))]);axes[0,0].set(xlabel='frequency (Hz)',ylabel='amplitude / Vth',title='Probe: 1 MΩ parallel with 100 pF\nSource Rth=100 kΩ (assumed)')
  axes[1,0].semilogx(f,np.angle(h)*180/np.pi);axes[1,0].set(xlabel='frequency (Hz)',ylabel='phase (degrees)',title='Capacitance changes the loading')
  for ax in axes.flat:ax.grid(alpha=.2)
  save(fig,'probe-loading')
  fig,axes=rows(2);x=np.linspace(0,7,401);axes[0,0].plot(x,np.exp(-x));axes[0,0].scatter([1,math.log(100)],[math.exp(-1),.01]);axes[0,0].set(xlabel='t / τ (dimensionless)',ylabel='remaining fraction',title='Exponential: τ is not a deadline')
  ratios=np.logspace(-2,1,301);axes[1,0].semilogx(ratios,20*np.log10(ratios),label='amplitude-ratio level');axes[1,0].semilogx(ratios,10*np.log10(ratios),label='power-ratio level');axes[1,0].set(xlabel='positive ratio of stated quantity',ylabel='level difference (dB)',title='State the quantity before using dB');axes[1,0].legend()
  for ax in axes.flat:ax.grid(alpha=.2)
  save(fig,'exp-db')
  fig,axes=rows(3);tt=np.linspace(0,.003,601)
  axes[0,0].step(tt*1000,[a.pulse_current(x)*1000 for x in tt],where='post');axes[0,0].fill_between(tt*1000,[a.pulse_current(x)*1000 for x in tt],step='post',alpha=.2);axes[0,0].set(xlabel='time (ms)',ylabel='current (mA)',title='Signed area: +0.2 − 0.1 = 0.1 μC')
  for v0 in (.4,.1):axes[1,0].plot(tt*1000,[a.pulse_voltage(x,v0) for x in tt],label=f'v0={v0} V')
  axes[1,0].set(xlabel='time (ms)',ylabel='voltage (V)',title='Same current; different initial states');axes[1,0].legend()
  axes[2,0].plot(tt*1000,[.5e-6*a.pulse_voltage(x)**2*1e6 for x in tt]);axes[2,0].set(xlabel='time (ms)',ylabel='stored energy (μJ)',title='C=1 μF: ΔE=0.045 μJ')
  for ax in axes.flat:ax.grid(alpha=.2)
  save(fig,'charge-slope')
  fig,ax=plt.subplots(figsize=(4.25,4.25));ax.axhline(0,color='gray');ax.axvline(0,color='gray');ax.annotate('',xy=(3,4),xytext=(0,0),arrowprops=dict(arrowstyle='->',color='#1769a6',lw=2));ax.plot([3,3,0],[0,4,4],ls='--',color='gray');ax.text(1.2,2.5,'|z|=5');ax.text(3.1,4.1,'z=3+j4');ax.text(1.5,-.5,'Re=3');ax.text(-.6,2,'Im=4',rotation=90);phi=math.atan2(4,3);arc=np.linspace(0,phi,50);ax.plot(np.cos(arc),np.sin(arc),color='orange');ax.text(.55,.8,'φ=53.13°',fontsize=10);ax.set(xlim=(-1,5),ylim=(-1,5),xlabel='Re z',ylabel='Im z',title='V07 supplement · modulus is distance');ax.set_aspect('equal');ax.grid(alpha=.2);save(fig,'V07-magnitude')
 # Native-width editable topology, with text kept at 14 px. No photographs or instrument captures.
 def T(x,y,s,color='#25334a'):return f'<text x="{x}" y="{y}" fill="{color}" stroke="none" font-family="DejaVu Sans" font-size="14">{s}</text>'
 def L(x1,y1,x2,y2,color=None):return f'<path d="M{x1},{y1} L{x2},{y2}"'+(f' stroke="{color}"' if color else '')+'/>'
 def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#25334a"/>'
 def R(x,y,label,h=False):
  if h:return L(x,y,x+10,y)+f'<rect x="{x+10}" y="{y-8}" width="40" height="16"/>'+L(x+50,y,x+60,y)+T(x+5,y-15,label)
  return L(x,y,x,y+10)+f'<rect x="{x-8}" y="{y+10}" width="16" height="40"/>'+L(x,y+50,x,y+65)+T(x+14,y+35,label)
 def S(x,y,label,current=False):
  body=f'<circle cx="{x}" cy="{y}" r="22"/>'+T(x-15,y-35,label)
  return body+(f'<path d="M{x},{y+12} L{x},{y-12} m-4,7 4,-7 4,7"/>' if current else T(x-5,y-5,'+')+T(x-5,y+15,'−'))
 def M(x,y,label):return f'<circle cx="{x}" cy="{y}" r="23"/>'+T(x-6,y+5,label)
 def A(x1,y1,x2,y2,label,x,y):return L(x1,y1,x2,y2)+f'<path d="M{x2},{y2} l-6,-4 m6,4 l-6,4"/>'+T(x,y,label)
 def svg(name,body,height):
  p=out/(name+'.svg');p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{height}" viewBox="0 0 360 {height}"><rect width="100%" height="100%" fill="white"/><g fill="none" stroke="#25334a" stroke-width="2">'+body+'</g></svg>');cairosvg.svg2png(url=str(p),write_to=str(out/(name+'.png')))
 b=T(15,25,'V02 · source absorption (ideal model)')+T(15,48,'Both negative terminals share node 0.')+S(50,180,'S5: 5 V')+S(300,180,'S1: 1 V')+L(50,158,50,105)+L(50,105,130,105)+R(130,105,'4 kΩ',True)+L(190,105,300,105)+L(300,105,300,158)+L(50,202,50,260)+L(50,260,300,260)+L(300,260,300,202)+dot(50,105)+dot(300,105)+T(50,83,'a=5 V')+T(255,83,'b=1 V')+T(165,285,'0 V')+A(130,72,210,72,'I=1 mA',140,65)+T(15,325,'S5 absorbed: −5 mW (delivers)')+T(15,350,'R absorbed: +4 mW')+T(15,375,'S1 absorbed: +1 mW')+T(15,405,'Sum = 0. No real sources connected.')
 svg('V02-source-absorption',b,435)
 # Two node network, direct branch direction annotations.
 b=T(15,25,'V03 · two nodes and branch currents')+S(40,205,'1 mA',True)+L(40,183,40,105)+L(40,105,130,105)+R(130,105,'1 kΩ',True)+L(190,105,300,105)+dot(130,105)+dot(300,105)+L(130,105,130,165)+R(130,165,'2 kΩ')+L(130,230,130,285)+L(300,105,300,165)+R(300,165,'2 kΩ')+L(300,230,300,285)+L(40,227,40,285)+L(40,285,300,285)+dot(130,285)+T(85,67,'a=1.2 V')+T(265,85,'b=0.8 V')+T(160,308,'0 V')+A(200,65,250,65,'0.4 mA',190,55)+L(105,165,105,220)+f'<path d="M105,220 l-4,-7 m4,7 l4,-7"/>'+T(15,245,'0.6 mA')+L(275,165,275,220)+f'<path d="M275,220 l-4,-7 m4,7 l4,-7"/>'+T(232,245,'0.4 mA')+T(15,345,'a: 1.0 = 0.6 + 0.4 mA')+T(15,372,'b: 0.4 in = 0.4 out mA')
 svg('V03-two-node-currents',b,400)
 # Meter diagrams: actual two-terminal V parallel, A series.
 b=''
 for offset,current in [(0,False),(410,True)]:
  k=offset;b+=T(15,k+25,'Current meter in series' if current else 'Voltage meter in parallel')+T(15,k+48,'5 V; R1=4 kΩ; R2=1 kΩ')+S(40,k+220,'5 V')+L(40,k+198,40,k+120)
  if current:b+=L(40,k+120,77,k+120)+M(100,k+120,'A')+L(123,k+120,150,k+120)+R(150,k+120,'R1',True)+L(210,k+120,240,k+120)
  else:b+=L(40,k+120,150,k+120)+R(150,k+120,'R1',True)+L(210,k+120,240,k+120)
  b+=dot(240,k+120)+T(250,k+108,'a (+)')+L(240,k+120,240,k+180)+R(240,k+180,'R2')+L(240,k+245,240,k+300)+L(40,k+242,40,k+300)+L(40,k+300,240,k+300)+T(180,k+323,'0 (−)')
  if not current:b+=L(240,k+120,315,k+120)+L(315,k+120,315,k+193)+M(315,k+216,'V')+L(315,k+239,315,k+300)+L(240,k+300,315,k+300)+T(270,k+175,'V jack')+T(265,k+277,'COM')
  else:b+=T(70,k+85,'A to COM')
  b+=T(15,k+360,'Rm parallels R2.' if not current else 'RA is added to the loop.')+T(15,k+383,'Model only; not instrument readings.')
 svg('meters',b,820)
 # Ground path is deliberately explicit. Lower circuit is a modeled fault, not an instruction to try.
 b=''
 for k,fault in [(0,False),(360,True)]:
  b+=T(15,k+25,'Modeled fault: clip at a shorts R2' if fault else 'Ground-referenced measurement')+T(15,k+48,'DUT 0 is already bonded to PE.')+S(50,k+180,'5 V DUT')+L(50,k+110,50,k+158)+L(50,k+202,50,k+250)+L(50,k+110,150,k+110)+R(150,k+110,'R1 4kΩ',True)+L(210,k+110,270,k+110)+dot(270,k+110)+T(275,k+95,'a')+L(270,k+110,270,k+145)+R(270,k+145,'R2 1kΩ')+L(270,k+210,270,k+250)+L(50,k+250,270,k+250)+L(50,k+250,50,k+285)+T(15,k+306,'DUT 0 to PE')+T(115,k+306,'Scope shell to PE')+L(50,k+285,150,k+285)+dot(150,k+285)
  b+=L(150,k+285,150,k+250)+L(150,k+250,150,k+230 if not fault else k+70,'#b64232' if fault else '#1769a6')
  if fault:b+=L(150,k+70,270,k+70,'#b64232')+L(270,k+70,270,k+110,'#b64232')+T(15,k+330,'Clip wire: a - PE - 0 (do not try)')
  else:b+=L(150,k+230,50,k+230,'#1769a6')+L(50,k+230,50,k+250,'#1769a6')+T(15,k+330,'Clip at 0; tip senses a (tip not wired here).')
 svg('earth-path',b,720)
 # Unit-rich machine data and blank measurement records.
 import cmath
 h=a.probe_h(1e4)
 data={'layer':'analytic predictions only; no instrument measurements','source_ledger':a.source_ledger(),'divider':{'vs_V':5,'r1_ohm':4000,'r2_ohm':1000,'loads_ohm':[None,1000,4000,10000],'predictions_V':[a.divider(5,4000,1000,x) for x in [None,1000,4000,10000]]},'probe_assumptions':{'Rth_ohm':100000,'Rp_ohm':1000000,'Cp_F':100e-12,'f_Hz':10000,'H_real':h.real,'H_imag':h.imag,'magnitude':abs(h),'phase_deg':cmath.phase(h)*180/math.pi},'two_nodes':{'ground_resistors_ohm':2000,'link_ohm':1000,'injected_A':[.001,0],'predicted_V':a.two_nodes()},'MNA_scales':{'V0_V':1,'I0_A':.001,'Khat':[[1,1],[1,0]],'kappa2':(3+math.sqrt(5))/2},'netlists':{'source_absorption':[['S5','a','0','5 V'],['S1','b','0','1 V'],['R','a','b','4000 ohm']],'two_nodes':[['I','0','a','0.001 A'],['Ra','a','0','2000 ohm'],['Rab','a','b','1000 ohm'],['Rb','b','0','2000 ohm']]}}
 (out/'predictions.json').write_text(json.dumps(data,indent=2)+'\n')
 with (out/'charge-data.csv').open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['t_s','i_A','v_V','q_change_C','stored_J']);writer.writerows((x,a.pulse_current(x),a.pulse_voltage(x),1e-6*(a.pulse_voltage(x)-.4),.5e-6*a.pulse_voltage(x)**2) for x in tt)
 with (out/'measurement-record.csv').open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['scenario','predicted_V','measured_V','device_model','range','red_jack','reference_node','notes']);writer.writerow(['unloaded divider',1,'','','','','0','NO MEASUREMENT']);writer.writerow(['assumed 1M meter',a.divider(5,4000,1000,1e6),'','','','','0','NO MEASUREMENT'])
 print('generated 9 editable SVG/PNG views, unit data and blank measurement records')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);build(p.parse_args().output)
