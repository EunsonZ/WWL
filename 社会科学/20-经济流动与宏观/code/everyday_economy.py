"""Exact arithmetic for four fictional general-education lessons; no tax/product advice.

Import is silent. CLI requires --output to write its JSON; no default write path.
"""
import argparse
import json
from fractions import Fraction as F
from pathlib import Path


def nonnegative_integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("expected a nonnegative integer")
    return F(value)


def pit(income):
    x = nonnegative_integer(income)
    return F(min(max(x - 100, 0), 100)) / 10 + F(max(x - 200, 0)) / 5


def indemnity(loss):
    x = nonnegative_integer(loss)
    return min(max(x - 20, 0), 70)


def tariff(amount):
    t = nonnegative_integer(amount)
    p = min(40 + t, F(60))
    demand, supply = 100 - p, p - 20
    imports = demand - supply
    cs, ps = (100 - p) * demand / 2, (p - 20) * supply / 2
    revenue = t * imports
    return {"price": p, "demand": demand, "supply": supply,
            "imports": imports, "cs": cs, "ps": ps,
            "revenue": revenue, "dwl": 2000 - cs - ps - revenue}


def combined_budget(central_tax, central_service, local_tax, local_service, transfer):
    """Two-level teaching budget; internal transfer cancels in consolidation."""
    values = [nonnegative_integer(x) for x in (central_tax, central_service, local_tax, local_service, transfer)]
    ct, cs, lt, ls, tr = values
    return {"central_balance": ct - cs - tr, "local_balance": lt + tr - ls,
            "combined_tax": ct + lt, "combined_services": cs + ls,
            "combined_deficit": cs + ls - ct - lt}


def nonnegative_amount(value):
    """Exact teaching amounts: int/Fraction only; no implicit float rounding."""
    if isinstance(value, bool) or not isinstance(value, (int, F)) or value < 0:
        raise ValueError("expected a nonnegative int or Fraction")
    return F(value)


def unit_share(value):
    value = nonnegative_amount(value)
    if value > 1:
        raise ValueError("share must be in [0, 1]")
    return value


def import_payment(amount, opening_deposit, *, trade_credit=False):
    """One delivered import: payment from existing foreign deposit or new credit."""
    if not isinstance(trade_credit, bool):
        raise ValueError("trade_credit must be bool")
    a, d = nonnegative_amount(amount), nonnegative_amount(opening_deposit)
    if not trade_credit and d < a:
        raise ValueError("opening foreign deposit is insufficient")
    return {"china_CA": -a, "china_FA": -a, "foreign_CA": a, "foreign_FA": a,
            "deposit_change": F(0) if trade_credit else -a,
            "new_trade_credit": a if trade_credit else F(0),
            "closing_deposit": d if trade_credit else d - a,
            "foreign_deposit_liability_change": F(0) if trade_credit else -a,
            "foreign_trade_credit_asset_change": a if trade_credit else F(0)}


def two_period_transfer(transfer, c, m):
    """Two teaching periods, fixed prices/new production and next-period spending.

    Imports use the explicit trade-credit branch of import_payment, not deposit
    depletion; banks lend transfer to government at t1 only. No taxes/interest.
    private_saving is CURRENT disposable income minus CURRENT consumption,
    not the unspent portion of the lagged income used to decide consumption.
    """
    t, c, m = nonnegative_amount(transfer), unit_share(c), unit_share(m)
    spending_base = t
    rows = []
    for period in (1, 2):
        consumption = c * spending_base
        imports = m * consumption
        domestic = consumption - imports
        current_transfer = t if period == 1 else F(0)
        current_income = domestic + current_transfer
        rows.append({"period": period, "spending_base": spending_base,
                     "current_disposable_income": current_income,
                     "consumption": consumption, "imports": imports,
                     "domestic_output": domestic,
                     "unspent_spending_base": spending_base - consumption,
                     "private_saving": current_income - consumption,
                     "government_net_lending": -current_transfer,
                     "new_bank_loan_to_government": current_transfer,
                     "foreign_net_lending": imports,
                     "import_accounts": import_payment(imports, 0, trade_credit=True)})
        spending_base = domestic
    return rows


def examples():
    sales = [F(100), F(160), F(200)]
    output = [x / 10 for x in sales]
    credits = [F(0), output[0], output[1]]
    net = [a - b for a, b in zip(output, credits)]
    return {"vat": {"output": output, "credit": credits, "net": net,
                    "total": sum(net), "consumer": F(220)},
            "pit": {str(x): pit(x) for x in (180, 220, 250, 260)},
            "budget": combined_budget(80, 50, 20, 60, 30),
            "budget_transfer_40": combined_budget(80, 50, 20, 60, 40),
            "import_payment_100": import_payment(100, 100),
            "import_payment_120": import_payment(120, 120),
            "import_credit_120": import_payment(120, 0, trade_credit=True),
            "two_period": {"c08_m0": two_period_transfer(10, F(4, 5), 0),
                           "c02_m0": two_period_transfer(10, F(1, 5), 0),
                           "c08_m025": two_period_transfer(10, F(4, 5), F(1, 4)),
                           "c02_m025": two_period_transfer(10, F(1, 5), F(1, 4))},
            "finance": {"pv": F(105) / F(105, 100),
                        "real_return": F(105, 103) - 1,
                        "expected_terminal": F(99, 100) * 104,
                        "claim_50": indemnity(50), "claim_100": indemnity(100),
                        "claim_200": indemnity(200), "expected_claim": F(7)},
            "trade": {"production_cloth": F(4), "production_wine": F(6),
                      "H_consumption": [F(2), F(3, 2)],
                      "F_consumption": [F(2), F(9, 2)],
                      "H_va": F(140), "F_va": F(60), "world_va": F(200)},
            "tariff": {str(x): tariff(x) for x in (0, 5, 10, 20, 30)},
            "fx": {"E_old": F(7), "E_new": F(77, 10),
                   "inverse_change": F(10, 11) - 1,
                   "forward": F(7) * F(104, 102),
                   "china_CA": F(-100), "china_FA": F(-100),
                   "foreign_CA": F(100), "foreign_FA": F(100),
                   "reserve_example_CA": F(30),
                   "reserve_example_FA": F(10) + 25 - 5}}


def encode(value):
    if isinstance(value, (F, int)) and not isinstance(value, bool):
        value = F(value)
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [encode(x) for x in value]
    raise TypeError("unexpected output type")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(encode(examples()), ensure_ascii=False,
                                      indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
