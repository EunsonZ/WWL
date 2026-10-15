"""Read-only EAGLE XML coordinates and net identities. No import work."""
from pathlib import Path
import xml.etree.ElementTree as ET
import math,numbers

def coordinate(x,y,ex,ey,rot='R0'):
 for v in (x,y,ex,ey):
  if isinstance(v,bool) or not isinstance(v,numbers.Real):raise ValueError('real finite mm coordinates required')
  try:q=float(v)
  except (OverflowError,ValueError,TypeError) as e:raise ValueError('finite coordinates required') from e
  if not math.isfinite(q) or abs(q)>1000:raise ValueError('teaching coordinate bound1000mm')
 if not isinstance(rot,str) or not rot.startswith('R'):raise ValueError('only unmirrored R rotations in this selected board subset')
 try:a=float(rot[1:])
 except (ValueError,OverflowError) as e:raise ValueError('rotation required') from e
 if a not in (0,90,180,270):raise ValueError('orthogonal rotations required')
 c,s=round(math.cos(math.radians(a))),round(math.sin(math.radians(a)))
 return float(ex)+c*float(x)-s*float(y),float(ey)+s*float(x)+c*float(y)

def load(root=None):
 root=Path(root) if root is not None else Path(__file__).parent/'sourceassets'
 brd=ET.parse(root/'UNO-TH_Rev3e.brd').getroot();sch=ET.parse(root/'UNO-TH_Rev3e.sch').getroot()
 packages={(l.get('name'),p.get('name')):p for l in brd.findall('.//board/libraries/library') for p in l.findall('packages/package')}
 elements={e.get('name'):e for e in brd.findall('.//board/elements/element')}
 signals={s.get('name'):s for s in brd.findall('.//board/signals/signal')}
 refs={(c.get('element'),c.get('pad')):net for net,s in signals.items() for c in s.findall('contactref')}
 targets=[('TP_A0','X'),('AD','1'),('ZU4','23'),('TP_5V','X'),('POWER','5'),('GND_TP','X'),('POWER','6'),('POWER','7')]
 points=[]
 for ref,pad in targets:
  e=elements[ref];p=packages[e.get('library'),e.get('package')];pin=next(q for q in p if q.tag in ('pad','smd') and q.get('name')==pad)
  x,y=coordinate(float(pin.get('x')),float(pin.get('y')),float(e.get('x')),float(e.get('y')),e.get('rot','R0'))
  points.append(dict(ref=ref,pad=pad,net=refs[ref,pad],x_mm=x,y_mm=y))
 schrefs={}
 for n in sch.findall('.//sheet/nets/net'):
  for p in n.findall('.//pinref'):schrefs[p.get('part'),p.get('pin')]=n.get('name')
 for ref,pin,expect in [('TP_A0','TESTP','AD0'),('AD','1','AD0'),('ZU4','(ADC0)PC0)','AD0'),('TP_5V','TESTP','+5V'),('POWER','5','+5V'),('GND_TP','TESTP','GND'),('POWER','6','GND')]:
  if schrefs.get((ref,pin))!=expect:raise ValueError('schematic identity mismatch')
 for ref,pad,expect in [('TP_A0','X','AD0'),('AD','1','AD0'),('ZU4','23','AD0'),('TP_5V','X','+5V'),('POWER','5','+5V'),('GND_TP','X','GND'),('POWER','6','GND')]:
  if refs[ref,pad]!=expect:raise ValueError('board identity mismatch')
 wires=[]
 for net in ('AD0','+5V','GND'):
  for w in signals[net].findall('wire'):
   if w.get('layer') in ('1','16'):wires.append(dict(net=net,**w.attrib))
 vias=[dict(net=net,**v.attrib) for net in ('AD0','+5V','GND') for v in signals[net].findall('via')]
 outline=[w.attrib for w in brd.findall('.//board/plain/wire') if w.get('layer')=='20']
 return dict(board='UNO-TH Rev3e',units='mm',points=points,wires=wires,vias=vias,outline=outline,schematic_refs={'AD0':['AD.1','ZU4.23','TP_A0.X'],'+5V':['POWER.5','TP_5V.X'],'GND':['POWER.6','POWER.7','GND_TP.X']},not_claimed=['fabrication','copper polygon fill','physical continuity','measured voltage'])
