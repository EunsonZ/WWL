"""A fixed observed stereo graph: localization versus joint metric window BA.

World = first left camera. R_CW P_W+t_CW; right point = left point-(B,0,0).
No online SLAM, descriptor matching, loop detection, or truth-based initialization.
"""
from pathlib import Path
import argparse
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import stereo_lab as stereo
import multiview_lab as geometry


def unpack(x,times=5,landmarks=12):
    x=np.asarray(x,float)
    count=6*(times-1)
    if x.shape!=(count+3*landmarks,) or not np.isfinite(x).all():
        raise ValueError("invalid finite pose/landmark state")
    poses=np.vstack((np.zeros(6),x[:count].reshape(times-1,6)))
    points=x[count:].reshape(landmarks,3)
    return poses,points


def pack(poses,points):
    poses,points=stereo.batch(poses,6),stereo.batch(points,3)
    if not np.array_equal(poses[0],np.zeros(6)): raise ValueError("pose0 must be anchored I/0")
    return np.r_[poses[1:].ravel(),points.ravel()]


def camera_points(points,pose):
    p=stereo.batch(points,3); pose=np.asarray(pose,float)
    if pose.shape!=(6,) or not np.isfinite(pose).all(): raise ValueError("pose must be finite (6,)")
    return p@Rotation.from_rotvec(pose[:3]).as_matrix().T+pose[3:]


def predict(poses,points,edges,spec,baseline=None):
    b=spec["baseline_m"] if baseline is None else float(baseline)
    if not np.isfinite(b) or b<0: raise ValueError("baseline must be finite >=0")
    output=[]
    for row in edges:
        t,eye,j=row["time"],row["eye"],row["landmark"]
        if not(0<=t<len(poses) and eye in (0,1) and 0<=j<len(points)):
            raise ValueError("edge index outside state")
        pc=camera_points(points[j:j+1],poses[t])-np.array([eye*b,0.,0.])
        output.append(stereo.project(pc,spec["f_px"],spec["principal_px"])[0])
    return stereo.batch(output,2)


def graph(uv,spec,closure="none"):
    if closure not in ("none","true","wrong"): raise ValueError("unknown closure")
    uv=np.asarray(uv,float)
    if uv.shape!=(5,2,12,2) or not np.isfinite(uv).all(): raise ValueError("observations must be finite (5,2,12,2)")
    edges=[]
    for t,ids in enumerate(spec["base_ids_by_frame"]):
        for j in ids:
            for eye in range(2):
                edges.append({"time":t,"eye":eye,"landmark":j,"pixel_source_id":j,
                              "uv_px":uv[t,eye,j].tolist(),"closure":False})
    if closure!="none":
        targets=spec["closure_ids_frame4"] if closure=="true" else [3,4,5,0,1,2]
        for source,target in zip(spec["closure_ids_frame4"],targets):
            for eye in range(2):
                edges.append({"time":4,"eye":eye,"landmark":target,"pixel_source_id":source,
                              "uv_px":uv[4,eye,source].tolist(),"closure":True})
    keys=[(e["time"],e["eye"],e["landmark"]) for e in edges]
    if len(set(keys))!=len(keys): raise ValueError("duplicate image factor")
    return edges


def bounds():
    # |rotvec components|<=.08 rad and |t components|<=.15 m; world box.
    lower=np.r_[np.tile([-.08,-.08,-.08,-.15,-.15,-.15],4),np.tile([-1.,-.8,.8],12)]
    upper=np.r_[np.tile([.08,.08,.08,.15,.15,.15],4),np.tile([1.,.8,3.],12)]
    return lower,upper


def initialize(uv,spec):
    """Sequential stereo points + known-map pose fits, using observations only."""
    uv=np.asarray(uv,float)
    poses=np.zeros((5,6)); points=np.full((12,3),np.nan)
    lo,hi=bounds()
    for t,ids in enumerate(spec["base_ids_by_frame"]):
        old=[j for j in ids if np.isfinite(points[j]).all()]
        if t:
            if len(old)<3: raise ValueError("initialization requires >=3 existing map points")
            local_edges=[{"time":0,"eye":eye,"landmark":j} for j in old for eye in range(2)]
            observed=np.array([uv[t,e["eye"],e["landmark"]] for e in local_edges])
            def residual(pose): return (predict(pose[None,:],points,local_edges,spec)-observed).ravel()
            result=least_squares(residual,poses[t-1],bounds=(lo[:6],hi[:6]),
                                 ftol=1e-11,xtol=1e-11,gtol=1e-11,max_nfev=120)
            if not result.success: raise ValueError("initial known-map pose fit failed")
            poses[t]=result.x
        new=[j for j in ids if not np.isfinite(points[j]).all()]
        if new:
            local=np.asarray(geometry.triangulate(uv[t,0,new],uv[t,1,new],np.eye(3),
                [spec["baseline_m"],0,0],spec["f_px"],spec["principal_px"],
                spec["f_px"],spec["principal_px"])["points_left_m"])
            r=Rotation.from_rotvec(poses[t,:3]).as_matrix()
            points[new]=(local-poses[t,3:])@r
    initial=pack(poses,points)
    if np.any(initial<=lo) or np.any(initial>=hi): raise ValueError("initializer outside declared solver box")
    return initial


def fit(uv,spec,closure="none",loss="linear",initial=None):
    if loss not in ("linear","soft_l1"): raise ValueError("loss policy must be linear or soft_l1")
    edges=graph(uv,spec,closure)
    observed=np.asarray([e["uv_px"] for e in edges])
    x0=initialize(uv,spec) if initial is None else np.asarray(initial,float)
    def residual(x):
        poses,points=unpack(x)
        return (predict(poses,points,edges,spec)-observed).ravel()
    result=least_squares(residual,x0,bounds=bounds(),loss=loss,f_scale=spec["ba"]["loss_scale_px"],
        x_scale="jac",ftol=1e-10,xtol=1e-10,gtol=1e-10,max_nfev=spec["ba"]["max_nfev"])
    if not result.success: raise ValueError(f"window solver failed: {result.message}")
    poses,points=unpack(result.x)
    pred=predict(poses,points,edges,spec)
    return {"closure":closure,"loss":loss,"poses_rotvec_t_CW":poses.tolist(),
      "points_world_m":points.tolist(),"edges":edges,"predicted_px":pred.tolist(),
      "residual_px":(pred-observed).tolist(),"point_rms_px":float(np.sqrt(np.mean(np.sum((pred-observed)**2,axis=1)))),
      "cost":float(result.cost),"nfev":int(result.nfev),"status":int(result.status),
      "message":result.message,"initial_state":x0.tolist(),"active_bound_count":int(np.count_nonzero(result.active_mask))}


def centers(poses):
    return np.asarray([-Rotation.from_rotvec(p[:3]).as_matrix().T@p[3:] for p in poses])


def evaluate(result,true_points,true_centers):
    poses=np.asarray(result["poses_rotvec_t_CW"])
    c=centers(poses)
    result["centers_world_m"]=c.tolist()
    result["center_errors_m"]=np.linalg.norm(c-true_centers,axis=1).tolist()
    result["map_errors_m"]=np.linalg.norm(np.asarray(result["points_world_m"])-true_points,axis=1).tolist()
    result["rotation_errors_rad"]=np.linalg.norm(poses[:,:3],axis=1).tolist()
    result["trajectory_rms_m"]=float(np.sqrt(np.mean(np.sum((c-true_centers)**2,axis=1))))
    result["map_rms_m"]=float(np.sqrt(np.mean(np.sum((np.asarray(result["points_world_m"])-true_points)**2,axis=1))))
    return result


def known_map(uv,spec,true_points):
    # Evaluation comparison: externally surveyed map is known, never joint-fit.
    lo,hi=bounds(); poses=np.zeros((5,6))
    for t in range(1,5):
        edges=[{"time":0,"eye":eye,"landmark":j} for j in spec["base_ids_by_frame"][t] for eye in range(2)]
        obs=np.asarray([uv[t,e["eye"],e["landmark"]] for e in edges])
        def fun(pose): return (predict(pose[None,:],true_points,edges,spec)-obs).ravel()
        result=least_squares(fun,poses[t-1],bounds=(lo[:6],hi[:6]),ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=120)
        if not result.success: raise ValueError("known map localization failed")
        poses[t]=result.x
    return {"poses_rotvec_t_CW":poses.tolist(),"centers_world_m":centers(poses).tolist(),
            "map_status":"truth supplied as externally known map for comparison; not SLAM"}


def jacobian(fun,x,h=1e-6):
    columns=[]
    for k in range(len(x)):
        step=np.zeros(len(x)); step[k]=h
        columns.append((fun(x+step)-fun(x-step))/(2*h))
    return np.column_stack(columns)


def gauges(spec,points,truth_centers,uv):
    poses=np.column_stack((np.zeros((5,3)),-truth_centers))
    edges=graph(uv,spec,"true")
    base=predict(poses,points,edges,spec)
    q=Rotation.from_rotvec([.13,-.08,.06]).as_matrix(); a=np.array([.2,-.1,.15])
    transformed=[]
    for p in poses:
        r=Rotation.from_rotvec(p[:3]).as_matrix()
        rp=r@q.T; tp=p[3:]-rp@a
        transformed.append(np.r_[Rotation.from_matrix(rp).as_rotvec(),tp])
    se3=predict(np.asarray(transformed),points@q.T+a,edges,spec)
    scale=1.7
    scaled=poses.copy(); scaled[:,3:]*=scale
    mono=predict(poses,points,edges,spec,0.)
    mono_scaled=predict(scaled,scale*points,edges,spec,0.)
    metric_scaled=predict(scaled,scale*points,edges,spec)
    x=pack(poses,points)
    def make(b):
        def f(state):
            pp,xx=unpack(state)
            return predict(pp,xx,edges,spec,b).ravel()
        return f
    js=jacobian(make(spec["baseline_m"]),x)
    jm=jacobian(make(0.),x)
    svs,svm=np.linalg.svd(js,compute_uv=False),np.linalg.svd(jm,compute_uv=False)
    direction=np.r_[np.column_stack((np.zeros((4,3)),poses[1:,3:])).ravel(),points.ravel()]
    return {"global_SE3_max_pixel_change_px":float(np.max(np.abs(se3-base))),
      "anchored_monocular_scale_max_pixel_change_px":float(np.max(np.abs(mono_scaled-mono))),
      "fixed_baseline_scaled_state_max_pixel_change_px":float(np.max(np.abs(metric_scaled-base))),
      "metric_jacobian_shape":list(js.shape),"metric_singular_values":svs.tolist(),
      "monocular_singular_values":svm.tolist(),"rank_policy":"sv > max_sv * 1e-7",
      "metric_rank":int(np.count_nonzero(svs>svs[0]*1e-7)),
      "monocular_rank":int(np.count_nonzero(svm>svm[0]*1e-7)),
      "mono_scale_direction_J_norm_px":float(np.linalg.norm(jm@direction)),"scale_factor":scale}


def run(spec,flow,output):
    tracked=np.asarray(flow["tracked_pixels_px"])
    true_uv=np.asarray(flow["truth_pixels_px"])
    true_points=np.asarray(flow["truth_points_world_m"])
    true_centers=np.asarray(spec["centers_world_m"])
    noise=np.random.default_rng(spec["seed"]).normal(0,spec["coordinate_noise_px"],tracked.shape)
    noisy=tracked+noise
    cases={}
    clean=fit(true_uv,spec,"true")
    cases["clean_true_closure"]=evaluate(clean,true_points,true_centers)
    for name,closure,loss in [("no_closure","none","linear"),("true_closure","true","linear"),
                              ("wrong_closure","wrong","linear"),("wrong_closure_robust","wrong","soft_l1")]:
        cases[name]=evaluate(fit(noisy,spec,closure,loss),true_points,true_centers)
    known=known_map(noisy,spec,true_points)
    result={"model":"fixed metric stereo window; supplied association graph; no automatic loop discovery",
      "state":"4 free SE3 poses +12 3D points =60; pose0 anchored; known B",
      "units":{"pose_rotvec":"rad","pose_t/map":"m","uv/residual":"px"},
      "coordinate_noise_px":noise.tolist(),"noisy_tracked_pixels_px":noisy.tolist(),
      "cases":cases,"known_map_localization":known,"gauges":gauges(spec,true_points,true_centers,true_uv)}
    output.mkdir(parents=True,exist_ok=True)
    (output/"window-ba-results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parent
    parser.add_argument("--input",type=Path,default=root/"inputs/motion-spec.json")
    parser.add_argument("--flow",type=Path,default=root/"results/flow-results.json")
    parser.add_argument("--output",type=Path,default=root/"results")
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text()),json.loads(args.flow.read_text()),args.output)
    print(json.dumps({name:{k:r[k] for k in ("point_rms_px","trajectory_rms_m","map_rms_m","active_bound_count","nfev")}
                      for name,r in result["cases"].items()},indent=2))
    print(json.dumps(result["gauges"],indent=2))

if __name__=="__main__": main()
