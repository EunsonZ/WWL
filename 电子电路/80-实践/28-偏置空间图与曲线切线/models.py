"""Finite teaching models, SI units; importing performs no generation.

The PN carrier approximation in the SCR is deliberately not self-consistent
Poisson/drift-diffusion. QNR minority profiles are not returned.
"""
import math

Q = 1.602176634e-19
KB = 1.380649e-23
EPS = 11.7 * 8.8541878128e-12
VT = KB * 300 / Q
NA, ND, NI = 1e22, 2e22, 1e16
VBI = VT * math.log(NA * ND / NI**2)

def finite(value, lo, hi, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'{name} outside finite teaching domain [{lo}, {hi}]')
    return float(value)

def pn(vd, x):
    vd = finite(vd, -2, .3, 'vd (V)')
    x = finite(x, -1e-6, 1e-6, 'x (m)')
    barrier = VBI - vd
    width = math.sqrt(2 * EPS * barrier / Q * (1 / NA + 1 / ND))
    xp, xn = ND * width / (NA + ND), NA * width / (NA + ND)
    if x < -xp:
        rho, field, phi = 0., 0., 0.
    elif x < 0:
        rho = -Q * NA
        field = -Q * NA * (x + xp) / EPS
        phi = Q * NA * (x + xp)**2 / (2 * EPS)
    elif x <= xn:
        rho = Q * ND
        field = Q * ND * (x - xn) / EPS
        phi = barrier - Q * ND * (xn - x)**2 / (2 * EPS)
    else:
        rho, field, phi = 0., 0., barrier
    inside = -xp <= x <= xn
    n = ND * math.exp((phi - barrier) / VT) if inside else None
    p = NA * math.exp(-phi / VT) if inside else None
    return dict(vd=vd, x=x, xp=xp, xn=xn, width=width, barrier=barrier,
                NA=NA if x < 0 else 0., ND=ND if x >= 0 else 0.,
                rho=rho, E=field, phi=phi, n=n, p=p,
                carrier_model='SCR approximate split quasi-Fermi; not full transport')

def diode(v):
    v = finite(v, 0, .65, 'diode V')
    current = 1e-12 * math.expm1(v / VT)
    slope = 1e-12 * math.exp(v / VT) / VT
    return current, slope

def bjt(vbe, vce):
    vbe = finite(vbe, .5, .75, 'vbe')
    vce = finite(vce, 0, 5, 'vce')
    ut, saturation, beta_r = .026, 1e-15, 1.
    f, r = math.expm1(vbe / ut), math.expm1((vbe - vce) / ut)
    current = saturation * (f - r - r / beta_r)
    gm = saturation * (math.exp(vbe / ut) - (1 + 1 / beta_r) * math.exp((vbe - vce) / ut)) / ut
    gds = saturation * (1 + 1 / beta_r) * math.exp((vbe - vce) / ut) / ut
    return current, gm, gds

def mos(vgs, vds):
    vgs = finite(vgs, 0, 2, 'vgs')
    vds = finite(vds, 0, 5, 'vds')
    k, threshold, lam = .002, .5, .02
    overdrive = vgs - threshold
    if overdrive <= 0:
        return 0., 0., 0.
    if vds < overdrive:
        base = k * (overdrive * vds - vds**2 / 2)
        gm0, gds0 = k * vds, k * (overdrive - vds)
    else:
        base = k * overdrive**2 / 2
        gm0, gds0 = k * overdrive, 0.
    return base * (1 + lam * vds), gm0 * (1 + lam * vds), gds0 * (1 + lam * vds) + base * lam

def intersection(current, vmax=5., resistance=2000.):
    """Bisection with endpoint/sign/convergence checks, bounded 80 iterations."""
    vmax = finite(vmax, .1, 5., 'vmax')
    resistance = finite(resistance, 10., 1e5, 'resistance')
    lo, hi = 0., vmax
    def evaluate(v):
        value = current(v)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('Current callback must return a finite real number (A)')
        try:
            value = float(value)
        except (OverflowError, ValueError):
            raise ValueError('Current callback must return a finite real number (A)') from None
        if not math.isfinite(value):
            raise ValueError('Current callback must return a finite real number (A)')
        residual = value - (vmax - v) / resistance
        if not math.isfinite(residual):
            raise ValueError('Load residual must be finite (A)')
        return value, residual
    def f(v):
        return evaluate(v)[1]
    if not f(lo) <= 0 <= f(hi):
        raise ValueError('No bracketed monotone load intersection')
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) <= 0:
            lo = mid
        else:
            hi = mid
    v = (lo + hi) / 2
    value, residual = evaluate(v)
    if abs(residual) > 1e-11:
        raise ArithmeticError('Load intersection residual exceeds contract')
    return v, value

def results():
    dv, di = intersection(lambda v: diode(v)[0], vmax=.65, resistance=1000.)
    bv, bi = intersection(lambda v: bjt(.026 * math.log(1e12), v)[0])
    mv, mi = intersection(lambda v: mos(1.5, v)[0])
    return {'units': 'V, A, S, m, V/m, C/m^3; all parameters teaching only',
            'pn': [{k:v for k,v in pn(d, 0).items() if k not in ('n','p')} for d in (0., .2, -1.)],
            'diode_Q': [dv, di], 'BJT_Q': [bv, bi], 'MOS_Q': [mv, mi]}
