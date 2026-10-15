"""Deterministic circuit SVG and direct-Figure plots; explicit output only."""
from pathlib import Path
import argparse
import json
import html
import amp_lab as a

class Circuit:
    def __init__(self,title,height=600):
        self.h=height;self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="440" height="{height}" viewBox="0 0 440 {height}"><rect width="440" height="{height}" fill="white"/><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7" fill="#222"/></marker></defs><g stroke="#222" stroke-width="2" fill="none">'];self.text(18,28,title,17)
    def line(self,x1,y1,x2,y2,arrow=False):self.s.append(f'<path d="M{x1},{y1} L{x2},{y2}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
    def text(self,x,y,t,size=15):self.s.append(f'<text x="{x}" y="{y}" stroke="none" fill="#111" font-family="DejaVu Sans, sans-serif" font-size="{size}">{html.escape(t)}</text>')
    def node(self,x,y):self.s.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#222"/>')
    def resistor(self,x,y1,y2,label,left=False):
        mid=(y1+y2)/2;self.line(x,y1,x,mid-20);self.s.append(f'<rect x="{x-9}" y="{mid-20}" width="18" height="40"/>');self.line(x,mid+20,x,y2);self.text(x-50 if left else x+14,mid+5,label)
    def ground(self,x,y):
        self.line(x,y,x,y+10)
        for w,dy in [(14,10),(9,15),(4,20)]:self.line(x-w,y+dy,x+w,y+dy)
    def mos(self,x,y,name):
        self.line(x,y-50,x,y-25);self.line(x,y-25,x-15,y-25);self.line(x-15,y-25,x-15,y+25);self.line(x-15,y+25,x,y+25);self.line(x,y+25,x,y+50);self.line(x-30,y-22,x-30,y+22);
        if name.startswith('P'):
            self.line(x-65,y,x-42,y);self.s.append(f'<circle cx="{x-36}" cy="{y}" r="6"/>')
        else:self.line(x-65,y,x-30,y)
        self.text(x+12,y+6,name)
        return (x,y-50),(x-65,y),(x,y+50)
    def bjt(self,x,y,name):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="29"/>');self.line(x-15,y-18,x-15,y+18);self.line(x-60,y,x-15,y);self.line(x-15,y-11,x+15,y-35);self.line(x+15,y-35,x+15,y-50);self.line(x-15,y+11,x+15,y+35,True);self.line(x+15,y+35,x+15,y+50);self.text(x+38,y+5,name)
        return (x+15,y-50),(x-60,y),(x+15,y+50)
    def source(self,x,y,label,arrow=False):
        
        dependent=label.startswith('gm')
        if dependent:self.s.append(f'<path d="M{x},{y-24} L{x+24},{y} L{x},{y+24} L{x-24},{y} Z"/>')
        else:self.s.append(f'<circle cx="{x}" cy="{y}" r="22"/>')
        extent=24 if dependent else 22
        self.line(x,y-50,x,y-extent);self.line(x,y+extent,x,y+50)
        if arrow:self.line(x,y-12,x,y+12,True)
        else:self.text(x-5,y-7,'+');self.text(x-5,y+15,'−')
        self.text(x+30,y+5,label)
    def finish(self,p):p.write_text(''.join(self.s)+'</g></svg>',encoding='utf-8')

def circuits(out):
    c=Circuit('BJT divider bias / DC',570)
    c.line(85,75,300,75);c.text(170,62,'VDD = 5 V');c.resistor(85,75,240,'RT 30k');c.resistor(85,240,450,'RB 10k');c.bjt(230,290,'Q1');c.line(85,240,85,290);c.line(85,290,170,290);c.node(85,290);c.node(85,240);c.resistor(245,75,240,'RC 4k');c.node(245,240);c.text(260,230,'VC');c.resistor(245,340,450,'RE 1k');c.text(260,354,'VE');c.line(85,450,245,450);c.ground(160,450);c.text(20,492,'IB to base; IC down collector');c.text(20,517,'IE = IC + IB; beta = 100');c.text(20,542,'IS = 1e-15 A, UT = 26 mV');c.finish(out/'bias-bjt.svg')
    c=Circuit('MOS bias / re-solve after RS',520);c.text(200,70,'5 V');c.resistor(230,85,220,'RD 2k');c.mos(230,270,'M1');c.node(230,220);c.text(250,215,'VD');c.line(165,270,100,270);c.text(20,255,'VG = 2 V');c.resistor(230,320,440,'RS 0 / 500');c.text(250,335,'VS');c.ground(230,440);c.text(20,476,'Body to own source; K = 2 mA/V²');c.text(20,502,'VT = 1 V, lambda = 0.02 /V');c.finish(out/'bias-mos.svg')
    c=Circuit('CS / connected AC model',600);c.text(220,67,'AC ground');c.resistor(225,80,220,'RD 2k');c.resistor(355,80,220,'RL 10k');c.line(225,80,355,80);c.line(225,220,355,220);c.node(225,220);c.text(20,210,'vd');c.line(100,220,355,220);c.resistor(100,220,365,'ro',True);c.line(225,220,225,242);c.source(225,292,'gm(vg − vs)',True);c.line(225,342,225,365);c.line(100,365,225,365);c.node(225,365);c.text(250,379,'vs');c.resistor(225,365,470,'RS');c.ground(225,470);c.source(50,425,'vi');c.node(50,375);c.ground(50,475);c.text(18,356,'vg');c.text(18,510,'Gate vi: zero input current');c.text(18,537,'RL: AC only; not in DC Q');c.text(18,564,'ro and gm share drain / source');c.finish(out/'cs-model.svg')
    c=Circuit('CE / connected hybrid-pi model',770);c.text(215,65,'AC ground');c.resistor(240,80,220,'RC');c.resistor(365,80,220,'RL');c.line(240,80,365,80);c.line(95,220,365,220);c.node(240,220);c.text(18,212,'vc');c.resistor(95,220,360,'ro',True);c.line(240,220,240,240);c.source(240,290,'gm(vb − ve)',True);c.line(240,340,240,360);c.line(95,360,240,360);c.node(240,360);c.resistor(240,360,475,'RE');c.ground(240,475);c.line(160,360,160,450);c.resistor(75,450,550,'rpi');c.line(75,450,160,450);c.line(75,550,30,550);c.line(30,550,30,590);c.source(30,640,'vb');c.ground(30,690);c.text(100,720,'vb input to rpi to ve');c.text(18,750,'Base current = (vb - ve) / rpi');c.finish(out/'ce-model.svg')
    c=Circuit('CG: two actual port tests',785);c.text(18,62,'(a) Input test; RL stays connected');c.resistor(235,90,195,'RD');c.resistor(355,90,195,'RL');c.line(235,90,355,90);c.ground(235,70);c.line(235,80,235,90);c.line(235,195,355,195);c.mos(235,245,'M');c.line(170,245,120,245);c.ground(120,245);c.line(235,295,100,295);c.source(100,345,'vi');c.ground(100,395);c.text(18,429,'ii to source; iL down load');c.text(18,459,'(b) Output test; remove RL');c.mos(235,575,'M');c.resistor(235,475,525,'RD');c.line(235,475,335,475);c.ground(235,455);c.line(235,465,235,475);c.source(335,575,'vx');c.line(335,525,235,525);c.node(235,525);c.ground(335,625);c.line(170,575,120,575);c.ground(120,575);c.resistor(235,625,720,'Rsig');c.ground(235,720);c.text(18,767,'ix enters drain; gate AC grounded');c.finish(out/'cg-test.svg')
    c=Circuit('Source follower / DC and AC tests',890);c.text(190,62,'Drain: 5 V DC');c.mos(235,155,'M1');c.line(235,105,235,80);c.line(170,155,80,155);c.text(18,136,'VG 3 V + vi');c.node(235,205);c.text(250,221,'VS / vo');c.resistor(235,205,355,'RS 1k');c.line(365,205,365,216);c.line(348,216,382,216);c.line(348,230,382,230);c.line(365,230,365,245);c.text(388,229,'CC');c.resistor(365,245,355,'RL 10k');c.line(235,205,365,205);c.line(235,355,365,355);c.ground(235,355);c.text(18,394,'CC: DC open / midband short');c.text(18,420,'AC output test: remove RL, vi = 0');c.mos(235,565,'M1');c.line(235,515,235,475);c.ground(235,455);c.line(170,565,120,565);c.ground(120,565);c.line(235,615,100,615);c.node(235,615);c.source(100,665,'vx');c.ground(100,715);c.resistor(235,615,760,'RS 1k');c.ground(235,760);c.text(18,823,'ix = (gm + go + 1/RS) vx');c.text(18,855,'Body to own source; gm from DC Q');c.finish(out/'follower-test.svg')
    c=Circuit('CB / actual AC input test',570);c.text(210,65,'AC ground');c.resistor(245,80,220,'RC');c.resistor(365,80,220,'RL');c.line(245,80,365,80);c.line(245,220,365,220);c.bjt(230,270,'Q1');c.line(170,270,120,270);c.ground(120,270);c.line(245,320,100,320);c.source(100,370,'ve');c.ground(100,420);c.text(18,480,'Input current enters emitter');c.text(18,510,'Base fixed; output at collector');c.text(18,540,'DC VE, VB set before this AC test');c.finish(out/'cb-test.svg')
    c=Circuit('Emitter follower / AC port tests',970);c.text(18,62,'(a) Voltage transfer: collector AC 0');c.bjt(230,155,'Q1');c.line(245,105,245,90);c.ground(245,70);c.line(170,155,80,155);c.source(80,205,'vb');c.ground(80,255);c.line(245,205,245,270);c.node(245,270);c.text(260,264,'vo');c.resistor(245,270,375,'Rbias');c.resistor(365,270,375,'RL');c.line(245,270,365,270);c.line(245,375,365,375);c.ground(245,375);c.text(18,440,'(b) Output test: RL removed');c.text(18,468,'Input source zero; retain Rb');c.bjt(230,590,'Q1');c.line(245,540,245,520);c.ground(245,500);c.line(170,590,105,590);c.resistor(105,590,700,'Rb');c.ground(105,700);c.line(245,640,245,740);c.node(245,740);c.resistor(245,740,840,'Rbias');c.ground(245,840);c.line(245,740,365,740);c.source(365,790,'vx');c.ground(365,840);c.text(18,906,'ix enters emitter; base responds');c.text(18,938,'Rb = source/bias termination');c.finish(out/'emitter-test.svg')
    c=Circuit('Simple NMOS mirror',540);c.source(135,120,'Iref',True);c.mos(135,290,'M1');c.mos(340,290,'M2');c.line(135,170,135,240);c.line(135,240,70,240);c.line(70,240,70,290);c.line(70,290,70,210);c.line(70,210,275,210);c.line(275,210,275,290);c.node(135,240);c.node(70,240);c.line(340,240,340,105);c.text(285,85,'VO / IO down');c.text(22,90,'Supply');c.line(135,340,135,400);c.line(340,340,340,400);c.line(135,400,340,400);c.ground(235,400);c.text(18,458,'M1 gate = drain = VG');c.text(18,484,'M2 needs VO ≥ VG − VT');c.text(18,510,'Both bodies tied to own source');c.finish(out/'mirror-simple.svg')
    c=Circuit('BJT mirror / reference current KCL',540);c.source(130,120,'Iref',True);c.bjt(115,290,'Q1');c.bjt(320,290,'Q2');c.line(130,170,130,240);c.line(130,240,55,240);c.line(55,240,55,290);c.line(55,240,260,240);c.line(260,240,260,290);c.node(130,240);c.node(55,240);c.line(335,240,335,105);c.text(295,85,'VO / IO down');c.line(130,340,130,400);c.line(335,340,335,400);c.line(130,400,335,400);c.ground(230,400);c.text(18,455,'Iref = IC1 + IB1 + IB2');c.text(18,484,'Q1 collector = base; emitters = 0');c.text(18,513,'Active output: VO ≥ VB');c.finish(out/'mirror-bjt.svg')
    c=Circuit('Four-MOS stacked cascode mirror',680);c.source(135,110,'Iref',True);c.mos(135,275,'M3');c.mos(340,275,'M4');c.mos(135,435,'M1');c.mos(340,435,'M2');c.line(135,160,135,225);c.line(135,225,70,225);c.line(70,225,70,275);c.line(70,225,70,185);c.line(70,185,275,185);c.line(275,185,275,275);c.node(135,225);c.node(70,225);c.line(135,325,135,385);c.line(340,325,340,385);c.node(340,355);c.text(355,360,'VX');c.line(135,385,70,385);c.line(70,385,70,435);c.line(70,385,70,355);c.line(70,355,275,355);c.line(275,355,275,435);c.node(135,385);c.node(70,385);c.line(340,225,340,105);c.text(288,85,'VO / IO down');c.line(135,485,135,535);c.line(340,485,340,535);c.line(135,535,340,535);c.ground(235,535);c.text(18,587,'Each body to own source');c.text(18,615,'Gate M2 = VG; gate M4 = 2 VG');c.text(18,643,'Ordinary stacked: VO ≥ 2 VG − VT');c.finish(out/'mirror-cascode.svg')
    c=Circuit('PMOS mirror as CS active load',660);c.line(135,90,340,90);c.text(185,65,'VDD 5 V');c.mos(135,215,'P1');c.mos(340,215,'P2');c.text(18,150,'PMOS: top = S');c.line(135,90,135,165);c.line(340,90,340,165);c.line(135,265,135,295);c.line(135,295,70,295);c.line(70,295,70,215);c.line(70,295,275,295);c.line(275,295,275,215);c.node(135,295);c.node(70,295);c.source(135,375,'Iref',True);c.line(135,295,135,325);c.ground(135,425);c.mos(340,435,'N1');c.line(340,265,340,385);c.node(340,325);c.line(340,325,415,325);c.text(350,350,'VO = 3 V');c.line(275,435,220,435);c.text(170,466,'VG,n');c.ground(340,485);c.text(18,545,'PMOS current down equals NMOS down at Q');c.text(18,577,'N body to source; P body to supply');c.text(18,609,'RL: AC only, added at VO');c.text(18,639,'Reference sets P1/P2 common gate');c.finish(out/'active-load.svg')

def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);assets=output/'assets';assets.mkdir(exist_ok=True)
    circuits(assets)
    import matplotlib as mpl
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import numpy as np
    import cairosvg
    with mpl.rc_context(fname=Path(__file__).with_name('matplotlibrc')):
        fig=Figure(figsize=(4.4,5.7),dpi=100);FigureCanvasAgg(fig)
        ax=fig.add_subplot();u=np.linspace(-.999,.350781,220);v=5-2*(1+u)**2
        ax.plot(u,v,label='DC path: no RL');ax.plot(u,1+u,'--',label='VD = VOV boundary');ax.scatter([0],[3],label='Q: (0, 3 V)');ax.set(xlabel='Gate change u (V)',ylabel='Drain voltage VD (V)',title='CS swing / lambda = 0');ax.legend(fontsize=11);ax.grid(alpha=.3);fig.tight_layout();fig.savefig(assets/'cs-swing.svg',metadata={'Date':None});fig.savefig(assets/'cs-swing.png')
        fig=Figure(figsize=(4.4,5.7),dpi=100);FigureCanvasAgg(fig);ax=fig.add_subplot();vo=np.linspace(3.2,4.6,90);simple=[a.mirror(x)['id']*1000 for x in vo];cascade=[a.cascode(x)['id']*1000 for x in vo]
        ax.plot(vo,simple,label='Simple mirror');ax.plot(vo,cascade,label='Stacked cascode');ax.axvline(2*a.mos_reference(),ls='--',color='gray');ax.set(xlabel='Output voltage VO (V)',ylabel='Output current (mA)',title='Saturated branches only');ax.legend(fontsize=11);ax.grid(alpha=.3);fig.tight_layout();fig.savefig(assets/'mirror-slope.svg',metadata={'Date':None});fig.savefig(assets/'mirror-slope.png')
    for svg in sorted(assets.glob('*.svg')):
        if svg.stem not in ('cs-swing','mirror-slope'):cairosvg.svg2png(url=str(svg),write_to=str(svg.with_suffix('.png')))
    p=a.mos_bias();d=a.mos_bias(rs=500);b=a.bjt_bias();f=a.follower_bias()
    data=dict(mos=p,mos_degenerated=d,bjt=b,cs=a.cs(p['gm'],p['go'],2000,0,10000),cs_degenerated=a.cs(d['gm'],d['go'],2000,500,10000),ce=a.ce(b['gm'],100,0,4000,1000,10000),cg=a.cg(p['gm'],p['go'],2000,10000,1000),follower_q=f,follower=a.follower(f['gm'],f['go'],1000,10000),mirror=a.mirror(3),cascode=a.cascode(2*a.mos_reference()),bjt_mirror=a.bjt_mirror(2),bjt_mirror_early=a.bjt_mirror(2,va=100),active_unloaded=a.active_load(),active_loaded=a.active_load(rl=10000),scope='scalar real DC and local AC toy models; no SPICE or hardware')
    (output/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();generate(args.output)
if __name__=='__main__':main()
