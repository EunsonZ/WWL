#!/usr/bin/env python3
"""Two-phase ideal charge ledger. SI units; exact Fraction voltage/charge, stdlib."""
import argparse
import csv
from fractions import Fraction as F
import json
from pathlib import Path
from xml.sax.saxutils import escape

# A and B are physical Cs plates, s is the OTA summing node, o its output.
ENDPOINTS = {"S1": ["x", "A"], "S2": ["A", "s"],
             "Cs": ["A", "0"], "Cf": ["s", "o"], "OTA+": ["0"]}
PHASES = [("phi1", True, False), ("dead", False, False),
          ("phi2", False, True), ("dead", False, False)]


def rational(value, name, positive=False):
    if not isinstance(value, str):
        raise ValueError(f"{name}: expected an exact rational string")
    try:
        number = F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name}: invalid rational") from exc
    if positive and number <= 0:
        raise ValueError(f"{name}: must be positive")
    return number


def load_input(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    names = {"Cs_F", "Cf_F", "Cp_F", "fs_Hz", "y0_V", "x_V"}
    if not isinstance(data, dict) or set(data) != names:
        raise ValueError("input requires exactly Cs_F, Cf_F, Cp_F, fs_Hz, y0_V, x_V")
    vals = {key: rational(data[key], key, key in {"Cs_F", "Cf_F", "fs_Hz"})
            for key in names - {"x_V"}}
    if vals["Cp_F"] < 0:
        raise ValueError("Cp_F: must be nonnegative")
    if not isinstance(data["x_V"], list) or not 1 <= len(data["x_V"]) <= 100:
        raise ValueError("x_V: expected a nonempty list, length at most 100")
    vals["x_V"] = [rational(x, "x_V") for x in data["x_V"]]
    return vals


def ledger(cs, cf, x, y0, cp=F(0)):
    """Union s+Cf(s plate)+A is isolated from conductive sources in phi2."""
    cap = cs + cp
    state = y0
    zero_state = F(0)
    rows = []
    for n, vin in enumerate(x):
        before = state
        qf_before = -cf * before
        qs_sample = cs * vin
        qp_sample = cp * vin
        q_union = qf_before + qs_sample + qp_sample
        # At the settled end of phi2 A=s=0, so Cs and Cp A-plate charge is zero.
        qf_after = q_union
        state = -qf_after / cf
        zero_state -= cap * vin / cf
        rows.append({"n": n, "x_V": str(vin), "y_before_V": str(before),
                     "qf_before_C": str(qf_before), "qs_sample_C": str(qs_sample),
                     "qp_sample_C": str(qp_sample), "q_union_C": str(q_union),
                     "qs_after_C": "0", "qp_after_C": "0",
                     "qf_after_C": str(qf_after), "w_after_V": str(state),
                     "zero_input_V": str(y0), "zero_state_after_V": str(zero_state),
                     "sum_after_V": str(y0 + zero_state)})
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def svg_open(title, desc, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
            '<rect width="100%" height="100%" fill="#fafbfc"/>',
            '<g font-family="Arial,sans-serif" font-size="18" fill="#152b3c" stroke-linecap="round">']


def text(out, x, y, value, size=18, color="#152b3c"):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>')


def line(out, x1, y1, x2, y2, color="#29485d", width=3):
    out.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}"/>')


def switch(out, x1, y, closed, label):
    line(out, x1-32, y, x1, y)
    line(out, x1+55, y, x1+87, y)
    line(out, x1, y, x1+55, y if closed else y-25,
         "#007a68" if closed else "#b34b27")
    for xx in [x1, x1+55]:
        out.append(f'<circle cx="{xx}" cy="{y}" r="4" fill="#29485d"/>')
    text(out, x1-4, y-42, label, 17)


def topology(path, vals):
    out = svg_open("SC actual endpoints and phase states",
                   "S1 connects x to A; S2 connects A to s. Cs from A to 0, Cf from s to o, OTA positive input at 0. Same endpoints in every panel.", 1010)
    text(out, 25, 36, "Two-phase inverting SC integrator", 25)
    text(out, 25, 67, f'Cs={vals["Cs_F"]} F; Cf={vals["Cf_F"]} F', 16)
    for k, (phase, on1, on2) in enumerate(PHASES[:3]):
        base = 100 + k*285
        text(out, 25, base-10, f'{phase}: S1={"ON" if on1 else "OFF"}, S2={"ON" if on2 else "OFF"}', 22)
        y = base+125
        line(out, 48, y, 85, y)
        switch(out, 117, y, on1, "S1 / phi1")
        line(out, 204, y, 295, y)
        switch(out, 327, y, on2, "S2 / phi2")
        line(out, 414, y, 460, y)
        line(out, 460, y, 475, y)
        out.append(f'<path d="M475,{y-32} L475,{y+67} L570,{y+17} Z" fill="#edf2f5" stroke="#29485d" stroke-width="3"/>')
        text(out, 484, y+3, "−", 22)
        text(out, 484, y+48, "+", 22)
        line(out, 460, y+40, 475, y+40)
        line(out, 460, y+40, 460, y+88)
        text(out, 446, y+113, "0", 20)
        line(out, 570, y+17, 670, y+17)
        line(out, 260, y, 260, y+36)
        line(out, 237, y+36, 283, y+36)
        line(out, 237, y+48, 283, y+48)
        line(out, 260, y+48, 260, y+89)
        text(out, 247, y+114, "B=0")
        text(out, 211, y-9, "A")
        text(out, 289, y+46, "Cs")
        line(out, 445, y, 445, y-65)
        line(out, 445, y-65, 513, y-65)
        line(out, 513, y-82, 513, y-48)
        line(out, 525, y-82, 525, y-48)
        line(out, 525, y-65, 630, y-65)
        line(out, 630, y-65, 630, y+17)
        text(out, 510, y-94, "Cf")
        text(out, 36, y-9, "x")
        text(out, 443, y-9, "s=0")
        text(out, 649, y+4, "o")
        text(out, 584, y+54, "OTA", 17)
    text(out, 25, 972, "Cf remains connected. No reset switch. Dead time: both OFF.", 17)
    path.write_text("\n".join(out+["</g></svg>"])+"\n", encoding="utf-8")


def timing(path, vals, rows):
    out = svg_open("Read phase and charge trajectory",
                   "Four cycles. phi1 sample read is before transfer, phi2 read after transfer. Dead gaps prevent S1 and S2 from conducting together. Charge rows come from ledger CSV.", 650)
    text(out, 25, 35, "Read timing: y[n] before, w[n]=y[n+1] after", 23)
    text(out, 25, 65, "Symbolic phase positions; no OTA settling-time guarantee", 16)
    for label, high0, high1, yy, color in [("phi1", 0, .40, 130, "#007a68"),
                                            ("phi2", .50, .90, 215, "#275ca3")]:
        text(out, 20, yy, label)
        for n in range(min(4, len(rows))):
            a=95+n*155
            points=[(a,yy+20),(a+155*high0,yy+20),(a+155*high0,yy-20),
                    (a+155*high1,yy-20),(a+155*high1,yy+20),(a+155,yy+20)]
            out.append('<polyline points="'+' '.join(f'{x:g},{y:g}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="3"/>')
            if label == "phi1":
                text(out,a+12,101,f'n={n}',16)
                text(out,a+44,178,f'y[{n}]',17,color)
            else:
                text(out,a+88,266,f'w[{n}]',17,color)
    text(out,25,313,"First up to four input records; all voltages in V",20)
    for xx, label in [(25,"n"),(85,"x[n]"),(190,"y[n]"),(295,"w[n]"),
                      (425,"zero-input + zero-state")]:
        text(out,xx,347,label,16)
    for i,row in enumerate(rows[:4]):
        yy=386+i*48
        for xx, key in [(25,"n"),(85,"x_V"),(190,"y_before_V"),(295,"w_after_V")]:
            text(out,xx,yy,row[key],18)
        text(out,425,yy,f'{row["zero_input_V"]} + ({row["zero_state_after_V"]})',18)
    text(out,25,605,"Positive x adds positive A-plate charge; output must decrease.",17)
    path.write_text("\n".join(out+["</g></svg>"])+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).with_name("fixed-inputs.json"))
    parser.add_argument("--out-dir", type=Path, required=True)
    args=parser.parse_args()
    vals=load_input(args.input)
    forbidden = {Path(__file__).resolve().parent, args.input.resolve().parent}
    forbidden.update(Path(__file__).resolve().parents)
    forbidden.update(args.input.resolve().parents)
    if args.out_dir.is_symlink() or args.out_dir.resolve() in forbidden:
        parser.error("out-dir must be a separate nonsymlink output directory")
    if args.out_dir.exists() and (not args.out_dir.is_dir() or any(args.out_dir.iterdir())):
        parser.error("out-dir must be absent or empty; existing files are preserved")
    rows=ledger(vals["Cs_F"],vals["Cf_F"],vals["x_V"],vals["y0_V"])
    parasitic=ledger(vals["Cs_F"],vals["Cf_F"],vals["x_V"],vals["y0_V"],vals["Cp_F"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir/"charge-ledger.csv",rows)
    write_csv(args.out_dir/"parasitic-ledger.csv",parasitic)
    result={"model":"ideal OTA, complete settling, nonoverlap, A-to-ground Cp only",
            "endpoints":ENDPOINTS,"phases":PHASES,"input_shape":[len(vals["x_V"])],
            "state_shape":[len(rows)+1],"y0_V":str(vals["y0_V"]),
            "alpha":str(vals["Cs_F"]/vals["Cf_F"]),
            "alpha_with_Cp":str((vals["Cs_F"]+vals["Cp_F"])/vals["Cf_F"]),
            "Req_ohm":str(1/(vals["Cs_F"]*vals["fs_Hz"])),
            "nominal":rows,"A_ground_parasitic":parasitic}
    (args.out_dir/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    topology(args.out_dir/"phase-endpoints.svg",vals)
    timing(args.out_dir/"read-timing.svg",vals,rows)
    print(json.dumps({"alpha":result["alpha"],"alpha_with_Cp":result["alpha_with_Cp"],
                      "Req_ohm":result["Req_ohm"],"w_after_V":[r["w_after_V"] for r in rows]},sort_keys=True))


if __name__ == "__main__":
    main()
