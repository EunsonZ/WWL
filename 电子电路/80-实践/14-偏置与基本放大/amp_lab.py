"""Scalar, real, low-voltage teaching models; no import-time file or GUI effects."""
import math
import numbers

def real(x, name, *, positive=False, nonnegative=False):
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise TypeError(f'{name}: finite real scalar required (bool/complex/array rejected)')
    try:
        value = float(x)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f'{name}: not representable') from exc
    if not math.isfinite(value) or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(f'{name}: invalid range')
    return value

def checked(x):
    if not math.isfinite(x):
        raise ValueError('derived result exceeds finite arithmetic')
    return x

def bisect(f, lo, hi, *, budget=160):
    """Bracketed monotone root; finite work, adjacent-float stop, residual selection."""
    lo, hi = real(lo,'lo'), real(hi,'hi')
    if type(budget) is not int or not 1 <= budget <= 4096: raise ValueError('budget: 1..4096 int')
    fl, fh = checked(f(lo)), checked(f(hi))
    if fl == 0: return lo
    if fh == 0: return hi
    if not lo < hi or (fl > 0) == (fh > 0): raise ValueError('root not bracketed')
    for _ in range(budget):
        mid = lo + (hi-lo)/2
        if mid == lo or mid == hi:
            return lo if abs(fl) <= abs(fh) else hi
        fm = checked(f(mid))
        if fm == 0: return mid
        if (fm > 0) == (fl > 0): lo, fl = mid, fm
        else: hi, fh = mid, fm
    raise RuntimeError('root budget exhausted')

def mos_point(vgs, vds, k=.002, vt=1., lam=.02):
    vgs,vds,k,vt,lam = real(vgs,'vgs'),real(vds,'vds',nonnegative=True),real(k,'k',positive=True),real(vt,'vt'),real(lam,'lam',nonnegative=True)
    ov = checked(vgs-vt)
    if ov <= 0: raise ValueError('strong-inversion saturation model: VGS > VT required')
    if vds < ov: raise ValueError('saturation model: VDS >= VGS-VT required')
    factor = checked(1+lam*vds)
    i0 = checked(.5*k*ov*ov)
    current = checked(i0*factor)
    gm, go = checked(k*ov*factor), checked(i0*lam)
    return dict(id=current, vov=ov, gm=gm, go=go, ro=None if go==0 else checked(1/go), vgs=vgs, vds=vds)

def mos_bias(vg=2., vdd=5., rd=2000., rs=0., k=.002, vt=1., lam=.02):
    vg,vdd,rd,rs,k,vt,lam = real(vg,'vg'),real(vdd,'vdd',positive=True),real(rd,'rd',positive=True),real(rs,'rs',nonnegative=True),real(k,'k',positive=True),real(vt,'vt'),real(lam,'lam',nonnegative=True)
    ov0=checked(vg-vt)
    if ov0 <= 0: raise ValueError('gate below strong-inversion threshold')
    rsum=checked(rd+rs)
    upper=min(vdd/rsum,ov0/rs) if rs else vdd/rd
    def f(i):
        ov=ov0-i*rs; vd=vdd-i*rsum
        return checked(i-.5*k*ov*ov*(1+lam*vd))
    i=bisect(f,0.,upper)
    vs,vd=checked(i*rs),checked(vdd-i*rd)
    p=mos_point(vg-vs,vd-vs,k,vt,lam)
    p.update(vg=vg,vd=vd,vs=vs,id=i)
    return p

def bjt_bias(vdd=5., rt=30000., rb=10000., re=1000., rc=4000., beta=100., isat=1e-15, ut=.026):
    vals=[real(x,n,positive=True) for x,n in zip((vdd,rt,rb,re,rc,beta,isat,ut),('vdd','rt','rb','re','rc','beta','isat','ut'))]
    vdd,rt,rb,re,rc,beta,isat,ut=vals
    vth=checked(vdd/(1+rt/rb)); rth=checked(rt/(1+rt/rb))
    rho=checked(rth/beta+(1+1/beta)*re)
    hi=checked(vth/rho)
    if hi <= isat: raise ValueError('no positive VBE bracket')
    def f(i): return checked(ut*(math.log(i)-math.log(isat))+i*rho-vth)
    ic=bisect(f,isat,hi)
    ib=ic/beta; ie=checked(ic+ib); ve=checked(ie*re); vb=checked(vth-ib*rth); vc=checked(vdd-ic*rc)
    if not vc > vb > ve: raise ValueError('forward-active assumption fails (VC > VB > VE required)')
    gm=checked(ic/ut)
    return dict(ic=ic,ib=ib,ie=ie,vb=vb,ve=ve,vc=vc,vbe=vb-ve,vce=vc-ve,gm=gm,rpi=checked(beta/gm),vth=vth,rth=rth)

def parallel(a,b):
    a,b=real(a,'a',positive=True),real(b,'b',positive=True)
    return checked(min(a,b)/(1+min(a,b)/max(a,b)))

def cs(gm,go,rd,rs=0.,rl=None):
    gm,go,rd,rs=real(gm,'gm',positive=True),real(go,'go',nonnegative=True),real(rd,'rd',positive=True),real(rs,'rs',nonnegative=True)
    yd=1/rd+(0 if rl is None else 1/real(rl,'rl',positive=True))
    den=checked(yd*checked(1+rs*checked(gm+go))+go)
    gain=checked(-gm/den)
    rout=rd if go==0 else parallel(rd,checked((1+gm*rs)/go+rs))
    return dict(av=gain,rout=rout,rin_gate=None)

def ce(gm,beta,go,rc,re,rl=None):
    gm,beta,go,rc,re=real(gm,'gm',positive=True),real(beta,'beta',positive=True),real(go,'go',nonnegative=True),real(rc,'rc',positive=True),real(re,'re',positive=True)
    gp=checked(gm/beta); yc=1/rc+(0 if rl is None else 1/real(rl,'rl',positive=True)); ye=1/re
    a=checked(yc+go); b=checked(go+gm); c=go; d=checked(ye+go+gm+gp)
    det=checked(a*d-b*c)
    if det <= 0: raise ValueError('invalid determinant')
    vc=checked((-gm*d+b*(gm+gp))/det)
    ve=checked((a*(gm+gp)-c*gm)/det)
    ib=checked(gp*(1-ve))
    if ib <= 0: raise ValueError('input conductance not positive')
    z=parallel(re,1/gp)
    rout=rc if go==0 else parallel(rc,checked(1/go+z*(1+gm/go)))
    return dict(av=vc,ve_over_vb=ve,rin_base=1/ib,rout=rout)

def cg(gm,go,rd,rl=None,rsig=0.):
    gm,go,rd,rsig=real(gm,'gm',positive=True),real(go,'go',nonnegative=True),real(rd,'rd',positive=True),real(rsig,'rsig',nonnegative=True)
    r=rd if rl is None else parallel(rd,rl)
    av=checked((gm+go)/(1/r+go))
    rin=checked(1/(av/r))
    rout=rd if go==0 else parallel(rd,checked(1/go+rsig*(1+gm/go)))
    return dict(av=av,rin=rin,rout=rout,ai_delivered=1.)

def follower(gm,go,rs,rl=None):
    gm,go,rs=real(gm,'gm',positive=True),real(go,'go',nonnegative=True),real(rs,'rs',positive=True)
    den=checked(gm+go+1/rs+(0 if rl is None else 1/real(rl,'rl',positive=True)))
    return dict(av=checked(gm/den),rout=checked(1/(gm+go+1/rs)),rin_gate=None)

def mos_reference(iref=.001,k=.002,vt=1.,lam=.02):
    iref,k,vt,lam=real(iref,'iref',positive=True),real(k,'k',positive=True),real(vt,'vt',nonnegative=True),real(lam,'lam',nonnegative=True)
    hi=checked(vt+math.sqrt(2*iref/k))
    return bisect(lambda vg: checked(.5*k*(vg-vt)**2*(1+lam*vg)-iref),vt,hi)

def mirror(vo,iref=.001,k=.002,vt=1.,lam=.02):
    vo=real(vo,'vo',nonnegative=True)
    vg=mos_reference(iref,k,vt,lam)
    p=mos_point(vg,vo,k,vt,lam);p.update(vg=vg,iref=iref,ratio=p['id']/iref)
    return p

def cascode(vo,iref=.001,k=.002,vt=1.,lam=.02):
    vo=real(vo,'vo',positive=True)
    vg=mos_reference(iref,k,vt,lam)
    # Four-transistor stacked mirror; each body tied to its own source.
    if vo < 2*vg-vt: raise ValueError('upper MOS saturation/compliance fails')
    lo=vg-vt; hi=min(vo,2*vg-vt)
    def f(x):
        i1=.5*k*(vg-vt)**2*(1+lam*x)
        i2=.5*k*(2*vg-x-vt)**2*(1+lam*(vo-x))
        return checked(i1-i2)
    vx=bisect(f,lo,hi)
    low=mos_point(vg,vx,k,vt,lam); high=mos_point(2*vg-vx,vo-vx,k,vt,lam)
    r1,r2=low['ro'],high['ro']
    rout=None if r1 is None or r2 is None else checked(r1+r2+high['gm']*r1*r2)
    return dict(id=low['id'],vg=vg,vc=2*vg,vx=vx,compliance=2*vg-vt,rout=rout,gm_upper=high['gm'])

def bjt_mirror(vo,iref=.001,beta=100.,va=None,isat=1e-15,ut=.026):
    vo,iref,beta,isat,ut=real(vo,'vo',positive=True),real(iref,'iref',positive=True),real(beta,'beta',positive=True),real(isat,'isat',positive=True),real(ut,'ut',positive=True)
    va=None if va is None else real(va,'va',positive=True)
    def currents(vb):
        base=checked(isat*math.exp(vb/ut))
        i1=checked(base*(1 if va is None else 1+vb/va));i2=checked(base*(1 if va is None else 1+vo/va))
        return i1,i2
    hi=checked(ut*(math.log(iref)-math.log(isat)))
    if hi <= 0: raise ValueError('reference current below model domain')
    vb=bisect(lambda v: checked(sum([currents(v)[0]*(1+1/beta),currents(v)[1]/beta])-iref),0.,hi)
    if vo < vb: raise ValueError('output BC junction forward biased: model not forward active')
    i1,i2=currents(vb)
    return dict(vb=vb,ic_ref=i1,ic_out=i2,ratio=i2/iref,ib_ref=i1/beta,ib_out=i2/beta)

def follower_bias(vg=3.,vdd=5.,rs=1000.,k=.002,vt=1.,lam=.02):
    vg,vdd,rs,k,vt,lam=real(vg,'vg'),real(vdd,'vdd',positive=True),real(rs,'rs',positive=True),real(k,'k',positive=True),real(vt,'vt'),real(lam,'lam',nonnegative=True)
    if vg <= vt: raise ValueError('gate below threshold')
    hi=min((vg-vt)/rs,vdd/rs)
    i=bisect(lambda i:checked(i-.5*k*(vg-vt-i*rs)**2*(1+lam*(vdd-i*rs))),0,hi)
    vs=checked(i*rs);p=mos_point(vg-vs,vdd-vs,k,vt,lam);p.update(vg=vg,vs=vs,vd=vdd,id=i)
    return p

def cb(gm,beta,go,rc,rl=None):
    gm,beta,go,rc=real(gm,'gm',positive=True),real(beta,'beta',positive=True),real(go,'go',nonnegative=True),real(rc,'rc',positive=True)
    r=rc if rl is None else parallel(rc,rl)
    av=checked((gm+go)/(1/r+go));gp=gm/beta
    gin=checked(av/r+gp)
    return dict(av=av,rin=checked(1/gin),ai_delivered=checked((av/r)/gin))

def emitter_follower(gm,beta,go,rbias,rl=None,rsource=0.):
    gm,beta,go,rbias,rsource=real(gm,'gm',positive=True),real(beta,'beta',positive=True),real(go,'go',nonnegative=True),real(rbias,'rbias',positive=True),real(rsource,'rsource',nonnegative=True)
    gp=checked(gm/beta);ge=1/rbias+(0 if rl is None else 1/real(rl,'rl',positive=True))
    den=checked(gm+gp+go+ge);av=checked((gm+gp)/den)
    # Avoid cancellation in 1-Av when the gain rounds to one.
    rin=checked((1/gp)*den/checked(go+ge))
    rout=checked(1/checked(go+1/rbias+(beta+1)/checked(1/gp+rsource)))
    return dict(av=av,rin_base=rin,rout=rout)

def active_load(vout=3.,current=.001,vdd=5.,k=.002,vt=1.,lam=.02,rl=None):
    vout,current,vdd,k,vt,lam=real(vout,'vout',positive=True),real(current,'current',positive=True),real(vdd,'vdd',positive=True),real(k,'k',positive=True),real(vt,'vt',nonnegative=True),real(lam,'lam',nonnegative=True)
    if vout >= vdd: raise ValueError('output must lie inside rails')
    vn=checked(math.sqrt(2*current/checked(k*checked(1+lam*vout))))
    vp=checked(math.sqrt(2*current/checked(k*checked(1+lam*(vdd-vout)))))
    n=mos_point(vt+vn,vout,k,vt,lam);p=mos_point(vt+vp,vdd-vout,k,vt,lam)
    den=checked(n['go']+p['go']+(0 if rl is None else 1/real(rl,'rl',positive=True)))
    if den <= 0: raise ValueError('zero output conductance: ideal infinite gain excluded')
    ref=mos_point(vt+vp,vt+vp,k,vt,lam)
    return dict(id=current,vout=vout,vg_n=vt+vn,vg_p=vdd-vt-vp,iref_p=ref['id'],gm=n['gm'],go_n=n['go'],go_p=p['go'],av=checked(-n['gm']/den),lower=vn,upper=vdd-vp)
