"""Known calibrated two-view geometry; perpendicular-line least squares.

P_R = R_RL @ (P_L - C_R_in_L). Column theory; NumPy (N,3) row batches.
Uses the published stereo_lab.project and its input protocol. No image matching,
camera calibration, pose estimation or maximum-likelihood triangulation claim.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import stereo_lab as stereo

MIN_BASELINE_M = 1e-12
MIN_SIN_PARALLAX = 1e-6


def pose(rotation, center_m):
    r, c = np.asarray(rotation, dtype=float), np.asarray(center_m, dtype=float)
    if r.shape != (3, 3) or c.shape != (3,) or not np.isfinite(r).all() or not np.isfinite(c).all():
        raise ValueError("expected finite R (3,3), C (3,)")
    if not np.allclose(r.T@r, np.eye(3), atol=1e-10, rtol=0) or abs(np.linalg.det(r)-1) > 1e-10:
        raise ValueError("R must be a proper rotation")
    return r, c


def yaw(angle_rad):
    angle = float(angle_rad)
    if not np.isfinite(angle):
        raise ValueError("yaw must be finite radians")
    cs, sn = np.cos(angle), np.sin(angle)
    return np.array([[cs, 0., sn], [0., 1., 0.], [-sn, 0., cs]])


def skew(vector):
    a = np.asarray(vector, dtype=float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError("cross-product vector must be finite (3,)")
    x, y, z = a
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def intrinsic(f_px, c_px):
    f, c = stereo.positive(f_px, "f_px"), stereo.principal(c_px)
    return np.array([[f, 0., c[0]], [0., f, c[1]], [0., 0., 1.]])


def normalized(uv_px, f_px, c_px):
    uv = stereo.batch(uv_px, 2)
    f, c = stereo.positive(f_px, "f_px"), stereo.principal(c_px)
    return stereo.batch(np.column_stack(((uv-c)/f, np.ones(len(uv)))), 3)


def pair_project(points_left_m, rotation, center_m, fl, cl, fr, cr):
    points = stereo.batch(points_left_m, 3)
    r, c = pose(rotation, center_m)
    return stereo.project(points, fl, cl), stereo.project((points-c)@r.T, fr, cr)


def epipolar(rotation, center_m, fl, cl, fr, cr):
    r, c = pose(rotation, center_m)
    translation = -r@c
    e = skew(translation)@r
    f = np.linalg.solve(intrinsic(fr, cr).T, e)@np.linalg.inv(intrinsic(fl, cl))
    return e, f


def right_line_distance(left_px, right_px, fundamental):
    """One-sided point-to-epipolar-line distance in right-image pixels."""
    left, right = stereo.batch(left_px, 2), stereo.batch(right_px, 2)
    f = np.asarray(fundamental, dtype=float)
    if left.shape != right.shape or f.shape != (3, 3) or not np.isfinite(f).all():
        raise ValueError("inconsistent pairs or invalid F")
    # Homogeneous F scale is arbitrary; rescale before the zero-normal policy.
    size = np.max(np.abs(f))
    if size == 0:
        raise ValueError("zero F does not define an epipolar line")
    lines = np.column_stack((left, np.ones(len(left))))@(f/size).T
    norms = np.linalg.norm(lines[:, :2], axis=1)
    if np.any(norms <= 1e-12):
        raise ValueError("epipolar line has zero or numerically tiny normal")
    right_h = np.column_stack((right, np.ones(len(right))))
    return np.abs(np.sum(right_h*lines, axis=1))/norms


def triangulate(left_px, right_px, rotation, center_m, fl, cl, fr, cr):
    """Minimize sum of squared perpendicular distances to two infinite lines.

    Returns a finite, forward point or rejects the entire input batch. Numerical
    baseline/parallax floors are declared policies, not camera reliability bounds.
    """
    left, right = stereo.batch(left_px, 2), stereo.batch(right_px, 2)
    r, c = pose(rotation, center_m)
    if left.shape != right.shape or np.linalg.norm(c) <= MIN_BASELINE_M:
        raise ValueError("shape mismatch or zero/tiny metric baseline")
    a, b = normalized(left, fl, cl), normalized(right, fr, cr)@r
    a, b = a/np.linalg.norm(a, axis=1)[:, None], b/np.linalg.norm(b, axis=1)[:, None]
    sins = np.linalg.norm(np.cross(a, b), axis=1)
    if np.any(sins < MIN_SIN_PARALLAX):
        raise ValueError("rays parallel or below numerical parallax policy")
    points, gaps, conditions = [], [], []
    for ai, bi in zip(a, b):
        ql, qr = np.eye(3)-np.outer(ai, ai), np.eye(3)-np.outer(bi, bi)
        matrix = np.vstack((ql, qr))  # (6,3), dimensionless
        rhs = np.r_[np.zeros(3), qr@c]  # (6,), metres
        point, _, rank, sv = np.linalg.lstsq(matrix, rhs, rcond=None)
        if rank != 3 or not np.isfinite(point).all():
            raise ValueError("rank-deficient or nonfinite reconstruction")
        ray_l, ray_r = np.dot(ai, point), np.dot(bi, point-c)
        if point[2] <= 0 or (r@(point-c))[2] <= 0 or ray_l <= 0 or ray_r <= 0:
            raise ValueError("triangulated point is not forward in both cameras")
        points.append(point)
        gaps.append(np.linalg.norm(ray_l*ai-(c+ray_r*bi)))
        conditions.append(sv[0]/sv[-1])
    points = stereo.batch(points, 3)
    projected_l, projected_r = pair_project(points, r, c, fl, cl, fr, cr)
    return {"points_left_m": points.tolist(), "ray_gap_m": list(map(float, gaps)),
            "sin_parallax": sins.tolist(), "design_condition": list(map(float, conditions)),
            "reprojection_left_px": np.linalg.norm(projected_l-left, axis=1).tolist(),
            "reprojection_right_px": np.linalg.norm(projected_r-right, axis=1).tolist()}


def run(config):
    points = stereo.batch(config["points_left_m"], 3)
    r = yaw(config["yaw_rad"])
    _, center = pose(r, config["center_right_in_left_m"])
    fl, cl = config["f_left_px"], config["c_left_px"]
    fr, cr = config["f_right_px"], config["c_right_px"]
    intrinsic(fl, cl), intrinsic(fr, cr)
    delta = stereo.principal(config["right_pixel_error_px"])
    scale = stereo.positive(config["scale_factor"], "scale_factor")
    factors = config["baseline_factors"]
    if not factors:
        raise ValueError("baseline_factors must be nonempty")
    cases = []
    for factor in factors:
        factor = stereo.positive(factor, "baseline_factor")
        c = center*factor
        left, right = pair_project(points, r, c, fl, cl, fr, cr)
        e, f = epipolar(r, c, fl, cl, fr, cr)
        clean = triangulate(left, right, r, c, fl, cl, fr, cr)
        noisy = triangulate(left, right+delta, r, c, fl, cl, fr, cr)
        for out in (clean, noisy):
            out["coordinate_error_m"] = np.linalg.norm(np.asarray(out["points_left_m"])-points, axis=1).tolist()
        xs_l, xs_r = normalized(left, fl, cl), normalized(right, fr, cr)
        scaled_l, scaled_r = pair_project(scale*points, r, scale*c, fl, cl, fr, cr)
        cases.append({"factor": factor, "center_right_in_left_m": c.tolist(),
          "baseline_m": float(np.linalg.norm(c)), "translation_RL_m": (-r@c).tolist(),
          "E": e.tolist(), "F": f.tolist(), "left_px": left.tolist(), "right_px": right.tolist(),
          "clean_epipolar_identity_m": np.sum(xs_r*(xs_l@e.T), axis=1).tolist(),
          "noisy_right_px": (right+delta).tolist(),
          "noisy_right_line_distance_px": right_line_distance(left, right+delta, f).tolist(),
          "scale_projection_error_px": float(max(np.max(np.abs(scaled_l-left)), np.max(np.abs(scaled_r-right)))),
          "clean": clean, "noisy": noisy})
    c = np.asarray(cases[0]["center_right_in_left_m"])
    fake = .6*points[:1]
    other = c+1.7*(fake-c)
    false_left, _ = pair_project(points[:1], r, c, fl, cl, fr, cr)
    _, false_right = pair_project(other, r, c, fl, cl, fr, cr)
    false_result = triangulate(false_left, false_right, r, c, fl, cl, fr, cr)
    pure_l, pure_r = pair_project(points, r, np.zeros(3), fl, cl, fr, cr)
    failures = {}
    for label, c0, right0 in [("pure_rotation", np.zeros(3), pure_r),
                              ("tiny_baseline", 1e-9*c, pair_project(points,r,1e-9*c,fl,cl,fr,cr)[1])]:
        try:
            triangulate(pure_l, right0, r, c0, fl, cl, fr, cr)
        except ValueError as error:
            failures[label] = str(error)
        else:
            raise AssertionError(f"expected {label} rejection")
    return {"model": "known calibrated pose; perpendicular-line LS, not pixel MLE",
      "config": config, "R_RL": r.tolist(), "cases": cases,
      "false_pair": {"left_source_point_m": points[0].tolist(), "right_source_point_m": other[0].tolist(),
                     "expected_false_point_m": fake[0].tolist(), "left_px": false_left.tolist(),
                     "right_px": false_right.tolist(), "reconstruction": false_result},
      "degenerate_rejections": failures,
      "pure_rotation_E": epipolar(r,np.zeros(3),fl,cl,fr,cr)[0].tolist()}


def figures(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    case = result["cases"][0]
    left, right = np.asarray(case["left_px"]), np.asarray(case["right_px"])
    f = np.asarray(case["F"])
    xmin, xmax = right[:,0].min()-40, right[:,0].max()+40
    ymin, ymax = right[:,1].min()-30, right[:,1].max()+30
    def xy(u, v):
        return 100+550*(u-xmin)/(xmax-xmin), 100+250*(v-ymin)/(ymax-ymin)
    colors = ["#176a9b", "#b04e19", "#6e5494", "#267242"]
    lines = []
    for i, (pl, pr) in enumerate(zip(left,right)):
        line = f@np.r_[pl,1.]
        # Clip the infinite line to the actual displayed pixel-coordinate box.
        intersections = []
        if abs(line[1]) > 1e-20:
            intersections.extend((u,-(line[0]*u+line[2])/line[1]) for u in [xmin,xmax])
        if abs(line[0]) > 1e-20:
            intersections.extend((-(line[1]*v+line[2])/line[0],v) for v in [ymin,ymax])
        pts = [(u,v) for u,v in intersections if xmin-1e-8<=u<=xmax+1e-8 and ymin-1e-8<=v<=ymax+1e-8]
        if len(pts)<2:
            raise ValueError("displayed epipolar line misses right point")
        x0,y0=xy(*pts[0]); x1,y1=xy(*pts[1]); xp,yp=xy(*pr)
        color=colors[i%4]
        lines.append(f'<path d="M{x0:.5f},{y0:.5f} L{x1:.5f},{y1:.5f}" stroke="{color}" stroke-width="2" fill="none"/><circle cx="{xp:.5f}" cy="{yp:.5f}" r="5" fill="{color}"/><text x="{xp+8:.5f}" y="{yp-7:.5f}" fill="{color}">P{i}</text>')
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="460" viewBox="0 0 840 460" role="img" aria-labelledby="title desc">
<title id="title">Right-image epipolar lines from four left pixels</title><desc id="desc">Same known pose and four points as JSON. Each line F pLeft contains the corresponding right pixel. Pixel axes have separately chosen drawing scales, v increases downwards. Color plus point ID identifies each pair.</desc>
<rect width="840" height="460" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
<text x="30" y="28">Known pose: right-image lines l_R=F p_L; points from same input</text>
<text x="30" y="58">u in [{xmin:.3f}, {xmax:.3f}] px; v in [{ymin:.3f}, {ymax:.3f}] px</text>
<path d="M100,80 V350 H690" fill="none" stroke="#536478"/>
<text x="690" y="375">+u_R (px)</text><text x="10" y="95">v_R (px)</text>
{''.join(lines)}<text x="100" y="410">Independent axis drawing scales; v increases downward.</text>
<text x="100" y="440">Lines constrain candidates; they do not establish correspondence.</text></g></svg>'''
    (directory/"multiview-epilines.svg").write_text(svg+"\n",encoding="utf-8")
    baselines=np.array([c["baseline_m"] for c in result["cases"]])
    errors=np.array([c["noisy"]["coordinate_error_m"] for c in result["cases"]])
    maximum=max(float(errors.max()),1e-12)
    curves=[]
    for i in range(errors.shape[1]):
        pts=" ".join(f"{150+500*b/baselines.max():.5f},{350-230*e/maximum:.5f}" for b,e in zip(baselines,errors[:,i]))
        dots="".join(f'<circle cx="{150+500*b/baselines.max():.5f}" cy="{350-230*e/maximum:.5f}" r="4"/>' for b,e in zip(baselines,errors[:,i]))
        curves.append(f'<g fill="{colors[i%4]}" stroke="{colors[i%4]}"><polyline points="{pts}" fill="none" stroke-width="2"/>{dots}<text x="{80+175*i}" y="70" stroke="none">P{i}</text></g>')
    delta=result["config"]["right_pixel_error_px"]
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="460" viewBox="0 0 840 460" role="img" aria-labelledby="title desc">
<title id="title">Coordinate error for fixed right-image perturbation and changed baseline</title>
<desc id="desc">Four point IDs match the epipolar diagram. Horizontal axis known camera-center distance in metres; vertical axis Euclidean reconstruction error in metres. Discrete cases only; segments connect sampled inputs and are not a universal law. Right pixel perturbation is {delta} pixels.</desc>
<rect width="840" height="460" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
<text x="25" y="28">Fixed right-pixel error {delta} px; same rotation, scaled camera center</text>
<path d="M150,100 V350 H700" fill="none" stroke="#536478"/><text x="35" y="105">error (m)</text>
<text x="55" y="125">{maximum:.6g}</text><text x="125" y="355">0</text>
<text x="140" y="380">0</text><text x="625" y="380">{baselines.max():.6g}</text>
{''.join(curves)}<text x="300" y="415">known baseline norm (m)</text><text x="85" y="445">Segments join finite test cases; no general error bound is asserted.</text></g></svg>'''
    (directory/"multiview-noise.svg").write_text(svg+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path(__file__).parent/"inputs/multiview.json")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text(encoding="utf-8")))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"multiview-results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    figures(result,args.output_dir)
    print(json.dumps({"clean_max_m":max(max(c["clean"]["coordinate_error_m"]) for c in result["cases"]),
      "degenerate_rejections":result["degenerate_rejections"]},allow_nan=False))


if __name__=="__main__":
    main()
