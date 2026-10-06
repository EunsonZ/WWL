"""Original editable circuit/curve assets. Import performs no plotting or output.

Run from the vault root with --output pointing to a caller-selected external folder.
The generator may replace same-named files inside that explicit output directory.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from storage_models import rc_interval, rlc_state, storage_energy, mutual_energy


def generate(output):
    """Generate original model assets and return their paths; no measured data."""
    import numpy as np
    import matplotlib
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle
    import cairosvg

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    created = []

    def subplots(*args, **kwargs):
        # Direct Figure construction avoids a GUI backend and pyplot global registry.
        fig = Figure(**kwargs)
        return fig, fig.subplots(*args)

    def save(fig, name):
        svg = out / (name + '.svg')
        fig.savefig(svg, format='svg', metadata={'Date': None, 'Creator': 'WWL storage models'})
        fig.clear()
        created.append(svg)
        for width in (360, 425):
            dest = out / f'{name}-{width}.png'
            cairosvg.svg2png(url=str(svg), write_to=str(dest), output_width=width)
            created.append(dest)

    def schematic(ax, title):
        ax.set(xlim=(-.5, 7.5), ylim=(-.8, 4.6), aspect='equal')
        ax.set_title(title, loc='left', pad=12, fontsize=14)
        ax.axis('off')

    def wire(ax, x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color='#202124', linewidth=1.8)

    def text(ax, x, y, label, **kw):
        ax.text(x, y, label, fontsize=12, ha='center', va='center', **kw)

    def node(ax, x, y, label=None, above=True):
        ax.plot(x, y, 'o', color='#202124', markersize=4)
        if label: text(ax, x, y + (.35 if above else -.35), label)

    def arrow(ax, start, end, label=None, loc=None):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops={'arrowstyle': '->', 'color': '#202124', 'lw': 1.6})
        if label: text(ax, *(loc or ((start[0]+end[0])/2+.5, (start[1]+end[1])/2)), label)

    def r_horizontal(ax, x, y, label):
        wire(ax, x, y, x+.4, y)
        xs = [x+.4, x+.6, x+.8, x+1, x+1.2, x+1.4, x+1.6]
        ys = [y, y+.15, y-.15, y+.15, y-.15, y+.15, y]
        ax.plot(xs, ys, color='#202124', lw=1.8)
        wire(ax, x+1.6, y, x+2, y)
        text(ax, x+1, y+.5, label)

    def r_vertical(ax, x, y, label):
        wire(ax, x, y, x, y-.6)
        ys = [y-.6, y-.8, y-1, y-1.2, y-1.4, y-1.6, y-1.8]
        xs = [x, x+.15, x-.15, x+.15, x-.15, x+.15, x]
        ax.plot(xs, ys, color='#202124', lw=1.8)
        wire(ax, x, y-1.8, x, 0)
        text(ax, x+.65, y-1.2, label)

    def cap(ax, x, y, label):
        wire(ax, x, y, x, 1.6)
        wire(ax, x-.45, 1.6, x+.45, 1.6)
        wire(ax, x-.45, 1.35, x+.45, 1.35)
        wire(ax, x, 1.35, x, 0)
        text(ax, x+.65, .95, label)
        text(ax, x-.6, 2, '+')
        text(ax, x-.6, .55, '−')

    def coil(ax, x, y, label):
        wire(ax, x, y, x, 2.3)
        for yc in np.linspace(2.13, .77, 5):
            theta = np.linspace(math.pi/2, -math.pi/2, 30)
            ax.plot(x+.25*np.cos(theta), yc+.17*np.sin(theta), color='#202124', lw=1.8)
        wire(ax, x, .6, x, 0)
        text(ax, x+.8, 1.45, label)
        text(ax, x-.4, 2.15, '+')
        text(ax, x-.4, .8, '−')

    def source(ax, x, y, label, current=False):
        wire(ax, x, y, x, 2)
        ax.add_patch(Circle((x, 1.4), .6, fill=False, color='#202124', lw=1.8))
        wire(ax, x, .8, x, 0)
        if current: arrow(ax, (x, 1.05), (x, 1.75))
        else:
            text(ax, x, 1.65, '+'); text(ax, x, 1.1, '−')
        text(ax, x-1, 1.4, label)

    def plot_style(ax, xlabel, ylabel):
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
        ax.grid(True, color='#bbbbbb', alpha=.45)

    rc_params = [dict(source_V=1., source_R_ohm=1000., C_F=1e-6),
                 dict(source_V=2., source_R_ohm=2000., C_F=1e-6, load_R_ohm=4000.)]
    v1 = rc_interval(.4, .001, **rc_params[0])[0]
    with matplotlib.rc_context({'font.family': 'DejaVu Sans', 'font.size': 12,
                                'axes.labelsize': 12, 'axes.titlesize': 13,
                                'svg.fonttype': 'none', 'svg.hashsalt': 'wwl-rlc-r1',
                                'figure.facecolor': 'white', 'axes.facecolor': 'white',
                                'savefig.facecolor': 'white'}):
        fig, axes = subplots(3, 1, figsize=(5, 10), layout='constrained')
        for ax, title, u, r, load in zip(axes[:2],
            ['A: 0 ≤ t < 1 ms', 'B: t ≥ 1 ms; same C and node a'], [1, 2], ['1 kΩ','2 kΩ'], [False,True]):
            schematic(ax, title); source(ax, 1, 3, f'{u} V')
            wire(ax, 1, 3, 2, 3); r_horizontal(ax, 2, 3, r)
            wire(ax, 4, 3, 6.3, 3); cap(ax, 6.3, 3, '1 μF')
            wire(ax, 1, 0, 6.3, 0); node(ax, 6.3, 3, 'a'); node(ax, 1, 0, '0', False)
            arrow(ax, (5.3, 2.6), (5.3, 1.8), 'iC', (4.9, 2.25))
            if load: r_vertical(ax, 4.2, 3, '4 kΩ'); node(ax, 4.2, 3)
        ts=np.linspace(0,.002,401)
        vs=[rc_interval(.4,t,**rc_params[0])[0] if t<=.001 else rc_interval(v1,t-.001,**rc_params[1])[0] for t in ts]
        axes[2].plot(ts*1000,vs,color='#0969a2',lw=2,label='vC(t), initial 0.4 V')
        axes[2].plot(1,v1,'o',color='black');axes[2].axvline(1,color='black',ls='--')
        axes[2].annotate('same voltage\nnew slope',xy=(1,v1),xytext=(.1,1.15),arrowprops={'arrowstyle':'->'})
        plot_style(axes[2],'absolute t (ms)','vC (V)');axes[2].legend(fontsize=10)
        save(fig,'piecewise-rc')

        fig, axes=subplots(3,1,figsize=(5,10),layout='constrained')
        for ax,title,u in zip(axes[:2], ['Before 0−: DC steady state', 'After 0+: same closed RL branch'], [2,1]):
            schematic(ax,title);source(ax,1,3,f'{u} V');wire(ax,1,3,2,3)
            r_horizontal(ax,2,3,'100 Ω');wire(ax,4,3,5.2,3);coil(ax,5.2,3,'10 mH');wire(ax,1,0,5.2,0)
            arrow(ax,(4.4,2.4),(4.4,1.8),'iL',(4,2.1));node(ax,1,0,'0',False)
            text(ax,3,-.65,'iL(0−) = iL(0+) = 20 mA')
        ax=axes[2]; schematic(ax,'s-domain initial source: equivalent relation')
        # Series branch direction is downward. The source is a rise, not a drop.
        node(ax,1.5,3.5,'a');wire(ax,1.5,3.5,1.5,2.9)
        ax.plot([1.15,1.85,1.85,1.15,1.15],[2.9,2.9,2.15,2.15,2.9],color='#202124',lw=1.8)
        wire(ax,1.5,2.15,1.5,1.9)
        ax.add_patch(Circle((1.5,1.3),.6,fill=False,color='#202124',lw=1.8))
        text(ax,1.5,1.55,'−');text(ax,1.5,1.0,'+')
        wire(ax,1.5,.7,1.5,0);node(ax,1.5,0,'0',False)
        text(ax,2.8,2.5,'sL');text(ax,3.8,1.3,'L i(0−) = 0.2 mV·s')
        arrow(ax,(.45,2.7),(.45,1.9),'I(s)',(.1,3.15))
        ax.text(3.5,3.6,'V(s)=sL I(s)−L i(0−)',fontsize=12,ha='center')
        ax.text(3.4,-.65,'Advanced: voltage impulse can change iL.',fontsize=10,ha='center')
        save(fig,'switch-rl')

        fig,axes=subplots(2,1,figsize=(5,7),layout='constrained')
        ax=axes[0];schematic(ax,'Series loop: u, R, L, C')
        source(ax,1,3,'u (V)');wire(ax,1,3,2,3);r_horizontal(ax,2,3,'R')
        # L is horizontal; rotate its separate winding trace.
        xs=np.linspace(4,5.5,120); ax.plot(xs,3+.2*np.sin(np.linspace(0,10*math.pi,120)),color='#202124',lw=1.8)
        text(ax,4.75,3.6,'L');wire(ax,5.5,3,6.3,3);cap(ax,6.3,3,'C');wire(ax,1,0,6.3,0)
        arrow(ax,(3.7,2.55),(4.5,2.55),'i',(4.1,2.1));node(ax,1,0,'0',False)
        ax=axes[1];schematic(ax,'Parallel: current injected into a')
        source(ax,1,3,'I (A)',True);wire(ax,1,3,6.3,3);wire(ax,1,0,6.3,0)
        r_vertical(ax,3,3,'R');cap(ax,4.7,3,'C');coil(ax,6.3,3,'L')
        arrow(ax,(5.6,2.5),(5.6,1.7),'iL',(5.2,2.1));node(ax,4.7,3,'a');node(ax,1,0,'0',False)
        save(fig,'rlc-topologies')

        rs=[50,200,400]; zs=[.25,1,2]; colors=['#1266a0','#a83f12','#555555']; styles=['-','--',':']
        fig,axes=subplots(2,1,figsize=(5,8),layout='constrained')
        times=np.linspace(0,.0015,601)
        rows=[]
        for r,z,col,sty,mark in zip(rs,zs,colors,styles,['x','o','s']):
            a=r/.02; delta=complex(a*a-1e8)**.5; poles=[-a+delta,-a-delta]
            axes[0].plot([p.real/1000 for p in poles],[p.imag/1000 for p in poles],marker=mark,linestyle='none',ms=9,mfc='none',color=col,label=f'series R={r} Ω; ζ={z:g}')
            vals=[rlc_state(t,r,.01,1e-6,1,0) for t in times]
            axes[1].plot(times*1000,[v for v,i in vals],sty,color=col,lw=2,label=f'R={r} Ω')
            for t,(v,i) in zip(times,vals):rows.append([r,t,v,i,storage_energy(v,i,.01,1e-6)])
        axes[0].axhline(0,color='black',lw=.7);axes[0].axvline(0,color='black',lw=.7)
        plot_style(axes[0],'Re(s) (10³ s⁻¹)','Im(s) (10³ s⁻¹)');axes[0].legend(fontsize=10,loc='upper left')
        plot_style(axes[1],'t (ms)','vC (V)');axes[1].legend(fontsize=11)
        axes[1].set_title('Same initial state: v=1 V, i=0 A, u=0 V')
        save(fig,'damping-poles')
        fig,axes=subplots(2,1,figsize=(5,8),layout='constrained')
        for r,z,col,sty in zip(rs,zs,colors,styles):
            vals=[rlc_state(t,r,.01,1e-6,1,0) for t in times]
            axes[0].plot([v for v,i in vals],[i/.01 for v,i in vals],sty,color=col,lw=2,label=f'R={r} Ω, ζ={z:g}')
            for idx in [8,30,60]:
                arrow(axes[0], (vals[idx][0],vals[idx][1]/.01), (vals[idx+1][0],vals[idx+1][1]/.01))
            axes[1].plot(times*1000,[storage_energy(v,i,.01,1e-6)*1e6 for v,i in vals],sty,color=col,lw=2,label=f'R={r} Ω')
        theta=np.linspace(0,2*math.pi,361);axes[0].plot(np.cos(theta),np.sin(theta),color='gray',ls='-.',label='R=0: constant energy')
        axes[0].set_aspect('equal',adjustable='box');plot_style(axes[0],'x = v/(1 V)','y = i/(10 mA)');axes[0].legend(fontsize=9)
        axes[0].set_title('Arrow: time direction; E=0.5(x²+y²) μJ')
        plot_style(axes[1],'t (ms)','stored E (μJ)');axes[1].legend(fontsize=10)
        save(fig,'energy-phase')

        fig,axes=subplots(2,1,figsize=(5,8),layout='constrained')
        exact_t=np.linspace(0,.001,401)
        exact=[rlc_state(t,50,.01,1e-6,1,0) for t in exact_t]
        axes[0].plot(exact_t*1000,[v for v,i in exact],color='black',lw=2,label='continuous exact')
        axes[1].plot(exact_t*1000,[storage_energy(v,i,.01,1e-6)*1e6 for v,i in exact],color='black',lw=2,label='continuous exact')
        euler_rows=[]
        for step,style in [(25e-6,'--'),(50e-6,':'),(100e-6,'-.')]:
            n=round(.001/step);state=np.array([1.,0.]);samples=[(0.,*state)]
            for j in range(n):
                state=state+step*np.array([state[1]/1e-6,(-50*state[1]-state[0])/.01])
                samples.append(((j+1)*step,*state))
            label=f'Euler T={step*1e6:g} μs'+(' (boundary)' if step==50e-6 else '')
            axes[0].plot([t*1000 for t,v,i in samples],[v for t,v,i in samples],style,lw=1.7,label=label)
            axes[1].plot([t*1000 for t,v,i in samples],[storage_energy(v,i,.01,1e-6)*1e6 for t,v,i in samples],style,lw=1.7,label=label)
            euler_rows.extend([[step,t,v,i,storage_energy(v,i,.01,1e-6)] for t,v,i in samples])
        plot_style(axes[0],'t (ms)','vC (V)');axes[0].legend(fontsize=9)
        plot_style(axes[1],'t (ms)','E (μJ)');axes[1].legend(fontsize=9)
        axes[0].set_title('Same passive RLC: R50 Ω, L10 mH, C1 μF')
        axes[1].set_title('Strict Euler condition: 0 < T < 50 μs')
        save(fig,'euler-energy')

        fig,axes=subplots(2,1,figsize=(5,7),layout='constrained')
        ax=axes[0];schematic(ax,'Two separate ports: dots are not wires')
        coil(ax,2,3,'L1');coil(ax,5.3,3,'L2')
        node(ax,2,3);text(ax,2.65,3.25,'1+')
        node(ax,2,0,'1−',False);node(ax,5.3,3);text(ax,5.95,3.25,'2+')
        node(ax,5.3,0,'2−',False)
        ax.plot([2.5,5.8],[2.2,2.2],'o',color='black',ms=7)
        arrow(ax,(2,4.05),(2,3.15),'i1',(1.5,3.75));arrow(ax,(5.3,4.05),(5.3,3.15),'i2',(4.8,3.75))
        ax.text(3.8,1.5,'M',ha='center',fontsize=14)
        ax=axes[1];ax.axis('off')
        ax.text(.02,.85,'Both currents enter dotted terminals.\nv1, v2: dot minus non-dot.\nλ1=L1 i1+M i2; λ2=M i1+L2 i2',transform=ax.transAxes,fontsize=13)
        ax.text(.02,.47,'L1=10 mH, L2=40 mH, k=0.8\nM=16 mH; open port 2: di2/dt=0\ndi1/dt=100 A/s ⇒ v2=1.6 V',transform=ax.transAxes,fontsize=13)
        ax.text(.02,.10,'Reversing a reference changes signs\nin both the matrix and port power.',transform=ax.transAxes,fontsize=12)
        save(fig,'coupled-dots')

        fig,axes=subplots(4,1,figsize=(5,13),layout='constrained')
        xx,yy=np.meshgrid(np.linspace(-3,3,180),np.linspace(-3,3,180))
        for ax,k in zip(axes,[0,.8,1,1.25]):
            # Teaching illustration includes the rejected parameter to reveal negative energy.
            ee=.5*(xx*xx+4*k*xx*yy+4*yy*yy) # μJ; both currents normalized by 10 mA
            levels=[-2,-.5,.5,2,5] if k>1 else [.5,2,5]
            cs=ax.contour(xx,yy,ee,levels=levels,colors=['#333333'],linewidths=1)
            ax.clabel(cs,inline=True,fontsize=10,fmt='%g μJ')
            ax.set_aspect('equal');plot_style(ax,'i1 / (10 mA)','i2 / (10 mA)')
            ax.set_title(f'k={k:g}: '+('invalid indefinite energy' if k>1 else ('PSD, null line i1=−2i2' if k==1 else 'positive definite energy')))
            if k==1: ax.plot([-3,3],[1.5,-1.5],ls='--',color='#1266a0')
        save(fig,'coupling-energy')

        fig,axes=subplots(3,1,figsize=(5,10),layout='constrained')
        t=np.linspace(0,.001,101); current=.2*t/.01; voltage=.1e-3*t/1e-6
        axes[0].fill_between(t*1000,0,.2,color='#1266a0',alpha=.2)
        axes[0].plot(t*1000,np.full_like(t,.2),color='#1266a0',lw=2)
        axes[0].set_ylim(0,.3);plot_style(axes[0],'t (ms)','vL (V)')
        axes[0].set_title('L=10 mH: voltage area = 0.2 mV·s')
        axes[1].plot(t*1000,current*1000,color='#1266a0',lw=2,label='iL; slope 20 A/s')
        plot_style(axes[1],'t (ms)','iL (mA)');axes[1].legend(fontsize=11)
        axes[1].set_title('vL=L diL/dt; ΔiL=20 mA; iL(0)=0')
        axes[2].plot(t*1000,.5*.01*current**2*1e6,color='#1266a0',lw=2,label='EL=½ L iL²')
        plot_style(axes[2],'t (ms)','EL (μJ)');axes[2].legend(fontsize=11)
        axes[2].set_title('End: EL=2 μJ; integral(vL iL dt)=2 μJ')
        save(fig,'inductor-area')
        fig,axes=subplots(3,1,figsize=(5,9),layout='constrained')
        axes[0].fill_between(t*1000,0,.1,color='#a83f12',alpha=.2);axes[0].plot(t*1000,np.full_like(t,.1),color='#a83f12',lw=2)
        plot_style(axes[0],'t (ms)','iC (mA)');axes[0].set_ylim(0,.15);axes[0].set_title('C=1 μF; charge area = 0.1 μC')
        axes[1].plot(t*1000,voltage,color='#a83f12',lw=2);plot_style(axes[1],'t (ms)','vC (V)');axes[1].set_title('iC=C dvC/dt; ΔvC=0.1 V; vC(0)=0')
        axes[2].plot(t*1000,.5e-6*voltage**2*1e6,color='#a83f12',lw=2);plot_style(axes[2],'t (ms)','EC (μJ)');axes[2].set_title('EC=½ C vC²; end = 0.005 μJ')
        save(fig,'capacitor-area')

        fig,axes=subplots(6,1,figsize=(5,15),layout='constrained')
        modal_rows=[]
        tm=np.linspace(0,.002,241)
        for ax,(sigma,omega) in zip(axes,[(s,w) for s in [-1000,0,1000] for w in [2000,6000]]):
            env=np.exp(sigma*tm);val=env*np.cos(omega*tm)
            ax.plot(tm*1000,val,color='#1266a0',lw=1.8,label='Re(exp(st))')
            ax.plot(tm*1000,env,color='gray',ls='--');ax.plot(tm*1000,-env,color='gray',ls='--')
            plot_style(ax,'t (ms)','dimensionless')
            ax.set_title(f'σ={sigma} s⁻¹; ω={omega} rad/s')
            for time,realval in zip(tm,val):modal_rows.append([sigma,omega,time,realval])
        save(fig,'six-modal-waves')
        fig,ax=subplots(figsize=(5,5),layout='constrained')
        for sigma in [-1000,0,1000]:
            for omega in [2000,6000]:
                ax.plot([sigma,sigma],[omega,-omega],'x',ms=9,color='#1266a0')
        ax.axhline(0,color='black',lw=.8);ax.axvline(0,color='black',lw=.8)
        ax.set_xticks([-1000,0,1000]);ax.set_yticks([-6000,-2000,0,2000,6000])
        plot_style(ax,'σ = Re(s) (s⁻¹)','ω = Im(s) (rad/s)')
        ax.set_title('3 decay/growth rates × 2 frequencies\n12 conjugate points; six real waveforms')
        save(fig,'modal-conjugates')

    for name,headers,data in [('rlc-model.csv',['R_ohm','t_s','v_V','i_A','E_J'],rows),
                              ('euler-model.csv',['step_s','t_s','v_V','i_A','E_J'],euler_rows),
                              ('modal-model.csv',['sigma_per_s','omega_rad_per_s','t_s','real_dimensionless'],modal_rows)]:
        dest=out/name
        with dest.open('w',newline='',encoding='utf-8') as fh:
            writer=csv.writer(fh);writer.writerow(headers);writer.writerows(data)
        created.append(dest)
    meta=out/'model-parameters.json'
    meta.write_text(json.dumps({'kind':'model_prediction_not_measurement','RLC':{'L_H':.01,'C_F':1e-6,'series_R_ohm':[50,200,400],'parallel_R_ohm':[200,50,25],'v0_V':1,'i0_A':0},'piecewise':rc_params,'mutual':{'L1_H':.01,'L2_H':.04,'valid_k':[0,.8,1],'invalid_illustration_k':1.25}},indent=2)+'\n')
    created.append(meta)
    return created


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    generate(args.output)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
