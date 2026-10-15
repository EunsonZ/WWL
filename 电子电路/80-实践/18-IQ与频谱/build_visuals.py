"""Explicit output only; imports remain pure and dependencies initialize in generate."""
import argparse
from pathlib import Path

def generate(output):
    import json
    import math
    import iq
    import cairosvg
    from PIL import Image, ImageOps
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib import rc_context
    from matplotlib.patches import Rectangle, Circle
    output = Path(output)
    main = Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if output.resolve().is_relative_to(main):
        raise ValueError('output must be outside main vault')
    output.mkdir(parents=True, exist_ok=True)
    fs,fc,z,x,recovered=iq.case()
    t=[k/fs for k in range(len(z))]
    data={'fs_Hz':fs,'carrier_Hz':fc,'N':len(z),'cutoff_Hz':4,
          'envelope_V':[[a.real,a.imag] for a in z],'RF_V':x,
          'recovered_V':[[a.real,a.imag] for a in recovered],
          'max_error_V':max(abs(a-b) for a,b in zip(z,recovered))}
    (output/'case.json').write_text(json.dumps(data,indent=2)+'\n')
    with rc_context({'font.family':'DejaVu Sans','font.size':10,'axes.grid':True,
                     'grid.color':'.82','svg.fonttype':'none','svg.hashsalt':'wwl-iq-r1','lines.linewidth':1.5}):
        def save(fig,name):
            FigureCanvasAgg(fig)
            fig.savefig(output/(name+'.svg'),metadata={'Date':None})
            for width in (360,425):
                target = output/(name+f'-{width}.png')
                cairosvg.svg2png(url=str(output/(name+'.svg')),write_to=str(target),output_width=width)
                with Image.open(target) as im:
                    gray=ImageOps.grayscale(im.convert('RGB'))
                    gray.save(target)
                    ImageOps.invert(gray).save(output/(name+f'-{width}-dark.png'))
        fig=Figure(figsize=(6,6),layout='constrained')
        a,b=fig.subplots(2,1)
        a.axhline(0,color='.6',lw=.8);a.axvline(0,color='.6',lw=.8)
        a.plot([0,2],[0,-1],color='black',marker='o',label='z = 2 - j V')
        a.plot([0,2],[0,0],color='.25',ls='--',label='I = 2 V')
        a.plot([2,2],[0,-1],color='.25',ls=':',label='Q = -1 V')
        a.set(xlim=(-.5,2.8),ylim=(-1.5,.6),xlabel='I (V, peak convention)',ylabel='Q (V)',title='Coordinates relative to a carrier reference')
        a.legend(loc='upper left',fontsize=9)
        b.plot(t,x,color='.55',lw=1,label='RF x (real V)')
        b.plot(t,[a.real for a in z],color='black',ls='--',label='I (real V)')
        b.plot(t,[a.imag for a in z],color='black',ls=':',label='Q (real V)')
        b.set(xlim=(0,.25),xlabel='Time (s)',ylabel='Voltage (V)',title='Time-varying envelope; no fixed phasor')
        b.legend(fontsize=9,ncol=3,loc='lower left')
        save(fig,'IQ-objects')
        fig=Figure(figsize=(6,4),layout='constrained');a=fig.subplots();a.set(xlim=(0,10),ylim=(-.7,6));a.axis('off')
        def box(x0,y,w,h,text):
            a.add_patch(Rectangle((x0,y),w,h,facecolor='white',edgecolor='black'))
            a.text(x0+w/2,y+h/2,text,ha='center',va='center',fontsize=10)
        def arrow(x0,y0,x1,y1):
            a.annotate('',(x1,y1),(x0,y0),arrowprops={'arrowstyle':'->','color':'black','lw':1.5})
        a.text(.2,3,'x(t)\nreal V',ha='center');a.plot([.6,1.2,1.2],[3,3,4.5],color='black');a.plot([1.2,1.2],[3,1.5],color='black');a.add_patch(Circle((1.2,3),.07,color='black'))
        for y,lo,result in ((4.5,'2 cos(LO)','I (V)'),(1.5,'-2 sin(LO)','Q (V)')):
            arrow(1.2,y,2,y);box(2,y-.4,1,.8,'multiply');arrow(3,y,4,y);box(4,y-.4,1.3,.8,'LPF');arrow(5.3,y,6.8,y);a.text(6.0,y+.2,result,ha='center');box(1.9,y-1.4,1.4,.7,lo);arrow(2.5,y-.7,2.5,y-.4)
        box(7,2.5,2,1,'combine\nI + jQ');arrow(6.8,4.5,7.8,3.5);arrow(6.8,1.5,7.8,2.5);arrow(9,3,9.8,3)
        a.text(5,5.6,'Two real projections, then one complex object',ha='center',fontsize=12)
        a.text(5,-.5,'LO = 2 pi fLO t + phase; LPF removes images',ha='center',fontsize=10)
        save(fig,'IQ-mix')
        fig=Figure(figsize=(6,7),layout='constrained');axes=fig.subplots(3,1)
        mixed=iq.mix(x,fs,fc)
        for a,values,title in zip(axes,(z,x,mixed),('Envelope Z/N','Real RF X/N','Complex mixer M/N before LPF')):
            spec=iq.fft(values);freq=[(k if k<64 else k-128) for k in range(128)]
            keep=[k for k,v in enumerate(spec) if abs(v)/128>1e-10]
            a.vlines([freq[k] for k in keep],0,[abs(spec[k])/128 for k in keep],color='black')
            a.plot([freq[k] for k in keep],[abs(spec[k])/128 for k in keep],'o',color='black',ms=4)
            for k in keep:a.annotate(str(freq[k]),(freq[k],abs(spec[k])/128),xytext=(0,4),textcoords='offset points',ha='center',fontsize=8)
            a.set(xlim=(-40,24),ylim=(0,2.8),ylabel='Coefficient |DFT/N| (V)',title=title)
        axes[-1].axvline(-4,color='.4',ls='--');axes[-1].axvline(4,color='.4',ls='--');axes[-1].set_xlabel('Signed bin frequency (Hz); spacing = 1 Hz')
        save(fig,'IQ-spectra')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    generate(args.output)
