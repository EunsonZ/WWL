from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def ridge_solution(x: Iterable[float], y: Iterable[float], lam: float) -> float:
    """Minimize mean((w*x-y)^2) + lam*w^2 for one scalar parameter."""
    x_arr = np.asarray(tuple(x), dtype=float)
    y_arr = np.asarray(tuple(y), dtype=float)
    if x_arr.shape != y_arr.shape or x_arr.ndim != 1 or x_arr.size == 0:
        raise ValueError("x and y must be non-empty vectors with equal shape")
    if not np.all(np.isfinite(x_arr)) or not np.all(np.isfinite(y_arr)) or lam < 0 or not math.isfinite(lam):
        raise ValueError("inputs must be finite and lam non-negative")
    denominator = float(np.dot(x_arr, x_arr) + lam * x_arr.size)
    if denominator == 0.0:
        raise ValueError("objective has no unique scalar ridge solution")
    return float(np.dot(x_arr, y_arr) / denominator)


def logistic_gradient(x: Iterable[float], y: float, w: Iterable[float], bias: float = 0.0) -> tuple[np.ndarray, float]:
    """Gradient of one Bernoulli negative log-likelihood sample."""
    x_arr = np.asarray(tuple(x), dtype=float)
    w_arr = np.asarray(tuple(w), dtype=float)
    if (
        x_arr.shape != w_arr.shape
        or not np.all(np.isfinite(x_arr))
        or not np.all(np.isfinite(w_arr))
        or not math.isfinite(bias)
        or y not in (0.0, 1.0)
    ):
        raise ValueError("shape mismatch or non-binary label")
    z = float(np.dot(x_arr, w_arr) + bias)
    p = 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, z))))
    return (p - y) * x_arr, p - y


def finite_class_gap(class_size: int, sample_size: int, delta: float) -> float:
    """Two-sided finite-class gap sqrt(log(2|H|/delta)/(2n))."""
    if class_size < 1 or sample_size < 1 or not 0.0 < delta < 1.0:
        raise ValueError("invalid class size, sample size, or delta")
    return math.sqrt(math.log(2.0 * class_size / delta) / (2.0 * sample_size))


def kmeans_step(points: Iterable[float], centers: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    points_arr = np.asarray(tuple(points), dtype=float)
    centers_arr = np.asarray(tuple(centers), dtype=float)
    if (
        points_arr.ndim != 1
        or centers_arr.ndim != 1
        or points_arr.size == 0
        or centers_arr.size == 0
        or not np.all(np.isfinite(points_arr))
        or not np.all(np.isfinite(centers_arr))
    ):
        raise ValueError("points and centers must be non-empty vectors")
    assignment = np.argmin((points_arr[:, None] - centers_arr[None, :]) ** 2, axis=1)
    updated = np.array([
        points_arr[assignment == k].mean() if np.any(assignment == k) else centers_arr[k]
        for k in range(centers_arr.size)
    ])
    return assignment, updated


def gmm_responsibilities(x: float, weights: Iterable[float], means: Iterable[float], stds: Iterable[float]) -> np.ndarray:
    weights_arr = np.asarray(tuple(weights), dtype=float)
    means_arr = np.asarray(tuple(means), dtype=float)
    stds_arr = np.asarray(tuple(stds), dtype=float)
    if weights_arr.shape != means_arr.shape or weights_arr.shape != stds_arr.shape:
        raise ValueError("mixture arrays must have equal shape")
    if (
        not math.isfinite(x)
        or not np.all(np.isfinite(weights_arr))
        or not np.all(np.isfinite(means_arr))
        or not np.all(np.isfinite(stds_arr))
        or np.any(weights_arr < 0)
        or np.any(stds_arr <= 0)
        or not np.isclose(weights_arr.sum(), 1.0)
    ):
        raise ValueError("invalid mixture parameters")
    with np.errstate(divide="ignore"):
        log_scores = (
            np.log(weights_arr)
            - np.log(stds_arr)
            - 0.5 * math.log(2.0 * math.pi)
            - 0.5 * ((x - means_arr) / stds_arr) ** 2
        )
    maximum = float(np.max(log_scores))
    if not math.isfinite(maximum):
        raise ValueError("at least one mixture weight must be positive")
    shifted = np.exp(log_scores - maximum)
    return shifted / shifted.sum()


def value_iteration(reward: np.ndarray, transition: np.ndarray, gamma: float, steps: int) -> np.ndarray:
    """Return V_0 ... V_steps for transition[state, action, next_state]."""
    reward = np.asarray(reward, dtype=float)
    transition = np.asarray(transition, dtype=float)
    if transition.ndim != 3 or transition.shape[:2] != reward.shape or transition.shape[2] != reward.shape[0]:
        raise ValueError("shape mismatch")
    if (
        not np.all(np.isfinite(reward))
        or not np.all(np.isfinite(transition))
        or np.any(transition < 0)
        or not 0.0 <= gamma < 1.0
        or steps < 0
        or not np.allclose(transition.sum(axis=2), 1.0)
    ):
        raise ValueError("invalid gamma, steps, or transition probabilities")
    values = [np.zeros(reward.shape[0])]
    for _ in range(steps):
        q = reward + gamma * np.einsum("san,n->sa", transition, values[-1])
        values.append(q.max(axis=1))
    return np.stack(values)


def td_targets(reward: float, gamma: float, next_q: Iterable[float], next_action: int) -> tuple[float, float]:
    q = np.asarray(tuple(next_q), dtype=float)
    if (
        q.ndim != 1
        or not np.all(np.isfinite(q))
        or not math.isfinite(reward)
        or not math.isfinite(gamma)
        or not 0 <= next_action < q.size
        or not 0 <= gamma <= 1
    ):
        raise ValueError("invalid target inputs")
    return reward + gamma * float(q[next_action]), reward + gamma * float(q.max())


def beta_bernoulli_update(alpha: float, beta: float, successes: int, failures: int) -> tuple[float, float, float]:
    if (
        not math.isfinite(alpha)
        or not math.isfinite(beta)
        or alpha <= 0
        or beta <= 0
        or successes < 0
        or failures < 0
    ):
        raise ValueError("invalid beta-bernoulli inputs")
    post_a, post_b = alpha + successes, beta + failures
    return post_a, post_b, post_a / (post_a + post_b)


def grouped_and_pooled_rates(successes: np.ndarray, totals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rows are treatments, columns are strata; return stratum rates and pooled treatment rates."""
    successes = np.asarray(successes, dtype=float)
    totals = np.asarray(totals, dtype=float)
    if (
        successes.shape != totals.shape
        or successes.ndim != 2
        or not np.all(np.isfinite(successes))
        or not np.all(np.isfinite(totals))
        or np.any(successes < 0)
        or np.any(totals <= 0)
        or np.any(successes > totals)
    ):
        raise ValueError("invalid count table")
    return successes / totals, successes.sum(axis=1) / totals.sum(axis=1)


def autoregressive_joint(p_x1: float, p_x2_given_x1: Iterable[float]) -> np.ndarray:
    cond = np.asarray(tuple(p_x2_given_x1), dtype=float)
    if (
        cond.shape != (2,)
        or not math.isfinite(p_x1)
        or not np.all(np.isfinite(cond))
        or not 0 <= p_x1 <= 1
        or np.any((cond < 0) | (cond > 1))
    ):
        raise ValueError("invalid Bernoulli probabilities")
    first = np.array([1.0 - p_x1, p_x1])
    return np.array([[first[x1] * (cond[x1] if x2 else 1.0 - cond[x1]) for x2 in (0, 1)] for x1 in (0, 1)])


def affine_flow_log_density(x: float, scale: float, shift: float) -> float:
    """Log density under x = scale*z + shift, z standard normal."""
    if scale == 0 or not all(map(math.isfinite, (x, scale, shift))):
        raise ValueError("scale must be non-zero and inputs finite")
    z = (x - shift) / scale
    return -0.5 * z * z - 0.5 * math.log(2.0 * math.pi) - math.log(abs(scale))
