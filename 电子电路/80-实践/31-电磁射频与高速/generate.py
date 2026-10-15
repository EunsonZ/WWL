"""Lazy dependencies, direct Figure, local rc_context, external required output."""
import argparse,json,math
from pathlib import Path
import models as m
PARAMETERS={'Lprime_H_per_m':250e-9,'Cprime_F_per_m':100e-12,'length_m':.1,'Vs_V':1,'source_ohm':25,'reference_ohm':50,'PDN_branches_C_ESR_ESL':[[1e-7,.02,1e-9],[1e-9,.02,1e-9]],'UI_s':1e-9,'eye_tau_s':.25e-9,'antenna_pattern':'short dipole normalized POWER sin(theta)^2, theta from +z'}
def generate(output):
 out=Path(output).resolve();candidate=Path(__file__).resolve().parents[3];main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
 if out==candidate or candidate in out.parents or out==main or main in out.parents:raise ValueError('caller output must be outside candidate/main')
 if out.exists() and any(out.iterdir()):raise ValueError('empty output required')
 out.mkdir(parents=True,exist_ok=True);assets=out/'assets';assets.mkdir();data=out/'data';data.mkdir()
 from matplotlib.figure import Figure
 from matplotlib import rc_context
 from matplotlib.patches import Rectangle,Circle
 import numpy as np
 import cairosvg
 def save(f,name):
  f.savefig(assets/(name+'.svg'),metadata={'Date':None})
  for width in (360,425):cairosvg.svg2png(url=str(assets/(name+'.svg')),write_to=str(assets/(name+'-'+str(width)+'.png')),output_width=width)
 def two():
  f=Figure(figsize=(8,6),layout='constrained');return f,f.subplots(2,1)
 def arrow(ax,a,b,label=None):
  ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'black'})
  if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2,label,fontsize=12)
 results={'parameters':PARAMETERS,'line':m.lossless(250e-9,100e-12,.1)}
 with rc_context({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','svg.hashsalt':'rf1-r1','axes.grid':True}):
  f,ax=two();a=ax[0];a.set(xlim=(0,10),ylim=(0,4));a.axis('off');a.add_patch(Rectangle((1,3),8,.15,color='gray'));a.add_patch(Rectangle((1,1),8,.15,color='gray'));a.text(1,3.4,'forward conductor: +i (A)');a.text(1,.45,'return conductor: -i (A)')
  for x in (2,4,6,8):arrow(a,(x,2.95),(x,1.2))
  a.text(4.5,2,'E (V/m)');arrow(a,(1,3.15),(8,3.15));arrow(a,(8,1.1),(1,1.1));a.text(7,2.6,'H around loop');a.text(1,0,'Two-conductor teaching cross section; not PCB field simulation')
  rises=np.logspace(-11,-7,200);ax[1].loglog(rises*1e9,.5e-9/rises);ax[1].axhline(1,ls='--',color='black');ax[1].set(xlabel='rise time ns',ylabel='one-way T / rise time');f.suptitle('Field storage -> distributed L/C; 0.1 m at 2e8 m/s: T=0.5 ns');save(f,'01-fields-scale')
  f,ax=two();b=m.bounce(1,25,None,50,.5e-9,4);results['open_bounce']=b
  for w in b['waves']:
   ax[0].annotate('',xy=(w['x1']*.1,w['t1_s']*1e9),xytext=(w['x0']*.1,w['t0_s']*1e9),arrowprops={'arrowstyle':'->','color':'black'});ax[0].text(.04,(w['t0_s']+w['t1_s'])*.5e9,f"{w['amplitude_V']:+.3f} V",fontsize=10)
  ax[0].set(xlabel='position m: source 0, load 0.1',ylabel='time ns',xlim=(-.005,.105),ylim=(4.2,-.1));ax[0].set_title('Open load: GammaL=+1, source25ohm GammaS=-1/3')
  for load,name,style in [(None,'open +1','-'),(50,'matched 0','--'),(0,'short -1',':')]:
   bb=m.bounce(1,25,load,50,.5e-9,8);events=[e for e in bb['events'] if e['end']=='load'];ts=[0]+[v['time_s']*1e9 for v in events]+[8.5];vs=[0]+[v['total_V'] for v in events]+[events[-1]['total_V']];ax[1].step(ts,vs,where='post',ls=style,label=name)
  ax[1].set(xlabel='time ns',ylabel='load voltage V');ax[1].legend(fontsize=11);f.suptitle('Travel time and boundary sign share one model; Vs=1V');save(f,'02-bounce')
  f=Figure(figsize=(7,6),layout='constrained');ax=f.subplots();ax.set_aspect('equal');ang=np.linspace(0,2*math.pi,361);ax.plot(np.cos(ang),np.sin(ang),'k');ax.axhline(0,color='gray',lw=.7)
  for r in (0,.2,.5,1,2,5):
   xx=np.linspace(-30,30,401);gg=[m.reflection(50*complex(r,x),50) for x in xx];ax.plot([g.real for g in gg],[g.imag for g in gg],color='gray',lw=.6)
  for x in (-2,-1,-.5,.5,1,2):
   rr=np.linspace(0,30,401);gg=[m.reflection(50*complex(r,x),50) for r in rr];ax.plot([g.real for g in gg],[g.imag for g in gg],color='gray',lw=.6)
  points=[(0,'short',(-.95,.1)),(None,'open',(.7,.1)),(50,'50',(-.06,.1)),(100,'100',(.4,.1)),(25,'25',(-.5,.1)),(50j,'+j50',(.1,.9)),(-50j,'-j50',(.1,-.95))];results['smith_points']=[]
  for z,label,pos in points:
   g=m.reflection(z,50);ax.plot(g.real,g.imag,'ko');ax.text(*pos,label,fontsize=13);results['smith_points'].append({'load':str(z),'Gamma':[g.real,g.imag]})
  arc=[m.reflection(100,50)*complex(math.cos(-2*t),math.sin(-2*t)) for t in np.linspace(0,math.pi/2,101)];ax.plot([g.real for g in arc],[g.imag for g in arc],'--',lw=2,label='100 ohm: toward source lambda/4');ax.legend(fontsize=10,loc='upper left');ax.set(xlim=(-1.13,1.13),ylim=(-1.13,1.13),xlabel='Re Gamma',ylabel='Im Gamma');f.suptitle('Smith mapping: z=(1+Gamma)/(1-Gamma), real reference50ohm');save(f,'03-smith')
  f,ax=two();chain=[[10,2],[4,5]];results['NF']=m.friis_noise(chain);ax[0].bar(['LNA F1','stage2 / G1'],[2,.4],color=['#4477aa','#ee7733']);ax[0].set(ylabel='linear noise factor terms');ax[0].set_title('LNA G1=10,F1=2; same-frequency stage F2=5: Ftotal=2.4')
  amps=np.logspace(-3,math.log10(.8),180);pin=amps**2/100;fund=[2*a-.75*a**3 for a in amps];twofund=[2*a-2.25*a**3 for a in amps];im3=[.75*a**3 for a in amps];to_db=lambda v:10*np.log10(v/.001)
  ax[1].plot(to_db(pin),to_db(np.array(fund)**2/100),label='single tone fundamental');ax[1].plot(to_db(pin),to_db(np.array(im3)**2/100),'--',label='two-tone IM3');ax[1].plot(to_db(pin),to_db(4*pin),':',label='small-signal extrapolation');ax[1].set(xlabel='input dBm per tone, R50ohm',ylabel='output dBm per line');ax[1].legend(fontsize=10);f.suptitle('Different tests: single-tone compression / two-tone intercept');save(f,'04-rf-budget');results['cubic']=m.cubic_metrics(2,-1);results['IQ_10percent']=m.iq_image(1.1,0)
  f,ax=two();skews=np.linspace(0,100e-12,201);modes=[m.differential_skew(.5,1e9,float(t),0) for t in skews];ax[0].plot(skews*1e12,[abs(v['Vdiff_peak']) for v in modes],label='difference peak');ax[0].plot(skews*1e12,[abs(v['Vcommon_peak']) for v in modes],'--',label='common peak');ax[0].set(xlabel='leg skew ps: f=1GHz, each leg .5V',ylabel='V');ax[0].legend(fontsize=10)
  bits=([1,-1,1,1,-1,-1,1,-1,-1,-1,1,1,1,-1,1,-1]*8);ey=m.eye_record(bits,1e-9,.25e-9,32);samples=ey['samples_V']
  for start in range(8*32,(len(bits)-2)*32,32):ax[1].plot([(j+1)/32 for j in range(64)],samples[start:start+64],color='#4477aa',alpha=.18)
  ax[1].set(xlabel='time UI (samples at (n+1)dt)',ylabel='received V',xlim=(0,2));ax[1].set_title('Finite deterministic NRZ through exact single pole, tau=.25UI');f.suptitle('Skew conversion and ISI are distinct mechanisms');save(f,'05-eye-mode');results['eye']={'bits':bits,'last_V':samples[-1],'initial_V':0,'tau_s':.25e-9,'UI_s':1e-9}
  f,ax=two();a=ax[0];a.axis('off');a.set(xlim=(0,10),ylim=(0,5));a.plot([1,9],[4,4],'k');a.plot([1,9],[.6,.6],'k');a.text(8.8,4.2,'IC power p');a.text(8.4,.1,'IC return 0')
  for x,label in [(1,'source + Rs/Ls'),(4,'ESR / ESL / C1'),(7,'ESR / ESL / C2')]:
   a.plot([x,x],[.6,4],'k');a.text(x,2.3,label,ha='center',rotation=90,fontsize=12,bbox={'facecolor':'white','edgecolor':'black'});a.plot([x,x],[4,.6],'ko',ms=3)
  a.text(5,4.7,'All branches connect p-0; small-signal supply reference',ha='center',fontsize=12)
  ff=np.logspace(5,9,401);zz=[m.pdn_impedance(float(fr),PARAMETERS['PDN_branches_C_ESR_ESL']) for fr in ff]
  for j,style in enumerate(['--',':']):ax[1].loglog(ff,[abs(v['branch_Z_ohm'][j]) for v in zz],ls=style,label='branch '+str(j+1))
  ax[1].loglog(ff,[abs(v['Z_ohm']) for v in zz],label='total with source .1ohm/10nH');ax[1].axhline(.1,color='black',ls='-.',label='screen target .1ohm');ax[1].set(xlabel='frequency Hz',ylabel='impedance ohm');ax[1].legend(fontsize=9);f.suptitle('Real C branches: .02ohm ESR,1nH ESL; 100nF and1nF');save(f,'06-pdn');results['PDN_at_113MHz']=m.pdn_impedance(113.100837e6,PARAMETERS['PDN_branches_C_ESR_ESL'])
  f,ax=two();a=ax[0];a.set(xlim=(0,10),ylim=(0,6));a.axis('off')
  for left,title,slot in [(.2,'Continuous reference',False),(5.2,'Reference with slot',True)]:
   a.add_patch(Rectangle((left,1),4.5,3.3,facecolor='#dddddd',edgecolor='black'));a.text(left,4.8,title,fontsize=13)
   if slot:a.add_patch(Rectangle((left+2.1,1),.3,3.3,facecolor='white',edgecolor='black'))
   arrow(a,(left+.3,3.7),(left+4.2,3.7));a.text(left+.3,4,'L1 signal +i',fontsize=11)
   if slot:
    a.plot([left+4.2,left+2.6,left+2.6,left+1.9,left+1.9,left+.3],[3.1,3.1,.7,.7,3.1,3.1],'k--');arrow(a,(left+1.9,3.1),(left+.3,3.1))
   else:arrow(a,(left+4.2,3.1),(left+.3,3.1))
   a.text(left+.2,1.6,'L2 return -i',fontsize=11)
  a.text(.3,.1,'Same forward trace; slot detour enlarges loop (schematic)',fontsize=12)
  a=ax[1];a.axis('off');a.set(xlim=(0,10),ylim=(0,5))
  for y,label in [(4,'L1 signal'),(3,'L2 reference 0'),(2,'L3 power'),(1,'L4 slow signal')]:a.plot([.5,9.5],[y,y],'k');a.text(.6,y+.1,label,fontsize=12)
  a.plot([5.3,5.3,5.7],[2,4.5,4.5],'k');a.plot([6.3,6.7,6.7],[4.5,4.5,3],'k')
  a.plot([5.7,5.7],[4.15,4.85],'k',lw=2);a.plot([6.3,6.3],[4.15,4.85],'k',lw=2);a.text(6,4.95,'C',ha='center',fontsize=12)
  a.plot([8.7,8.7],[2,3],'k',lw=2);a.text(8.7,2.5,'IC load',ha='center',fontsize=11,bbox={'facecolor':'white','edgecolor':'black'})
  a.plot([5.3,6.7,8.7,8.7],[2,3,2,3],'ko',ms=4);arrow(a,(6.9,2),(8.3,2));arrow(a,(8.3,3),(7,3));a.text(4,.25,'C -> power via -> IC -> return via -> C',fontsize=11)
  f.suptitle('L1/L2/L3/L4 teaching stack; 100ps edge, 0.1m T=.5ns');save(f,'07-return')
  f=Figure(figsize=(8,7),layout='constrained');grid=f.add_gridspec(2,2);a=f.add_subplot(grid[0,:],projection='3d');theta=np.linspace(0,math.pi,41);phi=np.linspace(0,2*math.pi,61);tt,pp=np.meshgrid(theta,phi);u=np.sin(tt)**2;x=u*np.sin(tt)*np.cos(pp);y=u*np.sin(tt)*np.sin(pp);z=u*np.cos(tt);a.plot_surface(x,y,z,color='#4477aa',alpha=.65,rstride=3,cstride=3,edgecolor='gray',linewidth=.3);a.set(xlabel='x',ylabel='y',zlabel='z',title='Radius = normalized POWER sin²theta; z-axis dipole');a.set_box_aspect((1,1,.6))
  ang=np.linspace(0,2*math.pi,361);a=f.add_subplot(grid[1,0],projection='polar');a.plot(ang,np.sin(ang)**2);a.set_theta_zero_location('N');a.set_theta_direction(-1);a.set(title='xz: angle from +z',rlim=(0,1.1));a.set_rticks([.5,1])
  a=f.add_subplot(grid[1,1],projection='polar');a.plot(ang,np.ones_like(ang),'--');a.set_theta_zero_location('E');a.set_theta_direction(1);a.set(title='xy: phi from +x to +y',rlim=(0,1.1));a.set_rticks([.5,1]);f.suptitle('Direction pattern, not field amplitude or real-space distance');save(f,'08-antenna-pattern');results['link']=m.friis_link(.1,1.5,1.5,1e9,10)
 def serialize(v):
  if isinstance(v,complex):return {'re':v.real,'im':v.imag}
  if isinstance(v,dict):return {k:serialize(x) for k,x in v.items()}
  if isinstance(v,(list,tuple)):return [serialize(x) for x in v]
  return v
 (data/'parameters.json').write_text(json.dumps(PARAMETERS,indent=2)+'\n');(data/'results.json').write_text(json.dumps(serialize(results),indent=2)+'\n')
 return results

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();generate(args.output)
if __name__=='__main__':main()
