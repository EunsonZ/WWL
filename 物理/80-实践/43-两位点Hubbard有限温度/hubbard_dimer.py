#!/usr/bin/env python3
"""Symmetric two-site Hubbard dimer, exactly N=2, real six-dimensional matrices.
Python standard library. No grand-canonical or thermodynamic-limit calculation.
"""
import argparse
import csv
import html
import itertools
import json
import math
from pathlib import Path
import re

KB = 1.380649e-23 / 1.602176634e-19
DASHES = ['', '7 3', '2 3', '9 3 2 3', '1 2', '4 2 1 2', '12 4', '3 5', '10 2 1 2 1 2', '5 1', '2 2 6 2', '8 5 1 5']
MODE_ORDER = ['1_up', '1_down', '2_up', '2_down']
PAIRS = list(itertools.combinations(range(4), 2))
BASIS = [tuple(int(a in pair) for a in range(4)) for pair in PAIRS]
LOOKUP = {ns: i for i, ns in enumerate(BASIS)}
LABELS = ['D1', 'T_plus', 'A', 'B', 'T_minus', 'D2']


def number(x, lo, hi, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x < lo or x > hi or not math.isfinite(x):
        raise ValueError(f'{name}: expected finite number in [{lo}, {hi}]')
    return float(x)


def exact_keys(obj, names, label):
    if not isinstance(obj, dict) or set(obj) != set(names):
        raise ValueError(f'{label}: expected exactly {sorted(names)}')


def read_card(path):
    raw = path.read_text(encoding='utf-8')
    if len(raw) > 100000:
        raise ValueError('input too large')
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError(f'duplicate key: {k}')
            d[k] = v
        return d
    card = json.loads(raw, object_pairs_hook=unique)
    exact_keys(card, ['units', 'particle_number', 'mode_order', 'cases', 'temperatures_K', 'interaction_ratios'], 'top level')
    if card['units'] != {'energy': 'eV', 'temperature': 'K'}:
        raise ValueError('units must be energy=eV, temperature=K')
    if isinstance(card['particle_number'], bool) or not isinstance(card['particle_number'], int) or card['particle_number'] != 2:
        raise ValueError('particle_number must be integer 2')
    if card['mode_order'] != MODE_ORDER:
        raise ValueError('mode_order must be [1_up,1_down,2_up,2_down]')
    cs = card['cases']
    if not isinstance(cs, list) or not 1 <= len(cs) <= 12:
        raise ValueError('cases: expected 1..12 cases')
    names = set()
    for c in cs:
        exact_keys(c, ['name', 't_eV', 'U_eV', 'temperature_K'], 'case')
        name = c['name']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', name) or name in names:
            raise ValueError('case name must be unique ASCII identifier of length 1..40')
        names.add(name)
        c['t_eV'] = number(c['t_eV'], 1e-5, 1, 't_eV')
        c['U_eV'] = number(c['U_eV'], 0, 2, 'U_eV')
        c['temperature_K'] = number(c['temperature_K'], .1, 2000, 'temperature_K')
    for key, lo, hi, cap in [('temperatures_K', .1, 2000, 121), ('interaction_ratios', 0, 80, 161)]:
        xs = card[key]
        if not isinstance(xs, list) or not 2 <= len(xs) <= cap:
            raise ValueError(f'{key}: expected 2..{cap} samples')
        card[key] = [number(x, lo, hi, key) for x in xs]
        if any(x >= y for x, y in zip(card[key], card[key][1:])):
            raise ValueError(f'{key} must be strictly increasing')
    return card


def zero(n=6):
    return [[0.0] * n for _ in range(n)]


def matmul(a, b):
    n = len(a)
    return [[math.fsum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]


def act(ns, a, create):
    if ns[a] == int(create):
        return None
    sign = -1 if sum(ns[:a]) % 2 else 1
    out = list(ns)
    out[a] = int(create)
    return tuple(out), sign


def bilinear(a, b):
    out = zero()
    for col, ns in enumerate(BASIS):
        first = act(ns, b, False)
        if first is None:
            continue
        second = act(first[0], a, True)
        if second is not None:
            out[LOOKUP[second[0]]][col] = first[1] * second[1]
    return out


def operators(t, u):
    hop = zero()
    for a, b in [(0, 2), (2, 0), (1, 3), (3, 1)]:
        op = bilinear(a, b)
        hop = [[hop[i][j] + op[i][j] for j in range(6)] for i in range(6)]
    d = zero(); n1 = zero(); n2 = zero()
    for i, ns in enumerate(BASIS):
        d[i][i] = ns[0] * ns[1] + ns[2] * ns[3]
        n1[i][i] = ns[0] + ns[1]
        n2[i][i] = ns[2] + ns[3]
    h = [[-t * hop[i][j] + u * d[i][j] for j in range(6)] for i in range(6)]
    flip1 = matmul(bilinear(0, 1), bilinear(3, 2))
    flip2 = matmul(bilinear(1, 0), bilinear(2, 3))
    spin = [[.5 * (flip1[i][j] + flip2[i][j]) for j in range(6)] for i in range(6)]
    for i, ns in enumerate(BASIS):
        spin[i][i] += .25 * (ns[0] - ns[1]) * (ns[2] - ns[3])
    return dict(H=h, D=d, spin=spin, n1=n1, n2=n2, hopping=hop)


def spectrum(t, u):
    r = math.hypot(u, 4 * t)
    em = -8 * t * t / (u + r)
    ep = (u + r) / 2
    d = 8 * t * t / (r * (r + u))
    a, b = math.sqrt(1 - d), math.sqrt(d)
    q = 1 / math.sqrt(2)
    singlet = [0, 0, q, -q, 0, 0]
    dp = [q, 0, 0, 0, 0, q]
    ground = [a * x + b * y for x, y in zip(singlet, dp)]
    upper = [-b * x + a * y for x, y in zip(singlet, dp)]
    vectors = [ground, [0, 1, 0, 0, 0, 0], [0, 0, q, q, 0, 0], [0, 0, 0, 0, 1, 0], [q, 0, 0, 0, 0, -q], upper]
    labels = ['singlet_lower', 'triplet_plus', 'triplet_zero', 'triplet_minus', 'double_odd', 'singlet_upper']
    energies = [em, 0.0, 0.0, 0.0, u, ep]
    gap = -em
    j2 = 4 * t * t / u if u > 0 else None
    # Exact relative overestimate = gap/U, avoids subtracting nearly equal gaps.
    rel = gap / u if u > 0 else None
    return dict(labels=labels, energies_eV=energies, vectors=vectors, R_eV=r,
                ground_D=d, ground_spin=-.75 * (1 - d),
                ground_n_bonding_per_spin=.5 + 2 * t / r,
                gap_eV=gap, J2_eV=j2, J2_relative_error=rel)


def expectation(rho, op):
    return math.fsum(rho[i][j] * op[j][i] for i in range(6) for j in range(6))


def thermal(t, u, temp):
    ops = operators(t, u)
    spec = spectrum(t, u)
    es, vecs = spec['energies_eV'], spec['vectors']
    theta = KB * temp
    shift = es[0]
    weights = [math.exp(-(e - shift) / theta) for e in es]
    zshift = math.fsum(weights)
    ps = [w / zshift for w in weights]
    rho = [[math.fsum(p * v[i] * v[j] for p, v in zip(ps, vecs)) for j in range(6)] for i in range(6)]
    d = expectation(rho, ops['D'])
    spin = expectation(rho, ops['spin'])
    mean1, mean2 = expectation(rho, ops['n1']), expectation(rho, ops['n2'])
    cov = expectation(rho, matmul(ops['n1'], ops['n2'])) - mean1 * mean2
    var1 = expectation(rho, matmul(ops['n1'], ops['n1'])) - mean1 * mean1
    gamma = [[expectation(rho, bilinear(a, b)) for b in range(4)] for a in range(4)]
    # Conditional state after projecting onto one particle on each site.
    s = [0, 0, 1/math.sqrt(2), -1/math.sqrt(2), 0, 0]
    single_weight = math.fsum(rho[i][i] for i in [1, 2, 3, 4])
    singlet_weight = math.fsum(s[i] * rho[i][j] * s[j] for i in range(6) for j in range(6))
    p_s = singlet_weight / single_weight
    ppt_min = (1 - 2 * p_s) / 2
    purity = math.fsum(rho[i][j] * rho[j][i] for i in range(6) for j in range(6))
    logz = math.log(zshift) - shift / theta
    obs = dict(mean_energy_eV=expectation(rho, ops['H']), D_total=d, D_per_site=d/2,
               spin_dot_dimensionless=spin, mean_n1=mean1, mean_n2=mean2,
               charge_connected=cov, variance_n1=var1, total_number_variance=0.0,
               purity=purity, single_single_probability=single_weight,
               conditioned_singlet_probability=p_s, conditioned_spin_dot=.25-p_s,
               conditioned_PPT_min=ppt_min, conditioned_negativity=max(0.0,-ppt_min),
               bonding_per_spin=.5*(gamma[0][0]+gamma[2][2]+gamma[0][2]+gamma[2][0]))
    residual = max(abs(math.fsum(ops['H'][i][j] * v[j] for j in range(6)) - e*v[i]) for e,v in zip(es,vecs) for i in range(6))
    return dict(spectrum=spec, probabilities=ps, rho=rho, gamma=gamma, operators=ops,
                logZ=logz, observables=obs, eigen_residual_eV=residual,
                site_reduced_diagonal=[d/2,(1-d)/2,(1-d)/2,d/2])


def csv_file(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def text(s, x, y, value, size=13, anchor='start'):
    s.append(f'<text x="{x:.4f}" y="{y:.4f}" font-size="{size}" text-anchor="{anchor}">{html.escape(str(value))}</text>')


def start(title, desc, height=780):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="'+str(height)+'" viewBox="0 0 1100 '+str(height)+'">',
         f'<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>',
         '<rect width="100%" height="100%" fill="#faf9f5"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#24323d}.grid{stroke:#d7dddf;stroke-width:1}.axis{stroke:#52616b;stroke-width:1}</style>']
    text(s,28,34,title,21)
    return s


def axes(s, box, xmin, xmax, ymin, ymax, xlabel, ylabel):
    x,y,w,h=box
    for j in range(6):
        yy=y+h*j/5; xx=x+w*j/5
        s.append(f'<line x1="{x}" x2="{x+w}" y1="{yy:.4f}" y2="{yy:.4f}" class="grid"/>')
        text(s,x-10,yy+4,f'{ymax-(ymax-ymin)*j/5:.3g}',12,'end')
        text(s,xx,y+h+22,f'{xmin+(xmax-xmin)*j/5:.3g}',12,'middle')
    s.append(f'<path d="M{x},{y}V{y+h}H{x+w}" fill="none" class="axis"/>')
    text(s,x+w/2,y+h+44,xlabel,14,'middle');text(s,x,y-18,ylabel,14)
    return lambda a,b:(x+w*(a-xmin)/(xmax-xmin),y+h-h*(b-ymin)/(ymax-ymin))


def line(s, points, color, dash=''):
    coords=' '.join(f'{x:.4f},{y:.4f}' for x,y in points)
    s.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')


def figures(out, cases, interactions, temperatures):
    rows=[r for r in interactions if r['case']==cases[0]['name']]
    xmin,xmax=rows[0]['U_over_t'],rows[-1]['U_over_t']
    s=start('Hubbard dimer: exact spectrum and exchange gap','Data from interaction.csv, first case; energy normalized by its t. Triplet is threefold degenerate.',680)
    text(s,85,78,'N=2; symmetric two-site model; all energies below divided by hopping t')
    ymax=max(r['E_plus_over_t'] for r in rows)*1.05
    f=axes(s,(85,145,430,330),xmin,xmax,-2.2,max(2,ymax),'U / t','energy / t')
    for key,col,dash in [('E_minus_over_t','#126a88',''),('E_triplet_over_t','#38774c','2 3'),('E_double_odd_over_t','#702c80','5 3'),('E_plus_over_t','#cf6427','8 3 2 3')]:
        line(s,[f(r['U_over_t'],r[key]) for r in rows],col,dash)
    g=axes(s,(620,145,430,330),xmin,xmax,0,2.1,'U / t','singlet-triplet gap / t')
    line(s,[g(r['U_over_t'],r['gap_over_t']) for r in rows],'#126a88')
    approx=[r for r in rows if r['U_over_t']>=2]
    if approx:
        line(s,[g(r['U_over_t'],r['J2_over_t']) for r in approx],'#cf6427','5 3')
    text(s,85,555,'Spectrum: blue lower singlet; green dotted triplet x3; purple dashed odd double; orange dash-dot upper singlet')
    text(s,85,580,'Gap: blue exact; orange dashed 4 t^2 / U (only U/t >= 2 shown; approximation is controlled at much larger U/t)')
    text(s,85,620,'Finite dimer spectrum; no thermodynamic phase transition or material parameter inference.')
    s.append('</svg>');(out/'spectrum.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')
    s=start('Charge suppression and spin correlation have different scales','Data from interaction.csv; all cases use the card temperature and their own hopping t.',620+45*len(cases))
    f=axes(s,(85,135,430,320),xmin,xmax,0,.55,'U / t','total double occupancy D')
    g=axes(s,(620,135,430,320),xmin,xmax,-.8,.05,'U / t','spin dot product / hbar^2')
    colors=['#126a88','#cf6427','#702c80','#38774c','#ae3e5b','#756a26','#2466b0','#989027','#252525','#8a509d','#8c3939','#176655']
    line(s,[f(r['U_over_t'],r['ground_D']) for r in rows],'#24323d','3 3')
    line(s,[g(r['U_over_t'],r['ground_spin']) for r in rows],'#24323d','3 3')
    for j,c in enumerate(cases):
        rr=[r for r in interactions if r['case']==c['name']]
        line(s,[f(r['U_over_t'],r['thermal_D']) for r in rr],colors[j],DASHES[j])
        line(s,[g(r['U_over_t'],r['thermal_spin']) for r in rr],colors[j],DASHES[j])
        y=540+45*j;text(s,85,y,c['name']);text(s,85,y+17,f"t={c['t_eV']:.6g} eV, T={c['temperature_K']:.6g} K (U varied)")
        s.append(f'<line x1="28" x2="75" y1="{y-4}" y2="{y-4}" stroke="{colors[j]}" stroke-width="3" stroke-dasharray="{DASHES[j]}"/>')
    text(s,85,600+45*len(cases),'Black dotted: zero-T ground state. Charge correlation C(n1,n2) = -D; spin correlation alone is not an entanglement test.')
    s.append('</svg>');(out/'correlation.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')
    s=start('Heating a fixed-N dimer: charge and conditional spin state','Data from thermal.csv. Right panel concerns only the state postselected to one particle at each site.',640+45*len(cases))
    ts=[r['temperature_K'] for r in temperatures]
    f=axes(s,(85,135,430,320),min(ts),max(ts),0,.55,'temperature (K)','total double occupancy D')
    g=axes(s,(620,135,430,320),min(ts),max(ts),0,1.05,'temperature (K)','postselected singlet probability')
    line(s,[g(min(ts),.5),g(max(ts),.5)],'#24323d','3 3')
    for j,c in enumerate(cases):
        rr=[r for r in temperatures if r['case']==c['name']]
        line(s,[f(r['temperature_K'],r['D_total']) for r in rr],colors[j],DASHES[j])
        line(s,[g(r['temperature_K'],r['conditioned_singlet_probability']) for r in rr],colors[j],DASHES[j])
        y=540+45*j;text(s,85,y,c['name']);text(s,85,y+17,f"t={c['t_eV']:.6g} eV, U={c['U_eV']:.6g} eV (T varied)")
        s.append(f'<line x1="28" x2="75" y1="{y-4}" y2="{y-4}" stroke="{colors[j]}" stroke-width="3" stroke-dasharray="{DASHES[j]}"/>')
    text(s,85,600+45*len(cases),'Dotted threshold p_singlet=1/2: conditional two-spin state is entangled above, separable at or below.')
    text(s,85,620+45*len(cases),'The projection changes the state; it does not classify the full unconditioned fermionic density matrix.')
    s.append('</svg>');(out/'thermal.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')


def build(card, out):
    results=[]; spectral=[]; matrices=[]; temps=[]; interactions=[]
    for c in card['cases']:
        t,u,temp=c['t_eV'],c['U_eV'],c['temperature_K']
        result=thermal(t,u,temp);result['case']=c;results.append(result)
        sp=result['spectrum'];ops=result['operators']
        for name,e,v,p in zip(sp['labels'],sp['energies_eV'],sp['vectors'],result['probabilities']):
            projector=[[v[i]*v[j] for j in range(6)] for i in range(6)]
            spectral.append(dict(case=c['name'],state=name,energy_eV=e,probability=p,
                                 D_total=expectation(projector,ops['D']),spin_dot_dimensionless=expectation(projector,ops['spin']),vector=';'.join(map(str,v))))
        for name,mat in [('H_eV',ops['H']),('rho',result['rho']),('D',ops['D']),('spin_dimensionless',ops['spin']),('gamma',result['gamma'])]:
            for a,row in enumerate(mat):
                for b,value in enumerate(row):
                    matrices.append(dict(case=c['name'],matrix=name,dimension=len(mat),a=a,b=b,value=value))
        for temp in card['temperatures_K']:
            z=thermal(t,u,temp)
            temps.append(dict(case=c['name'],temperature_K=temp,**z['observables']))
        for ratio in card['interaction_ratios']:
            z=thermal(t,t*ratio,c['temperature_K']);sp=z['spectrum']
            interactions.append(dict(case=c['name'],U_over_t=ratio,U_eV=t*ratio,temperature_K=c['temperature_K'],
                E_minus_over_t=sp['energies_eV'][0]/t,E_triplet_over_t=0.0,
                E_double_odd_over_t=ratio,E_plus_over_t=sp['energies_eV'][-1]/t,
                gap_over_t=sp['gap_eV']/t,J2_over_t=sp['J2_eV']/t if sp['J2_eV'] is not None else '',
                J2_relative_error=sp['J2_relative_error'] if sp['J2_relative_error'] is not None else '',
                ground_D=sp['ground_D'],ground_spin=sp['ground_spin'],ground_bonding_per_spin=sp['ground_n_bonding_per_spin'],
                thermal_D=z['observables']['D_total'],thermal_spin=z['observables']['spin_dot_dimensionless'],
                thermal_charge_connected=z['observables']['charge_connected'],
                conditioned_singlet_probability=z['observables']['conditioned_singlet_probability']))
    payload=dict(inputs=card,kB_eV_per_K=KB,basis=BASIS,basis_labels=LABELS,results=results,
        boundaries='Exactly N=2, t>0, U>=0, symmetric dimer. Triplet weights counted individually. Conditional PPT is for two local spins after one-particle-per-site projection, not for the full fermionic state.')
    # Serialization/finite-number validation occurs before the output directory exists.
    encoded=json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    for row in spectral+matrices+temps+interactions:
        if any(isinstance(v,float) and not math.isfinite(v) for v in row.values()):
            raise ValueError('nonfinite output')
    out.mkdir(parents=True,exist_ok=False)
    csv_file(out/'spectrum.csv',spectral);csv_file(out/'matrices.csv',matrices)
    csv_file(out/'thermal.csv',temps);csv_file(out/'interaction.csv',interactions)
    (out/'results.json').write_text(encoded,encoding='utf-8')
    figures(out,card['cases'],interactions,temps)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    try:
        card=read_card(args.inputs)
        if args.output.exists() or args.output.is_symlink():
            raise ValueError('output exists or is a symlink; choose a new directory')
        build(card,args.output)
    except (ValueError,OSError,TypeError,ArithmeticError) as e:
        ap.error(str(e))
    print(f'wrote 8 files to {args.output}')


if __name__=='__main__':
    main()
