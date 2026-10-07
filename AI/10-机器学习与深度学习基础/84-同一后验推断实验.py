"""One fixed A->B->C, B->D model: exact, mean-field, finite Metropolis.
Standard library only; import does not run, print, or write files.
"""
import argparse
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path

STATES = ((0, 0), (0, 1), (1, 0), (1, 1))


def joint_table():
    table = {}
    for a, b, c, d in itertools.product((0, 1), repeat=4):
        pa = F(2, 5) if a else F(3, 5)
        pb1 = F(4, 5) if a else F(1, 5)
        pc1 = F(9, 10) if b else F(1, 10)
        pd1 = F(7, 10) if b else F(3, 10)
        table[a, b, c, d] = pa * (pb1 if b else 1-pb1) * (pc1 if c else 1-pc1) * (pd1 if d else 1-pd1)
    return table


def collapsed_posterior():
    table = joint_table()
    masses = [sum(table[a, b, 1, d] for a in (0, 1)) for b, d in STATES]
    evidence = sum(masses)
    return masses, evidence, [m/evidence for m in masses]


def product_q(r, t):
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (r, t)):
        raise ValueError("Bernoulli probabilities must be finite in [0,1]")
    return [(r if b else 1-r)*(t if d else 1-t) for b, d in STATES]


def objective(q):
    if len(q) != 4 or not all(math.isfinite(v) and v >= 0 for v in q) or abs(sum(q)-1) > 1e-12:
        raise ValueError("normalized four-state q required")
    masses, evidence, pi = collapsed_posterior()
    elbo = sum(v*math.log(float(m)/v) for v, m in zip(q, masses) if v > 0)
    kl = sum(v*math.log(v/float(p)) for v, p in zip(q, pi) if v > 0)
    return elbo, kl


def sigmoid(value):
    return 1/(1+math.exp(-value))


def mean_field(iterations=20):
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("positive integer iterations required")
    r, t = .5, .5
    history = []
    for index in range(iterations+1):
        q = product_q(r, t)
        elbo, kl = objective(q)
        history.append({"sweep": index, "r": r, "t": t, "elbo": elbo, "kl": kl})
        # Each update holds the other coordinate fixed; use new r to update t.
        r = sigmoid((1-t)*math.log(297/98)+t*math.log(693/42))
        t = sigmoid((2*r-1)*math.log(7/3))
    return history


def transition_matrix():
    _, _, pi = collapsed_posterior()
    matrix = [[F(0) for _ in STATES] for _ in STATES]
    for i, state in enumerate(STATES):
        for j, proposed in enumerate(STATES):
            if sum(a != b for a, b in zip(state, proposed)) == 1:
                matrix[i][j] = F(1, 2)*min(F(1), pi[j]/pi[i])
        matrix[i][i] = 1-sum(matrix[i])
    return matrix


def evolve(distribution, matrix):
    return [sum(distribution[i]*matrix[i][j] for i in range(4)) for j in range(4)]


def exact_mean_variance(initial, steps, matrix):
    """Exact DP over (state, accumulated D); excludes X0 and retains X1..Xsteps."""
    if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 64:
        raise ValueError("steps must be an integer from 1 through 64")
    if len(initial) != 4 or any(p < 0 for p in initial) or sum(initial) != 1:
        raise ValueError("normalized four-state initial distribution required")
    law = {(i, 0): p for i, p in enumerate(initial) if p}
    for _ in range(steps):
        updated = {}
        for (i, count), mass in law.items():
            for j, transition in enumerate(matrix[i]):
                key = (j, count+STATES[j][1])
                updated[key] = updated.get(key, F(0))+mass*transition
        law = updated
    mean = sum(F(count, steps)*mass for (_, count), mass in law.items())
    second = sum(F(count*count, steps*steps)*mass for (_, count), mass in law.items())
    return mean, second-mean*mean


def walkthrough():
    # Fixed legal proposals and uniforms are for hand tracing, not a random run.
    proposals = (1, 2, 3, 1, 2, 0, 3, 2)
    uniforms = (.5, .2, .8, .2, .3, .5, .9, .8)
    _, _, pi = collapsed_posterior()
    state, rows = 0, []
    for step, (proposed, uniform) in enumerate(zip(proposals, uniforms), 1):
        assert sum(a != b for a, b in zip(STATES[state], STATES[proposed])) == 1
        alpha = min(F(1), pi[proposed]/pi[state])
        accepted = uniform < alpha
        following = proposed if accepted else state
        rows.append({"step": step, "from": STATES[state], "proposal": STATES[proposed],
                     "u": uniform, "alpha": str(alpha), "accepted": accepted,
                     "to": STATES[following]})
        state = following
    return rows


def report():
    table = joint_table()
    masses, evidence, pi = collapsed_posterior()
    # Independent scalar/hand-table oracles, not outputs from the generated code.
    assert sum(table.values()) == 1 and table[0, 1, 1, 1] == F(189, 2500)
    assert masses == [F(49, 1250), F(21, 1250), F(297, 2500), F(693, 2500)]
    assert evidence == F(113, 250) and pi == [F(98, 1130), F(42, 1130), F(297, 1130), F(693, 1130)]
    matrix = transition_matrix()
    hand_matrix = [[F(2, 7), F(3, 14), F(1, 2), F(0)],
                   [F(1, 2), F(0), F(0), F(1, 2)],
                   [F(49, 297), F(0), F(199, 594), F(1, 2)],
                   [F(0), F(1, 33), F(3, 14), F(349, 462)]]
    assert matrix == hand_matrix
    assert all(sum(row) == 1 for row in matrix) and evolve(pi, matrix) == pi
    assert all(pi[i]*matrix[i][j] == pi[j]*matrix[j][i] for i in range(4) for j in range(4))
    cold = [F(1), F(0), F(0), F(0)]
    # Independent eight-step expected average via repeated marginal evolution.
    law, summed = cold, F(0)
    for _ in range(8):
        law = evolve(law, hand_matrix)
        summed += law[1]+law[3]
    mean, variance = exact_mean_variance(cold, 8, matrix)
    assert mean == summed/8
    stationary_mean, stationary_variance = exact_mean_variance(pi, 8, matrix)
    target = pi[1]+pi[3]
    assert target == F(147, 226) and stationary_mean == target
    history = mean_field()
    assert abs(history[1]["r"]-99/113) < 1e-14
    assert all(row["elbo"]+1e-13 >= previous["elbo"] for previous, row in zip(history, history[1:]))
    assert all(abs(row["elbo"]+row["kl"]-math.log(float(evidence))) < 1e-13 for row in history)
    # Independent global mean-field optimum check by scalar derivative sign bisection.
    lo, hi = 0., 1.
    for _ in range(60):
        t = (lo+hi)/2
        r = sigmoid((1-t)*math.log(297/98)+t*math.log(693/42))
        derivative = (2*r-1)*math.log(7/3)-math.log(t/(1-t))
        if derivative > 0:
            lo = t
        else:
            hi = t
    optimum_t = (lo+hi)/2
    assert abs(history[-1]["t"]-optimum_t) < 1e-13
    rows = walkthrough()
    trajectory_mean = sum(row["to"][1] for row in rows)/8
    assert trajectory_mean == .5
    restricted = [0, 0, .3, .7]
    restricted_elbo, restricted_kl = objective(restricted)
    assert abs(restricted_kl+math.log(99/113)) < 1e-13
    joint_d1_next_d1 = sum(pi[i]*matrix[i][j] for i in (1, 3) for j in (1, 3))
    gamma1 = joint_d1_next_d1-target*target
    rejection_checks = 0
    for call in (lambda: product_q(-.1, .5), lambda: product_q(float('nan'), .5),
                 lambda: objective([0, 0, 0, 0]), lambda: objective([1, 0, 0]),
                 lambda: mean_field(0), lambda: exact_mean_variance(cold, 0, matrix),
                 lambda: exact_mean_variance([F(0)]*4, 8, matrix)):
        try:
            call()
        except ValueError:
            rejection_checks += 1
        else:
            raise AssertionError("invalid input accepted")
    return {"joint_16": [{"abcd": key, "mass": str(value)} for key, value in table.items()],
            "collapsed_mass": [str(m) for m in masses], "evidence": str(evidence),
            "posterior": [float(p) for p in pi], "target_D1": float(target),
            "vi_first_sweeps": history[:4], "vi_final": history[-1],
            "vi_marginal_error": history[-1]["t"]-float(target),
            "vi_joint": product_q(history[-1]["r"], history[-1]["t"]),
            "restricted_support_D1": .7, "restricted_kl": restricted_kl,
            "transition": [[str(p) for p in row] for row in matrix], "walkthrough": rows,
            "walkthrough_D1_average": trajectory_mean,
            "cold_8_mean": float(mean), "cold_8_bias": float(mean-target),
            "cold_8_variance": float(variance), "stationary_8_variance": float(stationary_variance),
            "iid_8_variance": float(target*(1-target)/8), "stationary_lag1_covariance": float(gamma1),
            "invalid_cases_rejected": rejection_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='optional explicit JSON destination outside the vault')
    args = parser.parse_args()
    encoded = json.dumps(report(), indent=2, ensure_ascii=False)+'\n'
    if args.output is None:
        print(encoded, end='')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')


if __name__ == '__main__':
    main()
