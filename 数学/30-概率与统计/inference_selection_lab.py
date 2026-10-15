"""Exact small experiments: conditioning, test selection and stopping.

Only the normal quantiles use floats; Bernoulli calculations use Fraction.
No simulation seed is needed because the finite spaces are enumerated exactly.
"""
from collections import defaultdict
from fractions import Fraction
from itertools import product
from math import comb
from statistics import NormalDist
import json


def upper_tail(n, h):
    """P[Binomial(n,1/2)>=h], including n=0; integers only."""
    if type(n) is not int or type(h) is not int or n < 0 or not 0 <= h <= n:
        raise ValueError("require integer n>=0 and 0<=h<=n")
    return Fraction(sum(comb(n, k) for k in range(h, n + 1)), 2 ** n)


def stopping_dp(steps=20, rule="peek"):
    """State (heads, ever_rejected); rejection remains absorbing.

    Probabilities are under iid Bernoulli(1/2). At a step, each state sends
    half its mass to each outcome. first_crossing records newly rejected mass.
    """
    if type(steps) is not int or steps < 0:
        raise ValueError("steps must be a nonnegative integer")
    if rule not in {"peek", "lr"}:
        raise ValueError("rule must be peek or lr")
    states = {(0, False): Fraction(1)}
    first = {}
    for n in range(1, steps + 1):
        new = defaultdict(Fraction)
        crossings = Fraction(0)
        for (h, ever), mass in states.items():
            for x in (0, 1):
                heads = h + x
                reject = (upper_tail(n, heads) <= Fraction(1, 20)
                          if rule == "peek" else 3 ** heads >= 20 * 2 ** n)
                probability = mass / 2
                new[heads, ever or reject] += probability
                if not ever and reject:
                    crossings += probability
        states = dict(new)
        first[n] = crossings
        assert sum(states.values()) == 1
    rejection = sum((mass for (_, ever), mass in states.items() if ever), Fraction(0))
    assert rejection == sum(first.values(), Fraction(0))
    return rejection, first


def conditioning_moments(n=4, p=Fraction(1, 2)):
    """Enumerate iid Bernoulli paths to verify conditional expectations."""
    p = Fraction(p)
    if type(n) is not int or n < 2 or not 0 < p < 1:
        raise ValueError("require n>=2 and 0<p<1")
    groups = defaultdict(lambda: [Fraction(0), Fraction(0), Fraction(0)])
    for path in product((0, 1), repeat=n):
        s = sum(path)
        mass = p ** s * (1 - p) ** (n - s)
        groups[s][0] += mass
        groups[s][1] += mass * path[0]
        groups[s][2] += mass * path[0] * path[1]
    rows = []
    mean = second = Fraction(0)
    for s, (mass, first, pair) in sorted(groups.items()):
        rb = first / mass
        assert rb == Fraction(s, n)
        assert pair / mass == Fraction(s * (s - 1), n * (n - 1))
        mean += mass * rb
        second += mass * rb ** 2
        rows.append({"s": s, "mass": mass, "x1_given_s": rb,
                     "x1x2_given_s": pair / mass})
    variance_before = p * (1 - p)
    variance_after = second - mean ** 2
    assert variance_after == variance_before / n
    return {"n": n, "p": p, "rows": rows, "variance_before": variance_before,
            "variance_after": variance_after}


def markov_path_probability(path, a=Fraction(1, 4), b=Fraction(3, 4)):
    """P(X1=1)=1/2, a=P(next=1|0), b=P(next=1|1)."""
    if not path or any(x not in (0, 1) for x in path):
        raise ValueError("path must contain binary values")
    a, b = Fraction(a), Fraction(b)
    if not 0 <= a <= 1 or not 0 <= b <= 1:
        raise ValueError("transition probabilities must lie in [0,1]")
    mass = Fraction(1, 2)
    for previous, current in zip(path, path[1:]):
        chance_one = a if previous == 0 else b
        mass *= chance_one if current else 1 - chance_one
    return mass


def randomized_upper_test(n, p0, p1, alpha):
    """NP upper-tail test for Bernoulli p1>p0, randomized at its boundary.

    At S=cutoff draw one independent U~Uniform(0,1) and reject if U<=rho.
    The reported size and power integrate that randomization, without drawing U.
    """
    p0, p1, alpha = Fraction(p0), Fraction(p1), Fraction(alpha)
    if type(n) is not int or n < 1 or not 0 < p0 < p1 < 1 or not 0 <= alpha <= 1:
        raise ValueError("require n>=1, 0<p0<p1<1, 0<=alpha<=1")
    size = power = Fraction(0)
    for k in range(n, -1, -1):
        null_mass = comb(n, k) * p0 ** k * (1 - p0) ** (n - k)
        alt_mass = comb(n, k) * p1 ** k * (1 - p1) ** (n - k)
        if size + null_mass >= alpha:
            rho = (alpha - size) / null_mass
            return {"cutoff": k, "rho": rho, "size": size + rho * null_mass,
                    "power": power + rho * alt_mass}
        size += null_mass
        power += alt_mass
    raise AssertionError("boundary not found")


def uniform_maximum(n=4, theta=Fraction(1)):
    """Integrate f_M(m)=n*m**(n-1)/theta**n on [0,theta] exactly."""
    theta = Fraction(theta)
    if type(n) is not int or n < 1 or theta <= 0:
        raise ValueError("require n>=1 and theta>0")
    # Antiderivative of m**(n-1+r) gives theta**(n+r)/(n+r).
    moments = {r: Fraction(n, n + r) * theta ** r for r in (1, 2)}
    variance = moments[2] - moments[1] ** 2
    correction = Fraction(n + 1, n)
    return {"n": n, "theta": theta, "mean_max": moments[1],
            "second_moment_max": moments[2], "variance_max": variance,
            "mean_corrected": correction * moments[1],
            "variance_corrected": correction ** 2 * variance}


def results():
    fixed = upper_tail(20, 15)
    peek, peek_first = stopping_dp(rule="peek")
    lr, lr_first = stopping_dp(rule="lr")
    return {"stopping_inputs": {"n": 20, "p0": Fraction(1, 2), "alpha": Fraction(1, 20),
                       "p1": Fraction(3, 4), "lr_threshold": 20},
            "stopping": {"fixed": fixed, "peek": peek, "lr": lr,
                         "peek_first_crossing": peek_first, "lr_first_crossing": lr_first},
            "multiple_testing": {"independent_100_at_001": 1 - Fraction(99, 100) ** 100,
                                 "identical_events_at_001": Fraction(1, 100),
                                 "one_sided_normal_001": NormalDist().inv_cdf(.99),
                                 "bonferroni_100_normal": NormalDist().inv_cdf(.9999)},
            "conditioning": [conditioning_moments(p=Fraction(1, 2)),
                             conditioning_moments(p=Fraction(1, 4))],
            "uniform_maximum": uniform_maximum(),
            "randomized_np": [
                {"inputs": {"n": 4, "p0": Fraction(1, 2), "p1": Fraction(3, 4), "alpha": Fraction(1, 10)},
                 **randomized_upper_test(4, Fraction(1, 2), Fraction(3, 4), Fraction(1, 10))},
                {"inputs": {"n": 20, "p0": Fraction(1, 2), "p1": Fraction(4, 5), "alpha": Fraction(1, 20)},
                 **randomized_upper_test(20, Fraction(1, 2), Fraction(4, 5), Fraction(1, 20))}],
            "markov": {"0011": markov_path_probability((0, 0, 1, 1)),
                       "0101": markov_path_probability((0, 1, 0, 1)),
                       "ratio": markov_path_probability((0, 0, 1, 1)) /
                                markov_path_probability((0, 1, 0, 1))}}


def encode(value):
    if isinstance(value, Fraction):
        return {"fraction": str(value), "decimal": float(value)}
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    print(json.dumps(results(), default=encode, ensure_ascii=False, indent=2))
