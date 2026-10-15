#!/usr/bin/env python3
"""Stdlib SVG renderer: plots only current JSON/CSV, units and domains explicit."""
import argparse
import csv
import html
import json
from pathlib import Path


def csv_rows(path):
    with path.open() as f:
        return [{k:v if k=='material' else float(v) for k,v in r.items()} for r in csv.DictReader(f)]


def text(x,y,s,size=13,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(s)}</text>'


def panel(x,y,title,xlabel,ylabel,series,region=False,yrange=None):
    left,top,w,h=x+80,y+52,435,258
    xs=[u for _,p,_,_ in series for u,v in p];ys=[v for _,p,_,_ in series for u,v in p]
    xmin,xmax=min(xs),max(xs);lo,hi=min(ys),max(ys)
    if xmin==xmax:
        pad=max(abs(xmin),1.0)*.1;xmin-=pad;xmax+=pad
    span=max(hi-lo,1e-12);ymin,ymax=yrange or (lo-.08*span,hi+.08*span)
    px=lambda v:left+(v-xmin)/(xmax-xmin)*w
    py=lambda v:top+(ymax-v)/(ymax-ymin)*h
    chunks=[text(x+18,y+22,title,17)]
    if region:
        chunks += [f'<rect x="{left}" y="{top}" width="{w/2}" height="{h}" fill="#eff6fc"/>',
                   f'<rect x="{left+w/2}" y="{top}" width="{w/2}" height="{h}" fill="#fcf2e9"/>',
                   text(left+80,top-8,'A: p',12),text(left+w-100,top-8,'B: n',12),
                   f'<path d="M{px(0)},{top}v{h}" stroke="#6b7280" stroke-dasharray="3 3"/>']
    for k in range(5):
        xv=xmin+(xmax-xmin)*k/4;yv=ymin+(ymax-ymin)*k/4
        chunks += [f'<path d="M{left},{py(yv)}h{w}" stroke="#d3d8de"/>',
                   text(left-8,py(yv)+4,f'{yv:.3g}',12,'end'),text(px(xv),top+h+21,f'{xv:.3g}',12,'middle')]
    chunks += [f'<rect x="{left}" y="{top}" width="{w}" height="{h}" fill="none" stroke="#57616c"/>',
               text(left+w/2,top+h+43,xlabel,12,'middle'),
               f'<text transform="translate({x+18},{top+h/2}) rotate(-90)" font-size="12" text-anchor="middle">{html.escape(ylabel)}</text>']
    for name,pts,color,style in series:
        if style=='points':
            chunks.extend(f'<circle cx="{px(a)}" cy="{py(b)}" r="4" fill="{color}"/>' for a,b in pts)
        else:
            poly=' '.join(f'{px(a):.3f},{py(b):.3f}' for a,b in pts)
            chunks.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{style}"/>')
    for k,(name,pts,color,style) in enumerate(series):
        ly=top+h+67+k*18
        chunks += [f'<path d="M{left+5},{ly-4}h24" stroke="{color}" stroke-width="2"/>',text(left+36,ly,name,11)]
    return '\n'.join(chunks)


def save(path,title,subtitle,description,panels,footer):
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1080" viewBox="0 0 1100 1080">'
    svg+=f'<title>{html.escape(title)}</title><desc>{html.escape(description)}</desc><rect width="1100" height="1080" fill="white"/><g font-family="Arial, sans-serif" fill="#172332">'
    svg+=text(25,32,title,22)+text(25,58,subtitle,14)+'\n'.join(panels)
    svg+=text(25,1030,footer,13)+text(25,1055,'Synthetic teaching inputs; equilibrium only. No measured Dit, biased DD or quantum confinement.',13)+'</g></svg>\n'
    path.write_text(svg)


def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=Path(__file__).with_name('results'));args=p.parse_args()
    out=args.results;report=json.loads((out/'results.json').read_text());card=report['base_card'];cases=report['cases'];fine=cases['equilibrium']
    profiles={name:csv_rows(out/(name+'-profile.csv')) for name in ('equilibrium','zero_states','one_shot_fixed')}
    colors={'equilibrium':'#1768ac','zero_states':'#66737f','one_shot_fixed':'#b04a16'}
    labels={'equilibrium':'coupled equilibrium','zero_states':'no interface states','one_shot_fixed':'one-shot fixed occupation'}
    def curves(field,scale=1):
        return [(labels[name],[(r['x_m']*1e9,r[field]*scale) for r in rows],colors[name],'' if name=='equilibrium' else '6 3') for name,rows in profiles.items()]
    rows=profiles['equilibrium'];length=card['half_length_m']*1e9
    bands=[('Ec',[(r['x_m']*1e9,r['Ec_eV']) for r in rows],'#1768ac',''),
           ('Ev',[(r['x_m']*1e9,r['Ev_eV']) for r in rows],'#b04a16','6 3'),
           ('common EF',[(-length,card['fermi_eV']),(length,card['fermi_eV'])],'#54616c','3 3')]
    bands.append(('localized Et at x=0',[(0,t['Et_eV']) for t in fine['traps']],'#7a43a3','points'))
    edges=csv_rows(out/'equilibrium-edges.csv')
    dp=[(-length,fine['boundary_D_left_C_m-2']*1e3)]+[(r['x_mid_m']*1e9,r['D_C_m-2']*1e3) for r in edges if r['x_mid_m']<0]
    dp += [(0,fine['D0minus_C_m-2']*1e3),(0,fine['D0plus_C_m-2']*1e3)]
    dp += [(r['x_mid_m']*1e9,r['D_C_m-2']*1e3) for r in edges if r['x_mid_m']>0]+[(length,fine['boundary_D_right_C_m-2']*1e3)]
    save(out/'space.svg','Interface occupation changes the entire equilibrium profile',
         f"Practice 08 A/B card: {card['temperature_K']:g} K; h={fine['h_m']*1e9:g} nm; EF={card['fermi_eV']:g} eV",
         'Shared x in nm; Et is a localized marker, not a third spatial band. The displacement jump uses corrected interface limits. The sheet is separate from volume charge.',
         [panel(0,85,'A common potential must be re-solved','x (nm)','phi (V)',curves('phi_V'),True),
          panel(550,85,'Et and bands use the same reference','x (nm)','energy (eV)',bands,True),
          panel(0,557,'Volume charge rearranges','x (nm)','rho (10^3 C/m^3)',curves('rho_C_m-3',1e-3),True),
          panel(550,557,'Corrected one-sided D includes the sheet','x (nm)','D (10^-3 C/m^2)',[('coupled equilibrium',dp,'#1768ac','')],True)],
         f"Sheet = {fine['sheet_C_m-2']:.8g} C/m², f = {(fine['traps'][0]['f'] if fine['traps'] else 0):.6g}; sheet is not plotted as volume rho.")
    occ=csv_rows(out/'occupation-sweep.csv');dens=csv_rows(out/'density-sweep.csv');ef=csv_rows(out/'EF-clamp-sweep.csv')
    t=fine['traps'][0] if fine['traps'] else {'f':0.0}
    save(out/'occupation-and-changes.svg','The fixed-sheet approximation has a defined comparison',
         'Same A/B material law; each density and EF point is a new equilibrium solve (sweep: 240 cells per side).',
         'Top left is the declared discrete-state FD law at baseline EF; top right changes site density with neutral outer potentials. Bottom panels instead fix both outer potentials on the explicitly shorter domain while changing common EF. Frozen means the initial short-domain occupation held fixed.',
         [panel(0,85,'Occupation reacts to the local potential','phi0 (V)','electron occupancy f',[
             ('f(phi0), baseline EF',[(r['phi0_V'],r['first_f']) for r in occ],'#1768ac',''),
             ('coupled root, fine mesh',[(fine['phi0_V'],t['f'])],'#b04a16','points')],yrange=(0,1)),
          panel(550,85,'More sites: new charge, new root','total interface sites (10^14 m^-2)','phi0 (V)',[
              ('coupled, neutral outer potentials',[(r['total_state_N_m-2']/1e14,r['phi0_V']) for r in dens],'#1768ac',''),
              ('reuse old sheet after changing N',[(r['total_state_N_m-2']/1e14,report['density_sweep_old_sheet_phi0_V']) for r in dens],'#b04a16','6 3')]),
          panel(0,557,'Short slab: EF changes with fixed ends','common EF (eV)','phi0 (V)',[
              ('coupled occupation',[(r['EF_eV'],r['coupled_phi0_V']) for r in ef],'#1768ac',''),
              ('frozen initial occupation',[(r['EF_eV'],r['frozen_phi0_V']) for r in ef],'#b04a16','6 3')]),
          panel(550,557,'The frozen comparison misses recharge','common EF (eV)','sheet (10^-5 C/m^2)',[
              ('coupled occupation',[(r['EF_eV'],r['coupled_sheet_C_m-2']*1e5) for r in ef],'#1768ac',''),
              ('frozen initial occupation',[(r['EF_eV'],r['frozen_sheet_C_m-2']*1e5) for r in ef],'#b04a16','6 3')])],
         f"Bottom only: half-length {report['interface_input']['short_half_length_m']*1e9:g} nm; phiL={fine['phiL_V']:.6g} V, phiR={fine['phiR_V']:.6g} V fixed.")
    print('Wrote space.svg and occupation-and-changes.svg from current CSV/JSON')

if __name__=='__main__':main()
