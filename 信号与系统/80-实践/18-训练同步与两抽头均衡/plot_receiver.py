#!/usr/bin/env python3
"""Plot only saved results/CSVs; no second receiver implementation."""
import argparse
import csv
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/wwl181-mpl')
os.environ.setdefault('MPLBACKEND','Agg')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def z(a):
    a=np.asarray(a);return a[:,0]+1j*a[:,1]


def save(fig,path,title,desc):
    if path.exists(): raise ValueError('refuse to overwrite '+str(path))
    fig.savefig(path,metadata={'Date':None},bbox_inches='tight')
    text=path.read_text()
    idx=text.index('>',text.index('<svg'))+1
    from xml.sax.saxutils import escape
    text=text[:idx]+'\n<title>'+escape(title)+'</title>\n<desc>'+escape(desc)+'</desc>'+text[idx:]
    path.write_text(text)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args()
    data=json.loads((a.results/'results.json').read_text()); demo=data['demo']
    matplotlib.rcParams.update({'font.size':10,'svg.hashsalt':'WWL181receiver'})
    with (a.results/'constellations.csv').open() as f: rows=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,3,figsize=(12.2,3.5),layout='constrained')
    for ax,name in zip(axes,['4PAM','QPSK','16QAM']):
        rr=[r for r in rows if r['modulation']==name]
        for r in rr:
            x,y=float(r['I_over_sqrtEs']),float(r['Q_over_sqrtEs'])
            ax.plot(x,y,'o',color='#176f99');ax.annotate(r['label'],(x,y),xytext=(0,7),textcoords='offset points',ha='center',fontsize=8)
        ax.axhline(0,color='gray',lw=.6);ax.axvline(0,color='gray',lw=.6)
        ax.set(xlim=(-1.6,1.6),ylim=(-1.4,1.4),aspect='equal',xlabel='I / sqrt(Es)',ylabel='Q / sqrt(Es)',title=name+'; mean energy = Es')
        ax.grid(alpha=.2)
    save(fig,a.results/'constellations.svg','Constellations at the same average symbol energy','Gray labels for 4PAM, QPSK and 16QAM. Axes are dimensionless I and Q divided by sqrt(Es); no RF voltage or random BER is plotted.')
    fig,axes=plt.subplots(1,3,figsize=(14.4,4.0),layout='constrained')
    with (a.results/'acquisition.csv').open() as f: rr=list(csv.DictReader(f))
    ds=sorted({int(r['delay_samples']) for r in rr});fs=sorted({float(r['CFO_Hz']) for r in rr})
    scores=np.array([float(r['residual_over_Eb']) for r in rr]).reshape(len(ds),len(fs))
    im=axes[0].imshow(scores.T-scores.min(),origin='lower',aspect='auto',extent=[-.5,7.5,fs[0]-10,fs[-1]+10],cmap='viridis')
    axes[0].plot(demo['delay_hat'],demo['cfo_hat_Hz'],'x',color='red',ms=10,mew=2)
    axes[0].set(xlabel='Delay d (sample)',ylabel='CFO (Hz)',title='Same 75-sample pilot window')
    fig.colorbar(im,ax=axes[0],label='(residual - minimum) / Eb')
    styles=[('raw','x','#b44c2a','d=0, f=0; no correction'),('matched','o','#176f99','acquired d/f; before equalizer')]
    for key,m,color,label in styles:
        zz=z(demo[key])[:7];axes[1].plot(zz.real,zz.imag,m,ms=7,color=color,label=label)
    for key,m,color in [('ZF','s','#9e5fa7'),('LMMSE','^','#267745')]:
        zz=z(demo[key]);axes[2].plot(zz.real,zz.imag,m,ms=7,color=color,label=key)
    for ax in axes[1:]:
        ax.plot([-1,1],[0,0],'+',ms=15,color='black',label='BPSK targets')
        ax.axhline(0,color='gray',lw=.6);ax.axvline(0,color='gray',lw=.6)
        ax.set(xlabel='I / sqrt(Eb)',ylabel='Q / sqrt(Eb)',aspect='equal')
        ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper left')
        ax.set_xlim(-2,2);ax.set_ylim(-1.4,1.6)
    axes[1].set_title('Same 7 data symbols; 1101001')
    axes[2].set_title('After estimated two-tap equalization')
    save(fig,a.results/'receiver.svg','Pilot acquisition and the same seven symbols before and after correction','Left: all 72 candidate residuals, minimum at delay 3 samples and CFO 40 Hz for this noisy realization. Middle: first seven observations with no correction and with acquired timing/frequency; eighth tail is kept in the solver. Right: ZF and complex-linear LMMSE for the same frame. Complex coordinates are divided by sqrt(Eb), not ADC volts.')
    print('Wrote constellations.svg and receiver.svg from saved JSON/CSV.')

if __name__=='__main__': main()
