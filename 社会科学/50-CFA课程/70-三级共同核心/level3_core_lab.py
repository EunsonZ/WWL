"""Reproducible numbers and SVGs for the Level III common-core learning chain.

All rates are decimals and all monetary amounts are in millions unless noted.
This is a teaching model, not an optimizer or investment recommendation.
"""
from __future__ import annotations

import math
from pathlib import Path


def portfolio_stats(weights, expected_returns, covariance):
    if len(weights) != len(expected_returns) or len(covariance) != len(weights):
        raise ValueError("dimensions must match")
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-12):
        raise ValueError("weights must sum to one")
    if any(len(row) != len(weights) for row in covariance):
        raise ValueError("covariance must be square")
    mean = sum(w * r for w, r in zip(weights, expected_returns))
    variance = sum(weights[i] * weights[j] * covariance[i][j]
                   for i in range(len(weights)) for j in range(len(weights)))
    if variance < -1e-12:
        raise ValueError("negative variance")
    return mean, math.sqrt(max(variance, 0.0))


def surplus_risk(asset_value, liability_value, asset_duration, liability_duration,
                 yield_change):
    """First-order change in surplus A-L under a parallel rate move."""
    asset_change = -asset_duration * asset_value * yield_change
    liability_change = -liability_duration * liability_value * yield_change
    return asset_change - liability_change


def futures_contracts(value, current_beta, target_beta, contract_price, multiplier):
    exposure = contract_price * multiplier
    if value <= 0 or exposure <= 0:
        raise ValueError("value and futures exposure must be positive")
    return (target_beta - current_beta) * value / exposure


def currency_overlay(local_value, spot_domestic_per_foreign, hedge_ratio,
                     forward_domestic_per_foreign):
    if local_value < 0 or spot_domestic_per_foreign <= 0 or forward_domestic_per_foreign <= 0:
        raise ValueError("invalid currency input")
    if not 0 <= hedge_ratio <= 1:
        raise ValueError("hedge ratio must lie in [0, 1]")
    foreign_notional = hedge_ratio * local_value / spot_domestic_per_foreign
    return foreign_notional, foreign_notional * forward_domestic_per_foreign


def brinson_allocation_selection_interaction(wp, wb, rp, rb):
    if not (len(wp) == len(wb) == len(rp) == len(rb)):
        raise ValueError("dimensions must match")
    if not math.isclose(sum(wp), 1.0, abs_tol=1e-12) or not math.isclose(sum(wb), 1.0, abs_tol=1e-12):
        raise ValueError("weights must sum to one")
    rb_total = sum(w * r for w, r in zip(wb, rb))
    alloc = [(wp[i] - wb[i]) * (rb[i] - rb_total) for i in range(len(wp))]
    select = [wb[i] * (rp[i] - rb[i]) for i in range(len(wp))]
    interact = [(wp[i] - wb[i]) * (rp[i] - rb[i]) for i in range(len(wp))]
    active = sum(w * r for w, r in zip(wp, rp)) - rb_total
    return alloc, select, interact, active


def appraisal_metrics(returns, benchmarks, mar=0.0):
    if len(returns) != len(benchmarks) or len(returns) < 3:
        raise ValueError("equal series with at least three observations required")
    if any(r <= -1 or b <= -1 for r, b in zip(returns, benchmarks)):
        raise ValueError("returns must be greater than -100%")
    mean_r = sum(returns) / len(returns)
    mean_b = sum(benchmarks) / len(benchmarks)
    benchmark_ss = sum((b - mean_b) ** 2 for b in benchmarks)
    if benchmark_ss == 0:
        raise ValueError("benchmark variance must be positive")
    beta = sum((b - mean_b) * (r - mean_r) for r, b in zip(returns, benchmarks)) / benchmark_ss
    alpha = mean_r - beta * mean_b
    residuals = [r - alpha - beta * b for r, b in zip(returns, benchmarks)]
    residual_risk = math.sqrt(sum(e * e for e in residuals) / (len(returns) - 2))
    if residual_risk <= 1e-15:
        raise ValueError("appraisal ratio undefined for zero residual risk")
    downside = [min(0.0, r - mar) for r in returns]
    downside_dev = math.sqrt(sum(x * x for x in downside) / len(downside))
    if downside_dev == 0:
        raise ValueError("Sortino ratio undefined for zero downside deviation")
    sortino = (sum(returns) / len(returns) - mar) / downside_dev
    appraisal = alpha / residual_risk
    wealth = peak = 1.0
    max_drawdown = 0.0
    duration = max_duration = 0
    for r in returns:
        wealth *= 1 + r
        if wealth >= peak:
            peak, duration = wealth, 0
        else:
            duration += 1
            max_duration = max(max_duration, duration)
            max_drawdown = min(max_drawdown, wealth / peak - 1)
    up = [i for i, b in enumerate(benchmarks) if b > 0]
    down = [i for i, b in enumerate(benchmarks) if b < 0]
    if not up or not down:
        raise ValueError("capture ratios require both up and down benchmark periods")
    def geometric(series, indices):
        return math.prod(1 + series[i] for i in indices) ** (1 / len(indices)) - 1
    up_b, down_b = geometric(benchmarks, up), geometric(benchmarks, down)
    if up_b == 0 or down_b == 0:
        raise ValueError("capture ratio benchmark denominator is zero")
    up_capture = geometric(returns, up) / up_b
    down_capture = geometric(returns, down) / down_b
    return {"sortino": sortino, "alpha": alpha, "beta": beta,
            "residual_risk": residual_risk, "appraisal_ratio": appraisal,
            "max_drawdown": max_drawdown,
            "drawdown_duration": max_duration, "up_capture": up_capture,
            "down_capture": down_capture}


def _svg(path, body, width=760, height=400):
    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#172033}'
        '.t{font-size:21px;font-weight:700}.s{font-size:14px}.box{fill:#f5f7fb;stroke:#4e6eaa;stroke-width:2}'
        '.accent{fill:#eaf3ff;stroke:#1864ab;stroke-width:2}.warn{fill:#fff4e6;stroke:#d9480f;stroke-width:2}'
        '.line{stroke:#486581;stroke-width:2;fill:none}.grid{stroke:#d9e2ec;stroke-width:1}</style>\n'
        f'<rect width="{width}" height="{height}" fill="white"/>\n{body}\n</svg>\n', encoding="utf-8")


def generate_figures(directory):
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    boxes = [(25,150,125,72,"客户/机构\n事实与负债"),(175,150,125,72,"IPS\n目标与约束"),
             (325,150,125,72,"资本预期\n与战略配置"),(475,150,125,72,"风险调整\n实施与再平衡"),
             (625,150,110,72,"归因评价\n经理判断")]
    body = '<text x="25" y="40" class="t">同一决策链：每一步都保留可检查的输入与反馈</text>'
    for i,(x,y,w,h,label) in enumerate(boxes):
        cls = 'accent' if i in (1,2) else ('warn' if i==4 else 'box')
        body += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="{cls}"/>'
        a,b=label.split('\n'); body += f'<text x="{x+w/2}" y="{y+29}" text-anchor="middle" class="s">{a}</text><text x="{x+w/2}" y="{y+51}" text-anchor="middle" class="s">{b}</text>'
        if i < 4: body += f'<path d="M{x+w} {y+h/2} L{boxes[i+1][0]-8} {y+h/2}" class="line"/><path d="M{boxes[i+1][0]-8} {y+h/2} l-9 -5 v10 z" fill="#486581"/>'
    body += '<path d="M680 230 C680 330 235 340 235 230" class="line" stroke-dasharray="7 6"/><text x="455" y="326" text-anchor="middle" class="s">归因结果只在任务、基准或约束变化时反馈修订；不能追逐一次输赢</text>'
    _svg(out/'l3-decision-chain.svg', body)

    er=[0.03,0.065]; cov=[[0.0025,0.0015],[0.0015,0.0225]]
    pts=[]
    for k in range(101):
        w=k/100; m,s=portfolio_stats([1-w,w],er,cov); pts.append((s,m))
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    sx=lambda x: 75+(x-min(xs))/(max(xs)-min(xs))*610
    sy=lambda y: 330-(y-min(ys))/(max(ys)-min(ys))*245
    poly=' '.join(f'{sx(x):.1f},{sy(y):.1f}' for x,y in pts)
    body='<text x="25" y="35" class="t">同一输入下的完整两资产可行轨迹（含非有效段）</text>'
    for i in range(6):
        y=85+i*49; body+=f'<line x1="75" y1="{y}" x2="685" y2="{y}" class="grid"/>'
    body+=f'<polyline points="{poly}" fill="none" stroke="#1864ab" stroke-width="4"/>'
    body+='<line x1="75" y1="330" x2="700" y2="330" class="line"/><line x1="75" y1="340" x2="75" y2="70" class="line"/>'
    body+='<text x="355" y="383" class="s">模型年化波动率（%）→</text><text x="12" y="210" class="s" transform="rotate(-90 12 210)">模型年化期望收益（%）→</text>'
    policy_mean, policy_vol = portfolio_stats([.6,.4], er, cov)
    policy_x, policy_y = sx(policy_vol), sy(policy_mean)
    body+=f'<circle cx="{policy_x:.1f}" cy="{policy_y:.1f}" r="8" fill="#d9480f" data-weights="0.6,0.4"/><text x="{policy_x+13:.1f}" y="{policy_y-8:.1f}" class="s">60/40：σ 7.225% / E[R] 4.40%</text><text x="{policy_x+13:.1f}" y="{policy_y+13:.1f}" class="s">负债与流动性检查可能把它移开</text>'
    _svg(out/'l3-allocation-robustness.svg', body)

    alloc,sel,inter,active=brinson_allocation_selection_interaction([.5,.3,.2],[.4,.4,.2],[.10,.03,.05],[.08,.04,.04])
    vals=[sum(alloc),sum(sel),sum(inter)]; labels=['配置','选择','交互']; scale=9000
    body='<text x="25" y="35" class="t">主动收益桥：归因是账本恒等式，不是因果证明</text><line x1="90" y1="300" x2="700" y2="300" class="line"/>'
    x=145
    for v,label in zip(vals,labels):
        h=abs(v)*scale; y=300-h if v>=0 else 300
        color='#2b8a3e' if v>=0 else '#d9480f'
        body+=f'<rect x="{x}" y="{y:.1f}" width="105" height="{h:.1f}" fill="{color}" opacity=".82"/><text x="{x+52}" y="330" text-anchor="middle" class="s">{label}</text><text x="{x+52}" y="{y-8 if v>=0 else y+h+18:.1f}" text-anchor="middle" class="s">{v*100:+.2f}%</text>'; x+=165
    body+=f'<text x="90" y="375" class="s">三项合计 {sum(vals)*100:.2f}% = 组合主动收益 {active*100:.2f}%（舍入前相等）</text>'
    _svg(out/'l3-attribution-bridge.svg', body)


def example_results():
    mean,vol=portfolio_stats([.6,.4],[.03,.065],[[.0025,.0015],[.0015,.0225]])
    surplus=surplus_risk(105,100,5.0,8.0,.01)
    contracts=futures_contracts(50_000_000,.60,.45,2500,50)
    fx_notional,fx_cash=currency_overlay(20_000_000,7.20,.75,7.24)
    a,s,i,active=brinson_allocation_selection_interaction([.5,.3,.2],[.4,.4,.2],[.10,.03,.05],[.08,.04,.04])
    metrics=appraisal_metrics([.03,-.02,.04,-.01,.02,.01],[.02,-.03,.03,-.005,.015,.012])
    return {"allocation":(mean,vol),"surplus_change":surplus,"futures":contracts,
            "fx":(fx_notional,fx_cash),"brinson":(a,s,i,active),"metrics":metrics}


if __name__ == "__main__":
    generate_figures(Path(__file__).with_name("assets"))
    for key,value in example_results().items(): print(key, value)
