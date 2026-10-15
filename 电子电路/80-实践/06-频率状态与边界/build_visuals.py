"""Original 425 px vertical diagrams; explicit --output, no plotting import on import."""
import argparse
import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from frequency_state_lab import rc_h, rc_started_cosine, db_phase, rc_asymptotic_db, second_order_h, zero_pair_h

COLORS=['#1265a8','#b54d19','#167747']


def text(x,y,value,size=15,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(str(value))}</text>'


def line(x1,y1,x2,y2,color='#222',dash=False):
    return f'<path d="M{x1} {y1}L{x2} {y2}" style="stroke:{color}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>'


def arrow(x1,y1,x2,y2):
    return f'<path d="M{x1} {y1}L{x2} {y2}" marker-end="url(#arrow)"/>'


def svg(height,title,description,body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7Z" fill="#222"/></marker></defs><rect width="425" height="{height}" style="fill:white;stroke:none"/><style>text{{font-family:DejaVu Sans,sans-serif;fill:#151515;stroke:none}} path,rect,circle{{stroke:#222;stroke-width:1.7;fill:none}}</style>{body}</svg>'''


def panel(top,title,xrange,yrange,curves,xlabel,ylabel,xticks,yticks,log=False):
    left=62;right=398;upper=top+52;bottom=top+225
    def xp(x):
        if log:return left+(math.log10(x)-math.log10(xrange[0]))/(math.log10(xrange[1])-math.log10(xrange[0]))*(right-left)
        return left+(x-xrange[0])/(xrange[1]-xrange[0])*(right-left)
    def yp(y):return bottom-(y-yrange[0])/(yrange[1]-yrange[0])*(bottom-upper)
    b=text(18,top+20,title,17)+text(left,upper-12,ylabel,14)
    b+=line(left,upper,left,bottom)+line(left,bottom,right,bottom)
    for value,label in xticks:
        x=xp(value);b+=line(x,bottom,x,bottom+5)+text(x,bottom+22,label,13,'middle')
    for value,label in yticks:
        y=yp(value);b+=line(left-5,y,left,y)+text(left-9,y+4,label,13,'end')
    b+=text((left+right)/2,bottom+44,xlabel,14,'middle')
    for xs,ys,color,dash in curves:
        points=' '.join(f'{xp(x):.4f},{yp(y):.4f}' for x,y in zip(xs,ys))
        b+=f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.3"'+(' stroke-dasharray="6 4"' if dash else '')+'/>'
    return b


def legend(y,labels):
    b=''
    for k,(label,color,dash) in enumerate(labels):
        b+=line(22,y+23*k,48,y+23*k,color,dash)+text(58,y+5+23*k,label,14)
    return b


def make_figures():
    figures={}
    t=[k*.01 for k in range(501)] # milliseconds
    volts=[1-.6*math.exp(-x) for x in t]
    sine=[math.sin(2*x) for x in t]
    grow=[math.exp(x) for x in t]
    b=panel(0,'Initial and final values',(0,5),(-1.1,1.2),[(t,volts,COLORS[0],False),(t,sine,COLORS[1],False)],'time (ms)','voltage (V)',[(0,'0'),(1,'1'),(3,'3'),(5,'5')],[(-1,'-1'),(0,'0'),(1,'1')])
    b+=legend(288,[('RC: .4 V -> 1 V',COLORS[0],False),('sin(2000 t): no final value',COLORS[1],False)])
    b+=panel(350,'Growth has no final value',(0,5),(0,160),[(t,grow,COLORS[2],False)],'time (ms)','exp(1000 t) (V)',[(0,'0'),(1,'1'),(3,'3'),(5,'5')],[(0,'0'),(80,'80'),(160,'160')])
    b+=text(22,645,'sX: RC pole -1000 /s -> allowed',14)+text(22,672,'sin: imaginary poles -> fails',14)+text(22,699,'growth: +1000 /s -> fails',14)
    figures['value-boundaries']=svg(730,'Initial and final value boundaries','RC has finite initial .4 V and final 1 V; sine and growth do not have final values. Pole tests label response sX, not only H.',b)
    b=text(18,25,'RC frequency response',18)+text(18,51,'R=1 kohm, C=1 uF, w=1000 rad/s',14)
    b+=line(80,145,350,145)+line(180, 75,180,235)
    b+=arrow(180,145,270,235)+text(283,218,'H=(1-j)/2',15)
    b+=text(345,136,'Re H',13,'end')+text(190,84,'Im H',13)+text(260,139,'.5',13)+text(150,235,'-.5',13)
    times=[k*.02 for k in range(501)]
    steady=[.5*math.cos(x)+.5*math.sin(x) for x in times]
    started=[rc_started_cosine(x/1000) for x in times]
    b+=panel(265,'Full response includes initial state',(0,10),(-1.1,1.1),[(times,[math.cos(x) for x in times],COLORS[1],False),(times,steady,COLORS[0],True),(times,started,COLORS[2],False)],'time (ms)','voltage (V)',[(0,'0'),(2,'2'),(6,'6'),(10,'10')],[(-1,'-1'),(0,'0'),(1,'1')])
    b+=legend(552,[('input: 1 V peak cosine',COLORS[1],False),('steady: .7071 V peak',COLORS[0],True),('started: v(0+)=.4 V',COLORS[2],False)])
    b+=text(18,650,'f=w/(2 pi)=159.154943 Hz',15)
    figures['rc-frequency']=svg(680,'RC frequency response and initial state','Complex gain and time-domain input, steady cosine, and switched cosine from .4 V; f and angular frequency explicitly separated.',b)
    ws=[10**(1+k/100) for k in range(401)]
    mags=[db_phase(rc_h(w))[0] for w in ws];phases=[db_phase(rc_h(w))[1] for w in ws]
    xt=[(10,'10'),(100,'100'),(1000,'1k'),(10000,'10k'),(100000,'100k')]
    b=panel(0,'RC: exact magnitude and asymptote',(10,1e5),(-42,2),[(ws,mags,COLORS[0],False),(ws,[rc_asymptotic_db(w) for w in ws],COLORS[1],True)],'w (rad/s), logarithmic','voltage gain (dB)',xt,[(-40,'-40'),(-20,'-20'),(0,'0')],True)
    b+=legend(287,[('exact; at 1k: -3.0103 dB',COLORS[0],False),('straight asymptote; at 1k: 0 dB',COLORS[1],True)])
    b+=panel(355,'RC: exact phase',(10,1e5),(-95,5),[(ws,phases,COLORS[0],False)],'w (rad/s), logarithmic','phase (degrees)',xt,[(-90,'-90'),(-45,'-45'),(0,'0')],True)
    b+=text(18,652,'1k rad/s = 159.154943 Hz',15)
    figures['bode-exact-asymptotic']=svg(680,'Exact RC Bode and asymptotic magnitude','Magnitude exact from 1/(1+j w tau), asymptote 0 then minus20 dB per decade; phase exact, corner error 3.0103 dB.',b)
    ws=[10**(1+k/100) for k in range(401)]
    left=[db_phase(zero_pair_h(w)) for w in ws];right=[db_phase(zero_pair_h(w,True)) for w in ws]
    b=panel(0,'Same magnitude: LHP and RHP zero',(10,1e5),(-1,21),[(ws,[x[0] for x in left],COLORS[0],False),(ws,[x[0] for x in right],COLORS[1],True)],'w (rad/s), logarithmic','voltage gain (dB)',xt,[(0,'0'),(10,'10'),(20,'20')],True)
    b+=legend(284,[('LHP (1+s/1k)/(1+s/10k)',COLORS[0],False),('RHP (1-s/1k)/(1+s/10k)',COLORS[1],True)])
    b+=panel(353,'Phase reveals the zero side',(10,1e5),(-185,65),[(ws,[x[1] for x in left],COLORS[0],False),(ws,[x[1] for x in right],COLORS[1],True)],'w (rad/s), logarithmic','phase (degrees)',xt,[(-180,'-180'),(-90,'-90'),(0,'0'),(60,'60')],True)
    time_ms=[k*.001 for k in range(501)]
    b+=panel(650,'Step reveals initial reversal',(0,.5),(-11,11),[(time_ms,[1+9*math.exp(-10*t) for t in time_ms],COLORS[0],False),(time_ms,[1-11*math.exp(-10*t) for t in time_ms],COLORS[1],True)],'time (ms)','output (V), 1 V step',[(0,'0'),(.1,'.1'),(.3,'.3'),(.5,'.5')],[(-10,'-10'),(0,'0'),(10,'10')])
    b+=text(18,953,'At 1k: +39.29 deg vs -50.71 deg',14)
    figures['zero-phase']=svg(985,'Same magnitude different zero phase','Stable proper examples share magnitudes but RHP zero contributes negative phase; denominator common left pole at minus10000 per second.',b)
    ws=[10**(2+k/125) for k in range(376)]
    pairs=[[db_phase(second_order_h(w,damping=z)) for w in ws] for z in [.25,1.]]
    xt2=[(100,'100'),(1000,'1k'),(10000,'10k'),(100000,'100k')]
    b=panel(0,'RLC: conjugate vs repeated real poles',(100,1e5),(-42,8),[(ws,[x[0] for x in pairs[0]],COLORS[0],False),(ws,[x[0] for x in pairs[1]],COLORS[1],True)],'w (rad/s), logarithmic','voltage gain (dB)',xt2,[(-40,'-40'),(-20,'-20'),(0,'0'),(6,'6')],True)
    b+=legend(286,[('zeta=.25; peak 9354.14 rad/s',COLORS[0],False),('zeta=1; repeated real poles',COLORS[1],True)])
    b+=panel(355,'Exact phase: atan2 keeps quadrant',(100,1e5),(-185,5),[(ws,[x[1] for x in pairs[0]],COLORS[0],False),(ws,[x[1] for x in pairs[1]],COLORS[1],True)],'w (rad/s), logarithmic','phase (degrees)',xt2,[(-180,'-180'),(-90,'-90'),(0,'0')],True)
    b+=text(18,655,'R=50 ohm, L=10 mH, C=1 uF',14)
    figures['rlc-resonance']=svg(685,'RLC resonance and damping','Original series RLC natural angular frequency10000 rad/s damping .25 versus mathematical repeated real pole comparison damping1; exact magnitude and phase.',b)
    def topology(top,rlc):
        b=text(18,top+24,'Series RLC: x=[v,i]' if rlc else 'RC: x=v',18)
        b+=line(65,top+90,120,top+90)+f'<rect x="120" y="{top+80}" width="45" height="20"/>'+text(142,top+70,'R',15,'middle')
        if rlc:
            b+=line(165,top+90,195,top+90)+f'<path d="M195 {top+90}c0 -17 12 -17 12 0c0 -17 12 -17 12 0c0 -17 12 -17 12 0c0 -17 12 -17 12 0"/>'+text(221,top+65,'L',15,'middle')+line(243,top+90,335,top+90)
        else:b+=line(165,top+90,335,top+90)
        b+=line(335,top+90,335,top+133)+line(316,top+133,354,top+133)+line(316,top+150,354,top+150)+line(335,top+150,335,top+210)
        b+=line(335,top+210,65,top+210)+line(65,top+210,65,top+175)+f'<circle cx="65" cy="{top+150}" r="25"/>'+line(65,top+125,65,top+90)
        b+=text(65,top+143,'+',17,'middle')+text(65,top+166,'-',17,'middle')+text(22,top+156,'u',16)
        b+=text(361,top+145,'C',15)+text(307,top+127,'+',16)+text(307,top+173,'-',16)+text(370,top+171,'v',15)
        b+=arrow(280,top+72,310,top+72)+text(290,top+59,'i',15)+text(351,top+94,'a',14)+text(351,top+214,'b=0',14)
        return b
    b=topology(0,False)+text(20,255,'C dv/dt=(u-v)/R',16)+text(20,282,'R=1 kohm; C=1 uF; v0=.4 V',14)
    b+=topology(315,True)+text(20,570,'C dv/dt=i; L di/dt=u-Ri-v',16)+text(20,598,'R=50 ohm; L=10 mH; C=1 uF',14)+text(20,628,'Passive i enters the capacitor + terminal',13)
    figures['state-topology']=svg(660,'Physical RC and RLC state topology','Closed source-resistor-capacitor loop and source-resistor-inductor-capacitor loop, source polarity, passive capacitor voltage and current references, ground node b.',b)
    b=text(18,25,'Abstract active hidden-state model',17)+text(18,52,'Normalized states; this is not passive RC',14)
    b+=text(22,120,'u',17)+arrow(45,115,95,115)+f'<rect x="95" y="82" width="190" height="55"/>'+text(190,115,'x1: pole -1000 /s',15,'middle')+arrow(285,110,367,110)+text(378,116,'y',16)
    b+=line(70,115,70,200)+arrow(70,200,95,200)+f'<rect x="95" y="173" width="190" height="55"/>'+text(190,205,'x2: pole +1000 /s',15,'middle')+text(302,205,'not read',13)
    b+=panel(255,'Measured output approaches one',(0,5),(0,1.05),[(t,[1-math.exp(-x) for x in t],COLORS[0],False)],'time (ms)','y=x1 (dimensionless)',[(0,'0'),(1,'1'),(3,'3'),(5,'5')],[(0,'0'),(.5,'.5'),(1,'1')])
    b+=panel(560,'Hidden state grows',(0,5),(0,160),[(t,[math.expm1(x) for x in t],COLORS[1],False)],'time (ms)','x2 (dimensionless)',[(0,'0'),(1,'1'),(3,'3'),(5,'5')],[(0,'0'),(80,'80'),(160,'160')])
    b+=text(18,865,'Both start at zero; u=1 after t=0',14)+text(18,893,'H=1000/(s+1000); internal + pole remains',13)
    figures['hidden-modes']=svg(920,'Hidden unstable mode with stable port','Abstract active normalized state model input excites both negative and positive1000 poles, output reads only negative mode, plots separately scaled.',b)
    return figures


def generate(output):
    import cairosvg
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    figures=make_figures()
    for stem,body in figures.items():
        (output/(stem+'.svg')).write_text(body,encoding='utf-8')
        for width in (360,425):
            cairosvg.svg2png(bytestring=body.encode(),write_to=str(output/f'{stem}-{width}.png'),output_width=width)
    with (output/'frequency-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['omega_rad_s','frequency_Hz','rc_real','rc_imag','rc_dB','rc_phase_deg','rc_asymptote_dB','rlc_dB','rlc_phase_deg','zero_LHP_dB','zero_LHP_phase_deg','zero_RHP_dB','zero_RHP_phase_deg'])
        for k in range(401):
            w=10**(1+k/100);h=rc_h(w);m,p=db_phase(h);m2,p2=db_phase(second_order_h(w))
            writer.writerow([w,w/(2*math.pi),h.real,h.imag,m,p,rc_asymptotic_db(w),m2,p2,*db_phase(zero_pair_h(w)),*db_phase(zero_pair_h(w,True))])
    with (output/'time-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['time_s','rc_started_V','rc_step_V','hidden_x1_dimensionless','hidden_x2_dimensionless','zero_LHP_step_V','zero_RHP_step_V'])
        for k in range(501):
            t=k/100000.;writer.writerow([t,rc_started_cosine(t),1-.6*math.exp(-1000*t),-math.expm1(-1000*t),math.expm1(1000*t),1+9*math.exp(-10000*t),1-11*math.exp(-10000*t)])
    (output/'parameters.json').write_text(json.dumps({'model':'analytic, not measured','rc':{'R_ohm':1000,'C_F':1e-6,'v0_V':.4,'source_peak_V':1,'omega_rad_s':1000},'rlc':{'R_ohm':50,'L_H':.01,'C_F':1e-6,'natural_rad_s':10000,'damping':.25},'zero_pair':{'zero_abs_rad_s':1000,'pole_rad_s':10000,'step_V':1,'LHP_direct_gain':10,'RHP_direct_gain':-10},'value_boundaries':{'sine_omega_rad_s':2000,'growth_per_s':1000},'comparison_damping':1,'hidden':'abstract normalized active model, poles -1000,+1000 per second','figures':list(figures),'canvas_width_px':425,'preview_widths_px':[360,425],'minimum_font_source_px':13},ensure_ascii=False,indent=2)+'\n')
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv);generate(args.output)


if __name__=='__main__':main()
