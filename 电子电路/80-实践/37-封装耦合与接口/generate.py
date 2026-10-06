"""Lazy, external-output-only author figures and finite teaching data."""
import argparse,json,math
from pathlib import Path
import models as m
PARAMETERS={'interface':{'lanes':16,'rate_bps':16e9,'coding':1,'payload_bytes':64,'frame_bytes':68,'utilization':.8,'message_bytes':256,'fixed_s':2e-9,'energy_J_per_wire_bit':.5e-12,'idle_W':.02},'RLC':{'R_ohm':20,'L_H':.2e-9,'C_F':.5e-12},'thermal':{'baseline_W':[8,4],'Ra_K_W':2,'R12_K_W':4,'C_J_K':2,'ambient_K':300},'geometry':'schematic coordinates independent of manufactured dimensions; die areas1cm2 for cost/power examples only'}
def generate(output):
 out=Path(output).resolve();candidate=Path(__file__).resolve().parents[3];main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
 if out==candidate or candidate in out.parents or out==main or main in out.parents:raise ValueError('external output required')
 if out.exists():raise ValueError('new output directory required')
 out.mkdir(parents=True);assets=out/'assets';assets.mkdir();data=out/'data';data.mkdir()
 from matplotlib.figure import Figure
 from matplotlib import rc_context
 from matplotlib.patches import Rectangle,Circle
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 import numpy as np
 import cairosvg
 def save(fig,name):
  fig.savefig(assets/(name+'.svg'),metadata={'Date':None})
  for w in (360,425):cairosvg.svg2png(url=str(assets/(name+'.svg')),write_to=str(assets/(name+f'-{w}.png')),output_width=w)
 def arrow(ax,a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'black'})
 def two():
  f=Figure(figsize=(8,6),layout='constrained');return f,f.subplots(2,1)
 def component(ax,x,y,w,h,label):ax.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor='black'));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=13)
 results={'interface':m.interface(**PARAMETERS['interface']),'thermal_with_link':m.thermal(8.0612,4.0612,2,4,2,100),'cte':m.thermo_mechanical(15e-6,3e-6,60,.005,.0001),'mono_cost':m.yield_cost([2],.3,20,0,5,.99),'chiplet_cost':m.yield_cost([1,1],.3,20,0,10,.95),'chiplet_expensive':m.yield_cost([1,1],.3,20,0,25,.95)}
 with rc_context({'font.family':'DejaVu Sans','font.size':14,'svg.fonttype':'none','svg.hashsalt':'frontier02-r1','axes.grid':True}):
  f=Figure(figsize=(8,7),layout='constrained');gs=f.add_gridspec(2,1);a=f.add_subplot(gs[0],projection='3d')
  def cuboid(x,y,z,dx,dy,dz,color):
   pts=[(x,y,z),(x+dx,y,z),(x+dx,y+dy,z),(x,y+dy,z),(x,y,z+dz),(x+dx,y,z+dz),(x+dx,y+dy,z+dz),(x,y+dy,z+dz)];faces=[[pts[i] for i in ids] for ids in [[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]];a.add_collection3d(Poly3DCollection(faces,facecolors=color,edgecolors='black',alpha=.55))
  cuboid(0,0,0,10,6,.4,'gray');cuboid(1,1,.7,8,4,.25,'#77aadd');cuboid(1.5,1.5,1.2,2.5,3,.5,'#eeaa77');cuboid(6,1.5,1.2,2.5,3,.5,'#eeaa77');a.text(2,3,1.8,'Die A');a.text(6.5,3,1.8,'Die B');a.plot([4,6],[2.9,2.9],[1.05,1.05],color='black',lw=2);a.plot([4,6],[3.1,3.1],[1,1],color='black',lw=2);a.quiver([2.75,7.25],[3,3],[1.7,1.7],[0,0],[0,0],[.65,.65],color='black',arrow_length_ratio=.25);a.set(xlim=(0,10),ylim=(0,6),zlim=(0,2.5),xlabel='schematic x',ylabel='schematic y',zlabel='schematic z',title='3D: side-to-side electrical path; vertical heat paths');a.set_box_aspect((2,1.2,1.1));a.view_init(elev=25,azim=-60)
  a=f.add_subplot(gs[1]);a.axis('off');a.set(xlim=(0,10),ylim=(0,6));component(a,.5,1,9,.5,'package substrate');component(a,1,2,8,.4,'');a.text(5,1.7,'interposer / bridge (schematic)',ha='center',fontsize=12);component(a,1.5,3,2.5,1,'A');component(a,6,3,2.5,1,'B')
  for x in (2,3.5,6.5,8):a.plot([x,x],[2.4,3],'ko-')
  a.plot([3.5,6.5],[2.6,2.6],'k');a.plot([2,8],[2.1,2.1],'k--');arrow(a,(3.5,4.1),(3.5,5));arrow(a,(7,4.1),(7,5));a.text(.3,5.3,'heat: seconds / K');a.text(4.1,2.8,'signal + return: ps');arrow(a,(2.2,.3),(7.7,.3));a.text(2.3,.55,'CTE mismatch: micrometers, not lifetime');f.suptitle('Independent schematic dimensions; NOT manufacturing geometry');save(f,'01-package')
  f,ax=two();a=ax[0];a.set(xlim=(0,10),ylim=(0,5));a.axis('off');a.plot([1,1,9,9],[3.8,.6,.6,3.8],'k');a.plot([1,9],[3.8,3.8],'k');a.add_patch(Circle((1,2.2),.6,facecolor='white',edgecolor='black'));a.text(1,2.2,'Vs',ha='center');a.text(.2,3,'+');a.text(.2,1.4,'-');component(a,2.4,3.5,1.8,.6,'R 20ohm');component(a,5,3.5,1.8,.6,'L .2nH');a.plot([9,9],[.6,3.8],'k');component(a,8.5,1.8,1,1,'C\n.5pF');a.text(7.3,4.2,'v, high-Z RX');a.text(4,.1,'return 0: complete two-terminal source loop');arrow(a,(4.2,3.8),(4.9,3.8));a.text(4.4,4.1,'i');a.plot([9],[3.8],'ko')
  tt=np.linspace(0,150e-12,301);vv=[m.rlc_step(20,.2e-9,.5e-12,float(t))['voltage_per_V'] for t in tt];ax[1].plot(tt*1e12,vv);ax[1].axhline(1,color='black',ls='--');ax[1].axvline(62.5,color='black',ls=':');ax[1].set(xlabel='time ps; dotted=62.5ps UI',ylabel='v / Vs');f.suptitle('Local lumped RLC, zeta=.5; not full channel eye certification');save(f,'02-rlc')
  f,ax=two();a=ax[0];a.axis('off');a.set(xlim=(0,10),ylim=(0,6));a.plot([2,8],[4.2,4.2],'k');component(a,4.2,3.9,1.6,.6,'R12=4 K/W');a.plot([1,9],[.5,.5],'k');a.text(1,.1,'theta=0: ambient 300K')
  for x,label in [(3,'A'),(7,'B')]:
   a.plot([x-1,x-1],[.5,4.2],'k');a.plot([x+1,x+1],[.5,4.2],'k');a.plot([x-1,x+1],[4.2,4.2],'k');component(a,x-1.5,1.5,1,1,'Ra=2\nK/W');component(a,x+.5,1.5,1,1,'C=2\nJ/K');a.plot([x],[4.2],'ko');arrow(a,(x,5.6),(x,4.4));a.text(x,5.7,'P'+label+' W',ha='center');a.text(x,4.5,'theta'+label,ha='center')
  tt=np.linspace(0,16,161);vals=[m.thermal(8,4,2,4,2,float(t))['rise_K'] for t in tt];ax[1].plot(tt,[v[0] for v in vals],label='A:8W');ax[1].plot(tt,[v[1] for v in vals],'--',label='B:4W');ax[1].set(xlabel='time seconds; zero initial temperature rise',ylabel='rise K');ax[1].legend();f.suptitle('Two mean die nodes, lateral heat and fixed environment');save(f,'03-thermal')
  f,ax=two();a=ax[0];a.axis('off');a.set(xlim=(0,10),ylim=(0,5));a.plot([1,9],[1,1],'k');a.plot([1,9],[3,3],'k');a.text(1,3.3,'material1 alpha=15ppm/K');a.text(1,.3,'material2 alpha=3ppm/K');a.plot([1,1],[.8,3.2],'k--');a.text(.4,4.3,'neutral x=0');a.plot([7,7],[1,3],'k');a.plot([7,7.4],[1,3],'k--');a.text(7.5,2,'joint h');arrow(a,(1,4),(7,4));a.text(4,4.2,'x=5mm',ha='center');a.text(1.5,1.6,'free mismatch du\nnot actual constrained shape',fontsize=12)
  dk=np.linspace(0,80,81);mm=[m.thermo_mechanical(15e-6,3e-6,float(t),.005,.0001)['free_mismatch_m']*1e6 for t in dk];ax[1].plot(dk,mm);ax[1].set(xlabel='specified temperature cycle range K',ylabel='free mismatch um');f.suptitle('At60K: du3.6um, du/h=.036; no fatigue-life prediction');save(f,'04-mechanical')
  f,ax=two();mult=[1,2,3,4];bud=[m.interface(n*16,16e9,1,64,68,.8,256,2e-9,.5e-12,.02) for n in mult];ax[0].plot(mult,[v['latency_s_no_queue']*1e9 for v in bud],'ko-',label='message ns');ax[0].set(xlabel='lane multiplier from16 (same message)',ylabel='no-queue delay ns');b=ax[0].twinx();b.plot(mult,[v['total_link_W'] for v in bud],'ks--',label='average link W');b.set_ylabel('link W');ax[0].set_title('More lanes reduce serialization; fixed2ns and idle20mW remain')
  ax[1].bar(['mono','2 dies pkg10','2 dies pkg25'],[results['mono_cost']['cost_per_good_assembly'],results['chiplet_cost']['cost_per_good_assembly'],results['chiplet_expensive']['cost_per_good_assembly']],color=['#77aadd','#eeaa77','#aaddaa']);ax[1].set(ylabel='cost units / good system');ax[1].set_title('Perfect known-good die sorting; independent Poisson & assembly');f.suptitle('Same partition: delay / energy / yield assumptions kept separate');save(f,'05-partition')
 (data/'parameters.json').write_text(json.dumps(PARAMETERS,indent=2)+'\n');(data/'results.json').write_text(json.dumps(results,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();generate(a.output)
if __name__=='__main__':main()
