#!/usr/bin/env python3
"""Synthetic Gaussian detection and finite paired-block analysis; standard library.

No stimuli, timing, recruitment, diagnosis, or clinical data collection.
"""
import argparse
import csv
from fractions import Fraction as F
from itertools import product
import json
import math
from pathlib import Path
from statistics import NormalDist


PROVENANCE = "synthetic teaching model and summaries; no participants"
FONT = "Hiragino Sans GB,Microsoft YaHei,Arial Unicode MS,sans-serif"


def keys(obj, expected, label):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f"{label}: expected keys {sorted(expected)}")


def real(x, low, high, label):
    if type(x) not in (int, float) or not math.isfinite(x) or not low <= x <= high:
        raise ValueError(f"{label}: finite number in [{low},{high}] required")


def integer(x, low, high, label):
    if type(x) is not int or not low <= x <= high:
        raise ValueError(f"{label}: integer in [{low},{high}] required")


def validate(data):
    keys(data, {"provenance", "signal_mean", "thresholds", "priors", "paired"}, "root")
    if data["provenance"] != PROVENANCE:
        raise ValueError("only explicitly synthetic teaching inputs accepted")
    real(data["signal_mean"], 0.125, 4, "signal mean")
    if not isinstance(data["thresholds"], list) or len(data["thresholds"]) != 2:
        raise ValueError("exactly two display thresholds required")
    for x in data["thresholds"]:
        real(x, -3, 3, "threshold")
    if not isinstance(data["priors"], list) or not 1 <= len(data["priors"]) <= 8:
        raise ValueError("one to eight priors required")
    for x in data["priors"]:
        real(x, 0.001, 0.999, "prior")
    rows = data["paired"]
    if not isinstance(rows, list) or not 2 <= len(rows) <= 16:
        raise ValueError("two to sixteen independent paired units required")
    seen = set()
    for row in rows:
        keys(row, {"id", "A_ms", "B_ms", "trials_each", "A_errors", "B_errors"}, "pair")
        if not isinstance(row["id"], str) or not row["id"].isdigit() or row["id"] in seen:
            raise ValueError("unique digit-only id required")
        seen.add(row["id"])
        integer(row["A_ms"], 1, 1000000, "A ms")
        integer(row["B_ms"], 1, 1000000, "B ms")
        integer(row["trials_each"], 1, 1000000, "trials")
        for name in ("A_errors", "B_errors"):
            integer(row[name], 0, row["trials_each"] - 1, name)


def tail(x):
    return math.erfc(x / math.sqrt(2)) / 2


def density(x, mean):
    return math.exp(-(x - mean) ** 2 / 2) / math.sqrt(2 * math.pi)


def calculate(data):
    mu = data["signal_mean"]
    points = []
    for k in data["thresholds"]:
        false_alarm, hit = tail(k), tail(k - mu)
        zh, zf = NormalDist().inv_cdf(hit), NormalDist().inv_cdf(false_alarm)
        points.append({"threshold_k": k, "F": false_alarm, "H": hit,
                       "dprime_from_rates": zh - zf, "criterion_C": -(zh + zf) / 2,
                       "accuracy": [{"prior": p, "value": p * hit + (1 - p) * (1 - false_alarm),
                                     "equal_cost_optimal_k": mu / 2 + math.log((1 - p) / p) / mu}
                                    for p in data["priors"]]})
    differences = [row["B_ms"] - row["A_ms"] for row in data["paired"]]
    n = len(differences)
    mean = F(sum(differences), n)
    variance = sum(((F(x) - mean) ** 2 for x in differences), F(0)) / (n - 1)
    flips = [(signs, sum((s * d for s, d in zip(signs, differences)), 0))
             for signs in product((-1, 1), repeat=n)]
    observed_sum = sum(differences)
    tail_count = sum(abs(total) >= abs(observed_sum) for _, total in flips)
    trials = sum(row["trials_each"] for row in data["paired"])
    results = {
        "provenance": PROVENANCE,
        "gaussian_model": {"noise_mean": 0, "signal_mean": mu, "both_sd": 1, "points": points},
        "paired": {"n_people": n, "unit": "ms; mean of each person's correct-response median difference B-A",
                   "differences_ms": differences, "mean_ms_exact": str(mean),
                   "sample_variance_ms2_exact": str(variance), "sample_sd_ms": math.sqrt(float(variance)),
                   "A_error_rate_exact": str(F(sum(row["A_errors"] for row in data["paired"]), trials)),
                   "B_error_rate_exact": str(F(sum(row["B_errors"] for row in data["paired"]), trials)),
                   "sign_flip_assumptions": "independent equal-probability block order; no carryover; sharp no-effect null at both periods",
                   "two_sided_rule": "absolute mean >= observed absolute mean; including ties",
                   "tail_count": tail_count, "allocations": len(flips),
                   "p_exact": str(F(tail_count, len(flips)))},
        "boundary": "synthetic summaries only; no raw trials reconstructed; no real psychological or clinical effect estimated",
    }
    curves = []
    for i in range(181):
        x = -4 + i * 0.05
        curves.append((x, density(x, 0), density(x, mu), tail(x), tail(x - mu)))
    return results, flips, curves


def svg_start(title, desc, width=900, height=460):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{title}</title><desc id="desc">{desc}</desc>',
            f'<rect width="{width}" height="{height}" fill="white"/><g font-family="{FONT}" fill="#1b2938">']


def polyline(points, color):
    values = " ".join(f"{x:.5f},{y:.5f}" for x, y in points)
    return f'<polyline points="{values}" fill="none" stroke="{color}" stroke-width="2.5"/>'


def detection_svg(data, result, curves):
    out = svg_start("固定证据分布与移动判准", "教学Gaussian分布与同一ROC；点由同输入方程生成，无真人数据")
    out += ['<text x="45" y="32" font-size="22">固定 d′，移动的是报告判准</text>',
            '<text x="45" y="60" font-size="14">合成模型：噪声N(0,1)，信号N(μ,1)；无真人刺激或表现</text>']
    for x0 in (60, 520):
        out.append(f'<path d="M{x0},100 V350 H{x0+320}" fill="none" stroke="#27394a"/>')
    for v in range(-4, 6):
        x = 60 + (v + 4) / 9 * 320
        out.append(f'<text x="{x:.3f}" y="373" font-size="13" text-anchor="middle">{v}</text>')
    out += ['<text x="60" y="88" font-size="15">概率密度</text>',
            '<text x="220" y="400" font-size="15" text-anchor="middle">标准化证据 x（噪声SD单位）</text>',
            '<text x="520" y="88" font-size="15">命中率 H</text>',
            '<text x="680" y="400" font-size="15" text-anchor="middle">虚警率 F</text>']
    for v in (0, 0.2, 0.4):
        y = 350 - v / 0.45 * 250
        out.append(f'<text x="52" y="{y+5:.3f}" font-size="13" text-anchor="end">{v:g}</text>')
    for v in (0, .25, .5, .75, 1):
        out.append(f'<text x="{520+320*v:g}" y="373" font-size="13" text-anchor="middle">{v:g}</text>')
        out.append(f'<text x="510" y="{355-250*v:g}" font-size="13" text-anchor="end">{v:g}</text>')
    for idx, color in ((1, "#215f96"), (2, "#a14e18")):
        out.append(polyline([(60 + (r[0] + 4) / 9 * 320, 350 - r[idx] / .45 * 250) for r in curves], color))
    roc = [(520, 350)] + [(520 + r[3] * 320, 350 - r[4] * 250) for r in reversed(curves)] + [(840, 100)]
    out.append(polyline(roc, "#214d75"))
    for i, row in enumerate(result["gaussian_model"]["points"]):
        k = row["threshold_k"]
        x = 60 + (k + 4) / 9 * 320
        dash = "5 4" if i == 0 else "2 3"
        out += [f'<line x1="{x:.3f}" x2="{x:.3f}" y1="105" y2="350" stroke="#39484e" stroke-dasharray="{dash}"/>',
                f'<text x="{x+7:.3f}" y="{115+24*i}" font-size="14">k={k:g}</text>']
        rx, ry = 520 + row["F"] * 320, 350 - row["H"] * 250
        out.append(f'<circle cx="{rx:.3f}" cy="{ry:.3f}" r="5" fill="#ad3c24"/>')
        out.append(f'<text x="{rx+8:.3f}" y="{ry+18:.3f}" font-size="13">k={k:g}</text>')
    out += [f'<text x="70" y="429" font-size="14" fill="#215f96">噪声μ=0</text>',
            f'<text x="205" y="429" font-size="14" fill="#a14e18">信号μ={data["signal_mean"]:g}</text>',
            f'<text x="520" y="429" font-size="14">模型 d′={data["signal_mean"]:g}，阈值改变H与F</text>', '</g></svg>']
    return "\n".join(out) + "\n"


def paired_svg(data, result):
    ds = result["paired"]["differences_ms"]
    mean = float(F(result["paired"]["mean_ms_exact"]))
    low = min(0, min(ds)) - 10
    high = max(0, max(ds)) + 10
    def y(v):
        return 350 - (v - low) / (high - low) * 230
    out = svg_start("每人配对差与均值", "合成六人或变式配对中位数差；每点一个人，单位ms；不显示置信区间")
    out += ['<text x="65" y="35" font-size="22">每点一个人，保留配对与不同方向</text>',
            '<text x="65" y="65" font-size="14">合成正确反应中位数差 B-A（ms）；没有原始逐试次记录</text>',
            '<path d="M90,95 V350 H835" fill="none" stroke="#27394a"/>']
    ticks = sorted(set([low, 0, mean, high]))
    for value in ticks:
        out.append(f'<line x1="90" x2="835" y1="{y(value):.4f}" y2="{y(value):.4f}" stroke="#d4dce4"/>')
        out.append(f'<text x="80" y="{y(value)+5:.4f}" text-anchor="end" font-size="13">{value:g}</text>')
    for i, (row, value) in enumerate(zip(data["paired"], ds)):
        x = 125 + i / max(1, len(ds)-1) * 650
        out.append(f'<circle cx="{x:.4f}" cy="{y(value):.4f}" r="5" fill="#255d85"/>')
        out.append(f'<text x="{x:.4f}" y="{y(value)-12:.4f}" text-anchor="middle" font-size="14">{value}</text>')
        out.append(f'<text x="{x:.4f}" y="377" text-anchor="middle" font-size="14">ID {row["id"]}</text>')
    out += [f'<line x1="90" x2="835" y1="{y(mean):.4f}" y2="{y(mean):.4f}" stroke="#a14e18" stroke-dasharray="6 4"/>',
            f'<text x="90" y="420" font-size="15">均值 {mean:g} ms；线表示样本均值，不是个体定律或置信区间</text>', '</g></svg>']
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        validate(data)
        result, flips, curves = calculate(data)
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "exact-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.out / "detection.svg").write_text(detection_svg(data, result, curves), encoding="utf-8")
    (args.out / "paired.svg").write_text(paired_svg(data, result), encoding="utf-8")
    with (args.out / "curves.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["evidence_or_threshold", "noise_density", "signal_density", "F", "H"])
        writer.writerows(curves)
    with (args.out / "randomization.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["signs", "mean_difference_ms_exact"])
        writer.writerows([" ".join(str(x) for x in signs), str(F(total, len(data["paired"])))] for signs, total in flips)
    print("wrote 5 synthetic-only outputs; no participants or raw trials")


if __name__ == "__main__":
    main()
