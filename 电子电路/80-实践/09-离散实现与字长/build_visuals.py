"""Original narrow SVG diagrams; required --output, no generation on import."""
import argparse
import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from discrete_lab import coefficients,simulate,interval_h,bilinear_h,modal_map,prewarp,Format,simulate_codes,fir_codes

COLORS=['#1265a8','#b54d19','#167747']


def text(x,y,value,size=15,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(str(value))}</text>'


def line(x1,y1,x2,y2,color='#222',dash=False):
    return f'<path d="M{x1} {y1}L{x2} {y2}" style="stroke:{color}"'+(' stroke-dasharray="'+(escape(dash) if isinstance(dash,str) else '5 4')+'"' if dash else '')+'/>'



def method_marker(x,y,index,color):
    """Method identity remains visible in grayscale: circle/square/triangle/diamond."""
    style=f'fill:white;stroke:{color};stroke-width:2'
    if index==0:return f'<circle cx="{x}" cy="{y}" r="5" style="{style}"/>'
    if index==1:return f'<rect x="{x-5}" y="{y-5}" width="10" height="10" style="{style}"/>'
    if index==2:points=f'{x},{y-6} {x+6},{y+5} {x-6},{y+5}'
    else:points=f'{x},{y-6} {x+6},{y} {x},{y+6} {x-6},{y}'
    return f'<polygon points="{points}" style="{style}"/>'


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
        b+=f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.3"'+(' stroke-dasharray="'+(escape(dash) if isinstance(dash,str) else '6 4')+'"' if dash else '')+'/>'
    return b


def legend(y,labels):
    b=''
    for k,(label,color,dash) in enumerate(labels):
        b+=line(22,y+23*k,48,y+23*k,color,dash)+text(58,y+5+23*k,label,14)
    return b


def frame(top,height,title,rows):
    b=f'<rect x="18" y="{top}" width="389" height="{height}" rx="7"/>'+text(30,top+27,title,17)
    for k,row in enumerate(rows):b+=text(30,top+55+25*k,row,14)
    return b


def make_figures():
    figures={};a,b=coefficients();T=.00025
    times=[k*.01 for k in range(101)]
    body=text(18,23,'Same RC, four domains, one contract',17)+text(18,49,'R=1 kohm; C=1 uF; tau=1 ms',14)
    body+=panel(62,'Time: separate initial states',(0,1),(0,1),[(times,[1-math.exp(-t) for t in times],COLORS[0],False),(times,[1-.6*math.exp(-t) for t in times],COLORS[1],False)],'time (ms)','voltage (V)',[(0,'0'),(.25,'.25'),(.5,'.5'),(1,'1')],[(0,'0'),(.4,'.4'),(1,'1')])
    body+=legend(350,[('v0=0 V: 1-exp(-t/tau)',COLORS[0],False),('v0=.4 V: 1-.6 exp(-t/tau)',COLORS[1],False)])
    body+=frame(420,145,'s: zero-state port and initial term',['H(s)=1000/(s+1000), pole -1000 /s','V=H U+v0/(s+1000)','causal ROC: Re s > -1000 /s','Laplace V and U have units V*s'])
    body+=arrow(212,574,212,600)+text(228,592,'imaginary axis in ROC',13)
    body+=frame(610,145,'j Omega: steady cosine only',['Omega=1000 rad/s; f=159.154943 Hz','H(j Omega)=(1-j)/2','magnitude .70710678; phase -45 deg','starting transient is a separate term'])
    body+=frame(795,198,'z: held input and boundary output',['T=.25 ms; u[k] held on [kT,(k+1)T)','v[k+1]=a v[k]+b u[k]; y[k]=v[k]','a=.7788007831; b=.2211992169','Hd=b z^-1/(1-a z^-1); pole z=a','V+=Hd U+ + v0/(1-a z^-1)','h[0]=0; n inputs -> n+1 states'])
    body+=text(18,1030,'Pole sampling exp(sT) does not fix all of Hd',13)
    figures['V14-four-domains']=svg(1060,'Same RC across time Laplace frequency and z','R1000 ohm C1 microfarad, separate zero and .4V initial responses, system pole minus1000 per second, frequency159.154943Hz, held T.25ms and explicit z inverse delay plus initial term.',body)
    inputs=[1.,0.,.5,1.];values=simulate(inputs)
    ts=[];continuous=[]
    for k,u in enumerate(inputs):
        for j in range(51):
            t=k*.25+j*.25/50;ts.append(t)
            decay=math.exp(-j*.25/50);continuous.append(values[k]*decay+u*(-math.expm1(-j*.25/50)))
    held_x=[];held_y=[]
    for k,u in enumerate(inputs):held_x.extend([k*.25,(k+1)*.25]);held_y.extend([u,u])
    body=panel(0,'Input lives on held intervals',(0,1),(0,1.2),[(held_x,held_y,COLORS[1],False)],'time (ms)','u[k] (V)',[(0,'0'),(.25,'.25'),(.5,'.5'),(.75,'.75'),(1,'1')],[(0,'0'),(.5,'.5'),(1,'1')])
    for k,u in enumerate(inputs):body+=text(62+(k+.5)*.25*336,83,'u['+str(k)+']',13,'middle')
    body+=text(18,291,'Every interval is [kT,(k+1)T), T=.25 ms',14)
    body+=panel(322,'Output samples include the initial state',(0,1),(0,1.2),[(ts,continuous,COLORS[0],False)],'time (ms)','v(t) (V), dots are y[k]',[(0,'0'),(.25,'.25'),(.5,'.5'),(.75,'.75'),(1,'1')],[(0,'0'),(.4,'.4'),(1,'1')])
    for k,value in enumerate(values):
        x=62+k*.25*336;y=322+225-value/1.2*173
        body+=f'<circle cx="{x}" cy="{y}" r="4" style="fill:{COLORS[0]};stroke:{COLORS[0]}"/>'
    body+=text(18,612,'y[0]=.4 V; y[1]=.5327195302 V',14)
    body+=frame(640,143,'Read -> advance -> store next boundary',['u[0]=1 V acts before v[1], not v[0]','v[1]=a v[0]+b u[0]','v[2]=a v[1]+b u[1]','len(u)=4; len(v)=5; first is v0'])
    figures['V17-update-timing']=svg(815,'ZOH intervals and output update timing','Four held inputs [1,0,.5,1] volts over quarter millisecond intervals, actual analytic continuous RC path and five boundary samples starting .4V, each interval input affects next sample.',body)
    body=text(18,25,'Strict decay regions in mu=sT plane',17)+text(18,52,'Shade: |z|<1; dashed boundary excluded',14)
    for index,(method,title,equation) in enumerate([
        ('exact','Exact modal sampling','z=exp(mu); Re mu<0'),
        ('euler','Forward Euler: disk centered at -1','z=1+mu; |1+mu|<1'),
        ('backward','Backward Euler: outside +1 disk','z=1/(1-mu); |1-mu|>1'),
        ('bilinear','Bilinear: strict left half-plane','z=(1+mu/2)/(1-mu/2)')]):
        top=80+index*375;left=70;upper=top+67;scale=60;cy=upper+120
        x=lambda value:left+(value+3)*scale;y=lambda value:cy-value*scale
        body+=text(18,top+20,title,17)+text(18,top+45,equation,14)
        if method in ('exact','bilinear'):body+=f'<rect x="{left}" y="{upper}" width="180" height="240" style="fill:#e8f3fb;stroke:none"/>'
        elif method=='euler':body+=f'<circle cx="{x(-1)}" cy="{cy}" r="60" style="fill:#e8f3fb;stroke:none"/>'
        else:body+=f'<rect x="{left}" y="{upper}" width="300" height="240" style="fill:#e8f3fb;stroke:none"/><circle cx="{x(1)}" cy="{cy}" r="60" style="fill:white;stroke:none"/>'
        body+=line(left,cy,370,cy)+line(x(0),upper,x(0),upper+240)
        if method in ('exact','bilinear'):body+=line(x(0),upper,x(0),upper+240,dash=True)
        else:body+=f'<circle cx="{x(-1 if method=="euler" else 1)}" cy="{cy}" r="60" stroke-dasharray="5 4"/>'
        for value in [-3,-2,-1,0,1,2]:body+=text(x(value),upper+260,str(value),13,'middle')
        for value in [-2,-1,1,2]:body+=text(48,y(value)+5,str(value),13,'middle')
        body+=text(374,cy-10,'Re',13)+text(x(0)+8,upper+15,'Im',13)
        for value,color in [(-.25,COLORS[0]),(-2,COLORS[1]),(-2.5,COLORS[2]),(1j,'#762b91')]:
            c=complex(value);body+=f'<circle cx="{x(c.real)}" cy="{y(c.imag)}" r="4" style="fill:{color};stroke:{color}"/>'
        body+=text(18,top+355,f'mu=-2.5: |z|={abs(modal_map(-2.5,1,method)):.6f}; mu=j: {abs(modal_map(1j,1,method)):.6f}',13)
    body+=text(18,1604,'Dots: -.25, -2, -2.5 on real axis; j above',13)+text(18,1632,'Unit magnitude is a boundary, not strict decay',13)
    top=1670;cx=212;cy=top+212;scale=83.3333333333
    body+=text(18,top+22,'z plane: strict unit disk, |z|<1',17)
    body+=f'<circle cx="{cx}" cy="{cy}" r="{scale}" style="fill:#e8f3fb;stroke:#222;stroke-dasharray:5 4"/>'
    body+=line(62,cy,362,cy)+line(cx,cy-150,cx,cy+150)
    for value in [-1,0,1]:body+=text(cx+value*scale,cy+173,str(value),13,'middle')
    for value in [-1,1]:body+=text(46,cy-value*scale+5,str(value),13)
    body+=text(363,cy-10,'Re z',13,'end')+text(cx+8,cy-137,'Im z',13)
    for index,method in enumerate(['exact','euler','backward','bilinear']):
        color=[*COLORS,'#762b91'][index]
        for mu in [-2.5,1j]:
            z=modal_map(mu,1,method)
            body+=method_marker(cx+z.real*scale,cy-z.imag*scale,index,color)
    for index,(name,color) in enumerate(zip(['exact: circle','Euler: square','backward Euler: triangle','bilinear: diamond'],[*COLORS,'#762b91'])):
        body+=method_marker(35,top+419+23*index,index,color)+text(58,top+424+23*index,name,14)
    body+=text(18,top+530,'Mapped mu=-2.5 and mu=j; circle excluded',13)
    figures['V18-stability-regions']=svg(2230,'Exact Euler backward Euler and bilinear strict stability regions','Four complex mu=sT plane equal-aspect regions, boundary excluded from strict decay, points negative .25 negative2 negative2.5 and imaginary1, modal factor magnitudes given.',body)
    t=[k*.000005 for k in range(201)]
    body=panel(0,'Different waves, identical sample list',(0,1),(-1.1,1.1),[([x*1000 for x in t],[math.cos(2*math.pi*1000*x) for x in t],COLORS[0],False),([x*1000 for x in t],[math.cos(2*math.pi*3000*x) for x in t],COLORS[1],True)],'time (ms)','voltage (V)',[(0,'0'),(.25,'.25'),(.5,'.5'),(.75,'.75'),(1,'1')],[(-1,'-1'),(0,'0'),(1,'1')])
    for k in range(5):
        value=math.cos(math.pi*k/2);x=62+k*.25*336;y=225-(value+1.1)/2.2*173
        body+=f'<circle cx="{x}" cy="{y}" r="4" style="fill:#222;stroke:#222"/>'
    body+=legend(287,[('1000 Hz',COLORS[0],False),('3000 Hz; fs=4000 Hz',COLORS[1],True)])
    theta=[k*math.pi/400 for k in range(301)]
    body+=panel(355,'Bilinear warps design coordinates', (0,.75),(0,21000),[([x/math.pi for x in theta],[prewarp(x) for x in theta],COLORS[0],False),([x/math.pi for x in theta],[x/T for x in theta],COLORS[1],True)],'theta/pi (rad/sample normalized)','prototype Omega (rad/s)',[(0,'0'),(.25,'.25'),(.5,'.5'),(.75,'.75')],[(0,'0'),(10000,'10k'),(20000,'20k')])
    body+=legend(642,[('Omega=(2/T) tan(theta/2)',COLORS[0],False),('linear theta/T; valid only near zero',COLORS[1],True)])
    body+=text(18,720,'Prewarp .25 rad/sample -> 1005.241 rad/s',13)+text(18,748,'Digital design does not undo input aliasing',13)
    figures['alias-warp']=svg(780,'Aliasing versus bilinear design warping','Different1kHz and3kHz waves at4kHz share samples; separately nonlinear tan prototype frequency versus digital theta compared to linear approximation, units distinct.',body)
    body=text(18,27,'Integer RC update: one rounding',18)+text(18,55,'W=16, F=14; Delta=1/16384 V',14)
    steps=[('Encode values','u and initial v -> signed q (W bits)'),('Quantize coefficients','A=12760; B=3624 (unitless scaled)'),('Exact multiply and add','P=A*q[k]+B*qu[k]; fraction 2F'),('Accumulator guard','2W+1=33 signed bits, or reject'),('Round once','roundEven(P/16384), fraction F'),('Narrow and store','saturate by default; wrap explicit'),('Next boundary','q[k+1]; q[0] is supplied initial code')]
    for k,(title,row) in enumerate(steps):
        top=85+k*115;body+=frame(top,83,title,[row])
        if k<6:body+=arrow(212,top+87,212,top+108)
    body+=text(18,920,'.4 V -> q0=6554 -> .4000244141 V',14)+text(18,950,'CPU exact integers; no actual DSP chip proof',13)
    figures['integer-path']=svg(980,'Integer multiply accumulate rounding and narrowing path','Volts and unitless coefficients separately encoded, exact integer products with2F fraction, declared accumulator guard, one ties-even rounding, explicit storage saturation or wrap, initial code preserved.',body)
    indices=list(range(17));fmt=Format(8,4)
    fixed=simulate_codes([0]*16,12,0,1,fmt);cycle=simulate_codes([0]*16,-12,0,1,fmt);trunc=simulate_codes([0]*16,-12,0,1,fmt,'toward_zero')
    body=panel(0,'One LSB can remain under feedback',(0,16),(-.1,1.1),[(indices,[.75**k for k in indices],COLORS[0],False),(indices,fixed,COLORS[1],True)],'sample k','state (LSB)',[(0,'0'),(4,'4'),(8,'8'),(16,'16')],[(0,'0'),(1,'1')])
    body+=legend(287,[('real a=.75 decay',COLORS[0],False),('integer nearest: one-code fixed point',COLORS[1],True)])
    body+=panel(355,'Two-code zero-input limit cycle',(0,16),(-1.2,1.2),[(indices,cycle,COLORS[1],False),(indices,trunc,COLORS[2],True)],'sample k','state (LSB)',[(0,'0'),(4,'4'),(8,'8'),(16,'16')],[(-1,'-1'),(0,'0'),(1,'1')])
    body+=legend(642,[('a=-.75 nearest: +1,-1,+1,...',COLORS[1],False),('toward zero: reaches zero',COLORS[2],True)])
    body+=text(18,720,'W=8 F=4: 1 LSB=.0625 V; u=0',14)
    figures['limit-cycles']=svg(750,'Zero-input deadband and period two quantized filter cycle','Real positive .75 decay compared to one-code fixed point, negative .75 nearest rounding period two versus truncation to zero; separate from actual exact RC coefficient.',body)
    inputs=[1.]*16;indices=list(range(17));times=[k*.25 for k in indices]
    methods=['exact','euler','backward','trapezoid_hold'];series=[simulate(inputs,method=m) for m in methods]
    body=panel(0,'Four methods, same held-step contract',(0,4),(.35,1.03),[(times,series[0],COLORS[0],False),(times,series[1],COLORS[1],'9 4'),(times,series[2],COLORS[2],'2 4'),(times,series[3],'#762b91','9 3 2 3')],'time (ms)','voltage (V)',[(0,'0'),(1,'1'),(2,'2'),(4,'4')],[(.4,'.4'),(.7,'.7'),(1,'1')])
    body+=legend(287,[('exact ZOH',COLORS[0],False),('forward Euler',COLORS[1],'9 4'),('backward Euler',COLORS[2],'2 4'),('trapezoid held interval','#762b91','9 3 2 3')])
    body+=panel(405,'At T=2 tau Euler does not decay',(0,8),(-.45,.45),[(list(range(9)),simulate([0]*8,T_s=.002,method='euler'),COLORS[1],False),(list(range(9)),[.4*math.exp(-2*k) for k in range(9)],COLORS[0],False)],'sample k (T=2 ms)','zero-input voltage (V)',[(0,'0'),(2,'2'),(4,'4'),(8,'8')],[(-.4,'-.4'),(0,'0'),(.4,'.4')])
    body+=text(18,698,'Stable continuous RC; numerical boundary |a|=1',13)
    figures['method-comparison']=svg(730,'RC interval integration methods and Euler boundary','Same1ms RC and quarter millisecond step methods compared from .4V; separately Euler T2ms zero-input alternation versus actual exponential decay.',body)
    return figures


def generate(output):
    import cairosvg
    output=Path(output);output.mkdir(parents=True,exist_ok=True);figures=make_figures()
    for stem,body in figures.items():
        (output/(stem+'.svg')).write_text(body,encoding='utf-8')
        for width in (360,425):cairosvg.svg2png(bytestring=body.encode(),write_to=str(output/f'{stem}-{width}.png'),output_width=width)
    methods=['exact','euler','backward','trapezoid_hold'];states={m:simulate([1.]*16,method=m) for m in methods};held=[1.,0.,.5,1.];hv=simulate(held)
    with (output/'state-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['k','time_s',*[m+'_V' for m in methods],'held_input_V','held_state_V'])
        for k in range(17):writer.writerow([k,k*.00025,*[states[m][k] for m in methods],held[k] if k<4 else '',hv[k] if k<5 else ''])
    fmt=Format(8,4);fine=Format();a,b=coefficients();fine_codes=simulate_codes([fine.encode(u) for u in [1.]*8+[-.1]*4],fine.encode(a),fine.encode(b),fine.encode(.4),fine)
    fixed=simulate_codes([0]*32,12,0,1,fmt);cycle=simulate_codes([0]*32,-12,0,1,fmt);trunc=simulate_codes([0]*32,-12,0,1,fmt,'toward_zero');fir=fir_codes([16]+[0]*32,[4,8,4],fmt)
    with (output/'integer-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['k','coarse_fixed_code','coarse_cycle_code','coarse_truncate_code','fine_RC_code','fine_RC_V','FIR_code','coarse_LSB_V'])
        for k in range(33):writer.writerow([k,fixed[k],cycle[k],trunc[k],fine_codes[k] if k<len(fine_codes) else '',fine.decode(fine_codes[k]) if k<len(fine_codes) else '',fir[k],1/16])
    with (output/'modal-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['mu_real','mu_imag','method','z_real','z_imag','abs_z'])
        for mu in [-.25,-2.,-2.5,1j,3.]:
            for method in ['exact','euler','backward','bilinear']:
                z=modal_map(mu,1,method);writer.writerow([complex(mu).real,complex(mu).imag,method,z.real,z.imag,abs(z)])
    with (output/'frequency-data.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['theta_rad_sample','digital_Hz','prewarped_Omega_rad_s','interval_H_real','interval_H_imag','bilinear_H_real','bilinear_H_imag'])
        for k in range(400):
            theta=k*math.pi/400;hi=interval_h(theta);hb=bilinear_h(theta);writer.writerow([theta,theta/(2*math.pi*.00025),prewarp(theta),hi.real,hi.imag,hb.real,hb.imag])
    parameters={'models':'analytic CPU and exact integer oracles, not measured','R_ohm':1000,'C_F':1e-6,'tau_s':.001,'T_s':.00025,'v0_V':.4,'interval_methods':{m:coefficients(method=m) for m in methods},'hold_inputs_V':held,'modal_mu_points':[[-.25,0],[-2,0],[-2.5,0],[0,1]],'alias_Hz':[1000,3000],'sample_rate_Hz':4000,'fine_format':{'W':16,'F':14,'A_code':fine.encode(a),'B_code':fine.encode(b),'initial_code':fine.encode(.4),'input_V':[1.]*8+[-.1]*4},'coarse_format':{'W':8,'F':4,'fixed_A_code':12,'cycle_A_code':-12,'initial_code':1,'input_code':0},'FIR_codes':[4,8,4],'canvas_width_px':425,'preview_widths_px':[360,425],'minimum_font_source_px':13,'figures':list(figures)}
    (output/'parameters.json').write_text(json.dumps(parameters,ensure_ascii=False,indent=2)+'\n')
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv);generate(args.output)


if __name__=='__main__':main()
