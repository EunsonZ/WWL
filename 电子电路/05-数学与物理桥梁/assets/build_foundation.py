"""Reproduce editable foundation views; output path is mandatory; no import-time plotting."""
from pathlib import Path
import argparse, math, json

def build(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    # Load our settings inside build, so importing this module changes no global rc state.
    with plt.rc_context(fname=Path(__file__).with_name('matplotlibrc')):
        def save(fig,name):
            fig.savefig(output/(name+'.svg'),metadata={'Date':None});fig.savefig(output/(name+'.png'),dpi=150);plt.close(fig)
        fig,ax=plt.subplots(figsize=(4.25,6));ax.axhline(0,color='gray');ax.axvline(0,color='gray')
        for x,y in [(1,1),(-1,1),(-1,-1),(1,-1)]:
            ax.plot(x,y,'o');ax.text(x+(.15 if x>0 else -.15),y+(.2 if y>0 else -.35),f'atan2={math.degrees(math.atan2(y,x)):.0f}°',ha='left' if x>0 else 'right',fontsize=9)
        for z,label,color in [(3+4j,'z=3+j4','#1669ac'),(3-4j,'z*=3-j4','#b8630a'),(-4+3j,'jz=-4+j3','#26843a')]:
            ax.annotate('',xy=(z.real,z.imag),xytext=(0,0),arrowprops=dict(arrowstyle='->',color=color,lw=2));ax.text(z.real+.1,z.imag+(.2 if z.imag>0 else -.3),label,color=color,fontsize=10)
        ax.set(xlim=(-6,7),ylim=(-5,5),xlabel='Re (same units as z)',ylabel='Im (same units as z)',title='V07 · coordinates & conjugate\nMultiplication by j: +90°');ax.set_aspect('equal');ax.grid(alpha=.2);save(fig,'V07-complex')
        fig=plt.figure(figsize=(4.25,9));gs=fig.add_gridspec(3,2,height_ratios=[1,1,1.6]);theta=np.linspace(0,2*np.pi,501)
        for k in range(4):
            ax=fig.add_subplot(gs[k//2,k%2]);a=k*np.pi/2
            ax.plot(np.cos(theta),np.sin(theta),color='lightgray');ax.axhline(0,color='gray');ax.axvline(0,color='gray');ax.annotate('',xy=(np.cos(a),np.sin(a)),xytext=(0,0),arrowprops=dict(arrowstyle='->',lw=2,color='#1669ac'));ax.plot([np.cos(a),np.cos(a)],[0,np.sin(a)],'--');ax.set(xlim=(-1.3,1.3),ylim=(-1.3,1.3),title=f't={k/4:g} s\nθ={k}π/2',xlabel='Re',ylabel='Im');ax.set_aspect('equal')
        ax=fig.add_subplot(gs[2,:]);t=theta/(2*np.pi);ax.plot(t,np.cos(theta),label='Re = cos(2πt)');ax.plot(t,np.sin(theta),'--',label='Im = sin(2πt)');ax.scatter(np.arange(4)/4,[1,0,-1,0]);ax.set(xlabel='time t (s), f=1 Hz',ylabel='unit amplitude');ax.legend();ax.grid(alpha=.2);fig.suptitle('V08 · counterclockwise rotation\nFour real projections');save(fig,'V08-frames')
        fig=plt.figure(figsize=(4.25,8));ax=fig.add_subplot(211,projection='3d');t=np.linspace(0,2,501);ax.plot(t,np.cos(2*np.pi*t),np.sin(2*np.pi*t));ax.set(xlabel='time t (s)',ylabel='Re',zlabel='Im',title='V08 · time, Re and Im\nUnit circle, f=1 Hz');ax=fig.add_subplot(212);ax.plot(t,np.cos(2*np.pi*t),label='real projection');ax.plot(t,np.sin(2*np.pi*t),'--',label='imaginary coordinate');ax.set(xlabel='time t (s)',ylabel='unit amplitude');ax.legend();ax.grid(alpha=.2);save(fig,'V08-helix')
        fig,axs=plt.subplots(4,1,figsize=(4.25,14));axs=axs.reshape(2,2);t=np.linspace(0,.04,1001);w=100*np.pi;v=6*np.cos(w*t)+8*np.cos(w*t+np.pi/2)
        ax=axs[0,0];ax.plot(t*1000,v);ax.axhline(10,color='gray',label='peak=10 V');ax.axhline(10/np.sqrt(2),color='orange',ls='--',label='RMS=7.071 V');ax.set(xlabel='time (ms)',ylabel='voltage (V)',title='Same waveform\nPeak and RMS amplitudes');ax.legend()
        ax=axs[0,1]
        for end,start,label in [((6,0),(0,0),'6 V'),((6,8),(6,0),'j8 V'),((6,8),(0,0),'sum: 6+j8 V peak')]:
            ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',lw=2));ax.text({'6 V':2,'j8 V':6.3,'sum: 6+j8 V peak':0.1}[label],{'6 V':-.65,'j8 V':4,'sum: 6+j8 V peak':9}[label],label,fontsize=9)
        ax.set(xlim=(-1,11),ylim=(-1,10),xlabel='Re peak (V)',ylabel='Im peak (V)',title='Same frequency\nVector addition');ax.set_aspect('equal')
        ax=axs[1,0];ax.plot(t*1000,6*np.cos(w*t),label='50 Hz');ax.plot(t*1000,8*np.cos(2*w*t+np.pi/2),label='100 Hz');ax.set(xlabel='time (ms)',ylabel='voltage (V)',title='different time factors');ax.legend()
        ax=axs[1,1];ax.plot(t*1000,6*np.cos(w*t)+8*np.cos(2*w*t+np.pi/2),label='actual two-frequency sum');ax.plot(t*1000,v,'--',label='wrong single 50 Hz phasor');ax.scatter([5],[0],color='black');ax.set(xlabel='time (ms)',ylabel='voltage (V)',title='At 5 ms: actual 0 V\nWrong single-frequency prediction: −8 V');ax.legend(fontsize=10)
        for ax in axs.flat:ax.grid(alpha=.2)
        fig.suptitle('V09 · peak, RMS\nSame-frequency requirement');save(fig,'V09-phasors')
    # Narrow-screen topology: 360px native viewport, text 14px, stacked panels.
    def text(x,y,s):return f'<text x="{x}" y="{y}" fill="#25334a" stroke="none" font-family="DejaVu Sans" font-size="14">{s}</text>'
    def line(x1,y1,x2,y2):return f'<path d="M{x1},{y1} L{x2},{y2}"/>'
    def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="4" fill="#25334a"/>'
    def res(x,y,horiz=True,label='R'):
        if horiz:return line(x,y,x+12,y)+f'<rect x="{x+12}" y="{y-9}" width="45" height="18"/>'+line(x+57,y,x+70,y)+text(x+10,y-17,label)
        return line(x,y,x,y+18)+f'<rect x="{x-9}" y="{y+18}" width="18" height="44"/>'+line(x,y+62,x,y+80)+text(x+14,y+95,label)
    def ground(x,y):return line(x,y,x,y+10)+line(x-12,y+10,x+12,y+10)+line(x-8,y+16,x+8,y+16)+line(x-4,y+22,x+4,y+22)
    def source(x,y,label):return line(x,y-70,x,y-25)+f'<circle cx="{x}" cy="{y}" r="25"/>'+line(x,y+25,x,y+90)+text(x-6,y-6,'+')+text(x-5,y+15,'−')+text(x-20,y-40,label)
    def svg(name,body,h):
        (output/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{h}" viewBox="0 0 360 {h}"><rect width="100%" height="100%" fill="white"/><g stroke="#25334a" fill="none" stroke-width="2">'+body+'</g></svg>')
    b=text(15,25,'V01 · Synthetic circuit symbols')+text(15,48,'Not actual package pinouts')
    b+=res(40,105,True,'resistor R')+text(150,110,'two terminals')
    b+=line(40,190,80,190)+line(80,170,80,210)+line(90,170,90,210)+line(90,190,130,190)+text(150,195,'capacitor C')
    b+=line(40,275,60,275)+'<path d="M60,275 c0,-25 20,-25 20,0 c0,-25 20,-25 20,0 c0,-25 20,-25 20,0"/>'+line(120,275,140,275)+text(170,280,'inductor L')
    b+=source(80,410,'V source')+text(145,410,'voltage source')
    b+=line(80,530,80,555)+'<circle cx="80" cy="580" r="25"/><path d="M80,595 L80,565 m-6,8 6,-8 6,8"/>'+line(80,605,80,640)+text(145,585,'current source')
    b+=ground(80,710)+text(145,725,'reference node 0')+text(15,780,'Check actual model and pin table.')
    svg('V01-symbols',b,810)
    b=text(15,25,'V02 · Opposite reference arrows')
    for k,up in [(0,False),(350,True)]:
        b+=source(55,155+k,'5 V')+line(55,85+k,200,85+k)+res(200,85+k,False,'1 kΩ')+line(200,165+k,200,245+k)+line(55,245+k,200,245+k)+ground(125,245+k)+dot(200,85+k)+text(185,70+k,'a (+)')+text(185,235+k,'0 (−)')
        if up:b+=f'<path d="M235,{140+k} L235,{95+k} m-5,8 5,-8 5,8"/>'+text(245,118+k,'i′ = −5 mA')+text(245,141+k,'0 to a')
        else:b+=f'<path d="M235,{95+k} L235,{140+k} m-5,-8 5,8 5,-8"/>'+text(245,118+k,'i = +5 mA')+text(245,141+k,'a to 0')
        b+=text(15,300+k,'Resistor absorbs +25 mW')+text(15,323+k,'Source absorbs −25 mW')
    svg('V02-signs',b,700)
    b=text(15,25,'V03 · Connections and node identity')
    b+=line(40,130,320,130)+line(180,80,180,200)+dot(180,130)+text(30,110,'a')+text(190,80,'a')+text(310,110,'a')+text(15,225,'Dot: all three wires are node a')
    b+=line(180,290,180,440)+line(40,370,165,370)+'<path d="M165,370 Q180,340 195,370" stroke="white" stroke-width="7"/><path d="M165,370 Q180,340 195,370"/>'+line(195,370,320,370)+text(30,350,'a')+text(195,290,'b')+text(15,470,'Bridge: a and b are not connected')
    b+=line(80,540,80,650)+line(80,650,270,650)+line(270,650,270,570)+dot(80,650)+text(65,525,'a')+text(280,570,'a')+text(15,690,'Folded wire: still the same node a')
    svg('V03-nodes',b,725)
    panels=[]
    for mode in ['open','loaded','equivalent','test']:
        x=50;y=180;b=text(15,28,{'open':'V04a · Open output','loaded':'V04b · Loaded output','equivalent':'V04c · Port equivalent','test':'V04d · Test after source is zeroed'}[mode])
        if mode in ('open','loaded'):
            b+=source(x,y,'5 V')+line(x,110,x+40,110)+res(x+40,110,True,'4 kΩ')+line(x+110,110,x+140,110)+dot(x+140,110)+res(x+140,130,False,'1 kΩ')+line(x+140,110,x+140,130)+line(x+140,210,x+140,270)+line(x,270,x+140,270)+text(x+10,95,'s')
            if mode=='loaded':b+=line(x+140,110,x+215,110)+line(x+215,110,x+215,130)+res(x+215,130,False,'4 kΩ RL')+line(x+215,210,x+215,270)+line(x+140,270,x+215,270)
        elif mode=='equivalent':b+=source(x,y,'1 V')+line(x,110,x+30,110)+res(x+30,110,True,'800 Ω')+line(x+100,110,x+190,110)+res(x+190,130,False,'4 kΩ RL')+line(x+190,110,x+190,130)+line(x+190,210,x+190,270)+line(x,270,x+190,270)
        else:b+=source(x,y,'1 V test')+line(x,110,x+190,110)+line(x+190,110,x+190,130)+res(x+190,130,False,'1 kΩ')+line(x+190,210,x+190,270)+line(x,270,x+190,270)+line(x+100,110,x+100,130)+res(x+100,130,False,'4 kΩ')+line(x+100,210,x+100,270)
        node=x+140 if mode in ('open','loaded') else x+190
        b+=text(node+5,95,'a (+)')+text(node+5,263,'0 (−)')+ground(x+80,270)
        if mode in ('open','loaded'):b+=f'<path d="M{x+95},72 L{x+135},72 m-7,-4 7,4 -7,4"/>'+text(x+92,60,'i1')
        if mode=='loaded':b+=f'<path d="M{x+123},140 L{x+123},190 m-4,-7 4,7 4,-7"/>'+text(x+95,163,'i2')+f'<path d="M{x+240},140 L{x+240},190 m-4,-7 4,7 4,-7"/>'+text(x+245,163,'iL')
        b+=text(15,325,{'open':'Va = 1 V; no external load','loaded':'Va = 5/6 V; i1 = i2 + iL','equivalent':'Va = 5/6 V; only port is equivalent','test':'Is = 1.25 mA into resistor network'}[mode])
        if mode=='test':b+=text(15,348,'Rth = 1 V / Is = 800 Ω')
        svg('V04-'+mode,b,370);panels.append(b)
    body=''.join(f'<g transform="translate(0,{k*380})">{b}</g>' for k,b in enumerate(panels));svg('V04-loading',body,1520)
    data={'nodes':['s','a','0'],'branches':[['Vs','s','0',5],['R1','s','a',4000],['R2','a','0',1000],['RL','a','0',4000]],'v_open_V':1,'v_loaded_V':5/6,'rth_ohm':800,'i1_A':25/24000,'i2_A':5/6000,'iL_A':5/24000,'phasor_peak_V':[6,8],'frequency_Hz':50,'rms_V':10/math.sqrt(2)}
    data['netlists']={'open':[['Vs','s','0',5],['R1','s','a',4000],['R2','a','0',1000]],'loaded':data['branches'],'equivalent':[['Vth','e','0',1],['Rth','e','a',800],['RL','a','0',4000]],'test':[['Vtest','a','0',1],['R1_zeroed_source','a','0',4000],['R2','a','0',1000]]}
    (output/'foundation-data.json').write_text(json.dumps(data,indent=2))
    import cairosvg
    for name in ('V01-symbols','V02-signs','V03-nodes','V04-loading','V04-open','V04-loaded','V04-equivalent','V04-test'):
        cairosvg.svg2png(url=str(output/(name+'.svg')),write_to=str(output/(name+'.png')))

def verify():
    from fractions import Fraction as F
    v=F(5,6);i1=(5-v)/4000;i2=v/1000;il=v/4000
    assert i1==i2+il
    assert i1*i1*4000+i2*i2*1000+il*il*4000==5*i1
    assert (1+1j)/(1-1j)==1j
    for x,y in [(1,1),(-1,1),(-1,-1),(1,-1)]:
        a=math.atan2(y,x);assert abs(math.cos(a)*math.hypot(x,y)-x)<1e-12;assert abs(math.sin(a)*math.hypot(x,y)-y)<1e-12
    for k in range(40):
        t=k/2000;w=100*math.pi;left=6*math.cos(w*t)+8*math.cos(w*t+math.pi/2);right=10*math.cos(w*t+math.atan2(8,6));assert abs(left-right)<1e-12
    t=.005;assert abs(6*math.cos(100*math.pi*t)+8*math.cos(200*math.pi*t+math.pi/2))<1e-12
    n=2000;mean=sum((10*math.cos(2*math.pi*k/n))**2 for k in range(n))/n;assert abs(mean-50)<1e-10
    print('PASS: exact KCL/power, complex division, four quadrants, waveform reconstruction, different-frequency counterexample, RMS integral quadrature')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();verify();build(a.output)
