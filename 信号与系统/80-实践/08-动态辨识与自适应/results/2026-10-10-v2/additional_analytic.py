from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json
base=Path(__file__).resolve().parent
samples=[(F(x),F(v)/2,F(w),F(n)/2) for x,v,w,n in product([-1,1],repeat=4)]
ideal=sum(x*w for x,v,w,n in samples)/16;measured=sum((x+v)*(w+n-v/2) for x,v,w,n in samples)/16
assert ideal==0 and measured==F(-1,8)
constant_gram=[[F(3),F(3)],[F(3),F(3)]];assert constant_gram[0][0]*constant_gram[1][1]-constant_gram[0][1]*constant_gram[1][0]==0
impulse_average=[[F(1,1000),F(0)],[F(0),F(1,1000)]]
theta=[F(1,2),F(-1,4)];center=[F(1,5),F(-1,3)];D=[F(10),F(1,10)];z=[theta[i]/D[i] for i in range(2)];zc=[center[i]/D[i] for i in range(2)]
original=sum((theta[i]-center[i])**2 for i in range(2));transformed=sum(D[i]**2*(z[i]-zc[i])**2 for i in range(2));wrong=sum((z[i]-zc[i])**2 for i in range(2));assert original==transformed and wrong!=original
# Two history spaces: stable one-step fit does not control independent initial mismatch.
a=F(11,10);delta=F(1,100);observed=[a**k for k in range(101)];one=[a*observed[k-1] for k in range(1,101)];free=[a**k*(1-delta) for k in range(1,101)]
assert one==observed[1:] and all(observed[k]-free[k-1]==delta*a**k for k in range(1,101))
u=[F(1),F(4),F(-2)];e=[F(2),F(-1),F(3)];um=sum(u)/3;em=sum(e)/3;cross=[sum((u[k-l]-um)*(e[k]-em) for k in range(l,3))/3 for l in range(3)];assert cross==[F(-4),F(5,3),F(0)]
(base/'additional-analytic-checks.json').write_text(json.dumps({'status':'PASS','source_imported':False,'ideal_true_error_moment':str(ideal),'measurement_true_error_moment':str(measured),'constant_information_rank':1,'finite_impulse_average_1000':[[str(x) for x in row] for row in impulse_average],'prior_original':str(original),'prior_DtR0D':str(transformed),'wrong_unscaled_coordinate_prior':str(wrong),'one_step_vs_free_initial_final_error':str(observed[-1]-free[-1]),'independent_centering_lag_fixture':list(map(str,cross))},indent=2)+'\n');print('PASS: independent exact noise/coordinate/information/history/centering checks')
