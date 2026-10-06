"""Editable original SVG/360425 renders. Lazy explicit output; no import state writes."""
import argparse,json,math,os
from pathlib import Path
from html import escape
import pcb_model as m

def line(x,y,X,Y,dash=False):return f'<line x1="{x}" y1="{y}" x2="{X}" y2="{Y}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>'
def text(x,y,s,size=15):return f'<text x="{x}" y="{y}" font-size="{size}">{escape(s)}</text>'
def box(x,y,w,h,label=''):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white"/>'+text(x+5,y+h/2+5,label)
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="3" fill="#111"/>'
def cap(x,y,label):return line(x,y,x,y+18)+line(x-12,y+18,x+12,y+18)+line(x-12,y+27,x+12,y+27)+line(x,y+27,x,y+52)+text(x+17,y+28,label,13)
def ground(x,y):return line(x,y-10,x,y)+line(x-12,y,x+12,y)+line(x-8,y+5,x+8,y+5)
def res(x,y,X,label):mid=(x+X)/2;return line(x,y,mid-22,y)+box(mid-22,y-8,44,16)+line(mid+22,y,X,y)+text(mid-25,y-18,label,13)
def wrap(b,h,title,desc):return f'<svg xmlns="http://www.w3.org/2000/svg" width="425" height="{h}" viewBox="0 0 425 {h}"><title>{escape(title)}</title><desc>{escape(desc)}</desc><rect width="425" height="{h}" fill="white"/><g stroke="#111" stroke-width="2" fill="none">{b}</g><style>text{{fill:#111;stroke:none;font-family:DejaVu Sans,sans-serif}}</style></svg>'
def schematic():
 b=text(15,25,'RCDAQ-P1: same original passive board',17)+text(15,55,'J1 input / J2 externalADC / J3 supply')
 b+=text(20,107,'J1.1 IN')+res(25,135,180,'R1 1k')+line(180,135,380,135)+dot(180,135)+dot(300,135)+text(310,118,'J2.2 OUT',13)+text(150,115,'TP2',13)
 b+=cap(180,135,'C1 1u')+line(180,187,180,250)+box(285,180,30,35,'')+line(300,135,300,180)+line(300,215,300,250)+text(325,200,'R2',13)+text(325,222,'10k',13)+line(25,250,380,250)+dot(180,250)+dot(300,250)+text(20,290,'J1.2 / J2.3 GND; TP4 reference')+ground(180,260)
 b+=text(15,335,'Supply rail is separate from IN/OUT',17)+line(35,380,385,380)+text(20,363,'J3.1 VDD')+text(260,363,'J2.1 / TP3',13)+dot(150,380)+dot(300,380)+cap(150,380,'C2 100n')+cap(300,380,'C3 1u')+line(150,432,150,475)+line(300,432,300,475)+line(35,475,385,475)+dot(150,475)+dot(300,475)+text(20,507,'J3.2 GND = common reference')
 b+=text(15,553,'TP1=IN; no poweredADC or clock on-board')+text(15,584,'0..3.3V; ceramic nonpolar C candidates')+text(15,615,'K=10/11; tau=.90909ms with10k load')+text(15,646,'Original SVG, not KiCad or measured photo')
 return wrap(b,670,'Same-board schematic','RCDAQ-P1 circuit pin-numbered external ADC/supply/input, R1/C1/R2 ground branches and C2/C3 supply loop. No onboard ADC. Connections with junction dots. Original editable schematic illustration.')
def boardtop(board):
 b=text(15,25,'RCDAQ-P1 top:40 x30mm',17)+text(15,55,'F.Cu routes; B.Cu GND zone requested')
 ox,oy,s=35,85,8.5;xy=lambda p:(ox+p[0]*s,oy+p[1]*s)
 b+=box(ox,oy,340,255)
 for net,paths in board['front_paths'].items():
  for p in paths:
   for a,c in zip(p,p[1:]):x,y=xy(a);X,Y=xy(c);b+=line(x,y,X,Y,net=='VDD')
 for p in board['pads']:
  x,y=xy((p['x_mm'],p['y_mm']));b+=f'<circle cx="{x}" cy="{y}" r="4" fill="white"/>'
 for p in board['ground_vias']:
  x,y=xy((p['x_mm'],p['y_mm']));b+=dot(x,y)
 # Labels use original coordinate regions, avoid overprinted pad labels.
 for x,y,lab in [(55,112,'J1'),(108,160,'R1'),(165,215,'C1'),(234,215,'R2'),(335,140,'J2'),(45,318,'J3'),(310,255,'C2'),(238,315,'C3'),(78,120,'TP1'),(195,120,'TP2'),(305,320,'TP3'),(185,330,'TP4')]:b+=text(x,y,lab,12)
 b+=text(15,383,'Solid: IN/OUT/GND; dashed: VDD')+text(15,412,'Filled dots are GND vias; pads white')+text(15,441,'Ground plane UNFILLED: not real DRC')+text(15,470,'Teaching CAD candidate; not actual photo')
 return wrap(b,495,'Same-board top view','Actual board.json pad/route/via coordinates scaled 8.5px/mm,40x30mm original top view. B.Cu zone not physically filled. Net line convention independent of color; not KiCad render or photograph.')
def pinmap():
 b=text(15,25,'Number is the bridge between three views',17)+box(25,90,125,70,'C1 symbol')+text(25,182,'1=OUT; 2=GND')+line(150,125,240,125)+box(240,85,155,80,'0805 pads')+box(250,178,42,42,'1')+box(340,178,42,42,'2')+line(270,166,270,178)+line(360,166,360,178)
 b+=text(15,264,'Candidate pads1.2 x1.4mm; pitch1.9mm')+text(15,297,'Actual MPN drawing not selected/checked')
 b+=text(15,355,'J2 front top view: fixed pin numbering',17)
 for j,lab in enumerate(['1 VDD','2 OUT','3 GND']):b+=box(40,400+j*45,28,28,str(j+1))+text(95,422+j*45,lab)
 b+=text(15,565,'Bottom view mirrors position, not pin IDs')+text(15,600,'Nonpolar ceramic C: replacement still qualified')
 return wrap(b,625,'Symbol footprint and connector mapping','Numbered capacitor symbol to pad1OUT pad2GND and J2 explicit VDD/OUT/GND. Land geometry teaching only;actualMPN/ratings/part polarity not qualified.')
def returns():
 b=text(15,25,'Top view: continuous vs split reference',17)
 for y,split in [(70,False),(245,True)]:
  b+=box(30,y,365,110)+box(45,y+28,65,65,'source')+box(310,y+28,65,65,'load')+line(110,y+40,310,y+40)+text(120,y+23,'forward signal',13)
  if not split:b+=line(310,y+80,110,y+80,True)+text(125,y+103,'nearby return',13)
  else:b+=line(210,y+10,210,y+95)+line(220,y+10,220,y+95)+f'<path d="M310 {y+80} L310 {y+120} L110 {y+120} L110 {y+80}" stroke-dasharray="5 4"/>'+text(125,y+145,'return detours around slot',13)
 b+=text(15,425,'Section: signal F.Cu / same GND B.Cu',17)+line(35,475,300,475)+line(330,475,350,475)+text(45,460,'F.Cu signal / separate GND pad')+box(35,490,350,65,'FR4 1.6mm teaching')+line(35,575,385,575)+text(45,604,'B.Cu reference; no slot in candidate')+line(340,475,340,575)+dot(340,575)+text(350,530,'via',12)
 b+=text(15,642,'Via shown is GND stitching, not signal short')+text(15,670,'2/20nH are assumed loop models')+text(15,698,'10kHz baseband example /100MHz edge model')
 # Avoid visually shorting signal to ground: GND stitching begins beside trace.
 # The separate groundpad at330..350 connects via340 to B.Cu;signal endsat300.
 return wrap(b,720,'Reference plane and split return contrast','Two complete source/load paths, solidforward/dashedreturn,split-reference detour. Crosssection two layer1.6mm teachingboard, separate GNDstitchingvia startsatgroundpad not signal trace; frequencybands explicit,inductances assumed not extracted.')
def decaploop():
 b=text(15,25,'Fast loop closes through external ADC',17)+text(15,55,'ADC not on-board; its loop remains unknown')+line(40,110,385,110)+text(15,95,'J3.1 sourceVDD')+cap(130,110,'')+text(40,190,'C2 100n',13)+line(130,162,130,260)+dot(130,110)+dot(130,260)+line(40,260,385,260)+text(15,290,'J3.2 / localGND via / C2 minus')
 b+=line(270,110,270,165)+box(240,165,145,55,'externalADC')+line(270,220,270,260)+text(265,150,'J2.1',12)+text(290,246,'J2.3',12)+f'<path d="M145 130 L215 130 L215 240 L145 240" stroke-dasharray="5 4"/>'+text(155,322,'fast C -> J2 ->ADC ->GND ->C')
 b+=text(15,378,'5mA x5ns /100nF =.25mV charge')+text(15,411,'ESR .05ohm gives.25mV current step')+text(15,444,'Assumed2nH x1mA/ns gives2mV')+text(15,477,'Different times: no automatic RSS or doubleL')+text(15,535,'Later source replenishes charge via J3')+text(15,566,'No real VDD trace / no chosen ADC model')
 return wrap(b,590,'Actual interface decoupling loop','C2 bothterminals to VDD/reference, J3source and J2externalADC power/return pins give closed load loop;dashedannotation only. External device and cable geometry not characterized; charge/ESR/L illustrative.')
def placement():
 b=text(15,25,'Function regions on same GND, not islands',17)+box(25,80,375,245)+box(45,125,70,75,'J1')+box(130,125,100,75,'R1/C1/R2')+box(290,125,90,75,'J2ADC')+line(115,160,130,160)+line(230,160,290,160)+text(160,105,'sensitiveOUT',13)+box(90,250,230,55,'J3 supply /C2C3')
 b+=text(15,367,'Counterexample: added clock crosses OUT',17)+line(30,420,390,420)+text(25,402,'external fastclock',13)+line(210,420,210,448)+line(198,448,222,448)+line(198,456,222,456)+line(210,456,210,485)+text(232,457,'Cx=1pF',13)+line(90,485,335,485)+text(90,515,'OUT + C1=1u to reference')
 b+=text(15,555,'3.3V edge ->3.3pC ->approx3.3uV')+text(15,587,'Assumption, not extraction or measured noise')+text(15,619,'No switcher/clock on original passiveboard')
 return wrap(b,645,'Placement and explicit coupling counterexample','Functionzones over commonreference, noAGND/DGNDsplit; hypotheticalnewclock toOUTviaCx labelled. Original board contains noclock/switcher/ADC; coupling assumptionsdo not constitute physicalextraction.')
def flow():
 b=text(15,25,'Same version: project -> reviewed package',17)
 rows=[('1 schematic/pinmap','symbols,pins,rails,externalcontract'),('2 footprint/BOM','actual MPN/drawing/ratings pending'),('3 PCB/rules/fill','ground zone fill + sourceparity'),('4 actualERC/DRC','not_run;CPUgeometry is different'),('5 Gerber/drill/BOM','not generated;layers+units+origin'),('6 independentviewer','not_run;holes/mask/outline/pin1'),('7 assemble/test','no sameboardphoto or live results')]
 for j,(a,c) in enumerate(rows):y=75+j*78;b+=box(35,y,350,40,a)+text(40,y+63,c,13)
 b+=text(15,660,'Do not send candidate as qualified fab package')
 return wrap(b,685,'Manufacturing evidence pipeline','Versioned nativeCAD inputs and exactreview boundaries throughactualsoftwareERC/DRC/fill/export,manufacturingviewer,assemblyandtest. Tool outputphotos not fabricated;CPU source candidate only.')
def debug():
 b=text(15,25,'Before power: inspect, verify pins and reference',17)+text(15,55,'0..3.3V isolated source;5mA initial limit plan')
 rows=[('VDD wrong?','source/limit ->disconnectADC ->J3/C2C3'),('IN wrong?','source/cable/J1 pin / TP4 reference'),('OUT DC wrong?','R1/R2 /loading /solder /instrument'),('OUT transient wrong?','C1effective /sourceR /initial /probe'),('volts okay, code wrong?','externalADCref /timing /format /valid')]
 for j,(a,c) in enumerate(rows):y=90+j*95;b+=box(30,y,365,40,a)+text(35,y+65,c,13)
 b+=text(15,598,'Sustainedunexpectedcurrent ->stop/poweroff')+text(15,629,'TP4 local reference; scopeground may be PE')+text(15,660,'Never remove protectiveearth to float a scope')
 return wrap(b,685,'Bounded bringup fault tree','Safe lowenergy passiveboard plan with TP localreference and explicitbranches/failurestop. No measuredreadings;realinstrumentground/ratings/manual stillneeded. Scopeearthnotremoved.')
def generate(output):
 out=Path(output);out.mkdir(parents=True,exist_ok=True);old={k:os.environ.get(k) for k in ['MPLCONFIGDIR','XDG_CACHE_HOME']};os.environ['MPLCONFIGDIR']=str(out/'.mpl');os.environ['XDG_CACHE_HOME']=str(out/'.xdg')
 try:
  import matplotlib as mpl
  from matplotlib.figure import Figure
  import cairosvg
  board=json.loads(Path(__file__).with_name('board.json').read_text())
  with mpl.rc_context({'font.family':'DejaVu Sans','font.size':13,'svg.fonttype':'none','svg.hashsalt':'pcb1'}):
   ims={'rc-board-schematic':schematic(),'board-top':boardtop(board),'pin-map':pinmap(),'return-stack':returns(),'decap-loop':decaploop(),'placement':placement(),'release-flow':flow(),'debug-tree':debug()}
   f=Figure(figsize=(4.25,7),dpi=100);a=f.subplots(2,1);f.subplots_adjust(left=.24,right=.95,top=.93,bottom=.12,hspace=.65)
   ts=[i*.00005 for i in range(101)];a[0].plot([x*1000 for x in ts],[m.rc(x)['voltage_V'] for x in ts],color='black');a[0].axhline(10/11,ls='--',color='black');a[0].set(xlabel='t / ms',ylabel='OUT / V',title='R1k/C1u/RL10k; v0=.4V')
   fs=[10**(2+i*7/140) for i in range(141)];a[1].loglog(fs,[m.decap(x)['magnitude_ohm'] for x in fs],color='black');a[1].set(xlabel='f / Hz',ylabel='abs(Z) / ohm',title='C100n ESR.05 ESL2nH assumed')
   p=out/'rc-and-impedance.svg';f.savefig(p,metadata={'Date':None},facecolor='white');s=p.read_text();i=s.index('>',s.index('<svg '))+1;ims['rc-and-impedance']=s[:i]+'<title>Loaded RC and assumed decap impedance</title><desc>SameRC initial.4 response and separate assumedC100n/ESR.05/ESL2n frequencymodel; neithermeasurement nor physicalextraction.</desc>'+s[i:]
   for name,s in ims.items():
    (out/(name+'.svg')).write_text(s)
    for w in [360,425]:cairosvg.svg2png(bytestring=s.encode(),write_to=str(out/f'{name}-{w}.png'),output_width=w)
   (out/'figure-data.json').write_text(json.dumps({'board_id':board['id'],'revision':board['revision'],'t_s':ts,'v_V':[m.rc(x)['voltage_V'] for x in ts],'f_Hz':fs,'Zmag_ohm':[m.decap(x)['magnitude_ohm'] for x in fs],'scope':'originalteachingvectors andmodelcurves;noCADsoftware/photographs/measurements'},indent=2,allow_nan=False)+'\n')
 finally:
  for k,v in old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);generate(p.parse_args(argv).output)
if __name__=='__main__':main()
