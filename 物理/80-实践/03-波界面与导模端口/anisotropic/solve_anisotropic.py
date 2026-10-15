#!/usr/bin/env python3
"""Two isolated branches of a nondispersive uniaxial slab; see README contract.

Peak phasors exp(+i omega t - i beta z), axis (sin(theta),cos(theta),0).
The real state is g=(Ey,-i Ez,Z0 Hy,-i Z0 Hz), all entries in V/m.
Only NumPy and SciPy are external dependencies. No installation/network access.
"""
from __future__ import annotations
import argparse
import csv
import html
import io
import json
import math
from pathlib import Path
import platform
import sys
import numpy as np
import scipy
from scipy.linalg import expm, svd
from scipy.optimize import brentq

C0 = 299792458.0
MU0 = 4e-7 * math.pi
EPS0 = 1 / (MU0 * C0**2)
Z0 = MU0 * C0
OUTPUT_NAMES = ('branch-1-fields.csv','branch-2-fields.csv','angle-scan.csv','root-scan.csv',
                'axis-branches.svg','mixed-fields.svg','values.json')
KEYS = {'n_ordinary','n_extraordinary','n_clad','wavelength0_m','reference_V',
        'axis_angle_deg','periodic_width_m','control_length_m','power_W'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(p):
    require(isinstance(p, dict) and set(p) == KEYS, 'Input must contain exactly the documented keys')
    for key, val in p.items():
        require(type(val) in (int, float) and abs(val) < 1e100 and math.isfinite(val), f'{key} must be a finite real number')
    no, ne, ns = p['n_ordinary'], p['n_extraordinary'], p['n_clad']
    require(1 < ns < no <= ne <= 1.6 and ne-no <= .04 + 1e-14, 'Require 1 < ns < no <= ne <= 1.6 and ne-no <= .04')
    require(4e-7 <= p['wavelength0_m'] <= 2e-6, 'Wavelength outside finite teaching range')
    require(.75 <= p['reference_V'] <= 1.2, 'Require .75 <= reference_V <= 1.2')
    vmax = p['reference_V'] * math.sqrt((ne*ne-ns*ns)/(no*no-ns*ns))
    require(vmax < 1.5, 'Maximum-index reference V must be below 1.5; higher branches not covered')
    require(abs(p['axis_angle_deg']) <= 60, 'Require -60 <= axis angle <= 60 degrees')
    require(1e-6 <= p['periodic_width_m'] <= .1, 'Periodic width outside teaching range')
    require(1e-6 <= p['control_length_m'] <= .1, 'Control length outside teaching range')
    require(1e-12 <= p['power_W'] <= 1, 'Power outside teaching range')
    return p


def tensor(p, theta):
    t = math.radians(theta)
    a = np.array([math.sin(t), math.cos(t), 0.0])
    return p['n_ordinary']**2*np.eye(3) + (p['n_extraordinary']**2-p['n_ordinary']**2)*np.outer(a,a)


def matrix(b, eps):
    xx, xy, yy, zz = eps[0,0], eps[0,1], eps[1,1], eps[2,2]
    return np.array([[0,0,0,1],
                     [b*xy/xx,0,1-b*b/xx,0],
                     [0,-zz,0,0],
                     [b*b-yy+xy*xy/xx,0,-b*xy/xx,0]], dtype=float)


def bases(b, ns):
    require(b > ns, 'Cladding must be strictly evanescent')
    gamma = math.sqrt(b*b-ns*ns)
    left = np.array([[1,0],[0,-gamma/(ns*ns)],[0,1],[gamma,0]],float)
    right = np.array([[1,0],[0,gamma/(ns*ns)],[0,1],[-gamma,0]],float)
    return left, right, gamma


class Slab:
    def __init__(self,p,theta):
        self.p=p
        self.theta=theta
        self.eps=tensor(p,theta)
        self.k0=2*math.pi/p['wavelength0_m']
        self.d=p['reference_V']/(self.k0*math.sqrt(p['n_ordinary']**2-p['n_clad']**2))
        self.ns=p['n_clad']

    def matching(self,b):
        left,right,_=bases(b,self.ns)
        T=expm(matrix(b,self.eps)*2*self.k0*self.d)
        raw=np.column_stack((T@left,-right))
        norms=np.linalg.norm(raw,axis=0)
        return raw/norms, norms, T

    def determinant(self,b):
        return float(np.linalg.det(self.matching(b)[0]))

    def roots(self):
        # A finite real grid is a diagnostic for this bounded two-branch card,
        # not a completeness theorem for general anisotropic waveguides.
        lo=self.ns+1e-8
        hi=self.p['n_extraordinary']-1e-8
        grid=np.linspace(lo,hi,1001)
        vals=[self.determinant(float(b)) for b in grid]
        roots=[]
        for i in range(len(grid)-1):
            if vals[i]*vals[i+1] < 0:
                a,b=float(grid[i]),float(grid[i+1])
                r=brentq(self.determinant,a,b,xtol=5e-15,rtol=9e-16)
                roots.append((r,[a,b]))
        require(len(roots)==2, f'Expected exactly two isolated sign-changing roots; found {len(roots)}. Refuse to label modes')
        require(roots[1][0]-roots[0][0] > 2e-5, 'Branches too close for this finite scan and tracking contract')
        return [Mode(self,*r) for r in roots],grid,vals


class Mode:
    def __init__(self,slab,b,bracket):
        self.slab,self.b,self.bracket=slab,b,bracket
        self.C=matrix(b,slab.eps)
        M,norms,T=slab.matching(b)
        _,singular,vh=svd(M)
        require(singular[-1]/singular[0] < 2e-10, 'Matching null residual too large')
        require(singular[-2]/singular[0] > 1e-5, 'Null space is not isolated')
        require(np.linalg.cond(T) < 1e4, 'Transfer matrix ill conditioned; use a stable method outside this card')
        coeff=vh[-1,:]/norms
        L,R,self.gamma=bases(b,slab.ns)
        self.gleft=L@coeff[:2]
        self.gright=R@coeff[2:]
        mid=expm(self.C*slab.k0*slab.d)@self.gleft
        sign=1 if mid[np.argmax(abs(mid))]>=0 else -1
        self.gleft*=sign
        self.gright*=sign
        self.singular=singular
        self.transfer_condition=float(np.linalg.cond(T))
        self.residual=float(np.linalg.norm(T@self.gleft-self.gright)/max(np.linalg.norm(self.gleft),np.linalg.norm(self.gright)))
        self.scale=1.
        self.label=''
        self.overlap=1.
        self.quad(96)
        require(self.Praw>0 and self.UEraw>0 and self.UHraw>0,'Positive power and energy required')
        self.scale=math.sqrt(slab.p['power_W']/(slab.p['periodic_width_m']*self.Praw))

    def state(self,x,region=None):
        s=self.slab
        if region is None:
            region='left' if x < -s.d else 'right' if x > s.d else 'core'
        if region=='left':
            g=self.gleft*np.exp(self.gamma*s.k0*(x+s.d))
            eps=s.ns*s.ns*np.eye(3)
        elif region=='right':
            g=self.gright*np.exp(-self.gamma*s.k0*(x-s.d))
            eps=s.ns*s.ns*np.eye(3)
        else:
            g=expm(self.C*s.k0*(x+s.d))@self.gleft
            eps=s.eps
        ex=(self.b*g[2]-eps[0,1]*g[0])/eps[0,0]
        E=np.array([ex,g[0],1j*g[1]],complex)*self.scale
        h=np.array([-self.b*g[0],g[2],1j*g[3]],complex)*self.scale
        return E,h,eps,g*self.scale

    def densities(self,x,region=None):
        E,h,eps,_=self.state(x,region)
        S=np.real(np.cross(E,h.conj()))/(2*Z0)
        ue=EPS0*np.vdot(E,eps@E).real/4
        uh=EPS0*np.vdot(h,h).real/4
        # The last two entries are field-square measures, not energy/power shares.
        return np.array([S[2],ue,uh,abs(E[1])**2,np.vdot(E,E).real,S[0]])

    def integrate(self,n):
        nodes,weights=np.polynomial.legendre.leggauss(n)
        core=sum(w*self.densities(float(t*self.slab.d),'core') for t,w in zip(nodes,weights))*self.slab.d
        kappa=self.gamma*self.slab.k0
        tails=(self.densities(-self.slab.d,'left')+self.densities(self.slab.d,'right'))/(2*kappa)
        return core,tails

    def quad(self,n):
        core,tail=self.integrate(n)
        self.Praw,self.UEraw,self.UHraw=(core+tail)[:3]

    def fingerprint(self):
        # Common x-grid in units of d, all six E and Z0 H components.
        fs=[]
        for x in np.linspace(-4*self.slab.d,4*self.slab.d,101):
            E,h,_,_=self.state(float(x))
            fs.extend(E);fs.extend(h)
        a=np.array(fs)
        return a/np.linalg.norm(a)

    def summary(self):
        core,tail=self.integrate(96)
        finecore,finetail=self.integrate(128)
        total=core+tail
        s=self.slab;p=s.p
        P=p['periodic_width_m']*total[0]
        UE=p['periodic_width_m']*p['control_length_m']*total[1]
        UH=p['periodic_width_m']*p['control_length_m']*total[2]
        return dict(branch=self.label,theta_deg=s.theta,n_eff=self.b,beta_per_m=self.b*s.k0,
                    kappa_per_m=self.gamma*s.k0,root_bracket=self.bracket,
                    det_residual=abs(s.determinant(self.b)),matching_relative_residual=self.residual,
                    singular_values=self.singular.tolist(),transfer_condition=self.transfer_condition,
                    previous_field_overlap=self.overlap,power_W=P,electric_energy_J=UE,
                    magnetic_energy_J=UH,total_energy_J=UE+UH,energy_velocity_m_per_s=total[0]/(total[1]+total[2]),
                    electric_magnetic_relative_difference=abs(UE-UH)/(UE+UH),
                    cladding_power_fraction=tail[0]/total[0],
                    Ey_field_square_fraction=total[3]/total[4],
                    quadrature_relative_change=float(np.max(abs((finecore+finetail-total)[:3]/total[:3]))),
                    transverse_power_density_max_W_per_m2=float(max(abs(self.densities(float(x))[5]) for x in np.linspace(-4*s.d,4*s.d,101))))


def track(p):
    steps=max(1,math.ceil(abs(p['axis_angle_deg'])/5))
    angles=np.array([0.0]) if p['axis_angle_deg']==0 else np.linspace(0,p['axis_angle_deg'],steps+1)
    rows=[]; previous=None
    for angle in angles:
        modes,grid,vals=Slab(p,float(angle)).roots()
        if previous is None:
            # At a=(0,1,0), pure TE has Ey and pure TM has Hy.
            modes.sort(key=lambda m: m.summary()['Ey_field_square_fraction'],reverse=True)
            modes[0].label='TE0-continuation';modes[1].label='TM0-continuation'
        else:
            overlaps=np.array([[abs(np.vdot(old.fingerprint(),new.fingerprint())) for new in modes] for old in previous])
            if overlaps[0,1]+overlaps[1,0] > overlaps[0,0]+overlaps[1,1]:
                modes.reverse();overlaps=overlaps[:,::-1]
            for i,mode in enumerate(modes):
                require(overlaps[i,i] > .85,'Field overlap below .85; reduce step or treat a subspace, do not relabel')
                mode.label=previous[i].label;mode.overlap=float(overlaps[i,i])
        rows.extend(m.summary() for m in modes)
        previous=modes
    return previous,rows,grid,vals


def csv_text(rows,keys):
    buf=io.StringIO(newline='')
    w=csv.DictWriter(buf,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)
    return buf.getvalue()


def fields(mode):
    s=mode.slab;tail=6/(mode.gamma*s.k0)
    rows=[]
    for region,xx in [('left',np.linspace(-s.d-tail,-s.d,81)),('core',np.linspace(-s.d,s.d,201)),('right',np.linspace(s.d,s.d+tail,81))]:
        for x in xx:
            E,h,eps,g=mode.state(float(x),region)
            dens=mode.densities(float(x),region)
            row={'region':region,'x_m':float(x)}
            for name,v in zip(('Ex','Ey','Ez','Hx','Hy','Hz'),[*E,*(h/Z0)]):
                row[name+'_real']=float(v.real);row[name+'_imag']=float(v.imag)
            row.update(Sz_W_per_m2=float(dens[0]),uE_J_per_m3=float(dens[1]),uH_J_per_m3=float(dens[2]),
                       Dx_C_per_m2=float(EPS0*(eps@E)[0].real),Bx_T=float(MU0*h[0].real/Z0))
            rows.append(row)
    return rows


def svg_plot(title,panels,foot):
    # Plain SVG uses the same numerical arrays written to CSV/JSON.
    W=940;H=80+260*len(panels)+60
    a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<rect width="100%" height="100%" fill="white"/>',
       '<style>text{font-family:Arial,sans-serif;font-size:14px;fill:#182a3a}.title{font-size:20px;font-weight:bold}</style>',
       f'<text x="32" y="30" class="title">{html.escape(title)}</text>']
    palette=['#1365ab','#d04d24','#298a61','#9b56a3']
    for i,panel in enumerate(panels):
        x0=92;y0=78+i*260;pw=805;ph=166
        series=panel['series']
        xs=[float(x) for ss in series for x,y in ss[1]]
        ys=[float(y) for ss in series for x,y in ss[1]]
        xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        if xmin==xmax:
            xmin-=1; xmax+=1  # A single sampled angle needs readable ticks, not duplicate labels.
        dy=max(ymax-ymin,1e-12);ymin-=.06*dy;ymax+=.06*dy
        def point(x,y):return (x0+(x-xmin)/(xmax-xmin or 1)*pw,y0+ph-(y-ymin)/(ymax-ymin)*ph)
        a.append(f'<text x="92" y="{y0-14}">{html.escape(panel["ylabel"])}</text>')
        for k in range(5):
            y=ymin+(ymax-ymin)*k/4;py=point(xmin,y)[1]
            x=xmin+(xmax-xmin)*k/4;px=point(x,ymin)[0]
            a.append(f'<path d="M{x0},{py:.3f}h{pw}" stroke="#e0e5e9"/><text x="{x0-10}" y="{py+5:.3f}" text-anchor="end">{y:.4g}</text>')
            a.append(f'<text x="{px:.3f}" y="{y0+ph+23}" text-anchor="middle">{x:.4g}</text>')
        for k,(name,xy) in enumerate(series):
            pts=' '.join(f'{px:.3f},{py:.3f}' for px,py in [point(x,y) for x,y in xy])
            a.append(f'<polyline points="{pts}" fill="none" stroke="{palette[k%4]}" stroke-width="2"/>')
            if len(xy)==1:
                px,py=point(*xy[0])
                a.append(f'<circle cx="{px:.3f}" cy="{py:.3f}" r="4" fill="{palette[k%4]}"/>')
            a.append(f'<text x="{x0+k*220}" y="{y0+ph+62}" style="fill:{palette[k%4]}">{html.escape(name)}</text>')
        a.append(f'<text x="495" y="{y0+ph+44}" text-anchor="middle">{html.escape(panel["xlabel"])}</text>')
    a.append(f'<text x="32" y="{H-18}">{html.escape(foot)}</text></svg>')
    return '\n'.join(a)+'\n'


def solve(p):
    modes,scan,grid,det=track(p)
    isotropic=dict(p,n_extraordinary=p['n_ordinary'],axis_angle_deg=0.)
    iso_modes,_,_,_=track(isotropic)
    for m in iso_modes: m.label='isotropic-'+m.label.split('-')[0]
    # Mirror-axis card is the exercise: eigenvalues are identical; mixed signs reverse.
    mirror=dict(p,axis_angle_deg=-p['axis_angle_deg'])
    mirror_modes,mirror_scan,_,_=track(mirror)
    summaries=[m.summary() for m in modes]
    data=dict(model='lossless nondispersive positive-definite uniaxial symmetric slab',input=p,
              constants=dict(c0_m_per_s=C0,mu0_H_per_m=MU0,epsilon0_F_per_m=EPS0,Z0_ohm=Z0),
              half_thickness_m=modes[0].slab.d,epsilon_r_core=modes[0].slab.eps.tolist(),
              modes=summaries,principal_axis_modes=scan[:2],isotropic_modes=[m.summary() for m in iso_modes],
              mirror_axis_modes=[m.summary() for m in mirror_modes],angle_scan=scan,
              numerical_contract=dict(root_grid_points=1001,core_Gauss_nodes=96,comparison_Gauss_nodes=128,
                                      root_min_gap=2e-5,max_angle_step_deg=5,min_field_overlap=.85,
                                      tails='analytic to infinity; field plot only extends six amplitude decay lengths'),
              provenance=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__))
    outputs={}
    all_fields=[fields(m) for m in modes]
    for i,rows in enumerate(all_fields):
        outputs[f'branch-{i+1}-fields.csv']=csv_text(rows,list(rows[0]))
    keys=['theta_deg','branch','n_eff','previous_field_overlap','Ey_field_square_fraction','cladding_power_fraction','power_W','total_energy_J','energy_velocity_m_per_s','matching_relative_residual','transfer_condition']
    outputs['angle-scan.csv']=csv_text([{k:r[k] for k in keys} for r in scan],keys)
    root_rows=[{'n_eff':float(b),'scaled_matching_determinant':float(v)} for b,v in zip(grid,det)]
    outputs['root-scan.csv']=csv_text(root_rows,list(root_rows[0]))
    title=f'Uniaxial slab: theta={p["axis_angle_deg"]:g} deg, {p["wavelength0_m"]*1e9:g} nm'
    scanpanels=[]
    for key,ylabel in [('n_eff','Effective index'),('Ey_field_square_fraction','Integral |Ey|^2 / integral |E|^2 (not power share)')]:
        series=[(m.label,[(r['theta_deg'],r[key]) for r in scan if r['branch']==m.label]) for m in modes]
        scanpanels.append(dict(xlabel='Axis angle from +y toward +x (deg)',ylabel=ylabel,series=series))
    outputs['axis-branches.svg']=svg_plot(title,scanpanels,'Labels follow field overlap from theta=0; an arbitrary sort by effective index is not used.')
    panels=[]
    for m,rows in zip(modes,all_fields):
        series=[]
        for key,label in [('Ex_real','Re Ex'),('Ey_real','Re Ey'),('Ez_imag','Im Ez')]:
            series.append((label,[(r['x_m']*1e6,r[key]) for r in rows]))
        panels.append(dict(xlabel='x (um); two values at each interface show the two sides',ylabel=f'{m.label}: E peak (V/m), P={p["power_W"]*1e6:g} uW',series=series))
    outputs['mixed-fields.svg']=svg_plot(title,panels,'Ex may jump; Ey, Ez, Hy, Hz and normal Dx, Bx must match. Both infinite tails enter P and U.')
    outputs['values.json']=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    return outputs


def unique_object(pairs):
    obj={}
    for key,val in pairs:
        require(key not in obj, f'Duplicate JSON key: {key}')
        obj[key]=val
    return obj


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).with_name('inputs.json'))
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        require(not args.output_dir.is_symlink(),'Refuse symlink output directory')
        for name in OUTPUT_NAMES:
            target=args.output_dir/name
            require(not target.exists() and not target.is_symlink(),f'Refuse existing output: {name}; choose a new directory')
        p=validate(json.loads(args.input.read_text(encoding='utf-8'),object_pairs_hook=unique_object))
        outputs=solve(p)  # All validation and solving finish before any output is changed.
        out=args.output_dir
        sources={Path(__file__).resolve(),args.input.resolve()}
        for name in outputs:
            target=out/name
            require(not target.is_symlink(),'Refuse symlink output')
            require(target.resolve() not in sources,'Output must not overwrite an input/source')
        require(not out.is_symlink(),'Refuse symlink output directory')
        out.mkdir(parents=True,exist_ok=True)
        for name,content in outputs.items():
            (out/name).write_text(content,encoding='utf-8')
        print(outputs['values.json'],end='')
    except (ValueError, OSError, OverflowError, np.linalg.LinAlgError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
