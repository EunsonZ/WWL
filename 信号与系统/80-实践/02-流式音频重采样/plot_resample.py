"""Editable deterministic plot source. --output explicitly owns all outputs."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from resample_lab import write_data, response, FS

def plots(output):
    output=Path(output)
    d=write_data(output)
    plt.rcParams.update({'font.size':11,'svg.hashsalt':'wwl-u3-v1','font.family':'DejaVu Sans'})
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(output/(name+'.svg'),metadata={'Date':None,'Creator':'WWL U3 deterministic plot source'})
        # Actual width exactly 425 pixels; source is 5 inches wide, dpi=85.
        fig.savefig(output/(name+'-425.png'),dpi=85,metadata={'Software':'WWL U3'})
        plt.close(fig)
    f,a=response(d['h'])
    fig,ax=plt.subplots(2,1,figsize=(5,5.2))
    ax[0].plot(f/1000,a,'k-',label='193-tap Blackman')
    ax[0].axvline(6,color='k',ls='--');ax[0].axvline(8,color='k',ls=':')
    ax[0].set(xlim=(0,12),ylim=(0,1.12),ylabel='|H| (unitless)',title='Pass <= 6 kHz; stop >= 8 kHz')
    ax[0].text(6.1,.55,'transition',fontsize=10)
    ax[1].plot(f/1000,20*np.log10(np.maximum(a,1e-7)),'k-')
    ax[1].axhline(-60,color='k',ls='--',label='stop limit -60 dB')
    ax[1].axvline(8,color='k',ls=':')
    ax[1].set(xlim=(0,24),ylim=(-130,5),xlabel='input frequency (kHz)',ylabel='20 log10 |H| (dB)')
    ax[1].legend(fontsize=9);save(fig,'filter-spec')
    fig,ax=plt.subplots(figsize=(5,3.5))
    n=np.arange(7)
    ax.plot(n[:4],np.zeros(4),'ko',markersize=5,label='record x[0..3]')
    ax.plot(n[4:],np.zeros(3),'ko',markersize=5,fillstyle='none',label='flush: 3 zeros')
    for i,value in zip([0,3,6],[1,20,16]):
        ax.plot(i,.6,'ks',markersize=6)
        ax.annotate(f'y[{i//3}]={value}',(i,.6),xytext=(i,.88),ha='center',fontsize=10)
    ax.axvline(1.5,color='k',ls='--')
    ax.axvline(3.5,color='k',ls=':')
    ax.axvspan(3.5,6.4,facecolor='.92')
    ax.text(.5,-.32,'block 1',ha='center',fontsize=9)
    ax.text(2.5,-.32,'block 2',ha='center',fontsize=9)
    ax.text(5,-.32,'EOF flush',ha='center',fontsize=9)
    ax.text(3,-.68,'h=[1,2,3,4]; full convolution ends at n=6',
            ha='center',fontsize=9)
    ax.set(xlim=(-.6,6.6),ylim=(-1.05,1.15),xticks=n,
           yticks=[0,.6],yticklabels=['input n','keep n=3m'],
           xlabel='global input sample index n',title='Blocks [0,1] / [2,3]; then 3 tail zeros')
    save(fig,'state-timeline')
    fig,ax=plt.subplots(2,1,figsize=(5,5.2),sharex=True)
    for axis,key,title in zip(ax,['naive','good'],['Drop points: 10 kHz aliases to 6 kHz','FIR then retain: suppress before folding']):
        axis.plot(d['f']/1000,20*np.log10(np.maximum(d[key],1e-7)),'k-')
        axis.set(ylim=(-130,0),ylabel='peak amplitude (dBV)',title=title)
        axis.axvline(1,color='k',ls='--');axis.axvline(6,color='k',ls=':')
    ax[0].text(5.1,-17,'0.3 V',fontsize=10)
    ax[1].text(2,-24,'1 kHz: ~0.6 V',fontsize=10)
    ax[1].set(xlim=(0,8),xlabel='output frequency (kHz), fs=16 kHz')
    save(fig,'alias-spectrum')
    return d['results']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(plots(p.parse_args().output))
