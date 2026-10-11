#!/usr/bin/env python3
"""Exact finite release distributions for a synthetic appointment cohort.

No sampling, personal data, model training, or legal compliance assessment.
All event probabilities use Fraction; exp(epsilon)=3 for M0.
"""
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path


def events(support):
    for n in range(len(support) + 1):
        yield from (set(x) for x in combinations(support, n))


def m0(count):
    # Randomized response to the fixed predicate count >= 10.
    high = int(count >= 10)
    return {high: Fraction(3, 4), 1 - high: Fraction(1, 4)}


def probability(distribution, event):
    return sum((p for x, p in distribution.items() if x in event), Fraction())


def main():
    base = Path(__file__).resolve().parent
    fixture = json.loads((base / "input.json").read_text())
    rows = fixture["records"]
    ids = [r["pid"] for r in rows]
    assert len(ids) == len(set(ids)) == 10
    assert set(ids) == {r["pid"] for r in fixture["mapping"]}
    assert all(r["slot"] == "2026-06-01 morning" for r in rows)
    other = [r for r in rows if r["pid"] != fixture["target_id"]]
    q, qp = len(rows), len(other)
    assert (q, qp) == (10, 9)
    left, right = m0(q), m0(qp)
    # All four events of the binary component, in both adjacency directions.
    component_events = list(events([0, 1]))
    assert all(probability(a, e) <= 3 * probability(b, e)
               for a, b in [(left, right), (right, left)]
               for e in component_events)
    joint_left = {(bit, q): p for bit, p in left.items()}
    joint_right = {(bit, qp): p for bit, p in right.items()}
    support = sorted(set(joint_left) | set(joint_right))
    joint_events = list(events(support))
    witness = {x for x in support if x[1] == 10}
    p_left = probability(joint_left, witness)
    p_right = probability(joint_right, witness)
    assert (p_left, p_right) == (1, 0)
    violations = sum(probability(joint_left, e) > 3 * probability(joint_right, e)
                     for e in joint_events)
    result = {
        "scenario": fixture["scenario"], "q_D": q, "q_D_prime": qp,
        "M0_exp_epsilon": 3, "M0_delta": 0,
        "M0_D": {str(k): str(v) for k, v in sorted(left.items())},
        "M0_D_prime": {str(k): str(v) for k, v in sorted(right.items())},
        "M0_event_count": len(component_events),
        "M0_both_directions_all_events_pass": True,
        "joint_D": {str(k): str(v) for k, v in sorted(joint_left.items())},
        "joint_D_prime": {str(k): str(v) for k, v in sorted(joint_right.items())},
        "joint_event_count": len(joint_events),
        "joint_forward_violations_at_exp_epsilon_3_delta_0": violations,
        "witness": "second coordinate equals 10",
        "witness_probability_D": str(p_left),
        "witness_probability_D_prime": str(p_right),
        "witness_required_delta_at_any_finite_epsilon": "1",
        "scope": "exact finite event check; no legal or runtime service claim",
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (base / "result.json").write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
