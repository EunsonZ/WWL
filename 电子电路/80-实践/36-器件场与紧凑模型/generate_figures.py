"""Original editable vectors. Lazy plotting; explicit fresh output; scoped config."""
import argparse,json,math,os
from pathlib import Path
from html import escape
import field_models as m

def text(x,y,s,size=14):return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'
def line(x,y,X,Y,dash=False):return f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>'
def box(x,y,w,h,s):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white"/>'+text(x+8,y+h/2+5,s)
def wrap(body,h,title,desc):return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{h}" viewBox="0 0 425 {h}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="425" height="{h}" fill="white"/><g stroke="#111" stroke-width="2" fill="none">{body}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'
def mesh():
 b=text(15,26,'F01: node unknowns, shared edge flux',17)+text(15,58,'1D material; drawing not fabrication scale')
 b+=line(35,135,390,135)+text(355,120,'+x / m',12)
 for i,x in enumerate([45,125,225,325]):
  b+=f'<circle cx="{x}" cy="135" r="5" fill="white"/>'+text(x-12,167,['0','i-1','i','N'][i])+text(x-22,198,['contact','phi,n,p','phi,n,p','contact'][i],12)
 for x in [85,175,275]:b+=line(x,105,x,235,True)
 b+=box(175,220,100,100,'')+text(183,244,'volume w_i',13)+text(183,273,'rho_i / C m^-3',12)+text(183,300,'R-G / m^-3 s^-1',11)
 b+=text(15,365,'D_right - D_left = rho_i w_i')+text(15,397,'Jn_right - Jn_left = q(R-G) w_i')+text(15,429,'Jp has the opposite source sign')
 b+=text(15,477,'Contacts: phi and carrier contract')+text(15,509,'No-flux boundary is a different condition')+text(15,541,'Shared edge -> internal flux cancels')+text(15,573,'Nodes: V, m^-3; edges: C/m^2, A/m^2')
 return wrap(b,600,'Poisson and carrier conservation mesh','F01/V41 device mesh contribution only. One dimensional schematic not to manufacture scale. Internal node quantities, contact boundary contracts and shared oriented edge fluxes. Dashed lines are control-volume faces, not wires.')
def levels():
 b=text(15,28,'One device: field -> port -> circuit',17)+text(15,59,'F01 contribution; package model is F02')
 rows=[('Geometry / material / contacts','x[m], epsilon[F/m], doping[m^-3]'),('Grid solve: phi, n, p','Poisson + continuity; residual budget'),('Port extraction: I and Q','I=area x J [A]; Q [C]'),('Compact law and fitted parameters','I(V,T); Q(V,T); domain card'),('Circuit nodes / states','KCL + port laws; bias and initial state')]
 for j,(a,c) in enumerate(rows):
  y=100+j*96;b+=box(25,y,375,42,a)+text(30,y+66,c,12)
  if j<4:b+=line(210,y+72,210,y+92)
 b+=text(15,603,'Holdout I/Q/derivatives check the mapping')+text(15,634,'No real PDK, process or professional run')
 return wrap(b,660,'Device field and compact port model hierarchy','Original diagram. Field geometry and mesh reduce to I and Q and finite compact laws then circuit unknowns. F01 supplies device field portion of V41; no packaging RLC/thermal/mechanical completion claim, no real PDK.')
def generate(output):
 out=m.new_output(output);out.mkdir(parents=True);old={k:os.environ.get(k) for k in ['MPLCONFIGDIR','XDG_CACHE_HOME']}
 os.environ['MPLCONFIGDIR']=str(out/'.mpl');os.environ['XDG_CACHE_HOME']=str(out/'.xdg')
 try:
  import matplotlib as mpl
  from matplotlib.figure import Figure
  import cairosvg
  m.generate(out/'model');data=json.loads((out/'model/results.json').read_text())
  with mpl.rc_context({'font.family':'DejaVu Sans','font.size':11.5,'svg.fonttype':'none','svg.hashsalt':'frontier01'}):
   images={'mesh-flux':mesh(),'model-levels':levels()}
   f=Figure(figsize=(4.25,7),dpi=100);a=f.subplots(2,1);f.subplots_adjust(left=.24,right=.95,top=.94,bottom=.10,hspace=.65)
   r=data['PB_mesh'][2];s=r['s'];vt=m.KB*300/m.Q;a[0].plot(s,[.5*vt*math.sin(math.pi*z)*1e3 for z in s],color='black',label='exact');a[0].plot(s,[v*1e3 for v in r['phi_V']],color='black',ls='--',label='N=32')
   a[0].set(xlabel='s = x/L',ylabel='phi / mV',title='Equilibrium PB; synthetic doping');a[0].legend(fontsize=10)
   a[1].loglog([r['cells'] for r in data['PB_mesh']],[r['max_error_V']*1e6 for r in data['PB_mesh']],'ko-');a[1].set(xlabel='cells N',ylabel='max error / microV',title='Same continuous problem, refined grid');a[1].set_xticks([8,16,32,64]);a[1].set_xticklabels(['8','16','32','64']);a[1].minorticks_off()
   p=out/'pb-convergence.svg';f.savefig(p,metadata={'Date':None},facecolor='white');images['pb-convergence']=p.read_text()
   f=Figure(figsize=(4.25,7),dpi=100);a=f.subplots(2,1);f.subplots_adjust(left=.24,right=.95,top=.94,bottom=.10,hspace=.65)
   fractions=[.99,1,1.01];b=[1e-12/(8*11.7*m.EPS0*z)*1e3 for z in fractions];a[0].plot(fractions,b,'ko-');a[0].set(xlabel='epsilon / nominal',ylabel='curvature b / mV',title='Fixed rho=1 C/m^3; L=1micro m')
   z=data['compact_bar'];a[1].plot(z['V_V'],[i*1e6 for i in z['I_A']],'ko',label='synthetic I');a[1].plot([0,.04],[0,z['G_S']*.04*1e6],color='black',ls='--',label='same mu*n');a[1].set(xlabel='V / V',ylabel='I / microA',title='mu/2 and 2n: indistinguishable ports');a[1].legend(fontsize=10)
   p=out/'sensitivity-fit.svg';f.savefig(p,metadata={'Date':None},facecolor='white');images['sensitivity-fit']=p.read_text()
   for name,s in images.items():
    if name in ['pb-convergence','sensitivity-fit']:
     at=s.index('>',s.index('<svg '))+1;s=s[:at]+f'<title>{name}</title><desc>Finite CPU teaching data; not professional TCAD or measured fabrication data. SI units and fixed conditions labelled.</desc>'+s[at:]
    (out/(name+'.svg')).write_text(s)
    for width in [360,425]:cairosvg.svg2png(bytestring=s.encode(),write_to=str(out/f'{name}-{width}.png'),output_width=width)
   (out/'figure-data.json').write_text(json.dumps({'PB_mesh_errors_V':[r['max_error_V'] for r in data['PB_mesh']],'cells':[r['cells'] for r in data['PB_mesh']],'epsilon_ratio':fractions,'curvature_mV':b,'synthetic_bar':z,'scope':'V41 F01 grid contribution only; no fabrication scale/PDK/TCAD run'},indent=2,allow_nan=False)+'\n')
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv);generate(args.output)
if __name__=='__main__':main()
