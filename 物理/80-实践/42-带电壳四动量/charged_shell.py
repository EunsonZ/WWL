#!/usr/bin/env python3
"""Exact passive boosts of one static charged shell and tangential membrane.

Standard library only. All grids are finite; the radial variable q=a/r maps
infinity to q=0. This computes static equilibrium integrals, not trajectories.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import sys
import time

C = 299792458.0
EPS0 = 8.8541878128e-12  # fixed SI teaching value, not fitted to a material
KEYS = {"charge_C", "radius_m", "material_rest_energy_J", "beta", "n_mu",
        "n_phi", "n_radial", "beta_sweep"}


def number(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name}: expected a finite number")
    value = float(value)
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{name}: must be finite in [{lo}, {hi}]")
    return value


def integer(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ValueError(f"{name}: expected integer in [{lo}, {hi}]")
    return value


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_card(path):
    if path.stat().st_size > 16384:
        raise ValueError("input card exceeds 16384 bytes")
    card = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(card, dict) or set(card) != KEYS:
        raise ValueError(f"input card must have exactly these keys: {sorted(KEYS)}")
    q = number(card["charge_C"], "charge_C", -1e-6, 1e-6)
    if abs(q) < 1e-15:
        raise ValueError("charge_C: require 1e-15 <= abs(Q) <= 1e-6")
    a = number(card["radius_m"], "radius_m", 1e-6, 10.0)
    w = number(card["material_rest_energy_J"], "material_rest_energy_J", 1e-15, 1e-2)
    card["beta"] = number(card["beta"], "beta", -0.9, 0.9)
    for name, lo, hi in [("n_mu", 8, 256), ("n_phi", 8, 64), ("n_radial", 8, 128)]:
        card[name] = integer(card[name], name, lo, hi)
    if card["n_mu"] * card["n_phi"] * card["n_radial"] > 1500000:
        raise ValueError("grid product exceeds 1500000 samples")
    sweep = card["beta_sweep"]
    if not isinstance(sweep, list) or not 2 <= len(sweep) <= 31:
        raise ValueError("beta_sweep: expected 2..31 numbers")
    card["beta_sweep"] = [number(b, "beta_sweep entry", -0.9, 0.9) for b in sweep]
    if len(set(card["beta_sweep"])) != len(sweep):
        raise ValueError("beta_sweep: entries must be unique")
    # This teaching card enforces w_surface >= tension in the rest frame.
    u = q*q/(8*math.pi*EPS0*a)
    if w < u/2:
        raise ValueError("material_rest_energy_J must be >= U_em/2 for this membrane card")
    card.update(charge_C=q, radius_m=a, material_rest_energy_J=w)
    return card


def angular_grid(n_mu, n_phi):
    # polar axis is x. mu midpoint, phi periodic trapezoid; weights /4pi.
    wt = 1/(n_mu*n_phi)
    for i in range(n_mu):
        mu = -1+(2*i+1)/n_mu
        transverse = math.sqrt(1-mu*mu)
        for j in range(n_phi):
            phi = 2*math.pi*j/n_phi
            yield (mu, transverse*math.cos(phi), transverse*math.sin(phi)), wt


def radial_measure(n_radial):
    # E/E(a)=(a/r)^2=q^2; r^2 |dr| /a^3 =q^-4 dq.
    # We evaluate the product on the compact grid rather than truncate at R.
    return math.fsum(((((i+0.5)/n_radial)**2)**2 /
                      (((i+0.5)/n_radial)**4))/n_radial
                     for i in range(n_radial))


def integrate(card, beta, n_mu=None):
    q, a, w = card["charge_C"], card["radius_m"], card["material_rest_energy_J"]
    u = q*q/(8*math.pi*EPS0*a)
    gamma = 1/math.sqrt(1-beta*beta)
    radial = radial_measure(card["n_radial"])
    n_mu = card["n_mu"] if n_mu is None else n_mu
    terms = {k: [] for k in ("rest_u", "em_xx", "em_yy", "em_zz", "em_xy", "mat_xx",
                             "mat_yy", "mat_zz", "field_E", "field_cp", "tensor_E",
                             "tensor_cp", "field_cpy", "field_cpz", "mat_E", "mat_cp")}
    for (nx, ny, nz), wt in angular_grid(n_mu, card["n_phi"]):
        spatial = (1-2*nx*nx, 1-2*ny*ny, 1-2*nz*nz)
        # local boosted E/E(a), cB/E(a), with shell moving -beta*c x.
        ex, ey, ez = nx, gamma*ny, gamma*nz
        bx, by, bz = 0.0, gamma*beta*nz, -gamma*beta*ny
        energy_field = ex*ex+ey*ey+ez*ez+bx*bx+by*by+bz*bz
        cp_field = 2*(ey*bz-ez*by)
        values = {
            "rest_u": u*radial,
            "em_xx": u*radial*spatial[0], "em_yy": u*radial*spatial[1],
            "em_zz": u*radial*spatial[2], "em_xy": -2*u*radial*nx*ny,
            # Integral of tension: 4pi*a^2*tau=U/2, two tangents.
            "mat_xx": -u/2*(1-nx*nx), "mat_yy": -u/2*(1-ny*ny),
            "mat_zz": -u/2*(1-nz*nz),
            "field_E": u*radial*energy_field/gamma,
            "field_cp": u*radial*cp_field/gamma,
            "field_cpy": u*radial*2*(ez*bx-ex*bz)/gamma,
            "field_cpz": u*radial*2*(ex*by-ey*bx)/gamma,
            "tensor_E": u*radial*gamma*(1+beta*beta*spatial[0]),
            "tensor_cp": -u*radial*gamma*beta*(1+spatial[0]),
            "mat_E": gamma*(w-beta*beta*u/2*(1-nx*nx)),
            "mat_cp": -gamma*beta*(w-u/2*(1-nx*nx)),
        }
        for key, val in values.items():
            terms[key].append(wt*val)
    out = {k: math.fsum(v) for k, v in terms.items()}
    e0 = u+w
    out.update(beta=beta, gamma=gamma, exact_U_em_J=u, material_rest_energy_J=w,
               exact_em_E_J=gamma*u*(1+beta*beta/3),
               exact_em_cp_J=-4*gamma*beta*u/3,
               exact_mat_E_J=gamma*(w-beta*beta*u/3),
               exact_mat_cp_J=-gamma*beta*(w-u/3),
               exact_total_E_J=gamma*e0, exact_total_cp_J=-gamma*beta*e0,
               # same rest t=0 geometric slice, expressed in S' coordinates
               same_slice_em_E_J=gamma*u, same_slice_em_cp_J=-gamma*beta*u,
               total_E_J=out["field_E"]+out["mat_E"],
               total_cp_J=out["field_cp"]+out["mat_cp"])
    out["invariant_relative_residual"] = ((out["total_E_J"]**2-out["total_cp_J"]**2)/e0**2-1)
    out["field_tensor_route_relative_difference"] = max(
        abs(out["field_E"]-out["tensor_E"]), abs(out["field_cp"]-out["tensor_cp"]))/e0
    return out


def exact_geometry(q, a, w):
    ea = q/(4*math.pi*EPS0*a*a)
    u = q*q/(8*math.pi*EPS0*a)
    pressure = EPS0*ea*ea/2
    tension = pressure*a/2
    return dict(charge_C=q, radius_m=a, surface_E_V_per_m=ea,
                surface_charge_C_per_m2=q/(4*math.pi*a*a), U_em_J=u,
                outward_pressure_Pa=pressure, tension_N_per_m=tension,
                membrane_rest_energy_J=w, membrane_energy_per_area_J_per_m2=w/(4*math.pi*a*a),
                local_energy_margin_J_per_m2=(w-u/2)/(4*math.pi*a*a))


def csv_write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def svg_start(title, desc, height=560):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 {height}" role="img">',
            f'<title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc>',
            '<rect width="1040" height="100%" fill="#fafafa"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#19212b} .axis{stroke:#19212b;stroke-width:1.4} .grid{stroke:#ccd4dd;stroke-width:1}</style>',
            f'<text x="40" y="32" font-size="22">{html.escape(title)}</text>']


def charts(rows, e0):
    elems = svg_start("Observer simultaneous slices: stresses close total momentum",
        "Exact passive boost. Field-only and total energy/momentum divided by the total rest energy E0. Material stress contribution has opposite sign to shell velocity. Curves come from beta-sweep.csv.")
    panels = [(80, 280, "E prime / E0", ["em_E_over_E0", "mat_E_over_E0", "total_E_over_E0"]),
              (610, 280, "c p prime x / E0", ["em_cp_over_E0", "mat_cp_over_E0", "total_cp_over_E0"])]
    colors = ["#1769aa", "#a34b19", "#222222"]
    labels = ["field", "membrane", "total"]
    for px, py, axis_label, keys in panels:
        # fixed range covers |beta|<=.9, energies and signed cp normalized E0
        low, high = ((-0.1, 2.6) if px == 80 else (-2.3, 2.3))
        mapx = lambda b: px+380*(b+0.9)/1.8
        mapy = lambda y: py+190-380*(y-low)/(high-low)
        for y in [0, 1, 2] if px == 80 else [-2,-1,0,1,2]:
            yy=mapy(y)
            elems.extend([f'<line x1="{px}" y1="{yy:.4f}" x2="{px+380}" y2="{yy:.4f}" class="grid"/>',
                          f'<text x="{px-9}" y="{yy+5:.4f}" font-size="14" text-anchor="end">{y}</text>'])
        elems.append(f'<line x1="{px}" y1="{py-190}" x2="{px}" y2="{py+190}" class="axis"/>')
        elems.append(f'<line x1="{px}" y1="{py+190}" x2="{px+380}" y2="{py+190}" class="axis"/>')
        for b in [-.9,-.6,-.3,0,.3,.6,.9]:
            xx=mapx(b)
            elems.append(f'<text x="{xx:.4f}" y="{py+212}" font-size="13" text-anchor="middle">{b:g}</text>')
        elems.extend([f'<text x="{px+190}" y="{py+239}" font-size="16" text-anchor="middle">observer beta = v/c; shell moves -v</text>',
                      f'<text x="{px}" y="{py-208}" font-size="17">{axis_label}</text>'])
        for key,col,label in zip(keys,colors,labels):
            points=" ".join(f'{mapx(r["beta"]):.4f},{mapy(r[key]):.4f}' for r in rows)
            elems.append(f'<polyline data-series="{key}" points="{points}" fill="none" stroke="{col}" stroke-width="2.5"/>')
            for r in rows:
                elems.append(f'<circle cx="{mapx(r["beta"]):.4f}" cy="{mapy(r[key]):.4f}" r="3.3" fill="{col}"/>')
            idx=labels.index(label)
            elems.append(f'<text x="{px+110*idx}" y="{py-170}" fill="{col}" style="fill:{col}" font-size="15">{label}</text>')
    elems.extend(['<text x="40" y="552" font-size="13">Exact equilibrium boost; line segments connect supplied samples. E0 = Uem + W. No acceleration or stability model.</text>', '</svg>'])
    return "\n".join(elems)+"\n"


def geometry_svg(geom, beta):
    p, tau = geom["outward_pressure_Pa"],geom["tension_N_per_m"]
    elems=svg_start("Charged shell: local force balance and two time slices",
        "Left: membrane tensions on two tangents counter outward electric traction with 2 tau/a = p. Right: rest t=0 and observer t'=0 are different spacelike slices across the shell world tube. Units ct and x are lengths.", 570)
    elems.extend(['<defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><path d="M0,0 L9,3.5 L0,7 Z" fill="#19212b"/></marker></defs>',
    '<circle cx="235" cy="260" r="125" fill="#eef5fa" stroke="#1769aa" stroke-width="3"/>',
    '<text x="228" y="264" font-size="20">Q</text>',
    '<line x1="235" y1="260" x2="360" y2="260" stroke="#19212b" marker-end="url(#arrow)"/>',
    '<text x="290" y="249" font-size="17">a</text>',
    '<line x1="360" y1="260" x2="440" y2="260" stroke="#19212b" stroke-width="2.4" marker-end="url(#arrow)"/>',
    '<text x="375" y="242" font-size="17">p n (out)</text>',
    '<path d="M360,260 Q357,220 342,195" fill="none" stroke="#a34b19" stroke-width="2.5"/>',
    '<polygon points="342,195 349.630,200.917 343.627,204.518" fill="#a34b19"/>',
    '<path d="M360,260 Q357,300 342,325" fill="none" stroke="#a34b19" stroke-width="2.5"/>',
    '<polygon points="342,325 343.627,315.482 349.630,319.083" fill="#a34b19"/>',
    '<text x="360" y="195" font-size="16">tangent tension tau</text>',
    '<text x="90" y="422" font-size="18">p = eps0 E(out)^2 / 2 ; 2 tau/a = p</text>',
    f'<text x="90" y="454" font-size="16">p = {p:.6g} Pa ; tau = {tau:.6g} N/m</text>',
    '<text x="90" y="483" font-size="16">Force arrows show directions, not a common scale.</text>',
    '<rect x="670" y="105" width="140" height="300" fill="#e8edf1"/>',
    '<line x1="650" y1="370" x2="980" y2="370" class="axis" marker-end="url(#arrow)"/>',
    '<line x1="740" y1="420" x2="740" y2="90" class="axis" marker-end="url(#arrow)"/>',
    '<text x="986" y="376" font-size="17">x/a</text><text x="750" y="93" font-size="17">ct/a</text>',
    '<line x1="670" y1="105" x2="670" y2="405" stroke="#526171" stroke-width="2"/>',
    '<line x1="810" y1="105" x2="810" y2="405" stroke="#526171" stroke-width="2"/>',
    '<text x="672" y="78" font-size="17">shell world tube in S</text>',
    '<line x1="660" y1="280" x2="955" y2="280" stroke="#1769aa" stroke-width="3"/>',
    '<text x="836" y="269" font-size="17" style="fill:#1769aa">rest t = 0</text>'])
    elems.extend([f'<line x1="660" y1="{280+80*beta:.4f}" x2="820" y2="{280-80*beta:.4f}" stroke="#a34b19" stroke-width="3"/>',
                 f'<text x="825" y="{280-80*beta-15:.4f}" font-size="17" style="fill:#a34b19">t prime = 0</text>',
                 '<text x="648" y="450" font-size="17">Observer slice in rest coordinates: ct = beta x</text>',
                 '<text x="648" y="480" font-size="16">Both slices are spacelike; they select different events.</text>',
                 '<text x="40" y="545" font-size="14">Static shell and its Lorentz transforms only. Field tensor remains covariant; field slice integrals differ.</text>', '</svg>'])
    # Move the x-axis to the actual ct=0 baseline for mathematical consistency.
    text="\n".join(elems)+"\n"
    text=text.replace('x1="650" y1="370" x2="980" y2="370"','x1="650" y1="280" x2="980" y2="280"').replace('x="986" y="376"','x="986" y="286"')
    if abs(beta) < 0.2:
        # Keep labels apart when the two lines are close or coincident.
        old=f'x="825" y="{280-80*beta-15:.4f}"'
        text=text.replace(old, 'x="825" y="320"')
    if beta == 0:
        text=text.replace('Both slices are spacelike; they select different events.',
                          'At beta = 0 the two slices coincide.')
        text=text.replace('field slice integrals differ.', 'at beta = 0 both field integrals agree.')
        text=text.replace('t prime = 0', 't prime = t = 0')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=Path(__file__).with_name("inputs.json"))
    parser.add_argument("--out", type=Path, required=True, help="new output directory only; existing path refused")
    args = parser.parse_args()
    started=time.monotonic()
    try:
        card=read_card(args.inputs)
        out=args.out
        if out.exists() or out.is_symlink():
            raise ValueError("output path already exists; choose a new directory")
        if not out.parent.is_dir():
            raise ValueError("output parent must already be a directory")
        # Validate and compute all data before creating the output path.
        default=integrate(card,card["beta"])
        u=default["exact_U_em_J"]; w=card["material_rest_energy_J"]; e0=u+w
        geometry=exact_geometry(card["charge_C"],card["radius_m"],w)
        sweep=[]
        for b in sorted(card["beta_sweep"]):
            r=integrate(card,b)
            sweep.append(dict(beta=b,gamma=r["gamma"],em_E_J=r["field_E"],
                mat_E_J=r["mat_E"],total_E_J=r["total_E_J"],em_cp_J=r["field_cp"],
                mat_cp_J=r["mat_cp"],total_cp_J=r["total_cp_J"],
                em_E_over_E0=r["field_E"]/e0,mat_E_over_E0=r["mat_E"]/e0,total_E_over_E0=r["total_E_J"]/e0,
                em_cp_over_E0=r["field_cp"]/e0,mat_cp_over_E0=r["mat_cp"]/e0,total_cp_over_E0=r["total_cp_J"]/e0,
                expected_total_E_J=r["exact_total_E_J"],expected_total_cp_J=r["exact_total_cp_J"]))
        conv=[]
        grids=sorted(set([8,16,32,64,128,card["n_mu"]]))
        for nm in grids:
            r=integrate(card,card["beta"],nm)
            conv.append(dict(n_mu=nm,n_phi=card["n_phi"],n_radial=card["n_radial"],
                em_stress_xx_over_U=r["em_xx"]/u,mat_stress_xx_over_U=r["mat_xx"]/u,
                total_stress_xx_over_U=(r["em_xx"]+r["mat_xx"])/u,
                total_E_error_over_E0=(r["total_E_J"]-r["exact_total_E_J"])/e0,
                total_cp_error_over_E0=(r["total_cp_J"]-r["exact_total_cp_J"])/e0,
                invariant_relative_residual=r["invariant_relative_residual"]))
        changes=[]
        for label,qs,aa in [("baseline",1,1),("a_doubled",1,2),("Q_doubled",2,1),("Q_reversed",-1,1)]:
            geom=exact_geometry(card["charge_C"]*qs,card["radius_m"]*aa,w)
            geom.update(case=label,W_fixed_J=w,local_energy_bound_satisfied=w>=geom["U_em_J"]/2)
            changes.append(geom)
        beta=card["beta"]; g=default["gamma"]
        no_mem=dict(description="rest initial-slice force diagnostic with zero tension; no time extension or boosted slice integral",
            net_vector_force_N=[0,0,0],outward_local_traction_Pa=geometry["outward_pressure_Pa"],
            unbalanced_integrated_Txx_J=u/3)
        result=dict(model="static finite charged shell plus tangential tension membrane; passive boost",
            constants=dict(c_m_per_s=C,epsilon0_F_per_m=EPS0),inputs=card,geometry=geometry,
            default=default,rest_total_energy_J=e0,rest_mass_kg=e0/C**2,
            membrane_removed=no_mem,parameter_cases=changes,
            numerical_method="midpoint mu, periodic phi; compact q=a/r integrates full radial domain; observer slice measure dVrest/gamma",
            elapsed_s=time.monotonic()-started)
        plot=charts(sweep,e0);geom_plot=geometry_svg(geometry,beta)
        out.mkdir()  # refuses a path created concurrently; no overwrite flag
        csv_write(out/"beta-sweep.csv",sweep)
        csv_write(out/"convergence.csv",conv)
        csv_write(out/"parameter-cases.csv",changes)
        (out/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        (out/"momentum.svg").write_text(plot,encoding="utf-8")
        (out/"shell-slices.svg").write_text(geom_plot,encoding="utf-8")
        print(json.dumps(dict(output=str(out),files=6,U_em_J=u,E_total_J=default["total_E_J"],
            cp_total_J=default["total_cp_J"],invariant_relative_residual=default["invariant_relative_residual"]),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
        print(f"charged_shell: {exc}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
