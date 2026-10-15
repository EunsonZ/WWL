#!/usr/bin/env python3
"""Finite teaching cards; standard library only. Energies are SI internally."""
import argparse
import cmath
import csv
import html
import json
import math
from pathlib import Path

Q = 1.602176634e-19
HBAR = 1.054571817e-34
KB = 1.380649e-23
M0 = 9.1093837015e-31


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def reciprocal(a):
    volume = dot(a[0], cross(a[1], a[2]))
    if volume <= 0:
        raise ValueError("primitive basis must be right-handed and independent")
    b = [[2*math.pi*x/volume for x in cross(a[(i+1)%3], a[(i+2)%3])] for i in range(3)]
    return volume, b


def cubic_band(k, a, t, onsite=0.0):
    energy = onsite - 2*t*sum(math.cos(a*x) for x in k)
    velocity = [2*t*a/HBAR*math.sin(a*x) for x in k]
    inverse_mass = [2*t*a*a/HBAR**2*math.cos(a*x) for x in k]
    return energy, velocity, inverse_mass


def chain_omega(q, a, spring, mass):
    return 2*math.sqrt(spring/mass)*abs(math.sin(q*a/2))


def acoustic_rate(energy, temperature, mass, deformation, rho, sound):
    """Equipartition/quasi-elastic 3D LA rate; DOS for one spin only."""
    if energy < 0 or temperature <= 0:
        raise ValueError("nonnegative energy and positive temperature required")
    dos_one_spin = (2*mass/HBAR**2)**1.5*math.sqrt(energy)/(4*math.pi**2)
    return 2*math.pi/HBAR * deformation**2*KB*temperature/(rho*sound**2) * dos_one_spin


def simpson(function, stop, intervals):
    if intervals < 2 or intervals % 2:
        raise ValueError("positive even integration intervals required")
    step = stop/intervals
    return step/3*(function(0)+function(stop)+sum((4 if i % 2 else 2)*function(i*step) for i in range(1, intervals)))


def moments(stop, intervals):
    # tau(E)/tau(kBT)=u**(-1/2); factor u**1.5 makes both moments integrable.
    denominator = simpson(lambda u: u**1.5*math.exp(-u), stop, intervals)
    first = simpson(lambda u: u*math.exp(-u), stop, intervals)/denominator
    second = simpson(lambda u: math.sqrt(u)*math.exp(-u), stop, intervals)/denominator
    return first, second, second/first**2


def impurity_angular_ratio(screening_over_k):
    """tau_tr / tau_s, after common Coulomb dimensional prefactor cancels."""
    s = screening_over_k**2
    rate_s = (1/s-1/(s+4))/2
    rate_tr = (math.log1p(4/s)-4/(s+4))/4
    return rate_s/rate_tr


def plot(path, title, xlabel, ylabel, curves, xmin, xmax, ymin, ymax):
    width, height = 760, 380
    left, right, top, bottom = 85, 30, 50, 85
    def point(x, y):
        return (left+(x-xmin)/(xmax-xmin)*(width-left-right), height-bottom-(y-ymin)/(ymax-ymin)*(height-top-bottom))
    esc = html.escape
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img"><title>{esc(title)}</title><desc>{esc(xlabel)}; {esc(ylabel)}. Teaching inputs; curves computed from the equations in lattice_transport.py.</desc><rect width="100%" height="100%" fill="white"/>']
    parts.append(f'<text x="25" y="25" font-size="18">{esc(title)}</text>')
    for fraction in [0, .25, .5, .75, 1]:
        x = xmin+fraction*(xmax-xmin); px, py = point(x, ymin)
        parts.append(f'<path d="M{px:.2f},{top} V{py:.2f}" stroke="#ddd"/><text x="{px:.2f}" y="{py+20:.2f}" text-anchor="middle" font-size="12">{x:.3g}</text>')
        y = ymin+fraction*(ymax-ymin); px, py = point(xmin, y)
        parts.append(f'<path d="M{px:.2f},{py:.2f} H{width-right}" stroke="#ddd"/><text x="{left-10}" y="{py+4:.2f}" text-anchor="end" font-size="12">{y:.3g}</text>')
    for index, (label, color, dash, values) in enumerate(curves):
        points = ' '.join(f'{px:.2f},{py:.2f}' for px, py in (point(x, y) for x, y in values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/><text x="{left+index*220}" y="{height-12}" font-size="12" fill="{color}">{esc(label)}</text>')
    parts.append(f'<text x="{width/2}" y="{height-38}" text-anchor="middle">{esc(xlabel)}</text><text x="15" y="{height/2}" transform="rotate(-90 15 {height/2})" text-anchor="middle">{esc(ylabel)}</text></svg>')
    path.write_text('\n'.join(parts)+'\n', encoding='utf-8')


def geometry_plot(path, b):
    # Hexagonal reciprocal vectors in nm^-1; six nearest reciprocal vectors define BZ.
    b1, b2 = b[0], b[1]
    g = math.hypot(b1[0], b1[1]); radius = g/math.sqrt(3)
    bz = [(radius*math.cos(i*math.pi/3), radius*math.sin(i*math.pi/3)) for i in range(7)]
    cell = [(s*b1[0]+t*b2[0], s*b1[1]+t*b2[1]) for s,t in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5),(-.5,-.5)]]
    # Dedicated geometry drawing uses equal scales, unlike generic line plots.
    scale = 12
    def points(values):
        return ' '.join(f'{380+x*scale:.2f},{220-y*scale:.2f}' for x,y in values)
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 450" role="img"><title>Hexagonal reciprocal cell</title><desc>Equal kx and ky scales in nm^-1; solid first BZ and dashed primitive cell have equal area.</desc><rect width="100%" height="100%" fill="white"/><text x="20" y="25">First BZ (solid) and primitive reciprocal cell (dashed)</text><path d="M50 220H710 M380 40V400" stroke="#999"/>']
    parts += [f'<polyline points="{points(bz)}" fill="none" stroke="#1565c0" stroke-width="3"/>',f'<polyline points="{points(cell)}" fill="none" stroke="#c45100" stroke-dasharray="7 5" stroke-width="2"/>']
    for h1,h2 in [(0,0),(1,0),(0,1),(1,1),(-1,0),(0,-1),(-1,-1)]:
        x=h1*b1[0]+h2*b2[0];y=h1*b1[1]+h2*b2[1]
        parts.append(f'<circle cx="{380+x*scale:.2f}" cy="{220-y*scale:.2f}" r="4"/><text x="{385+x*scale:.2f}" y="{215-y*scale:.2f}">({h1},{h2})</text>')
    for v in [-10,0,10]:
        parts.append(f'<text x="{380+v*scale}" y="240" text-anchor="middle">{v}</text><text x="355" y="{220-v*scale}">{v}</text>')
    parts.append('<text x="665" y="205">kx (nm^-1)</text><text x="390" y="80">ky (nm^-1)</text></svg>')
    path.write_text('\n'.join(parts)+'\n',encoding='utf-8')


def write_csv(path, header, rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(header);writer.writerows(rows)


def build(card, out):
    out.mkdir(parents=True,exist_ok=True);assets=out/'assets';assets.mkdir(exist_ok=True)
    hx=card['hexagonal'];a=hx['a_nm'];c=hx['c_nm']
    primitive=[[a,0,0],[a/2,math.sqrt(3)*a/2,0],[0,0,c]]
    volume,b=reciprocal(primitive)
    dual=[[dot(x,y) for y in b] for x in primitive]
    cells=math.prod(hx['cells'])
    band=card['tight_binding'];a_m=band['a_nm']*1e-9;t=band['t_eV']*Q;onsite=band['onsite_eV']*Q
    rows=[]
    for i in range(201):
        x=i/200;k=x*math.pi/a_m;e,v,im=cubic_band([k,0,0],a_m,t,onsite)
        rows.append([x,(e-(onsite-6*t))/Q,t*(k*a_m)**2/Q,v[0],im[0]])
    write_csv(out/'band.csv',['ka_over_pi','E_minus_Ec_eV','parabola_eV','vx_m_per_s','inverse_mass_kg_inverse'],rows)
    plot(assets/'tight-binding.svg','Cubic band along Gamma-X','ka / pi','E - Ec (eV)', [('cosine','#1565c0','',[(r[0],r[1]) for r in rows]),('edge parabola','#c45100','6 4',[(r[0],r[2]) for r in rows])],0,1,0,2.5)
    plot(assets/'band-velocity.svg','Group velocity; curvature vanishes at ka=pi/2','ka / pi','vx (10^5 m/s)', [('vx','#1565c0','',[(r[0],r[3]/1e5) for r in rows])],0,1,0,4)
    geometry_plot(assets/'reciprocal-cell.svg',b)
    n_ring=16
    max_orth=0
    for j in range(n_ring):
        for l in range(n_ring):
            overlap=sum(cmath.exp(2j*math.pi*(l-j)*r/n_ring)/n_ring for r in range(n_ring))
            max_orth=max(max_orth,abs(overlap-(1 if j==l else 0)))
    chain=card['chain'];a_ch=chain['a_nm']*1e-9;spring=chain['spring_N_per_m'];mass_ch=chain['mass_kg']
    phonons=[[i/200,chain_omega(i/200*math.pi/a_ch,a_ch,spring,mass_ch)/1e12] for i in range(201)]
    write_csv(out/'phonon.csv',['qa_over_pi','omega_1e12_rad_per_s'],phonons)
    plot(assets/'phonon-chain.svg','Monatomic harmonic chain','qa / pi','omega (10^12 rad/s)', [('exact chain','#1565c0','',phonons),('long-wave','#c45100','6 4',[(x,math.sqrt(spring/mass_ch)*math.pi*x/1e12) for x,_ in phonons])],0,1,0,70)
    ac=card['acoustic'];mass=ac['mass_ratio']*M0;deformation=ac['deformation_eV']*Q;rho=ac['rho_kg_per_m3'];sound=ac['sound_m_per_s']
    integ=card['energy_integral'];first,second,rh_num=moments(integ['maximum_over_kBT'],integ['intervals'])
    transport=[]
    for temp in ac['temperature_K']:
        rate=acoustic_rate(KB*temp,temp,mass,deformation,rho,sound);tau=1/rate
        mu=Q/mass*tau/math.gamma(2.5)  # Gamma(2)/Gamma(5/2)
        k=math.sqrt(2*mass*KB*temp)/HBAR
        transport.append({'T_K':temp,'rate_at_kBT_per_s':rate,'tau_at_kBT_s':tau,'mobility_m2_per_Vs':mu,'Hall_factor':3*math.pi/8,'RH_m3_per_C':-3*math.pi/8/(Q*ac['density_per_m3']),'phonon_energy_at_2k_over_kBT':HBAR*sound*2*k/(KB*temp),'2k_over_cutoff':2*k/ac['cutoff_q_per_m']})
    plot(assets/'mobility.svg','LA deformation-potential model; density fixed','T (K)','mobility (m^2 / V s)', [('drift mobility','#1565c0','',[(r['T_K'],r['mobility_m2_per_Vs']) for r in transport]),('Hall mobility','#c45100','6 4',[(r['T_K'],r['Hall_factor']*r['mobility_m2_per_Vs']) for r in transport])],min(ac['temperature_K']),max(ac['temperature_K']),0,max(r['Hall_factor']*r['mobility_m2_per_Vs'] for r in transport)*1.1)
    result={'identity':card['identity'],'hexagonal':{'primitive_nm':primitive,'reciprocal_per_nm':b,'dual_products':dual,'cell_volume_nm3':volume,'periodic_cell_count':cells,'spatial_states_per_band':cells,'states_with_two_spins':2*cells,'k_cell_volume_per_nm3':(2*math.pi)**3/(volume*cells)},'cubic':{'bandwidth_eV':12*band['t_eV'],'mass_ratio':HBAR**2/(2*t*a_m*a_m*M0),'maximum_vx_m_per_s':2*t*a_m/HBAR,'ring16_bloch_orthogonality_max_error':max_orth},'chain':{'sound_m_per_s':a_ch*math.sqrt(spring/mass_ch),'edge_omega_rad_per_s':2*math.sqrt(spring/mass_ch),'zero_mode_omega':chain_omega(0,a_ch,spring,mass_ch),'modes':chain['cells']},'acoustic':transport,'quadrature':{'first_tau_ratio':first,'second_tau_ratio_squared':second,'Hall_factor':rh_num,'analytic_Hall_factor':3*math.pi/8,'u_max':integ['maximum_over_kBT'],'intervals':integ['intervals']},'impurity_angular':[{'qs_over_k':s,'tau_tr_over_tau_s':impurity_angular_ratio(s)} for s in card['screened_impurity']['screening_over_k']]}
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,default=Path(__file__).with_name('inputs.json'));parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();card=json.loads(args.inputs.read_text(encoding='utf-8'));result=build(card,args.out)
    print(json.dumps({'status':'computed_teaching_models','output':str(args.out),'cards':4,'periodic_cells':result['hexagonal']['periodic_cell_count']},ensure_ascii=False))
