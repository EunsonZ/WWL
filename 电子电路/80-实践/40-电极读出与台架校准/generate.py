"""Generate only in a required, new, external --output directory. No import work."""
from pathlib import Path
import json,math
import models as m

def generate(output):
 output=Path(output).expanduser().resolve()
 candidate=Path(__file__).resolve().parents[3]
 main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
 if output.exists() or output==main or main in output.parents or output==candidate or candidate in output.parents:
  raise ValueError('output must be a new directory outside both vault and candidate')
 import matplotlib
 from matplotlib.figure import Figure
 from matplotlib.backends.backend_agg import FigureCanvasAgg
 import cairosvg
 output.mkdir(parents=True);assets=output/'assets';assets.mkdir()
 def svg(name,body,height=650):
  head=f'<svg xmlns="http://www.w3.org/2000/svg" width="450" height="{height}" viewBox="0 0 450 {height}"><rect width="450" height="{height}" fill="white"/><g stroke="#152333" stroke-width="2" fill="none">'
  assets.joinpath(name+'.svg').write_text(head+body+'</g></svg>')
 def text(x,y,s,size=16):return f'<text x="{x}" y="{y}" fill="#152333" stroke="none" font-family="sans-serif" font-size="{size}">{s}</text>'
 def line(x,y,a,b):return f'<path d="M{x},{y} L{a},{b}"/>'
 def box(x,y,w,h,label):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>'+text(x+8,y+h/2+5,label)
 def ground(x,y):return line(x,y,x,y+10)+line(x-14,y+10,x+14,y+10)+line(x-9,y+16,x+9,y+16)+line(x-4,y+22,x+4,y+22)
 # Spatial cross section is a conceptual model; no real manufacturing or anatomy dimensions.
 s=text(18,28,'Interface: spatial model and small signal',18)
 s+=box(20,60,110,105,'metal e-')+box(130,60,95,105,'')+text(134,117,'double layer',14)+box(225,60,205,105,'electrolyte ions')
 s+=text(25,193,'charge storage: Q(V); local Cdl = dQ/dV')+text(25,221,'reaction slope: Rct = d(eta)/dI')+text(25,249,'Rs: bulk ionic/contact path; all are local')
 s+=text(20,292,'Two-terminal model; teaching parameters')
 s+=line(30,390,70,390)+box(70,372,70,36,'Rs')+line(140,390,180,390)+line(180,335,180,455)+line(180,335,225,335)+box(225,317,75,36,'Rct')+line(300,335,350,335)+line(350,335,350,455)
 s+=line(180,455,252,455)+line(252,436,252,474)+line(267,436,267,474)+line(267,455,350,455)+line(350,390,410,390)+text(242,507,'Cdl')+text(24,368,'a')+text(406,368,'b')
 s+=text(18,551,'Ehc is a separate DC source, not Z(f).')+text(18,581,'No skin geometry / diffusion / motion claim.')
 svg('interface',s,610)
 # Closed synthetic source / input-loading network, each source returned to same bench 0.
 s=text(15,28,'Synthetic bench: two loaded input nodes',18)
 for y,label,pol in ((100,'Vc + Vd/2','+'),(270,'Vc - Vd/2','-')):
  s+=f'<circle cx="55" cy="{y}" r="24"/>'+text(47,y-5,'+')+text(48,y+17,'-')+line(55,y+24,55,y+80)+line(55,y+80,350,y+80)+line(55,y-24,55,y-45)+line(55,y-45,115,y-45)+box(115,y-63,70,36,'Ze')+line(185,y-45,350,y-45)+line(350,y-45,350,y-10)+box(305,y-10,90,40,'Zin')+line(350,y+30,350,y+80)+text(12,y+111,label)
  s+=line(240,y-45,240,y-20)+text(192,y+3,'v'+('1' if y==100 else '2'))
 s+=ground(350,180)+text(375,200,'0')+ground(350,350)+text(375,375,'0')
 s+=box(30,443,390,70,'Vo = Ad(v1-v2) + Ac(v1+v2)/2')+text(20,547,'Zin = Rin || Cin, local reference 0')+text(20,577,'Abstract powered readout; no body terminals')+text(20,607,'Electrode DC offsets / noise enter separately')
 svg('readout',s,640)
 s=text(15,28,'Isolation: domains and residual coupling',18)
 s+=box(25,60,160,145,'')+box(265,60,160,145,'')+text(35,85,'bench domain A')+text(275,85,'host domain H')+text(43,107,'phantom source',14)+text(42,134,'protect / bias',14)+text(42,160,'AFE',14)+text(42,187,'ADC / reference A',14)+text(282,107,'data / reference H',14)
 s+=line(185,190,205,190)+box(205,171,60,38,'ISO')+text(20,246,'Power and data barriers both matter')
 s+=line(80,305,205,305)+line(205,285,205,325)+line(220,285,220,325)+line(220,305,360,305)+text(193,357,'Cp')+text(45,289,'A')+text(356,289,'H')
 s+=line(80,305,80,420)+line(360,305,360,420)+line(80,420,175,420)+f'<circle cx="200" cy="420" r="25"/>'+line(225,420,360,420)+text(185,425,'~')
 s+=text(24,470,'Bench AC source VAH; two-terminal Cp loop')+text(24,500,'Irms = 2 pi f Cp Vrms (ideal sinusoid)')+text(24,539,'Protection / fault paths need separate models')+text(24,569,'NOT a human hookup or compliance schematic')
 svg('isolation',s,605)
 with matplotlib.rc_context({'font.size':10,'svg.hashsalt':'f05-r1','axes.grid':True}):
  def plot(name,fn):
   fig=Figure(figsize=(4.5,6.0),layout='constrained');FigureCanvasAgg(fig);fn(fig);fig.savefig(assets/(name+'.svg'),metadata={'Date':None})
  freq=[10**(-1+5*i/200) for i in range(201)]
  def imped(fig):
   a,b=fig.subplots(2,1);z=[m.randles(f) for f in freq];a.plot([v.real/1000 for v in z],[-v.imag/1000 for v in z]);a.set(xlabel='Re Z (kohm)',ylabel='-Im Z (kohm)',title='Randles: one local time constant');a.set_aspect('equal',adjustable='datalim')
   b.semilogx(freq,[20*math.log10(abs(m.readout(f)[0]/m.readout(f)[1])) for f in freq],label='1 kohm mismatch');b.axhline(100,color='black',linestyle='--',label='nominal 100 dB');b.set(xlabel='Frequency (Hz)',ylabel='Effective CMRR (dB)');b.legend(fontsize=9)
  plot('impedance-cmrr',imped)
  def noise(fig):
   a,b=fig.subplots(2,1)
   for key,style in (('electrode','-'),('current','--'),('voltage',':')):
    a.loglog(freq,[math.sqrt(m.noise_psd(f)[key])/100*1e9 for f in freq],linestyle=style,label=key)
   a.set(xlabel='Frequency (Hz)',ylabel='Output-referred / Ad (nV/sqrt Hz)',title='Independent source budget');a.legend(fontsize=9)
   f=[5,20,80];b.plot(f,[1/math.sqrt(1+(v/100)**2) for v in f],'o-',label='analog RC: fc=100 Hz');b.set(xlabel='Calibration frequency (Hz)',ylabel='Magnitude (V/V)',ylim=(0,1.1));b.legend(fontsize=9)
  plot('noise-calibration',noise)
  fs=1000;n=2000;hd,hc,*_=m.readout(50);t=[i/fs for i in range(n)]
  # tone-specific transfer: independent 10 Hz Hd and 50 Hz Hc, plus explicit offset-motion input already at amplifier nodes.
  h10=m.readout(10)[0];raw=[(h10*100e-6*complex(math.cos(2*math.pi*10*v),math.sin(2*math.pi*10*v))).imag+(hc*.1*complex(math.cos(2*math.pi*50*v),math.sin(2*math.pi*50*v))).imag+(1.2 if v>=1 else 0) for v in t]
  clipped=[max(-1,min(1,v)) for v in raw];filtered=m.rc_hold(clipped)
  def traces(fig):
   a,b=fig.subplots(2,1);a.plot(t,raw,label='pre-ADC model');a.plot(t,clipped,'--',label='clip +/-1 V');a.set(xlabel='Time (s)',ylabel='Output (V)',title='Synthetic motion offset step');a.legend(fontsize=9)
   b.plot(t,filtered,label='RC after clipping');b.set(xlabel='Time (s)',ylabel='Output (V)');b.legend(fontsize=9)
  plot('synthetic-artifact',traces)
 for p in sorted(assets.glob('*.svg')):
  for width in (360,425):cairosvg.svg2png(url=str(p),write_to=str(p.with_name(p.stem+f'-{width}.png')),output_width=width)
 summary={'parameters':{'status':'teaching only; no device guarantee','electrode1_Rs_Rct_Cdl_SI':[5000,100000,1e-6],'electrode2_Rs_Rct_Cdl_SI':[6000,100000,1e-6],'Rin_ohm':1e7,'Cin_F':1e-10,'Ad':100,'Ac':.001,'temperature_K':300,'en_V_per_sqrtHz':20e-9,'each_in_A_per_sqrtHz':1e-12,'noise_rect_band_Hz':[1,100],'adc_span_V':2,'adc_bits':16},'randles_10Hz':{'real':m.randles(10).real,'imag':m.randles(10).imag},'readout_50Hz':{'Hd_abs':abs(hd),'Hc_abs':abs(hc),'cmrr_db':20*math.log10(abs(hd/hc))},'noise_1_100Hz_output_rms':m.integrate_noise(),'noise_1_100Hz_output_rms_2048':m.integrate_noise(intervals=2048),'barrier_100Hz_10pF_1Vrms_A':m.barrier_current(100,1e-11,1),'adc':m.adc_budget(),'offset_10mV_adc':m.adc_budget(offset=.01),'calibration_RC_5_20_80Hz':[1/math.sqrt(1+(v/100)**2) for v in (5,20,80)],'synthetic_clipped_samples':sum(abs(a-b)>1e-15 for a,b in zip(raw,clipped))}
 (output/'result.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 (output/'synthetic.json').write_text(json.dumps({'fs_Hz':fs,'construction':{'N':n,'differential_Hz':10,'differential_peak_V':100e-6,'common_Hz':50,'common_peak_V':.1,'motion_output_step_V':1.2,'step_time_s':1,'clip_limits_V':[-1,1],'postclip_hold_RC_fc_Hz':100,'postclip_initial_V':0},'time_s':t,'raw_V':raw,'clipped_V':clipped,'postclip_RC_V':filtered},separators=(',',':'))+'\n')
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args();generate(args.output)
