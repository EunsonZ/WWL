"""Render results.json using standard-library SVG; no plotting dependency."""
from pathlib import Path
from html import escape
import json
import math

COLORS=['#1565c0','#b23c17','#168045']
class Figure:
    def __init__(self,title,width=1100,height=650):
        self.w=width;self.h=height
        self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fff"/>',
                '<style>text{font:15px sans-serif;fill:#1f2937} .small{font-size:12px} .title{font-size:22px;font-weight:600}</style>']
        self.text(28,32,title,'title')
    def text(self,x,y,t,cls=''):
        self.s.append(f'<text x="{x}" y="{y}" class="{cls}">{escape(t)}</text>')
    def panel(self,x,y,w,h,xlim,ylim,xlabel,ylabel,title):
        self.text(x,y-18,title)
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fafafa" stroke="#9ca3af"/>')
        for i in range(5):
            px=x+i*w/4;py=y+h-i*h/4
            self.s.append(f'<path d="M {px} {y} V {y+h} M {x} {py} H {x+w}" stroke="#e5e7eb"/>')
            self.text(px-15,y+h+20,f'{xlim[0]+i*(xlim[1]-xlim[0])/4:.3g}','small')
            self.text(x-52,py+4,f'{ylim[0]+i*(ylim[1]-ylim[0])/4:.3g}','small')
        self.text(x+w/2-50,y+h+44,xlabel);self.text(x,y-42,ylabel,'small')
        def point(a,b): return (x+(a-xlim[0])*w/(xlim[1]-xlim[0]),y+h-(b-ylim[0])*h/(ylim[1]-ylim[0]))
        return point
    def line(self,point,xy,color,dashed=False):
        coords=' '.join(f'{a:.3f},{b:.3f}' for a,b in [point(x,y) for x,y in xy])
        self.s.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="6 4"' if dashed else '')+'/>')
    def save(self,name):
        self.s.append('</svg>');Path('assets',name).write_text('\n'.join(self.s)+'\n')

def build():
    d=json.loads(Path('results.json').read_text());s=d['summary']
    f=Figure('Same contact card: position, band edges, electric field and space charge',1100,920)
    p1=f.panel(90,110,420,240,(-40,400),(-1.3,.75),'x (nm)','E (eV), Ec(bulk)=0','Ec solid / Ev dashed; metal EF at x < 0')
    p2=f.panel(650,110,380,240,(0,400),(-5,0),'x (nm)','E (10^6 V/m)','Field points toward the metal')
    p3=f.panel(90,570,420,220,(0,400),(-.7,0),'x (nm)','electrostatic phi (V)','Ec (eV) = -phi (V), numerical equality')
    p4=f.panel(650,570,380,220,(0,400),(0,1.8),'x (nm)','rho (10^3 C/m^3)','Ionized donors in depletion approximation')
    for col,row in zip(COLORS,d['spatial']):
        pr=row['profile'];v=row['V_V'];w=row['depletion']['W_m']*1e9
        f.line(p1,[(z['x_m']*1e9,z['Ec_eV']) for z in pr],col)
        f.line(p1,[(z['x_m']*1e9,z['Ev_eV']) for z in pr],col,True)
        f.line(p1,[(-40,row['EFmetal_eV']),(0,row['EFmetal_eV'])],col)
        f.line(p2,[(z['x_m']*1e9,z['E_V_m']/1e6) for z in pr],col)
        f.line(p3,[(z['x_m']*1e9,z['phi_V']) for z in pr],col)
        f.line(p4,[(0,1.602176634),(w,1.602176634),(w,0),(400,0)],col)
    f.line(p1,[(0,-s['xi_eV']),(400,-s['xi_eV'])],'#555',True)
    f.text(90,430,'Blue: V=-0.2 V     Red: V=0 V     Green: V=+0.2 V')
    f.text(90,456,'Grey dashed: semiconductor bulk reservoir EF; not an interface distribution function.','small')
    f.text(90,482,'At x=0, Ec-EFmetal=0.600 V x q for every bias; Ec-EFbulk changes with bias.','small')
    f.text(90,890,'Single isotropic valley, MB supply, fully ionized ND=1e22 m^-3; not a silicon process model.','small')
    f.save('contact-space.svg')
    f=Figure('One Schottky card: depletion C-V and thermionic current',1100,620)
    p1=f.panel(90,110,420,300,(-.2,.2),(2.5,8.5),'junction V (V)','1/C_A^2 (10^6 m^4/F^2)','Area capacitance: inverse square is affine')
    p2=f.panel(650,110,380,300,(-.06,.06),(-1,10),'junction V (V)','J/Js (dimensionless)','Local thermionic I-V: same Js in both directions')
    f.line(p1,[(r['V_V'],1/r['C_F_m2']**2/1e6) for r in d['cv']],COLORS[0])
    f.line(p2,[(r['V_V'],r['J_A_m2']/s['Js_A_m2']) for r in d['iv'] if abs(r['V_V'])<=.0600000001],COLORS[1])
    f.text(90,480,f'Vbi={s["Vbi_V"]:.6f} V; slope = -2/(eps q ND). C_A means F/m^2, not total F.','small')
    f.text(90,507,f'Js={s["Js_A_m2"]:.6f} A/m^2; forward convention: positive current from metal into semiconductor.','small')
    f.text(90,534,'Shown V is the local contact voltage. A measured external voltage may also include I Rs.','small')
    f.text(90,561,'Reverse saturation is conditional: no tunnelling, image-force correction, interface traps or breakdown.','small')
    f.save('contact-cv-iv.svg')
    f=Figure('Contact model changes: width, quantum scale and a separate bar measurement',1100,830)
    p1=f.panel(90,110,420,240,(22,25),(0,260),'log10 ND (m^-3)','W (nm), fixed B=0.449872 V','Space-charge width decreases as ND^-1/2')
    p2=f.panel(650,110,380,240,(22,25),(0,1.4),'log10 ND (m^-3)','E00 / kBT (dimensionless)','WKB scale; not a complete tunnelling I-V')
    rows=d['fixed_bending_diagnostics']
    f.line(p1,[(math.log10(r['ND_m3']),r['W_m']*1e9) for r in rows],COLORS[0])
    f.line(p2,[(math.log10(r['ND_m3']),r['E00_over_kT']) for r in rows],COLORS[1])
    f.line(p2,[(22,1),(25,1)],'#555',True)
    f.text(90,409,'Width scan fixes band bending; it does not reuse the MB chemical potential at high doping.','small')
    f.text(90,435,'At ND=1e25 m^-3, ND/Nc=3.006: the original MB population assumption fails.','small')
    p3=f.panel(90,535,420,200,(0,4),(0,220),'bar length (um)','R (kOhm)','Separate uniform linear contacts: Rtotal = 2 Rc + Rbulk')
    b=d['bar_length_series'];slope=d['bar_recovered']['slope_ohm_m'];inter=d['bar_recovered']['intercept_ohm']
    f.line(p3,[(0,inter/1e3),(4,(inter+slope*4e-6)/1e3)],COLORS[2])
    f.line(p3,[(0,0),(4,slope*4e-6/1e3)],'#555',True)
    for r in b:
        x,y=p3(r['L_m']*1e6,r['Rtotal_ohm']/1e3);f.s.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{COLORS[2]}"/>')
    f.text(650,565,'Bar card is independent of Schottky TE card:')
    f.text(650,595,'n=1e21 m^-3, mu=0.135 m^2/(V s)','small')
    f.text(650,625,'A=Ac=1e-12 m^2; rho_c=1e-8 Ohm m^2','small')
    f.text(650,655,'Intercept=20 kOhm => each Rc=10 kOhm','small')
    f.text(650,685,'At L=1 um: G=15.0981 uS','small')
    f.text(650,715,'Slope still identifies n*mu only.','small')
    f.text(90,806,'No hardware measurement, activated implant, surface preparation or true tunnelling current is verified.','small')
    f.save('contact-width-port.svg')

if __name__=='__main__': build()
