"""Exact finite monitoring POMDP; no network, sampling, or third-party packages.

belief DP and the full-policy oracle use separate evaluation paths.
The model's hidden Y is static. The known horizon limits sensing opportunities.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
import json
from pathlib import Path


def exact(value: F | int | str) -> F:
    if isinstance(value, bool) or not isinstance(value, (F, int, str)):
        raise ValueError("use Fraction, integer, or exact numeric string")
    return F(value)


def distribution(values):
    row = tuple(exact(x) for x in values)
    if not row or any(x < 0 for x in row) or sum(row) != 1:
        raise ValueError("probability row must be nonnegative and sum to one")
    return row


def belief_update(belief, transition, observation, observed_index):
    """T rows: old state, columns: new state; O rows: state, columns: signal."""
    b = distribution(belief)
    n = len(b)
    t = tuple(distribution(row) for row in transition)
    o = tuple(distribution(row) for row in observation)
    if len(t) != n or any(len(row) != n for row in t) or len(o) != n:
        raise ValueError("state dimensions must agree")
    width = len(o[0])
    if any(len(row) != width for row in o):
        raise ValueError("observation rows must have equal width")
    if isinstance(observed_index, bool) or not isinstance(observed_index, int):
        raise ValueError("observation index must be an integer")
    if not 0 <= observed_index < width:
        raise ValueError("observation index out of range")
    predicted = tuple(sum(b[s] * t[s][sp] for s in range(n)) for sp in range(n))
    masses = tuple(predicted[sp] * o[sp][observed_index] for sp in range(n))
    probability = sum(masses)
    if probability == 0:
        raise ValueError("observation has zero probability under this model")
    return tuple(mass / probability for mass in masses), probability


@dataclass(frozen=True)
class Monitor:
    prevention: F = F(20)
    damage: F = F(100)
    sense_cost: F = F(1)
    sensitivity: F = F(4, 5)
    false_positive: F = F(1, 10)

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, exact(getattr(self, name)))
        if self.prevention < 0 or self.damage <= 0 or self.sense_cost < 0:
            raise ValueError("losses/cost must be nonnegative; damage must be positive")
        if not 0 <= self.sensitivity <= 1 or not 0 <= self.false_positive <= 1:
            raise ValueError("sensor probabilities must lie in [0,1]")

    @property
    def observation(self):
        return ((self.false_positive, 1 - self.false_positive),
                (self.sensitivity, 1 - self.sensitivity))


def prior_probability(p):
    p = exact(p)
    if not 0 <= p <= 1:
        raise ValueError("prior must lie in [0,1]")
    return p


def horizon_limit(horizon):
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 1 <= horizon <= 4:
        raise ValueError("teaching enumeration supports horizons 1 through 4")


def signal_branches(p, model):
    """Only positive-probability branches; index 0 is +, index 1 is -."""
    p = prior_probability(p)
    identity = ((F(1), F(0)), (F(0), F(1)))
    for signal in range(2):
        q = (1 - p) * model.observation[0][signal] + p * model.observation[1][signal]
        if q > 0:
            posterior, checked_q = belief_update((1 - p, p), identity, model.observation, signal)
            yield signal, checked_q, posterior[1]


def bellman(p, horizon, model=Monitor()):
    """Returns reward and all tied root actions; sensing is forbidden at h=1."""
    p = prior_probability(p)
    horizon_limit(horizon)

    @lru_cache(None)
    def solve(current, h):
        candidates = {"skip": -model.damage * current, "protect": -model.prevention}
        if h >= 2:
            candidates["sense"] = -model.sense_cost + sum(
                q * solve(post, h - 1)[0] for _, q, post in signal_branches(current, model))
        best = max(candidates.values())
        return best, tuple(action for action, value in candidates.items() if value == best)

    return solve(p, horizon)


@lru_cache(None)
def policies(horizon):
    """All deterministic observation-contingent trees, including early stops."""
    horizon_limit(horizon)
    leaves = ("skip", "protect")
    if horizon == 1:
        return leaves
    previous = policies(horizon - 1)
    return leaves + tuple(("sense", plus, minus) for plus, minus in product(previous, repeat=2))


def state_tree_loss(tree, state, model):
    """Independent oracle: integrate true-state signal paths, never Bayes or DP."""
    if tree == "skip":
        return model.damage * state
    if tree == "protect":
        return model.prevention
    if not isinstance(tree, tuple) or len(tree) != 3 or tree[0] != "sense":
        raise ValueError("invalid policy tree")
    # Use the original likelihood parameters directly, not signal_branches.
    plus_likelihood = model.false_positive if state == 0 else model.sensitivity
    return (model.sense_cost
            + plus_likelihood * state_tree_loss(tree[1], state, model)
            + (1 - plus_likelihood) * state_tree_loss(tree[2], state, model))


def oracle(p, horizon, model=Monitor()):
    p = prior_probability(p)
    horizon_limit(horizon)
    candidates = tuple(((1 - p) * state_tree_loss(tree, 0, model)
                        + p * state_tree_loss(tree, 1, model), tree)
                       for tree in policies(horizon))
    best = min(value for value, _ in candidates)
    return best, tuple(tree for value, tree in candidates if value == best)


def information(p, model=Monitor()):
    """One free signal before one terminal decision; sense_cost is excluded."""
    p = prior_probability(p)
    r0 = min(p * model.damage, model.prevention)
    rs = F(0)
    branches = []
    for signal, q, post in signal_branches(p, model):
        skip_loss = post * model.damage
        best = min(skip_loss, model.prevention)
        actions = tuple(name for name, loss in (("skip", skip_loss), ("protect", model.prevention))
                        if loss == best)
        rs += q * best
        branches.append({"signal": "+" if signal == 0 else "-", "probability": q,
                         "posterior": post, "risk": best, "actions": actions})
    perfect = p * min(model.damage, model.prevention)
    return {"R0": r0, "RS": rs, "RY": perfect, "EVSI": r0 - rs, "EVPI": r0 - perfect,
            "net_gain_if_bought": r0 - rs - model.sense_cost,
            "optimal_risk_buy_or_not": min(r0, model.sense_cost + rs), "branches": branches}


def same_mean_example():
    states = (-1, 0, 1)
    beliefs = {"delta0": (F(0), F(1), F(0)), "symmetric": (F(1, 2), F(0), F(1, 2))}
    result = {}
    for name, b in beliefs.items():
        mean = sum(p * x for p, x in zip(b, states))
        risky = sum(p * (x * x - F(1, 2)) for p, x in zip(b, states))
        result[name] = {"mean": mean, "safe_reward": F(0), "risky_reward": risky,
                        "best_action": "risky" if risky > 0 else "safe"}
    return result


def jsonify(value):
    if isinstance(value, F):
        return {"exact": str(value), "decimal": float(value)}
    if isinstance(value, dict):
        return {key: jsonify(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonify(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", default="1/10")
    parser.add_argument("--cost", default="1")
    parser.add_argument("--prevention", default="20")
    parser.add_argument("--sensitivity", default="4/5")
    parser.add_argument("--false-positive", default="1/10")
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--output", type=Path, help="new JSON file; existing files are never overwritten")
    args = parser.parse_args()
    model = Monitor(prevention=exact(args.prevention), sense_cost=exact(args.cost),
                    sensitivity=exact(args.sensitivity), false_positive=exact(args.false_positive))
    p = prior_probability(args.prior)
    reward, actions = bellman(p, args.horizon, model)
    risk, trees = oracle(p, args.horizon, model)
    if risk != -reward:
        raise AssertionError("belief Bellman and independent policy oracle disagree")
    report = {"model": {"static_hidden_states": [0, 1], "prior": p,
                        "prevention": model.prevention, "damage": model.damage,
                        "sense_cost": model.sense_cost, "sensitivity": model.sensitivity,
                        "false_positive": model.false_positive, "horizon": args.horizon,
                        "signals_conditionally_independent": True, "last_step_sensing": False},
              "bellman_reward": reward, "root_actions": actions,
              "oracle_risk": risk, "policy_count": len(policies(args.horizon)), "optimal_trees": trees,
              "one_signal_information": information(p, model), "same_mean": same_mean_example()}
    rendered = json.dumps(jsonify(report), ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
