"""Editable deterministic vector circuits and CPU plots. Import is inert."""
from pathlib import Path
import math,json,csv,argparse,html
from dataclasses import asdict,replace
from power_models import Params,buck_summary,simulate,losses,thermal,buck_gvd,boost_gvd,pwm_phases,state_matrices,design_candidates
MAIN=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
class SVG:
 def __init__(self,title,h=430):
  self.h=h;self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}"><rect width="420" height="{h}" fill="white"/><g fill="none" stroke="#161616" stroke-width="2" stroke-linejoin="round">'];self.text(14,25,title,17)
 def line(self,x,y,u,v,**attrs):self.parts.append(f'<line x1="{x}" y1="{y}" x2="{u}" y2="{v}" '+ ' '.join(f'{k.replace("_","-")}="{v}"' for k,v in attrs.items())+'/>' )
 def poly(self,pts,fill='none'):self.parts.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{fill}"/>')
 def text(self,x,y,t,size=14):self.parts.append(f'<text x="{x}" y="{y}" stroke="none" fill="#111" font-family="DejaVu Sans,sans-serif" font-size="{size}">{html.escape(t)}</text>')
 def dot(self,x,y):self.parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>')
 def res(self,x,y,u,v,label):
  dx=u-x;dy=v-y;n=math.hypot(dx,dy);nx=-dy/n;ny=dx/n;pts=[(x,y)]
  for k in range(1,8):
   z=k/8;off=(1 if k%2 else -1)*5;pts.append((x+z*dx+off*nx,y+z*dy+off*ny))
  pts.append((u,v));self.poly(pts);self.text((x+u)/2+8,(y+v)/2+18,label)
 def cap(self,x,y,u,v,label):
  dx=u-x;dy=v-y;n=math.hypot(dx,dy);nx=-dy/n;ny=dx/n;mx=(x+u)/2;my=(y+v)/2
  for off in (-4,4):self.line(mx+off*dx/n-10*nx,my+off*dy/n-10*ny,mx+off*dx/n+10*nx,my+off*dy/n+10*ny)
  self.line(x,y,mx-4*dx/n,my-4*dy/n);self.line(mx+4*dx/n,my+4*dy/n,u,v);self.text(mx+13,my+19,label)
 def coil(self,x,y,u,v,label):
  dx=u-x;dy=v-y;n=math.hypot(dx,dy);nx=-dy/n;ny=dx/n;pts=[]
  for k in range(65):
   t=k/64;off=8*abs(math.sin(t*4*math.pi));pts.append((x+t*dx+off*nx,y+t*dy+off*ny))
  self.poly(pts);self.text((x+u)/2+12,(y+v)/2-14,label)
 def diode(self,x,y,u,v,label):
  dx=u-x;dy=v-y;n=math.hypot(dx,dy);ex=dx/n;ey=dy/n;nx=-ey;ny=ex;mx=(x+u)/2;my=(y+v)/2
  self.line(x,y,mx-9*ex,my-9*ey);self.poly([(mx-9*ex+9*nx,my-9*ey+9*ny),(mx+7*ex,my+7*ey),(mx-9*ex-9*nx,my-9*ey-9*ny),(mx-9*ex+9*nx,my-9*ey+9*ny)])
  self.line(mx+8*ex-10*nx,my+8*ey-10*ny,mx+8*ex+10*nx,my+8*ey+10*ny);self.line(mx+8*ex,my+8*ey,u,v);self.text(mx+12,my+18,label)
 def switch(self,x,y,u,v,on,label):
  dx=u-x;dy=v-y;n=math.hypot(dx,dy);ex=dx/n;ey=dy/n;nx=-ey;ny=ex
  a=(x+dx*.3,y+dy*.3);b=(x+dx*.7,y+dy*.7);self.line(x,y,*a);self.line(*b,u,v);self.dot(*a);self.dot(*b);self.line(*a,b[0]+(0 if on else 10*nx),b[1]+(0 if on else 10*ny));self.text((x+u)/2+8,(y+v)/2-14,label)
 def ground(self,x,y,name='0'):self.line(x,y,x,y+8);self.line(x-10,y+8,x+10,y+8);self.line(x-6,y+13,x+6,y+13);self.text(x+14,y+15,name)
 def source(self,x,y,u,v,label):
  self.line(x,y,x,(y+v)/2-18);self.line(x,(y+v)/2+18,u,v);self.parts.append(f'<circle cx="{x}" cy="{(y+v)/2}" r="18"/>');self.text(x-5,(y+v)/2-3,'+');self.text(x-5,(y+v)/2+13,'−');self.text(x-23,y-12,label)
 def finish(self):return ''.join(self.parts)+'</g></svg>\n'
def buck_states():
 s=SVG('Buck: three conduction states',950)
 for k,(on,title) in enumerate([(True,'ON: q=1; S on, D blocked'),(False,'OFF: q=0; diode carries iL'),(False,'IDLE: S/D blocked; iL=0')]):
  y=80+k*295;s.text(15,y-25,title);s.source(40,y,40,y+160,'12 V');s.line(40,y,75,y);s.switch(75,y,165,y,on,'S');s.dot(170,y);s.line(165,y,180,y);s.coil(180,y,260,y,'100 µH');s.line(260,y,365,y);s.dot(285,y);s.dot(365,y);s.cap(285,y,285,y+160,'100 µF');s.res(365,y+25,365,y+135,'R');s.line(365,y,365,y+25);s.line(365,y+135,365,y+160);s.line(40,y+160,365,y+160);s.line(170,y,170,y+30);s.diode(170,y+125,170,y+30,'D');s.line(170,y+125,170,y+160);s.dot(170,y+160);s.ground(40,y+160);s.text(180,y+25,'SW');s.text(310,y-12,'OUT +v');s.text(225,y+30,'iL ->');s.text(15,y+215,['L di/dt = 12−v; C dv/dt = i−v/R','L di/dt = −v; C dv/dt = i−v/R','SW=v (ideal float); C dv/dt = −v/R'][k])
 s.text(14,934,'0: common return; dots join; q = conduction');return s

def ldo():
 s=SVG('LDO: pass path, reference and feedback',430);s.source(35,75,35,285,'Vin');s.line(35,75,100,75);s.line(100,75,200,75);s.line(120,90,180,90);s.line(120,99,180,99);s.line(150,99,150,110);s.text(115,60,'pass Q');s.line(200,75,380,75);s.dot(230,75);s.dot(300,75);s.cap(230,75,230,175,'C');s.res(230,175,230,250,'ESR');s.line(230,250,230,285);s.res(300,95,300,155,'Rt');s.line(300,75,300,95);s.line(300,155,300,200);s.dot(300,180);s.res(300,200,300,260,'Rb');s.line(300,260,300,285);s.res(380,110,380,250,'RL');s.line(380,75,380,110);s.line(380,250,380,285);s.line(35,285,380,285);s.ground(35,285);s.poly([(110,140),(110,230),(185,185),(110,140)]);s.text(114,163,'+');s.text(114,214,'−');s.line(300,180,210,180);s.line(210,180,210,220);s.line(210,220,110,220);s.line(185,185,195,185);s.line(195,185,195,110);s.line(195,110,150,110);s.dot(150,110);s.text(152,237,'drive');s.line(145,161,145,130);s.line(145,130,90,130);s.line(90,130,90,75);s.dot(90,75);s.text(95,121,'V+');s.line(145,209,145,250);s.line(145,250,100,250);s.line(100,250,100,285);s.dot(100,285);s.text(105,269,'V−');s.line(80,150,110,150);s.source(80,150,80,285,'Vref');s.dot(80,285);s.text(315,60,'OUT');s.text(14,352,'FB=OUT × Rb/(Rt+Rb); capacitor includes ESR');s.text(14,382,'Reference and amplifier require real supply/return');return s

def driver():
 s=SVG('High-side drive: referenced to source SW',470);s.line(250,65,250,105);s.text(250,53,'+12 V');s.line(250,105,250,185);s.line(233,115,233,175);s.line(220,105,220,185);s.line(220,145,165,145);s.text(262,117,'D');s.text(262,185,'S = SW');s.text(198,139,'G');s.line(250,185,250,230);s.dot(250,215);s.coil(250,230,340,230,'L');s.line(340,230,380,230);s.res(380,230,380,330,'RL');s.line(380,330,250,330);s.diode(250,330,250,235,'freewheel');s.ground(250,330);s.parts.append('<rect x="50" y="100" width="75" height="90"/>');s.text(58,125,'driver');s.text(58,154,'VDDf');s.text(60,180,'RETf');s.line(125,145,140,145);s.res(140,145,165,145,'Rg');s.line(87,190,87,215);s.line(87,215,250,215);s.source(35,70,35,215,'Vf');s.line(35,70,85,70);s.line(85,70,85,100);s.line(35,215,87,215);s.dot(87,215);s.text(14,370,'RETf follows SW; drive is G−S, not G−0');s.text(14,400,'Qg supplied each cycle; Cgd creates Miller interval');s.text(14,435,'Device/SOA and isolated or bootstrap supply differ');return s

def others():
 s=SVG('Boost and inverting buck-boost: actual returns',720)
 y=95;s.source(40,y,40,y+185,'Vin');s.line(40,y,85,y);s.coil(85,y,170,y,'L');s.line(170,y,205,y);s.dot(205,y);s.diode(205,y,310,y,'D A->K');s.line(310,y,370,y);s.cap(320,y,320,y+185,'C');s.res(370,y+35,370,y+145,'RL');s.line(370,y,370,y+35);s.line(370,y+145,370,y+185);s.switch(205,y,205,y+185,False,'S');s.line(40,y+185,370,y+185);s.ground(40,y+185);s.text(320,y-20,'OUT +');s.text(14,327,'ON: L sees Vin; OUT supplied only by C')
 y=440;s.source(40,y,40,y+180,'Vin');s.line(40,y,65,y);s.switch(65,y,150,y,True,'S');s.line(150,y,180,y);s.dot(180,y);s.coil(180,y,180,y+180,'L');s.diode(330,y,180,y,'D: A at OUT');s.line(330,y,375,y);s.cap(330,y,330,y+180,'C');s.res(375,y+35,375,y+145,'RL');s.line(375,y,375,y+35);s.line(375,y+145,375,y+180);s.line(40,y+180,375,y+180);s.ground(40,y+180);s.text(314,y-25,'OUT −u');s.text(14,684,'ON stores; OFF returns via negative OUT');return s

def flyback():
 s=SVG('Flyback: separate returns; storage in Lm',470);s.source(40,90,40,285,'12 V');s.line(40,90,135,90);s.coil(135,90,135,180,'Np, Lm');s.dot(125,96);s.switch(135,180,135,285,True,'S');s.line(40,285,135,285);s.ground(40,285,'0p');s.coil(235,90,235,180,'Ns');s.dot(225,174);s.line(235,180,235,285);s.line(235,285,375,285);s.line(235,90,255,90);s.diode(255,90,340,90,'D');s.line(340,90,375,90);s.cap(340,90,340,285,'C');s.res(375,130,375,245,'RL');s.line(375,90,375,130);s.line(375,245,375,285);s.ground(235,285,'0s');s.text(270,70,'OUT +');s.line(175,95,175,175);s.line(185,95,185,175);s.text(14,360,'Dots: primary top / secondary bottom');s.text(14,391,'ON blocks D; OFF delivers Lm energy to secondary');s.text(14,422,'No wire between 0p and 0s; leakage is separate');return s

def forward():
 s=SVG('Forward: transmit ON / reset flux OFF',520);s.source(30,70,30,300,'Vin');s.line(30,70,145,70);s.coil(145,70,145,180,'Np');s.dot(135,75);s.switch(145,180,145,300,True,'S');s.line(30,300,145,300);s.ground(30,300,'0p');s.coil(85,130,85,230,'Nr');s.dot(75,225);s.line(85,230,85,300);s.dot(85,300);s.line(85,130,85,110);s.diode(85,110,85,70,'Dr');s.dot(85,70);s.coil(245,70,245,175,'Ns');s.dot(235,75);s.line(245,175,245,300);s.line(245,300,390,300);s.diode(245,70,315,70,'D1');s.dot(315,70);s.coil(315,70,390,70,'Lo');s.cap(355,70,355,300,'Co');s.res(390,115,390,255,'RL');s.line(390,70,390,115);s.line(390,255,390,300);s.line(315,70,315,145);s.diode(315,245,315,145,'D2');s.line(315,245,315,300);s.dot(315,300);s.ground(245,300,'0s');s.text(14,366,'Nr dot at 0p; Dr anode at top, cathode at Vin');s.text(14,398,'Np=Nr: reset voltage −Vin; ideal D ≤ 0.5');s.text(14,430,'D1 sends power ON; D2 freewheels output OFF');s.text(14,465,'Magnetic coupling is not a conducting connection');return s

def rectifier():
 s=SVG('Full-wave bridge: four unidirectional paths',430);s.diode(70,180,210,70,'Dap');s.diode(350,180,210,70,'Dbp');s.diode(210,290,70,180,'Dna');s.diode(210,290,350,180,'Dnb');s.line(70,180,40,180);s.line(350,180,365,180);s.text(22,163,'a');s.text(365,163,'b');s.dot(210,70);s.dot(210,290);s.line(210,70,410,70);s.line(210,290,410,290);s.res(390,110,390,250,'R');s.line(410,70,390,70);s.line(390,70,390,110);s.line(390,250,390,290);s.line(390,290,410,290);s.text(218,55,'p +');s.text(218,321,'n −');s.text(14,370,'a>b: a -> Dap -> load -> Dnb -> b');s.text(14,400,'b>a: b -> Dbp -> load -> Dna -> a');return s

def inverter(three=False):
 s=SVG('Three-phase: floating star point N' if three else 'Full bridge: two legs, inductive load',570 if three else 470)
 xs=[70,200,330] if three else [80,280]
 s.line(30,70,390,70);s.line(30,260,390,260);s.text(14,55,'p = +12 V');s.text(14,286,'n = 0');s.ground(30,260)
 for k,x in enumerate(xs):
  s.switch(x,70,x,155,False,'H'+str(k));s.switch(x,155,x,260,False,'L'+str(k));s.dot(x,155)
  s.line(x+38,70,x+38,100);s.diode(x+38,155,x+38,100,'');s.line(x+38,70,x,70);s.line(x+38,155,x,155)
  s.line(x+38,260,x,260);s.diode(x+38,260,x+38,155,'');s.text(x-14,150,'ABC'[k])
 if three:
  for k,x in enumerate(xs):
   s.line(x,155,x+20,155);s.line(x+20,155,x+20,300);s.coil(x+20,300,x+20,405,'phase');s.line(x+20,405,x+20,440)
  s.line(90,440,350,440);s.dot(220,440);s.text(228,465,'N (no ground wire)');s.text(14,510,'iA+iB+iC=0; phase mean uses floating N');s.text(14,540,'H/L interlock and current sample are external duties')
 else:
  s.line(80,155,80,340);s.line(280,155,280,340);s.res(80,340,145,340,'R');s.coil(145,340,220,340,'L');s.parts.append('<circle cx="250" cy="340" r="18"/>');s.text(236,344,'+');s.text(255,344,'−');s.text(244,315,'e');s.line(220,340,232,340);s.line(268,340,280,340)
  # source must be horizontal here; overwrite last vertical source using explicit original circle only is handled below.
  s.text(14,405,'vAB=(qA−qB)Vdc; L di/dt=vAB−Ri−e');s.text(14,439,'Reverse paths remain when gates are OFF')
 return s

def loop():
 s=SVG('Buck: measured OUT closes the sampled loop',710)
 s.source(35,75,35,230,'12 V');s.line(35,75,70,75);s.switch(70,75,145,75,True,'S');s.line(145,75,160,75);s.dot(145,75);s.coil(160,75,245,75,'100 µH');s.line(245,75,365,75);s.dot(285,75);s.cap(285,75,285,230,'');s.text(185,155,'C=100 µF');s.res(365,100,365,205,'');s.text(335,255,'10 Ω');s.line(365,75,365,100);s.line(365,205,365,230);s.line(35,230,365,230);s.ground(35,230);s.diode(145,200,145,110,'D');s.line(145,75,145,110);s.line(145,200,145,230);s.dot(145,230);s.text(307,55,'OUT +v')
 # Ideal high-impedance two-terminal voltage measurement, unit gain. Dashed edges are signals.
 s.line(325,75,325,139);s.parts.append('<circle cx="325" cy="155" r="16"/>');s.text(320,160,'V');s.line(325,171,325,230);s.dot(325,75);s.dot(325,230)
 s.line(341,155,405,155,stroke_dasharray='5 4');s.line(405,155,405,280,stroke_dasharray='5 4');s.line(405,280,70,280,stroke_dasharray='5 4');s.line(70,280,70,330,stroke_dasharray='5 4');s.poly([(65,320),(70,330),(75,320)]);s.text(90,270,'sample v[k], high-Z; gain = 1')
 for x,w,t in [(20,100,'5−v [V]'),(155,110,'K / clamp'),(300,100,'PWM q')]:
  s.parts.append(f'<rect x="{x}" y="330" width="{w}" height="50"/>');s.text(x+6,360,t)
 s.line(120,355,155,355);s.line(265,355,300,355)
 s.line(350,380,350,440,stroke_dasharray='5 4');s.line(350,440,5,440,stroke_dasharray='5 4');s.line(5,440,5,95,stroke_dasharray='5 4');s.line(5,95,105,95,stroke_dasharray='5 4');s.poly([(100,95),(105,85),(110,95)]);s.text(14,465,'q changes S; not a power connection')
 s.text(14,492,'Solid network: energy paths; dashed: signals');s.text(14,527,'One voltage sample and duty update per T');s.text(14,562,'Aon=Aoff, but Bon differs from Boff');s.text(14,597,'Continuous average omits switching ripple');s.text(14,632,'Duty clamps to [.05,.95]; CPU uses K=.01 /V');s.text(14,667,'No PI firmware or real ADC latency verified');return s

def llc():
 s=SVG('LLC: three states and isolated rectifier',890);s.line(40,70,80,70);s.text(15,54,'+12 V');s.switch(80,70,80,165,False,'S1');s.switch(80,165,80,310,False,'S2');s.line(40,310,305,310);s.ground(40,310,'0p');s.dot(80,165);s.cap(80,165,160,165,'Cr');s.coil(160,165,235,165,'Lr');s.line(235,165,305,165);s.dot(245,165);s.coil(245,165,245,310,'Lm');s.coil(305,165,305,270,'Np');s.line(305,270,305,310);s.dot(295,170);s.coil(350,165,350,270,'Ns');s.dot(340,170);s.line(350,165,390,165);s.line(350,270,390,270);s.text(389,151,'a');s.text(389,293,'b');s.text(14,362,'a,b are the same named secondary nets below');s.text(14,397,'fr=1/[2π√(Lr Cr)] [Hz]');s.text(14,426,'fm=1/[2π√((Lr+Lm) Cr)] [Hz]')
 s.diode(55,620,170,500,'Dap');s.diode(285,620,170,500,'Dbp');s.diode(170,740,55,620,'Dna');s.diode(170,740,285,620,'Dnb');s.text(25,620,'a');s.text(282,600,'b');s.dot(170,500);s.dot(170,740);s.line(170,500,380,500);s.line(170,740,380,740);s.cap(325,500,325,740,'Co');s.res(380,545,380,700,'RL');s.line(380,500,380,545);s.line(380,700,380,740);s.ground(170,740,'0s');s.text(325,485,'OUT');s.text(14,809,'FHA uses effective reflected Re, not bare RL');s.text(14,846,'ZVS: direction + charge + energy + time');return s

def zvs():
 s=SVG('Dead time: charge transfer and fast trip',520);s.line(50,70,190,70);s.text(20,55,'p +12 V');s.switch(95,70,95,170,False,'H');s.switch(95,170,95,290,False,'L');s.cap(165,70,165,170,'Coss H');s.cap(165,170,165,290,'Coss L');s.line(95,170,290,170);s.dot(165,170);s.coil(290,170,370,170,'tank L');s.cap(370,170,370,290,'Cr');s.line(190,290,370,290);s.line(95,70,165,70);s.line(50,290,190,290);s.ground(50,290);s.text(190,205,'i -> moves Qoss');s.text(14,346,'During dead time H=L=OFF; current persists');s.parts.append('<rect x="20" y="375" width="155" height="45"/><rect x="235" y="375" width="160" height="45"/>');s.text(27,402,'sense i > limit');s.text(242,402,'independent OFF');s.line(175,398,235,398);s.text(14,458,'Delay adds Δi ≈ Vin × tdelay / L');s.text(14,492,'Expected condition only; no device trip measurement');return s

def hot():
 s=SVG('Buck differential hot loop and sense return',460);s.cap(55,80,55,280,'Cin');s.line(55,80,170,80);s.switch(170,80,170,170,True,'H');s.switch(170,170,170,280,False,'L/D');s.line(55,280,390,280);s.dot(170,170);s.coil(170,170,290,170,'L');s.line(290,170,390,170);s.cap(310,170,310,280,'Cout');s.res(390,170,390,280,'RL');s.ground(55,280);s.parts.append('<rect x="30" y="60" width="170" height="240" stroke-dasharray="6 4"/>');s.text(210,90,'hot-loop envelope');s.text(14,350,'Cin <-> H/L: pulsed difference current');s.text(14,383,'OUT sense: quiet node, not SW');s.text(14,416,'Envelope is geometry; no extra electrical wire');return s

def _generate(output):
 out=Path(output).expanduser().resolve()
 if out==MAIN or MAIN in out.parents:raise ValueError('output must be outside main vault')
 if out==Path(__file__).resolve().parent or Path(__file__).resolve().parent in out.parents:raise ValueError('output must be outside source subtree')
 # Heavy dependencies occur only after explicit validated output.
 import cairosvg
 from matplotlib.figure import Figure
 from matplotlib.backends.backend_agg import FigureCanvasAgg
 from matplotlib import rc_context
 p=Params();s=buck_summary(p);dc=buck_summary(replace(p,r=100));rows=simulate(p,2000,32);drows=simulate(replace(p,r=100),500,32,initial=(0,dc['v_V']));av=simulate(p,400,32,initial=(.49,4.95),average=True,control_k=.01);sw=simulate(p,400,32,initial=(.49,4.95),control_k=.01)
 comparison={'initial_i_A':.49,'initial_v_V':4.95,'cycles':400,'steps_per_interval':32,'control_K_per_V':.01,'instantaneous_vs_averaged_initial':'equal numerical states, not phase-matched cycle means','switched_min_i_A':min(z['i_A'] for z in sw),'averaged_min_i_A':min(z['i_A'] for z in av),'idle_records':sum('idle' in z['mode'] for z in sw),'observed_max_cycle_endpoint_v_difference_V':max(abs(x['v_V']-y['v_V']) for x,y in zip(sw[::64],av[::64])),'scope':'finite mode check, not averaging error bound or global stability proof'}
 if comparison['idle_records'] or min(comparison['switched_min_i_A'],comparison['averaged_min_i_A'])<=0:raise ArithmeticError('comparison leaves declared CCM domain')
 out.mkdir(parents=True,exist_ok=True)
 circuits={'ldo':ldo(),'driver':driver(),'buck-states':buck_states(),'boost-inverting':others(),'flyback':flyback(),'forward':forward(),'rectifier':rectifier(),'inverter':inverter(),'three-phase':inverter(True),'average-loop':loop(),'llc':llc(),'zvs-protection':zvs(),'hot-loop':hot()}
 for name,svg in circuits.items():
  text=svg.finish();(out/(name+'.svg')).write_text(text)
  for width in (360,425):cairosvg.svg2png(bytestring=text.encode(),write_to=str(out/f'{name}-{width}.png'),output_width=width)
 with rc_context({'font.size':14,'svg.hashsalt':'wwl-power1','font.family':'DejaVu Sans','axes.grid':True}):
  def plot(name,panels):
   fig=Figure(figsize=(4.2,2.8*len(panels)),dpi=100);FigureCanvasAgg(fig)
   for k,(title,xlabel,ylabel,curves) in enumerate(panels):
    ax=fig.add_subplot(len(panels),1,k+1)
    for x,y,label,style in curves:ax.plot(x,y,style,label=label,linewidth=1.5)
    
    if 'ω' in xlabel:ax.set_xscale('log')
    ax.set_title(title,fontsize=14);ax.set_xlabel(xlabel);ax.set_ylabel(ylabel);ax.legend(fontsize=12,loc='best')
   fig.tight_layout();fig.savefig(out/(name+'.svg'),metadata={'Date':None})
   # Native width 420 px; use renderer SVG for fixed preview sizes.
   for w in (360,425):cairosvg.svg2png(url=str(out/(name+'.svg')),write_to=str(out/f'{name}-{w}.png'),output_width=w)
  def trace(rr,key,last):
   z=rr[-last:];t0=z[0]['t_s'];return [(a['t_s']-t0)*1e6 for a in z],[a[key] for a in z]
  a,b=trace(rows,'i_A',129);c,d=trace(rows,'v_V',129);e,f=trace(drows,'i_A',129);g,h=trace(drows,'v_V',129)
  plot('buck-waves',[('CCM: R=10 Ω','time [µs]','iL [A]',[(a,b,'switched','-')]),('Same L/C/fs and duty','time [µs]','vC [V]',[(c,d,'ESR=0','-')])])
  plot('boundary',[('DCM: R=100 Ω','time [µs]','iL [A]',[(e,f,'zero interval','-')]),('Same duty, different load','time [µs]','vC [V]',[(g,h,'DCM output','-')])])
  plot('average-comparison',[
   ('CCM check; K=.01 [1/V]','time [ms]','v [V]',[([z['t_s']*1e3 for z in sw[::16]],[z['v_V'] for z in sw[::16]],'switched','-'),([z['t_s']*1e3 for z in av[::16]],[z['v_V'] for z in av[::16]],'average','--')]),
   ('Equal numerical x0: .49 A, 4.95 V','time [ms]','iL [A]',[([z['t_s']*1e3 for z in sw[::16]],[z['i_A'] for z in sw[::16]],'instantaneous','-'),([z['t_s']*1e3 for z in av[::16]],[z['i_A'] for z in av[::16]],'averaged','--')])])
  times=[k for k in range(101)];plot('thermal',[('System thermal RC','time [s]','T [°C]',[(times,[thermal(t,.7006) for t in times],'LDO .7006 W','-'),(times,[thermal(t,.1) for t in times],'one .1 W node','--')])])
  ws=[10**(2+k*5/150) for k in range(151)];gs=[buck_gvd(p,w) for w in ws];bp=replace(p,d=.4,r=40);bs=[boost_gvd(bp,w) for w in ws]
  plot('control-response',[('Different CCM plants','ω [rad/s]','magnitude [dB]',[(ws,[20*math.log10(abs(z)) for z in gs],'Buck','-'),(ws,[20*math.log10(abs(z)) for z in bs],'Boost','--')])])
 values={'identity':'synthetic CPU; ideal switching separate from loss estimate; not SPICE or measured','comparison_CCM':comparison,'design_candidates':design_candidates(),'params_SI':asdict(p),'ccm':s,'dcm_R100':dc,'loss_estimate':losses(p),'buck_matrices':state_matrices(p),'boost_matrices':state_matrices(replace(p,d=.4,r=40),'boost'),'three_phase_at_pi_over_2':pwm_phases(math.pi/2)}
 (out/'parameters.json').write_text(json.dumps(values,indent=2,ensure_ascii=False)+'\n')
 with (out/'waveforms.csv').open('w',newline='') as handle:
  writer=csv.writer(handle);writer.writerow(['case','t_s','i_A','v_V','mode','d'])
  for label,data in [('CCM',rows[-129:]),('DCM',drows[-129:]),('switched_step',sw[::16]),('average_step',av[::16])]:
   for z in data:writer.writerow([label,z['t_s'],z['i_A'],z['v_V'],z['mode'],z['d']])
 return values

def generate(output):
 import tempfile,os
 out=Path(output).expanduser().resolve();source=Path(__file__).resolve().parent
 if out==MAIN or MAIN in out.parents or out==source or source in out.parents:raise ValueError('new output must be outside main and source subtree')
 previous={k:os.environ.get(k) for k in ('MPLCONFIGDIR','XDG_CACHE_HOME')}
 try:
  with tempfile.TemporaryDirectory(prefix='wwl-power-render-') as cache:
   os.environ['MPLCONFIGDIR']=cache+'/mpl';os.environ['XDG_CACHE_HOME']=cache+'/xdg'
   return _generate(out)
 finally:
  for k,v in previous.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();generate(args.output)
if __name__=='__main__':main()
