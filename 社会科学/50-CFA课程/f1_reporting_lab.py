"""Scalar, annual teaching arithmetic; not a GAAP engine or investment model.
Amounts: ten-thousand currency units; shares: ten-thousand shares; EPS: currency/share.
No participating securities, contingent shares, tax law, stochastic returns or mid-year funding.
"""
from dataclasses import dataclass
from math import isfinite


def number(x, name, minimum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x):
        raise ValueError(name + ' must be a finite number')
    if minimum is not None and x < minimum:
        raise ValueError(name + ' is below its bound')
    return float(x)


def weighted_shares(segments):
    """(restated shares, fraction of year), complete nonoverlapping time segments."""
    if not segments:
        raise ValueError('empty timeline')
    total = duration = 0.0
    for shares, fraction in segments:
        shares = number(shares, 'shares', 0)
        fraction = number(fraction, 'fraction', 0)
        if fraction == 0:
            raise ValueError('zero duration')
        total += shares * fraction
        duration += fraction
    if abs(duration - 1) > 1e-12 or total <= 0:
        raise ValueError('timeline must cover one year with positive shares')
    return total


def treasury_increment(options, strike, average_price, fraction=1):
    options = number(options, 'options', 0)
    strike = number(strike, 'strike', 0)
    average_price = number(average_price, 'average_price', 0)
    fraction = number(fraction, 'fraction', 0)
    if average_price == 0 or not 0 < fraction <= 1:
        raise ValueError('positive average price and fraction in (0,1] required')
    return options * max(0, 1 - strike / average_price) * fraction


@dataclass(frozen=True)
class Potential:
    name: str
    earnings: float
    shares: float


def diluted_eps(earnings, shares, instruments):
    """Control numerator is continuing ordinary profit; all amounts already time weighted.
    This restricted example has no discontinued operations or consequential profit changes.
    Return sorted inclusion decisions, retaining equal-EPS instruments as excluded.
    """
    earnings = number(earnings, 'earnings')
    shares = number(shares, 'shares', 0)
    if shares == 0:
        raise ValueError('zero shares')
    checked = []
    names = set()
    for x in instruments:
        if not x.name or x.name in names:
            raise ValueError('names must be unique')
        names.add(x.name)
        n = number(x.earnings, 'incremental earnings', 0)
        d = number(x.shares, 'incremental shares', 0)
        if d == 0:
            raise ValueError('zero incremental shares; omit before calculation')
        checked.append((n / d, x.name, n, d))
    steps = []
    for ratio, name, n, d in sorted(checked):
        trial = (earnings + n) / (shares + d)
        include = trial < earnings / shares - 1e-12
        if include:
            earnings += n
            shares += d
        steps.append(dict(name=name, increment_eps=ratio, trial=trial,
                          included=include, earnings=earnings, shares=shares))
    return dict(eps=earnings / shares, earnings=earnings, shares=shares, steps=steps)


def lease_schedule(payments, rate):
    """End-year fixed payments, no residual, incentives, costs, reassessment or exemptions."""
    rate = number(rate, 'rate', 0)
    if not payments:
        raise ValueError('empty payments')
    payments = [number(p, 'payment', 0) for p in payments]
    pv = sum(p / (1 + rate) ** (i + 1) for i, p in enumerate(payments))
    if pv == 0:
        raise ValueError('zero lease')
    debt = finance_rou = operating_rou = pv
    straight_cost = sum(payments) / len(payments)
    rows = []
    for year, payment in enumerate(payments, 1):
        interest = debt * rate
        principal = payment - interest
        debt -= principal
        finance_rou -= pv / len(payments)
        operating_rou -= straight_cost - interest
        rows.append(dict(year=year, payment=payment, interest=interest,
                         principal=principal, liability=debt, finance_rou=finance_rou,
                         operating_rou=operating_rou, finance_cost=pv / len(payments) + interest,
                         operating_cost=straight_cost))
    return dict(pv=pv, rows=rows)


def pension_rollforward():
    """Fixed original DB plan, no past-service, settlement, asset ceiling or deferred tax."""
    obligation = 100 + 8 + 5 + 6 - 4
    assets = 80 + 3 + 10 - 4
    profit_cost = 8 + .05 * (100 - 80)
    oci_loss = 6 - (3 - .05 * 80)
    net_liability = obligation - assets
    return dict(obligation=obligation, assets=assets, profit_cost=profit_cost,
                oci_loss=oci_loss, contribution=10, net_liability=net_liability)


def tax_bridge(profit, permanent_add, exempt_income, extra_tax_dep, rate, paid,
               opening_payable=0, opening_dtl=0):
    """Positive profit/taxable-income example; one reversing depreciation difference.
    No loss carryforward, tax credits, rate changes, uncertain tax or OCI tax allocation.
    """
    profit = number(profit, 'profit', 0)
    permanent_add = number(permanent_add, 'permanent_add', 0)
    exempt_income = number(exempt_income, 'exempt_income', 0)
    extra_tax_dep = number(extra_tax_dep, 'extra_tax_dep', 0)
    rate = number(rate, 'rate', 0)
    paid = number(paid, 'paid', 0)
    opening_payable = number(opening_payable, 'opening_payable', 0)
    opening_dtl = number(opening_dtl, 'opening_dtl', 0)
    taxable = profit + permanent_add - exempt_income - extra_tax_dep
    if rate > 1 or profit == 0 or taxable < 0:
        raise ValueError('restricted positive-profit/taxable example; tax rate in [0,1]')
    current = taxable * rate
    deferred = extra_tax_dep * rate
    expense = current + deferred
    return dict(taxable=taxable, current=current, deferred=deferred, expense=expense,
                ending_dtl=opening_dtl + deferred,
                ending_net_payable=opening_payable + current - paid,
                effective=expense / profit, cash_rate=paid / profit)


def disposal(book_value, proceeds, tax_basis, rate):
    """Initial-DTL disposal fragment only: tax basis <= book value; full tax utilization."""
    book_value = number(book_value, 'book_value', 0)
    proceeds = number(proceeds, 'proceeds', 0)
    tax_basis = number(tax_basis, 'tax_basis', 0)
    rate = number(rate, 'rate', 0)
    if rate > 1:
        raise ValueError('rate > 1')
    if tax_basis > book_value:
        raise ValueError('initial-DTL fragment requires tax basis <= book value')
    gain = proceeds - book_value
    current_tax = (proceeds - tax_basis) * rate
    prior_dtl = (book_value - tax_basis) * rate
    total_tax = current_tax - prior_dtl
    return dict(gain=gain, current_tax=current_tax, dtl_reversal=prior_dtl,
                total_tax=total_tax, ni=gain - total_tax,
                net_cash=proceeds - current_tax)


def pro_forma(sales=550, cash_floor=130):
    """Next-year isolated forecast from course10 closing balances. Loans occur year-end;
    existing interest frozen at15, no repayment interest saving during the year.
    Tax paid includes opening4.25; no end tax payable. Minimum cash uses new debt only.
    """
    sales = number(sales, 'sales', 0)
    cash_floor = number(cash_floor, 'cash_floor', 0)
    if sales == 0:
        raise ValueError('positive sales required')
    cogs, cash_opex, dep = .56 * sales, .20 * sales, 44
    ebit = sales - cogs - cash_opex - dep
    profit = ebit - 15
    if profit < 0:
        raise ValueError('negative profit requires a separate tax-loss model')
    tax = .25 * profit
    ni = profit - tax
    ar, inventory, ap = .12 * sales, .16 * sales, .12 * sales
    delta_nwc = (ar - 60) + (inventory - 80) - (ap - 60)
    paid_tax = tax + 4.25
    cfo = ni + dep - delta_nwc - 4.25
    capex, repayment, dividend = 70, 20, 20
    cash_before_funding = 113 + cfo - capex - repayment - dividend
    borrowing = max(0, cash_floor - cash_before_funding)
    cash = cash_before_funding + borrowing
    ppe, debt, equity = 220 + capex - dep, 180 - repayment + borrowing, 228.75 + ni - dividend
    assets = cash + ar + inventory + ppe
    liabilities = ap + debt
    receipts = sales - (ar - 60)
    purchases = cogs + inventory - 80
    supplier_payments = purchases - (ap - 60)
    direct_cfo = receipts - supplier_payments - cash_opex - 15 - paid_tax
    return dict(sales=sales, cogs=cogs, cash_opex=cash_opex, dep=dep, ebit=ebit,
                profit=profit, tax=tax, ni=ni, ar=ar, inventory=inventory, ap=ap,
                delta_nwc=delta_nwc, paid_tax=paid_tax, cfo=cfo, direct_cfo=direct_cfo,
                cfi=-capex, cff=borrowing-repayment-dividend, borrowing=borrowing,
                cash=cash, ppe=ppe, debt=debt, equity=equity, assets=assets,
                liabilities=liabilities, receipts=receipts, supplier_payments=supplier_payments)


def ratio(numerator, denominator):
    numerator = number(numerator, 'numerator')
    denominator = number(denominator, 'denominator', 0)
    if denominator == 0:
        raise ValueError('undefined ratio')
    return numerator / denominator


if __name__ == '__main__':
    import json
    eps = diluted_eps(108, 207.5, [Potential('options', 0, 16), Potential('A', 3, 10),
                                  Potential('convertible preferred', 12, 30), Potential('B', 12, 25)])
    print(json.dumps(dict(eps=eps, lease=lease_schedule([60,55],.1), pension=pension_rollforward(),
                         tax=tax_bridge(65,4,6,20,.25,12),
                         disposal=disposal(30,38,20,.25), forecast=pro_forma()), indent=2))
