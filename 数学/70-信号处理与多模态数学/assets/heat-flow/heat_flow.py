#!/usr/bin/env python3
"""Finite Gaussian heat-flow calculation; no trained model or convergence claim.

Run with Python 3 + matplotlib. Each output directory receives the exact input,
quadrature/finite-difference checks, Monte Carlo uncertainties and plot data.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import xml.etree.ElementTree as ET


def density(x, variance):
    return math.exp(-x * x / (2 * variance)) / math.sqrt(2 * math.pi * variance)


def trapezoid(values, dx):
    return dx * (math.fsum(values) - (values[0] + values[-1]) / 2)


def mean_se(values):
    return {"estimate": statistics.fmean(values),
            "standard_error": statistics.stdev(values) / math.sqrt(len(values))}


def write_csv(path, names, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(names)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("input.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.input.read_text(encoding="utf-8"))
    v0, kappa, s, end = (cfg[key] for key in ("v0", "kappa", "s", "t"))
    if not all(math.isfinite(x) for x in (v0, kappa, s, end)) or not (v0 > 0 and kappa > 0 and 0 <= s < end):
        parser.error("require finite v0 > 0, kappa > 0 and 0 <= s < t; singular v0=0 is treated analytically")
    for key, lo, hi in (("samples", 2, 200000), ("plot_steps", 2, 2000),
                        ("plot_paths", 1, 8), ("quadrature_intervals", 10, 20000)):
        if not isinstance(cfg[key], int) or not lo <= cfg[key] <= hi:
            parser.error(f"{key} must be an integer in [{lo}, {hi}]")
    if not math.isfinite(cfg["quadrature_sd"]) or not 4 <= cfg["quadrature_sd"] <= 12:
        parser.error("quadrature_sd must lie in [4, 12]")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "input.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    variance = lambda time: v0 + 2 * kappa * time
    vs, vt = variance(s), variance(end)
    times = [0.0, end / 2, end]
    # Broad finite interval, fixed spacing; tail and quadrature are numerical approximations.
    radius = cfg["quadrature_sd"] * math.sqrt(vt)
    intervals = cfg["quadrature_intervals"]
    dx = 2 * radius / intervals
    xs = [-radius + j * dx for j in range(intervals + 1)]
    integrals = []
    columns = []
    for time in times:
        v = variance(time)
        p = [density(x, v) for x in xs]
        columns.append(p)
        entropy = [-px * (-0.5 * math.log(2 * math.pi * v) - x*x/(2*v)) for x, px in zip(xs, p)]
        fisher = [px * x*x/(v*v) for x, px in zip(xs, p)]
        integrals.append({"time": time, "mass": trapezoid(p, dx),
                          "h_quadrature": trapezoid(entropy, dx),
                          "J_quadrature": trapezoid(fisher, dx),
                          "h_formula": 0.5 * math.log(2 * math.pi * math.e * v),
                          "J_formula": 1 / v})
    write_csv(out / "density.csv", ["x"] + [f"p_t={time}" for time in times],
              zip(xs, *columns))
    # Central differences computed from density values, not analytic derivatives.
    tm = end / 2
    dt = min(end * 1e-4, variance(tm) / kappa * 1e-4)
    hx = math.sqrt(variance(tm)) * 1e-3
    residuals = []
    for x in [-2 * math.sqrt(variance(tm)), 0, math.sqrt(variance(tm))]:
        dtime = (density(x, variance(tm+dt)) - density(x, variance(tm-dt))) / (2*dt)
        dxx = (density(x+hx, variance(tm)) - 2*density(x, variance(tm)) + density(x-hx, variance(tm))) / hx**2
        residuals.append({"x": x, "time_derivative_fd": dtime,
                          "kappa_laplacian_fd": kappa*dxx,
                          "absolute_residual": abs(dtime-kappa*dxx)})
    def h_quad(time):
        v = variance(time)
        return trapezoid([density(x,v) * (0.5*math.log(2*math.pi*v)+x*x/(2*v)) for x in xs], dx)
    h_derivative = (h_quad(tm+dt)-h_quad(tm-dt))/(2*dt)
    # Exact grid transition: X_t = X_s + independent N(0,2*kappa*(t-s)).
    rng = random.Random(cfg["seed"])
    sde_products, ode_products, sde_s2, sde_t2, ode_t2 = [], [], [], [], []
    for _ in range(cfg["samples"]):
        x0 = rng.gauss(0, math.sqrt(v0))
        x_s = x0 + rng.gauss(0, math.sqrt(2*kappa*s))
        x_t = x_s + rng.gauss(0, math.sqrt(2*kappa*(end-s)))
        z_s, z_t = x0*math.sqrt(vs/v0), x0*math.sqrt(vt/v0)
        sde_products.append(x_s*x_t)
        ode_products.append(z_s*z_t)
        sde_s2.append(x_s*x_s)
        sde_t2.append(x_t*x_t)
        ode_t2.append(z_t*z_t)
    cov_sde, cov_ode = mean_se(sde_products), mean_se(ode_products)
    cov_sde["formula"] = vs
    cov_ode["formula"] = math.sqrt(vs*vt)
    # Independent RNG stream prevents sample-count changes from silently changing the figure.
    rng_paths = random.Random(cfg["seed"] + 1)
    plot_times = [end*i/cfg["plot_steps"] for i in range(cfg["plot_steps"]+1)]
    step = end/cfg["plot_steps"]
    rows, plot_data = [], []
    for path_id in range(cfg["plot_paths"]):
        initial = rng_paths.gauss(0, math.sqrt(v0))
        x = initial
        sde, ode = [], []
        for i, time in enumerate(plot_times):
            if i:
                x += rng_paths.gauss(0, math.sqrt(2*kappa*step))
            z = initial*math.sqrt(variance(time)/v0)
            rows.append((path_id,time,initial,x,z))
            sde.append(x)
            ode.append(z)
        plot_data.append((sde,ode))
    write_csv(out / "paths.csv", ["path_id","t","x0","sde_grid","ode_exact"], rows)
    metrics = {"input": cfg, "python": sys.version.split()[0],
               "model": "X=X0+sqrt(2*kappa)*W; Z=X0*sqrt(v_t/v0); v_t=v0+2*kappa*t",
               "units": {"variance":"U^2", "covariance":"U^2", "h_difference":"nat", "J":"U^-2"},
               "quadrature": {"radius":radius,"dx":dx,"rows":integrals},
               "PDE_finite_differences": {"time":tm,"dt":dt,"dx":hx,"rows":residuals},
               "de_Bruijn": {"h_derivative_fd_of_quadrature":h_derivative,
                              "kappa_J_quadrature":kappa*integrals[1]["J_quadrature"]},
               "covariance_known_zero_means": {"SDE":cov_sde,"ODE":cov_ode},
               "second_moments": {"SDE_s":mean_se(sde_s2), "SDE_t":mean_se(sde_t2), "ODE_t":mean_se(ode_t2)},
               "entropy_increment_s_to_t":0.5*math.log(vt/vs),
               "boundary": "v0=0 deliberately rejected: no unique deterministic flow from the point initial condition"}
    # Figure has no model-training or continuum-path verification meaning.
    os.environ.setdefault("MPLCONFIGDIR", str(out / ".mpl-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.9), layout="constrained")
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]
    styles = ["-", "--", ":"]
    for j, time in enumerate(times):
        axes[0].plot(xs, columns[j], color=colors[j], linestyle=styles[j], lw=2.4,
                     label=f"t={time:g}, variance={variance(time):g}")
    axes[0].set(xlim=(-3.5*math.sqrt(vt),3.5*math.sqrt(vt)), ylim=(0,None),
                xlabel=f"State x [{cfg['state_unit']}]", ylabel=f"Density p [1/{cfg['state_unit']}]",
                title="Same marginal density for SDE and ODE")
    axes[0].legend(fontsize=9)
    for j,(sde,ode) in enumerate(plot_data):
        color = colors[j%len(colors)]
        axes[1].plot(plot_times,sde,color=color,lw=1,alpha=.7)
        axes[1].plot(plot_times,ode,color=color,lw=2.3,ls="--")
    axes[1].plot([],[],color="#333333",lw=1,label="SDE: exact samples on finite grid")
    axes[1].plot([],[],color="#333333",lw=2.3,ls="--",label="ODE: exact deterministic flow")
    # Arrow follows a positive exact ODE path from the displayed draws.
    positive = max(path[1][0] for path in plot_data)
    if positive > 0:
        a,b = end*.4,end*.7
        za,zb = positive*math.sqrt(variance(a)/v0),positive*math.sqrt(variance(b)/v0)
        axes[1].annotate("", xy=(b,zb), xytext=(a,za),
                         arrowprops={"arrowstyle":"->","color":"black","lw":1.8})
        axes[1].text(a,za+0.22*math.sqrt(v0), "ODE outward at x > 0", fontsize=9)
    axes[1].set(xlabel=f"Forward time t [{cfg['time_unit']}] (increasing)", ylabel=f"State [{cfg['state_unit']}]",
                title="Same initial draws; different path relations")
    axes[1].legend(loc="lower left",fontsize=9)
    for ax in axes:
        ax.grid(alpha=.18)
    fig.suptitle(f"Gaussian heat flow | v0={v0:g}, kappa={kappa:g} | coordinate units U=Tu=1", fontsize=13)
    fig.savefig(out/"heat-flow.svg")
    fig.savefig(out/"heat-flow.png",dpi=150)
    plt.close(fig)
    path = out/"heat-flow.svg"
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(path)
    ns="{http://www.w3.org/2000/svg}"
    title=ET.Element(ns+"title");title.text="Gaussian heat-flow density and SDE versus ODE paths"
    desc=ET.Element(ns+"desc");desc.text=("Left: exact normalized Gaussian densities widen as variance v0+2*kappa*t grows. "
        "Right: four common Gaussian initial draws; solid lines connect exact finite-grid Brownian samples; "
        "dashed curves are deterministic ODE paths. A forward ODE arrow at positive state points outward. "
        "Horizontal time and state axes use declared coordinate units; this is a finite model calculation, not a trained generator.")
    tree.getroot().insert(0,desc);tree.getroot().insert(0,title)
    tree.write(path,encoding="utf-8",xml_declaration=True)
    metrics["matplotlib"] = matplotlib.__version__
    (out/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output_dir":str(out),"SDE_cov":cov_sde,"ODE_cov":cov_ode,
                     "de_Bruijn":metrics["de_Bruijn"],
                     "max_PDE_residual":max(r["absolute_residual"] for r in residuals)}))


if __name__ == "__main__":
    main()
