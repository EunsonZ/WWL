"""Explicit generator; import is inert and only loads the standard library."""
import argparse
import json
import os
from pathlib import Path
from html import escape
import logic_examples as model


def line(x1,y1,x2,y2,dash=False):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'+(' stroke-dasharray="4 3"' if dash else '')+'/>'

def text(x,y,s,size=16):
    return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'

def node(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'

def wrap(body,height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}"><rect width="425" height="{height}" fill="white"/><g fill="none" stroke="#111" stroke-width="2">{body}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}} rect.cell{{fill:white}}</style></svg>'


def mos(x,y,name,p=False):
    # channel top/bottom; source, drain and gate explicitly wired by caller.
    s=line(x,y-20,x,y+20)+line(x-17,y-17,x-17,y+17)+line(x,y-30,x,y-20)+line(x,y+20,x,y+30)
    s+=line(x-40,y,x-17,y)
    if p:s+=f'<circle cx="{x-22}" cy="{y}" r="4" fill="white"/>'
    return s+text(x+10,y+5,name,15)


def topology():
    b=text(20,26,'CMOS: u gates, y common drains',17)
    b+=line(70,55,260,55)+text(270,60,'D=3.3 V')+mos(210,110,'P',True)+mos(210,265,'N')
    b+=line(210,55,210,80)+line(210,140,210,235)+node(210,188)
    b+=line(70,110,170,110)+line(70,110,70,265)+line(70,265,170,265)+text(25,192,'u')
    b+=line(210,295,210,342)+line(170,342,365,342)+text(15,347,'GND=0 V')
    b+=line(210,188,350,188)+node(350,188)+text(357,193,'y')
    b+=line(350,188,350,250)+line(335,250,365,250)+line(335,260,365,260)+line(350,260,350,342)+text(275,291,'CL=20 pF',14)
    b+=text(25,395,'P: source, body -> D',16)+text(25,425,'N: source, body -> GND',16)
    b+=text(25,457,'Capacitor return is GND',16)
    return wrap(b,485)


def kmap():
    b=text(20,28,'F = AB + not(A) C',18)+text(20,57,'Gray columns; wrap adjacency',15)
    for j,s in enumerate(('00','01','11','10')):b+=text(109+70*j,95,s)
    for i,a in enumerate((0,1)):
        b+=text(20,145+65*i,'A='+str(a),16)
        for j,v in enumerate(((0,1,1,0),(0,0,1,1))[i]):
            b+=f'<rect class="cell" x="{85+70*j}" y="{110+65*i}" width="70" height="65"/>'+text(115+70*j,150+65*i,str(v),21)
    b+='<rect x="156" y="117" width="136" height="48" rx="8" stroke-dasharray="5 3"/>'
    b+='<rect x="226" y="182" width="136" height="48" rx="8" stroke-width="3"/>'
    b+=text(20,268,'Row 0 group: not(A) C',16)+text(20,298,'Row 1 group: AB',16)+text(20,328,'Column 11 also gives BC',16)
    return wrap(b,355)


def sram():
    b=text(14,25,'6T SRAM: Q <-> QB feedback',17)
    # two full complementary branches
    b+=line(100,60,330,60)+text(170,50,'VDD',15)
    for x,p,n,g in ((145,'P1','N1','QB'),(285,'P2','N2','Q')):
        b+=mos(x,110,p,True)+mos(x,265,n)+line(x,60,x,80)+line(x,140,x,235)+line(x,295,x,345)
        b+=line(x-40,110,x-40,265)+text(x-55,220,g,15)+node(x,185)
    b+=line(100,345,330,345)+text(169,367,'GND',15)
    # feedback wires with routes avoiding galvanic short of Q to QB.
    b+=f'<path d="M145 185 L215 185 L215 160 L245 160"/>'+node(245,160)
    b+=f'<path d="M285 185 L330 185 L330 320 L80 320 L80 160 L105 160"/>'+node(105,160)
    b+=text(150,178,'Q',15)+text(288,178,'QB',15)
    # Horizontal access channels, WL gates. body tied ground noted below.
    for xa,xb,base,name in ((25,145,65,'A1'),(285,405,365,'A2')):
        b+=line(xa,185,base-15,185)+line(base+15,185,xb,185)+line(base-15,185,base+15,185)
        b+=line(base-13,168,base+13,168)+line(base,168,base,145)+text(base-15,209,name,14)
        b+=line(xa if base==65 else xb,100,xa if base==65 else xb,290)
    b+=line(65,145,365,145)+text(187,137,'WL',15)
    b+=text(10,92,'BL',15)+text(369,92,'BLB',15)
    b+=text(15,402,'P1/P2 source & body: VDD',15)+text(15,428,'N1/N2 source & body: GND',15)+text(15,454,'A1/A2 body: GND; gate: WL',15)
    b+=text(15,482,'WL=0 isolates bitlines from Q/QB',14)
    b+=text(15,507,'Crossings without dots: no junction',14)
    return wrap(b,530)


def buses():
    b=text(16,25,'1. Two push-pull outputs on one bus',16)
    b+=line(75,55,340,55)+text(170,48,'D=3.3 V',15)
    for x,label in ((110,'A'),(285,'B')):
        b+=mos(x,105,label+'_P',True)+mos(x,270,label+'_N')
        b+=line(x,55,x,75)+line(x,135,x,240)+line(x,300,x,330)+node(x,188)
    b+=line(110,188,285,188)+text(158,179,'bus=1.65 V',14)
    b+=line(75,330,340,330)+text(173,352,'GND',15)
    b+=text(15,380,'ON: A_P and B_N, each Ron=20 ohm',14)
    b+=text(15,405,'OFF: A_N and B_P; I=82.5 mA',14)
    b+=text(15,430,'All P/N sources & bodies: rails',14)
    b+=text(16,465,'2. Open-drain: no active pull-up',17)
    b+=line(220,496,220,517)+text(250,501,'3.3 V',15)+f'<rect x="209" y="517" width="22" height="45"/>'+text(250,545,'Rp=4.7k',14)+line(220,562,220,594)
    b+=line(60,594,350,594)+node(220,594)+text(265,585,'bus',15)
    for x,g in ((90,'g1'),(220,'g2')):
        b+=mos(x,655,'N')+line(x,594,x,625)+line(x,685,x,729)+text(x-55,642,g,14)
    b+=line(350,594,350,649)+line(334,649,366,649)+line(334,659,366,659)+line(350,659,350,729)+text(290,697,'100 pF',14)
    b+=line(60,729,370,729)+text(16,759,'Sources & bodies: GND',15)+text(16,787,'All released: RC rise, not instant 1',15)
    return wrap(b,810)


def generate(output):
    output=Path(output)
    # No dependency import until a concrete output has been supplied.
    output.mkdir(parents=True,exist_ok=True)
    os.environ['MPLCONFIGDIR']=str(output/'.mplconfig')
    os.environ['XDG_CACHE_HOME']=str(output/'.cache')
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib
    matplotlib.rcParams.update({'font.size':12,'svg.fonttype':'none','svg.hashsalt':'WWL-M15','font.family':'DejaVu Sans'})
    import cairosvg
    from PIL import Image, ImageOps
    for name,svg in {'inverter-topology':topology(),'kmap':kmap(),'sram6t':sram(),'buses':buses()}.items():(output/(name+'.svg')).write_text(svg)
    m=model.margins();d=m['vdd'];vt=m['vt']
    fig=Figure(figsize=(4.25,4.25),dpi=100);FigureCanvasAgg(fig);ax=fig.add_subplot(111)
    for lo,hi in ((0,d/2-1e-5),(d/2+1e-5,d)):
        xs=np.linspace(lo,hi,350);ax.plot(xs,[model.vtc(float(x)) for x in xs],color='#111',lw=2)
    ax.plot([d/2]*2,[d/2-vt,d/2+vt],ls=':',color='#111',label='Nonunique at D/2')
    for key in ('vil','vih'):ax.axvline(m[key],ls='--',color='#555',lw=1)
    ax.axhline(m['vol'],ls=':',color='#555');ax.axhline(m['voh'],ls=':',color='#555')
    ax.text(.12,2.45,'D = 3.3 V\nT = 0.6 V',fontsize=11)
    ax.text(.12,.65,'NML = NMH = 1.125 V',fontsize=10)
    ax.set(xlim=(0,d),ylim=(0,d),xlabel='Input u (V)',ylabel='Output y (V)',title='VTC: symmetric square-law')
    ax.set_xticks([0,m['vil'],m['vih'],d],['0','VIL\n1.3875','VIH\n1.9125','3.3'],fontsize=9)
    ax.set_yticks([0,m['vol'],m['voh'],d],['0','VOL\n0.2625','VOH\n3.0375','3.3'],fontsize=9)
    fig.subplots_adjust(left=.21,bottom=.20,right=.96,top=.87)
    fig.savefig(output/'inverter-vtc.svg',metadata={'Date':None});fig.savefig(output/'inverter-vtc-plot.png')
    fig=Figure(figsize=(4.25,4.0),dpi=100);FigureCanvasAgg(fig);ax=fig.add_subplot(111)
    ts=np.linspace(0,100e-9,201);ys=[model.charge(float(t)) for t in ts]
    ax.plot(ts*1e9,ys,'k-',label='charge');ax.plot(ts*1e9,[d-y for y in ys],'k--',label='discharge')
    ax.axvline(20*np.log(2),color='#555',ls=':');ax.axhline(d/2,color='#555',ls=':')
    ax.text(25,.75,'R=1k, CL=20 pF\nt50=13.863 ns',fontsize=11)
    ax.set(xlabel='Time (ns)',ylabel='Output y (V)',title='RC load: stated approximation',xlim=(0,100),ylim=(0,3.5));ax.legend(fontsize=10,loc='upper right')
    fig.subplots_adjust(left=.16,bottom=.17,right=.95,top=.87);fig.savefig(output/'inverter-load.svg',metadata={'Date':None});fig.savefig(output/'inverter-load-plot.png')
    fig=Figure(figsize=(4.25,4.3),dpi=100);FigureCanvasAgg(fig)
    for k,(label,times,values) in enumerate((('Static 1 hazard (transport)',[-1,3,6,9],[1,0,1,1]),('Dynamic: x XOR xd2 XOR xd5',[-1,0,2,5,9],[0,1,0,1,1])),1):
        ax=fig.add_subplot(2,1,k);ax.step(times,values,where='post',color='#111',lw=2);ax.set(xlim=(-1,9),ylim=(-.2,1.3),yticks=[0,1],xlabel='Time (ns)',title=label);ax.grid(axis='x',ls=':')
    fig.subplots_adjust(left=.12,right=.95,bottom=.14,top=.88,hspace=.85);fig.savefig(output/'hazards.svg',metadata={'Date':None});fig.savefig(output/'hazards-plot.png')
    (output/'figure-data.json').write_text(json.dumps({'model':model.results(),'vtc_midpoint':'nonunique; excluded from sampled branches','vtc_samples_per_branch':350,'load_samples':201},indent=2,allow_nan=False)+'\n')
    # Inline diagrams contain a white substrate, so dark backgrounds keep text readable.
    for svg in sorted(output.glob('*.svg')):
        for width in (360,425):
            png=output/f'{svg.stem}-{width}.png';cairosvg.svg2png(url=str(svg),write_to=str(png),output_width=width)
            im=Image.open(png).convert('RGB');ImageOps.grayscale(im).save(output/f'{svg.stem}-{width}-gray.png')
            dark=Image.new('RGB',(im.width+24,im.height+24),'#171717');dark.paste(im,(12,12));dark.save(output/f'{svg.stem}-{width}-dark.png')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args();generate(args.output)

if __name__=='__main__':main()
