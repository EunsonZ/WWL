from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
base=Path(__file__).resolve().parent
# Independent closed normal objective 2D, Cramer's determinants.
def weighted(rows,y,l,p,center):
 n=len(rows);weights=[l**(n-1-i) for i in range(n)];reg=p*l**n
 R=[[sum(w*x[i]*x[j] for w,x in zip(weights,rows))+(reg if i==j else 0) for j in range(2)] for i in range(2)]
 b=[sum(w*x[i]*d for w,x,d in zip(weights,rows,y))+reg*center[i] for i in range(2)]
 det=R[0][0]*R[1][1]-R[0][1]*R[1][0]
 return [(b[0]*R[1][1]-R[0][1]*b[1])/det,(R[0][0]*b[1]-b[0]*R[1][0])/det]
rows=[[F(1),F(0)],[F(0),F(1)],[F(1),F(1)]];y=[F(1,2),F(-1,4),F(1,4)]
prefixes=[]
for l,expected in [(F(1),[F(9,32),F(-3,32)]),(F(1,2),[F(31,79),F(-13,79)])]:
 assert weighted(rows,y,l,F(1),[F(0),F(0)])==expected
 for center in [[F(0),F(0)],[F(1,3),F(-2,5)]]:
  prefixes.append({'lambda':str(l),'center':list(map(str,center)),'prefix_solutions':[list(map(str,weighted(rows[:n],y[:n],l,F(1),center))) for n in range(1,4)]})
closed=[]
for k in [F(0),F(1)]:
 physical=[(r,(r-k*e)/(1+k/2),e) for r,e in product([-1,1],repeat=2)]
 observed=[(r,u,u/2+e) for r,u,e in physical]
 ols=sum(u*v for r,u,v in observed)/sum(u*u for r,u,v in observed);iv=sum(r*v for r,u,v in observed)/sum(r*u for r,u,v in observed)
 assert ols==(F(1,2) if k==0 else F(-1,4)) and iv==F(1,2)
 closed.append({'kappa':str(k),'OLS':str(ols),'IV':str(iv)})
# For random four-axis phi=+/-sqrt(2)*e_i, gradient map acts by 1-2mu on chosen coordinate.
mu=F(3,2);t=1-2*mu;init=[F(1),F(2)];outputs=[[t*init[0],init[1]],[t*init[0],init[1]],[init[0],t*init[1]],[init[0],t*init[1]]]
mean=[sum(row[i] for row in outputs)/4 for i in range(2)];sq=sum(sum(v*v for v in row) for row in outputs)/4;assert mean==[-v/2 for v in init] and sq==F(5,2)*sum(v*v for v in init)
# ARX physical Var(x)=(.25^2*Var(u)+.75)/(1-.5^2)=13/12.
varx=(F(1,16)+F(3,4))/(1-F(1,4));population_a=(varx/2)/(varx+F(1,4));assert population_a==F(13,32)
result={'status':'PASS','business_source_imported':False,'short_prefix_exact':prefixes,'closed_loop_exact':closed,'LMS_four_axis':{'mean_factor':'-1/2','mean_square_factor':'5/2','mean':list(map(str,mean)),'mean_square_norm':str(sq),'model':'iid independent draws; no reused temporal regressor model'},'physical_ARX':{'state_variance':str(varx),'ideal_a':'1/2','measured_a_OLS':str(population_a),'b':'1/4','lagged_output_true_error_moment_ideal':'0','lagged_output_true_error_moment_measured':'-1/8'},'impulse_theta':['1/2','-1/4'],'constant_information_rank':1,'index_contract':{'FIR':{'train':[3,1024],'validation':[1024,2048],'test':[2048,4096]},'AR':{'burn':[0,256],'train':[256,2304],'test':[2304,6400]},'physical_cross_lag':'u[k-lag] times e[k], both within test window; lag0 is u[k], predictor uses u[k-1] at lag1; subtract full-window means and divide by 4096 at every AR lag'}}
(base/'analytic-expected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','expected_before_runtime':True}))
