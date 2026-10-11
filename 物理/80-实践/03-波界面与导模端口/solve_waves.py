"""SI analytic plane-interface/layer and lossless slab/PEC-mode models.

Canonical source; standard library only. Peak phasors use exp(+i omega t).
Forward spatial phases use exp(-i beta z), so decaying roots have Im(q)<=0.
No measured materials, coupling structure, commercial EM solver or hardware.
"""
import argparse
import cmath
import csv
import html
import json
import math
import platform
from pathlib import Path

MU0 = 4 * math.pi * 1e-7  # approximation, not an exact modern SI constant
C0 = 299792458.0
EPS0 = 1 / (MU0 * C0**2)


def simpson(f, a, b, n):
    h = (b-a)/n
    return h/3*(f(a)+f(b)+4*sum(f(a+i*h) for i in range(1,n,2))
                +2*sum(f(a+i*h) for i in range(2,n,2)))


def complex_pair(z):
    return {'real':z.real, 'imag':z.imag}


def forward_root(z):
    q = cmath.sqrt(z)
    if q.imag > 0: q = -q
    if q.real < 0 and abs(q.imag) < 1e-15: q = -q
    return q


def interface_at(p, angle):
    omega=2*math.pi*C0/p['wavelength0_m']
    n1,n2=p['n_incident'],p['n_transmitted']
    k0=omega/C0; kx=k0*n1*math.sin(math.radians(angle))
    q1=k0*n1*math.cos(math.radians(angle))
    discriminant=(k0*n2)**2-kx*kx
    scale=max((k0*n2)**2,kx*kx)
    # Compare squared wave numbers before sqrt amplifies cancellation.
    if abs(discriminant)<=1e-12*scale:
        raise ValueError('Evaluate the exact critical angle by a limit, not division by zero')
    q2=forward_root(complex(discriminant))
    result={'angle_deg':angle,'q2_per_m':complex_pair(q2)}
    for pol in ['TE','TM']:
        y1=q1/(omega*MU0) if pol=='TE' else omega*EPS0*n1*n1/q1
        y2=q2/(omega*MU0) if pol=='TE' else omega*EPS0*n2*n2/q2
        reflection=(y1-y2)/(y1+y2); transmission=1+reflection
        reflected=abs(reflection)**2
        transmitted=y2.real/y1*abs(transmission)**2
        result[pol]={'r_tangential_E':complex_pair(reflection),
                     't_tangential_E':complex_pair(transmission),
                     'R':reflected,'T':transmitted,
                     'power_balance_residual':abs(1-reflected-transmitted),
                     'E_continuity_residual':abs(1+reflection-transmission),
                     'H_continuity_residual_normalized':abs(y1*(1-reflection)-y2*transmission)/y1}
    return result


def finite_layer(p,n):
    omega=2*math.pi*p['frequency_Hz']; k0=omega/C0
    kx=k0*p['n_incident']*math.sin(math.radians(p['angle_deg']))
    eps=[EPS0*p['n_incident']**2,
         EPS0*p['n_layer_real']**2-1j*p['sigma_layer_S_per_m']/omega,
         EPS0*p['n_exit']**2]
    qs=[forward_root(omega*omega*MU0*e-kx*kx) for e in eps]
    if any(abs(q)<1e-12*k0 for q in qs):
        raise ValueError('This layer implementation excludes exact q=0; evaluate the critical-angle limit separately')
    if abs(qs[0].imag)>0 or qs[2].real<=0:
        raise ValueError('This finite-layer power comparison requires propagating incident/exit media')
    length=p['thickness_m']; amplitude=p['incident_tangential_E_peak_V_per_m']
    records={}; samples={}
    for pol in ['TE','TM']:
        ys=[q/(omega*MU0) if pol=='TE' else omega*e/q for q,e in zip(qs,eps)]
        r23=(ys[1]-ys[2])/(ys[1]+ys[2]); phase=cmath.exp(-1j*qs[1]*length)
        back=r23*phase**2
        a=2*ys[0]/(ys[0]*(1+back)+ys[1]*(1-back)); b=a*back
        r=a+b-1; t=a*phase*(1+r23)
        def field(z):
            fwd=a*cmath.exp(-1j*qs[1]*z); rev=b*cmath.exp(1j*qs[1]*z)
            f=amplitude*(fwd+rev); g=amplitude*ys[1]*(fwd-rev)
            ez=-amplitude*kx/qs[1]*(fwd-rev) if pol=='TM' else 0j
            flux=.5*(f*g.conjugate()).real
            heat=.5*p['sigma_layer_S_per_m']*(abs(f)**2+abs(ez)**2)
            return f,g,flux,heat
        incoming=.5*ys[0].real*amplitude**2
        reflected=abs(r)**2; transmitted=ys[2].real/ys[0].real*abs(t)**2
        absorbed=simpson(lambda z:field(z)[3],0,length,n)/incoming
        f0,g0,_,_=field(0); fl,gl,_,_=field(length)
        charges=[]
        if pol=='TM':
            # D uses real epsilon; sigma is counted as free conduction.
            # Normal total current is continuous while free surface charge
            # may accumulate at a jump of conductivity.
            ei0=-amplitude*kx/qs[1]*(a-b)
            eiL=-amplitude*kx/qs[1]*(a*phase-b/phase)
            eo0=-amplitude*kx/qs[0]*(1-r)
            eoL=-amplitude*kx/qs[2]*t
            rho0=EPS0*p['n_layer_real']**2*ei0-eps[0]*eo0
            rhoL=eps[2]*eoL-EPS0*p['n_layer_real']**2*eiL
            scale=omega*EPS0*p['n_layer_real']**2*amplitude
            charges=[{'z_m':0.0,'rho_free_surface_C_per_m2':complex_pair(rho0),
                      'surface_continuity_residual_normalized':abs(1j*omega*rho0+p['sigma_layer_S_per_m']*ei0)/scale},
                     {'z_m':length,'rho_free_surface_C_per_m2':complex_pair(rhoL),
                      'surface_continuity_residual_normalized':abs(1j*omega*rhoL-p['sigma_layer_S_per_m']*eiL)/scale}]
        records[pol]={'r':complex_pair(r),'t_at_exit':complex_pair(t),
                      'R':reflected,'T':transmitted,'A_Joule_quadrature':absorbed,
                      'power_balance_residual':abs(1-reflected-transmitted-absorbed),
                      'incident_flux_W_per_m2':incoming,
                      'free_surface_charge_checks':charges,
                      'boundary_E_residual_normalized':max(abs(f0/amplitude-(1+r)),abs(fl/amplitude-t)),
                      'boundary_H_residual_normalized':max(abs(g0/amplitude-ys[0]*(1-r)),abs(gl/amplitude-ys[2]*t))/abs(ys[0])}
        samples[pol]=[{'z_m':length*i/200,'abs_Et_V_per_m':abs(field(length*i/200)[0]),
                       'net_flux_over_incident':field(length*i/200)[2]/incoming,
                       'heat_W_per_m3':field(length*i/200)[3]} for i in range(201)]
    return {'q_layer_per_m':complex_pair(qs[1]),'polarizations':records},samples


def mode_root(v,m,steps):
    if v <= m*math.pi/2:
        raise ValueError('At/below this cutoff there is no square-integrable guided mode')
    target=(m+1)*math.pi/2
    lo=m*math.pi/2; hi=min(v,target)
    for _ in range(steps):
        mid=(lo+hi)/2
        value=mid+math.asin(min(1,mid/v))-target
        if value<0:lo=mid
        else:hi=mid
    u=(lo+hi)/2; w=math.sqrt(max(0,v*v-u*u))
    return u,w


def slab_mode(p,v,m,n,steps):
    nc,ns=p['n_core'],p['n_clad']; k0=2*math.pi/p['wavelength0_m']; omega=C0*k0
    d=v/(k0*math.sqrt(nc*nc-ns*ns));u,w=mode_root(v,m,steps)
    h,kappa=u/d,w/d;beta=math.sqrt((nc*k0)**2-h*h)
    even=m%2==0;boundary=math.cos(u) if even else math.sin(u)
    core_i=d*(1+(1 if even else -1)*math.sin(2*u)/(2*u))
    clad_i=boundary**2/kappa;total_i=core_i+clad_i
    core_grad=h*h*d*(1+(-1 if even else 1)*math.sin(2*u)/(2*u))
    grad=core_grad+kappa*kappa*clad_i
    a=math.sqrt(2*omega*MU0*p['power_W']/(p['periodic_width_m']*beta*total_i))
    def e_unit(x):
        if abs(x)<=d:return math.cos(h*x) if even else math.sin(h*x)
        return (1 if even or x>0 else -1)*boundary*math.exp(-kappa*(abs(x)-d))
    def ep_unit(x):
        if abs(x)<d:return -h*math.sin(h*x) if even else h*math.cos(h*x)
        return -(1 if x>0 else -1)*kappa*e_unit(x)
    xmax=d+p['tail_decay_lengths']/kappa
    numerical=simpson(lambda x:e_unit(x)**2,-d,d,n)+2*simpson(lambda x:e_unit(x)**2,d,xmax,n)
    tail=boundary**2/kappa*math.exp(-2*kappa*(xmax-d))
    power_quad=p['periodic_width_m']*beta*a*a/(2*omega*MU0)*(numerical+tail)
    we=.25*EPS0*a*a*(nc*nc*core_i+ns*ns*clad_i)
    wm=.25*a*a/(omega*omega*MU0)*(beta*beta*total_i+grad)
    energy_velocity=(p['power_W']/p['periodic_width_m'])/(we+wm)
    group_velocity=C0*beta/(nc*nc*k0-u*u/(k0*d*d*(w+1)))
    # Perturb omega with this model's physical d fixed, not its normalized V.
    def beta_at(k):
        vi=k*d*math.sqrt(nc*nc-ns*ns);ui,_=mode_root(vi,m,steps)
        return math.sqrt((nc*k)**2-(ui/d)**2)
    dk=k0*1e-5;dbeta=(beta_at(k0+dk)-beta_at(k0-dk))/(2*dk)
    group_fd=C0/dbeta
    root_res=abs(u*math.tan(u)-w) if even else abs(-u/math.tan(u)-w)
    derivative_inner=-h*math.sin(u) if even else h*math.cos(u)
    derivative_outer=-kappa*boundary
    data={'mode_index':m,'parity':'even' if even else 'odd','V':v,'half_thickness_d_m':d,
          'u':u,'w':w,'root_residual':root_res,'n_eff':beta/k0,'beta_per_m':beta,
          'kappa_per_m':kappa,'decay_length_m':1/kappa,
          'E_coefficient_peak_V_per_m':a,'power_W':p['power_W'],
          'power_quadrature_plus_exact_tail_W':power_quad,
          'power_relative_error':abs(power_quad-p['power_W'])/p['power_W'],
          'cladding_power_fraction':clad_i/total_i,'tail_power_fraction_outside_control':tail/total_i,
          'control_x_max_m':xmax,'periodic_width_m':p['periodic_width_m'],
          'boundary_derivative_residual_normalized':abs(derivative_inner-derivative_outer)/h,
          'WE_J_per_m2':we,'WM_J_per_m2':wm,
          'electric_magnetic_energy_relative_difference':abs(we-wm)/(we+wm),
          'total_energy_control_length_J':(we+wm)*p['periodic_width_m']*p['control_length_m'],
          'phase_velocity_m_per_s':omega/beta,'group_velocity_m_per_s':group_velocity,
          'group_velocity_finite_difference_m_per_s':group_fd,'energy_velocity_m_per_s':energy_velocity,
          'group_energy_velocity_relative_difference':abs(group_velocity-energy_velocity)/group_velocity,
          'group_finite_difference_relative_error':abs(group_fd-group_velocity)/group_velocity}
    samples=[{'x_m':-xmax+2*xmax*i/400,'E_unit':e_unit(-xmax+2*xmax*i/400),
              'E_peak_V_per_m':a*e_unit(-xmax+2*xmax*i/400),
              'Hz_imag_peak_A_per_m':a*ep_unit(-xmax+2*xmax*i/400)/(omega*MU0),
              'Sz_W_per_m2':beta*a*a*e_unit(-xmax+2*xmax*i/400)**2/(2*omega*MU0)} for i in range(401)]
    return data,samples


def rectangle(p,n):
    a,b,length=p['width_a_m'],p['height_b_m'],p['length_m']
    epsilon,mu=EPS0*p['epsilon_r'],MU0*p['mu_r'];speed=1/math.sqrt(epsilon*mu)
    omega=2*math.pi*p['frequency_Hz'];kx=math.pi/a; k=omega/speed
    cutoff=speed/(2*a)
    if k<=kx:raise ValueError('The reference TE10 port must be above cutoff')
    beta=math.sqrt(k*k-kx*kx);impedance=omega*mu/beta
    e0=math.sqrt(4*impedance*p['forward_power_W']/(a*b))
    power=b*simpson(lambda x:e0*e0*math.sin(kx*x)**2/(2*impedance),0,a,n)
    we=epsilon*e0*e0*a*b/8;wm=mu*e0*e0*(beta*beta+kx*kx)*a*b/(8*omega*omega*mu*mu)
    below_omega=2*math.pi*p['below_cutoff_frequency_Hz'];below_k=below_omega/speed
    if below_k>=kx:raise ValueError('The comparison frequency must be below TE10 cutoff')
    alpha=math.sqrt(kx*kx-below_k*below_k)
    kz=math.pi/length;resonance=speed*math.sqrt(kx*kx+kz*kz)/(2*math.pi)
    cavity_e0=math.sqrt(8*p['cavity_total_energy_J']/(epsilon*a*b*length))
    # Separate spatial integrals of E and both H components for closed TE101.
    cavity_omega=2*math.pi*resonance
    e_int=b*simpson(lambda x:simpson(lambda z:cavity_e0**2*math.sin(kx*x)**2*math.sin(kz*z)**2,0,length,40),0,a,40)
    h_int=b*simpson(lambda x:simpson(lambda z:cavity_e0**2/(cavity_omega*mu)**2*(kz*kz*math.sin(kx*x)**2*math.cos(kz*z)**2+kx*kx*math.cos(kx*x)**2*math.sin(kz*z)**2),0,length,40),0,a,40)
    phases=[]
    for phase in [0,math.pi/4,math.pi/2]:
        electric=.5*epsilon*e_int*math.cos(phase)**2;magnetic=.5*mu*h_int*math.sin(phase)**2
        phases.append({'omega_t_rad':phase,'WE_instant_J':electric,'WM_instant_J':magnetic,
                       'total_relative_error':abs(electric+magnetic-p['cavity_total_energy_J'])/p['cavity_total_energy_J']})
    return {'TE10_cutoff_Hz':cutoff,'next_TE_cutoff_Hz':min(speed/a,speed/(2*b)),
            'beta_per_m':beta,'Z_TE_ohm':impedance,'E0_peak_V_per_m':e0,
            'power_quadrature_W':power,'power_relative_error':abs(power-p['forward_power_W'])/p['forward_power_W'],
            'WE_prime_J_per_m':we,'WM_prime_J_per_m':wm,'matched_control_segment_energy_J':(we+wm)*length,'energy_velocity_m_per_s':p['forward_power_W']/(we+wm),
            'phase_velocity_m_per_s':omega/beta,'group_velocity_m_per_s':speed*speed*beta/omega,
            'phase_group_product_over_speed_squared':(omega/beta)*(speed*speed*beta/omega)/(speed*speed),
            'matched_S21':complex_pair(cmath.exp(-1j*beta*length)),'matched_S11':complex_pair(0j),
            'modal_V_forward_peak_V':math.sqrt(2*p['reference_R_ohm']*p['forward_power_W']),
            'modal_I_forward_peak_A':math.sqrt(2*p['forward_power_W']/p['reference_R_ohm']),
            'below_cutoff_alpha_per_m':alpha,'single_decaying_field_amplitude_ratio':math.exp(-alpha*length),
            'single_decaying_field_average_axial_power_W':0.0,
            'cavity_TE101_frequency_Hz':resonance,'cavity_E0_peak_V_per_m':cavity_e0,
            'cavity_instantaneous_energy_checks':phases}


def svg_start(w,h,title,condition):
    esc=html.escape
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{esc(title)}</title><desc id="desc">{esc(condition)}</desc>',
            f'<rect width="{w}" height="{h}" fill="white"/>',
            '<style>text{font:13px Arial,sans-serif;fill:#172b3a}.axis{stroke:#172b3a;fill:none}.grid{stroke:#dde4ea;fill:none}.blue{stroke:#1565c0;stroke-width:2;fill:none}.orange{stroke:#b45100;stroke-width:2;fill:none;stroke-dasharray:6 4}.green{stroke:#16806a;stroke-width:2;fill:none}</style>']


def axes(parts,top,bottom,xlo,xhi,ylo,yhi,xlabel,ylabel):
    xp=lambda x:80+530*(x-xlo)/(xhi-xlo);yp=lambda y:bottom-(bottom-top)*(y-ylo)/(yhi-ylo)
    parts.append(f'<path class="axis" d="M80 {top}V{bottom}H610"/>')
    for f in [0,.25,.5,.75,1]:
        y=ylo+f*(yhi-ylo);x=xlo+f*(xhi-xlo)
        parts.append(f'<path class="grid" d="M80 {yp(y):.3f}H610"/><text x="70" y="{yp(y)+4:.3f}" text-anchor="end">{y:.3g}</text>')
        parts.append(f'<text x="{xp(x):.3f}" y="{bottom+20}" text-anchor="middle">{x:.3g}</text>')
    parts.append(f'<text x="80" y="{top-12}">{html.escape(ylabel)}</text>')
    parts.append(f'<text x="80" y="{bottom+42}">{html.escape(xlabel)}</text>')
    return xp,yp


def poly(parts,points,xp,yp,style):
    parts.append(f'<polyline class="{style}" points="'+' '.join(f'{xp(x):.3f},{yp(y):.3f}' for x,y in points)+'"/>')


def interface_svg(p):
    condition=f'n1={p["n_incident"]:g}, n2={p["n_transmitted"]:g}, lambda0={p["wavelength0_m"]*1e9:g} nm; tangential E amplitude convention'
    parts=svg_start(690,440,'Fresnel reflected power',condition)
    parts.extend([f'<text x="80" y="25">{html.escape(condition)}</text>','<text x="80" y="48">Blue: TE R; orange dashed: TM R. Incident medium lossless.</text>'])
    xp,yp=axes(parts,90,340,0,p['plot_max_angle_deg'],0,1.05,'Incidence angle from +z normal (degrees)','Reflected / incident power R (dimensionless)')
    points={key:[] for key in ['TE','TM']}
    for i in range(401):
        angle=p['plot_max_angle_deg']*i/400
        try:value=interface_at(p,angle)
        except ValueError:continue
        for key in points:points[key].append((angle,value[key]['R']))
    for key,style in [('TE','blue'),('TM','orange')]:poly(parts,points[key],xp,yp,style)
    parts.append('<text x="80" y="419">Evanescent decay in lossless medium is not Joule dissipation.</text></svg>')
    return '\n'.join(parts)


def layer_svg(p,samples):
    condition=f'f={p["frequency_Hz"]:g} Hz, layer n={p["n_layer_real"]:g}, sigma={p["sigma_layer_S_per_m"]:g} S/m, L={p["thickness_m"]*1000:g} mm'
    parts=svg_start(690,660,'Finite lossy slab: fields and normal power',condition)
    parts.extend([f'<text x="80" y="25">{condition}</text>',f'<text x="80" y="48">n in/out={p["n_incident"]:g}/{p["n_exit"]:g}, angle={p["angle_deg"]:g} deg, incident Et={p["incident_tangential_E_peak_V_per_m"]:g} V/m peak</text>'])
    max_e=max(q['abs_Et_V_per_m'] for pol in samples.values() for q in pol)*1.1
    for index,(key,ylim,label) in enumerate([('abs_Et_V_per_m',max_e,'Tangential E magnitude (V/m peak)'),('net_flux_over_incident',1.05,'Net Sz / incident Sz (dimensionless)')]):
        top,bottom=(90,280) if index==0 else (385,575)
        xp,yp=axes(parts,top,bottom,0,p['thickness_m']*1000,0,ylim,'z inside finite material layer (mm)',label)
        for pol,style in [('TE','blue'),('TM','orange')]:poly(parts,[(q['z_m']*1000,q[key]) for q in samples[pol]],xp,yp,style)
    parts.append('<text x="80" y="650">Blue: TE; orange dashed: TM. Both boundaries are matched by the solution.</text></svg>')
    return '\n'.join(parts)


def slab_svg(p,records,samples,steps):
    condition=f'nc={p["n_core"]:g}, ns={p["n_clad"]:g}, lambda0={p["wavelength0_m"]*1e9:g} nm, Vn={p["V_normalized"]:g}, P={p["power_W"]*1e6:g} micro-W'
    parts=svg_start(690,720,'Slab TE roots and normalized field',condition)
    parts.extend([f'<text x="80" y="25">{condition}</text>',f'<text x="80" y="48">Periodic width={p["periodic_width_m"]*1000:g} mm; x edges = +/-d, d={records[0]["half_thickness_d_m"]*1e9:.6g} nm</text>'])
    xmax=max(abs(q['x_m']) for data in samples for q in data);xp,yp=axes(parts,95,315,-xmax*1e9,xmax*1e9,-1.05,1.05,'Transverse x (nm)','E_y / coefficient A (dimensionless)')
    field_legend='; '.join(f'TE{m} '+['blue','orange dashed','green'][m%3] for m in range(len(samples)))
    parts.append(f'<text x="80" y="68">Upper fields: {html.escape(field_legend)}</text>')
    for m,data in enumerate(samples):poly(parts,[(q['x_m']*1e9,q['E_unit']) for q in data],xp,yp,['blue','orange','green'][m%3])
    d=records[0]['half_thickness_d_m']
    for edge in [-d,d]:parts.append(f'<path class="grid" stroke-dasharray="3 3" d="M{xp(edge*1e9):.3f} 95V315"/>')
    branch_legend='; '.join(f'TE{m} '+['blue','orange dashed','green'][m%3] for m in range(math.ceil(2*p['plot_V_max']/math.pi)))
    parts.append(f'<text x="80" y="389">Lower branches: {html.escape(branch_legend)}</text>')
    xp,yp=axes(parts,430,630,0,p['plot_V_max'],p['n_clad'],p['n_core'],'Vn (changing physical half-thickness at fixed lambda0)','Guided TE effective index (dimensionless)')
    for m in range(math.ceil(2*p['plot_V_max']/math.pi)):
        pts=[]
        for i in range(401):
            v=p['plot_V_max']*i/400
            if v<=m*math.pi/2 or v==0:continue
            u,_=mode_root(v,m,steps);neff=math.sqrt(p['n_core']**2-(u/v)**2*(p['n_core']**2-p['n_clad']**2));pts.append((v,neff))
        poly(parts,pts,xp,yp,['blue','orange','green'][m%3])
    parts.append('<text x="80" y="704">All shown branches are TE; cutoff points with zero decay are excluded.</text></svg>')
    return '\n'.join(parts)


def slab_root_data(p,modes,transfers,steps):
    existing={p['V_normalized']:modes,p['transfer_V_normalized']:transfers}
    conditions=[]
    for v in sorted({p['root_diagram_comparison_V'],p['V_normalized'],p['transfer_V_normalized']}):
        roots=[]
        for m in range(math.ceil(2*v/math.pi)):
            if v<=m*math.pi/2:continue
            if v in existing:
                record=existing[v][m];u,w=record['u'],record['w']
            else:u,w=mode_root(v,m,steps)
            residual=abs(u*math.tan(u)-w) if m%2==0 else abs(-u/math.tan(u)-w)
            roots.append({'mode_index':m,'parity':'even' if m%2==0 else 'odd',
                          'u':u,'w':w,'root_residual':residual})
        d=v/(2*math.pi/p['wavelength0_m']*math.sqrt(p['n_core']**2-p['n_clad']**2))
        conditions.append({'V':v,'half_thickness_d_m':d,'roots':roots})
    return conditions


def slab_roots_svg(p,conditions):
    description=(f'nc={p["n_core"]:g}, ns={p["n_clad"]:g}, lambda0={p["wavelength0_m"]*1e9:g} nm; '
                 'Vn panels='+', '.join(f'{c["V"]:g}' for c in conditions))
    parts=svg_start(690,135+310*len(conditions),'Slab TE characteristic intersections',description)
    parts.extend([f'<text x="80" y="25">{html.escape(description)}</text>',
                  '<text x="80" y="50">Blue: u tan(u), even TE; orange dashed: -u cot(u), odd TE.</text>',
                  '<text x="80" y="73">Green: w = sqrt(Vn^2-u^2); black circles: computed intersections.</text>',
                  '<text x="80" y="96">Only positive physical branches 0 &lt; u &lt; Vn; pole ends are not joined.</text>'])
    for index,condition in enumerate(conditions):
        v=condition['V'];top=155+index*310;bottom=top+165;ylim=1.3*v
        parts.append(f'<text x="80" y="{top-40}">Vn={v:g}; d={condition["half_thickness_d_m"]*1e9:.6g} nm</text>')
        xp,yp=axes(parts,top,bottom,0,v,0,ylim,'u = h d (dimensionless)','Characteristic function / w (dimensionless)')
        clip=f'root-panel-{index}'
        parts.append(f'<defs><clipPath id="{clip}"><rect x="80" y="{top}" width="530" height="165"/></clipPath></defs>')
        parts.append(f'<g clip-path="url(#{clip})">')
        poly(parts,[(v*i/400,math.sqrt(max(0,v*v-(v*i/400)**2))) for i in range(401)],xp,yp,'green')
        for root in condition['roots']:
            m=root['mode_index'];lo=m*math.pi/2;hi=min(v,(m+1)*math.pi/2)
            points=[]
            for i in range(401):
                u=lo+(hi-lo)*i/400
                if u==0:f=0.0
                elif i==400 and hi==(m+1)*math.pi/2:break
                else:f=u*math.tan(u) if m%2==0 else -u/math.tan(u)
                points.append((u,f))
                if f>ylim:break
            poly(parts,points,xp,yp,'blue' if m%2==0 else 'orange')
        parts.append('</g>')
        for root in condition['roots']:
            parts.append(f'<circle cx="{xp(root["u"]):.3f}" cy="{yp(root["w"]):.3f}" r="4" fill="#172b3a"/>')
        labels='; '.join(f'TE{q["mode_index"]}: u={q["u"]:.6g}, w={q["w"]:.6g}' for q in condition['roots'])
        parts.append(f'<text x="80" y="{bottom+68}">{html.escape(labels)}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def rectangle_svg(p,r):
    condition=f'a={p["width_a_m"]*1000:g} mm, b={p["height_b_m"]*1000:g} mm, L={p["length_m"]*1000:g} mm, eps_r={p["epsilon_r"]:g}, mu_r={p["mu_r"]:g}'
    parts=svg_start(690,680,'PEC TE10 propagation and TE101 closed cavity',condition)
    parts.extend([f'<text x="80" y="25">{condition}</text>',f'<text x="80" y="48">TE10 port f={p["frequency_Hz"]/1e9:g} GHz; closed-cavity f101={r["cavity_TE101_frequency_Hz"]/1e9:.6g} GHz</text>'])
    xp,yp=axes(parts,95,290,.5,2,0,2.2,'f / TE10 cutoff (dimensionless)','beta / kc solid; alpha / kc dashed (dimensionless)')
    poly(parts,[(x,math.sqrt(x*x-1)) for x in [1+i/200 for i in range(201)]],xp,yp,'blue')
    poly(parts,[(x,math.sqrt(1-x*x)) for x in [.5+i/400 for i in range(201)]],xp,yp,'orange')
    parts.append('<text x="80" y="365">Closed cavity: E_y / E0 = sin(pi x/a) sin(pi z/L), y-independent</text>')
    x0,z0,width,height=80,395,530,210
    for ix in range(60):
        for iz in range(24):
            value=math.sin(math.pi*(ix+.5)/60)*math.sin(math.pi*(iz+.5)/24)
            color=f'rgb({round(245-220*value)},{round(250-120*value)},{round(255-60*value)})'
            parts.append(f'<rect x="{x0+width*ix/60:.3f}" y="{z0+height*(23-iz)/24:.3f}" width="{width/60+.1:.3f}" height="{height/24+.1:.3f}" fill="{color}"/>')
    parts.extend([f'<rect class="axis" x="{x0}" y="{z0}" width="{width}" height="{height}"/>',
                  f'<text x="80" y="627">x: 0 to {p["width_a_m"]*1000:g} mm (left to right); z: 0 to {p["length_m"]*1000:g} mm (bottom to top)</text>',
                  '<text x="80" y="650">Darker blue = larger positive E_y/E0, range 0 to 1; not power density.</text>',
                  '<text x="80" y="673">PEC cavity has no dissipative linewidth or coupling port in this model.</text></svg>'])
    return '\n'.join(parts)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    p=json.loads(args.input.read_text());n=p['simpson_subintervals'];steps=p['mode_bisection_steps']
    if not isinstance(n,int) or n<4 or n%2:raise ValueError('Simpson count must be even integer >=4')
    if not isinstance(steps,int) or steps<20:raise ValueError('Bisection count must be integer >=20')
    for section in ['interface','layer','slab','rectangle']:
        for key,value in p[section].items():
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (value==0 and key not in ['sigma_layer_S_per_m','angle_deg','sample_angle_deg','TIR_angle_deg']):raise ValueError(f'Invalid nonnegative SI input {section}.{key}')
    if p['slab']['n_core']<=p['slab']['n_clad']:raise ValueError('Guided slab requires core index > cladding index')
    for section,key in [('interface','sample_angle_deg'),('interface','TIR_angle_deg'),('interface','plot_max_angle_deg'),('layer','angle_deg')]:
        if p[section][key]>=90:raise ValueError('Angles must be less than 90 degrees')
    layer,samples_layer=finite_layer(p['layer'],n);modes=[];samples_slab=[]
    for m in range(math.ceil(2*p['slab']['V_normalized']/math.pi)):
        if p['slab']['V_normalized']<=m*math.pi/2:continue
        data,points=slab_mode(p['slab'],p['slab']['V_normalized'],m,n,steps);modes.append(data);samples_slab.append(points)
    transfers=[]
    for m in range(math.ceil(2*p['slab']['transfer_V_normalized']/math.pi)):
        if p['slab']['transfer_V_normalized']<=m*math.pi/2:continue
        data,_=slab_mode(p['slab'],p['slab']['transfer_V_normalized'],m,n,steps);transfers.append(data)
    root_conditions=slab_root_data(p['slab'],modes,transfers,steps)
    rect=rectangle(p['rectangle'],n)
    result={'python':platform.python_version(),'inputs':p,'constants':{'mu0_H_per_m_approx':MU0,'c0_m_per_s':C0,'epsilon0_F_per_m_derived':EPS0},
            'interface_sample':interface_at(p['interface'],p['interface']['sample_angle_deg']),
            'interface_TIR_comparison':interface_at(p['interface'],p['interface']['TIR_angle_deg']),
            'layer':layer,'slab_TE_modes':modes,'slab_transfer_TE_modes':transfers,'slab_root_intersections':root_conditions,'rectangle':rect}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'values.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,svg in [('fresnel.svg',interface_svg(p['interface'])),('finite-layer.svg',layer_svg(p['layer'],samples_layer)),('slab-modes.svg',slab_svg(p['slab'],modes,samples_slab,steps)),('slab-roots.svg',slab_roots_svg(p['slab'],root_conditions)),('rectangle-cavity.svg',rectangle_svg(p['rectangle'],rect))]:
        (args.output_dir/name).write_text(svg)
    for name,data in [('layer-TE-fields.csv',samples_layer['TE']),('slab-TE0-fields.csv',samples_slab[0])]:
        with (args.output_dir/name).open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=data[0].keys());writer.writeheader();writer.writerows(data)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
