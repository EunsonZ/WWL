"""Independent finite-domain oracle for reviewer A/B execution, no network/files.

The source is imported from ../candidate/计算机知识/65-分布式系统. Expected
counter values come from sets of unique writer event ids, not join/max. LUB is
checked by enumerating all upper bounds independently over the fixed test domain.
Finite checks supplement the Markdown proof; they are not a general CRDT theorem.
"""
import importlib.util
from itertools import product, permutations
from pathlib import Path
import json

SOURCE = Path(__file__).resolve().parents[1] / "candidate/计算机知识/65-分布式系统/gcounter_join_examples.py"
spec = importlib.util.spec_from_file_location("gcounter_subject", SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


def order(x, y):
    return x[0] <= y[0] and x[1] <= y[1]


def event_set(state):
    return {("A", i) for i in range(1, state[0] + 1)} | {("B", i) for i in range(1, state[1] + 1)}


def check_all():
    states = list(product(range(4), repeat=2))
    pair_count = triple_count = schedule_count = 0
    for x, y in product(states, repeat=2):
        merged = subject.join(x, y)
        upper_bounds = [z for z in states if order(x, z) and order(y, z)]
        minima = [z for z in upper_bounds if all(order(z, w) for w in upper_bounds)]
        assert minima == [merged], (x, y, minima, merged)
        assert subject.value(merged) == len(event_set(x) | event_set(y))
        assert merged == subject.join(y, x)
        assert subject.join(x, x) == x
        pair_count += 1
    for x, y, z in product(states, repeat=3):
        assert subject.join(subject.join(x, y), z) == subject.join(x, subject.join(y, z))
        triple_count += 1
    messages = ((2, 0), (0, 3), (2, 0))
    expected_events = set().union(*(event_set(m) for m in messages))
    for sequence in set(permutations(messages)):
        actual = subject.fold(sequence)
        assert event_set(actual) == expected_events
        assert subject.value(actual) == 5
        schedule_count += 1
    failures = subject.conditions_fail()
    assert failures["shared_identity"]["query"] == 1
    assert failures["lost_state_reused_identity"]["query"] == 2
    assert failures["last_update_not_delivered"]["same"] is False
    assert failures["last_update_not_delivered"]["after_delivery"] == (2, 3)
    assert failures["wraparound"]["inflationary"] is False
    assert failures["wraparound"]["merged_with_old"] == (3, 0)
    assert failures["repeated_command"]["two_calls"] == (2, 0)
    assert failures["repeated_command"]["same_state_twice"] == (1, 0)
    booking = subject.booking_example()
    records = booking["merged_A"]
    overlaps = [(x[0], y[0]) for i, x in enumerate(records) for y in records[i+1:]
                if x[2] == y[2] and x[3] < y[4] and y[3] < x[4]]
    assert booking["same"] is True and overlaps == [("A:1", "B:1")]
    assert booking["capacity_holds"] is False
    return {"status": "PASS", "states": len(states), "LUB_pairs": pair_count,
            "ACI_triples": triple_count, "message_orders": schedule_count,
            "oracle": "upper-bound enumeration and event-id set union; independent of subject join",
            "failure_examples": failures, "booking_overlap": overlaps}


if __name__ == "__main__":
    print(json.dumps(check_all(), ensure_ascii=False, indent=2))
