"""Finite scalar teaching models; SI units. Import performs no I/O.
Not BSIM, not PDK data. Real DC inputs are validated before conversion.
"""
import argparse
import cmath
import json
import math
import numbers
from pathlib import Path


def real(name, x, *, positive=False, nonnegative=False):
    if isinstance(x, (bool, complex)) or not isinstance(x, numbers.Real):
        raise ValueError(name + ' must be a finite real scalar')
    y = float(x)
    if not math.isfinite(y) or (positive and y <= 0) or (nonnegative and y < 0):
        raise ValueError(name + ' outside domain')
    return y


def checked(values):
    for name, value in values.items():
        if isinstance(value, numbers.Real) and not math.isfinite(value):
            raise ValueError(name + ' result outside finite teaching domain')
    return values


def threshold(vsb, vt0=.5, gamma=.4, phi2=.6):
    vsb=real('vsb',vsb,nonnegative=True)
    vt0=real('vt0',vt0); gamma=real('gamma',gamma,nonnegative=True)
    phi2=real('phi2',phi2,positive=True)
    result=vt0+gamma*(math.sqrt(phi2+vsb)-math.sqrt(phi2))
    if not math.isfinite(result):raise ValueError('threshold outside finite domain')
    return result


def mos(vgs,vds,vsb=0,*,k=.002,vt0=.5,gamma=.4,phi2=.6,lam=.02):
    vgs=real('vgs',vgs); vds=real('vds',vds,nonnegative=True)
    k=real('k',k,positive=True); lam=real('lam',lam,nonnegative=True)
    vt=threshold(vsb,vt0,gamma,phi2); ov=vgs-vt
    eta=gamma/(2*math.sqrt(phi2+vsb))
    if ov<=0: return dict(id=0.,gm=0.,gds=0.,gmb=0.,vt=vt,region='cutoff')
    if vds<ov:
        base=k*(ov*vds-vds*vds/2)
        gm=k*vds*(1+lam*vds)
        gds=k*(ov-vds)*(1+lam*vds)+base*lam
        region='triode'
    else:
        base=k*ov*ov/2
        gm=k*ov*(1+lam*vds)
        gds=base*lam; region='saturation'
    return checked(dict(id=base*(1+lam*vds),gm=gm,gds=gds,gmb=eta*gm,vt=vt,region=region))


def bias(vg,*,vdd=5.,rd=2000.,vsb=0.,max_iter=100,tol=1e-12,**model):
    vg=real('vg',vg); vdd=real('vdd',vdd,positive=True);rd=real('rd',rd,positive=True)
    tol=real('tol',tol,positive=True)
    if isinstance(max_iter,bool) or not isinstance(max_iter,int) or not 1<=max_iter<=10000:
        raise ValueError('max_iter must be integer 1..10000')
    lo,hi=0.,vdd
    def residual(vd): return (vdd-vd)/rd-mos(vg,vd,vsb,**model)['id']
    for it in range(1,max_iter+1):
        mid=(lo+hi)/2; r=residual(mid)
        if abs(r)<=tol:
            q=mos(vg,mid,vsb,**model);q.update(vd=mid,kcl=r,iterations=it);return q
        if mid==lo or mid==hi: raise RuntimeError('bias stagnated before current tolerance')
        if r>0:lo=mid
        else:hi=mid
    raise RuntimeError('bias iteration budget exhausted')


def ebers(vbe,vbc,*,is_=1e-15,beta_f=100.,beta_r=2.,ut=.026):
    vbe=real('vbe',vbe);vbc=real('vbc',vbc)
    is_=real('is_',is_,positive=True);bf=real('beta_f',beta_f,positive=True)
    br=real('beta_r',beta_r,positive=True);ut=real('ut',ut,positive=True)
    if max(vbe/ut,vbc/ut)>700:raise ValueError('exponential outside representable teaching domain')
    f=math.expm1(vbe/ut);r=math.expm1(vbc/ut)
    transport=is_*(f-r);ib=is_*(f/bf+r/br);ic=transport-is_*r/br
    return checked(dict(ic=ic,ib=ib,ie=-(ic+ib)))


def weak(vgs,vds,*,vt=.5,n=1.5,ut=.026,i0=1e-6,dibl=0.):
    vgs=real('vgs',vgs);vds=real('vds',vds,nonnegative=True);vt=real('vt',vt)
    n=real('n',n,positive=True);ut=real('ut',ut,positive=True)
    i0=real('i0',i0,positive=True);dibl=real('dibl',dibl,nonnegative=True)
    if n<1:raise ValueError('ordinary thermal MOS n must be >=1')
    effective=vt-dibl*vds
    if vgs>=effective:raise ValueError('weak model requires vgs < effective vt')
    a=(vgs-effective)/(n*ut)
    current=i0*math.exp(a)*(-math.expm1(-vds/ut))
    # direct derivative form remains valid at vds=0, unlike id/(exp(vds/ut)-1)
    go=current*dibl/(n*ut)+i0*math.exp(a-vds/ut)/ut
    return checked(dict(id=current,gm=current/(n*ut),gds=go,slope=n*ut*math.log(10)))


def moscap(psi,*,na=1e22,eps=11.7*8.8541878128e-12,cox=3.453e-3,vfb=-.2):
    psi=real('psi',psi,positive=True);na=real('na',na,positive=True)
    eps=real('eps',eps,positive=True);cox=real('cox',cox,positive=True);vfb=real('vfb',vfb)
    q=1.602176634e-19;w=math.sqrt(2*eps*psi/(q*na));qd=-q*na*w
    cd=eps/w;c=cox*cd/(cox+cd)
    return checked(dict(w=w,qd=qd,vgb=vfb+psi-qd/cox,c=c,cd=cd))


def source_gain(*,gm=.002,gmb=.0005163977794943223,go=.00002,rd=2000.,rl=10000.,rsource=100.):
    """Loaded D/S network with B at AC ground; finite real DC gain."""
    gm=real('gm',gm,nonnegative=True);gmb=real('gmb',gmb,nonnegative=True);go=real('go',go,nonnegative=True)
    rd=real('rd',rd,positive=True);rl=real('rl',rl,positive=True);rsource=real('rsource',rsource,nonnegative=True)
    gd=1/rd+1/rl
    if not math.isfinite(gd):raise ValueError('load conductance outside finite domain')
    scale=max(gd,gm,gmb,go)
    # Divide conductances by a common scale before their product with RS.
    # gm=1e200, RS=1e200 remains representable without forming gm*RS.
    numerator=gm/scale
    feedback=gd*rsource
    denominator=gd/scale+go/scale+feedback*(gm/scale+gmb/scale+go/scale)
    if not math.isfinite(denominator) or denominator<=0:
        raise ValueError('source gain denominator outside finite domain')
    result=-numerator/denominator
    if not math.isfinite(result) or (gm>0 and result==0):
        raise ValueError('source gain outside finite representable domain')
    return result


def ac_gain(f,*,gm=.002,go=0.,rs=10000.,rd=2000.,rl=10000.,cgs=20e-12,cgd=2e-12,cl=10e-12):
    """Gate and drain nodal solve; S=B=AC ground. Complex output is intentional."""
    f=real('f',f,nonnegative=True);gm=real('gm',gm,nonnegative=True);go=real('go',go,nonnegative=True)
    rs=real('rs',rs,positive=True);rd=real('rd',rd,positive=True);rl=real('rl',rl,positive=True)
    cgs=real('cgs',cgs,nonnegative=True);cgd=real('cgd',cgd,nonnegative=True);cl=real('cl',cl,nonnegative=True)
    s=complex(0,2*math.pi*f)
    a=1/rs+s*(cgs+cgd);b=-s*cgd;c=gm-s*cgd;d=1/rd+1/rl+go+s*(cl+cgd)
    determinant=a*d-b*c
    if determinant==0:raise RuntimeError('singular AC nodal matrix')
    result=-c/rs/determinant
    if not math.isfinite(result.real) or not math.isfinite(result.imag):
        raise ValueError('AC result outside finite domain')
    return result


def experiment():
    q=bias(1.5,lam=0.)
    q2=bias(1.505,lam=0.)
    m=bias(1.5,lam=.02)
    return dict(units={'id':'A','vd':'V','gm':'S','gds':'S','c':'F'},q=q,
                delta_vd=q2['vd']-q['vd'],linear_delta_vd=-q['gm']*2000*.005,
                clm=m,moscap=moscap(.3),weak=weak(.4,.2),
                bjt=ebers(.7,-2.3),ac=[dict(f=f,re=ac_gain(f).real,im=ac_gain(f).imag) for f in [0,1e3,1e5,1e6]])


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'results.json').write_text(json.dumps(experiment(),indent=2)+'\n')

if __name__=='__main__':main()
