"""Independent verification. Never imports business implementation or its tests.
Exact kernel K(s)=exp(-k(T-s)); EM kernel H(s)=a^(m-1-i) on interval i.
Integrate (H-K)^2 interval by interval in Decimal, without geometric sum formulas.
Reconstruct MC directly with weighted terminal sums and fine time prefix kernels.
"""
import json, math, csv, time, resource, os
from pathlib import Path
from decimal import Decimal, localcontext
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np
base=Path(__file__).resolve().parent
started=time.monotonic()
c=json.loads((base/'snapshot/fixed-input.json').read_text());r=json.loads((base/'output/report.json').read_text())
checks=[]
def near(label,actual,expected,atol=1e-12):
 delta=abs(float(actual)-float(expected)); checks.append({'check':label,'actual':float(actual),'independent':float(expected),'absolute_difference':delta,'tolerance':atol,'pass':delta<=atol}); assert delta<=atol,(label,delta)
with localcontext() as ctx:
 ctx.prec=70
 D=lambda x:Decimal(str(x))
 k,mu,sigma,x0,T=[D(c[x]) for x in ('kappa','mu','sigma','x0','T')]
 exact_mean=mu+(x0-mu)*(-k*T).exp()
 exact_var=sigma*sigma*(1-(-2*k*T).exp())/(2*k)
 near('exact mean',r['exact_theory']['mean'],exact_mean)
 near('exact variance',r['exact_theory']['variance'],exact_var)
 theory=[]
 for row in r['rows']:
  m=row['theory']['steps'];h=T/D(m);a=1-k*h
  em_mean=mu+(x0-mu)*a**m
  var=Decimal(0);cross=Decimal(0);kernel_error=Decimal(0)
  for i in range(m):
   weight=a**(m-1-i);left=D(i)*h;right=D(i+1)*h
   intK=((-k*(T-right)).exp()-(-k*(T-left)).exp())/k
   intK2=((-2*k*(T-right)).exp()-(-2*k*(T-left)).exp())/(2*k)
   var+=sigma*sigma*weight*weight*h
   cross+=sigma*sigma*weight*intK
   kernel_error+=sigma*sigma*(weight*weight*h-2*weight*intK+intK2)
  bias=em_mean-exact_mean;mse=bias*bias+kernel_error
  values={'mean':em_mean,'variance':var,'second_moment':var+em_mean*em_mean,'cross_covariance':cross,'strong_mse':mse,'strong_rmse':mse.sqrt(),'weak_mean_bias':bias,'weak_second_bias':var+em_mean*em_mean-exact_var-exact_mean*exact_mean,'independent_noise_mse':bias*bias+var+exact_var}
  for key,value in values.items():near(f'kernel integral steps={m} {key}',row['theory'][key],value)
  theory.append({'steps':m,'h':float(h),'kernel_error_variance':str(kernel_error),'strong_mse':str(mse),'strong_rmse':str(mse.sqrt()),'independent_noise_mse':str(values['independent_noise_mse'])})
 n=c['paths'];fine=c['fine_steps'];dt=float(T)/fine;kf=float(k)
 rng=np.random.default_rng(c['seed']); terminals={m:np.empty(n) for m in c['steps']}; exact=np.empty(n);traces={}
 # Independent integral coefficients for joint normal pair; direct mathematical moments.
 vJ=float((1-(-2*k*D(str(dt))).exp())/(2*k));cov=float((1-(-k*D(str(dt))).exp())/k)
 residual=vJ-cov*cov/dt
 for start in range(0,n,c['chunk']):
  size=min(c['chunk'],n-start);z=rng.standard_normal((size,fine,2))
  dw=math.sqrt(dt)*z[:,:,0];J=(cov/dt)*dw+math.sqrt(residual)*z[:,:,1]
  exact[start:start+size]=float(mu)+(float(x0)-float(mu))*math.exp(-kf*float(T))+float(sigma)*(J@np.exp(-kf*dt*np.arange(fine-1,-1,-1)))
  for m in c['steps']:
   q=fine//m;step=float(T)/m;a=1-kf*step
   # Every fine increment receives its coarse EM terminal weight.
   w=np.repeat(a**np.arange(m-1,-1,-1),q)
   terminals[m][start:start+size]=float(mu)+(float(x0)-float(mu))*a**m+float(sigma)*(dw@w)
   if start==0:
    for p in range(c['trace_paths']):
     for j in range(m+1):
      end=j*q
      em=float(mu)+(float(x0)-float(mu))*a**j+float(sigma)*np.dot(dw[p,:end],np.repeat(a**np.arange(j-1,-1,-1),q))
      ex=float(mu)+(float(x0)-float(mu))*math.exp(-kf*end*dt)+float(sigma)*np.dot(J[p,:end],np.exp(-kf*dt*np.arange(end-1,-1,-1)))
      traces[(p,m,j)]=(em,ex)
 independent=float(exact_mean)+math.sqrt(float(exact_var))*np.random.default_rng(c['independent_seed']).standard_normal(n)
 def stats(label,values,reported):
  near(label+' estimate',reported['estimate'],np.mean(values))
  near(label+' SE',reported['se'],np.std(values,ddof=1)/math.sqrt(n))
 for name,arr in [('coupled',exact),('independent_terminal',independent)]:
  stats(name+' mean',arr,r['exact_terminal_checks'][name]['mean']);stats(name+' second',arr*arr,r['exact_terminal_checks'][name]['second_moment'])
 for row in r['rows']:
  m=row['theory']['steps'];em=terminals[m];err=em-exact
  for key,values in [('strong_mse',err*err),('weak_mean_bias',err),('weak_second_bias',em*em-exact*exact),('euler_mean',em),('euler_second_moment',em*em),('independent_noise_mse',(em-independent)**2)]:stats(f'm={m} {key}',values,row[key])
 trace_max=0.;common_max=0.;csv_rows=list(csv.DictReader((base/'output/traces.csv').open()))
 indexed={}
 for row in csv_rows:
  p=int(row['path']);m=int(row['steps']);j=round(float(row['time'])*m/float(T));em,ex=traces[(p,m,j)]
  trace_max=max(trace_max,abs(float(row['euler'])-em),abs(float(row['exact'])-ex));indexed[(p,m,j)]=float(row['exact'])
 for p in range(c['trace_paths']):
  for j in range(9):common_max=max(common_max,abs(indexed[(p,8,j)]-indexed[(p,64,j*8)]))
 assert trace_max<1e-12 and common_max<1e-12
 slopes=[math.log(float(theory[i]['strong_rmse'])/float(theory[i+1]['strong_rmse']))/math.log(2) for i in range(3)]
 result={'status':'PASS','source_imported':False,'author_test_used_as_oracle':False,'decimal_precision':70,'method':'Interval-by-interval integrals of EM terminal kernel minus exact OU terminal kernel; independent linear terminal sums and prefix kernels','checks':checks,'analytic_kernel_rows':theory,'analytic_local_rmse_orders':slopes,'trace_rows_checked':len(csv_rows),'trace_independent_max_abs':trace_max,'eight_vs_sixtyfour_public_time_max_abs':common_max,'resource':{'wall_seconds':time.monotonic()-started,'self_max_rss_bytes_Darwin':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'interpretation':'This additive-noise OU endpoint RMS error approaches order 1; this numerical audit does not prove general Ito/EM convergence. Weak moment sampling noise is distinct from paired strong error. Independent-noise MSE stays nonzero as h shrinks. Estimated 6-SE bands are diagnostic, not a guarantee. No native Obsidian, hardware, human learning, real financial use, or SVG rendering assessed.'}
 (base/'independent-oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':result['status'],'check_count':len(checks),'trace_rows':len(csv_rows),'trace_max':trace_max,'common_time_max':common_max,'analytic_orders':slopes,'resource':result['resource']}))
