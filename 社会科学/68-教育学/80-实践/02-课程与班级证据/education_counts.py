#!/usr/bin/env python3
"""Exact synthetic classroom weighting, sharp-null enumeration and missing bounds.

No participant data, model fitting, independent-student shuffle or causal claims.
"""
import argparse
import csv
from fractions import Fraction as F
from html import escape
from itertools import combinations
import json
from pathlib import Path


def keys(obj, expected, label):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ValueError(f"{label}: expected keys {sorted(expected)}")


def integer(value, lower, label):
    if type(value) is not int or not lower <= value <= 1000000:
        raise ValueError(f"{label}: integer in [{lower},1000000] required")


def validate(data):
    keys(data, {"provenance", "classes", "missing_scenario"}, "root")
    if data["provenance"] != "synthetic teaching counts; no participants or school records":
        raise ValueError("provenance: synthetic teaching input only")
    classes = data["classes"]
    if not isinstance(classes, list) or len(classes) != 4:
        raise ValueError("exactly four classes required for this finite design")
    seen = set()
    for row in classes:
        keys(row, {"id", "plan", "n", "success"}, "class")
        if not isinstance(row["id"], str) or not row["id"] or row["id"] in seen:
            raise ValueError("class id must be a unique nonempty string")
        seen.add(row["id"])
        if row["plan"] not in ("A", "B"):
            raise ValueError("plan must be A or B")
        integer(row["n"], 1, "class n")
        integer(row["success"], 0, "class success")
        if row["success"] > row["n"]:
            raise ValueError("success exceeds class n")
    if sum(row["plan"] == "A" for row in classes) != 2:
        raise ValueError("exactly two classes per plan required")
    keys(data["missing_scenario"], {"A", "B"}, "missing scenario")
    for label, row in data["missing_scenario"].items():
        keys(row, {"assigned", "observed", "success"}, label)
        for name in row:
            integer(row[name], 1 if name == "assigned" else 0, f"{label} {name}")
        if not 0 <= row["success"] <= row["observed"] <= row["assigned"]:
            raise ValueError("require success <= observed <= assigned")


def calculate(data):
    classes = data["classes"]
    rates = [F(row["success"], row["n"]) for row in classes]
    pooled, equal = {}, {}
    for plan in ("A", "B"):
        selected = [row for row in classes if row["plan"] == plan]
        pooled[plan] = F(sum(row["success"] for row in selected), sum(row["n"] for row in selected))
        equal[plan] = sum((F(row["success"], row["n"]) for row in selected), F(0)) / 2
    enumeration = []
    for chosen in combinations(range(4), 2):
        treatment = sum((rates[i] for i in chosen), F(0)) / 2
        control = sum((rates[i] for i in range(4) if i not in chosen), F(0)) / 2
        enumeration.append({"A_classes": [classes[i]["id"] for i in chosen], "T": treatment - control})
    observed_t = equal["A"] - equal["B"]
    tail = sum(abs(row["T"]) >= abs(observed_t) for row in enumeration)
    missing = {}
    for label, row in data["missing_scenario"].items():
        unobserved = row["assigned"] - row["observed"]
        missing[label] = {
            "observed_rate": F(row["success"], row["observed"]) if row["observed"] else None,
            "bounds": [F(row["success"], row["assigned"]), F(row["success"] + unobserved, row["assigned"])],
        }
    lower = missing["A"]["bounds"][0] - missing["B"]["bounds"][1]
    upper = missing["A"]["bounds"][1] - missing["B"]["bounds"][0]
    return {
        "provenance": data["provenance"],
        "pooled_student_rates": pooled,
        "equal_class_rates": equal,
        "observed_equal_class_difference": observed_t,
        "sharp_null": {
            "assumptions": "two of four classes assigned A uniformly; fixed outcomes under no effect on anyone; no interference",
            "enumeration": enumeration,
            "two_sided_rule": "abs(T) >= abs(T_observed), including ties",
            "tail_count": tail,
            "assignments": len(enumeration),
            "p_exact": F(tail, len(enumeration)),
        },
        "missing_scenario": missing,
        "missing_A_minus_B_bounds": [lower, upper],
        "boundary": "arithmetic for synthetic data only; bounds are not confidence intervals; no real learning or treatment effects observed",
    }


def percentage(rate):
    return f"{float(rate * 100):.2f}".rstrip("0").rstrip(".") + "%"


def make_svg(data, result):
    bars = []
    for plan in ("A", "B"):
        selected = [row for row in data["classes"] if row["plan"] == plan]
        s, n = sum(x["success"] for x in selected), sum(x["n"] for x in selected)
        bars.append((f"学生等权 {plan}", result["pooled_student_rates"][plan], f"{s}/{n}", "#245f91"))
    for plan in ("A", "B"):
        selected = [row for row in data["classes"] if row["plan"] == plan]
        explanation = "(" + "+".join(percentage(F(x["success"], x["n"])) for x in selected) + ")/2"
        bars.append((f"班级等权 {plan}", result["equal_class_rates"][plan], explanation, "#805219"))
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="460" viewBox="0 0 860 460" role="img" aria-labelledby="title desc">',
        '<title id="title">同一合成班级计数的两种权重</title>',
        '<desc id="desc">学生等权和班级等权的成功比例。标签与高度均由输入计数计算；仅教学合成数据，无真实学习效果。</desc>',
        '<rect width="860" height="460" fill="white"/>',
        '<g font-family="Hiragino Sans GB,Microsoft YaHei,Arial Unicode MS,sans-serif" fill="#172635">',
        '<text x="80" y="35" font-size="23">同一计数，先确定平均的是谁</text>',
        '<text x="80" y="64" font-size="15">合成班级数据；成功比例（%），纵轴从0开始</text>',
    ]
    for percent in range(0, 101, 20):
        y = 350 - 2.4 * percent
        pieces.append(f'<line x1="80" x2="815" y1="{y:g}" y2="{y:g}" stroke="#d6dfe6"/>')
        pieces.append(f'<text x="65" y="{y+5:g}" font-size="14" text-anchor="end">{percent}</text>')
    for i, (label, rate, note, color) in enumerate(bars):
        x = 133 + i * 175
        height = float(rate) * 240
        pieces.append(f'<rect x="{x}" y="{350-height:g}" width="95" height="{height:g}" fill="{color}"/>')
        pieces.append(f'<text x="{x+47.5:g}" y="{338-height:g}" font-size="19" text-anchor="middle">{percentage(rate)}</text>')
        pieces.append(f'<text x="{x+47.5:g}" y="378" font-size="16" text-anchor="middle">{escape(label)}</text>')
        pieces.append(f'<text x="{x+47.5:g}" y="404" font-size="14" text-anchor="middle">{escape(note)}</text>')
    pieces.append('<text x="80" y="442" font-size="14">权重不同产生不同描述；未给分配经过，不解释为教学因果效果。</text></g></svg>')
    return "\n".join(pieces) + "\n"


def serializable(obj):
    if isinstance(obj, F):
        return str(obj)
    if isinstance(obj, list):
        return [serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: serializable(value) for key, value in obj.items()}
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        validate(data)
        result = calculate(data)
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "exact-results.json").write_text(json.dumps(serializable(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "class-weights.svg").write_text(make_svg(data, result), encoding="utf-8")
    with (args.out / "randomization.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["A_classes", "class_difference", "assignment_probability"])
        writer.writerows(["+".join(row["A_classes"]), str(row["T"]), "1/6"] for row in result["sharp_null"]["enumeration"])
    print("wrote exact-results.json, class-weights.svg, randomization.csv (synthetic only)")


if __name__ == "__main__":
    main()
