"""Directly read first CSV; exact binary-rational fit and independent loss moments."""
import pathlib,json,csv,math
from fractions import Fraction as F
root=pathlib.Path(__file__).resolve().parent;checks=[];tol=json.loads((root/'fixed-inputs.json').read_text())['comparison_tolerances_declared_before_run'];ABS=tol['deterministic_absolute'];REL=tol['deterministic_relative']
def check(name,a,b):checks.append({'check':name,'match':a==b,'actual':str(a),'expected':str(b)})
def close(name,a,b):checks.append({'check':name,'match':math.isclose(float(a),float(b),abs_tol=ABS,rel_tol=REL),'absolute_difference':abs(float(a)-float(b))})
def read(path):return list(csv.DictReader(path.open()))
for run in ['preflight','standard']:
    data=json.loads((root/run/'results.json').read_text());train=read(root/run/'train.csv');test=read(root/run/'test.csv');changed=read(root/run/'correlated_test.csv');est=read(root/run/'estimates.csv')
    ft=[[F(float(train[n]['x_V'])),F(float(train[n-1]['x_V']))] for n in range(1,len(train))];ds=[F(float(v['s_V'])) for v in train[1:]];N=len(ds)
    R=[[sum((row[i]*row[j] for row in ft),F(0))/N for j in range(2)] for i in range(2)];p=[sum((row[i]*d for row,d in zip(ft,ds)),F(0))/N for i in range(2)];det=R[0][0]*R[1][1]-R[0][1]*R[1][0];w=[(p[0]*R[1][1]-p[1]*R[0][1])/det,(R[0][0]*p[1]-R[1][0]*p[0])/det]
    for i in range(2):
        close(run+'/CSV_fraction_fit/p'+str(i),data['fits'][0]['p'][i],p[i]);close(run+'/CSV_fraction_fit/w'+str(i),data['fits'][0]['weights'][i],w[i])
        for j in range(2):close(run+'/CSV_fraction_fit/R'+str(i)+str(j),data['fits'][0]['R'][i][j],R[i][j])
    times=[int(row['n']) for row in est];check(run+'/shared_window',times,list(range(128,len(test)-32)))
    check(run+'/future_range_in_bounds',all(n-32>=0 and n+32<len(test) for n in times),True)
    for name in list(est[0])[1:]:
        error=[float(test[n]['s_V'])-float(row[name]) for n,row in zip(times,est)]
        close(run+'/CSV_direct_mse/'+name,data['observed_mse'][name]['values'][0],math.fsum(e*e for e in error)/len(error));moment=data['observed_error_moments'][name][0]
        close(run+'/CSV_direct_error_mean/'+name,moment['mean_error'],math.fsum(error)/len(error))
        for lag in [-1,0,1]:close(run+'/CSV_direct_error_moment/'+name+'/'+str(lag),moment['error_observation_moments'][str(lag)],math.fsum(e*float(test[n-lag]['x_V']) for n,e in zip(times,error))/len(error))
    for name,wc in [('wrong_noise_old_weights',[F(7,15),F(2,15)]),('correlated_noise_current',[F(1,2),F(0)])]:
        error=[float(changed[n]['s_V'])-float(wc[0])*float(changed[n]['x_V'])-float(wc[1])*float(changed[n-1]['x_V']) for n in range(1,len(changed))];moment=data['observed_error_moments'][name][0]
        close(run+'/CSV_changed_mse/'+name,data['observed_mse'][name]['values'][0],math.fsum(e*e for e in error)/len(error))
        for lag in [0,1]:close(run+'/CSV_changed_moment/'+name+'/'+str(lag),moment['error_observation_moments'][str(lag)],math.fsum(e*float(changed[n-lag]['x_V']) for n,e in zip(range(1,len(changed)),error))/len(error))
# Population loss of the actual radius32 bilateral kernel; not confused with finite observation.
pole=2-math.sqrt(3);indices=list(range(-32,33));weights=[math.sqrt(3)/4*pole**abs(k) for k in indices]
mse=1-2*math.fsum(a*.5**abs(k) for a,k in zip(weights,indices))+math.fsum(a*b*(.5**abs(k-l)+int(k==l)) for a,k in zip(weights,indices) for b,l in zip(weights,indices))
close('bilateral_infinite_to_radius32_theory',mse,math.sqrt(3)/4)
report={'business_source_imported':False,'checks_total':len(checks),'all_match':all(v['match'] for v in checks),'failed_checks':[v for v in checks if not v['match']],'first_csv_fit_method':'exact Fraction.from_float values; coefficient sums then closed 2x2 determinant solve','radius32_population_mse_float':mse,'bilateral_infinite_population_mse_float':math.sqrt(3)/4,'checks':checks}
(root/'csv-oracle-results.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
if not report['all_match']:raise SystemExit(1)
