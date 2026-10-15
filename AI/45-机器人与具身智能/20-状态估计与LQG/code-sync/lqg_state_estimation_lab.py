#!/usr/bin/env python3
"""Deterministic Kalman/LQG teaching lab for a 1-D double integrator.

State x=[position_m, velocity_m_per_s], input u=acceleration_m_per_s2,
and measurement y=position_m.  The batch Gaussian conditioner is an
independent oracle for the recursive Kalman filter, not a general estimator.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _array(value, *, ndim: int, name: str) -> np.ndarray:
    out = np.asarray(value, dtype=float)
    if out.ndim != ndim or not np.all(np.isfinite(out)):
        raise ValueError(f"{name} must be a finite {ndim}-D array")
    return out


def _symmetric_psd(value, *, name: str, positive: bool = False) -> np.ndarray:
    out = _array(value, ndim=2, name=name)
    if out.shape[0] != out.shape[1] or not np.allclose(out, out.T, atol=1e-12):
        raise ValueError(f"{name} must be square and symmetric")
    minimum = float(np.min(np.linalg.eigvalsh(out)))
    if (positive and minimum <= 0.0) or (not positive and minimum < -1e-12):
        kind = "positive definite" if positive else "positive semidefinite"
        raise ValueError(f"{name} must be {kind}")
    return out


def double_integrator(dt: float = 0.2) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact zero-order-hold model for p_dot=v, v_dot=u; y=p."""
    if not np.isfinite(dt) or dt < 1e-9:
        raise ValueError("dt must be finite and at least 1e-9 s")
    A = np.array([[1.0, dt], [0.0, 1.0]])
    B = np.array([[0.5 * dt * dt], [dt]])
    H = np.array([[1.0, 0.0]])
    return A, B, H


def gaussian_condition(mean_a, mean_b, cov_aa, cov_ab, cov_bb, observed_b):
    """Condition jointly Gaussian a on b using a linear solve."""
    mean_a = _array(mean_a, ndim=1, name="mean_a")
    mean_b = _array(mean_b, ndim=1, name="mean_b")
    observed_b = _array(observed_b, ndim=1, name="observed_b")
    cov_aa = _symmetric_psd(cov_aa, name="cov_aa")
    cov_bb = _symmetric_psd(cov_bb, name="cov_bb", positive=True)
    cov_ab = _array(cov_ab, ndim=2, name="cov_ab")
    if cov_aa.shape != (mean_a.size, mean_a.size):
        raise ValueError("cov_aa shape does not match mean_a")
    if cov_bb.shape != (mean_b.size, mean_b.size) or observed_b.shape != mean_b.shape:
        raise ValueError("b shapes do not match")
    if cov_ab.shape != (mean_a.size, mean_b.size):
        raise ValueError("cov_ab shape does not match a and b")
    gain = np.linalg.solve(cov_bb, cov_ab.T).T
    conditioned_mean = mean_a + gain @ (observed_b - mean_b)
    conditioned_cov = cov_aa - gain @ cov_ab.T
    return conditioned_mean, 0.5 * (conditioned_cov + conditioned_cov.T), gain


def kalman_update(mean_prior, cov_prior, H, R, measurement):
    mean_prior = _array(mean_prior, ndim=1, name="mean_prior")
    cov_prior = _symmetric_psd(cov_prior, name="cov_prior")
    H = _array(H, ndim=2, name="H")
    R = _symmetric_psd(R, name="R", positive=True)
    measurement = _array(measurement, ndim=1, name="measurement")
    n = mean_prior.size
    p = measurement.size
    if cov_prior.shape != (n, n) or H.shape != (p, n) or R.shape != (p, p):
        raise ValueError("Kalman update shapes are inconsistent")
    innovation = measurement - H @ mean_prior
    innovation_cov = H @ cov_prior @ H.T + R
    gain = np.linalg.solve(innovation_cov, (cov_prior @ H.T).T).T
    mean_post = mean_prior + gain @ innovation
    identity = np.eye(n)
    residual_map = identity - gain @ H
    cov_post = residual_map @ cov_prior @ residual_map.T + gain @ R @ gain.T
    cov_post = 0.5 * (cov_post + cov_post.T)
    return mean_post, cov_post, innovation, innovation_cov, gain


def kalman_predict(mean_post, cov_post, A, B, control, W):
    mean_post = _array(mean_post, ndim=1, name="mean_post")
    cov_post = _symmetric_psd(cov_post, name="cov_post")
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    control = _array(control, ndim=1, name="control")
    W = _symmetric_psd(W, name="W")
    n = mean_post.size
    if A.shape != (n, n) or cov_post.shape != (n, n) or W.shape != (n, n):
        raise ValueError("state prediction shapes are inconsistent")
    if B.shape != (n, control.size):
        raise ValueError("B and control shapes are inconsistent")
    mean_prior = A @ mean_post + B @ control
    cov_prior = A @ cov_post @ A.T + W
    return mean_prior, 0.5 * (cov_prior + cov_prior.T)


def filter_sequence(mean0, cov0, A, B, H, W, R, controls, measurements):
    """Update at y_k, then predict with u_k. Measurements include y_0..y_N."""
    controls = _array(controls, ndim=2, name="controls")
    measurements = _array(measurements, ndim=2, name="measurements")
    if measurements.shape[0] != controls.shape[0] + 1:
        raise ValueError("measurements must contain y_0 through y_N")
    mean = _array(mean0, ndim=1, name="mean0").copy()
    cov = _symmetric_psd(cov0, name="cov0").copy()
    means, covariances, innovations, innovation_covariances, gains = [], [], [], [], []
    for k, measurement in enumerate(measurements):
        mean, cov, innovation, innovation_cov, gain = kalman_update(mean, cov, H, R, measurement)
        means.append(mean.copy()); covariances.append(cov.copy())
        innovations.append(innovation.copy()); innovation_covariances.append(innovation_cov.copy())
        gains.append(gain.copy())
        if k < controls.shape[0]:
            mean, cov = kalman_predict(mean, cov, A, B, controls[k], W)
    return {
        "means": np.asarray(means),
        "covariances": np.asarray(covariances),
        "innovations": np.asarray(innovations),
        "innovation_covariances": np.asarray(innovation_covariances),
        "gains": np.asarray(gains),
    }


def batch_current_state_condition(mean0, cov0, A, B, H, W, R, controls, measurements):
    """Condition x_N on y_0..y_N from one explicitly stacked joint Gaussian."""
    mean0 = _array(mean0, ndim=1, name="mean0")
    cov0 = _symmetric_psd(cov0, name="cov0")
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    H = _array(H, ndim=2, name="H")
    W = _symmetric_psd(W, name="W")
    R = _symmetric_psd(R, name="R", positive=True)
    controls = _array(controls, ndim=2, name="controls")
    measurements = _array(measurements, ndim=2, name="measurements")
    n, p, horizon = mean0.size, H.shape[0], controls.shape[0]
    if A.shape != (n, n) or B.shape != (n, controls.shape[1]) or H.shape[1] != n:
        raise ValueError("batch model shapes are inconsistent")
    if cov0.shape != (n, n) or W.shape != (n, n) or R.shape != (p, p):
        raise ValueError("batch covariance shapes are inconsistent")
    if measurements.shape != (horizon + 1, p):
        raise ValueError("measurements must have horizon+1 rows")

    latent_dim = n + horizon * n + (horizon + 1) * p
    latent_cov = np.zeros((latent_dim, latent_dim))
    latent_cov[:n, :n] = cov0
    for k in range(horizon):
        start = n + k * n
        latent_cov[start:start + n, start:start + n] = W
    noise_offset = n + horizon * n
    for k in range(horizon + 1):
        start = noise_offset + k * p
        latent_cov[start:start + p, start:start + p] = R

    state_map = np.zeros((n, latent_dim)); state_map[:, :n] = np.eye(n)
    state_mean = mean0.copy()
    measurement_maps, measurement_means = [], []
    for k in range(horizon + 1):
        measurement_map = H @ state_map
        start = noise_offset + k * p
        measurement_map[:, start:start + p] += np.eye(p)
        measurement_maps.append(measurement_map)
        measurement_means.append(H @ state_mean)
        if k < horizon:
            next_map = A @ state_map
            start = n + k * n
            next_map[:, start:start + n] += np.eye(n)
            state_map = next_map
            state_mean = A @ state_mean + B @ controls[k]

    measurement_map = np.vstack(measurement_maps)
    measurement_mean = np.concatenate(measurement_means)
    cov_xx = state_map @ latent_cov @ state_map.T
    cov_xy = state_map @ latent_cov @ measurement_map.T
    cov_yy = measurement_map @ latent_cov @ measurement_map.T
    return gaussian_condition(
        state_mean, measurement_mean, cov_xx, cov_xy, cov_yy, measurements.reshape(-1)
    )[:2]


def observability_matrix(A, H) -> np.ndarray:
    A = _array(A, ndim=2, name="A")
    H = _array(H, ndim=2, name="H")
    if A.shape[0] != A.shape[1] or H.shape[1] != A.shape[0]:
        raise ValueError("A and H shapes are inconsistent")
    return np.vstack([H @ np.linalg.matrix_power(A, k) for k in range(A.shape[0])])


def detectable(A, H, *, tolerance: float = 1e-9) -> bool:
    """PBH test: every mode on/outside the unit circle must be observable."""
    A = _array(A, ndim=2, name="A")
    H = _array(H, ndim=2, name="H")
    if A.shape[0] != A.shape[1] or H.shape[1] != A.shape[0] or tolerance <= 0:
        raise ValueError("invalid detectability inputs")
    n = A.shape[0]
    for eigenvalue in np.linalg.eigvals(A):
        if abs(eigenvalue) >= 1.0 - tolerance:
            pbh = np.vstack([eigenvalue * np.eye(n) - A, H])
            if np.linalg.matrix_rank(pbh, tol=tolerance) < n:
                return False
    return True


def stabilizable(A, B, *, tolerance: float = 1e-9) -> bool:
    """PBH test: every mode on/outside the unit circle must be controllable."""
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    if A.shape[0] != A.shape[1] or B.shape[0] != A.shape[0] or tolerance <= 0:
        raise ValueError("invalid stabilizability inputs")
    n = A.shape[0]
    for eigenvalue in np.linalg.eigvals(A):
        pbh = np.hstack([eigenvalue * np.eye(n) - A, B])
        if abs(eigenvalue) >= 1.0 - tolerance and np.linalg.matrix_rank(pbh, tol=tolerance) < n:
            return False
    return True


def steady_kalman(A, H, W, R, *, tolerance: float = 1e-13, max_iterations: int = 10000):
    A = _array(A, ndim=2, name="A")
    H = _array(H, ndim=2, name="H")
    W = _symmetric_psd(W, name="W")
    R = _symmetric_psd(R, name="R", positive=True)
    n = A.shape[0]
    if A.shape != (n, n) or H.shape[1] != n or W.shape != (n, n):
        raise ValueError("steady Kalman shapes are inconsistent")
    if R.shape != (H.shape[0], H.shape[0]) or tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid steady Kalman settings")
    prior = np.eye(n)
    for iteration in range(1, max_iterations + 1):
        _, post, _, _, gain = kalman_update(np.zeros(n), prior, H, R, np.zeros(H.shape[0]))
        next_prior = A @ post @ A.T + W
        next_prior = 0.5 * (next_prior + next_prior.T)
        if np.linalg.norm(next_prior - prior, ord="fro") <= tolerance:
            _, post, _, _, gain = kalman_update(np.zeros(n), next_prior, H, R, np.zeros(H.shape[0]))
            return next_prior, post, gain, iteration
        prior = next_prior
    raise RuntimeError("Kalman covariance iteration did not converge")


def steady_lqr(A, B, Q, R, *, tolerance: float = 1e-13, max_iterations: int = 10000):
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    Q = _symmetric_psd(Q, name="Q")
    R = _symmetric_psd(R, name="R", positive=True)
    n = A.shape[0]
    if A.shape != (n, n) or B.shape[0] != n or Q.shape != (n, n):
        raise ValueError("steady LQR shapes are inconsistent")
    if R.shape != (B.shape[1], B.shape[1]) or tolerance <= 0 or max_iterations < 1:
        raise ValueError("invalid steady LQR settings")
    value = np.zeros((n, n))
    for iteration in range(1, max_iterations + 1):
        gain = np.linalg.solve(R + B.T @ value @ B, B.T @ value @ A)
        next_value = Q + A.T @ value @ A - A.T @ value @ B @ gain
        next_value = 0.5 * (next_value + next_value.T)
        if np.linalg.norm(next_value - value, ord="fro") <= tolerance:
            gain = np.linalg.solve(R + B.T @ next_value @ B, B.T @ next_value @ A)
            return next_value, gain, iteration
        value = next_value
    raise RuntimeError("LQR Riccati iteration did not converge")


def separation_matrix(A, B, H, control_gain, filter_gain) -> np.ndarray:
    """Noiseless [x;e] dynamics for update-control-predict timing."""
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    H = _array(H, ndim=2, name="H")
    control_gain = _array(control_gain, ndim=2, name="control_gain")
    filter_gain = _array(filter_gain, ndim=2, name="filter_gain")
    n = A.shape[0]
    if A.shape != (n, n) or B.shape[0] != n or H.shape[1] != n:
        raise ValueError("separation model shapes are inconsistent")
    if control_gain.shape != (B.shape[1], n) or filter_gain.shape != (n, H.shape[0]):
        raise ValueError("gain shapes are inconsistent")
    return np.block([
        [A - B @ control_gain, B @ control_gain],
        [np.zeros((n, n)), (np.eye(n) - filter_gain @ H) @ A],
    ])


def simulate_lqg(
    *, seed: int, steps: int, true_measurement_sigma: float = 0.05,
    assumed_measurement_sigma: float = 0.05, sensor_bias: float = 0.0,
    saturation: float | None = None, x0=(1.0, 0.0), dt: float = 0.2,
):
    if not isinstance(steps, int) or steps < 2:
        raise ValueError("steps must be an integer of at least two")
    for value, name in ((true_measurement_sigma, "true_measurement_sigma"),
                        (assumed_measurement_sigma, "assumed_measurement_sigma")):
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if saturation is not None and (not np.isfinite(saturation) or saturation <= 0):
        raise ValueError("saturation must be finite and positive")
    A, B, H = double_integrator(dt)
    process_sigma = 0.2
    W = process_sigma**2 * (B @ B.T)
    assumed_R = np.array([[assumed_measurement_sigma**2]])
    _, control_gain, _ = steady_lqr(A, B, np.diag([1.0, 0.1]), np.array([[0.05]]))
    rng = np.random.default_rng(seed)
    state = _array(x0, ndim=1, name="x0").copy()
    if state.shape != (2,):
        raise ValueError("x0 must have position and velocity")
    mean = np.zeros(2)
    covariance = np.diag([0.25, 0.25])
    states=[]; estimates=[]; errors=[]; sigmas=[]; innovations=[]; innovation_sigmas=[]
    nis=[]; raw_controls=[]; controls=[]; measurements=[]
    for _ in range(steps):
        measurement = H @ state + sensor_bias + rng.normal(0.0, true_measurement_sigma, 1)
        mean, covariance, innovation, innovation_cov, _ = kalman_update(
            mean, covariance, H, assumed_R, measurement
        )
        raw = float((-control_gain @ mean)[0])
        applied = raw if saturation is None else float(np.clip(raw, -saturation, saturation))
        states.append(state.copy()); estimates.append(mean.copy()); errors.append(state-mean)
        sigmas.append(np.sqrt(np.maximum(np.diag(covariance), 0.0)))
        innovations.append(float(innovation[0])); innovation_sigmas.append(float(np.sqrt(innovation_cov[0,0])))
        nis.append(float(innovation @ np.linalg.solve(innovation_cov, innovation)))
        raw_controls.append(raw); controls.append(applied); measurements.append(float(measurement[0]))
        process_acceleration = rng.normal(0.0, process_sigma)
        state = A @ state + B[:, 0] * (applied + process_acceleration)
        mean, covariance = kalman_predict(mean, covariance, A, B, np.array([applied]), W)
    return {
        "states": np.asarray(states), "estimates": np.asarray(estimates),
        "errors": np.asarray(errors), "sigmas": np.asarray(sigmas),
        "innovations": np.asarray(innovations), "innovation_sigmas": np.asarray(innovation_sigmas),
        "nis": np.asarray(nis), "raw_controls": np.asarray(raw_controls),
        "controls": np.asarray(controls), "measurements": np.asarray(measurements),
        "control_gain": control_gain,
    }


def compute_demo(*, seed: int = 20260920, steps: int = 160) -> dict:
    A, B, H = double_integrator(0.2)
    W = 0.2**2 * (B @ B.T)
    R = np.array([[0.05**2]])
    Q = np.diag([1.0, 0.1]); Ru = np.array([[0.05]])
    value, control_gain, lqr_iterations = steady_lqr(A, B, Q, Ru)
    prior_ss, post_ss, filter_gain, filter_iterations = steady_kalman(A, H, W, R)

    manual_R = np.array([[0.01]])
    manual_W = 0.2**2 * (B @ B.T)
    manual_controls = np.array([[0.5], [-0.2]])
    manual_measurements = np.array([[0.10], [0.14], [0.18]])
    recursive = filter_sequence(
        np.zeros(2), np.diag([0.04, 0.25]), A, B, H,
        manual_W, manual_R, manual_controls, manual_measurements,
    )
    batch_mean, batch_cov = batch_current_state_condition(
        np.zeros(2), np.diag([0.04, 0.25]), A, B, H,
        manual_W, manual_R, manual_controls, manual_measurements,
    )

    nominal = simulate_lqg(seed=seed, steps=steps)
    biased = simulate_lqg(seed=seed, steps=steps, sensor_bias=0.15)
    mismatched = simulate_lqg(
        seed=seed, steps=steps, true_measurement_sigma=0.15,
        assumed_measurement_sigma=0.05,
    )
    saturated = simulate_lqg(seed=seed, steps=steps, saturation=0.8, x0=(1.0, 0.0))
    augmented = separation_matrix(A, B, H, control_gain, filter_gain)
    burn = min(30, steps // 4)
    manual_steps=[]
    for k in range(3):
        manual_steps.append({
            "k": k,
            "innovation": recursive["innovations"][k].tolist(),
            "innovation_covariance": recursive["innovation_covariances"][k].tolist(),
            "gain": recursive["gains"][k].tolist(),
            "posterior_mean": recursive["means"][k].tolist(),
            "posterior_covariance": recursive["covariances"][k].tolist(),
        })
    return {
        "A": A, "B": B, "H": H, "W": W, "R": R, "Q": Q, "Ru": Ru,
        "lqr_value": value, "control_gain": control_gain,
        "steady_prior_covariance": prior_ss, "steady_posterior_covariance": post_ss,
        "filter_gain": filter_gain,
        "lqr_iterations": lqr_iterations, "filter_iterations": filter_iterations,
        "controller_poles": np.linalg.eigvals(A-B@control_gain),
        "filter_poles": np.linalg.eigvals((np.eye(2)-filter_gain@H)@A),
        "augmented_poles": np.linalg.eigvals(augmented),
        "manual_steps": manual_steps,
        "batch_mean": batch_mean, "batch_covariance": batch_cov,
        "batch_mean_error": float(np.max(np.abs(batch_mean-recursive["means"][-1]))),
        "batch_covariance_error": float(np.max(np.abs(batch_cov-recursive["covariances"][-1]))),
        "nominal": nominal, "biased": biased, "mismatched": mismatched, "saturated": saturated,
        "nominal_nis_mean_after_burn": float(np.mean(nominal["nis"][burn:])),
        "mismatched_nis_mean_after_burn": float(np.mean(mismatched["nis"][burn:])),
        "biased_true_position_mean_last20": float(np.mean(biased["states"][-20:,0])),
        "biased_estimated_position_mean_last20": float(np.mean(biased["estimates"][-20:,0])),
        "saturation_fraction": float(np.mean(np.abs(saturated["raw_controls"])>0.8)),
        "seed": seed, "steps": steps, "dt": 0.2,
    }


def _complex_pairs(values) -> list[list[float]]:
    return [[float(np.real(value)), float(np.imag(value))] for value in values]


def summary_json(result: dict) -> dict:
    return {
        "model": {
            "state": ["position_m", "velocity_m_per_s"],
            "input": "acceleration_m_per_s2", "measurement": "position_m",
            "dt_s": result["dt"], "A": result["A"].tolist(), "B": result["B"].tolist(),
            "H": result["H"].tolist(), "W": result["W"].tolist(), "R": result["R"].tolist(),
        },
        "manual_steps": result["manual_steps"],
        "analytic_batch_oracle": {
            "posterior_mean": result["batch_mean"].tolist(),
            "posterior_covariance": result["batch_covariance"].tolist(),
            "max_abs_mean_difference": result["batch_mean_error"],
            "max_abs_covariance_difference": result["batch_covariance_error"],
        },
        "steady_state": {
            "lqr_gain": result["control_gain"].tolist(),
            "kalman_current_gain": result["filter_gain"].tolist(),
            "controller_poles": _complex_pairs(result["controller_poles"]),
            "filter_poles": _complex_pairs(result["filter_poles"]),
            "augmented_poles": _complex_pairs(result["augmented_poles"]),
            "lqr_iterations": result["lqr_iterations"],
            "kalman_iterations": result["filter_iterations"],
        },
        "fixed_seed_diagnostics": {
            "seed": result["seed"], "steps": result["steps"],
            "nominal_nis_mean_after_burn": result["nominal_nis_mean_after_burn"],
            "mismatched_nis_mean_after_burn": result["mismatched_nis_mean_after_burn"],
            "biased_true_position_mean_last20_m": result["biased_true_position_mean_last20"],
            "biased_estimated_position_mean_last20_m": result["biased_estimated_position_mean_last20"],
            "saturation_fraction": result["saturation_fraction"],
            "evidence_limit": "one fixed-seed trajectory is a reproducible diagnostic, not a coverage proof",
        },
    }


def save_figures(result: dict, output_dir: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "wwl-kalman-lqg"
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    paths=[]
    time=np.arange(result["steps"])*result["dt"]
    nominal=result["nominal"]

    fig, axes=plt.subplots(2,1,figsize=(8.0,6.2),sharex=True,layout="constrained")
    axes[0].plot(time,nominal["states"][:,0],label="true position",lw=2)
    axes[0].plot(time,nominal["measurements"],".",ms=2,alpha=.45,label="position measurement")
    axes[0].plot(time,nominal["estimates"][:,0],label="Kalman estimate",lw=1.5)
    band=2*nominal["sigmas"][:,0]
    axes[0].fill_between(time,nominal["estimates"][:,0]-band,nominal["estimates"][:,0]+band,alpha=.18,label="estimate ±2 posterior sd")
    axes[0].set_ylabel("position (m)"); axes[0].legend(ncol=2,fontsize=8); axes[0].grid(alpha=.25)
    axes[1].plot(time,nominal["errors"][:,0],label="position error")
    axes[1].plot(time,2*nominal["sigmas"][:,0],"--",color="tab:gray",label="±2 posterior sd")
    axes[1].plot(time,-2*nominal["sigmas"][:,0],"--",color="tab:gray")
    axes[1].axhline(0,color="black",lw=.7); axes[1].set_xlabel("time (s)"); axes[1].set_ylabel("true − estimate (m)")
    axes[1].legend(fontsize=8); axes[1].grid(alpha=.25)
    path=output_dir/"kalman-error-diagnostics.svg"; fig.savefig(path,metadata={"Date":None}); plt.close(fig); paths.append(path)

    fig,ax=plt.subplots(figsize=(6.0,5.6),layout="constrained")
    theta=np.linspace(0,2*np.pi,500); ax.plot(np.cos(theta),np.sin(theta),color="0.65",label="unit circle")
    groups=((result["controller_poles"],"LQR: A−BK","o"),(result["filter_poles"],"filter: (I−LH)A","s"),(result["augmented_poles"],"combined poles","x"))
    for values,label,marker in groups:
        ax.scatter(np.real(values),np.imag(values),s=55,marker=marker,label=label)
    ax.axhline(0,color="0.75",lw=.8); ax.axvline(0,color="0.75",lw=.8); ax.set_aspect("equal")
    ax.set_xlim(-1.1,1.1); ax.set_ylim(-1.1,1.1); ax.set_xlabel("real part"); ax.set_ylabel("imaginary part")
    ax.set_title("Separation: combined poles are the two diagonal blocks"); ax.grid(alpha=.25); ax.legend(fontsize=8)
    path=output_dir/"lqg-separation-poles.svg"; fig.savefig(path,metadata={"Date":None}); plt.close(fig); paths.append(path)

    biased=result["biased"]; mismatched=result["mismatched"]; saturated=result["saturated"]
    fig,axes=plt.subplots(3,1,figsize=(8.0,8.2),sharex=True,layout="constrained")
    axes[0].plot(time,biased["states"][:,0],label="true position")
    axes[0].plot(time,biased["estimates"][:,0],label="estimated position")
    axes[0].axhline(-.15,color="tab:red",ls="--",label="−sensor bias")
    axes[0].set_ylabel("bias case (m)"); axes[0].legend(ncol=3,fontsize=8); axes[0].grid(alpha=.25)
    axes[1].plot(time,mismatched["nis"],lw=.8,label="NIS with true σ=0.15, assumed σ=0.05")
    axes[1].axhline(1,color="tab:red",ls="--",label="scalar model expectation = 1")
    axes[1].set_ylim(0,min(25,max(8,float(np.quantile(mismatched["nis"],.95)))))
    axes[1].set_ylabel("NIS"); axes[1].legend(fontsize=8); axes[1].grid(alpha=.25)
    axes[2].plot(time,saturated["raw_controls"],label="requested −K x-hat")
    axes[2].plot(time,saturated["controls"],label="applied after saturation")
    axes[2].axhline(.8,color="tab:red",ls="--"); axes[2].axhline(-.8,color="tab:red",ls="--",label="actuator bounds")
    axes[2].set_ylabel("acceleration (m/s²)"); axes[2].set_xlabel("time (s)"); axes[2].legend(ncol=2,fontsize=8); axes[2].grid(alpha=.25)
    path=output_dir/"lqg-failure-boundaries.svg"; fig.savefig(path,metadata={"Date":None}); plt.close(fig); paths.append(path)
    return paths


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--seed",type=int,default=20260920)
    parser.add_argument("--steps",type=int,default=160)
    args=parser.parse_args(argv)
    result=compute_demo(seed=args.seed,steps=args.steps)
    paths=save_figures(result,args.output_dir)
    summary_path=args.output_dir/"demo-summary.json"
    summary_path.write_text(json.dumps(summary_json(result),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    paths.append(summary_path)
    for path in paths: print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
