"""Finite simulated readouts for the installed C++ API; no model writes/hardware.

Run with --vault pointing to the published vault and --output outside that root.
Payload protocol is deliberately fixed: three named rows, six codes each.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path


def load_model(path: Path):
    spec = importlib.util.spec_from_file_location("wwl_readout_" + path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load model")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encode_mv(value):
    # Nearest, ties-to-even; reject overload instead of silently clipping.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("readout must be a real voltage in mV")
    if not math.isfinite(value) or not 0 <= value <= 4095:
        raise ValueError("readout outside [0,4095] mV")
    code = round(value)
    if abs(code - value) > 0.500000000001:
        raise RuntimeError("nearest-code bound failed")
    return code


def summarize(codes):
    n = len(codes)
    mean = Fraction(sum(codes), n)
    variance = sum((Fraction(x) - mean)**2 for x in codes) / n
    return {"n": n, "sum_mv": sum(codes), "mean_mv": str(mean),
            "variance_mv2": str(variance),
            "rms2_mv2": str(sum(Fraction(x*x) for x in codes)/n)}


def observations(vault: Path):
    thermal = load_model(vault / "控制论/80-实践/01-热调节/thermal_control_lab.py")
    quantum = load_model(vault / "物理/40-量子力学/实践/qm_first_segment.py")
    diode = load_model(vault / "电子电路/80-实践/12-半导体与真实元件/semiconductor_lab.py")
    thermal_rows = thermal.trajectory(1., 5)
    quantum_times = [k*2e-7 for k in range(6)]
    quantum_values = [quantum.probability(quantum.evolved(quantum.RC,t),quantum.PX)
                      for t in quantum_times]
    expected = [(1+math.cos(quantum.OMEGA*t))/2 for t in quantum_times]
    if any(abs(a-b)>1e-12 for a,b in zip(quantum_values,expected)):
        raise RuntimeError("Born projection disagrees with specified analytic solution")
    sources = list(range(1,7))
    diode_rows = [diode.diode_load(v,1000.,max_iterations=200,voltage_tol=1e-12)
                  for v in sources]
    # Check the published circuit equation, separate from millivolt coding.
    for source,row in zip(sources,diode_rows):
        if abs(source-row["v"]-1000*row["i"])>1e-12:
            raise RuntimeError("diode KVL failed")
        if abs(diode.diode_current(row["v"])-row["i"])>1e-11:
            raise RuntimeError("diode current residual failed")
    records = [
        dict(name="thermal", coordinate_unit="s", coordinate=[r["t_s"] for r in thermal_rows],
             observable_unit="K", observable=[r["y_K"] for r in thermal_rows],
             mv_per_observable=1000., interval_s=1.,
             model="C=10 J/K,h=1 W/K,kp=3 W/K,r=2 K; ZOH, old sampled state; n=d=0"),
        dict(name="quantum", coordinate_unit="s", coordinate=quantum_times,
             observable_unit="probability", observable=quantum_values,
             mv_per_observable=1000., interval_s=2e-7,
             model="H=hbar*Omega*sigma_z/2,Omega=2*pi*1e6 rad/s,rho0=Px+; exact U,rho 2x2"),
        dict(name="diode", coordinate_unit="source_V", coordinate=sources,
             observable_unit="V", observable=[r["v"] for r in diode_rows],
             mv_per_observable=1000., interval_s=0.,
             model="Vs=VD+R*Is*expm1(VD/VT);R=1000 ohm,Is=1e-12 A,eta=1,T=300 K; static sweep"),
    ]
    for record in records:
        record["readout_mv"] = [x*record["mv_per_observable"] for x in record["observable"]]
        record["codes"] = [encode_mv(x) for x in record["readout_mv"]]
        record["code_shape"] = [6]
        record["max_abs_readout_error_mv"] = max(abs(q-x) for q,x in
                                                 zip(record["codes"],record["readout_mv"]))
        record["code_statistics"] = summarize(record["codes"])
    return records


def payload(records):
    return "".join(f'{r["name"]} {r["interval_s"]:.17g} 6 ' +
                   " ".join(str(c) for c in r["codes"]) + "\n" for r in records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    vault=args.vault.resolve(); output=args.output.resolve()
    candidate=Path(__file__).resolve().parents[5]
    if output.is_relative_to(vault) or output.is_relative_to(candidate):
        parser.error("--output must be outside the vault and this source tree")
    records=observations(vault)
    output.mkdir(parents=True,exist_ok=True)
    (output/"physics-readouts.txt").write_text(payload(records),encoding="utf-8")
    (output/"physics-readouts.json").write_text(json.dumps(records,indent=2)+"\n",encoding="utf-8")
    print("physics_readouts=PASS three_models,explicit_voltage_map,no_clip,six_observations")


if __name__ == "__main__":
    main()
