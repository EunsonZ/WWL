"""CSV-first independent normal-equation and physical-index audit. No business imports."""
import json,csv,math,itertools,random,time
from pathlib import Path
from fractions import Fraction as F
base=Path(__file__).resolve().parent;start=time.monotonic();report=json.loads((base/'output/results.json').read_text());expected=json.loads((base/'analytic-expected.json').read_text());probes=json.loads((base/'source-probes.json').read_text());checks=[]
def near(label,a,b,tol=1e-10):
 if isinstance(a,list):
  assert len(a)==len(b),(label,'shape')
  for i,(x,y) in enumerate(zip(a,b)):near(label+f'[{i}]',x,y,tol)
 else:
  delta=abs(float(a)-float(b));assert delta<=tol,(label,a,b,delta)
  checks.append({'check':label,'abs_difference':delta,'tolerance':tol})
def read(name):
 with (base/'output'/f'{name}.csv').open() as f:rows=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
 assert all(int(row['k'])==i for i,row in enumerate(rows));return rows
data={name:read(name) for name in ['fir','ar','drift','later_validation']}
assert [len(data[name]) for name in data]==[4096,6400,2048,1024]
def det(A):
 if len(A)==1:return A[0][0]
 return math.fsum(((-1)**j)*A[0][j]*det([row[:j]+row[j+1:] for row in A[1:]]) for j in range(len(A)))
def resolve(A,b):
 determinant=det(A);assert abs(determinant)>1e-12
 return [det([[b[i] if j==col else A[i][j] for j in range(len(b))] for i in range(len(b))])/determinant for col in range(len(b))]
def objective(rows,target,prior=1e-6,lam=1):
 n=len(rows);m=len(rows[0]);weight=[lam**(n-1-k) for k in range(n)]
 R=[[math.fsum(w*phi[i]*phi[j] for w,phi in zip(weight,rows))+(prior*lam**n if i==j else 0) for j in range(m)] for i in range(m)]
 b=[math.fsum(w*phi[i]*y for w,phi,y in zip(weight,rows,target)) for i in range(m)]
 return R,b,resolve(R,b)
def mse(actual,pred):return math.fsum((a-b)**2 for a,b in zip(actual,pred))/len(actual)
def diagnostics(label,u,e,observed):
 n=len(e);um=math.fsum(u)/n;em=math.fsum(e)/n
 auto=[math.fsum((e[k]-em)*(e[k-l]-em) for k in range(l,n))/n for l in range(9)]
 cross=[math.fsum((u[k-l]-um)*(e[k]-em) for k in range(l,n))/n for l in range(9)]
 near(label+' residual mean',observed['residual_mean'],em);near(label+' all residual lags',observed['residual_covariance'],auto);near(label+' all physical input lags',observed['input_residual_covariance'],cross)
 assert observed['denominator']==n and observed['lag_range']==[0,8]
 return {'residual_mean':em,'residual_covariance':auto,'input_residual_covariance':cross,'denominator':n}
def fitcheck(label,observed,rows,target):
 R,b,theta=objective(rows,target);near(label+' R',observed['R'],R);near(label+' b',observed['b'],b);near(label+' theta',observed['theta'],theta);return theta
fir=data['fir'];u=[x['u'] for x in fir];y=[x['y'] for x in fir];val=[]
assert report['fir_order_validation']['splits']=={'train':[3,1024],'validation':[1024,2048],'test':[2048,4096]}
for candidate in report['fir_order_validation']['candidates']:
 m=candidate['order'];rows=[[u[k-j] for j in range(m)] for k in range(3,1024)]
 theta=fitcheck(f'FIR{m}',candidate['fit'],rows,y[3:1024]);error=mse(y[1024:2048],[math.fsum(theta[j]*u[k-j] for j in range(m)) for k in range(1024,2048)]);near(f'FIR{m} validation',candidate['validation_mse'],error);val.append((error,m,theta))
chosen=min(val,key=lambda x:x[0]);assert report['fir_order_validation']['selected_order']==chosen[1]
res=[y[k]-math.fsum(chosen[2][j]*u[k-j] for j in range(chosen[1])) for k in range(2048,4096)]
near('FIR frozen test MSE',report['fir_order_validation']['frozen_test_mse'],math.fsum(x*x for x in res)/2048);fd=diagnostics('FIR',u[2048:],res,report['fir_order_validation']['diagnostics'])
ar=data['ar'];ua=[x['u'] for x in ar];assert report['AR_splits']==expected['index_contract']['AR'];ar_results={}
for name,col in [('ideal_observation','x'),('output_measurement_noise','y_measured')]:
 obs=[x[col] for x in ar];record=report['same_physical_AR_two_noise_paths'][name];rows=[[obs[k-1],ua[k-1]] for k in range(256,2304)]
 a,b=fitcheck(name,record['fit'],rows,obs[256:2304]);one=[a*obs[k-1]+b*ua[k-1] for k in range(2304,6400)]
 # Free simulation starts only with the last training observation, then its own history.
 state=obs[2303];free=[]
 for k in range(2304,6400):state=a*state+b*ua[k-1];free.append(state)
 near(name+' one MSE',record['one_step_mse'],mse(obs[2304:],one));near(name+' free MSE',record['free_run_mse'],mse(obs[2304:],free))
 residual=[obs[k]-one[k-2304] for k in range(2304,6400)];d=diagnostics(name,ua[2304:6400],residual,record['diagnostics'])
 true_error=[obs[k]-.5*obs[k-1]-.25*ua[k-1] for k in range(2304,6400)]
 moment=math.fsum(obs[k-1]*true_error[k-2304] for k in range(2304,6400))/4096;near(name+' true fixed parameter error moment',record['lagged_output_times_true_error_mean'],moment)
 ar_results[name]={'theta':[a,b],'one_mse':mse(obs[2304:],one),'free_mse':mse(obs[2304:],free),'true_parameter_error_moment':moment,'all_lags':d,'free_initial':obs[2303],'population_a':.5 if col=='x' else 13/32}
# Verify all original physical records regenerate exactly from declared seeds, independently.
rng=random.Random(180000);su=[rng.choice([-1.,1.]) for _ in range(4096)];sy=[.5*su[k]-.25*(su[k-1] if k else 0)+.05*rng.gauss(0,1) for k in range(4096)]
near('seed FIR all u',u,su,0);near('seed FIR all y',y,sy,0)
rng=random.Random(180100);sa=[rng.choice([-1.,1.]) for _ in range(6400)];x=0;xs=[];ys=[]
for k in range(6400):x=.5*x+.25*(sa[k-1] if k else 0)+math.sqrt(.75)*rng.gauss(0,1);xs.append(x);ys.append(x+.5*rng.gauss(0,1))
near('seed AR input',ua,sa,0);near('seed shared physical x',[r['x'] for r in ar],xs,0);near('seed measured output',[r['y_measured'] for r in ar],ys,0)
drift=data['drift'];du=[r['u'] for r in drift];dy=[r['y'] for r in drift];later=data['later_validation'];lu=[r['u'] for r in later];ly=[r['y'] for r in later]
rng=random.Random(180200);sd=[rng.choice([-1.,1.]) for _ in range(2048)];sh=[.5 if k<1024 else .5+.3*(k-1024)/1023 for k in range(2048)];sy=[sh[k]*sd[k]-.25*(sd[k-1] if k else 0)+.05*rng.gauss(0,1) for k in range(2048)]
near('seed drift u',du,sd,0);near('seed drift y',dy,sy,0);near('drift truth schedule',[r['h0_true'] for r in drift],sh,0)
rng=random.Random(180300);sl=[rng.choice([-1.,1.]) for _ in range(1024)];sy=[.8*sl[k]-.25*(sl[k-1] if k else 0)+.05*rng.gauss(0,1) for k in range(1024)]
near('independent later seed u',lu,sl,0);near('independent later y',ly,sy,0)
rowsd=[[du[k],du[k-1]] for k in range(1,2048)];target=dy[1:];dr={}
for name,lam in [('RLS_lambda_1',1),('RLS_lambda_098',.98)]:
 observed=report['drift'][name];A=[[.01,0],[0,.01]];B=[0.,0.];maxdelta=0.
 for k,(phi,value) in enumerate(zip(rowsd,target)):
  # Objective information recurrence, not gain/inverse recursive least squares.
  A=[[lam*A[i][j]+phi[i]*phi[j] for j in range(2)] for i in range(2)];B=[lam*B[i]+phi[i]*value for i in range(2)];theta=resolve(A,B)
  maxdelta=max(maxdelta,max(abs(theta[j]-observed['trajectory'][k][j]) for j in range(2)))
 assert maxdelta<=1e-10
 R,b,theta=objective(rowsd,target,prior=.01,lam=lam);near(name+' direct final objective',observed['theta'],theta)
 inverse=[[A[1][1]/det(A),-A[0][1]/det(A)],[-A[1][0]/det(A),A[0][0]/det(A)]];near(name+' final inverse',observed['inverse_information'],inverse)
 latermse=mse(ly[1:],[theta[0]*lu[k]+theta[1]*lu[k-1] for k in range(1,1024)]);near(name+' frozen later validation',observed['later_independent_mse'],latermse);dr[name]={'theta':theta,'later_mse':latermse,'all_prefix_objective_max_difference':maxdelta,'prefix_count':len(target)}
observed=report['drift']['LMS_mu_002'];theta=[0.,0.];maxdelta=0.
for k,(phi,value) in enumerate(zip(rowsd,target)):
 # Gradient of 1/2 squared prediction loss at the previous iterate.
 error=theta[0]*phi[0]+theta[1]*phi[1]-value;theta=[theta[j]-.02*error*phi[j] for j in range(2)];maxdelta=max(maxdelta,max(abs(theta[j]-observed['trajectory'][k][j]) for j in range(2)))
assert maxdelta<1e-12;near('LMS final',observed['theta'],theta);latermse=mse(ly[1:],[theta[0]*lu[k]+theta[1]*lu[k-1] for k in range(1,1024)]);near('LMS frozen validation',observed['later_independent_mse'],latermse);dr['LMS_mu_002']={'theta':theta,'later_mse':latermse,'all_prefix_gradient_max_difference':maxdelta,'prefix_count':len(target)}
# Fraction expected was recorded before runtime; compare all source nonzero-center prefixes.
for observed,exact in zip(probes['short_prefix'],expected['short_prefix_exact']):
 near('prefix lambda',observed['lambda'],F(exact['lambda']));near('prefix center',observed['center'],[F(x) for x in exact['center']]);oracle=[[float(F(x)) for x in row] for row in exact['prefix_solutions']]
 near('short source RLS every exact prefix',observed['rls']['trajectory'],oracle);near('short batch every exact prefix',[x['theta'] for x in observed['batch_prefix']],oracle)
for lam,truth in [('1.0',[9/32,-3/32]),('0.5',[31/79,-13/79])]:
 near('short report batch'+lam,report['short_batch_RLS'][lam]['batch']['theta'],truth);near('short report RLS'+lam,report['short_batch_RLS'][lam]['rls']['theta'],truth)
near('impulse',probes['impulse'],[.5,-.25]);errors=[[theta+truth for theta,truth in zip(row['theta'],[1.,2.])] for row in probes['LMS_iid_four_axis']];near('four axis mean',[math.fsum(row[j] for row in errors)/4 for j in range(2)],[-.5,-1.]);near('four axis mean square norm',math.fsum(math.fsum(x*x for x in row) for row in errors)/4,12.5)
result={'status':'PASS','business_source_imported':False,'checks_count':len(checks),'max_abs_comparison_difference':max(x['abs_difference'] for x in checks),'fir':{'validation':[{'order':m,'mse':e,'theta':t} for e,m,t in val],'selected_order':chosen[1],'all_lags':fd,'test_mse':report['fir_order_validation']['frozen_test_mse']},'AR':ar_results,'drift_frozen_validation':dr,'later_validation_winner':min(dr,key=lambda x:dr[x]['later_mse']),'seed_record_lengths':{name:len(rows) for name,rows in data.items()},'physical_all_seed_regeneration_match':True,'wall_seconds':time.monotonic()-start,'scope':'Finite synthetic model. Sample true-error moments fluctuate around analytic values; estimated OLS is not forced to equal population OLS. No general LMS stability/real noise/closed-loop/device certificate.'}
(base/'independent-oracle.json').write_text(json.dumps(result,indent=2)+'\n');(base/'independent-comparisons.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(result))
