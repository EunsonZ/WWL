#!/usr/bin/env python3
"""Constant-source 1D p-Laplace conforming FEM via flux shooting; standard library."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import tempfile
import sys


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int,float)):
        raise ValueError('Expected a finite numeric parameter')
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError('Numeric overflow') from exc
    if not math.isfinite(value):
        raise ValueError('Nonfinite parameter')
    return value


def integer(value, low, high):
    if isinstance(value,bool) or not isinstance(value,int) or not low <= value <= high:
        raise ValueError(f'Expected integer {low}..{high}')
    return value


def load_card(path):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    card = json.loads(Path(path).read_text(),object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    required = {'schema','boundary','length','source','p_values','cells','profile_points',
                'quadrature_abs_tol','resonance_amplitudes'}
    if not isinstance(card,dict):
        raise ValueError('Input card must be a JSON object')
    if set(card) != required or card['schema'] != 'wwl-elliptic-flux-1':
        raise ValueError('Unexpected schema or keys')
    if card['boundary'] != 'zero_dirichlet':
        raise ValueError('Only zero Dirichlet boundaries are implemented')
    if not .1 <= finite(card['length']) <= 4 or abs(finite(card['source'])) > 8:
        raise ValueError('Require .1<=length<=4 and |source|<=8')
    for key in ('p_values','cells','resonance_amplitudes'):
        if not isinstance(card[key],list) or not card[key] or len(card[key])>8:
            raise ValueError('Require nonempty lists of at most eight entries')
        for value in card[key]:
            finite(value)
        if len(set(card[key])) != len(card[key]):
            raise ValueError('Repeated list entry')
    if any(not 1.25<=finite(p)<=6 for p in card['p_values']):
        raise ValueError('Executable p window is 1.25..6; theorem is 1<p<infinity')
    for n in card['cells']:
        integer(n,2,256)
    if len(card['p_values'])*len(card['cells'])>32:
        raise ValueError('At most 32 finite cases')
    integer(card['profile_points'],33,2001)
    if not 1e-12<=finite(card['quadrature_abs_tol'])<=1e-6:
        raise ValueError('Quadrature tolerance must be 1e-12..1e-6')
    if any(abs(finite(a))>8 for a in card['resonance_amplitudes']):
        raise ValueError('Resonance amplitude budget exceeded')
    return card


def signed_power(value, exponent):
    return math.copysign(abs(value)**exponent,value) if value else 0.0


def flux(slope,p):
    # This implements a(0)=0 for p<2 without evaluating a negative power at zero.
    return signed_power(slope,p-1)


def exact_profile(x,p,length,source):
    alpha = 1/(p-1)
    beta = alpha+1
    return signed_power(source,alpha)*((length/2)**beta-abs(x-length/2)**beta)/beta


def exact_gradient(x,p,length,source):
    return signed_power(source*(length/2-x),1/(p-1))


def shoot(p,n,length,source):
    h = length/n
    mid = [(j+.5)*h for j in range(n)]
    if not source:
        return [0.]*(n+1),[0.]*n,[0.]*n,0.
    lower,upper = min(source*x for x in mid),max(source*x for x in mid)
    def endpoint(c):
        return h*math.fsum(signed_power(c-source*x,1/(p-1)) for x in mid)
    for _ in range(100):
        center = (lower+upper)/2
        value = endpoint(center)
        if value == 0 or center in (lower,upper):
            break
        if value>0:
            upper=center
        else:
            lower=center
    # Near a zero-flux cell inverse powers can amplify one ulp. Evaluate adjacent
    # floating candidates and exact cell-zero candidates instead of trusting stagnation.
    candidates=[lower,upper,center,(lower+upper)/2]+[source*x for x in mid]
    c=min(candidates,key=lambda value:abs(endpoint(value)))
    q=[c-source*x for x in mid]
    slopes=[signed_power(v,1/(p-1)) for v in q]
    nodes=[0.]
    for s in slopes:
        nodes.append(nodes[-1]+h*s)
    # Do not force the right endpoint to zero after solving; reject unresolved roots.
    endpoint_scale=max(1.,length*max(abs(s) for s in slopes))
    if abs(nodes[-1])>1e-11*endpoint_scale:
        raise ValueError('Floating shooting root does not resolve the Dirichlet endpoint')
    return nodes,slopes,q,c


def interpolate(x,nodes,length):
    n=len(nodes)-1
    h=length/n
    j=min(n-1,max(0,int(x/h)))
    theta=(x-j*h)/h
    return nodes[j]+theta*(nodes[j+1]-nodes[j]),j


def integrate(func,left,right,tol,depth=20):
    """Adaptive Simpson estimate and local diagnostic, not a rigorous interval bound."""
    middle=(left+right)/2
    fa,fm,fb=func(left),func(middle),func(right)
    whole=(right-left)*(fa+4*fm+fb)/6
    def refine(a,b,fa,fm,fb,whole,eps,remaining):
        m=(a+b)/2
        fl,fr=func((a+m)/2),func((m+b)/2)
        lhs=(m-a)*(fa+4*fl+fm)/6
        rhs=(b-m)*(fm+4*fr+fb)/6
        delta=lhs+rhs-whole
        if abs(delta)<=15*eps or remaining==0:
            return lhs+rhs+delta/15,abs(delta)/15,int(remaining==0 and abs(delta)>15*eps)
        l=refine(a,m,fa,fl,fm,lhs,eps/2,remaining-1)
        r=refine(m,b,fm,fr,fb,rhs,eps/2,remaining-1)
        return l[0]+r[0],l[1]+r[1],l[2]+r[2]
    return refine(left,right,fa,fm,fb,whole,tol,depth)


def case(p,n,card):
    length,source=finite(card['length']),finite(card['source'])
    nodes,slopes,q,c=shoot(p,n,length,source)
    h=length/n
    node_rows=[[p,n,i,i*h,u,exact_profile(i*h,p,length,source),
                u-exact_profile(i*h,p,length,source)] for i,u in enumerate(nodes)]
    edge_rows=[[p,n,j,j*h,(j+1)*h,slopes[j],q[j],source*(length/2-(j+.5)*h),
                flux(slopes[j],p)-q[j]] for j in range(n)]
    profile=[]
    for k in range(card['profile_points']):
        x=length*k/(card['profile_points']-1)
        uh,j=interpolate(x,nodes,length)
        profile.append([p,n,x,uh,exact_profile(x,p,length,source),slopes[j],
                        exact_gradient(x,p,length,source),q[j],source*(length/2-x)])
    l2_integral=grad_integral=quad_error=0.
    depth_limited=0
    for j in range(n):
        left,right=j*h,(j+1)*h
        def funerr(x):
            uh=nodes[j]+(x-left)*slopes[j]
            return (uh-exact_profile(x,p,length,source))**2
        def graderr(x):
            return abs(slopes[j]-exact_gradient(x,p,length,source))**p
        # Split any cell containing the zero flux point; midpoint singular curvature is explicit.
        breaks=[left]+([length/2] if left<length/2<right else [])+[right]
        for a,b in zip(breaks,breaks[1:]):
            eps=finite(card['quadrature_abs_tol'])*(b-a)/length
            value,err,limited=integrate(funerr,a,b,eps)
            l2_integral+=value;quad_error+=err;depth_limited+=limited
            value,err,limited=integrate(graderr,a,b,eps)
            grad_integral+=value;quad_error+=err;depth_limited+=limited
    energy_left=h*math.fsum(abs(s)**p for s in slopes)
    energy_right=source*h*math.fsum(nodes[1:-1])
    if abs(energy_left-energy_right)>1e-10*max(1.,abs(energy_left),abs(energy_right)):
        raise ValueError('Discrete energy identity is unresolved')
    info={'p':p,'cells':n,'h':h,'shooting_c':c,'c_minus_exact':c-source*length/2,
          'right_endpoint_residual':nodes[-1],
          'flux_balance_max':max(abs(q[i-1]-q[i]-source*h) for i in range(1,n)),
          'constitutive_residual_max':max(abs(row[-1]) for row in edge_rows),
          'energy_identity_residual':energy_left-energy_right,
          'discrete_energy':energy_left/p-energy_right,
          'nodal_max_error':max(abs(row[-1]) for row in node_rows),
          'profile_sampled_max_error':max(abs(row[3]-row[4]) for row in profile),
          'l2_error_estimate':max(0.,l2_integral)**.5,
          'gradient_lp_error_estimate':max(0.,grad_integral)**(1/p),
          'quadrature_diagnostic_sum':quad_error,'quadrature_depth_limited_count':depth_limited}
    if not all(math.isfinite(v) for v in info.values()):
        raise ValueError('Finite model budget exceeded')
    if p==2:
        info['p2_exact_l2_error']=abs(source)*math.sqrt(length)*h*h/math.sqrt(120)
        info['p2_exact_gradient_l2_error']=abs(source)*math.sqrt(length)*h/math.sqrt(12)
    return node_rows,edge_rows,profile,info


def run(input_path,out):
    out=Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('Refusing nonempty output directory')
    card=load_card(input_path)
    all_nodes=[];all_edges=[];all_profile=[];infos=[]
    for p in card['p_values']:
        for n in card['cells']:
            nr,er,pr,info=case(float(p),n,card)
            all_nodes+=nr;all_edges+=er;all_profile+=pr;infos.append(info)
    resonance=[]
    for i in range(card['profile_points']):
        x=i/(card['profile_points']-1)
        for amplitude in card['resonance_amplitudes']:
            u=amplitude*math.sin(math.pi*x)
            resonance.append([amplitude,x,u,amplitude*math.pi**2*math.sin(math.pi*x)-math.pi**2*u])
    summary={'schema':'wwl-elliptic-flux-results-1','input_snapshot':card,'cases':infos,
             'quadrature_is_rigorous_error_bound':False,
             'resonance_operator':'-u_second_derivative - pi^2*u on (0,1), zero Dirichlet',
             'resonance_is_p_laplace_counterexample':False}
    out.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.elliptic-flux-',dir=out.parent))
    try:
        entries=[('nodes.csv',['p','cells','node','x','u_h','u_exact','error'],all_nodes),
                 ('edges.csv',['p','cells','edge','left','right','slope','q_h','q_exact_mid','constitutive_error'],all_edges),
                 ('profiles.csv',['p','cells','x','u_h','u_exact','gradient_h','gradient_exact','q_h','q_exact'],all_profile),
                 ('resonance.csv',['amplitude','x','u','analytic_residual'],resonance)]
        for name,header,rows in entries:
            with (temporary/name).open('w',newline='') as handle:
                writer=csv.writer(handle);writer.writerow(header);writer.writerows(rows)
        (temporary/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        if out.exists():
            if any(out.iterdir()):
                raise ValueError('Output changed; refusing publication')
            out.rmdir()
        temporary.rename(out)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=run(args.inputs,args.out)
    except (ValueError,OSError,TypeError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        sys.exit(2)
    print(json.dumps({'output':str(args.out),'cases':len(result['cases'])}))
