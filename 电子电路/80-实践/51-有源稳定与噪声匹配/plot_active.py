"""Render SVGs exclusively from saved numerical results; no recomputation/import of lab."""
import argparse
import html
import json
import math
from pathlib import Path

COLORS = ["#64748b", "#c2410c", "#0369a1"]
NAMES = ["参考直连", "最大增益", "最小噪声＋输出匹配"]


def z(v):
    return complex(*v) if isinstance(v, list) else complex(v)


class SVG:
    def __init__(self, title, height):
        self.items = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}">',
                      f'<title>{html.escape(title)}</title>',
                      f'<desc>{html.escape(title)}；来自保存的同一模型与固定输入，不是实测。</desc>',
                      '<style>text{font-family:Arial Unicode MS,PingFang SC,Noto Sans CJK SC,system-ui,sans-serif;fill:#172033;font-size:17px} .small{font-size:14px} .title{font-size:24px;font-weight:bold}</style>',
                      f'<rect width="1100" height="{height}" fill="#f8fafc"/>']
        self.text(40, 42, title, "title")

    def text(self, x, y, value, css=""):
        self.items.append(f'<text x="{x}" y="{y}" class="{css}">{html.escape(str(value))}</text>')

    def line(self, x1, y1, x2, y2, color="#94a3b8", width=1.3):
        self.items.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def rect(self, x, y, w, h, fill, stroke="none"):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" stroke="{stroke}"/>')

    def poly(self, points, color, width=2):
        self.items.append('<polyline points="'+" ".join(f"{x:.4f},{y:.4f}" for x, y in points)+f'" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def circle(self, x, y, r, color, fill="none", width=2):
        self.items.append(f'<circle cx="{x}" cy="{y}" r="{r}" stroke="{color}" fill="{fill}" stroke-width="{width}"/>')

    def finish(self, path):
        path.write_text("\n".join(self.items+["</svg>"])+"\n")


def plane(s, x, y, size, label, extent=1.1, kind="gamma"):
    s.text(x, y-32, label)
    scale = size/(2*extent)
    def xy(v):
        return x+size/2+v.real*scale, y+size/2-v.imag*scale
    s.rect(x, y, size, size, "#fff", "#cbd5e1")
    for q in ((-1, 0, 1) if kind == "gamma" else (-extent, 0, extent)):
        xx, yy = xy(complex(q, q))
        s.line(xx, y, xx, y+size, "#e2e8f0")
        s.line(x, yy, x+size, yy, "#e2e8f0")
        s.text(xx-12, y+size+23, f"{q:g}", "small")
        if q:
            s.text(x-38, yy+5, f"{q:g}", "small")
    cx, cy = xy(0j)
    if kind == "gamma":
        s.circle(cx, cy, scale, "#172033")
    s.text(x+size-85, y+size+43, "Re Γ" if kind == "gamma" else "Re s/ω0", "small")
    s.text(x+2, y-8, "Im Γ" if kind == "gamma" else "Im s/ω0", "small")
    return xy, scale


def charts(data, out):
    r0 = data["input"]["reference_ohm"]
    f0 = data["input"]["frequency_Hz"]/1e9
    pars = data["noise_parameters"]
    s = SVG("同一双端口：负载稳定区域与源噪声最优点属于不同平面", 1010)
    xy, scale = plane(s, 60, 116, 430, "A 负载 ΓL：对照 Sc 的终端稳定区域（f0）")
    circle = data["conditional"]["stability"]["load_stability_circle"]
    sm = [[z(v) for v in row] for row in data["input"]["conditional_S"]]
    a, d = sm[0][0], sm[1][1]
    delta = sm[0][0]*sm[1][1]-sm[0][1]*sm[1][0]
    # Exact circle parameters are saved; finite shading is only visualization.
    for i in range(43):
        for j in range(43):
            v = complex(-1.05+.05*i, -1.05+.05*j)
            if abs(v) < .98 and abs(a-delta*v)**2 > abs(1-d*v)**2:
                px, py = xy(v)
                s.rect(px-5, py-5, 10, 10, "#fee2e2")
    # Repaint axes/unit disk, then clip the large stability circle to the panel.
    s.items.append('<defs><clipPath id="loadclip"><rect x="60" y="116" width="430" height="430"/></clipPath></defs>')
    s.items.append('<g clip-path="url(#loadclip)">')
    if circle is not None:
        cx, cy = xy(z(circle["center"]))
        s.circle(cx, cy, circle["radius"]*scale, "#dc2626")
    else:
        coeff = d-a.conjugate()*delta
        rhs = (1-abs(a)**2)/2
        pts = []
        for q in (-1.1, 1.1):
            if abs(coeff.imag) > 1e-14:
                yy = (coeff.real*q-rhs)/coeff.imag
                if abs(yy) <= 1.1:
                    pts.append(xy(complex(q, yy)))
            if abs(coeff.real) > 1e-14:
                xx = (rhs+coeff.imag*q)/coeff.real
                if abs(xx) <= 1.1:
                    pts.append(xy(complex(xx, q)))
        if len(pts) >= 2:
            s.line(*pts[0], *pts[1], "#dc2626", 2)
    s.items.append('</g>')
    cx, cy = xy(0j)
    s.circle(cx, cy, scale, "#172033")
    for v, text in ((0j, "ΓL=0"), (complex(data["input"]["conditional_gamma"]), f'ΓL={data["input"]["conditional_gamma"]:g}')):
        px, py = xy(v)
        s.circle(px, py, 4, "#172033", "#172033")
        s.text(px-55, py-13, text, "small")
    s.text(60, 590, "红区：|Γin|>1，存在使闭环失稳的被动源。", "small")
    s.text(60, 615, "并非红区任意源都失稳；着色按原隐式式判侧。", "small")
    s.text(60, 640, f'S0 整个被动负载圆盘：max|Γin|={data["stability"]["max_abs_gin"]:.6f}。', "small")

    xy, scale = plane(s, 610, 116, 430, "B 源 ΓS：S0 的等噪声因子圆（f0）")
    for con in data["noise_contours"]:
        cx, cy = xy(z(con["center"]))
        s.circle(cx, cy, con["radius"]*scale, "#93c5fd")
        s.text(cx-35, cy-con["radius"]*scale-5, f'F={con["F"]:g}', "small")
    for idx, row in enumerate(data["designs"]):
        px, py = xy(z(row["gamma_S"]))
        s.circle(px, py, 5, COLORS[idx], COLORS[idx])
        dx, dy = ((-50, 38), (-30, -25), (-70, -22))[idx]
        s.text(px+dx, py+dy, NAMES[idx], "small")
    s.text(610, 590, f'Fmin={pars["F_min"]:.4f}；Γopt={z(pars["gamma_opt"]).real:.3f}{z(pars["gamma_opt"]).imag:+.3f}j。', "small")
    s.text(610, 615, "单位圆边界仅为几何极限；不测量零吸收的 SNR。", "small")
    s.text(610, 640, "两面板的 Γ 对象不同，不将噪声圆当稳定圆。", "small")

    s.text(60, 704, f'C 同一 R0={r0:g} Ω / f0={f0:g} GHz / Pav={data["input"]["available_power_W"]*1e6:g} μW')
    s.rect(55, 727, 990, 195, "#fff", "#cbd5e1")
    for x, label in ((75, "设计"), (385, "GT (dB)"), (570, "NF (dB)"), (755, "PL (μW)"), (925, "F")):
        s.text(x, 758, label)
    for idx, row in enumerate(data["designs"]):
        yy = 802+idx*44
        s.text(75, yy, NAMES[idx])
        s.text(385, yy, f'{row["G_T_dB"]:.6f}')
        s.text(570, yy, f'{row["NF_dB"]:.6f}')
        s.text(755, yy, f'{row["P_L_W"]*1e6:.6f}')
        s.text(925, yy, f'{row["F"]:.6f}')
    s.text(60, 963, "降低 NF 不必牺牲相同数值的增益；默认实例由两种不同极值问题确定。", "small")
    s.finish(out/"matching.svg")

    s = SVG("把匹配落成电路，并检查频率与动态稳定边界", 1040)
    s.text(50, 92, f'A 最小噪声设计：DUT向两侧先并联电抗，再串联L到 {r0:g} Ω')
    row = data["designs"][2]
    s.rect(450, 150, 200, 120, "#e0f2fe", "#0369a1")
    s.text(490, 199, "b = S0 a + c")
    s.text(476, 231, "固定偏置的小信号模型", "small")
    s.line(120, 185, 450, 185, "#172033", 2)
    s.line(650, 185, 1000, 185, "#172033", 2)
    for node, net, label, compx in ((380, row["source_L_section"], "源端", 200), (720, row["load_L_section"], "负载端", 865)):
        s.line(node, 185, node, 235, "#172033", 2)
        if net["shunt_L_H"] is None:
            s.line(node, 235, node, 250, "#172033", 2)
            s.line(node-15, 250, node+15, 250, "#172033", 2)
            s.line(node-15, 258, node+15, 258, "#172033", 2)
            s.line(node, 258, node, 283, "#172033", 2)
        else:
            s.rect(node-12, 235, 24, 36, "#fff", "#172033")
            s.text(node-5, 259, "L", "small")
            s.line(node, 271, node, 283, "#172033", 2)
        s.line(node-18, 283, node+18, 283, "#172033", 2)
        s.rect(compx-55, 168, 110, 34, "#fff", "#172033")
        s.text(compx-42, 190, f'L={net["series_L_H"]*1e9:.3f}nH', "small")
        s.text(node-65, 318, f'{label} C={net["shunt_C_F"]*1e12:.4f}pF' if net["shunt_L_H"] is None else f'{label} 并L={net["shunt_L_H"]*1e9:.4f}nH', "small")
    s.text(75, 155, f"Vs, {r0:g} Ω", "small")
    s.text(950, 155, f"{r0:g} Ω", "small")
    s.text(444, 136, "a1 →      ← b1", "small")
    s.text(650, 136, "b2 →      ← a2", "small")
    s.text(50, 358, f'两侧为理想无损教学LC；Pav={data["input"]["available_power_W"]*1e6:g} μW，非PDK / PCB提取值。', "small")

    left, top, ww, hh = 80, 455, 445, 330
    s.text(left, top-40, "B 同一实际 LC 离开设计频率：GT 改变")
    rows = data["frequency_probes"]
    freqs = [r["frequency_Hz"]/1e9 for r in rows]
    vals = [r["G_T_dB"] for r in rows]
    xmin, xmax = min(freqs), max(freqs)
    ymin, ymax = min(vals)-.4, max(vals)+.4
    if xmin == xmax:
        xmin, xmax = xmin-.1, xmax+.1
    def fx(x):
        return left+(x-xmin)/(xmax-xmin)*ww
    def fy(y):
        return top+hh-(y-ymin)/(ymax-ymin)*hh
    s.rect(left, top, ww, hh, "#fff", "#cbd5e1")
    for i in range(5):
        value = ymin+(ymax-ymin)*i/4
        yy = fy(value)
        s.line(left, yy, left+ww, yy, "#e2e8f0")
        s.text(left-55, yy+5, f"{value:.1f}", "small")
    for idx, label in enumerate(("reference_match", "maximum_gain", "minimum_noise_output_matched")):
        selected = sorted([r for r in rows if r["label"] == label], key=lambda r:r["frequency_Hz"])
        pts = [(fx(r["frequency_Hz"]/1e9), fy(r["G_T_dB"])) for r in selected]
        s.poly(pts, COLORS[idx], 2.5)
        for px, py in pts:
            s.circle(px, py, 4, COLORS[idx], COLORS[idx])
        s.text(left+idx*140, top+hh+58, NAMES[idx], "small")
    for x in sorted(set(freqs)):
        s.text(fx(x)-15, top+hh+24, f"{x:g}", "small")
    s.text(left+ww-30, top+hh+82, "GHz", "small")
    s.text(left-25, top-10, "dB", "small")

    omega = 2*math.pi*data["input"]["frequency_Hz"]
    poles = [z(v)/omega for v in data["conditional"]["poles_rad_per_s"]]
    extent = max(1.1, math.ceil(max(max(abs(p.real), abs(p.imag)) for p in poles)*1.15*2)/2)
    xy, scale = plane(s, 665, 455, 330, "C Sc 同一终端：归一极点 s/ω0", extent, "poles")
    for pole in data["conditional"]["poles_rad_per_s"]:
        pp = z(pole)/omega
        px, py = xy(pp)
        s.line(px-6, py-6, px+6, py+6, "#dc2626" if pp.real > 0 else "#0369a1", 2.5)
        s.line(px-6, py+6, px+6, py-6, "#dc2626" if pp.real > 0 else "#0369a1", 2.5)
    unstable = any(p.real > 0 for p in poles)
    s.text(665, 850, f'ΓS=ΓL={data["input"]["conditional_gamma"]:g}：'+("存在右半平面红叉。" if unstable else "本卡无右半平面根。"), "small")
    den = z(data["conditional"]["formal_frequency_solution"]["D"])
    s.text(665, 878, f'D(f0)={den.real:.3f}{den.imag:+.3f}j，仍不保证稳态存在。', "small")
    s.text(50, 950, f'H(s)为明确的稳定带通扩展；S0加权界={data["weighted_small_gain_bound"]:.4f}，仅当<1给小增益证明。', "small")
    s.text(50, 981, "频率线只连接已算的有限点，不认证带内处处指标；噪声卡仅定义在 f0。", "small")
    s.finish(out/"network-dynamics.svg")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.results.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    charts(data, args.out)


if __name__ == "__main__":
    main()
