"""Lazy deterministic generator. Required output must be outside vault/candidate."""
from pathlib import Path
import argparse, json, math
from models import triple_loop,triple_poles,triple_step,radius,delay_limit,delay_phase_crossings,robust_onepole,injection

def generate(output):
    output=Path(output).resolve()
    here=Path(__file__).resolve().parent
    vault=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    candidate=here.parents[2]
    if output==vault or vault in output.parents or output==candidate or candidate in output.parents:
        raise ValueError('output must be outside main vault and candidate')
    if output.exists() and any(output.iterdir()): raise ValueError('output must be empty; preserve existing artifacts')
    output.mkdir(parents=True,exist_ok=True); assets=output/'assets'; assets.mkdir(exist_ok=True)
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_svg import FigureCanvasSVG
    from matplotlib import rc_context
    import cairosvg
    def plot(name,setup,height=480):
        with rc_context({'font.family':'DejaVu Sans','font.size':16,'svg.fonttype':'none','svg.hashsalt':'wwl-feedback1-fixed'}):
            fig=Figure(figsize=(7.2,height/100),dpi=100); FigureCanvasSVG(fig)
            setup(fig,np)
            fig.savefig(assets/(name+'.svg'),metadata={'Date':None},bbox_inches='tight')
    def svg(name,body,height=480):
        text='<svg xmlns="http://www.w3.org/2000/svg" width="720" height="'+str(height)+'" viewBox="0 0 720 '+str(height)+'"><defs><marker id="arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="#222"/></marker></defs><rect width="100%" height="100%" fill="white"/><g stroke="#222" stroke-width="2.5" fill="none">'+body+'</g></svg>'
        (assets/(name+'.svg')).write_text(text,encoding='utf-8')
    def txt(x,y,s,size=22): return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="#111" stroke="none">{s}</text>'
    def line(x1,y1,x2,y2,arrow=False): return f'<path d="M{x1} {y1} L{x2} {y2}"'+(' marker-end="url(#arr)"' if arrow else '')+'/>'
    def ground(x,y): return line(x,y,x,y+12)+line(x-12,y+12,x+12,y+12)+line(x-8,y+18,x+8,y+18)+line(x-4,y+24,x+4,y+24)
    def node(x,y): return f'<circle cx="{x}" cy="{y}" r="4" fill="#222"/>'
    def res(x,y,w=64): return line(x,y,x+10,y)+f'<rect x="{x+10}" y="{y-8}" width="{w-20}" height="16"/>'+line(x+w-10,y,x+w,y)
    def cap(x,y): return line(x,y,x+22,y)+line(x+22,y-13,x+22,y+13)+line(x+30,y-13,x+30,y+13)+line(x+30,y,x+52,y)
    b=txt(20,28,'Four ideal port models: loaded A, dimensionless L',23)
    for j,(title,mix,gain,beta,samp) in enumerate([('Series / voltage','e=vi-vf','Av [V/V]','vf=beta vo [V]','vo [V]'),('Shunt / voltage','ie=iin-if','Rm [ohm]','if=beta vo [A]','vo [V]'),('Series / current','e=vi-vf','Gm [S]','vf=beta io [V]','io [A]'),('Shunt / current','ie=iin-if','Ai [A/A]','if=beta io [A]','io [A]')]):
        y=66+j*125
        b+=txt(20,y,title,22)+txt(20,y+32,mix,19)+f'<rect x="245" y="{y-18}" width="145" height="48"/>'+txt(254,y+13,gain,20)+line(170,y+6,245,y+6,True)+line(390,y+6,620,y+6,True)+txt(535,y-3,samp,20)
        b+=f'<path d="M590 {y+6} L590 {y+61} L180 {y+61} L180 {y+6}" marker-end="url(#arr)"/>'+txt(260,y+54,beta,20)
        b+=txt(615,y+48,'0',18)+line(620,y+30,650,y+30)+ground(650,y+30)
        b+=node(590,y+6)
    b+=txt(20,583,'Signal ports: series KVL / shunt KCL; ideal unilateral blocks',20)
    svg('01-ports',b,600)
    b=txt(18,30,'Same loop, four independent voltage injections',23)
    for x,y,s in [(90,150,'+'),(290,150,'+'),(550,150,'+')]: b+=f'<circle cx="{x}" cy="{y}" r="20"/>'+txt(x-8,y+7,s,24)
    b+=line(20,150,70,150,True)+txt(20,130,'r')+line(110,150,140,150,True)+f'<rect x="140" y="125" width="100" height="50"/>'+txt(175,157,'C')+line(240,150,270,150,True)+txt(250,133,'u')+line(310,150,355,150,True)+f'<rect x="355" y="125" width="100" height="50"/>'+txt(390,157,'P')+line(455,150,530,150,True)+line(570,150,685,150,True)+txt(650,132,'y')
    b+=line(290,70,290,130,True)+txt(270,59,'di')+line(550,70,550,130,True)+txt(530,59,'do')
    b+=f'<path d="M620 150 L620 260 L90 260 L90 170" marker-end="url(#arr)"/>'+node(620,150)+line(90,65,90,130,True)+txt(62,55,'n (-)')+txt(98,245,'y (-)',18)
    b+=txt(25,335,'u = C(r-y-n)    y = P(u+di)+do',24)+txt(25,383,'y:  T r + PS di + S do - T n',24)+txt(25,431,'u: CS r - T di - CS do - CS n',24)
    svg('02-injections',b)
    def bode(fig,np):
        axes=fig.subplots(3,1); x=np.logspace(-2,2,600)
        for k,sty in [(1,'-'),(8,'--'),(20,':')]:
            v=k/(1+1j*x)**3
            axes[0].semilogx(x,20*np.log10(abs(v)),sty,color='black',label=f'K={k}')
            axes[1].semilogx(x,-3*np.arctan(x)*180/math.pi,sty,color='black')
            t=np.linspace(0,6,241); axes[2].plot(t,[triple_step(k,float(q)) for q in t],sty,color='black')
        axes[0].axhline(0,color='.5',lw=1); axes[0].set_ylabel('|L| [dB]');axes[0].legend(ncol=3,fontsize=12)
        axes[1].axhline(-180,color='.5',lw=1);axes[1].set_ylabel('phase [deg]');axes[1].set_xlabel('omega/p [rad/s divided by rad/s]')
        axes[2].set_xlabel('p t [dimensionless]');axes[2].set_ylabel('unit step y')
        for ax in axes: ax.grid(True,alpha=.2)
        fig.tight_layout()
    plot('03-bode',bode,850)
    def nyquist(fig,np):
        ax=fig.subplots(); w=np.concatenate((-np.logspace(3,-4,1500),[0],np.logspace(-4,3,1500)))
        for k,sty in [(1,'-'),(8,'--'),(20,':')]:
            z=k/(1+1j*w)**3; ax.plot(z.real,z.imag,sty,color='black',label=f'K={k}')
            for wi in (-1,1):
                z1=k/(1+1j*wi)**3; z2=k/(1+1j*(wi+.12))**3
                ax.annotate('',xy=(z2.real,z2.imag),xytext=(z1.real,z1.imag),arrowprops={'arrowstyle':'->','color':'black'})
        ax.plot([-1],[0],'x',color='black',ms=10);ax.annotate('-1: K=8 boundary',(-1,0),xytext=(-6,2),arrowprops={'arrowstyle':'->'})
        ax.set_title('P=0: N=Z; K=1: 0, K=20: 2\nK=8 passes -1 (boundary)',fontsize=13);ax.set_xlim(-7,21);ax.set_ylim(-16,16);ax.set_xlabel('Re L');ax.set_ylabel('Im L');ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(fontsize=13);fig.tight_layout()
    plot('04-nyquist',nyquist,650)
    def roots(fig,np):
        ax=fig.subplots(); ks=np.linspace(.001,30,700)
        for j in range(3):
            z=[triple_poles(float(k))[j] for k in ks];ax.plot([v.real for v in z],[v.imag for v in z],color='black')
        for k,m in [(1,'o'),(8,'s'),(20,'^')]:
            z=triple_poles(k);ax.plot([v.real for v in z],[v.imag for v in z],m,color='black',fillstyle='none',label=f'K={k}')
        ax.axvline(0,color='.5',linestyle='--');ax.plot([-1],[0],'x',color='black');ax.set_xlabel('Re s/p');ax.set_ylabel('Im s/p');ax.set_xlim(-4.5,1);ax.set_ylim(-3,3);ax.grid(alpha=.2);ax.legend(fontsize=14);fig.tight_layout()
    plot('05-root-locus',roots,600)
    b=txt(20,28,'Physical passive networks: each node returns to 0',22)
    # lead: vo--parallel Rf/Cf--vb--Rg--ground
    b+=txt(20,72,'Lead: Rf || Cf; beta = vb/vo')+line(20,112,100,112)+node(100,112)+line(100,112,100,90)+res(100,90,160)+line(260,90,260,112)+line(100,112,100,140)+cap(140,140)+line(100,140,140,140)+line(192,140,260,140)+line(260,140,260,112)+line(260,112,370,112)+node(370,112)+res(370,112,120)+line(490,112,550,112)+ground(550,112)+txt(22,105,'vo')+txt(375,91,'vb')+txt(160,169,'Cf')+txt(403,99,'Rg')
    b+=txt(20,225,'Lag: F = v/vi (buffer input unloaded)')+txt(20,266,'vi')+line(20,280,100,280)+res(100,280,150)+line(250,280,320,280)+node(320,280)+line(320,280,390,280)+res(390,280,100)+cap(500,280)+line(490,280,500,280)+line(552,280,600,280)+ground(600,280)+txt(150,267,'R1')+txt(325,265,'v')+txt(413,267,'R2')+txt(513,320,'C')
    b+=txt(20,382,'Isolation: sample vi; RL || CL at vL')+txt(20,423,'vi')+line(20,438,105,438)+res(105,438,120)+line(225,438,330,438)+node(330,438)+txt(130,423,'Riso')+txt(336,423,'vL')+line(330,438,400,438)+res(400,438,110)+line(510,438,600,438)+ground(600,438)
    b+=line(330,438,330,510)+line(330,510,400,510)+cap(400,510)+line(452,510,600,510)+line(600,510,600,438)+txt(425,425,'RL')+txt(416,551,'CL')+txt(20,597,'Ports are vi/vo relative to common 0, not floating sources',20)
    svg('06-compensation',b,620)
    b=txt(20,30,'Two-node common-source small-signal model',24)
    b+=txt(15,117,'iin')+line(20,140,150,140,True)+node(150,140)+txt(130,123,'v1')+line(150,140,150,60)+line(150,60,270,60)+cap(270,60)+line(322,60,540,60)+line(540,60,540,140)+node(540,140)+txt(545,123,'v2')+txt(260,94,'Cgd')
    # Each shunt to common ground drawn as horizontal branch from down node; controlled current diamond vertical
    b+=line(150,140,150,235)+res(150,235,90)+line(240,235,280,235)+ground(280,235)+txt(177,221,'G1')+line(150,235,150,300)+cap(150,300)+line(202,300,280,300)+line(280,300,280,235)+txt(173,339,'C1')
    b+=line(540,140,540,235)+res(540,235,90)+line(630,235,675,235)+ground(675,235)+txt(567,221,'G2')+line(540,235,540,300)+cap(540,300)+line(592,300,675,300)+line(675,300,675,235)+txt(560,339,'C2')
    b+=line(540,140,410,140)+line(410,140,410,187)+f'<path d="M410 187 L434 215 L410 243 L386 215 Z"/>'+line(410,243,410,278)+ground(410,278)+line(410,201,410,228,True)+txt(295,368,'gm v1 flows from v2 to 0',22)
    b+=txt(20,423,'v2/v1 = -(gm-s Cgd)/(G2+s(C2+Cgd))',23)+txt(20,468,'RHP zero: s = +gm/Cgd [rad/s]',23)
    svg('07-miller',b,500)
    b=txt(20,30,'Wien equal-RC network and controlled amplifier',23)
    # amplifier vo output triangle, plus vb bottom? create left amp ports and network return
    b+=f'<path d="M140 80 L140 200 L260 140 Z"/>'+txt(155,114,'+')+txt(155,179,'-')+line(260,140,640,140)+node(620,140)+txt(620,119,'vo')
    b+=line(620,140,620,255)+line(620,255,560,255)+res(460,255,100)+line(560,255,560,255)+cap(370,255)+line(422,255,460,255)+line(320,255,370,255)+node(320,255)+txt(489,239,'R')+txt(382,292,'C')+txt(296,240,'vb')
    b+=f'<path d="M320 255 L70 255 L70 105 L140 105"/>'+line(320,255,320,325)+res(320,325,100)+line(420,325,620,325)+ground(620,325)+txt(345,310,'R')+line(320,325,320,385)+cap(350,385)+line(320,385,350,385)+line(402,385,620,385)+line(620,385,620,325)+txt(362,422,'C')
    b+=f'<path d="M620 140 L680 140 L680 55 L400 55 M280 55 L30 55 L30 175 L60 175 C65 163 75 163 80 175 L140 175"/>'+res(280,55,120)+txt(320,84,'Rf*')+line(90,175,90,335)+res(90,335,100)+line(190,335,235,335)+ground(235,335)+txt(110,321,'Rg*')
    b+=txt(20,475,'*Gain control changes Rf/Rg; no device amplitude guarantee',20)
    b+=txt(20,549,'Original amplitude model: mu=10, alpha=10; r*=1 V',22)
    b+=line(85,585,85,760)+line(85,760,665,760)+txt(20,570,'r [V]',20)+txt(270,805,'t [s]',21)
    for yv in (0,1,2):
        yy=760-yv*80; b+=line(80,yy,665,yy)+txt(50,yy+7,str(yv),18)
    for tv in (0,.5,1):
        xx=85+tv*550; b+=line(xx,760,xx,768)+txt(xx-10,790,str(tv),18)
    for ri,sty in [(.01,''),(.5,' stroke-dasharray="9 5"'),(2,' stroke-dasharray="2 5"')]:
        pts=[]
        for j in range(201):
            tt=j/200; rr=radius(tt,ri,10,10);pts.append(f'{85+550*tt:.3f},{760-80*rr:.3f}')
        b+='<polyline points="'+' '.join(pts)+'"'+sty+'/>'
    b+=txt(130,582,'r0: 0.01 solid; 0.5 dashed; 2 dotted [V]',18)
    svg('08-wien-amplitude',b,825)
    b=txt(20,28,'Coupled capacitor nodes: currents powered by supplies',22)
    for x,label,g,cc in [(130,'x','G1','C1'),(500,'y','G2','C2')]:
        b+=node(x,95)+txt(x-10,79,label)+line(x,95,x,160)+res(x,160,80)+line(x+80,160,x+130,160)+ground(x+130,160)+txt(x+22,146,g)+line(x,160,x,215)+cap(x,215)+line(x+52,215,x+130,215)+line(x+130,215,x+130,160)+txt(x+23,250,cc)
        b+=line(x,95,x-55,95)+line(x-55,95,x-55,115)+f'<path d="M{x-55} 115 L{x-35} 140 L{x-55} 165 L{x-75} 140 Z"/>'+line(x-55,165,x-55,185)+ground(x-55,185)+line(x-55,154,x-55,126,True)
    b+=txt(18,287,'Into x: gm12 y [A]    Into y: gm21 x [A]',22)+txt(18,334,'A = [-a, b; c, -d]   det A = ad-bc',24)+txt(18,387,'Delay: angle = -atan(omega/p)-omega tau',22)+txt(18,432,'Every phase crossing: (2m+1) pi, m=0,1,...',22)+txt(18,480,'Robust: stable nominal + stable Delta; ||WT||inf &lt; 1',20)
    svg('09-nested-delay-robust',b,505)
    for path in sorted(assets.glob('*.svg')):
        for width in (360,425): cairosvg.svg2png(url=str(path),write_to=str(path.with_name(path.stem+f'-{width}.png')),output_width=width)
    result={'parameters':'teaching only; not device or hardware measurements','triple':{str(k):{'poles_over_p':[[z.real,z.imag] for z in triple_poles(k)],'step_at_pt2':triple_step(k,2)} for k in (1,8,20)},'injections':{s:injection(2,3,**{s: .07}) for s in ('r','di','do','n')},'delay':delay_limit(2,1000),'phase_crossings_below_30000':delay_phase_crossings(1000,.001,30000),'robust_norm_exact':robust_onepole(9,.2),'radius_at_05':radius(.5,.01,10,10),'radius_at_1':radius(1,.01,10,10)}
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True,type=Path); ns=ap.parse_args();generate(ns.output)
if __name__=='__main__': main()
