#!/usr/bin/env python3
"""Declared linear OTA port model, two physical phases; deterministic stdlib only."""
import argparse
import csv
from fractions import Fraction as F
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape


def number(v, name, positive=False, nonnegative=False):
    if not isinstance(v, str):
        raise ValueError(f"{name}: use a rational string")
    try:
        q=F(v)
        f=float(q)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"{name}: invalid finite rational") from exc
    if not math.isfinite(f) or (positive and q <= 0) or (nonnegative and q < 0):
        raise ValueError(f"{name}: outside allowed domain")
    if positive and f == 0:
        raise ValueError(f"{name}: underflows binary64")
    return q


def psd_matrix(matrix, n):
    if not isinstance(matrix,list) or len(matrix)!=n or any(not isinstance(r,list) or len(r)!=n for r in matrix):
        raise ValueError("eta_cov_V2: require NxN matrix matching x")
    c=[[number(v,"eta_cov_V2") for v in r] for r in matrix]
    if any(c[i][j]!=c[j][i] for i in range(n) for j in range(n)):
        raise ValueError("eta_cov_V2: must be symmetric")
    # Exact symmetric elimination, including semidefinite zero pivots.
    a=[r[:] for r in c]
    for k in range(n):
        pivot=a[k][k]
        if pivot < 0 or (pivot==0 and any(a[j][k]!=0 for j in range(k+1,n))):
            raise ValueError("eta_cov_V2: must be positive semidefinite")
        if pivot:
            for i in range(k+1,n):
                for j in range(k+1,n):
                    a[i][j]-=a[i][k]*a[k][j]/pivot
    return c


def load(path):
    d=json.loads(path.read_text(encoding="utf-8"))
    keys={"Cs_F","Cf_F","Cp_F","A0","tau_a_s","Tphi2_s","Tisolated_s",
          "y0_V","s0_V","Vos_V","x_V","eta_cov_V2","ota_single_PSD_V2_per_Hz",
          "absolute_error_V","max_step_V"}
    if not isinstance(d,dict) or set(d)!=keys:
        raise ValueError("exact declared input fields required")
    positive={"Cs_F","Cf_F","A0","tau_a_s","absolute_error_V","max_step_V"}
    nonnegative={"Cp_F","Tphi2_s","Tisolated_s","ota_single_PSD_V2_per_Hz"}
    p={k:number(d[k],k,k in positive,k in nonnegative) for k in keys-{"x_V","eta_cov_V2"}}
    if p['absolute_error_V']>=p['max_step_V']:
        raise ValueError("absolute_error_V must be less than max_step_V")
    if not isinstance(d['x_V'],list) or not 1<=len(d['x_V'])<=32:
        raise ValueError("x_V: length 1..32")
    p['x_V']=[number(v,'x_V') for v in d['x_V']]
    p['eta_cov_V2']=psd_matrix(d['eta_cov_V2'],len(p['x_V']))
    alpha=(p['Cs_F']+p['Cp_F'])/p['Cf_F']
    p['alpha']=alpha
    p['tau1']=float(p['tau_a_s']/(p['A0']+1))
    p['tau2']=float(p['tau_a_s']*(1+alpha)/(p['A0']+1+alpha))
    if min(p['tau1'],p['tau2'])<=0 or not all(math.isfinite(t) for t in [p['tau1'],p['tau2']]):
        raise ValueError("derived time constants must be positive finite binary64")
    p['rho1']=math.exp(-float(p['Tisolated_s'])/p['tau1'])
    p['rho2']=math.exp(-float(p['Tphi2_s'])/p['tau2'])
    return p


def static(p):
    A=p['A0']; alpha=p['alpha']; D=A+1+alpha
    ag=(A+1)/D; bg=A*alpha/D
    y=p['y0_V']; ideal=y; out=[]
    for n,x in enumerate(p['x_V']):
        y=ag*y-bg*(x-p['Vos_V'])
        ideal-=alpha*x
        out.append({'n':n,'ideal_after_V':str(ideal),'static_after_V':str(y)})
    return ag,bg,out


def physical(p):
    A=float(p['A0']); alpha=float(p['alpha']); cf=float(p['Cf_F'])
    y=float(p['y0_V']); r=float(p['s0_V']-p['y0_V']); vos=float(p['Vos_V'])
    k1=A/(A+1); k2=A/(A+1+alpha); rows=[]
    for n,xx in enumerate(p['x_V']):
        x=float(xx); q=r+alpha*x
        target2=k2*((1+alpha)*vos-q)
        w=target2+p['rho2']*(y-target2)
        s2=(q+w)/(1+alpha)
        rnext=s2-w
        target1=k1*(vos-rnext)
        ynext=target1+p['rho1']*(w-target1)
        rows.append({'n':n,'x_V':x,'r_before_V':r,'y_before_V':y,
                     'Qunion_C':cf*q,'target2_V':target2,'w_phi2_V':w,
                     's_phi2_V':s2,'qf_after_C':cf*rnext,'r_after_V':rnext,
                     'target1_V':target1,'y_next_V':ynext,'s_next_V':ynext+rnext,
                     'read_difference_V':ynext-w,
                     'static_relation_residual_V':s2-(vos-w/A)})
        r,y=rnext,ynext
    return rows


def matvec(M,v):
    return [sum(a*b for a,b in zip(row,v)) for row in M]


def parameters(p):
    A=float(p['A0']); a=float(p['alpha']); h=p['rho1']; t=p['rho2']
    beta=1/(1+a); gamma=a/(1+a); k1=A/(A+1); f=(1-t)*A/(A+1+a)
    c=h+(1-h)*k1*gamma
    M=[[beta+gamma*f,-gamma*t],[-c*f-(1-h)*k1*beta,c*t]]
    N=[gamma*(1+a*f),-a*c*f-(1-h)*k1*gamma]
    return M,N,[-gamma,c],[0.,1.]


def noise(p):
    n=len(p['x_V']); C=p['eta_cov_V2']; M,N,G2,G1=parameters(p)
    weights=[]
    for j in range(n):
        v=N[:]
        for _ in range(n-1-j):v=matvec(M,v)
        weights.append(v[1])
    eta_var=sum(weights[i]*weights[j]*float(C[i][j]) for i in range(n) for j in range(n))
    A=float(p['A0']); ta=float(p['tau_a_s']); S=float(p['ota_single_PSD_V2_per_Hz'])
    z1=S*A*A*p['tau1']/(4*ta*ta)*(1-p['rho1']**2)
    z2=S*A*A*p['tau2']/(4*ta*ta)*(1-p['rho2']**2)
    ota1=ota2=0.; rows=[]
    for j in range(n):
        g1=G1[:]; g2=G2[:]
        for _ in range(n-1-j):g1=matvec(M,g1);g2=matvec(M,g2)
        ota1+=g1[1]**2*z1;ota2+=g2[1]**2*z2
        rows.append({'j':j,'eta_to_yN':weights[j],'zeta1_to_yN':g1[1],
                     'zeta2_to_yN':g2[1]})
    mean_var=sum(sum(r) for r in C)/F(n*n)
    return {'information':'given eta covariance; white input OTA noise in disjoint windows; eta independent of OTA; deterministic initial state; phi2-switch noise NOT included',
            'eta_mean_variance_V2_exact':str(mean_var),'eta_yN_variance_V2':eta_var,
            'zeta1_variance_V2':z1,'zeta2_variance_V2':z2,
            'OTA_phi1_yN_variance_V2':ota1,'OTA_phi2_yN_variance_V2':ota2,
            'selected_ports_yN_variance_V2':eta_var+ota1+ota2,
            'M':M,'N':N,'G2':G2,'G1':G1,'rows':rows}


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def figure(path,p,rows):
    # Trace the actual same phase targets, not the scalar end-point interpolation.
    row=rows[0]; T2=float(p['Tphi2_s']); TH=float(p['Tisolated_s']); total=T2+TH
    if total==0:
        total=1e-9
    pts=[]
    for k in range(41):
        t=T2*k/40; y=row['target2_V']+math.exp(-t/p['tau2'])*(row['y_before_V']-row['target2_V'])
        pts.append((t,y))
    for k in range(1,41):
        t=TH*k/40; y=row['target1_V']+math.exp(-t/p['tau1'])*(row['w_phi2_V']-row['target1_V'])
        pts.append((T2+t,y))
    lo=min(v for t,v in pts);hi=max(v for t,v in pts);span=max(hi-lo,.01)
    X=lambda t:80+600*t/total
    Y=lambda v:380-260*(v-lo)/span
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 650" role="img" aria-labelledby="title desc">',
         '<title id="title">Finite OTA first-cycle phase recovery</title>',
         '<desc id="desc">Blue phi2 transfer followed by orange isolated summing-node recovery; w and next y can differ. Trace uses the same two-state equations and fixed first input as CSV.</desc>',
         '<rect width="760" height="650" fill="#fafbfc"/>',
         '<g font-family="Arial,sans-serif" font-size="18" fill="#152b3c">']
    def txt(x,y,s,size=18):out.append(f'<text x="{x}" y="{y}" font-size="{size}">{escape(str(s))}</text>')
    txt(25,35,'Finite OTA: two phases, two physical states',25)
    txt(25,70,'First input record; deterministic linear port model',17)
    for subset,color in [(pts[:41],'#2466b3'),(pts[40:],'#bd6120')]:
        out.append('<polyline points="'+' '.join(f'{X(t):.8f},{Y(v):.8f}' for t,v in subset)+f'" fill="none" stroke="{color}" stroke-width="4"/>')
    out.append(f'<path d="M80,400 H680 M80,110 V400 M{X(T2):.8f},110 V400" fill="none" stroke="#607989" stroke-width="2"/>')
    txt(20,115,'V')
    if T2+TH==0:
        out.append(f'<circle cx="80" cy="{Y(row["y_before_V"]):.8f}" r="6" fill="#2466b3"/>')
        txt(80,435,'0 ns; both windows zero')
        txt(225,245,'No elapsed time; output unchanged',18)
        txt(225,275,'Charge can redistribute instantly',18)
    else:
        txt(80,435,'0 ns / phi2 end' if T2==0 else '0')
        if T2>0 and TH>0:txt(X(T2)-22,435,f'{T2*1e9:.5g}')
        txt(605,435,f'{(T2+TH)*1e9:.5g} ns')
    txt(95,465,'phi2: S2 ON');txt(min(X(T2)+5,505),495,'isolated: S2 OFF')
    txt(25,535,f'y[0] = {row["y_before_V"]:.9f} V')
    txt(25,565,f'w[0] = {row["w_phi2_V"]:.9f} V; next y[1] = {row["y_next_V"]:.9f} V')
    txt(25,595,f'Cf charge fixed only during isolated interval; r = qf/Cf.')
    txt(25,625,'No saturation, switch Ron transient or physical noise in this trace.',16)
    for v in [lo,hi]:txt(12,Y(v)+5,f'{v:.3f}',15)
    path.write_text('\n'.join(out+['</g></svg>'])+'\n',encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',type=Path,default=Path(__file__).with_name('finite-ota-inputs.json'))
    ap.add_argument('--out-dir',type=Path,required=True)
    args=ap.parse_args();p=load(args.inputs)
    forbidden=set(Path(__file__).resolve().parents)|set(args.inputs.resolve().parents)
    if args.out_dir.is_symlink() or args.out_dir.resolve() in forbidden:
        ap.error('output must be a separate nonsymlink directory')
    if args.out_dir.exists() and (not args.out_dir.is_dir() or any(args.out_dir.iterdir())):
        ap.error('output must be absent or empty; old files preserved')
    ag,bg,stat=static(p);rows=physical(p);budget=noise(p)
    epsilon=float(p['absolute_error_V']/p['max_step_V'])
    result={'model':'A(s)=A0/(1+s*tau_a); zero OTA input current; ideal output drive; Cs sample completely established; no switch injection/thermal source except given eta; Cp A-to-ground',
            'read_protocol':'y[n] before phi2, w[n] phi2 end, next y[n+1] after isolated interval; generally w != next y',
            'ag_exact':str(ag),'bg_exact':str(bg),'alpha_exact':str(p['alpha']),
            'initial_equilibrium':p['s0_V']==p['Vos_V']-p['y0_V']/p['A0'],
            'tau1_s':p['tau1'],'tau2_s':p['tau2'],'rho1':p['rho1'],'rho2':p['rho2'],
            'max_step_V':float(p['max_step_V']),'absolute_error_V':float(p['absolute_error_V']),
            'phi2_required_s':p['tau2']*math.log(1/epsilon),
            'static':stat,'physical':rows,'noise':budget,
            'input_shape':[len(rows)],'state_shape':[len(rows)+1,2]}
    if not all(math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError('trajectory overflows binary64')
    serialized=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    args.out_dir.mkdir(parents=True,exist_ok=True)
    write_csv(args.out_dir/'phase-budget.csv',rows)
    write_csv(args.out_dir/'noise-budget.csv',budget['rows'])
    (args.out_dir/'results.json').write_text(serialized,encoding='utf-8')
    figure(args.out_dir/'finite-phase.svg',p,rows)
    print(json.dumps({'ag':str(ag),'bg':str(bg),'rho2':p['rho2'],
                      'first_w':rows[0]['w_phi2_V'],'first_next_y':rows[0]['y_next_V'],
                      'eta_mean_variance_V2':budget['eta_mean_variance_V2_exact']},sort_keys=True))


if __name__=='__main__':main()
