"""Explicit output-only build. SVG source remains editable; dependencies are lazy."""
import argparse
import json
from pathlib import Path
import math
import models

def output_path(p):
    p=Path(p).expanduser().resolve(); here=Path(__file__).resolve().parent
    forbidden=[Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL'),here,*[q for q in here.parents if (q/'AGENTS.md').exists()]]
    for q in forbidden:
        if p==q or q in p.parents: raise ValueError('output must be outside candidate/vault')
    return p

class SVG:
    def __init__(self,title): self.a=['<svg xmlns="http://www.w3.org/2000/svg" width="425" height="360" viewBox="0 0 425 360"><rect width="425" height="360" fill="white"/>']; self.text(14,22,title,14)
    def line(self,x1,y1,x2,y2): self.a.append(f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="#222" stroke-width="1.5"/>')
    def text(self,x,y,t,size=11): self.a.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#222">{t}</text>')
    def node(self,x,y,label=''): self.a.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="#222"/>'); self.text(x+5,y-5,label) if label else None
    def ground(self,x,y):
        self.line(x,y,x,y+6)
        for k in range(3): self.line(x-8+3*k,y+6+4*k,x+8-3*k,y+6+4*k)
    def resistor(self,x1,y1,x2,y2,label):
        self.line(x1,y1,x2,y2)
        if x1==x2: self.a.append(f'<rect x="{x1-5}" y="{(y1+y2)/2-12}" width="10" height="24" fill="white" stroke="#222"/>'); self.text(x1+8,(y1+y2)/2+4,label)
        else: self.a.append(f'<rect x="{(x1+x2)/2-13}" y="{y1-5}" width="26" height="10" fill="white" stroke="#222"/>'); self.text((x1+x2)/2-10,y1-10,label)
    def cap(self,x1,y1,x2,y2,label):
        self.line(x1,y1,x2,y2)
        if y1==y2:
            m=(x1+x2)/2; self.a.append(f'<rect x="{m-5}" y="{y1-10}" width="10" height="20" fill="white"/>'); self.line(m-4,y1-10,m-4,y1+10); self.line(m+4,y1-10,m+4,y1+10); self.text(m-9,y1-14,label)
        else:
            m=(y1+y2)/2; self.a.append(f'<rect x="{x1-10}" y="{m-5}" width="20" height="10" fill="white"/>'); self.line(x1-10,m-4,x1+10,m-4); self.line(x1-10,m+4,x1+10,m+4); self.text(x1+12,m+4,label)
    def source(self,x,y,label,current=False,reverse=False):
        self.a.append(f'<circle cx="{x}" cy="{y}" r="15" fill="white" stroke="#222"/>')
        if current: self.line(x,y-9,x,y+9); self.line(x,y+9,x-4,y+3); self.line(x,y+9,x+4,y+3)
        else: self.text(x-4,y-4,'−' if reverse else '+'); self.text(x-3,y+10,'+' if reverse else '−')
        self.text(x+19,y+4,label)
    def mos(self,x,y,label):
        # terminals drain at y-25, source at y+25, gate x-25; source-tied body teaching model
        self.line(x,y-25,x,y-13); self.line(x,y+13,x,y+25); self.line(x,y-13,x-8,y-13); self.line(x,y+13,x-8,y+13); self.line(x-8,y-13,x-8,y+13); self.line(x-13,y-16,x-13,y+16); self.line(x-25,y,x-13,y); self.text(x+8,y,label)
    def save(self,p): Path(p).write_text(''.join(self.a)+'</svg>')

def differential(p):
    s=SVG('Matched MOS differential pair · body tied to source')
    s.line(85,55,300,55); s.source(35,95,'VDD'); s.line(35,80,35,55); s.line(35,55,85,55); s.line(35,110,35,310); s.ground(35,310)
    for x,name,inp in ((110,'M1','v1'),(275,'M2','v2')):
        s.resistor(x,55,x,120,'RD'); s.node(x,120,'vo1' if x==110 else 'vo2'); s.line(x,120,x,150); s.mos(x,175,name); s.line(x,200,x,220)
        gx=x-45; s.line(gx,175,x-25,175); s.line(gx,175,gx,255); s.source(gx,270,inp); s.line(gx,285,gx,310); s.ground(gx,310)
    s.line(110,220,275,220); s.node(195,220,'vs'); s.line(195,220,195,240); s.source(195,255,'IT',True); s.line(195,270,195,300); s.line(195,300,365,300)
    s.source(365,270,'|VSS|'); s.line(365,285,365,300); s.line(365,255,365,230); s.ground(365,230); s.text(218,343,'tail compliance + finite rt'); s.save(p)

def cascade(p):
    s=SVG('Loading (top) and CS–CG cascode (bottom)')
    s.source(30,80,'A1 vi'); s.ground(30,110); s.line(30,95,30,110); s.resistor(30,65,155,65,'Rout1'); s.node(155,65,'v2'); s.resistor(155,65,155,110,'Rin2'); s.ground(155,110)
    s.source(245,80,'A2 v2'); s.line(245,95,245,110); s.ground(245,110); s.resistor(245,65,370,65,'Rout2'); s.resistor(370,65,370,110,'RL'); s.ground(370,110)
    s.text(14,145,'Dependent sources refer to the same 0 V node.')
    s.source(35,190,'VDD'); s.line(35,175,35,160); s.line(35,160,300,160); s.line(35,205,35,320); s.ground(35,320)
    s.resistor(300,160,300,205,'RD'); s.node(300,205,'vo'); s.line(300,205,300,210); s.mos(300,235,'M2'); s.node(300,260,'x'); s.mos(300,285,'M1'); s.line(300,310,300,325); s.ground(300,325)
    s.source(225,235,'VB'); s.line(225,220,255,220); s.line(255,220,255,235); s.line(255,235,275,235); s.line(225,250,225,325); s.ground(225,325)
    s.source(130,285,'vi'); s.line(130,270,250,270); s.line(250,270,250,285); s.line(250,285,275,285); s.line(130,300,130,325); s.ground(130,325); s.text(50,348,'Bias sources: + terminal at gate; return at 0.'); s.save(p)

def cgd(p):
    s=SVG('Complete small-signal Cgd two-node network')
    s.source(30,185,'vs'); s.line(30,170,30,100); s.resistor(30,100,130,100,'Rg'); s.node(130,100,'vg'); s.cap(130,100,300,100,'Cgd'); s.node(300,100,'vo')
    s.cap(130,100,130,270,'Cgs'); s.resistor(300,100,300,270,'Ro'); s.line(300,100,365,100); s.cap(365,100,365,270,'Co'); s.line(300,100,230,100); s.line(230,100,230,170); s.source(230,185,'gm vg',True); s.line(230,200,230,270)
    s.line(30,200,30,270); s.line(30,270,365,270); s.ground(130,270); s.text(18,320,'All branches return to the same reference.'); s.text(18,340,'Controlled source direction: output to reference.'); s.save(p)

def output(p):
    s=SVG('A resistor load; B/AB complementary output')
    s.source(30,85,'VCC'); s.line(30,70,30,50); s.line(30,50,105,50); s.line(30,100,30,285); s.ground(30,285); s.resistor(105,50,105,135,'R'); s.node(105,135,'voA'); s.line(105,135,105,165)
    s.line(85,168,85,192); s.line(85,172,105,165); s.line(85,188,105,205); s.line(105,205,105,285); s.line(101,202,95,201); s.line(101,202,100,196); s.ground(105,285); s.text(112,180,'NPN'); s.source(50,240,'vB'); s.line(50,225,50,180); s.line(50,180,85,180); s.line(50,255,50,285); s.ground(50,285); s.text(12,320,'A: biased common emitter'); s.text(12,337,'AC load is collector R')
    s.line(280,50,390,50); s.source(390,85,''); s.text(341,85,'+rail'); s.line(390,70,390,50); s.line(390,100,390,180); s.node(390,180,'0'); s.source(390,245,''); s.text(341,245,'−rail'); s.line(390,180,390,230); s.line(390,260,390,305); s.line(280,305,390,305)
    # BJT symbols include explicit collector and emitter and arrows
    for y,label,up in ((100,'NPN',True),(265,'PNP',False)):
        s.line(260,y-13,260,y+13); s.line(240,y,260,y); s.line(260,y-7,280,y-20); s.line(260,y+7,280,y+20); s.text(285,y,label)
        ax,ay=(275,y+17) if up else (265,y-10); 
        if up: s.line(ax,ay,ax-5,ay-1); s.line(ax,ay,ax-1,ay-5)
        else: s.line(ax,ay,ax+6,ay-1); s.line(ax,ay,ax+2,ay-6)
    s.line(280,50,280,80); s.resistor(280,120,280,180,'RE'); s.resistor(280,180,280,245,'RE'); s.line(280,285,280,305); s.node(280,180,'vo'); s.resistor(280,180,340,180,'RL'); s.line(340,180,340,205); s.ground(340,205)
    s.source(205,100,'bN'); s.line(205,85,240,85); s.line(240,85,240,100); s.line(205,115,205,180); s.source(205,265,'bP',reverse=True); s.line(205,280,235,280); s.line(235,280,235,265); s.line(235,265,240,265); s.line(205,250,205,180); s.ground(205,180); s.ground(390,180)
    s.text(180,328,'AB: bN − bP = Vbias'); s.text(180,346,'B: bN = bP = drive'); s.save(p)

def coupling(p):
    s=SVG('Coupling capacitor: stored state vc = va − vb')
    s.source(35,175,'e(t)'); s.line(35,160,35,100); s.resistor(35,100,145,100,'Rs'); s.node(145,100,'a'); s.cap(145,100,290,100,'C'); s.node(290,100,'b'); s.resistor(290,100,290,260,'RL'); s.line(35,190,35,260); s.line(35,260,290,260); s.ground(145,260)
    s.text(148,144,'+ vc −'); s.text(154,171,'i >'); s.text(18,305,'q = C vc; vc is continuous for finite current.'); s.text(18,327,'Periodic closure: ∫ one period i dt = 0.'); s.save(p)

def wave(p):
    s=SVG('Periodic state vs frozen old state · a = 0.35 V')
    s.line(40,290,400,290); s.line(40,55,40,290)
    values=[]
    for k in range(361):
        t=k/360/100; vc,vd,margin=models.legacy_periodic(t,.35,100,1e-6); frozen=(5/2000+3/10000-.001*(1+.35*math.sin(2*math.pi*100*t))**2)/(1/2000+1/10000)
        values.append((40+k,290-(vd-1)*68,290-(frozen-1)*68))
    for idx,dash in ((1,''),(2,' stroke-dasharray="6 4"')):
        pts=' '.join(f'{x:.2f},{row[idx]:.2f}' for row in values for x in [row[0]])
        s.a.append(f'<polyline points="{pts}" fill="none" stroke="#222" stroke-width="1.7"{dash}/>')
    for v in (1,2,3,4): s.text(15,294-(v-1)*68,str(v))
    s.text(44,317,'0'); s.text(342,317,'10 ms'); s.text(20,44,'VD / V'); s.text(44,339,'solid: finite-C periodic; dashed: frozen VC = 3 V'); s.save(p)

def run(out):
    import cairosvg
    out.mkdir(parents=True,exist_ok=True); assets=out/'assets'; assets.mkdir(exist_ok=True)
    for name,fun in [('differential',differential),('cascade',cascade),('cgd',cgd),('output',output),('coupling',coupling),('periodic',wave)]:
        svg=assets/(name+'.svg'); fun(svg)
        for width in (360,425): cairosvg.svg2png(url=str(svg),write_to=str(assets/(name+f'-{width}.png')),output_width=width,output_height=round(360*width/425))
    cycle,n,res=models.periodic_rk4(.35,100,1e-6)
    error=max(abs(v-models.legacy_periodic(k/(100*len(cycle)),.35,100,1e-6)[0]) for k,v in enumerate(cycle))
    results={'parameter_status':'teaching only','cgd':models.cgd_coefficients(1e4,1e4,.001,20e-12,2e-12,10e-12),'class_b':models.class_b(4,5,8),'harmonics_deadzone':models.harmonics(1,.6),'thermal':models.thermal_idle(.01,5,1,.002,10),'periodic':{'cycles':n,'sampled_state_error_estimate_V':res,'vs_analytic_max_error_V':error},'hardware':'not run','spice':'not run'}
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); args=p.parse_args(); run(output_path(args.output))
