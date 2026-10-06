"""Editable native circuits + direct Figure plots; imports never create caches."""
import argparse
import json
import os
from pathlib import Path
from html import escape
import noise_models as model

def line(a,b,c,d):return f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}"/>'
def text(x,y,s,n=14):return f'<text x="{x}" y="{y}" font-size="{n}">{escape(s)}</text>'
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'
def gnd(x,y):return line(x,y-15,x,y)+line(x-10,y,x+10,y)+line(x-6,y+5,x+6,y+5)
def resistor(a,b,y,label):
 mid=(a+b)/2;return line(a,y,mid-18,y)+f'<rect x="{mid-18}" y="{y-8}" width="36" height="16" fill="white"/>'+line(mid+18,y,b,y)+text(mid-22,y-15,label,12)
def vres(x,a,b,label):
 mid=(a+b)/2;return line(x,a,x,mid-18)+f'<rect x="{x-8}" y="{mid-18}" width="16" height="36" fill="white"/>'+line(x,mid+18,x,b)+text(x+12,mid+4,label,12)
def capacitor(x,y,label):return line(x,y-30,x,y-4)+line(x-14,y-4,x+14,y-4)+line(x-14,y+4,x+14,y+4)+line(x,y+4,x,y+30)+text(x+20,y+4,label,12)
def source(x,y,label,vertical=True,plus_first=True,current=False):
 s=f'<circle cx="{x}" cy="{y}" r="14" fill="white"/>'
 if current:
  tip=y-8 if current=='up' else y+8;base=y-3 if current=='up' else y+3
  s+=line(x,y-8,x,y+8)+f'<path d="M{x-4} {base} L{x} {tip} L{x+4} {base}"/>'
 elif vertical:s+=text(x-4,y-2,'+' if plus_first else '-',12)+text(x-3,y+10,'-' if plus_first else '+',12)
 else:s+=text(x-11,y+4,'-' if plus_first else '+',12)+text(x+3,y+4,'+' if plus_first else '-',12)
 return s+text(x+18,y+3,label,12)
def wrap(s,h=500):return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{h}" viewBox="0 0 425 {h}"><rect width="425" height="{h}" fill="white"/><g fill="none" stroke="#111" stroke-width="1.8">{s}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'
def thermal_diagram():
 s=text(12,25,'Same thermal port, two representations',17)
 s+=source(45,100,'er')+line(45,86,45,70)+resistor(45,260,70,'R 2k')+line(260,70,260,90)+dot(260,70)+text(272,72,'v',14)+line(45,114,45,165)+line(45,165,260,165)+vres(260,90,165,'RL 3k')+gnd(45,180)
 s+=text(12,218,'er PSD=4kTR; noiseless RL teaching case',13)
 s+=source(75,320,'ir',current='up')+line(75,306,75,270)+line(75,270,260,270)+line(75,334,75,390)+line(75,390,260,390)+vres(175,270,390,'R 2k')+vres(260,270,390,'RL 3k')+gnd(75,405)+dot(260,270)+text(273,275,'v',14)
 s+=text(12,450,'ir PSD=4kT/R; v=ir (R || RL)',13)+text(12,475,'Real warm RL needs its OWN thermal source',13)
 return wrap(s)
def opamp_diagram():
 s=text(12,25,'Noise sources have different injection ports',16)
 s+='<path d="M225 240 L225 340 L305 290 Z"/>'+text(231,266,'-',18)+text(231,328,'+',18)
 s+=line(265,265,265,215)+text(274,218,'+5 V',13)+line(265,315,265,365)+text(274,372,'-5 V',13)
 s+=line(305,290,370,290)+dot(335,290)+text(341,280,'o')+vres(370,290,420,'RL 10k')+gnd(370,435)
 s+=line(165,260,225,260)+dot(165,260)+text(169,281,'m')+line(165,260,165,90)+resistor(165,250,90,'Rf 90k')+line(250,90,261,90)+source(275,90,'er,f',False,False)+line(289,90,335,90)+line(335,90,335,290)
 s+=line(165,260,185,260)+line(185,260,185,204)+source(185,190,'im',current='up')+line(185,176,185,135)+dot(185,135)+text(193,140,'0')
 s+=source(30,310,'u')+line(30,296,30,260)+line(30,260,56,260)+source(70,260,'',False)+line(84,260,95,260)+resistor(95,165,260,'Ri 10k')+text(50,240,'er,i',12)+line(30,324,30,385)+gnd(30,400)
 s+=line(165,320,186,320)+source(200,320,'',False)+line(214,320,225,320)+text(189,352,'en',13)+dot(165,320)+text(157,310,'p')
 s+=line(165,320,80,320)+vres(80,320,395,'Rp 2k')+source(80,420,'er,p')+line(80,395,80,406)+line(80,434,80,470)+gnd(80,485)
 s+=line(165,320,165,406)+source(165,420,'ip',current=True)+line(165,434,165,470)+gnd(165,485)
 s+=text(12,525,'Current arrows: node to 0; vo=A(p-m+en)',13)+text(12,551,'Every voltage is relative to 0; ideal supplies',13)+text(12,577,'Ri/Rf/Rp noise sources shown once each',13)+text(12,603,'Input conduction i=0; output r=0; linear model',13)
 return wrap(s,630)
def rc_diagram():
 s=text(12,25,'Thermal RC and switched sample state',17)
 s+=source(40,105,'er')+line(40,91,40,70)+resistor(40,270,70,'Rs 2k')+line(270,70,270,100)+capacitor(270,130,'C 10nF')+line(270,160,270,180)+gnd(270,195)+line(40,119,40,180)+gnd(40,195)+dot(270,70)+text(282,76,'v')
 s+=text(12,238,'er PSD=4kTRs; only Rs dissipates at T',13)
 s+=source(40,350,'u')+line(40,336,40,310)+resistor(40,170,310,'Ron')+line(170,310,200,310)+dot(200,310)+line(200,310,225,296)+dot(235,310)+line(235,310,300,310)+line(300,310,300,350)+capacitor(300,380,'Cs')+gnd(300,425)+line(40,364,40,410)+gnd(40,425)
 s+=text(190,278,'switch open',12)+text(310,309,'sample v',12)+text(12,475,'Closed: heat approaches kT/C; open: hold state',13)+text(12,500,'Finite acquisition retains initial-state memory',13)
 return wrap(s,525)

def generate(output):
 """Generate explicitly; restore environment and all Matplotlib rc state on exit."""
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 keys=('MPLCONFIGDIR','XDG_CACHE_HOME')
 previous={key:os.environ.get(key) for key in keys}
 try:
  os.environ['MPLCONFIGDIR']=str(output/'.mplconfig')
  os.environ['XDG_CACHE_HOME']=str(output/'.cache')
  import matplotlib
  with matplotlib.rc_context({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none','svg.hashsalt':'WWL-M13'}):
   return _generate(output)
 finally:
  for key,value in previous.items():
   if value is None:os.environ.pop(key,None)
   else:os.environ[key]=value

def _generate(output):
 import numpy as np
 import matplotlib
 from matplotlib.figure import Figure
 from matplotlib.backends.backend_agg import FigureCanvasAgg
 import cairosvg
 from PIL import Image,ImageOps
 data={'schema':'M13 CPU theoretical plots, not hardware','parameters':{'T_K':300,'R_ohm':2000,'C_F':1e-8,'fs_Hz':4096,'FFT_samples':256,'seed':20261006},'models':model.results()}
 def fig(height=4.8):
  f=Figure(figsize=(4.25,height),dpi=100);FigureCanvasAgg(f);return f
 def save(f,name):f.savefig(output/(name+'.svg'),metadata={'Date':None},facecolor='white')
 for name,body in [('thermal-topologies',thermal_diagram()),('opamp-noise-ports',opamp_diagram()),('rc-thermal-sampling',rc_diagram())]:(output/(name+'.svg')).write_text(body)
 f=fig(7.0);a=f.add_subplot(311);b=f.add_subplot(312);c=f.add_subplot(313);freq=np.linspace(-1500,1500,601);s2=np.where(abs(freq)<=1000,32.,0.);a.plot(freq,s2,'k-');a.set(xlabel='f (Hz), two-sided',ylabel='PSD (nV^2/Hz)',title='Same variance: 0.064 uV^2');a.grid(ls=':');freq1=np.linspace(0,1500,301);s1=np.where(freq1<=1000,64.,0.);b.plot(freq1,s1,'k-');b.set(xlabel='f (Hz), one-sided',ylabel='PSD (nV^2/Hz)');b.grid(ls=':');c.plot(freq1,np.sqrt(s1),'k-');c.set(xlabel='f (Hz), one-sided',ylabel='ASD (nV/sqrtHz)');c.grid(ls=':');f.subplots_adjust(left=.2,right=.96,top=.93,bottom=.08,hspace=.65);save(f,'side-density');data['side']={'f2_Hz':freq.tolist(),'PSD2_nV2_Hz':s2.tolist(),'f1_Hz':freq1.tolist(),'PSD1_nV2_Hz':s1.tolist(),'ASD1_nV_sqrtHz':np.sqrt(s1).tolist()}
 f=fig(5.3);a=f.add_subplot(211);b=f.add_subplot(212);fs=np.geomspace(.01,1e4,500);s=64e-18+1.28e-15/fs;a.loglog(fs,s/1e-18,'k-',label='PSD');a.set(ylabel='PSD (nV^2/Hz)',title='White + 1/f: finite model band');a.axvspan(.1,1000,color='#ddd');b.loglog(fs,np.sqrt(s)/1e-9,'k-');b.set(xlabel='f (Hz)',ylabel='ASD (nV/sqrtHz)');b.axvspan(.1,1000,color='#ddd');a.grid(ls=':');b.grid(ls=':');f.subplots_adjust(left=.21,right=.96,top=.9,bottom=.12,hspace=.45);save(f,'flicker-band');data['flicker']={'f_Hz':fs.tolist(),'PSD_V2_Hz':s.tolist(),'integration_band_Hz':[.1,1000]}
 f=fig(5.8);a=f.add_subplot(211);b=f.add_subplot(212);fs=np.geomspace(1,1e7,400);en=8e-9;ii=.3e-12
 for name,rho,style in [('en',en,'-'),('ip',ii,'--'),('im',ii,':')]:
  H=np.array([model.ports(float(x))[name] for x in fs]);asd=abs(H)*rho;a.loglog(fs,asd/1e-9,style,color='#111',label=name);b.loglog(fs,asd/abs(np.array([model.ports(float(x))['signal'] for x in fs]))/1e-9,style,color='#111',label=name);data[name+'_output_ASD']=asd.tolist()
 a.set(ylabel='Output ASD (nV/sqrtHz)',title='Own paths; en vs ip vs im');b.set(xlabel='f (Hz)',ylabel='u-port ASD (nV/sqrtHz)');a.legend(fontsize=9);b.legend(fontsize=9);a.grid(ls=':');b.grid(ls=':');f.subplots_adjust(left=.23,right=.97,top=.91,bottom=.11,hspace=.5);save(f,'port-contributions');data['port_frequency_Hz']=fs.tolist()
 f=fig(5.8);a=f.add_subplot(211);b=f.add_subplot(212);rc=model.rc_band(2000,1e-8);x=np.linspace(0,6,601);power=1/(1+x*x);a.plot(x,power,'k-',label='|H|^2');a.fill_between(x,power,color='#ddd');a.plot([0,mathpi:=np.pi/2,mathpi],[1,1,0],'k--',label='Equal-area rectangle');a.set(xlabel='f/fc',ylabel='Normalized power',title='ENBW=pi fc/2, fc=7957.747 Hz');a.legend(fontsize=8);a.grid(ls=':');z=np.geomspace(.001,100,400);var=np.array([model.rc_band(2000,1e-8,high=float(t*rc['fc_Hz']))['variance_V2'] for t in z]);b.semilogx(z,var/rc['variance_V2'],'k-',label='Variance fraction');b.semilogx(z,np.sqrt(var/rc['variance_V2']),'k--',label='RMS fraction');b.axhline(1,color='#555',ls=':');b.set(xlabel='Integration upper limit / fc',ylabel='Fraction of full band');b.grid(ls=':');b.legend(fontsize=8);f.subplots_adjust(left=.19,right=.96,top=.9,bottom=.11,hspace=.5);save(f,'rc-area');data['RC_area']={'f_over_fc':x.tolist(),'H2':power.tolist(),'upper_over_fc':z.tolist(),'variance_V2':var.tolist()}
 f=fig(4.6);a=f.add_subplot(111);theta=np.linspace(0,2*np.pi,401)
 for rho,style in [(-.8,':'),(0,'--'),(.8,'-')]:
  S=np.array([[4,6*rho],[6*rho,9]]);v,Q=np.linalg.eigh(S);xy=Q@np.diag(np.sqrt(v))@np.stack([np.cos(theta),np.sin(theta)]);a.plot(xy[0],xy[1],style,color='#111',label='rho='+str(rho));data['ellipse_'+str(rho)]={'x_uV':xy[0].tolist(),'y_uV':xy[1].tolist(),'covariance_uV2':S.tolist()}
 a.set(xlabel='x (uV)',ylabel='y (uV)',title='Unit covariance contours; not 95% CI',aspect='equal');a.legend(fontsize=8);a.grid(ls=':');f.subplots_adjust(left=.2,right=.95,top=.88,bottom=.14);save(f,'covariance-ellipse')
 f=fig(7.6);a=f.add_subplot(311);b=f.add_subplot(312);c=f.add_subplot(313);n=256;fsamp=4096;nn=np.arange(n);rng=np.random.default_rng(20261006)
 for kind,style in [('rect','-'),('hann','--')]:
  w=model.window(n,kind);W=abs(np.fft.rfft(w,4096))/w.sum();xx=np.fft.rfftfreq(4096)*n;a.plot(xx,np.maximum(20*np.log10(np.maximum(W,1e-12)),-100),style,color='#111',label=kind)
  tone=np.cos(2*np.pi*16.35*nn/n)*1e-6;ps=model.periodogram(tone,fsamp,kind);b.plot(ps['frequency_Hz'],10*np.log10(np.maximum(ps['PSD_V2_per_Hz']/1e-12,1e-14)),style,color='#111',label=kind);data['FFT_'+kind]={'frequency_Hz':ps['frequency_Hz'].tolist(),'PSD_V2_Hz':ps['PSD_V2_per_Hz'].tolist(),'CG':ps['coherent_gain'],'ENBW_Hz':ps['window_ENBW_Hz']}
 white=rng.standard_normal(4096)*1e-6;single=model.periodogram(white[:256],fsamp,'hann');avg=model.average_periodogram(white,fsamp,256);c.plot(single['frequency_Hz'],single['PSD_V2_per_Hz']/1e-12,'k:',label='one segment');c.plot(avg['frequency_Hz'],avg['PSD_V2_per_Hz']/1e-12,'k-',label='16 segments');c.axhline(2/fsamp,color='#555',ls='--',label='iid theory (interior)')
 a.set(xlim=(0,12),ylim=(-100,5),xlabel='Offset (original bins)',ylabel='Window response (dB)',title='True window FFT: zero padding interpolates');b.set(xlim=(0,1000),ylim=(-100,-10),xlabel='f (Hz), noncoherent 261.6 Hz',ylabel='PSD (dB re 1 uV^2/Hz)');c.set(xlabel='f (Hz)',ylabel='PSD (uV^2/Hz)')
 for ax in (a,b,c):ax.legend(fontsize=8);ax.grid(ls=':')
 f.subplots_adjust(left=.23,right=.97,top=.93,bottom=.08,hspace=.7);save(f,'fft-window-leakage');data['average']={'frequency_Hz':avg['frequency_Hz'].tolist(),'PSD_V2_Hz':avg['PSD_V2_per_Hz'].tolist(),'one_PSD_V2_Hz':single['PSD_V2_per_Hz'].tolist(),'segments':16,'known_iid_variance_V2':1e-12}
 (output/'figure-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 for p in sorted(output.glob('*.svg')):
  for width in (360,425):
   png=output/f'{p.stem}-{width}.png';cairosvg.svg2png(url=str(p),write_to=str(png),output_width=width);im=Image.open(png).convert('RGB');ImageOps.grayscale(im).save(output/f'{p.stem}-{width}-gray.png');dark=Image.new('RGB',(im.width+24,im.height+24),'#171717');dark.paste(im,(12,12));dark.save(output/f'{p.stem}-{width}-dark.png')
 return data

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv);generate(args.output);return 0
if __name__=='__main__':raise SystemExit(main())
