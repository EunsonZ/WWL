"""Analytic magnetic BVP and material/QS models with independent quadratures.

All inputs use SI units. SVG labels are built from the same input object.
No finite-element solver, measured material data or hardware test is claimed.
"""

import argparse
import cmath
import csv
import json
import math
import platform
from pathlib import Path


MU0 = 4 * math.pi * 1e-7  # conventional approximation in H/m
C0 = 299792458.0
EPS0 = 1 / (MU0 * C0**2)


def simpson(f, left, right, n):
    h = (right - left) / n
    return h / 3 * (f(left) + f(right)
                    + 4 * sum(f(left + i * h) for i in range(1, n, 2))
                    + 2 * sum(f(left + i * h) for i in range(2, n, 2)))


def rectangle(p, grids, quadrature_n):
    a, b, current, mu = p['a_m'], p['b_m'], p['current_A'], MU0 * p['mu_r']
    kx, ky = math.pi / a, math.pi / b
    j0 = current * math.pi**2 / (4 * a * b)
    a0 = mu * j0 / (kx*kx + ky*ky)
    pot = lambda x, y: a0 * math.sin(kx*x) * math.sin(ky*y)
    field = lambda x, y: (a0*ky*math.sin(kx*x)*math.cos(ky*y), -a0*kx*math.cos(kx*x)*math.sin(ky*y))
    # Integrate the two distinct density expressions on a 40x40 Simpson grid.
    energy = simpson(lambda x: simpson(lambda y: sum(v*v for v in field(x,y))/(2*mu), 0,b,40),0,a,40)
    source_energy = simpson(lambda x: simpson(lambda y: .5*j0*math.sin(kx*x)*math.sin(ky*y)*pot(x,y),0,b,40),0,a,40)
    analytic = mu*j0*j0*a*b/(8*(kx*kx+ky*ky))
    returned = 2*simpson(lambda y: -a0*kx/mu*math.sin(ky*y),0,b,quadrature_n) + 2*simpson(lambda x: -a0*ky/mu*math.sin(kx*x),0,a,quadrature_n)
    residuals=[]
    for n in grids:
        hx,hy=a/n,b/n
        peak=0.0
        for ix in range(1,n):
            for iy in range(1,n):
                x,y=ix*hx,iy*hy
                lap=(pot(x+hx,y)-2*pot(x,y)+pot(x-hx,y))/hx**2+(pot(x,y+hy)-2*pot(x,y)+pot(x,y-hy))/hy**2
                source=mu*j0*math.sin(kx*x)*math.sin(ky*y)
                peak=max(peak,abs(-lap-source)/(mu*j0))
        residuals.append({'grid_intervals_each_axis':n,'max_normalized_PDE_residual':peak})
    return {'J0_A_per_m2':j0,'A0_Wb_per_m':a0,'I_volume_A':current,'I_return_quadrature_A':returned,
            'L_prime_H_per_m':2*analytic/current**2,'W_prime_J_per_m':analytic,'W_control_J':analytic*p['control_length_m'],
            'field_energy_quadrature_J_per_m':energy,'source_energy_quadrature_J_per_m':source_energy,
            'relative_energy_difference':abs(energy-source_energy)/analytic,
            'return_current_residual_A':returned+current,'PDE_grid_residuals':residuals}


def core_point(p, current):
    turns,area,lc,g=p['turns'],p['area_m2'],p['core_length_m'],p['gap_m']
    bs,h0=p['B_s_T'],p['B_s_T']/(MU0*p['initial_mu_r'])
    linear_l=turns**2*area/(lc/(MU0*p['initial_mu_r'])+g/MU0)
    if current==0:
        return {'I_A':0.0,'B_T':0.0,'lambda_Wb':0.0,'L_sec_H':linear_l,'L_inc_H':linear_l,'W_J':0.0,'ampere_residual_A':0.0}
    equation=lambda field: lc*h0*math.atanh(field/bs)+g*field/MU0
    left,right=0.0,bs*(1-1e-14)
    if equation(right)<turns*current:
        raise ValueError('Current requires a root closer to saturation than this floating-point bracket')
    for _ in range(80):
        mid=(left+right)/2
        if equation(mid)<turns*current:left=mid
        else:right=mid
    field=(left+right)/2
    fluxlink=turns*area*field
    increment=turns**2*area/(lc*h0/(bs*(1-(field/bs)**2))+g/MU0)
    core_density=h0*(field*math.atanh(field/bs)+bs/2*math.log1p(-(field/bs)**2))
    energy=area*lc*core_density+area*g*field**2/(2*MU0)
    return {'I_A':current,'B_T':field,'lambda_Wb':fluxlink,'L_sec_H':fluxlink/current,'L_inc_H':increment,
            'W_J':energy,'half_lambda_I_J':.5*fluxlink*current,'ampere_residual_A':equation(field)-turns*current}


def core(p, n):
    turns,area,lc,g=p['turns'],p['area_m2'],p['core_length_m'],p['gap_m']
    denom=lc/(MU0*p['initial_mu_r'])+g/MU0
    field=turns*p['sample_current_A']/denom
    linear_l=turns**2*area/denom
    sample=core_point(p,p['sample_current_A'])
    h0=p['B_s_T']/(MU0*p['initial_mu_r'])
    field_quad=area*lc*simpson(lambda B:h0*math.atanh(B/p['B_s_T']),0,sample['B_T'],n)+area*g*sample['B_T']**2/(2*MU0)
    step=p['sample_current_A']*1e-4
    derivative=(core_point(p,p['sample_current_A']+step)['lambda_Wb']-core_point(p,p['sample_current_A']-step)['lambda_Wb'])/(2*step)
    return {'linear':{'B_T':field,'L_H':linear_l,'W_J':.5*linear_l*p['sample_current_A']**2,
                      'gap_energy_fraction':g/(g+lc/p['initial_mu_r']),'gap_force_opening_N':-area*field**2/(2*MU0)},
            'nonlinear_sample':sample,'nonlinear_energy_quadrature_J':field_quad,
            'relative_energy_quadrature_error':abs(field_quad-sample['W_J'])/sample['W_J'],
            'L_incremental_finite_difference_H':derivative,
            'relative_incremental_difference':abs(derivative-sample['L_inc_H'])/sample['L_inc_H']}


def capacitor(p,frequency):
    epsilon,mu=EPS0*p['epsilon_r'],MU0*p['mu_r']
    omega=2*math.pi*frequency
    wave=omega*p['radius_m']*math.sqrt(epsilon*mu)
    capacitance=epsilon*math.pi*p['radius_m']**2/p['gap_m']
    return {'frequency_Hz':frequency,'C_F':capacitance,'I_peak_A':omega*capacitance*p['voltage_peak_V'],
            'kR':wave,'leading_center_field_relative_correction':wave**2/4,'leading_WB_over_WE':wave**2/8}


def skin(p,n):
    sigma,epsilon,mu=p['sigma_S_per_m'],EPS0*p['epsilon_r'],MU0*p['mu_r']
    omega,H0,d=2*math.pi*p['frequency_Hz'],p['H0_peak_A_per_m'],p['depth_m']
    area=p['width_m']*p['length_m']
    delta=math.sqrt(2/(omega*mu*sigma))
    exact=cmath.sqrt(1j*omega*mu*sigma-omega**2*mu*epsilon)
    mqs=(1+1j)/delta
    data={}
    for name,gamma,conductivity in [('full',exact,sigma+1j*omega*epsilon),('MQS',mqs,complex(sigma))]:
        impedance=gamma/conductivity
        incoming=.5*impedance.real*H0**2*area
        outgoing=incoming*math.exp(-2*gamma.real*d)
        joule=area*simpson(lambda x:.5*sigma*abs(impedance*H0*cmath.exp(-gamma*x))**2,0,d,n)
        data[name]={'gamma_real_per_m':gamma.real,'gamma_imag_per_m':gamma.imag,'Zs_real_ohm':impedance.real,'Zs_imag_ohm':impedance.imag,
                    'P_in_W':incoming,'P_out_W':outgoing,'P_joule_quadrature_W':joule,
                    'relative_power_balance_residual':abs(incoming-outgoing-joule)/incoming}
    data.update({'delta_MQS_m':delta,'d_over_delta':d/delta,'charge_relaxation_s':epsilon/sigma,
                 'omega_epsilon_over_sigma':omega*epsilon/sigma,'magnetic_diffusion_scale_s':mu*sigma*d*d,
                 'vacuum_k_length':omega*p['length_m']/C0,'relative_gamma_difference':abs(exact-mqs)/abs(exact)})
    return data


def svg_start(width,height,title,desc):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{title}</title><desc id="desc">{desc}</desc>',
            f'<rect width="{width}" height="{height}" fill="white"/>',
            '<style>text{font-family:Arial,sans-serif;font-size:13px;fill:#172b3a}.axis{stroke:#172b3a;fill:none}.blue{stroke:#1565c0;fill:none;stroke-width:2}.orange{stroke:#be5500;fill:none;stroke-width:2;stroke-dasharray:6 4}.grid{stroke:#d9e1e5;fill:none}</style>']


def rectangle_svg(p,r):
    a,b,mu=p['a_m'],p['b_m'],MU0*p['mu_r']
    a0=r['A0_Wb_per_m']
    kx,ky=math.pi/a,math.pi/b
    condition=f'a={a*1000:g} mm, b={b*1000:g} mm, I={p["current_A"]:g} A, mu_r={p["mu_r"]:g}'
    parts=svg_start(690,450,'Rectangular magnetic BVP: '+condition,'Analytic contours of Az; normalized arrows show B direction. Az=0 on four edges, with surface return current and zero exterior H. '+condition)
    parts += [f'<text x="75" y="25">{condition}</text>','<text x="75" y="48">Az=0 boundary; sheet return -I; contours Az (micro-Wb/m)</text>',
              '<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#34495e"/></marker></defs>']
    scale=min(500/a,260/b)
    xp=lambda x:75+scale*x
    yp=lambda y:350-scale*y
    parts.append(f'<rect class="axis" x="75" y="{yp(b):.3f}" width="{scale*a:.3f}" height="{scale*b:.3f}"/>')
    labels=[]
    for label_index,fraction in enumerate([.2,.4,.6,.8]):
        left=math.asin(fraction)/kx
        right=a-left
        xs=[left+(right-left)*i/150 for i in range(151)]
        lower=[math.asin(min(1,fraction/math.sin(kx*x)))/ky for x in xs]
        points=[(xp(x),yp(y)) for x,y in zip(xs,lower)]+[(xp(x),yp(b-y)) for x,y in reversed(list(zip(xs,lower)))]
        parts.append('<polygon class="blue" points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+'"/>')
        label=f'{fraction*a0*1e6:.3g}'
        # Alternate the contour annotation positions to keep adjacent rows
        # separate when the README width-change case compresses the height.
        label_physical_x=a/2-(min(60/scale,.12*a) if label_index%2 else 0)
        label_physical_y=math.asin(fraction/math.sin(kx*label_physical_x))/ky
        label_x,label_y=xp(label_physical_x)+4,yp(label_physical_y)-5
        # Draw opaque label backgrounds after all field arrows, so an arrow
        # cannot turn a positive contour value into an apparent minus sign.
        labels.append(f'<rect x="{label_x-4:.3f}" y="{label_y-13:.3f}" width="{len(label)*8+8}" height="17" fill="white"/><text x="{label_x:.3f}" y="{label_y:.3f}">{label}</text>')
    for ix in range(1,10):
        for iy in range(1,6):
            x,y=a*ix/10,b*iy/6
            bx,by=a0*ky*math.sin(kx*x)*math.cos(ky*y),-a0*kx*math.cos(kx*x)*math.sin(ky*y)
            norm=math.hypot(bx,by)
            if norm<abs(a0)*max(kx,ky)*1e-12:continue
            parts.append(f'<path d="M{xp(x):.3f} {yp(y):.3f}l{13*bx/norm:.3f} {-13*by/norm:.3f}" stroke="#34495e" marker-end="url(#arr)"/>')
    parts.extend(labels)
    for fraction in [0,.5,1]:
        parts.append(f'<text x="{xp(fraction*a):.3f}" y="375" text-anchor="middle">{fraction*a*1000:g}</text>')
        parts.append(f'<text x="65" y="{yp(fraction*b)+4:.3f}" text-anchor="end">{fraction*b*1000:g}</text>')
    parts += ['<text x="600" y="375">x (mm)</text>','<text x="25" y="70">y (mm)</text>',
              '<text x="75" y="414">Arrows share a display length; they show direction, not B magnitude.</text>',
              '<text x="75" y="436">Translation-invariant model; physical end closure is outside this BVP.</text></svg>']
    return '\n'.join(parts)


def core_svg(p):
    condition=f'N={p["turns"]:g}, A={p["area_m2"]*1e6:g} mm2, lc={p["core_length_m"]*1000:g} mm, gap={p["gap_m"]*1000:g} mm'
    material=f'initial mu_r={p["initial_mu_r"]:g}, Bs={p["B_s_T"]:g} T; reversible tanh model'
    parts=svg_start(690,570,'Gapped magnetic circuit: '+condition,condition+'. '+material+'. Top: B versus I. Bottom: secant and incremental inductance. No hysteresis data.')
    parts += [f'<text x="75" y="24">{condition}</text>',f'<text x="75" y="46">{material}</text>']
    points=[core_point(p,p['plot_max_current_A']*i/120) for i in range(121)]
    ymaxs=[p['B_s_T']*1.1,points[0]['L_inc_H']*1e6*1.1]
    for index,ymax in enumerate(ymaxs):
        top,bottom=85+index*230,255+index*230
        xp=lambda current:75+540*current/p['plot_max_current_A']
        yp=lambda value:bottom-170*value/ymax
        for i in range(5):
            y=bottom-170*i/4
            parts.append(f'<path class="grid" d="M75 {y}H615"/><text x="66" y="{y+4}" text-anchor="end">{ymax*i/4:.3g}</text>')
        parts.append(f'<path class="axis" d="M75 {top}V{bottom}H615"/>')
        for f in [0,.5,1]:parts.append(f'<text x="{xp(p["plot_max_current_A"]*f)}" y="{bottom+20}" text-anchor="middle">{p["plot_max_current_A"]*f:g}</text>')
        parts.append(f'<text x="640" y="{bottom+20}">I (A)</text>')
        if index==0:
            parts.append(f'<text x="75" y="{top-10}">B (T)</text>')
            series=[('blue','B_T',1)]
        else:
            parts.append(f'<text x="75" y="{top-10}">L (micro-H): blue solid secant; orange dashed incremental</text>')
            series=[('blue','L_sec_H',1e6),('orange','L_inc_H',1e6)]
        for style,key,factor in series:
            parts.append(f'<polyline class="{style}" points="'+ ' '.join(f'{xp(q["I_A"]):.3f},{yp(q[key]*factor):.3f}' for q in points)+'"/>')
    parts.append('<text x="75" y="552">A specified reversible material law; not measured core loss or saturation.</text></svg>')
    return '\n'.join(parts)


def skin_svg(p,r):
    delta=r['delta_MQS_m']
    extent=max(5*delta,p['depth_m'])
    condition=f'f={p["frequency_Hz"]:g} Hz; sigma={p["sigma_S_per_m"]:g} S/m; mu_r={p["mu_r"]:g}; epsilon_r={p["epsilon_r"]:g}'
    control=f'H0={p["H0_peak_A_per_m"]:g} A/m peak; control depth={p["depth_m"]*1e6:g} micrometers'
    parts=svg_start(690,565,'Skin diffusion: '+condition,condition+'. '+control+'. Full Maxwell solid and MQS dashed. Amplitude and real part at t=0 are distinct. Each horizontal axis is depth in micrometers.')
    parts += [f'<text x="75" y="24">{condition}</text>',f'<text x="75" y="46">{control}</text>']
    for index in range(2):
        top,bottom=85+index*230,255+index*230
        ymin,ymax=(0,1.05) if index==0 else (-.2,1.05)
        xp=lambda x:75+x/extent*540
        yp=lambda y:bottom-(y-ymin)/(ymax-ymin)*170
        for i in range(5):
            value=ymin+(ymax-ymin)*i/4
            y=yp(value)
            parts.append(f'<path class="grid" d="M75 {y:.3f}H615"/><text x="66" y="{y+4:.3f}" text-anchor="end">{value:.3g}</text>')
        parts.append(f'<path class="axis" d="M75 {top}V{bottom}H615"/>')
        parts.append(f'<text x="75" y="{top-10}">'+('|H/H0|' if index==0 else 'Re(H/H0) at t=0')+': solid full Maxwell; dashed MQS</text>')
        for f in [0,.5,1]:parts.append(f'<text x="{xp(extent*f):.3f}" y="{bottom+20}" text-anchor="middle">{extent*f*1e6:.3g}</text>')
        parts.append(f'<text x="640" y="{bottom+20}">x (um)</text>')
        xd=xp(p['depth_m'])
        parts.append(f'<path stroke="#777" stroke-dasharray="2 4" d="M{xd:.3f} {top}V{bottom}"/>')
        for style,key in [('blue','full'),('orange','MQS')]:
            gamma=complex(r[key]['gamma_real_per_m'],r[key]['gamma_imag_per_m'])
            values=[]
            for i in range(301):
                x=extent*i/300
                h=cmath.exp(-gamma*x)
                values.append(f'{xp(x):.3f},{yp(abs(h) if index==0 else h.real):.3f}')
            parts.append(f'<polyline class="{style}" points="'+ ' '.join(values)+'"/>')
    parts.append('<text x="75" y="551">Constant-material half-space; vertical marker is the finite control depth.</text></svg>')
    return '\n'.join(parts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    p=json.loads(args.input.read_text())
    for section in ['rectangle','core','capacitor','skin']:
        for value in p[section].values():
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('All model inputs must be finite and positive')
    n=p['simpson_subintervals']
    if not isinstance(n,int) or n<4 or n%2:raise ValueError('Need a positive even Simpson grid')
    if any(not isinstance(g,int) or g<4 for g in p['rectangle_residual_grids']):raise ValueError('Need integer residual grid sizes at least 4')
    result={'python':platform.python_version(),'inputs':p,'constants':{'mu0_H_per_m_approx':MU0,'c0_m_per_s':C0,'epsilon0_F_per_m_derived':EPS0},
            'rectangle':rectangle(p['rectangle'],p['rectangle_residual_grids'],n),'core':core(p['core'],n),
            'capacitor':capacitor(p['capacitor'],p['capacitor']['frequency_Hz']),
            'capacitor_compare':capacitor(p['capacitor'],p['capacitor']['compare_frequency_Hz']),
            'skin':skin(p['skin'],n)}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'values.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,text in [('rectangle-field.svg',rectangle_svg(p['rectangle'],result['rectangle'])),('core-response.svg',core_svg(p['core'])),('skin-depth.svg',skin_svg(p['skin'],result['skin']))]:
        (args.output_dir/name).write_text(text)
    with (args.output_dir/'skin-fields.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['x_m','H_real_A_per_m','H_imag_A_per_m','H_amplitude_A_per_m','E_real_V_per_m','E_imag_V_per_m','S_average_W_per_m2'])
        r=result['skin']['full']
        gamma=complex(r['gamma_real_per_m'],r['gamma_imag_per_m'])
        impedance=complex(r['Zs_real_ohm'],r['Zs_imag_ohm'])
        for i in range(101):
            x=p['skin']['depth_m']*i/100
            h=p['skin']['H0_peak_A_per_m']*cmath.exp(-gamma*x)
            e=-impedance*h
            writer.writerow([x,h.real,h.imag,abs(h),e.real,e.imag,-.5*(e*h.conjugate()).real])
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
