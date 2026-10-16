#!/usr/bin/env python3
"""Small synthetic macro economies; stdlib only. No optimization or sampling package."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction as Q
import html
import json
import math
from pathlib import Path


def f(x):
    return float(Q(str(x)))


def fs(x):
    return str(x) if isinstance(x, Q) else x


def close(a, b, tol, label):
    if not (math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tol):
        raise AssertionError(label + ': ' + repr((a, b)))


def solow(spec, periods, tol):
    a, s, de, n, g = [Q(spec[z]) for z in ('alpha','s','delta','n','g')]
    if a != Q(1,2) or not (0<s<1 and 0<de<=1 and n>=0 and g>=0):
        raise ValueError('Solow alpha must be 1/2; 0<s<1, 0<delta<=1, n,g>=0')
    K0,A0,L0=[Q(spec[z]) for z in ('K0','A0','L0')]
    if min(K0,A0,L0)<=0:
        raise ValueError('positive K0/A0/L0 required; zero boundary is checked separately')
    G=(1+n)*(1+g); d=G-1+de
    ks=(s/d)**2; kg=(a/d)**2; lam=1-(1-a)*d/G
    k=float(K0/(A0*L0)); A=float(A0)
    rows=[]
    for t in range(periods+1):
        rows.append({'t':t,'k':k,'c_effective':(1-float(s))*math.sqrt(k),
                     'y_worker':A*math.sqrt(k),'c_worker':A*(1-float(s))*math.sqrt(k)})
        k=((1-float(de))*k+float(s)*math.sqrt(k))/float(G); A*=1+float(g)
    # Independent route: high precision original aggregate K,A,L, not k-update.
    max_error=0.0
    with localcontext() as ctx:
        ctx.prec=70
        dec=lambda z:Decimal(z.numerator)/Decimal(z.denominator)
        K,A,L=map(dec,(K0,A0,L0)); sd,dd,nd,gd=map(dec,(s,de,n,g))
        for t,row in enumerate(rows):
            Y=(K*A*L).sqrt()
            max_error=max(max_error,abs(row['k']-float(K/(A*L))),
                          abs(row['y_worker']-float(Y/L)))
            K=(1-dd)*K+sd*Y; A*=1+gd; L*=1+nd
    if max_error>tol:
        raise AssertionError('aggregate vs normalized path mismatch')
    for left,right in zip(rows,rows[1:]):
        z,w=left['k'],right['k']; eq=float(ks)
        if z<eq-tol and not z<w<eq+tol: raise AssertionError('lower bracket')
        if z>eq+tol and not eq-tol<w<z: raise AssertionError('upper bracket')
    return {'G':str(G),'d':str(d),'steady_k':str(ks),
            'steady_c_effective':str((1-s)*(s/d)),
            'golden_k':str(kg),'golden_s':str(a),'local_derivative':str(lam),
            'aggregate_max_abs_error':max_error,'zero_next_k':'0','path':rows}


def utility(a,b,k0,s):
    return (math.log1p(-s)/(1-b)+a*math.log(k0)/(1-a*b)
            +a*b*math.log(s)/((1-b)*(1-a*b)))


def planner(spec,periods,tol):
    aq,bq,kq=map(Q,(spec['alpha'],spec['beta'],spec['k0']))
    if aq!=Q(1,2) or Q(spec['delta'])!=1 or not (0<bq<1) or kq<=0:
        raise ValueError('planner contract: alpha=1/2, delta=1, 0<beta<1, k0>0')
    a,b,k0=map(float,(aq,bq,kq)); sq=aq*bq; s=float(sq)
    ks=sq**2; cs=(1-sq)*sq
    ff=-Q(1,4)/(sq**3)
    J=[[1/bq,Q(-1)],[cs*ff,1-bq*cs*ff]]
    ev=[aq,1/(aq*bq)]
    for z in ev:
        assert (J[0][0]-z)*(J[1][1]-z)-J[0][1]*J[1][0]==0
    out={}; residual=0.; patherr=0.; valerr=0.
    for name,sp in [('optimal',s),('golden',a)]:
        k=k0; rows=[]; partial=0.; xs=math.log(sp)/(1-a)
        for t in range(periods+1):
            c=(1-sp)*k**a; kn=sp*k**a
            exact=math.exp(xs+a**t*(math.log(k0)-xs))
            patherr=max(patherr,abs(k-exact))
            partial+=b**t*math.log(c)
            rows.append({'t':t,'k':k,'c':c,'k_next':kn,
                         'tvc_term':b**t*kn/c})
            if name=='optimal':
                cn=(1-sp)*kn**a
                residual=max(residual,abs(1/c-b*a*kn**(a-1)/cn))
            k=kn
        # Exact tail from terminal state, so no finite truncation claims infinite proof.
        value=utility(a,b,k0,sp)
        rebuilt=partial+b**(periods+1)*utility(a,b,k,sp)
        valerr=max(valerr,abs(value-rebuilt))
        out[name]={'s':sp,'steady_k':sp**(1/(1-a)),
                   'steady_c':(1-sp)*sp**(a/(1-a)),
                   'utility':value,'sum_plus_exact_tail':rebuilt,'path':rows}
    if max(residual,patherr,valerr)>tol: raise AssertionError('planner route residual')
    # Finite horizon dynamic programming: last period leaves no capital.
    finite=[]
    for N in (1,2,5,20,80,200):
        B=Q(0)
        for _ in range(N):
            share=bq*B/(1+bq*B)
            B=aq*(1+bq*B)
        finite.append({'remaining_periods':N,'initial_saving_fraction':str(share)})
    # A feasible Euler path that violates TVC; q = saving fraction, not a probability.
    bad=[]
    for t in (0,1,5,10,20):
        r=Q(1,2)*(Q(5,2)**t); q=(Q(2,5)+r)/(1+r)
        bad.append({'t':t,'saving_fraction':str(q),
                    'tvc':str(Q(4,5)**t*q/(1-q))})
    out.update({'steady_k_exact':str(ks),'steady_c_exact':str(cs),
                'jacobian':[[str(z) for z in row] for row in J],
                'eigenvalues':[str(z) for z in ev],
                'max_euler_error':residual,'max_path_error':patherr,
                'value_route_error':valerr,'finite_horizon':finite,
                'euler_without_tvc_fixed_beta_4_5':bad})
    if not out['optimal']['utility'] >= out['golden']['utility']-tol:
        raise AssertionError('welfare comparison')
    return out


def household(spec,tol):
    y,z,R,beta,ell=[Q(spec[k]) for k in ('y0','y1','R','beta','credit_limit')]
    if min(y,z,R,beta)<=0 or ell<0: raise ValueError('positive income/R/beta and nonnegative credit')
    bu=(beta*R*y-z)/(R*(1+beta))
    cases={}
    for name,lower in [('free',None),('credit',-ell),('no_borrow',Q(0))]:
        b=bu if lower is None else max(bu,lower)
        c0=y-b;c1=z+R*b
        if min(c0,c1)<=0: raise ValueError('infeasible household positive consumption')
        nu=1/c0-beta*R/c1
        assert nu>=0 and (lower is None and nu==0 or lower is not None and nu*(b-lower)==0)
        cases[name]={'b':str(b),'c0':str(c0),'c1':str(c1),'multiplier':str(nu)}
    # Independent strictly increasing Euler residual, fixed original risk exercise.
    h=lambda b:1/(2-b)-.5*(1/(4+b)+1/(12+b))
    lo,hi=-3.999999,1.999999
    for _ in range(180):
        mid=(lo+hi)/2
        if h(mid)<0:lo=mid
        else:hi=mid
    rb=(lo+hi)/2
    close(rb,(-11+math.sqrt(57))/2,tol,'risky root')
    # The closed two-household counterexample and an actual clearing equilibrium.
    for Rt in [Q(1),Q(1,4)]:
        bs=[max(Q(0),(Rt*x-w)/(Rt*2)) for x,w in [(Q(2),Q(8)),(Q(8),Q(2))]]
        cases['closed_R_'+str(Rt)]={'b':[str(v) for v in bs],
                'sum_b':str(sum(bs)),'sum_c0':str(10-sum(bs)),
                'sum_c1':str(10+Rt*sum(bs))}
    cases['risky_fixed_original']={'b':rb,'c0':2-rb,'euler_residual':h(rb),
                                  'no_borrow_multiplier':'1/3'}
    return cases


def svg_panel(parts,x,y,w,h,curves,xlabel,ylabel,title):
    values=[z for _,_,pts in curves for _,z in pts]
    xs=[z for _,_,pts in curves for z,_ in pts]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(values),max(values)
    pad=max(.05,(ymax-ymin)*.13); ymin-=pad;ymax+=pad
    X=lambda v:x+(v-xmin)/(xmax-xmin)*w
    Y=lambda v:y+h-(v-ymin)/(ymax-ymin)*h
    parts.append(f'<text x="{x}" y="{y-25}" class="head">{html.escape(title)}</text>')
    for j in range(5):
        v=ymin+(ymax-ymin)*j/4; yy=Y(v)
        parts.append(f'<path d="M{x},{yy:.3f}h{w}" class="grid"/><text x="{x-8}" y="{yy+4:.3f}" text-anchor="end">{v:.3g}</text>')
        xx=x+j*w/4; xv=xmin+(xmax-xmin)*j/4
        parts.append(f'<text x="{xx}" y="{y+h+21}" text-anchor="middle">{xv:.3g}</text>')
    parts.append(f'<path d="M{x},{y}v{h}h{w}" class="axis"/><text x="{x+w/2}" y="{y+h+44}" text-anchor="middle">{xlabel}</text><text x="{x}" y="{y-7}">{ylabel}</text>')
    for j,(name,col,pts) in enumerate(curves):
        line=' '.join(('M' if i==0 else 'L')+f'{X(t):.3f},{Y(v):.3f}' for i,(t,v) in enumerate(pts))
        parts.append(f'<path d="{line}" fill="none" stroke="{col}" stroke-width="2.4"/><path d="M{x},{y+h+73+j*20}h22" stroke="{col}" stroke-width="3"/><text x="{x+30}" y="{y+h+78+j*20}">{html.escape(name)}</text>')
        if len(pts)==2 and name.startswith('optimal s='):
            parts.append(f'<circle cx="{X((pts[0][0]+pts[1][0])/2):.3f}" cy="{Y(pts[0][1]):.3f}" r="4.5" fill="{col}"/>')


def svg(title,desc,panels):
    p=['<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="620" viewBox="0 0 1180 620" role="img">',
       '<title>'+html.escape(title)+'</title><desc>'+html.escape(desc)+'</desc>',
       '<style>text{font:14px sans-serif;fill:#17263a}.head{font-weight:bold;font-size:17px}.axis{fill:none;stroke:#45566b}.grid{stroke:#e2e7ef;fill:none}</style><rect width="1180" height="620" fill="white"/>',
       '<text x="65" y="32" class="head">'+html.escape(title)+'</text>']
    for i,(curves,xlab,ylab,heading) in enumerate(panels):
        svg_panel(p,75+580*i,100,455,300,curves,xlab,ylab,heading)
    p.append('<text x="65" y="604">Synthetic model paths; parameters are inputs, not empirical estimates.</text></svg>')
    return '\n'.join(p)+'\n'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    inp=json.loads(args.input.read_text());N=inp['periods'];tol=inp['tolerance']
    if not isinstance(N,int) or not 2<=N<=500 or not 0<tol<=1e-8:raise ValueError('bounded periods/tolerance required')
    base=inp['solow']; scenarios={}
    for name,changes in [('base',{}),('higher_s',{'s':base['higher_s']}),
          ('A_level',{'A0':str(Q(base['A0'])*Q(base['level_factor']))}),('A_growth',{'g':base['higher_g']})]:
        scenarios[name]=solow(dict(base,**changes),N,tol)
    mig=dict(base,s='1/5',delta='1/10',n='1/50',g='3/100',K0='1',A0='1',L0='1')
    scenarios['migration']=solow(mig,N,tol)
    plan=planner(inp['planner'],N,tol)
    pm=planner(dict(inp['planner'],beta=inp['planner']['migration_beta']),N,tol)
    out={'identity':inp['identity'],'solow':scenarios,'planner':plan,'planner_migration':pm,
         'household':household(inp['household'],tol),'status':'PASS'}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    colors=['#235faa','#cc5918','#20855a','#8054a8'];names=['base','higher_s','A_level','A_growth']
    left=[(name,colors[i],[(z['t'],z['c_worker']) for z in scenarios[name]['path']]) for i,name in enumerate(names[:2])]
    right=[(name,colors[i],[(z['t'],z['y_worker']) for z in scenarios[name]['path']]) for i,name in enumerate(names)]
    (args.out/'solow.svg').write_text(svg('Saving changes levels; technology growth changes trend',
      '同初始实物资本比较储蓄、技术水平和增长率；每工人消费与产出分栏，非现实估计。',
      [(left,'period','consumption / worker','Consumption transition'),(right,'period','output / worker','A level versus A growth')]))
    a,b,k0=[f(inp['planner'][z]) for z in ('alpha','beta','k0')]
    curves=[(name,colors[i],[(z['t'],z['c']) for z in plan[name]['path'][:21]]) for i,name in enumerate(('optimal','golden'))]
    points=[(.02+i*.96/192,utility(a,b,k0,.02+i*.96/192)) for i in range(193)]
    obj=[('full discounted utility','#235faa',points),('optimal s='+str(round(a*b,6)),'#cc5918',[(a*b,utility(a,b,k0,a*b))]*2)]
    # A separate marker makes a maximum visible even if not on the sampling grid.
    marker=(a*b,utility(a,b,k0,a*b));obj[1]=(obj[1][0],obj[1][1],[(marker[0]-.001,marker[1]),(marker[0]+.001,marker[1])])
    (args.out/'planner.svg').write_text(svg('Steady consumption and discounted welfare answer different questions',
      '最优与黄金律消费路径；右图用解析全路径目标比较储蓄规则，非稳态福利替代。',
      [(curves,'period','consumption','Same initial capital; delta=1'),(obj,'saving fraction s','discounted log utility','Full path objective; beta='+str(b))]))
    print('PASS: aggregate normalization; closed paths; Euler/TVC quantities; exact KKT/market clearing; outputs written')

if __name__=='__main__':
    main()
