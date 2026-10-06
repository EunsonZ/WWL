"""Deterministic original SVGs; explicit fresh output, no import-time work."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
from models import cases, waveform


def text(x, y, value, size=24, anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def line(x1,y1,x2,y2,color='#222',dash='',arrow=False):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="3" '
            f'stroke-dasharray="{dash}"'+(' marker-end="url(#tip)"' if arrow else '')+'/>' )


def svg(height, parts):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="680" height="'+str(height)+'" viewBox="0 0 680 '+str(height)+'">'
            '<rect width="680" height="100%" fill="white"/><defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#222"/></marker></defs>'
            '<g font-family="sans-serif" fill="#111">'+''.join(parts)+'</g></svg>')


def topology():
    a=[text(30,40,'Which nodes carry the same series current?'),
       text(30,80,'Fixed RLC: 10 V RMS; omega = 1000 rad/s'),
       line(130,160,210,160), line(290,160,340,160),line(420,160,490,160),
       line(510,160,580,160),line(580,160,580,400),line(580,400,130,400),
       line(130,400,130,330),line(130,230,130,160),
       '<circle cx="130" cy="280" r="50" fill="none" stroke="#222" stroke-width="3"/>',
       text(130,260,'+',anchor='middle'),text(130,310,'-',anchor='middle'),
       '<rect x="210" y="140" width="80" height="40" fill="none" stroke="#222" stroke-width="3"/>',
       '<path d="M340 160 Q350 125 360 160 Q370 125 380 160 Q390 125 400 160 Q410 125 420 160" fill="none" stroke="#222" stroke-width="3"/>',
       line(490,135,490,185),line(510,135,510,185),
       text(180,235,'R=10 ohm'),text(340,270,'L=10 mH'),text(445,320,'C=200 uF'),
       line(190,115,290,115,arrow=True),text(315,120,'i(t) ->'),
       text(95,155,'n1'),text(305,200,'n2'),text(440,200,'n3'),text(90,415,'0'),
       text(30,480,'vR = v(n1)-v(n2); vL = v(n2)-v(n3)'),
       text(30,525,'vC = v(n3)-v(0); v = v(n1)-v(0)'),
       text(30,570,'Current enters each positive voltage terminal.'),
       text(30,615,'KVL: vR + vL + vC = v. Same rule in RMS.'),
       text(30,660,'Ideal steady-state model, no physical assembly.')]
    for x,y in [(130,160),(320,160),(440,160),(130,400)]:
        a.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#222"/>')
    return svg(705,a)


def impedances():
    a=[text(30,40,'Why is L above and C below the real axis?'),text(30,85,'RLC: R=10 ohm; XL=+10 ohm; XC=-5 ohm')]
    ox,oy,s=140,430,24
    a += [line(70,oy,610,oy,arrow=True),line(ox,590,ox,140,arrow=True),
          text(545,470,'Re(Z)'),text(150,155,'Im(Z) [ohm]')]
    for z,label,col,ly in [(10+0j,'ZR = 10','#215b91',475),(10j,'ZL = +j10','#287c40',225),(-5j,'ZC = -j5','#965020',570),(10+5j,'Z = 10+j5','#222',270)]:
        x,y=ox+s*z.real,oy-s*z.imag
        a += [line(ox,oy,x,y,col,arrow=True),text(x+15,ly,label)]
    a += [text(30,635,'e^(+j omega t), passive reference, omega > 0.'),
          text(30,680,'ZL = j omega L; ZC = 1/(j omega C).')]
    return svg(720,a)


def triangles():
    a=[text(30,40,'Which sign belongs to reactive power?')]
    for k,c in enumerate(cases()[1:]):
        top=85+360*k; ox,oy,s=140,top+150,24
        p,q=c['P_W'],c['Q_var'];x,y=ox+s*p,oy-s*q
        a += [text(30,top,c['name']+f': P={p:g} W; Q={q:g} var; |S|={c["apparent_VA"]:.3f} VA'),
              line(80,oy,580,oy,arrow=True),line(ox,top+290,ox,top+25,arrow=True),
              text(535,oy+35,'P [W]'),text(150,top+25,'Q [var]'),
              line(ox,oy,x,oy,'#215b91',arrow=True),line(x,oy,x,y,'#965020',dash='8 5',arrow=True),
              line(ox,oy,x,y,arrow=True),text(x+14,y+12,'S'),
              text(220,top+315,'S = V I*; |S|^2 = P^2 + Q^2')]
    return svg(1195,a)


def power_waves():
    a=[text(30,40,'Can p(t) be negative while its mean is positive?')]
    for k,c in enumerate(cases()[1:]):
        rows=waveform(c,512);top=95+k*360; left,right=100,620
        # All three panels deliberately share the same W scale and time range.
        y=lambda value:top+240-value*10
        xmax=2*math.pi/c['omega_rad_s'];xs=lambda value:left+(right-left)*value/xmax
        a += [text(30,top,c['name']+f': mean = {c["P_W"]:g} W'),
              line(left,y(-5),left,y(20),arrow=True),line(left,y(0),right,y(0),arrow=True),
              text(35,y(20)+8,'20'),text(55,y(0)+8,'0'),text(35,y(-5)+8,'-5'),text(105,top+35,'p [W]'),
              text(left,top+330,'0'),text(right,top+330,f'{xmax*1000:.2f} ms',anchor='end'),
              line(left,y(c['P_W']),right,y(c['P_W']),'#215b91',dash='9 6'),
              '<polyline fill="none" stroke="#222" stroke-width="3" points="'+
              ' '.join(f'{xs(r["t_s"]):.3f},{y(r["p_W"]):.3f}' for r in rows)+'"/>']
    a += [text(30,1220,'Dashed: whole-period mean. Solid: v(t) i(t).'),
          text(30,1265,'Only P is net dissipated power; Q is not heat.')]
    return svg(1305,a)


def generate(output):
    if output is None: raise ValueError('an explicit fresh output directory is required')
    target=Path(output)
    if target.exists(): raise FileExistsError('output directory must be new')
    import cairosvg
    target.mkdir(parents=True)
    diagrams={'01-topology':topology(),'02-impedances':impedances(),
              '03-power-triangles':triangles(),'04-period-power':power_waves()}
    for name,source in diagrams.items():
        (target/(name+'.svg')).write_text(source,encoding='utf-8')
        for width in (360,425):
            cairosvg.svg2png(bytestring=source.encode(),write_to=str(target/f'{name}-{width}.png'),output_width=width)
    serial=lambda v:[v.real,v.imag] if isinstance(v,complex) else v
    (target/'cases.json').write_text(json.dumps([{key:serial(v) for key,v in c.items()} for c in cases()],indent=2)+'\n')
    with (target/'waveforms.csv').open('w',newline='') as out:
        rows=waveform(cases()[-1]);writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return target


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv);generate(args.output)


if __name__=='__main__': main()
