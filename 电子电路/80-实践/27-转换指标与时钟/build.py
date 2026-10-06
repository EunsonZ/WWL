"""Caller-selected external output; plotting dependencies load only inside generate."""
import argparse
import csv
import json
import math
from pathlib import Path
import models

def generate(output):
    output=Path(output).resolve()
    source=Path(__file__).resolve().parents[3]
    main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL')
    if output==source or source in output.parents or output==main or main in output.parents:
        raise ValueError('output must be outside candidate and main vault')
    if output.exists() and any(output.iterdir()): raise ValueError('output must be empty')
    output.mkdir(parents=True,exist_ok=True)
    from matplotlib.figure import Figure
    from matplotlib import rc_context
    import cairosvg
    assets=output/'assets';assets.mkdir();data=output/'data';data.mkdir()
    results={}
    def save(fig,name):
        fig.savefig(assets/(name+'.svg'),metadata={'Date':None})
        for width in (360,425):
            cairosvg.svg2png(url=str(assets/(name+'.svg')),write_to=str(assets/(name+'-'+str(width)+'.png')),output_width=width)
    def figure(rows=2):
        f=Figure(figsize=(8,6),layout='constrained');return f,f.subplots(rows,1,squeeze=False)[:,0]
    with rc_context({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','svg.hashsalt':'adc2-v1','axes.grid':True}):
        ts=[1.1,2,3.2,4.2,4.2,6.3,7.1];st=models.static_metrics(ts,0,8,3);results['static']=st
        fig,ax=figure(3);xs=[i/100 for i in range(801)];codes=[sum(v>=t for t in ts) for v in xs]
        ax[0].step(xs,codes,where='post',label='actual transitions (V)');ax[0].plot([0,8],[0,8],':',label='ideal straight reference');ax[0].set(xlabel='input V',ylabel='code');ax[0].legend(fontsize=10)
        ax[1].plot(range(1,7),st['internal_dnl_LSB'],'o-',label='internal DNL');ax[1].plot(range(1,8),st['endpoint_transition_inl_LSB'],'s--',label='transition INL');ax[1].set(ylabel='LSB');ax[1].legend(fontsize=10)
        ax[2].plot(xs,[math.floor(v)-v+.5 for v in xs],label='mid-rise error: deterministic sawtooth');ax[2].set(xlabel='input V (1 V LSB)',ylabel='error V');ax[2].legend(fontsize=10)
        fig.suptitle('Static transfer / missing code 4 / error depends on input');save(fig,'01-static')
        n=128;record=[.1+.8*math.sin(2*math.pi*5*j/n)+.02*math.sin(2*math.pi*15*j/n)+.005*math.cos(2*math.pi*17*j/n) for j in range(n)]
        powers=models.one_sided_power(record);results['dynamic']=models.coherent_metrics(record,5)
        fig,ax=figure();ax[0].stem(range(65),[10*math.log10(max(v,1e-20)) for v in powers]);ax[0].set(xlabel='bin = Hz (fs=128 Hz,N=128)',ylabel='power dBV²',ylim=(-100,0));ax[0].set_title('5 Hz signal; 15 Hz harmonic; 17 Hz nonharmonic line')
        leak=models.one_sided_power([.8*math.sin(2*math.pi*5.25*j/n) for j in range(n)])
        ax[1].plot(range(65),[10*math.log10(max(v,1e-20)) for v in leak],label='5.25 bins, rectangular leakage');ax[1].set(xlabel='bin',ylabel='power dBV²',ylim=(-100,0));ax[1].legend(fontsize=10)
        fig.suptitle('Finite record lines, not noise PSD: 7 MHz harmonics fold\n(fs=20 MHz) 7,14,21,28,35 -> 7,6,1,8,5 MHz');save(fig,'02-spectral-test')
        fig,ax=figure();ax[0].axis('off')
        def flow(ax,labels,feedback,extra):
            ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
            points=[.07,.29,.55,.81,.97]
            for i,(x,label) in enumerate(zip(points,labels)):
                ax.text(x,.72,label,ha='center',va='center',fontsize=13,bbox={'boxstyle':'round,pad=.25','facecolor':'white','edgecolor':'black'})
                if i: ax.annotate('',xy=(x-.06,.72),xytext=(points[i-1]+.06,.72),arrowprops={'arrowstyle':'->'})
            ax.plot([.97,.97,.29,.29],[.65,.43,.43,.65],color='black')
            ax.annotate('',xy=(.29,.66),xytext=(.29,.43),arrowprops={'arrowstyle':'->'})
            if ' / N' in feedback: ax.text(.63,.43,'1/N',ha='center',va='center',fontsize=13,bbox={'facecolor':'white','edgecolor':'black'})
            ax.text(.63,.32,feedback,ha='center',fontsize=12)
            ax.text(.5,.06,extra,ha='center',fontsize=12)
        flow(ax[0],['X','Σ (+,−)','H','V + e','Y'],'Y negative feedback; e = Y − V','H=z⁻¹/(1−z⁻¹); white e is an extra assumption')
        f=[i/1000 for i in range(501)];ax[1].plot(f,[1]*len(f),label='|STF| = 1');ax[1].plot(f,[2*math.sin(math.pi*v) for v in f],'--',label='|NTF| = 2 sin(pi f/fs)');ax[1].set(xlabel='f / fs',ylabel='magnitude');ax[1].legend(fontsize=10)
        fig.suptitle('First-order model: signal and error follow different paths');save(fig,'03-noise-shaping')
        sd=models.sigma_delta_dc(.25,128);results['sigma_delta']={'mean':sd['mean'],'x':.25,'count':128,'state_min':min(sd['states']),'state_max':max(sd['states'])}
        fig,ax=figure();osrs=[1,2,4,8,16,32,64,128,256]
        ax[0].loglog(osrs,[models.band_variance(.25,m) for m in osrs],'o-',label='white, ideal band: OSR^-1');ax[0].loglog(osrs,[models.band_variance(.25,m,True) for m in osrs],'s--',label='shaped white, ideal band: asymptotic OSR^-3');ax[0].loglog(osrs,[2*(.25**2/12)/m**2 for m in osrs],'^:',label='shaped white, box mean: M^-2');ax[0].set(xlabel='OSR or box length M',ylabel='variance V²');ax[0].legend(fontsize=9)
        fr=[i/100 for i in range(301)];ax[1].plot(fr,[abs(models.zoh_normalized(v,1)) for v in fr]);ax[1].set(xlabel='f / DAC update rate',ylabel='normalized ZOH gain');fig.suptitle('Filtering matters: ideal band differs from finite averaging');save(fig,'04-osr-reconstruction')
        tt=[j/128 for j in range(128)];dt=[1e-4*math.cos(2*math.pi*3*t) for t in tt];jrec=[.8*math.sin(2*math.pi*20*t)+models.sine_timing_error(.8,20,t,d) for t,d in zip(tt,dt)];jp=models.one_sided_power(jrec)
        fig,ax=figure();dense=[i/2000 for i in range(401)];ax[0].plot(dense,[.8*math.sin(2*math.pi*20*t) for t in dense],label='continuous 20 Hz sine');ax[0].plot([t+d for t,d in zip(tt[:26],dt[:26])],jrec[:26],'o',ms=4,label='perturbed sample times');ax[0].set(xlabel='time s',ylabel='V');ax[0].legend(fontsize=9)
        ax[1].stem(range(65),[10*math.log10(max(v,1e-20)) for v in jp]);ax[1].set(xlabel='frequency Hz',ylabel='power dBV²',xlim=(10,30),ylim=(-100,0));fig.suptitle('Periodic timing error produces 17/23 Hz sidebands\n100 us peak at 3 Hz; not random white jitter');save(fig,'05-timing-spurs')
        results['jitter_100MHz_1ps_dB']=models.jitter_snr(1e8,1e-12);results['phase_noise']=models.phase_jitter([[1e3,-140],[1e6,-140]],1e8)
        coef=models.pll_coefficients(1400,1e6);results['pll']={k:([[p.real,p.imag] for p in v] if k=='poles' else v) for k,v in coef.items()}
        fig,ax=figure();ax[0].axis('off');flow(ax[0],['φr','Σ (+,−)','Kd F','Kv/s','φo'],'φo / N negative feedback; output adds φv','F=kp+ki/s [V/V]; Kd [V/rad], Kv [rad/s/V]')
        ww=[10**(i/50) for i in range(251)];tr=[models.pll_transfer(1400,1e6,w) for w in ww];ax[1].semilogx(ww,[abs(v['T']) for v in tr],label='|T| reference path / N');ax[1].semilogx(ww,[abs(v['S']) for v in tr],'--',label='|S| VCO path');ax[1].set(xlabel='omega rad/s',ylabel='gain');ax[1].legend(fontsize=10);fig.suptitle('One crossing only for this PI model; extra delay needs new analysis');save(fig,'06-pll-phase')
    (data/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
    for filename,header,rows in [('spectrum.csv',['bin_Hz','power_V2'],enumerate(powers)),('bitstream.csv',['n','bit','state','error'],((i,b,v,e) for i,(b,v,e) in enumerate(zip(sd['bits'],sd['states'],sd['errors'])))),('static.csv',['transition_index','threshold_V'],enumerate(ts,1))]:
        with (data/filename).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();generate(args.output)
if __name__=='__main__': main()
