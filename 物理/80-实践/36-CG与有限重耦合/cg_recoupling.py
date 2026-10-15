#!/usr/bin/env python3
"""Finite CG by highest weights; separate factorial 3j/6j checks. Python stdlib."""
import argparse
import cmath
import csv
from fractions import Fraction as F
import html
import json
import math
from pathlib import Path


def dot(u, v):
    return sum(a.conjugate() * b for a, b in zip(u, v))


def mv(a, v):
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def adj(a):
    return [[a[i][j].conjugate() for i in range(len(a))] for j in range(len(a[0]))]


def mm(a, b):
    return [[sum(x * y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def ident(n):
    return [[float(i == j) for j in range(n)] for i in range(n)]


def err(a, b):
    return max((abs(x-y) for u, v in zip(a, b) for x, y in zip(u, v)), default=0.)


def cols(vs):
    return [list(r) for r in zip(*vs)]


def ms(t):
    return list(range(t, -t-1, -2))


def labels(t1, t2):
    return [(a, b) for a in ms(t1) for b in ms(t2)]


def total_operators(ts):
    import itertools
    basis = list(itertools.product(*(ms(t) for t in ts)))
    ix = {b: i for i, b in enumerate(basis)}
    n = len(basis)
    z = [[float(i == k) * sum(b)/2 for k in range(n)] for i, b in enumerate(basis)]
    plus = [[0.]*n for _ in range(n)]
    for k, b in enumerate(basis):
        for r, t in enumerate(ts):
            m = b[r]
            if m < t:
                c = list(b); c[r] += 2
                plus[ix[tuple(c)]][k] += math.sqrt((t-m)*(t+m+2))/2
    minus = adj(plus)
    c2 = mm(minus, plus)
    for i, b in enumerate(basis):
        m = sum(b)/2
        c2[i][i] += m*m + m
    return basis, z, plus, minus, c2


def couple(t1, t2):
    """Q[row product m1,m2][column J,M], J and M descending.

    Doubled integer input, 0<=t<=6. Highest-weight seed is m1=j1,
    m2=J-j1. Two-pass projection removes all earlier irreps at M=J.
    Positive seed fixes Condon-Shortley phases; lowering is never renormalized.
    """
    if any(type(t) is not int or not 0 <= t <= 6 for t in (t1, t2)):
        raise ValueError('two_j must be integer 0..6')
    basis, z, plus, minus, c2 = total_operators([t1, t2])
    n = len(basis); ix = {b: i for i, b in enumerate(basis)}
    states = {}; order = []
    for tj in range(t1+t2, abs(t1-t2)-1, -2):
        seed = ix[(t1, tj-t1)]
        v = [float(i == seed) for i in range(n)]
        previous = [u for (a,b), u in states.items() if b == tj]
        for _ in range(2):
            for u in previous:
                s = dot(u, v); v = [x-s*y for x,y in zip(v,u)]
        norm = math.sqrt(dot(v,v).real)
        if norm < 1e-12:
            raise ArithmeticError('highest-weight projection collapsed')
        v = [x/norm for x in v]
        if v[seed].real < 0: v = [-x for x in v]
        for tm in ms(tj):
            states[(tj,tm)] = v; order.append((tj,tm))
            if tm > -tj:
                scale = math.sqrt((tj+tm)*(tj-tm+2))/2
                v = [x/scale for x in mv(minus,v)]
    q = cols([states[k] for k in order])
    d2 = [[float(i == k)*(a/2)*(a/2+1) for k in range(n)] for i,(a,b) in enumerate(order)]
    dz = [[float(i == k)*b/2 for k in range(n)] for i,(a,b) in enumerate(order)]
    raising = 0.
    for (tj,tm), v in states.items():
        goal = [0.]*n if tm == tj else [math.sqrt((tj-tm)*(tj+tm+2))/2*x for x in states[(tj,tm+2)]]
        raising = max(raising,max(abs(x-y) for x,y in zip(mv(plus,v),goal)))
    checks = {'unitarity':err(mm(adj(q),q),ident(n)),
              'casimir':err(mm(c2,q),mm(q,d2)), 'Jz':err(mm(z,q),mm(q,dz)),
              'raising':raising,
              'factorial_CG':max(abs(q[i][k]-cg_factorial(F(t1,2),F(a,2),F(t2,2),F(b,2),F(j,2),F(m,2))) for i,(a,b) in enumerate(basis) for k,(j,m) in enumerate(order))}
    if t1 == t2:
        checks['swap_parity'] = max(abs(states[(j,m)][ix[(b,a)]]-(-1)**(t1-j//2)*states[(j,m)][i]) for (j,m) in order for i,(a,b) in enumerate(basis))
    return {'basis':basis,'order':order,'states':states,'Q':q,'checks':checks}


def fact(x):
    x = F(x)
    if x.denominator != 1 or x < 0:
        raise ValueError('noninteger or negative factorial')
    return math.factorial(x.numerator)


def triangle(a,b,c):
    return abs(a-b) <= c <= a+b and (a+b+c).denominator == 1


def delta(a,b,c):
    if not triangle(a,b,c): return 0.
    return math.sqrt(float(F(fact(a+b-c)*fact(a-b+c)*fact(-a+b+c),fact(a+b+c+1))))


def cg_factorial(a,ma,b,mb,c,mc):
    """DLMF 34.1.1 + 34.2.4; independent factorial sum, no CG lookup."""
    if ma+mb != mc or not triangle(a,b,c) or abs(ma)>a or abs(mb)>b or abs(mc)>c:
        return 0.
    pref = math.sqrt(2*c+1)*delta(a,b,c)*math.sqrt(fact(a+ma)*fact(a-ma)*fact(b+mb)*fact(b-mb)*fact(c+mc)*fact(c-mc))
    total = F(0)
    for s in range(int(a+b+c)+1):
        args = [s,a+b-c-s,a-ma-s,b+mb-s,c-b+ma+s,c-a-mb+s]
        if min(args) >= 0:
            denom = math.prod(fact(x) for x in args)
            total += F((-1)**s,denom)
    # The 3j phase cancels the CG-to-3j phase (both a-b+mc).
    return pref*float(total)


def sixj(a,b,c,d,e,f):
    """DLMF 34.4.2 Racah sum with all four triangle factors."""
    a,b,c,d,e,f = map(F,(a,b,c,d,e,f))
    triangles = [(a,b,c),(a,e,f),(d,b,f),(d,e,c)]
    if not all(triangle(*t) for t in triangles): return 0.
    lo = [a+b+c,a+e+f,d+b+f,d+e+c]
    hi = [a+b+d+e,b+c+e+f,c+a+f+d]
    total = F(0)
    for z in range(int(max(lo)),int(min(hi))+1):
        den = math.prod(fact(z-x) for x in lo)*math.prod(fact(x-z) for x in hi)
        total += F((-1)**z*fact(z+1),den)
    return math.prod(delta(*t) for t in triangles)*float(total)


def recoupling(tm=2):
    """Three ordered addressable spin-1 factors. Fixed total J=1, doubled M."""
    if type(tm) is not int or tm not in (-2,0,2): raise ValueError('three-spin two_M must be -2, 0, 2')
    pair = couple(2,2)
    basis,z,p,minus,c2 = total_operators([2,2,2])
    left=[]; right=[]
    for e in range(3):
        ec = couple(2*e,2); ae = couple(2,2*e)
        wl=[]; vr=[]
        for a,b,c in basis:
            mu=a+b; nu=b+c
            wl.append(pair['states'].get((2*e,mu),[0.]*9)[pair['basis'].index((a,b))] * ec['states'][(2,tm)][ec['basis'].index((mu,c))] if abs(mu)<=2*e else 0.)
            vr.append(pair['states'].get((2*e,nu),[0.]*9)[pair['basis'].index((b,c))] * ae['states'][(2,tm)][ae['basis'].index((a,nu))] if abs(nu)<=2*e else 0.)
        left.append(wl); right.append(vr)
    w=cols(left); v=cols(right); r=mm(adj(v),w)
    # Actual 27x27 pair Casimirs, from two-spin product-space operator.
    pair_c2=total_operators([2,2])[-1]; n=27
    c12=[[pair_c2[i//3][k//3]*float(i%3==k%3) for k in range(n)] for i in range(n)]
    c23=[[pair_c2[i%9][k%9]*float(i//9==k//9) for k in range(n)] for i in range(n)]
    diag=[[float(i==k)*i*(i+1) for k in range(3)] for i in range(3)]
    b_in_w=mm(adj(w),mm(c23,w))
    symbol=[[sixj(1,1,e,1,1,f) for e in range(3)] for f in range(3)]
    from6=[[math.sqrt((2*e+1)*(2*f+1))*symbol[f][e] for e in range(3)] for f in range(3)]
    checks={'left_orthogonality':err(mm(adj(w),w),ident(3)), 'right_orthogonality':err(mm(adj(v),v),ident(3)),
            'same_subspace':err(w,mm(v,r)), 'recoupling_unitarity':err(mm(adj(r),r),ident(3)),
            'sixj':err(r,from6), 'left_total_J2':err(mm(c2,w),[[2*x for x in row] for row in w]),
            'right_total_J2':err(mm(c2,v),[[2*x for x in row] for row in v]),
            'Jz':err(mm(z,w),[[tm/2*x for x in row] for row in w]),
            'pair_AB':err(mm(adj(w),mm(c12,w)),diag), 'pair_BC':err(b_in_w,mm(adj(r),mm(diag,r)))}
    comm=[[diag[i][i]*b_in_w[i][k]-b_in_w[i][k]*diag[k][k] for k in range(3)] for i in range(3)]
    return {'basis':basis,'W':w,'V':v,'R':r,'sixj':symbol,'BC_in_AB_basis':b_in_w,
            'pair_commutator':comm,'checks':checks}


def phase_check(cg, phases):
    if len(phases) != len(set(j for j,m in cg['order'])): raise ValueError('one phase per J multiplet required')
    phase_map=dict(zip(sorted(set(j for j,m in cg['order']),reverse=True),phases))
    ds=[cmath.exp(1j*phase_map[j]) for j,m in cg['order']]
    q=cg['Q']; qp=[[x*d for x,d in zip(row,ds)] for row in q]
    # A coherent state spans ALL coupled columns; fixed physical state, coefficients covariant.
    coeff=[cmath.exp(0.37j*k)/math.sqrt(len(ds)) for k in range(len(ds))]
    psi=mv(q,coeff); coeffp=[x/d for x,d in zip(coeff,ds)]; psip=mv(qp,coeffp)
    fixed=mv(qp,coeff)
    return {'reconstruction_residual':max(abs(a-b) for a,b in zip(psi,psip)),
            'Born_residual':max(abs(abs(a)**2-abs(b)**2) for a,b in zip(psi,psip)),
            'fixed_coefficients_probability_change':max(abs(abs(a)**2-abs(b)**2) for a,b in zip(psi,fixed)),
            'product_probabilities': [abs(x)**2 for x in psi], 'rephased_product_probabilities':[abs(x)**2 for x in psip]}


def clean(obj):
    if isinstance(obj,complex):
        return obj.real if abs(obj.imag)<1e-13 else [obj.real,obj.imag]
    if isinstance(obj,dict): return {str(k):clean(v) for k,v in obj.items() if k != 'states'}
    if isinstance(obj,(list,tuple)): return [clean(x) for x in obj]
    return obj


def csv_write(path, header, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(header); w.writerows(rows)


def cg_csv(path,c):
    csv_write(path,['row','two_m1','two_m2','column','two_J','two_M','CG'],
              ([i,a,b,k,j,m,float(c['Q'][i][k].real)] for i,(a,b) in enumerate(c['basis']) for k,(j,m) in enumerate(c['order'])))


def text_svg(x,y,s,size=14,color='#17212b',anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(s))}</text>'


def heatmap(a, rowlabels, collabels, title, x=115,y=105,cell=62):
    out=[text_svg(x,y-62,title,19)]
    for k,s in enumerate(collabels): out.append(text_svg(x+k*cell+cell/2,y-15,s,12,anchor='middle'))
    for i,row in enumerate(a):
        out.append(text_svg(x-12,y+i*cell+cell/2+5,rowlabels[i],12,anchor='end'))
        for k,v in enumerate(row):
            val=float(v.real); vabs=min(1.,abs(val))
            tint=int(255-150*vabs); col=f'rgb({tint},{tint},255)' if val>=0 else f'rgb(255,{tint},{tint})'
            out.append(f'<rect x="{x+k*cell}" y="{y+i*cell}" width="{cell}" height="{cell}" fill="{col}" stroke="#fff"/>')
            s='0' if abs(val)<1e-12 else f'{val:.3f}'
            out.append(text_svg(x+k*cell+cell/2,y+i*cell+cell/2+5,s,12,anchor='middle'))
    return out


def svg_write(path,width,height,elements):
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fff"/><g font-family="sans-serif">'+''.join(elements)+'</g></svg>\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json')); p.add_argument('--output',type=Path,default=Path(__file__).with_name('assets'))
    args=p.parse_args(); inp=json.loads(args.input.read_text()); out=args.output; out.mkdir(parents=True,exist_ok=True)
    if inp['main_two_j'] != [2,2]: raise ValueError('main example is fixed spin 1 x spin 1; change variant_two_j for migration')
    for key in ('multiplet_phases_radians','left_phases_radians','right_phases_radians'):
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in inp[key]): raise ValueError('phases must be finite real radians')
    tol=inp['tolerance']
    if not isinstance(tol,(int,float)) or not 0<tol<=1e-8: raise ValueError('tolerance must be 0..1e-8 exclusive zero')
    main_cg=couple(*inp['main_two_j']); variant=couple(*inp['variant_two_j'])
    re=recoupling(inp['three_two_M']); phase=phase_check(main_cg,inp['multiplet_phases_radians'])
    residuals={**{f'main_{k}':v for k,v in main_cg['checks'].items()},**{f'variant_{k}':v for k,v in variant['checks'].items()},**{f'recoupling_{k}':v for k,v in re['checks'].items()},'phase_reconstruction':phase['reconstruction_residual'],'phase_Born':phase['Born_residual']}
    for m in (-2,0,2): residuals[f'M_invariance_{m}']=err(re['R'],recoupling(m)['R'])
    max_error=max(residuals.values())
    if max_error>tol: raise ArithmeticError(f'residual {max_error} exceeds {tol}')
    # Rephasing both multiplicity bases changes coordinates R'=D_V^dagger R D_W.
    dl=[cmath.exp(1j*x) for x in inp['left_phases_radians']]; dr=[cmath.exp(1j*x) for x in inp['right_phases_radians']]
    if len(dl)!=3 or len(dr)!=3: raise ValueError('three multiplicity phases each')
    rp=[[dr[f].conjugate()*re['R'][f][e]*dl[e] for e in range(3)] for f in range(3)]
    born_phase=max(abs(abs(re['R'][f][e])**2-abs(rp[f][e])**2) for f in range(3) for e in range(3))
    residuals['rephased_recoupling_single_basis_Born']=born_phase
    r=re['R']; samples=inp['phase_samples']
    if type(samples) is not int or not 3<=samples<=2001: raise ValueError('phase_samples integer 3..2001')
    migration=[]
    for k in range(samples):
        phi=2*math.pi*k/(samples-1)
        ps=[abs((r[f][0]+cmath.exp(1j*phi)*r[f][1])/math.sqrt(2))**2 for f in range(3)]
        prediction=2/9-math.cos(phi)/(3*math.sqrt(3))
        residuals['phase_probability_formula']=max(residuals.get('phase_probability_formula',0.),abs(ps[0]-prediction),abs(sum(ps)-1))
        migration.append([phi,*ps,prediction])
    max_error=max(residuals.values())
    if max_error>tol: raise ArithmeticError(f'residual {max_error} exceeds {tol}')
    result={'input':inp,'units':{'operators':'Jz/hbar; J2/hbar^2; probabilities dimensionless','angles':'radian'},'main':main_cg,'variant':variant,'three':re,'phase':phase,'rephased_R':rp,'residuals':residuals,'maximum_residual':max_error,'author_execution_only':True}
    (out/'results.json').write_text(json.dumps(clean(result),ensure_ascii=False,indent=2)+'\n')
    cg_csv(out/'cg-nine.csv',main_cg); cg_csv(out/'cg-variant.csv',variant)
    csv_write(out/'recoupling.csv',['f_BC','e_AB','overlap','sixj','probability'],([f,e,r[f][e].real,re['sixj'][f][e],abs(r[f][e])**2] for f in range(3) for e in range(3)))
    csv_write(out/'phase-migration.csv',['phi_radians','p_f0','p_f1','p_f2','analytic_p_f0'],migration)
    a=main_cg
    elems=heatmap(a['Q'],[f'({x/2:g},{y/2:g})' for x,y in a['basis']],[f'{j/2:g},{m/2:g}' for j,m in a['order']],f'CG Q: j1={inp["main_two_j"][0]/2:g}, j2={inp["main_two_j"][1]/2:g}; columns J,M')
    elems += [text_svg(115,695,'Rows m1,m2; blue positive / red negative; exact zeros are white',13),text_svg(115,722,'J2/hbar^2 eigenvalues: J(J+1); generated from the same Q as CSV',13)]
    svg_write(out/'cg-nine.svg',800,752,elems)
    elems=heatmap(r,['f=0','f=1','f=2'],['e=0','e=1','e=2'],f'R = V dagger W; J=1, M={inp["three_two_M"]/2:g}',x=110,y=110,cell=82)
    elems += [text_svg(445,70,'Prepare W0: measure (B+C)^2/hbar^2',17)]
    for f in range(3):
        prob=abs(r[f][0])**2; yy=125+f*70
        elems += [text_svg(445,yy,f'f={f}: {prob:.6f}',14),f'<rect x="445" y="{yy+10}" width="{prob*400}" height="23" fill="#396ba8"/>']
    elems += [text_svg(110,415,'Coherent preparation (W0 + exp(i phi) W1)/sqrt(2)',18)]
    x0,y0,w,h=110,445,690,170
    elems += [f'<path d="M{x0},{y0} V{y0+h} H{x0+w}" fill="none" stroke="#555"/>',text_svg(x0-12,y0+5,'1',12,anchor='end'),text_svg(x0-12,y0+h+5,'0',12,anchor='end')]
    for f,col in enumerate(['#235d9c','#bf463e','#287d54']):
        pts=' '.join(f'{x0+row[0]/(2*math.pi)*w:.3f},{y0+(1-row[1+f])*h:.3f}' for row in migration)
        elems += [f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>',text_svg(150+f*190,665,f'p(f={f})',14,col)]
    elems += [text_svg(x0,y0+h+25,'0',12),text_svg(x0+w/2,y0+h+25,'pi',12,anchor='middle'),text_svg(x0+w,y0+h+25,'2pi',12,anchor='end'),text_svg(110,702,'phi in radians; curves use phase-migration.csv values',13)]
    svg_write(out/'recoupling.svg',880,735,elems)
    print(json.dumps({'main_dimension':len(main_cg['Q']),'variant_dimension':len(variant['Q']),'three_dimension':len(re['W']),'fixed_JM_dimension':3,'maximum_residual':max_error,'outputs':7}))


if __name__=='__main__': main()
