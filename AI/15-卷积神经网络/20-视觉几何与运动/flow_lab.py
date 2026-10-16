"""Actual grayscale pixel patches -> local translations, not identity certification.

I[v,u] uses row/column indexing; uv arrays store continuous (u,v) pixels.
Synthetic sequence has static frontoparallel textured patches and translating rigs.
The public photo is real texture with an explicitly artificial translation.
"""
from pathlib import Path
import argparse
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, uniform_filter
import stereo_lab as stereo


def image(value):
    a = np.asarray(value, dtype=float)
    if a.ndim != 2 or min(a.shape) < 3 or not np.isfinite(a).all():
        raise ValueError("image must be finite (H,W), H,W>=3")
    if np.min(a) < 0 or np.max(a) > 1:
        raise ValueError("gray intensities must be in [0,1]")
    return a


def sample(a, uv, gradient=False):
    """Bilinear interior sampler and its exact piecewise derivatives; no padding."""
    a, uv = image(a), stereo.batch(uv, 2)
    x, y = uv.T
    h,w = a.shape
    if np.any(x<0) or np.any(y<0) or np.any(x>=w-1) or np.any(y>=h-1):
        raise ValueError("sample outside bilinear interior")
    u,v = np.floor(x).astype(int), np.floor(y).astype(int)
    dx,dy = x-u,y-v
    p,q,r,s = a[v,u],a[v,u+1],a[v+1,u],a[v+1,u+1]
    values = (1-dy)*((1-dx)*p+dx*q)+dy*((1-dx)*r+dx*s)
    if gradient:
        jac = np.column_stack(((1-dy)*(q-p)+dy*(s-r),
                               (1-dx)*(r-p)+dx*(s-q)))
        return values,jac
    return values


def offsets(half):
    if not isinstance(half,int) or isinstance(half,bool) or half<1:
        raise ValueError("half window must be a positive integer")
    y,x=np.mgrid[-half:half+1,-half:half+1]
    return np.column_stack((x.ravel(),y.ravel()))


def solve_patch(a,b,uv,half=5,search=5,min_eigen=5e-5):
    """Coarse integer SSD then forward-additive Gauss Newton, at most 40 steps."""
    if not isinstance(search,int) or isinstance(search,bool) or search<0:
        raise ValueError("search must be a nonnegative integer")
    a,b=image(a),image(b)
    if a.shape!=b.shape:
        raise ValueError("image shapes differ")
    center=stereo.principal(uv)
    grid=center+offsets(half)
    template,j0=sample(a,grid,True)
    eig=np.linalg.eigvalsh(j0.T@j0/len(grid))
    if eig[0]<min_eigen:
        raise ValueError("flat/edge aperture: insufficient two-direction texture")
    best=None
    for dy in range(-search,search+1):
        for dx in range(-search,search+1):
            d=np.array([dx,dy],float)
            try: residual=sample(b,grid+d)-template
            except ValueError: continue
            score=float(residual@residual)
            if best is None or score<best[0]: best=(score,d)
    if best is None: raise ValueError("no valid search window")
    d=best[1].copy()
    converged=False
    for it in range(40):
        values,jac=sample(b,grid+d,True)
        if np.linalg.eigvalsh(jac.T@jac/len(grid))[0]<min_eigen:
            raise ValueError("target loses two-direction texture")
        step=np.linalg.lstsq(jac,template-values,rcond=None)[0]
        # Backtracking keeps the actual nonlinear SSD from increasing.
        cost=float(np.sum((values-template)**2))
        accepted=False
        for fraction in (1.,.5,.25,.125,.0625,.03125,.015625,.0078125,.00390625,.001953125,.0009765625):
            proposal=d+fraction*step
            if np.linalg.norm(proposal,np.inf)>search+1:
                continue
            try: trial=sample(b,grid+proposal)-template
            except ValueError: continue
            if trial@trial<=cost+1e-15:
                d=proposal; accepted=True; break
        if not accepted:
            converged=True  # declared finite line-search stopping, not global optimality
            break
        if np.linalg.norm(fraction*step)<1e-5:
            converged=True; break
    residual=sample(b,grid+d)-template
    return {"uv_px":(center+d).tolist(),"displacement_px":d.tolist(),
            "rms_intensity":float(np.sqrt(np.mean(residual**2))),
            "source_mean_eigenvalues":eig.tolist(),"iterations":it+1,
            "stopped":converged,"stop_rule":"small step <=1e-5 px or no descent at fractions 2^0..2^-10; not global optimum"}


def track(a,b,points,half=5,search=5,min_eigen=5e-5,max_rms=.035,max_fb=.15):
    rows=[]
    for uv in stereo.batch(points,2):
        try:
            item=solve_patch(a,b,uv,half,search,min_eigen)
            if not item["stopped"]: raise ValueError("local iteration hit limit")
            if item["rms_intensity"]>max_rms: raise ValueError("brightness/occlusion residual exceeds policy")
            reverse=solve_patch(b,a,item["uv_px"],half,search,min_eigen)
            if not reverse["stopped"]: raise ValueError("reverse iteration hit limit")
            fb=float(np.linalg.norm(np.asarray(reverse["uv_px"])-uv))
            if fb>max_fb: raise ValueError("forward/backward disagreement exceeds policy")
            item.update({"accepted":True,"fb_error_px":fb})
        except ValueError as exc:
            item={"accepted":False,"reason":str(exc)}
        rows.append(item)
    return rows


def detect(a,count=12,half=5,min_distance=12):
    """Greedy minimum-eigenvalue patch detector; deterministic tie order v then u."""
    a=image(a)
    gy,gx=np.gradient(a)
    h00=uniform_filter(gx*gx,size=2*half+1)
    h11=uniform_filter(gy*gy,size=2*half+1)
    h01=uniform_filter(gx*gy,size=2*half+1)
    score=(h00+h11-np.sqrt((h00-h11)**2+4*h01*h01))/2
    margin=half+8
    score[:margin]=0; score[-margin:]=0; score[:,:margin]=0; score[:,-margin:]=0
    order=np.argsort(-score.ravel(),kind="stable")
    points=[]
    for idx in order:
        v,u=divmod(int(idx),a.shape[1])
        if score[v,u]<5e-5: break
        if all(np.linalg.norm(np.array([u,v])-p)>=min_distance for p in points):
            points.append(np.array([u,v]))
            if len(points)==count: break
    if not points: raise ValueError("no two-direction texture detected")
    return np.asarray(points,float)


def scene(spec):
    uv=stereo.batch(spec["seed_left_px"],2)
    z=np.asarray(spec["depth_m"],float)
    f,c=spec["f_px"],np.asarray(spec["principal_px"])
    points=np.column_stack(((uv-c)*z[:,None]/f,z))
    centers=stereo.batch(spec["centers_world_m"],3)
    if np.any(centers[:,2]!=0):
        raise ValueError("fixture supports lateral translation only; texture depth scaling is not modeled")
    shape=spec["shape_t_eye_h_w"]
    if shape[:2]!=[len(centers),2] or len(points)!=12: raise ValueError("fixture shape mismatch")
    frames=np.full(shape,.08,float)
    truth=np.empty((len(centers),2,len(points),2))
    yy,xx=np.mgrid[:shape[2],:shape[3]]
    for t,center in enumerate(centers):
        for eye in range(2):
            camera=points-center-np.array([eye*spec["baseline_m"],0,0])
            pixels=stereo.project(camera,f,c)
            truth[t,eye]=pixels
            for j,p in enumerate(pixels):
                dx,dy=xx-p[0],yy-p[1]
                inside=(abs(dx)<=12)&(abs(dy)<=12)
                tex=(.45+.17*np.sin(.39*dx+.17*dy+j*.43)
                     +.16*np.cos(-.23*dx+.41*dy+j*.27)
                     +.09*np.sin(.13*dx-.27*dy+j*.61))
                frames[t,eye][inside]=tex[inside]
    return frames.astype(np.float32),truth,points


def sequence_tracks(frames,spec):
    tracker=spec["tracker"]
    kw=dict(half=tracker["half_window"],min_eigen=tracker["min_eigen_mean"],
            max_rms=tracker["max_rms"],max_fb=tracker["max_fb_px"])
    observations=np.empty((len(frames),2,12,2))
    observations[0,0]=spec["seed_left_px"]  # supplied seeds, not detected identities
    logs=[]
    for t in range(len(frames)):
        if t:
            rows=track(frames[t-1,0],frames[t,0],observations[t-1,0],
                       search=tracker["search_temporal"],**kw)
            if not all(r["accepted"] for r in rows): raise ValueError(f"temporal lost track at {t}: {rows}")
            observations[t,0]=[r["uv_px"] for r in rows]
            logs.append({"time":t,"kind":"temporal","rows":rows})
        rows=track(frames[t,0],frames[t,1],observations[t,0],search=tracker["search_stereo"],**kw)
        if not all(r["accepted"] for r in rows): raise ValueError(f"stereo lost track at {t}: {rows}")
        observations[t,1]=[r["uv_px"] for r in rows]
        logs.append({"time":t,"kind":"stereo","rows":rows})
    return observations,logs


def photo_case(root,spec):
    original=np.asarray(Image.open(root/"inputs/camera.png"),float)/255
    y,x,h,w=spec["photo_crop_yxhw"]
    a=gaussian_filter(original[y:y+h,x:x+w],1.2,mode="reflect")
    yy,xx=np.mgrid[:h,:w]
    delta=np.asarray(spec["photo_translation_px"])
    coords=np.column_stack((xx.ravel()-delta[0],yy.ravel()-delta[1]))
    # Only this declared warp uses clipped border extension; LK samples no border.
    coords[:,0]=np.clip(coords[:,0],0,w-1-1e-9); coords[:,1]=np.clip(coords[:,1],0,h-1-1e-9)
    b=sample(a,coords).reshape(h,w)
    seeds=detect(a)
    rows=track(a,b,seeds,search=3)
    errors=[float(np.linalg.norm(np.asarray(r["displacement_px"])-delta)) if r["accepted"] else None for r in rows]
    return a,b,seeds,{"source":"CC0 real photo, Gaussian-smoothed crop + artificial bilinear translation",
      "translation_px":delta.tolist(),"seeds_px":seeds.tolist(),"rows":rows,"errors_px":errors}


def failures(a,spec):
    yy,xx=np.mgrid[:64,:64]
    flat=np.full((64,64),.5)
    edge=.5+.2*np.sin(.3*xx)
    texture=.5+.15*np.sin(.3*xx)+.15*np.cos(.4*yy)
    bright=np.clip(texture+.18,0,1)
    # One whole-period wrong correspondence is observationally indistinguishable.
    periodic=.5+.15*np.cos(2*np.pi*xx/8)+.15*np.cos(2*np.pi*yy/8)
    periodic_result=track(periodic,periodic,[[24,24]],search=0)
    p=periodic_result[0]
    return {"flat":track(flat,flat,[[24,24]],search=2)[0],
            "edge":track(edge,edge,[[24,24]],search=2)[0],
            "brightness_change":track(texture,bright,[[24,24]],search=2)[0],
            "occluded":track(texture,flat,[[24,24]],search=2)[0],
            "periodic_wrong_identity":{"declared_true_displacement_px":[8,0],
                  "estimated":p,"identity_error_px":8.0,
                  "note":"periodic texture shifted by 8 px equals same raster; zero/FB cannot identify period"}}


def run(spec,root,output):
    frames,truth,points=scene(spec)
    uv,logs=sequence_tracks(frames,spec)
    a,b,seeds,photo=photo_case(root,spec)
    shifted_seeds=np.asarray(spec["seed_left_px"],float)+[1.5,-.75]
    biased=track(frames[0,0],frames[1,0],shifted_seeds,search=5)
    localized={"seed_offset_px":[1.5,-.75],"rows":biased,
       "errors_to_intended_patch_center_px":[float(np.linalg.norm(np.asarray(r["uv_px"])-p))
           if r["accepted"] else None for r,p in zip(biased,truth[1,0])],
       "meaning":"a perturbed supplied localization keeps tracking a nearby patch location; tracking is not a semantic center detector"}
    small_search=track(frames[0,0],frames[1,0],spec["seed_left_px"],search=0)
    output.mkdir(parents=True,exist_ok=True)
    np.save(output/"motion-pixels.npy",frames,allow_pickle=False)
    np.save(output/"photo-pair.npy",np.stack((a,b)),allow_pickle=False)
    result={"model":"synthetic stereo time sequence; public photo has artificial warp",
      "units":{"uv":"px","gray":"0..1","xyz":"m"},"shape":list(frames.shape),
      "truth_points_world_m":points.tolist(),"truth_pixels_px":truth.tolist(),
      "tracked_pixels_px":uv.tolist(),"pixel_errors_px":np.linalg.norm(uv-truth,axis=-1).tolist(),
      "tracking_log":logs,"photo":photo,"seed_localization_perturbation":localized,
      "too_small_search":small_search,"failure_cases":failures(a,spec)}
    (output/"flow-results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parent
    parser.add_argument("--input",type=Path,default=root/"inputs/motion-spec.json")
    parser.add_argument("--output",type=Path,default=root/"results")
    args=parser.parse_args()
    result=run(json.loads(args.input.read_text()),root,args.output)
    print(json.dumps({"max_synthetic_track_error_px":np.max(result["pixel_errors_px"]),
      "photo_errors_px":result["photo"]["errors_px"],"failures":result["failure_cases"]},indent=2))

if __name__=="__main__": main()
