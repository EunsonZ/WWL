#!/usr/bin/env python3
"""Three thick coaxial conductors: SI electrostatic BVP, analytic and radial FV.
Only Python standard library. No exterior field or open-end correction is solved.
"""
import argparse
import csv
import html
import json
import math
import platform
from pathlib import Path

C0 = 299792458.0
MU0 = 4 * math.pi * 1e-7  # consistent teaching approximation, not SI-exact
EPS0 = 1 / (MU0 * C0 * C0)


def finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def validate(data):
    rs = [finite(data['radii_m'][k], k) for k in ('a', 'b_inner', 'b_outer', 'c')]
    if not 0 < rs[0] < rs[1] < rs[2] < rs[3]:
        raise ValueError('require 0 < a < b_inner < b_outer < c')
    es = [finite(x, 'epsilon_r') for x in data['epsilon_r']]
    if len(es) != 2 or min(es) <= 0:
        raise ValueError('epsilon_r must contain two positive values')
    if finite(data['length_m'], 'length_m') <= 0:
        raise ValueError('length_m must be positive')
    for key in ('voltages_V', 'voltage_rates_V_per_s'):
        if len(data[key]) != 3:
            raise ValueError(f'{key} must contain three entries')
        for x in data[key]:
            finite(x, key)
    for key in ('mesh_cells_per_material',):
        ns = data[key]
        if len(ns) < 2 or any(type(n) is not int or not 4 <= n <= 8192 for n in ns):
            raise ValueError('mesh list requires at least two integer sizes from 4 to 8192')
        if any(y <= x for x, y in zip(ns, ns[1:])):
            raise ValueError('mesh sizes must strictly increase')
    n = data['simpson_intervals_per_material']
    if type(n) is not int or n < 2 or n > 100000 or n % 2:
        raise ValueError('Simpson intervals must be a positive even integer <= 100000')
    n = data['curve_intervals_per_gap']
    if type(n) is not int or not 4 <= n <= 10000:
        raise ValueError('curve intervals must be an integer from 4 to 10000')
    transfer = data['layered_transfer']
    s = finite(transfer['interface_m'], 'interface_m')
    if not rs[0] < s < rs[1]:
        raise ValueError('transfer interface must be in the inner gap')
    tes = [finite(x, 'inner_epsilon_r') for x in transfer['inner_epsilon_r']]
    if len(tes) != 2 or min(tes) <= 0:
        raise ValueError('transfer epsilon values must be positive')
    return rs, es


def gap_cap(segments):
    # Independent closed-form resistance integral; each segment has constant epsilon.
    return 2 * math.pi / sum(math.log(r1 / r0) / eps for r0, r1, eps in segments)


def analytic_field(segments, left, right, r, segment_index):
    cap = gap_cap(segments)
    flux = cap * (left - right) / (2 * math.pi)
    r0, _, eps = segments[segment_index]
    drop_before = sum(flux / e * math.log(hi / lo)
                      for lo, hi, e in segments[:segment_index])
    phi = left - drop_before - flux / eps * math.log(r / r0)
    er = flux / (eps * r)
    return phi, er, flux / r


def simpson(fn, lo, hi, n):
    step = (hi - lo) / n
    return step / 3 * (fn(lo) + fn(hi) + sum(
        (4 if i % 2 else 2) * fn(lo + step * i) for i in range(1, n)))


def energy_integral(segments, left, right, n):
    total = 0.0
    for idx, (lo, hi, eps) in enumerate(segments):
        total += simpson(lambda r: math.pi * eps * r * analytic_field(
            segments, left, right, r, idx)[1] ** 2, lo, hi, n)
    return total


def fv_gap(segments, left, right, n):
    """Solve conservative radial discrete BVP. No logarithms enter this solve.
    Edge conductance g_e = 2*pi*epsilon*r_mid/h. Constant radial flux
    solves g_left*(phi_prev-phi) = g_right*(phi-phi_next) at every node.
    """
    edges = []
    for lo, hi, eps in segments:
        h = (hi - lo) / n
        for j in range(n):
            x0, x1 = lo + j * h, lo + (j + 1) * h
            edges.append((x0, x1, eps, 2 * math.pi * eps * (x0 + x1) / (2 * h)))
    resistance = sum(1 / e[3] for e in edges)
    flux = (left - right) / resistance
    nodes = [(segments[0][0], left)]
    resistance_so_far = 0.0
    for _, x1, _, g in edges:
        resistance_so_far += 1 / g
        nodes.append((x1, left - flux * resistance_so_far))
    discrete_energy = 0.5 * sum(e[3] * (nodes[i][1] - nodes[i+1][1]) ** 2
                                for i, e in enumerate(edges))
    max_node_err = 0.0
    for idx, (lo, hi, _) in enumerate(segments):
        for j in range(n + 1):
            r, phi = nodes[idx * n + j]
            expected = analytic_field(segments, left, right, r, idx)[0]
            max_node_err = max(max_node_err, abs(phi - expected))
    fluxes = [e[3] * (nodes[i][1] - nodes[i+1][1]) for i, e in enumerate(edges)]
    flux_res = max((abs(x-y) for x, y in zip(fluxes, fluxes[1:])), default=0)
    return {'cap_F_per_m': 1 / resistance, 'left_charge_C_per_m': flux,
            'right_charge_C_per_m': -flux, 'discrete_energy_J_per_m': discrete_energy,
            'max_phi_error_V': max_node_err,
            'boundary_residual_V': max(abs(nodes[0][1]-left), abs(nodes[-1][1]-right)),
            'flux_balance_residual_C_per_m': flux_res}


def matvec(matrix, vector):
    return [sum(a*b for a, b in zip(row, vector)) for row in matrix]


def matrices(a_cap, b_cap):
    return ([[a_cap, -a_cap], [-a_cap, a_cap+b_cap]],
            [[a_cap, -a_cap, 0.0], [-a_cap, a_cap+b_cap, -b_cap], [0.0, -b_cap, b_cap]])


def charges_by_surfaces(gaps, voltages, cells=None):
    u1, u2, u3 = voltages
    if cells is None:
        f1 = gap_cap(gaps[0]) * (u1-u2)
        f2 = gap_cap(gaps[1]) * (u2-u3)
    else:
        f1 = fv_gap(gaps[0], u1, u2, cells)['left_charge_C_per_m']
        f2 = fv_gap(gaps[1], u2, u3, cells)['left_charge_C_per_m']
    return [f1, -f1+f2, -f2], [f1, -f1, f2, -f2]


def extract_matrix(gaps, n):
    # Columns are conductor charges from separate unit-voltage BVPs, not copied C.
    cols = [charges_by_surfaces(gaps, [float(i==j) for i in range(3)], n)[0]
            for j in range(3)]
    return [[cols[j][i] for j in range(3)] for i in range(3)]


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def svg_start(width, height, title, desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(desc)}</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#172b4d;font-size:16px}.small{font-size:13px}.axis{stroke:#52657a;stroke-width:1}.grid{stroke:#dfe7ef;stroke-width:1}</style>']


def txt(out, x, y, s, css=''):
    out.append(f'<text x="{x}" y="{y}" class="{css}">{html.escape(s)}</text>')


def poly(out, points, color, dashed=False):
    d = (' stroke-dasharray="2 4"' if dashed == 'dotted' else ' stroke-dasharray="8 5"') if dashed else ''
    out.append(f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="2.5"{d}/>')


def plot_panel(out, box, xrange, yrange, xlabel, ylabel, series):
    x, y, w, h = box
    xmin, xmax = xrange
    ymin, ymax = yrange
    def sx(v):return x+w*(v-xmin)/(xmax-xmin)
    def sy(v):return y+h-h*(v-ymin)/(ymax-ymin)
    for j in range(5):
        xx = x + w*j/4
        yy = y + h*j/4
        out.append(f'<path d="M{xx},{y}V{y+h} M{x},{yy}H{x+w}" class="grid"/>')
        txt(out, xx-12, y+h+23, f'{xmin+(xmax-xmin)*j/4:.3g}', 'small')
        txt(out, x-60, yy+5, f'{ymax-(ymax-ymin)*j/4:.3g}', 'small')
    out.append(f'<path d="M{x},{y}V{y+h}H{x+w}" fill="none" class="axis"/>')
    txt(out, x+w/2-50, y+h+47, xlabel)
    txt(out, x, y-14, ylabel)
    for points, color, dashed in series:
        poly(out, [(sx(a), sy(b)) for a,b in points], color, dashed)
    return sx, sy


def geometry_svg(data, rs, es):
    a, b, d, c = [r*1000 for r in rs]
    out=svg_start(960,680,'Three coaxial conductors with a thick middle shell',
                  'Central x-y cross-section in millimetres. Two separate dielectric gaps; metal electric field is zero. No open-end model.')
    txt(out, 35, 35, 'Thick-shell three-conductor electrostatic cross-section')
    txt(out, 35, 61, f'a={a:g}, b-={b:g}, b+={d:g}, c={c:g} mm; relative permittivity {es[0]:g}/{es[1]:g}', 'small')
    cx, cy, scale = 285, 350, 220/c
    for r, fill in [(c,'#e4f0ff'),(d,'#b2bac5'),(b,'#fff0d9'),(a,'#8b98aa')]:
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r*scale}" fill="{fill}" stroke="#53677d" stroke-width="2"/>')
    out.append(f'<path d="M{cx-250},{cy}H{cx+250} M{cx},{cy+250}V{cy-250}" class="axis" stroke-dasharray="4 4"/>')
    for v in [-c, -b, 0, b, c]:
        xx=cx+v*scale
        txt(out, xx-10, cy+24, f'{v:g}', 'small')
    txt(out, cx+210, cy+46,'x (mm)')
    txt(out, cx+8, cy-233,'y (mm)')
    txt(out, 580, 140, 'Conductor 1: r < a, potential U1')
    txt(out, 580, 180, 'Inner gap: a < r < b-, epsilon_1')
    txt(out, 580, 220, 'Conductor 2: b- < r < b+, U2')
    txt(out, 580, 260, 'Outer gap: b+ < r < c, epsilon_2')
    txt(out, 580, 300, f'Conductor 3: r = c, U3 = {data["voltages_V"][2]:g} V')
    txt(out, 580, 350, 'Surface normal into dielectric:')
    txt(out, 580, 380, 'a: +er; b-: -er; b+: +er; c: -er')
    txt(out, 580, 425, 'For U1 > U2 > U3:')
    txt(out, 580, 455, 'surface charges: +, -, +, -')
    txt(out, 580, 495, 'The middle net charge is a sum,')
    txt(out, 580, 522, 'not the charge on only one face.')
    txt(out, 35, 630, 'Finite length: dphi/dz = 0 at both ends. Outside reference surface is excluded.', 'small')
    out.append('</svg>');return '\n'.join(out)+'\n'


def fields_svg(data, rs, es, rows):
    out=svg_start(1000,1030,'Potential, electric field and cumulative energy from fields.csv',
                  'Same radii and dielectric inputs as fields.csv. Solid middle clamped voltage, dashed neutral floating middle. Metal interval is shaded; radial field may jump at conductor surfaces.')
    txt(out,30,32,'Same electrostatic geometry: clamped vs neutral floating middle conductor')
    txt(out,30,59,f'epsilon_r={es[0]:g}/{es[1]:g}; U1/U2/U3={data["voltages_V"][0]:g}/{data["voltages_V"][1]:g}/{data["voltages_V"][2]:g} V; end Neumann condition','small')
    txt(out,30,87,'solid: specified U2; dashed: Q2 = 0; grey band: middle metal, E = 0','small')
    for idx,(key,label,unit) in enumerate([('phi_V','Potential','V'),('E_r_V_per_m','Radial electric field','V/m'),('cumulative_energy_pJ_per_m','Cumulative field energy','pJ/m')]):
        vals=[r[key] for r in rows]
        low=min(0,min(vals)); high=max(vals)
        if high==low:high=low+1
        pad=(high-low)*.06
        series=[]
        for case in ('clamped','floating_neutral'):
            for region in ('inner_gap','middle_metal','outer_gap'):
                pts=[(r['r_m']*1000,r[key]) for r in rows if r['case']==case and r['region']==region]
                series.append((pts,'#1767a5' if case=='clamped' else '#a13e1c',case!='clamped'))
        box=(115,150+idx*285,815,205)
        sx,sy=plot_panel(out,box,(rs[0]*1000,rs[3]*1000),(low-pad,high+pad),'r (mm)',f'{label} ({unit})',[])
        x=sx(rs[1]*1000);w=sx(rs[2]*1000)-x
        out.append(f'<rect x="{x}" y="{box[1]}" width="{w}" height="{box[3]}" fill="#bdc5cf" fill-opacity=".32"/>')
        for pts,color,dashed in series:poly(out,[(sx(x),sy(y)) for x,y in pts],color,dashed)
    txt(out,30,1010,'Separate lines stop at each material/metal boundary; no finite-thickness transition is implied.','small')
    out.append('</svg>');return '\n'.join(out)+'\n'


def sweep_svg(rs, es, rows, floating):
    out=svg_start(1000,745,'Charge and energy against middle potential from sweep.csv',
                  'Inner voltage difference fixed to one volt and outer to zero. Three conductor charges conserve charge. Energy minimum at the neutral floating potential.')
    txt(out,30,32,'Clamp V1 = 1 V, V3 = 0; vary middle voltage V2')
    txt(out,30,59,f'epsilon_r={es[0]:g}/{es[1]:g}; same geometry; neutral middle V2={floating:.6f} V','small')
    series=[]
    for key,color,dash in [('Q1_pC_per_m','#1767a5',False),('Q2_pC_per_m','#a13e1c',True),('Q3_pC_per_m','#307c4b','dotted')]:
        series.append(([(r['V2_V'],r[key]) for r in rows],color,dash))
    vals=[r[k] for r in rows for k in ('Q1_pC_per_m','Q2_pC_per_m','Q3_pC_per_m')]
    sx,sy=plot_panel(out,(115,130,815,205),(-.25,1.25),(min(vals)*1.08,max(vals)*1.08),'V2 (V)','Conductor net charge (pC/m)',series)
    out.append(f'<path d="M{sx(floating)},130V335" stroke="#555" stroke-dasharray="4 4"/>')
    txt(out,30,86,'Q1 solid blue; Q2 dashed brown; Q3 dotted green; vertical line: Q2=0','small')
    vals=[r['energy_pJ_per_m'] for r in rows]
    sx,sy=plot_panel(out,(115,440,815,205),(-.25,1.25),(0,max(vals)*1.06),'V2 (V)','Field energy (pJ/m)',[([(r['V2_V'],r['energy_pJ_per_m']) for r in rows],'#6244a0',False)])
    out.append(f'<path d="M{sx(floating)},440V645" stroke="#555" stroke-dasharray="4 4"/>')
    txt(out,30,725,'This is a family of static states, not a time waveform; V2 is a prescribed boundary condition.','small')
    out.append('</svg>');return '\n'.join(out)+'\n'


def run(data, output):
    rs, es = validate(data)
    a,b,d,c=rs
    gaps=[[(a,b,EPS0*es[0])],[(d,c,EPS0*es[1])]]
    ac,bc=[gap_cap(g) for g in gaps]
    reduced,full=matrices(ac,bc)
    u=data['voltages_V']; v=[u[0]-u[2],u[1]-u[2]]
    q,surface_q=charges_by_surfaces(gaps,u)
    surface_r=[a,b,d,c]
    sigma=[qv/(2*math.pi*r) for qv,r in zip(surface_q,surface_r)]
    energy=.5*sum(x*y for x,y in zip(u,q))
    n=data['simpson_intervals_per_material']
    integrated=sum(energy_integral(g,left,right,n) for g,left,right in zip(gaps,u[:2],u[1:]))
    integrated_coarse=sum(energy_integral(g,left,right,n//2) for g,left,right in zip(gaps,u[:2],u[1:])) if n%4==0 else None
    eig_disc=math.sqrt((reduced[0][0]-reduced[1][1])**2+4*reduced[0][1]**2)
    eigs=[(reduced[0][0]+reduced[1][1]-eig_disc)/2,(reduced[0][0]+reduced[1][1]+eig_disc)/2]
    floating_v2=ac/(ac+bc)*v[0]
    effective=ac*bc/(ac+bc)
    mesh=[]
    for cells in data['mesh_cells_per_material']:
        mf=extract_matrix(gaps,cells)
        qf=matvec(mf,u)
        ef=sum(fv_gap(g,left,right,cells)['discrete_energy_J_per_m'] for g,left,right in zip(gaps,u[:2],u[1:]))
        phi=max(fv_gap(g,left,right,cells)['max_phi_error_V'] for g,left,right in zip(gaps,u[:2],u[1:]))
        mesh.append({'cells_per_material':cells,'C3_F_per_m':mf,
                     'max_matrix_relative_error':max(abs(mf[i][j]-full[i][j]) for i in range(3) for j in range(3))/max(abs(x) for row in full for x in row),
                     'max_reciprocity_residual_F_per_m':max(abs(mf[i][j]-mf[j][i]) for i in range(3) for j in range(3)),
                     'charge_balance_C_per_m':sum(qf),'max_phi_error_V':phi,
                     'max_boundary_residual_V':max(fv_gap(g,left,right,cells)['boundary_residual_V'] for g,left,right in zip(gaps,u[:2],u[1:])),
                     'max_flux_balance_residual_C_per_m':max(fv_gap(g,left,right,cells)['flux_balance_residual_C_per_m'] for g,left,right in zip(gaps,u[:2],u[1:])),
                     'energy_J_per_m':ef,'energy_relative_error':abs(ef-energy)/energy if energy else 0,
                     'discrete_field_vs_terminal_energy_difference_J_per_m':ef-.5*sum(x*y for x,y in zip(u,qf))})
    trans=data['layered_transfer'];s=trans['interface_m'];e1,e2=trans['inner_epsilon_r']
    layered=[(a,s,EPS0*e1),(s,b,EPS0*e2)]
    la=gap_cap(layered);lf=la/(la+bc);lv=[1.0,lf,0.0]
    layer_l=analytic_field(layered,1,lf,s,0);layer_r=analytic_field(layered,1,lf,s,1)
    layer_energy=energy_integral(layered,1,lf,n)+energy_integral(gaps[1],lf,0,n)
    layer_eff=la*bc/(la+bc)
    unit_basis_checks=[]
    for j in range(3):
        uu=[float(k==j) for k in range(3)]
        qq,_=charges_by_surfaces(gaps,uu)
        unit_basis_checks.append({'excited_conductor':j+1,'charges_C_per_m':qq,
                                  'matrix_column_difference_C_per_m':[qq[i]-full[i][j] for i in range(3)]})
    rates=data['voltage_rates_V_per_s'];currents=[data['length_m']*x for x in matvec(full,rates)]
    values={'model':'two annular dielectric domains, thick PEC middle, finite length end Neumann; no exterior or end correction',
            'constants':{'epsilon0_F_per_m':EPS0,'mu0_H_per_m_approx':MU0,'c0_m_per_s':C0},
            'input':data,'gap_capacitances_F_per_m':[ac,bc],
            'C_reduced_F_per_m':reduced,'C_full_F_per_m':full,'reduced_eigenvalues_F_per_m':eigs,
            'conductor_charges_C_per_m':q,'surface_charges_C_per_m':surface_q,'surface_sigma_C_per_m2':sigma,
            'charge_balance_C_per_m':sum(q),'row_sums_F_per_m':[sum(row) for row in full],
            'energy_J_per_m':energy,'integrated_energy_J_per_m':integrated,
            'integration_relative_error':abs(integrated-energy)/energy if energy else 0,
            'coarse_integrated_energy_J_per_m':integrated_coarse,
            'unit_excitation_checks':unit_basis_checks,'mesh_checks':mesh,
            'floating_neutral':{'V2_relative_V':floating_v2,'effective_C_F_per_m':effective,
                                'charges_C_per_m':matvec(full,[v[0],floating_v2,0]),
                                'energy_J_per_m':.5*effective*v[0]**2},
            'port':{'currents_A_entering_conductors':currents,
                    'power_W':sum(x*y for x,y in zip(u,currents))},
            'layered_transfer':{'inner_cap_F_per_m':la,'floating_V2_V':lf,'effective_C_F_per_m':layer_eff,
                'interface_phi_jump_V':layer_r[0]-layer_l[0],
                'interface_D_jump_C_per_m2':layer_r[2]-layer_l[2],
                'interface_E_ratio_left_over_right':layer_l[1]/layer_r[1],
                'field_energy_J_per_m':layer_energy,'terminal_energy_J_per_m':.5*layer_eff,
                'mesh_checks':[fv_gap(layered,1,lf,m) for m in data['mesh_cells_per_material']]}}
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case,uu in [('clamped',u),('floating_neutral',[u[0],u[2]+floating_v2,u[2]])]:
        e_inner=.5*ac*(uu[0]-uu[1])**2
        for region,gap_idx in [('inner_gap',0),('outer_gap',1)]:
            lo,hi,eps=gaps[gap_idx][0]
            for j in range(data['curve_intervals_per_gap']+1):
                r=lo+(hi-lo)*j/data['curve_intervals_per_gap']
                p,e,dr=analytic_field(gaps[gap_idx],uu[gap_idx],uu[gap_idx+1],r,0)
                cum=math.pi*eps*((uu[gap_idx]-uu[gap_idx+1])/math.log(hi/lo))**2*math.log(r/lo)
                if gap_idx==1:cum+=e_inner
                rows.append({'case':case,'region':region,'r_m':r,'phi_V':p,'E_r_V_per_m':e,
                             'D_r_C_per_m2':dr,'cumulative_energy_pJ_per_m':cum*1e12})
        for r in [b,d]:rows.append({'case':case,'region':'middle_metal','r_m':r,'phi_V':uu[1],
                                    'E_r_V_per_m':0.0,'D_r_C_per_m2':0.0,'cumulative_energy_pJ_per_m':e_inner*1e12})
    write_csv(output/'fields.csv',rows)
    sweep=[]
    for j in range(151):
        vv2=-.25+1.5*j/150
        qq=matvec(full,[1,vv2,0])
        sweep.append({'V2_V':vv2,'Q1_pC_per_m':qq[0]*1e12,'Q2_pC_per_m':qq[1]*1e12,
                      'Q3_pC_per_m':qq[2]*1e12,'energy_pJ_per_m':.5*(ac*(1-vv2)**2+bc*vv2**2)*1e12})
    write_csv(output/'sweep.csv',sweep)
    for name,svg in [('geometry.svg',geometry_svg(data,rs,es)),('fields.svg',fields_svg(data,rs,es,rows)),
                     ('charge-energy.svg',sweep_svg(rs,es,sweep,ac/(ac+bc)))]:
        (output/name).write_text(svg,encoding='utf-8')
    (output/'values.json').write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Acceptance criteria only verify this input and this model, not arbitrary 3D physics.
    assert eigs[0] > 0
    assert abs(sum(q)) < 1e-20
    assert abs(integrated-energy) < max(1e-24,abs(energy)*1e-9)
    assert mesh[-1]['max_matrix_relative_error'] < mesh[0]['max_matrix_relative_error']
    assert mesh[-1]['max_phi_error_V'] < max(mesh[0]['max_phi_error_V'],1e-14)
    assert all(m['max_reciprocity_residual_F_per_m'] < 1e-20 for m in mesh)
    assert abs(layer_r[2]-layer_l[2]) < 1e-20
    summary={'python_version':platform.python_version(),'platform':platform.system()+' '+platform.machine(),
             'gap_capacitances_pF_per_m':[x*1e12 for x in [ac,bc]],'C_reduced_pF_per_m':[[x*1e12 for x in row] for row in reduced],
             'charges_pC_per_m':[x*1e12 for x in q],'energy_pJ_per_m':energy*1e12,
             'integration_relative_error':values['integration_relative_error'],
             'mesh_matrix_relative_errors':[m['max_matrix_relative_error'] for m in mesh],
             'floating_neutral_V2_V':floating_v2,'floating_effective_C_pF_per_m':effective*1e12,
             'currents_uA': [x*1e6 for x in currents],
             'layered_effective_C_pF_per_m':layer_eff*1e12,'checks':'PASS'}
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        run(json.loads(args.input.read_text(encoding='utf-8')),args.output_dir)
    except (ValueError,KeyError,TypeError,AssertionError) as exc:
        parser.exit(2,f'{type(exc).__name__}: {exc}\n')


if __name__=='__main__':main()
