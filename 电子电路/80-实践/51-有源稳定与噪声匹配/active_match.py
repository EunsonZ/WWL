"""RMS real-reference two-port lab; no device data or random sampling."""
import argparse
import cmath
import csv
import json
import math
from pathlib import Path
import sys

KB = 1.380649e-23


def real(x, name):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError(name + " must be a finite number, not bool")
    return float(x)


def zpair(x):
    if not isinstance(x, list) or len(x) != 2:
        raise ValueError("complex value must be [real,imag]")
    return complex(real(x[0], "real"), real(x[1], "imag"))


def matrix(x):
    if not isinstance(x, list) or len(x) != 2 or any(
            not isinstance(r, list) or len(r) != 2 for r in x):
        raise ValueError("matrix must be 2 by 2")
    return [[zpair(v) for v in r] for r in x]


def determinant(m):
    return m[0][0]*m[1][1] - m[0][1]*m[1][0]


def gin(m, gl):
    a, b = m[0]
    c, d = m[1]
    den = 1-d*gl
    if abs(den) < 1e-12:
        raise ValueError("input reflection has a pole")
    return a+b*c*gl/den


def gout(m, gs):
    return gin([[m[1][1], m[1][0]], [m[0][1], m[0][0]]], gs)


def stability(m):
    a, b = m[0]
    c, d = m[1]
    delta, p = determinant(m), b*c
    if abs(a) >= 1 or abs(d) >= 1 or abs(p) < 1e-8:
        raise ValueError("lab needs |S11|,|S22|<1 and nonzero reverse loop")
    ci = (a-delta*d.conjugate())/(1-abs(d)**2)
    co = (d-delta*a.conjugate())/(1-abs(a)**2)
    ri, ro = abs(p)/(1-abs(d)**2), abs(p)/(1-abs(a)**2)
    circles = []
    for t, other in ((d, a), (a, d)):
        v = abs(t)**2-abs(delta)**2
        circles.append(None if abs(v) < 1e-12 else {
            "center": (t-delta*other.conjugate()).conjugate()/v,
            "radius": abs(p)/abs(v)})
    return {"delta": delta,
            "K": (1-abs(a)**2-abs(d)**2+abs(delta)**2)/(2*abs(p)),
            "input_image_center": ci, "input_image_radius": ri,
            "output_image_center": co, "output_image_radius": ro,
            "max_abs_gin": abs(ci)+ri, "max_abs_gout": abs(co)+ro,
            "load_stability_circle": circles[0],
            "source_stability_circle": circles[1]}


def noise_parameters(m, n, r0):
    a, c = m[0][0], m[1][0]
    const = n[1][1].real/abs(c)**2
    cross = n[0][1]/c.conjugate()-const*a
    quad = n[0][0].real + const*abs(a)**2 - 2*(n[0][1]*a.conjugate()/c.conjugate()).real
    disc = (quad+const)**2-4*abs(cross)**2
    if disc <= 0:
        raise ValueError("degenerate noise model outside lab")
    kappa = (quad+const+math.sqrt(disc))/2
    opt = -cross.conjugate()/kappa
    return {"quadratic": quad, "cross": cross, "constant": const,
            "kappa": kappa, "gamma_opt": opt, "F_min": 1+kappa-quad,
            "R_n_ohm": r0*kappa*abs(1+opt)**2/4}


def noise_factor(m, n, gs):
    if abs(gs) >= 1:
        raise ValueError("noise factor requires a dissipative source")
    t = (1-m[0][0]*gs)/m[1][0]
    added = (abs(gs)**2*n[0][0].real + abs(t)**2*n[1][1].real
             + 2*(gs*n[0][1]*t.conjugate()).real)
    return 1+added/(1-abs(gs)**2)


def impedance(gamma, r0):
    if abs(1-gamma) < 1e-12:
        raise ValueError("open impedance; use gamma coordinate")
    return r0*(1+gamma)/(1-gamma)


def gamma(z, r0):
    if abs(z+r0) < 1e-12:
        raise ValueError("impedance mapping pole")
    return (z-r0)/(z+r0)


def closure(m, gs, gl, pav, r0):
    if abs(gs) >= 1 or abs(gl) >= 1:
        raise ValueError("power readout uses strictly dissipative terminations")
    a, b = m[0]
    c, d = m[1]
    den = (1-a*gs)*(1-d*gl)-b*c*gs*gl
    if abs(den) < 1e-12:
        raise ValueError("closed two-port determinant is singular")
    ag = math.sqrt(pav*(1-abs(gs)**2))
    a1 = (1-d*gl)*ag/den
    b2 = c*ag/den
    a2 = gl*b2
    b1 = a*a1+b*a2
    vs = ag*(impedance(gs, r0)+r0)/math.sqrt(r0)
    v1, v2 = math.sqrt(r0)*(a1+b1), math.sqrt(r0)*(a2+b2)
    i1, i2 = (a1-b1)/math.sqrt(r0), (a2-b2)/math.sqrt(r0)
    pl = abs(b2)**2-abs(a2)**2
    return {"gamma_S": gs, "gamma_L": gl, "Z_S_ohm": impedance(gs, r0),
            "Z_L_ohm": impedance(gl, r0), "D": den, "a_g_sqrtW": ag,
            "a1_sqrtW": a1, "b1_sqrtW": b1, "a2_sqrtW": a2, "b2_sqrtW": b2,
            "V_s_V": vs, "V1_V": v1, "V2_V": v2, "I1_A": i1, "I2_A": i2,
            "P1_into_DUT_W": abs(a1)**2-abs(b1)**2, "P_L_W": pl,
            "G_T": pl/pav, "G_T_dB": 10*math.log10(pl/pav),
            "V2_over_V1": v2/v1, "gamma_in": gin(m, gl), "gamma_out": gout(m, gs),
            "source_return_margin": 1-abs(gs*gin(m, gl)),
            "load_return_margin": 1-abs(gl*gout(m, gs))}


def conjugate_match(m):
    a, b = m[0]
    c, d = m[1]
    delta = determinant(m)
    result = []
    for t, other in ((a, d), (d, a)):
        bval = 1+abs(t)**2-abs(other)**2-abs(delta)**2
        cval = t-delta*other.conjugate()
        if abs(cval) < 1e-12:
            result.append(0j)
        else:
            disc = bval*bval-4*abs(cval)**2
            if disc < 0:
                raise ValueError("no simultaneous passive match")
            roots = [(bval+s*math.sqrt(disc))/(2*cval) for s in (-1, 1)]
            candidates = [g for g in roots if abs(g) < 1]
            if len(candidates) != 1:
                raise ValueError("match root is not unique")
            result.append(candidates[0])
    return result


def l_section(g, r0, omega):
    z = impedance(g, r0)
    y = 1/z
    rad = r0/y.real-r0*r0
    if rad < -1e-8:
        raise ValueError("target outside chosen shunt-at-DUT L-section branch")
    xs = math.sqrt(max(0, rad))
    bs = y.imag+xs/(r0*r0+xs*xs)
    # Signed susceptance is represented by a C or L; negative is not a negative capacitor.
    return {"target_Z_ohm": z, "series_L_H": xs/omega,
            "shunt_C_F": max(bs, 0)/omega,
            "shunt_L_H": -1/(omega*bs) if bs < 0 else None,
            "X_series_ohm": xs, "B_shunt_S": bs}


def l_impedance(net, r0, omega):
    bs = omega*net["shunt_C_F"]
    if net["shunt_L_H"] is not None:
        bs -= 1/(omega*net["shunt_L_H"])
    return 1/(1/(r0+1j*omega*net["series_L_H"])+1j*bs)


def bandpass(ratio, q):
    z = 1j*ratio
    return (z/q)/(z*z+z/q+1)


def validate(cfg):
    if not isinstance(cfg, dict):
        raise ValueError("input must be a JSON object")
    if cfg.get("schema") != 1 or type(cfg.get("schema")) is not int:
        raise ValueError("schema must be integer 1")
    for name, lo, hi in (("reference_ohm", 1, 1000), ("frequency_Hz", 1e6, 1e11),
                         ("Q", .2, 20), ("temperature_K", 1, 1000),
                         ("available_power_W", 1e-12, .001)):
        value = real(cfg.get(name), name)
        if not lo <= value <= hi:
            raise ValueError(name+" out of finite lab budget")
    m, sc, n = (matrix(cfg.get(k)) for k in ("S", "conditional_S", "noise_C_over_kBT"))
    for mat in (m, sc, n):
        if any(abs(v) > 10 for row in mat for v in row):
            raise ValueError("matrix magnitude budget exceeded")
    st = stability(m)
    if max(st["max_abs_gin"], st["max_abs_gout"]) >= .999:
        raise ValueError("main S must have a strict passive disk margin")
    stability(sc)
    if abs(n[0][0].imag)+abs(n[1][1].imag)+abs(n[0][1]-n[1][0].conjugate()) > 1e-12:
        raise ValueError("noise covariance must be Hermitian")
    if n[0][0].real <= 1e-6 or determinant(n).real <= 1e-6:
        raise ValueError("noise covariance must be strictly positive definite")
    probes = cfg.get("probe_gammas")
    if not isinstance(probes, list) or not 1 <= len(probes) <= 8:
        raise ValueError("one to eight probe gammas needed")
    for item in probes:
        if abs(zpair(item)) > .95:
            raise ValueError("probe outside passive budget")
    ratios = cfg.get("frequency_ratios")
    if not isinstance(ratios, list) or not 1 <= len(ratios) <= 16:
        raise ValueError("one to sixteen frequency ratios needed")
    if any(not .1 <= real(r, "frequency ratio") <= 10 for r in ratios):
        raise ValueError("frequency ratio budget exceeded")
    levels = cfg.get("noise_factor_contours")
    if not isinstance(levels, list) or not 1 <= len(levels) <= 8:
        raise ValueError("one to eight contour levels needed")
    pars = noise_parameters(m, n, cfg["reference_ohm"])
    if any(real(f, "contour") < pars["F_min"] for f in levels):
        raise ValueError("contour below minimum noise factor")
    if not 0 < real(cfg.get("conditional_gamma"), "conditional_gamma") < .99:
        raise ValueError("counter termination must be dissipative")
    if zpair(cfg.get("legacy_load_ohm")).real <= 0:
        raise ValueError("legacy load must be dissipative")
    # Validate all synthesis targets before creating any output directory.
    gs, gl = conjugate_match(m)
    for g in (gs, gl, pars["gamma_opt"], gout(m, pars["gamma_opt"]).conjugate()):
        l_section(g, cfg["reference_ohm"], 2*math.pi*cfg["frequency_Hz"])
    return m, sc, n


def run(cfg):
    m, sc, n = validate(cfg)
    r0, pav, omega = cfg["reference_ohm"], cfg["available_power_W"], 2*math.pi*cfg["frequency_Hz"]
    pars = noise_parameters(m, n, r0)
    main_st = stability(m)
    gs_max, gl_max = conjugate_match(m)
    opt = pars["gamma_opt"]
    designs = []
    for label, gs, gl in (("reference_match", 0j, 0j),
                           ("maximum_gain", gs_max, gl_max),
                           ("minimum_noise_output_matched", opt, gout(m, opt).conjugate())):
        row = closure(m, gs, gl, pav, r0)
        fval = noise_factor(m, n, gs)
        row.update(label=label, F=fval, NF_dB=10*math.log10(fval),
                   source_L_section=l_section(gs, r0, omega),
                   load_L_section=l_section(gl, r0, omega))
        sn = KB*cfg["temperature_K"]*row["G_T"]
        row["source_output_noise_W_per_Hz"] = sn
        row["added_output_noise_W_per_Hz"] = sn*(fval-1)
        row["total_output_noise_W_per_Hz"] = sn*fval
        designs.append(row)
    probes = []
    for gs in map(zpair, cfg["probe_gammas"]):
        for gl in map(zpair, cfg["probe_gammas"]):
            row = closure(m, gs, gl, pav, r0)
            row["F"] = noise_factor(m, n, gs)
            probes.append(row)
    legacy_gl = gamma(zpair(cfg["legacy_load_ohm"]), r0)
    legacy = closure(m, 0j, legacy_gl, pav, r0)
    unilateral = [[m[0][0], 0j], m[1][:]]
    legacy["wrong_unilateral_gamma_in"] = gin(unilateral, legacy_gl)
    legacy["wrong_unilateral_V2_over_V1"] = closure(unilateral, 0j, legacy_gl, pav, r0)["V2_over_V1"]
    frequencies = []
    for design in designs:
        for ratio in cfg["frequency_ratios"]:
            hh = bandpass(ratio, cfg["Q"])
            ss = [[hh*v for v in row] for row in m]
            gs = gamma(l_impedance(design["source_L_section"], r0, omega*ratio), r0)
            gl = gamma(l_impedance(design["load_L_section"], r0, omega*ratio), r0)
            frequencies.append({"label": design["label"], "frequency_Hz": ratio*cfg["frequency_Hz"],
                                "H": hh, **closure(ss, gs, gl, pav, r0)})
    contours = []
    for fval in cfg["noise_factor_contours"]:
        u = (fval-pars["F_min"])/pars["kappa"]
        contours.append({"F": fval, "center": opt/(1+u),
                         "radius": math.sqrt(u*u+u*(1-abs(opt)**2))/(1+u)})
    g = cfg["conditional_gamma"]
    eigdisc = cmath.sqrt((sc[0][0]-sc[1][1])**2+4*sc[0][1]*sc[1][0])
    lambdas = [g*(sc[0][0]+sc[1][1]+s*eigdisc)/2 for s in (1, -1)]
    poles = []
    for lam in lambdas:
        damp = (1-lam)/cfg["Q"]
        disc = cmath.sqrt(damp*damp-4)
        poles.extend([omega*(-damp+s*disc)/2 for s in (1, -1)])
    formal = closure(sc, g, g, pav, r0)
    formal["is_usable_steady_state"] = all(p.real < 0 for p in poles)
    # S0 absolute weighted max norm v=(1,4); a sufficient all-frequency bound.
    v = (1, 4)
    bound = max(sum(abs(m[i][j])*v[j]/v[i] for j in range(2)) for i in range(2))
    l11 = math.sqrt(n[0][0].real)
    l21 = n[1][0]/l11
    l22 = math.sqrt(n[1][1].real-abs(l21)**2)
    return {"input": cfg, "stability": main_st, "noise_parameters": pars,
            "noise_cholesky": [[l11, 0], [l21, l22]],
            "weighted_small_gain_bound": bound,
            "declared_extension_certified_by_bound": bound < 1,
            "designs": designs, "legacy": legacy, "termination_probes": probes,
            "frequency_probes": frequencies, "noise_contours": contours,
            "conditional": {"stability": stability(sc), "loop_eigenvalues": lambdas,
                            "poles_rad_per_s": poles, "formal_frequency_solution": formal}}


def pack(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    if isinstance(obj, dict):
        return {k: pack(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [pack(v) for v in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("output directory already exists")
        cfg = json.loads(args.input.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
        data = pack(run(cfg))
        encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
        args.out.mkdir(parents=True)
        (args.out/"results.json").write_text(encoded)
        with (args.out/"designs.csv").open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["label", "GT", "GT_dB", "F", "NF_dB", "PL_W", "input_return_margin", "output_return_margin"])
            for row in data["designs"]:
                writer.writerow([row[k] for k in ("label", "G_T", "G_T_dB", "F", "NF_dB", "P_L_W", "source_return_margin", "load_return_margin")])
        print(json.dumps({"designs": len(data["designs"]), "termination_pairs": len(data["termination_probes"]),
                          "frequencies": len(data["frequency_probes"]),
                          "weighted_bound": data["weighted_small_gain_bound"],
                          "counter_usable": data["conditional"]["formal_frequency_solution"]["is_usable_steady_state"]}))
    except (ValueError, TypeError, KeyError, ZeroDivisionError, OverflowError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
