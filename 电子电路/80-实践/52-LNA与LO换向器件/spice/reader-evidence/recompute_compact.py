"""Recompute recorded nonuniform finite-window projections; no simulation or resampling."""
from pathlib import Path
import argparse,json,gzip,hashlib,numpy as np

def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 if args.output.exists() or args.output.is_symlink():raise FileExistsError('fresh output required')
 root=Path(__file__).resolve().parent;interface=json.loads((root/'interface.json').read_text());rows=[]
 for item in interface['files']:
  p=root/item['case']/'projection-window.csv.gz';raw=gzip.decompress(p.read_bytes());assert hashlib.sha256(raw).hexdigest()==item['compact_plain_sha256'];d=np.loadtxt(p,delimiter=',',skiprows=1);start,stop=item['window_s'];mask=(d[:,0]>start)&(d[:,0]<stop);t=np.r_[start,d[mask,0],stop];v=np.interp(t,d[:,0],d[:,1]);cm=np.interp(t,d[:,0],d[:,2]);span=stop-start;projections={}
  for freq in [10e6,30e6,50e6]:
   c=2*np.trapezoid(v*np.cos(2*np.pi*freq*t),t)/span;s=2*np.trapezoid(v*np.sin(2*np.pi*freq*t),t)/span;projections[str(int(freq))]={'cos_V':float(c),'sin_V':float(s),'amplitude_V':float(np.hypot(c,s))}
  rows.append({'case':item['case'],'window_s':[start,stop],'purpose':item['purpose'],'DC_output_diff_V':float(np.trapezoid(v,t)/span),'common_mode_mean_V':float(np.trapezoid(cm,t)/span),'projections':projections})
 args.output.write_text(json.dumps({'method':'exact same nonuniform trapezoidal quadrature; endpoints interpolated using retained original bracketing row','cases':rows},indent=2))
if __name__=='__main__':main()
