"""CG MOS nodal/noise and explicit ideal commutating limit; SI, stdlib only."""
import argparse
import cmath
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

KB = 1.380649e-23


def load_source(path, name):
    saved = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


def number(v, name, low, high):
    if type(v) not in (float, int) or not math.isfinite(v) or not low <= v <= high:
        raise ValueError(name+" outside finite real budget (bool rejected)")
    return float(v)


def validate(c):
    if not isinstance(c, dict) or type(c.get("schema")) is not int or c["schema"] != 1:
        raise ValueError("schema 1 object required")
    number(c["reference_ohm"], "R0", 1, 1000)
    number(c["temperature_K"], "temperature", 100, 500)
    l, m = c["lna"], c["mixer"]
    if l["bias_policy"] != "hold_Id_rebias_gate":
        raise ValueError("this experiment rebiases each Rs at fixed Id")
    for k in ("vdd_V", "source_bias_V", "Vth_V"):
        number(l[k], k, 0, 5)
    for k in ("nominal_Rs_ohm", "Rd_ohm", "Rl_ohm"):
        number(l[k], k, 1, 1e6)
    number(l["nominal_Id_A"], "Id", 1e-6, .01)
    number(l["kp_A_per_V2"], "KP", 1e-5, 1)
    number(l["lambda_per_V"], "lambda", 0, .2)
    number(l["gamma_channel"], "gamma", .1, 3)
    number(l["eps_oxide_F_per_m"], "eps oxide", 1e-12, 1e-10)
    for k in ("W_m", "L_m", "tox_m"):
        number(l[k], k, 1e-9, 1e-3)
    for k in ("Cgs_external_F", "Cgd_external_F", "Cds_external_F", "Cout_F"):
        number(l[k], k, 1e-16, 1e-6)
    number(l["signal_available_power_W"], "Pav", 1e-12, 1e-3)
    for k, lo, hi in (("Rs_cases_ohm", 1, 1e4), ("frequencies_Hz", 1, 1e10)):
        if not isinstance(l[k], list) or not 1 <= len(l[k]) <= 16:
            raise ValueError("finite nonempty LNA arrays required")
        for v in l[k]:
            number(v, k, lo, hi)
        if len(set(l[k])) != len(l[k]):
            raise ValueError("duplicate LNA case")
    for k in ("source_diff_ohm", "load_diff_ohm", "output_bias_each_ohm"):
        number(m[k], k, 1, 1e9)
    for k in ("common_mode_V", "LO_high_V", "LO_low_V", "weak_LO_high_V", "Vth_V"):
        number(m[k], k, 0, 5)
    for k in ("kp_A_per_V2",):
        number(m[k], k, 1e-5, 1)
    for k in ("W_m", "L_m", "tox_m"):
        number(m[k], k, 1e-9, 1e-3)
    for k in ("LO_Hz", "IF_Hz", "blocker_Hz"):
        number(m[k], k, 1e3, 1e10)
    if m["IF_Hz"] >= m["LO_Hz"]:
        raise ValueError("positive wanted/image bands need IF<LO")
    number(m["LO_edge_s"], "LO edge", 1e-13, .1/m["LO_Hz"])
    for k in ("small_signal_peak_V", "blocker_peak_V"):
        number(m[k], k, 1e-6, 1)
    if not isinstance(m["blocker_peak_cases_V"], list) or not 1 <= len(m["blocker_peak_cases_V"]) <= 8:
        raise ValueError("finite large-signal cases required")
    for v in m["blocker_peak_cases_V"]:
        number(v, "large signal peak", 1e-6, 1)
    if not isinstance(m["odd_harmonics"], list) or not 1 <= len(m["odd_harmonics"]) <= 32:
        raise ValueError("finite odd harmonics required")
    if any(type(n) is not int or n <= 0 or n % 2 != 1 or n > 99 for n in m["odd_harmonics"]):
        raise ValueError("positive odd integer harmonic required")
    if m["odd_harmonics"] != sorted(set(m["odd_harmonics"])) or m["odd_harmonics"][0] != 1:
        raise ValueError("sorted unique harmonics starting at 1 required")
    if not m["LO_low_V"] < m["common_mode_V"]+m["Vth_V"] < m["LO_high_V"]:
        raise ValueError("nominal LO must straddle the zero-signal on/off threshold")
    return l, m


def solve2(a, b, c, d, x, y):
    det = a*d-b*c
    if abs(det) < 1e-28:
        raise ValueError("singular nodal matrix")
    return ((d*x-b*y)/det, (a*y-c*x)/det)


def matmul(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def adjoint(a):
    return [[a[j][i].conjugate() for j in range(2)] for i in range(2)]


def inv2(a):
    det = a[0][0]*a[1][1]-a[0][1]*a[1][0]
    return [[a[1][1]/det, -a[0][1]/det], [-a[1][0]/det, a[0][0]/det]]


def gate_for_id(l, rs):
    current = l["nominal_Id_A"]
    vd, vs = l["vdd_V"]-current*l["Rd_ohm"], l["source_bias_V"]+current*rs
    k = l["kp_A_per_V2"]*l["W_m"]/l["L_m"]
    ov = math.sqrt(2*current/(k*(1+l["lambda_per_V"]*(vd-vs))))
    if vd-vs <= ov or ov <= 0:
        raise ValueError("rebias target leaves saturation")
    return vs+l["Vth_V"]+ov


def point(l, rs, gate, amp):
    q = amp.mos_bias(vg=gate-l["source_bias_V"], vdd=l["vdd_V"]-l["source_bias_V"],
                     rd=l["Rd_ohm"], rs=rs, k=l["kp_A_per_V2"]*l["W_m"]/l["L_m"],
                     vt=l["Vth_V"], lam=l["lambda_per_V"])
    return {**q, "gate_V": gate, "drain_V": q["vd"]+l["source_bias_V"],
            "source_V": q["vs"]+l["source_bias_V"]}


def lna_case(l, rs, freq, q, c, old):
    gm, go = q["gm"], q["go"]
    r0, temp = c["reference_ohm"], c["temperature_K"]
    intrinsic = (2/3)*l["eps_oxide_F_per_m"]/l["tox_m"]*l["W_m"]*l["L_m"]
    cgs = l["Cgs_external_F"]+intrinsic
    cgd, cds, co = l["Cgd_external_F"], l["Cds_external_F"], l["Cout_F"]
    gs, gd, gl = 1/rs, 1/l["Rd_ohm"], 1/l["Rl_ohm"]
    s = 2j*math.pi*freq
    zl = l["Rl_ohm"]+1/(s*co)
    yl = 1/zl
    y = [[gm+go+s*(cgs+cds), -go-s*cds],
         [-gm-go-s*cds, gd+go+s*(cgd+cds)]]
    a, b, cc, d = y[0][0]+gs, y[0][1], y[1][0], y[1][1]+yl
    vs, vd = solve2(a, b, cc, d, gs, 0)
    read = l["Rl_ohm"]/zl
    ho = vd*read
    _, hch = solve2(a, b, cc, d, 1, -1)
    _, hrd = solve2(a, b, cc, d, 0, -1)
    hch, hrd = hch*read, hrd*read
    psds = {"source": 4*KB*temp*rs*abs(ho)**2,
            "channel": 4*KB*temp*l["gamma_channel"]*gm*abs(hch)**2,
            "Rd": 4*KB*temp*gd*abs(hrd)**2}
    fval = sum(psds.values())/psds["source"]
    zin = 1/(y[0][0]-y[0][1]*y[1][0]/(y[1][1]+yl))
    eye_plus = [[(1 if i == j else 0)+r0*y[i][j] for j in range(2)] for i in range(2)]
    eye_minus = [[(1 if i == j else 0)-r0*y[i][j] for j in range(2)] for i in range(2)]
    inv = inv2(eye_plus)
    smat = matmul(eye_minus, inv)
    # Current-noise PSD J/(kBT), n_ch=(-1,+1), n_Rd=(0,+1).
    jnorm = [[4*l["gamma_channel"]*gm, -4*l["gamma_channel"]*gm],
             [-4*l["gamma_channel"]*gm, 4*l["gamma_channel"]*gm+4*gd]]
    cnorm = [[r0*v for v in row] for row in matmul(matmul(inv, jnorm), adjoint(inv))]
    gs_ref, gl_ref = old.gamma(complex(rs), r0), old.gamma(zl, r0)
    port = old.closure(smat, gs_ref, gl_ref, l["signal_available_power_W"], r0)
    wave_f = old.noise_factor(smat, cnorm, gs_ref)
    direct_gt = 4*rs/l["Rl_ohm"]*abs(ho)**2
    if abs(port["G_T"]-direct_gt) > 1e-10 or abs(wave_f-fval) > 1e-10:
        raise ArithmeticError("node/wave glue inconsistent")
    # det three-node M(s)=p0+p1*s+p2*s²+p3*s³. Positive cubic Routh.
    a0, b0 = gs+gm+go, gd+go
    bzero = gs*(gd+go)+gd*(gm+go)
    bone = a0*cgd+b0*cgs+cds*(gs+gd)
    btwo = cgs*cgd+cgs*cds+cgd*cds
    poly = [bzero*gl, bzero*co+bone*gl+a0*co*gl,
            bone*co+btwo*gl+(cgs+cds)*co*gl, btwo*co]
    return {"Rs_ohm": rs, "frequency_Hz": freq, "Q": q, "Cgs_intrinsic_F": intrinsic,
            "Cgs_total_F": cgs, "Y_S": y, "S": smat, "noise_C_over_kBT": cnorm,
            "source_node_over_e": vs, "drain_over_e": vd, "output_over_e": ho,
            "channel_to_output_ohm": hch, "Rd_to_output_ohm": hrd,
            "Zin_ohm": zin, "G_T": direct_gt, "G_T_dB": 10*math.log10(direct_gt),
            "F": fval, "NF_dB": 10*math.log10(fval), "output_PSD_V2_per_Hz": psds,
            "port": port, "noise_parameters": old.noise_parameters(smat, cnorm, r0),
            "stability_frequency": old.stability(smat), "natural_polynomial_S3": poly,
            "routh_ratio": poly[1]*poly[2]/(poly[0]*poly[3])}


def mixer_limit(m, temp):
    k = m["kp_A_per_V2"]*m["W_m"]/m["L_m"]
    ron = 1/(k*(m["LO_high_V"]-m["common_mode_V"]-m["Vth_V"]))
    rb_diff = 2*m["output_bias_each_ohm"]
    rl = m["load_diff_ohm"]
    reff = 1/(1/rl+1/rb_diff)
    rs = m["source_diff_ohm"]
    series = rs+2*ron
    eta, q1 = reff/(reff+series), 2/math.pi
    hb = 1/(1/reff+1/series)
    switch_out = eta**2*4*KB*temp*(2*ron)
    bias_out = hb**2*4*KB*temp/rb_diff
    desired_out = eta**2*q1*q1*4*KB*temp*rs
    internal_ratio = (switch_out+bias_out)/desired_out
    cumulative, rows = 0, []
    for harmonic in m["odd_harmonics"]:
        coeff = 2*math.sin(harmonic*math.pi/2)/(math.pi*harmonic)
        cumulative += 2*coeff*coeff
        rows.append({"odd": harmonic, "coefficient_complex_series_real": coeff,
                     "source_white_fraction_summed": cumulative,
                     "specified_bands_SSB_F": cumulative/q1**2+internal_ratio})
    return {"on_R_ohm": ron, "effective_diff_load_ohm": reff,
            "alpha": eta, "q1": q1, "IF_voltage_over_e": eta*q1,
            "G_conversion_into_RL": 4*rs/rl*(eta*q1)**2,
            "G_conversion_all_diff_resistors": 4*rs/reff*(eta*q1)**2,
            "desired_source_output_PSD_V2_per_Hz": desired_out,
            "on_switch_output_PSD_V2_per_Hz": switch_out,
            "bias_resistor_output_PSD_V2_per_Hz": bias_out,
            "two_RF_bands_SSB_F": 2+internal_ratio,
            "all_white_RF_SSB_F": 1/q1**2+internal_ratio,
            "specified_odd_RF_bands": rows}


def pack(o):
    if isinstance(o, complex):
        return [o.real, o.imag]
    if isinstance(o, dict):
        return {k: pack(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [pack(v) for v in o]
    return o


def run(cfg, vault):
    l, m = validate(cfg)
    amp_path = vault/"电子电路/80-实践/14-偏置与基本放大/amp_lab.py"
    port_path = vault/"电子电路/80-实践/51-有源稳定与噪声匹配/active_match.py"
    amp, old = load_source(amp_path, "wwl_amp"), load_source(port_path, "wwl_port")
    rows = []
    dc = []
    for rs in l["Rs_cases_ohm"]:
        q = point(l, rs, gate_for_id(l, rs), amp)
        current = q["id"]
        dc.append({"Rs_ohm": rs, "Q": q, "VDD_supplied_W": l["vdd_V"]*current,
                   "source_bias_absorbed_W": l["source_bias_V"]*current,
                   "Rs_heat_W": current*current*rs, "Rd_heat_W": current*current*l["Rd_ohm"],
                   "MOS_heat_W": current*q["vds"]})
        rows.extend(lna_case(l, rs, f, q, cfg, old) for f in l["frequencies_Hz"])
    original_gate = gate_for_id(l, l["nominal_Rs_ohm"])
    fixed_gate = [point(l, rs, original_gate, amp) for rs in l["Rs_cases_ohm"]]
    return {"input": cfg, "sources": [{"path": str(p.relative_to(vault)),
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (amp_path, port_path)],
            "lna_dc": dc, "lna": rows, "fixed_gate_migration": fixed_gate,
            "mixer_ideal_limit": mixer_limit(m, cfg["temperature_K"])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--vault-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("output path already exists")
        cfg = json.loads(args.input.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
        data = pack(run(cfg, args.vault_root))
        encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
        args.out.mkdir(parents=True)
        (args.out/"analytical.json").write_text(encoded)
        print(json.dumps({"lna_cases": len(data["lna"]), "dc_cases": len(data["lna_dc"]),
                          "mixer_noise_models": "specified RF bands / full white; quasi-static limit"}))
    except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
