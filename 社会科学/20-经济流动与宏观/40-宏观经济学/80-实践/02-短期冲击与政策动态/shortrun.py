#!/usr/bin/env python3
"""Exact, deterministic short-run teaching model. Fractions are the numeric truth."""
import argparse
from fractions import Fraction as Q
import html
import json
from pathlib import Path


def gaussian(matrix, rhs):
    """Exact independent linear solve; no reduced-form coefficients used here."""
    A=[list(row)+[v] for row,v in zip(matrix,rhs)];n=len(A)
    for j in range(n):
        k=next((k for k in range(j,n) if A[k][j]),None)
        if k is None:raise ValueError('singular original equations')
        A[j],A[k]=A[k],A[j];scale=A[j][j];A[j]=[v/scale for v in A[j]]
        for k in range(n):
            if k!=j:
                scale=A[k][j];A[k]=[u-scale*v for u,v in zip(A[k],A[j])]
    return [row[-1] for row in A]


def validate(p):
    if not (p['a']>0 and p['b']>0 and p['kappa']>0 and 0<=p['omega']<=1
            and p['phi_pi']>=0 and p['phi_x']>=0 and p['Y_potential']>0
            and 0<=p['u_star']<=100 and p['pi_star']>-100 and p['i_min']>-100):
        raise ValueError('parameter domain violated')
    if not p['r_star']+p['pi_star']>p['i_min']:
        raise ValueError('reference nominal rate must strictly exceed floor')


def coefficients(p):
    a,b,fp,fx,w=[p[k] for k in ('a','b','phi_pi','phi_x','omega')]
    H=1+a*fx;D=H+a*b*fp;A=w*(H+a*b)/D
    return H,D,A


def node(p,z,d,s,bounded):
    a,b,fp,fx,w=[p[k] for k in ('a','b','phi_pi','phi_x','omega')]
    istar=p['r_star']+p['pi_star'];floor=p['i_min'];e=p['pi_star']+w*z
    H,D,A=coefficients(p)
    x=(a*w*(1-fp)*z+d-a*fp*s)/D;dev=w*z+b*x+s
    iu=istar+fp*dev+fx*x
    # Route 2 solves the three ORIGINAL simultaneous equations for x,p,i.
    mat=[[Q(1),Q(0),a],[-b,Q(1),Q(0)],[-fx,-fp,Q(1)]]
    direct=gaussian(mat,[a*(e+p['r_star'])+d,w*z+s,istar])
    assert direct==[x,dev,iu]
    bound=bounded and iu<floor
    i=floor if bound else iu
    if bound:
        x=a*(e+p['r_star']-i)+d;dev=w*z+b*x+s
        # Independent original equations in binding branch.
        direct=gaussian([[Q(1),Q(0),a],[-b,Q(1),Q(0)],[Q(0),Q(0),Q(1)]],
                        [a*(e+p['r_star'])+d,w*z+s,floor])
        assert direct==[x,dev,i]
    shadow=istar+fp*dev+fx*x
    assert x==-a*(i-e-p['r_star'])+d
    assert dev==w*z+b*x+s
    assert i==(max(floor,shadow) if bounded else shadow)
    assert not bound or shadow<=floor
    pi=p['pi_star']+dev;Y=p['Y_potential']*(1+x/100);u=p['u_star']-p['kappa']*x
    if not (Y>0 and 0<=u<=100 and pi>-100 and i>-100):
        raise ValueError('path outside positive output/price or unemployment/rate domain')
    return {'x':x,'p':dev,'Y':Y,'u':u,'pi':pi,'i':i,'shadow_i':shadow,
            'unconstrained_i':iu,'e':e,'real_linear':i-e,'d':d,'s':s,'binding':bound}


def path(p,scenario,N):
    bounded=scenario.get('enforce_lower_bound',True)
    z=Q(scenario['p_initial']);start=z;rows=[];H,D,A=coefficients(p)
    ds=list(map(Q,scenario['d']));ss=list(map(Q,scenario['s']));P=Q(100);baseP=Q(100)
    for t in range(N):
        d=ds[t] if t<len(ds) else Q(0);s=ss[t] if t<len(ss) else Q(0)
        row=node(p,z,d,s,bounded);row['t']=t
        P*=1+row['pi']/100;baseP*=1+p['pi_star']/100
        row['price_index']=P;row['relative_price_to_target_path']=P/baseP
        if not any(q['binding'] for q in rows) and not row['binding']:
            convolution=A**(t+1)*start+sum(A**(t-j)*(p['b']*(ds[j] if j<len(ds) else 0)
                      +H*(ss[j] if j<len(ss) else 0))/D for j in range(t+1))
            assert row['p']==convolution
        rows.append(row);z=row['p']
    summary={'H':H,'D':D,'A_interior':A,'A_binding':p['omega']*(1+p['a']*p['b']),
             'sum_gap_finite':sum(v['x'] for v in rows),'binding_count':sum(v['binding'] for v in rows)}
    if p['omega']==1 and A<1 and not any(v['binding'] for v in rows) and N>=max(len(ds),len(ss)):
        # Exact infinite tail only when shocks have ended and future interior branch remains valid.
        # Positive deviation implies future positive nominal rates for these nonnegative coefficients.
        if rows[-1]['p']>=0:
            tail=-p['a']*(p['phi_pi']-1)/D*rows[-1]['p']/(1-A)
            summary['sum_gap_with_analytic_tail']=summary['sum_gap_finite']+tail
            assert summary['sum_gap_with_analytic_tail']==(-start-sum(ss))/p['b']
    return {'parameters':p,'initial_p':start,'enforce_lower_bound':bounded,'rows':rows,'summary':summary}


def encode(v):
    if isinstance(v,Q):return str(v)
    if isinstance(v,list):return [encode(z) for z in v]
    if isinstance(v,dict):return {k:encode(z) for k,z in v.items()}
    return v


def panel(out,x,y,w,h,curves,title,unit):
    points=[p for _,_,ps in curves for p in ps];xs=[p[0] for p in points];ys=[p[1] for p in points]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);pad=max(.1,(ymax-ymin)*.12);ymin-=pad;ymax+=pad
    X=lambda a:x+(a-xmin)/(xmax-xmin)*w
    Y=lambda a:y+h-(a-ymin)/(ymax-ymin)*h
    out.append(f'<text x="{x}" y="{y-25}" class="head">{html.escape(title)}</text><text x="{x}" y="{y-7}">{html.escape(unit)}</text>')
    for j in range(4):
        yy=ymin+(ymax-ymin)*j/3;loc=Y(yy)
        out.append(f'<path d="M{x},{loc:.3f}h{w}" class="grid"/><text x="{x-8}" y="{loc+4:.3f}" text-anchor="end">{yy:.4g}</text>')
        xx=x+j*w/3;xxv=xmin+(xmax-xmin)*j/3
        out.append(f'<text x="{xx:.3f}" y="{y+h+20}" text-anchor="middle">{xxv:.3g}</text>')
    out.append(f'<path d="M{x},{y}v{h}h{w}" class="axis"/><text x="{x+w/2}" y="{y+h+42}" text-anchor="middle">period (one year)</text>')
    for j,(label,color,ps) in enumerate(curves):
        line=' '.join(('M' if n==0 else 'L')+f'{X(t):.3f},{Y(v):.3f}' for n,(t,v) in enumerate(ps))
        out.append(f'<path d="{line}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for t,v in ps:out.append(f'<circle cx="{X(t):.3f}" cy="{Y(v):.3f}" r="2" fill="{color}"/>')
        out.append(f'<path d="M{x},{y+h+64+j*18}h20" stroke="{color}" stroke-width="3"/><text x="{x+28}" y="{y+h+69+j*18}">{html.escape(label)}</text>')


def figure(title,desc,panels):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1220" height="1000" viewBox="0 0 1220 1000" role="img">',
         '<title>'+html.escape(title)+'</title><desc>'+html.escape(desc)+'</desc>',
         '<style>text{font:14px sans-serif;fill:#17263a}.head{font-weight:bold;font-size:17px}.axis{stroke:#45566b;fill:none}.grid{stroke:#e3e8ee;fill:none}</style><rect width="1220" height="1000" fill="white"/>',
         '<text x="65" y="30" class="head">'+html.escape(title)+'</text>']
    for n,(curves,heading,unit) in enumerate(panels):
        panel(out,75+610*(n%2),95+450*(n//2),455,265,curves,heading,unit)
    out.append('<text x="65" y="982">Synthetic economic model; no empirical calibration or measured policy effects.</text></svg>')
    return '\n'.join(out)+'\n'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);arg=ap.parse_args()
    inp=json.loads(arg.input.read_text());N=inp['periods']
    if not isinstance(N,int) or not 2<=N<=60:raise ValueError('periods must be integer 2..60')
    base={k:Q(v) for k,v in inp['parameters'].items()};validate(base);results={}
    for sc in inp['scenarios']:
        p=dict(base);p.update({k:Q(v) for k,v in sc.get('changes',{}).items()});validate(p)
        count=sc.get('periods',N)
        if not isinstance(count,int) or not 2<=count<=60:raise ValueError('scenario periods 2..60 required')
        if sc['name'] in results:raise ValueError('duplicate scenario name')
        results[sc['name']]=path(p,sc,count)
    # Construct observation-equivalent finite path with a different Phillips slope.
    observed=results['demand'];model=observed['parameters'];bp=model['b']/2;dlist=[];slist=[]
    for row in observed['rows']:
        dlist.append(str(row['d']));slist.append(str(row['s']+(model['b']-bp)*row['x']))
    altered=dict(model,b=bp)
    M=len(observed['rows'])
    twin=path(altered,{'p_initial':str(observed['initial_p']),'d':dlist,'s':slist,'enforce_lower_bound':observed['enforce_lower_bound']},M)
    for one,two in zip(observed['rows'],twin['rows']):
        assert all(one[k]==two[k] for k in ('x','p','Y','u','pi','i','e'))
    # Hold each world's input shocks fixed, change policy; observed equivalence need not persist.
    p1=dict(model,phi_pi=model['phi_pi']+1);p2=dict(altered,phi_pi=model['phi_pi']+1)
    intervention1=path(p1,{'p_initial':str(observed['initial_p']),'d':dlist,'s':[str(q['s']) for q in observed['rows']],'enforce_lower_bound':observed['enforce_lower_bound']},M)
    intervention2=path(p2,{'p_initial':str(observed['initial_p']),'d':dlist,'s':slist,'enforce_lower_bound':observed['enforce_lower_bound']},M)
    output={'identity':inp['identity'],'status':'PASS','scenarios':results,
            'observation_equivalent_world':twin,'policy_counterfactual_original':intervention1,
            'policy_counterfactual_altered':intervention2}
    arg.out.mkdir(parents=True,exist_ok=True)
    (arg.out/'results.json').write_text(json.dumps(encode(output),ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    palette=['#235faa','#b65022','#20855a','#6b5aa5']
    def curves(names,key,reference=None):
        c=[]
        for j,name in enumerate(names):
            spec=results[name]['parameters']
            label=name+': fpi='+str(float(spec['phi_pi']))+', w='+str(float(spec['omega']))
            c.append((label,palette[j],[(q['t'],float(q[key])) for q in results[name]['rows']]))
        if reference is not None:
            last=max(v['rows'][-1]['t'] for k,v in results.items() if k in names)
            c.append(('global reference','#78828f',[(0,float(reference)),(last,float(reference))]))
        return c
    refs=[base['Y_potential'],base['u_star'],base['pi_star'],base['r_star']+base['pi_star']]
    labels=[('Y','Real output','output index'),('u','Unemployment','percent of labor force'),('pi','Inflation','percent per period'),('i','Nominal interest','percent per period')]
    panels=[(curves(['demand','cost'],k,refs[j]),heading,unit) for j,(k,heading,unit) in enumerate(labels)]
    (arg.out/'shocks.svg').write_text(figure('Demand versus cost-push paths: parameters fixed in input',
       '按输入给定的需求与成本模型，展示产出、失业、通胀和名义利率，单位逐栏标明。',panels))
    panels=[(curves(['cost','cost_stronger','cost_anchored'],k),heading,unit) for k,heading,unit in
            [('x','Cost shock: output gap','gap percentage points'),('pi','Cost shock: inflation','percent per period')]]
    panels += [(curves(['lower_bound','negative_allowed'],k),heading,unit) for k,heading,unit in
            [('x','Negative demand: output gap','gap percentage points'),('i','Negative demand: policy constraint','nominal percent per period')]]
    (arg.out/'regimes.svg').write_text(figure('Feedback, forecasts, and an effective lower bound',
       '上栏一次成本冲击比较政策/预期，下栏另一次负需求冲击比较下限与允许负利率，非同一政策净收益。',panels))
    print('PASS: exact original equations, branches, convolution, price accounting and observation-equivalent worlds')

if __name__=='__main__':main()
