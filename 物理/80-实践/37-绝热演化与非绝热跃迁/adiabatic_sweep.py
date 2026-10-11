#!/usr/bin/env python3
"""Full two-level ODE via unitary CF4; finite-time projections, not hardware data."""
import argparse
import cmath
import csv
import html
import json
import math
from pathlib import Path

H_PLANCK = 6.62607015e-34
HBAR = H_PLANCK/(2*math.pi)


def inner(a,b): return sum(x.conjugate()*y for x,y in zip(a,b))
def norm(a): return math.sqrt(inner(a,a).real)
def mv(a,v): return [sum(x*y for x,y in zip(row,v)) for row in a]
def matrix(columns): return [list(x) for x in zip(*columns)]
def maxdiff(a,b): return max(abs(x-y) for u,v in zip(a,b) for x,y in zip(u,v))


def eigens(d,b,u):
    r=math.hypot(d,b*u); theta=math.atan2(d,b*u)
    c,s=math.cos(theta/2),math.sin(theta/2)
    return r,theta,[c,s],[-s,c]


def frozen_step(d,z,dt,v):
    """Exact exp[-i dt (d sigma_x + z sigma_z)/2] applied to v."""
    r=math.hypot(d,z)
    c=math.cos(dt*r/2); a=-1j*math.sin(dt*r/2)/r if r else -0.5j*dt
    x,y=v
    return [c*x+a*(z*x+d*y),c*y+a*(d*x-z*y)]


def advance(d,b,u,h,v,method):
    if method=='midpoint': return frozen_step(d,b*(u+h/2),h,v)
    # For affine H, the two-exponential fourth-order commutator-free
    # Magnus formula reduces to half steps at u+h/6, then u+5h/6.
    v=frozen_step(d,b*(u+h/6),h/2,v)
    return frozen_step(d,b*(u+5*h/6),h/2,v)


def propagate(d,b,L,n,intervals,method='cf4'):
    h=2*L/n; stride=n//intervals; columns=[[1+0j,0j],[0j,1+0j]]; mats=[]
    worst_unitarity=0.
    for k in range(n+1):
        if k%stride==0:
            mats.append(matrix(columns))
            worst_unitarity=max(worst_unitarity,abs(inner(columns[0],columns[0])-1),abs(inner(columns[1],columns[1])-1),abs(inner(columns[0],columns[1])))
        if k<n:
            u=-L+k*h
            columns=[advance(d,b,u,h,v,method) for v in columns]
    return mats,worst_unitarity


def primitive_gap(d,b,u):
    return (u*math.hypot(d,b*u)+(d*d/b)*math.asinh(b*u/d))/2


def jrs_bound(d,b,L,u):
    """Rank-one JRS Theorem 3, h(s)=H/E0, s=(u+L)/(2L), tau=2L."""
    r=math.hypot(d,b*u); rend=math.hypot(d,b*L)
    return b/2*(1/rend**2+1/r**2)+7*b*b/(4*d*d)*(u/r+L/rend)


def run_case(c,settings):
    d,b,L=c['gap_ratio'],c['sweep_ratio'],c['half_duration_scaled']
    intervals=settings['sample_intervals']; base=settings['base_steps']
    # Bound the largest frozen-H rotation per coarse step, not a claimed error bound.
    n=max(base,math.ceil(2*L*math.hypot(d,b*L)/settings['max_step_rotation']))
    n=math.ceil(n/intervals)*intervals
    if 4*n>settings['maximum_fine_steps']: raise ValueError('requested grid exceeds maximum_fine_steps')
    runs=[propagate(d,b,L,n*k,intervals) for k in (1,2,4)]
    midpoint=propagate(d,b,L,4*n,intervals,'midpoint')
    mats=runs[2][0]; r0,th0,up0,g0=eigens(d,b,-L)
    omega0=2*math.pi*settings['energy_scale_frequency_hz']; E0=H_PLANCK*settings['energy_scale_frequency_hz']
    rows=[]; gauge_error=0.; born_sum_error=0.; bound_violation=0.; phase0=primitive_gap(d,b,-L)/2
    for k,U in enumerate(mats):
        u=-L+2*L*k/intervals; r,theta,upper,ground=eigens(d,b,u); psi=mv(U,g0)
        phase=primitive_gap(d,b,u)/2-phase0
        ad=[cmath.exp(1j*phase)*x for x in ground]
        pexc=abs(inner(upper,psi))**2; pg=abs(inner(ground,psi))**2
        born_sum_error=max(born_sum_error,abs(pexc+pg-1))
        # Gauge g'=exp(i chi)g, gamma'=-chi(u)+chi(-L), c0'=exp(-i chi(-L)).
        chi=lambda x:settings['gauge_quadratic']*(x/L)**2+settings['gauge_linear']*x/L
        ad_gauge=[cmath.exp(1j*(phase-chi(u)+chi(-L)))*cmath.exp(1j*chi(u))*cmath.exp(-1j*chi(-L))*x for x in ground]
        gauge_error=max(gauge_error,max(abs(x-y) for x,y in zip(ad,ad_gauge)))
        bound=jrs_bound(d,b,L,u); bound_violation=max(bound_violation,pexc-min(1.,bound*bound))
        row={'case':c['id'],'u':u,'time_us':u/omega0*1e6,'detuning_over_gap':b*u/d,
             'E_plus_over_E0':r/2,'E_minus_over_E0':-r/2,'gap_over_E0':r,
             'theta_rad':theta,'eta_local':b*d/(2*r**3),'p_excited':pexc,'p_ground':pg,
             'p_z_plus':abs(psi[0])**2,'adiabatic_p_z_plus':abs(ground[0])**2,
             'adiabatic_p_excited':0.,'norm_error':abs(inner(psi,psi)-1),
             'dynamic_ground_phase_rad':phase,'ray_distance':math.sqrt(max(0.,2-2*abs(inner(ad,psi)))),
             'JRS_amplitude_bound':bound,'JRS_probability_bound':min(1.,bound*bound),
             'psi0_re':psi[0].real,'psi0_im':psi[0].imag,'psi1_re':psi[1].real,'psi1_im':psi[1].imag}
        for i in range(2):
            for j in range(2): row[f'U{i}{j}_re']=U[i][j].real; row[f'U{i}{j}_im']=U[i][j].imag
        rows.append(row)
    e1=max(maxdiff(a,bm) for a,bm in zip(runs[0][0],runs[1][0])); e2=max(maxdiff(a,bm) for a,bm in zip(runs[1][0],runs[2][0]))
    pm1=max(abs(abs(inner(eigens(d,b,row['u'])[2],mv(U,g0)))**2-row['p_excited']) for row,U in zip(rows,runs[1][0]))
    midprob=max(abs(abs(inner(eigens(d,b,row['u'])[2],mv(U,g0)))**2-row['p_excited']) for row,U in zip(rows,midpoint[0]))
    p_lz=math.exp(-math.pi*d*d/(2*b))
    info={'input':c,'dimension':2,'basis':['+z','-z'],'initial_preparation':'instantaneous ground at -L',
          'Delta_J':d*E0,'v_J_per_s':b*E0*omega0,'Delta_over_h_Hz':d*settings['energy_scale_frequency_hz'],
          'half_duration_seconds':L/omega0,'kappa':d*d/b,'eta_max':b/(2*d*d),
          'grids':[n,2*n,4*n],'max_U_coarse_half':e1,'max_U_half_fine':e2,
          'convergence_ratio':e1/e2 if e2 else None,'max_p_half_fine':pm1,
          'max_midpoint_CF4_probability_difference':midprob,'max_unitarity_error':max(x[1] for x in runs),
          'max_Born_sum_error':born_sum_error,'gauge_state_residual':gauge_error,
          'max_JRS_bound_violation':max(0.,bound_violation),
          'P_finite_excited':rows[-1]['p_excited'],'P_LZ_infinite_excited':p_lz,
          'finite_minus_LZ':rows[-1]['p_excited']-p_lz,'JRS_endpoint_amplitude_bound':rows[-1]['JRS_amplitude_bound'],
          'U_final':mats[-1]}
    if max(info['max_unitarity_error'],born_sum_error,gauge_error)>settings['norm_tolerance']: raise ArithmeticError('norm/Born/gauge check failed')
    if e2>settings['convergence_tolerance'] or info['max_JRS_bound_violation']>settings['convergence_tolerance']: raise ArithmeticError('convergence or theorem-bound check failed')
    return rows,info


def berry_check(settings):
    theta=settings['berry_cone_angle_rad']; c,s=math.cos(theta/2),math.sin(theta/2)
    rows=[]
    for n in (360,720,1440):
        for band in ('upper','lower'):
            vec=[]; gauged=[]
            for k in range(n):
                phi=2*math.pi*k/n
                v=[c,cmath.exp(1j*phi)*s] if band=='upper' else [-cmath.exp(-1j*phi)*s,c]
                phase=cmath.exp(1j*(0.31*math.sin(phi)+0.23*phi))
                vec.append(v); gauged.append([phase*x for x in v])
            product=math.prod(inner(vec[k],vec[(k+1)%n])/abs(inner(vec[k],vec[(k+1)%n])) for k in range(n))
            product2=math.prod(inner(gauged[k],gauged[(k+1)%n])/abs(inner(gauged[k],gauged[(k+1)%n])) for k in range(n))
            gamma=-cmath.phase(product); analytic=(-1 if band=='upper' else 1)*math.pi*(1-math.cos(theta))
            distance=abs(cmath.exp(1j*gamma)-cmath.exp(1j*analytic))
            rows.append({'points':n,'band':band,'gamma_rad_principal':gamma,'analytic_gamma_rad':analytic,
                         'phase_factor_error':distance,'cyclic_gauge_error':abs(product-product2)})
    return rows


def resonant_counterexample(epsilon):
    theta=math.atan2(epsilon,1); up=[math.cos(theta/2),math.sin(theta/2)]; g=[-math.sin(theta/2),math.cos(theta/2)]
    psi=frozen_step(epsilon,0,math.pi/epsilon,g)
    p=abs(inner(up,psi))**2
    return {'epsilon':epsilon,'local_ratio_everywhere':epsilon/(2*(1+epsilon**2)),
            'omega0_t':math.pi/epsilon,'P_excited_at_pi_pulse':p,'analytic_P':1/(1+epsilon**2)}


def real_json(x):
    if isinstance(x,complex): return [x.real,x.imag]
    if isinstance(x,dict): return {k:real_json(v) for k,v in x.items()}
    if isinstance(x,list): return [real_json(v) for v in x]
    return x


def csv_file(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def txt(x,y,s,size=14,color='#19232c',anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(s))}</text>'


def panel(x,y,w,h,xlo,xhi,ylo,yhi,xlabel,ylabel):
    out=[f'<path d="M{x},{y} V{y+h} H{x+w}" fill="none" stroke="#68727b"/>']
    for k in range(5):
        xv=xlo+(xhi-xlo)*k/4; yv=ylo+(yhi-ylo)*k/4
        xx=x+w*k/4; yy=y+h-h*k/4
        out += [txt(xx,y+h+22,f'{xv:g}',12,anchor='middle'),txt(x-8,yy+4,f'{yv:.3g}',12,anchor='end')]
    out += [txt(x+w/2,y+h+49,xlabel,13,anchor='middle'),txt(x,y-13,ylabel,14)]
    return out,lambda a,b:(x+(a-xlo)/(xhi-xlo)*w,y+h-(b-ylo)/(yhi-ylo)*h)


def line(points,transform,color,dash=''):
    pts=' '.join(f'{x:.4f},{y:.4f}' for x,y in (transform(a,b) for a,b in points))
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'


def svg(path,width,height,title,desc,elements):
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif">'+''.join(elements)+'</g></svg>\n')


def figures(out,all_rows,infos,boundary):
    colors=['#235d9c','#b44534','#267755','#8c4da0']; refid=infos[0]['input']['id']; rows=[r for r in all_rows if r['case']==refid]; L=infos[0]['input']['half_duration_scaled']
    elems=[txt(80,28,f'Full finite sweep: {refid}; start in instantaneous ground',18)]
    ymax=max(r['E_plus_over_E0'] for r in rows)*1.1
    p,tr=panel(80,75,690,180,-L,L,-ymax,ymax,'u = E0 t / hbar','E / E0'); elems+=p
    for key,color in [('E_plus_over_E0',colors[1]),('E_minus_over_E0',colors[0])]: elems.append(line([(r['u'],r[key]) for r in rows],tr,color))
    p,tr=panel(80,355,690,215,-L,L,0,1,'u = E0 t / hbar','Projection probability'); elems+=p
    for key,color,dash in [('p_excited',colors[1],''),('p_z_plus',colors[0],''),('adiabatic_p_z_plus',colors[2],'6 4')]: elems.append(line([(r['u'],r[key]) for r in rows],tr,color,dash))
    elems += [txt(90,660,'red: instantaneous excited; blue: fixed z+; dashed green: adiabatic z+',13),txt(90,690,'Different projection labels; both use the same initial state and Hamiltonian',13)]
    svg(out/'sweep.svg',850,720,'Avoided crossing and measured populations','Two energy branches and two distinct projection bases from trajectories.csv.',elems)
    elems=[txt(75,30,'Change speed or gap: finite-time excited probability',18)]
    for k,info in enumerate(infos):
        col=k%2; row=k//2; x=75+col*430; y=110+row*295; rs=[r for r in all_rows if r['case']==info['input']['id']]; end=max(r['detuning_over_gap'] for r in rs)
        p,tr=panel(x,y,340,175,-end,end,0,1,'x = vt / Delta',f'{info["input"]["id"]}: kappa={info["kappa"]:g}'); elems+=p
        elems.append(line([(r['detuning_over_gap'],r['p_excited']) for r in rs],tr,colors[k]))
        xx,yy=tr(end,info['P_LZ_infinite_excited']); elems.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="#111"/>')
        elems.append(txt(x,y+250,f'black dot: infinite-time final LZ = {info["P_LZ_infinite_excited"]:.6g}',12))
    elems += [txt(75,700,'Each curve starts at its own finite -T ground; dots are final asymptotic values only',13)]
    svg(out/'conditions.svg',920,735,'Speed and gap migration','Four complete finite-input curves; black dots compare only final infinite-time Landau-Zener probabilities.',elems)
    elems=[txt(80,28,'Extend endpoints at fixed Delta and v: not a slower fixed path',18)]
    xs=[r['endpoint_detuning_over_gap'] for r in boundary]; ps=[r['P_finite_excited'] for r in boundary]; pinf=boundary[0]['P_LZ_infinite_excited']
    ymax=max(ps+[pinf])*1.2
    p,tr=panel(80,90,690,200,min(xs),max(xs),0,ymax,'endpoint x = vT / Delta','Final excited probability'); elems+=p
    elems.append(line(list(zip(xs,ps)),tr,colors[0])); elems.append(line([(min(xs),pinf),(max(xs),pinf)],tr,colors[1],'6 4'))
    for a,b in zip(xs,ps): xx,yy=tr(a,b); elems.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="{colors[0]}"/>')
    vals=[abs(r['finite_minus_LZ']) for r in boundary]+[r['max_p_half_fine'] for r in boundary]
    logs=[math.log10(max(v,1e-18)) for v in vals]; lo=math.floor(min(logs))-1; hi=math.ceil(max(logs))+1
    p,tr=panel(80,400,690,180,min(xs),max(xs),lo,hi,'endpoint x = vT / Delta','log10 absolute probability difference'); elems+=p
    for key,color in [('finite_minus_LZ',colors[1]),('max_p_half_fine',colors[2])]: elems.append(line([(r['endpoint_detuning_over_gap'],math.log10(max(abs(r[key]),1e-18))) for r in boundary],tr,color))
    elems += [txt(80,665,'blue above: finite endpoint; dashed red above: infinite-time LZ',13),txt(80,693,'below red: finite-minus-LZ; green: half/fine grid error (separate quantities)',13)]
    svg(out/'boundary.svg',850,725,'Finite endpoints and numerical convergence','Both panels use boundary.csv; endpoint difference and step-size error are separately labelled.',elems)


def validate(inp):
    s=inp['settings']; ints=['sample_intervals','base_steps','maximum_fine_steps']
    for k in ints:
        if type(s[k]) is not int or s[k]<=0: raise ValueError(f'{k} positive integer required')
    if not 40<=s['sample_intervals']<=1000 or not 400<=s['base_steps']<=50000 or s['maximum_fine_steps']>1000000: raise ValueError('grid budget exceeded')
    for k in ['energy_scale_frequency_hz','max_step_rotation','norm_tolerance','convergence_tolerance']:
        if type(s[k]) not in (int,float) or not math.isfinite(s[k]) or s[k]<=0: raise ValueError(f'{k} finite positive required')
    if not 1e-3<=s['energy_scale_frequency_hz']<=1e12: raise ValueError('energy_scale_frequency_hz outside unit-conversion range')
    if not .01<=s['max_step_rotation']<=.5 or s['norm_tolerance']>1e-6 or s['convergence_tolerance']>1e-4: raise ValueError('step or tolerance budget invalid')
    for k in ['gauge_quadratic','gauge_linear','berry_cone_angle_rad','resonant_epsilon']:
        if type(s[k]) not in (int,float) or not math.isfinite(s[k]): raise ValueError('finite phase/counterexample parameters required')
    if not 0<s['berry_cone_angle_rad']<math.pi or not 0<s['resonant_epsilon']<=.1: raise ValueError('cone/epsilon invalid')
    if len(inp['cases'])!=4 or len(set(c['id'] for c in inp['cases']))!=4: raise ValueError('four unique case ids required for figure layout')
    for c in inp['cases']:
        for key,lo,hi in [('gap_ratio',.05,4),('sweep_ratio',.005,10),('half_duration_scaled',.1,400)]:
            if type(c[key]) not in (int,float) or not math.isfinite(c[key]) or not lo<=c[key]<=hi: raise ValueError(f'{key} outside finite input range')
    if not 2<=len(inp['boundary_half_durations'])<=12 or any(type(x) not in (int,float) or not math.isfinite(x) or not .1<=x<=400 for x in inp['boundary_half_durations']): raise ValueError('boundary durations invalid')
    if len(set(inp['boundary_half_durations']))<2: raise ValueError('at least two distinct boundary durations required for an axis')


def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json')); p.add_argument('--output',type=Path,default=Path(__file__).with_name('assets'))
    args=p.parse_args(); inp=json.loads(args.input.read_text()); validate(inp); s=inp['settings']; out=args.output; out.mkdir(parents=True,exist_ok=True)
    rows=[]; infos=[]
    for c in inp['cases']:
        rr,info=run_case(c,s); rows+=rr; infos.append(info)
    boundary=[]
    for L in inp['boundary_half_durations']:
        c={**inp['cases'][0],'half_duration_scaled':L}
        existing=next((i for i in infos if i['input']==c),None)
        info=existing if existing else run_case(c,s)[1]
        boundary.append({'half_duration_scaled':L,'endpoint_detuning_over_gap':c['sweep_ratio']*L/c['gap_ratio'],**{k:info[k] for k in ['P_finite_excited','P_LZ_infinite_excited','finite_minus_LZ','max_p_half_fine','max_U_half_fine','max_unitarity_error','JRS_endpoint_amplitude_bound']}})
    berry=berry_check(s); resonant=resonant_counterexample(s['resonant_epsilon'])
    result={'input':inp,'constants':{'h_J_s':H_PLANCK,'hbar_J_s':HBAR},'environment':{'Python_standard_library_only':True,'algorithm':'unitary affine-H CF4; midpoint cross-check','physical_device_data':False},'cases':infos,'boundary':boundary,'berry':berry,'resonant_counterexample':resonant}
    (out/'results.json').write_text(json.dumps(real_json(result),ensure_ascii=False,indent=2)+'\n')
    csv_file(out/'trajectories.csv',rows); csv_file(out/'boundary.csv',boundary); csv_file(out/'berry.csv',berry); figures(out,rows,infos,boundary)
    print(json.dumps({'cases':[(x['input']['id'],x['P_finite_excited'],x['max_U_half_fine']) for x in infos],'outputs':7,'trajectory_rows':len(rows)}))


if __name__=='__main__': main()
