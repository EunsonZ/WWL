#!/usr/bin/env python3
"""Exact finite-state algebra and declared witnesses. Not empirical asset pricing or an arbitrage searcher."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path


def vector(values): return [F(x) for x in values]
def matrix(rows): return [vector(row) for row in rows]
def dot(a,b): return sum((x*y for x,y in zip(a,b)),F(0))
def transpose(a): return [list(col) for col in zip(*a)]
def matvec(a,h): return [dot(row,h) for row in a]
def append_column(a,col): return [row+[value] for row,value in zip(a,col)]


def solve(a,b):
    """Rational RREF: a particular solution plus a basis of the kernel, including inconsistent RHS."""
    n=len(a[0])
    if len(a)!=len(b) or any(len(row)!=n for row in a): raise ValueError('matrix/vector shape mismatch')
    aug=[list(row)+[rhs] for row,rhs in zip(a,b)]
    pivots=[]
    row=0
    for col in range(n):
        pivot=next((r for r in range(row,len(aug)) if aug[r][col]),None)
        if pivot is None: continue
        aug[row],aug[pivot]=aug[pivot],aug[row]
        value=aug[row][col]
        aug[row]=[v/value for v in aug[row]]
        for r in range(len(aug)):
            if r!=row:
                value=aug[r][col]
                aug[r]=[v-value*w for v,w in zip(aug[r],aug[row])]
        pivots.append(col)
        row+=1
        if row==len(aug): break
    kernel=[]
    for free in [j for j in range(n) if j not in pivots]:
        v=[F(0)]*n; v[free]=F(1)
        for r,col in enumerate(pivots): v[col]=-aug[r][free]
        kernel.append(v)
    consistent=not any(all(v==0 for v in r[:n]) and r[n]!=0 for r in aug)
    particular=[F(0)]*n if consistent else None
    if consistent:
        for r,col in enumerate(pivots): particular[col]=aug[r][n]
        assert matvec(a,particular)==b
    for v in kernel: assert all(x==0 for x in matvec(a,v))
    return dict(consistent=consistent,rank=len(pivots),particular=particular,kernel=kernel)


def probabilities(values):
    p=vector(values)
    if not p or any(x<=0 for x in p) or sum(p)!=1: raise ValueError('P must have positive entries summing to one')
    return p


def representation(pi,p,a,prices):
    if len(pi)!=len(p) or len(a)!=len(p):raise ValueError('state count mismatch')
    b=prices[0]
    if b<=0 or any(row[0]!=1 for row in a):raise ValueError('first security must pay one in every state with positive price')
    rf=1/b
    assert matvec(transpose(a),pi)==prices
    m=[s/prob for s,prob in zip(pi,p)]
    q=[rf*s for s in pi]
    em=dot(p,m)
    assert em==b and sum(q)==1
    assets=[]
    for payoff,price in zip(transpose(a),prices):
        assert dot([prob*mi for prob,mi in zip(p,m)],payoff)==price
        if price<=0:
            assets.append(dict(price=price,return_defined=False));continue
        r=[x/price for x in payoff]
        er=dot(p,r)
        covariance=dot(p,[mi*ri for mi,ri in zip(m,r)])-em*er
        premium=er-rf
        assert premium==-covariance/em
        assets.append(dict(price=price,gross_returns=r,expected_gross_return=er,
                           covariance_m_return=covariance,expected_excess_gross_return=premium))
    return dict(P=p,pi=pi,m=m,Q=q,E_m=em,R_f=rf,assets=assets)


def witness(a,prices,h):
    payoff=matvec(a,h);cost=dot(prices,h)
    arbitrage=cost<=0 and all(x>=0 for x in payoff) and (cost<0 or any(x>0 for x in payoff))
    return dict(positions=h,initial_cost=cost,terminal_payoff=payoff,is_arbitrage=arbitrage)


def run(inp):
    d=inp['three_state'];a=matrix(d['A']);prices=vector(d['prices'])
    if a!=matrix([['1','1'],['1','2'],['1','3']]) or prices!=vector(['1','2']):
        raise ValueError('the three-state teaching/plot contract fixes B,S payments and prices')
    p=probabilities(d['physical_P']);up=probabilities(d['uniform_P'])
    family=solve(transpose(a),prices)
    h=vector(d['H'])
    if h!=vector(['0','0','1']):raise ValueError('H is fixed as the state-three unit claim')
    scenarios=[]
    for value in d['t_values']:
        t=F(value)
        if not 0<t<F(1,2):raise ValueError('consumer examples require strictly positive state prices: 0<t<1/2')
        pi=[x+t*v for x,v in zip(family['particular'],family['kernel'][0])]
        rep=representation(pi,p,a,prices)
        consumption=[1/mi for mi in rep['m']]
        euler=[dot(p,[pay/c for pay,c in zip(col,consumption)]) for col in transpose(a)]
        assert euler==prices  # log utility, beta=c0=1; global optimality follows from concavity in the text.
        scenarios.append(dict(t=t,representation=rep,H_extension_price=dot(pi,h),
                              log_consumer=dict(c0=F(1),c1=consumption,beta=F(1),euler_prices=euler)))
    ah=append_column(a,h)
    quotes=[]
    for value in d['H_quotes']:
        c=F(value);q=prices+[c]
        state=solve(transpose(ah),q)
        positive=all(x>0 for x in state['particular'])
        item=dict(H_quote=c,pi=state['particular'],strictly_positive_state_prices=positive,
                  complete=state['rank']==3)
        if c<=0:item['witness']=witness(ah,q,vector(['0','0','1']))
        elif c>=F(1,2):item['witness']=witness(ah,q,vector(['-1','1','-2']))
        if 'witness' in item:assert item['witness']['is_arbitrage']
        quotes.append(item)
    uniform=representation(vector(['1/4','1/2','1/4']),up,ah,prices+[F(1,4)])
    # Redundant column after completing with H: alternative positions remain, state prices are still unique.
    redundant=append_column(ah,vector(['2','2','2']))
    rq=prices+[F(1,4),F(2)]
    rsol=solve(redundant,h)
    for v in rsol['kernel']:assert dot(rq,v)==0
    binary=inp['binary'];ba=matrix(binary['A']);bq=vector(binary['prices']);call=vector(binary['call'])
    bpi=solve(transpose(ba),bq)['particular']
    ch=solve(ba,call)['particular'];call_price=dot(bq,ch)
    binary_cases=[representation(bpi,probabilities(case),ba,bq) for case in binary['physical_cases']]
    # A shadow state price at t=1/4 certifies all permitted positions with H>=0 at its quote 1/2.
    shadow=vector(['1/4','1/2','1/4'])
    restricted=dict(shadow_pi=shadow,shadow_H_price=dot(shadow,h),H_quote=F(1,2),
                    nonnegative_H_cost_slack=F(1,2)-dot(shadow,h),
                    forbidden_unrestricted_witness=witness(ah,prices+[F(1,2)],vector(['-1','1','-2'])))
    assert restricted['nonnegative_H_cost_slack']>0
    g=vector(d['migration_G'])
    return dict(identity=inp['identity'],three_state=dict(payment_matrix=a,prices=prices,state_price_family=family,
                H_replication=solve(a,h),scenarios=scenarios,H_quotes=quotes,
                uniform_P_complete_market=uniform,restricted_H=restricted,
                redundant_complete=dict(A=redundant,prices=rq,H_replication=rsol,state_prices=solve(transpose(redundant),rq)),
                migration_G=dict(payoff=g,replication=solve(a,g),price_family_intercept=dot(family['particular'],g),
                                 price_family_slope=dot(family['kernel'][0],g))),
                binary=dict(pi=bpi,call_positions_bank_units_stock_units=ch,
                            call_bank_initial_value=ch[0]*bq[0],call_price=call_price,
                            physical_cases=binary_cases))


def figure(result):
    # This diagram belongs to the fixed r=0 three-state economy above, not to arbitrary payment matrices.
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="980" height="460" viewBox="0 0 980 460">',
       '<title>Strictly positive state prices and the nonunique price of an unspanned state-three claim</title>',
       '<desc>Left: state-price coordinates pi1 and pi2 with pi3=1-pi1-pi2. The admissible segment is pi=(t,1-2t,t), zero less than t less than one half. Right: the new claim H=(0,0,1) has price c=t; both endpoints excluded under unrestricted trading. These are pricing weights, not real probabilities or confidence intervals.</desc>',
       '<rect width="980" height="460" fill="white"/>',
       '<style>text{font-family:Arial,sans-serif;font-size:14px;fill:#18212c}.head{font-size:18px;font-weight:bold}.axis{stroke:#263238;stroke-width:1.5}.grid{stroke:#dfe4e8;stroke-width:1}</style>',
       '<text x="25" y="30" class="head">A. State-price plane (R_f=1, sum pi=1)</text>',
       '<text x="505" y="30" class="head">B. H is unspanned: extension price c=t</text>']
    x=lambda v:85+float(v)*330
    y=lambda v:340-float(v)*250
    s += [f'<polygon points="{x(0)},{y(0)} {x(1)},{y(0)} {x(0)},{y(1)}" fill="#f6f8fb" stroke="#a6b0bb"/>',
          f'<line x1="{x(0)}" y1="{y(0)}" x2="{x(1)}" y2="{y(0)}" class="axis"/>',
          f'<line x1="{x(0)}" y1="{y(0)}" x2="{x(0)}" y2="{y(1)}" class="axis"/>',
          f'<line x1="{x(0)}" y1="{y(1)}" x2="{x(F(1,2))}" y2="{y(0)}" stroke="#2563a6" stroke-width="4"/>']
    for t in [F(0),F(1,2)]:s.append(f'<circle cx="{x(t)}" cy="{y(1-2*t)}" r="6" fill="white" stroke="#2563a6" stroke-width="2.5"/>')
    for row in result['three_state']['scenarios']:
        pi=row['representation']['pi']
        s.append(f'<circle cx="{x(pi[0])}" cy="{y(pi[1])}" r="4" fill="#2563a6"/>')
    s += ['<text x="45" y="85">pi2</text>','<text x="420" y="347">pi1</text>',
          '<text x="62" y="361">0</text>','<text x="243" y="361">1/2</text>','<text x="412" y="361">1</text>',
          '<text x="66" y="95">1</text>','<text x="150" y="105">(0,1,0): endpoint excluded</text>',
          '<text x="205" y="328">(1/2,0,1/2)</text>',
          '<text x="85" y="398">pi3=1-pi1-pi2; line: pi1=pi3=t</text>',
          '<text x="85" y="427">State prices are not physical P.</text>']
    xx=lambda t:565+float(t)*620
    yy=lambda c:340-float(c)*500
    s += [f'<line x1="{xx(0)}" y1="{yy(0)}" x2="{xx(F(1,2))}" y2="{yy(0)}" class="axis"/>',
          f'<line x1="{xx(0)}" y1="{yy(0)}" x2="{xx(0)}" y2="{yy(F(1,2))}" class="axis"/>',
          f'<line x1="{xx(0)}" y1="{yy(0)}" x2="{xx(F(1,2))}" y2="{yy(F(1,2))}" stroke="#2563a6" stroke-width="4"/>']
    for t in [F(0),F(1,2)]:
        s += [f'<circle cx="{xx(t)}" cy="{yy(t)}" r="6" fill="white" stroke="#2563a6" stroke-width="2.5"/>',
              f'<text x="{xx(t)-4}" y="363">{t}</text>',f'<text x="525" y="{yy(t)+4}">{t}</text>']
    for row in result['three_state']['scenarios']:
        s.append(f'<circle cx="{xx(row["t"])}" cy="{yy(row["H_extension_price"])}" r="4" fill="#2563a6"/>')
    s += ['<text x="535" y="65">c: current H price</text>', '<text x="895" y="347">t</text>',
          '<text x="580" y="110">c=1/2: -B+S-2H pays (0,1,0)</text>',
          '<text x="600" y="320">c=0: free H pays (0,0,1)</text>',
          '<text x="565" y="398">0 &lt; c &lt; 1/2 under two-way trading</text>',
          '<text x="565" y="427">Not a price forecast or confidence interval.</text>', '</svg>']
    return '\n'.join(s)+'\n'


def encode(value):
    if isinstance(value,F):return str(value)
    raise TypeError(type(value).__name__)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).with_name('results'))
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text(encoding='utf-8')))
    svg=figure(result)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'exact-results.json').write_text(json.dumps(result,default=encode,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output_dir/'state-prices.svg').write_text(svg,encoding='utf-8')
    print('PASS: rational solution spaces, replication, state prices, endpoint witnesses, P-Q-m identities and Euler moments')


if __name__=='__main__':main()
