"""Bounded teaching models; no device/process/measurement or compliance claims.
Import uses only the standard library and never parses argv or writes files.
"""
import math
import random
from numbers import Real

K_EV = 8.617333262e-5
THERMAL = {'Cj_J_per_K': 2.0, 'Cb_J_per_K': 8.0,
           'Rjb_K_per_W': 5.0, 'Rba_K_per_W': 20.0,
           'Rja_K_per_W': 100.0, 'Ta_K': 300.0}


def real(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(name + ' must be a finite real scalar (not bool)')
    try:
        v = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(name + ' is not a representable real') from exc
    if not math.isfinite(v) or not low <= v <= high:
        raise ValueError(name + ' outside bounded teaching domain')
    return v


def integer(name, value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(name + ' must be a bounded integer')
    return value


def poisson_yield(area_m2, density_per_m2):
    """Uniform independent fatal Poisson defects, not fitted process yield."""
    a = real('area_m2', area_m2, 0, 1)
    d = real('density_per_m2', density_per_m2, 0, 1e12)
    return math.exp(-a * d)


def accepted_bad(prior_bad, sensitivity, false_reject):
    """Bayes calculation for real-defect population assumptions, not coverage."""
    d = real('prior_bad', prior_bad, 0, 1)
    s = real('sensitivity', sensitivity, 0, 1)
    f = real('false_reject', false_reject, 0, 1)
    bad_passed = d * (1 - s)
    acceptance = (1 - d) * (1 - f) + bad_passed
    if acceptance == 0:
        raise ValueError('acceptance probability is zero in float arithmetic')
    return bad_passed / acceptance


def zero_failure_upper(n, alpha=0.05):
    integer('n', n, 1, 1_000_000)
    a = real('alpha', alpha, 1e-12, 1 - 1e-12)
    return -math.expm1(math.log(a) / n)


def mismatch_mc(n=10000, seed=2403, sigma_global=0.03,
                sigma_local=0.01, threshold=0.02):
    """Independent virtual dies; one shared G and two iid L per die.
    Return sample statistics and first 300 plotting points, not production data.
    """
    integer('n', n, 2, 100000)
    integer('seed', seed, 0, 2**32 - 1)
    sg = real('sigma_global', sigma_global, 0, .2)
    sl = real('sigma_local', sigma_local, 0, .2)
    limit = real('threshold', threshold, 0, 1)
    rng = random.Random(seed)
    md = ma = vd = va = 0.0
    passed = 0
    points = []
    for k in range(1, n + 1):
        g = rng.gauss(0, sg)
        l1, l2 = rng.gauss(0, sl), rng.gauss(0, sl)
        x1, x2 = g + l1, g + l2
        diff, avg = l1 - l2, g + (l1 + l2) / 2
        dd, da = diff - md, avg - ma
        md += dd / k
        ma += da / k
        vd += dd * (diff - md)
        va += da * (avg - ma)
        passed += abs(diff) <= limit
        if k <= 300:
            points.append((x1, x2))
    analytic = 1.0 if sl == 0 else math.erf(limit / (2 * sl))
    return {'n': n, 'seed': seed, 'passed': passed, 'fraction': passed / n,
            'mean_difference': md, 'variance_difference': vd / (n - 1),
            'mean_average': ma, 'variance_average': va / (n - 1),
            'analytic_fraction': analytic, 'points_first_300': points}


def thermal_rhs(theta_j, theta_b, power_W=.2, feedback_W_per_K=0):
    j = real('theta_j', theta_j, -100, 100)
    b = real('theta_b', theta_b, -100, 100)
    p = real('power_W', power_W, 0, .5)
    g = real('feedback_W_per_K', feedback_W_per_K, 0, .04)
    return ((p + g*j - (j-b)/5 - j/100) / 2,
            ((j-b)/5 - b/20) / 8)


def thermal_trace(t_end_s=200, step_s=.1, power_W=.2,
                  feedback_W_per_K=0):
    """Fixed network, zero excess-temperature IC, bounded explicit RK4.
    Stability/convergence verified only on this fixed domain, not arbitrary RC.
    """
    end = real('t_end_s', t_end_s, 0, 200)
    step = real('step_s', step_s, 1e-5, .1)
    p = real('power_W', power_W, 0, .5)
    g = real('feedback_W_per_K', feedback_W_per_K, 0, .04)
    if end == 0:
        return [(0.0, 0.0, 0.0)]
    n = math.ceil(end / step)
    if n > 20000:
        raise ValueError('RK4 step budget exceeds 20000')
    dt = end / n
    j = b = 0.0
    rows = [(0.0, j, b)]
    for k in range(n):
        a = thermal_rhs(j, b, p, g)
        c = thermal_rhs(j + dt*a[0]/2, b + dt*a[1]/2, p, g)
        d = thermal_rhs(j + dt*c[0]/2, b + dt*c[1]/2, p, g)
        e = thermal_rhs(j + dt*d[0], b + dt*d[1], p, g)
        j += dt*(a[0]+2*c[0]+2*d[0]+e[0])/6
        b += dt*(a[1]+2*c[1]+2*d[1]+e[1])/6
        rows.append((end*(k+1)/n, j, b))
    return rows


def thermal_grid(power_W=.2, tolerance_W=1e-10):
    """9x9 fixed-temperature boundary, 7x7 inner nodes, links .1 W/K.
    Gauss-Seidel termination on node heat-balance residual (max 4000 sweeps).
    Units: excess K; coordinates are indices, not specified metric geometry.
    """
    p = real('power_W', power_W, 0, .5)
    tol = real('tolerance_W', tolerance_W, 1e-12, 1e-6)
    t = [[0.0]*9 for _ in range(9)]
    for iteration in range(1, 4001):
        for y in range(1, 8):
            for x in range(1, 8):
                source = p if x == y == 4 else 0.0
                t[y][x] = (t[y-1][x]+t[y+1][x]+t[y][x-1]+t[y][x+1]+source/.1)/4
        residual = max(abs(.1*(4*t[y][x]-t[y-1][x]-t[y+1][x]
                            -t[y][x-1]-t[y][x+1])-(p if x == y == 4 else 0))
                       for y in range(1,8) for x in range(1,8))
        if residual <= tol:
            flux = .1*sum(t[1][i]+t[7][i]+t[i][1]+t[i][7] for i in range(1,8))
            return {'theta_K': t, 'iterations': iteration,
                    'max_residual_W': residual, 'boundary_flux_W': flux}
    raise ValueError('grid residual did not reach tolerance within budget')


def arrhenius_factor(Ea_eV, use_K, stress_K):
    ea = real('Ea_eV', Ea_eV, 0, 5)
    u = real('use_K', use_K, 1, 5000)
    s = real('stress_K', stress_K, 1, 5000)
    exponent = ea/K_EV*(1/u-1/s)
    if not -700 <= exponent <= 700:
        raise ValueError('acceleration exponent outside representable teaching range')
    return math.exp(exponent)


def affected_serials(records, lot):
    """Toy traceability; validate shape, never change past assembly records."""
    if not isinstance(lot, str) or not lot:
        raise ValueError('lot must be a nonempty string')
    if not isinstance(records, (list, tuple)):
        raise ValueError('records must be a finite list or tuple')
    if len(records) > 10000:
        raise ValueError('trace budget exceeds 10000')
    seen, result = set(), []
    for r in records:
        if not isinstance(r, dict) or set(r) != {'serial', 'bom', 'lot'}:
            raise ValueError('record must have exactly serial/bom/lot')
        if any(not isinstance(r[k], str) or not r[k] for k in r):
            raise ValueError('record fields must be nonempty strings')
        if r['serial'] in seen:
            raise ValueError('duplicate serial needs explicit revision history, unsupported here')
        seen.add(r['serial'])
        if r['lot'] == lot:
            result.append(r['serial'])
    return sorted(result)
