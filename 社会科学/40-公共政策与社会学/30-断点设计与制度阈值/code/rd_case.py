#!/usr/bin/env python3
"""Transparent local-polynomial calculations for Lee (2008), NumPy only.

Input is the CSV made from official table_two_final.dta by prepare_data.R.
Hand-chosen bandwidths and HC1 are used; this is not RBC inference.
"""
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np

ZIP_SHA256="ce7a164d659aa5e0706266c852526b7727b126566f4d38e7bbddf49d4720d9bf"
DTA_SHA256="4114a0c1120e6a5cf1e7a2e1f790f04c8d1678bc4e41bd2a901a088affae9db6"

def load_csv(path):
    with Path(path).open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    return {n:np.asarray([float(r[n]) if r[n].strip() not in ("","NA") else np.nan for r in rows]) for n in rows[0]}

def load_source_proof(path,data_path):
    proof={}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        key,sep,value=line.partition("=")
        if not sep: raise ValueError("invalid source-proof line")
        proof[key]=value
    if proof.get("dta_sha256") != DTA_SHA256 or proof.get("dta_sha256_verified") != "true":
        raise ValueError("source proof does not verify the fixed official DTA")
    if proof.get("rows_use") != "6559": raise ValueError("source proof has wrong use-sample size")
    actual=hashlib.sha256(Path(data_path).read_bytes()).hexdigest()
    if proof.get("csv_sha256") != actual: raise ValueError("CSV SHA-256 mismatch against source proof")
    return proof

def side(x,y,h,which,order=1,donut=0):
    ok=np.isfinite(x)&np.isfinite(y)&(np.abs(x)<=h)&(np.abs(x)>=donut)
    ok &= x<0 if which=="left" else x>0
    xx,yy=x[ok],y[ok]; w=1-np.abs(xx)/h; keep=w>0; xx,yy,w=xx[keep],yy[keep],w[keep]
    X=np.column_stack([xx**j for j in range(order+1)])
    bread=np.linalg.inv(X.T@(w[:,None]*X)); beta=bread@(X.T@(w*yy)); e=yy-X@beta
    cov=bread@(X.T@((w*w*e*e)[:,None]*X))@bread*len(yy)/(len(yy)-X.shape[1])
    return {"n":int(len(yy)),"intercept":float(beta[0]),"slope":float(beta[1]),"variance":float(cov[0,0])}

def rd(x,y,h,order=1,donut=0):
    l=side(x,y,h,"left",order,donut); r=side(x,y,h,"right",order,donut)
    tau=r["intercept"]-l["intercept"]
    # Convert the two side-specific HC1 pieces back to HC0, then apply one
    # N/(N-2k) correction for the joint two-sided model (2k parameters).
    k=order+1; n=l["n"]+r["n"]
    v0=l["variance"]*(l["n"]-k)/l["n"] + r["variance"]*(r["n"]-k)/r["n"]
    se=float(np.sqrt(v0*n/(n-2*k)))
    return {"h":h,"order":order,"donut":donut,"n_left":l["n"],"n_right":r["n"],
      "left_limit":l["intercept"],"right_limit":r["intercept"],"left_slope":l["slope"],"right_slope":r["slope"],
      "tau":tau,"se_hc1":se,"ci95_low":tau-1.96*se,"ci95_high":tau+1.96*se}

def bins(x,y,lo=-.2,hi=.2,width=.02):
    out=[]
    for a in np.arange(lo,hi,width):
        q=np.isfinite(y)&(x>=a)&(x<a+width)
        if q.any(): out.append({"x":float(x[q].mean()),"y":float(y[q].mean()),"n":int(q.sum()),"lo":float(a),"hi":float(a+width)})
    return out

def plot_svg(res,path):
    x0,x1,y0,y1=92,740,505,74; sx=lambda x:x0+(x+.2)/.4*(x1-x0); sy=lambda y:y0-(y-.35)/.3*(y0-y1)
    dots=''.join(f'<circle cx="{sx(b["x"]):.1f}" cy="{sy(b["y"]):.1f}" r="5" fill="#176b87"><title>{100*b["lo"]:.0f}到{100*b["hi"]:.0f}点：n={b["n"]}</title></circle>' for b in res["binned_means"])
    f=res["estimates"]["h10_linear"]; lines=[]
    for s,a,b in [("left",-.1,0),("right",0,.1)]:
        c,m=f[s+"_limit"],f[s+"_slope"]
        lines.append(f'<line x1="{sx(a):.1f}" y1="{sy(c+m*a):.1f}" x2="{sx(b):.1f}" y2="{sy(c+m*b):.1f}" stroke="#a23e48" stroke-width="4"/>')
    xt=''.join(f'<text x="{sx(v/100):.1f}" y="535" text-anchor="middle">{v}</text>' for v in [-20,-10,0,10,20])
    yt=''.join(f'<text x="78" y="{sy(v/100)+5:.1f}" text-anchor="end">{v}</text>' for v in [35,45,55,65])
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600"><title>Lee 2008众议院选举断点图</title><desc>横轴是本次民主党得票差，纵轴是下一次民主党得票率。点是2个百分点箱均值，线是带宽10个百分点的局部线性拟合。</desc><rect width="900" height="600" fill="#fbfaf7"/><g font-family="Arial Unicode MS, Noto Sans CJK SC, sans-serif" fill="#202124"><text x="450" y="35" font-size="24" font-weight="700" text-anchor="middle">刚好赢得本次席位，下一次政党得票率跳升多少？</text><text x="450" y="60" font-size="14" text-anchor="middle">Lee（2008）美国众议院真实样本；2点箱均值；h=10 局部线性</text><line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#555"/><line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#555"/><line x1="{sx(0):.1f}" y1="{y0}" x2="{sx(0):.1f}" y2="{y1}" stroke="#555" stroke-dasharray="6 5"/>{''.join(lines)}{dots}{xt}{yt}<text x="505" y="575" font-size="16" text-anchor="middle">t期民主党得票差（百分点；0为阈值）</text><text transform="translate(24 300) rotate(-90)" font-size="16" text-anchor="middle">t+1期民主党得票率（%）</text><text x="92" y="557" font-size="13" fill="#555">跳跃 {100*f["tau"]:.2f} 点；HC1 95%区间 [{100*f["ci95_low"]:.2f}, {100*f["ci95_high"]:.2f}]（非RBC）</text></g></svg>'''
    Path(path).write_text(svg,encoding="utf-8")

def sensitivity_svg(res,path):
    rows=[res["estimates"][f"h{h}_linear"] for h in [5,10,15,20]]; x0,x1=150,800; sx=lambda v:x0+(v+1)/12*(x1-x0); items=[]
    for i,r in enumerate(rows):
        y=130+i*82; lo,hi,t=100*r["ci95_low"],100*r["ci95_high"],100*r["tau"]
        items.append(f'<line x1="{sx(lo):.1f}" y1="{y}" x2="{sx(hi):.1f}" y2="{y}" stroke="#526d82" stroke-width="6"/><circle cx="{sx(t):.1f}" cy="{y}" r="9" fill="#d55e00"/><text x="128" y="{y+5}" text-anchor="end">h={100*r["h"]:.0f}</text><text x="{sx(t):.1f}" y="{y-16}" text-anchor="middle" font-size="13">{r["n_left"]}+{r["n_right"]}；τ={t:.2f}</text>')
    ticks=''.join(f'<text x="{sx(v):.1f}" y="486" text-anchor="middle">{v}</text>' for v in [0,2,4,6,8,10])
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="560" viewBox="0 0 900 560"><title>带宽敏感性</title><desc>四个手动带宽下的局部线性跳跃和普通HC1区间。</desc><rect width="900" height="560" fill="#fbfaf7"/><g font-family="Arial Unicode MS, Noto Sans CJK SC, sans-serif" fill="#202124"><text x="450" y="38" font-size="24" font-weight="700" text-anchor="middle">带宽改变了哪些临界选举进入比较</text><text x="450" y="64" font-size="14" text-anchor="middle">点为跳跃，线为普通HC1 95%区间；均不是RBC。</text><line x1="{sx(0):.1f}" y1="85" x2="{sx(0):.1f}" y2="455" stroke="#777" stroke-dasharray="5 5"/>{''.join(items)}<line x1="{x0}" y1="455" x2="{x1}" y2="455" stroke="#555"/>{ticks}<text x="525" y="525" font-size="16" text-anchor="middle">t+1民主党得票率的阈值跳跃（百分点）</text></g></svg>'''
    Path(path).write_text(svg,encoding="utf-8")

def compute(path,source_proof):
    proof=load_source_proof(source_proof,path)
    d=load_csv(path); x,y=d["difdemshare"],d["demsharenext"]
    if len(x)!=6559 or np.any(~np.isfinite(x)) or np.any(~np.isfinite(y)):
        raise ValueError("CSV must contain 6559 complete running-variable/outcome rows")
    defined=np.isfinite(d["right"]); undefined=~defined
    if undefined.sum()!=1 or x[undefined][0]!=0:
        raise ValueError("undefined treatment must be the unique exact-zero row")
    if np.any(~np.isin(d["right"][defined],[0,1])) or np.any(d["right"][defined]!=(x[defined]>0)):
        raise ValueError("right labels must agree with the running-variable sign")
    x=np.where(defined,x,np.nan)
    est={f"h{int(100*h)}_linear":rd(x,y,h) for h in [.05,.10,.15,.20]}
    est.update(h10_quadratic=rd(x,y,.1,2),h15_quadratic=rd(x,y,.15,2),h10_donut1=rd(x,y,.1,1,.01))
    cov={k:rd(x,d[k],.1) for k in ["demshareprev","demwinprev","demofficeexp","othofficeexp","demelectexp","othelectexp"]}
    den=[{"lo":float(a),"hi":float(a+.02),"n":int(((x>=a)&(x<a+.02)).sum())} for a in np.arange(-.1,.1,.02)]
    return {"provenance":{"zip_sha256_claimed":ZIP_SHA256,"dta_sha256_verified":proof["dta_sha256"],"csv_sha256_verified":proof["csv_sha256"],"source_proof_verified":True,"rows_use":len(x),"exact_zero_excluded":int(undefined.sum()),"analysis_rows":int(defined.sum()),"period":"U.S. House, 1946-1998"},"estimator":{"kernel":"triangular","cutoff":0,"variance":"HC1 sandwich, joint N/(N-2k) correction","rbc":False,"clustered":False},"estimates":est,"covariate_diagnostics_h10":cov,"density_bin_counts":den,"binned_means":bins(x,y)}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",type=Path,required=True); p.add_argument("--source-proof",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--assets",type=Path,required=True); a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True); a.assets.mkdir(parents=True,exist_ok=True)
    r=compute(a.data,a.source_proof); plot_svg(r,a.assets/"01-众议院选举断点图.svg"); sensitivity_svg(r,a.assets/"02-带宽敏感性.svg"); (a.out/"rd_results.json").write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
