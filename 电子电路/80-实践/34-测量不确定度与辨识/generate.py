"""Explicit empty external output only; no plotting imports or writes at import."""
import argparse
import csv
import json
from pathlib import Path
import models as m

MAIN=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
HERE=Path(__file__).resolve().parents[2]


def output_path(output):
    if output is None:raise ValueError('explicit output required')
    p=Path(output).expanduser().resolve()
    for root in (MAIN,HERE):
        if p==root or root in p.parents:raise ValueError('output must be outside main and published electronics subtree')
    if p.exists() and (not p.is_dir() or any(p.iterdir())):
        raise ValueError('output must be absent or an empty directory')
    return p


def generate(output):
    out=output_path(output)
    # Third-party libraries deliberately lazy; no global pyplot or backend selection.
    import math
    import numpy as np
    import matplotlib as mpl
    from matplotlib.figure import Figure
    import cairosvg
    assets=out/'assets';data=out/'data'
    assets.mkdir(parents=True);data.mkdir()
    (assets/'probe-circuit.svg').write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="460" viewBox="0 0 640 460"><rect width="640" height="460" fill="white"/><g stroke="#111" stroke-width="2.5" fill="none"><path d="M55 125 H135 V85 H215 M255 85 H345 V125 H400 M135 125 V180 H215 M255 180 H345 V125 M400 125 H515 V235 M515 285 V355 H55 V170 M400 125 V235 M400 285 V355"/><rect x="215" y="70" width="40" height="30"/><path d="M225 162 V198 M245 162 V198 M215 180 H225 M245 180 H255"/><rect x="385" y="235" width="30" height="50"/><path d="M495 245 H535 M495 275 H535 M515 235 V245 M515 275 V285"/><circle cx="55" cy="125" r="5"/><circle cx="55" cy="170" r="5"/><path d="M335 355 V385 M320 385 H350 M326 393 H344 M332 401 H338"/></g><g fill="#111"><circle cx="135" cy="125" r="4"/><circle cx="345" cy="125" r="4"/><circle cx="400" cy="125" r="4"/><circle cx="400" cy="355" r="4"/><circle cx="515" cy="355" r="4"/></g><g font-family="DejaVu Sans" font-size="19" fill="#111"><text x="25" y="35">Teaching compensated divider (no cable model)</text><text x="35" y="108">tip a</text><text x="30" y="200">0 / return</text><text x="185" y="60">Ra = 9 Mohm</text><text x="165" y="225">Ca adjustable</text><text x="367" y="105">scope b</text><text x="335" y="315">Rb=1 Mohm</text><text x="485" y="315">Cb=20 pF</text><text x="35" y="440">Input: Va-V0. Readout: Vb-V0. Common return shown.</text></g></svg>\n""")
    (assets/'experiment-circuit.svg').write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="560" viewBox="0 0 640 560"><rect width="640" height="560" fill="white"/><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="#111"/></marker></defs><g stroke="#111" stroke-width="2.5" fill="none"><path d="M65 175 V105 H170 M230 105 H300 H435 H540 M65 225 V330 H540 V235 M300 105 V170 M300 210 V330 M435 105 V170 M435 230 V330 M540 105 V170 M540 210 V235"/><circle cx="65" cy="200" r="25"/><rect x="170" y="90" width="60" height="30"/><path d="M280 180 H320 M280 200 H320 M300 170 V180 M300 200 V210 M520 180 H560 M520 200 H560 M540 170 V180 M540 200 V210"/><rect x="420" y="170" width="30" height="60"/><path d="M250 75 H300" marker-end="url(#arrow)"/><path d="M300 330 V360 M285 360 H315 M290 369 H310 M296 378 H304"/></g><g fill="#111"><circle cx="300" cy="105" r="4"/><circle cx="435" cy="105" r="4"/><circle cx="300" cy="330" r="4"/><circle cx="435" cy="330" r="4"/></g><g font-family="DejaVu Sans" font-size="19" fill="#111"><text x="25" y="30">Proposed RC observation; synthetic model only</text><text x="30" y="165">+</text><text x="35" y="250">-</text><text x="20" y="285">u=1 V</text><text x="175" y="150">DUT R</text><text x="230" y="60">i: source to C</text><text x="275" y="95">a</text><text x="270" y="245">DUT C</text><text x="370" y="260">Probe Rp</text><text x="505" y="260">Cp</text><text x="320" y="355">0 / return</text><text x="20" y="415">V input: u across source. V output: Va-V0.</text><text x="20" y="445">Ideal current observation: no added impedance.</text><text x="20" y="475">Display = Hinst x loaded Va (model cascade).</text><text x="20" y="505">Baseline: remove Rp/Cp. Finite probe changes K/tau.</text><text x="20" y="535">A real current shunt adds Rs; rederive the circuit.</text></g></svg>\n""")
    with mpl.rc_context({'font.family':'DejaVu Sans' ,'font.size':11,
                         'svg.hashsalt':'measurement1-r1','axes.grid':True}):
        def save(fig,name):
            fig.savefig(assets/(name+'.svg'),metadata={'Date':None},facecolor='white')
        def figure(nrows=1,height=4):
            f=Figure(figsize=(6.4,height),layout='constrained')
            return f,f.subplots(nrows,1,squeeze=False)[:,0]
        t=np.linspace(0,.004,241)
        f,ax=figure(2,7.8)
        # Compensated probe network has DC gain .1 and tau denominator Rpar(Cp+Cs).
        for cp,label,style in [(1e-12,'Under: Cp=1 pF','--'),(20e-12/9,'Matched: Cp=2.222 pF','-'),(4e-12,'Over: Cp=4 pF',':')]:
            q=np.linspace(0,100e-6,241);dc=.1;hf=cp/(cp+20e-12);tau=(9e6*1e6/1e7)*(cp+20e-12)
            ax[0].plot(q*1e6,dc+(hf-dc)*np.exp(-q/tau),style,label=label)
        ax[0].set(xlabel='t / us',ylabel='Scope voltage / V',title='Synthetic 1 V step; Rp=9 Mohm, Rs=1 Mohm')
        ax[0].legend(fontsize=9)
        for rn,label,style in [(1000,'Rnode=1 kohm','-'),(100000,'Rnode=100 kohm','--')]:
            w=np.logspace(3,8,241);zp=1/(1/1e7+1j*w*12e-12);h=zp/(rn+zp)
            ax[1].semilogx(w/(2*math.pi),np.abs(h),style,label=label)
        ax[1].set(xlabel='f / Hz',ylabel='Tip loading gain',title='Teaching probe: 10 Mohm || 12 pF')
        ax[1].legend(fontsize=9);save(f,'probe-response')
        f,ax=figure(2,7.8)
        for r,c,label,style in [(1000,1e-6,'1 kohm / 1 uF','-'),(2000,.5e-6,'2 kohm / 0.5 uF','--')]:
            ax[0].plot(t*1e3,[m.step(r,c,float(x)) for x in t],style,label=label)
            ax[1].plot(t*1e3,[m.current(r,c,float(x))*1e3 for x in t],style,label=label)
        ax[0].set(ylabel='vC / V',title='Same tau=1 ms: coincident voltage',xlabel='t / ms')
        ax[1].set(ylabel='Source current / mA',title='Additional observation separates the pairs',xlabel='t / ms')
        for a in ax:a.legend(fontsize=9)
        save(f,'same-tau-observation')
        f,ax=figure(2,7.8)
        ss=np.array([m.sensitivity(1000,1e-6,float(x)) for x in t])
        ax[0].plot(t*1e3,ss[:,0,0],label='dv/d ln R');ax[0].plot(t*1e3,ss[:,0,1],'--',label='dv/d ln C')
        ax[1].plot(t*1e3,ss[:,1,0]*1e3,label='di/d ln R');ax[1].plot(t*1e3,ss[:,1,1]*1e3,'--',label='di/d ln C')
        ax[0].set(ylabel='Voltage sensitivity / V',title='Equal columns give a null direction')
        ax[1].set(ylabel='Current sensitivity / mA',title='At t=tau: R column 0, C column nonzero')
        for a in ax:a.set_xlabel('t / ms');a.legend(fontsize=9)
        save(f,'sensitivity')
        times=[.00025,.0005,.001,.002];ys=[m.step(1000,1e-6,x) for x in times]
        rs=np.linspace(500,2500,81);cs=np.linspace(.4e-6,2e-6,81)
        rr,cc=np.meshgrid(rs,cs)
        loss=np.zeros_like(rr);aug=np.zeros_like(rr)
        for j in range(81):
            for k in range(81):
                loss[j,k]=m.voltage_loss(float(rr[j,k]),float(cc[j,k]),times,ys)
                aug[j,k]=loss[j,k]+((m.current(float(rr[j,k]),float(cc[j,k]),.001)-m.current(1000,1e-6,.001))/1e-6)**2
        f=Figure(figsize=(6.4,12),layout='constrained')
        a=f.add_subplot(311,projection='3d');a.plot_surface(rr/1000,cc*1e6,np.log10(1+loss),cmap='cividis',rstride=3,cstride=3)
        a.set(xlabel='R / kohm',ylabel='C / uF',zlabel='log10(1+SSE)',title='Voltage-only objective: equal-tau valley')
        for n,z,title in [(2,loss,'2D projection: voltage only'),(3,aug,'2D: voltage + current at 1 ms')]:
            a=f.add_subplot(3,1,n);im=a.contourf(rr/1000,cc*1e6,np.log10(1+z),levels=15,cmap='cividis')
            a.plot(rs/1000,.001/rs*1e6,'k--',label='RC = 1 ms')
            a.plot([1,2],[1,.5],'wo',markeredgecolor='k');a.annotate('A',(1,1));a.annotate('B',(2,.5))
            a.set(xlabel='R / kohm',ylabel='C / uF',title=title,ylim=(.4,2));a.legend(fontsize=9)
            f.colorbar(im,ax=a,label='log10(1+SSE)')
        save(f,'identifiability-valley')
        args=(.001,1-1/math.e,1,2e-6,.001,.001)
        budget=m.tau_budget(*args,rho=.6);mc=m.mc_tau(*args,rho=.6,samples=10000,seed=23)
        f,ax=figure(2,7.8)
        # Component labels and numerical table are complemented by chapter03.
        sensitivity=budget['sensitivities']
        contributions=[sensitivity[0]*2e-6,abs(sensitivity[1])*.0006,abs(sensitivity[1])*.0008,abs(sensitivity[2])*.001]
        ax[0].barh(['t: B','V repeat: A','V cal: B','U cal: B'],np.array(contributions)*1e6,color='#46677e')
        ax[0].set(xlabel='Absolute c_i u_i / us',title='Synthetic budget; correlated cal terms not summed as bars')
        rh=np.linspace(-1,1,101)
        ax[1].plot(rh,[m.tau_budget(*args,rho=float(x))['uc_s']*1e6 for x in rh])
        ax[1].plot([.6],[budget['uc_s']*1e6],'ko');ax[1].set(xlabel='Total rho(V,U)',ylabel='u_c(tau) / us',title='Sign of sensitivities changes correlation effect')
        save(f,'uncertainty-budget')
        f,ax=figure(2,7.8)
        base=np.array([m.step(1000,1e-6,float(x)) for x in t])
        cases={'R +1%, C +5%':np.array([m.step(1010,1.05e-6,float(x)) for x in t]),
               'Initial v0=0.4 V':np.array([m.step(1000,1e-6,float(x),v0=.4) for x in t]),
               'RL=10 kohm, Cp=12 pF':np.array([m.loaded_step(1000,1e-6,float(x),10000,cp=12e-12)[0] for x in t]),
               'Recorded clock +1%':np.array([m.step(1000,1e-6,float(x)/1.01) for x in t]),
               'Voltage offset +2 mV':base+.002}
        for (label,v),style in zip(cases.items(),['-','--',':','-.',(0,(5,2))]):ax[0].plot(t*1e3,v-base,linestyle=style,label=label)
        ax[0].set(xlabel='Recorded t / ms',ylabel='Residual v - baseline / V',title='Synthetic competing explanations; no instrument readings');ax[0].legend(fontsize=8)
        ax[1].set_axis_off()
        boxes=[(.5,.98,'Mismatch vs baseline\nCheck wiring / units / source'),(.5,.71,'Change ONE condition\nProbe / IC / temperature / averaging'),(.23,.42,'Signature changes\nModel that influence'),(.77,.42,'No change\nTest another explanation'),(.5,.12,'Predict a hold-out observation\nRecord remaining ambiguity')]
        for x,y,text in boxes:
            ax[1].text(x,y,text,ha='center',va='top',transform=ax[1].transAxes,fontsize=9,bbox={'facecolor':'white','edgecolor':'black'})
        for start,end in [((.5,.87),(.5,.74)),((.45,.60),(.23,.45)),((.55,.60),(.77,.45)),((.23,.30),(.45,.15)),((.77,.30),(.55,.15))]:
            ax[1].annotate('',xy=end,xytext=start,xycoords='axes fraction',arrowprops={'arrowstyle':'->','color':'black'})
        save(f,'fault-tree')
        rows=[]
        for x in [0,.00025,.0005,.001,.002,.004]:
            rows.append([x,m.step(1000,1e-6,x),m.step(2000,.5e-6,x),m.current(1000,1e-6,x),m.current(2000,.5e-6,x)])
        with (data/'rc-synthetic.csv').open('w',newline='') as fh:
            w=csv.writer(fh);w.writerow(['synthetic_t_s','voltage_A_V','voltage_B_V','current_A_A','current_B_A']);w.writerows(rows)
        params={'data_kind':'SYNTHETIC teaching model, not instrument readings','pair_A':{'R_ohm':1000,'C_F':1e-6},'pair_B':{'R_ohm':2000,'C_F':.5e-6},'U_step_V':1,'v0_V':0,'tau_s':.001,'voltage_times_s':times,'sigma_voltage_V':.001,'extra_current_time_s':.001,'sigma_current_A':1e-6,'grid_shape':[81,81],'MC_samples':10000,'MC_seed':23,'budget_inputs':{'t_s':.001,'V_V':1-1/math.e,'U_V':1,'ut_s':2e-6,'uv_V':.001,'uu_V':.001,'rho_V_U':.6}}
        results={'budget':budget,'MC_teaching':mc,'voltage_fisher':m.fisher(1000,1e-6,.001),'augmented_fisher':m.fisher(1000,1e-6,.001,include_current=True),'input_Z_A_ohm':[1000,-1000],'input_Z_B_ohm':[2000,-2000], 'initial_condition_wrong_zero_tau_s':m.tau_from_crossing(.001,m.step(1000,1e-6,.001,v0=.4),1)}
        for name,obj in [('parameters.json',params),('results.json',results)]:
            (data/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        for svg in sorted(assets.glob('*.svg')):
            for width in [360,425]:cairosvg.svg2png(url=str(svg),write_to=str(assets/f'{svg.stem}-{width}.png'),output_width=width)
    return out


def main(argv=None):
    parser=argparse.ArgumentParser(description='Synthetic RC measurement teaching assets')
    parser.add_argument('--output',required=True,help='new/empty directory outside main and published electronics subtree')
    args=parser.parse_args(argv)
    generate(args.output)

if __name__=='__main__':main()
