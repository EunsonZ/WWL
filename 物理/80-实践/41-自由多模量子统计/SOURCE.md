---
title: 自由多模量子统计源码镜像
aliases: []
stage: 0
sources: []
prerequisites:
  - "[[物理/80-实践/41-自由多模量子统计/README]]"
---

# 自由多模量子统计源码镜像

真源为同目录 `free_fock.py`；执行和输出见 [[物理/80-实践/41-自由多模量子统计/README#复算入口与输出|复算入口]]。

<!-- code-sync: ./free_fock.py -->

```python
#!/usr/bin/env python3
"""Finite free-mode canonical enumeration and untruncated grand-canonical moments.
Only the total-number display is truncated for bosons. Python standard library.
"""
import argparse
import csv
import html
import itertools
import json
import math
from pathlib import Path
import re

KB = 1.380649e-23 / 1.602176634e-19  # eV/K, exact defining SI constants


def number(x, low, high, name):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x < low or x > high or not math.isfinite(x):
        raise ValueError(f'{name}: expected finite number in [{low}, {high}]')
    return float(x)


def integer(x, low, high, name):
    if isinstance(x, bool) or not isinstance(x, int) or not low <= x <= high:
        raise ValueError(f'{name}: expected integer in [{low}, {high}]')
    return x


def keys(obj, expected, name):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f'{name}: expected exactly {sorted(expected)}')


def load_card(path):
    raw = Path(path).read_text(encoding='utf-8')
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
    keys(card, ['units', 'cases', 'temperatures_K', 'number_cutoff'], 'top level')
    if card['units'] != {'energy': 'eV', 'temperature': 'K'}:
        raise ValueError('units must be energy=eV and temperature=K')
    cases = card['cases']
    if not isinstance(cases, list) or not 1 <= len(cases) <= 12:
        raise ValueError('cases: expected 1..12 cases')
    names = set()
    for c in cases:
        keys(c, ['name', 'statistics', 'energies_eV', 'labels', 'upper_modes', 'N', 'temperature_K'], 'case')
        name = c['name']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', name) or name in names:
            raise ValueError('case name must be unique ASCII identifier')
        names.add(name)
        if c['statistics'] not in ('boson', 'fermion'):
            raise ValueError('statistics must be boson or fermion')
        es = c['energies_eV']
        if not isinstance(es, list) or not 2 <= len(es) <= 6:
            raise ValueError('energies_eV: expected 2..6 modes')
        c['energies_eV'] = [number(e, 0, 2, 'energy') for e in es]
        m = len(es)
        labels = c['labels']
        if not isinstance(labels, list) or len(labels) != m or any(not isinstance(s, str) or not 1 <= len(s) <= 24 or any(ord(ch) < 32 or 0xD800 <= ord(ch) <= 0xDFFF or ord(ch) in (0xFFFE, 0xFFFF) for ch in s) for s in labels) or len(set(labels)) != m:
            raise ValueError('labels: unique 1..24 character labels, one per mode')
        u = c['upper_modes']
        if not isinstance(u, list) or not 1 <= len(u) < m:
            raise ValueError('upper_modes: nonempty proper subset')
        for a in u:
            integer(a, 0, m - 1, 'upper mode')
        if len(set(u)) != len(u):
            raise ValueError('upper_modes: duplicate index')
        integer(c['N'], 1, 6, 'N')
        if c['statistics'] == 'fermion' and c['N'] >= m:
            raise ValueError('paired finite-mu fermion comparison requires 0 < N < number of modes')
        c['temperature_K'] = number(c['temperature_K'], 10, 2000, 'temperature')
    ts = card['temperatures_K']
    if not isinstance(ts, list) or not 2 <= len(ts) <= 121:
        raise ValueError('temperatures_K: expected 2..121 samples')
    card['temperatures_K'] = [number(t, 10, 2000, 'sweep temperature') for t in ts]
    if any(a >= b for a, b in zip(ts, ts[1:])):
        raise ValueError('temperatures_K must be strictly increasing')
    integer(card['number_cutoff'], max(c['N'] for c in cases), 80, 'number_cutoff')
    return card


def occupations(m, n, stats):
    if stats == 'fermion':
        for filled in itertools.combinations(range(m), n):
            s = set(filled)
            yield tuple(int(a in s) for a in range(m))
    elif m == 1:
        yield (n,)
    else:
        for k in range(n + 1):
            for rest in occupations(m - 1, n - k, stats):
                yield (k,) + rest


def canonical(c, temp):
    theta = KB * temp
    es = c['energies_eV']
    states = list(occupations(len(es), c['N'], c['statistics']))
    energies = [math.fsum(e * n for e, n in zip(es, ns)) for ns in states]
    # Ground energy of this N sector, including Pauli filling for fermions.
    e0 = min(energies)
    weights = [math.exp(-(e - e0) / theta) for e in energies]
    w = math.fsum(weights)
    ps = [x / w for x in weights]
    means = [math.fsum(p * ns[a] for p, ns in zip(ps, states)) for a in range(len(es))]
    cov = [[math.fsum(p * (ns[a] - means[a]) * (ns[b] - means[b]) for p, ns in zip(ps, states)) for b in range(len(es))] for a in range(len(es))]
    logz = math.log(w) - e0 / theta
    return dict(states=states, energies=energies, probabilities=ps, means=means,
                covariance=cov, logZ=logz, Z=math.exp(logz), dimension=len(states),
                mean_N=math.fsum(means), variance_N=0.0,
                mean_upper=math.fsum(means[a] for a in c['upper_modes']))


def logistic(x):
    if x >= 0:
        q = math.exp(-x)
        return q / (1 + q)
    q = math.exp(x)
    return 1 / (1 + q)


def softplus(x):
    return max(x, 0.0) + math.log1p(math.exp(-abs(x)))


def logsumexp(values):
    top = max(values)
    return top + math.log(math.fsum(math.exp(x - top) for x in values))


def grand(c, temp):
    theta = KB * temp
    es = c['energies_eV']
    n = c['N']
    if c['statistics'] == 'boson':
        factors = [math.exp(-(e - min(es)) / theta) for e in es]
        lo, hi = 0.0, 1.0
        for _ in range(100):
            z = (lo + hi) / 2
            qs = [z * f for f in factors]
            total = math.fsum(q / (1 - q) for q in qs)
            if total < n:
                lo = z
            else:
                hi = z
        z = (lo + hi) / 2
        qs = [z * f for f in factors]
        mu = min(es) + theta * math.log(z)
        means = [q / (1 - q) for q in qs]
        variances = [v * (1 + v) for v in means]
        logxi = -math.fsum(math.log1p(-q) for q in qs)
        logq = [math.log(z) - (e - min(es)) / theta for e in es]
    else:
        lo, hi = min(es) - 64 * theta, max(es) + 64 * theta
        ordered = sorted(es)
        for _ in range(100):
            mu = (lo + hi) / 2
            # Equal holes in the lowest N modes and particles in remaining modes.
            # Logarithmic sums resolve a low-T gap even when total rounds to N.
            holes = logsumexp([-softplus((mu - e) / theta) for e in ordered[:n]])
            particles = logsumexp([-softplus((e - mu) / theta) for e in ordered[n:]])
            if particles < holes:
                lo = mu
            else:
                hi = mu
        mu = (lo + hi) / 2
        means = [logistic((e - mu) / theta) for e in es]
        variances = [v * (1 - v) for v in means]
        qs = means
        xs = [(mu - e) / theta for e in es]
        logxi = math.fsum(max(x, 0) + math.log1p(math.exp(-abs(x))) for x in xs)
        logq = xs  # log fugacity weight, distinct from Bernoulli probability
    mean = math.fsum(means)
    var = math.fsum(variances)
    return dict(mu_eV=mu, means=means, variances=variances,
                covariance=[[variances[a] if a == b else 0.0 for b in range(len(es))] for a in range(len(es))],
                logXi=logxi, mean_N=mean, variance_N=var, second_moment_N=var + mean * mean,
                mean_upper=math.fsum(means[a] for a in c['upper_modes']),
                root_residual=mean - n, parameters=qs, log_weights=logq)


def distribution(c, g, cutoff):
    m = len(c['energies_eV'])
    k = cutoff if c['statistics'] == 'boson' else m
    p = [1.0] + [0.0] * k
    for q in g['parameters']:
        mode = [(1 - q) * q**n for n in range(k + 1)] if c['statistics'] == 'boson' else [1 - q, q]
        p = [math.fsum(p[n - j] * mode[j] for j in range(min(n, len(mode) - 1) + 1)) for n in range(k + 1)]
    mass = math.fsum(p)
    r1 = math.fsum(n * x for n, x in enumerate(p))
    r2 = math.fsum(n * n * x for n, x in enumerate(p))
    conditional = [x / mass for x in p]
    cm = r1 / mass
    cv = r2 / mass - cm * cm
    raw = [1 - mass, g['mean_N'] - r1, g['second_moment_N'] - r2]
    scale = [1, max(1, g['mean_N']), max(1, g['second_moment_N'])]
    if any(x < -1e-11 * s for x, s in zip(raw, scale)):
        raise ValueError('negative tail beyond floating-point endpoint tolerance')
    tails = [max(0.0, x) for x in raw]
    if c['statistics'] == 'boson':
        ell = k // m + 1
        a = math.fsum(q**ell for q in g['parameters'])
        bounds = [a, (ell + g['mean_N']) * a, (g['variance_N'] + (ell + g['mean_N'])**2) * a]
    else:
        ell, bounds = None, [0.0, 0.0, 0.0]
        tails = [0.0, 0.0, 0.0]  # exactly finite full support; raw residuals retained below
    return dict(probabilities=p, conditioned_probabilities=conditional, cutoff=k,
                retained_mass=mass, tail_mass=tails[0], tail_first_N=tails[1], tail_second_N=tails[2],
                raw_tail_residuals=raw, tail_bounds=bounds, union_threshold=ell,
                conditioned_mean_N=cm, conditioned_variance_N=max(0.0, cv))


def paired(c, cutoff):
    can = canonical(c, c['temperature_K'])
    gc = grand(c, c['temperature_K'])
    dist = distribution(c, gc, cutoff)
    # Independent per-mode grand-canonical log probabilities at each fixed-N state.
    logs = [math.fsum(n * x for n, x in zip(ns, gc['log_weights'])) - gc['logXi'] for ns in can['states']]
    conditional = [math.exp(lp) / dist['probabilities'][c['N']] for lp in logs]
    # At extreme thermal gaps P(N) stays positive for this matched-N domain.
    error = max(abs(p - q) for p, q in zip(can['probabilities'], conditional))
    return dict(case=c, canonical=can, grand_canonical=gc, number=dist,
                gc_given_N_probabilities=conditional, conditional_N_max_error=error)


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def svg_start(title, description, width=1100, height=660):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<title>{html.escape(title)}</title><desc>{html.escape(description)}</desc>',
            '<rect width="100%" height="100%" fill="#faf9f5"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#24323d;font-size:13px}.title{font-size:21px;font-weight:bold}.subtitle{font-size:13px}.axis{stroke:#52616b;stroke-width:1}.grid{stroke:#d7dddf;stroke-width:1}.label{font-size:14px}</style>',
            f'<text x="28" y="34" class="title">{html.escape(title)}</text>']


def text_svg(s, x, y, label, cls=''):
    s.append(f'<text x="{x:.4f}" y="{y:.4f}" class="{cls}">{html.escape(str(label))}</text>')


def axis(s, box, xmin, xmax, ymin, ymax, xlabel, ylabel):
    x, y, w, h = box
    for j in range(6):
        yy = y + h * j / 5
        val = ymax - (ymax - ymin) * j / 5
        s.append(f'<line x1="{x}" x2="{x+w}" y1="{yy:.4f}" y2="{yy:.4f}" class="grid"/>')
        text_svg(s, x - 46, yy + 4, f'{val:.3g}')
    s.append(f'<path d="M{x},{y}V{y+h}H{x+w}" fill="none" class="axis"/>')
    for j in range(6):
        xx = x + w * j / 5
        text_svg(s, xx - 12, y + h + 22, f'{xmin+(xmax-xmin)*j/5:.3g}')
    text_svg(s, x + w/2 - 40, y + h + 45, xlabel, 'label')
    text_svg(s, x, y - 16, ylabel, 'label')
    return lambda a,b: (x + w*(a-xmin)/(xmax-xmin), y+h - h*(b-ymin)/(ymax-ymin))


def curve(s, xy, color, dash='', points=False):
    pts = ' '.join(f'{x:.4f},{y:.4f}' for x,y in xy)
    s.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
    if points:
        for x,y in xy:
            s.append(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="3" fill="{color}"/>')


def figures(out, results, sweep):
    selected = []
    for stats in ('boson', 'fermion'):
        match = next((r for r in results if r['case']['statistics'] == stats), None)
        if match:
            selected.append(match)
    s = svg_start('Fixed N and matched-mean grand canonical states', 'Total-number probabilities from number-distribution.csv. Raw GC is not renormalized after truncation.')
    for j,r in enumerate(selected):
        c,d = r['case'],r['number']
        box = (85 + 535*j, 155, 440, 340)
        text_svg(s,box[0],80,c['name'])
        text_svg(s,box[0],100,f"{c['statistics']}, M={len(c['labels'])}, N={c['N']}, T={c['temperature_K']:.3f} K")
        text_svg(s,box[0],120,f"energies (eV): {', '.join(f'{e:.4g}' for e in c['energies_eV'])}; tail={d['tail_mass']:.3g}")
        f=axis(s,box,0,d['cutoff'],0,1.05,'total N (count)','probability (dimensionless)')
        for vals,col,dash in [(d['probabilities'],'#126a88',''),(d['conditioned_probabilities'],'#cf6427','5 3'),([float(n==c['N']) for n in range(d['cutoff']+1)],'#702c80','2 3')]:
            curve(s,[f(n,p) for n,p in enumerate(vals)],col,dash,True)
    text_svg(s,85,575,'blue solid: GC raw P(N); orange dashed: GC conditioned on N <= cutoff; purple dotted: canonical fixed N')
    text_svg(s,85,600,'Matching mean N fixes one expectation; it leaves particle-number fluctuations and mode correlations different.')
    s.append('</svg>'); (out/'number.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')
    s=svg_start('Mode covariance: a fixed total creates correlations', 'Covariance matrices from mode-moments.csv; mode order follows each input card.',1100,1050)
    for j,r in enumerate(selected):
        c=r['case']; m=len(c['labels']); size=260/m
        for k,(key,label) in enumerate([('canonical','canonical'),('grand_canonical','grand canonical')]):
            x=95+535*k; y=115+440*j
            cov=r[key]['covariance']; vmax=max(.01,max(abs(v) for row in cov for v in row))
            text_svg(s,x,y-50,c['name'])
            text_svg(s,x,y-32,f'{label} / covariance (count squared)')
            for a in range(m):
                text_svg(s,x-35,y+(a+.55)*size,a)
                text_svg(s,x+(a+.4)*size,y-10,a)
                for b in range(m):
                    v=cov[a][b]; strength=min(1,abs(v)/vmax)
                    base=(39,112,143) if v>=0 else (177,78,39)
                    rgb=tuple(round(250+(z-250)*strength*.7) for z in base)
                    s.append(f'<rect x="{x+b*size:.4f}" y="{y+a*size:.4f}" width="{size:.4f}" height="{size:.4f}" fill="rgb{rgb}" stroke="#faf9f5"/>')
                    font_size = 9 if m >= 5 else 11
                    s.append(f'<text x="{x+(b+.5)*size:.4f}" y="{y+(a+.55)*size:.4f}" text-anchor="middle" style="font-size:{font_size}px">{v:.3g}</text>')
            for a, label in enumerate(c['labels']):
                text_svg(s,x,y+280+17*a,f'mode {a}: {label}')
    text_svg(s,95,1020,'Blue cells: positive; orange: negative. Each panel uses its own maximum shade; numeric values permit comparison.')
    s.append('</svg>'); (out/'covariance.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')
    s=svg_start('Temperature changes occupation and number fluctuations','All curves from sweep.csv; canonical N is fixed and grand canonical mu is refitted at each T.',1100,620+45*len(results))
    colors=['#126a88','#cf6427','#702c80','#38774c','#ae3e5b','#756a26','#2466b0','#989027','#252525','#8a509d','#8c3939','#176655']
    temps=[row['temperature_K'] for row in sweep]
    ymax=max(row['mean_upper'] for row in sweep)*1.08
    vmax=max(row['variance_N'] for row in sweep)*1.08
    f1=axis(s,(85,125,440,330),min(temps),max(temps),0,max(.1,ymax),'temperature (K)','mean upper occupation (count)')
    f2=axis(s,(620,125,440,330),min(temps),max(temps),0,max(.1,vmax),'temperature (K)','variance total N (count squared)')
    for i,r in enumerate(results):
        name=r['case']['name']; col=colors[i]
        for ens,dash in [('canonical',''),('grand_canonical','5 3')]:
            rows=[z for z in sweep if z['case']==name and z['ensemble']==ens]
            curve(s,[f1(z['temperature_K'],z['mean_upper']) for z in rows],col,dash)
            curve(s,[f2(z['temperature_K'],z['variance_N']) for z in rows],col,dash)
        yy = 540+45*i
        text_svg(s,85,yy,f"{name}: {r['case']['statistics']}, N={r['case']['N']}")
        energies = ', '.join(f'{e:.6g}' for e in r['case']['energies_eV'])
        text_svg(s,85,yy+17,f'energies (eV): [{energies}]')
        s.append(f'<line x1="65" x2="80" y1="{yy-4}" y2="{yy-4}" stroke="{col}" stroke-width="3"/>')
    text_svg(s,85,600+45*len(results),'Solid: canonical. Dashed: GC with matched mean N. Finite mode model; no phase transition or material spectrum is inferred.')
    s.append('</svg>'); (out/'thermal.svg').write_text('\n'.join(s)+'\n',encoding='utf-8')


def build(card, out):
    results=[paired(c,card['number_cutoff']) for c in card['cases']]
    states=[]; modes=[]; nums=[]; sweep=[]
    for r in results:
        c=r['case']; ca=r['canonical']; gc=r['grand_canonical']; d=r['number']
        for ns,e,p,q in zip(ca['states'],ca['energies'],ca['probabilities'],r['gc_given_N_probabilities']):
            states.append(dict(case=c['name'],occupations=';'.join(map(str,ns)),energy_eV=e,canonical_probability=p,gc_given_N_probability=q))
        for ens,z in [('canonical',ca),('grand_canonical',gc)]:
            for a,label in enumerate(c['labels']):
                for b,other in enumerate(c['labels']):
                    modes.append(dict(case=c['name'],ensemble=ens,a=a,b=b,label_a=label,label_b=other,energy_a_eV=c['energies_eV'][a],mean_a=z['means'][a],variance_a=z['covariance'][a][a],covariance_ab=z['covariance'][a][b]))
        for n,(p,q) in enumerate(zip(d['probabilities'],d['conditioned_probabilities'])):
            nums.append(dict(case=c['name'],total_N=n,canonical_probability=int(n==c['N']),gc_raw_probability=p,gc_conditioned_cutoff_probability=q))
        for t in card['temperatures_K']:
            for ens,z in [('canonical',canonical(c,t)),('grand_canonical',grand(c,t))]:
                sweep.append(dict(case=c['name'],ensemble=ens,temperature_K=t,mean_N=z['mean_N'],variance_N=z['variance_N'],mean_upper=z['mean_upper'],mu_eV=z.get('mu_eV','')))
    # Compute and validate everything before making output; never overwrite an existing directory.
    out.mkdir(parents=True,exist_ok=False)
    write_csv(out/'canonical-states.csv',list(states[0]),states)
    write_csv(out/'mode-moments.csv',list(modes[0]),modes)
    write_csv(out/'number-distribution.csv',list(nums[0]),nums)
    write_csv(out/'sweep.csv',list(sweep[0]),sweep)
    payload=dict(units=card['units'],kB_eV_per_K=KB,inputs=card,results=results,
                 numerical_notes='Z may underflow to zero while logZ and shifted probabilities remain valid; tail raw residuals retained, negative endpoint residuals up to 1e-11 relative scale are reported as zero. Fermion full-support tails are exactly zero.')
    (out/'results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    figures(out,results,sweep)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    try:
        card=load_card(args.inputs)
        if args.output.exists():
            raise ValueError('output already exists; choose a new directory')
        build(card,args.output)
    except (ValueError,OSError,TypeError,OverflowError,ZeroDivisionError) as e:
        ap.error(str(e))
    print(f'wrote 8 files to {args.output}')


if __name__=='__main__':
    main()
```
