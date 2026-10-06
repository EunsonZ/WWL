---
aliases: []
stage: 3
prerequisites: []
sources: []
---
# 离散实现与字长源码镜像

以下代码由同目录真源逐字复制；运行与单位合同见[[电子电路/80-实践/09-离散实现与字长/README|实践说明]]。

## discrete_lab.py

```python
"""RC interval-state and integer arithmetic teaching models; import does no I/O.

Every interval simulation returns len(inputs)+1 states, including initial.
Input u[k] acts over [kT,(k+1)T). Standard bilinear H is a separate filter
transfer contract; it is never presented as this ZOH interval simulation.
"""
from dataclasses import dataclass
import cmath
import math


def real(value,positive=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)):raise ValueError('finite real required')
    try:value=float(value)
    except OverflowError as exc:raise ValueError('outside float range') from exc
    if not math.isfinite(value) or (positive and value<=0):raise ValueError('finite positive required' if positive else 'finite real required')
    return value


def finite(value):
    if isinstance(value,complex):okay=math.isfinite(value.real) and math.isfinite(value.imag)
    else:okay=math.isfinite(value)
    if not okay:raise ValueError('derived value outside range')
    return value


def coefficients(T_s=.00025,tau_s=.001,method='exact'):
    T=real(T_s,True);tau=real(tau_s,True);h=finite(T/tau)
    if h==0:raise ValueError('step ratio underflow')
    if method=='exact':a=math.exp(-h);b=-math.expm1(-h)
    elif method=='euler':a=1-h;b=h
    elif method=='backward':a=1/(1+h);b=h/(1+h)
    elif method=='trapezoid_hold':
        # Equivalent to (1-h/2)/(1+h/2), without forming h+2 near range limit.
        a=2/(1+h/2)-1;b=h/(1+h/2)
    else:raise ValueError('unknown interval integration method')
    return finite(a),finite(b)


def simulate(inputs,T_s=.00025,initial_V=.4,method='exact',tau_s=.001):
    a,b=coefficients(T_s,tau_s,method);state=real(initial_V);result=[state]
    for value in inputs:
        u=real(value);state=finite(a*state+b*u);result.append(state)
    return result


def interval_h(theta_rad_sample,T_s=.00025,method='exact'):
    theta=real(theta_rad_sample);a,b=coefficients(T_s,method=method)
    q=cmath.exp(-1j*theta);denominator=1-a*q
    if denominator==0:raise ValueError('singular frequency')
    return finite(b*q/denominator)


def bilinear_h(theta_rad_sample,T_s=.00025,prototype_tau_s=.001):
    """Zero-state endpoint-input filter H with numerator 1+z^-1, no IC API."""
    theta=real(theta_rad_sample);T=real(T_s,True);tau=real(prototype_tau_s,True)
    h=finite(T/tau);a=2/(1+h/2)-1;c=(h/2)/(1+h/2)
    q=cmath.exp(-1j*theta);denominator=1-a*q
    if denominator==0:raise ValueError('singular frequency')
    return finite(c*(1+q)/denominator)


def modal_map(s_per_s,T_s,method='exact'):
    if isinstance(s_per_s,bool) or not isinstance(s_per_s,(int,float,complex)):raise ValueError('finite scalar mode required')
    try:s=complex(s_per_s)
    except (ValueError,OverflowError) as exc:raise ValueError('mode outside float range') from exc
    finite(s);T=real(T_s,True);q=finite(s*T)
    try:
        if method=='exact':z=cmath.exp(q)
        elif method=='euler':z=1+q
        elif method=='backward':
            if 1-q==0:raise ValueError('singular backward mode')
            z=1/(1-q)
        elif method=='bilinear':
            if 1-q/2==0:raise ValueError('singular bilinear mode')
            z=(1+q/2)/(1-q/2)
        else:raise ValueError('unknown mode map')
    except OverflowError as exc:raise ValueError('mode overflow') from exc
    return finite(z)


def prewarp(theta_rad_sample,T_s=.00025):
    theta=real(theta_rad_sample);T=real(T_s,True)
    if not -math.pi<theta<math.pi:raise ValueError('principal digital frequency must be strictly inside +/-pi')
    return finite((2/T)*math.tan(theta/2))


@dataclass(frozen=True)
class Format:
    """Signed W-bit code times 2^-F; caller declares volts or unitless coefficient."""
    bits:int=16
    fraction:int=14
    def __post_init__(self):
        if type(self.bits) is not int or type(self.fraction) is not int or not 2<=self.bits<=32 or not 0<=self.fraction<self.bits:raise ValueError('integer 2<=W<=32, 0<=F<W required')
    @property
    def scale(self):return 1<<self.fraction
    @property
    def low(self):return -(1<<(self.bits-1))
    @property
    def high(self):return (1<<(self.bits-1))-1
    def code(self,value):
        if type(value) is not int or not self.low<=value<=self.high:raise ValueError('signed code outside format')
        return value
    def encode(self,value):
        value=real(value);value=max(self.low/self.scale,min(self.high/self.scale,value))
        return round(value*self.scale)
    def decode(self,code):return self.code(code)/self.scale
    def narrow(self,code,overflow='saturate'):
        if type(code) is not int:raise ValueError('integer required')
        if overflow=='saturate':return max(self.low,min(self.high,code))
        if overflow=='wrap':return (code-self.low)%(1<<self.bits)+self.low
        raise ValueError('overflow must be saturate or wrap')


def round_divide(numerator,denominator,rounding='nearest_even'):
    """Exact signed integer rescaling, with tie handling independent of float."""
    if type(numerator) is not int or type(denominator) is not int or denominator<=0:raise ValueError('integer numerator/positive denominator required')
    sign=-1 if numerator<0 else 1;whole,remainder=divmod(abs(numerator),denominator)
    if rounding=='nearest_even':
        if 2*remainder>denominator or (2*remainder==denominator and whole%2):whole+=1
    elif rounding!='toward_zero':raise ValueError('unknown rounding')
    return sign*whole


def simulate_codes(input_codes,a_code,b_code,initial_code,fmt=Format(),rounding='nearest_even',overflow='saturate',accumulator_bits=None):
    """Exact multiply/add -> signed accumulator guard -> one round -> narrowing.

    Coefficients use the same fraction F; codes are preserved initial and n+1.
    Python integers compute the oracle exactly; guard represents chosen hardware
    accumulator range, not the actual host's integer storage.
    """
    if not isinstance(fmt,Format):raise ValueError('Format required')
    fmt.code(a_code);fmt.code(b_code);state=fmt.code(initial_code);result=[state]
    # Validate policies even for an empty input list.
    round_divide(0,fmt.scale,rounding);fmt.narrow(0,overflow)
    width=2*fmt.bits+1 if accumulator_bits is None else accumulator_bits
    if type(width) is not int or not 2<=width<=128:raise ValueError('accumulator width 2..128 required')
    lower=-(1<<(width-1));upper=(1<<(width-1))-1
    for input_code in input_codes:
        u=fmt.code(input_code);accumulator=a_code*state+b_code*u
        if not lower<=accumulator<=upper:raise OverflowError('declared accumulator overflow')
        state=fmt.narrow(round_divide(accumulator,fmt.scale,rounding),overflow);result.append(state)
    return result


def fir_codes(input_codes,coefficient_codes,fmt=Format(),rounding='nearest_even',overflow='saturate',accumulator_bits=None):
    """Nonrecursive tapped delay line, zero history, one output per input sample."""
    if not isinstance(fmt,Format):raise ValueError('Format required')
    coefficients=[fmt.code(x) for x in coefficient_codes]
    if not coefficients:raise ValueError('at least one FIR tap required')
    inputs=[fmt.code(x) for x in input_codes];round_divide(0,fmt.scale,rounding);fmt.narrow(0,overflow)
    width=2*fmt.bits+math.ceil(math.log2(len(coefficients)))+1 if accumulator_bits is None else accumulator_bits
    if type(width) is not int or not 2<=width<=128:raise ValueError('accumulator width 2..128 required')
    lower=-(1<<(width-1));upper=(1<<(width-1))-1;result=[]
    for n in range(len(inputs)):
        accumulator=sum(c*inputs[n-j] for j,c in enumerate(coefficients) if n>=j)
        if not lower<=accumulator<=upper:raise OverflowError('declared accumulator overflow')
        result.append(fmt.narrow(round_divide(accumulator,fmt.scale,rounding),overflow))
    return result
```

## build_visuals.py

```python
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
```

## test_discrete_lab.py

```python
"""Independent IVP/Fraction/series oracles; original RC interface read-only."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from discrete_lab import (coefficients,simulate,interval_h,bilinear_h,modal_map,prewarp,
 Format,round_divide,simulate_codes,fir_codes)

HERE=Path(__file__).resolve().parent


def original_rc():
    path=HERE.parent/'01-RC跨层'/'rc_lab.py'
    spec=importlib.util.spec_from_file_location('wwl_original_rc_readonly',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def rk4_hold(initial,inputs,T,steps=2000):
    value=initial;result=[value];dt=T/steps
    for u in inputs:
        f=lambda v:(u-v)/.001
        for _ in range(steps):
            a=f(value);b=f(value+dt*a/2);c=f(value+dt*b/2);d=f(value+dt*c)
            value+=dt*(a+2*b+2*c+d)/6
        result.append(value)
    return result


class NumericalTests(unittest.TestCase):
    def test_original_n_plus_one_and_hold_ivp(self):
        rc=original_rc().RC();inputs=[1.,0.,.5,-.1]
        for method in ['exact','euler']:
            values=simulate(inputs,initial_V=.4,method=method)
            self.assertEqual(len(values),5);self.assertEqual(values[0],.4)
            self.assertEqual(values,list(rc.simulate(inputs,.00025,v0=.4,method=method)))
        actual=simulate(inputs);reference=rk4_hold(.4,inputs,.00025)
        for value,expected in zip(actual,reference):self.assertAlmostEqual(value,expected,places=13)
        self.assertEqual(simulate([],initial_V=.4),[.4])
        self.assertEqual(simulate([1],initial_V=0)[0],0)
        self.assertAlmostEqual(simulate([1],initial_V=0)[1],.2211992169285951,places=15)

    def test_single_and_bilateral_series_initial_and_delay(self):
        a,b=coefficients();z=complex(1.2,.1)
        sequence=simulate([1.]+[0.]*119,initial_V=.4)
        summed=sum(v*z**(-k) for k,v in enumerate(sequence))
        expected=.4/(1-a/z)+b/(z-a)
        self.assertLess(abs(summed-expected),1e-14)
        impulse=simulate([1.]+[0.]*5,initial_V=0)
        self.assertEqual(impulse[0],0.)
        for k in range(1,7):self.assertAlmostEqual(impulse[k],b*a**(k-1),places=15)
        # Independent left-side geometric sum including k=0.
        z=complex(.3,.1)
        left=sum(-b*a**(k-1)*z**(-k) for k in range(-90,1))
        self.assertLess(abs(left-b/(z-a)),1e-14)

    def test_methods_against_equations_and_fixed_time_orders(self):
        for method in ['backward','trapezoid_hold']:
            a,b=coefficients(method=method);v0=.4;u=1.;v1=simulate([u],initial_V=v0,method=method)[1];h=.25
            if method=='backward':residual=v1-v0-h*(u-v1)
            else:residual=v1-v0-h/2*((u-v0)+(u-v1))
            self.assertAlmostEqual(residual,0,places=15)
            self.assertAlmostEqual(a+b,1,places=15)
        exact=1-.6*math.exp(-1)
        for method,order in [('euler',1),('backward',1),('trapezoid_hold',2)]:
            errors=[]
            for n in [40,80,160]:errors.append(abs(simulate([1.]*n,T_s=.001/n,method=method)[-1]-exact))
            observed=math.log2(errors[-2]/errors[-1]);self.assertLess(abs(observed-order),.03)

    def test_euler_boundary_and_mapping_regions(self):
        values=simulate([0.]*4,T_s=.002,method='euler')
        self.assertEqual(values,[.4,-.4,.4,-.4,.4])
        self.assertGreater(abs(simulate([0.]*5,T_s=.0025,method='euler')[-1]),.4)
        for method in ['exact','backward','bilinear']:
            self.assertLess(abs(modal_map(-1000,.0025,method)),1)
        self.assertEqual(abs(modal_map(-1000,.002,'euler')),1)
        self.assertGreater(abs(modal_map(1j*4000,.00025,'euler')),1)
        self.assertLess(abs(modal_map(1j*4000,.00025,'backward')),1)
        for method in ['exact','bilinear']:self.assertAlmostEqual(abs(modal_map(1j*4000,.00025,method)),1,places=14)
        self.assertLess(abs(modal_map(3000,.001,'backward')),1) # numerical stability does not prove physical stability

    def test_bilinear_is_not_interval_transfer(self):
        a,b=coefficients(method='trapezoid_hold');self.assertAlmostEqual(a,7/9,places=15)
        for theta in [.1,.25,1.,2.5]:
            expected=1/complex(1,.001*prewarp(theta))
            self.assertLess(abs(bilinear_h(theta)-expected),1e-14)
            self.assertGreater(abs(bilinear_h(theta)-interval_h(theta,method='trapezoid_hold')),1e-4)
        self.assertAlmostEqual(abs(bilinear_h(math.pi)),0,places=14)
        self.assertAlmostEqual(interval_h(0).real,1,places=15)

    def test_aliasing_and_prewarp_units(self):
        T=.00025
        for k in range(-10,11):self.assertAlmostEqual(math.cos(2*math.pi*1000*k*T),math.cos(2*math.pi*3000*k*T),places=13)
        self.assertAlmostEqual(math.cos(2*math.pi*1000*T/2),math.sqrt(.5),places=14)
        self.assertAlmostEqual(math.cos(2*math.pi*3000*T/2),-math.sqrt(.5),places=14)
        s=-1000+1000j;other=s+2j*math.pi/T
        self.assertLess(abs(modal_map(s,T)-modal_map(other,T)),1e-14)
        prototype_tau=1/prewarp(.25)
        self.assertLess(abs(bilinear_h(.25,prototype_tau_s=prototype_tau)-complex(.5,-.5)),1e-14)
        self.assertAlmostEqual(prewarp(math.pi/2),8000,places=10)
        self.assertAlmostEqual(2*math.atan(1000*T/2)/(2*math.pi*T),158.33369664226217,places=10)

    def test_rounding_exhaustive_fraction_oracle(self):
        for denominator in range(1,18):
            for numerator in range(-200,201):
                fraction=Fraction(numerator,denominator)
                self.assertEqual(round_divide(numerator,denominator),round(fraction))
                self.assertEqual(round_divide(numerator,denominator,'toward_zero'),math.trunc(fraction))

    def test_integer_rc_exact_fraction_and_original_float_reference(self):
        fmt=Format();a,b=coefficients();A=fmt.encode(a);B=fmt.encode(b);initial=fmt.encode(.4)
        self.assertEqual((A,B,initial),(12760,3624,6554));self.assertEqual(A+B,fmt.scale)
        inputs=[1.]*8+[-.1]*4;codes=[fmt.encode(u) for u in inputs]
        result=simulate_codes(codes,A,B,initial,fmt)
        oracle=[initial]
        for u in codes:oracle.append(max(fmt.low,min(fmt.high,round(Fraction(A*oracle[-1]+B*u,fmt.scale)))))
        self.assertEqual(result,oracle);self.assertEqual(result[0],initial);self.assertEqual(len(result),len(codes)+1)
        original=original_rc();reference=original.RC().simulate(inputs,.00025,v0=.4,quantizer=original.QFormat(16,14))
        self.assertEqual([fmt.decode(q) for q in result],list(reference))

    def test_deadband_period_two_and_truncation(self):
        fmt=Format(8,4)
        self.assertEqual(simulate_codes([0]*8,12,0,1,fmt),[1]*9)
        self.assertEqual(simulate_codes([0]*8,-12,0,1,fmt),[1,-1,1,-1,1,-1,1,-1,1])
        self.assertEqual(simulate_codes([0]*4,-12,0,1,fmt,'toward_zero'),[1,0,0,0,0])
        # Complete finite state space, not a few plotted points.
        for q in range(fmt.low,fmt.high+1):
            result=simulate_codes([0]*256,12,0,q,fmt)
            self.assertEqual(result[-1],result[-2])

    def test_overflow_locations_and_fir_flush(self):
        fmt=Format(8,4)
        self.assertEqual(simulate_codes([112],0,32,0,fmt),[0,127])
        self.assertEqual(simulate_codes([112],0,32,0,fmt,overflow='wrap'),[0,-32])
        with self.assertRaises(OverflowError):simulate_codes([112],0,32,0,fmt,accumulator_bits=12)
        self.assertEqual(fir_codes([16,0,0,0,0],[4,8,4],fmt),[4,8,4,0,0])
        self.assertEqual(fir_codes([127,0,0,0,0],[127,127,127],fmt)[-2:],[0,0])

    def test_deterministic_error_bound_no_saturation(self):
        fmt=Format();a,b=coefficients();A=fmt.encode(a);B=fmt.encode(b);initial=.4;inputs=[.7,-.3,.5,0.,1.]*20
        ideal=simulate(inputs,initial_V=initial);codes=simulate_codes([fmt.encode(x) for x in inputs],A,B,fmt.encode(initial),fmt)
        ahat=A/fmt.scale;bhat=B/fmt.scale;delta=1/fmt.scale
        E=abs(ahat-a)+abs(bhat-b)+abs(bhat)*delta/2+delta/2;e0=abs(fmt.decode(codes[0])-initial)
        for k,(v,q) in enumerate(zip(ideal,codes)):
            bound=abs(ahat)**k*e0+E*(1-abs(ahat)**k)/(1-abs(ahat))
            self.assertLessEqual(abs(fmt.decode(q)-v),bound+1e-15)
            self.assertGreater(q,fmt.low);self.assertLess(q,fmt.high)

    def test_real_sources_reject_complex_before_conversion(self):
        import numpy as np
        import warnings
        invalid=[1+2j,1+0j,object(),[1.],np.array(1+2j),
                 np.array(1+0j),np.array([1+2j],dtype=object)]
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for value in invalid:
                with self.subTest(value_type=type(value).__name__):
                    with self.assertRaises(ValueError):simulate([value])
                    with self.assertRaises(ValueError):simulate([],initial_V=value)
                    with self.assertRaises(ValueError):Format().encode(value)
            for values in [np.array([1+2j]),np.array([1+0j]),
                           np.array([1+2j],dtype=object),[[1.]]]:
                with self.assertRaises(ValueError):simulate(values)
            self.assertEqual(captured,[])
        self.assertEqual(simulate(np.array([1.,0.])),simulate([1.,0.]))
        self.assertIsInstance(interval_h(.25),complex)
        self.assertIsInstance(modal_map(1000j,.00025),complex)

    def test_invalid_inputs_and_explicit_policy(self):
        for value in [True,'0.25',math.nan,math.inf]:
            with self.assertRaises(ValueError):coefficients(value)
            with self.assertRaises(ValueError):simulate([value])
        for value in [-1,0]:
            with self.assertRaises(ValueError):coefficients(value)
        for theta in [math.pi,-math.pi,4.,math.inf]:
            with self.assertRaises(ValueError):prewarp(theta)
        with self.assertRaises(ValueError):modal_map(1,.001,'bad')
        with self.assertRaises(ValueError):modal_map(1000,.001,'backward')
        with self.assertRaises(ValueError):modal_map(2000,.001,'bilinear')
        with self.assertRaises(ValueError):coefficients(1e308,1e-308)
        with self.assertRaises(ValueError):coefficients(1e-308,1e308)
        with self.assertRaises(ValueError):modal_map(10**1000,1)
        with self.assertRaises(ValueError):simulate_codes([],1,1,0,Format(),rounding='bad')
        with self.assertRaises(ValueError):simulate_codes([],1,1,0,Format(),overflow='bad')
        with self.assertRaises(ValueError):simulate_codes([True],1,1,0)
        with self.assertRaises(ValueError):simulate_codes([32768],1,1,0)
        with self.assertRaises(ValueError):Format(16,16)
        with self.assertRaises(ValueError):fir_codes([],[])


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wwl-discrete-');self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.before={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    def tearDown(self):
        after={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts};self.assertEqual(after,self.before)
    def process(self,args):return subprocess.run([sys.executable,'-B',*args],cwd=self.work,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=120)
    def test_import_and_missing_output(self):
        result=self.process(['-c',"import sys;sys.path.insert(0,sys.argv[1]);sys.argv=['alien','--unknown'];import discrete_lab,build_visuals;assert 'cairosvg' not in sys.modules",str(HERE)])
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(list(self.work.iterdir()),[])
        result=self.process([str(HERE/'build_visuals.py')]);self.assertEqual(result.returncode,2,result.stderr);self.assertIn('--output',result.stderr);self.assertEqual(list(self.work.iterdir()),[])
    def test_nested_generation_structure_units_and_codes(self):
        output=self.work/'new'/'nested'/'assets';result=self.process([str(HERE/'build_visuals.py'),'--output',str(output)]);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(list(output.glob('*.svg'))),7)
        for file in output.glob('*.svg'):
            root=ET.parse(file).getroot();ns='{http://www.w3.org/2000/svg}';self.assertTrue(root.find(ns+'title').text);self.assertTrue(root.find(ns+'desc').text)
            for node in root.findall('.//'+ns+'text'):self.assertGreaterEqual(float(node.attrib['font-size']),13)
        for file in output.glob('*.png'):self.assertEqual(struct.unpack('>I',file.read_bytes()[16:20])[0],360 if file.stem.endswith('-360') else 425)
        with (output/'state-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(float(rows[0]['time_s']),0.);self.assertEqual(float(rows[0]['exact_V']),.4)
        self.assertAlmostEqual(float(rows[1]['exact_V']),.5327195301571571,places=14)
        with (output/'integer-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(int(rows[0]['coarse_fixed_code']),1);self.assertEqual(int(rows[1]['coarse_cycle_code']),-1)
        self.assertEqual(int(rows[2]['coarse_cycle_code']),1)


if __name__=='__main__':unittest.main()
```
