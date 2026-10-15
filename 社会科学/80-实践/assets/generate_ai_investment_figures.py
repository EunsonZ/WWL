"""生成金融课程 09 的三张 SVG；数值来源为同目录精确分数模型。

绘图需要 Matplotlib；复算 ai_investment_examples.py 只需 Python 标准库。
英文图中文字避免依赖额外中文字库，中文说明和单位映射保留在正文。
本脚本只写同目录三张指定 SVG，不下载数据，也不修改原稿。
"""

from fractions import Fraction as F
from html import escape
from pathlib import Path
import re

from ai_investment_examples import examples, two_year_scenario


OUTPUT = Path(__file__).resolve().parent


def svg_document(title, description, body, height):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">{escape(description)}</desc>
<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#334155"/></marker>
<style>text{{font-family:DejaVu Sans,Arial,sans-serif;fill:#172554}} .heading{{font-size:24px;font-weight:700}} .label{{font-size:19px}} .small{{font-size:16px}} .note{{font-size:17px;fill:#475569}} .box{{fill:#eff6ff;stroke:#64748b;stroke-width:1.5}} .arrow{{fill:none;stroke:#334155;stroke-width:2;marker-end:url(#arrow)}}</style></defs>
<rect width="1000" height="{height}" fill="white"/>
{body}
</svg>
'''


def draw_timeline():
    body = '''<text x="38" y="44" class="heading">One valuation date for all cash flows</text>
<text x="38" y="76" class="note">Money in the same currency; r = 10% per year; no operating cash flow</text>
<path d="M140,130 H890" class="arrow"/>
<g class="label" text-anchor="middle">
  <text x="170" y="120">t = 0</text><text x="510" y="120">t = 1</text><text x="850" y="120">t = 2</text>
  <text x="170" y="177">Invest -100</text><text x="510" y="177">Cash 0</text><text x="850" y="177">Sell asset +121</text>
</g>
<path d="M170,136 V152 M510,136 V152 M850,136 V152" stroke="#334155" stroke-width="2"/>
<path d="M850,198 V242 H225" class="arrow"/>
<text x="540" y="231" class="label" text-anchor="middle">121 / (1.10 × 1.10) = 100 today</text>
<rect x="95" y="268" width="810" height="56" rx="8" class="box"/>
<text x="500" y="304" class="heading" text-anchor="middle">NPV at t = 0: -100 + 100 = 0</text>
<text x="38" y="359" class="note">The horizontal position shows time. Arrow length does not encode money.</text>'''
    (OUTPUT / "ai-investment-timeline.svg").write_text(svg_document(
        "初始投资与终值的共同估值时点",
        "t0 投入100；t1经营现金0；t2经营现金0且处置收到121。按年10%贴现，121的现值100，净现值为0。箭头不是金额比例。",
        body, 385), encoding="utf-8")


def draw_payment_ledger():
    body = '''<text x="35" y="43" class="heading">Follow payments before adding sales</text>
<text x="35" y="74" class="note">One period; deliveries and payment in the same period; teaching money units</text>
<rect x="285" y="98" width="678" height="443" rx="12" fill="#f8fafc" stroke="#64748b" stroke-dasharray="7 5"/>
<text x="306" y="128" class="small">Analysis boundary: model provider + cloud + equipment supplier</text>
<rect x="25" y="160" width="215" height="72" rx="8" class="box"/>
<text x="132" y="190" text-anchor="middle" class="label">Households</text>
<text x="132" y="215" text-anchor="middle" class="small">Service payment 40</text>
<rect x="25" y="333" width="215" height="72" rx="8" class="box"/>
<text x="132" y="363" text-anchor="middle" class="label">Non-AI business</text>
<text x="132" y="388" text-anchor="middle" class="small">Service payment 60</text>
<rect x="360" y="195" width="225" height="110" rx="8" class="box"/>
<text x="472" y="228" text-anchor="middle" class="label">Model provider M</text>
<text x="472" y="258" text-anchor="middle" class="small">Service sales: 100</text>
<text x="472" y="283" text-anchor="middle" class="small">Listed cash change: +40</text>
<rect x="725" y="195" width="215" height="110" rx="8" class="box"/>
<text x="832" y="228" text-anchor="middle" class="label">Cloud C</text>
<text x="832" y="258" text-anchor="middle" class="small">Service sales: 60</text>
<text x="832" y="283" text-anchor="middle" class="small">Listed cash change: +30</text>
<rect x="725" y="405" width="215" height="110" rx="8" class="box"/>
<text x="832" y="438" text-anchor="middle" class="label">Equipment E</text>
<text x="832" y="468" text-anchor="middle" class="small">Equipment sales: 30</text>
<text x="832" y="493" text-anchor="middle" class="small">Listed cash change: +30</text>
<path d="M240,196 L360,229" class="arrow"/>
<path d="M240,369 L360,280" class="arrow"/>
<text x="304" y="188" class="label">40</text><text x="294" y="299" class="label">60</text>
<path d="M585,250 H725" class="arrow"/>
<text x="655" y="232" text-anchor="middle" class="label">60</text>
<text x="655" y="283" text-anchor="middle" class="small">Cloud service</text>
<path d="M832,305 V405" class="arrow"/>
<text x="808" y="349" text-anchor="end" class="label">30</text>
<text x="808" y="375" text-anchor="end" class="small">Capital equipment for C</text>
<text x="310" y="459" class="note">Internal payments cancel</text>
<text x="310" y="485" class="note">when this boundary is combined.</text>
<text x="35" y="586" class="heading">Customer cash entering: 100 | Layered sales: 190</text>
<text x="35" y="619" class="note">Cash changes shown are not profits. This is not a complete GDP account.</text>'''
    (OUTPUT / "ai-investment-payment-ledger.svg").write_text(svg_document(
        "同期间支付与分析合并边界",
        "家庭付模型商40，非AI企业付模型商60，模型商付云商60，云商买设备30。边界内现金净变化40、30、30合计100；各层销售收入100、60、30合计190。设备购买属于云商投资；现金增量不是利润或GDP。",
        body, 648), encoding="utf-8")


def draw_cost_and_scenarios():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none", "svg.hashsalt": "wwl-ai-investment-v1"})
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.1), constrained_layout=True)
    left, right = axes
    revenues = [F(i, 10) for i in range(121)]
    xs = [float(r) for r in revenues]
    left.plot(xs, xs, color="#075985", label="Revenue R", linewidth=2.5)
    left.plot(xs, [float(6 + r / 4) for r in revenues], color="#b45309",
              linestyle="--", label="Total cost 6 + 0.25R", linewidth=2.5)
    left.axhline(6, color="#64748b", linestyle=":", label="Fixed cost 6")
    left.scatter([8], [8], color="#172554", zorder=5)
    left.annotate("Break-even (8, 8)", (8, 8), xytext=(3, 10.4),
                  arrowprops={"arrowstyle": "->", "color": "#475569"})
    left.set(xlim=(0, 12), ylim=(0, 13), xlabel="Annual revenue R (money/year)",
             ylabel="Annual amount (money/year)", title="A. One cost, one deduction")
    left.legend(loc="upper left", frameon=False)

    utilization = [F(i, 100) for i in range(30, 101)]
    specs = [("Prices 2, 2; resale 49", {}, "#075985", "-"),
             ("Prices 2, 1.6; resale 49", {"second_price": F("1.6")}, "#b45309", "--"),
             ("Prices 2, 2; resale 4", {"resale_decline": F("0.8")}, "#7c3aed", ":")]
    for label, kwargs, color, style in specs:
        vals = [float(two_year_scenario(utilization=u, **kwargs)["npv"]) for u in utilization]
        right.plot([float(u) for u in utilization], vals, label=label,
                   color=color, linestyle=style, linewidth=2.3)
    right.axhline(0, color="#64748b", linewidth=1)
    offsets = {"A": (8, 8), "B": (8, -12), "C": (-48, 12), "D": (8, -12)}
    for name, case in examples()["scenarios"].items():
        xy = (float(case["utilization"]), float(case["npv"]))
        right.scatter(*xy, color="#172554", zorder=5, s=22)
        right.annotate(f"{name}: {xy[1]:.2f}", xy, xytext=offsets[name], textcoords="offset points")
    right.set(xlim=(0.28, 1.03), ylim=(-65, 48), xlabel="Sold utilization u (same in both years)",
              ylabel="NPV at t=0 (money)", title="B. Same closure progress: 50% to 70%")
    right.legend(loc="upper left", frameon=False, fontsize=10)
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    dest = OUTPUT / "ai-investment-cost-scenarios.svg"
    fig.savefig(dest, metadata={"Date": None, "Creator": "WWL generate_ai_investment_figures.py"})
    plt.close(fig)
    svg = dest.read_text(encoding="utf-8")
    start = re.search(r"<svg\b[^>]*>", svg)
    if start is None:
        raise RuntimeError("Matplotlib did not produce an SVG root")
    description = ("左图年度收入R与总成本6+0.25R在8相交。右图固定闭环率从50%升至70%，"
                   "比较不同售价、残值下NPV随利用率变化；A为正5.7851，B负12.7273，C负25.2066，D负31.4050。")
    opening = start.group().replace("<svg ", '<svg role="img" aria-labelledby="title desc" ', 1)
    accessible = '<title id="title">成本与现金流条件怎样改变盈亏</title><desc id="desc">' + description + "</desc>"
    dest.write_text(svg[:start.start()] + opening + accessible + svg[start.end():], encoding="utf-8")


if __name__ == "__main__":
    draw_cost_and_scenarios()
    draw_timeline()
    draw_payment_ledger()
    print("Generated three SVG figures in", OUTPUT)
