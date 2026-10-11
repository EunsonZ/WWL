#!/usr/bin/env python3
"""Figures consume the actual solver JSON/CSV; no invented curves."""
import argparse
import csv
import html
import json
from pathlib import Path


def read_csv(p):
    with p.open() as f:
        return [{k: (v if k=='material' else float(v)) for k,v in r.items()} for r in csv.DictReader(f)]


XRANGE = (-600.0,600.0)
SUBTITLE = ""
FOOTER = ""

def text(x,y,s,size=14,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(s)}</text>'


def panel(x,y,w,h,title,yrange,label,series):
    # Plot area is inset; every curve carries its own line style/legend.
    values=[z for _,points,_,_ in series for _,z in points]
    span=max(max(values)-min(values),1e-12)
    yrange=(min(yrange[0],min(values)-.04*span),max(yrange[1],max(values)+.04*span))
    left,top,width,height = x+77,y+44,w-104,h-97
    def px(z): return left+(z-XRANGE[0])/(XRANGE[1]-XRANGE[0])*width
    def py(z): return top+(yrange[1]-z)/(yrange[1]-yrange[0])*height
    chunks=[text(x+20,y+23,title,17),f'<rect x="{left}" y="{top}" width="{width/2}" height="{height}" fill="#eef5fd"/>',
            f'<rect x="{left+width/2}" y="{top}" width="{width/2}" height="{height}" fill="#faf2e8"/>']
    for i in range(5):
        v=yrange[0]+(yrange[1]-yrange[0])*i/4; yy=py(v)
        chunks += [f'<path d="M{left},{yy}h{width}" stroke="#ccd3da"/>',text(left-8,yy+5,f'{v:.3g}',12,'end')]
    for v in (XRANGE[0],XRANGE[0]/2,0,XRANGE[1]/2,XRANGE[1]): chunks += [text(px(v),top+height+21,f'{v:g}',12,'middle')]
    chunks += [f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="none" stroke="#56606b"/>',
               f'<path d="M{px(0)},{top}v{height}" stroke="#58606a" stroke-dasharray="3 3"/>',
               text(px(XRANGE[0]*.7),top-6,'A: p',12),text(px(XRANGE[1]*.7),top-6,'B: n',12),
               text(left+width/2,top+height+43,'x (nm), interface at 0',12,'middle'),
               f'<text transform="translate({x+17},{top+height/2}) rotate(-90)" font-size="12" text-anchor="middle">{html.escape(label)}</text>']
    for name,pts,color,dash in series:
        poly=' '.join(f'{px(xx):.2f},{py(yy):.2f}' for xx,yy in pts)
        chunks.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
    # Legends outside data area; long labels wrap as separate small lines.
    for i,(name,_,color,dash) in enumerate(series):
        lx=left+8+(i%2)*width/2; ly=top+height+60+(i//2)*18
        chunks += [f'<path d="M{lx},{ly-4}h22" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>',text(lx+28,ly,name,11)]
    return '\n'.join(chunks)


def save(path,title,desc,panels):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="980" viewBox="0 0 1100 980"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="1100" height="980" fill="white"/><g font-family="Arial, sans-serif" fill="#172332">'
    svg+=text(28,32,title,22)+text(28,56,SUBTITLE,14)
    svg+='\n'.join(panels)
    svg+=text(28,956,FOOTER,14)+'</g></svg>\n'
    path.write_text(svg)


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=Path(__file__).with_name('results')); args=p.parse_args()
    out=args.results; report=json.loads((out/'results.json').read_text())
    global XRANGE,SUBTITLE,FOOTER
    inp=report['input']; fine=report['cases']['positive']['meshes'][-1]
    length=inp['half_length_m']*1e9; XRANGE=(-length,length)
    SUBTITLE=f"Synthetic A/B, {inp['temperature_K']:g} K, equilibrium MB; same {fine['h_m']*1e9:g} nm data"
    FOOTER=f"E_F = {inp['fermi_eV']:g} eV. Sheet charge is C/m² at x=0; it is not plotted as volume rho."
    profiles={k:read_csv(out/(k+'-profile.csv')) for k in ('zero','positive','negative')}
    edges={k:read_csv(out/(k+'-edges.csv')) for k in profiles}
    colors={'zero':'#1768ac','positive':'#ae3f12','negative':'#674fb3'}
    dash={'zero':'','positive':'8 3','negative':'2 3'}
    names={k:f"sheet = {report['cases'][k]['meshes'][-1]['sigma_C_m-2']:+.4g} C/m²" for k in ('zero','positive','negative')}
    def curves(key,scale=1,edge=False):
        rows=edges if edge else profiles; xpos='x_mid_m' if edge else 'x_m'
        result=[]
        for k in profiles:
            pts=[(r[xpos]*1e9,r[key]*scale) for r in rows[k]]
            if edge:
                fine=report['cases'][k]['meshes'][-1]
                const=report['constants']['epsilon0_F_m-1']
                jumps=[fine['D0minus_C_m-2'],fine['D0plus_C_m-2']]
                if key=='E_V_m-1':
                    jumps=[jumps[0]/(const*report['input']['materials']['A']['epsilon_r']),jumps[1]/(const*report['input']['materials']['B']['epsilon_r'])]
                pts=[p for p in pts if p[0]<0]+[(0,z*scale) for z in jumps]+[p for p in pts if p[0]>0]
            result.append((names[k],pts,colors[k],dash[k]))
        return result
    positive=profiles['positive']; band=[]
    for key,color,d in [('Ec_eV','#1768ac',''),('Ev_eV','#ae3f12','6 3')]:
        band.append((key.split('_')[0]+' (+sheet)',[(r['x_m']*1e9,r[key]) for r in positive],color,d))
    band.append(('E_F',[(XRANGE[0],inp['fermi_eV']),(XRANGE[1],inp['fermi_eV'])],'#4c5864','3 3'))
    save(out/'space.svg','One potential, two band edges, one charge ledger',
         'Four panels share the finite input domain in nm. Potential is continuous; conduction/valence steps use material offsets. D and E use mid-edge values and corrected one-sided interface limits; vertical jumps mark x=0.',
         [panel(0,76,550,390,'Potential responds to sheet',(-.4,.55),'phi (V)',curves('phi_V')),
          panel(550,76,550,390,'Material steps are not phi jumps',(-1.7,.4),'energy (eV)',band),
          panel(0,498,550,390,'Displacement jump + bulk charge',(-.45,.03),'D (10^-3 C/m²)',curves('D_C_m-2',1e3,True)),
          panel(550,498,550,390,'E also depends on each epsilon',(-4.8,.2),'E (10^6 V/m)',curves('E_V_m-1',1e-6,True))])
    density=[]
    import math
    for key,color,d in [('n_m-3','#1768ac',''),('p_m-3','#ae3f12','6 3')]:
        density.append((key[0]+' (+sheet)',[(r['x_m']*1e9,math.log10(r[key])) for r in positive],color,d))
    doping=read_csv(out/'doping-profile.csv');bc=read_csv(out/'boundary-profile.csv')
    changes=[('base +sheet',[(r['x_m']*1e9,r['phi_V']) for r in positive],'#1768ac',''),
             ('ND_B doubled',[(r['x_m']*1e9,r['phi_V']) for r in doping],'#ae3f12','8 3'),
             ('right phi +0.05 V',[(r['x_m']*1e9,r['phi_V']) for r in bc],'#674fb3','2 3')]
    # Depletion rho is a distinct approximation, not relabelled as nonlinear data.
    dep=report['cases']['positive']['depletion']; inp=report['input'];q=report['constants']['q_C']
    wa,wb=dep['wA_m']*1e9,dep['wB_m']*1e9
    ra=-q*inp['materials']['A']['NA_m-3']/1e3;rb=q*inp['materials']['B']['ND_m-3']/1e3
    approx=[(XRANGE[0],0),(-wa,0),(-wa,ra),(0,ra),(0,rb),(wb,rb),(wb,0),(XRANGE[1],0)]
    rhop=[('PB +sheet',[(r['x_m']*1e9,r['rho_C_m-3']/1e3) for r in positive],'#1768ac',''),('depletion +sheet',approx,'#ae3f12','8 3')]
    carrier_ratio=[('n/Nc +sheet',[(r['x_m']*1e9,r['n_m-3']/inp['materials'][r['material']]['Nc_m-3']*1e3) for r in positive],'#1768ac',''),
                   ('p/Nv +sheet',[(r['x_m']*1e9,r['p_m-3']/inp['materials'][r['material']]['Nv_m-3']*1e3) for r in positive],'#ae3f12','6 3')]
    save(out/'charge-and-changes.svg','Carriers set rho; changing the card requires a new solve',
         'PB and depletion volume charge are different approximations. n and p use logarithmic density; ratios expose nondegenerate condition. The right boundary change is an equilibrium electrostatic clamp with a common Fermi energy, not a biased two-reservoir device.',
         [panel(0,76,550,390,'Edges have mobile carrier tails',(-1.8,3.5),'rho (10^3 C/m³)',rhop),
          panel(550,76,550,390,'Same equilibrium Fermi energy',(0,23),'log10(density / 1 m^-3)',density),
          panel(0,498,550,390,'Doping and boundary are distinct',(-.4,.58),'phi (V)',changes),
          panel(550,498,550,390,'Check MB after solving',(0,1.1),'carrier/DOS (10^-3)',carrier_ratio)])
    print('Wrote space.svg and charge-and-changes.svg from solver output')
if __name__=='__main__':main()
