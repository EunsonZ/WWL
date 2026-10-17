#!/usr/bin/env python3
"""Finite 1-D blocking-electron DD--Poisson teaching model; SI input.

No artificial sources, density clipping, or overwritten failed steps.
Only NumPy/SciPy are required to run; --plots additionally uses Matplotlib.
"""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import sys

import numpy as np
import scipy
from scipy.integrate import quad
from scipy.sparse import lil_matrix, diags
from scipy.sparse.linalg import spsolve

Q = 1.602176634e-19
KB = 1.380649e-23
EPS0 = 8.8541878128e-12


class NumericalFailure(RuntimeError):
    pass


def bernoulli(z):
    """B and analytic derivative, including cancellation-safe small z."""
    z = np.asarray(z, dtype=float)
    if np.any(~np.isfinite(z)) or np.max(np.abs(z), initial=0) > 80:
        raise NumericalFailure("Bernoulli argument outside finite |z|<=80 contract")
    small = np.abs(z) < 1e-3
    b = np.empty_like(z)
    bp = np.empty_like(z)
    t = z[small]
    b[small] = 1-t/2+t*t/12-t**4/720+t**6/30240
    bp[small] = -.5+t/6-t**3/180+t**5/5040
    t = z[~small]
    den = np.expm1(t)
    b[~small] = t/den
    bp[~small] = (den-t*np.exp(t))/den**2
    return b, bp


def validate(card):
    keys = {"L_m", "T_K", "mu_m2_Vs", "nref_m3", "eps_relative",
            "equilibrium_amplitude", "perturbation", "cells", "dtau", "tau_end"}
    if set(card) != keys:
        raise ValueError("input must contain exactly the declared parameter keys")
    for key, value in card.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key}: finite numeric input required")
    for key in ("L_m", "T_K", "mu_m2_Vs", "nref_m3", "eps_relative", "dtau", "tau_end"):
        if card[key] <= 0:
            raise ValueError(f"{key}: must be positive")
    if type(card["cells"]) is not int or not 8 <= card["cells"] <= 256:
        raise ValueError("cells must be an integer in [8,256]")
    if not 0 <= card["equilibrium_amplitude"] <= 1 or not 0 <= card["perturbation"] <= .5:
        raise ValueError("amplitude in [0,1], perturbation in [0,.5] required")
    if card["tau_end"]/card["dtau"] > 10000:
        raise ValueError("at most 10000 time steps")
    return card


def scales(card):
    vt = KB*card["T_K"]/Q
    diffusion = card["mu_m2_Vs"]*vt
    result = {"VT_V": vt, "D_m2_s": diffusion,
            "time_s": card["L_m"]**2/diffusion,
            "lambda2": EPS0*card["eps_relative"]*vt/(Q*card["nref_m3"]*card["L_m"]**2),
            "particle_flux_m2s": card["nref_m3"]*diffusion/card["L_m"],
            "electron_current_Am2": Q*card["nref_m3"]*diffusion/card["L_m"]}
    if not all(math.isfinite(x) and x > 0 for x in result.values()):
        raise ValueError("derived scales must be finite and positive")
    if not 1e-5 <= result["lambda2"] <= 100:
        raise ValueError("this teaching solver requires lambda2 in [1e-5,100]")
    return result


class Model:
    def __init__(self, card, cells=None):
        self.card = validate(card)
        self.N = card["cells"] if cells is None else cells
        self.h = 1/self.N
        self.s = np.linspace(0, 1, self.N+1)
        self.w = np.full(self.N+1, self.h)
        self.w[[0, -1]] /= 2
        self.scale = scales(card)
        self.l2 = self.scale["lambda2"]
        self.ustar = card["equilibrium_amplitude"]*np.sin(np.pi*self.s)
        self.nstar = np.exp(self.ustar)
        self.d = self.nstar+self.l2*np.pi**2*self.ustar
        # The SAME continuous target mass is used on every mesh.
        self.mass = quad(lambda s: math.exp(card["equilibrium_amplitude"]*math.sin(math.pi*s)),
                         0, 1, epsabs=2e-13, epsrel=2e-13)[0]
        self.P = diags([-np.ones(self.N-2), 2*np.ones(self.N-1), -np.ones(self.N-2)],
                       [-1, 0, 1], format="csc")*self.l2/self.h**2

    def poisson(self, n):
        u = np.zeros(self.N+1)
        u[1:-1] = spsolve(self.P, self.d[1:-1]-n[1:-1])
        return u

    def flux(self, n, u):
        delta = np.diff(u)
        b, bp = bernoulli(delta)
        bm, bpm = bernoulli(-delta)
        f = (bm*n[:-1]-b*n[1:])/self.h
        c = (-bpm*n[:-1]-bp*n[1:])/self.h
        return f, bm/self.h, -b/self.h, c

    def residual_jacobian(self, n, u, old, dt):
        N = self.N
        f, a, b, c = self.flux(n, u)
        divergence = np.r_[f[0], np.diff(f), -f[-1]]/self.w
        r = np.r_[n-old+dt*divergence,
                  self.P@u[1:-1]+n[1:-1]-self.d[1:-1]]
        j = lil_matrix((2*N, 2*N))
        j[:N+1, :N+1] = diags(np.ones(N+1))
        for edge in range(N):
            for row, sign in ((edge, 1), (edge+1, -1)):
                factor = dt*sign/self.w[row]
                j[row, edge] += factor*a[edge]
                j[row, edge+1] += factor*b[edge]
                if edge > 0:
                    j[row, N+edge] -= factor*c[edge]
                if edge+1 < N:
                    j[row, N+edge+1] += factor*c[edge]
        for i in range(1, N):
            row = N+i
            j[row, i] = 1
            j[row, N+i] = 2*self.l2/self.h**2
            if i > 1:
                j[row, N+i-1] = -self.l2/self.h**2
            if i < N-1:
                j[row, N+i+1] = -self.l2/self.h**2
        return r, j.tocsc()

    def step(self, old, old_u, dt, max_newton=30, tolerance=1e-10):
        n, u = old.copy(), old_u.copy()
        total_backtracks = 0
        for iteration in range(max_newton+1):
            r, j = self.residual_jacobian(n, u, old, dt)
            norm = float(np.linalg.norm(r, np.inf))
            if norm <= tolerance:
                return n, u, {"iterations": iteration, "backtracks": total_backtracks, "residual": norm}
            if iteration == max_newton:
                raise NumericalFailure(f"Newton budget exhausted: residual={norm:.8g}")
            delta = spsolve(j, -r)
            if not np.all(np.isfinite(delta)):
                raise NumericalFailure("nonfinite Newton correction")
            for k in range(25):
                alpha = 2.0**(-k)
                candidate_n = n+alpha*delta[:self.N+1]
                candidate_u = u.copy()
                candidate_u[1:-1] += alpha*delta[self.N+1:]
                if np.min(candidate_n) <= 1e-12 or np.max(np.abs(candidate_u)) > 40:
                    continue
                candidate_r, _ = self.residual_jacobian(candidate_n, candidate_u, old, dt)
                if np.linalg.norm(candidate_r, np.inf) <= (1-1e-4*alpha)*norm:
                    n, u = candidate_n, candidate_u
                    total_backtracks += k
                    break
            else:
                raise NumericalFailure("line-search budget exhausted")
        raise AssertionError("unreachable")

    def equilibrium(self):
        """Independent steady equations: n=exp(c+u), Poisson + total mass."""
        u = self.ustar.copy()
        c = math.log(self.mass/float(self.w@np.exp(u)))
        for _ in range(30):
            n = np.exp(c+u)
            r = np.r_[self.P@u[1:-1]+n[1:-1]-self.d[1:-1], self.w@n-self.mass]
            if np.linalg.norm(r, np.inf) < 1e-12:
                return n, u, c
            j = np.zeros((self.N, self.N))
            j[:-1, :-1] = self.P.toarray()+np.diag(n[1:-1])
            j[:-1, -1] = n[1:-1]
            j[-1, :-1] = self.w[1:-1]*n[1:-1]
            j[-1, -1] = self.w@n
            delta = np.linalg.solve(j, -r)
            u[1:-1] += delta[:-1]
            c += delta[-1]
        raise NumericalFailure("equilibrium budget exhausted")

    def energy(self, n, u):
        return float(self.w@(n*(np.log(n)-1))+self.l2*np.sum(np.diff(u)**2)/(2*self.h))

    def initial(self):
        n = self.nstar*(1+self.card["perturbation"]*np.cos(np.pi*self.s))
        n *= self.mass/(self.w@n)
        return n, self.poisson(n)

    def run(self, dt=None, end=None):
        dt = self.card["dtau"] if dt is None else dt
        end = self.card["tau_end"] if end is None else end
        n, u = self.initial()
        trajectory = []
        snapshots = []
        tau = 0.0
        max_residual = 0.0
        max_iterations = 0
        backtracks = 0
        previous_energy = self.energy(n, u)
        max_energy_increase = 0.0
        max_total_current_spread = 0.0
        current_trajectory = []
        min_density = float(n.min())
        next_snapshot = 0
        targets = [0, end/10, end/2, end]
        step_count = max(1, math.ceil(end/dt))
        for step_index in range(step_count+1):
            f = self.flux(n, u)[0]
            trajectory.append({"tau": tau, "mass": float(self.w@n), "energy": self.energy(n, u),
                               "min_density": float(n.min()), "max_abs_flux": float(np.max(np.abs(f)))})
            if next_snapshot < len(targets) and tau >= targets[next_snapshot]:
                snapshots.append({"tau": tau, "n": n.tolist(), "u": u.tolist(), "F": f.tolist()})
                next_snapshot += 1
            if step_index == step_count:
                break
            next_tau = min((step_index+1)*dt, end)
            step_dt = next_tau-tau
            old_n, old_u = n, u
            n, u, info = self.step(n, u, step_dt)
            tau = next_tau
            # D is normalized by q*nref*L, current by q*nref*D/L.
            old_displacement = -self.l2*np.diff(old_u)/self.h
            displacement = -self.l2*np.diff(u)/self.h
            total_inner = -self.flux(n, u)[0]+(displacement-old_displacement)/step_dt
            left_displacement = displacement[0]-(self.d[0]-n[0])*self.w[0]
            old_left_displacement = old_displacement[0]-(self.d[0]-old_n[0])*self.w[0]
            right_displacement = displacement[-1]+(self.d[-1]-n[-1])*self.w[-1]
            old_right_displacement = old_displacement[-1]+(self.d[-1]-old_n[-1])*self.w[-1]
            terminal_left = (left_displacement-old_left_displacement)/step_dt
            terminal_right = (right_displacement-old_right_displacement)/step_dt
            all_current = np.r_[terminal_left, total_inner, terminal_right]
            spread = float(np.ptp(all_current))
            max_total_current_spread = max(max_total_current_spread, spread)
            current_trajectory.append({"tau": tau, "left_total_current": float(terminal_left),
                                       "right_total_current": float(terminal_right), "total_current_spread": spread})
            max_residual = max(max_residual, info["residual"])
            max_iterations = max(max_iterations, info["iterations"])
            backtracks += info["backtracks"]
            energy = self.energy(n, u)
            max_energy_increase = max(max_energy_increase, energy-previous_energy)
            previous_energy = energy
            min_density = min(min_density, float(n.min()))
        ne, ue, c = self.equilibrium()
        summary = {"cells": self.N, "dtau": dt, "tau_end": end,
                   "mass_target": self.mass, "mass_max_error": max(abs(a["mass"]-self.mass) for a in trajectory),
                   "min_density": min_density, "max_energy_increase": max_energy_increase,
                   "max_residual": max_residual, "max_newton_iterations": max_iterations,
                   "total_backtracks": backtracks, "final_n_equilibrium_error": float(np.max(np.abs(n-ne))),
                   "max_total_current_spread": max_total_current_spread,
                   "final_u_equilibrium_error": float(np.max(np.abs(u-ue))),
                   "equilibrium_u_continuous_error": float(np.max(np.abs(ue-self.ustar))),
                   "equilibrium_n_continuous_error": float(np.max(np.abs(ne-self.nstar))),
                   "equilibrium_c": c}
        return {"summary": summary, "s": self.s.tolist(), "d": self.d.tolist(),
                "equilibrium_n": ne.tolist(), "equilibrium_u": ue.tolist(),
                "trajectory": trajectory, "current_trajectory": current_trajectory,
                "snapshots": snapshots}, n, u


def linear_check(cells=64, dt=.001, end=.02):
    """Independent scalar cosine answer for prescribed zero field (Poisson removed)."""
    h = 1/cells
    s = np.linspace(0, 1, cells+1)
    w = np.full(cells+1, h)
    w[[0, -1]] /= 2
    lap = lil_matrix((cells+1, cells+1))
    for e in range(cells):
        for row, sign in ((e, 1), (e+1, -1)):
            lap[row, e] += sign/(h*w[row])
            lap[row, e+1] -= sign/(h*w[row])
    matrix = diags(np.ones(cells+1))+dt*lap.tocsc()
    count = round(end/dt)
    n = 1+.2*np.cos(np.pi*s)
    for _ in range(count):
        n = spsolve(matrix, n)
    eigenvalue = 4*np.sin(np.pi*h/2)**2/h**2
    exact_discrete = 1+.2*np.cos(np.pi*s)*(1+dt*eigenvalue)**(-count)
    exact_continuous = 1+.2*np.cos(np.pi*s)*np.exp(-np.pi**2*end)
    return {"same_grid_modal_error": float(np.max(np.abs(n-exact_discrete))),
            "continuous_error": float(np.max(np.abs(n-exact_continuous))),
            "amplitude_discrete": float(.2*(1+dt*eigenvalue)**(-count))}


def suite(card):
    base = Model(card)
    output, _, _ = base.run()
    meshes = []
    for N in [16, 32, 64, 128]:
        model = Model(card, N)
        ne, ue, c = model.equilibrium()
        meshes.append({"N": N, "u_error": float(np.max(abs(ue-model.ustar))),
                       "n_error": float(np.max(abs(ne-model.nstar))), "mass_error": float(abs(model.w@ne-model.mass))})
    time_results = []
    _, reference_n, reference_u = base.run(.0000625, .02)
    for dt in [.002, .001, .0005, .00025]:
        result, n, u = base.run(dt, .02)
        time_results.append({"dtau": dt, "n_error_reference": float(np.max(abs(n-reference_n))),
                             "u_error_reference": float(np.max(abs(u-reference_u))),
                             "mass_error": result["summary"]["mass_max_error"]})
    # Preserve exact discrete equilibrium in a time step and exercise failure exit.
    ne, ue, _ = base.equilibrium()
    nr, ur, _ = base.step(ne, ue, .05)
    old, old_u = base.initial()
    if np.linalg.norm(base.residual_jacobian(old, old_u, old, .1)[0], np.inf) <= 1e-10:
        old = 1+.1*np.cos(np.pi*base.s)
        old *= base.mass/(base.w@old)
        old_u = base.poisson(old)
    try:
        base.step(old, old_u, .1, max_newton=0)
    except NumericalFailure as e:
        expected_failure = str(e)
    else:
        raise NumericalFailure("zero-budget non-equilibrium step unexpectedly succeeded")
    # Fixed-field centered flux can reverse positivity once |delta|>2.
    delta = 4.0
    sg, _ = bernoulli(np.array([delta, -delta]))
    centered_matrix = np.array([[7., 2.], [-6., -1.]])
    centered_density = np.linalg.solve(centered_matrix, np.ones(2))
    b4, _ = bernoulli(np.array([4.]))
    bm4, _ = bernoulli(np.array([-4.]))
    sg_matrix = np.array([[1+2*bm4[0], -2*b4[0]], [-2*bm4[0], 1+2*b4[0]]])
    sg_density = np.linalg.solve(sg_matrix, np.ones(2))
    checks = {"equilibrium_step_n_error": float(max(abs(nr-ne))),
              "equilibrium_step_u_error": float(max(abs(ur-ue))),
              "zero_budget_expected_failure": expected_failure,
              "zero_field_linear": linear_check(),
              "centered_right_offdiagonal_at_delta4": -(1-delta/2),
              "two_node_centered_density_dt1_delta4": centered_density.tolist(),
              "two_node_SG_density_dt1_delta4": sg_density.tolist(),
              "SG_B_plus_minus4": sg.tolist()}
    # These check physical/analytic contracts, with explicit numerical failure.
    def require(condition, reason):
        if not condition:
            raise NumericalFailure(reason)
    require(output["summary"]["mass_max_error"] < 2e-9, "number conservation tolerance failed")
    require(output["summary"]["min_density"] > 0, "nonpositive density")
    require(output["summary"]["max_energy_increase"] < 2e-9, "free energy tolerance failed")
    require(output["summary"]["max_total_current_spread"] < 2e-7, "total current tolerance failed")
    require(checks["equilibrium_step_n_error"] < 2e-9, "discrete equilibrium was not preserved")
    require(checks["zero_field_linear"]["same_grid_modal_error"] < 2e-11, "linear modal answer mismatch")
    require(min(centered_density) < 0 < min(sg_density), "fixed-field sign diagnostic failed")
    if card["equilibrium_amplitude"] > 0:
        require(all(meshes[k+1]["u_error"] > 0 and meshes[k]["u_error"]/meshes[k+1]["u_error"] > 3.8
                    for k in range(3)), "manufactured mesh trend unresolved: refine/domain or roundoff diagnosis required")
    else:
        require(max(row["u_error"] for row in meshes) < 1e-10, "uniform equilibrium mismatch")
    require(all(time_results[k]["n_error_reference"]+1e-11 >= time_results[k+1]["n_error_reference"]
                for k in range(3)), "time refinement trend unresolved")
    return {"card": card, "scales": base.scale, "environment": {"python": sys.version,
            "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__},
            "run": output, "mesh_equilibrium": meshes, "time_convergence": time_results, "checks": checks}


def plots(result, out):
    os.environ.setdefault("MPLCONFIGDIR", str(out/".mpl-cache"))
    os.environ.setdefault("XDG_CACHE_HOME", str(out/".xdg-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"svg.fonttype": "none", "font.size": 10})
    s = np.array(result["run"]["s"])
    x = s*result["card"]["L_m"]*1e6
    run = result["run"]
    scale = result["scales"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), constrained_layout=True)
    for snap, style in zip(run["snapshots"], ["-", "--", "-.", ":"]):
        label = f't = {snap["tau"]*scale["time_s"]*1e12:.2f} ps'
        axes[0].plot(x, snap["n"], linestyle=style, label=label)
        axes[1].plot(x, np.array(snap["u"])*scale["VT_V"]*1e3, linestyle=style, label=label)
        axes[2].plot((x[:-1]+x[1:])/2, snap["F"], linestyle=style, label=label)
    axes[0].plot(x, run["equilibrium_n"], "k--", label="discrete equilibrium")
    for ax, ylabel in zip(axes, ["n / nref [1]", "potential [mV]", "electron particle F / Fref [1]"]):
        ax.set(xlabel="x [um]", ylabel=ylabel)
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    axes[2].text(.97, .03, "Outer F = 0; inner flux can vary", transform=axes[2].transAxes, ha="right", va="bottom", fontsize=8)
    fig.suptitle(f'Synthetic blocking-electron DD-Poisson; fixed donor, {result["card"]["T_K"]:g} K, N={run["summary"]["cells"]}')
    fig.savefig(out/"relaxation.svg", metadata={"Title": "Blocking electron relaxation", "Description": "Same input.json and results.json: positive density, selfconsistent potential, internal particle flux."})
    plt.close(fig)
    trajectory = run["trajectory"]
    times = np.array([a["tau"] for a in trajectory])*scale["time_s"]*1e12
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), constrained_layout=True)
    axes[0].plot(times, [a["mass"]-run["summary"]["mass_target"] for a in trajectory])
    axes[0].set(xlabel="t [ps]", ylabel="mass - target [1]")
    axes[1].plot(times, [a["energy"] for a in trajectory])
    axes[1].set(xlabel="t [ps]", ylabel="dimensionless free energy [1]")
    meshes = result["mesh_equilibrium"]
    axes[2].loglog([a["N"] for a in meshes], [a["u_error"] for a in meshes], "o-", label="potential / VT")
    axes[2].loglog([a["N"] for a in meshes], [a["n_error"] for a in meshes], "s--", label="density / nref")
    axes[2].set(xlabel="uniform cells N [1]", ylabel="max equilibrium error [1]")
    axes[2].set_xticks([row["N"] for row in meshes], labels=[str(row["N"]) for row in meshes])
    axes[2].xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.25)
    fig.suptitle("Three different checks: number conservation, energy decay, continuous equilibrium")
    fig.savefig(out/"evidence.svg", metadata={"Title": "Conservation energy and mesh evidence", "Description": "Number and energy from the same transient; mesh comparison against continuous manufactured equilibrium with fixed donor and fixed mass."})
    plt.close(fig)
    for name, title, description in [
        ("relaxation.svg", "Blocking electron relaxation", f'Synthetic {result["card"]["T_K"]:g} K model, N={run["summary"]["cells"]}. Same input and trajectory for density, potential and electron particle flux. Time curves use distinct line styles.'),
        ("evidence.svg", "Conservation energy and mesh evidence", "Three separate tests: number conservation, free energy decay and fixed continuous manufactured equilibrium mesh error.")]:
        import re
        svg = (out/name).read_text()
        svg = re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1)+f"\n<title>{title}</title>\n<desc>{description}</desc>", svg, count=1)
        (out/name).write_text(svg)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path(__file__).with_name("input.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--suite", action="store_true")
    p.add_argument("--plots", action="store_true")
    args = p.parse_args()
    try:
        card = validate(json.loads(args.input.read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s))))
        args.out.mkdir(parents=True, exist_ok=False)
        if args.suite:
            result = suite(card)
        else:
            model = Model(card)
            run, _, _ = model.run()
            result = {"card": card, "scales": model.scale, "run": run}
        (args.out/"results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
        if args.plots:
            if not args.suite:
                raise ValueError("--plots requires --suite")
            plots(result, args.out)
        print(json.dumps(result["run"]["summary"], indent=2))
    except (ValueError, OSError, NumericalFailure, ArithmeticError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
