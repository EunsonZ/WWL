"""Editable original SVG + actual 360/425 pixel views; all imports lazy."""
from pathlib import Path
import photon_models as m

def svg(body,height=440):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{height}" viewBox="0 0 720 {height}"><rect width="720" height="{height}" fill="white"/><style>text{{font-family:DejaVu Sans,sans-serif;font-size:22px;fill:#111}}path,line,polyline{{fill:none;stroke:#152c46;stroke-width:3}} .opt{{stroke:#ae451c}} .note{{font-size:19px}}</style><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#152c46"/></marker></defs>'+body+'</svg>'

def diagrams():
 return {
 'photon-charge':svg('''<text x="25" y="35">850 nm: energy to collected charge</text><path class="opt" d="M45 95H250" marker-end="url(#a)"/><text x="30" y="80">Pdet [W]</text><rect x="270" y="70" width="180" height="55" fill="#f0c7af"/><rect x="270" y="125" width="180" height="85" fill="#dae7f4"/><rect x="270" y="210" width="180" height="60" fill="#e4dfac"/><text x="285" y="106">P / anode</text><text x="282" y="166">depletion</text><text x="286" y="247">N / cathode</text><path d="M360 125V75M360 210V260"/><text x="463" y="112">holes up</text><text x="463" y="245">e- down</text><path d="M450 95H595V330H190V240H270"/><circle cx="595" cy="210" r="34" fill="white" stroke="#152c46" stroke-width="3"/><text x="568" y="218">load</text><path d="M405 330H330" marker-end="url(#a)"/><text x="245" y="364">external conventional I</text><text x="25" y="409" class="note">η [electron/photon]; R = ηqλ/(hc) [A/W]</text>'''),
 'waveguide':svg('''<text x="25" y="36">2D slab: geometry schematic</text><rect x="80" y="130" width="560" height="150" fill="#dbe9f0" stroke="#152c46" stroke-width="3"/><text x="90" y="108">cladding n=1.45</text><text x="85" y="315">cladding n=1.45</text><text x="395" y="208">core n=1.50</text><path class="opt" d="M85 170L285 130L635 200"/><path d="M285 130V205" stroke-dasharray="7 6"/><text x="205" y="196">θ &gt; θc</text><path d="M100 365H630" marker-end="url(#a)"/><text x="150" y="396">z [m], P(z)=P0 exp(-αp z)</text><path d="M675 275V60" marker-end="url(#a)"/><text x="647" y="53">x</text><text x="25" y="429" class="note">ray not to angle scale / no solved mode; outside decay</text>''',460),
 'tia-circuit':svg('''<text x="20" y="35">Reverse-biased PD / finite-A receiver</text><path d="M70 115V185"/><text x="22" y="98">+3 V</text><path d="M50 215H90L70 185Z M50 185H90 M70 215V270H275"/><text x="25" y="249">PD</text><path class="opt" d="M15 140L46 178M14 164L42 193" marker-end="url(#a)"/><circle cx="185" cy="270" r="5" fill="#152c46"/><text x="180" y="304">X</text><path d="M130 270V315M112 315H148M112 325H148M130 325V385M115 385H145"/><text x="24" y="350">CT=10 pF</text><path d="M275 220L275 330L390 275Z M275 305H240V385M225 385H255 M390 275H655"/><text x="285" y="268">−</text><text x="286" y="314">+</text><text x="625" y="309">vo</text><path d="M325 243.913043478V175 M325 306.086956522V370"/><text x="286" y="155">+5 V</text><text x="285" y="398">−5 V</text><path d="M185 270V65H360 M455 65H565V275 M360 55H455V75H360Z"/><text x="361" y="97">RF=100k</text><path d="M185 120H385 M385 108V132 M401 108V132 M401 120H565"/><text x="402" y="151">CF=1pF</text><circle cx="565" cy="275" r="5" fill="#152c46"/><path d="M100 270H160" marker-end="url(#a)"/><text x="95" y="245">i into X</text><text x="25" y="433" class="note">+3 V is AC reference; CT includes PD+wire+input</text>''',455),
 'mzi-arms':svg('''<text x="25" y="35">Balanced MZI: phase becomes power</text><path class="opt" d="M30 210H120L220 110H490L580 210L650 160 M120 210L220 310H490L580 210L650 265"/><text x="25" y="186">Pin [W]</text><text x="214" y="91">arm 1: φ1</text><text x="215" y="344">arm 2: φ2</text><rect x="275" y="138" width="170" height="27" fill="#d4d4d4" stroke="#152c46"/><path d="M360 165V215H280"/><text x="188" y="244">Vdrive [V]</text><text x="505" y="100">P+ [W]</text><text x="502" y="309">P− [W]</text><text x="30" y="390">Δφ = π/2 + π V/Vπ; Vπ=4 V</text><text x="30" y="427" class="note">lossless splitter sum P+ + P− = Pin τ</text>''',455)
 }

def generate(output):
 import os,tempfile
 from contextlib import ExitStack
 p=m.fresh_output(output)
 # Before any third-party import, protect process environment. Restore even if rendering raises.
 keys=['MPLCONFIGDIR','XDG_CACHE_HOME'];old={k:os.environ.get(k) for k in keys}
 with tempfile.TemporaryDirectory(prefix='photon-render-',dir=p.parent if p.parent.exists() else None) as cache:
  try:
   os.environ['MPLCONFIGDIR']=cache;os.environ['XDG_CACHE_HOME']=cache
   import matplotlib as mpl
   from matplotlib.figure import Figure
   import numpy as np
   import cairosvg
   with mpl.rc_context({'font.family':'DejaVu Sans','font.size':18,'axes.labelsize':18,'axes.titlesize':18,'xtick.labelsize':15,'ytick.labelsize':15,'legend.fontsize':15,'svg.fonttype':'none','svg.hashsalt':'wwl-photon-v1'}):
    p.mkdir(parents=True);figs=diagrams()
    f=np.logspace(2,7,301);z=np.array([abs(m.tia(x)[0]) for x in f]);o=m.optical();psd=np.array([m.output_psd(x,o['photo_A']) for x in f])
    fig=Figure(figsize=(7.2,6),layout='constrained');ax=fig.subplots(2,1);ax[0].semilogx(f,z/1e3,color='#152c46');ax[0].set(ylabel='|Zt| [kΩ]',title='Same receiver / finite A(s)');ax[0].grid(True);ax[1].loglog(f,np.sqrt(psd)*1e9,color='#ae451c');ax[1].set(xlabel='frequency [Hz]',ylabel='output ASD [nV/√Hz]');ax[1].grid(True)
    fig.savefig(p/'receiver-response.svg',metadata={'Date':None})
    fig=Figure(figsize=(7.2,4.4),layout='constrained');ax=fig.subplots();v=np.linspace(-4,4,321);plus=np.array([m.mzi(1e-4,x)[0]*1e6 for x in v]);ax.plot(v,plus,color='#152c46',label='P+');ax.plot(v,10-plus,color='#ae451c',linestyle='--',label='P−');ax.set(xlabel='drive voltage [V]',ylabel='received power [µW]',title='Vπ=4 V / available power=10 µW');ax.grid(True);ax.legend();fig.savefig(p/'modulation-curve.svg',metadata={'Date':None})
    for name,body in figs.items():(p/(name+'.svg')).write_text(body)
    for fpath in sorted(p.glob('*.svg')):
     for w in [360,425]:cairosvg.svg2png(url=str(fpath),write_to=str(p/(fpath.stem+f'-{w}.png')),output_width=w)
  finally:
   for k,v in old.items():
    if v is None:os.environ.pop(k,None)
    else:os.environ[k]=v
 return p

def main(argv=None):
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args(argv)
 try:generate(args.output)
 except ValueError as e:parser.error(str(e))
if __name__=='__main__':main()
