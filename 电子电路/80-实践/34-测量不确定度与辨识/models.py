"""Finite teaching models; SI units; synthetic observations, no instrument I/O."""
import math
import random
import statistics


def real(x, name, lo, hi):
    # Validate before conversion: bool/complex/arrays/coercion objects not accepted.
    if type(x) not in (int, float):
        raise ValueError(f'{name}: builtin real required')
    try:
        y = float(x)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f'{name}: finite required') from exc
    if not math.isfinite(y) or not lo <= y <= hi:
        raise ValueError(f'{name}: outside [{lo}, {hi}]')
    return y


def count(x, name, lo, hi):
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError(f'{name}: integer in [{lo}, {hi}] required')
    return x


def rc(r, c):
    r = real(r, 'R/ohm', 10, 1e7)
    c = real(c, 'C/F', 1e-12, .01)
    tau = r*c
    real(tau, 'tau/s', 1e-8, 100)
    return r, c, tau


def step(r, c, t, u=1., v0=0.):
    r, c, tau = rc(r, c)
    t = real(t, 't/s', 0, 1e4)
    u = real(u, 'U/V', -100, 100)
    v0 = real(v0, 'v0/V', -100, 100)
    q = t/tau
    e = math.exp(-q)
    # Keep nonzero initial values even for small t, avoid U+(v0-U)*e.
    return v0*e + u*(-math.expm1(-q))


def current(r, c, t, u=1., v0=0.):
    r, c, tau = rc(r, c)
    t = real(t, 't/s', 0, 1e4)
    u = real(u, 'U/V', -100, 100)
    v0 = real(v0, 'v0/V', -100, 100)
    return (u-v0)/r*math.exp(-t/tau)


def frequency(r, c, omega):
    r, c, tau = rc(r, c)
    omega = real(omega, 'omega/rad_s', 0, 1e9)
    return 1/(1+1j*omega*tau)


def input_impedance(r, c, omega):
    r, c, tau = rc(r, c)
    omega = real(omega, 'omega/rad_s', 1e-6, 1e9)
    return complex(r, -1/(omega*c))


def identify_impedance(z, omega):
    if type(z) is not complex or not math.isfinite(z.real) or not math.isfinite(z.imag):
        raise ValueError('finite builtin complex Z required')
    omega = real(omega, 'omega/rad_s', 1e-6, 1e9)
    if z.imag >= 0:
        raise ValueError('ideal series RC requires negative imaginary Z')
    r, c, _ = rc(z.real, -1/(omega*z.imag))
    return r, c


def identify_current(tau, i_at_tau, u=1.):
    tau = real(tau, 'tau/s', 1e-8, 100)
    i_at_tau = real(i_at_tau, 'i/A', 1e-12, 10)
    u = real(u, 'U/V', 1e-6, 100)
    r = u/math.e/i_at_tau
    r, c, _ = rc(r, tau/r)
    return r, c


def loaded_step(r, c, t, rl, cp=0., rs=0., u=1., v0=0.):
    r, c, _ = rc(r, c)
    rl = real(rl, 'RL/ohm', 10, 1e9)
    cp = real(cp, 'Cp/F', 0, .01)
    rs = real(rs, 'Rs/ohm', 0, 1e7)
    rt = r+rs
    k = rl/(rt+rl)
    tau = (rt*rl/(rt+rl))*(c+cp)
    real(tau, 'loaded tau/s', 1e-8, 100)
    t = real(t, 't/s', 0, 1e4)
    u = real(u, 'U/V', -100, 100)
    v0 = real(v0, 'v0/V', -100, 100)
    return v0*math.exp(-t/tau)+k*u*(-math.expm1(-t/tau)), k, tau


def sensitivity(r, c, t, u=1.):
    """Rows d[V,I]/d[ln(R/R0),ln(C/C0)]; fixed t,U and zero IC."""
    r, c, tau = rc(r, c)
    t = real(t, 't/s', 0, 1e4)
    u = real(u, 'U/V', -100, 100)
    q = t/tau
    s = -u*q*math.exp(-q)
    i = u/r*math.exp(-q)
    return ((s, s), (i*(q-1), i*q))


def fisher(r, c, t, sigma_v=.001, sigma_i=1e-6, include_current=False):
    if type(include_current) is not bool:
        raise ValueError('include_current must be bool')
    sigma_v = real(sigma_v, 'sigma_v/V', 1e-12, 10)
    sigma_i = real(sigma_i, 'sigma_i/A', 1e-12, 10)
    v, i = sensitivity(r, c, t)
    rows = [(v[0]/sigma_v, v[1]/sigma_v)]
    if include_current:
        rows.append((i[0]/sigma_i, i[1]/sigma_i))
    a = math.fsum(x*x for x,y in rows)
    b = math.fsum(x*y for x,y in rows)
    d = math.fsum(y*y for x,y in rows)
    return ((a,b),(b,d))


def tau_from_crossing(t, v, u):
    t = real(t, 't/s', 1e-12, 1e4)
    u = real(u, 'U/V', 1e-6, 100)
    v = real(v, 'V/V', 0, 100)
    if not 0 < v < u:
        raise ValueError('zero-IC positive step requires 0<V<U')
    try:
        a = -math.log1p(-v/u)
        result = t/a
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError('crossing is outside finite numerical support') from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError('crossing tau must be finite and positive')
    return result


def tau_sensitivity(t, v, u):
    tau = tau_from_crossing(t, v, u)
    a = t/tau
    try:
        cs = (1/a, -t/(a*a*(u-v)), t*v/(a*a*u*(u-v)))
    except (ZeroDivisionError, OverflowError) as exc:
        raise ValueError('crossing sensitivity outside finite numerical support') from exc
    if not all(math.isfinite(x) for x in cs):
        raise ValueError('crossing sensitivity must be finite')
    return cs


def tau_budget(t, v, u, ut, uv, uu, rho=0.):
    cs = tau_sensitivity(t, v, u)
    ut = real(ut, 'u_t/s', 0, 100)
    uv = real(uv, 'u_v/V', 0, 10)
    uu = real(uu, 'u_u/V', 0, 10)
    rho = real(rho, 'rho(V,U)', -1, 1)
    x,y,z = (a*b for a,b in zip(cs,(ut,uv,uu)))
    # PSD covariance expressed as squares; avoids negative cancellation at rho=+-1.
    try:
        variance = x*x+(y+rho*z)**2+(1-rho*rho)*z*z
    except OverflowError as exc:
        raise ValueError('budget outside finite numerical support') from exc
    if not math.isfinite(variance):
        raise ValueError('budget variance must be finite')
    diagonal=(x*x,y*y,z*z);cross=2*rho*y*z
    if not all(math.isfinite(q) for q in (*diagonal,cross)):
        raise ValueError('reported budget components must be finite')
    return {'tau_s':tau_from_crossing(t,v,u), 'sensitivities':cs,
            'diagonal_s2':diagonal, 'cross_s2':cross,
            'uc_s':math.sqrt(variance)}


def mean_uncertainty(values):
    if type(values) not in (list,tuple) or not 2 <= len(values) <= 10000:
        raise ValueError('2..10000 observations required')
    xs=[real(x,'observation',-1e9,1e9) for x in values]
    return statistics.fmean(xs), statistics.stdev(xs)/math.sqrt(len(xs)), len(xs)-1


def expanded(uc, k):
    return real(uc,'uc',0,1e9)*real(k,'k',0,100)


def mc_tau(t, v, u, ut, uv, uu, rho=0., samples=10000, seed=23):
    """Finite Gaussian joint-PDF teaching propagation; no adaptive coverage guarantee.

    Invalid model draw fails, never silently reject/resample it. Local PRNG only.
    """
    tau_from_crossing(t,v,u)
    ut=real(ut,'u_t/s',0,100)
    uv=real(uv,'u_v/V',0,10)
    uu=real(uu,'u_u/V',0,10)
    rho=real(rho,'rho',-1,1)
    samples=count(samples,'samples',100,20000)
    seed=count(seed,'seed',0,2**32-1)
    rng=random.Random(seed)
    ys=[]
    for _ in range(samples):
        zt,zv,zu=(rng.gauss(0,1) for k in range(3))
        ys.append(tau_from_crossing(t+ut*zt,v+uv*zv,
                    u+uu*(rho*zv+math.sqrt(1-rho*rho)*zu)))
    ys.sort()
    def quantile(p):
        q=(samples-1)*p; j=int(q); f=q-j
        return ys[j]*(1-f)+ys[min(j+1,samples-1)]*f
    return {'mean_s':statistics.fmean(ys),'std_s':statistics.stdev(ys),
            'q025_s':quantile(.025),'q975_s':quantile(.975),
            'samples':samples,'seed':seed,'distribution':'specified joint Gaussian',
            'interval':'empirical linear-interpolated central 95%; no tolerance certification'}


def voltage_loss(r, c, times, values, sigma=.001):
    rc(r,c)
    if type(times) not in (list,tuple) or type(values) not in (list,tuple):
        raise ValueError('lists/tuples required')
    if not 1 <= len(times) <= 256 or len(times) != len(values):
        raise ValueError('matching 1..256 samples required')
    sigma=real(sigma,'sigma/V',1e-12,10)
    terms=[]
    for t,v in zip(times,values):
        v=real(v,'observed V',-100,100)
        terms.append(((step(r,c,t)-v)/sigma)**2)
    return math.fsum(terms)
