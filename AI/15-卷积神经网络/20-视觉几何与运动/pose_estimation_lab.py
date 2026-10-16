"""Known intrinsics + correspondences -> E and relative pose up to scale.

Teaching normalized eight-point solver and finite seeded RANSAC. Uses the frozen
multiview projection/triangulation API. No image matching, calibration, five-point
solver, bundle adjustment, or universal degeneracy-detection claim.
"""
from pathlib import Path
import argparse
import json
import math
import numpy as np
import multiview_lab as geometry
import stereo_lab as stereo

MIN_DESIGN_RATIO = 1e-6
MIN_MEDIAN_SIN = 1e-3


def pairs(left, right, minimum=8):
    l, r = stereo.batch(left, 2), stereo.batch(right, 2)
    if l.shape != r.shape or len(l) < minimum:
        raise ValueError("need equal finite (N,2) arrays and enough pairs")
    return l, r


def hartley(points):
    p = stereo.batch(points, 3)
    if not np.all(p[:, 2] == 1):
        raise ValueError("Hartley input must have homogeneous last coordinate one")
    mean = p[:, :2].mean(axis=0)
    rms = np.sqrt(np.mean(np.sum((p[:, :2]-mean)**2, axis=1)))
    if not np.isfinite(rms) or rms <= 1e-12:
        raise ValueError("zero or tiny image spread")
    scale = np.sqrt(2)/rms
    transform = np.array([[scale, 0., -scale*mean[0]], [0., scale, -scale*mean[1]], [0., 0., 1.]])
    return p@transform.T, transform


def project_essential(matrix):
    e = np.asarray(matrix, dtype=float)
    if e.shape != (3, 3) or not np.isfinite(e).all() or np.linalg.norm(e) <= 1e-14:
        raise ValueError("expected nonzero finite (3,3) E")
    u, sv, vh = np.linalg.svd(e)
    equal = (sv[0]+sv[1])/2
    projected = (u*np.array([equal, equal, 0.]))@vh
    return projected/np.linalg.norm(projected)*np.sqrt(2), sv


def estimate_essential(left, right, fl, cl, fr, cr):
    l, r = pairs(left, right)
    xl = geometry.normalized(l, fl, cl)
    xr = geometry.normalized(r, fr, cr)
    nl, tl = hartley(xl)
    nr, tr = hartley(xr)
    design = np.einsum('ni,nj->nij', nr, nl).reshape(len(l), 9)
    # Full Vh is crucial for exactly eight rows: the ninth vector spans the null.
    _, sv, vh = np.linalg.svd(design, full_matrices=True)
    ratio = sv[7]/sv[0]
    if not np.isfinite(ratio) or ratio < MIN_DESIGN_RATIO:
        raise ValueError("eight-point design is rank deficient or below conditioning policy")
    raw = tr.T@vh[-1].reshape(3, 3)@tl
    e, raw_sv = project_essential(raw)  # enforce E only after undoing Hartley transforms
    return e, {"design_singular_values": sv.tolist(), "sigma8_over_sigma1": float(ratio),
               "raw_E_singular_values": raw_sv.tolist(), "E_singular_values": np.linalg.svd(e,compute_uv=False).tolist()}


def fundamental(e, fl, cl, fr, cr):
    return np.linalg.solve(geometry.intrinsic(fr, cr).T, e)@np.linalg.inv(geometry.intrinsic(fl, cl))


def sampson_px(left, right, e, fl, cl, fr, cr):
    l, r = pairs(left, right, minimum=1)
    f = fundamental(e, fl, cl, fr, cr)
    size = np.max(np.abs(f))
    if not np.isfinite(size) or size == 0:
        raise ValueError("invalid F")
    f = f/size
    lh, rh = np.column_stack((l,np.ones(len(l)))), np.column_stack((r,np.ones(len(r))))
    flines, rlines = lh@f.T, rh@f
    denominator = np.sum(flines[:, :2]**2+rlines[:, :2]**2, axis=1)
    if np.any(denominator <= 1e-24):
        raise ValueError("zero or tiny Sampson gradient")
    return np.abs(np.sum(rh*flines,axis=1))/np.sqrt(denominator)


def decompose(e):
    e, _ = project_essential(e)
    u, _, vh = np.linalg.svd(e)
    if np.linalg.det(u) < 0: u[:, -1] *= -1
    if np.linalg.det(vh) < 0: vh[-1] *= -1
    w = np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    rotations = [u@w@vh, u@w.T@vh]
    t = u[:,2]
    return [(r, sign*t) for r in rotations for sign in [1., -1.]]


def choose_pose(e, left, right, fl, cl, fr, cr):
    l,r = pairs(left,right)
    candidates=[]
    for rotation, translation in decompose(e):
        center = -rotation.T@translation
        ids, points, sins, errors = [], [], [], []
        for i in range(len(l)):
            try:
                out=geometry.triangulate(l[i:i+1],r[i:i+1],rotation,center,fl,cl,fr,cr)
            except ValueError:
                continue
            ids.append(i); points.append(out['points_left_m'][0])
            sins.append(out['sin_parallax'][0])
            errors.append([out['reprojection_left_px'][0],out['reprojection_right_px'][0]])
        candidates.append({"R_RL":rotation.tolist(),"t_unit":translation.tolist(),
          "C_baseline_units":center.tolist(),"positive_count":len(ids),"positive_local_ids":ids,
          "points_baseline_units":points,"sin_parallax":sins,"reprojection_px":errors})
    counts=[c['positive_count'] for c in candidates]
    order=sorted(range(4),key=lambda i:-counts[i])
    best=candidates[order[0]]
    if counts[order[0]] == counts[order[1]] or counts[order[0]] < max(8,math.ceil(.75*len(l))):
        raise ValueError("ambiguous or insufficient forward-point consensus")
    if np.median(best['sin_parallax']) < MIN_MEDIAN_SIN:
        raise ValueError("median parallax below pose policy")
    return {"candidate_positive_counts":counts,"selected_candidate":order[0],**best}


def robust_essential(left,right,fl,cl,fr,cr,seed,trials,threshold_px):
    l,r=pairs(left,right)
    threshold=stereo.positive(threshold_px,'threshold_px')
    if isinstance(trials,bool) or not isinstance(trials,int) or trials <= 0:
        raise ValueError("trials must be a positive integer")
    if isinstance(seed,bool) or not isinstance(seed,int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    rng=np.random.default_rng(seed)
    best_key=None; best_mask=None; trace=[]
    for trial in range(trials):
        sample=np.sort(rng.choice(len(l),8,replace=False))
        try:
            e,_=estimate_essential(l[sample],r[sample],fl,cl,fr,cr)
            distance=sampson_px(l,r,e,fl,cl,fr,cr)
        except ValueError as error:
            trace.append({"trial":trial,"sample":sample.tolist(),"rejected":str(error)})
            continue
        mask=distance <= threshold
        count=int(mask.sum())
        cost=float(np.minimum(distance**2,threshold**2).sum())
        key=(count,-cost)  # Equal key keeps the earliest trial.
        trace.append({"trial":trial,"sample":sample.tolist(),"consensus_count":count,"truncated_cost_px2":cost})
        if best_key is None or key>best_key:
            best_key,best_mask,best_trial=key,mask,trial
    if best_mask is None or int(best_mask.sum())<8:
        raise ValueError("finite RANSAC found no consensus of eight")
    # Exactly one refit; final membership is recomputed, with no hidden iteration.
    e,diagnostics=estimate_essential(l[best_mask],r[best_mask],fl,cl,fr,cr)
    distance=sampson_px(l,r,e,fl,cl,fr,cr)
    final=distance<=threshold
    if int(final.sum())<8: raise ValueError("refit lost consensus")
    return e,final,{"best_trial":best_trial,"initial_inlier_ids":np.flatnonzero(best_mask).tolist(),
      "final_inlier_ids":np.flatnonzero(final).tolist(),"sampson_px":distance.tolist(),
      "fit":diagnostics,"trace":trace}


def angle_between(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return float(np.arctan2(np.linalg.norm(np.cross(a,b)),a@b))


def evaluate(e,pose,true_r,true_center,true_points,input_ids):
    true_t=-true_r@true_center
    unit_t=true_t/np.linalg.norm(true_t)
    rotation=np.asarray(pose['R_RL']); translation=np.asarray(pose['t_unit'])
    diff=rotation@true_r.T
    antisym=np.array([diff[2,1]-diff[1,2],diff[0,2]-diff[2,0],diff[1,0]-diff[0,1]])/2
    true_e=geometry.skew(unit_t)@true_r
    matched_ids=np.asarray(input_ids)[pose['positive_local_ids']]
    errors=np.linalg.norm(np.asarray(pose['points_baseline_units'])-true_points[matched_ids]/np.linalg.norm(true_center),axis=1)
    return {"rotation_error_rad":float(np.arctan2(np.linalg.norm(antisym),(np.trace(diff)-1)/2)),
      "translation_direction_error_rad":angle_between(translation,unit_t),
      "E_error_up_to_sign":float(min(np.linalg.norm(e-true_e),np.linalg.norm(e+true_e))),
      "positive_input_ids":matched_ids.tolist(), "point_error_baseline_units":errors.tolist()}


def run(config):
    points=stereo.batch(config['points_left_m'],3)
    true_r=geometry.yaw(config['yaw_rad']); _,true_c=geometry.pose(true_r,config['center_right_in_left_m'])
    k=(config['f_left_px'],config['c_left_px'],config['f_right_px'],config['c_right_px'])
    left,right=geometry.pair_project(points,true_r,true_c,*k)
    sources=np.asarray(config['right_source_indices'])
    if sources.shape!=(len(points),) or sources.dtype.kind not in 'iu' or np.any(sources<0) or np.any(sources>=len(points)):
        raise ValueError("right sources must be one valid integer ID per point")
    noise=stereo.batch(config['right_noise_px'],2)
    if noise.shape!=right.shape:raise ValueError("noise shape mismatch")
    observed=right[sources]+noise
    clean_e,clean_fit=estimate_essential(left,right,*k)
    clean_pose=choose_pose(clean_e,left,right,*k)
    robust_e,mask,robust_info=robust_essential(left,observed,*k,config['ransac_seed'],config['ransac_trials'],config['sampson_threshold_px'])
    robust_pose=choose_pose(robust_e,left[mask],observed[mask],*k)
    plain_e,plain_fit=estimate_essential(left,observed,*k)
    plain={"E":plain_e.tolist(),"fit":plain_fit,"sampson_px":sampson_px(left,observed,plain_e,*k).tolist()}
    try:
        plain_pose=choose_pose(plain_e,left,observed,*k)
        plain.update({"pose":plain_pose,"truth_comparison":evaluate(plain_e,plain_pose,true_r,true_c,points,np.arange(len(points)))})
    except ValueError as error:plain['pose_rejected']=str(error)
    failures={}
    for label,scene,center in [('plane',np.column_stack((points[:,:2],np.full(len(points),3.))),true_c),
                                ('near_plane',np.column_stack((points[:,:2],3+1e-9*points[:,2])),true_c),
                                ('pure_rotation',points,np.zeros(3))]:
        dl,dr=geometry.pair_project(scene,true_r,center,*k)
        try:estimate_essential(dl,dr,*k)
        except ValueError as error:failures[label]=str(error)
        else:raise AssertionError(f"expected {label} rank-policy rejection")
    # Coherent wrong identities can satisfy one geometry for every observation.
    fake=.6*points
    wrong_sources=true_c+1.7*(fake-true_c)
    _,wrong_right=geometry.pair_project(wrong_sources,true_r,true_c,*k)
    wrong_e,wrong_fit=estimate_essential(left,wrong_right,*k)
    wrong_pose=choose_pose(wrong_e,left,wrong_right,*k)
    identity=sources==np.arange(len(points))
    return {"model":"known K, simulated correspondences; unit-baseline pose only",
      "config":config,"left_px":left.tolist(),"clean_right_px":right.tolist(),"observed_right_px":observed.tolist(),
      "clean":{"E":clean_e.tolist(),"fit":clean_fit,"pose":clean_pose,"truth_comparison":evaluate(clean_e,clean_pose,true_r,true_c,points,np.arange(len(points)))},
      "plain_all_pairs":plain,"robust":{"E":robust_e.tolist(),"fit_and_sampling":robust_info,"pose":robust_pose,
        "truth_comparison":evaluate(robust_e,robust_pose,true_r,true_c,points,np.flatnonzero(mask)),
        "identity_evaluation_only":{"tp":int(np.sum(mask&identity)),"fp":int(np.sum(mask&~identity)),
          "fn":int(np.sum(~mask&identity)),"tn":int(np.sum(~mask&~identity))}},
      "degenerate_rejections":failures,
      "coherent_wrong_pairs":{"right_source_points_m":wrong_sources.tolist(),"right_px":wrong_right.tolist(),
        "E":wrong_e.tolist(),"fit":wrong_fit,"pose":wrong_pose,
        "sampson_px":sampson_px(left,wrong_right,wrong_e,*k).tolist(),
        "expected_fake_points_baseline_units":(fake/np.linalg.norm(true_c)).tolist()}}


def figures(result,directory):
    directory.mkdir(parents=True,exist_ok=True)
    robust=np.asarray(result['robust']['fit_and_sampling']['sampson_px'])
    plain=np.asarray(result['plain_all_pairs']['sampson_px'])
    threshold=result['config']['sampson_threshold_px']
    floor=1e-4
    low,high=-4,max(0.,float(np.ceil(np.log10(max(plain.max(),robust.max(),threshold)))))
    def xx(i):return 100+620*i/max(1,len(robust)-1)
    def yy(value):return 350-240*(np.log10(max(float(value),floor))-low)/(high-low)
    dots=[]
    sources=result['config']['right_source_indices']
    for i,(a,b) in enumerate(zip(robust,plain)):
        dots.append(f'<circle cx="{xx(i):.5f}" cy="{yy(a):.5f}" r="4" fill="#176a9b"/>')
        dots.append(f'<path d="M{xx(i)-4:.5f},{yy(b)-4:.5f} l8,8 m-8,0 l8,-8" stroke="#b04e19" stroke-width="2"/>')
        if sources[i]!=i:
            dots.append(f'<rect x="{xx(i)-5:.5f}" y="365" width="10" height="10" fill="none" stroke="#172638"/>')
    ticks=''.join(f'<text x="40" y="{yy(10**v)+5:.5f}">1e{v}</text>' for v in range(int(low),int(high)+1,2))
    labels=''.join(f'<text x="{xx(i)-6:.5f}" y="398">{i}</text>' for i in range(0,len(robust),3))
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="475" viewBox="0 0 840 475" role="img" aria-labelledby="title desc">
<title id="title">Finite correspondence scores before and after robust fitting</title>
<desc id="desc">Horizontal axis original pair ID. Vertical log axis square-root Sampson distance in pixels, display floor 1e-4. Circles robust, crosses all-pair fit. Dashed threshold {threshold:g} px. Open squares below axis mark simulated wrong identity for evaluation only; the estimator does not read these identities.</desc>
<rect width="840" height="475" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
<text x="25" y="27">Square-root Sampson distance (px); same raw correspondence input</text>
<text x="65" y="57" fill="#176a9b">circles: robust refit</text><text x="380" y="57" fill="#b04e19">crosses: all-pair eight-point fit</text>
<path d="M100,85 V350 H750" fill="none" stroke="#536478"/>{ticks}{labels}
<path d="M100,{yy(threshold):.5f} H750" stroke="#536478" stroke-dasharray="7 5"/><text x="570" y="{yy(threshold)-8:.5f}">threshold {threshold:g} px</text>
{''.join(dots)}<text x="350" y="425">original pair ID</text><text x="65" y="452">Open squares: wrong identity (truth for evaluation only); display floor 1e-4 px.</text></g></svg>'''
    (directory/'pose-consensus.svg').write_text(svg+'\n',encoding='utf-8')
    truth=np.asarray(result['config']['points_left_m'])
    baseline=np.linalg.norm(result['config']['center_right_in_left_m'])
    ids=result['robust']['truth_comparison']['positive_input_ids']
    truth=truth[ids]/baseline
    recovered=np.asarray(result['robust']['pose']['points_baseline_units'])
    allp=np.vstack((truth,recovered))
    xmin,xmax=allp[:,0].min(),allp[:,0].max()
    zmin,zmax=allp[:,2].min(),allp[:,2].max()
    dx,dz=max(xmax-xmin,1e-6),max(zmax-zmin,1e-6)
    def xx2(x):return 130+500*(x-xmin)/dx
    def yy2(z):return 350-240*(z-zmin)/dz
    markers=[]
    for i,(p,q) in enumerate(zip(truth,recovered)):
        tx,tz,rx,rz=xx2(p[0]),yy2(p[2]),xx2(q[0]),yy2(q[2])
        markers.append(f'<path d="M{tx:.5f},{tz:.5f} L{rx:.5f},{rz:.5f}" stroke="#9da6b0"/><circle cx="{tx:.5f}" cy="{tz:.5f}" r="4" fill="none" stroke="#536478"/><path d="M{rx-4:.5f},{rz-4:.5f} l8,8 m-8,0 l8,-8" stroke="#176a9b" stroke-width="2"/>')
        if i%5==0:markers.append(f'<text x="{rx+8:.5f}" y="{rz-8:.5f}">P{ids[i]}</text>')
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="465" viewBox="0 0 840 465" role="img" aria-labelledby="title desc">
<title id="title">Reconstruction in unit-baseline coordinates</title><desc id="desc">XZ projection only, independent drawing scales. {len(ids)} forward model-consensus points. Open circles truth divided by the known synthetic baseline solely for evaluation; blue crosses the estimated unit-baseline reconstruction. Axes are baseline units, not measured metres.</desc>
<rect width="840" height="465" fill="white"/><g font-family="sans-serif" font-size="16" fill="#172638">
<text x="25" y="27">Unit-baseline reconstruction: XZ projection of {len(ids)} selected points</text>
<text x="25" y="57">open circles: synthetic truth / B; blue crosses: estimate</text>
<path d="M105,85 V375 H700" fill="none" stroke="#536478"/>
<text x="20" y="100">Z / B</text><text x="690" y="400">X / B</text>
<text x="112" y="399">{xmin:.4g}</text><text x="610" y="399">{xmax:.4g}</text>
<text x="40" y="354">{zmin:.4g}</text><text x="40" y="114">{zmax:.4g}</text>
{''.join(markers)}<text x="90" y="435">Independent axis drawing scales; baseline units, not measured metres.</text></g></svg>'''
    (directory/'pose-reconstruction.svg').write_text(svg+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).parent/'inputs/pose-estimation.json')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text(encoding='utf-8')))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'pose-estimation-results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    figures(result,args.output_dir)
    print(json.dumps({"robust":result['robust']['truth_comparison'],"identity":result['robust']['identity_evaluation_only'],
      "cheirality":result['robust']['pose']['candidate_positive_counts'],"degenerate":result['degenerate_rejections']}))


if __name__=='__main__':main()
