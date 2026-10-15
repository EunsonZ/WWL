"""Reproducible synthetic equity-market and valuation teaching case.

Amounts are millions of currency unless explicitly stated per share.  The module
uses only the Python standard library, no live prices, and makes no recommendation.
"""
from fractions import Fraction
from html import escape
from math import isfinite
from pathlib import Path
import json


def number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: finite numeric value required") from exc
    if not isfinite(result):
        raise ValueError(f"{name}: finite numeric value required")
    return result


def q(value, name):
    number(value, name)
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name}: rational input required") from exc


def execution_cost(bid, ask, execution, shares, commission, decision_price):
    """Buy-order costs relative to the contemporaneous midpoint and decision price.

    Prices are currency/share, shares is a positive integer, commission is currency.
    Effective spread is the conventional round-trip measure per share.
    """
    b, a, x, fee, decision = [q(v, n) for v, n in zip(
        (bid, ask, execution, commission, decision_price),
        ("bid", "ask", "execution", "commission", "decision price"))]
    if isinstance(shares, bool) or not isinstance(shares, int) or shares <= 0:
        raise ValueError("shares must be a positive integer")
    if b <= 0 or a <= 0 or x <= 0 or decision <= 0 or b > a or fee < 0:
        raise ValueError("positive prices, bid <= ask, and nonnegative commission required")
    midpoint = (b + a) / 2
    implicit_midpoint_cost = (x - midpoint) * shares
    decision_shortfall = (x - decision) * shares + fee
    return {
        "midpoint": midpoint,
        "quoted_spread": a - b,
        "effective_spread_per_share": 2 * (x - midpoint),
        "implicit_midpoint_cost": implicit_midpoint_cost,
        "commission": fee,
        "total_midpoint_cost": implicit_midpoint_cost + fee,
        "decision_shortfall": decision_shortfall,
        "decision_shortfall_bps": decision_shortfall / (decision * shares) * 10_000,
        "cash_outflow": x * shares + fee,
    }


def index_case():
    """Three-stock price/equal/capitalization weighted price and total returns."""
    names = ("星桥", "河谷", "远岚")
    prices0 = tuple(map(Fraction, (60, 30, 10)))
    shares0 = tuple(map(Fraction, (10, 20, 50)))  # million shares
    split = tuple(map(Fraction, (2, 1, 1)))
    reference = tuple(p / f for p, f in zip(prices0, split))
    shares1 = tuple(s * f for s, f in zip(shares0, split))
    prices1 = tuple(map(Fraction, (33, 27, 11)))
    dividends1 = (Fraction("0.5"), Fraction(0), Fraction("0.2"))

    price_returns = tuple(p1 / ref - 1 for p1, ref in zip(prices1, reference))
    total_returns = tuple((p1 + d) / ref - 1 for p1, d, ref in zip(prices1, dividends1, reference))
    initial_index = Fraction(100)
    divisor0 = sum(prices0) / initial_index
    divisor1 = sum(reference) / initial_index
    price_weight_value1 = sum(prices1) / divisor1
    price_weight_return = price_weight_value1 / initial_index - 1
    price_weight_total_return = (sum(prices1) + sum(dividends1)) / divisor1 / initial_index - 1
    equal_price_return = sum(price_returns) / len(names)
    equal_total_return = sum(total_returns) / len(names)
    caps0 = tuple(p * s for p, s in zip(prices0, shares0))
    caps1 = tuple(p * s for p, s in zip(prices1, shares1))
    distributions = tuple(d * s for d, s in zip(dividends1, shares1))
    cap_price_return = sum(caps1) / sum(caps0) - 1
    cap_total_return = (sum(caps1) + sum(distributions)) / sum(caps0) - 1
    return {
        "names": names,
        "prices0": prices0,
        "reference_after_split": reference,
        "prices1": prices1,
        "shares0_m": shares0,
        "shares1_m": shares1,
        "dividends1": dividends1,
        "price_returns": price_returns,
        "total_returns": total_returns,
        "divisor0": divisor0,
        "divisor1": divisor1,
        "price_weight_value1": price_weight_value1,
        "price_weight_return": price_weight_return,
        "price_weight_total_return": price_weight_total_return,
        "equal_price_return": equal_price_return,
        "equal_total_return": equal_total_return,
        "cap_price_return": cap_price_return,
        "cap_total_return": cap_total_return,
        "caps0": caps0,
        "caps1": caps1,
        "distributions": distributions,
    }


def company_forecast(industry_units=106, market_share="0.105", price=103,
                     operating_margin="0.07", interest=20, tax_rate="0.25",
                     depreciation=20, capex=30, delta_nwc=8, net_borrowing=3,
                     shares=20):
    """One-year driver forecast; units are million units/currency/million shares."""
    units, share, asp, margin, interest = [q(v, n) for v, n in zip(
        (industry_units, market_share, price, operating_margin, interest),
        ("industry units", "market share", "price", "operating margin", "interest"))]
    tax, dep, investment, nwc, borrowing, count = [q(v, n) for v, n in zip(
        (tax_rate, depreciation, capex, delta_nwc, net_borrowing, shares),
        ("tax rate", "depreciation", "capex", "delta NWC", "net borrowing", "shares"))]
    if units <= 0 or not 0 <= share <= 1 or asp <= 0 or not -1 <= margin <= 1:
        raise ValueError("positive units/price, 0 <= share <= 1, and valid margin required")
    if not 0 <= tax < 1 or dep < 0 or investment < 0 or count <= 0:
        raise ValueError("0 <= tax < 1, nonnegative D&A/capex, and positive shares required")
    company_units = units * share
    revenue = company_units * asp
    ebit = revenue * margin
    pretax = ebit - interest
    tax_expense = max(pretax, Fraction(0)) * tax  # case assumption: no loss tax benefit
    net_income = pretax - tax_expense
    fcfe = net_income + dep - investment - nwc + borrowing
    return {
        "company_units": company_units,
        "revenue": revenue,
        "ebit": ebit,
        "pretax_income": pretax,
        "tax_expense": tax_expense,
        "net_income": net_income,
        "eps": net_income / count,
        "fcfe": fcfe,
        "fcfe_per_share": fcfe / count,
        "shares_m": count,
    }


def two_stage_ddm(dividend1, dividend2, required_return, stable_growth):
    """Two explicit annual dividends; terminal value at t=2 starts with D3."""
    d1, d2, r, g = [q(v, n) for v, n in zip(
        (dividend1, dividend2, required_return, stable_growth),
        ("D1", "D2", "required return", "stable growth"))]
    if d1 < 0 or d2 < 0 or r <= g or r <= -1 or g <= -1:
        raise ValueError("nonnegative dividends and required return > growth > -1 required")
    d3 = d2 * (1 + g)
    terminal2 = d3 / (r - g)
    value0 = d1 / (1 + r) + (d2 + terminal2) / (1 + r) ** 2
    return {"d3": d3, "terminal2": terminal2, "value0": value0}


def preferred_value(dividend, required_return):
    """Non-callable, non-convertible perpetual preferred share."""
    d, r = q(dividend, "preferred dividend"), q(required_return, "required return")
    if d < 0 or r <= 0:
        raise ValueError("nonnegative dividend and positive required return required")
    return d / r


def pe_values(eps, peer_pe, nonrecurring_gain_per_share=0):
    """P/E values; positive normalized EPS is required for the usual meaning."""
    e, pe, gain = [q(v, n) for v, n in zip(
        (eps, peer_pe, nonrecurring_gain_per_share),
        ("EPS", "P/E", "gain/share"))]
    if e <= 0 or pe <= 0:
        raise ValueError("positive EPS and P/E required")
    return {
        "normalized_pe_value": e * pe,
        "reported_pe_value": (e + gain) * pe,
    }


def ps_value(revenue, shares, peer_ps):
    """P/S value; it remains computable when the same company has negative EPS."""
    sales, count, ps = [q(v, n) for v, n in zip(
        (revenue, shares, peer_ps), ("revenue", "shares", "P/S"))]
    if sales < 0 or count <= 0 or ps <= 0:
        raise ValueError("nonnegative revenue and positive shares/P/S required")
    return sales / count * ps


def relative_values(eps, revenue, shares, peer_pe, peer_ps,
                    nonrecurring_gain_per_share=0):
    """Convenience wrapper for the demo; each multiple keeps its own domain."""
    values = pe_values(eps, peer_pe, nonrecurring_gain_per_share)
    values["ps_value"] = ps_value(revenue, shares, peer_ps)
    return values


def abnormal_return(actual, expected):
    return q(actual, "actual return") - q(expected, "expected return")


def demo():
    trade = execution_cost("32.90", "33.10", "33.10", 1000, 20, "32.95")
    indexes = index_case()
    forecast = company_forecast()
    ddm = two_stage_ddm("1.50", "1.65", "0.10", "0.04")
    ddm_low_discount = two_stage_ddm("1.50", "1.65", "0.09", "0.04")
    relatives = relative_values(forecast["eps"], forecast["revenue"], 20, 14, "0.55", "0.40")
    return {
        "trade": trade,
        "indexes": indexes,
        "forecast": forecast,
        "ddm": ddm,
        "ddm_9pct": ddm_low_discount,
        "preferred": preferred_value("2.40", "0.08"),
        "relative": relatives,
        "abnormal_market_model": abnormal_return("0.04", "0.01"),
        "abnormal_industry_model": abnormal_return("0.04", "0.015"),
    }


def fmt(value, digits=4):
    return f"{float(value):.{digits}f}"


def svg_document(title, blocks, footer, width=1120, height=470):
    colors = ("#eaf2fb", "#f6efe5", "#e7f4ec", "#f4ebf7")
    block_width = 250
    gap = 24
    y, h = 120, 235
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
        '<style>.title{font:700 29px -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#152033}.head{font:700 20px -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#152033}.body{font:16px -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#243047}.small{font:14px -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",sans-serif;fill:#3f4d63}.line{stroke:#52677f;stroke-width:2;fill:none}</style>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="38" y="50" class="title">{escape(title)}</text>',
    ]
    for i, (head, lines) in enumerate(blocks):
        x = 38 + i * (block_width + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{block_width}" height="{h}" rx="15" fill="{colors[i % len(colors)]}" stroke="#49647d" stroke-width="2"/>')
        parts.append(f'<text x="{x+18}" y="{y+40}" class="head">{escape(head)}</text>')
        for j, line in enumerate(lines):
            parts.append(f'<text x="{x+18}" y="{y+82+j*36}" class="body">{escape(line)}</text>')
        if i < len(blocks) - 1:
            x2 = x + block_width
            parts.append(f'<path d="M{x2+4} {y+118} L{x2+gap-4} {y+118}" class="line"/>')
            parts.append(f'<path d="M{x2+gap-10} {y+112} L{x2+gap-4} {y+118} L{x2+gap-10} {y+124}" class="line"/>')
    parts.append(f'<text x="38" y="420" class="small">{escape(footer)}</text>')
    parts.append('</svg>\n')
    return ''.join(parts)


def render_svgs(output_dir):
    data = demo()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trade = data["trade"]
    market = svg_document(
        "同一买单：决定价格、报价、成交与成本必须分层",
        [
            ("决策时点", ["基准价 32.95/股", "买入 1,000 股", "基准名义 32,950"]),
            ("盘口报价", ["bid 32.90", "ask 33.10", "中点 33.00"]),
            ("实际成交", ["市场买单 33.10", "佣金 20", f"现金流出 {fmt(trade['cash_outflow'], 0)}"]),
            ("成本解释", [f"相对中点 {fmt(trade['total_midpoint_cost'], 0)}", f"决策短缺 {fmt(trade['decision_shortfall'], 0)}", f"约 {fmt(trade['decision_shortfall_bps'], 1)} bp"]),
        ],
        "市场单重成交、不锁价格；限价单锁最差价格、不保证成交。成本不等于发行人的价值变化。",
    )
    indexes = data["indexes"]
    index_svg = svg_document(
        "同三只股票，不同加权方法回答不同问题",
        [
            ("拆股校正", ["A: 60 → 30（2拆1）", "指数基点 100", f"除数 1 → {fmt(indexes['divisor1'], 1)}"]),
            ("收盘价格回报", ["A +10%", "B −10%", "C +10%"]),
            ("三种价格指数", [f"价格加权 {fmt(indexes['price_weight_return']*100, 4)}%", f"等权 {fmt(indexes['equal_price_return']*100, 4)}%", f"市值加权 {fmt(indexes['cap_price_return']*100, 4)}%"]),
            ("市值总回报", ["股息总额 20 百万", f"价格回报 {fmt(indexes['cap_price_return']*100, 4)}%", f"总回报 {fmt(indexes['cap_total_return']*100, 4)}%"]),
        ],
        "除数只中和拆股等非市场价值事件；权重、样本、自由流通调整和再平衡仍会改变指数暴露。",
    )
    forecast = data["forecast"]
    valuation = svg_document(
        "行业假设先变成经营预测，再变成权益现金流与估值",
        [
            ("行业与份额", ["行业 106 百万件", "份额 10.5%", "售价 103/件"]),
            ("公司预测", [f"收入 {fmt(forecast['revenue'], 2)}", "经营利润率 7%", f"净利润 {fmt(forecast['net_income'], 2)}"]),
            ("权益现金流", ["D&A 20 / Capex 30", "ΔNWC 8 / 净借款 3", f"FCFE {fmt(forecast['fcfe'], 2)}"]),
            ("每股条件估值", [f"DDM {fmt(data['ddm']['value0'], 2)}", f"同业P/E {fmt(data['relative']['normalized_pe_value'], 2)}", "观察价格 33.00"]),
        ],
        "模型差异来自现金流代表性、同行可比性、增长和折现率；多个数字不能机械平均成推荐。",
    )
    files = {
        "market-order-cost.svg": market,
        "index-weighting-bridge.svg": index_svg,
        "forecast-valuation-bridge.svg": valuation,
    }
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    return files


def jsonable(value):
    if isinstance(value, Fraction):
        return {"fraction": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    return value


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    render_svgs(root / "assets")
    print(json.dumps(jsonable(demo()), ensure_ascii=False, indent=2))
