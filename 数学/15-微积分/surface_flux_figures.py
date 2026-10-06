"""One dimensionless graph: r(u,v)=(u,v,u*u+v*v), D=[0,1]^2.

Editable SVG, PNG, CSV and JSON are generated locally; no network is used.
Use the existing NumPy/Matplotlib environment, --output DIR, and a writable
MPLCONFIGDIR. The drawn finite patch is illustrative, not an exact area formula.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def points(u, v):
    u, v = np.broadcast_arrays(np.asarray(u, dtype=float), np.asarray(v, dtype=float))
    if not np.all(np.isfinite(u)) or not np.all(np.isfinite(v)):
        raise ValueError("parameters must be finite")
    return np.stack((u, v, u*u + v*v), axis=-1)


def tangents(u, v):
    p = points(u, v)
    one, zero = np.ones_like(p[..., 0]), np.zeros_like(p[..., 0])
    return (np.stack((one, zero, 2*p[..., 0]), axis=-1),
            np.stack((zero, one, 2*p[..., 1]), axis=-1))


def normal_area(u, v):
    return np.cross(*tangents(u, v))


def integrate_square(function, order=32):
    if isinstance(order, bool) or not isinstance(order, int) or order < 1:
        raise ValueError("quadrature order must be a positive integer")
    q, weights = np.polynomial.legendre.leggauss(order)
    u, v = np.meshgrid((q+1)/2, (q+1)/2, indexing="ij")
    values = np.asarray(function(u, v), dtype=float)
    if values.shape != u.shape or not np.all(np.isfinite(values)):
        raise ValueError("integrand must give one finite value per point")
    return float(np.sum(np.outer(weights, weights)*values)/4)


def exact_area():
    # Independent closed-form reference for this square, not the disk example.
    return float(1 + 7*np.log(5)/12 - np.arctan(4/3)/12)


def save_figure(fig, target, title, description):
    fig.savefig(target.with_suffix(".svg"), metadata={"Date": None})
    fig.savefig(target.with_suffix(".png"), dpi=100)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.parse(target.with_suffix(".svg")).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    root.set("role", "img")
    root.set("aria-labelledby", "figure-title figure-desc")
    for tag, identifier, text in [("title", "figure-title", title),
                                   ("desc", "figure-desc", description)]:
        node = ET.Element(ns+tag, {"id": identifier})
        node.text = text
        root.insert(0, node)
    ET.ElementTree(root).write(target.with_suffix(".svg"), encoding="utf-8", xml_declaration=True)


def render(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties, findfont
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    font_path = findfont(FontProperties(family="Arial Unicode MS"), fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial Unicode MS", "font.size": 11,
                         "svg.fonttype": "none", "svg.hashsalt": "wwl-surface-flux-v1",
                         "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff"})
    p = points(.5, .5)
    a, b = tangents(.5, .5)
    n = normal_area(.5, .5)
    delta = .2
    blue, orange, green = "#155eb0", "#b55212", "#207148"
    fig = plt.figure(figsize=(4.25, 5.1))
    ax = fig.add_axes([.16, .32, .78, .56])
    fig.text(.06, .955, "二维域：小矩形从哪里来？", fontsize=15)
    ax.plot([0, 1, 1, 0, 0], [0, 0, 1, 1, 0], color="#536170")
    ax.fill([.5, .7, .7, .5], [.5, .5, .7, .7], color="#dcecf6")
    ax.plot([.5, .7, .7, .5, .5], [.5, .5, .7, .7, .5], color="#263238")
    ax.annotate("", (.7, .5), (.5, .5), arrowprops={"arrowstyle": "->", "color": blue, "lw": 2})
    ax.annotate("", (.5, .7), (.5, .5), arrowprops={"arrowstyle": "->", "color": orange, "lw": 2, "linestyle": "--"})
    ax.text(.6, .43, "Δu", ha="center", color=blue)
    ax.text(.43, .61, "Δv", ha="right", color=orange)
    ax.plot(.5, .5, "ko", markersize=4)
    ax.text(.47, .35, "q₀=(½,½)", ha="center")
    ax.text(.18, .84, "D=[0,1]²", fontsize=13)
    ax.set(xlim=(-.03, 1.03), ylim=(-.03, 1.03), xlabel="u", ylabel="v")
    ax.set_aspect("equal")
    ax.set_xticks([0, .5, 1]); ax.set_yticks([0, .5, 1])
    fig.text(.06, .19, "映射 r(u,v)=(u,v,u²+v²)\n实线：固定 v，沿 u 增加\n虚线：固定 u，沿 v 增加", linespacing=1.6, va="top")
    fig.text(.06, .035, "参数与坐标均无量纲；图中 Δu=Δv=0.2。", fontsize=10)
    save_figure(fig, output/"surface-domain-2d", "二维参数域与小矩形",
                "单位正方形内从二分之一、二分之一出发，实线边增大u，虚线边增大v。小矩形映到抛物面曲面片。有限边长0.2用于示意。")
    plt.close(fig)

    fig = plt.figure(figsize=(4.25, 6.25))
    ax = fig.add_axes([.04, .40, .92, .48], projection="3d")
    fig.text(.06, .955, "三维面：面积与方向如何合在一起？", fontsize=13)
    grid = np.linspace(.3, .85, 25)
    u, v = np.meshgrid(grid, grid, indexing="ij")
    ax.plot_surface(u, v, u*u+v*v, color="#bfdae8", alpha=.30, edgecolor="#81949f", linewidth=.25, rstride=3, cstride=3)
    pu, pv = np.meshgrid(np.linspace(.5, .7, 7), np.linspace(.5, .7, 7), indexing="ij")
    ax.plot_surface(pu, pv, pu*pu+pv*pv, color=green, alpha=.8, edgecolor="none")
    corners = [p, p+delta*a, p+delta*(a+b), p+delta*b]
    ax.add_collection3d(Poly3DCollection([corners], facecolor="#ffe4be", edgecolor="#593b1b", alpha=.45))
    ax.plot(*np.array([p, p+delta*a]).T, color=blue, lw=3)
    ax.plot(*np.array([p, p+delta*b]).T, color=orange, lw=3, linestyle="--")
    ax.quiver(*p, *(delta*a), color=blue, arrow_length_ratio=.25, linewidth=2)
    ax.quiver(*p, *(delta*b), color=orange, arrow_length_ratio=.25, linewidth=2)
    ax.quiver(*p, *(n/np.linalg.norm(n)*.42), color="#202020", arrow_length_ratio=.2, linewidth=2)
    ax.text(*(p+n/np.linalg.norm(n)*.49), "N↑", fontsize=11, zorder=20)
    fp = points(.78, .35)
    ax.quiver(*fp, 0, 0, .42, color=green, arrow_length_ratio=.2, linewidth=2)
    ax.text(*(fp+np.array([0, 0, .46])), "F", color=green, zorder=20, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.scatter(*p, color="black", s=18)
    ax.set(xlim=(.3, .85), ylim=(.3, .85), zlim=(.1, 1.5), xlabel="x=u", ylabel="y=v", zlabel="z")
    ax.set_xticks([.3, .5, .8]); ax.set_yticks([.3, .5, .8]); ax.set_zticks([.5, 1, 1.5])
    ax.tick_params(labelsize=10, pad=0)
    ax.set_box_aspect((1, 1, 1.25))
    ax.view_init(elev=27, azim=-58)
    fig.text(.06, .30, "同一 q₀ 对应 P=(½,½,½)\n实线：r_uΔu；虚线：r_vΔv\n浅色平行四边形：切平面近似\n深色曲面片：小矩形的实际像", linespacing=1.5, fontsize=11, va="top")
    fig.text(.06, .16, "P 处 N=r_u×r_v=(−1,−1,1)\n黑箭头按长度 0.42 缩放，仅表示方向。\nF=(0,0,1)；全曲面向上通量=1。", linespacing=1.5, fontsize=11, va="top")
    fig.text(.06, .025, "画面为局部；坐标无量纲；曲面片 ≠ 切平面片。", fontsize=10)
    save_figure(fig, output/"surface-patch-3d", "同一参数小矩形的三维像与切平面近似",
                "抛物面z=x平方加y平方上，深色曲面片为二维小矩形的像，浅色平行四边形是P点切平面近似。实线和虚线分别为两个切向边，黑箭头是朝上的叉积方向且缩放显示，绿色F竖直朝上。")
    plt.close(fig)
    return font_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    flux = integrate_square(lambda u, v: normal_area(u, v)[..., 2])
    area = integrate_square(lambda u, v: np.linalg.norm(normal_area(u, v), axis=-1))
    np.testing.assert_allclose(flux, 1, atol=1e-14, rtol=0)
    np.testing.assert_allclose(area, exact_area(), atol=2e-13, rtol=0)
    font_path = render(args.output)
    with (args.output/"surface-grid.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["u", "v", "x", "y", "z", "N_x", "N_y", "N_z", "area_density", "flux_density_up"])
        for u in np.linspace(0, 1, 25):
            for v in np.linspace(0, 1, 25):
                n = normal_area(u, v)
                writer.writerow([u, v, *points(u, v), *n, np.linalg.norm(n), n[2]])
    (args.output/"surface-checks.json").write_text(json.dumps({
        "model": "r(u,v)=(u,v,u*u+v*v), F=(0,0,1)",
        "domain": "[0,1]^2", "units": "all dimensionless",
        "orientation": "upward N_z=1 everywhere", "regular": "norm(N)>=1",
        "local_point": [.5, .5, .5], "r_u": [1, 0, 1], "r_v": [0, 1, 1],
        "N": [-1, -1, 1], "local_area_density": float(np.sqrt(3)),
        "local_unit_normal": (np.array([-1, -1, 1])/np.sqrt(3)).tolist(),
        "flux_up_quadrature": flux, "flux_up_exact": 1, "flux_down_exact": -1,
        "area_quadrature_order_32": area, "area_exact": exact_area(),
        "area_formula": "1+(7*log(5)-atan(4/3))/12",
        "display_patch_delta": .2, "normal_arrow_display_length": .42,
        "font_file_observed": font_path, "numpy_version": np.__version__,
        "evidence": "local numeric and generated files only; no Obsidian or learner validation"
    }, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"flux": flux, "area": area, "area_exact": exact_area(), "font": font_path}))


if __name__ == "__main__":
    main()
