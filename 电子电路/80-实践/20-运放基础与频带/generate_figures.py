"""Native node diagrams and direct-Figure plots, explicit output only."""
import argparse
import json
import os
from pathlib import Path
from html import escape
import opamp_examples as model


def line(x1,y1,x2,y2):return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
def label(x,y,s,size=15):return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'
def resistor(x1,x2,y,name):
    mid=(x1+x2)/2
    return line(x1,y,mid-24,y)+f'<rect x="{mid-24}" y="{y-9}" width="48" height="18" fill="white"/>'+line(mid+24,y,x2,y)+label(mid-34,y-15,name,14)
def capacitor(x1,x2,y,name):
    mid=(x1+x2)/2
    return line(x1,y,mid-4,y)+line(mid-4,y-12,mid-4,y+12)+line(mid+4,y-12,mid+4,y+12)+line(mid+4,y,x2,y)+label(mid-30,y-19,name,14)
def ground(x,y):return line(x,y-15,x,y)+line(x-12,y,x+12,y)+line(x-8,y+5,x+8,y+5)+line(x-4,y+10,x+4,y+10)
def source(x,y,name):
    return f'<circle cx="{x}" cy="{y}" r="16"/>'+label(x-5,y-2,'+',14)+label(x-4,y+11,'-',14)+line(x,y+16,x,y+38)+ground(x,y+53)+label(x-29,y+80,name,14)
def opamp():
    s='<path d="M225 130 L225 230 L305 180 Z"/>'+label(231,155,'-',18)+label(230,214,'+',18)
    s+=line(265,155,265,118)+label(274,123,'+5 V',14)+line(265,205,265,250)+label(274,251,'-5 V',14)
    s+=line(305,180,370,180)+dot(335,180)+label(349,166,'o',16)
    s+=line(370,180,370,262)+'<rect x="360" y="262" width="20" height="36" fill="white"/>'+line(370,298,370,326)+ground(370,341)+label(310,290,'RL 10k',13)
    return s

def wrap(body,height=460):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}"><rect width="425" height="{height}" fill="white"/><g stroke="#111" stroke-width="2" fill="none">{body}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'


def resistor_network(mode):
    titles={'inverting':'Inverting: p=0, signal -9','noninverting':'Noninverting: signal +10','summing':'Summer: two input currents','difference':'Difference: two resistor ratios'}
    b=label(15,26,titles[mode],17)+opamp()+line(165,150,225,150)+dot(165,150)+label(171,169,'m',15)
    b+=line(165,150,165,70)+resistor(165,335,70,'Rf 90k')+line(335,70,335,180)
    if mode=='noninverting':
        b+=line(165,150,165,264)+'<rect x="155" y="264" width="20" height="38" fill="white"/>'+line(165,302,165,326)+ground(165,341)+label(95,289,'Rg 10k',14)
        b+=line(200,210,225,210)+source(200,250,'ui')+line(200,210,200,234)+label(187,201,'p',15)
    elif mode=='difference':
        b+=resistor(55,165,150,'R1 10k')+line(55,150,55,205)+source(55,221,'u1')
        b+=resistor(55,165,210,'R3 10k')+line(55,210,55,186) # separate u2 source routed below, not on u1 node
        # Replace overlapping source route with separate branch u2 at bottom left.
        b=b.replace(resistor(55,165,210,'R3 10k')+line(55,210,55,186),resistor(95,165,210,'R3 10k')+line(95,210,95,300)+source(95,316,'u2'))
        b+=line(165,210,225,210)+dot(165,210)+label(171,202,'p',15)
        b+=line(165,210,165,264)+'<rect x="155" y="264" width="20" height="38" fill="white"/>'+line(165,302,165,326)+ground(165,341)+label(180,289,'R4 90k',13)
    else:
        b+=resistor(55,165,150,'Ri 10k' if mode=='inverting' else 'R1 10k')+line(55,150,55,190)+source(55,206,'ui' if mode=='inverting' else 'u1')
        if mode=='summing':b+=line(165,150,165,195)+resistor(95,165,195,'R2 20k')+line(95,195,95,284)+source(95,300,'u2')
        b+=line(225,210,205,210)+line(205,210,205,326)+ground(205,341)+label(145,246,'p=0',14)
    b+=label(15,427,'Voltages relative to 0; ideal supplies',14)+label(15,451,'Input i=0; output r=0; no AC coupling',13)
    return wrap(b,478)


def reactive_panel(mode):
    integ=mode=='integrator';title='Leaky integrator' if integ else 'Limited differentiator'
    b=label(15,26,title,17)+opamp()+line(165,150,225,150)+dot(165,150)+label(169,169,'m',14)
    b+=line(165,150,165,55)+resistor(165,335,55,'Rf 1M' if integ else 'Rf 10k')+line(335,55,335,180)
    b+=line(165,95,165,150)+capacitor(165,335,95,'Cf 100n' if integ else 'Cf 1n')+line(335,95,335,180)+dot(165,95)+dot(335,95)
    if integ:b+=resistor(55,165,150,'Ri 10k')+line(55,150,55,190)+source(55,206,'u')
    else:b+=capacitor(30,100,150,'Ci 100n')+resistor(100,165,150,'Ri 1k')+line(30,150,30,190)+source(30,206,'u')
    b+=line(225,210,205,210)+line(205,210,205,326)+ground(205,341)+label(145,246,'p=0',14)
    b+=label(15,390,'Cf is across m-o, not output-ground',14)
    b+=label(15,416,'Ideal +/-5V rails; RL directly to 0',14)
    if not integ:b+=label(15,442,'Ci blocks DC; specified zero-state H',14)
    else:b+=label(15,442,'Cf voltage state: vm - vo',14)
    return b


def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    os.environ['MPLCONFIGDIR']=str(output/'.mplconfig');os.environ['XDG_CACHE_HOME']=str(output/'.cache')
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib
    import cairosvg
    from PIL import Image,ImageOps
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'WWL-M11'})
    for mode in ('inverting','noninverting','summing','difference'):(output/(mode+'.svg')).write_text(resistor_network(mode))
    (output/'reactive-circuits.svg').write_text(wrap(reactive_panel('integrator')+'<g transform="translate(0 475)">'+reactive_panel('differentiator')+'</g>',950))
    fs=np.geomspace(.1,1e7,401);s=2j*np.pi*fs
    plot_data={'f_Hz':fs.tolist(),'frequency_samples':401,'state_samples':301,'model':model.results()}
    fig=Figure(figsize=(4.25,6.2),dpi=100);FigureCanvasAgg(fig)
    for k,mode in enumerate(('integrator','differentiator'),1):
        ax=fig.add_subplot(2,1,k)
        if mode=='integrator':
            ideal=-1/(s*1e4*1e-7);limited=-(1e6/1e4)/(1+s*1e6*1e-7);finite=np.array([model.integrate_transfer(float(f)) for f in fs])
        else:
            ideal=-s*1e4*1e-7;limited=ideal/((1+s*1e3*1e-7)*(1+s*1e4*1e-9));finite=np.array([model.differentiate_transfer(float(f)) for f in fs])
        for zs,style,name in ((ideal,':','pure ideal'),(limited,'--','RC limited'),(finite,'-','finite A')):ax.semilogx(fs,20*np.log10(abs(zs)),color='#111',ls=style,label=name,lw=1.7)
        ax.set(xlabel='Frequency f (Hz)',ylabel='Voltage gain (dB)',title=mode.capitalize(),ylim=(-80,70),xlim=(.1,1e7));ax.legend(fontsize=9,loc='upper right');ax.grid(ls=':',lw=.5)
        plot_data[mode+'_finite_mag']=abs(finite).tolist()
    fig.subplots_adjust(left=.19,right=.96,top=.91,bottom=.1,hspace=.62);fig.savefig(output/'reactive-frequency.svg',metadata={'Date':None})
    fig=Figure(figsize=(4.25,3.8),dpi=100);FigureCanvasAgg(fig);ax=fig.add_subplot(111)
    ts=np.linspace(0,5,301);ideal=np.array([model.integrator_state(float(t)) for t in ts]);leak=np.array([model.integrator_state(float(t),rf=1e6) for t in ts])
    valid=ts<=4.2;ax.plot(ts[valid],ideal[valid],'k-',label='ideal C feedback');ax.plot(ts[~valid],ideal[~valid],'k:',label='outside linear range');ax.plot(ts,leak,'k--',label='with 1M leak')
    ax.axhline(-4,color='#555',ls=':');ax.text(.25,-3.2,'u=1 mV, initial=0.2 V\nRi=10k, Cf=100n',fontsize=10)
    ax.set(xlabel='Time (s)',ylabel='Output vo (V)',title='State and DC accumulation',xlim=(0,5),ylim=(-5,.7));ax.legend(fontsize=9,loc='lower left');fig.subplots_adjust(left=.19,right=.96,bottom=.18,top=.87);fig.savefig(output/'integrator-state.svg',metadata={'Date':None})
    plot_data['t_s']=ts.tolist();plot_data['ideal_state_V']=ideal.tolist();plot_data['leak_state_V']=leak.tolist()
    (output/'figure-data.json').write_text(json.dumps(plot_data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    for svg in sorted(output.glob('*.svg')):
        for width in (360,425):
            png=output/f'{svg.stem}-{width}.png';cairosvg.svg2png(url=str(svg),write_to=str(png),output_width=width)
            im=Image.open(png).convert('RGB');ImageOps.grayscale(im).save(output/f'{svg.stem}-{width}-gray.png')
            dark=Image.new('RGB',(im.width+24,im.height+24),'#171717');dark.paste(im,(12,12));dark.save(output/f'{svg.stem}-{width}-dark.png')


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args(argv)
    generate(args.output);return 0

if __name__=='__main__':raise SystemExit(main())
