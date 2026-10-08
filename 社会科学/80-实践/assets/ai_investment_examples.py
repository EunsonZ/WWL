"""Issue #66 的有限教学模型；仅用标准库，不读取行情或外部文件。

金额和比例使用 Fraction。输入均为整数或精确分数，小数只用于输出显示。
同目录绘图脚本复用本模型；公式、定义和原稿定位见金融课程第 09 页。
"""

from fractions import Fraction as F
import json


def npv(initial, cash_flows, terminal, rate):
    """t=0 投入 initial，逐年年末现金，terminal 在最后一年末另收。"""
    if not cash_flows or rate <= -1:
        raise ValueError("需要至少一期现金流，且每期折现率必须大于 -1")
    factor = F(1) + rate
    operating_pv = sum(
        (cash / factor**year for year, cash in enumerate(cash_flows, 1)),
        F(0),
    )
    return -initial + operating_pv + terminal / factor ** len(cash_flows)


def break_even_revenue(fixed, variable_rate):
    """线性年度模型：利润 = (1-variable_rate)*收入 - fixed。"""
    if fixed < 0 or not 0 <= variable_rate < 1:
        raise ValueError("本教学模型要求固定成本非负，且 0 <= 变动成本率 < 1")
    return fixed / (F(1) - variable_rate)


def two_year_scenario(second_price=F(2), utilization=F(4, 5), resale_decline=F(3, 10)):
    """固定技术进步 a=(0.5,0.7)，只改变第 2 年售价、售出率或残值。"""
    if not 0 <= utilization <= 1 or not 0 <= resale_decline <= 1:
        raise ValueError("售出率和年转售价值下降率必须在 [0,1] 内")
    if second_price < 0:
        raise ValueError("本教学情景价格非负")
    initial, reference_capacity, unit_cost, fixed = map(F, (100, 100, 1, 10))
    closure = (F(1, 2), F(7, 10))
    prices = (F(2), second_price)
    sold = tuple(utilization * a * reference_capacity for a in closure)
    cash_flows = tuple((price - unit_cost) * n - fixed for price, n in zip(prices, sold))
    terminal = initial * (1 - resale_decline) ** 2
    return {
        "closure": closure,
        "sold": sold,
        "prices": prices,
        "utilization": utilization,
        "resale_decline": resale_decline,
        "cash_flows": cash_flows,
        "terminal": terminal,
        "npv": npv(initial, cash_flows, terminal, F(1, 10)),
    }


def examples():
    fixed, variable_rate = F(6), F(1, 4)
    threshold = break_even_revenue(fixed, variable_rate)
    total_at_threshold = fixed + variable_rate * threshold
    wrong_threshold = total_at_threshold / (1 - variable_rate)

    # 订单编号 1..70 有终端用途；41..90 有战略动机。41..70 两者都有。
    terminal_use = set(range(1, 71))
    strategic_motive = set(range(41, 91))

    # 同一期间已交付且收现；设备采购是云商的投资，不是其当期全部费用。
    payments = (("家庭", "模型商", 40), ("非AI企业", "模型商", 60),
                ("模型商", "云商", 60), ("云商", "设备商", 30))
    inside = {"模型商", "云商", "设备商"}
    cash_change = {name: F(0) for name in sorted(inside)}
    outside_customer_cash = F(0)
    layered_sales = F(0)
    for payer, payee, amount in payments:
        if payer in inside:
            cash_change[payer] -= amount
        if payee in inside:
            cash_change[payee] += amount
            layered_sales += amount
        if payer not in inside and payee in inside:
            outside_customer_cash += amount

    return {
        "terminal_npv": npv(F(100), (F(0), F(0)), F(121), F(1, 10)),
        "break_even": {
            "revenue": threshold,
            "total_cost": total_at_threshold,
            "profit": threshold - total_at_threshold,
            "double_counted_threshold": wrong_threshold,
            "profit_at_wrong_threshold": (1 - variable_rate) * wrong_threshold - fixed,
        },
        "unit_conversion_only": {
            "input_billion_usd_per_year": F("8.514"),
            "divided_by_half_billion_usd_per_year": F("8.514") / F("0.5"),
            "same_amount_in_hundred_million_usd_per_year": F("8.514") / F("0.5") * 10,
        },
        "demand": {
            "terminal_use": len(terminal_use),
            "strategic_motive": len(strategic_motive),
            "intersection": len(terminal_use & strategic_motive),
            "union": len(terminal_use | strategic_motive),
        },
        "payment_ledger": {
            "payments": payments,
            "cash_change": cash_change,
            "outside_customer_cash": outside_customer_cash,
            "layered_sales": layered_sales,
            "rho_cash_over_gross": outside_customer_cash / layered_sales,
        },
        "scenarios": {
            "A": two_year_scenario(),
            "B": two_year_scenario(second_price=F("1.6")),
            "C": two_year_scenario(utilization=F("0.5")),
            "D": two_year_scenario(resale_decline=F("0.8")),
        },
    }


def _display(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": f"{float(value):.6f}"}
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    print(json.dumps(examples(), ensure_ascii=False, indent=2, default=_display))
