---
type: code
stage: 0
aliases: []
sources: []
prerequisites: []
---
# 人口复算源码

源码是真源；返回[[社会科学/61-人口学/80-实践/01-人口分母生命表与投影/README|实践说明]]。

<!-- code-sync: 社会科学/61-人口学/80-实践/01-人口分母生命表与投影/demography.py -->

```python
#!/usr/bin/env python3
"""Exact arithmetic for explicit synthetic demographic scenarios; no fitting."""
import argparse
import copy
from fractions import Fraction as F
import json
from html import escape
from pathlib import Path
import platform
import sys


def fraction(x):
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        raise ValueError("numbers must be integers or rational strings")
    return F(x)


def life_table(spec):
    l = fraction(spec['radix'])
    if l <= 0:
        raise ValueError('positive radix required')
    rows = []
    end = F(0)
    for row in spec['finite']:
        x, n, m, a = (fraction(row[k]) for k in ('x', 'n', 'm', 'a'))
        if x != end or n <= 0 or m < 0 or not 0 <= a <= n:
            raise ValueError('invalid consecutive life-table interval')
        q = n*m/(1+(n-a)*m)
        if not 0 <= q <= 1:
            raise ValueError('m and a imply invalid probability; do not clip')
        d = l*q
        L = n*l-(n-a)*d
        rows.append(dict(x=x, n=n, m=m, a=a, q=q, l=l, d=d, L=L))
        l -= d
        end = x+n
    m = fraction(spec['tail_m'])
    if fraction(spec['tail_x']) != end or m <= 0:
        raise ValueError('tail must start at last boundary with positive m')
    rows.append(dict(x=end, n=None, m=m, a=None, q=F(1), l=l, d=l, L=l/m))
    T = F(0)
    for row in reversed(rows):
        T += row['L']
        row['T'] = T
        row['e'] = T/row['l'] if row['l'] else None
    return rows


def projection(spec, migration):
    p = list(map(fraction, spec['start']))
    b = list(map(fraction, spec['births_per_start_woman']))
    s = list(map(fraction, spec['survival']))
    u = list(map(fraction, migration))
    r = fraction(spec['birth_survival'])
    if len(p) != 4 or len(b) != 4 or len(s) != 4 or len(u) != 4:
        raise ValueError('four age groups required')
    if any(x < 0 for x in p+b) or any(not 0 <= x <= 1 for x in s+[r]):
        raise ValueError('invalid population, birth or survival input')
    if fraction(spec['step_years']) != 20:
        raise ValueError('age groups are twenty years wide')
    if type(spec['steps']) is not int or not 1 <= spec['steps'] <= 20:
        raise ValueError('steps must be integer in 1..20')
    result = []
    for t in range(spec['steps']):
        births = sum(x*y for x, y in zip(b, p))
        initial_deaths = sum((1-x)*y for x, y in zip(s, p))
        newborn_deaths = (1-r)*births
        nxt = [r*births, s[0]*p[0], s[1]*p[1], s[2]*p[2]+s[3]*p[3]]
        nxt = [x+y for x,y in zip(nxt,u)]
        if any(x < 0 for x in nxt):
            raise ValueError('end migration makes an age group negative')
        total = sum(nxt)
        if total != sum(p)+births-initial_deaths-newborn_deaths+sum(u):
            raise ArithmeticError('population balance failed')
        ratio = (nxt[0]+nxt[3])/(nxt[1]+nxt[2]) if nxt[1]+nxt[2] else None
        result.append(dict(step=t+1, start=p, births=births,
                           initial_deaths=initial_deaths, newborn_deaths=newborn_deaths,
                           end=nxt, total=total, age_dependency_ratio=ratio))
        p = nxt
    return result


def calculate(data):
    if data['kind'] != 'synthetic-teaching-only':
        raise ValueError('this program only accepts the declared teaching scenario')
    bal = {k: fraction(v) for k,v in data['balance'].items()}
    if any(x < 0 for x in bal.values()):
        raise ValueError('negative event count')
    end = bal['start']+bal['births']-bal['deaths']+bal['in']-bal['out']
    if end < 0:
        raise ValueError('negative end population')
    exposure = F(0)
    for _, a, b in data['traces']:
        a, b = fraction(a), fraction(b)
        if not 0 <= a <= b <= 1:
            raise ValueError('trace outside one year')
        exposure += b-a
    weights = list(map(fraction, data['standard_weights']))
    if len(weights) != 2 or sum(weights) != 1 or min(weights) < 0:
        raise ValueError('two common weights must be nonnegative and sum to one')
    rates = {}
    for name, row in data['rates'].items():
        E, D = (list(map(fraction, row[k])) for k in ('exposure','deaths'))
        if len(E) != 2 or len(D) != 2 or min(E) <= 0 or min(D) < 0:
            raise ValueError('invalid rate denominator or event count')
        m = [d/e for d,e in zip(D,E)]
        rates[name] = dict(m=m, crude=sum(D)/sum(E),
                           standardized=sum(w*x for w,x in zip(weights,m)))
    if len(data['life']['finite']) != 2:
        raise ValueError('this teaching comparison requires exactly two finite age intervals')
    tail = copy.deepcopy(data['life'])
    tail['tail_m'] = str(2*fraction(data['life']['tail_m']))
    early = copy.deepcopy(data['life'])
    early['finite'][0]['a'] = str(fraction(early['finite'][0]['n'])/4)
    return dict(end_population=end, trace_person_years=exposure, rates=rates,
                life=life_table(data['life']), changed_tail=life_table(tail),
                changed_early_timing=life_table(early),
                projection_closed=projection(data['projection'],[0]*4),
                projection_migration=projection(data['projection'],data['projection']['end_migration']))


def encode(value):
    if isinstance(value,F):
        return str(value)
    if isinstance(value,dict):
        return {k:encode(v) for k,v in value.items()}
    if isinstance(value,list):
        return [encode(v) for v in value]
    return value


def svg(result):
    # Geometry, descriptions and labels all use the calculated life-table rows.
    rows = [('baseline', result['life']), ('tail m doubled', result['changed_tail'])]
    colors = ['#31688e','#35b779','#f0bd38']
    totals = [table[0]['e'] for _, table in rows]
    max_total = max(totals)
    contribution = [[row['L']/table[0]['l'] for row in table] for _,table in rows]
    labels = [f"{row['x']}+" if row['n'] is None else f"{row['x']}-{row['x']+row['n']}"
              for row in rows[0][1]]
    details = []
    for j,(name,table) in enumerate(rows):
        components = ', '.join(f"{label}: {v}" for label,v in zip(labels,contribution[j]))
        details.append(f"{name}, tail m={table[-1]['m']}: contributions in years ({components}); e0={table[0]['e']}.")
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="405" viewBox="0 0 900 405">',
             '<title>Life expectancy is the sum of lived-year areas</title>',
             '<desc>'+escape('Synthetic life-table comparison. '+' '.join(details))+'</desc>',
             '<rect width="900" height="405" fill="white"/>',
             '<g font-family="sans-serif" font-size="18" fill="#18232b">',
             '<text x="30" y="35">Synthetic life table: contributions to e0 (years)</text>']
    for j,(label,table) in enumerate(rows):
        y=75+j*95
        parts.append(f'<text x="30" y="{y+27}">{label}</text>')
        x=220
        for k,v in enumerate(contribution[j]):
            width=float(v/max_total)*530 if max_total else 0
            parts.append(f'<rect x="{x:g}" y="{y}" width="{width:g}" height="44" fill="{colors[k]}" stroke="white"/>')
            if width >= 55:
                parts.append(f'<text x="{x+width/2:g}" y="{y+28}" text-anchor="middle" fill="black">{float(v):.4g}</text>')
            x+=width
        parts.append(f'<text x="{x+12:g}" y="{y+28}">sum = {float(table[0]["e"]):.4g}</text>')
    for k,label in enumerate(labels):
        y=280+33*k
        parts.append(f'<rect x="220" y="{y-16}" width="16" height="16" fill="{colors[k]}"/>')
        parts.append(f'<text x="248" y="{y}">{escape(label)}: {float(contribution[0][k]):.4g} / {float(contribution[1][k]):.4g} years (baseline / doubled)</text>')
    parts += ['<text x="220" y="388" font-size="14">Labels rounded to 4 significant digits; exact values in results.json and SVG description.</text>','</g></svg>']
    return '\n'.join(parts)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding='utf-8'))
    result=calculate(data)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'results.json').write_text(json.dumps(encode(result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.out/'life-years.svg').write_text(svg(result),encoding='utf-8')
    print(f'OK: end={result["end_population"]}, exposure={result["trace_person_years"]}, e0={result["life"][0]["e"]}')
    print(f'Python {platform.python_version()} ({sys.implementation.name}); standard library only')


if __name__=='__main__':
    main()
```
