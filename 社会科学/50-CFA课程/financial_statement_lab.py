"""澄河制造合成账本；标准库；万元/年。与80课镜像一同交接。"""
from decimal import Decimal, localcontext
from fractions import Fraction
import json


def q(value):
    """禁止float和bool；Decimal必须有限；str使用精确十进制/有理数。"""
    if isinstance(value, (float, bool)):
        raise TypeError("use int, str, Decimal or Fraction, never float/bool")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("amount/rate must be finite")
    if not isinstance(value, (int, str, Decimal, Fraction)):
        raise TypeError("unsupported numeric type")
    return Fraction(value)


def dec(value):
    value = q(value)
    with localcontext() as ctx:
        ctx.prec = 40
        return Decimal(value.numerator) / Decimal(value.denominator)


def ratio(numerator, denominator):
    denominator = q(denominator)
    if denominator == 0:
        raise ValueError("ratio undefined for zero denominator")
    return q(numerator) / denominator


def npv(rate, cashflows):
    rate = q(rate)
    cashflows = tuple(q(v) for v in cashflows)
    if rate <= -1 or not cashflows:
        raise ValueError("require rate > -1 and nonempty cashflows")
    return sum((v / (1 + rate) ** t for t, v in enumerate(cashflows)), q(0))


def nonnegative_conventional_irr(cashflows, steps=160):
    """仅初始负、随后非负且至少一项正，且NPV(0)>=0；返回非负根近似。

    不搜非传统CF的多根，不支持不规则日间隔；固定160次二分不是全域证书。
    """
    cashflows = tuple(q(v) for v in cashflows)
    if (len(cashflows) < 2 or cashflows[0] >= 0
            or any(v < 0 for v in cashflows[1:])
            or not any(v > 0 for v in cashflows[1:])):
        raise ValueError("require conventional cashflow sign pattern")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
        raise ValueError("positive integer bisection steps required")
    at_zero = npv(0, cashflows)
    if at_zero < 0:
        raise ValueError("no nonnegative IRR under this contract")
    if at_zero == 0:
        return Decimal(0)
    low, high = q(0), q(1)
    for _ in range(32):
        if npv(high, cashflows) < 0:
            break
        high = 2 * high + 1
    else:
        raise ValueError("nonnegative root not bracketed within search bound")
    for _ in range(steps):
        mid = (low + high) / 2
        if npv(mid, cashflows) > 0:
            low = mid
        else:
            high = mid
    return dec((low + high) / 2)


def wacc(equity_weight, debt_weight, equity_cost, debt_cost, tax):
    we, wd, re, rd, tax = map(q, (equity_weight, debt_weight,
                                equity_cost, debt_cost, tax))
    if we < 0 or wd < 0 or we + wd != 1:
        raise ValueError("nonnegative market weights must sum exactly to one")
    if re < 0 or rd < 0 or not 0 <= tax <= 1:
        raise ValueError("nonnegative costs and tax in [0,1] required")
    return we * re + wd * rd * (1 - tax)


class Ledger:
    """正为借方、负为贷方；post在写入前验证整笔分录，不允许部分入账。"""
    income_accounts = {"revenue", "cogs", "opex", "depreciation", "interest",
                       "tax_current", "tax_deferred", "impairment"}
    allowed = income_accounts | {"cash", "ar", "inventory", "ppe", "rou",
                                "dta", "ap", "debt", "lease", "tax_balance",
                                "dtl", "contract", "capital", "re"}

    def __init__(self):
        self.b = {k: q(0) for k in self.allowed}
        self.b.update({k: q(v) for k, v in {
            "cash": 100, "ar": 40, "inventory": 60, "ppe": 200,
            "ap": -50, "debt": -150, "capital": -160, "re": -40}.items()})
        self.cf = {k: q(0) for k in ("operating", "investing", "financing")}
        self.journal = []

    def post(self, label, entries, category=None):
        entries = {k: q(v) for k, v in entries.items()}
        if not entries or set(entries) - self.allowed or sum(entries.values()) != 0:
            raise ValueError("journal must use known accounts and balance exactly")
        change = entries.get("cash", q(0))
        if change and category not in self.cf:
            raise ValueError("cash transaction requires CFO/CFI/CFF category")
        if not change and category is not None:
            raise ValueError("noncash entry must not be in cashflow categories")
        for account, amount in entries.items():
            self.b[account] += amount
        if change:
            self.cf[category] += change
        self.journal.append((label, entries, category))
        if sum(self.b.values()) != 0:
            raise ValueError("ledger no longer balances")

    def statements(self):
        ni = -sum(self.b[k] for k in self.income_accounts)
        profit = {"revenue": -self.b["revenue"], "cogs": self.b["cogs"],
                  "ebit": -self.b["revenue"] - sum(self.b[k] for k in
                           ("cogs", "opex", "depreciation", "impairment")),
                  "interest": self.b["interest"],
                  "tax": self.b["tax_current"] + self.b["tax_deferred"],
                  "ni": ni}
        assets = {k: self.b[k] for k in
                  ("cash", "ar", "inventory", "ppe", "rou", "dta")}
        assets["tax_receivable"] = max(self.b["tax_balance"], q(0))
        liabilities = {k: -self.b[k] for k in
                       ("ap", "debt", "lease", "dtl", "contract")}
        liabilities["tax_payable"] = max(-self.b["tax_balance"], q(0))
        equity = {"capital": -self.b["capital"], "retained": -self.b["re"] + ni}
        if any(v < 0 for v in assets.values()) or any(v < 0 for v in liabilities.values()):
            raise ValueError("negative asset/liability outside this synthetic model")
        if sum(assets.values()) != sum(liabilities.values()) + sum(equity.values()):
            raise ValueError("statement does not balance")
        if assets["cash"] != 100 + sum(self.cf.values()):
            raise ValueError("cashflow bridge does not reconcile")
        return {"profit": profit, "assets": assets, "liabilities": liabilities,
                "equity": equity, "cashflows": dict(self.cf),
                "total_assets": sum(assets.values())}


def company(scenario="base", collection=480):
    """仅年度期末非负现金模型，不新增融资/透支；非逐日流动性证明。

    应收可收总额540；期末现金=collection-367，advance多30、lease少60。
    合法collection：通常[367,540]、advance[337,540]、lease[427,540]。
    """
    valid = {"base", "advance", "average", "inventory_write_down",
             "ppe_impairment", "accelerated_tax", "lease"}
    if scenario not in valid:
        raise ValueError("unknown scenario")
    collection = q(collection)
    minimum = 337 if scenario == "advance" else 427 if scenario == "lease" else 367
    if not minimum <= collection <= 540:
        raise ValueError(f"collection must be in [{minimum}, 540] for {scenario}; "
                         "no additional funding or overdraft is modeled")
    b = Ledger()
    b.post("delivered credit sales", {"ar": 500, "revenue": -500})
    b.post("collections", {"cash": collection, "ar": -collection}, "operating")
    b.post("credit purchases", {"inventory": 300, "ap": -300})
    b.post("supplier payments", {"ap": 290, "cash": -290}, "operating")
    b.post("FIFO cost sold", {"cogs": 280, "inventory": -280})
    b.post("cash expenses", {"opex": 100, "cash": -100}, "operating")
    b.post("equipment purchase", {"ppe": 60, "cash": -60}, "investing")
    b.post("depreciation", {"depreciation": 40, "ppe": -40})
    b.post("cash interest", {"interest": 15, "cash": -15}, "operating")
    b.post("current tax expense", {"tax_current": q("16.25"),
                                   "tax_balance": -q("16.25")})
    b.post("tax payment", {"tax_balance": 12, "cash": -12}, "operating")
    b.post("new borrowing", {"cash": 50, "debt": -50}, "financing")
    b.post("principal repayment", {"debt": 20, "cash": -20}, "financing")
    b.post("paid dividend", {"re": 20, "cash": -20}, "financing")
    if scenario == "advance":
        b.post("undelivered advance", {"cash": 30, "contract": -30}, "operating")
    if scenario in {"average", "inventory_write_down", "ppe_impairment"}:
        if scenario == "average":
            loss, asset, expense = q("320/13"), "inventory", "cogs"
        elif scenario == "inventory_write_down":
            loss, asset, expense = q(10), "inventory", "impairment"
        else:
            loss, asset, expense = q(30), "ppe", "impairment"
        b.post("book reduction without current tax deduction", {expense: loss, asset: -loss})
        b.post("recoverable deferred tax asset", {"dta": loss / 4, "tax_deferred": -loss / 4})
    if scenario == "accelerated_tax":
        b.post("current tax reduced by extra tax depreciation", {"tax_current": -5, "tax_balance": 5})
        b.post("future deduction reduced", {"tax_deferred": 5, "dtl": -5})
    if scenario == "lease":
        b.post("noncash lease inception", {"rou": 100, "lease": -100})
        b.post("ROU depreciation", {"depreciation": 50, "rou": -50})
        b.post("lease interest", {"interest": 10, "cash": -10}, "operating")
        b.post("lease principal", {"lease": 50, "cash": -50}, "financing")
        b.post("lease deductions same as book expenses", {"tax_current": -15, "tax_balance": 15})
    return b.statements()


def reject(call):
    try:
        call()
    except (TypeError, ValueError, ZeroDivisionError):
        return
    raise AssertionError("invalid input unexpectedly accepted")


def require(condition, message="regression check failed"):
    """测试断言始终执行，python -O也不移除。"""
    if not condition:
        raise AssertionError(message)


def self_test():
    base = company()
    require(base['profit']['ni'] == q('48.75'), "regression check failed")
    require(base['total_assets'] == 473, "regression check failed")
    require(base['cashflows'] == {'operating': 63, 'investing': -60, 'financing': 10}, "regression check failed")
    require(base['assets']['cash'] == 113, "regression check failed")
    require(base['equity']['retained'] == q('68.75'), "regression check failed")
    indirect = q("48.75") + 40 - 20 - 20 + 10 + q("4.25")
    require(indirect == base['cashflows']['operating'], "regression check failed")
    for scenario, ni, total, cash, cfo in [
        ("advance", "48.75", "503", "143", "93"),
        ("average", "1575/52", "23636/52", "113", "63"),
        ("inventory_write_down", "41.25", "465.5", "113", "63"),
        ("ppe_impairment", "26.25", "450.5", "113", "63"),
        ("accelerated_tax", "48.75", "473.75", "113", "63"),
        ("lease", "3.75", "473.75", "53", "53")]:
        s = company(scenario)
        require(s['profit']['ni'] == q(ni), scenario)
        require(s['total_assets'] == q(total), scenario)
        require(s['assets']['cash'] == q(cash), scenario)
        require(s['cashflows']['operating'] == q(cfo), scenario)
    require(company(collection=470)['assets']['ar'] == 70, "regression check failed")
    require(company(collection=470)['assets']['cash'] == 103, "regression check failed")
    require(company(collection=470)['profit'] == base['profit'], "regression check failed")
    require(npv('0.1', [-100, 230, -132]) == 0, "regression check failed")
    require(npv('0.2', [-100, 230, -132]) == 0, "regression check failed")
    require(npv('0.1', [-1000, 1250]) > npv('0.1', [-100, 130]), "regression check failed")
    require(npv('0.1', [-100, 0, 150]) > npv('0.1', [-100, 125, 0]), "regression check failed")
    require(npv('0.2', [0, -125, 150]) == 0, "regression check failed")
    flows = [-155, q("58.75"), q("58.75"), q("93.75")]
    require(npv('0.1', flows) == q('46315/2662'), "regression check failed")
    irr = nonnegative_conventional_irr(flows)
    require(abs(npv(irr, flows)) < q('0.0000000001'), "regression check failed")
    require(wacc('0.6', '0.4', '0.12', '0.06', '0.25') == q('0.09'), "regression check failed")
    require(wacc('0.6', '0.4', '0.12', '0.06', 0) == q('0.096'), "regression check failed")
    require(1000 + 100 - 180 == 1000 - (180 - 100) == 920, "regression check failed")
    reject(lambda: npv(-1, flows))
    reject(lambda: npv(0, []))
    reject(lambda: q(0.1))
    reject(lambda: q(True))
    reject(lambda: q(Decimal("NaN")))
    reject(lambda: q(Decimal("Infinity")))
    reject(lambda: ratio(1, 0))
    reject(lambda: company("unknown"))
    # Inclusive endpoints and one unit outside each liquidity/receivable boundary.
    for scenario, minimum in (("base", 367), ("advance", 337), ("average", 367),
                              ("inventory_write_down", 367), ("ppe_impairment", 367),
                              ("accelerated_tax", 367), ("lease", 427)):
        low = company(scenario, collection=minimum)
        high = company(scenario, collection=540)
        require(low["assets"]["cash"] == 0, scenario + " lower endpoint")
        require(low["assets"]["ar"] == 540 - minimum, scenario + " lower receivables")
        require(high["assets"]["cash"] == 540 - minimum, scenario + " upper endpoint")
        require(high["assets"]["ar"] == 0, scenario + " upper receivables")
        for bad in (-1, 0, 1, minimum - 1, 541):
            reject(lambda s=scenario, c=bad: company(s, collection=c))
    # Direct Ledger misuse must also reject negative-cash statements under -O.
    unsafe = Ledger()
    unsafe.post("unfunded payment", {"cash": -101, "opex": 101}, "operating")
    reject(unsafe.statements)
    reject(lambda: nonnegative_conventional_irr([-100, 230, -132]))
    reject(lambda: nonnegative_conventional_irr([-100, 90]))
    reject(lambda: wacc("0.7", "0.4", "0.12", "0.06", "0.25"))
    reject(lambda: wacc("0.6", "0.4", "0.12", "0.06", "1.1"))
    ledger = Ledger()
    initial = ledger.b.copy()
    reject(lambda: ledger.post("bad", {"cash": 10, "debt": -9}, "financing"))
    reject(lambda: ledger.post("unknown", {"cash": 10, "secret": -10}, "financing"))
    reject(lambda: ledger.post("no category", {"cash": 10, "debt": -10}))
    require(ledger.b == initial and ledger.journal == [], "regression check failed")
    return irr


def printable(value):
    if isinstance(value, Fraction):
        return {"exact": str(value), "decimal": str(dec(value))}
    if isinstance(value, dict):
        return {k: printable(v) for k, v in value.items()}
    return value


def main():
    irr = self_test()
    flows = [-155, q("58.75"), q("58.75"), q("93.75")]
    report = {s: company(s) for s in ("base", "advance", "average",
              "inventory_write_down", "ppe_impairment", "accelerated_tax", "lease")}
    report["project"] = {"npv_at_10_percent": npv("0.1", flows), "irr": str(irr)}
    print(json.dumps(printable(report), ensure_ascii=False, indent=2))
    print("PASS: balanced journals, seven scenarios, NPV/IRR/WACC, collection endpoints and invalid-input guards")


if __name__ == "__main__":
    main()
