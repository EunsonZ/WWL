"""Reproduce a bounded quadratic example. No network or external services.

Run with the vault's existing NumPy/Matplotlib environment and --output DIR.
All variables are dimensionless; a 3D graph adds function height, not a third
parameter. This is exact-gradient, unconstrained, Euclidean GD without momentum.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def trajectory(eta: float, steps: int = 12) -> np.ndarray:
    points = np.empty((steps + 1, 2), dtype=float)
    points[0] = (2.0, 0.6)
    for k in range(steps):
        points[k + 1] = points[k] - eta * np.array([1.0, 10.0]) * points[k]
    return points


def objective(points: np.ndarray) -> np.ndarray:
    return 0.5 * (points[..., 0] ** 2 + 10.0 * points[..., 1] ** 2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13,
                         "svg.fonttype": "none", "figure.facecolor": "white"})
    good, bad = trajectory(0.1), trajectory(0.25)
    # Analytical references are independent of the iterative recurrence.
    steps = np.arange(len(good))
    exact_good = np.column_stack([2.0 * 0.9 ** steps,
                                 np.where(steps == 0, 0.6, 0.0)])
    exact_bad = np.column_stack([2.0 * 0.75 ** steps, 0.6 * (-1.5) ** steps])
    np.testing.assert_allclose(good, exact_good, atol=1e-14)
    np.testing.assert_allclose(bad, exact_bad, atol=1e-12)
    assert np.all(np.diff(objective(good)) < 0)
    assert abs(bad[-1, 1]) > abs(bad[0, 1])
    assert np.all(np.isfinite(bad))  # finite is not converged
    # Boundary eta=.2 preserves |y|; an exactly zero y hides its instability.
    np.testing.assert_allclose(abs(trajectory(0.2)[:, 1]), 0.6)

    grid_x, grid_y = np.meshgrid(np.linspace(-2.3, 2.3, 121),
                                np.linspace(-0.85, 0.85, 101))
    grid_z = 0.5 * (grid_x ** 2 + 10 * grid_y ** 2)
    fig, ax = plt.subplots(figsize=(5.2, 4.3), layout="constrained")
    contours = ax.contour(grid_x, grid_y, grid_z, levels=[.2, .5, 1, 2, 3, 4, 5],
                          colors="#6d7785", linewidths=.7)
    ax.clabel(contours, inline=True, fontsize=12)
    ax.plot(good[:, 0], good[:, 1], "o-", color="#1565c0", markersize=4,
            label="eta=0.10: convergent")
    ax.plot(bad[:2, 0], bad[:2, 1], "s--", color="#b34b12", markersize=5,
            label="eta=0.25: first step only")
    # Scale vector for display; text records the true direction at the start.
    ax.quiver([2], [.6], [-2], [-6], angles="xy", scale_units="xy", scale=10,
              color="black", width=.008)
    ax.plot(0, 0, "k+", markersize=10, label="minimum (0,0)")
    ax.set(xlabel="x (dimensionless)", ylabel="y (dimensionless)",
           title="Contours and updates in (x,y)")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.28), fontsize=12,
              frameon=False)
    fig.savefig(args.output / "quadratic-2d.svg", bbox_inches="tight")
    fig.savefig(args.output / "quadratic-2d.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig = plt.figure(figsize=(5.2, 4.6), layout="constrained")
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(grid_x, grid_y, grid_z, cmap="Blues", alpha=.6,
                    rcount=30, ccount=30, edgecolor="none")
    ax.plot(good[:, 0], good[:, 1], objective(good), "o-", color="#101010",
            markersize=4, linewidth=2)
    ax.set(xlabel="x (parameter)", ylabel="y (parameter)",
           zlabel="f(x,y) (height)", title="3D graph: z=f(x,y)\nTwo independent parameters")
    ax.view_init(elev=27, azim=-55)
    fig.savefig(args.output / "quadratic-3d.svg", bbox_inches="tight")
    fig.savefig(args.output / "quadratic-3d.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 4.0), layout="constrained")
    ax.semilogy(steps, objective(good), "o-", color="#1565c0", label="eta=0.10")
    ax.semilogy(steps, objective(bad), "s--", color="#b34b12", label="eta=0.25")
    ax.set(xlabel="k (update index)", ylabel="f(x_k,y_k), log scale",
           title="Finite values can still diverge")
    ax.legend(); ax.grid(alpha=.2)
    fig.savefig(args.output / "quadratic-stability.svg")
    fig.savefig(args.output / "quadratic-stability.png", dpi=180)
    plt.close(fig)
    with (args.output / "quadratic-data.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["eta", "step", "x", "y", "objective"])
        for eta, points in [(0.1, good), (0.25, bad), (0.2, trajectory(0.2))]:
            for k, point in enumerate(points):
                writer.writerow([eta, k, *point, objective(point)])
    (args.output / "quadratic-checks.json").write_text(json.dumps({
        "model": "f=0.5*(x*x+10*y*y), initial=(2,0.6)",
        "dimensions": "parameters=2; graph=3; all quantities dimensionless",
        "hessian_eigenvalues": [1, 10], "condition_number_2": 10,
        "converges_for_all_initial_points": "0 < eta < 0.2",
        "analytical_reference": "passed", "eta_0_2_boundary": "passed",
        "finite_but_divergent": "passed",
        "scope": "exact Euclidean GD, no momentum; toy numerical evidence"
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
