#!/usr/bin/env python3
"""Reproduce selected Card--Krueger NJ/PA results with Python stdlib only.

The original data are downloaded from David Card's Berkeley data page and are
not redistributed here.  Units: one row per restaurant; employment is FTE per
restaurant; wages are nominal US dollars per hour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import urllib.request
import zipfile
from pathlib import Path

DATA_URL = "https://eml.berkeley.edu/~card/data_sets/njmin.zip"
ZIP_SHA256 = "41a29aec6b489658b20030d044a2b20a5f5a04b871cde41df057afd6013ba587"
PUBLIC_DAT_SHA256 = "04bde0cad5540980f32ce099c6dad369e2f05494698071d8a65b3e1cbe9ca53a"

COLUMNS = """SHEET CHAIN CO_OWNED STATE SOUTHJ CENTRALJ NORTHJ PA1 PA2 SHORE
NCALLS EMPFT EMPPT NMGRS WAGE_ST INCTIME FIRSTINC BONUS PCTAFF MEALS OPEN
HRSOPEN PSODA PFRY PENTREE NREGS NREGS11 TYPE2 STATUS2 DATE2 NCALLS2 EMPFT2
EMPPT2 NMGRS2 WAGE_ST2 INCTIME2 FIRSTIN2 SPECIAL2 MEALS2 OPEN2R HRSOPEN2
PSODA2 PFRY2 PENTREE2 NREGS2 NREGS112""".split()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(destination: Path) -> Path:
    """Download the official ZIP, verify it, and extract public.dat."""
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "njmin.zip"
    urllib.request.urlretrieve(DATA_URL, archive)
    if sha256(archive) != ZIP_SHA256:
        archive.unlink(missing_ok=True)
        raise ValueError("njmin.zip SHA-256 mismatch; file removed")
    with zipfile.ZipFile(archive) as bundle:
        payload = bundle.read("public.dat")
    data_path = destination / "public.dat"
    data_path.write_bytes(payload)
    if sha256(data_path) != PUBLIC_DAT_SHA256:
        data_path.unlink(missing_ok=True)
        raise ValueError("public.dat SHA-256 mismatch; file removed")
    return data_path


def parse_number(token: str) -> float | None:
    return None if token == "." else float(token)


def read_rows(path: Path, verify_hash: bool = True) -> list[dict[str, float | None]]:
    if verify_hash and sha256(path) != PUBLIC_DAT_SHA256:
        raise ValueError("public.dat SHA-256 differs from the pinned author file")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        values = line.split()
        if len(values) != len(COLUMNS):
            raise ValueError(f"line {line_number}: expected 46 fields, got {len(values)}")
        row = dict(zip(COLUMNS, map(parse_number, values)))
        row["FTE1"] = fte(row, "")
        row["FTE2"] = fte(row, "2")
        rows.append(row)
    return rows


def fte(row: dict[str, float | None], suffix: str) -> float | None:
    values = [row[f"EMPFT{suffix}"], row[f"EMPPT{suffix}"], row[f"NMGRS{suffix}"]]
    if any(value is None for value in values):
        return None
    full, part, managers = values
    assert full is not None and part is not None and managers is not None
    return full + 0.5 * part + managers


def mean_present(rows: list[dict[str, float | None]], name: str) -> tuple[int, float]:
    values = [row[name] for row in rows if row[name] is not None]
    return len(values), statistics.fmean(values)  # type: ignore[arg-type]


def summarize(rows: list[dict[str, float | None]]) -> dict:
    if len(rows) != 410:
        raise ValueError(f"expected 410 restaurants, got {len(rows)}")
    states = {"PA": [r for r in rows if r["STATE"] == 0], "NJ": [r for r in rows if r["STATE"] == 1]}
    result: dict[str, object] = {"restaurants": len(rows), "states": {}, "status2": {}}
    changes: dict[str, list[float]] = {}
    for state, group in states.items():
        n1, pre = mean_present(group, "FTE1")
        n2, post = mean_present(group, "FTE2")
        balanced = [r for r in group if r["FTE1"] is not None and r["FTE2"] is not None]
        delta = [float(r["FTE2"] - r["FTE1"]) for r in balanced]  # type: ignore[operator]
        changes[state] = delta
        w1n, wage1 = mean_present(group, "WAGE_ST")
        w2n, wage2 = mean_present(group, "WAGE_ST2")
        result["states"][state] = {  # type: ignore[index]
            "restaurants": len(group),
            "fte_pre_n": n1, "fte_pre_mean": pre,
            "fte_post_n": n2, "fte_post_mean": post,
            "fte_change_of_means": post - pre,
            "balanced_n": len(delta), "balanced_change_mean": statistics.fmean(delta),
            "wage_pre_n": w1n, "wage_pre_mean": wage1,
            "wage_post_n": w2n, "wage_post_mean": wage2,
        }
    did_all = (result["states"]["NJ"]["fte_change_of_means"]  # type: ignore[index]
               - result["states"]["PA"]["fte_change_of_means"])  # type: ignore[index]
    did_balanced = statistics.fmean(changes["NJ"]) - statistics.fmean(changes["PA"])
    se = math.sqrt(statistics.variance(changes["NJ"]) / len(changes["NJ"])
                   + statistics.variance(changes["PA"]) / len(changes["PA"]))
    result["did"] = {
        "all_available_change_of_means": did_all,
        "balanced_change_mean": did_balanced,
        "balanced_naive_se": se,
        "balanced_t": did_balanced / se,
        "balanced_95ci_normal": [did_balanced - 1.96 * se, did_balanced + 1.96 * se],
    }
    def change_did(sample: list[dict[str, float | None]]) -> dict[str, float | int]:
        by_state = {
            state: [float(r["FTE2"] - r["FTE1"]) for r in sample
                    if r["STATE"] == state and r["FTE1"] is not None and r["FTE2"] is not None]
            for state in (0, 1)
        }
        return {
            "n": len(by_state[0]) + len(by_state[1]), "nj_n": len(by_state[1]), "pa_n": len(by_state[0]),
            "estimate": statistics.fmean(by_state[1]) - statistics.fmean(by_state[0]),
        }
    def binary_ols(sample: list[dict[str, float | None]]) -> dict[str, float | int]:
        """OLS of FTE change on intercept and NJ; report classical and HC1 SE."""
        groups = {
            state: [float(r["FTE2"] - r["FTE1"]) for r in sample
                    if r["STATE"] == state and r["FTE1"] is not None and r["FTE2"] is not None]
            for state in (0, 1)
        }
        means = {state: statistics.fmean(values) for state, values in groups.items()}
        n = len(groups[0]) + len(groups[1])
        residual_ss = {
            state: sum((value - means[state]) ** 2 for value in values)
            for state, values in groups.items()
        }
        coefficient = means[1] - means[0]
        classical = math.sqrt(
            sum(residual_ss.values()) / (n - 2) * (1 / len(groups[0]) + 1 / len(groups[1]))
        )
        hc0_variance = sum(residual_ss[state] / len(groups[state]) ** 2 for state in (0, 1))
        hc1 = math.sqrt(hc0_variance * n / (n - 2))
        return {
            "n": n, "nj_n": len(groups[1]), "pa_n": len(groups[0]),
            "coefficient": coefficient,
            "classical_homoskedastic_se": classical,
            "hc1_heteroskedastic_robust_se": hc1,
        }
    answered = [r for r in rows if r["STATUS2"] == 1]
    table4 = [r for r in rows if r["FTE1"] is not None and r["FTE2"] is not None
              and (r["STATUS2"] == 3 or (r["WAGE_ST"] is not None and r["WAGE_ST2"] is not None))]
    temporary_zero = []
    for original in rows:
        row = original.copy()
        if row["STATUS2"] in (2, 4, 5) and row["FTE1"] is not None:
            row["FTE2"] = 0.0
        temporary_zero.append(row)
    result["sample_variants"] = {
        "balanced": change_did(rows),
        "answered_status1": change_did(answered),
        "table4_valid_employment_and_wages": change_did(table4),
        "temporary_closures_as_zero": change_did(temporary_zero),
        "table4_unadjusted_regression": binary_ols(table4),
    }
    for status in range(6):
        result["status2"][str(status)] = sum(r["STATUS2"] == status for r in rows)  # type: ignore[index]
    return result


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_lines(result: dict, path: Path, measure: str) -> None:
    """Write an accessible two-state pre/post line chart from the real-data means."""
    if measure == "fte":
        keys = ("fte_pre_mean", "fte_post_mean")
        title, subtitle, ymin, ymax, ticks = (
            "餐馆平均就业：政策前后", "FTE/店；每名兼职计0.5，经理计1", 19.0, 24.0, range(19, 25))
        colors = {"PA": "#b45309", "NJ": "#2563eb"}
        filename_desc = "Card–Krueger公开数据中NJ与PA两期店均FTE"
    else:
        keys = ("wage_pre_mean", "wage_post_mean")
        title, subtitle, ymin, ymax, ticks = (
            "平均起薪：政策前后", "名义美元/小时；各期按非缺失回答计算", 4.5, 5.2, [4.5, 4.7, 4.9, 5.1])
        colors = {"PA": "#b45309", "NJ": "#2563eb"}
        filename_desc = "Card–Krueger公开数据中NJ与PA两期平均起薪"
    width, height = 760, 500
    left, right, top, bottom = 90, 690, 100, 410
    x = [230, 550]
    def y(value: float) -> float:
        return bottom - (value - ymin) / (ymax - ymin) * (bottom - top)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title><desc id="desc">{esc(filename_desc)}。点旁标出精确到两位小数的均值。</desc>',
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        f'<text x="{left}" y="42" font-size="25" font-weight="700" fill="#172033">{esc(title)}</text>',
        f'<text x="{left}" y="70" font-size="15" fill="#475569">{esc(subtitle)}</text>',
    ]
    for tick in ticks:
        yy = y(float(tick))
        parts += [f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="#d8dee9"/>',
                  f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end" font-size="14" fill="#475569">{tick:g}</text>']
    for xx, label in zip(x, ["1992年2–3月", "1992年11–12月"]):
        parts.append(f'<text x="{xx}" y="445" text-anchor="middle" font-size="15" fill="#334155">{label}</text>')
    for state in ("PA", "NJ"):
        vals = [float(result["states"][state][key]) for key in keys]  # type: ignore[index]
        color = colors[state]
        parts.append(f'<path d="M{x[0]},{y(vals[0]):.1f} L{x[1]},{y(vals[1]):.1f}" fill="none" stroke="{color}" stroke-width="5"/>')
        for index, (xx, val) in enumerate(zip(x, vals)):
            if measure == "fte" and index == 1:
                label_y = y(val) + (-20 if state == "PA" else 28)
            elif measure == "wage" and index == 0:
                label_y = y(val) + (-22 if state == "PA" else 30)
            else:
                label_y = y(val) - 10
            parts += [f'<circle cx="{xx}" cy="{y(val):.1f}" r="8" fill="{color}"/>',
                      f'<text x="{xx+13}" y="{label_y:.1f}" font-size="16" font-weight="700" fill="{color}">{state} {val:.2f}</text>']
    parts += [f'<text x="{left}" y="480" font-size="13" fill="#64748b">来源：Card作者官网 njmin.zip；脚本按codebook复算。线仅连接两期均值，不证明平行趋势。</text>', '</svg>']
    path.write_text("\n".join(parts), encoding="utf-8")


def run(data_path: Path, output_dir: Path) -> dict:
    rows = read_rows(data_path)
    result = summarize(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "reference_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    svg_lines(result, output_dir / "01-employment-did.svg", "fte")
    svg_lines(result, output_dir / "02-starting-wage.svg", "wage")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", type=Path, help="download and verify official data into DIR")
    parser.add_argument("--data", type=Path, help="path to verified public.dat")
    parser.add_argument("--out", type=Path, default=Path("generated"))
    args = parser.parse_args()
    data_path = fetch(args.fetch) if args.fetch else args.data
    if data_path is None:
        parser.error("provide --data FILE or --fetch DIR")
    result = run(data_path, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
