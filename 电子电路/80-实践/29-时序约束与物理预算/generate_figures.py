"""Editable 425px teaching SVG, actual360/425 PNG, lazy plotting imports."""
import argparse,json,math,os
from pathlib import Path
from html import escape
import implementation_model as m

def ln(x,y,X,Y,dash=False):return f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>'
def tx(x,y,s,size=14):return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'
def box(x,y,w,h,label=''):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white"/>'+tx(x+6,y+h/2+5,label)
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'
def cap(x,y,label):return ln(x,y,x,y+15)+ln(x-10,y+15,x+10,y+15)+ln(x-10,y+23,x+10,y+23)+ln(x,y+23,x,y+45)+tx(x+14,y+24,label,12)
def ground(x,y):return ln(x,y-10,x,y)+ln(x-10,y,x+10,y)+ln(x-6,y+4,x+6,y+4)
def res(x,y,X,label):a=(x+X)/2;return ln(x,y,a-20,y)+box(a-20,y-8,40,16)+ln(a+20,y,X,y)+tx(a-20,y-16,label,12)
def ff(x,y,label='DFF',reset=False):
 s=box(x,y,70,65,label)+tx(x+4,y+17,'D',12)+tx(x+54,y+17,'Q',12)+f'<path d="M{x} {y+42} L{x+8} {y+47} L{x} {y+52}"/>'
 if reset:s+=ln(x+35,y+65,x+35,y+82)+tx(x+38,y+80,'RN',11)
 return s

def wrap(body,h,title,desc):return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{h}" viewBox="0 0 425 {h}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="425" height="{h}" fill="white"/><g stroke="#111" stroke-width="2" fill="none">{body}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'

def process():
 b=tx(15,25,'Planar CMOS: section, not foundry masks',17)+tx(15,52,'PMOS in n-well; NMOS in p-substrate')
 b+=box(25,120,375,140)+box(40,135,160,110,'n-well')+tx(240,220,'p-substrate')
 for x,lab in [(55,'p+S'),(145,'p+D'),(255,'n+D'),(345,'n+S')]:b+=box(x,130,25,28)+tx(x-3,178,lab,12)
 for x in [112,312]:b+=box(x-22,112,44,6)+box(x-15,85,30,25,'G')
 b+=ln(40,65,390,65)+tx(345,56,'u')+ln(112,65,112,85)+ln(312,65,312,85)
 b+=ln(67,130,67,103)+ln(357,130,357,103)+tx(30,94,'VDD')+tx(350,94,'VSS',12)
 b+=ln(157,130,157,125)+ln(157,125,267,125)+ln(267,125,267,130)+tx(206,116,'y metal',12)
 b+=ln(185,180,185,285)+tx(105,305,'well tap -> VDD')+ln(370,220,370,285)+tx(270,305,'body tap -> VSS',12)
 b+=tx(15,346,'Cell top view: geometry + pins + rails',17)+box(35,385,340,165)+ln(35,392,375,392)+tx(40,381,'VDD rail')+ln(35,542,375,542)+tx(40,575,'VSS rail')
 b+=box(60,420,85,30)+tx(80,442,'P',12)+box(60,486,85,30)+tx(80,508,'N',12)+ln(103,408,103,529)+tx(155,419,'drain metal',12)+ln(103,464,240,464)+dot(103,464)+tx(248,469,'u pin')
 b+=ln(70,435,70,392)+dot(70,435)+ln(70,501,70,542)+dot(70,501)+dot(135,435)+dot(135,501)+ln(135,435,280,435)+ln(135,501,280,501)+ln(280,435,280,501)+tx(288,501,'y pin')
 b+=tx(15,615,'Pin crossing only joins with stated contact')+tx(15,642,'LEF/GDS geometry must match Liberty/netlist')
 return wrap(b,665,'CMOS process and cell views','Qualitative planarCMOS section and abstract cell top view. Geometry is teaching coordinates, not DRC-clean masks or a named technology process; voltage terminals and body/well taps labeled.')

def floorplan():
 b=tx(15,25,'Floorplan: rows, macro, routes and layers',17)+tx(15,53,'Corearea2000um2; cellarea1200um2')+box(25,85,375,340)
 for y in [100,165,230,295,360]:
  b+=ln(35,y,390,y)+ln(35,y+38,390,y+38)
  for x in [40,100,160,220,280,340]:
   if not(150<=x<=250 and 150<=y<=260):b+=box(x,y+3,45,32,'c')
 b+=box(148,151,125,113,'macro / block')
 b+=f'<path d="M62 120 L125 120 L125 278 L290 278 L290 380" stroke-dasharray="5 4"/>'+tx(35,453,'Dashed net detours around blockage')
 b+=tx(15,495,'Routing cross-section: different layers',17)+ln(40,550,380,550)+tx(40,535,'M2 net')+ln(120,615,350,615)+tx(125,640,'M1 net')+box(240,548,12,69,'')+tx(260,589,'via joins here',12)
 b+=tx(15,685,'Demand12 / capacity10 -> overflow2 tracks')+tx(15,714,'Average utilization is not pin-access proof')
 return wrap(b,735,'Floorplan and routing layers','Qualitative cellrows, macro blockage and detoured net;M1/M2 connected only at explicitvia. No legal placement/routing result claimed.')

def sta():
 b=tx(15,25,'Setup and hold use different capture edges',17)+tx(15,53,'T10ns; capture-launch skew+0.5ns')
 b+=ff(45,95,'launch')+ff(290,95,'capture')+ln(115,112,155,112)+box(155,95,90,35,'logic/wire')+ln(245,112,290,112)+tx(120,154,'Q -> max6/min0.25ns -> D',12)
 b+=ln(45,142,25,142)+ln(25,142,25,185)+ln(290,142,275,142)+ln(275,142,275,185)+tx(20,205,'clk L0=0')+tx(270,205,'clk C0=0.5',12)
 b+=tx(15,249,'Latest data vs next edge: setup',17)
 def timeline(y):
  s=ln(55,y,390,y)
  for val in [0,.5,6.8,9.6,10.5]:
   x=55+val*30;s+=ln(x,y-6,x,y+6)
  return s
 b+=timeline(300)+tx(35,283,'L0=0')+tx(215,329,'latest6.8ns')+tx(286,362,'deadline9.6ns')+tx(305,280,'C1=10.5')+ln(259,302,343,302)+tx(120,395,'setup slack2.8ns; uncertainty0.2')
 b+=tx(15,445,'Earliest data vs same edge: hold',17)+ln(55,505,390,505)
 for val,label in [(0,'L0'),(.4,'new earliest'),(.5,'C0'),(.65,'hold deadline')]:
  x=55+val*450;b+=ln(x,498,x,512)+tx(270 if val==.65 else x-10,535 if val in [0,.5] else (475 if val==.4 else 575), 'deadline0.65' if val==.65 else ('.4 earliest' if val==.4 else label),12)
 b+=tx(15,613,'0.4ns <0.65ns -> holdslack-0.25ns')+tx(15,642,'Hold axis is zoomed; lowering f does not fix')
 return wrap(b,670,'STA physical paths and deadlines','Teaching absolute-clock and data paths;setupnextcapture10.5ns andholdsamecapture.5ns;max6.8nsarrival,min.4nsarrival. Holdaxis uses a different zoom explicitly. No actual STA log.')

def rcclock():
 b=tx(15,25,'Extracted teaching RC tree: first moment',17)+tx(15,52,'All capacitors to reference; no coupling')
 b+=tx(15,115,'u')+res(30,130,135,'Rd100')+res(135,130,250,'R1 200')+res(250,130,365,'R2 300')+dot(250,130)+dot(365,130)+tx(247,115,'a')+tx(365,115,'b')+cap(250,130,'20fF')+ln(250,175,250,178)+ground(250,188)+cap(365,130,'30fF')+ln(365,175,365,178)+ground(365,188)
 b+=tx(15,228,'a:15ps; b:24ps one-sided first moment')+tx(15,257,'Not measured50%delay; not foundry SPEF')
 b+=tx(15,316,'Clock tree and independent data route',17)+box(165,355,90,35,'rootclk')+ln(210,390,210,430)+dot(210,430)+ln(75,430,350,430)+ln(75,430,75,470)+ln(350,430,350,470)+box(45,470,70,35,'buf L')+box(310,470,70,35,'buf C')
 b+=ln(75,505,25,505)+ln(25,505,25,602)+ln(25,602,45,602)+ln(350,505,290,505)+ln(290,505,290,566)+f'<path d="M290 566 Q278 572 290 578"/>'+ln(290,578,290,602)+ln(290,602,310,602)+ff(45,555,'launch')+ff(310,555,'capture')+ln(115,572,180,572)+box(180,555,80,35,'data')+ln(260,572,310,572)
 b+=tx(155,415,'shared0.3ns',12)+tx(15,535,'branch0.5ns',12)+tx(290,535,'branch1.0ns',12)+tx(15,657,'Clock L0.8ns / C1.3ns -> skew+0.5ns')+tx(15,688,'Equal route length need not equal delay')
 return wrap(b,710,'RC extraction and clock tree paths','SourceR and two-section RC with explicitly grounded capacitors. Separate teachingclocktree common.3 plusbranches.5/1ns into DFF clockpins;data route joins Q/D,not clock. No real extraction or CTS.')

def powergrid():
 b=tx(15,25,'Power grid: feed, return, load and decap',17)+tx(15,55,'Source1V; I20mA; VDDpath0.5ohm')+tx(15,112,'Vsource')+res(40,135,235,'Rfeed0.5')+dot(235,135)+ln(235,135,350,135)+tx(245,115,'Vlocal0.99V',12)
 b+=cap(235,135,'Cdecap')+ln(235,180,235,330)+box(305,180,80,95,'cell load')+ln(350,135,350,180)+ln(350,275,350,330)+ln(350,330,235,330)+dot(235,330)+res(30,330,235,'Rreturn')+tx(20,366,'VSSsource')+tx(290,310,'20mA down',12)
 b+=tx(15,411,'ReturnR can lift localVSS; not renamed away')+tx(15,454,'Metal section for EM units',17)+box(90,490,190,55)+tx(110,522,'1um x0.2um')+tx(15,587,'J=0.02A /0.2um2 =1e11A/m2')+tx(15,616,'No technology lifetime threshold asserted')+tx(15,655,'Transient1mA x1ns /10mV ->100pF')+tx(15,684,'ESR/ESL and actual source grid still needed')
 return wrap(b,710,'Supply feed and return physical budget','Feed R and return R,cell currentload and localdecap connected across localrails. EMcrosssection dimensions explicitly teaching. Does not assert lifetimes, IRtoolrun or transient waveform.')

def cdc():
 b=tx(15,25,'CDC: first stage resolves, second is timed',17)+tx(15,53,'Two real storage stages; binary model only')+ff(90,105,'sync1')+ff(285,105,'sync2')+ln(20,122,90,122)+tx(15,95,'async bit')+ln(160,122,220,122)+box(220,105,35,32,'buf')+ln(255,122,285,122)+ln(355,122,400,122)+tx(365,105,'out',12)
 b+=ln(90,152,70,152)+ln(285,152,265,152)+ln(70,152,70,200)+ln(265,152,265,200)+ln(70,200,265,200)+tx(80,228,'destination clk to both')+tx(15,266,'Tr = T+s-delta1-d12-setup2-u')+tx(15,288,'s: capture-(launch+T); d12: wire/buffer',12)+tx(15,310,'delta1: fitted tail origin after launch',12)+tx(15,332,'ns: T=1,s=0,delta1=.2,d12=.1',12)+tx(15,354,'setup2=.1,u=.05 -> Tr=.55ns')+tx(15,376,'delta1 not guaranteed CQ upper bound')+tx(15,398,'Do not false-path stage1Q -> stage2D')
 b+=tx(15,444,'Reset release chain per destination domain',17)+ff(90,496,'r1',True)+ff(285,496,'r2',True)+tx(20,513,'1')+ln(35,513,90,513)+ln(160,513,285,513)+ln(355,513,400,513)+tx(315,486,'localRN',12)
 b+=ln(90,543,70,543)+ln(285,543,265,543)+ln(70,543,70,591)+ln(265,543,265,591)+ln(70,591,265,591)+tx(80,616,'localclk; release needs edges')+ln(125,578,125,648)+ln(320,578,320,648)+ln(30,648,320,648)+dot(125,648)+tx(15,676,'external active-low RN -> async clear pins')
 b+=tx(15,719,'Data bus held under req/ack, not bitwise CDC')+tx(15,748,'Independent source reset can change Q async')+tx(15,777,'Recovery/removal + reset epoch still checked')
 return wrap(b,801,'CDC and reset physical structures','Explicit DFF stages,stage1Qto2D timeddata,shared destination clock; separate two-flop resetrelease with externalRNclears. CDC budget uses launch L0, next capture L0+T+s, fitted first-stage tail origin L0+delta1, interstage d12, setup2 and uncertainty u. delta1 is not a guaranteed ordinary tCQ upper bound under metastability; fitted prefactor/tau/time-origin must match, with no double counting. No analog metastabilitytrace, no fullFIFO implementation.')

def powerseq():
 b=tx(15,25,'AON supply owns isolation and controller',17)+tx(15,57,'validclamp0; receiver ignores data when0')+tx(15,100,'VDD_AON')+ln(40,118,390,118)+box(80,151,110,45,'power switch')+ln(110,118,110,151)+ln(110,196,110,240)+tx(115,226,'VSW',12)+box(55,240,125,105,'domain flops')+ln(180,280,240,280)+box(240,250,95,60,'isolate')+ln(335,280,395,280)+tx(340,264,'valid',12)+ln(290,118,290,250)
 b+=box(205,360,160,45,'retention backup')+ln(365,380,390,380)+ln(390,380,390,118)+tx(200,431,'backup on AON rail',12)+ln(130,345,130,383)+ln(130,383,205,383)+tx(25,405,'save/restore',12)+box(30,450,355,45,'AON controller: isolate, clk, power, RN')
 b+=tx(15,544,'k action                  required boundary',17)
 labs=['1 quiesce: in-flight done/cancelled','2 save: retention state acknowledged','3 isolate: clamp valid0 before powerloss','4 clock_off; 5 power_off','6 power_on: wait actualpower_good','7 clock_on; 8 restore/resetrelease','9 release: valid protocol may restart']
 for j,s in enumerate(labs):b+=tx(15,580+j*34,s,14)
 b+=tx(15,850,'No universal IPsequence or voltage waveforms')
 return wrap(b,875,'Powerdomain isolation and retention sequence','Switched VSW rail distinct from always-onrail;isolation andbackup powered byAON;clampvalid0 under specifiedreceiverprotocol; nine discreteactions and realexternalprerequisites. No power-aware simulation.')

def scan():
 b=tx(15,25,'Single-node stuck-at network, 12 raw faults',17)+tx(15,53,'a/b/c/n/y/unused; no equivalence collapse')
 b+=tx(20,105,'a')+tx(20,145,'b')+tx(20,225,'c')+ln(35,102,110,102)+dot(60,102)+ln(35,142,110,142)+box(110,90,85,65,'AND')+ln(195,122,255,122)+tx(215,109,'n')+box(255,110,80,60,'OR')+ln(35,222,230,222)+ln(230,222,230,152)+ln(230,152,255,152)+ln(335,137,395,137)+tx(377,125,'y')
 b+=ln(60,102,60,275)+box(60,275,110,35,'NOT -> unused')+tx(185,297,'not observed',12)
 b+=tx(15,355,'Scan functional/serial mux before each DFF',17)
 for j,x in enumerate([55,180,305]):
  b+=box(x,430,38,50,'mux')+ff(x,500,'q'+str(j))+ln(x+19,480,x-15,480)+ln(x-15,480,x-15,517)+ln(x-15,517,x,517)+ln(x+19,404,x+19,430)+tx(x+4,399,'Dfunc',12)+ln(x+38,443,x+58,443)+tx(x+40,436,'SE',12)
  b+=ln(x,547,x-12,547)+ln(x-12,547,x-12,585)
  if j<2:b+=ln(x+70,517,x+105,517)+ln(x+105,517,x+105,457)+ln(x+105,457,x+125,457)
 b+=ln(15,455,55,455)+tx(15,439,'SI',12)+ln(375,517,410,517)+tx(377,502,'SO',12)+ln(43,585,293,585)+tx(80,612,'test clock; stages read old Q')
 b+=tx(15,655,'Load target110: serial0,1,1 ->000/100/110')+tx(15,684,'110 detects aSA0; 111 masks it via c=1')+tx(15,713,'Full8patterns:10/12 raw;10/10 detectable')
 return wrap(b,740,'Fault propagation and scan architecture','ExplicitAND/OR observednetwork,unusedbranch;three scanmuxDFF chain SItoSO withseparatetestclock. FunctionalD/SE labeled terminals ideal; results refer to combinational faultmodel, not inserted hardware scan.')

def bist():
 b=tx(15,25,'3bit LFSR: qnext=[q1,q0,q2 XOR q0]',17)+tx(15,53,'bits q2q1q0; each Q moves left after edge')
 # Draw DFF chain left-to-right q0 ->q1 ->q2; feedback q2 XOR q0 feeds q0.
 for x,lab in [(60,'q0'),(185,'q1'),(310,'q2')]:b+=ff(x,140,lab)
 b+=ln(130,157,185,157)+dot(150,157)+ln(255,157,310,157)+ln(380,157,402,157)+ln(402,157,402,267)+box(175,235,70,50,'XOR')+tx(178,248,'A',10)+tx(232,257,'B',10)+tx(178,280,'Y',10)+ln(245,260,402,260)+dot(402,260)+ln(150,157,150,248)+ln(150,248,175,248)+ln(175,270,30,270)+ln(30,270,30,157)+ln(30,157,60,157)
 b+=ln(60,187,45,187)+ln(185,187,170,187)+ln(310,187,295,187)+ln(45,187,45,315)+ln(170,187,170,315)+ln(295,187,295,315)+ln(45,315,295,315)+tx(70,341,'testclk; feedback uses old q2/q0')+tx(15,365,'Only dots join crossing wires',12)
 b+=tx(15,389,'Seed001:1,3,7,6,5,2,4,1; zero locks')+tx(15,429,'Signature is a different injected recurrence',17)+tx(15,465,'f = oldq2 XOR response bit')+tx(15,499,'newq = (oldq<<1)&7 XOR (f ?011:000)')+tx(15,533,'q2next=q1; q1next=q0 XOR f; q0next=f')+tx(15,579,'Initial000; ordered responses0000 and1011')+tx(15,613,'Both signature000: explicit information loss')+tx(15,647,'No uniform-fault assumption or HWcoverage')
 return wrap(b,670,'LFSR feedback and signature alias contract','Three DFF serialpath withfeedbackXOR;equivalent explicitoldstate recurrence. SignatureMISRalternateinjectionequations below; collisionfourbitstrings given. No fabricatedrandomness or toolwaveforms.')

def generate(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True);old={k:os.environ.get(k) for k in ['MPLCONFIGDIR','XDG_CACHE_HOME']};os.environ['MPLCONFIGDIR']=str(out/'.mplconfig');os.environ['XDG_CACHE_HOME']=str(out/'.cache')
 try:
  import matplotlib as mpl
  from matplotlib.figure import Figure
  import cairosvg
  with mpl.rc_context({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','svg.hashsalt':'implementation1'}):
   images={'process-cell':process(),'floorplan':floorplan(),'sta-paths':sta(),'rc-clock':rcclock(),'power-grid':powergrid(),'cdc-reset':cdc(),'power-sequence':powerseq(),'scan-fault':scan(),'bist':bist()}
   f=Figure(figsize=(4.25,6.5),dpi=100);a=f.subplots(2,1);f.subplots_adjust(left=.23,right=.95,top=.92,bottom=.14,hspace=.6)
   stages=list(range(1,9));ds=[m.effort(stages=n)['delay_normalized'] for n in stages];a[0].plot(stages,ds,'o-',color='black');a[0].set(xlabel='Stage count N',ylabel='D / tau_inv',title='F64;g1,p1; polarity may differ')
   a[1].plot([0,1,2,3],[1,4,16,64],'o-',color='black');a[1].set_yscale('log',base=2);a[1].set(xlabel='Node in three-stage chain',ylabel='Relative input C',title='1 ->4 ->16 ->64; D15')
   p=out/'sizing.svg';f.savefig(p,metadata={'Date':None},facecolor='white');s=p.read_text();i=s.index('>',s.index('<svg '))+1;s=s[:i]+'<title>Continuous effort sizing</title><desc>Uniform effort teaching curves; all positive stages1..8 finite; polarity and actualcells must be checked.</desc>'+s[i:];images['sizing']=s
   for name,s in images.items():
    (out/(name+'.svg')).write_text(s)
    for w in [360,425]:cairosvg.svg2png(bytestring=s.encode(),write_to=str(out/f'{name}-{w}.png'),output_width=w)
   data={'units':'SI in model; ns/ps annotations explicit','stage_N':stages,'normalized_delay':ds,'caps_relative':[1,4,16,64],'timing':m.timing(),'rc':m.elmore_tree(),'supply':m.supply(),'scan':m.scan_shift(),'faults':m.faults(),'power_events':m.power_sequence(),'lfsr':m.lfsr(),'claim':'teaching figures, no realSTA/HDL/physical/analogwaveforms'}
   (out/'figure-data.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)
if __name__=='__main__':main()
