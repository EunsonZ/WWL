"""Finite state-based G-Counter illustrations; Python 3.10+, standard library.

Run: python3 -B gcounter_join_examples.py
A/B are fixed unique identities and sole writers of their own component. Local
updates/merges are serialized, natural numbers do not wrap, acknowledged state
is retained, and final updates eventually reach each correct replica. These are
assumptions, not services enforced by this pure-function teaching model.
Only already-produced states are merged. Repeated client intents are a separate
contract. Failure examples intentionally violate a stated assumption.
"""
from itertools import permutations
import json

IDENTITIES = ("A", "B")
ZERO = (0, 0)


def check(state):
    if not isinstance(state, tuple) or len(state) != len(IDENTITIES):
        raise ValueError("fixed two-component tuple required")
    if any(type(component) is not int or component < 0 for component in state):
        raise ValueError("natural-number components required")


def leq(left, right):
    check(left)
    check(right)
    return all(a <= b for a, b in zip(left, right))


def join(left, right):
    check(left)
    check(right)
    return tuple(max(a, b) for a, b in zip(left, right))


def increment(state, owner):
    check(state)
    if owner not in IDENTITIES:
        raise ValueError("unknown fixed identity")
    result = list(state)
    result[IDENTITIES.index(owner)] += 1
    return tuple(result)


def value(state):
    check(state)
    return sum(state)


def fold(messages):
    state = ZERO
    for message in messages:
        state = join(state, message)
    return state


def trace(messages):
    state = ZERO
    rows = []
    for message in messages:
        state = join(state, message)
        rows.append({"message": message, "state": state, "query": value(state)})
    return rows


def fixed_examples():
    p, q = (2, 0), (0, 3)
    sequences = sorted(set(permutations((p, q, p))))
    return {"p": p, "q": q, "message_sequences": [trace(s) for s in sequences],
            "grouped_left": join(join(p, p), q),
            "grouped_right": join(p, join(p, q)),
            "three_merges": {"scalar_max": max(2, 3, 2),
                             "scalar_sum": 2 + 3 + 2,
                             "vector_state": fold((p, q, p)),
                             "vector_query": value(fold((p, q, p)))}}


def conditions_fail():
    # Two independent writers wrongly use the same logical component.
    shared_identity = join(increment(ZERO, "A"), increment(ZERO, "A"))
    # Old acknowledged state 2 remains elsewhere; A resets and performs one more.
    after_loss = join((2, 0), increment(ZERO, "A"))
    # Without final propagation, states containing the last updates stay apart.
    undelivered_a, undelivered_b = (2, 0), (0, 3)
    # A deliberately broken four-valued integer implementation wraps 3 to 0.
    before_wrap, after_wrap = (3, 0), ((3 + 1) % 4, 0)
    return {
        "shared_identity": {"actual_increments": 2, "merged": shared_identity,
                            "query": value(shared_identity)},
        "lost_state_reused_identity": {"actual_increments": 3, "merged": after_loss,
                                       "query": value(after_loss)},
        "last_update_not_delivered": {"A": undelivered_a, "B": undelivered_b,
                                      "same": undelivered_a == undelivered_b,
                                      "after_delivery": join(undelivered_a, undelivered_b)},
        "wraparound": {"before": before_wrap, "after": after_wrap,
                       "inflationary": leq(before_wrap, after_wrap),
                       "merged_with_old": join(before_wrap, after_wrap),
                       "actual_increments": 4},
        # Transporting duplicate state and issuing another increment differ.
        "repeated_command": {"two_calls": increment(increment(ZERO, "A"), "A"),
                             "same_state_twice": join((1, 0), (1, 0))},
    }


def booking_example():
    # Distinct booking identities; one resource, same valid interval; no cancel.
    a = frozenset({("A:1", "甲", "room", 540, 600)})
    b = frozenset({("B:1", "乙", "room", 540, 600)})
    merged_a, merged_b = a | b, b | a
    return {"reads": {"A": [], "B": []}, "local_A": sorted(a), "local_B": sorted(b),
            "merged_A": sorted(merged_a), "merged_B": sorted(merged_b),
            "same": merged_a == merged_b,
            "capacity": 1, "active_same_slot": len(merged_a),
            "capacity_holds": len(merged_a) <= 1,
            "scope": "constructed no-coordination rule; not reservation_v2 execution"}


def main():
    report = {"fixed": fixed_examples(), "condition_failures": conditions_fail(),
              "booking": booking_example(), "boundary": "finite math; no real network or storage"}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
