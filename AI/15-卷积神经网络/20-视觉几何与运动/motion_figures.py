"""Standalone SVG plots from the same raw pixels and stored numerical results."""
from pathlib import Path
import base64
import io
import json
import numpy as np
from PIL import Image
from xml.sax.saxutils import escape

COLORS={"no_closure":"#aa6814","true_closure":"#09699b","wrong_closure":"#b32934","wrong_closure_robust":"#76449a"}
LABELS={"no_closure":"No closure","true_closure":"Correct closure","wrong_closure":"Wrong, quadratic","wrong_closure_robust":"Wrong, soft-L1"}


def raster(a):
    out=io.BytesIO()
    Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(out,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(out.getvalue()).decode()


def svg(title,desc,w,h,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif" font-size="15" fill="#172638">{body}</g></svg>\n'


def flow_plot(flow,spec,results):
    photo=np.load(results/"photo-pair.npy",allow_pickle=False)
    pixels=np.load(results/"motion-pixels.npy",allow_pickle=False)
    seeds=np.asarray(flow["photo"]["seeds_px"])
    body='<text x="25" y="28" font-size="19">Real texture, artificial shift: actual pixels and detected patches</text>'
    for k in (0,1):
        ox,oy=25+k*405,65
        body+=f'<image x="{ox}" y="{oy}" width="384" height="256" href="{raster(photo[k])}"/>'
        for j,(uv,row) in enumerate(zip(seeds,flow["photo"]["rows"])):
            p=uv if k==0 else np.asarray(row["uv_px"])
            body+=f'<rect x="{ox+2*(p[0]-5):.4f}" y="{oy+2*(p[1]-5):.4f}" width="20" height="20" fill="none" stroke="#00ffff"/><text x="{ox+2*p[0]+10:.4f}" y="{oy+2*p[1]:.4f}" fill="#fff">{j}</text>'
        body+=f'<text x="{ox}" y="345">{("Source crop (CC0), smoothed" if k==0 else "Bilinear shifted by (1.25, -0.75) px")}</text>'
    body+='<text x="25" y="380">Patch IDs are the same detections; no real independent time pair is claimed.</text>'
    errors=flow["photo"]["errors_px"]
    body+=f'<text x="25" y="407">12 accepted; error range {min(errors):.4f}–{max(errors):.4f} px. Image display scale: 2 screen px / image px.</text>'
    # Third image, synthetic left frame2, with tracked physical seeds.
    body+=f'<image x="25" y="450" width="384" height="256" href="{raster(pixels[2,0])}"/>'
    truth=np.asarray(flow["truth_pixels_px"])[2,0]
    tracked=np.asarray(flow["tracked_pixels_px"])[2,0]
    for j,(a,b) in enumerate(zip(truth,tracked)):
        body+=f'<circle cx="{25+2*a[0]:.4f}" cy="{450+2*a[1]:.4f}" r="5" fill="none" stroke="#ffff00"/><path d="M {25+2*b[0]-3:.4f},{450+2*b[1]:.4f} h 6 m -3,-3 v 6" stroke="#00ffff"/><text x="{25+2*b[0]+6:.4f}" y="{450+2*b[1]-6:.4f}" fill="#fff">{j}</text>'
    body+='<text x="435" y="475">Synthetic stereo sequence, frame 2 left</text><text x="435" y="505">Yellow circle: projected truth</text><text x="435" y="535">Cyan cross: tracked seed (almost overlap)</text>'
    body+=f'<text x="435" y="570">5 × 2 × 128 × 192 gray pixels</text><text x="435" y="600">Max track error: {np.max(flow["pixel_errors_px"]):.5f} px</text><text x="435" y="635">12 initial seeds are supplied.</text><text x="435" y="665">Temporal tracking + independent stereo search</text>'
    return svg("Actual image patches and measured tracking error","Top: CC0 real photo crop with synthetic known warp and 12 actual detected features. Bottom: synthetic frame2 left, truth and tracked points in same pixel model. Intensities0..1, coordinates pixels; y increases down.",840,735,body)


def graph_plot(ba,spec):
    body='<text x="25" y="28" font-size="19">The closure adds new observations, not duplicate weights</text>'
    for t in range(5):
        x=155+t*140
        body+=f'<text x="{x-18}" y="68">t={t}</text>'
        for j in range(12):
            y=100+j*24
            active=j in spec["base_ids_by_frame"][t]
            closure=t==4 and j in spec["closure_ids_frame4"]
            if active or closure:
                color="#09699b" if active else "#07814c"
                body+=f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/>'
                if closure: body+=f'<circle cx="{x}" cy="{y}" r="10" fill="none" stroke="{color}"/>'
            else: body+=f'<circle cx="{x}" cy="{y}" r="3" fill="#ccd2d8"/>'
            if t==0: body+=f'<text x="52" y="{y+5}">ID {j}</text>'
            if t>0 and active and j in spec["base_ids_by_frame"][t-1]:
                body+=f'<path d="M {x-140+7},{y} H {x-7}" stroke="#96b5c9"/>'
            if closure: body+=f'<path d="M 162,{y} H {x-11}" stroke="#07814c" stroke-dasharray="3 5"/>'
    body+='<text x="25" y="425">Each colored node supplies two eye factors (u,v each). Pose0 fixed; B=0.08 m.</text><text x="25" y="452">Base: 66 image points / 132 scalar residuals. Closure: +12 / +24, total78 /156.</text><text x="25" y="479">Wrong closure uses those same 12 new pixels but swaps IDs 0,1,2 with 3,4,5.</text><text x="25" y="506">A supplied association graph isolates its effect; there is no automatic loop detector.</text>'
    return svg("Which observations close the window?","Rows landmark identity0..11, columns time0..4. Blue nodes are base observations, green rings new closing observations, gray absent. Each node is a stereo pair. No duplicate time/eye/landmark factors.",840,535,body)


def errors_plot(ba):
    body='<text x="25" y="28" font-size="19">A smaller fitting residual is not the same as a more accurate trajectory</text>'
    for panel,(key,label,unit) in enumerate([("center_errors_m","Camera-center error","m"),("map_errors_m","Landmark error","m")]):
        x0,y0=75+panel*410,335
        n=5 if panel==0 else 12
        ymax=max(max(ba["cases"][k][key]) for k in COLORS)*1.08
        body+=f'<text x="{x0}" y="65">{label} ({unit})</text><path d="M {x0},{y0-240} V {y0} H {x0+330}" fill="none" stroke="#596779"/>'
        for frac in (0,.25,.5,.75,1):
            val=ymax*frac; y=y0-240*frac
            body+=f'<text x="{x0-55}" y="{y+4:.2f}">{val:.3f}</text><path d="M {x0},{y:.2f} H {x0+330}" stroke="#ddd"/>'
        for name,color in COLORS.items():
            vals=ba["cases"][name][key]
            coords=[(x0+330*i/(n-1),y0-240*v/ymax) for i,v in enumerate(vals)]
            body+=f'<polyline points="'+" ".join(f"{x:.4f},{y:.4f}" for x,y in coords)+f'" fill="none" stroke="{color}" stroke-width="2"/>'
            for x,y in coords: body+=f'<circle cx="{x:.4f}" cy="{y:.4f}" r="3" fill="{color}"/>'
        for i in range(n): body+=f'<text x="{x0+330*i/(n-1)-4:.3f}" y="360">{i}</text>'
        body+=f'<text x="{x0+110}" y="387">{("time index" if panel==0 else "landmark ID")}</text>'
    body+='<text x="25" y="430">Case</text><text x="310" y="430">point RMS px</text><text x="470" y="430">trajectory RMS m</text><text x="650" y="430">map RMS m</text><text x="770" y="430">active bounds</text>'
    for i,(name,color) in enumerate(COLORS.items()):
        r=ba["cases"][name]; y=464+i*34
        body+=f'<text x="25" y="{y}" fill="{color}">{LABELS[name]}</text><text x="310" y="{y}">{r["point_rms_px"]:.5f}</text><text x="470" y="{y}">{r["trajectory_rms_m"]:.5f}</text><text x="650" y="{y}">{r["map_rms_m"]:.5f}</text><text x="790" y="{y}">{r["active_bound_count"]}</text>'
    body+='<text x="25" y="622">Fixed finite data: soft-L1 also fails under this wrong association. Bounds limit the deformation.</text><text x="25" y="650">Truth is used only to score these errors. Different graphs have different fitting residual sets.</text>'
    return svg("Joint estimation errors under correct and incorrect closing observations","Upper two panels plot exact stored center and landmark error in metres, against time or point identity; four cases distinguished by color and table labels. Lower table reports point RMS pixels, trajectory/map RMS metres and active solver bounds. A fixed experiment, no statistical guarantee.",890,680,body)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parent
    parser.add_argument("--results",type=Path,default=root/"results")
    parser.add_argument("--input",type=Path,default=root/"inputs/motion-spec.json")
    args=parser.parse_args()
    flow=json.loads((args.results/"flow-results.json").read_text()); ba=json.loads((args.results/"window-ba-results.json").read_text())
    spec=json.loads(args.input.read_text())
    outputs={"motion-pixels.svg":flow_plot(flow,spec,args.results),"window-graph.svg":graph_plot(ba,spec),"window-errors.svg":errors_plot(ba)}
    for name,value in outputs.items(): (args.results/name).write_text(value)
    print("wrote "+", ".join(outputs))

if __name__=="__main__": main()
