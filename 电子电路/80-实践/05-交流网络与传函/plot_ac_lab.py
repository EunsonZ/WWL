"""Deterministic SVG/PNG/JSON/CSV views. No plotting at import; explicit output required."""
from pathlib import Path
import argparse, math, json, csv
import ac_lab as a

def build(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import cairosvg
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    with plt.rc_context(fname=Path(__file__).with_name('matplotlibrc')):
        def save(fig,name):
            fig.savefig(out/(name+'.svg'),metadata={'Date':None});fig.savefig(out/(name+'.png'),dpi=150);plt.close(fig)
        def rows(n,height=3):return plt.subplots(n,1,figsize=(4.25,height*n),squeeze=False)
        t=np.linspace(0,2*math.pi/1000,401);v=np.sqrt(2)*np.cos(1000*t);I=.0005+.0005j;V=.5-.5j
        i=np.sqrt(2)*np.real(I*np.exp(1000j*t));vc=np.sqrt(2)*np.real(V*np.exp(1000j*t));vr=v-vc
        fig,axes=rows(2);ax=axes[0,0];ax.plot(t*1000,v,label='source voltage');ax.plot(t*1000,vc,label='capacitor voltage');ax.set(xlabel='time (ms)',ylabel='voltage (V)',title='V10 · RC at ω=1000 rad/s\nR=1 kΩ, C=1 μF; 1 V RMS source');ax.legend();ax=axes[1,0]
        for z,label,color in [(1,'Vs', 'gray'),(V,'VC','#1669ac'),(1-V,'VR','#b85e00')]:
            ax.annotate('',xy=(z.real,z.imag),xytext=(0,0),arrowprops=dict(arrowstyle='->',color=color));ax.text(z.real+.02,z.imag+.03,label,color=color)
        ax.set(xlim=(-.2,1.4),ylim=(-.8,.8),xlabel='Re voltage RMS (V)',ylabel='Im voltage RMS (V)',title='VR + VC = Vs\nI = (0.5+j0.5) mA RMS');ax.set_aspect('equal')
        for ax in axes.flat:ax.grid(alpha=.2)
        save(fig,'V10-rc-phasors')
        fig,axes=rows(3)
        for ax,values,label in [(axes[0,0],v*i,'source port network power'),(axes[1,0],vr*i,'resistor absorbed power'),(axes[2,0],vc*i,'capacitor absorbed power')]:
            ax.plot(t*1000,values*1000,label='instantaneous p(t)');ax.axhline(np.mean(values[:-1])*1000,ls='--',label='cycle mean');ax.set(xlabel='time (ms)',ylabel='power (mW)',title=label);ax.legend();ax.grid(alpha=.2)
        fig.suptitle('V10 · absorbed power account\nNegative p: energy returned');save(fig,'V10-power')
        ws=np.logspace(3,5,1000);fig,axes=rows(3)
        for r in (50,100):axes[0,0].semilogx(ws,[abs(a.series(w,r=r)['HR']) for w in ws],label=f'total R={r} Ω')
        axes[0,0].axhline(1/math.sqrt(2),ls='--',color='gray',label='half-power amplitude');axes[0,0].set(title='Series: total-resistor voltage / Vs',ylabel='amplitude ratio')
        for r in (200,100):axes[1,0].semilogx(ws,[abs(a.parallel(w,r=r))*.005 for w in ws],label=f'Rp={r} Ω')
        axes[1,0].set(title='Parallel: voltage, 5 mA RMS source',ylabel='voltage RMS (V)')
        for key,label in [('HR','total resistor'),('HC','capacitor'),('HL','inductor')]:axes[2,0].semilogx(ws,[abs(a.series(w)[key]) for w in ws],label=label)
        axes[2,0].set(title='Same series network: different outputs',ylabel='amplitude ratio')
        for ax in axes.flat:ax.axvline(10000,color='gray',ls=':');ax.set(xlabel='angular frequency ω (rad/s)');ax.legend();ax.grid(alpha=.2)
        fig.suptitle('V16 · resonance views (partial)\nL=10 mH, C=1 μF');save(fig,'V16-resonance-curves')
        fig,axes=rows(3);tt=np.linspace(0,.006,401)
        for v0 in (0,.4):axes[0,0].plot(tt*1000,[a.rc_step(x,v0) for x in tt],label=f'v0={v0} V')
        axes[0,0].set(xlabel='time (ms)',ylabel='capacitor voltage (V)',title='1 V step; τ=1 ms');axes[0,0].legend()
        ww=np.logspace(1,5,401);hh=1/(1+1j*ww*.001);axes[1,0].semilogx(ww,20*np.log10(abs(hh)));axes[1,0].axvline(1000,ls='--');axes[1,0].set(xlabel='ω (rad/s)',ylabel='magnitude (dB)',title='H(jω), zero-state frequency response')
        axes[2,0].axhline(0,color='gray');axes[2,0].axvline(0,color='gray');axes[2,0].scatter([-1000],[0],marker='x',s=70,label='system pole −1000 s⁻¹');axes[2,0].scatter([0],[0],facecolors='none',edgecolors='orange',label='step U pole (not H pole)');axes[2,0].set(xlim=(-1400,400),ylim=(-600,600),xlabel='Re s (s⁻¹)',ylabel='Im s (s⁻¹)',title='V14 · t / s / jω views (partial)');axes[2,0].legend(fontsize=9)
        for ax in axes.flat:ax.grid(alpha=.2)
        save(fig,'V14-rc-response')
        fig,axes=rows(4);qs=np.linspace(0,5,401)
        for ax,case in zip(axes.flat,['distinct','repeated','conjugate','delay']):
            ax.plot(qs,[a.inverse(q,case) for q in qs]);ax.set(xlabel='q=t/T0; T0=1 s',ylabel='normalized amplitude',title={'distinct':'Distinct poles: e⁻q − e⁻²q','repeated':'Repeated pole: (1+2q)e⁻q','conjugate':'Conjugates: e⁻q cos(2q)','delay':'Delay d=0.5: zero before q=0.5'}[case]);ax.grid(alpha=.2)
        fig.suptitle('V14 · inverse-transform cases');save(fig,'V14-inverse-cases')
        fig,axes=rows(4);ax=axes[0,0];ax.axhline(0,color='gray');ax.axvline(0,color='gray');ax.scatter([-1],[0],marker='x',s=90,label='double pole −1');ax.scatter([1],[0],facecolors='none',edgecolors='orange',label='RHP zero +1');ax.set(xlim=(-2,2),ylim=(-1,1),xlabel='Re p',ylabel='Im p',title='H−=(1−p)/(1+p)²');ax.legend()
        ax=axes[1,0];ax.plot(qs,[a.inverse(q,'rhp_step') for q in qs],label='RHP-zero step');ax.plot(qs,1-np.exp(-qs),'--',label='H+=1/(1+p)');ax.scatter([.5],[1-2*math.exp(-.5)]);ax.set(xlabel='q=t/T0; T0=1 s',ylabel='normalized output',title='Initial reverse response ≠ instability');ax.legend()
        nu=np.logspace(-2,2,401);hp=1/(1+1j*nu);hm=(1-1j*nu)/(1+1j*nu)**2
        axes[2,0].semilogx(nu,20*np.log10(abs(hm)),label='H− exact');axes[2,0].semilogx(nu,20*np.log10(abs(hp)),'--',label='H+ exact (same magnitude)');axes[2,0].semilogx(nu,np.where(nu<1,0,-20*np.log10(nu)),':',label='asymptote');axes[2,0].set(xlabel='ν=ωT0 (rad)',ylabel='magnitude (dB)',title='Magnitude alone misses the RHP zero');axes[2,0].legend(fontsize=9)
        axes[3,0].semilogx(nu,-3*np.arctan(nu)*180/np.pi,label='H− continuous phase');axes[3,0].semilogx(nu,-np.arctan(nu)*180/np.pi,label='H+ continuous phase');axes[3,0].set(xlabel='ν=ωT0 (rad)',ylabel='phase (degrees)',title='Phase branch continuous from 0°');axes[3,0].legend()
        for ax in axes.flat:ax.grid(alpha=.2)
        fig.suptitle('V15 · poles, Bode and step');save(fig,'V15-rhp-zero')
        fig,axes=rows(2);q=np.linspace(0,6,401);axes[0,0].plot(q,1-np.exp(-q),label='y=x1=1−e⁻q');axes[0,0].plot(q,np.exp(q)-1,label='x2=e^q−1');axes[0,0].set(xlabel='q=t/T0; T0=1 s',ylabel='normalized state/output',title='Input excites an unobserved unstable mode');axes[0,0].legend()
        axes[1,0].plot(q,1-np.exp(-q),label='y=x1');axes[1,0].plot(q,1-np.exp(-q)+.001*(np.exp(q)-1),label='y=x1+0.001x2');axes[1,0].set(xlabel='q=t/T0; T0=1 s',ylabel='normalized output',title='Small extra readout exposes the mode');axes[1,0].legend()
        for ax in axes.flat:ax.grid(alpha=.2)
        fig.suptitle('V15 · hidden state / IO distinction');save(fig,'V15-hidden-mode')
        fig,axes=rows(3);p=1j*nu
        for H,label,asym in [(1/(1+p),'one pole',np.where(nu<1,0,-20*np.log10(nu))),((1+p),'one zero (improper alone)',np.where(nu<1,0,20*np.log10(nu))),(1/(1+p)**2,'repeated pole',np.where(nu<1,0,-40*np.log10(nu)))]:
            axes[0,0].semilogx(nu,20*np.log10(abs(H)),label=label);axes[1,0].semilogx(nu,asym,label=label);axes[2,0].semilogx(nu,np.unwrap(np.angle(H))*180/np.pi,label=label)
        for ax,yl,title in zip(axes.flat,['magnitude (dB)','magnitude (dB)','phase (degrees)'],['Exact elementary factors','Magnitude asymptotes','Continuous phase from 0°']):ax.set(xlabel='ν=ωT0; T0=1 s',ylabel=yl,title=title);ax.grid(alpha=.2);ax.legend(fontsize=9)
        fig.suptitle('V15 · elementary pole / zero factors\nA standalone zero is not a proper system');save(fig,'V15-pole-cases')
    # Actual circuit topologies: editable SVG, native width 360 and 14px labels.
    def text(x,y,s):return f'<text x="{x}" y="{y}" fill="#25334a" stroke="none" font-family="DejaVu Sans" font-size="14">{s}</text>'
    def line(x1,y1,x2,y2):return f'<path d="M{x1},{y1} L{x2},{y2}"/>'
    def res(x,y,h=True,label='R'):
        if h:return line(x,y,x+10,y)+f'<rect x="{x+10}" y="{y-8}" width="40" height="16"/>'+line(x+50,y,x+60,y)+text(x+5,y-15,label)
        return line(x,y,x,y+12)+f'<rect x="{x-8}" y="{y+12}" width="16" height="40"/>'+line(x,y+52,x,y+70)+text(x-20,y+90,label)
    def cap(x,y):return line(x,y,x,y+25)+line(x-15,y+25,x+15,y+25)+line(x-15,y+35,x+15,y+35)+line(x,y+35,x,y+70)
    def ind(x,y):return line(x,y,x,y+10)+f'<path d="M{x},{y+10} c25,0 25,15 0,15 c25,0 25,15 0,15 c25,0 25,15 0,15"/>'+line(x,y+55,x,y+70)
    def source(x,y,current=False):
        b=line(x,y-70,x,y-25)+f'<circle cx="{x}" cy="{y}" r="25"/>'+line(x,y+25,x,y+90)
        return b+(f'<path d="M{x},{y+12} L{x},{y-12} m-5,7 5,-7 5,7"/>' if current else text(x-5,y-7,'+')+text(x-5,y+15,'−'))
    def svg(name,body,h):
        (out/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="360" height="{h}" viewBox="0 0 360 {h}"><rect width="100%" height="100%" fill="white"/><g stroke="#25334a" fill="none" stroke-width="2">'+body+'</g></svg>');cairosvg.svg2png(url=str(out/(name+'.svg')),write_to=str(out/(name+'.png')))
    b=''
    for k,loaded in [(0,False),(410,True)]:
        body=text(15,25+k,'V10 · '+('loaded RC' if loaded else 'ideal RC'))+text(15,48+k,'Vs=1 V RMS; ω=1000 rad/s')+source(40,200+k)+text(5,155+k,'Vs')
        if loaded:body+=res(40,130+k,True,'Rs200Ω')+line(100,130+k,110,130+k)+res(110,130+k,True,'R1kΩ')+line(170,130+k,225,130+k)
        else:body+=line(40,130+k,95,130+k)+res(95,130+k,True,'R1kΩ')+line(155,130+k,225,130+k)
        body+=line(225,130+k,225,165+k)+cap(225,165+k)+line(225,235+k,225,290+k)+line(40,290+k,225,290+k)+text(230,115+k,'a (+)')+text(235,260+k,'0 (−)')+text(160,220+k,'C1μF')
        if loaded:body+=line(225,130+k,305,130+k)+line(305,130+k,305,165+k)+res(305,165+k,False,'RL10kΩ')+line(305,235+k,305,290+k)+line(225,290+k,305,290+k)
        body+=f'<path d="M175,{95+k} L215,{95+k} m-7,-4 7,4 -7,4"/>'+text(175,85+k,'I to a')+text(15,350+k,'All voltages measured against node 0.')
        b+=body
    svg('V10-rc-topology',b,795)
    b=text(15,25,'V16 · Series resonance')+text(15,48,'Vs=1 V RMS; total Rt=50 Ω')+source(40,200)+text(5,155,'Vs')+line(40,130,170,130)+res(170,130,True,'Rt')+line(230,130,300,130)+line(300,130,300,165)+ind(300,165)+line(300,235,300,270)+cap(300,270)+line(300,340,300,360)+line(40,290,40,360)+line(40,360,300,360)+text(235,210,'L10mH')+text(225,320,'C1μF')+text(15,385,'Same series current; C and L opposite phase.')
    b+=text(15,435,'V16 · Parallel resonance')+text(15,458,'Is=5 mA RMS; Rp=200 Ω')+source(40,600,True)+text(5,555,'Is')+line(40,530,300,530)+line(130,530,130,570)+res(130,570,False,'Rp200Ω')+line(130,640,130,690)+line(210,530,210,570)+ind(210,570)+line(210,640,210,690)+line(300,530,300,570)+cap(300,570)+line(300,640,300,690)+line(40,690,300,690)+text(185,675,'L10mH')+text(272,675,'C1μF')+text(285,513,'a (+)')+text(285,715,'0 (−)')+text(15,755,'Parallel voltage shared; branch currents cancel.')
    svg('V16-resonance-topology',b,790)
    def cj(z):return {'real':z.real,'imag':z.imag}
    loaded=a.rc(1000,rs=200,rl=10000);power=a.power_rc()
    data={'units':'SI; RMS phasors; p=sT0, q=t/T0 with T0=1s for normalized examples','loaded_rc':{k:cj(v) if isinstance(v,complex) else v for k,v in loaded.items()},'power_rc':{k:cj(v) if isinstance(v,complex) else v for k,v in power.items()},'series':a.resonance(),'parallel':a.resonance(r=200,parallel=True),'netlists':{'idealRC':[['Vs','s','0','1 V RMS'],['R','s','a','1000 ohm'],['C','a','0','1e-6 F']],'loadedRC':[['Vs','s','0','1 V RMS'],['Rs','s','b','200 ohm'],['R','b','a','1000 ohm'],['C','a','0','1e-6 F'],['RL','a','0','10000 ohm']],'seriesRLC':[['Vs','s','0','1 V RMS'],['Rt','s','b','50 ohm'],['L','b','c','0.01 H'],['C','c','0','1e-6 F']],'parallelRLC':[['Is','0','a','0.005 A RMS'],['Rp','a','0','200 ohm'],['L','a','0','0.01 H'],['C','a','0','1e-6 F']]}}
    (out/'results.json').write_text(json.dumps(data,indent=2))
    with (out/'waveforms.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['time_s','vs_V','vc_V','i_A','p_network_W','p_R_W','p_C_W'])
        writer.writerows(zip(t,v,vc,i,v*i,vr*i,vc*i))
    print('generated 10 editable SVG/PNG views, RMS data, explicit netlists and waveform CSV')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();build(args.output)
