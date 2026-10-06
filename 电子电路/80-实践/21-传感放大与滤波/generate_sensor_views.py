"""Editable topology and computed plots; all output is explicit caller-owned."""
from pathlib import Path
import math
import sensor_filter_lab as m

class SVG:
    def __init__(self,title,h=520):
        self.h=h;self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}">',
          '<rect width="420" height="100%" style="fill:white;stroke:none"/>',
          '<style>text{font-family:Arial,sans-serif;font-size:14px;fill:#111}path,line,rect,polygon,circle{stroke:#111;stroke-width:2;fill:none} .node{fill:#111}</style>']
        self.text(16,25,title)
    def text(self,x,y,t,size=None):self.parts.append(f'<text x="{x}" y="{y}"'+(f' style="font-size:{size}px"' if size else '')+f'>{t}</text>')
    def wire(self,*points):self.parts.append('<polyline fill="none" stroke="#111" stroke-width="2" points="'+' '.join(f'{x},{y}' for x,y in points)+'"/>')
    def node(self,x,y):self.parts.append(f'<circle class="node" cx="{x}" cy="{y}" r="3"/>')
    def ground(self,x,y):
        self.wire((x,y),(x,y+8));self.wire((x-12,y+8),(x+12,y+8));self.wire((x-8,y+13),(x+8,y+13));self.wire((x-4,y+18),(x+4,y+18))
    def res(self,x1,y1,x2,y2,label):
        vertical=x1==x2;dx=x2-x1;dy=y2-y1
        a=(x1+dx*.32,y1+dy*.32);b=(x1+dx*.68,y1+dy*.68)
        self.wire((x1,y1),a);self.wire(b,(x2,y2))
        if vertical:self.parts.append(f'<rect x="{x1-6}" y="{a[1]}" width="12" height="{b[1]-a[1]}"/>');self.text(x1+12,(y1+y2)/2,label)
        else:self.parts.append(f'<rect x="{a[0]}" y="{y1-6}" width="{b[0]-a[0]}" height="12"/>');self.text((x1+x2)/2-22,y1-13,label)
    def cap(self,x1,y1,x2,y2,label):
        dx=x2-x1;dy=y2-y1;cx=(x1+x2)/2;cy=(y1+y2)/2
        if dx==0:
            self.wire((x1,y1),(cx,cy-5));self.wire((cx,cy+5),(x2,y2));self.wire((cx-12,cy-5),(cx+12,cy-5));self.wire((cx-12,cy+5),(cx+12,cy+5));self.text(cx+15,cy+3,label)
        else:
            self.wire((x1,y1),(cx-5,cy));self.wire((cx+5,cy),(x2,y2));self.wire((cx-5,cy-12),(cx-5,cy+12));self.wire((cx+5,cy-12),(cx+5,cy+12));self.text(cx-15,cy-19,label)
    def amp(self,x,y,minus_top=True,name='A'):
        self.parts.append(f'<polygon points="{x},{y-45} {x},{y+45} {x+70},{y}"/>')
        self.text(x+5,y-16,'−' if minus_top else '+');self.text(x+5,y+25,'+' if minus_top else '−');self.text(x+28,y+4,name)
        self.wire((x+28,y-27),(x+28,y-65));self.text(x+32,y-57,'+5 V')
        self.wire((x+28,y+27),(x+28,y+65));self.text(x+32,y+61,'−5 V')
    def save(self,path):path.write_text('\n'.join(self.parts)+ '\n</svg>\n')

def circuits(out):
    d=SVG('TIA: current enters X; small signal about 0 V',490)
    d.amp(270,240);d.wire((30,220),(270,220));d.node(150,220);d.text(32,205,'i →');d.text(154,212,'X = v−')
    d.cap(150,220,150,365,'CT 30 pF');d.ground(150,365)
    d.wire((150,220),(150,100));d.res(150,100,370,100,'RF 1 MΩ');d.wire((370,100),(370,240),(340,240));d.node(370,240);d.text(347,270,'vo')
    d.wire((150,150),(150,160));d.cap(150,150,370,150,'CF 1 pF');d.wire((370,150),(370,100));d.node(150,150);d.node(370,150)
    d.wire((270,260),(235,260),(235,365));d.ground(235,365)
    d.text(16,420,'RF and CF share both endpoints; CT includes input C.')
    d.text(16,445,'Loop model: set i=0, vo→divider X→−A→vo.')
    d.text(16,469,'A(s)=A0/(1+s/wp); no extra poles or delay here.')
    d.save(out/'tia-circuit.svg')
    d=SVG('Three-op-amp INA: DC nodes and real resistor ratios',760)
    # First amplifiers, plus input above; shared gain resistor below.
    for x,name,vi in ((70,'A1','v1'),(265,'A2','v2')):
        d.amp(x,180,False,name);d.wire((x-40,160),(x,160));d.text(x-38,145,vi)
        d.wire((x,200),(x-20,200),(x-20,290));d.res(x-20,290,x+100,290,'Rf 10k')
        d.wire((x+100,290),(x+100,180),(x+70,180));d.node(x-20,290);d.node(x+100,180);d.text(x+70,165,'o1' if name=='A1' else 'o2')
    d.wire((50,290),(50,365));d.res(50,365,245,365,'Rg 2k');d.wire((245,365),(245,290))
    d.amp(225,555,True,'A3');d.text(16,422,'A1/A2 inputs: v−=v+ only in linear ideal limit.')
    d.wire((170,180),(185,180),(185,475),(25,475),(25,535));d.res(25,535,225,535,'R1 10k')
    d.wire((365,180),(395,180),(395,445),(15,445),(15,575));d.res(15,575,225,575,'R3 10k')
    d.wire((200,535),(200,460));d.res(200,460,345,460,'R2 100k');d.parts[-1]=d.parts[-1].replace('y="447"','y="482"');d.wire((345,460),(345,555),(295,555));d.node(200,535);d.node(345,555);d.text(348,560,'vo')
    d.res(200,575,200,665,'R4');d.node(200,575);d.text(126,690,'Vref = 2.5 V (stiff source)');d.wire((200,665),(200,676))
    d.text(16,708,'R1/R3=10k; R2/R4=100k. All amps ±5 V.')
    d.text(16,728,'Reference node for vi/vo is 0 V.')
    d.text(16,746,'Crossed wires without a dot are not joined.')
    d.save(out/'instrumentation.svg')
    d=SVG('Inverting Schmitt comparator: open-drain output',590)
    d.amp(230,260,True,'CMP');d.wire((30,240),(230,240));d.text(30,226,'vi');d.text(32,327,'Vref 2.5 V')
    d.res(30,280,230,280,'Rref 10k');d.text(18,303,'stiff ref');d.node(195,280);d.text(171,303,'vt')
    d.wire((195,280),(195,380));d.res(195,380,355,380,'Rfb 20k');d.wire((355,380),(355,260),(300,260));d.node(355,260);d.text(361,266,'vo')
    d.res(355,90,355,220,'Rp 10k');d.wire((355,220),(355,260));d.text(315, 70,'+5 V pullup')
    d.cap(355,380,355,460,'Co');d.ground(355,460);d.text(245,455,'Co=100pF')
    # Comparator power must be 0..5, overriding op-amp -5 label.
    d.parts=[s.replace('−5 V','0 V') for s in d.parts]
    d.text(16,505,'Released: vo=4.375 V; feedback loads Rp.')
    d.text(16,531,'Low state: sink holds 0.1 V, requires 0.57 mA.')
    d.text(16,557,'Positive feedback: high output raises vt to 3.125 V.')
    d.text(16,583,'Polarity here: high for v+ > v−; choose matching part.')
    d.save(out/'comparator.svg')
    d=SVG('RC relaxation oscillator: push-pull comparator',820)
    d.amp(230,235,True,'CMP');d.parts=[s.replace('−5 V','0 V') for s in d.parts]
    d.wire((35,215),(230,215));d.node(90,215);d.text(100,202,'vC');d.cap(90,215,90,355,'C 10nF');d.ground(90,355)
    d.wire((35,215),(35,100));d.res(35,100,355,100,'R 10k');d.wire((355,100),(355,235),(300,235));d.node(355,235);d.text(362,240,'vo')
    d.text(20,291,'Vref');d.text(20,309,'2.5 V');d.res(35,255,230,255,'Rref 10k');d.node(190,255)
    d.wire((190,255),(190,365));d.res(190,365,355,365,'Rfb 20k');d.wire((355,365),(355,235))
    d.text(16,418,'Rails: 0.1 / 4.9 V. Thresholds: 1.7 / 3.3 V.')
    d.text(16,443,'Input and feedback share 0 V reference; no float node.')
    d.text(16,468,'R, C form timing path; this is a nonlinear switch model.')
    tau=m.oscillator()['tau_s']; th=m.oscillator()['t_high_s']; T=2*th
    d.text(18,505,'Zero-delay periodic cycle; t=0 starts high at vC=1.7V')
    d.wire((40,540),(40,740),(395,740))
    d.text(8,535,'V');d.text(6,560,'5');d.text(6,741,'0')
    vc=[];vo=[]
    for j in range(601):
        t=2*T*j/600;p=t%T;x=40+350*t/(2*T)
        val=4.9+(1.7-4.9)*math.exp(-p/tau) if p<th else .1+(3.3-.1)*math.exp(-(p-th)/tau)
        vc.append((x,740-36*val));vo.append((x,740-36*(4.9 if p<th else .1)))
    d.wire(*vc);d.parts[-1]=d.parts[-1].replace('stroke="#111"','stroke="#165b8c"')
    d.wire(*vo);d.parts[-1]=d.parts[-1].replace('stroke="#111"','stroke="#8a3511" stroke-dasharray="6 4"')
    for t,label in ((0,'0'),(th,'69.31'),(T,'138.63'),(2*T,'277.26')):
        x=40+350*t/(2*T);d.text(max(18,x-22),764,label)
    d.text(295,791,'Time (µs)');d.text(42,814,'Solid vC; dashed vo; thresholds 1.7 / 3.3 V.')
    d.save(out/'oscillator-circuit.svg')
    for kind in ('sk','mfb'):
        d=SVG(('Sallen-Key' if kind=='sk' else 'MFB')+': actual node equations use x, y, vo',580)
        d.amp(270,290,kind=='mfb');d.wire((20,270),(30,270));d.text(20,254,'vi')
        d.res(30,270,145,270,'R1');d.node(145,270);d.text(144,253,'x')
        d.res(145,270,270,270,'R2' if kind=='sk' else 'R3');d.text(243,251,'y')
        d.wire((340,290),(385,290));d.text(361,315,'vo');d.node(385,290)
        if kind=='sk':
            d.cap(225,270,225,415,'C1');d.node(225,270);d.ground(225,415)
            d.wire((145,270),(145,130));d.cap(145,130,385,130,'C2');d.wire((385,130),(385,290))
            d.wire((270,310),(250,310),(250,395));d.res(250,395,385,395,'Rf');d.wire((385,395),(385,290));d.res(250,395,250,460,'Rg');d.ground(250,460)
            d.text(16,500,'R1=R2=10k; C1=C2=10nF; K=3−√2.')
            d.text(16,525,'Rf/Rg=2−√2; ideal Q=1/√2, f0=1591.55 Hz.')
        else:
            d.cap(145,270,145,415,'C2');d.ground(145,415)
            d.wire((145,270),(145,110));d.res(145,110,385,110,'R2');d.wire((385,110),(385,290))
            d.wire((230,270),(230,165));d.cap(230,165,385,165,'C1');d.wire((385,165),(385,110));d.node(230,270);d.node(385,165)
            d.wire((270,310),(235,310),(235,415));d.ground(235,415)
            d.text(16,500,'R1=R2=R3=10k; C1=10nF; C2=45nF.')
            d.text(16,525,'Ideal gain −1, Q=1/√2, f0=750.264 Hz.')
        d.text(16,551,'Amp rails ±5 V; unloaded small-signal output.')
        d.text(16,576,'Crossings without dots are not joined. Reference: 0 V.')
        d.save(out/(kind+'-circuit.svg'))
    d=SVG('Reference loading: DC draw and switched charge',460)
    d.text(18, 70,'Videal = 2.5 V');d.wire((35,90),(35,140));d.parts.append('<circle cx="35" cy="165" r="25"/>');d.text(28,161,'+');d.text(29,179,'−');d.wire((35,190),(35,300));d.ground(35,300)
    d.res(35,140,200,140,'Ro 0.1Ω');d.node(200,140);d.text(208,124,'vREF')
    d.res(200,140,200,300,'Rload 2.5k');d.ground(200,300)
    d.wire((200,140),(360,140));d.cap(360,140,360,300,'Cref');d.ground(360,300)
    d.text(240,72,'ADC charge draw');d.text(250,96,'Δq per event ↓')
    d.text(16,355,'DC: Δv≈−Ro ΔI = −0.1 mV at 1 mA.')
    d.text(16,381,'Fast event: Δv≈−Δq/Cref before replenishment.')
    d.text(16,407,'Cref, ESR, buffer loop and event spacing need checking.')
    d.text(16,433,'This source is a model; Cref is not a universal fix.')
    d.save(out/'reference-load.svg')


def generate(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    import os
    os.environ.setdefault('MPLCONFIGDIR', str(out/'.cache'/'mpl'))
    os.environ.setdefault('XDG_CACHE_HOME', str(out/'.cache'))
    m.generate(out);circuits(out)
    # Heavy libraries are lazy; Figure/Agg avoids any default GUI backend.
    import matplotlib
    matplotlib.rc_file(str(Path(__file__).with_name('matplotlibrc')))
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import numpy as np
    def fig(name,plots):
        f=Figure(figsize=(4.2,6.5),dpi=100);FigureCanvasAgg(f)
        axes=f.subplots(len(plots),1)
        if len(plots)==1:axes=[axes]
        for ax,paint in zip(axes,plots):paint(ax)
        f.tight_layout(pad=.8);f.savefig(out/(name+'.svg'),metadata={'Date':None})
    hz=np.logspace(2,7,400)
    def tia_gain(ax):
        for cf,style in ((0,'--'),(1e-12,'-')):
            ax.semilogx(hz,[20*math.log10(abs(m.tia(x,cf=cf)['loop'])) for x in hz],style,label=f'CF={cf/1e-12:g}pF')
        ax.axhline(0,color='black',lw=.8);ax.set(ylabel='Loop |A/NG| (dB)',title='CT=30pF; RF=1MΩ');ax.legend(fontsize=12);ax.grid(True)
    def tia_phase(ax):
        for cf,style in ((0,'--'),(1e-12,'-')):
            ax.semilogx(hz,[math.degrees(__import__('cmath').phase(m.tia(x,cf=cf)['loop'])) for x in hz],style)
        ax.set(xlabel='Frequency (Hz)',ylabel='Loop phase (deg)');ax.grid(True)
    fig('tia-loop',[tia_gain,tia_phase])
    ws=np.logspace(-2,1.4,400);styles={'butterworth':'-','chebyshev1':'--','bessel':':'}
    def proto_gain(ax):
        for k,st in styles.items():ax.semilogx(ws,[20*math.log10(abs(m.prototype_response(k,w)['H'])) for w in ws],st,label=k)
        ax.set(title='Order 2; unity DC; same −3dB corner',ylabel='Magnitude (dB)',ylim=(-45,3));ax.legend(fontsize=11);ax.grid(True)
    def proto_delay(ax):
        for k,st in styles.items():ax.semilogx(ws,[m.prototype_response(k,w)['group_delay_normalized'] for w in ws],st)
        ax.set(xlabel='ω / ωc (ωc=1 rad/s)',ylabel='Group delay × ωc',ylim=(0,3));ax.grid(True)
    fig('prototypes',[proto_gain,proto_delay])
    import cairosvg
    from PIL import Image,ImageOps
    for source in sorted(out.glob('*.svg')):
        for width in (360,425):
            path=out/(source.stem+f'-{width}.png');cairosvg.svg2png(url=str(source),write_to=str(path),output_width=width)
    return out


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    args=p.parse_args();generate(args.output)

if __name__=='__main__':main()
