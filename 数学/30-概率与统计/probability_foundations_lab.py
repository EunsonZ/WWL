"""Recompute the S01 teaching examples; no network or implicit file writes.

Requires NumPy; --figures-dir also requires Matplotlib. These finite teaching
calculations are checks of examples, not proofs or validation of real data.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def binomial_pmf(n: int, p: float) -> np.ndarray:
    if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 10000:
        raise ValueError("n must be an integer in [0, 10000]")
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("p must be finite and in [0, 1]")
    if p in (0, 1):
        out = np.zeros(n + 1)
        out[n if p == 1 else 0] = 1
        return out
    out = np.array([math.exp(math.lgamma(n + 1) - math.lgamma(k + 1)
                            - math.lgamma(n - k + 1) + k * math.log(p)
                            + (n - k) * math.log1p(-p)) for k in range(n + 1)])
    return out  # Retain computed mass; do not hide errors by renormalizing.


def binomial_tail(n: int, p: float, c: int) -> float:
    mass = binomial_pmf(n, p)
    if isinstance(c, bool) or not isinstance(c, int) or not 0 <= c <= n + 1:
        raise ValueError("c must be an integer in [0, n+1]")
    return float(mass[c:].sum())


def critical_count(n: int, p0: float = 0.5, alpha: float = 0.05) -> int:
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    mass = binomial_pmf(n, p0)
    tails = np.r_[np.cumsum(mass[::-1])[::-1], 0.0]
    return next(c for c in range(n + 2) if tails[c] <= alpha)


def lower_bound(n: int, k: int, alpha: float = 0.05) -> float:
    binomial_pmf(n, 0.5)
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= n:
        raise ValueError("k must be an integer in [0, n]")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if k == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(70):
        mid = (lo + hi) / 2
        if binomial_tail(n, mid, k) < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_tail(t: float, nu: int) -> float:
    """P(T_nu >= t), t >= 0, by a finite angular Gauss-Legendre integral."""
    if not math.isfinite(t) or t < 0 or isinstance(nu, bool) or not isinstance(nu, int) or nu <= 0:
        raise ValueError("t must be finite/nonnegative; nu a positive integer")
    nodes, weights = np.polynomial.legendre.leggauss(128)
    left, right = math.atan(t / math.sqrt(nu)), math.pi / 2
    theta = left + (nodes + 1) * (right - left) / 2
    # x=sqrt(nu)*tan(theta), density*dx=C*sqrt(nu)*cos(theta)^(nu-1).
    coef = math.exp(math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2)) / math.sqrt(math.pi)
    return float(coef * (right - left) / 2 * np.dot(weights, np.cos(theta) ** (nu - 1)))


def t_quantile(q: float, nu: int) -> float:
    if not math.isfinite(q) or not 0.5 < q < 1:
        raise ValueError("q must be in (0.5, 1)")
    lo, hi = 0.0, 1.0
    while t_tail(hi, nu) > 1 - q:
        hi *= 2
        if hi > 1e12:
            raise ValueError("quantile outside this teaching routine's range")
    for _ in range(70):
        mid = (lo + hi) / 2
        if t_tail(mid, nu) > 1 - q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def chi4_cdf(x: float) -> float:
    """Stable CDF of chi-square(4), including its quadratic small-x tail."""
    if not math.isfinite(x) or x < 0:
        raise ValueError("x must be finite and nonnegative")
    z = x / 2
    if z <= 1:
        # P(2,z)=exp(-z)*z^2*(1/2 + z/6 + z^2/24 + ...).
        # Positive terms avoid subtracting two numbers close to one.
        term = total = 0.5
        for denominator in range(3, 64):
            term *= z / denominator
            previous = total
            total += term
            if total == previous:
                break
        return math.exp(-z) * z * z * total
    return -math.expm1(-z) - z * math.exp(-z)


def chi4_quantile(q: float) -> float:
    # Avoid subnormal probability arithmetic at the very bottom of float64.
    if not math.isfinite(q) or not 1e-300 <= q < 1:
        raise ValueError("q must be finite and in [1e-300, 1)")
    lo = 0.0
    hi = 2 * math.sqrt(8*q) if q < 0.1 else 128.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if mid == lo or mid == hi:
            break
        if q <= 0.5:
            below = chi4_cdf(mid) < q
        else:
            # Use survival probability to avoid cancellation near q=1.
            z = mid / 2
            below = math.exp(-z) * (1+z) > 1-q
        if below:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def simple_regression(x, y) -> dict:
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.shape != x.shape or len(x) <= 2:
        raise ValueError("x/y must be equal one-dimensional arrays of length >2")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("x/y must be finite")
    # Subtract a represented observation first, so large offsets do not enter
    # the residual computation. Normalize both centered coordinate vectors.
    with np.errstate(over='ignore', invalid='ignore'):
        xd, yd = x-x[0], y-y[0]
    if not np.isfinite(xd).all() or not np.isfinite(yd).all():
        raise ValueError("centered differences must be representable in float64")
    with np.errstate(over='ignore', invalid='ignore'):
        xm, ym = float(xd.mean()), float(yd.mean())
        xc, yc = xd-xm, yd-ym
    if not np.isfinite(xc).all() or not np.isfinite(yc).all():
        raise ValueError("centered coordinates must be representable in float64")
    xs, ys = float(np.max(np.abs(xc))), float(np.max(np.abs(yc)))
    if xs == 0:
        raise ValueError("design must have full column rank")
    if ys == 0:
        raise ValueError("zero response variation: t/F routine is undefined")
    xn, yn = xc/xs, yc/ys
    design = np.column_stack((np.ones(len(x)), xn))
    scaled_beta, _, rank, _ = np.linalg.lstsq(design, yn, rcond=None)
    if rank != 2:
        raise ValueError("design must have full column rank")
    fitted_n = design @ scaled_beta
    residual_n = yn-fitted_n
    if np.linalg.norm(residual_n) <= 16*np.finfo(float).eps*np.linalg.norm(yn):
        raise ValueError("residual variation is below float64 working precision")
    residual = residual_n*ys
    sse_n = float(residual_n @ residual_n)
    sst_n = float(yn @ yn)
    ssr_n = float(fitted_n @ fitted_n)
    df = len(x)-2
    sxx_n = float(xn @ xn)
    se_n = math.sqrt(sse_n/df/sxx_n)
    slope = float(scaled_beta[1]*ys/xs)
    intercept = float(y[0]+ym+scaled_beta[0]*ys-slope*(x[0]+xm))
    se = se_n*ys/xs
    t = float(scaled_beta[1]/se_n)
    # Returning raw second moments requires them to remain representable;
    # inference is calculated in normalized coordinates before rescaling.
    sse, sst, ssr = sse_n*ys*ys, sst_n*ys*ys, ssr_n*ys*ys
    s2 = sse/df
    if not all(math.isfinite(v) for v in [sse,sst,ssr,s2,slope,intercept,se]) or se <= 0:
        raise ValueError("reported moments/coefficients must be representable in float64")
    if s2 < np.finfo(float).tiny:
        raise ValueError("reported variance must be in the float64 normal-number range")
    half = t_quantile(0.975, df)*se
    return dict(beta=[intercept,slope], residual=residual.tolist(), sse=sse,
                ssr=ssr, sst=sst, s2=s2, df=df, se_slope=se, t=t, f=t*t,
                p_two_sided=2*t_tail(abs(t), df),
                slope_ci=[slope-half,slope+half], r2=ssr_n/sst_n)


def one_way_anova(groups) -> dict:
    arrays = [np.asarray(g, dtype=float) for g in groups]
    if len(arrays) < 2 or any(g.ndim != 1 or len(g) < 2 or not np.isfinite(g).all() for g in arrays):
        raise ValueError("at least two finite groups of length >=2 required")
    count = sum(len(g) for g in arrays)
    grand = sum(float(g.sum()) for g in arrays) / count
    between = sum(len(g) * float(g.mean()-grand)**2 for g in arrays)
    within = sum(float(np.sum((g-g.mean())**2)) for g in arrays)
    if within <= 0:
        raise ValueError("within-group variance must be positive")
    df_b, df_w = len(arrays)-1, count-len(arrays)
    f = (between / df_b) / (within / df_w)
    return dict(grand=grand, between=between, within=within,
                total=between+within, df=[df_b, df_w], f=f)


def calculations() -> dict:
    reg = simple_regression([0, 1, 2, 3, 4], [1, 2, 2, 4, 5])
    anova = one_way_anova([[1, 2, 3], [3, 4, 5], [5, 6, 7]])
    mass = binomial_pmf(100, 0.8)
    exact = float(mass[:71].sum() + mass[90:].sum())  # |K-80|>=10; integer endpoints.
    c = critical_count(20)
    mean, s2, se = 2.8, 2.7, math.sqrt(0.54)
    half = t_quantile(0.975, 4) * se
    return dict(bernoulli=dict(n=100, p=0.8, epsilon=0.1, chebyshev=0.16,
                              exact_tail=exact, normal_cc_tail=math.erfc(2.375/math.sqrt(2))),
                test=dict(n=20, c=c, size=binomial_tail(20, .5, c),
                          invalid_c14_size=binomial_tail(20, .5, 14),
                          power_p08=binomial_tail(20, .8, c), lower95_k15=lower_bound(20, 15)),
                returns=dict(mean=mean, s2=s2, se=se, t=mean/se,
                             p_two_sided=2*t_tail(mean/se, 4), mean_ci=[mean-half, mean+half],
                             variance_ci=[4*s2/chi4_quantile(.975), 4*s2/chi4_quantile(.025)]),
                regression=reg, anova={**anova, 'p': (6/(6+2*anova['f']))**3},
                selective_reporting=1-.95**20)


def figures(directory: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 11, 'svg.fonttype': 'none', 'svg.hashsalt': 'wwl-s01-probability'})
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    ax[0].add_patch(Polygon([[0, 0], [0, 1], [1, 1]], color='#73b7db', alpha=.6))
    ax[0].plot([0, .6], [.6, .6], color='#b94b21', lw=3, label='Y=0.6: 0<X<0.6')
    ax[0].set(xlim=(0, 1), ylim=(0, 1), xlabel='X', ylabel='Y', title='Joint density 2 on 0<X<Y<1')
    ax[0].set_aspect('equal'); ax[0].legend(fontsize=9)
    grid = np.linspace(.01, 1, 600)
    ax[1].plot(grid, 1/(2*np.sqrt(grid)), color='#1676ad')
    ax[1].set(xlabel='Y = X^2, X~Uniform(-1,1)', ylabel='density', title='f(Y)=1/(2 sqrt(Y)), 0<Y<1')
    fig.savefig(directory/'joint-transform.svg', metadata={'Date': None}); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), constrained_layout=True)
    for ax, n in zip(axes, [5, 20, 100]):
        scale = math.sqrt(n*.8*.2); step = 1/scale
        z = (np.arange(n+1)-n*.8)/scale
        ax.bar(z, binomial_pmf(n, .8)/step, width=step, color='#73b7db', edgecolor='white', linewidth=.4, label='mass / grid spacing')
        grid = np.linspace(-4, 4, 500)
        ax.plot(grid, np.exp(-grid**2/2)/math.sqrt(2*math.pi), color='#b94b21', label='standard normal')
        ax.set(xlim=(-4, 4), xlabel='Z=(K-np)/sqrt(np(1-p))', ylabel='density', title=f'p=0.8, n={n}')
    axes[0].legend(fontsize=9)
    fig.savefig(directory/'clt-binomial.svg', metadata={'Date': None}); plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    k = np.arange(21); null = binomial_pmf(20, .5); alt = binomial_pmf(20, .8)
    ax[0].bar(k-.18, null, width=.36, color='#428dbd', label='H0: p=0.5')
    ax[0].bar(k+.18, alt, width=.36, color='#d77c48', label='H1: p=0.8')
    ax[0].axvspan(14.5, 20.5, color='#75ad84', alpha=.2, label='reject K>=15')
    ax[0].set(xlabel='K successes, n=20', ylabel='probability mass', title='Type I: null right tail; Type II: alt left region')
    ax[0].legend(fontsize=9)
    for n in [10, 20, 50]:
        c = critical_count(n)
        grid = np.linspace(.5, 1, 101)
        ax[1].plot(grid, [binomial_tail(n, float(p), c) for p in grid], label=f'n={n}, c={c}')
    ax[1].set(xlabel='true p', ylabel='P(reject)', title='Exact binomial power; alpha<=0.05', ylim=(0, 1))
    ax[1].legend()
    fig.savefig(directory/'errors-power.svg', metadata={'Date': None}); plt.close(fig)
    x = np.arange(5); y = np.array([1, 2, 2, 4, 5]); fitted = .8+x
    fig, ax = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    ax[0].scatter(x, y, color='#1676ad', label='teaching observations')
    ax[0].plot(x, fitted, color='#b94b21', label='fit: y=0.8+x')
    ax[0].set(xlabel='x (teaching index)', ylabel='y (percentage points)', title='OLS fit, n=5'); ax[0].legend(fontsize=9)
    ax[1].scatter(fitted, y-fitted, color='#1676ad'); ax[1].axhline(0, color='#777', lw=1)
    ax[1].set(xlabel='fitted y (percentage points)', ylabel='residual (percentage points)', title='Residuals vs fitted values')
    fig.savefig(directory/'regression-diagnostics.svg', metadata={'Date': None}); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures-dir', type=Path, help='explicit output directory for four original SVG figures')
    args = parser.parse_args()
    print(json.dumps(calculations(), ensure_ascii=False, indent=2, allow_nan=False))
    if args.figures_dir is not None:
        figures(args.figures_dir)


if __name__ == '__main__':
    main()
