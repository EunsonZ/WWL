import importlib.util,json,sys
from pathlib import Path
from math import log,nextafter,inf,exp,expm1
from decimal import Decimal as D,localcontext
p=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('mathoracle',p/'independent_oracle.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
s=importlib.util.spec_from_file_location('business',p/'snapshot/dynamics_lab.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
rows=[]
for args in [(1e-6,100,10,1e-10),(1e-6,-100,10,1e-10),(100,0,1e-6,1),(1,1,1,100)]:
 ref=o.radial(*args);actual=m.radial_exact(*args);rel=abs(actual-float(ref))/abs(float(ref));assert rel<2e-14
 rows.append({'input':args,'radius_oracle_decimal':str(ref),'actual':actual,'relative_error':rel})
# Exact mathematical blow-up t*=log(101)/2 lies near several binary64 neighbours.
# Classify denominator sign at high precision, separately from the API rejection.
tstar=log(101)/2
boundary=[]
for t in [nextafter(tstar,-inf),tstar,nextafter(tstar,inf),tstar-1e-12]:
 ref=o.radial(1,-1,.1,t)
 try:value=m.radial_exact(1,-1,.1,t);status='finite';error=None
 except ValueError as e:value=None;status='refused';error=str(e)
 if t!=tstar-1e-12:assert status=='refused'
 else:assert status=='finite'
 boundary.append({'t_binary64':t,'mathematical_radius_at_decimal_roundtrip_t':None if ref is None else str(ref),'api_status':status,'api_value':value,'reason':error})
# expm1 finite small-time improvement: compare direct exp subtraction with high-precision expectation.
mu,alpha,r0,t=1e-6,100,10,1e-10
ref=float(o.radial(mu,alpha,r0,t));old=r0/(exp(-2*mu*t)+(alpha*r0*r0/mu)*(1-exp(-2*mu*t)))**.5
new=m.radial_exact(mu,alpha,r0,t)
r={'finite_domain_cases':rows,'near_cancellation':boundary,'small_time':{'input':[mu,alpha,r0,t],'high_precision':ref,'new_error':abs(new-ref),'old_subtraction_error':abs(old-ref)},'scope':'Boundary rejection is a numerical interface result, not a physical blow-up diagnosis; Decimal roundtrip inputs specify comparison values.'}
assert abs(new-ref)<abs(old-ref)
(p/'radial-boundary-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
