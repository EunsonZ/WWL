#!/usr/bin/env python3
"""Exact finite payoff/deviation checks; this is not a general Nash existence algorithm."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path


def maxima(values):
    top = max(values)
    return [i for i, value in enumerate(values) if value == top]


def pure_equilibria(a, b):
    return [[i, j] for i in range(len(a)) for j in range(len(a[0]))
            if i in maxima([a[r][j] for r in range(len(a))])
            and j in maxima(b[i])]


def expected(matrix, p, q):
    return p * q * matrix[0][0] + p * (1-q) * matrix[0][1] + (1-p) * q * matrix[1][0] + (1-p) * (1-q) * matrix[1][1]


def deviations(a, b, p, q):
    row = [q*a[i][0] + (1-q)*a[i][1] for i in range(2)]
    col = [p*b[0][j] + (1-p)*b[1][j] for j in range(2)]
    current = [expected(a,p,q), expected(b,p,q)]
    return dict(row_pure=row, column_pure=col, current=current,
                max_unilateral_gain=[max(row)-current[0],max(col)-current[1]])


def isolated_interior(a, b):
    """Only the nonsingular two-by-two, fully supported candidate; not degenerate support enumeration."""
    den_q = a[0][0]-a[1][0]-a[0][1]+a[1][1]
    den_p = b[0][0]-b[0][1]-b[1][0]+b[1][1]
    if not den_q or not den_p:
        return None
    q = (a[1][1]-a[0][1])/den_q
    p = (b[1][1]-b[1][0])/den_p
    if not (0 < p < 1 and 0 < q < 1):
        return None
    check = deviations(a,b,p,q)
    assert check['max_unilateral_gain'] == [0,0]
    return dict(p=p,q=q,check=check)


def parse_game(game):
    a,b = [[F(v) for v in row] for row in game['A']], [[F(v) for v in row] for row in game['B']]
    if len(a)!=2 or len(b)!=2 or any(len(row)!=2 for row in a+b):
        raise ValueError('input examples require two-by-two payoff matrices')
    return a,b


def run(inp):
    out={}
    parsed={}
    for name, game in inp['games'].items():
        a,b=parse_game(game)
        parsed[name]=(a,b)
        cells=[]
        for i in range(2):
            for j in range(2):
                cells.append(dict(row_action=i,column_action=j,
                    row_best_responses=maxima([a[r][j] for r in range(2)]),
                    column_best_responses=maxima(b[i]),
                    row_payoff=a[i][j],column_payoff=b[i][j]))
        out[name]=dict(cells=cells,pure_equilibria=pure_equilibria(a,b),
                       isolated_interior=isolated_interior(a,b))
    transforms={}
    alpha,beta=F(inp['affine_row']['scale']),F(inp['affine_row']['shift'])
    if alpha<=0: raise ValueError('a utility-preserving affine scale must be positive')
    for name in ['weighted_two','migration_three']:
        a,b=parsed[name]
        cube=[[u**3 for u in row] for row in a]
        affine=[[alpha*u+beta for u in row] for row in a]
        old=out[name]['isolated_interior']
        assert old is not None
        transforms[name]=dict(cube_matrix=cube,cube_interior=isolated_interior(cube,b),
                              old_mix_after_cube=deviations(cube,b,old['p'],old['q']),
                              affine_interior=isolated_interior(affine,b))
    a,b=parsed['matching_pennies']
    profile=[0,0]
    cycle=[profile]
    for _ in range(4):
        i,j=profile
        ri=maxima([a[r][j] for r in range(2)])
        cj=maxima(b[i])
        assert len(ri)==len(cj)==1
        profile=[ri[0],cj[0]]
        cycle.append(profile)
    # Observed-action variant: column's plan lists response after H then response after T.
    plans=[[0,0],[0,1],[1,0],[1,1]]
    seq_a=[[a[i][plan[i]] for plan in plans] for i in range(2)]
    seq_b=[[b[i][plan[i]] for plan in plans] for i in range(2)]
    ca,cb=parsed['coordination']
    correlated=[(F(1,2),0,0),(F(1,2),1,1)]
    shared_payoffs=[sum(prob*matrix[i][j] for prob,i,j in correlated) for matrix in [ca,cb]]
    return dict(identity=inp['identity'],games=out,transforms=transforms,
                matching_simultaneous_best_response_cycle=cycle,
                observed_action=dict(column_plans=plans,A=seq_a,B=seq_b,pure_equilibria=pure_equilibria(seq_a,seq_b)),
                coordination_shared_coin=dict(joint=[[F(1,2),F(0)],[F(0),F(1,2)]],expected=shared_payoffs),
                coordination_independent_half=deviations(ca,cb,F(1,2),F(1,2)))


def figure(result,inp):
    # Display the actual matching-pennies input's pure action values and support thresholds.
    a,b=parse_game(inp['games']['matching_pennies'])
    eq=result['games']['matching_pennies']['isolated_interior']
    pstar,qstar=eq['p'],eq['q']
    if (a,b)!=([[F(1),F(-1)],[F(-1),F(1)]],[[-F(1),F(1)],[F(1),-F(1)]]):
        raise ValueError('the teaching figure is specifically for matching pennies +/-1')
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="980" height="450" viewBox="0 0 980 450">',
       '<title>Matching pennies: pure action utilities and mutual best responses</title>',
       '<desc>Left: row H utility 2q-1 and T utility 1-2q intersect at q=one half. Right: blue row best response and dashed red column best response meet only at p=q=one half. Central full horizontal and vertical segments represent indifference, not a learning trajectory.</desc>',
       '<rect width="980" height="450" fill="white"/>',
       '<style>text{font-family:Arial,sans-serif;font-size:15px;fill:#18212c}.head{font-size:19px;font-weight:bold}.axis{stroke:#263238;stroke-width:1.5}.grid{stroke:#dce2e8;stroke-width:1}</style>',
       '<text x="30" y="30" class="head">A. Row action utilities given q</text>',
       '<text x="515" y="30" class="head">B. Mutual best responses in (p,q)</text>']
    left,right,top,bottom=80,430,80,340
    x=lambda q:left+float(q)*(right-left)
    y=lambda u:bottom-(float(u)+1)/2*(bottom-top)
    for u in [-1,0,1]:
        s += [f'<line x1="{left}" y1="{y(u)}" x2="{right}" y2="{y(u)}" class="grid"/>',f'<text x="45" y="{y(u)+5}">{u}</text>']
    s += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',f'<line x1="{left}" y1="{y(0)}" x2="{right}" y2="{y(0)}" class="axis"/>']
    for q in [F(0),F(1,2),F(1)]:s.append(f'<text x="{x(q)-5}" y="365">{q}</text>')
    for i,color,dash in [(0,'#2563a6',''),(1,'#b34438','stroke-dasharray="7 4"')]:
        vals=[F(q)*a[i][0]+(1-F(q))*a[i][1] for q in [0,1]]
        s.append(f'<line x1="{x(0)}" y1="{y(vals[0])}" x2="{x(1)}" y2="{y(vals[1])}" stroke="{color}" stroke-width="3" {dash}/>')
    s += [f'<circle cx="{x(qstar)}" cy="{y(0)}" r="5" fill="#18212c"/>',
          '<text x="90" y="65">Utility (not money)</text>',
          '<text x="90" y="395">Solid H: 2q-1; dashed T: 1-2q</text>',
          '<text x="150" y="425">q = P(column H)</text>']
    l,r,t,bt=575,910,80,340
    xx=lambda p:l+float(p)*(r-l)
    yy=lambda q:bt-float(q)*(bt-t)
    for v in [F(0),F(1,2),F(1)]:
        s += [f'<line x1="{xx(v)}" y1="{t}" x2="{xx(v)}" y2="{bt}" class="grid"/>',
              f'<line x1="{l}" y1="{yy(v)}" x2="{r}" y2="{yy(v)}" class="grid"/>',
              f'<text x="{xx(v)-5}" y="365">{v}</text>',f'<text x="535" y="{yy(v)+5}">{v}</text>']
    s += [f'<line x1="{l}" y1="{t}" x2="{l}" y2="{bt}" class="axis"/>',f'<line x1="{l}" y1="{bt}" x2="{r}" y2="{bt}" class="axis"/>']
    blue=[[(0,0),(0,qstar)],[(0,qstar),(1,qstar)],[(1,qstar),(1,1)]]
    red=[[(0,1),(pstar,1)],[(pstar,0),(pstar,1)],[(pstar,0),(1,0)]]
    for segments,color,dash in [(blue,'#2563a6',''),(red,'#b34438','stroke-dasharray="7 4"')]:
        for (p0,q0),(p1,q1) in segments:
            s.append(f'<line x1="{xx(p0)}" y1="{yy(q0)}" x2="{xx(p1)}" y2="{yy(q1)}" stroke="{color}" stroke-width="4" {dash}/>')
    s += [f'<circle cx="{xx(pstar)}" cy="{yy(qstar)}" r="7" fill="#18212c" stroke="white" stroke-width="2"/>',
          '<text x="585" y="65">q = P(column H)</text>',
          '<text x="585" y="395">Solid blue: row BR; dashed red: column BR</text>',
          '<text x="665" y="425">p = P(row H)</text>', '</svg>']
    return '\n'.join(s)+'\n'


def encode(value):
    if isinstance(value,F):return str(value)
    raise TypeError(type(value).__name__)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args()
    inp=json.loads(args.input.read_text(encoding='utf-8'))
    result=run(inp)
    plot=figure(result,inp)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'exact-results.json').write_text(json.dumps(result,default=encode,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output_dir/'best-responses.svg').write_text(plot,encoding='utf-8')
    print('PASS: exact pure deviations, nonsingular interior candidates, utility transformations, cycle and observed-action plans')


if __name__=='__main__':main()
