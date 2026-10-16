#!/usr/bin/env python3
"""Exact fixed atlas/tangent/cotangent experiments; not a general manifold proof.

Standard library only. Run with --output-dir /tmp/manifold-atlas-demo.
Charts use the raw (not yet orientation-adjusted) north/south projections.
"""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path


def rational(value):
    if type(value) not in (int, Q):
        raise ValueError("coordinates must be integers or Fractions, not floats/bools")
    return Q(value)


def vector(values, n):
    if not isinstance(values, (tuple, list)) or len(values) != n:
        raise ValueError(f"expected a vector of length {n}")
    return tuple(rational(x) for x in values)


def pole(sign):
    if type(sign) is not int or sign not in (-1, 1):
        raise ValueError("pole sign must be 1 (north) or -1 (south)")
    return sign


def dot(a, b):
    if len(a) != len(b):
        raise ValueError("dot shape mismatch")
    return sum((x * y for x, y in zip(a, b)), Q(0))


def transpose(a):
    return tuple(zip(*a))


def mv(a, v):
    return tuple(dot(row, v) for row in a)


def mm(a, b):
    return tuple(tuple(dot(row, col) for col in transpose(b)) for row in a)


def det2(a):
    return a[0][0] * a[1][1] - a[0][1] * a[1][0]


def inv2(a):
    d = det2(a)
    if d == 0:
        raise ValueError("matrix must be invertible")
    return ((a[1][1] / d, -a[0][1] / d), (-a[1][0] / d, a[0][0] / d))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def inverse_chart(u, sign):
    u = vector(u, 2)
    pole(sign)
    r2 = dot(u, u)
    return (2*u[0]/(1+r2), 2*u[1]/(1+r2), sign*(r2-1)/(1+r2))


def chart(p, sign):
    p = vector(p, 3)
    pole(sign)
    if dot(p, p) != 1:
        raise ValueError("point must lie on the unit sphere")
    denominator = 1-sign*p[2]
    if denominator == 0:
        raise ValueError("excluded projection pole")
    return (p[0]/denominator, p[1]/denominator)


def inversion(u):
    u = vector(u, 2)
    r2 = dot(u, u)
    if r2 == 0:
        raise ValueError("overlap excludes the origin")
    return tuple(x/r2 for x in u)


def inversion_jacobian(u):
    u = vector(u, 2)
    r2 = dot(u, u)
    if r2 == 0:
        raise ValueError("overlap excludes the origin")
    return tuple(tuple(Q(i == j)/r2-2*u[i]*u[j]/r2**2 for j in range(2)) for i in range(2))


def inverse_derivative(u, sign):
    u = vector(u, 2)
    pole(sign)
    d = 1+dot(u, u)
    top = tuple(tuple(2*Q(i == j)/d-4*u[i]*u[j]/d**2 for j in range(2)) for i in range(2))
    return top+(tuple(4*sign*x/d**2 for x in u),)


def projection_derivative(p, sign):
    chart(p, sign)  # validate unit point and domain before using ambient derivative
    x, y, z = vector(p, 3)
    d = 1-sign*z
    return ((1/d, Q(0), sign*x/d**2), (Q(0), 1/d, sign*y/d**2))


def record(u):
    u = vector(u, 2)
    s = inversion(u)
    p = inverse_chart(u, 1)
    assert chart(p, 1) == u and chart(p, -1) == s
    assert inverse_chart(s, -1) == p and inversion(s) == u
    j = inversion_jacobian(u)
    j_back = inversion_jacobian(s)
    identity = ((Q(1), Q(0)), (Q(0), Q(1)))
    assert mm(j_back, j) == identity
    assert det2(j) == -1/dot(u, u)**2
    rn, rs = inverse_derivative(u, 1), inverse_derivative(s, -1)
    # A distinct route: ambient projection derivative composed with inverse embedding.
    assert mm(projection_derivative(p, -1), rn) == j
    assert mm(rs, j) == rn
    vn = (Q(3), Q(-1))
    vs = mv(j, vn)
    ambient = mv(rn, vn)
    assert mv(rs, vs) == ambient and dot(p, ambient) == 0
    gn, gs = mm(transpose(rn), rn), mm(transpose(rs), rs)
    assert gn == tuple(tuple(4*Q(i == k)/(1+dot(u, u))**2 for k in range(2)) for i in range(2))
    assert mm(transpose(j), mm(gs, j)) == gn
    an, ass = rn[2], rs[2]  # dz = final row of inverse embedding derivative
    assert mv(transpose(inv2(j)), an) == ass
    pair = dot(an, vn)
    assert dot(ass, vs) == pair
    gradn, grads = mv(inv2(gn), an), mv(inv2(gs), ass)
    assert mv(j, gradn) == grads
    ambient_grad = tuple(Q(i == 2)-p[2]*p[i] for i in range(3))
    assert mv(rn, gradn) == mv(rs, grads) == ambient_grad
    fieldn, fields = (-u[1], u[0]), (-s[1], s[0])
    assert mv(j, fieldn) == fields
    assert mv(rn, fieldn) == (-p[1], p[0], Q(0))
    raw_n_sign = dot(cross(*transpose(rn)), p)
    raw_s_sign = dot(cross(*transpose(rs)), p)
    assert raw_n_sign < 0 < raw_s_sign
    return {"u": u, "s": s, "point": p, "J": j, "det_J": det2(j),
            "v_north": vn, "v_south": vs, "ambient_velocity": ambient,
            "dz_north": an, "dz_south": ass, "pairing": pair,
            "g_north": gn, "g_south": gs, "grad_north": gradn, "grad_south": grads,
            "ambient_gradient": ambient_grad, "rotation_field_north": fieldn,
            "rotation_field_south": fields,
            "raw_orientation_north": raw_n_sign, "raw_orientation_south": raw_s_sign}


def scaled_line(scale, x, v):
    scale, x, v = map(rational, (scale, x, v))
    if scale == 0:
        raise ValueError("coordinate scale must be nonzero")
    return {"scale": scale, "x": x, "y": scale*x, "v_x": v, "v_y": scale*v,
            "df_x": 2*x, "df_y": 2*x/scale, "g_x": Q(1), "g_y": 1/scale**2,
            "grad_x": 2*x, "grad_y": scale*2*x, "pairing": 2*x*v}


def serial(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


def build_data():
    records = [record((Q(a, 2), Q(b, 2))) for a in range(-4, 5) for b in range(-4, 5) if a or b]
    reference = next(r for r in records if r["u"] == (1, 2))
    wrong_covector = mv(reference["J"], reference["dz_north"])
    wrong_pairing = dot(wrong_covector, reference["v_south"])
    assert wrong_pairing == Q(1, 225) != reference["pairing"]
    wrong_rule = {"u": (1, 2), "wrong_J_times_covector": wrong_covector,
                  "wrong_pairing": wrong_pairing, "correct_pairing": reference["pairing"]}
    origins = []
    for sign in (1, -1):
        p = inverse_chart((0, 0), sign)
        assert chart(p, sign) == (0, 0)
        r = inverse_derivative((0, 0), sign)
        assert mm(projection_derivative(p, sign), r) == ((1, 0), (0, 1))
        origins.append({"chart_pole_sign": sign, "u": (0, 0), "point": p,
                        "rotation_field": (0, 0), "ambient_field": (0, 0, 0)})
    line = [scaled_line(2, 1, 3), scaled_line(3, 1, -2), scaled_line(-2, 1, 3)]
    for row in line:
        assert row["df_x"]*row["v_x"] == row["df_y"]*row["v_y"] == row["pairing"]
        assert row["g_y"]*row["grad_y"] == row["df_y"]
    a = ((Q(1), Q(0)), (Q(0), Q(1)), (Q(-1), Q(2)))
    v, covector = (Q(3), Q(4)), (Q(2), Q(-1), Q(5))
    av, atb = mv(a, v), mv(transpose(a), covector)
    assert av == (3, 4, 5) and atb == (-3, 9)
    assert dot(covector, av) == dot(atb, v) == 27
    rejected = [lambda: inversion((0, 0)), lambda: inversion_jacobian((0, 0)),
                lambda: chart((0, 0, 1), 1), lambda: chart((0, 0, -1), -1),
                lambda: chart((1, 1, 1), 1), lambda: inverse_chart((1.0, 0), 1),
                lambda: inverse_chart((True, 0), 1), lambda: inverse_chart((1, 0), 0),
                lambda: inverse_chart((1, 2, 3), 1), lambda: scaled_line(0, 1, 3)]
    for action in rejected:
        try:
            action()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input accepted")
    return {"status": "PASS", "date": "2026-10-17", "overlap_grid": "u=(a/2,b/2), a,b=-4..4, excluding (0,0)",
            "overlap_records": records, "wrong_covector_rule": wrong_rule,
            "chart_origins": origins, "scaled_line": line,
            "nonsquare_map": {"F": "(x,y)->(x,y,xy)", "point": (2, -1), "A": a,
                              "v": v, "covector": covector, "JVP": av, "VJP_column": atb, "pairing": 27},
            "field_pushforward_failure": {"F": "t^2", "source_points": (1, -1),
                                           "same_target": 1, "pushed_velocities": (2, -2),
                                           "pullback_dy": "2t dt (valid also at t=0)"},
            "rejected_inputs": len(rejected),
            "limits": "Finite rational checks only. General atlas/tangent/bundle proofs are in lessons; no global trivialization or Stokes claim. Old labs not run."}


def frame(title, desc, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}">',
            f'<title>{title}</title><desc>{desc}</desc>',
            f'<rect width="1000" height="{height}" fill="#f8fafc"/>',
            '<g font-family="sans-serif" fill="#172b4d">', f'<text x="30" y="40" font-size="23">{title}</text>']


def write_figures(data, folder):
    folder.mkdir(parents=True, exist_ok=True)
    row = next(r for r in data["overlap_records"] if r["u"] == (2, 0))
    # Meridian Y=0 is shown as an X-Z section; both coordinate planes meet at Z=0.
    def screen(x, z):
        return (220+100*float(x), 200-100*float(z))
    p = screen(row["point"][0], row["point"][2])
    un = screen(row["u"][0], 0)
    ss = screen(row["s"][0], 0)
    j_fixed = next(r["J"] for r in data["overlap_records"] if r["u"] == (1, 0))
    assert j_fixed == ((-1, 0), (0, 1))
    svg = frame("Same sphere point, two coordinate reports",
                "Left: Y=0 meridian, P=(4/5,0,3/5), north projection u=2 and south projection s=1/2. Right: inversion at u=(1,0), radial derivative -1 and transverse derivative +1.", 440)
    svg += ['<circle cx="220" cy="200" r="100" fill="#e5eff9" stroke="#527598" stroke-width="2"/>',
            '<line x1="80" x2="455" y1="200" y2="200" stroke="#8494a7"/>',
            '<text x="85" y="224" font-size="15">Z=0</text>',
            f'<line x1="220" y1="100" x2="{un[0]}" y2="{un[1]}" stroke="#1f64a0" stroke-width="2"/>',
            f'<line x1="220" y1="300" x2="{p[0]}" y2="{p[1]}" stroke="#20826b" stroke-width="2"/>']
    for x, y, label, dx, dy in [(220,100,'N',-18,-12),(220,300,'S',-18,25),(*p,'P',12,-5),(*un,'u=2',-12,30),(*ss,'s=1/2',-8,49)]:
        svg += [f'<circle cx="{x}" cy="{y}" r="4" fill="#172b4d"/>',
                f'<text x="{x+dx}" y="{y+dy}" font-size="17">{label}</text>']
    svg += ['<text x="55" y="355" font-size="16">Section Y=0; projection coordinates live at Z=0.</text>',
            '<line x1="510" x2="510" y1="75" y2="365" stroke="#c3ceda"/>',
            '<text x="555" y="100" font-size="18">At u=(1,0), I(u)=u</text>',
            f'<text x="555" y="130" font-size="17">DI = diag({j_fixed[0][0]}, {j_fixed[1][1]})</text>',
            '<line x1="670" x2="825" y1="235" y2="235" stroke="#8494a7"/>',
            '<line x1="745" x2="745" y1="155" y2="315" stroke="#8494a7"/>',
            '<circle cx="745" cy="235" r="5" fill="#172b4d"/>',
            '<path d="M745 235 L685 235 l10 -6 m-10 6 l10 6" fill="none" stroke="#bc4553" stroke-width="3"/>',
            '<path d="M745 235 L745 175 l-6 10 m6 -10 l6 10" fill="none" stroke="#20826b" stroke-width="3"/>',
            '<text x="555" y="287" font-size="16">radial direction reverses</text>',
            '<text x="775" y="181" font-size="16">transverse</text>',
            '<text x="775" y="203" font-size="16">keeps sign</text>',
            '<text x="555" y="345" font-size="17">det(DI) &lt; 0: raw charts are not oriented.</text>',
            '<text x="30" y="412" font-size="16">The origin is valid in each single chart, but is excluded from their overlap transition.</text>', '</g></svg>']
    (folder/'sphere-atlas.svg').write_text('\n'.join(svg)+'\n')
    row = data['scaled_line'][0]
    svg = frame("Direction and readout transform differently",
                "Same real line with y=2x, f=x squared at x=1. v changes 3 to 6, df changes 2 to 1, pairing stays 6. Fixed metric dx squared has y coefficient 1/4, gradient changes 2 to 4.", 350)
    headings = ['coordinate', 'direction v', 'covector df', 'metric g', 'gradient']
    positions = [35, 225, 425, 625, 810]
    for x, label in zip(positions, headings):
        svg.append(f'<text x="{x}" y="95" font-size="17">{label}</text>')
    for y, values in [(145, [f'x={row["x"]}',row['v_x'],row['df_x'],row['g_x'],row['grad_x']]),
                      (215, [f'y={row["y"]}',row['v_y'],row['df_y'],row['g_y'],row['grad_y']])]:
        svg.append(f'<rect x="25" y="{y-31}" width="940" height="49" rx="7" fill="#e5eff9"/>')
        for x, value in zip(positions, values):
            svg.append(f'<text x="{x}" y="{y}" font-size="24">{value}</text>')
    svg += [f'<text x="35" y="278" font-size="20">Pairing: 3 x 2 = 6 x 1 = {row["pairing"]}</text>',
            '<text x="35" y="318" font-size="17">Setting g_y=1 would change the metric. A covector array is not already the metric gradient.</text>', '</g></svg>']
    (folder/'tangent-cotangent.svg').write_text('\n'.join(svg)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    data = build_data()
    output = args.output_dir/'实践结果'
    output.mkdir(parents=True, exist_ok=True)
    (output/'manifold-atlas-20261017.json').write_text(json.dumps(serial(data), ensure_ascii=False, indent=2)+'\n')
    write_figures(data, args.output_dir/'assets')
    print(json.dumps({'status':data['status'], 'overlap_points':len(data['overlap_records']),
                      'chart_origins':len(data['chart_origins']), 'line_cases':len(data['scaled_line']),
                      'rejected_inputs':data['rejected_inputs']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
