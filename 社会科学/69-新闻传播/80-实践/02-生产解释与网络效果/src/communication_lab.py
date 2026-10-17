"""Exact synthetic newsroom choices and design-based network effects.

No scraping, publishing, participant data, training, or statistical inference
about real audiences. Fractions in JSON are exact strings, not rounded floats.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import html
import itertools
import json
from pathlib import Path


CONDITIONS = ((0, 0), (0, 1), (1, 0), (1, 1))
OUTCOMES = ("knowledge", "attitude", "behavior")


def integer(value, name, minimum=None):
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"invalid integer: {name}")
    return value


def validate(data):
    nw = data["network"]
    n = integer(nw["n"], "n", 2)
    if n > 12:
        raise ValueError("exact enumeration limited to n <= 12")
    p = F(nw["probability"])
    if not 0 < p < 1:
        raise ValueError("Bernoulli probability must be strictly between 0 and 1")
    seen = set()
    for edge in nw["edges"]:
        if len(edge) != 2:
            raise ValueError("each edge has two endpoints")
        a, b = (integer(x, "endpoint", 0) for x in edge)
        if a >= n or b >= n or a == b:
            raise ValueError("simple graph requires valid distinct endpoints")
        pair = tuple(sorted((a, b)))
        if pair in seen:
            raise ValueError("duplicate undirected edge")
        seen.add(pair)
    for key in ("knowledge_base", "attitude_direct", "attitude_neighbor", "behavior"):
        if len(nw[key]) != n:
            raise ValueError(f"wrong length: {key}")
        for x in nw[key]:
            integer(x, key)
    integer(nw["attitude_base"], "attitude_base")
    for z, e in CONDITIONS:
        for i in range(n):
            vals = potential(nw, i, z, e)
            if not 0 <= vals["knowledge"] <= 4 or not 1 <= vals["attitude"] <= 5:
                raise ValueError("synthetic scores outside declared scales")
            if vals["behavior"] not in (0, 1):
                raise ValueError("behavior must be binary")
    nr = data["newsroom"]
    if F(nr["lambda"]) < 0 or F(nr["budget"]) < 0:
        raise ValueError("negative newsroom parameter")
    if any(F(p) < 0 for p in nr["p_grid"]):
        raise ValueError("negative commercial weight")
    ids = []
    for c in nr["candidates"]:
        ids.append(c["id"])
        if type(c["verified"]) is not bool or F(c["cost_hours"]) < 0:
            raise ValueError("invalid candidate constraint")
        F(c["v"]); F(c["r"])
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("candidate identifiers must be nonempty and unique")
    missing_bounds(data["missing"])


def potential(nw, i, z, e):
    return {
        "knowledge": nw["knowledge_base"][i] + z + e,
        "attitude": nw["attitude_base"] + nw["attitude_direct"][i] * z
        + nw["attitude_neighbor"][i] * e,
        "behavior": nw["behavior"][i],
    }


def choice(nr, commercial, budget=None, require_verification=True):
    budget = F(nr["budget"]) if budget is None else F(budget)
    rows = []
    for c in nr["candidates"]:
        score = F(nr["lambda"]) * F(c["v"]) + F(commercial) * F(c["r"]) - F(c["cost_hours"])
        feasible = F(c["cost_hours"]) <= budget and (c["verified"] or not require_verification)
        rows.append({"id": c["id"], "score": score, "feasible": feasible})
    feasible = [r for r in rows if r["feasible"]]
    best = max((r["score"] for r in feasible), default=None)
    return {"commercial": F(commercial), "budget": budget,
            "require_verification": require_verification, "candidates": rows,
            "optimal": [r["id"] for r in feasible if r["score"] == best]}


def exposures(nw, assignment):
    neighbors = [set() for _ in range(nw["n"])]
    for a, b in nw["edges"]:
        neighbors[a].add(b); neighbors[b].add(a)
    return [(assignment[i], int(any(assignment[j] for j in neighbors[i])))
            for i in range(nw["n"])]


def label(d):
    return f"{d[0]}{d[1]}"


def design(nw, balanced=False):
    n, p = nw["n"], F(nw["probability"])
    assignments = list(itertools.product((0, 1), repeat=n))
    if balanced:
        if n % 2:
            raise ValueError("balanced example requires even population size")
        assignments = [z for z in assignments if sum(z) == n // 2]
    rows = []
    pi = [{d: F(0) for d in CONDITIONS} for _ in range(n)]
    for z in assignments:
        prob = F(1, len(assignments)) if balanced else p ** sum(z) * (1 - p) ** (n - sum(z))
        ds = exposures(nw, z)
        for i, d in enumerate(ds):
            pi[i][d] += prob
        rows.append({"assignment": list(z), "probability": prob, "exposure": ds})
    assert sum(r["probability"] for r in rows) == 1
    truth = {o: {label(d): sum(F(potential(nw, i, *d)[o]) for i in range(n)) / n
                 for d in CONDITIONS} for o in OUTCOMES}
    estimable = {d: all(pi[i][d] > 0 for i in range(n)) for d in CONDITIONS}
    for row in rows:
        values = [potential(nw, i, *d) for i, d in enumerate(row["exposure"])]
        row["observed"] = values
        row["ht"] = {o: {label(d): (
            sum((F(values[i][o]) / pi[i][d] for i in range(n) if row["exposure"][i] == d), F(0)) / n
            if estimable[d] else None) for d in CONDITIONS} for o in OUTCOMES}
    expectation = {o: {label(d): (sum(r["probability"] * r["ht"][o][label(d)] for r in rows)
                    if estimable[d] else None) for d in CONDITIONS} for o in OUTCOMES}
    ranges = {o: {label(d): ([min(r["ht"][o][label(d)] for r in rows),
                              max(r["ht"][o][label(d)] for r in rows)]
                             if estimable[d] else None) for d in CONDITIONS} for o in OUTCOMES}
    contrasts = {}
    for o in OUTCOMES:
        t = truth[o]
        contrasts[o] = {"direct_e0": t["10"] - t["00"], "direct_e1": t["11"] - t["01"],
                        "neighbor_z0": t["01"] - t["00"], "neighbor_z1": t["11"] - t["10"],
                        "joint_11_vs_00": t["11"] - t["00"]}
    return {"assignment_count": len(rows), "probabilities": [{label(d): v for d, v in r.items()} for r in pi],
            "estimable": {label(d): v for d, v in estimable.items()}, "truth": truth,
            "expected_ht": expectation, "ht_ranges": ranges, "contrasts": contrasts, "assignments": rows}


def missing_bounds(m):
    lo, hi = F(m["minimum"]), F(m["maximum"])
    if lo > hi:
        raise ValueError("reversed score limits")
    result = {}
    for group in ("A", "B"):
        x = m[group]
        total = integer(x["total"], "total", 1)
        observed = integer(x["observed"], "observed", 1)
        if observed > total or not lo * observed <= F(x["sum"]) <= hi * observed:
            raise ValueError("invalid observed count or score sum")
        missing = total - observed
        result[group] = {"complete_case_mean": F(x["sum"], observed),
                         "population_interval": [(F(x["sum"]) + missing * lo) / total,
                                                  (F(x["sum"]) + missing * hi) / total]}
    a, b = result["A"]["population_interval"], result["B"]["population_interval"]
    result["A_minus_B_interval"] = [a[0] - b[1], a[1] - b[0]]
    return result


def serial(value):
    if isinstance(value, float):
        raise TypeError("exact output must not contain binary floats")
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


def svg_start(width, height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<title>{html.escape(title)}</title>', '<desc>Generated from the fixed synthetic model.json input; no real audience or platform observations.</desc>', '<rect width="100%" height="100%" fill="#f7f8fa"/>',
            '<g font-family="sans-serif" fill="#182a3a">']


def text(parts, x, y, content, size=18, color="#182a3a"):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{html.escape(str(content))}</text>')


def choice_svg(nr):
    parts = svg_start(1000, 440, "Synthetic newsroom utility under verified facts and five-hour budget")
    text(parts, 35, 36, "Same facts and owner; change the commercial weight p", 24)
    text(parts, 35, 67, "Synthetic scores; lambda = 1; budget = 5 hours; no estimated real preferences", 17)
    colors = {"S": "#167d9a", "F": "#c35d24"}
    x0, y0, w, h = 80, 340, 720, 220
    parts.append(f'<path d="M{x0} 100 V{y0} H840" fill="none" stroke="#596b7c"/>')
    for tick in (0, 2, 4, 6):
        yy = y0-tick*h/6
        parts.append(f'<line x1="{x0-5}" y1="{yy:.3f}" x2="{x0}" y2="{yy:.3f}" stroke="#596b7c"/>')
        text(parts, x0-28, yy+6, tick, 16)
    for c in nr["candidates"]:
        if c["id"] not in colors:
            continue
        vals = [(F(nr["lambda"]) * F(c["v"]) + F(p) * F(c["r"]) - F(c["cost_hours"])) for p in (0, 1)]
        points = " ".join(f"{x0+int(p*w)},{y0-float(v)*h/6:.3f}" for p, v in zip((0, 1), vals))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colors[c["id"]]}" stroke-width="4"/>')
        text(parts, 850, y0-float(vals[1])*h/6+6, c["id"], 22, colors[c["id"]])
    parts.append('<path d="M440 90 V340" stroke="#697a8a" stroke-dasharray="6 5"/>')
    for p in (0, F(1, 2), 1):
        text(parts, x0+float(p)*w-12, 368, str(p))
    text(parts, 730, 396, "commercial weight p", 17)
    text(parts, 90, 100, "utility", 17)
    text(parts, 355, 92, "tie at p = 1/2", 17)
    text(parts, 40, 424, "H excluded: unsupported permanent-policy claim. V excluded: 8 hours > budget.", 17)
    return "\n".join(parts + ["</g></svg>"]) + "\n"


def network_svg(nw, bernoulli, balanced):
    parts = svg_start(1200, 560, "Synthetic cycle exposure probabilities and exact design expectations")
    text(parts, 30, 37, "Assignment is not understanding, endorsement, or behavior", 25)
    text(parts, 30, 70, "Any assigned neighbor: e = 1. Four-node cycle; independent Bernoulli(1/2).", 18)
    positions = [(85, 150), (290, 150), (290, 330), (85, 330)]
    for a, b in nw["edges"]:
        xa, ya = positions[a]; xb, yb = positions[b]
        parts.append(f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="#8195a5" stroke-width="4"/>')
    for i, (x, y) in enumerate(positions):
        parts.append(f'<circle cx="{x}" cy="{y}" r="24" fill="#e4eff4" stroke="#167d9a" stroke-width="3"/>')
        text(parts, x-6, y+7, i, 21)
    text(parts, 38, 405, "16 assignments, each probability 1/16", 17)
    text(parts, 420, 117, "Condition (z,e)", 20)
    for j, d in enumerate(CONDITIONS):
        text(parts, 690+j*115, 117, str(d), 18)
    for row, (caption, values) in enumerate([
        ("P(exposure), Bernoulli", bernoulli["probabilities"][0]),
        ("P(exposure), exactly 2 treated", balanced["probabilities"][0]),
        ("Knowledge: true mean", bernoulli["truth"]["knowledge"]),
        ("Knowledge: expected HT", bernoulli["expected_ht"]["knowledge"]),
        ("Attitude: true / expected HT", bernoulli["truth"]["attitude"]),
        ("Behavior: true / expected HT", bernoulli["truth"]["behavior"]),
    ]):
        yy = 163+row*45
        text(parts, 420, yy, caption, 17)
        for j, d in enumerate(CONDITIONS):
            text(parts, 705+j*115, yy, values[label(d)], 19,
                 "#b33d26" if row == 1 and d == (0, 0) else "#182a3a")
    text(parts, 35, 474, "One draw 0000: knowledge HT for (0,0) = 8, true mean = 1. Unbiasedness is an expectation.", 19)
    text(parts, 35, 510, "Exactly 2 treated: (0,0) impossible. No inverse weight can recover that missing exposure.", 19, "#b33d26")
    text(parts, 35, 542, "All numbers are synthetic. Scores and design come from inputs/model.json; no real audience observations.", 17)
    return "\n".join(parts + ["</g></svg>"]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--input", type=Path, default=default_root / "inputs/model.json")
    parser.add_argument("--output-dir", type=Path, default=default_root)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    validate(data)
    bernoulli, balanced = design(data["network"]), design(data["network"], balanced=True)
    result = {"identity": data["identity"], "newsroom": {
        "grid": [choice(data["newsroom"], p) for p in data["newsroom"]["p_grid"]],
        "budget4_p0": choice(data["newsroom"], 0, budget=4),
        "without_verification_p1": choice(data["newsroom"], 1, require_verification=False)},
        "bernoulli": bernoulli, "balanced": balanced, "missing": missing_bounds(data["missing"])}
    for folder in ("results", "assets"):
        (args.output_dir / folder).mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results/communication.json").write_text(json.dumps(serial(result), ensure_ascii=False, indent=2)+"\n")
    (args.output_dir / "assets/newsroom-choices.svg").write_text(choice_svg(data["newsroom"]))
    (args.output_dir / "assets/network-effects.svg").write_text(network_svg(data["network"], bernoulli, balanced))
    print(json.dumps({"bernoulli_assignments": bernoulli["assignment_count"],
                      "balanced_assignments": balanced["assignment_count"],
                      "optimal_grid": [r["optimal"] for r in result["newsroom"]["grid"]],
                      "outputs": ["results/communication.json", "assets/newsroom-choices.svg", "assets/network-effects.svg"]}))


if __name__ == "__main__":
    main()
