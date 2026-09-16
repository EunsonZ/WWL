"""Recompute the R=2 sphere/cylinder lessons; no discrete path proves minimality.
Angles are radians, positions and arc length use one consistent length unit.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np


def positive(value, name):
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def vector(value, size, name):
    arr = np.asarray(value, dtype=float)
    if arr.shape != (size,) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must have shape ({size},) and finite entries")
    return arr


def forms(kind, radius, phi=np.pi / 3):
    """Return metric, second form, shape operator for OUTWARD normal, S=-dn."""
    radius = positive(radius, "radius")
    if not np.sqrt(np.finfo(float).tiny) < radius < np.sqrt(np.finfo(float).max):
        raise ValueError("radius is outside the representable metric scale")
    if kind == "sphere":
        phi = float(phi)
        if not np.isfinite(phi) or not 0 < phi < np.pi:
            raise ValueError("sphere phi must lie strictly between 0 and pi")
        metric = np.diag([radius**2, radius**2 * np.sin(phi)**2])
        second = -metric / radius
    elif kind == "cylinder":
        metric = np.diag([radius**2, 1.0])  # coordinates (theta,z)
        second = np.diag([-radius, 0.0])
    else:
        raise ValueError("kind must be sphere or cylinder")
    if not np.all(np.isfinite(metric)) or not np.all(np.isfinite(second)):
        raise ValueError("radius is outside the representable numerical scale")
    if np.min(np.diag(metric)) <= np.finfo(float).tiny:
        raise ValueError("metric is numerically degenerate")
    return metric, second, np.linalg.solve(metric, second)


def helix_frame(t, a=2.0, b=1.0):
    a = positive(a, "a")
    t, b = float(t), float(b)
    if not np.isfinite(t) or not np.isfinite(b):
        raise ValueError("t and b must be finite")
    speed = np.hypot(a, b)
    tangent = np.array([-a*np.sin(t), a*np.cos(t), b]) / speed
    normal = np.array([-np.cos(t), -np.sin(t), 0.0])
    binormal = np.cross(tangent, normal)
    return np.column_stack([tangent, normal, binormal]), (a/speed)/speed, (b/speed)/speed


def sphere_xyz(q, radius=2.0):
    radius = positive(radius, "radius")
    q = np.asarray(q, dtype=float)
    if q.ndim not in (1, 2) or q.size == 0 or q.shape[-1] != 2 or not np.all(np.isfinite(q)):
        raise ValueError("q must be finite, shape (2,) or (n,2)")
    phi, theta = q[..., 0], q[..., 1]
    return radius*np.stack([np.sin(phi)*np.cos(theta), np.sin(phi)*np.sin(theta), np.cos(phi)], axis=-1)


def sphere_rhs(state):
    phi, theta, u, v = vector(state, 4, "state")
    # This chart is deliberately rejected before the poles; switch charts instead.
    if not 1e-6 < phi < np.pi - 1e-6:
        raise ValueError("trajectory left the safe spherical chart; change chart")
    return np.array([u, v, np.sin(phi)*np.cos(phi)*v*v, -2*np.cos(phi)/np.sin(phi)*u*v])


def integrate_sphere(initial, length=2.0, steps=100):
    """Fixed-step classical RK4, state=(phi,theta,dphi/ds,dtheta/ds).
    'length' is the parameter interval; it is arc length only for unit speed.
    """
    length = positive(length, "length")
    if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)) or steps < 1 or steps > 1000000:
        raise ValueError("steps must be an integer from 1 to 1000000")
    initial = vector(initial, 4, "initial")
    sphere_rhs(initial)
    h = length / steps
    result = np.empty((steps+1, 4)); result[0] = initial
    for i in range(steps):
        y = result[i]
        k1 = sphere_rhs(y); k2 = sphere_rhs(y+h*k1/2)
        k3 = sphere_rhs(y+h*k2/2); k4 = sphere_rhs(y+h*k3)
        result[i+1] = y+h*(k1+2*k2+2*k3+k4)/6
        sphere_rhs(result[i+1])
    return np.linspace(0, length, steps+1), result


def invariants(states, radius=2.0):
    radius = positive(radius, "radius")
    states = np.asarray(states, dtype=float)
    if states.ndim != 2 or states.shape[1] != 4 or states.shape[0] == 0 or not np.all(np.isfinite(states)):
        raise ValueError("states must be a nonempty finite (n,4) array")
    phi, _, u, v = states.T
    speed2 = radius**2*(u*u+np.sin(phi)**2*v*v)
    angular = radius**2*np.sin(phi)**2*v
    return speed2, angular


def great_circle(s, radius=2.0):
    """Independent ambient exact solution for the particular lesson initial data."""
    radius = positive(radius, "radius")
    s = np.asarray(s, dtype=float)
    if s.size == 0 or not np.all(np.isfinite(s)):
        raise ValueError("s must be finite")
    a = np.array([np.sqrt(3)/2, 0, 1/2]); b = np.array([0, 1, 0])
    return radius*(np.cos(s[..., None]/radius)*a+np.sin(s[..., None]/radius)*b)


def cylinder_branches(radius=2.0, delta_theta=np.pi/2, delta_z=np.pi/2, windings=range(-2, 3)):
    radius = positive(radius, "radius")
    delta_theta, delta_z = float(delta_theta), float(delta_z)
    if not np.isfinite(delta_theta) or not np.isfinite(delta_z):
        raise ValueError("endpoint differences must be finite")
    winding_list = list(windings)
    if not winding_list or any(isinstance(k, bool) or not isinstance(k, (int, np.integer)) for k in winding_list):
        raise ValueError("windings must be a nonempty collection of integers")
    answer = [(int(k), float(np.hypot(radius*(delta_theta+2*np.pi*k), delta_z))) for k in winding_list]
    if not all(np.isfinite(length) for _, length in answer):
        raise ValueError("endpoint scale is not representable")
    return answer


def report():
    initial = [np.pi/3, 0, 0, 1/np.sqrt(3)]
    rows = []
    for steps in (10, 20, 40, 80):
        s, y = integrate_sphere(initial, steps=steps)
        speed2, angular = invariants(y)
        error = np.max(np.linalg.norm(sphere_xyz(y[:, :2])-great_circle(s), axis=1))
        rows.append((steps, 2/steps, float(error), float(np.max(abs(speed2-speed2[0]))), float(np.max(abs(angular-angular[0])))))
    print("N, h(length unit), max position error, speed^2 drift, angular invariant drift")
    for row in rows: print(" ".join(f"{value:.10g}" for value in row))
    print("cylinder winding,length:", cylinder_branches())
    return rows


def figures(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({"svg.hashsalt": "wwl-geometry-r2-v1", "font.family": "DejaVu Sans"})
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    def save(fig, name):
        path = output/name
        fig.savefig(path, metadata={"Date": None, "Creator": "WWL geometry_lab.py"})
        path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()).rstrip('\n') + '\n', encoding='utf-8')
        plt.close(fig)
    t = np.linspace(0, np.pi/2, 160)
    fig = plt.figure(figsize=(10, 4)); ax = fig.add_subplot(121, projection="3d")
    angles, heights = np.meshgrid(np.linspace(0, 2*np.pi, 24), np.linspace(0, np.pi/2, 8))
    ax.plot_wireframe(2*np.cos(angles), 2*np.sin(angles), heights, color="gray", alpha=.18, linewidth=.5)
    ax.set_box_aspect((4, 4, np.pi/2))
    ax.plot(2*np.cos(t), 2*np.sin(t), t, label="R=2, theta=t, z=t", color="tab:blue", linewidth=2)
    ax.set(xlabel="x [length]", ylabel="y [length]", zlabel="z [length]", title="Cylinder geodesic segment")
    ax.legend(fontsize=7)
    ax2 = fig.add_subplot(122)
    for k in (-1, 0, 1):
        ax2.plot([0, 2*(np.pi/2+2*np.pi*k)], [0, np.pi/2], label=f"winding k={k}")
    ax2.set(xlabel="X=R theta [length]", ylabel="Z=z [length]", title="Different lifts of the same endpoints")
    ax2.legend(); ax2.grid(); fig.tight_layout(); save(fig, "geometry-cylinder.svg")
    s, y = integrate_sphere([np.pi/3, 0, 0, 1/np.sqrt(3)], steps=40)
    exact = great_circle(s); computed = sphere_xyz(y[:, :2])
    fig = plt.figure(figsize=(10, 4)); ax = fig.add_subplot(121, projection="3d")
    ph, th = np.meshgrid(np.linspace(0, np.pi, 15), np.linspace(0, 2*np.pi, 24))
    ax.plot_wireframe(2*np.sin(ph)*np.cos(th), 2*np.sin(ph)*np.sin(th), 2*np.cos(ph), color="gray", alpha=.15, linewidth=.5)
    ax.set_box_aspect((1, 1, 1))
    ax.plot(*exact.T, label="exact great circle, R=2", linewidth=2)
    ax.scatter(*computed[::4].T, s=10, label="RK4 h=0.05")
    ax.set(xlabel="x [length]", ylabel="y [length]", zlabel="z [length]", title="s in [0,2], one safe chart"); ax.legend(fontsize=7)
    ax2 = fig.add_subplot(122); ax2.plot(s, np.linalg.norm(computed-exact, axis=1))
    ax2.set(xlabel="s [length]", ylabel="position error [length]", title="Numerical agreement is not a proof")
    ax2.grid(); fig.tight_layout(); save(fig, "geometry-sphere.svg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--figures", type=Path)
    args = parser.parse_args(); report()
    if args.figures: figures(args.figures)
