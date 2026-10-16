"""Known rectified stereo, +X right/+Y down/+Z forward; SI length and pixels.

Reuses the renderer's NumPy row-batch (N,3) position protocol, not its clip data.
Only forward pinhole projection and exact horizontal-ray intersection are modeled.
"""
from pathlib import Path
import argparse
import json
import numpy as np


def positive(value, name):
    if isinstance(value, (bool, np.bool_)) or np.ndim(value) != 0:
        raise ValueError(f"{name} must be a positive finite scalar")
    result = float(value)
    if not np.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a positive finite scalar")
    return result


def batch(value, width):
    result = np.asarray(value, dtype=float)
    if (result.ndim != 2 or result.shape[1] != width or len(result) == 0
            or not np.isfinite(result).all()):
        raise ValueError(f"expected nonempty finite (N,{width}) array")
    return result


def principal(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (2,) or not np.isfinite(result).all():
        raise ValueError("principal_px must be a finite (2,) array")
    return result


def project(points_m, f_px, principal_px=(0., 0.)):
    """Camera points (N,3) m -> continuous pixels (N,2); no visibility test."""
    points = batch(points_m, 3)
    f = positive(f_px, "f_px")
    c = principal(principal_px)
    if np.any(points[:, 2] <= 0):
        raise ValueError("all points must have Z > 0 m")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        uv = f * (points[:, :2] / points[:, 2:3]) + c
    return batch(uv, 2)


def stereo_project(points_left_m, f_px, baseline_m, principal_px=(0., 0.)):
    points = batch(points_left_m, 3)
    baseline = positive(baseline_m, "baseline_m")
    right = points - np.array([baseline, 0., 0.])
    return project(points, f_px, principal_px), project(right, f_px, principal_px)


def reconstruct(left_px, right_px, f_px, baseline_m, principal_px=(0., 0.)):
    """Exact rectified pairs only; vertical inconsistency is rejected, not fitted.

    The 1e-9 px tolerance is numerical consistency, not a real sensor threshold.
    A wrong pair on the same row can pass every check here.
    """
    left, right = batch(left_px, 2), batch(right_px, 2)
    if left.shape != right.shape:
        raise ValueError("left/right shapes differ")
    f, baseline = positive(f_px, "f_px"), positive(baseline_m, "baseline_m")
    c = principal(principal_px)
    with np.errstate(over="ignore", invalid="ignore"):
        delta = left - right
    if not np.isfinite(delta).all() or np.any(np.abs(delta[:, 1]) > 1e-9):
        raise ValueError("nonrectified vertical pair or nonfinite disparity")
    if np.any(delta[:, 0] <= 0):
        raise ValueError("finite forward depth requires disparity > 0 px")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        z = (f * baseline) / delta[:, 0]
        xyz = np.column_stack(((left - c) * (z / f)[:, None], z))
    if np.any(xyz[:, 2] <= 0):
        raise ValueError("invalid floating-point depth")
    return batch(xyz, 3)


def depth_interval(disparity_px, error_px, f_px, baseline_m):
    d, e = positive(disparity_px, "disparity_px"), positive(error_px, "error_px")
    f, b = positive(f_px, "f_px"), positive(baseline_m, "baseline_m")
    if e >= d:
        raise ValueError("interval reaches zero disparity: no finite upper bound")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        result = np.asarray([f*b/(d+e), f*b/(d-e)], dtype=float)
    if not np.isfinite(result).all() or np.any(result <= 0):
        raise ValueError("invalid floating-point interval")
    return result


def run(config):
    points = batch(config["points_left_m"], 3)
    f, c = positive(config["f_px"], "f_px"), principal(config["principal_px"])
    e = positive(config["disparity_error_px"], "disparity_error_px")
    scale = positive(config["scale_factor"], "scale_factor")
    cases = []
    if not config["baselines_m"]:
        raise ValueError("baselines_m must be nonempty")
    for baseline in config["baselines_m"]:
        b = positive(baseline, "baseline_m")
        left, right = stereo_project(points, f, b, c)
        recovered = reconstruct(left, right, f, b, c)
        disparity = left[:, 0] - right[:, 0]
        scaled_left, scaled_right = stereo_project(scale*points, f, scale*b, c)
        cases.append({
            "baseline_m": b, "left_px": left.tolist(), "right_px": right.tolist(),
            "disparity_px": disparity.tolist(), "recovered_left_m": recovered.tolist(),
            "max_coordinate_error_m": float(np.max(np.abs(recovered-points))),
            "first_depth_interval_m": depth_interval(disparity[0], e, f, b).tolist(),
            "first_sensitivity_m_per_px": float(f*b/disparity[0]**2),
            "scale_projection_error_px": float(max(np.max(np.abs(scaled_left-left)),
                                                      np.max(np.abs(scaled_right-right)))),
        })
    # Synthetic false association, same row: exact fit does not prove identity.
    first_b = cases[0]["baseline_m"]
    false_left = project([[.3, 0., 2.]], f, c)
    _, false_right = stereo_project([[.2, 0., 4.]], f, first_b, c)
    false_point = reconstruct(false_left, false_right, f, first_b, c)
    l2, r2 = stereo_project(false_point, f, first_b, c)
    return {"model": "known parallel rectified pinhole; not camera measurement",
            "f_px": f, "principal_px": c.tolist(), "disparity_error_px": e,
            "points_left_m": points.tolist(), "scale_factor": scale,
            "units": {"xyz": "m", "uv": "px", "sensitivity": "m/px"},
            "cases": cases, "false_pair": {"f_px": f, "baseline_m": first_b,
              "principal_px": c.tolist(),
              "left_source_point_m": [.3, 0., 2.], "right_source_point_m": [.2, 0., 4.],
              "left_px": false_left.tolist(), "right_px": false_right.tolist(),
              "recovered_left_m": false_point.tolist(),
              "max_reprojection_error_px": float(max(np.max(np.abs(l2-false_left)),
                                                      np.max(np.abs(r2-false_right))))}}


def figures(result, directory):
    """Plot the first input point; every coordinate is taken from this run."""
    directory.mkdir(parents=True, exist_ok=True)
    first = result["cases"][0]
    x, y, z = result["points_left_m"][0]
    baseline, focal = first["baseline_m"], result["f_px"]
    principal_x = result["principal_px"][0]
    error = result["disparity_error_px"]
    # Top view has independent X/Z drawing scales, always explicitly labeled.
    min_x, max_x = min(0., x), max(baseline, x)
    span_x = max_x-min_x
    sx, sz, oy = 370/span_x, 300/z, 390.
    ox = 120-min_x*sx
    def point(xv, zv):
        return f"{ox+sx*xv:.3f},{oy-sz*zv:.3f}"
    p, cl, cr = point(x, z), point(0, 0), point(baseline, 0)
    ul, ur = first["left_px"][0][0], first["right_px"][0][0]
    geometry = f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="480" viewBox="0 0 840 480" role="img" aria-labelledby="title desc">
<title id="title">One point and two known camera centers</title>
<desc id="desc">Top view X-Z; Y={y:g} metres is suppressed. CL=(0,0), CR=({baseline:g},0), P=({x:g},{z:g}) metres. X/Z drawing scales differ. f={focal:g} px, cx={principal_x:g} px; left u={ul:g} px, right u={ur:g} px.</desc>
<rect width="840" height="480" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
<text x="25" y="28">Known stereo: P=({x:g}, {y:g}, {z:g}) m, f={focal:g} px</text>
<path d="M {cl} L {p} L {cr}" fill="none" stroke="#156a9b" stroke-width="3"/>
<path d="M {cl} L {cr}" stroke="#b24d17" stroke-width="5"/>
<path d="M 70,390 H 520 M {ox:.3f},420 V 45" fill="none" stroke="#536478"/>
<text x="465" y="418">+X (m)</text><text x="{ox-65:.3f}" y="65">+Z (m)</text>
<circle cx="{ox:.3f}" cy="390" r="6"/><circle cx="{ox+sx*baseline:.3f}" cy="390" r="6"/>
<circle cx="{ox+sx*x:.3f}" cy="90" r="6" fill="#156a9b"/>
<text x="{ox-35:.3f}" y="438">C_L</text><text x="{ox+sx*baseline-5:.3f}" y="438">C_R</text>
<text x="{ox+sx*x+8:.3f}" y="85">P</text>
<text x="100" y="470">B={baseline:g} m (known)</text>
<text x="555" y="125">X/Z={x/z:.6g}</text><text x="555" y="155">(X-B)/Z={(x-baseline)/z:.6g}</text>
<text x="555" y="205">u_L={ul:.6g} px</text><text x="555" y="235">u_R={ur:.6g} px</text>
<text x="555" y="275">d={ul-ur:.6g} px; Z={z:.6g} m</text>
<text x="555" y="325">Top view; +Y into page</text>
<text x="555" y="355">X/Z drawing scales differ</text></g></svg>'''
    (directory/"stereo-rays.svg").write_text(geometry+"\n", encoding="utf-8")
    all_curves = []
    samples = np.linspace(-error, error, 101)
    for case in result["cases"]:
        d, baseline = case["disparity_px"][0], case["baseline_m"]
        exact = focal*baseline/(d+samples)
        tangent = z-case["first_sensitivity_m_per_px"]*samples
        all_curves.append((case, exact, tangent))
    lo = min(float(min(exact.min(), tangent.min())) for _,exact,tangent in all_curves)
    hi = max(float(max(exact.max(), tangent.max())) for _,exact,tangent in all_curves)
    margin = .08*(hi-lo)
    lo, hi = lo-margin, hi+margin
    def sy(value):
        return 355-250*(value-lo)/(hi-lo)
    curves, legends = [], []
    for i, (case, exact, tangent) in enumerate(all_curves):
        color = ["#156a9b", "#b24d17", "#705c98", "#357046"][i%4]
        for values, dash in [(exact, ""), (tangent, ' stroke-dasharray="7 5"')]:
            pts = " ".join(f"{400+250*t/error:.4f},{sy(v):.4f}" for t,v in zip(samples,values))
            curves.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
        legends.append(f'<text x="65" y="{25+23*i}" fill="{color}">B={case["baseline_m"]:g} m: solid exact, dashed first order</text>')
    ticks = "".join(f'<text x="70" y="{sy(v)+5:.4f}">{v:.5g}</text>' for v in [lo+margin,z,hi-margin])
    graph = f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="450" viewBox="0 0 840 450" role="img" aria-labelledby="title desc">
<title id="title">Depth sensitivity for the same point at Z={z:g} metres</title>
<desc id="desc">f={focal:g} pixels. Horizontal axis disparity error from {-error:g} to {error:g} pixel; vertical axis depth in metres. Solid exact inverse; dashed first order. Each legend names the baseline.</desc>
<rect width="840" height="450" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
{''.join(legends)}<path d="M 150,360 H 700 M 150,360 V 80 M 150,{sy(z):.4f} H 700" fill="none" stroke="#536478"/>
<text x="135" y="385">{-error:g}</text><text x="395" y="385">0</text><text x="640" y="385">+{error:g}</text>
<text x="315" y="425">disparity error delta d (px)</text>
<text x="22" y="95">Z (m)</text>{ticks}{''.join(curves)}</g></svg>'''
    (directory/"stereo-sensitivity.svg").write_text(graph+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).parent/"inputs/stereo.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.input.read_text(encoding="utf-8"))
    result = run(config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir/"stereo-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    figures(result, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
