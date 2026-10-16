#!/usr/bin/env python3
"""Exact two-good teaching cases and a matching SVG; no numerical optimizer."""
import argparse
from fractions import Fraction as F
from html import escape
from math import isqrt
import json
from pathlib import Path


def positive(value):
    if not isinstance(value, str):
        raise ValueError("use exact strings such as '5/2' for input numbers")
    value = F(value)
    if value <= 0:
        raise ValueError("prices and budgets must be positive")
    return value


def prices(values):
    if len(values) != 2:
        raise ValueError("exactly two prices required")
    return tuple(positive(v) for v in values)


def sqrt_exact(value):
    """Keep fixed rational examples exact; explicitly reject irrational roots."""
    a, b = isqrt(value.numerator), isqrt(value.denominator)
    if a*a != value.numerator or b*b != value.denominator:
        raise ValueError("this exact lab requires rational square roots; see analytic formula")
    return F(a, b)


def cost(p, q):
    return sum(pi*qi for pi, qi in zip(p, q))


def ordinary(p, m):
    return m/(2*p[0]), m/(2*p[1])


def utility(q):
    return q[0]*q[1]


def hicks(p, target):
    if target <= 0:
        raise ValueError("this lab fixes a strictly positive old utility target")
    return sqrt_exact(target*p[1]/p[0]), sqrt_exact(target*p[0]/p[1])


def case(p0, p1, m):
    a = ordinary(p0, m)
    target = utility(a)
    h = hicks(p1, target)
    e = cost(p1, h)
    ms = cost(p1, a)
    points = {"A": a, "M": ordinary(p1, m), "H": h, "S": ordinary(p1, ms)}
    # Local consistency checks, not a substitute for the all-bundle proof in text.
    assert cost(p0, a) == m
    assert utility(h) == target and p1[0]*h[0] == p1[1]*h[1]
    assert e*e == 4*p1[0]*p1[1]*target and e <= ms
    return {"p0": p0, "p1": p1, "budget": m, "target": target,
            "hicks_expenditure": e, "hicks_topup": e-m,
            "old_basket_budget": ms, "old_basket_topup": ms-m,
            "points": {k: {"quantity": q, "utility": utility(q),
                           "new_price_cost": cost(p1, q)} for k, q in points.items()}}


def linear_choice(p, m, weights):
    ratios = tuple(w/pi for w, pi in zip(weights, p))
    if ratios[0] == ratios[1]:
        return {"kind": "segment", "equation": f"{p[0]}*x+{p[1]}*y={m}"}
    index = 0 if ratios[0] > ratios[1] else 1
    q = (m/p[0], F(0)) if index == 0 else (F(0), m/p[1])
    return {"kind": "unique", "quantity": q, "utility": sum(w*x for w, x in zip(weights,q))}


def linear_hicks(p, target, weights):
    best = max(w/pi for w, pi in zip(weights, p))
    amount = target/best
    return {"expenditure": amount, "choice": linear_choice(p, amount, weights)}


def serial(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


def build_svg(main, corner, destination):
    """Use the same exact main-case results; float conversion is drawing-only."""
    width, height = 1120, 700
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Ordinary demand, Hicks compensation, and old-basket compensation</title>',
             '<desc id="desc">Synthetic teaching cases. Left: xy preferences, old prices 1 and 1, budget 10; new prices 4 and 1. A=(5,5), M=(1.25,5), H=(2.5,10), S=(3.125,12.5). H costs 20; the old basket costs 25. Right: linear preferences 2x+y, same prices and initial budget. Choices move between axes; target utility 20 costs 20 at new prices.</desc>',
             '<rect width="1120" height="700" fill="white"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#172235;font-size:14px}.title{font-size:21px;font-weight:bold}.small{font-size:13px}.axis{stroke:#334155;stroke-width:1.4}.grid{stroke:#e2e8f0;stroke-width:1}</style>',
             '<text x="560" y="30" text-anchor="middle" class="title">Same prices, different fixed objects</text>',
             '<text x="560" y="53" text-anchor="middle">Synthetic data; quantity in portions, prices in currency / portion</text>']
    def panel(left, title, xmax, ymax):
        top, pw, ph = 105, 440, 440
        sx=lambda x: left+float(x)/xmax*pw
        sy=lambda y: top+ph-float(y)/ymax*ph
        parts.append(f'<text x="{left}" y="85" class="title">{escape(title)}</text>')
        for x in range(0, xmax+1, 2):
            parts.append(f'<line class="grid" x1="{sx(x)}" y1="{top}" x2="{sx(x)}" y2="{top+ph}"/><text x="{sx(x)}" y="{top+ph+20}" text-anchor="middle">{x}</text>')
        for y in range(0, ymax+1, 5):
            parts.append(f'<line class="grid" x1="{left}" y1="{sy(y)}" x2="{left+pw}" y2="{sy(y)}"/><text x="{left-10}" y="{sy(y)+5}" text-anchor="end">{y}</text>')
        parts.append(f'<line class="axis" x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}"/><line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}"/><text x="{left+pw}" y="{top+ph+43}" text-anchor="end">x (portions)</text><text x="{left}" y="{top-7}">y (portions)</text>')
        def line(p, amount, color, dash):
            xs=min(F(xmax), amount/p[0]); xe=max(F(0),(amount-p[1]*ymax)/p[0])
            ys=(amount-p[0]*xs)/p[1]; ye=(amount-p[0]*xe)/p[1]
            parts.append(f'<line x1="{sx(xe)}" y1="{sy(ye)}" x2="{sx(xs)}" y2="{sy(ys)}" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>')
        def point(q,label,color,dx=7,dy=-9):
            parts.append(f'<circle cx="{sx(q[0])}" cy="{sy(q[1])}" r="5" fill="{color}" stroke="white" stroke-width="1.5"/>')
            # Draw two separate text nodes: CairoSVG need not support paint-order.
            attrs = f'x="{sx(q[0])+dx}" y="{sy(q[1])+dy}" class="small"'
            parts.append(f'<text {attrs} stroke="white" stroke-width="4" stroke-linejoin="round">{escape(label)}</text>')
            parts.append(f'<text {attrs} stroke="none">{escape(label)}</text>')
        return sx,sy,line,point
    sx,sy,line,point=panel(65,"Product preferences: u = xy",10,25)
    p0,p1,m=main["p0"],main["p1"],main["budget"]
    colors={"A":"#334155","M":"#c2410c","H":"#047857","S":"#7e22ce"}
    line(p0,m,colors["A"],"8 4");line(p1,m,colors["M"],"0")
    line(p1,main["hicks_expenditure"],colors["H"],"10 3");line(p1,main["old_basket_budget"],colors["S"],"3 4")
    for label in ("M","H","S"):
        target=main["points"][label]["utility"]
        pts=[]
        for j in range(1,501):
            x=F(j,50);y=target/x
            if y<=25:pts.append(f'{sx(x):.2f},{sy(y):.2f}')
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[label]}" opacity="0.65" stroke-width="1.5"/>')
    for k,dx,dy in [("A",8,19),("M",-45,22),("H",8,-10),("S",8,-10)]:
        q=main["points"][k]["quantity"]
        point(q,f'{k} ({float(q[0]):g}, {float(q[1]):g})',colors[k],dx,dy)
    sx,sy,line,point=panel(650,"Corner preferences: u = 2x + y",10,25)
    weights=corner["weights"]
    line(p0,m,"#334155","8 4");line(p1,m,"#c2410c","0")
    line(p1,corner["hicks"]["expenditure"],"#047857","10 3")
    line(weights,corner["target"],"#0e7490","3 4")
    point(corner["old"]["quantity"],"A_L (10, 0)","#334155",-95,-10)
    point(corner["new"]["quantity"],"M_L (0, 10)","#c2410c",8,20)
    point(corner["hicks"]["choice"]["quantity"],"H_L (0, 20)","#047857",8,-10)
    legends=[("#334155","8 4","Initial budget: x + y = 10"),("#c2410c","0","New prices, fixed income: 4x + y = 10"),("#047857","10 3","Hicks expenditure: 4x + y = 20"),("#7e22ce","3 4","Old-basket budget (left only): 4x + y = 25")]
    for i,(c,d,t) in enumerate(legends):
        col=i%2;row=i//2;x=65+col*540;y=615+row*27
        parts.append(f'<line x1="{x}" x2="{x+35}" y1="{y}" y2="{y}" stroke="{c}" stroke-width="2" stroke-dasharray="{d}"/><text x="{x+43}" y="{y+5}">{escape(t)}</text>')
    parts.append('<text x="650" y="680" class="small">Right dotted blue: old indifference line 2x + y = 20.</text></svg>')
    destination.write_text('\n'.join(parts)+'\n',encoding="utf-8")


def main():
    here=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=here/"inputs.json")
    parser.add_argument("--output-dir",type=Path,default=here/"results")
    parser.add_argument("--no-figure",action="store_true",help="compute changed parameters without the fixed-example diagram")
    args=parser.parse_args()
    config=json.loads(args.input.read_text(encoding="utf-8"))
    p0=prices(config["baseline"]["prices"]);p1=prices(config["new_prices"])
    m=positive(config["baseline"]["budget"])
    main_case=case(p0,p1,m)
    t=config["transfer"]
    transfer=case(prices(t["baseline_prices"]),prices(t["new_prices"]),positive(t["budget"]))
    weights=prices(config["corner"]["weights"])
    old=linear_choice(p0,m,weights)
    if old["kind"] != "unique":
        raise ValueError("fixed lab corner baseline requires a unique old basket")
    target=old["utility"]
    corner={"weights":weights,"old":old,"new":linear_choice(p1,m,weights),"target":target,
            "hicks":linear_hicks(p1,target,weights),"old_basket_budget":cost(p1,old["quantity"]),
            "tie_case":linear_choice(prices(config["corner"]["tie_prices"]),m,weights)}
    if not args.no_figure and (p0,p1,m,weights) != ((F(1),F(1)),(F(4),F(1)),F(10),(F(2),F(1))):
        raise ValueError("diagram is for the text fixed example; use --no-figure for changed parameters")
    out={"model":"synthetic continuous two-good choices", "main":main_case,"transfer":transfer,"corner":corner}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"exact-results.json").write_text(json.dumps(serial(out),ensure_ascii=False,indent=2)+'\n',encoding="utf-8")
    if not args.no_figure:
        build_svg(main_case,corner,args.output_dir/"demand-compensation.svg")
    print(json.dumps(serial(out),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
