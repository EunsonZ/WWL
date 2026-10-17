"""Recompute finite-window amplitude/frequency/CM from exact compact nonuniform samples."""
from pathlib import Path
import argparse,gzip,json,numpy as np
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists() or a.output.is_symlink():raise FileExistsError('fresh output required')
r=Path(__file__).resolve().parent;out={}
for name in json.loads((r/'fixed-inputs.json').read_text())['cases']:
 with gzip.open(r/name/'late.csv.gz','rt') as f:x=np.loadtxt(f,delimiter=',',skiprows=1)
 t,v,cm,ivdd=x.T;i=np.where((v[:-1]<=0)&(v[1:]>0))[0];zc=t[i]-v[i]*(t[i+1]-t[i])/(v[i+1]-v[i]);freq=float(1/np.mean(np.diff(zc))) if len(zc)>2 and max(abs(v))>1e-6 else None
 with gzip.open(r/name/'device-cycle.csv.gz','rt') as f:y=np.loadtxt(f,delimiter=',',skiprows=1)
 vgs=y[:,2]-y[:,3];vds=y[:,1]-y[:,3];ov=vgs-.5;reg=np.where(ov<=0,0,np.where(vds>=ov,2,1));dt=np.diff(y[:,0]);regions={n:float(np.sum(dt*(reg[:-1]==j))/sum(dt)) for j,n in enumerate(['cutoff','triode','saturation'])}
 out[name]={'frequency_Hz':freq,'peak_diff_V':float(max(abs(v))),'CM_mean_V':float(np.trapezoid(cm,t)/(t[-1]-t[0])),'m1_region_time_fractions_selected_cycle':regions,'supply_mean_W':float(-1.8*np.trapezoid(ivdd,t)/(t[-1]-t[0])),'supply_mean_W_selected_cycle':float(-1.8*np.trapezoid(y[:,4],y[:,0])/(y[-1,0]-y[0,0]))}
a.output.write_text(json.dumps(out,indent=2));print('recomputed',len(out),'finite cases')
