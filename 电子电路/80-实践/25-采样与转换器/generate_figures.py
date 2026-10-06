"""Editable425px SVG and360/425 PNG; explicit output, lazy dependencies."""
import argparse
from pathlib import Path
import json
import math
from html import escape
import converter_model as m


def line(x,y,X,Y):return f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}"/>'
def text(x,y,s,size=14):return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'
def ground(x,y):return line(x,y-12,x,y)+line(x-10,y,x+10,y)+line(x-7,y+4,x+7,y+4)
def cap(x,y,label):return line(x,y,x,y+15)+line(x-12,y+15,x+12,y+15)+line(x-12,y+23,x+12,y+23)+line(x,y+23,x,y+40)+text(x+16,y+25,label,13)
def res(x,y,X,label):
 a=(x+X)/2;return line(x,y,a-20,y)+f'<rect x="{a-20}" y="{y-8}" width="40" height="16" fill="white"/>'+line(a+20,y,X,y)+text(a-22,y-15,label,13)
def switch(x,y,X,label):return line(x,y,x+12,y)+line(x+12,y,X-8,y-12)+line(X-8,y,X,y)+text(x,y-35,label,13)
def svg(body,height,title,desc):return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{height}" viewBox="0 0 425 {height}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="425" height="{height}" fill="white"/><g stroke="#111" stroke-width="2" fill="none">{body}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'
def comparator(x,y):
 return f'<path d="M{x} {y} L{x} {y+90} L{x+70} {y+45} Z"/>'+text(x+6,y+28,'+',16)+text(x+6,y+73,'-',16)+line(x+35,y+22.5,x+35,y-15)+text(x+40,y-10,'+3.3V',12)+line(x+35,y+67.5,x+35,y+110)+text(x+40,y+110,'-3.3V',12)


def circuits():
 b=text(15,25,'Track: source R, reservoir and CH',17)+text(15,51,'u, a, h are volts relative to ground')
 b+=text(15,108,'u')+res(35,120,145,'Rsource')+dot(145,120)+text(147,108,'a')+switch(145,120,250,'track clock')+dot(250,120)+text(255,108,'h')+line(250,120,340,120)
 b+=cap(145,120,'CR 1nF')+ground(145,172)+cap(250,120,'CH 20pF')+ground(250,172)+text(305,180,'to ADC',12)
 b+=text(15,211,'Closure shares old charge; then R restores')+text(15,239,'CR:2V, CH:0V -> 1.960784V')
 b+=text(15,290,'Reference: periodic charge withdrawal',17)+text(15,331,'VRef=3V')+res(85,345,225,'Rref 10ohm')+dot(225,345)+line(225,345,345,345)+text(310,332,'to CDAC')+cap(225,345,'Cref 1uF')+ground(225,397)
 b+=line(335,345,335,402)+'<circle cx="335" cy="417" r="15"/>'+line(335,410,335,424)+'<path d="M331 420 L335 425 L339 420"/>'+line(335,432,335,457)+ground(335,469)+text(15,494,'Q=20pC/event, period10us; pulse current')+text(15,519,'External VDD powers switches/comparator')+text(15,544,'Reference scale is separate from VDD')
 return {'track-reference':svg(b,565,'Track and reference networks','Actual source-series resistance, switched reservoir/hold capacitor and reference recharge RC. Switches ideal; ADC/comparator downstream separate.')}


def dac_networks():
 b=text(15,25,'String: select tap4, bottom-to-top r',17)+text(15,50,'VRef3V at top; tap0=0; no top code')
 for j in range(8):
  y=85+j*29;b+=line(80,y,80,y+7)+f'<rect x="72" y="{y+7}" width="16" height="15" fill="white"/>'+line(80,y+22,80,y+29)
  if j==3:b+=dot(80,y+29)+line(80,y+29,260,y+29)+text(180,y+18,'tap4 out')
 b+=line(260,201,260,226)+'<rect x="252" y="226" width="16" height="30" fill="white"/>'+line(260,256,260,275)+ground(260,287)+text(275,244,'RL10k',13)+text(95,85,'3V')+ground(80,329)+text(150,260,'')+text(150,285,'Rth(tap4)=2k')+text(150,310,'loaded1.25V')
 b+=text(15,375,'R-2R: node0 output, extra termination',17)
 ys=420
 for j,x in enumerate([70,190,310]):
  b+=dot(x,ys)+text(x-15,ys-10,'v'+str(j))+line(x,ys,x,ys+25)+f'<rect x="{x-8}" y="{ys+25}" width="16" height="32" fill="white"/>'+line(x,ys+57,x,ys+82)+text(x+12,ys+45,'2R',12)+text(x-25,ys+102,['b2 VRef','b1 VRef','b0 VRef'][j],12)
  if j<2:b+=res(x,ys,x+120,'R')
 b+=line(310,ys,390,ys)+line(390,ys,390,ys+25)+f'<rect x="382" y="{ys+25}" width="16" height="32" fill="white"/>'+line(390,ys+57,390,ys+82)+ground(390,ys+94)+text(365,ys+118,'2R',12)+text(15,565,'Bit sources choose0/3V; out=v0')
 b+=text(15,625,'CDAC: floating top x; conserved charge',17)+line(65,670,350,670)+text(15,672,'x')
 for j,x in enumerate([65,155,245,335]):b+=dot(x,670)+cap(x,670,['4C','2C','C','C'][j])+line(x,710,x,738)+text(x-28,760,['b2','b1','b0','dummy0'][j],12)
 b+=text(15,799,'Track: x=0, all bottoms Vin; hold: float x')+text(15,824,'Bits bottom0/3V; dummy0; total8C')
 b+=text(15,885,'Current steering: output or dummy',17)+text(15,912,'VDD=3.3V; ideal current compliance assumed')
 for j,x in enumerate([75,190,305]):
  b+=line(x,950,x,970)+f'<circle cx="{x}" cy="985" r="15"/>'+line(x,978,x,992)+f'<path d="M{x-4} 988 L{x} 993 L{x+4} 988"/>'+text(x+18,986,['4I','2I','I'][j],13)+line(x,1000,x,1020)+line(x,1020,x-20,1045)+line(x-20,1045,x-20,1060)+line(x+20,1045,x+20,1100)
 b+=line(75,950,305,950)+text(15,944,'VDD')+line(55,1060,90,1060)+'<path d="M90 1060 Q95 1050 100 1060"/>'+line(100,1060,205,1060)+'<path d="M205 1060 Q210 1050 215 1060"/>'+line(215,1060,320,1060)+'<path d="M320 1060 Q325 1050 330 1060"/>'+line(330,1060,335,1060)+dot(55,1060)+dot(170,1060)+dot(285,1060)+text(20,1050,'o')+line(95,1100,325,1100)+text(340,1104,'d')+line(335,1060,335,1140)+line(325,1100,325,1156)+ground(335,1168)+ground(325,1168)+text(15,1195,'o:RL1k to0; d:dummy sink to0')+text(15,1220,'All source currents flow even at code0')
 # Replace output direct wire to ground by resistor, preserving dummy sink.
 b=b.replace(line(335,1060,335,1140),line(335,1060,335,1114)+'<rect x="327" y="1114" width="16" height="26" fill="white"/>'+line(335,1140,335,1156))
 return svg(b,1245,'Four DAC physical networks','String taps; tridiagonal voltage-modeR2R; top-plate charge conserving CDAC; current sources steered to resistive output or grounded dummy. Bit voltage terminals are ideal controlled voltage sources0/VRef.')


def sar_circuit():
 b=text(15,25,'3bit CDAC SAR: held charge + decisions',17)+text(15,54,'Track x=0; all bottom plates Vin')+line(50,115,340,115)+text(15,119,'x')
 b+=line(340,115,390,115)+line(390,115,390,135)+line(390,135,377,158)+line(390,158,390,177)+ground(390,189)+text(260,90,'reset track ->0',12)
 for j,x in enumerate([50,145,240,335]):
  b+=cap(x,180,['4C','2C','C','dummyC'][j])+line(x,115,x,180)+line(x,220,x,245)+line(x,245,x+18,258)+text(x-24,240,['b2','b1','b0','dummy'][j],11)
  for dx,lab in [(-22,'Vin'),(0,'0'),(22,'3V' if j<3 else '0')]:
   b+=f'<circle cx="{x+dx}" cy="260" r="2"/>'+text(x+dx-8,279,lab,10)

 b+=text(15,300,'Hold bottoms select0/VRef3V (dummy0)')+text(15,325,'Track closes input selection; hold opens it')
 b+=comparator(220,380)+line(50,115,8,115)+line(8,115,8,455)+line(8,455,220,455)+line(220,410,185,410)+ground(185,422)+line(290,425,360,425)+text(300,405,'d=1 if x<=0',12)
 b+=text(15,520,'Analog comparator +/-3.3V; logic0/3.3V')+text(15,545,'Level interface assumed ideal, not fabricated')+text(15,579,'Clock: update -> settle -> compare -> latch')+text(15,604,'SAR register bits drive three bottom switches')+text(15,629,'Vin1.9V: VD1.5,2.25,1.875 -> code101')
 return svg(b,650,'CDAC SAR physical signal and decision convention','Top reset switch and four capacitors; comparison0 versus floating topx=-Vin+VD; explicit analog rails and logical voltage interface. Bottom selectors indicated by labeled ideal voltage terminals, action sequenced by clock.')


def architecture():
 b=text(15,25,'Flash: held Vin vs seven thresholds',17)
 for j in range(7):
  y=70+j*40;b+=text(15,y+18,f'{(j+1)*.375:.3f}V')+line(100,y+23,145,y+23)+line(130,y+8,145,y+8)+dot(130,y+8)+f'<path d="M145 {y} L145 {y+30} L178 {y+15} Z"/>'+text(147,y+12,'+',12)+text(147,y+26,'-',12)+line(160,y+6.8,160,y-5)+line(160,y+23.2,160,y+35)+text(164,y-1,'+',10)+text(164,y+37,'-',10)+line(178,y+15,225,y+15)+text(230,y+20,'t'+str(j+1),13)
 b+=line(130,55,130,318)+text(105,49,'Vin',12)+text(275,90,'Vin shared')+text(275,125,'latch clock')+text(275,165,'rails +/-3.3V')+text(275,205,'all comparator')+text(275,230,'supply pins')+text(275,255,'same model')+text(15,378,'valid thermometer -> encode -> register')
 b+=text(15,430,'Pipeline: two3bit stages, gain8 residue',17)+text(15,469,'v[k] -> c1[k], D1=c1*3/8')+text(15,500,'r[k]=8(v[k]-D1[k]) -> c2[k] next stage')+text(15,531,'align: code[k]=8c1[k]+c2[k]')+text(15,562,'Filled pipeline: rate1/clock; latency2clocks')
 b+=text(15,620,'First-order normalized delta-sigma',17)+text(15,662,'q[k]=s[k]+u[k]; y[k]=sign(q[k])')+text(15,693,'s[k+1]=q[k]-y[k], feedbackDAC +/-1')+text(15,724,'Initial s0=0; |u|<=1, |s0|<=1')+text(15,755,'Bounded state here is proved, not assumed')+text(15,786,'Linear e replacement: STF1, NTF1-z^-1')
 return svg(b,810,'Architecture signal and state contracts','Flash actual comparator symbols; abstract pipeline and specific normalized first-order delta-sigma update equations. Does not claim transistor implementation of all architectures.')


def generate(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 # Explicit generation confines font/cache initialization. Restore process state.
 import os
 old={k:os.environ.get(k) for k in ['MPLCONFIGDIR','XDG_CACHE_HOME']}
 os.environ['MPLCONFIGDIR']=str(output/'.mplconfig');os.environ['XDG_CACHE_HOME']=str(output/'.cache')
 try:
  import matplotlib as mpl
  from matplotlib.figure import Figure
  import cairosvg
  with mpl.rc_context({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','svg.hashsalt':'adc-v1'}):
   diagrams=circuits();diagrams.update({'dac-networks':dac_networks(),'sar-circuit':sar_circuit(),'architectures':architecture()})
   def save(name,fig):
    fig.savefig(output/(name+'.svg'),metadata={'Date':None},facecolor='white')
   def fig(n,h):
    f=Figure(figsize=(4.25,h),dpi=100);a=f.subplots(n,1);f.subplots_adjust(left=.24,right=.96,top=.92,bottom=.12,hspace=.55);return f,([a] if n==1 else list(a))
   f,ax=fig(2,6);f.subplots_adjust(bottom=.18);v=[i*3/320 for i in range(321)];q=[m.quantize(x) for x in v]
   ax[0].step(v,[r['center_V'] for r in q],where='post',color='black');ax[0].plot(v,v,'--',color='gray');ax[0].set(ylabel='Center / V',title='3bit midrise, range0..3V')
   ax[1].plot(v,[r['error_V'] for r in q],color='black');ax[1].axhline(.1875,ls='--',color='gray');ax[1].axhline(-.1875,ls='--',color='gray');ax[1].set(xlabel='Input / V',ylabel='Error / V',title='Tie goes upper; endpoints clipped');f.text(.03,.018,'Variance delta^2/12: uniform, no overload\nWhite-error model needs extra decorrelation',fontsize=9.5);save('quantizer',f)
   f,ax=fig(4,10);t=[i/8000 for i in range(9)];continuous=[i/128000 for i in range(129)]
   for hz,ls in [(2000,'-'),(6000,'--')]:ax[0].plot([s*1e3 for s in continuous],[math.cos(2*math.pi*hz*s) for s in continuous],ls,color='black',label=str(hz)+'Hz')
   ax[0].plot([s*1e3 for s in t],[math.cos(2*math.pi*2000*s) for s in t],'o',color='gray');ax[0].set(ylabel='V',xlabel='Time / ms',title='fs8kS/s;2k and6k same samples');ax[0].legend(fontsize=11)
   ax[1].plot(list(range(16)),[m.quantize(.1)['error_V']]*16,'o-',color='black');ax[1].set(xlabel='Sample k',ylabel='Error / V',title='DC0.1V: correlated error, not white')
   tt=[i/2000000 for i in range(251)];ax[2].plot([s*1e6 for s in tt],[(math.sin(2*math.pi*2000*(s+10e-9))-math.sin(2*math.pi*2000*s))*1e3 for s in tt],color='black');ax[2].set(xlabel='Time / us',ylabel='Timing error / mV',title='1V2kHz; fixed+10ns, not random');ax[3].stem([2],[1],linefmt='k-',markerfmt='ko',basefmt='k-');ax[3].annotate('Either2k or6k ->2kHz',xy=(2,1),xytext=(.2,.65),fontsize=11);ax[3].set(xlim=(0,4),ylim=(0,1.25),xlabel='Sampled frequency / kHz',ylabel='Amplitude / V',title='fs8k; folded line spectrum (notPSD)');save('alias-jitter',f)
   f,ax=fig(4,10);ax[0].step([0,2,3,4,5,6],[0,1.5,2.25,1.875,1.875,1.875],where='post',color='black');ax[0].axhline(1.9,color='gray',ls='--');ax[0].set(ylabel='DAC / V',title='Trials1.5 ->2.25 ->1.875V')
   ax[1].step([0,2,3,4,5,6],[1,0,0,0,0,1],where='post',color='black');ax[1].set(ylabel='TRACK',ylim=(-.2,1.2),title='Aperture2us; hold until next frame')
   ax[2].step([0,3,4,5,6],[0,4,4,5,5],where='post',color='black');ax[2].plot([3,4,5],[4,4,5],'o',color='black');ax[2].set(ylabel='Retained code',title='Decisions at3,4,5us; valid101 at5');ax[3].step([0,2.8,3,3.8,4,4.8,5,6],[0,1,0,1,0,1,0,0],where='post',color='black');ax[3].set(xlabel='Time / us',ylabel='Decision clock',ylim=(-.2,1.2),title='Latch at trailing edges3,4,5us');save('sar-timing',f)
   f,ax=fig(2,6);ts=[i*3e-6/300 for i in range(301)];errors=[3.3*math.exp(-t/(1e4*20e-12))/(3.3/2**17) for t in ts];ax[0].semilogy([t*1e6 for t in ts],errors,color='black');ax[0].axhline(1,ls='--',color='gray');ax[0].set(xlabel='Track time / us',ylabel='Error / halfLSB',title='16bit3.3V;10k,20pF; DCstep')
   rows=m.reference_cycle(cycles=12);ax[1].plot([r['cycle'] for r in rows],[(3-r['after_V'])*1e6 for r in rows],'o-',color='black');ax[1].set(xlabel='Event k',ylabel='Reference droop / uV',title='20pC,1uF,10ohm,10us repeated');save('settling',f)
   for name,s in diagrams.items():(output/(name+'.svg')).write_text(s)
   for name in ['quantizer','alias-jitter','sar-timing','settling']:
    p=output/(name+'.svg');s=p.read_text();s=s.replace('<svg ',f'<svg ',1);i=s.index('>',s.index('<svg '))+1;s=s[:i]+f'<title>{name}</title><desc>Traceable SI teaching model; parameters and arrays in figure-data.json.</desc>'+s[i:];p.write_text(s)
   for name in ['quantizer','alias-jitter','sar-timing','settling',*diagrams]:
    for w in [360,425]:cairosvg.svg2png(url=str(output/(name+'.svg')),write_to=str(output/f'{name}-{w}.png'),output_width=w)
   data={'quant_input_V':v,'quant_center_V':[r['center_V'] for r in q],'quant_error_V':[r['error_V'] for r in q],'sample_t_s':[i/8000 for i in range(9)],'alias_continuous_t_s':continuous,'alias_candidate2k_V':[math.cos(2*math.pi*2000*s) for s in continuous],'alias_candidate6k_V':[math.cos(2*math.pi*6000*s) for s in continuous],'jitter_t_s':tt,'fixed10ns_error_V':[math.sin(2*math.pi*2000*(s+10e-9))-math.sin(2*math.pi*2000*s) for s in tt],'sar_trace':m.sar(1.9),'settling_t_s':ts,'settling_halfLSB':errors,'reference_events':rows,'conventions':'V/s/Hz;3bit0..3V midrise center;SAR lower-edge DAC;fixed10ns timing offset;alternative2k/6k inputs, not summed;no PSD'}
   (output/'figure-data.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)

if __name__=='__main__':
 import math
 main()
