"""Deterministically generate editable SVG, 425 px PNG and data; explicit --output."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from detection_lab import periodogram, simulation, threshold

plt.rcParams.update({'font.size':10,'svg.hashsalt':'wwl-u6','font.family':'DejaVu Sans'})

def save(fig,out,name):
    fig.savefig(out/(name+'.svg'),metadata={'Date':None},bbox_inches=None)
    fig.savefig(out/(name+'-425.png'),dpi=100,metadata={'Software':'WWL U6'},bbox_inches=None)
    plt.close(fig)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True,type=Path); a=p.parse_args(); out=a.output; out.mkdir(parents=True,exist_ok=True)
    n=64; fs=64; x=2+np.sin(2*np.pi*8*np.arange(n)/fs)
    f,raw=periodogram(x,fs); _,centered=periodogram(x,fs,True)
    fig,ax=plt.subplots(figsize=(4.25,3.3)); ax.stem(f,raw,linefmt='k-',markerfmt='ko',basefmt=' '); ax.plot(f,centered,'x--',label='demeaned',color='0.4'); ax.set(xlabel='Frequency (Hz)',ylabel='Density (unit^2/Hz)',title='DC area 4; tone area 0.5'); ax.legend(); fig.tight_layout(); save(fig,out,'psd-dc')
    fig,ax=plt.subplots(figsize=(4.25,3.1)); ax.axis('off')
    boxes=[(.02,.72,'x[n]'),(.36,.72,'h[r]=s[L-1-r]'),(.68,.72,'y[k+L-1]'),(.36,.18,'z[k] > threshold')]
    for bx,by,label in boxes: ax.text(bx,by,label,ha='left',va='center',bbox={'boxstyle':'round','facecolor':'white','edgecolor':'black'},fontsize=9)
    for start,end in [((.17,.72),(.35,.72)),((.64,.72),(.68,.72)),((.85,.61),(.61,.27))]: ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->'})
    ax.text(.02,.46,'k: window start\nValid starts: 0 ... N-L\nOutput sample delayed by L-1',fontsize=10)
    ax.text(.04,.01,'Known k: one test. Unknown k: maximum over K tests.',fontsize=9); save(fig,out,'matched-timing')
    result=simulation(); (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    k=np.arange(1,51); alpha=.01
    fig,ax=plt.subplots(figsize=(4.25,3.3)); ax.plot(k,1-(1-alpha)**k,'k-',label='global: independent positions'); ax.axhline(alpha,color='0.4',linestyle='--',label='per-position = 0.01'); ax.plot(k,k*alpha,':',color='0.3',label='union bound K * 0.01'); ax.set(xlabel='Number of searches K',ylabel='False alarm probability',ylim=(0,.52)); ax.legend(fontsize=8); fig.tight_layout(); save(fig,out,'multiple-fpr')
    (out/'plot-data.json').write_text(json.dumps({'fs':fs,'x':x.tolist(),'frequency_hz':f.tolist(),'raw_psd':raw.tolist(),'demeaned_psd':centered.tolist(),'K':k.tolist(),'global_independent':(1-(1-alpha)**k).tolist()},indent=2)+'\n')

if __name__=='__main__': main()
