"""Numerically recompute four Gauss--Bonnet examples.

This script checks stated integrals with composite Simpson quadrature.  It does
not prove Gauss--Bonnet.  Angles are radians and every radius is positive.
"""
from __future__ import annotations

import argparse
import math


def positive(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def even_steps(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2 or value > 1_000_000 or value % 2:
        raise ValueError("steps must be an even integer from 2 to 1000000")
    return value


def simpson(function, lower: float, upper: float, steps: int = 4096) -> float:
    """Composite Simpson rule on one finite interval."""
    steps = even_steps(steps)
    lower, upper = float(lower), float(upper)
    if not math.isfinite(lower) or not math.isfinite(upper) or lower == upper:
        raise ValueError("integration bounds must be distinct and finite")
    width = (upper - lower) / steps
    total = function(lower) + function(upper)
    for index in range(1, steps):
        total += (4.0 if index % 2 else 2.0) * function(lower + index * width)
    return total * width / 3.0


def terms(curvature: float, boundary: float, corners: float, chi: int) -> dict[str, float]:
    total = curvature + boundary + corners
    target = 2.0 * math.pi * chi
    return {
        "curvature": curvature,
        "boundary": boundary,
        "corners": corners,
        "chi": float(chi),
        "total": total,
        "target": target,
        "residual": total - target,
    }


def plane_disk(radius: float = 3.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    # Positive boundary is counterclockwise: kg=1/r and ds=r dt.
    boundary = simpson(lambda _t: (1.0 / radius) * radius, 0.0, 2.0 * math.pi, steps)
    return terms(0.0, boundary, 0.0, 1)


def sphere_octant(radius: float = 2.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    # 0<=phi<=pi/2, 0<=theta<=pi/2. Integrating theta first gives pi/2.
    curvature = simpson(
        lambda phi: (1.0 / radius**2) * radius**2 * math.sin(phi) * (math.pi / 2.0),
        0.0,
        math.pi / 2.0,
        steps,
    )
    return terms(curvature, 0.0, 3.0 * math.pi / 2.0, 1)


def sphere_cap(radius: float = 2.0, phi0: float = math.pi / 3.0, steps: int = 4096) -> dict[str, float]:
    radius = positive(radius, "radius")
    phi0 = float(phi0)
    if not math.isfinite(phi0) or not 0.0 < phi0 < math.pi:
        raise ValueError("phi0 must lie strictly between 0 and pi")
    curvature = simpson(
        lambda phi: (1.0 / radius**2) * radius**2 * math.sin(phi) * 2.0 * math.pi,
        0.0,
        phi0,
        steps,
    )
    # T points east, JT points into the north cap: kg=cot(phi0)/R.
    boundary = simpson(
        lambda _theta: (math.cos(phi0) / (radius * math.sin(phi0))) * radius * math.sin(phi0),
        0.0,
        2.0 * math.pi,
        steps,
    )
    return terms(curvature, boundary, 0.0, 1)


def cylinder_band(radius: float = 2.0, height: float = 3.0) -> dict[str, float]:
    positive(radius, "radius")
    positive(height, "height")
    # K=0. Both boundary circles have tangential acceleration zero, hence kg=0.
    return terms(0.0, 0.0, 0.0, 0)


def report(radius: float, phi0: float, steps: int) -> list[tuple[str, dict[str, float]]]:
    rows = [
        ("plane disk", plane_disk(radius, steps)),
        ("sphere octant", sphere_octant(radius, steps)),
        ("sphere cap", sphere_cap(radius, phi0, steps)),
        ("cylinder band", cylinder_band(radius, 3.0)),
    ]
    print("example | int KdA | int kg ds | corners | 2pi chi | residual")
    for name, row in rows:
        print(
            f"{name} | {row['curvature']:.12g} | {row['boundary']:.12g} | "
            f"{row['corners']:.12g} | {row['target']:.12g} | {row['residual']:.3e}"
        )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=float, default=2.0)
    parser.add_argument("--phi0", type=float, default=math.pi / 3.0)
    parser.add_argument("--steps", type=int, default=4096)
    arguments = parser.parse_args()
    report(arguments.radius, arguments.phi0, arguments.steps)
