"""Self drawn topology and teaching curves. Pure import, explicit output."""
import argparse
from pathlib import Path
import math
from xml.sax.saxutils import escape
import transistor_lab as t

class D:
    def __init__(self,h=600):
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="{h}" viewBox="0 0 600 {h}"><rect width="100%" height="100%" fill="white"/><defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"/></marker></defs><g stroke="black" stroke-width="2.5" fill="none">']
    def line(self,x,y,X,Y,arrow=False,dash=False):self.p.append(f'<path d="M{x} {y}L{X} {Y}"'+(' marker-end="url(#a)"' if arrow else '')+(' stroke-dasharray="7 5"' if dash else '')+'/>')
    def box(self,x,y,w,h):self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>')
    def text(self,x,y,s,size=21):self.p.append(f'<text x="{x}" y="{y}" fill="black" stroke="none" font-family="DejaVu Sans,sans-serif" font-size="{size}">{escape(s)}</text>')
    def node(self,x,y):self.p.append(f'<circle cx="{x}" cy="{y}" r="4" fill="black"/>')
    def r(self,x,y,h,label):self.line(x,y,x,y+10);self.box(x-9,y+10,18,h-20);self.line(x,y+h-10,x,y+h);self.text(x+16,y+h/2+7,label,19)
    def cs(self,x,y,h,label):
        m=y+h/2;self.line(x,y,x,m-25);self.p.append(f'<path d="M{x} {m-25}l23 25l-23 25l-23 -25z"/>');self.line(x,m-15,x,m+15,True);self.line(x,m+25,x,y+h);self.text(x+29,m+7,label,18)
    def cv(self,x,y,h,label):
        m=y+h/2;self.line(x,y,x,m-6);self.line(x-15,m-6,x+15,m-6);self.line(x-15,m+6,x+15,m+6);self.line(x,m+6,x,y+h);self.text(x+17,m+7,label,19)
    def ch(self,x,y,w,label):
        m=x+w/2;self.line(x,y,m-6,y);self.line(m-6,y-15,m-6,y+15);self.line(m+6,y-15,m+6,y+15);self.line(m+6,y,x+w,y);self.text(m-22,y-22,label,19)
    def ground(self,x,y):self.line(x,y,x,y+10);self.line(x-14,y+10,x+14,y+10);self.line(x-9,y+16,x+9,y+16);self.line(x-4,y+22,x+4,y+22)
    def save(self,p):p.write_text(''.join(self.p)+'</g></svg>')

def topology(o):
    d=D(620);d.text(20,30,'V20  Planar NMOS, schematic not to scale',22)
    d.box(60,140,480,170);d.text(245,280,'p-type body B');d.box(80,140,100,70);d.text(93,182,'n+ S');d.box(420,140,100,70);d.text(432,182,'n+ D')
    d.box(195,112,210,16);d.text(22,112,'oxide',19);d.line(86,116,195,120);d.box(195,60,210,32);d.text(279,83,'G')
    d.line(180,150,420,150,dash=True);d.text(212,206,'inversion electrons',19)
    d.line(130,140,130,62);d.text(100,56,'S');d.line(470,140,470,62);d.text(460,56,'D');d.line(300,310,300,340);d.text(318,340,'B');d.line(555,140,555,240,True);d.text(550,266,'x')
    d.text(24,387,'VGS = VG - VS     VDS = VD - VS');d.text(24,420,'VSB = VS - VB     VGB = VGS + VSB')
    for x,label,q in [(25,'accumulation','+ + +'),(220,'depletion','- - -'),(415,'inversion','e e e')]:
        d.box(x,470,160,100);d.line(x,490,x+160,490);d.text(x+7,462,label,18);d.text(x+14,518,q);d.text(x+9,550,'p body',18)
    d.text(24,602,'Charge types only; thickness is not inferred',20);d.save(o/'V20-structure.svg')
    d=D(650);d.text(15,30,'V21  Four terminals: body arrow p to n',21)
    for x,name,rev in [(145,'NMOS: p body',False),(430,'PMOS: n body',True)]:
        d.text(x-103,65,name);d.line(x,100,x,250);d.line(x,100,x+60,100);d.line(x,250,x+60,250);d.line(x-30,135,x-30,215);d.line(x-100,175,x-30,175)
        d.text(x-106,160,'G');d.text(x+66,104,'D');d.text(x+66,258,'S')
        if rev:d.line(x+3,175,x+85,175,True)
        else:d.line(x+85,175,x+3,175,True)
        d.text(x+92,182,'B',19)
    d.text(20,302,'NMOS: ID > 0 D -> S; VS, VD >= VB',20);d.text(20,337,'PMOS: J = -ID > 0 S -> D; VS, VD <= VB',20)
    d.text(20,376,'N body diodes: B(anode) -> D/S(cathode)',19);d.text(20,412,'P body diodes: D/S(anode) -> B(cathode)',19)
    for x,name,rev in [(140,'NPN',False),(415,'PNP',True)]:
        d.text(x-65,464,name);d.line(x,490,x,575);d.line(x-75,535,x,535);d.text(x-94,540,'B');d.line(x,510,x+65,475);d.text(x+74,483,'C')
        if rev:d.line(x+65,595,x,560,True)
        else:d.line(x,560,x+65,595,True)
        d.text(x+75,603,'E')
    d.text(15,637,'Emitter arrow: NPN B -> E, PNP E -> B',20);d.save(o/'V21-polarity.svg')
    d=D(540);d.text(18,30,'V21  NPN Ebers-Moll transport network',22)
    d.line(230,85,535,85);d.text(545,92,'C');d.line(230,405,535,405);d.text(545,412,'E');d.line(35,245,125,245);d.text(20,229,'B');d.line(125,160,125,340)
    d.cs(230,85,320,'IT = Is(f-r)');d.line(125,160,440,160);d.line(440,160,440,85,True);d.text(330,141,'Is r / betaR',19);d.line(125,340,440,340);d.line(440,340,440,405,True);d.text(326,324,'Is f / betaF',19)
    d.node(125,245);d.node(230,85);d.node(230,405);d.text(18,461,'f = exp(VBE/UT)-1, r = exp(VBC/UT)-1',20);d.text(18,495,'Signed arrows may carry negative currents',20);d.text(18,531,'IC + IB + IE = 0; no breakdown or storage',20);d.save(o/'V21-bjt-transport.svg')
    d=D(650);d.text(18,30,'V22  DC bias: source and body explicit',22);d.text(440,65,'VDD');d.r(450,75,80,'RD');d.line(450,155,450,213);d.text(469,208,'D');d.line(450,213,450,275);d.line(428,225,428,263);d.line(160,244,428,244);d.text(20,233,'VGQ + vg',20)
    d.line(450,275,450,293);d.text(468,280,'S');d.r(450,293,70,'RS');d.ground(450,363);d.line(450,249,530,249);d.text(537,254,'B');d.text(20,288,'B fixed by separate body bias',20)
    d.line(15,407,585,407,dash=True);d.text(15,441,'Small signal: ro and both currents D -> S',21);d.line(70,480,520,480);d.text(540,487,'D');d.line(70,597,520,597);d.text(540,604,'S');d.r(100,480,117,'ro');d.cs(255,480,117,'gm(vg-vs)');d.cs(435,480,117,'gmb(vb-vs)');d.text(15,636,'G/B: controls only, no input conductance',20);d.save(o/'V22-mos-nodes.svg')
    # Full loaded network: parallel resistor labels fit their separate branches.
    d=D(580);d.text(14,30,'V22  S = B = AC ground: loaded NMOS',22);d.text(12,105,'vsrc');d.line(20,125,90,125);d.box(90,115,70,20);d.text(90,98,'Rsig',20);d.line(160,125,220,125);d.node(220,125);d.text(210,105,'G');d.ch(220,125,230,'Cgd');d.node(450,125);d.text(466,110,'D = vd')
    d.cv(220,125,160,'Cgs');d.ground(220,285);d.line(450,125,450,355);d.line(80,355,540,355);d.node(450,355)
    d.r(80,355,150,'RD');d.ground(80,505);d.r(195,355,150,'RL');d.ground(195,505);d.r(310,355,150,'ro');d.ground(310,505);d.cs(435,355,150,'gm vg');d.ground(435,505);d.line(450,125,540,125);d.node(540,125);d.cv(540,125,160,'CL');d.ground(540,285)
    d.text(13,558,'ro -> infinite for gds = 0; Cgd joins G-D',21);d.save(o/'V22-ac-nodes.svg')
    d=D(550);d.text(15,30,'V22  NPN: emitter at AC ground',23);d.text(15,108,'vsrc');d.line(25,130,90,130);d.box(90,120,70,20);d.text(88,100,'Rsig',20);d.line(160,130,225,130);d.text(222,109,'B');d.r(225,130,145,'rpi');d.ground(225,275)
    d.line(320,130,545,130);d.text(339,110,'C = vc');d.cs(320,130,145,'gm vbe');d.ground(320,275);d.r(535,130,145,'ro');d.ground(535,275);d.r(425,130,145,'RC||RL');d.ground(425,275)
    d.text(15,360,'vbe = vB-vE; gm vbe flows C -> E',21);d.text(15,406,'rpi connects B-E; ro connects C-E',21);d.text(15,451,'All grounds share E; base is a control',20);d.text(15,502,'Source attenuation: 2.6k / (20k + 2.6k)',20);d.save(o/'V22-bjt-nodes.svg')

    d=D(650);d.text(15,30,'V22  Four-terminal loaded small signal',22)
    d.line(65,110,525,110);d.text(545,115,'D')
    d.r(65,110,330,'RD');d.ground(65,440);d.r(150,110,330,'RL');d.ground(150,440)
    d.line(245,330,525,330);d.text(545,337,'S');d.r(255,110,220,'ro')
    d.cs(450,110,220,'i controlled');d.r(380,330,110,'RS');d.ground(380,440)
    d.text(20,515,'i = gm(vg-vs) + gmb(vb-vs)',23)
    d.text(20,554,'Direction D -> S; G/B are voltage controls',20)
    d.text(20,591,'B fixed: vb=0.  B tied to S: vb=vs.',21)
    d.text(20,632,'RD, RL and RS end at the same AC ground',20)
    d.save(o/'V22-body-network.svg')

def charts(o, Figure, FigureCanvasAgg, np):
    def fig(h=4.5):
        f=Figure(figsize=(5.5,h),layout='constrained');FigureCanvasAgg(f);return f
    def save(f,n):f.savefig(o/(n+'.svg'))
    f=fig();a=f.subplots();x=np.linspace(0,5,251)
    for ov,ls in [(0.5,':'),(1,'-'),(1.5,'--')]:
        a.plot(x,[t.mos(.5+ov,float(v),lam=0)['id']*1e3 for v in x],ls,label=f'OV={ov:g} V')
        a.plot([ov,ov],[0,ov*ov],color='gray',ls='--',lw=1)
    a.plot(x,(5-x)/2,'-.',color='black',label='5V/2kohm load');a.plot(3,1,'ko');a.annotate('Q: 3V, 1mA',(3,1),xytext=(2.2,0.68),fontsize=12)
    a.set(xlabel='VDS (V) / PMOS VSD (V)',ylabel='ID (mA) / PMOS J=-ID',ylim=(0,3),title='V21  Constant-gate curves');a.legend(fontsize=11);a.grid(alpha=.3);save(f,'V21-curves')
    f=fig();a=f.subplots();x=np.linspace(.15,.49,160)
    for n,ls in [(1,':'),(1.5,'-'),(2,'--')]:a.semilogy(x,[t.weak(float(v),.2,n=n)['id'] for v in x],ls,label=f'n={n:g}')
    a.set(xlabel='VGS (V), VTH=0.5 V',ylabel='ID (A)',title='V23  Weak inversion, I0=1uA');a.legend(fontsize=12);a.grid(alpha=.3);save(f,'V23-weak')
    f=fig(6);a,b=f.subplots(2,1,sharex=True);freq=np.logspace(2,8,300)
    for cgd,ls,label in [(2e-12,'-','Cgd=2pF'),(0,'--','Cgd removed')]:
        h=np.array([t.ac_gain(float(v),cgd=cgd) for v in freq]);a.semilogx(freq,20*np.log10(abs(h)),ls,label=label);b.semilogx(freq,np.unwrap(np.angle(h))*180/math.pi,ls)
    a.set(ylabel='Gain (dB)',title='V24  Same Q: two-node AC');b.set(xlabel='Frequency (Hz)',ylabel='Phase (degree)');a.legend(fontsize=11)
    for ax in [a,b]:ax.grid(alpha=.3)
    save(f,'V24-ac')

def generate(output):
    # Dependency initialization (including font caches) is authorized only here.
    import cairosvg
    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import numpy as np
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    matplotlib.rcParams.update({'font.size':13,'svg.fonttype':'none'})
    topology(output);charts(output,Figure,FigureCanvasAgg,np)
    for svg in output.glob('*.svg'):
        for w in [360,425]:cairosvg.svg2png(url=str(svg),write_to=str(svg.with_name(svg.stem+f'-{w}.png')),output_width=w)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    generate(a.output)

if __name__=='__main__':main()
