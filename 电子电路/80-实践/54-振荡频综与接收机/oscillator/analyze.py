from pathlib import Path
import numpy as np,json,gzip,hashlib,re,shutil
r=Path(__file__).resolve().parent;card=json.loads((r/'fixed-inputs.json').read_text());summary={};delivery=r/'reader-evidence';delivery.mkdir(exist_ok=True)
for name in card['cases']:
 d=r/name;out=delivery/name;out.mkdir(exist_ok=True);source=d/'waveform.txt';x=np.loadtxt(source,skiprows=1);t=x[:,0];v=x[:,1]-x[:,2];cm=(x[:,1]+x[:,2])/2;late=t>=1e-6;tt=t[late];vv=v[late]
 inds=np.where((vv[:-1]<=0)&(vv[1:]>0))[0];zc=tt[inds]-vv[inds]*(tt[inds+1]-tt[inds])/(vv[inds+1]-vv[inds]);freq=1/np.mean(np.diff(zc)) if len(zc)>2 and max(abs(vv))>1e-6 else None
 def avg(y,q):return float(np.trapezoid(y[q],t[q])/(t[q][-1]-t[q][0]))
 def half(a,b):q=(t>=a)&(t<=b);return float(max(abs(v[q])))
 op={k:float(val) for k,val in re.findall(r'^([^\n=]+)\s+=\s+([-+0-9.e]+)$',(d/'run.log').read_text(),re.M)}
 q=t>=(2e-6-(20/freq if freq else .2e-6));vp=x[q,1];vn=x[q,2];s=x[q,3];vgs=vn-s;vds=vp-s;vov=vgs-.5;region=np.where(vov<=0,0,np.where(vds>=vov,2,1));duration=np.diff(t[q]);fractions={n:float(np.sum(duration*(region[:-1]==i))/sum(duration)) for i,n in enumerate(['cutoff','triode','saturation'])}
 gm=op['@m1[gm]'];gds=op['@m1[gds]'];c=card|card['cases'][name];Rp=c['L_each_H']/(c['R_series_each_ohm']*c['C_each_F']);positive=1/(2*Rp);negative=-gm/2+gds/2
 summary[name]={'frequency_Hz':None if freq is None else float(freq),'peak_diff_V':float(max(abs(vv))),'peak_diff_first_late_half_V':half(1e-6,1.5e-6),'peak_diff_second_late_half_V':half(1.5e-6,2e-6),'CM_mean_V':avg(cm,late),'supply_mean_W':-c['VDD_V']*avg(x[:,4],late),'m1_region_time_fractions_last20cycles':fractions,'late_min_vds_V':float(vds.min()),'late_branch_current_range_A':[float(x[q,5:].min()),float(x[q,5:].max())],'op':op,'small_signal_approx':{'tank_Rp_ohm':Rp,'tank_positive_diff_S':positive,'active_negative_diff_S':negative,'net_diff_S':positive+negative,'ideal_lossless_Hz':float(1/(2*np.pi*np.sqrt(c['L_each_H']*c['C_each_F'])))},'startup_100ns_peak_diff_V':[half(i*1e-7,(i+1)*1e-7) for i in range(10)],'rows':len(x)}
 windows={}
 for label,mask in [('startup',t<=.2e-6),('late',t>=1e-6)]:
  a=np.column_stack([t[mask],v[mask],cm[mask],x[mask,4]]) if label=='late' else np.column_stack([t[mask],v[mask],cm[mask]]);path=out/(label+'.csv.gz')
  with gzip.open(path,'wt') as f:np.savetxt(f,a,delimiter=',',header='t_s,vdiff_V,CM_V,ivdd_A' if label=='late' else 't_s,vdiff_V,CM_V',comments='',fmt='%.17g')
  windows[label]={'rows':len(a),'first_actual_t_s':float(a[0,0]),'last_actual_t_s':float(a[-1,0]),'columns':['t_s','vdiff_V','CM_V','ivdd_A'] if label=='late' else ['t_s','vdiff_V','CM_V'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 # Exact actual samples for final complete cycle device-region/current inspection, with one bracketing point.
 start=zc[-2] if freq else 1.9e-6;ix=max(0,np.searchsorted(t,start)-1);end=np.searchsorted(t,zc[-1],side='right')+1 if freq else len(t);a=x[ix:end]
 with gzip.open(out/'device-cycle.csv.gz','wt') as f:np.savetxt(f,a,delimiter=',',header='t_s,vp_V,vn_V,vs_V,ivdd_A,id1_A,id2_A',comments='',fmt='%.17g')
 for file in ['osc.cir','run.log','command.json','configuration.json']:shutil.copy2(d/file,out/file)
 windows['device_cycle']={'rows':len(a),'first_actual_t_s':float(a[0,0]),'last_actual_t_s':float(a[-1,0]),'sha256':hashlib.sha256((out/'device-cycle.csv.gz').read_bytes()).hexdigest()}
 (out/'interface.json').write_text(json.dumps({'original_full_text_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_full_rows':len(x),'source_columns':['t_s','vp_V','vn_V','vs_V','ivdd_A','id1_A','id2_A'],'selection':'actual nonuniform rows; no resampling; startup0..200ns and late1..2us; omitted200ns..1us reproducible by deck','windows':windows},indent=2))
 # Archive complete original output only in process directory, outside reader package.
 with source.open('rb') as a,gzip.open(d/'waveform.txt.gz','wb') as b:shutil.copyfileobj(a,b)
 source.unlink()
(delivery/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({n:{k:v for k,v in s.items() if k in ['frequency_Hz','peak_diff_V','supply_mean_W','m1_region_time_fractions_last20cycles']} for n,s in summary.items()},indent=2))
for name in ['fixed-inputs.json','generate.py','run.py','analyze.py']:shutil.copy2(r/name,delivery/name)
print('reader total bytes',sum(p.stat().st_size for p in delivery.rglob('*') if p.is_file()))
