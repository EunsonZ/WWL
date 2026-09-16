"""Original, deterministic teaching models; no live prices or forecasting.

Run: python -B economics_lab.py [--figures]
All rates are annual simple rates, tau is years. Quotes are price/base units.
"""
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from pathlib import Path
import argparse
import json


def finite(name, value, minimum=None, strict=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real number")
    value = float(value)
    if not isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and (value <= minimum if strict else value < minimum):
        raise ValueError(f"{name} outside model domain")
    return value


def checked(values):
    for key, value in values.items():
        finite(key, value)
    return values


@dataclass(frozen=True)
class QuadraticFirm:
    """TC=F+c*q+k*q**2; H is an additional avoidable operating charge."""
    fixed: float = 100.0
    linear: float = 20.0
    quadratic: float = 1.0
    operating: float = 0.0

    def __post_init__(self):
        for name in ('fixed', 'linear', 'operating'):
            object.__setattr__(self, name, finite(name, getattr(self, name), 0))
        object.__setattr__(self, 'quadratic', finite('quadratic', self.quadratic, 0, True))

    def cost(self, q):
        q = finite('q', q, 0)
        return finite('cost', self.fixed + self.linear*q + self.quadratic*q*q
                      + (self.operating if q > 0 else 0))

    def competitive(self, price, capacity=None):
        p = finite('price', price, 0)
        q = max(0.0, (p-self.linear)/(2*self.quadratic))
        if capacity is not None:
            q = min(q, finite('capacity', capacity, 0))
        gain = finite('incremental surplus', (p-self.linear)*q-self.quadratic*q*q)
        if gain <= self.operating:
            q = 0.0  # Exact ties select shutdown; near ties need a sensitivity check.
        return checked({'q': q, 'price': p, 'profit': p*q-self.cost(q)})

    def monopoly(self, intercept=120.0, slope=2.0, capacity=None):
        a, b = finite('intercept', intercept, 0), finite('slope', slope, 0, True)
        q = max(0.0, (a-self.linear)/(2*(b+self.quadratic)))
        if capacity is not None:
            q = min(q, finite('capacity', capacity, 0))
        gain = finite('incremental surplus', (a-self.linear)*q-(b+self.quadratic)*q*q)
        if gain <= self.operating:
            q = 0.0
        return self.welfare(q, a, b)

    def welfare(self, q, intercept=120.0, slope=2.0):
        q = finite('q', q, 0)
        a, b = finite('intercept', intercept, 0), finite('slope', slope, 0, True)
        if q > a/b:
            raise ValueError('q exceeds the nonnegative-price demand domain')
        p = a-b*q
        cs = b*q*q/2
        profit = p*q-self.cost(q)
        return checked({'q': q, 'price': p, 'profit': profit, 'cs': cs,
                        'ps': profit+self.fixed, 'welfare': cs+profit})


def competitive_benchmark(firm=QuadraticFirm(), intercept=120.0, slope=2.0):
    """Same aggregate technology; efficient/competitive price equals aggregate MC."""
    a, b = finite('intercept', intercept, 0), finite('slope', slope, 0, True)
    q = max(0.0, (a-firm.linear)/(b+2*firm.quadratic))
    if firm.operating:
        raise ValueError('benchmark requires zero extra operating charge')
    return firm.welfare(q, a, b)


def small_country_tariff(world=20.0, tariff=5.0):
    """D=100-2P, S=2P-20; world in [10,30], no export regime.

    Price caps at autarky P=30 when tariff is prohibitive.
    National welfare includes tariff revenue, not foreign quota rents.
    """
    w, t = finite('world', world, 10), finite('tariff', tariff, 0)
    if w > 30:
        raise ValueError('world above autarky price: use an export model')
    p = min(finite('world plus tariff', w+t), 30.0)
    qd, qs = 100-2*p, 2*p-20
    imports = qd-qs
    cs, ps, revenue = (50-p)*qd/2, (p-10)*qs/2, t*imports
    free_cs, free_ps = (50-w)*(100-2*w)/2, (w-10)*(2*w-20)/2
    return checked({'price': p, 'demand': qd, 'supply': qs, 'imports': imports,
                    'cs': cs, 'ps': ps, 'revenue': revenue,
                    'welfare': cs+ps+revenue, 'dwl': free_cs+free_ps-cs-ps-revenue})


def small_country_quota(limit=20.0, domestic_rent_share=1.0, world=20.0):
    """Same small-country curves; quota permits up to limit imports per period."""
    limit = finite('limit', limit, 0)
    share = finite('domestic_rent_share', domestic_rent_share, 0)
    if share > 1:
        raise ValueError('domestic rent share must not exceed one')
    # Free imports at world; excess quota capacity does not force imports.
    free = small_country_tariff(world, 0)
    imports = min(limit, free['imports'])
    p = (120-imports)/4
    result = small_country_tariff(world, p-world)
    rent = (p-world)*imports
    welfare = result['cs']+result['ps']+share*rent
    return checked({'price': p, 'demand': result['demand'], 'supply': result['supply'],
                    'imports': imports, 'cs': result['cs'], 'ps': result['ps'],
                    'rent': rent, 'domestic_rent': share*rent, 'welfare': welfare,
                    'dwl': free['welfare']-welfare})


def opportunity_cost_cloth(cloth_hours, wine_hours):
    """Wine forgone per unit cloth, with one labor input and constant returns."""
    c, w = finite('cloth_hours', cloth_hours, 0, True), finite('wine_hours', wine_hours, 0, True)
    return finite('wine per cloth', c/w, 0, True)


def quote(bid, ask):
    bid, ask = finite('bid', bid, 0, True), finite('ask', ask, 0, True)
    if bid > ask:
        raise ValueError('bid must not exceed ask')
    return bid, ask


def inverse_quote(bid, ask):
    bid, ask = quote(bid, ask)
    return tuple(finite('inverse quote', x, 0, True) for x in (1/ask, 1/bid))


def cross_quote(price_per_middle, middle_per_base):
    """Multiply quotes only after caller has checked matching currency units."""
    pairs = []
    for pair in (price_per_middle, middle_per_base):
        try:
            values = list(pair)
        except TypeError as exc:
            raise ValueError('quote must contain exactly bid and ask') from exc
        if len(values) != 2:
            raise ValueError('quote must contain exactly bid and ask')
        pairs.append(quote(*values))
    x, y = pairs
    return tuple(finite('cross quote', z, 0, True) for z in (x[0]*y[0], x[1]*y[1]))


def accumulation(rate, tau):
    rate, tau = finite('rate', rate), finite('tau', tau, 0)
    return finite('accumulation', 1+rate*tau, 0, True)


def cip_forward(spot, domestic_rate, foreign_rate, tau):
    s = finite('spot', spot, 0, True)
    ad, af = accumulation(domestic_rate, tau), accumulation(foreign_rate, tau)
    return finite('forward', s*ad/af, 0, True)


def cip_bounds(spot_bid, spot_ask, domestic_lend, domestic_borrow,
               foreign_lend, foreign_borrow, tau):
    """No-arbitrage requires forward ask >= lower and bid <= upper."""
    sb, sa = quote(spot_bid, spot_ask)
    dl, db = finite('domestic lend', domestic_lend), finite('domestic borrow', domestic_borrow)
    fl, fb = finite('foreign lend', foreign_lend), finite('foreign borrow', foreign_borrow)
    if dl > db or fl > fb:
        raise ValueError('lending rate cannot exceed borrowing rate in this model')
    lower = sb*accumulation(dl, tau)/accumulation(fb, tau)
    upper = sa*accumulation(db, tau)/accumulation(fl, tau)
    return tuple(finite('bound', x, 0, True) for x in (lower, upper))


def forward_points(spot, forward, point_size=0.0001):
    s, f = finite('spot', spot, 0, True), finite('forward', forward, 0, True)
    h = finite('point_size', point_size, 0, True)
    return finite('points', (f-s)/h)


def ppp_relative(spot, domestic_inflation, foreign_inflation):
    return cip_forward(spot, domestic_inflation, foreign_inflation, 1)


def concentration(shares):
    try:
        xs = [finite('share', x, 0) for x in shares]
    except TypeError as exc:
        raise ValueError('shares must be an iterable of real numbers') from exc
    if not xs or any(x > 1 for x in xs) or abs(sum(xs)-1) > 1e-10:
        raise ValueError('shares must be a nonempty full market summing to one')
    return checked({'cr4': sum(sorted(xs, reverse=True)[:4]),
                    'hhi_fraction': sum(x*x for x in xs),
                    'hhi_10000': 10000*sum(x*x for x in xs)})


def examples():
    firm = QuadraticFirm()
    fwd = cip_forward(1.1, .04, .02, .5)
    return {'competitive': competitive_benchmark(firm), 'monopoly': firm.monopoly(),
            'short_run_loss': firm.competitive(30),
            'cournot_same_technology': firm.welfare(20),
            'tariff': small_country_tariff(), 'free_trade': small_country_tariff(tariff=0),
            'quota_domestic_rents': small_country_quota(),
            'quota_foreign_rents': small_country_quota(domestic_rent_share=0),
            'cloth_opportunity_costs': [opportunity_cost_cloth(2, 4), opportunity_cost_cloth(1, 1)],
            'cross_JPY_per_EUR': cross_quote((149.9, 150.1), (1.099, 1.101)),
            'cip_forward_USD_per_EUR': fwd,
            'forward_points_0.0001': forward_points(1.1, fwd),
            'cip_bid_ask_bounds': cip_bounds(1.099, 1.101, .04, .05, .02, .03, .5),
            'relative_ppp_USD_per_EUR': ppp_relative(1.1, .03, .01),
            'concentration': concentration([.4, .3, .2, .1])}


def figures(directory):
    """Regenerate exactly two deterministic SVGs for the text's examples."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'svg.hashsalt': 'wwl-economics-v1', 'font.family': 'DejaVu Sans',
                         'font.size': 10, 'svg.fonttype': 'none'})
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    q = np.linspace(0, 35, 351)
    qm, qc = 100/6, 25
    fig, ax = plt.subplots(figsize=(7.4, 4.6), layout='constrained')
    ax.plot(q, 120-2*q, label='Demand: P = 120 - 2Q')
    ax.plot(q, 120-4*q, label='MR = 120 - 4Q')
    ax.plot(q, 20+2*q, label='MC = 20 + 2Q')
    lossq = np.linspace(qm, qc, 101)
    ax.fill_between(lossq, 20+2*lossq, 120-2*lossq, alpha=.25, color='red', label='DWL = 138.889 money/period')
    ax.scatter([qm, qc], [120-2*qm, 70], color='black')
    ax.annotate('Monopoly: Q=16.667, P=86.667', (qm, 120-2*qm), xytext=(3, 107),
                arrowprops={'arrowstyle': '->'})
    ax.annotate('Same technology: Q=25, P=70', (qc, 70), xytext=(14, 40),
                arrowprops={'arrowstyle': '->'})
    ax.set(xlim=(0, 35), ylim=(0, 125), xlabel='Q (units/period)', ylabel='Price or marginal value (money/unit)',
           title='Uniform pricing; fixed technology; no externalities')
    ax.legend(loc='lower left', fontsize=8)
    fig.savefig(directory/'economics-market.svg', metadata={'Date': None})
    plt.close(fig)
    qty = np.linspace(0, 85, 341)
    fig, ax = plt.subplots(figsize=(7.4, 4.6), layout='constrained')
    ax.plot(qty, 50-qty/2, label='Demand: P=50-Q/2')
    ax.plot(qty, 10+qty/2, label='Supply: P=10+Q/2')
    ax.axhline(20, color='grey', linestyle='--', label='World price = 20')
    ax.axhline(25, color='black', linestyle=':', label='Tariff price = 25')
    ax.fill_between([20, 30], [20, 25], [20, 20], alpha=.3, color='red', label='Production DWL = 25')
    ax.fill_between([50, 60], [25, 20], [20, 20], alpha=.3, color='orange', label='Consumption DWL = 25')
    ax.fill_between([30, 50], [25, 25], [20, 20], alpha=.2, color='green', label='Tariff revenue = 100')
    ax.set(xlim=(0, 85), ylim=(0, 55), xlabel='Quantity (units/period)', ylabel='Price (money/unit)',
           title='Small importing country; tariff = 5; no externalities')
    ax.legend(fontsize=8, loc='upper right')
    fig.savefig(directory/'economics-tariff.svg', metadata={'Date': None})
    plt.close(fig)
    for path in directory.glob('economics-*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()).rstrip('\n') + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true')
    args = parser.parse_args()
    print(json.dumps(examples(), indent=2, ensure_ascii=False))
    if args.figures:
        figures(Path(__file__).parent/'assets')
