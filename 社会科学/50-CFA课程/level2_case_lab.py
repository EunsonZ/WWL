"""Original Level II teaching cases; standard library only, no market connection."""
from math import isfinite, sqrt
from random import Random
import json


def number(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x):
        raise ValueError('finite real required')
    return float(x)


def vector(xs):
    try:
        values = tuple(number(x) for x in xs)
    except TypeError as exc:
        raise ValueError('one-dimensional sequence required') from exc
    if not values:
        raise ValueError('nonempty sequence required')
    return values


def ar1(c, phi, last, sigma, horizon):
    """AR(1) forecasts under zero conditional-mean innovations.
    Assumes Var(eps_t | history) = sigma**2 at every date (homoskedastic).
    Marginal variance alone is insufficient; no ARCH variance recursion is fitted.
    """
    c, phi, last, sigma = map(number, (c, phi, last, sigma))
    if abs(phi) >= 1 or sigma < 0 or isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 100:
        raise ValueError('stationary AR(1), nonnegative sigma, horizon 1..100')
    mean = c / (1 - phi)
    forecasts, variances = [], []
    prediction, variance = last, 0.0
    for _ in range(horizon):
        prediction = c + phi * prediction
        variance = sigma * sigma + phi * phi * variance
        if not isfinite(prediction) or not isfinite(variance):
            raise ValueError('numeric range exceeded')
        forecasts.append(prediction)
        variances.append(variance)
    return {'mean': mean, 'unconditional_variance': sigma**2 / (1-phi**2),
            'forecasts': forecasts, 'conditional_variances': variances}


def rmse(actual, predicted):
    actual, predicted = vector(actual), vector(predicted)
    if len(actual) != len(predicted):
        raise ValueError('equal lengths required')
    value = sqrt(sum((a-p)**2 for a, p in zip(actual, predicted))/len(actual))
    if not isfinite(value):
        raise ValueError('numeric range exceeded')
    return value


def ols(x, y):
    x, y = vector(x), vector(y)
    if len(x) != len(y) or len(x) < 3:
        raise ValueError('equal lengths, n >= 3')
    n = len(x)
    mx, my = sum(x)/n, sum(y)/n
    sxx = sum((z-mx)**2 for z in x)
    syy = sum((z-my)**2 for z in y)
    if sxx == 0 or syy == 0:
        raise ValueError('nonconstant x and y required')
    slope = sum((a-mx)*(b-my) for a, b in zip(x,y))/sxx
    intercept = my-slope*mx
    residuals = [b-intercept-slope*a for a,b in zip(x,y)]
    sse = sum(e*e for e in residuals)
    se = sqrt(sse/(n-2)/sxx)
    if se == 0:
        raise ValueError('zero residual standard error')
    outputs = (slope, intercept, se, 1-sse/syy, slope/se)
    if not all(isfinite(z) for z in outputs):
        raise ValueError('numeric range exceeded')
    return dict(zip(('slope','intercept','slope_se','r2','statistic'),outputs))


def df_no_lag(levels):
    """Intercept-only DF regression; statistic has no ordinary Student-t p value."""
    levels = vector(levels)
    return ols(levels[:-1], [b-a for a,b in zip(levels,levels[1:])])


def spurious_sample():
    """Fixed independent drifted random walks, illustrative single realization."""
    rng = Random(2718)
    x, y = [10.0], [20.0]
    for _ in range(79):
        x.append(x[-1]+0.4+rng.gauss(0,1))
        y.append(y[-1]+0.4+rng.gauss(0,1))
    return x, y


def fcff(ebit, tax, dep, capex, delta_nwc):
    ebit, tax, dep, capex, delta_nwc = map(number,(ebit,tax,dep,capex,delta_nwc))
    if not 0 <= tax <= 1 or dep < 0 or capex < 0:
        raise ValueError('tax in [0,1], nonnegative dep/capex')
    return ebit*(1-tax)+dep-capex-delta_nwc


def dcf(cashflows, rate, terminal_next, growth):
    flows = vector(cashflows)
    rate, terminal_next, growth = map(number,(rate,terminal_next,growth))
    if rate <= -1 or growth <= -1 or rate <= growth or terminal_next < 0:
        raise ValueError('rate > growth > -1; terminal cash nonnegative')
    value = sum(cf/(1+rate)**t for t,cf in enumerate(flows,1)) + terminal_next/(rate-growth)/(1+rate)**len(flows)
    if not isfinite(value):
        raise ValueError('numeric range exceeded')
    return value


def equity_bridge(operating_ev, surplus_cash, associate, debt, lease, minority, preferred):
    values = tuple(map(number,(operating_ev,surplus_cash,associate,debt,lease,minority,preferred)))
    if any(v < 0 for v in values):
        raise ValueError('nonnegative component values required')
    ev,c,a,d,l,m,p = values
    return ev+c+a-d-l-m-p


def bond_tree(rates, coupon=6, face=100, call=None, spread=0):
    """q=1/2 recombining tree, annual effective rates; call after coupon.
    call is mapping {integer date: ex-coupon redemption}; maturity not callable.
    Node value excludes coupon just paid. t0 has no coupon.
    """
    try:
        rows = tuple(vector(row) for row in rates)
    except TypeError as exc:
        raise ValueError('triangular rows required') from exc
    coupon, face, spread = map(number,(coupon,face,spread))
    calls = {} if call is None else dict(call)
    n = len(rows)
    if not n or n > 100 or coupon < 0 or face <= 0:
        raise ValueError('1..100 periods, nonnegative coupon, positive face')
    for t,row in enumerate(rows):
        if len(row) != t+1 or any(r+spread <= -1 for r in row):
            raise ValueError('triangular tree; discount denominator > 0')
    for date, redemption in calls.items():
        if isinstance(date,bool) or not isinstance(date,int) or not 1 <= date < n or number(redemption) <= 0:
            raise ValueError('call dates 1..n-1, positive redemption')
    values = [face]*(n+1)
    levels = [None]*n
    for t in range(n-1,-1,-1):
        values = [(coupon+0.5*values[j]+0.5*values[j+1])/(1+r+spread) for j,r in enumerate(rows[t])]
        if t in calls:
            values = [min(v,calls[t]) for v in values]
        if not all(isfinite(v) for v in values):
            raise ValueError('numeric range exceeded')
        levels[t] = values[:]
    return {'price':values[0], 'ex_coupon_nodes':levels}


def oas(rates, market_price, call, low=0, high=0.2):
    target, low, high = map(number,(market_price,low,high))
    if target <= 0 or low >= high:
        raise ValueError('positive target, ordered bracket')
    if not bond_tree(rates,call=call,spread=low)['price'] >= target >= bond_tree(rates,call=call,spread=high)['price']:
        raise ValueError('target outside price bracket')
    for _ in range(80):
        mid = (low+high)/2
        if bond_tree(rates,call=call,spread=mid)['price'] > target:
            low = mid
        else:
            high = mid
    return (low+high)/2


def credit_zero(default_probs, recoveries, rate, face=100):
    """Conditional risk-neutral default hazards; end-period absolute recovery, absorbs default."""
    probs, recovery = vector(default_probs), vector(recoveries)
    rate, face = map(number,(rate,face))
    if len(probs) != len(recovery) or rate <= -1 or face <= 0 or any(not 0 <= p <= 1 for p in probs) or any(not 0 <= r <= face for r in recovery):
        raise ValueError('matched hazards/recoveries, p in [0,1], recovery in [0,face], rate > -1')
    survival, value = 1.0, 0.0
    for t,(p,r) in enumerate(zip(probs,recovery),1):
        value += survival*p*r/(1+rate)**t
        survival *= 1-p
    n = len(probs)
    value += survival*face/(1+rate)**n
    if not isfinite(value) or value <= 0:
        raise ValueError('positive finite price required for implied yield')
    yield_rate = (face/value)**(1/n)-1
    return {'price':value,'survival':survival,'risk_free_price':face/(1+rate)**n,
            'cva':face/(1+rate)**n-value,'yield':yield_rate,'yield_spread':yield_rate-rate}


def example():
    rates = [[.05],[.08,.04],[.11,.06,.02]]
    x,y = spurious_sample()
    flows = [fcff(132,.25,24,42,18),fcff(145.2,.25,26.4,44.4,19.8)]
    ev = dcf(flows,.09,91.953,.03)
    return {'ar':ar1(.4,.8,3,.3,2), 'ar_rmse':rmse([2.9,2.3,2.5,2.1],[2.8,2.72,2.24,2.4]),
        'randomwalk_rmse':rmse([2.9,2.3,2.5,2.1],[3,2.9,2.3,2.5]),
        'df':df_no_lag([10,11,10,12,13,12,14,15,14]),'spurious':ols(x,y),
        'normalized_fcff':fcff(110,.25,20,35,15),'forecast_fcff':flows,'operating_ev':ev,
        'equity':equity_bridge(ev,80,90,280,40,25,15),'ddm_policy_scenario':dcf([20,25],.12,25.75,.03),
        'straight':bond_tree(rates),'callable':bond_tree(rates,call={1:100,2:100}),
        'oas_to_99':oas(rates,99,{1:100,2:100}), 'credit':credit_zero([.02,.03],[40,40],.05)}


if __name__ == '__main__':
    print(json.dumps(example(),ensure_ascii=False,indent=2))
