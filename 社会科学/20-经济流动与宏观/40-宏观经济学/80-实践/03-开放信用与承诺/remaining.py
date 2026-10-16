#!/usr/bin/env python3
"""Exact finite synthetic models. Python >=3.9, standard library only.
No empirical estimation, random sampling, policy advice, or external writes.
"""
import argparse
from fractions import Fraction as F
from html import escape
import json
from pathlib import Path


def rat(x):
    if not isinstance(x, (str, int)) or isinstance(x, bool):
        raise ValueError('rational inputs must be strings or integers')
    return F(x)


def solve(matrix, rhs):
    """Independent equation-level Gaussian elimination, not model formulas."""
    n = len(rhs)
    a = [[F(v) for v in row] + [F(rhs[i])] for i, row in enumerate(matrix)]
    for j in range(n):
        pivot = next((i for i in range(j, n) if a[i][j]), None)
        if pivot is None:
            raise ValueError('singular closure')
        a[j], a[pivot] = a[pivot], a[j]
        q = a[j][j]
        a[j] = [v/q for v in a[j]]
        for i in range(n):
            if i != j:
                q = a[i][j]
                a[i] = [x-q*y for x, y in zip(a[i], a[j])]
    return [row[-1] for row in a]


def open_parameters(raw):
    p = {k: rat(raw[k]) for k in ('c', 'm', 'b', 'nu', 'ell', 'h')}
    if not (0 < p['c'] < 1 and p['m'] >= 0
            and all(p[k] > 0 for k in ('b', 'nu', 'ell', 'h'))):
        raise ValueError('open economy requires 0<c<1, m>=0, b/nu/ell/h>0')
    return p


def open_economy(p, raw):
    c, m, b, nu, ell, h = (p[k] for k in ('c', 'm', 'b', 'nu', 'ell', 'h'))
    A, D, L = 1-c+m, h*(1-c+m)+ell*(b+nu), b+nu+h*nu
    g, tax = ([rat(v) for v in raw[k]] for k in ('g', 'tax'))
    if len(g) != 2 or len(tax) != 2 or g != tax:
        raise ValueError('two periods and current balanced fiscal funding required')
    f = [g[t]-c*tax[t] for t in range(2)]
    regime = raw['regime']
    if regime == 'peg':
        if raw['mu'] is not None or rat(raw['epsilon2']) != 0:
            raise ValueError('peg makes mu endogenous and requires epsilon2=0')
        p1, j1, e1 = f[1]/nu, F(0), F(0)
        x0 = (f[0]+b*p1)/A
        j0, e0 = F(0), F(0)
        mu = [ell*x0, p1]
        # Original equations, unknown x0, mu0, p1, mu1.
        direct = solve([[A,0,-b,0], [ell,-1,0,0],
                        [0,0,nu,0], [0,0,1,-1]], [f[0],0,f[1],0])
        assert direct == [x0,mu[0],p1,mu[1]]
        e2 = F(0)
    elif regime in ('float', 'controls'):
        if raw['mu'] is None or len(raw['mu']) != 2:
            raise ValueError('float/controls require two money inputs')
        mu = [rat(v) for v in raw['mu']]
        if regime == 'float':
            e2 = rat(raw['epsilon2'])
            p1 = (h*f[1]+(b+nu)*mu[1]+h*nu*e2)/L
            j1, e1 = (p1-mu[1])/h, e2-(p1-mu[1])/h
            x0 = (h*f[0]+h*b*p1+h*nu*e1+(b+nu)*mu[0])/D
            j0, e0 = (ell*x0-mu[0])/h, e1-(ell*x0-mu[0])/h
            # Six original equations, unknown x0,j0,e0,p1,j1,e1.
            direct = solve([[A,b,-nu,-b,0,0], [ell,-h,0,0,0,0],
                            [0,1,1,0,0,-1], [0,0,0,nu,b,-nu],
                            [0,0,0,1,-h,0], [0,0,0,0,1,1]],
                           [f[0],mu[0],0,f[1],mu[1],e2])
        else:
            if raw['epsilon2'] is not None:
                raise ValueError('controls drop UIP and do not use an exchange anchor')
            e2 = None
            j1 = f[1]/b
            p1 = mu[1]+h*j1
            e1 = p1
            dc = h*(1-c)+b*ell
            x0 = (h*f[0]+h*b*p1+b*mu[0])/dc
            j0, e0 = (ell*x0-mu[0])/h, m*x0/nu
            direct = solve([[A,b,-nu,-b,0,0], [ell,-h,0,0,0,0],
                            [-m,0,nu,0,0,0], [0,0,0,nu,b,-nu],
                            [0,0,0,1,-h,0], [0,0,0,-nu,0,nu]],
                           [f[0],mu[0],0,f[1],mu[1],0])
        assert direct == [x0,j0,e0,p1,j1,e1]
    else:
        raise ValueError('unknown open regime')
    nodes = []
    for t, (x,j,e,p,pp) in enumerate([(x0,j0,e0,F(0),p1),
                                     (F(0),j1,e1,p1,p1)]):
        rho = j-(pp-p)
        dc, di, nx = c*(x-tax[t]), -b*rho, nu*(e-p)-m*x
        residuals = {'IS':A*x-f[t]+b*rho-nu*(e-p),
                     'money':ell*x-h*j-mu[t]+p,
                     'goods':x-dc-di-g[t]-nx}
        if regime != 'controls':
            residuals['UIP'] = j-((e1 if t == 0 else e2)-e)
        else:
            residuals['NX_zero'] = nx
        assert all(v == 0 for v in residuals.values())
        C, I, G, Y = 60+dc, 20+di, 20+g[t], 100+x
        if min(C,I,G,Y) <= 0:
            raise ValueError('open input leaves positive C/I/G/Y model domain')
        nodes.append(dict(t=t,x=x,j=j,epsilon=e,p=p,mu=mu[t],rho=rho,
                          dC=dc,dI=di,dG=g[t],NX=nx,CA=nx,FA=nx,
                          C=C,I=I,G=G,Y=Y,residuals=residuals))
    return dict(regime=regime,parameters=p,A=A,D=D,L=L,epsilon2=e2,
                nodes=nodes,exact_linear_system_matches=True)


def household(y, durable, beta, R, theta, Q):
    y0, y1 = y
    if min(y0,y1,beta,R) <= 0 or durable < 0 or Q < 0 or not 0 <= theta <= 1:
        raise ValueError('credit incomes/beta/R positive; h/Q>=0; theta in [0,1]')
    limit = theta*Q*durable/R
    bu = (beta*R*y0-y1)/(R*(1+beta))
    b = max(bu,-limit)
    c0, c1 = y0-b, y1+R*b
    eta = 1/c0-beta*R/c1
    assert c0 > 0 and c1 > 0 and eta >= 0 and eta*(b+limit) == 0
    return dict(income=y,durable=durable,limit=limit,b_unconstrained=bu,
                b=b,c0=c0,c1=c1,eta=eta,strictly_binding=(eta > 0))


def credit_economy(raw, Q, transfer=F(0)):
    beta, R, theta = (rat(raw[k]) for k in ('beta','R','theta'))
    ya, yb = ([rat(v) for v in raw[k]['income']] for k in ('A','B'))
    if len(ya) != 2 or len(yb) != 2:
        raise ValueError('two credit dates required')
    ya, yb = [ya[0]+transfer,ya[1]], [yb[0]-transfer,yb[1]]
    a = household(ya,rat(raw['A']['durable']),beta,R,theta,Q)
    b = household(yb,rat(raw['B']['durable']),beta,R,theta,Q)
    C0, C1, assets = a['c0']+b['c0'],a['c1']+b['c1'],a['b']+b['b']
    Y0, Y1 = ya[0]+yb[0],ya[1]+yb[1]
    # Net foreign interest is (R-1)*assets in date 1, unlike the R=1 baseline.
    TB0, TB1 = Y0-C0,Y1-C1
    NPI1 = (R-1)*assets
    CA0, CA1 = TB0,TB1+NPI1
    assert CA0 == assets and CA1 == -assets and assets+CA1 == 0
    domestic_loans = max(-a['b'],0)+max(-b['b'],0)
    deposits = max(a['b'],0)+max(b['b'],0)
    assert domestic_loans+assets == deposits
    bank = dict(domestic_loans=domestic_loans,deposits=deposits,
                signed_external_assets=assets,
                date1_asset_receipts=R*(domestic_loans+assets),
                date1_deposit_payment=R*deposits)
    # The representative comparison deliberately has no borrowing constraint.
    rb = (beta*R*Y0-Y1)/(R*(1+beta))
    return dict(Q=Q,transfer=transfer,A=a,B=b,C0=C0,C1=C1,net_b=assets,
                TB=[TB0,TB1],NPI=[F(0),NPI1],CA=[CA0,CA1],FA=[CA0,CA1],
                terminal_net_asset=assets+CA1,bank=bank,
                representative_unconstrained=dict(b=rb,c0=Y0-rb,c1=Y1+R*rb))


def risk_rival(raw, beta, R):
    y0, ys, ps, limit, b = (rat(raw['income0']),[rat(v) for v in raw['income1']],
                          [rat(v) for v in raw['probabilities']],
                          rat(raw['loan_limit']),rat(raw['candidate_b']))
    if len(ys) != len(ps) or not ys or sum(ps) != 1 or min(ps) <= 0 or limit < 0:
        raise ValueError('risk probabilities positive/sum 1; nonnegative limit')
    c0, cs = y0-b,[y+R*b for y in ys]
    if min([c0]+cs) <= 0 or b < -limit:
        raise ValueError('risk candidate infeasible')
    derivative = -1/c0+beta*R*sum(p/c for p,c in zip(ps,cs))
    curvature = -1/c0**2-beta*R**2*sum(p/c**2 for p,c in zip(ps,cs))
    assert curvature < 0
    return dict(b=b,c0=c0,state_c1=cs,probabilities=ps,
                objective_derivative=derivative,objective_second_derivative=curvature,
                optimal_interior=(b > -limit and derivative == 0),
                scope='one realised high-income record coincides; not full observational distribution')


def commitment(alpha, lam, target, Fs):
    if min(alpha,lam,target) <= 0 or any(v < 0 for v in Fs):
        raise ValueError('commitment alpha/lambda/xbar positive, F>=0')
    K, piD = lam*alpha**2,lam*alpha*target
    low, high = piD**2/(1+K),piD**2*(1+K)
    def loss(pi,e):
        return pi**2+lam*(alpha*(pi-e)-target)**2
    def best(e,Fcost):
        br = lam*alpha*(alpha*e+target)/(1+K)
        v0 = loss(F(0),e)
        vb = loss(br,e)+(Fcost if br != 0 else 0)
        return sorted(set(([F(0)] if v0 <= vb else [])+([br] if vb <= v0 else [])))
    rows=[]
    for fc in Fs:
        outcomes=[]
        for pi in (F(0),piD):
            if pi in best(pi,fc):
                outcomes.append(dict(e=pi,pi=pi,x=F(0),base_loss=loss(pi,pi),
                                     total_loss=loss(pi,pi)+(fc if pi != 0 else 0),
                                     private_loss=F(0)))
        predicted=([F(0)] if fc >= low else [])+([piD] if fc <= high else [])
        assert [v['pi'] for v in outcomes] == predicted
        rows.append(dict(F=fc,outcomes=outcomes,
                         policy_best_at_zero_forecast=best(F(0),fc),
                         policy_best_at_discretion_forecast=best(piD,fc)))
    return dict(alpha=alpha,lambda_=lam,xbar=target,K=K,pi_D=piD,
                commitment_loss=loss(F(0),F(0)),discretion_base_loss=loss(piD,piD),
                temptation_pi=piD/(1+K),temptation_loss=loss(piD/(1+K),F(0)),
                F_low=low,F_high=high,rows=rows)


def compute(inp):
    op=inp['open']; p=open_parameters(op['parameters'])
    scenarios={s['name']:open_economy(p,s) for s in op['scenarios']}
    if len(scenarios) != len(op['scenarios']):
        raise ValueError('duplicate scenario names')
    for key in ('fiscal_float','fiscal_peg','money_float','money_peg'):
        if key not in scenarios:
            raise ValueError('four named baseline scenarios required for diagram')
        expected = 'float' if key.endswith('_float') else 'peg'
        if scenarios[key]['regime'] != expected:
            raise ValueError('named diagram scenario must retain its float/peg regime')
    if not op['import_grid'] or not inp['credit']['Q_grid']:
        raise ValueError('nonempty diagram grids required')
    imports=[]
    for rawm in op['import_grid']:
        m=rat(rawm)
        if m < 0: raise ValueError('import grid must be nonnegative')
        A=1-p['c']+m; D=p['h']*A+p['ell']*(p['b']+p['nu'])
        imports.append(dict(m=m,float_fiscal=p['h']*(1-p['c'])/D,
                            peg_fiscal=(1-p['c'])/A))
    migration_p=dict(p,m=rat(op['migration_m']))
    open_parameters({k:str(v) for k,v in migration_p.items()})
    migration={s['name']:open_economy(migration_p,s) for s in op['scenarios']}
    cr=inp['credit']; qb,ql,tr=(rat(cr[k]) for k in ('Q_base','Q_low','transfer'))
    credit={name:credit_economy(cr,q,t) for name,q,t in
            [('baseline',qb,F(0)),('low_Q',ql,F(0)),('low_Q_transfer',ql,tr)]}
    qgrid=[credit_economy(cr,rat(q)) for q in cr['Q_grid']]
    risk=risk_rival(cr['risk_rival'],rat(cr['beta']),rat(cr['R']))
    cp=inp['commitment']; alpha,lam,target=(rat(cp[k]) for k in ('alpha','lambda','xbar'))
    com=commitment(alpha,lam,target,[rat(x) for x in cp['F']])
    com_m=commitment(alpha,rat(cp['migration_lambda']),target,[rat(x) for x in cp['migration_F']])
    return dict(identity=inp['identity'],open=scenarios,import_multipliers=imports,
                migration_open=migration,credit=credit,credit_Q_grid=qgrid,risk_rival=risk,
                commitment=com,migration_commitment=com_m,
                verification={'all_arithmetic':'exact rational',
                              'open_formula_vs_original_linear_system':True,
                              'household_KKT_and_bank_external_accounts':True,
                              'commitment_candidates_vs_loss_comparison':True})


def serial(x):
    if isinstance(x,F): return str(x)
    if isinstance(x,dict): return {k:serial(v) for k,v in x.items()}
    if isinstance(x,list): return [serial(v) for v in x]
    return x


def fmt(x):
    return str(x) if abs(float(x)) < 100 else '%.2f' % float(x)


class SVG:
    def __init__(self,title,desc):
        self.s=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="510" viewBox="0 0 1100 510">',
                '<title>'+escape(title)+'</title><desc>'+escape(desc)+'</desc>',
                '<rect width="1100" height="510" fill="white"/>',
                '<style>text{font-family:Arial,sans-serif;fill:#182b3a;font-size:15px}.small{font-size:13px}.title{font-size:20px;font-weight:bold}</style>']
        self.text(30,30,title,'title')
    def text(self,x,y,t,cls=''):
        self.s.append('<text x="%g" y="%g" class="%s">%s</text>'%(x,y,cls,escape(str(t))))
    def line(self,x1,y1,x2,y2,color='#aab5bc',width=1):
        self.s.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'%(x1,y1,x2,y2,color,width))
    def circle(self,x,y,r,color):
        self.s.append('<circle cx="%g" cy="%g" r="%g" fill="%s"/>'%(x,y,r,color))
    def rect(self,x,y,w,h,color):
        self.s.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>'%(x,y,w,h,color))
    def finish(self): return '\n'.join(self.s+['</svg>'])+'\n'


def open_svg(r):
    s=SVG('Open economy: closure and import leakage',
          'Synthetic exact rational outputs. Left: date-0 output by input scenario. Right: balanced-budget fiscal derivatives holding future deviations zero; not empirical multipliers.')
    s.text(45,65,'Date-0 output deviation x (goods units)')
    labels=[('fiscal_float','F / float'),('fiscal_peg','F / peg'),
            ('money_float','M / float'),('money_peg','M / peg')]
    vals=[r['open'][k]['nodes'][0]['x'] for k,_ in labels]
    lo=min(F(0),*vals); hi=max(F(1),*vals); span=hi-lo
    def y(v):return 390-270*float((v-lo)/span)
    s.line(65,y(0),505,y(0),'#687d8c')
    for i,(key,label) in enumerate(labels):
        x=100+i*105;v=r['open'][key]['nodes'][0]['x']
        s.rect(x-22,min(y(v),y(0)),44,max(1,abs(y(v)-y(0))), '#2878a0' if i%2==0 else '#df8b2b')
        s.text(x-30,(y(v)-10 if v>=0 else y(v)+20),fmt(v),'small')
        s.text(x-38,420,label,'small')
    s.text(50,460,'F/M are the fiscal/money scenarios in inputs.json.','small')
    rows=r['import_multipliers']
    xmin=min(x['m'] for x in rows);xmax=max(x['m'] for x in rows)
    if xmax == xmin: xmax=xmin+1
    ymax=max(F(1,10),*(v[k] for v in rows for k in ('float_fiscal','peg_fiscal')))
    def xx(v):return 630+400*float((v-xmin)/(xmax-xmin))
    def yy(v):return 390-270*float(v/ymax)
    s.text(615,65,'Balanced-budget fiscal dx / dG')
    for k,color,label in [('float_fiscal','#2878a0','float'),('peg_fiscal','#df8b2b','peg')]:
        pts=sorted(rows,key=lambda x:x['m'])
        for a,b in zip(pts,pts[1:]):s.line(xx(a['m']),yy(a[k]),xx(b['m']),yy(b[k]),color,3)
        for a in pts:s.circle(xx(a['m']),yy(a[k]),4,color)
        s.line(650,460+(20 if k=='peg_fiscal' else 0),680,460+(20 if k=='peg_fiscal' else 0),color,3)
        s.text(690,465+(20 if k=='peg_fiscal' else 0),label,'small')
    for m in sorted(set(v['m'] for v in rows)):
        s.line(xx(m),390,xx(m),396);s.text(xx(m)-10,415,fmt(m),'small')
    for t in range(5):
        v=ymax*F(t,4);s.line(625,yy(v),1035,yy(v),'#d9e0e4');s.text(582,yy(v)+4,'%.2f'%float(v),'small')
    s.text(930,440,'import slope m','small')
    return s.finish()


def frictions_svg(r):
    s=SVG('Different mechanisms: collateral and enforceable commitment',
          'Left plots exact household consumption as exogenous recoverable collateral Q changes. Right shows pure equilibrium inflation outcomes as external deviation cost F changes. Separate models, no empirical data.')
    grid=sorted(r['credit_Q_grid'],key=lambda a:a['Q'])
    q0=min(v['Q'] for v in grid);q1=max(v['Q'] for v in grid)
    if q1 == q0:q1=q0+1
    vmin=min(F(0),*(v[k] for v in grid for k in ('C0','C1')))
    vmax=max(F(1),*(v[k] for v in grid for k in ('C0','C1')))
    def xx(q):return 75+410*float((q-q0)/(q1-q0))
    def yy(v):return 390-270*float((v-vmin)/(vmax-vmin))
    s.text(45,65,'Aggregate consumption (goods units)')
    for k,color in [('C0','#2878a0'),('C1','#df8b2b')]:
        for a,b in zip(grid,grid[1:]):s.line(xx(a['Q']),yy(a[k]),xx(b['Q']),yy(b[k]),color,3)
        for a in grid:s.circle(xx(a['Q']),yy(a[k]),3,color)
    for t in range(5):
        v=vmin+(vmax-vmin)*F(t,4);s.line(70,yy(v),490,yy(v),'#d9e0e4');s.text(30,yy(v)+4,'%.1f'%float(v),'small')
    for v in grid:s.text(xx(v['Q'])-8,414,fmt(v['Q']),'small')
    s.text(365,442,'collateral value Q','small')
    s.line(80,465,110,465,'#2878a0',3);s.text(120,470,'C0','small')
    s.line(200,465,230,465,'#df8b2b',3);s.text(240,470,'C1','small')
    c=r['commitment'];low,high,pid=c['F_low'],c['F_high'],c['pi_D']
    end=max(high*F(3,2),*(v['F'] for v in c['rows']))
    def xf(v):return 640+390*float(v/end)
    s.text(605,65,'Pure inflation outcomes, not an estimated response')
    s.rect(xf(low),105,xf(high)-xf(low),290,'#f2e3cb')
    s.text(xf(low)+8,125,'both supported','small')
    s.line(640,350,1030,350,'#9baab5')
    s.line(640,185,1030,185,'#d9e0e4')
    s.text(585,355,'pi=0','small');s.text(575,190,'pi='+fmt(pid),'small')
    s.line(xf(low),350,xf(end),350,'#2878a0',5);s.circle(xf(low),350,5,'#2878a0')
    s.line(xf(F(0)),185,xf(high),185,'#bc5a45',5);s.circle(xf(high),185,5,'#bc5a45')
    for f,label in [(F(0),'0'),(low,'low='+fmt(low)),(high,'high='+fmt(high)),(end,fmt(end))]:
        s.line(xf(f),390,xf(f),398);s.text(xf(f)-12,420,label,'small')
    s.text(900,448,'deviation cost F','small')
    s.text(605,475,'Boundary dots included; tie choices must be compatible.','small')
    return s.finish()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    inp=json.loads(args.input.read_text())
    result=compute(inp)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'results.json').write_text(json.dumps(serial(result),ensure_ascii=False,indent=2)+'\n')
    (args.output_dir/'open.svg').write_text(open_svg(result))
    (args.output_dir/'frictions.svg').write_text(frictions_svg(result))
    print('PASS: exact original-equation, household/account, and commitment-loss checks; synthetic models only')


if __name__ == '__main__':
    main()
