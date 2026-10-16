#!/usr/bin/env python3
"""Recount a fixed synthetic person-level exposure log using exact fractions."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path


def ratio(numerator, denominator):
    if denominator == 0:
        return None
    value = Fraction(numerator, denominator)
    return {"fraction": str(value), "percent": str(100 * value)}


def recount(path):
    counts = {group: {"eligible": 0, "exposed_unique": 0, "clicked_unique": 0}
              for group in ("A", "B")}
    seen = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {"group", "person_id", "exposed_unique", "clicked_unique"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError("expected one row per eligible person and four named fields")
        for row in reader:
            group, person = row["group"], row["person_id"]
            if group not in counts or not person or person in seen:
                raise ValueError("unknown group, blank ID, or duplicate eligible person")
            seen.add(person)
            if row["exposed_unique"] not in {"0", "1"} or row["clicked_unique"] not in {"0", "1"}:
                raise ValueError("person-level flags must be 0 or 1")
            exposed, clicked = int(row["exposed_unique"]), int(row["clicked_unique"])
            if clicked > exposed:
                raise ValueError("clicked person is not in the exposed set")
            current = counts[group]
            current["eligible"] += 1
            current["exposed_unique"] += exposed
            current["clicked_unique"] += clicked
    for current in counts.values():
        n, e, c = current.values()
        current["exposure_rate"] = ratio(e, n)
        current["person_click_given_exposure"] = ratio(c, e)
        current["target_person_click_rate"] = ratio(c, n)
        # This exact identity checks the nested sets; it does not identify causation.
        if n and e:
            assert Fraction(e, n) * Fraction(c, e) == Fraction(c, n)
    return {"data_kind": "synthetic teaching log; not a platform experiment",
            "unit": "unique eligible person within one fixed 24-hour window",
            "groups": counts,
            "not_observed": ["attention", "reading", "understanding", "agreement", "causal effect"]}


def main():
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=here / "固定曝光记录.csv")
    parser.add_argument("--output", type=Path, default=here / "results" / "exact-counts.json")
    args = parser.parse_args()
    report = recount(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
