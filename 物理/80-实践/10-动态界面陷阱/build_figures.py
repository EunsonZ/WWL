#!/usr/bin/env python3
"""Plot selected output CSV columns as self-contained SVG; stdlib only."""
import argparse
import csv
from html import escape
import math
import json
from pathlib import Path


def read(path):
    with path.open() as file:
        return [{k:float(v) for k,v in row.items()} for row in csv.DictReader(file)]


def panel(parts, x, y, title, xlabel, ylabel, curves, xcol, ycol, xscale=1.0, yscale=1.0):
    width,height=400,235
    left,top=x+64,y+40;pw,ph=width-80,height-85
    values=[(r[xcol]*xscale,r[col]*yscale) for _,_,rows,col in curves for r in rows]
    xmin,xmax=min(v[0] for v in values),max(v[0] for v in values)
    ymin,ymax=min(v[1] for v in values),max(v[1] for v in values)
    if ymin==ymax: ymin-=.5;ymax+=.5
    gap=.07*(ymax-ymin);ymin-=gap;ymax+=gap
    parts.append(f'<text x="{x+10}" y="{y+21}" class="title">{escape(title)}</text>')
    for i in range(5):
        py=top+ph*i/4;value=ymax-(ymax-ymin)*i/4
        parts.append(f'<path d="M {left} {py} h {pw}" stroke="#dce3eb"/>')
        parts.append(f'<text x="{left-7}" y="{py+4}" text-anchor="end">{value:.3g}</text>')
        px=left+pw*i/4;val=xmin+(xmax-xmin)*i/4
        parts.append(f'<text x="{px}" y="{top+ph+18}" text-anchor="middle">{val:.3g}</text>')
    parts.append(f'<path d="M {left} {top} v {ph} h {pw}" fill="none" stroke="#64748b"/>')
    parts.append(f'<text x="{left+pw/2}" y="{top+ph+38}" text-anchor="middle">{escape(xlabel)}</text>')
    parts.append(f'<text transform="translate({x+15},{top+ph/2}) rotate(-90)" text-anchor="middle">{escape(ylabel)}</text>')
    for label,color,rows,col in curves:
        points=' '.join(f'{left+(r[xcol]*xscale-xmin)/(xmax-xmin)*pw:.3f},{top+(ymax-r[col]*yscale)/(ymax-ymin)*ph:.3f}' for r in rows)
        parts.append(f'<polyline data-csv-column="{escape(col)}" points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    # Legend above each panel's plot, kept within available width.
    for i,(label,color,_,_) in enumerate(curves):
        px=left+i*pw/len(curves)
        parts.append(f'<path d="M {px} {top-12} h 12" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{px+16}" y="{top-8}" font-size="10">{escape(label)}</text>')


def document(title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="860" height="570" viewBox="0 0 860 570"><title>{escape(title)}</title>',
            '<style>text{font-family:Arial,sans-serif;font-size:11px;fill:#213047}.title{font-size:14px;font-weight:bold}</style>',
            '<rect width="860" height="570" fill="#fff"/>',
            f'<text x="26" y="25" class="title">{escape(title)}</text>',
            f'<text x="26" y="46">{escape(subtitle)}</text>']


def build(directory):
    if any((directory/name).exists() for name in ('dynamics.svg','charge-balance.svg')):
        raise ValueError('refuse to replace existing figures; use a new output directory')
    parameters=json.loads((directory/'results.json').read_text())['inputs']
    if len(parameters['dos_bin_centers_eV'])!=3:
        raise ValueError('this four-panel layout requires exactly three DOS bins; solver supports other finite spectra')
    density_label=f"{parameters['density_factor']:g}x density"
    slow_label=f"{parameters['capture_factors'][0]:g}x"
    fast_label=f"{parameters['capture_factors'][1]:g}x"
    energy_labels=[f'Et0={energy:g}' for energy in parameters['dos_bin_centers_eV']]
    step=read(directory/'step-time.csv');slow=read(directory/'slow-time.csv');fast=read(directory/'fast-time.csv')
    density=read(directory/'density-time.csv');dos=read(directory/'finite_dos-time.csv');frozen=read(directory/'frozen-analytic.csv')
    name=next(key[2:] for key in step[0] if key.startswith('f_'))
    parts=document('Dynamic sheet occupation and electrostatic feedback', 'A-side capture/emission; clamped distributed carrier reservoirs; time starts at 0+')
    panel(parts,15,65,'Occupation lags after carrier step','t (us)','occupation',
          [('coupled','#1769aa',step,'f_'+name),('frozen field','#b36118',frozen,'f_frozen_exact')], 't_s',None,1e6)
    panel(parts,440,65,'Potential follows stored sheet charge','t (us)','phi(0) (V)',
          [('coupled','#1769aa',step,'phi0_V'),(density_label,'#a23d6b',density,'phi0_V')], 't_s',None,1e6)
    panel(parts,15,305,'Capture coefficients change the clock','t (us)','occupation',
          [(slow_label,'#718096',slow,'f_'+name),('1x','#1769aa',step,'f_'+name),(fast_label,'#15956c',fast,'f_'+name)],'t_s',None,1e6)
    panel(parts,440,305,'Three equal-weight discrete energy bins','t (us)','occupation',
          [(energy_labels[0],'#a23d6b',dos,'f_bin0'),(energy_labels[1],'#1769aa',dos,'f_bin1'),(energy_labels[2],'#b36118',dos,'f_bin2')],'t_s',None,1e6)
    parts.append('</svg>');(directory/'dynamics.svg').write_text('\n'.join(parts)+'\n')
    balance=read(directory/'step-balance.csv')
    parts=document('Charge bookkeeping uses the same time steps and Poisson solution', 'Event integrals are exact for each frozen-rate substep; time discretization checked separately')
    panel(parts,15,65,'Stored charges and compensating electrodes','t (us)','charge (uC/m2)',
          [('sheet','#1769aa',step,'sheet_C_m-2'),('bulk','#15956c',step,'volume_C_m-2'),('electrodes','#a23d6b',step,'electrodes_C_m-2')],'t_s',None,1e6,1e6)
    panel(parts,440,65,'Net electron and hole loss need not agree','t (us)','net loss (m-2 s-1)',
          [('Un','#1769aa',step,'Un_'+name+'_m-2_s-1'),('Up','#b36118',step,'Up_'+name+'_m-2_s-1')],'t_s',None,1e6)
    panel(parts,15,305,'Four nonnegative event counts per step','t (us)','events per m2 per step',
          [('Cn','#1769aa',balance,'capture_n_m-2'),('En','#15956c',balance,'emission_n_m-2'),('Cp','#a23d6b',balance,'capture_p_m-2'),('Ep','#b36118',balance,'emission_p_m-2')],'t_end_s',None,1e6)
    panel(parts,440,305,'Trap and supplied-charge algebra residuals','t (us)','residual (C/m2)',
          [('trap','#1769aa',balance,'trap_balance_error_C_m-2'),('supply','#b36118',balance,'supply_balance_error_C_m-2')],'t_end_s',None,1e6)
    parts.append('</svg>');(directory/'charge-balance.svg').write_text('\n'.join(parts)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--results',type=Path,default=Path(__file__).with_name('results'))
    build(parser.parse_args().results)
