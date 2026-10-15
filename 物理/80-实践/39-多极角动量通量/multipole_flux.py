#!/usr/bin/env python3
"""Finite uniform P/M ball: exterior stress versus distributed Lorentz sources.
Peak phasors exp(-i omega t), SI. NumPy, one process/thread, no network.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import csv
import json
import math
from pathlib import Path
import time
import numpy as np

C = 299792458.0
EPS = 8.8541878128e-12  # adopted numeric constant; no precision metrology claim


def sphere(n_mu, n_phi):
    mu, w = np.polynomial.legendre.leggauss(n_mu)
    phi = np.arange(n_phi) * (2 * np.pi / n_phi)
    mm, pp = np.meshgrid(mu, phi, indexing='ij')
    n = np.column_stack((np.sqrt(1-mm.ravel()**2)*np.cos(pp.ravel()),
                         np.sqrt(1-mm.ravel()**2)*np.sin(pp.ravel()), mm.ravel()))
    return n, np.repeat(w, n_phi) * (2*np.pi/n_phi)


def shape(a):
    return 3 * (np.sin(a)-a*np.cos(a)) / a**3


def fields(x, n, p, q, a, inside=False, radiation=False):
    """Return E/E0, cB/E0. E0=p0 k^3/(4 pi epsilon0); x=kr."""
    np_ = (n @ p)[:, None]
    nq = (n @ q)[:, None]
    if radiation:
        e = shape(a)*np.exp(1j*x)/x * (p-n*np_-np.cross(n, q))
        return e, np.cross(n, e)
    if not inside:
        rad = np.exp(1j*x)*shape(a)/x
        near = np.exp(1j*x)*shape(a)*(1/x**3-1j/x**2)
        cross = np.exp(1j*x)*shape(a)*(1/x+1j/x**2)
        e = rad*(p-n*np_)+near*(3*n*np_-p)-cross*np.cross(n, q)
        d = cross*np.cross(n, p)+rad*(q-n*nq)+near*(3*n*nq-q)
        return e, d
    # j0 and derivatives via convergent power series, x<=ka<=1.
    j0 = sum((-1)**l*x**(2*l)/math.factorial(2*l+1) for l in range(12))
    j1 = sum((-1)**l*(2*l)*x**(2*l-1)/math.factorial(2*l+1) for l in range(1,12))
    j2 = sum((-1)**l*(2*l)*(2*l-1)*x**(2*l-2)/math.factorial(2*l+1) for l in range(1,12))
    dens = 3/a**3
    aa = np.exp(1j*a)*(1-1j*a)
    h, hp, hpp = dens*(aa*j0-1), dens*aa*j1, dens*aa*j2
    def hessian(v, nv):
        return hp/x*v+(hpp-hp/x)*n*nv
    e = h*p+hessian(p,np_)+1j*hp*np.cross(n,q)
    d = -1j*hp*np.cross(n,p)+(h+dens)*q+hessian(q,nq)
    return e, d


def surface_flux(x, n, w, p, q, a, shift, radiation=False):
    e,d=fields(x,n,p,q,a,radiation=radiation)
    # sigma.n / (epsilon0 E0^2/2), with the full trace term.
    traction=np.real(e*np.conj(np.sum(e*n,axis=1))[:,None]
                     +d*np.conj(np.sum(d*n,axis=1))[:,None])
    traction-=0.5*(np.sum(abs(e)**2+abs(d)**2,axis=1))[:,None]*n
    dp=-x*x*traction
    power=x*x*np.real(np.sum(np.cross(e,np.conj(d))*n,axis=1))
    dj=np.cross(x*n,dp)
    shifted=np.cross(x*n-shift,dp)
    return np.array([np.sum(w*power),*(w@dp),*(w@dj),*(w@shifted)])


def source_exchange(n,w,p,q,a,nr,shift):
    """Independently integrate physical volume and surface charge/current forces.
    Returns outward-equivalent rates: negative of the field's work/force/torque
    on prescribed matter. Never filled from the surface-flux remainder.
    """
    nodes, rw=np.polynomial.legendre.leggauss(nr)
    xs=(nodes+1)*a/2
    rw=rw*a/2
    dens=3/a**3
    power=0.; force=np.zeros(3); torque=np.zeros(3)
    j=-1j*dens*p
    for x, weight in zip(xs,rw):
        e,d=fields(x,n,p,q,a,inside=True)
        power+=weight*x*x*np.sum(w*np.real(np.sum(j*np.conj(e),axis=1)))
        f=np.real(np.cross(j,np.conj(d)))
        force+=weight*x*x*(w@f)
        torque+=weight*x*x*(w@np.cross(x*n,f))
    ei,di=fields(a,n,p,q,a,inside=True)
    eo,do=fields(a,n,p,q,a)
    e,d=(ei+eo)/2,(di+do)/2
    rho=dens*(n@p)
    sheet=dens*np.cross(q,n)
    power+=a*a*np.sum(w*np.real(np.sum(sheet*np.conj(e),axis=1)))
    f=np.real(rho[:,None]*np.conj(e)+np.cross(sheet,np.conj(d)))
    force+=a*a*(w@f)
    torque+=a*a*(w@np.cross(a*n,f))
    return -np.array([power,*force,*torque,*(torque-np.cross(shift,force))])


def oracle(p,q,a,shift):
    fac=8*np.pi/3*shape(a)**2
    power=fac*np.real(np.vdot(p,p)+np.vdot(q,q))
    force=fac*np.real(np.cross(p,np.conj(q)))
    torque=fac*np.imag(np.cross(np.conj(p),p)+np.cross(np.conj(q),q))
    return np.array([power,*force,*torque,*(torque-np.cross(shift,force))])


def svg_plot(path,title,xs,series,xlabel,ylabel,logx=False):
    width,height=840,430
    left,top,right,bottom=82,58,815,337
    xx=np.log10(xs) if logx else np.array(xs)
    ymin=min(0.,min(min(y) for _,y,_ in series)); ymax=max(max(y) for _,y,_ in series)
    gap=max((ymax-ymin)*.08,1e-8); ymin-=gap; ymax+=gap
    def px(x):return left+(x-xx[0])/(xx[-1]-xx[0])*(right-left)
    def py(y):return bottom-(y-ymin)/(ymax-ymin)*(bottom-top)
    bits=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>',
          f'<g font-family="sans-serif" font-size="14" fill="#152638"><text x="82" y="27" font-size="18">{title}</text>']
    for y in np.linspace(ymin,ymax,5):
        bits += [f'<path d="M {left} {py(y):.3f} H {right}" stroke="#dce3e9"/>',f'<text x="74" y="{py(y)+5:.3f}" text-anchor="end">{y:.3g}</text>']
    for i in np.linspace(0,len(xs)-1,6).astype(int):
        bits += [f'<text x="{px(xx[i]):.3f}" y="359" text-anchor="middle">{xs[i]:.3g}</text>']
    for index,(label,ys,color) in enumerate(series):
        points=' '.join(f'{px(x):.3f},{py(y):.3f}' for x,y in zip(xx,ys))
        bits += [f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>',f'<text x="{82+index*250}" y="409" fill="{color}">{label}</text>']
    bits += [f'<text x="448" y="384" text-anchor="middle">{xlabel}</text>',f'<text transform="translate(20,205) rotate(-90)" text-anchor="middle">{ylabel}</text></g></svg>']
    path.write_text('\n'.join(bits)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();cfg=json.loads(args.inputs.read_text())
    for key in ('frequency_Hz','p0_C_m','ka','ellipticity','magnetic_ratio','magnetic_phase_rad'):
        if not isinstance(cfg[key],(int,float)) or not math.isfinite(cfg[key]):raise ValueError(key+' must be finite')
    if not 0.05<=cfg['ka']<=1 or cfg['frequency_Hz']<=0 or cfg['p0_C_m']<=0:raise ValueError('positive frequency/p0 and 0.05<=ka<=1 required')
    if abs(cfg['ellipticity'])>2 or abs(cfg['magnetic_ratio'])>2:raise ValueError('amplitude ratios must have magnitude <=2')
    for key,lo,hi in [('n_mu',8,64),('n_phi',16,128),('n_r',8,64)]:
        if type(cfg[key]) is not int or not lo<=cfg[key]<=hi:raise ValueError(key+' outside bounded grid')
    shift=np.array(cfg['origin_shift_dimensionless'],dtype=float)
    if shift.shape!=(3,) or not np.isfinite(shift).all() or np.max(abs(shift))>10:raise ValueError('finite 3-vector shift, magnitude components <=10')
    radii=np.array(cfg['kr'],dtype=float)
    if radii.ndim!=1 or not 2<=len(radii)<=32 or not np.isfinite(radii).all() or np.any(radii<=cfg['ka']) or np.any(radii>1000) or np.any(np.diff(radii)<=0):raise ValueError('2..32 increasing ka<kr<=1000 required')
    # Reject unrepresentable SI scales before creating any output directory.
    try:
        k=2*math.pi*cfg['frequency_Hz']/C
        e0=cfg['p0_C_m']*k**3/(4*math.pi*EPS)
        ps=EPS*C*e0**2/(2*k**2);fs=ps/C;js=fs/k
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError('SI scales overflow or underflow') from exc
    if not all(math.isfinite(v) and v>0 for v in (k,e0,ps,fs,js)):
        raise ValueError('SI scales must be finite and positive')
    scales=np.array([ps,*([fs]*3),*([js]*6)])
    args.output.mkdir(parents=True,exist_ok=False)
    t0=time.perf_counter();a=cfg['ka'];p=np.array([1,1j*cfg['ellipticity'],0]);q=np.array([0,cfg['magnetic_ratio']*np.exp(1j*cfg['magnetic_phase_rad']),0])
    expected=oracle(p,q,a,shift)
    columns=['power_W','Fx_N','Fy_N','Fz_N','Jx_N_m','Jy_N_m','Jz_N_m','shift_Jx_N_m','shift_Jy_N_m','shift_Jz_N_m']
    rows=[]; errors=[]; sources=[]
    for refinement in (1,2):
        n,w=sphere(cfg['n_mu']*refinement,cfg['n_phi']*refinement)
        src=source_exchange(n,w,p,q,a,cfg['n_r']*refinement,shift)
        err=float(np.max(abs(src-expected))/expected[0]); errors.append(err)
        sources.append({'refinement':refinement,'outward_equivalent_SI':dict(zip(columns,(src*scales).tolist())),'scaled_max_error':err})
        for x in radii:
            full=surface_flux(x,n,w,p,q,a,shift)
            rad=surface_flux(x,n,w,p,q,a,shift,radiation=True)
            errors.append(float(np.max(abs(full-expected))/expected[0]))
            rows.append([refinement,x,*(full*scales),rad[6]*js])
    with (args.output/'surface.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['refinement','kr',*columns,'radiation_only_Jz_N_m']);writer.writerows(rows)
    # Far angular cut; data drive both CSV and figure.
    theta=np.linspace(0,np.pi,181);n=np.column_stack((np.sin(theta),np.zeros_like(theta),np.cos(theta)))
    b=p-(n@p)[:,None]*n-np.cross(n,q)
    epart=p-(n@p)[:,None]*n;mpart=-np.cross(n,q)
    total=ps*shape(a)**2*np.sum(abs(b)**2,axis=1)
    incoherent=ps*shape(a)**2*np.sum(abs(epart)**2+abs(mpart)**2,axis=1)
    with (args.output/'angular.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['theta_deg','U_W_per_sr','without_interference_W_per_sr']);writer.writerows(zip(np.degrees(theta),total,incoherent))
    svg_plot(args.output/'angular.svg','Far angular power: xz plane, phi=0',np.degrees(theta),[('Coherent total',total*1e6,'#1769aa'),('Omit cross term',incoherent*1e6,'#ba4938')],'theta (degrees)','U (microW/sr)')
    nr,wr=sphere(cfg['n_mu'],cfg['n_phi']);scan=np.geomspace(radii[0],radii[-1],51)
    exact=[];wrong=[];local=[]
    probe=np.array([[np.sqrt(.5),0,np.sqrt(.5)]])
    for x in scan:
        exact.append(surface_flux(x,nr,wr,p,q,a,shift)[6]/expected[0])
        wrong.append(surface_flux(x,nr,wr,p,q,a,shift,radiation=True)[6]/expected[0])
        ee,dd=fields(x,probe,p,q,a);er,dr=fields(x,probe,p,q,a,radiation=True)
        local.append(float(np.linalg.norm(ee-er)/(abs(shape(a))*np.sqrt(np.vdot(p,p).real+np.vdot(q,q).real)/x)))
    with (args.output/'radius.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['kr','omega_Jz_over_P','radiation_only_omega_Jz_over_P','local_E_error_over_radiation_scale']);writer.writerows(zip(scan,exact,wrong,local))
    svg_plot(args.output/'radius.svg','Angular momentum survives at every exterior radius',scan,[('Full stress',exact,'#1769aa'),('Radiation only',wrong,'#ba4938')],'kr (dimensionless, log axis)','omega Jz / P (dimensionless)',logx=True)
    result={'input':cfg,'constants':{'c_m_s':C,'epsilon0_F_m':EPS},'source_radius_m':a/k,'shape_factor':float(shape(a)),'analytic_SI':dict(zip(columns,(expected*scales).tolist())),'source_integrals':sources,'max_scaled_error':max(errors),'normalization':'power by ps; force by ps/c; torque by ps/(c k); all errors divided by dimensionless analytic power','pass':max(errors)<2e-7,'environment':{'numpy':np.__version__,'threads':1},'elapsed_s':time.perf_counter()-t0}
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'pass':result['pass'],'max_scaled_error':max(errors),'elapsed_s':result['elapsed_s']}))
    if not result['pass']:raise SystemExit(1)

if __name__=='__main__':main()
