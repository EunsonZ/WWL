#!/usr/bin/env python3
"""Exact synthetic potential-outcome tables; no observed counterfactual labels."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path


def probability(value):
    if not isinstance(value, str):
        raise ValueError("probabilities must be strings, e.g. '1/5'")
    result = Fraction(value)
    if not 0 <= result <= 1:
        raise ValueError("probability outside [0, 1]")
    return result


def checked_table(values):
    if len(values) != 4:
        raise ValueError("type order requires exactly four entries: 11,10,01,00")
    result = tuple(probability(x) for x in values)
    if sum(result) != 1:
        raise ValueError("four type probabilities must sum to one")
    return result


def margins(table):
    p11, p10, p01, _ = table
    return p11 + p10, p11 + p01


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument("--input", type=Path, default=here / "inputs.json")
    parser.add_argument("--output-dir", type=Path, default=here / "outputs")
    args = parser.parse_args()
    try:
        config = json.loads(args.input.read_text(encoding="utf-8"))
        p1, p0 = probability(config["p1"]), probability(config["p0"])
        if p1 == 0:
            raise ValueError("PN requires positive probability of A=1,Y=1")
        q_min, q_max = max(Fraction(0), p1 + p0 - 1), min(p1, p0)
        cases = []
        names = set()
        for case in config["q_cases"]:
            name, q = case["name"], probability(case["q"])
            if not isinstance(name, str) or not name or name in names:
                raise ValueError("case names must be distinct nonempty strings")
            names.add(name)
            if not q_min <= q <= q_max:
                raise ValueError(f"{name}: q violates four-cell nonnegativity")
            table = (q, p1 - q, p0 - q, 1 - p1 - p0 + q)
            # Recompute from the four cells rather than copy declared margins.
            m1, m0 = margins(table)
            pn = table[1] / m1
            if sum(table) != 1 or min(table) < 0 or (m1, m0) != (p1, p0):
                raise ValueError("invalid reconstructed joint distribution")
            cases.append({"name": name, "q": str(q),
                          "types_11_10_01_00": [str(x) for x in table],
                          "p1": str(m1), "p0": str(m0), "ate": str(m1 - m0),
                          "pn_under_joint_independence": str(pn),
                          "monotone_y1_ge_y0": table[2] == 0})
        if not cases:
            raise ValueError("at least one q case required")
        separate = config["separate_independence_example"]
        a_prob = probability(separate["assignment_probability"])
        if not 0 < a_prob < 1:
            raise ValueError("both assignment groups require positive probability")
        a1 = checked_table(separate["types_given_a1"])
        a0 = checked_table(separate["types_given_a0"])
        if margins(a1) != margins(a0):
            raise ValueError("separate-independence example must have equal margins")
        population = tuple(a_prob * u + (1 - a_prob) * v for u, v in zip(a1, a0))
        selected_p1, selected_p0 = margins(a1)
        population_p1, population_p0 = margins(population)
        if selected_p1 == 0 or population_p1 == 0:
            raise ValueError("separate-independence example PN denominator is zero")
        selected_pn = a1[1] / selected_p1
        population_ratio = population[1] / population_p1
        report = {
            "scope": "exact synthetic model; not a confidence interval or legal probability",
            "type_order": ["11", "10", "01", "00"],
            "q_bounds": [str(q_min), str(q_max)],
            "pn_bounds_under_joint_independence": [str((p1 - q_max) / p1),
                                                   str((p1 - q_min) / p1)],
            "cases": cases,
            "separate_independence_example": {
                "assignment_probability": str(a_prob),
                "types_given_a1": [str(x) for x in a1],
                "types_given_a0": [str(x) for x in a0],
                "population_types": [str(x) for x in population],
                "p1_in_both_groups": str(selected_p1),
                "p0_in_both_groups": str(selected_p0),
                "actual_conditional_pn": str(selected_pn),
                "population_joint_ratio": str(population_ratio),
                "joint_independence": a1 == a0,
                "ratio_equality": selected_pn == population_ratio
            }
        }
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OSError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "exact-results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.output_dir / "exact-table.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["case", "q", "p11", "p10", "p01", "p00", "p1", "p0", "ate", "pn"])
        for case in cases:
            writer.writerow([case["name"], case["q"], *case["types_11_10_01_00"],
                             case["p1"], case["p0"], case["ate"], case["pn_under_joint_independence"]])
    print(f"Computed {len(cases)} exact joint tables and one separate-independence example.")
    print(f"PN bounds: {report['pn_bounds_under_joint_independence']}")
    print(f"Separate-independence example: actual PN={selected_pn}; population ratio={population_ratio}")


if __name__ == "__main__":
    main()
