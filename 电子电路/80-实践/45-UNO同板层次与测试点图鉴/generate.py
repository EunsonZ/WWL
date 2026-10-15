"""Generate editable same-board photo/layout/net/testpoint figures; required fresh output."""
from pathlib import Path
import json,shutil,html
import models

def generate(output):
 out=Path(output).expanduser().resolve();c=Path(__file__).resolve().parents[3];m=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
 if out.exists() or out==c or c in out.parents or out==m or m in out.parents:raise ValueError('fresh output outside publication and main required')
 data=models.load();import cairosvg
 out.mkdir(parents=True);(out/'assets').mkdir();(out/'sourceassets').mkdir()
 for name in ('A000066-front.jpg','A000066-back.jpg'):shutil.copy2(Path(__file__).parent/'sourceassets'/name,out/'sourceassets'/name)
 def text(x,y,t,size=16):return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#152333">{html.escape(t)}</text>'
 def line(x,y,a,b,stroke='#152333',dash=''):return f'<path d="M{x} {y} L{a} {b}" fill="none" stroke="{stroke}" stroke-width="2" '+(f'stroke-dasharray="{dash}"' if dash else '')+'/>'
 def save(name,body,height):
  p=out/'assets'/(name+'.svg');p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="450" height="{height}" viewBox="0 0 450 {height}"><rect width="450" height="{height}" fill="white"/>'+body+'</svg>')
  for w in (360,425):cairosvg.svg2png(url=str(p),write_to=str(p.with_name(p.stem+f'-{w}.png')),output_width=w,unsafe=True)
 body=text(16,28,'UNO-TH Rev3e: actual front / back',20)
 body+='<image x="15" y="50" width="420" height="315" xlink:href="../sourceassets/A000066-front.jpg"/>'
 body+=text(20,385,'FRONT: USB left; POWER / A0 lower edge')
 body+='<image x="15" y="410" width="420" height="315" xlink:href="../sourceassets/A000066-back.jpg"/>'
 body+=text(20,745,'BACK: USB right; Rev3e text at lower right')+text(20,773,'Photos: Arduino, CC BY-SA4; resized only')+text(20,801,'Bottom view mirrors x; net identity stays')
 # Actual normalized photo positions, landmark circles; coordinates approximate image localization, not metrology.
 for x,y,t,lx in [(326,326,'A0',320),(275,326,'GND',270),(262,326,'5V',230)]:
  body+=f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="#c92919" stroke-width="2"/>'+line(x,y,lx+8,y-37,'#c92919')+f'<rect x="{lx-2}" y="{y-59}" width="{len(t)*9+4}" height="22" fill="white"/>'+text(lx,y-42,t,14)
 for x,y,t,lx in [(125,688,'A0',105),(164,688,'GND',148),(190,688,'5V',206)]:
  body+=f'<circle cx="{x}" cy="{y}" r="6" fill="none" stroke="#c92919" stroke-width="2"/>'+line(x,y,lx+8,y-37,'#c92919')+f'<rect x="{lx-2}" y="{y-59}" width="{len(t)*9+4}" height="22" fill="white"/>'+text(lx,y-42,t,14)
 save('same-board-photos',body,830)
 body=text(16,28,'CAD copper subset / same TOP coordinates',19)
 for n,layer in enumerate(('1','16')):
  base=70+365*n;scale=5.5
  def xy(x,y):return 30+float(x)*scale,base+(53.34-float(y))*scale
  body+=text(20,base-15,'Layer'+layer+(' TOP solid' if layer=='1' else ' BOTTOM dashed; viewed from TOP'))
  for w in data['outline']:
   x,y=xy(w['x1'],w['y1']);a,b=xy(w['x2'],w['y2']);body+=line(x,y,a,b,'#bbbbbb')
  for w in data['wires']:
   if w['layer']!=layer:continue
   x,y=xy(w['x1'],w['y1']);a,b=xy(w['x2'],w['y2']);body+=line(x,y,a,b,'#156ba2' if w['net']=='AD0' else '#9a9a9a','5 3' if layer=='16' else '')
  for v in data['vias']:
   x,y=xy(v['x'],v['y']);body+=f'<circle cx="{x}" cy="{y}" r="2" fill="none" stroke="#777"/>'
  for p in data['points']:
   x,y=xy(p['x_mm'],p['y_mm']);body+=f'<circle cx="{x}" cy="{y}" r="4" fill="white" stroke="#c92919"/>'
  body+=text(23,base+312,'Blue=AD0; gray=+5V/GND tracks; red=pads')
 body+=text(16,820,'Selected traces only; planes NOT filled')+text(16,848,'Curve wires shown by endpoint chords')+text(16,876,'Original Arduino EAGLE CAD: CC BY-SA4')
 save('layout-layers',body,905)
 # Enlarged actual pad coordinates along common lower edge.
 body=text(16,28,'Lower-edge detail: CAD identities (TOP)',19)
 pts=[p for p in data['points'] if p['ref'] in ('TP_5V','GND_TP','TP_A0','AD','POWER')]
 for p in pts:
  y=80+62*pts.index(p);body+=text(18,y,f'{p["ref"]}.{p["pad"]} -> {p["net"]}',18)+text(18,y+25,f'x={p["x_mm"]:.2f}, y={p["y_mm"]:.2f} mm',16)
 body+=text(16,535,'TP_A0 is CAD testpad near A0 header;')+text(16,563,'Use labeled header A0 when pad is tiny.')+text(16,591,'No claim that a photo exposes every TP')+text(16,619,'Coordinate origin / units from EAGLE file')
 save('testpoint-detail',body,650)
 # Original connectivity subset, translated from exact source net identities.
 body=text(16,28,'Same schematic / board nets: local subset',18)
 for n,(net,left,right,tp) in enumerate([('AD0','AD.1 / A0','ZU4.23 / PC0','TP_A0.X'),('+5V','POWER.5 / 5V','supply net','TP_5V.X'),('GND','POWER.6,7','ZU4.8,22','GND_TP.X')]):
  y=100+140*n;body+=line(40,y,400,y)+line(220,y,220,y+50)+f'<circle cx="220" cy="{y+50}" r="6" fill="white" stroke="#152333" stroke-width="2"/>'+text(20,y-25,left)+text(255,y+30,right)+text(228,y+70,tp)+text(160,y-25,net)
 body+=text(16,545,'Lines denote actual same-net identities;')+text(16,573,'not complete schematic or direct DC path')+text(16,601,'Read SOURCE Arduino Rev3e sheet for devices')
 save('schematic-net-subset',body,630)
 # Instrument plan on actual named header nets; probe model original explicit loaded port.
 body=text(16,28,'Instrument PLAN: A0 relative to GND',20)
 body+=text(18,64,'Disconnect supply before locating terminals')
 body+=line(55,135,250,135)+line(55,365,250,365)+line(250,135,250,200)+'<rect x="220" y="200" width="60" height="65" fill="white" stroke="#152333" stroke-width="2"/>'+text(225,235,'Rin',16)+line(250,265,250,365)+line(330,135,330,222)+line(250,135,330,135)+line(316,222,344,222)+line(316,236,344,236)+line(330,236,330,365)+line(250,365,330,365)
 body+=text(18,119,'A0 / AD.1 / TP_A0')+text(18,400,'GND / POWER.6 / GND_TP')+text(335,233,'Cin',16)+text(70,170,'probe TIP -> A0')+text(65,343,'probe RETURN -> GND')
 body+=line(165,365,165,435)+line(145,435,185,435)+line(151,444,179,444)+line(157,453,173,453)+text(205,448,'PE if scope uses grounded return',14)
 body+=text(18,500,'Confirm instrument manual + compatible potentials')+text(18,528,'Never remove protective earth to float scope')+text(18,556,'Low-energy condition: isolated low-voltage source')+text(18,584,'No barrel/VIN, shield, high energy or mains loads')+text(18,612,'Supply current limit; no dual-supply backfeed')+text(18,640,'Expected nodes only; zero real measurements')
 save('instrument-connection-plan',body,675)
 (out/'assets/layout-net-data.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n');return out
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();generate(a.output)
