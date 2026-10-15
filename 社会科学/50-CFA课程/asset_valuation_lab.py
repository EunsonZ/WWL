"""Original teaching models: annual bond, linear zero curve, contract cash flows, fund fees.
No live prices, calendar conventions, counterparty adjustment, or real LPA engine.
"""
from bisect import bisect_right
from fractions import Fraction
from math import exp, fsum, isfinite, sqrt
from pathlib import Path
import argparse
import json


def finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: finite numeric input required") from exc
    if not isfinite(number):
        raise ValueError(f"{name}: finite numeric input required")
    return number


def flows(times, amounts):
    ts = tuple(finite(t, "time") for t in times)
    cs = tuple(finite(c, "cash flow") for c in amounts)
    if not ts or len(ts) != len(cs):
        raise ValueError("nonempty equal-length time/cash-flow vectors required")
    if any(t <= 0 for t in ts) or any(b <= a for a, b in zip(ts, ts[1:])):
        raise ValueError("strictly increasing positive times required")
    if any(c < 0 for c in cs) or not any(c > 0 for c in cs):
        raise ValueError("nonnegative cash flows with positive total required")
    return ts, cs


def safe(value):
    if not isfinite(value):
        raise ValueError("numerical overflow/underflow outside teaching range")
    return value


def safe_sum(values):
    try:
        return safe(fsum(values))
    except OverflowError as exc:
        raise ValueError("numerical sum exceeded range") from exc


def bond_metrics(times, amounts, annual_yield):
    ts, cs = flows(times, amounts)
    y = finite(annual_yield, "annual effective yield")
    if y <= -1:
        raise ValueError("annual effective yield must exceed -1")
    try:
        pvs = [safe(c / (1 + y)**t) for t, c in zip(ts, cs)]
        price = safe(fsum(pvs))
        if price <= 0:
            raise ValueError("positive price required")
        duration = safe(fsum(t * p / (1+y) for t, p in zip(ts, pvs)) / price)
        convexity = safe(fsum(t*(t+1)*p / (1+y)**2 for t, p in zip(ts, pvs)) / price)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("numerical range exceeded") from exc
    return price, duration, convexity


def curve_price_and_krd(times, amounts, nodes, zero_rates):
    """Continuous annual zero rates, linear interpolation, no extrapolation.
    Returns exact price and analytic sensitivities -dP/dz_j/P in years.
    """
    ts, cs = flows(times, amounts)
    ns = tuple(finite(n, "node") for n in nodes)
    zs = tuple(finite(z, "zero rate") for z in zero_rates)
    if len(ns) < 2 or len(ns) != len(zs):
        raise ValueError("at least two matching nodes/rates required")
    if ns[0] <= 0 or any(b <= a for a,b in zip(ns, ns[1:])):
        raise ValueError("strictly increasing positive nodes required")
    if ts[0] < ns[0] or ts[-1] > ns[-1]:
        raise ValueError("cash flows must lie inside node coverage")
    pvs, weights = [], []
    for t, c in zip(ts, cs):
        j = min(bisect_right(ns, t)-1, len(ns)-2)
        a = (t-ns[j])/(ns[j+1]-ns[j])
        w = [0.0] * len(ns)
        w[j], w[j+1] = 1-a, a
        z = safe_sum(wi*zi for wi,zi in zip(w,zs))
        try:
            pvs.append(safe(c*exp(-z*t)))
        except OverflowError as exc:
            raise ValueError("numerical range exceeded") from exc
        weights.append(w)
    p = safe_sum(pvs)
    if p <= 0:
        raise ValueError("positive price required")
    k = [safe(safe_sum(t*pv*w[j] for t,pv,w in zip(ts,pvs,weights))/p)
         for j in range(len(ns))]
    return p, k


def forward_value(spot, delivery, annual_rate, remaining, quantity=1):
    """No income stock. Prices in currency/share; signed quantity in shares."""
    s, k, r, tau, q = [finite(v,n) for v,n in zip(
        (spot,delivery,annual_rate,remaining,quantity),
        ("spot","delivery","rate","remaining years","quantity"))]
    if s <= 0 or k <= 0 or r <= -1 or tau < 0:
        raise ValueError("positive spot/delivery, rate > -1, remaining >= 0 required")
    try:
        factor = (1+r)**tau
        fair = safe(s*factor)
        value = safe(q*(s-k/factor))
    except (OverflowError,ZeroDivisionError) as exc:
        raise ValueError("numerical range exceeded") from exc
    return fair, value


def futures_variation(settlements, multiplier, contracts=1):
    fs = tuple(finite(f,"settlement") for f in settlements)
    m, n = finite(multiplier,"multiplier"), finite(contracts,"contracts")
    if len(fs) < 2 or m <= 0 or not n.is_integer():
        raise ValueError("two prices, positive multiplier, integer signed contracts required")
    # Negative settlement prices are possible for some futures; no positivity rule.
    return [safe(n*m*(b-a)) for a,b in zip(fs,fs[1:])]


def call_payoff(terminal, strike):
    s, k = finite(terminal,"terminal stock"), finite(strike,"strike")
    if s < 0 or k <= 0:
        raise ValueError("nonnegative stock and positive strike required")
    return max(s-k,0)


def rational(value, name):
    finite(value,name)
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name}: rational numeric input required") from exc


def waterfall(capital, proceeds, years=2, hurdle="0.08", carry="0.20", catch_up=False):
    """One initial investment, terminal liquidation only; exact rational ledger.
    All capital returned first, compound preferred return, optional 100% GP catch-up.
    Fees are paid separately and are NOT returnable/preferred capital in this model.
    """
    c, v, h, a = [rational(x,n) for x,n in zip(
        (capital,proceeds,hurdle,carry),("capital","proceeds","hurdle","carry"))]
    if isinstance(years,bool) or not isinstance(years,int) or not 1 <= years <= 100:
        raise ValueError("years must be integer from 1 to 100")
    if not isinstance(catch_up,bool) or c <= 0 or v < 0 or h < 0 or not 0 <= a < 1:
        raise ValueError("capital > 0, proceeds/hurdle >= 0, 0 <= carry < 1 required")
    returned = min(c,v)
    remaining = v-returned
    preference = min(remaining,c*((1+h)**years-1))
    remaining -= preference
    catch = min(remaining, a*preference/(1-a)) if catch_up else Fraction(0)
    remaining -= catch
    gp = catch+a*remaining
    lp_residual = (1-a)*remaining
    return dict(returned=returned, preference=preference, catch_up=catch,
                lp_residual=lp_residual, lp=returned+preference+lp_residual, gp=gp)


def two_year_irr(initial, year_one_outflow, terminal_inflow):
    """Unique IRR for (-initial, -year_one_outflow, +terminal_inflow).
    Positive root of initial*(1+r)^2 + year_one_outflow*(1+r) = terminal.
    """
    c, f, v = [finite(x,n) for x,n in zip(
        (initial,year_one_outflow,terminal_inflow),("initial","year1 fee","terminal"))]
    if c <= 0 or f < 0 or v <= 0:
        raise ValueError("positive initial/terminal and nonnegative year1 fee required")
    # Stable positive quadratic root; moderate finite arithmetic checked explicitly.
    discriminant = safe(f*f+4*c*v)
    denominator = sqrt(discriminant)+f
    if denominator <= 0:
        raise ValueError("IRR root below floating-point range")
    r = safe(2*v/denominator-1)
    if r <= -1:
        raise ValueError("IRR root below floating-point resolution")
    return r


def demo():
    p,d,c = bond_metrics([1,2],[5,105],0.05)
    rows=[]
    for shock in [-0.02,-0.01,0.01,0.02]:
        exact=bond_metrics([1,2],[5,105],0.05+shock)[0]
        rows.append(dict(shock=shock, exact=exact, duration=p*(1-d*shock),
                         second_order=p*(1-d*shock+0.5*c*shock**2)))
    cp,krd=curve_price_and_krd([1,2],[5,105],[1,1.5,2],[0.05]*3)
    twisted=curve_price_and_krd([1,2],[5,105],[1,1.5,2],[0.06,0.05,0.04])[0]
    fair,value=forward_value(110,105,0.04,0.5)
    hard=waterfall(100,150)
    catch=waterfall(100,150,catch_up=True)
    # Management fee 2% of commitment 120 in year 1; 2% of invested 100 in year 2.
    f1,f2=Fraction("2.4"),Fraction(2)
    net=hard['lp']-f2
    return dict(bond=dict(price=p,duration=d,convexity=c,shocks=rows),
                curve=dict(price=cp,krd=krd,twist_price=twisted,
                           twist_linear=cp*(1-sum(k*s for k,s in zip(krd,[.01,0,-.01])))),
                forward=dict(fair=fair,long_value=value,short_value=-value),
                futures=futures_variation([105,108,103,110],10,2),
                fund=dict(hard=hard,catch=catch,fee1=f1,fee2=f2,
                          paid_in=100+f1+f2,net_distribution=hard['lp'],
                          net_multiple=hard['lp']/(100+f1+f2),
                          irr=two_year_irr(100,float(f1),float(net))))


def plots(directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.hashsalt':'wwl-assets-v1','font.size':10})
    directory.mkdir(parents=True,exist_ok=True)
    p,d,c=bond_metrics([1,2],[5,105],.05)
    ys=[.01+i*.0005 for i in range(161)]
    fig,ax=plt.subplots(figsize=(8,4.5))
    ax.plot([100*y for y in ys],[bond_metrics([1,2],[5,105],y)[0] for y in ys],label='Exact repricing')
    ax.plot([100*y for y in ys],[p*(1-d*(y-.05)) for y in ys],label='Duration only')
    ax.plot([100*y for y in ys],[p*(1-d*(y-.05)+.5*c*(y-.05)**2) for y in ys],label='Duration + convexity')
    ax.set(xlabel='Annual effective yield (%)',ylabel='Price (currency per 100 face)',
           title='Fixed cash flows 5 at year 1, 105 at year 2; local approximations at 5%')
    ax.legend();ax.grid(alpha=.25);fig.tight_layout()
    path=directory/'asset-bond-convexity.svg'
    fig.savefig(path,metadata={'Date':None});plt.close(fig)
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()).rstrip('\n') + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plots',action='store_true')
    args=parser.parse_args()
    print(json.dumps(demo(),default=str,ensure_ascii=False,indent=2))
    if args.plots:
        plots(Path(__file__).parent/'assets')
