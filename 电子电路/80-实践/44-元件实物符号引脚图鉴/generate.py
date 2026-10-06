"""Editable photo/symbol atlas. Import is inert; explicit new external --output required."""
from pathlib import Path
import json,hashlib,html,shutil

def catalog():
 root=Path(__file__).resolve().parent/'sourceassets'
 rows=json.loads((root/'catalog.json').read_text())
 if len(rows)!=7 or {r['family'] for r in rows}!={'R','C','L','D','MOS','BJT','OP'}:raise ValueError('seven unique families required')
 for r in rows:
  p=root/r['file']
  if p.parent!=root or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('source photo hash mismatch')
 return rows

def symbol(kind):
 # All coordinates are schematic-only. Numeric pin labels refer only to named reference model.
 line=lambda x,y,a,b:f'<path d="M{x} {y}L{a} {b}"/>'
 tx=lambda x,y,t:f'<text x="{x}" y="{y}" fill="#152333" stroke="none" font-size="17">{html.escape(t)}</text>'
 s=''
 if kind in ('R','C','L','D'):
  s=line(60,405,155,405)+line(270,405,365,405)+tx(65,385,'a' if kind!='D' else 'A')+tx(350,385,'b' if kind!='D' else 'K')
  if kind=='R':s+='<rect x="155" y="388" width="115" height="34"/>'
  if kind=='C':s+=line(155,405,201,405)+line(201,380,201,430)+line(220,380,220,430)+line(220,405,270,405)
  if kind=='L':s+='<path d="M155 405 c0 -30 28 -30 28 0 c0 -30 28 -30 28 0 c0 -30 28 -30 28 0 c0 -30 31 -30 31 0"/>'
  if kind=='D':s+='<path d="M155 405L185 405L185 380L230 405L185 430L185 405 M230 380L230 430 M230 405L270 405"/>'
 if kind=='BJT':
  s=line(65,405,170,405)+line(170,372,170,438)+line(170,387,235,357)+line(235,357,235,340)+line(170,424,235,457)+line(235,457,235,470)+'<path d="M205 441L218 443L210 433Z" fill="#152333"/>'+tx(65,385,'B(2)')+tx(240,348,'C(1)')+tx(240,477,'E(3)')
 if kind=='MOS':
  s=line(65,405,160,405)+line(160,370,160,440)+line(183,370,183,388)+line(183,398,183,412)+line(183,422,183,440)+line(183,377,240,377)+line(240,377,240,340)+line(183,433,240,433)+line(240,433,240,470)+tx(65,385,'G')+tx(245,348,'D / tab')+tx(245,477,'S')+tx(275,418,'NMOS')
 if kind=='OP':
  s='<path d="M155 355L155 465L260 410Z"/>'+line(65,385,155,385)+line(65,435,155,435)+line(260,410,365,410)+line(195,376,195,340)+line(195,444,195,480)+tx(125,382,'-')+tx(125,441,'+')+tx(65,373,'2')+tx(65,463,'3')+tx(355,396,'1')+tx(201,343,'8 V+')+tx(200,484,'4 V-')
 return '<g transform="translate(0 20)" stroke="#152333" stroke-width="2.5" fill="none">'+s+'</g>'

def generate(output):
 out=Path(output).expanduser().resolve();here=Path(__file__).resolve().parents[3];main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
 if out.exists() or out==here or here in out.parents or out==main or main in out.parents:raise ValueError('new output outside publication and main required')
 rows=catalog();import cairosvg
 out.mkdir(parents=True);(out/'sourceassets').mkdir();(out/'assets').mkdir()
 for r in rows:
  shutil.copy2(Path(__file__).parent/'sourceassets'/r['file'],out/'sourceassets'/r['file'])
  photo_width=180 if r['family']=='C' else 390
  texts=[r['title'],*r['pins']]
  body='<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="450" height="770" viewBox="0 0 450 770"><rect width="450" height="770" fill="white"/>'
  body+=f'<text x="20" y="28" font-size="21" font-family="sans-serif">{r["family"]}: photo / symbol / reference</text>'
  body+=f'<image x="30" y="45" width="{photo_width}" height="270" preserveAspectRatio="xMidYMid meet" xlink:href="../sourceassets/{r["file"]}"/>'
  if r['family']=='C':
   body+=f'<svg x="235" y="65" width="185" height="220" viewBox="300 300 400 600"><image width="904" height="2259" xlink:href="../sourceassets/{r["file"]}"/></svg><text x="235" y="307" font-size="15">224: photo detail</text>'
  if r['family']=='D':
   body+=f'<svg x="100" y="215" width="235" height="85" viewBox="400 78 110 60"><image width="912" height="373" xlink:href="../sourceassets/{r["file"]}"/></svg><text x="100" y="314" font-size="14">Source photo cathode-band detail</text>'
  body+='<text x="20" y="335" font-size="16">Photo positions are not certified pin numbers</text>'+symbol(r['symbol'])
  for n,t in enumerate(texts):body+=f'<text x="20" y="{535+28*n}" font-family="sans-serif" font-size="16">{html.escape(t)}</text>'
  body+=f'<text x="20" y="690" font-family="sans-serif" font-size="15">Photo: {html.escape(r["author"])}</text><text x="20" y="716" font-size="15">{r["license"]}; resized + original annotations</text><text x="20" y="743" font-size="15">Full source/license links: SOURCES.md</text></svg>'
  p=out/'assets'/(r['family'].lower()+'.svg');p.write_text(body)
  for w in (360,425):cairosvg.svg2png(url=str(p),write_to=str(p.with_name(p.stem+f'-{w}.png')),output_width=w,unsafe=True)
 (out/'assets/photo-hashes.json').write_text(json.dumps({r['file']:r['sha256'] for r in rows},indent=2,sort_keys=True)+'\n')
 return out

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();generate(a.output)
