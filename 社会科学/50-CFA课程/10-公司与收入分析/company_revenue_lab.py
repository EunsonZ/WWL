"""Reproducible company, ROIC, and IFRS 15 teaching calculations.

Money is CNY million. Rates are decimals. The functions implement only the
explicit assumptions in the adjacent lessons; they are not accounting, legal,
tax, or investment advice.
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path


def _finite_nonnegative(name, value):
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def allocate_transaction_price(total, standalone_prices):
    """Allocate fixed consideration by relative stand-alone selling prices."""
    _finite_nonnegative("total", total)
    if not standalone_prices:
        raise ValueError("at least one performance obligation is required")
    if any(not isinstance(name, str) or not name for name in standalone_prices):
        raise ValueError("performance obligation names must be non-empty strings")
    if any(not math.isfinite(price) or price <= 0 for price in standalone_prices.values()):
        raise ValueError("stand-alone selling prices must be finite and positive")
    denominator = sum(standalone_prices.values())
    return {name: total * price / denominator
            for name, price in standalone_prices.items()}


def bundle_contract():
    """Contract A: integrated system accepted in 2026, monitoring in 2027."""
    allocation = allocate_transaction_price(
        120.0, {"integrated_system": 120.0, "monitoring": 30.0})
    cash_collected = 60.0
    receivable = 60.0
    revenue = allocation["integrated_system"]
    contract_liability = cash_collected + receivable - revenue
    return {"allocation": allocation, "cash": cash_collected,
            "receivable": receivable, "revenue": revenue,
            "contract_liability": contract_liability,
            "system_cost": 55.0, "gross_profit": revenue - 55.0}


def over_time_contract(price, cost_incurred, expected_cost, billings, cash,
                       customer_controls_asset=True):
    """Contract B: cost-to-cost progress only after an over-time criterion is met."""
    for name, value in (("price", price), ("cost_incurred", cost_incurred),
                        ("expected_cost", expected_cost), ("billings", billings),
                        ("cash", cash)):
        _finite_nonnegative(name, value)
    if expected_cost <= 0 or cost_incurred > expected_cost:
        raise ValueError("expected cost must be positive and not below cost incurred")
    if cash > billings:
        raise ValueError("cash cannot exceed cumulative billings in this teaching case")
    if not customer_controls_asset:
        raise ValueError("the stated over-time criterion is not met")
    progress = cost_incurred / expected_cost
    revenue = price * progress
    receivable = billings - cash
    contract_asset = revenue - billings
    if contract_asset < -1e-12:
        raise ValueError("billings exceed revenue; this case would present a contract liability")
    return {"progress": progress, "revenue": revenue, "cash": cash,
            "receivable": receivable, "contract_asset": max(contract_asset, 0.0),
            "cost": cost_incurred, "gross_profit": revenue - cost_incurred}


def revenue_cash_bridge(cash_collected, delta_receivable, delta_contract_asset,
                        delta_contract_liability):
    """Revenue = cash + increases in AR/contract asset - increase in contract liability."""
    values = (cash_collected, delta_receivable, delta_contract_asset,
              delta_contract_liability)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("bridge inputs must be finite")
    return cash_collected + delta_receivable + delta_contract_asset - delta_contract_liability


def roic(nopat, beginning_invested_capital, ending_invested_capital):
    """Period NOPAT divided by average operating invested capital."""
    for name, value in (("nopat", nopat),
                        ("beginning invested capital", beginning_invested_capital),
                        ("ending invested capital", ending_invested_capital)):
        _finite_nonnegative(name, value)
    average = (beginning_invested_capital + ending_invested_capital) / 2
    if average <= 0:
        raise ValueError("average invested capital must be positive")
    return nopat / average


def reinvestment_growth(nopat, net_reinvestment, next_nopat):
    """Return reinvestment rate, ROIIC, growth, and the exact bridge check."""
    for name, value in (("nopat", nopat), ("net_reinvestment", net_reinvestment),
                        ("next_nopat", next_nopat)):
        _finite_nonnegative(name, value)
    if nopat <= 0 or net_reinvestment <= 0:
        raise ValueError("NOPAT and net reinvestment must be positive")
    delta_nopat = next_nopat - nopat
    reinvestment_rate = net_reinvestment / nopat
    roiic = delta_nopat / net_reinvestment
    growth = delta_nopat / nopat
    return {"reinvestment_rate": reinvestment_rate, "roiic": roiic,
            "growth": growth, "product": reinvestment_rate * roiic}


def economic_profit(nopat, average_invested_capital, capital_charge):
    for name, value in (("nopat", nopat),
                        ("average invested capital", average_invested_capital),
                        ("capital charge", capital_charge)):
        _finite_nonnegative(name, value)
    if average_invested_capital <= 0:
        raise ValueError("average invested capital must be positive")
    return nopat - capital_charge * average_invested_capital


def case_results():
    contract_a = bundle_contract()
    contract_b = over_time_contract(80.0, 18.0, 48.0, 20.0, 10.0)
    aggregate_revenue = contract_a["revenue"] + contract_b["revenue"]
    bridge = revenue_cash_bridge(
        contract_a["cash"] + contract_b["cash"],
        contract_a["receivable"] + contract_b["receivable"],
        contract_b["contract_asset"], contract_a["contract_liability"])
    owned = {"sales": 200.0, "nopat": 30.0, "begin": 140.0, "end": 160.0,
             "next_nopat": 32.5}
    partner = {"sales": 200.0, "nopat": 24.0, "begin": 54.0, "end": 60.0,
               "next_nopat": 26.4}
    for item in (owned, partner):
        item["average"] = (item["begin"] + item["end"]) / 2
        item["roic"] = roic(item["nopat"], item["begin"], item["end"])
        item["growth"] = reinvestment_growth(
            item["nopat"], item["end"] - item["begin"], item["next_nopat"])
        item["economic_profit"] = economic_profit(item["nopat"], item["average"], 0.11)
    bad_increment = {"investment": 20.0, "incremental_nopat": 1.5,
                     "roiic": 1.5 / 20.0, "capital_charge": 0.11,
                     "incremental_economic_profit": 1.5 - 20.0 * 0.11}
    return {"contract_a": contract_a, "contract_b": contract_b,
            "aggregate_revenue": aggregate_revenue, "bridge": bridge,
            "owned": owned, "partner": partner, "bad_increment": bad_increment}


def _svg(path, body, width=1080, height=430):
    style = ('text{font-family:"PingFang SC","Hiragino Sans GB",'
             '"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#172033}'
             '.title{font-size:25px;font-weight:700}.head{font-size:18px;font-weight:700}'
             '.body{font-size:15px}.small{font-size:13px}.line{stroke:#506680;stroke-width:2;fill:none}'
             '.box{fill:#eef4fb;stroke:#2f5d8a;stroke-width:2}.accent{fill:#e9f7ef;stroke:#2b7a4b;stroke-width:2}'
             '.warn{fill:#fff3e8;stroke:#b65d18;stroke-width:2}')
    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'<style>{style}</style>\n<rect width="{width}" height="{height}" fill="#ffffff"/>\n{body}\n</svg>\n',
        encoding="utf-8")


def generate_figures(directory):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    result = case_results()

    body = '<text x="35" y="45" class="title">组织与所有权改变融资路径，也改变投资者能观察到什么</text>'
    columns = [
        (40, '独资 / 普通合伙', '所有者与经营靠得近', '责任、税和存续依本地法', '融资多受个人资源约束', 'warn'),
        (385, '私人有限责任公司', '公司与所有者分离', '股权转让与披露通常受限', '可引入私募债股资本', 'box'),
        (730, '公众有限责任公司', '法律形式不等于已上市', '公开交易时披露/监督增加', '上市证券通常更有流动性', 'accent')]
    for x, title, a, b, c, css in columns:
        body += f'<rect x="{x}" y="105" width="310" height="225" rx="14" class="{css}"/>'
        body += f'<text x="{x+18}" y="145" class="head">{escape(title)}</text>'
        for y, line in ((188, a), (230, b), (272, c)):
            body += f'<text x="{x+18}" y="{y}" class="body">{escape(line)}</text>'
    body += '<path d="M350 215 L375 215" class="line"/><path d="M695 215 L720 215" class="line"/>'
    body += '<text x="40" y="385" class="body">比较顺序：适用法域 → 责任与控制 → 税和披露 → 证券流动性 → 未来资本需求；名称本身不替代合同与法律核对。</text>'
    _svg(out / 'org-capital-map.svg', body)

    owned, partner = result["owned"], result["partner"]
    body = '<text x="35" y="45" class="title">同为收入200：资本占用不同，ROIC与增长桥就不同</text>'
    items = [(65, '自有产能', owned, '#2f5d8a'), (560, '合作网络', partner, '#2b7a4b')]
    for x, label, item, color in items:
        h = item['average'] * 1.25
        body += f'<text x="{x}" y="95" class="head">{label}</text>'
        body += f'<rect x="{x}" y="{325-h:.1f}" width="110" height="{h:.1f}" fill="{color}" opacity=".78"/>'
        body += f'<text x="{x}" y="350" class="body">平均投入资本 {item["average"]:.0f}</text>'
        body += f'<text x="{x+155}" y="145" class="body">NOPAT {item["nopat"]:.1f}</text>'
        body += f'<text x="{x+155}" y="180" class="body">ROIC {item["roic"]*100:.2f}%</text>'
        body += f'<text x="{x+155}" y="215" class="body">净再投资 {item["end"]-item["begin"]:.1f}</text>'
        body += f'<text x="{x+155}" y="250" class="body">ROIIC {item["growth"]["roiic"]*100:.2f}%</text>'
        body += f'<text x="{x+155}" y="285" class="body">下一期增长 {item["growth"]["growth"]*100:.2f}%</text>'
    body += '<text x="65" y="402" class="body">增长恒等桥（本例）：净再投资/NOPAT × ΔNOPAT/净再投资 = ΔNOPAT/NOPAT；它不是永续预测。</text>'
    _svg(out / 'roic-reinvestment-bridge.svg', body)

    a, b = result["contract_a"], result["contract_b"]
    body = '<text x="35" y="45" class="title">同一年两份客户合同：收入126如何与现金70勾稽</text>'
    labels = [('现金收取', 70, 60, 'accent'), ('应收增加', 70, 60, 'box'),
              ('合同资产增加', 10, 20, 'box'), ('合同负债增加', -24, 12, 'warn')]
    x = 50
    for label, value, width_scale, css in labels:
        w = 160 + width_scale
        body += f'<rect x="{x}" y="120" width="{w}" height="105" rx="12" class="{css}"/>'
        body += f'<text x="{x+15}" y="158" class="head">{escape(label)}</text><text x="{x+15}" y="198" class="body">{value:+.0f}</text>'
        x += w + 18
    body += '<text x="50" y="275" class="head">70 + 70 + 10 - 24 = 126</text>'
    body += f'<text x="50" y="315" class="body">合同A：系统收入 {a["revenue"]:.0f}，期末合同负债 {a["contract_liability"]:.0f}；合同B：期间收入 {b["revenue"]:.0f}，期末合同资产 {b["contract_asset"]:.0f}。</text>'
    body += '<text x="50" y="360" class="body">应收是只差时间的无条件权利；合同资产仍取决于合同中的后续条件。三者都要另查减值、退款与可收性。</text>'
    _svg(out / 'revenue-contract-bridge.svg', body)


if __name__ == "__main__":
    generate_figures(Path(__file__).with_name("assets"))
    for key, value in case_results().items():
        print(key, value)
