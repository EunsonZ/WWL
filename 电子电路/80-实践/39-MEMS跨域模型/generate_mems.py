"""Deterministic editable teaching SVGs/data, explicit empty output directory."""
import argparse
import csv
import json
from pathlib import Path
import mems_model as model

MAIN=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
PUBLISH=Path(__file__).resolve().parents[2]

def generate(output):
    out=Path(output).expanduser().resolve()
    if out==MAIN or MAIN in out.parents or out==PUBLISH or PUBLISH in out.parents:
        raise ValueError('output cannot be main vault or candidate publication tree')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('output must be absent or empty')
    import numpy as np
    import matplotlib as mpl
    from matplotlib.figure import Figure
    import cairosvg
    out.mkdir(parents=True,exist_ok=True)
    def save(name,fig):
        fig.savefig(out/(name+'.svg'),metadata={'Date':None},facecolor='white')
    def svg(name,body,height=520):
        text='<svg xmlns="http://www.w3.org/2000/svg" width="620" height="'+str(height)+'" viewBox="0 0 620 '+str(height)+'"><rect width="620" height="'+str(height)+'" fill="white"/><style>text{font:18px sans-serif;fill:#111}path,line,rect{stroke:#111;stroke-width:2} .wire{fill:none} .box{fill:#f3f3f3}.dash{stroke-dasharray:7 5}</style>'+body+'</svg>\n'
        (out/(name+'.svg')).write_text(text)
    with mpl.rc_context({'font.size':11,'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'frontier04-r1','axes.grid':True}):
        svg('section', '''<text x="20" y="30">Geometry: z normal to plates (not to scale)</text>
<rect class="box" x="130" y="80" width="360" height="18"/><text x="135" y="65">fixed top electrode: +Vc</text>
<rect class="box" x="130" y="198" width="360" height="70"/><text x="145" y="230">proof mass node p; x=0</text><text x="145" y="255">200 x 200 x 10 um</text>
<rect class="box" x="130" y="368" width="360" height="18"/><text x="135" y="416">fixed bottom electrode: -Vc</text>
<path class="wire" d="M105 98 V198 M98 105 L105 98 L112 105 M98 191 L105 198 L112 191"/><text x="15" y="157">g - x</text>
<path class="wire" d="M105 268 V368 M98 275 L105 268 L112 275 M98 361 L105 368 L112 361"/><text x="15" y="328">g + x</text>
<path class="wire" d="M520 270 V145 L512 158 M520 145 L528 158"/><text x="530" y="185">+z, +x</text>
<text x="20" y="455">g=2 um at x=0; motion x is relative to base.</text><text x="20" y="483">Suspension has effective k,b; geometry does not set k.</text>''')
        svg('readout', '''<text x="20" y="30">Quasi-static charge divider: Qp=0</text>
<path class="wire" d="M90 90 H225 M240 90 H370 M385 90 H525"/><line x1="225" y1="65" x2="225" y2="115"/><line x1="240" y1="65" x2="240" y2="115"/><line x1="370" y1="65" x2="370" y2="115"/><line x1="385" y1="65" x2="385" y2="115"/>
<circle cx="305" cy="90" r="5" fill="#111"/><path class="wire" d="M305 90 V165 H470"/><text x="210" y="55">C+</text><text x="360" y="55">C-</text><text x="40" y="95">+Vc</text><text x="530" y="95">-Vc</text><text x="310" y="145">p: vp</text><text x="390" y="190">high-Z buffer</text>
<text x="20" y="235">vp/Vc = (C+ - C-)/(C+ + C-)</text><text x="20" y="265">Qp initial charge / input leakage breaks this relation.</text>
<text x="20" y="315">Full bridge: s=+Vexc, reference 0</text>
<path class="wire" d="M100 350 H510 M160 350 V365 M450 350 V365 M160 410 V450 M450 410 V450 M160 495 V510 H450 V495"/>
<rect class="box" x="145" y="365" width="30" height="45"/><rect class="box" x="435" y="365" width="30" height="45"/><rect class="box" x="145" y="450" width="30" height="45"/><rect class="box" x="435" y="450" width="30" height="45"/>
<circle cx="160" cy="430" r="4"/><circle cx="450" cy="430" r="4"/><text x="205" y="395">R(1+d)</text><text x="470" y="395">R(1-d)</text><text x="205" y="480">R(1-d)</text><text x="470" y="480">R(1+d)</text><text x="110" y="435">a (-)</text><text x="460" y="435">b (+)</text><text x="270" y="542">0 V return</text><text x="20" y="577">vo=vb-va=Vexc*d; d=GF*strain, |d|&lt;1</text>''',610)
        p=model.mechanics(); x0=model.displacement(model.G0).real
        fig=Figure(figsize=(5.8,4.8)); ax=fig.add_subplot(111,projection='3d')
        u=np.array([-100,100]); X,Y=np.meshgrid(u,u)
        for z,col in [(-7,'#aaa'),(-5,'#ddd'),(5,'#ddd'),(7,'#aaa')]:
            ax.plot_surface(X,Y,np.full_like(X,z),color=col,alpha=.5,edgecolor='black')
        for xx in [-100,100]:
            for yy in [-100,100]:ax.plot([xx,xx],[yy,yy],[-5,5],color='black')
        ax.set(xlabel='X (um)',ylabel='Y (um)',zlabel='Z (um)',title='Physical plates: thickness 10 um, gap 2 um')
        ax.set_box_aspect((1,1,.8)); fig.text(.05,.02,'Z aspect enlarged; surface coordinates are physical. Synthetic geometry.',fontsize=9)
        save('geometry-3d',fig)
        fig=Figure(figsize=(5.8,5.)); ax=fig.subplots(); r=np.linspace(-.45,.45,201)
        ax.plot(r,2*r/(1-r*r),label='exact DeltaC/C0',color='black');ax.plot(r,2*r,'--',label='linear 2x/g',color='#555');ax.plot(r,r,':',label='ideal vp/Vc = x/g',color='#333')
        ax.set(xlabel='x / gap',ylabel='dimensionless output',title='Same geometry; raw difference is nonlinear'); ax.legend(); fig.tight_layout();save('capacitance',fig)
        fig=Figure(figsize=(5.8,6.)); axs=fig.subplots(2,1); f=np.geomspace(1,10000,400)
        for z,style in [(.7,'-'),(.1,'--')]:
            vals=[abs(model.displacement(1.,ff,zeta=z))*1e6 for ff in f];axs[0].semilogx(f,vals,style,color='black',label='zeta='+str(z))
        axs[0].set(xlabel='frequency (Hz)',ylabel='um / (m/s2)',title='Mechanical sensitivity, same m and f0');axs[0].legend()
        th=model.thermal(); bands=np.linspace(0,200,100)
        axs[1].plot(bands,[model.thermal(bandwidth=v)['accel_rms']/model.G0*1e3 for v in bands],color='black')
        axs[1].set(xlabel='rectangular input-equivalent B (Hz)',ylabel='noise RMS (mg)',title='Thermal force only, T=300 K, zeta=0.7');fig.tight_layout();save('response-noise',fig)
        fig=Figure(figsize=(5.8,5.));ax=fig.subplots(); a=np.linspace(-8,8,241);K=9*p['k'];Fmax=2*p['m']*model.G0
        for style,label,func in [('-','force/m feedback estimate',lambda v:model.feedback_static(v*model.G0,K,Fmax)['estimate']/model.G0),('--','true acceleration',lambda v:v)]:ax.plot(a,[func(v) for v in a],style,color='black',label=label)
        ax.set(xlabel='true a (g)',ylabel='estimate (g)',title='P feedback: K=9k, force limit=2mg0');ax.legend();fig.tight_layout();save('feedback-range',fig)
        svg('integration', '''<text x="20" y="32">Integration evidence flow (not measured results)</text>
<rect class="box" x="35" y="65" width="550" height="65"/><text x="50" y="93">Package / PCB / fixture / environment</text><text x="50" y="119">stress -&gt; bias,k ; pressure -&gt; b ; fixture modes</text>
<path class="wire" d="M310 130 V165 L303 155 M310 165 L317 155"/>
<rect class="box" x="35" y="170" width="550" height="60"/><text x="50" y="196">mass dynamics -&gt; C or R -&gt; port readout</text><text x="50" y="221">mechanical clipping occurs before digital filter</text>
<path class="wire" d="M310 230 V265 L303 255 M310 265 L317 255"/>
<rect class="box" x="35" y="270" width="550" height="60"/><text x="50" y="296">calibration: axes / T / excitation / timestamps</text><text x="50" y="320">residual + repeatability + drift + validity range</text>
<path class="wire" d="M310 330 V365 L303 355 M310 365 L317 355"/>
<rect class="box" x="35" y="370" width="550" height="65"/><text x="50" y="397">publish raw records + units + model + uncertainty</text><text x="50" y="423">CPU synthetic / instrument / human: distinct</text><text x="20" y="478">Nonlinear q*a^2: mean shift q*A_peak^2/2 survives LPF.</text>''')
    for pth in sorted(out.glob('*.svg')):
        for width in (360,425):cairosvg.svg2png(url=str(pth),write_to=str(out/(pth.stem+'-'+str(width)+'.png')),output_width=width)
    params={'kind':'synthetic teaching, not ADXL355','m_kg':p['m'],'f0_Hz':1000.,'zeta':.7,'gap_m':2e-6,'area_m2':4e-8,'temperature_K':300.,'g0_m_s2':model.G0}
    results={'mechanics':p,'x_1g_m':x0,'capacitors_1g':model.capacitors(x0),'strain_at_positive_1um':model.beam_strain(1e-6),'bridge_GF100_1um':model.bridge(100*model.beam_strain(1e-6)), 'thermal_B100':th,'feedback_1g':model.feedback_static(model.G0,9*p['k'],Fmax),'feedback_8g':model.feedback_static(8*model.G0,9*p['k'],Fmax),'vibration_bias_A2g_q001':model.vibration_bias(2*model.G0,.001)}
    (out/'parameters.json').write_text(json.dumps(params,indent=2,sort_keys=True)+'\n');(out/'results.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    with (out/'capacitance.csv').open('w',newline='') as fp:
        writer=csv.writer(fp);writer.writerow(['x_over_gap','deltaC_over_C0','linear','ratio'])
        for r in (-.4,-.1,0.,.1,.4):writer.writerow([r,2*r/(1-r*r),2*r,r])
    return sorted(p.name for p in out.iterdir())

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv);generate(args.output)

if __name__=='__main__':main()
