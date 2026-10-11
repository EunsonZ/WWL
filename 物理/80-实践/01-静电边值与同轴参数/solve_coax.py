"""Finite ideal coax BVP: analytic fields, quadrature checks and SVG figures.

No FEM or hardware measurement. Each layer has zero free volume charge;
interfaces have zero free surface charge. Conductors have prescribed voltages;
end faces obey d(phi)/dz = 0. All stored quantities use SI units.
"""

import argparse
import csv
import json
import math
import platform
from pathlib import Path


C0 = 299792458.0  # m/s, exact SI value
MU0 = 4.0 * math.pi * 1e-7  # H/m, conventional approximation, not exact SI
EPS0 = 1.0 / (MU0 * C0 * C0)  # F/m, consistent with the approximation


def simpson(function, left, right, count):
    if count <= 0 or count % 2:
        raise ValueError("Simpson subinterval count must be positive and even")
    step = (right - left) / count
    total = function(left) + function(right)
    total += 4.0 * sum(function(left + i * step) for i in range(1, count, 2))
    total += 2.0 * sum(function(left + i * step) for i in range(2, count, 2))
    return total * step / 3.0


def layered(a, b, interface, relative, voltage, count):
    eps1, eps2 = (EPS0 * x for x in relative)
    resistance = math.log(interface / a) / eps1 + math.log(b / interface) / eps2
    k = voltage / resistance  # r D_r, C/m
    capacitance = 2.0 * math.pi / resistance

    def potential(r):
        if r <= interface:
            return voltage - k / eps1 * math.log(r / a)
        return k / eps2 * math.log(b / r)

    # Separate the integrals at the material jump. An endpoint value from
    # the wrong material would give a spurious finite quadrature contribution.
    voltage_integral = sum(
        simpson(lambda r: k / (eps * r), left, right, count)
        for left, right, eps in ((a, interface, eps1), (interface, b, eps2))
    )
    energy_integral = sum(
        simpson(lambda r: math.pi * k * k / (eps * r), left, right, count)
        for left, right, eps in ((a, interface, eps1), (interface, b, eps2))
    )
    phi_left = voltage - k / eps1 * math.log(interface / a)
    phi_right = k / eps2 * math.log(b / interface)
    field_left = k / (eps1 * interface)
    field_right = k / (eps2 * interface)
    return {
        "interface_m": interface,
        "epsilon_r": relative,
        "C_prime_F_per_m": capacitance,
        "k_C_per_m": k,
        "interface_phi_V": potential(interface),
        "layer_voltage_V": [voltage - potential(interface), potential(interface)],
        "interface_E_V_per_m": [field_left, field_right],
        "interface_D_C_per_m2": [eps1 * field_left, eps2 * field_right],
        "bound_interface_sigma_C_per_m2": EPS0 * (field_right - field_left),
        "W_E_prime_J_per_m": 0.5 * capacitance * voltage * voltage,
        "voltage_quadrature_V": voltage_integral,
        "energy_quadrature_J_per_m": energy_integral,
        "residuals": {
            "phi_a_minus_V_V": potential(a) - voltage,
            "phi_b_V": potential(b),
            "phi_jump_V": phi_right - phi_left,
            "D_jump_C_per_m2": eps2 * field_right - eps1 * field_left,
            "relative_voltage_quadrature_error": abs(voltage_integral - voltage) / abs(voltage),
            "relative_energy_quadrature_error": abs(energy_integral - 0.5 * capacitance * voltage**2)
            / (0.5 * capacitance * voltage**2),
        },
    }


def curve_svg(inputs, uniform, layer):
    a, b = inputs["a_m"], inputs["b_m"]
    c = inputs["layer_interface_m"]
    voltage = inputs["voltage_V"]
    eps1, eps2 = [EPS0 * x for x in inputs["layer_epsilon_r"]]
    k = layer["k_C_per_m"]
    conditions = f'a={a * 1000:g} mm, b={b * 1000:g} mm, V={voltage:g} V; c={c * 1000:g} mm for layers'
    uniform_label = f'uniform epsilon_r={inputs["epsilon_r"]:g}'
    layer_label = f'layers epsilon_r={inputs["layer_epsilon_r"][0]:g} / {inputs["layer_epsilon_r"][1]:g}'
    continuity = 'E jumps at c' if eps1 != eps2 else 'E is continuous at c'
    panels = [
        ("Potential phi (V)", 1.05 * abs(voltage), lambda r: voltage * math.log(b / r) / math.log(b / a),
         lambda r: voltage - k / eps1 * math.log(r / a) if r <= c else k / eps2 * math.log(b / r)),
        ("Radial E (V/m)", 1.05 * max(abs(voltage / (a * math.log(b / a))), abs(k / (eps1 * a))),
         lambda r: voltage / (r * math.log(b / a)),
         lambda r: k / ((eps1 if r <= c else eps2) * r)),
        ("Accumulated energy (pJ/m)", 1.05 * max(uniform["W_E_prime_J_per_m"], layer["W_E_prime_J_per_m"]) * 1e12,
         lambda r: uniform["W_E_prime_J_per_m"] * math.log(r / a) / math.log(b / a) * 1e12,
         lambda r: math.pi * k**2 * (math.log(min(r, c) / a) / eps1 +
                                  (math.log(r / c) / eps2 if r > c else 0.0)) * 1e12),
    ]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 690 760" role="img" aria-labelledby="title desc">',
             f'<title id="title">Coax potential, radial field and cumulative field energy: {conditions}</title>',
             f'<desc id="desc">Actual inputs: {conditions}. Blue solid: {uniform_label}. Orange dashed: {layer_label}. Each horizontal axis is radius in mm. {continuity}; phi and cumulative energy remain continuous.</desc>',
             '<rect width="690" height="760" fill="white"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#172b3a;font-size:13px}.axis{stroke:#172b3a;stroke-width:1.3;fill:none}.grid{stroke:#d9e1e5;fill:none}.uniform{stroke:#1565c0;fill:none;stroke-width:2.5}.layer{stroke:#be5500;fill:none;stroke-width:2.5;stroke-dasharray:7 4}</style>',
             f'<text x="75" y="23">{conditions}</text>',
             f'<path class="uniform" d="M75 43h35"/><text x="118" y="47">{uniform_label}</text>',
             f'<path class="layer" d="M370 43h35"/><text x="414" y="47">{layer_label}</text>']
    for index, (title, ymax, fu, fl) in enumerate(panels):
        top, bottom = 80 + index * 220, 245 + index * 220
        xmap = lambda r: 75 + (r - a) / (b - a) * 540
        ymap = lambda value: bottom - value / ymax * (bottom - top)
        parts.append(f'<text x="75" y="{top - 8}">{title}</text>')
        for i in range(5):
            y = bottom - i / 4 * (bottom - top)
            value = ymax * i / 4
            parts.append(f'<path class="grid" d="M75 {y:.2f}H615"/><text x="66" y="{y+4:.2f}" text-anchor="end">{value:.3g}</text>')
        parts.append(f'<path class="axis" d="M75 {top}V{bottom}H615"/>')
        for fraction in (0, 1/3, 2/3, 1):
            r = a + fraction * (b - a)
            x = xmap(r)
            parts.append(f'<path class="axis" d="M{x:.2f} {bottom}v5"/><text x="{x:.2f}" y="{bottom+20}" text-anchor="middle">{r*1000:.2g}</text>')
        parts.append(f'<text x="625" y="{bottom+20}">r (mm)</text>')
        xc = xmap(c)
        parts.append(f'<path stroke="#888" stroke-dasharray="2 4" d="M{xc:.2f} {top}V{bottom}"/>')
        # Include c twice for the E panel to draw the discontinuity at the
        # same x coordinate, never as an interpolated finite-thickness ramp.
        radii = [a + (c-a) * i / 100 for i in range(101)] + [c + (b-c) * i / 100 for i in range(101)]
        for style, function in (("uniform", fu), ("layer", fl)):
            points = []
            for j, r in enumerate(radii):
                value = function(r)
                if index == 1 and style == "layer" and j == 101:
                    value = k / (eps2 * c)
                points.append(f'{xmap(r):.3f},{ymap(value):.3f}')
            parts.append(f'<polyline class="{style}" points="{" ".join(points)}"/>')
    parts.append('<text x="75" y="749">Ideal static BVP; curves are generated from its equations, not measurements.</text></svg>')
    return "\n".join(parts)


def geometry_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 440" role="img" aria-labelledby="title desc">
<title id="title">固定参考同轴中央截面的场、电荷与法向</title>
<desc id="desc">固定几何参考，不随输入文件变化：内半径1毫米、外导体内半径4毫米、内电位1伏、外电位0伏、相对介电常数4。内导体正电荷，外导体负电荷。电场径向向外。内导体朝介质法向向外，外导体朝介质法向向内。图为静态横截面，不包含实际开放端部。</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs>
<rect width="650" height="440" fill="white"/>
<style>text{font-family:Arial,"PingFang SC",sans-serif;font-size:15px;fill:#172b3a}</style>
<circle cx="210" cy="200" r="158" fill="#dce3e8" stroke="#334b5f" stroke-width="2"/>
<circle cx="210" cy="200" r="144" fill="#edf6ff" stroke="#334b5f" stroke-width="2"/>
<circle cx="210" cy="200" r="36" fill="#dce3e8" stroke="#334b5f" stroke-width="2"/>
<text x="190" y="225">+</text><text x="349" y="206">−</text>
<g stroke="#1565c0" stroke-width="3" marker-end="url(#arrow)">
<path d="M255 200H325"/><path d="M165 200H95"/><path d="M210 155V85"/><path d="M210 245V315"/>
</g>
<path d="M237 228L268 259" stroke="#be5500" stroke-width="3" marker-end="url(#arrow)"/>
<path d="M312 302L281 271" stroke="#be5500" stroke-width="3" marker-end="url(#arrow)"/>
<path d="M210 200H246" stroke="#172b3a"/><text x="220" y="190">a</text>
<path d="M210 200L108 98" stroke="#172b3a"/><text x="134" y="134">b</text>
<text x="394" y="70">a = 1 mm, b = 4 mm</text>
<text x="394" y="110">Inner electrode: phi = 1 V</text><text x="394" y="140">Outer electrode: phi = 0 V</text>
<text x="394" y="188" fill="#1565c0">Blue: E radial outward</text>
<text x="394" y="225" fill="#be5500">Orange: n_c into dielectric</text>
<text x="394" y="257">Inner: n_c = +e_r</text><text x="394" y="289">Outer: n_c = -e_r</text>
<text x="70" y="408">Fixed reference: a=1 mm, b=4 mm, V=1 V, epsilon_r=4.</text>
<text x="70" y="431">Arrows show direction; geometry is to scale.</text>
</svg>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inputs = json.loads(args.input.read_text())
    a, b = inputs["a_m"], inputs["b_m"]
    length = inputs["length_m"]
    voltage, current = inputs["voltage_V"], inputs["current_A"]
    count = inputs["simpson_subintervals_per_layer"]
    if not (0 < a < b and length > 0 and voltage > 0 and inputs["epsilon_r"] > 0 and inputs["mu_r"] > 0):
        raise ValueError("Need positive dimensions, voltage and material constants")
    for ckey, ekey in (("layer_interface_m", "layer_epsilon_r"), ("transfer_interface_m", "transfer_epsilon_r")):
        if not (a < inputs[ckey] < b and len(inputs[ekey]) == 2 and min(inputs[ekey]) > 0):
            raise ValueError("Each interface must lie inside the annulus with two positive permittivities")
    eps, mu = EPS0 * inputs["epsilon_r"], MU0 * inputs["mu_r"]
    logratio = math.log(b / a)
    cp, lp = 2 * math.pi * eps / logratio, mu * logratio / (2 * math.pi)
    energy = 0.5 * cp * voltage**2
    energy_quad = simpson(lambda r: math.pi * eps * voltage**2 / (r * logratio**2), a, b, count)
    power_quad = simpson(lambda r: voltage * current / logratio / r, a, b, count)
    uniform = {
        "C_prime_F_per_m": cp, "L_prime_H_per_m": lp,
        "Z0_ohm": math.sqrt(lp / cp), "vp_m_per_s": 1 / math.sqrt(lp * cp),
        "finite_model_C_F": cp * length, "one_way_delay_s": length * math.sqrt(lp * cp),
        "E_a_V_per_m": voltage / (a * logratio), "E_b_V_per_m": voltage / (b * logratio),
        "W_E_prime_J_per_m": energy, "W_H_prime_J_per_m": 0.5 * lp * current**2,
        "energy_quadrature_J_per_m": energy_quad,
        "VI_W": voltage * current, "power_quadrature_W": power_quad,
        "DC_V_over_I_ohm": voltage / current if current else None,
        "relative_energy_quadrature_error": abs(energy_quad - energy) / energy,
        "relative_power_quadrature_error": abs(power_quad - voltage * current) / abs(voltage * current) if current else None,
    }
    layer = layered(a, b, inputs["layer_interface_m"], inputs["layer_epsilon_r"], voltage, count)
    transfer = layered(a, b, inputs["transfer_interface_m"], inputs["transfer_epsilon_r"], voltage, count)
    output = {
        "model": "static linear coax, zero free volume/interface charge, Dirichlet cylindrical faces, Neumann end faces",
        "python": platform.python_version(), "inputs": inputs,
        "constants": {"c0_m_per_s": C0, "mu0_H_per_m_approx": MU0, "epsilon0_F_per_m_derived": EPS0},
        "uniform": uniform, "two_layer": layer, "transfer": transfer,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "values.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    (args.output_dir / "coax-curves.svg").write_text(curve_svg(inputs, uniform, layer))
    (args.output_dir / "coax-geometry.svg").write_text(geometry_svg())
    with (args.output_dir / "uniform-fields.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["r_m", "phi_V", "E_r_V_per_m", "D_r_C_per_m2", "cumulative_W_E_prime_J_per_m"])
        for i in range(101):
            r = a + (b - a) * i / 100
            field = voltage / (r * logratio)
            writer.writerow([r, voltage * math.log(b / r) / logratio, field, eps * field,
                             energy * math.log(r / a) / logratio])
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
