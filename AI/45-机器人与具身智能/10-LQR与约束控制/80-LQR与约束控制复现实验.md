---
type: lab-note
domain: artificial-intelligence
stage: 2
content_status: draft
evidence_status: unreviewed
aliases:
- LQR MPC复现实验
sources:
- https://ee363.stanford.edu/archive/lectures/dlqr.pdf
- https://ee363.stanford.edu/archive/lectures/dlqr-ss.pdf
- https://underactuated.mit.edu/lqr.html
- https://underactuated.mit.edu/trajopt.html
prerequisites:
- '[[AI/45-机器人与具身智能/10-LQR与约束控制/00-LQR与约束控制-MOC]]'
---

# LQR 与约束控制复现实验

本实验只用 NumPy；三张 SVG 另用仓库现有 Matplotlib。规范源码和测试都在本目录的 code-sync 中，并在本页逐字镜像。它复算一个一维双积分器有限例，不模拟真实执行器、传感器、接触或碰撞。

## 从发布目录运行

在 Vault 根目录运行单测：

```bash
.venv/bin/python -B -m unittest -v 'AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/test_lqr_mpc_lab.py'
```

生成同一数值例的 SVG 与 JSON；输出位置和全部关键参数显式给出，不依赖 authors 路径：

```bash
.venv/bin/python -B 'AI/45-机器人与具身智能/10-LQR与约束控制/code-sync/lqr_mpc_lab.py' \\
  --output-dir 'AI/45-机器人与具身智能/10-LQR与约束控制/assets' \\
  --dt 0.2 --horizon 8 --umax 0.8
```

候选环境实测得到：无约束、剪裁、盒 QP 与终端等式代价分别为 1.07191995、1.84716559、1.16085039、1.21099600；盒 QP 最大 KKT 违约为 $5.6\times10^{-17}$；终端与移位终端残差约为 $1.1\times10^{-16}$、$1.0\times10^{-16}$。这些是确定性浮点复算，不是硬实时基准。

## 七项检查覆盖什么

1. 双积分器离散矩阵、shape、单位对应的一步解析值；
2. 两步 Riccati 手算数值与终端索引；
3. Riccati 闭环序列与独立堆叠二次型直接解一致；
4. DARE 残差与闭环极点分别检查，并含零残差不稳定分支反例；
5. clip 可行但比连续盒 QP 最优解更差，且独立 KKT 证书区分二者；
6. 终端等式解、精确模型移位可行见证，以及八步不可达初态；
7. CLI 图输出和无效输入边界。

新增四个测试方法核对等式支持域：零行冗余与重复行（含一致/不一致）、空等式、满行秩内点及活跃边界解析值，以及shape/有限值边界；连同原七个方法共十一项，原结果身份不改。

活动集程序接受一到十个标量控制，枚举 lower/free/upper 后在每个活动集内解连续线性方程。非空等式矩阵 `E` 必须在 NumPy 的数值秩判断下满行秩，`d` 的shape须匹配；`E` 为 `(0,n)`、`d` 为 `(0,)` 时等同无等式。零行或重复行可以是数学上合法的冗余约束，但实现明确抛 `ValueError` 表示“不支持”，不把它们误称为无解；重复行右端不一致则数学上无解，也先被同一支持域检查拒绝，不能将该异常用作一般可行性认证。支持域内没有可行候选时返回 `None`；它仍是带容差的浮点枚举，不认证任意病态约束的精确解。它故意不是通用求解器；一般稀疏 MPC 应使用经验证的 QP 求解器并另测时限、缩放、容差与失败路径。

## 规范源码镜像

<!-- code-sync: ./code-sync/lqr_mpc_lab.py -->
```python
#!/usr/bin/env python3
"""Small, deterministic LQR/QP/MPC lab for a one-dimensional double integrator.

The executable model is x=[position_m, velocity_m_per_s] and
u=acceleration_m_per_s2. The active-set solver is intentionally limited to
at most ten scalar controls; it is a checkable teaching oracle, not a general
quadratic-programming package.
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class StackedQuadratic:
    """J(U)=constant + U.T@H@U + 2*f.T@U and X=G@x0+M@U."""

    H: np.ndarray
    f: np.ndarray
    constant: float
    G: np.ndarray
    M: np.ndarray


@dataclass(frozen=True)
class QPSolution:
    u: np.ndarray
    objective_without_constant: float
    patterns_checked: int


def _array(value, *, ndim: int, name: str) -> np.ndarray:
    out = np.asarray(value, dtype=float)
    if out.ndim != ndim or not np.all(np.isfinite(out)):
        raise ValueError(f"{name} must be a finite {ndim}-D array")
    return out


def double_integrator(dt: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    """Exact zero-order-hold discretization for p_dot=v, v_dot=u."""
    if not np.isfinite(dt) or dt <= 0 or dt < 1e-9:
        raise ValueError("dt must be finite and at least 1e-9 s")
    return np.array([[1.0, dt], [0.0, 1.0]]), np.array([[0.5 * dt * dt], [dt]])


def _validate_lqr(A, B, Q, R, Qf=None) -> tuple[np.ndarray, ...]:
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    Q = _array(Q, ndim=2, name="Q")
    R = _array(R, ndim=2, name="R")
    if A.shape[0] != A.shape[1] or B.shape[0] != A.shape[0]:
        raise ValueError("A must be square and B must have the same row count")
    n, m = A.shape[0], B.shape[1]
    if Q.shape != (n, n) or R.shape != (m, m):
        raise ValueError("Q and R shapes must match state and input dimensions")
    if not np.allclose(Q, Q.T, atol=1e-12) or np.min(np.linalg.eigvalsh(Q)) < -1e-12:
        raise ValueError("Q must be symmetric positive semidefinite")
    if not np.allclose(R, R.T, atol=1e-12) or np.min(np.linalg.eigvalsh(R)) <= 0:
        raise ValueError("R must be symmetric positive definite")
    if Qf is None:
        return A, B, Q, R
    Qf = _array(Qf, ndim=2, name="Qf")
    if Qf.shape != (n, n) or not np.allclose(Qf, Qf.T, atol=1e-12):
        raise ValueError("Qf must be symmetric with the state shape")
    if np.min(np.linalg.eigvalsh(Qf)) < -1e-12:
        raise ValueError("Qf must be positive semidefinite")
    return A, B, Q, R, Qf


def riccati_step(A, B, Q, R, S_next) -> tuple[np.ndarray, np.ndarray]:
    A, B, Q, R, S_next = _validate_lqr(A, B, Q, R, S_next)
    middle = R + B.T @ S_next @ B
    K = np.linalg.solve(middle, B.T @ S_next @ A)
    S = Q + A.T @ S_next @ A - A.T @ S_next @ B @ K
    return K, 0.5 * (S + S.T)


def finite_lqr(A, B, Q, R, Qf, horizon: int) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Return K[0:N] and S[0:N+1] for u_k=-K_k x_k."""
    A, B, Q, R, Qf = _validate_lqr(A, B, Q, R, Qf)
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    gains = [np.empty((B.shape[1], A.shape[0])) for _ in range(horizon)]
    values = [np.empty_like(A) for _ in range(horizon)] + [Qf.copy()]
    S = Qf.copy()
    for k in range(horizon - 1, -1, -1):
        gains[k], S = riccati_step(A, B, Q, R, S)
        values[k] = S
    return gains, values


def rollout(A, B, x0, controls) -> np.ndarray:
    A = _array(A, ndim=2, name="A")
    B = _array(B, ndim=2, name="B")
    x0 = _array(x0, ndim=1, name="x0")
    controls = _array(controls, ndim=2, name="controls")
    if A.shape[0] != A.shape[1] or x0.shape != (A.shape[0],):
        raise ValueError("x0 and A shapes do not match")
    if B.shape != (A.shape[0], controls.shape[1]):
        raise ValueError("B and control shapes do not match")
    states = np.empty((controls.shape[0] + 1, A.shape[0]))
    states[0] = x0
    for k, u in enumerate(controls):
        states[k + 1] = A @ states[k] + B @ u
    return states


def finite_cost(states, controls, Q, R, Qf) -> float:
    states = _array(states, ndim=2, name="states")
    controls = _array(controls, ndim=2, name="controls")
    _, _, Q, R, Qf = _validate_lqr(
        np.eye(states.shape[1]), np.zeros((states.shape[1], controls.shape[1])), Q, R, Qf
    )
    if states.shape[0] != controls.shape[0] + 1:
        raise ValueError("states must contain one more sample than controls")
    running = sum(float(x @ Q @ x + u @ R @ u) for x, u in zip(states[:-1], controls))
    return running + float(states[-1] @ Qf @ states[-1])


def stack_quadratic(A, B, Q, R, Qf, horizon: int, x0) -> StackedQuadratic:
    """Eliminate states for a scalar-input finite-horizon LQR problem."""
    A, B, Q, R, Qf = _validate_lqr(A, B, Q, R, Qf)
    x0 = _array(x0, ndim=1, name="x0")
    if B.shape[1] != 1:
        raise ValueError("this small stacking oracle supports one scalar input")
    if x0.shape != (A.shape[0],) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("x0 shape or horizon is invalid")
    n = A.shape[0]
    G = np.vstack([np.linalg.matrix_power(A, k) for k in range(1, horizon + 1)])
    M = np.zeros((n * horizon, horizon))
    for k in range(1, horizon + 1):
        for j in range(k):
            M[n * (k - 1):n * k, j:j + 1] = np.linalg.matrix_power(A, k - 1 - j) @ B
    Qbar = np.zeros((n * horizon, n * horizon))
    for k in range(horizon):
        Qbar[n * k:n * (k + 1), n * k:n * (k + 1)] = Qf if k == horizon - 1 else Q
    Rbar = np.eye(horizon) * float(R[0, 0])
    free_states = G @ x0
    H = M.T @ Qbar @ M + Rbar
    f = M.T @ Qbar @ free_states
    constant = float(x0 @ Q @ x0 + free_states @ Qbar @ free_states)
    return StackedQuadratic(0.5 * (H + H.T), f, constant, G, M)


def direct_unconstrained(problem: StackedQuadratic) -> np.ndarray:
    return np.linalg.solve(problem.H, -problem.f)


def stacked_objective(problem: StackedQuadratic, u) -> float:
    u = _array(u, ndim=1, name="u")
    if u.shape != problem.f.shape:
        raise ValueError("u has the wrong horizon")
    return float(problem.constant + u @ problem.H @ u + 2.0 * problem.f @ u)


def solve_box_qp_active_set(H, f, lower, upper, *, E=None, d=None) -> QPSolution | None:
    """Enumerate a small strictly convex box QP with optional full-row-rank E.

    Empty E with shape (0,n) means no equalities. Nonempty E must have
    full row rank under NumPy's numerical rank test. Rank-deficient E is
    unsupported and raises ValueError regardless of consistency; this is
    not an infeasibility result. This is a finite-precision teaching solver,
    not an exact-arithmetic oracle for arbitrary ill-conditioned constraints.
    """
    H = _array(H, ndim=2, name="H")
    f = _array(f, ndim=1, name="f")
    lower = _array(lower, ndim=1, name="lower")
    upper = _array(upper, ndim=1, name="upper")
    n = f.size
    if not 1 <= n <= 10 or H.shape != (n, n) or lower.shape != (n,) or upper.shape != (n,):
        raise ValueError("box QP must have matching shapes and one to ten variables")
    if not np.allclose(H, H.T, atol=1e-12) or np.min(np.linalg.eigvalsh(H)) <= 0:
        raise ValueError("H must be symmetric positive definite")
    if np.any(lower >= upper):
        raise ValueError("every lower bound must be strictly below its upper bound")
    if (E is None) != (d is None):
        raise ValueError("E and d must be supplied together")
    if E is not None:
        E = _array(E, ndim=2, name="E")
        d = _array(d, ndim=1, name="d")
        if E.shape[1] != n or d.shape != (E.shape[0],):
            raise ValueError("equality shapes do not match the QP")
        if E.shape[0] == 0:
            E, d = None, None
        elif np.linalg.matrix_rank(E) != E.shape[0]:
            raise ValueError("rank-deficient E is unsupported; supply independent equality rows")
    best: tuple[float, np.ndarray] | None = None
    checked = 0
    for pattern in itertools.product((-1, 0, 1), repeat=n):
        checked += 1
        pattern_array = np.asarray(pattern)
        fixed = pattern_array != 0
        free = ~fixed
        u = np.zeros(n)
        u[pattern_array == -1] = lower[pattern_array == -1]
        u[pattern_array == 1] = upper[pattern_array == 1]
        Hff = H[np.ix_(free, free)]
        rhs_stationary = -f[free] - H[np.ix_(free, fixed)] @ u[fixed]
        if E is None:
            if np.any(free):
                u[free] = np.linalg.solve(Hff, rhs_stationary)
        else:
            rhs_equality = d - E[:, fixed] @ u[fixed]
            if not np.any(free):
                if np.max(np.abs(rhs_equality), initial=0.0) > 1e-9:
                    continue
            else:
                Ef = E[:, free]
                kkt = np.block([[Hff, Ef.T], [Ef, np.zeros((E.shape[0], E.shape[0]))]])
                try:
                    solved = np.linalg.solve(kkt, np.concatenate([rhs_stationary, rhs_equality]))
                except np.linalg.LinAlgError:
                    continue
                u[free] = solved[:np.count_nonzero(free)]
                if np.max(np.abs(E @ u - d), initial=0.0) > 1e-8:
                    continue
        if np.any(u < lower - 1e-9) or np.any(u > upper + 1e-9):
            continue
        objective = float(u @ H @ u + 2.0 * f @ u)
        if best is None or objective < best[0]:
            best = objective, u.copy()
    return None if best is None else QPSolution(best[1], best[0], checked)


def box_kkt_violation(H, f, u, lower, upper, *, tolerance: float = 1e-8) -> float:
    """Independent first-order certificate for a box-only convex QP."""
    H = _array(H, ndim=2, name="H")
    f = _array(f, ndim=1, name="f")
    u = _array(u, ndim=1, name="u")
    lower = _array(lower, ndim=1, name="lower")
    upper = _array(upper, ndim=1, name="upper")
    if H.shape != (u.size, u.size) or f.shape != u.shape or lower.shape != u.shape or upper.shape != u.shape:
        raise ValueError("KKT inputs have inconsistent shapes")
    reduced_gradient = H @ u + f
    violation = 0.0
    for ui, gi, lo, hi in zip(u, reduced_gradient, lower, upper):
        if abs(ui - lo) <= tolerance:
            violation = max(violation, max(0.0, -float(gi)))
        elif abs(ui - hi) <= tolerance:
            violation = max(violation, max(0.0, float(gi)))
        else:
            violation = max(violation, abs(float(gi)))
    violation = max(violation, float(np.max(np.maximum(lower - u, 0.0), initial=0.0)))
    violation = max(violation, float(np.max(np.maximum(u - upper, 0.0), initial=0.0)))
    return violation


def dare_iteration(A, B, Q, R, *, tolerance: float = 1e-12, max_iterations: int = 10000):
    A, B, Q, R = _validate_lqr(A, B, Q, R)
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("iteration limits must be positive")
    S = np.zeros_like(Q)
    for iteration in range(1, max_iterations + 1):
        _, S_new = riccati_step(A, B, Q, R, S)
        if np.linalg.norm(S_new - S, ord="fro") <= tolerance:
            K = np.linalg.solve(R + B.T @ S_new @ B, B.T @ S_new @ A)
            return S_new, K, iteration
        S = S_new
    raise RuntimeError("DARE value iteration did not converge")


def dare_residual(A, B, Q, R, S) -> float:
    A, B, Q, R, S = _validate_lqr(A, B, Q, R, S)
    K = np.linalg.solve(R + B.T @ S @ B, B.T @ S @ A)
    rhs = Q + A.T @ S @ A - A.T @ S @ B @ K
    return float(np.linalg.norm(S - rhs, ord="fro"))


def default_problem(dt: float = 0.2, horizon: int = 8, x0=(0.5, 0.0)):
    A, B = double_integrator(dt)
    Q = np.diag([1.0, 0.1])
    R = np.array([[0.05]])
    Qf = np.diag([8.0, 2.0])
    x0_array = _array(x0, ndim=1, name="x0")
    if x0_array.shape != (2,):
        raise ValueError("x0 must contain position and velocity")
    return A, B, Q, R, Qf, stack_quadratic(A, B, Q, R, Qf, horizon, x0_array), x0_array


def compute_demo(dt: float = 0.2, horizon: int = 8, umax: float = 0.8) -> dict:
    if not np.isfinite(umax) or umax <= 0:
        raise ValueError("umax must be finite and positive")
    A, B, Q, R, Qf, problem, x0 = default_problem(dt, horizon)
    lower = np.full(horizon, -umax)
    upper = np.full(horizon, umax)
    unconstrained = direct_unconstrained(problem)
    clipped = np.clip(unconstrained, lower, upper)
    constrained = solve_box_qp_active_set(problem.H, problem.f, lower, upper)
    if constrained is None:
        raise RuntimeError("default box QP unexpectedly infeasible")
    n = A.shape[0]
    terminal_E = problem.M[n * (horizon - 1):n * horizon]
    terminal_d = -problem.G[n * (horizon - 1):n * horizon] @ x0
    terminal = solve_box_qp_active_set(problem.H, problem.f, lower, upper, E=terminal_E, d=terminal_d)
    if terminal is None:
        raise RuntimeError("default terminal-equality MPC problem unexpectedly infeasible")
    controls = {
        "unconstrained": unconstrained,
        "clipped": clipped,
        "box_qp": constrained.u,
        "terminal_mpc": terminal.u,
    }
    states = {name: rollout(A, B, x0, u[:, None]) for name, u in controls.items()}
    costs = {name: finite_cost(states[name], u[:, None], Q, R, Qf) for name, u in controls.items()}
    shifted = np.concatenate([terminal.u[1:], [0.0]])
    x1 = states["terminal_mpc"][1]
    shifted_states = rollout(A, B, x1, shifted[:, None])
    return {
        "A": A, "B": B, "Q": Q, "R": R, "Qf": Qf, "x0": x0,
        "controls": controls, "states": states, "costs": costs,
        "box_kkt_violation": box_kkt_violation(problem.H, problem.f, constrained.u, lower, upper),
        "terminal_residual": float(np.linalg.norm(states["terminal_mpc"][-1])),
        "shifted_terminal_residual": float(np.linalg.norm(shifted_states[-1])),
        "shifted_states": shifted_states,
        "patterns_checked": constrained.patterns_checked,
    }


def save_figures(result: dict, output_dir: Path, dt: float, umax: float) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "wwl-lqr-mpc"
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    t = np.arange(next(iter(result["states"].values())).shape[0]) * dt
    colors = {"unconstrained": "#7a7a7a", "clipped": "#d95f02", "box_qp": "#1b9e77"}
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)
    for name in ("unconstrained", "clipped", "box_qp"):
        axes[0].plot(t, result["states"][name][:, 0], marker="o", ms=3, color=colors[name], label=name)
        axes[1].plot(t, result["states"][name][:, 1], marker="o", ms=3, color=colors[name], label=name)
    axes[0].set_ylabel("position (m)"); axes[1].set_ylabel("velocity (m/s)"); axes[1].set_xlabel("time (s)")
    axes[0].legend(ncol=3, fontsize=8); axes[0].grid(alpha=0.25); axes[1].grid(alpha=0.25)
    fig.suptitle("Same model, different finite-horizon decisions"); fig.tight_layout()
    path = output_dir / "finite-horizon-trajectories.svg"
    fig.savefig(path, format="svg", metadata={"Date": None}); plt.close(fig); created.append(path)

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.6))
    k = np.arange(len(result["controls"]["clipped"]))
    for name in ("unconstrained", "clipped", "box_qp"):
        axes[0].step(k, result["controls"][name], where="post", color=colors[name], label=name)
    axes[0].axhline(umax, color="black", lw=0.8, ls="--"); axes[0].axhline(-umax, color="black", lw=0.8, ls="--")
    axes[0].set_xlabel("control step k"); axes[0].set_ylabel("u (m/s²)"); axes[0].grid(alpha=0.25); axes[0].legend(fontsize=8)
    names = ["clipped", "box_qp"]
    axes[1].bar(names, [result["costs"][name] for name in names], color=[colors[n] for n in names])
    axes[1].set_ylabel("dimensionless finite cost J"); axes[1].set_title("Clipping is feasible, but costlier"); axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout(); path = output_dir / "clip-versus-box-qp.svg"
    fig.savefig(path, format="svg", metadata={"Date": None}); plt.close(fig); created.append(path)

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)
    terminal_states = result["states"]["terminal_mpc"]; shifted_states = result["shifted_states"]
    axes[0].plot(t, terminal_states[:, 0], "o-", color="#7570b3", label="plan at k")
    axes[0].plot(t, shifted_states[:, 0], "s--", color="#1b9e77", label="shifted witness at k+1")
    axes[1].plot(t, terminal_states[:, 1], "o-", color="#7570b3")
    axes[1].plot(t, shifted_states[:, 1], "s--", color="#1b9e77")
    axes[0].axhline(0, color="black", lw=0.7); axes[1].axhline(0, color="black", lw=0.7)
    axes[0].set_ylabel("position (m)"); axes[1].set_ylabel("velocity (m/s)"); axes[1].set_xlabel("local horizon time (s)")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=0.25); axes[1].grid(alpha=0.25)
    fig.suptitle("Terminal equality supplies the next feasible candidate"); fig.tight_layout()
    path = output_dir / "terminal-shift-witness.svg"
    fig.savefig(path, format="svg", metadata={"Date": None}); plt.close(fig); created.append(path)
    return created


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--horizon", type=int, default=8)
    parser.add_argument("--umax", type=float, default=0.8)
    args = parser.parse_args(argv)
    result = compute_demo(args.dt, args.horizon, args.umax)
    figures = save_figures(result, args.output_dir, args.dt, args.umax)
    summary = {
        "schema": "wwl-lqr-mpc-demo-v1", "dt_s": args.dt, "horizon": args.horizon,
        "umax_m_per_s2": args.umax, "x0": result["x0"].tolist(), "costs": result["costs"],
        "box_kkt_violation": result["box_kkt_violation"], "terminal_residual": result["terminal_residual"],
        "shifted_terminal_residual": result["shifted_terminal_residual"], "figures": [p.name for p in figures],
    }
    summary_path = args.output_dir / "demo-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 测试镜像

<!-- code-sync: ./code-sync/test_lqr_mpc_lab.py -->
```python
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


MODULE_PATH = Path(__file__).with_name("lqr_mpc_lab.py")
SPEC = importlib.util.spec_from_file_location("lqr_mpc_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class LqrMpcLabTests(unittest.TestCase):
    def test_double_integrator_units_and_exact_step(self):
        A, B = lab.double_integrator(0.2)
        np.testing.assert_allclose(A, [[1, 0.2], [0, 1]])
        np.testing.assert_allclose(B, [[0.02], [0.2]])
        states = lab.rollout(A, B, [0, 1], np.array([[2.0]]))
        np.testing.assert_allclose(states[-1], [0.24, 1.4])

    def test_two_step_riccati_hand_values_and_direct_oracle(self):
        A, B = lab.double_integrator(0.2)
        Q = np.diag([1.0, 0.1]); R = np.array([[0.05]]); Qf = np.diag([8.0, 2.0])
        gains, values = lab.finite_lqr(A, B, Q, R, Qf, 2)
        np.testing.assert_allclose(gains[1], [[1.2012012012, 3.2432432432]], rtol=1e-9)
        np.testing.assert_allclose(gains[0], [[3.8120857063, 2.9523387172]], rtol=1e-9)
        np.testing.assert_allclose(values[2], Qf)
        problem = lab.stack_quadratic(A, B, Q, R, Qf, 2, [1.0, 0.0])
        direct = lab.direct_unconstrained(problem)
        x = np.array([1.0, 0.0]); dynamic = []
        for K in gains:
            u = -K @ x; dynamic.append(float(u[0])); x = A @ x + B[:, 0] * u[0]
        np.testing.assert_allclose(dynamic, direct, atol=1e-11)
        states = lab.rollout(A, B, [1.0, 0.0], direct[:, None])
        self.assertAlmostEqual(lab.finite_cost(states, direct[:, None], Q, R, Qf), lab.stacked_objective(problem, direct))

    def test_dare_residual_and_closed_loop_poles_are_separate_checks(self):
        A, B = lab.double_integrator(0.2)
        Q = np.diag([1.0, 0.1]); R = np.array([[0.05]])
        S, K, iterations = lab.dare_iteration(A, B, Q, R)
        self.assertLess(iterations, 200)
        self.assertLess(lab.dare_residual(A, B, Q, R, S), 1e-10)
        self.assertLess(np.max(np.abs(np.linalg.eigvals(A - B @ K))), 1.0)
        np.testing.assert_allclose(K, [[3.21775154, 2.73329391]], rtol=2e-8)

        # Q=0 does not detect unstable A=2. Both S=0 and S=3 solve DARE,
        # but only S=3 gives the stabilizing pole 0.5.
        As = np.array([[2.0]]); Bs = np.array([[1.0]])
        Qs = np.array([[0.0]]); Rs = np.array([[1.0]])
        for candidate in (np.array([[0.0]]), np.array([[3.0]])):
            self.assertLess(lab.dare_residual(As, Bs, Qs, Rs, candidate), 1e-12)
        K0 = np.linalg.solve(Rs + Bs.T @ np.zeros((1, 1)) @ Bs, Bs.T @ np.zeros((1, 1)) @ As)
        K3 = np.linalg.solve(Rs + Bs.T @ np.array([[3.0]]) @ Bs, Bs.T @ np.array([[3.0]]) @ As)
        self.assertEqual(float((As - Bs @ K0)[0, 0]), 2.0)
        self.assertEqual(float((As - Bs @ K3)[0, 0]), 0.5)

    def test_clipping_is_feasible_but_not_optimal(self):
        *_, problem, _ = lab.default_problem()
        lower = np.full(8, -0.8); upper = np.full(8, 0.8)
        unconstrained = lab.direct_unconstrained(problem)
        clipped = np.clip(unconstrained, lower, upper)
        optimum = lab.solve_box_qp_active_set(problem.H, problem.f, lower, upper)
        self.assertIsNotNone(optimum)
        assert optimum is not None
        self.assertLess(lab.stacked_objective(problem, optimum.u), lab.stacked_objective(problem, clipped) - 0.6)
        self.assertLess(lab.box_kkt_violation(problem.H, problem.f, optimum.u, lower, upper), 1e-10)
        self.assertGreater(lab.box_kkt_violation(problem.H, problem.f, clipped, lower, upper), 0.1)

    def test_terminal_equality_and_recursive_shift_witness(self):
        result = lab.compute_demo()
        self.assertLess(result["terminal_residual"], 1e-12)
        self.assertLess(result["shifted_terminal_residual"], 1e-12)
        self.assertLessEqual(np.max(np.abs(result["controls"]["terminal_mpc"])), 0.8 + 1e-12)
        self.assertLessEqual(np.max(np.abs(np.r_[result["controls"]["terminal_mpc"][1:], 0.0])), 0.8 + 1e-12)

        A, B, Q, R, Qf, problem, x0 = lab.default_problem(x0=(0.6, 0.0))
        E = problem.M[-2:]; d = -problem.G[-2:] @ x0
        infeasible = lab.solve_box_qp_active_set(problem.H, problem.f, np.full(8, -0.8), np.full(8, 0.8), E=E, d=d)
        self.assertIsNone(infeasible)

    def test_cli_figure_outputs(self):
        result = lab.compute_demo()
        with tempfile.TemporaryDirectory() as directory:
            paths = lab.save_figures(result, Path(directory), 0.2, 0.8)
            self.assertEqual({p.name for p in paths}, {
                "finite-horizon-trajectories.svg", "clip-versus-box-qp.svg", "terminal-shift-witness.svg"
            })
            self.assertTrue(all(p.stat().st_size > 1000 for p in paths))

    def test_rank_deficient_equalities_are_unsupported_not_infeasible(self):
        # min u^2 over [-1,1]: zero-row equality leaves optimum u=0, J=0.
        # Repeating u=0 is also consistent, while u=0 and u=1 contradict.
        # All three lie outside this implementation's declared rank domain.
        for E, d in (([[0.]], [0.]), ([[1.], [1.]], [0., 0.]),
                     ([[1.], [1.]], [0., 1.])):
            with self.subTest(E=E, d=d):
                with self.assertRaisesRegex(ValueError, "rank-deficient E is unsupported"):
                    lab.solve_box_qp_active_set([[1.]], [0.], [-1.], [1.], E=E, d=d)

    def test_empty_equalities_are_box_only(self):
        # u^2-0.5u=(u-0.25)^2-0.0625.
        plain = lab.solve_box_qp_active_set([[1.]], [-0.25], [-1.], [1.])
        empty = lab.solve_box_qp_active_set([[1.]], [-0.25], [-1.], [1.],
                                            E=np.empty((0, 1)), d=np.empty(0))
        for solution in (plain, empty):
            self.assertIsNotNone(solution)
            np.testing.assert_allclose(solution.u, [0.25], atol=1e-14)
            self.assertAlmostEqual(solution.objective_without_constant, -0.0625)
        self.assertEqual(plain.patterns_checked, empty.patterns_checked)

    def test_full_row_rank_equalities_with_interior_and_active_bound(self):
        # u1+u2=1 minimizes u1^2+u2^2 at (0.5,0.5), J=0.5.
        # Restrict u1<=0.25: minimizing t^2+(1-t)^2 on [-1,0.25]
        # selects t=0.25, giving (0.25,0.75), J=0.625.
        for upper, expected, objective in (([2., 2.], [0.5, 0.5], 0.5),
                                            ([0.25, 2.], [0.25, 0.75], 0.625)):
            solution = lab.solve_box_qp_active_set(np.eye(2), [0., 0.], [-1., -1.], upper,
                                                   E=[[1., 1.]], d=[1.])
            self.assertIsNotNone(solution)
            np.testing.assert_allclose(solution.u, expected, atol=1e-14)
            self.assertAlmostEqual(solution.objective_without_constant, objective)
        # Full-rank u=2 has no point in [-1,1]: supported but infeasible.
        self.assertIsNone(lab.solve_box_qp_active_set([[1.]], [0.], [-1.], [1.], E=[[1.]], d=[2.]))

    def test_equality_input_shapes_and_finite_values(self):
        for E, d in (([[1., 0.]], [0.]), ([[1.]], []),
                     (np.empty((0, 2)), []), ([], []),
                     ([[np.nan]], [0.]), ([[1.]], [np.inf]),
                     ([[1.]], None), (None, [0.])):
            with self.subTest(E=E, d=d):
                with self.assertRaises(ValueError):
                    lab.solve_box_qp_active_set([[1.]], [0.], [-1.], [1.], E=E, d=d)
        with self.assertRaises(ValueError):
            lab.solve_box_qp_active_set(np.empty((0, 0)), [], [], [])

    def test_invalid_inputs(self):
        for dt in (0, -1, np.nan, np.inf, 1e-12):
            with self.assertRaises(ValueError): lab.double_integrator(dt)
        A, B = lab.double_integrator()
        with self.assertRaises(ValueError): lab.finite_lqr(A, B, np.diag([1, -1]), [[1]], np.eye(2), 3)
        with self.assertRaises(ValueError): lab.solve_box_qp_active_set(np.eye(11), np.zeros(11), -np.ones(11), np.ones(11))
        with self.assertRaises(ValueError): lab.default_problem(x0=(1,))


if __name__ == "__main__":
    unittest.main()
```

返回[[AI/45-机器人与具身智能/10-LQR与约束控制/00-LQR与约束控制-MOC|课程地图]]。内容、来源、真实 Obsidian 显示和真人理解仍需与程序测试分层验收。

