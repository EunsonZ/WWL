"""Deterministic editable SVGs and CairoSVG previews; explicit --output only."""
from pathlib import Path
import argparse
import csv
import numpy as np
from frontend_budget import Budget, fail_case, evaluate, noise_spectra, acquisition_error, settling_error, half_lsb


def generate(output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import cairosvg
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.hashsalt':'wwl-u4-v1','svg.fonttype':'none'})

    def save(fig, output, name):
        svg=output/(name+'.svg');fig.savefig(svg,metadata={'Date':None},facecolor='white')
        plt.close(fig)
        cairosvg.svg2png(url=str(svg),write_to=str(output/(name+'-425.png')),output_width=425)


    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cfg=Budget();freq=np.geomspace(cfg.low_hz,cfg.high_hz,700)
    spectra=np.array([noise_spectra(cfg,float(f)) for f in freq]);psd=spectra.sum(axis=1)
    cumulative=np.concatenate(([0.],np.cumsum((psd[:-1]+psd[1:])*.5*np.diff(freq))))
    fig,axes=plt.subplots(2,1,figsize=(6,5));fig.subplots_adjust(left=.17,right=.95,bottom=.12,top=.91,hspace=.45)
    axes[0].loglog(freq,np.sqrt(psd)/200*1e9,label='Both stages, filtered')
    axes[0].set(ylabel='RTI ASD (nV / sqrt(Hz))',title='Noise area accumulates variance')
    axes[1].semilogx(freq,np.sqrt(cumulative)/200*1e6,label='Stages only')
    axes[1].axhline(evaluate(cfg)['input_noise_rms']*1e6,color='tab:orange',ls='--',label='Including driver / ADC / quant.')
    axes[1].set(xlabel='Frequency / integration upper limit (Hz)',ylabel='RTI RMS (uV)')
    for ax in axes:ax.grid(True,alpha=.3);ax.legend(fontsize=8)
    save(fig,output,'noise-integral')
    with (output/'noise-integral.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['frequency_Hz','stage1_output_PSD_V2_per_Hz','stage2_output_PSD_V2_per_Hz','cumulative_RTI_RMS_V'])
        writer.writerows(zip(freq,spectra[:,0],spectra[:,1],np.sqrt(cumulative)/200))
    fig,ax=plt.subplots(figsize=(7,4.5));fig.subplots_adjust(left=.03,right=.97,bottom=.04,top=.92)
    ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off');ax.set_title('Signal, reference and noise enter different ports',fontsize=11)
    blocks=[(1,4.4,'Sensor\n1 mV peak'),(4,4.4,'Stage 1\nG = N = 20'),(7.5,4.4,'Stage 2\nG = N = 10'),(1,1.7,'Analog LP\n4 poles, 5 kHz'),(4,1.7,'Unity driver\nR = 200 ohm'),(7.5,1.7,'ADC\n16 bit, 100 kS/s')]
    for x,y,label in blocks:ax.text(x,y,label,ha='center',va='center',fontsize=11,bbox={'boxstyle':'round,pad=.45','fc':'#edf5ff','ec':'#456'})
    for a,b in [((2.1,4.4),(2.8,4.4)),((5.3,4.4),(6.2,4.4)),((2.3,1.7),(2.8,1.7)),((5.3,1.7),(6.2,1.7))]:ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':1.5})
    ax.plot([8.8,9.5,9.5,.1,.1],[4.4,4.4,3.3,3.3,1.7],color='#456');ax.annotate('',xy=(.1,1.7),xytext=(.1,2.5),arrowprops={'arrowstyle':'->'})
    ax.text(4.7,3.65,'Reference: 1.65 V to BOTH feedback bases',ha='center',fontsize=9,color='#803')
    for x in [4,7.5]:ax.annotate('',xy=(x,4.05),xytext=(x,3.8),arrowprops={'arrowstyle':'->','color':'#803'})
    for x,y,label in [(4,5.55,'e1, i1, resistors'),(7.5,5.55,'e2, i2, resistors'),(4,.45,'30 uVrms lumped'),(7.5,.45,'20 uVrms + quant.')]:
        ax.text(x,y,label,ha='center',fontsize=9,color='#065');ax.annotate('',xy=(x,4.9 if y>5 else 1.1),xytext=(x,y-.2 if y>5 else y+.2),arrowprops={'arrowstyle':'->','color':'#065'})
    ax.text(1,.45,'Teaching block model',ha='center',fontsize=9)
    save(fig,output,'frontend-chain')
    good,bad=Budget(),fail_case();times=np.linspace(0,7e-6,600)
    fig,axes=plt.subplots(2,1,figsize=(6,5.8));fig.subplots_adjust(left=.17,right=.95,bottom=.11,top=.92,hspace=.48)
    for c,label,color in [(bad,'Bad: 10 kohm, slow driver','tab:red'),(good,'Good: 200 ohm, fast driver','tab:blue')]:
        err=np.array([acquisition_error(c.fsr,c.driver_r,c.sample_c,float(t),c.driver_fc,c.driver_sr)/half_lsb(c.fsr,c.bits) for t in times])
        axes[0].semilogy(times*1e6,np.maximum(err,1e-5),label=label,color=color)
        axes[0].scatter([c.acq*1e6],[max(acquisition_error(c.fsr,c.driver_r,c.sample_c,c.acq,c.driver_fc,c.driver_sr)/half_lsb(c.fsr,c.bits),1e-5)],color=color,zorder=3)
    axes[0].axhline(1,color='black',ls='--',label='Half LSB');axes[0].set(xlabel='Acquisition time (us)',ylabel='Residual / half LSB',ylim=(1e-5,1e6),title='Specified dead-time + two-pole model');axes[0].legend(fontsize=8);axes[0].grid(True,alpha=.3)
    ax=axes[1];ax.axvspan(.5,2.8,color='#e2eedf',label='Assumed op-amp window')
    for y,c,label,color in [(1,bad,'Bad','tab:red'),(0,good,'Good','tab:blue')]:
        lo,hi=evaluate(c)['output_envelope'];ax.plot([lo,hi],[y,y],lw=6,color=color);ax.plot([lo,hi],[y,y],'|',ms=14,color=color)
        ax.text((lo+hi)/2,y+.15,f'{lo:.3f} to {hi:.3f} V',ha='center',fontsize=9)
    ax.set(xlim=(0,3.3),ylim=(-.45,1.55),yticks=[0,1],yticklabels=['Good','Bad'],xlabel='Worst-case DC + nominal signal envelope (V)');ax.legend(fontsize=8,loc='lower right');ax.grid(True,axis='x',alpha=.3)
    save(fig,output,'settling-swing')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    generate(parser.parse_args(argv).output)


if __name__=='__main__':
    main()
