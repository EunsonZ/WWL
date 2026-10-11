"""Symmetric nondispersive slab: TM plus TE reference, peak exp(+iwt-ibz).

Standard library only. This is an additive practice-03 calculation; it neither
imports nor runs the existing solve_waves.py and never writes its output paths.
"""
import argparse
import csv
import html
import json
import math
import platform
from pathlib import Path

C0 = 299792458.0
MU0 = 4 * math.pi * 1e-7  # teaching approximation, not an exact SI definition
EPS0 = 1 / (MU0 * C0 * C0)


def root(v, m, ratio, steps=80):
    """Continuous phase residual; never bisect across a tan/cot pole."""
    if not math.isfinite(v) or v <= m * math.pi / 2 or m < 0:
        raise ValueError('At/below this branch cutoff: no normalizable guided mode')
    lo, hi = m * math.pi / 2, min(v, (m + 1) * math.pi / 2)
    for _ in range(steps):
        u = (lo + hi) / 2
        w = math.sqrt(max(0, (v-u)*(v+u)))
        residual = u - math.atan2(ratio*w, u) - m*math.pi/2
        if residual < 0:
            lo = u
        else:
            hi = u
    u = (lo+hi)/2
    w = math.sqrt(max(0, (v-u)*(v+u)))
    if w <= 0:
        raise ValueError('Root is numerically indistinguishable from cutoff')
    return u, w


def simpson(f, a, b, n):
    step = (b-a)/n
    return step/3 * (f(a)+f(b)+sum((4 if j%2 else 2)*f(a+j*step) for j in range(1,n)))


def solve(p, v, m, pol):
    nc, ns = p['n_core'], p['n_clad']
    ec, es = EPS0*nc*nc, EPS0*ns*ns
    ratio = ec/es if pol == 'TM' else 1.0
    k0 = 2*math.pi/p['wavelength0_m']
    omega = C0*k0
    d = v/(k0*math.sqrt(nc*nc-ns*ns))
    u, w = root(v,m,ratio,p['mode_bisection_steps'])
    h, q = u/d, w/d
    beta = math.sqrt((nc*k0)**2-h*h)
    even = m%2 == 0
    boundary = math.cos(u) if even else math.sin(u)
    sinc = math.sin(2*u)/(2*u)
    ic = d*(1+(1 if even else -1)*sinc)
    is_ = boundary**2/q  # both infinite claddings, not one
    gc = h*h*d*(1+(-1 if even else 1)*sinc)
    gs = q*q*is_
    iw = ic/ec+is_/es
    coefficient = math.sqrt(2*omega*p['power_W']/
        (p['periodic_width_m']*beta*(iw if pol=='TM' else (ic+is_)/MU0)))
    if pol == 'TM':
        ue = coefficient**2/(4*omega**2)*(beta**2*iw+gc/ec+gs/es)
        uh = MU0*coefficient**2*(ic+is_)/4
        clad_fraction = (is_/es)/iw
    else:
        ue = coefficient**2*(ec*ic+es*is_)/4
        uh = coefficient**2/(4*omega**2*MU0)*(beta**2*(ic+is_)+gc+gs)
        clad_fraction = is_/(ic+is_)
    def scalar(x, region):
        if region == 'core':
            return ((math.cos(h*x),-h*math.sin(h*x)) if even else
                    (math.sin(h*x),h*math.cos(h*x)))
        f = (1 if even or x>=0 else -1)*boundary*math.exp(-q*(abs(x)-d))
        return f, -(1 if x>=0 else -1)*q*f
    def fields(x, region):
        f, fp = scalar(x,region)
        eps = ec if region=='core' else es
        s, sp = coefficient*f, coefficient*fp
        if pol == 'TM':
            ex, ezi = beta*s/(omega*eps), -sp/(omega*eps)
            ey, hx, hy, hzi = 0.0,0.0,s,0.0
        else:
            ex,ezi,hy = 0.0,0.0,0.0
            ey,hx,hzi = s,-beta*s/(omega*MU0),sp/(omega*MU0)
        sz = (ex*hy-ey*hx)/2
        we = eps*(ex*ex+ey*ey+ezi*ezi)/4
        wh = MU0*(hx*hx+hy*hy+hzi*hzi)/4
        return {'x_m':x,'region':region,'scalar_over_coefficient':f,
                'Ex_peak_V_per_m':ex,'Ey_peak_V_per_m':ey,'Ez_imag_peak_V_per_m':ezi,
                'Hx_peak_A_per_m':hx,'Hy_peak_A_per_m':hy,'Hz_imag_peak_A_per_m':hzi,
                'Sz_W_per_m2':sz,'electric_energy_J_per_m3':we,'magnetic_energy_J_per_m3':wh}
    xmax = d+p['tail_decay_lengths']/q
    n=p['simpson_subintervals']
    def integral(key):
        return (simpson(lambda x:fields(x,'core')[key],-d,d,n)+
                2*simpson(lambda x:fields(x,'clad')[key],d,xmax,n)+
                fields(xmax,'clad')[key]/q)  # exact two-sided exponential tail
    checks={key:integral(key) for key in ('Sz_W_per_m2','electric_energy_J_per_m3','magnetic_energy_J_per_m3')}
    # Full four tangential conditions, and normal D, at both interfaces.
    interfaces=[]
    for x in (-d,d):
        a,b=fields(x,'core'),fields(x,'clad')
        interfaces.append({'x_m':x,'core':a,'clad':b,
            'Hy_jump_A_per_m':b['Hy_peak_A_per_m']-a['Hy_peak_A_per_m'],
            'Ez_imag_jump_V_per_m':b['Ez_imag_peak_V_per_m']-a['Ez_imag_peak_V_per_m'],
            'Ey_jump_V_per_m':b['Ey_peak_V_per_m']-a['Ey_peak_V_per_m'],
            'Hz_imag_jump_A_per_m':b['Hz_imag_peak_A_per_m']-a['Hz_imag_peak_A_per_m'],
            'Dx_jump_C_per_m2':es*b['Ex_peak_V_per_m']-ec*a['Ex_peak_V_per_m']})
    derivative_core = -h*math.sin(u) if even else h*math.cos(u)
    derivative_clad = -q*boundary
    derivative_residual = (d*(derivative_core-ratio*derivative_clad))
    du_dv = ratio*u*v/(w*(u*u+ratio*ratio*w*w)+ratio*v*v)
    vg = C0*beta/(nc*nc*k0-u*du_dv*v/(k0*d*d))
    def beta_at(k):
        vv=k*d*math.sqrt(nc*nc-ns*ns)
        uu,_=root(vv,m,ratio,p['mode_bisection_steps'])
        return math.sqrt((nc*k)**2-(uu/d)**2)
    dk=k0*1e-5
    vg_fd=C0/((beta_at(k0+dk)-beta_at(k0-dk))/(2*dk)) if k0*d*math.sqrt(nc*nc-ns*ns)*(1-1e-5)>m*math.pi/2 else None
    lhs=u*math.tan(u) if even else -u/math.tan(u)
    rec={'polarization':pol,'mode_index':m,'scalar_parity':'even' if even else 'odd',
         'V':v,'epsilon_core_over_clad':ec/es,'half_thickness_d_m':d,
         'u':u,'w':w,'h_per_m':h,'q_per_m':q,'beta_per_m':beta,'n_eff':beta/k0,
         'decay_length_m':1/q,'root_original_residual':lhs-ratio*w,
         'matching_derivative_dimensionless_residual':derivative_residual,
         'coefficient':coefficient,'coefficient_unit':'A/m' if pol=='TM' else 'V/m',
         'core_scalar_square_integral_m':ic,'clad_scalar_square_integral_m':is_,
         'power_W':p['power_W'],'power_per_y_width_W_per_m':p['power_W']/p['periodic_width_m'],
         'clad_power_fraction':clad_fraction,'UE_per_y_width_per_z_length_J_per_m2':ue,
         'UH_per_y_width_per_z_length_J_per_m2':uh,
         'energy_per_z_length_J_per_m':(ue+uh)*p['periodic_width_m'],
         'control_energy_J':(ue+uh)*p['periodic_width_m']*p['control_length_m'],
         'power_quadrature_with_tail_W':checks['Sz_W_per_m2']*p['periodic_width_m'],
         'power_quadrature_relative_error':abs(checks['Sz_W_per_m2']*p['periodic_width_m']/p['power_W']-1),
         'UE_quadrature_relative_error':abs(checks['electric_energy_J_per_m3']/ue-1),
         'UH_quadrature_relative_error':abs(checks['magnetic_energy_J_per_m3']/uh-1),
         'energy_equipartition_relative_error':abs(ue-uh)/(ue+uh),
         'omitted_tail_power_fraction_before_closure':clad_fraction*math.exp(-2*p['tail_decay_lengths']),
         'phase_velocity_m_per_s':omega/beta,'group_velocity_fixed_d_m_per_s':vg,
         'group_velocity_fd_fixed_d_m_per_s':vg_fd,
         'energy_velocity_m_per_s':(p['power_W']/p['periodic_width_m'])/(ue+uh),
         'interface_checks':interfaces}
    # Include separate core/cladding endpoint rows so jumps are never hidden.
    samples=[]
    for region,a,b in [('clad',-xmax,-d),('core',-d,d),('clad',d,xmax)]:
        samples.extend(fields(a+(b-a)*j/160,region) for j in range(161))
    return rec,samples


def modes(p,v,pol):
    return [solve(p,v,m,pol) for m in range(math.ceil(2*v/math.pi)) if v>m*math.pi/2]


def start_svg(width,height,title,subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f'<title>{html.escape(title)}</title><desc>{html.escape(subtitle)}</desc>',
            '<rect width="100%" height="100%" fill="white"/>',
            '<style>text{font-family:Arial,sans-serif;font-size:13px;fill:#172033} .title{font-size:19px;font-weight:bold} .small{font-size:11px}</style>',
            f'<text x="24" y="28" class="title">{html.escape(title)}</text>',
            f'<text x="24" y="51" class="small">{html.escape(subtitle)}</text>']


def panel(parts,box,xrange,yrange,title,xlabel,ylabel):
    x,y,ww,hh=box
    def xy(a,b):
        return x+ww*(a-xrange[0])/(xrange[1]-xrange[0]), y+hh*(1-(b-yrange[0])/(yrange[1]-yrange[0]))
    parts.append(f'<text x="{x}" y="{y-12}">{html.escape(title)}</text>')
    parts.append(f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="#fafbfe" stroke="#aab3c5"/>')
    for j in range(5):
        xv=xrange[0]+(xrange[1]-xrange[0])*j/4
        yv=yrange[0]+(yrange[1]-yrange[0])*j/4
        xx,_=xy(xv,yrange[0]);_,yy=xy(xrange[0],yv)
        parts.append(f'<text x="{xx}" y="{y+hh+17}" text-anchor="middle" class="small">{xv:.3g}</text>')
        parts.append(f'<text x="{x-8}" y="{yy+4}" text-anchor="end" class="small">{yv:.3g}</text>')
    parts.extend([f'<text x="{x+ww/2}" y="{y+hh+36}" text-anchor="middle">{html.escape(xlabel)}</text>',
                  f'<text x="{x}" y="{y-30}" class="small">{html.escape(ylabel)}</text>'])
    return xy


def line(parts,xy,points,color,dash=False):
    coords=' '.join(f'{xx:.3f},{yy:.3f}' for xx,yy in [xy(a,b) for a,b in points])
    parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="6 4"' if dash else '')+'/>')


def make_figures(p,cases,sweep):
    nc,ns=p['n_core'],p['n_clad'];ratio=(nc/ns)**2
    out={}
    parts=start_svg(800,750,'TM roots: two interfaces select the mode',f'nc={nc:g}, ns={ns:g}, lambda0={p["wavelength0_m"]*1e9:g} nm; Hy parity; u,w and characteristic functions dimensionless')
    for j,v in enumerate([p['V_normalized'],p['comparison_V_normalized'][-1]]):
        tm=cases[str(v)]['TM'];ymax=3.0 if v<=2 else 2*v
        xy=panel(parts,(85,112+j*310,635,205),(0,v),(0,ymax),f'V={v:g}; d={tm[0][0]["half_thickness_d_m"]*1e9:.3f} nm', 'u = h d (dimensionless)','blue: u tan u; orange dashed: -u cot u; green: (eps_c/eps_s) w')
        for rec,_ in tm:
            m=rec['mode_index'];lo=m*math.pi/2;hi=min(v,(m+1)*math.pi/2)
            pts=[]
            for k in range(1,200):
                u=lo+(hi-lo)*k/200
                f=u*math.tan(u) if m%2==0 else -u/math.tan(u)
                if 0<=f<=ymax:pts.append((u,f))
            line(parts,xy,pts,'#2360b3' if m%2==0 else '#c96b18',m%2==1)
            xx,yy=xy(rec['u'],ratio*rec['w'])
            labelx,anchor=(xx-7,'end') if rec['u']>0.8*v else (xx+7,'start')
            parts.append(f'<circle cx="{xx}" cy="{yy}" r="4" fill="#172033"/><text x="{labelx}" y="{yy-8}" text-anchor="{anchor}" class="small">TM{m}: u={rec["u"]:.6f}</text>')
        line(parts,xy,[(v*k/200,ratio*math.sqrt(max(0,v*v-(v*k/200)**2))) for k in range(201)],'#258557')
    parts.append('<text x="24" y="735" class="small">Only allowed positive branches shown; pole segments are omitted. Endpoint w=0 is not a normalizable mode.</text></svg>')
    out['tm-roots.svg']='\n'.join(parts)+'\n'
    tm,ts=cases[str(p['V_normalized'])]['TM'][0]
    te,es=cases[str(p['V_normalized'])]['TE'][0]
    d=tm['half_thickness_d_m'];extent=3*d*1e6
    parts=start_svg(1130,1130,'Same slab, same forward power: TE0 and TM0',f'V={p["V_normalized"]:g}, d={d*1e9:.3f} nm, {p["power_W"]*1e6:g} uW; y periodic width {p["periodic_width_m"]*1e3:g} mm, z control length {p["control_length_m"]*1e3:g} mm')
    specs=[('Hy_peak_A_per_m',None,'TM0 magnetic field (blue)','Hy peak (A/m)',(0,tm['coefficient']*1.12)),
           ('Ex_peak_V_per_m','Ey_peak_V_per_m','TM0 Ex blue; TE0 Ey orange dashed','electric field peak (V/m)',(0,max(max(z['Ex_peak_V_per_m'] for z in ts),te['coefficient'])*1.12)),
           ('Ez_imag_peak_V_per_m',None,'TM0 longitudinal electric field','Im Ez peak (V/m)',(-max(abs(z['Ez_imag_peak_V_per_m']) for z in ts)*1.12,max(abs(z['Ez_imag_peak_V_per_m']) for z in ts)*1.12)),
           ('Sz_W_per_m2','Sz_W_per_m2','Forward power density: TM0 blue; TE0 orange dashed','Sz (W/m^2)',(0,max(max(z['Sz_W_per_m2'] for z in ts),max(z['Sz_W_per_m2'] for z in es))*1.12))]
    for j,(key,tkey,title,label,yr) in enumerate(specs):
        xy=panel(parts,(95,110+j*250,950,165),(-extent,extent),yr,title,'x (um)',label)
        for side in (-d,d):
            xx,_=xy(side*1e6,0)
            parts.append(f'<line x1="{xx}" x2="{xx}" y1="{110+j*250}" y2="{275+j*250}" stroke="#8993a6" stroke-dasharray="3 3"/>')
        for rows,k,col,dash in [(ts,key,'#2360b3',False),(es,tkey,'#c96b18',True)]:
            if k:
                # Draw each smooth piece separately; field/power jumps at the interface are real.
                for segment in (rows[:161],rows[161:322],rows[322:]):
                    line(parts,xy,[(z['x_m']*1e6,z[k]) for z in segment if abs(z['x_m']*1e6)<=extent],col,dash)
    parts.append('<text x="24" y="1110" class="small">Vertical dotted lines: x=+/-d. Core between lines; cladding outside. Plot cropped; normalization includes both infinite tails.</text></svg>')
    out['tm-fields.svg']='\n'.join(parts)+'\n'
    parts=start_svg(800,710,'Change thickness: confinement depends on branch',f'Fixed nc={nc:g}, ns={ns:g}, lambda0={p["wavelength0_m"]*1e9:g} nm; varying d (not frequency response); blue TM, orange dashed TE')
    for j,(key,label,yr,title) in enumerate([('n_eff','n_eff (dimensionless)',(ns,nc),'Propagation constant'),('clad_power_fraction','cladding fraction (dimensionless)',(0,1),'Fraction of forward power in both claddings')]):
        xy=panel(parts,(85,112+j*295,630,190),(0,p['plot_V_max']),yr,title,'V = k0 d sqrt(nc^2-ns^2) (dimensionless)',label)
        for pol,col,dash in [('TM','#2360b3',False),('TE','#c96b18',True)]:
            for m in range(math.ceil(2*p['plot_V_max']/math.pi)):
                pts=[(z['V'],z[key]) for z in sweep[pol] if z['mode_index']==m]
                if pts:line(parts,xy,pts,col,dash)
    parts.append('<text x="24" y="695" class="small">Branches start strictly above m*pi/2; endpoint cutoff excluded. Every mode separately normalized to the input power.</text></svg>')
    out['tm-confinement.svg']='\n'.join(parts)+'\n'
    return out


def validate(p):
    keys=('n_core','n_clad','wavelength0_m','V_normalized','periodic_width_m','control_length_m','power_W','tail_decay_lengths','plot_V_max')
    for k in keys:
        if isinstance(p[k],bool) or not isinstance(p[k],(int,float)) or not math.isfinite(p[k]) or p[k]<=0:
            raise ValueError(f'{k} must be finite positive')
    if p['n_core']<=p['n_clad']:raise ValueError('Guided slab requires n_core > n_clad')
    for v in [p['V_normalized'],p['plot_V_max']]+p['comparison_V_normalized']:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0.05<=v<=8:
            raise ValueError('This numerical practice accepts 0.05 <= V <= 8')
    for key in ('simpson_subintervals','mode_bisection_steps'):
        if type(p[key]) is not int:raise ValueError(f'{key} must be an integer')
    if not 20<=p['simpson_subintervals']<=20000 or p['simpson_subintervals']%2:raise ValueError('Simpson count must be even, 20..20000')
    if not 40<=p['mode_bisection_steps']<=100:raise ValueError('Bisection steps must be 40..100')
    if not 1<=p['tail_decay_lengths']<=20:raise ValueError('Tail decay lengths must be 1..20')
    if not p['comparison_V_normalized']:raise ValueError('At least one comparison V is needed')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--require-mode',type=int,help='Reject if this TM branch is at/below cutoff')
    args=ap.parse_args()
    p=json.loads(args.input.read_text());validate(p)
    if args.require_mode is not None:root(p['V_normalized'],args.require_mode,(p['n_core']/p['n_clad'])**2)
    cases={}
    for v in dict.fromkeys([p['V_normalized']]+p['comparison_V_normalized']):
        cases[str(v)]={pol:modes(p,v,pol) for pol in ('TM','TE')}
    # Sweep root/analytic quantities only; numerical quadrature is still bounded.
    sweep={pol:[] for pol in ('TM','TE')}
    quick=dict(p);quick['simpson_subintervals']=20
    for j in range(1,91):
        v=p['plot_V_max']*j/90
        if v<0.05:continue
        for pol in sweep:
            for rec,_ in modes(quick,v,pol):
                sweep[pol].append({k:rec[k] for k in ('V','mode_index','n_eff','clad_power_fraction')})
    result={'python':platform.python_version(),'inputs':p,'phasor':'peak exp(+i omega t - i beta z)',
            'constants':{'c0_m_per_s':C0,'mu0_H_per_m_approx':MU0,'epsilon0_F_per_m_derived':EPS0},
            'cases':{v:{pol:[r for r,_ in records] for pol,records in data.items()} for v,data in cases.items()},
            'sweep':sweep,'cutoff_rule':'strict V > m*pi/2; equality is not square integrable',
            'numerical_V_envelope':[0.05,8.0]}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    (args.output_dir/'values.json').write_text(encoded)
    for name,svg in make_figures(p,cases,sweep).items():(args.output_dir/name).write_text(svg)
    for pol in ('TM','TE'):
        rec,samples=cases[str(p['V_normalized'])][pol][0]
        with (args.output_dir/f'{pol}0-fields.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(samples[0]),lineterminator='\n')
            writer.writeheader();writer.writerows(samples)
    print(encoded,end='')


if __name__=='__main__':main()
