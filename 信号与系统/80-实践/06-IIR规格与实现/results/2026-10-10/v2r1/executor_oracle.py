"""Executor-owned Fraction/interval receipt checker; candidate output is evidence.
Expected gain expands coefficient autocorrelations; phase derivative uses degree/2-E/Q.
Does not use candidate expected/report/run/design or interval Horner as its oracle.
Only supplementary tested operations import frozen iir_lab public interfaces.
"""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,localcontext
import json,sys,struct,time,resource,hashlib
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'snapshot/candidate-v2/信号与系统/80-实践/06-IIR规格与实现'))
import iir_lab as subject

def frac(x):return F(Decimal(x)) if isinstance(x,str) else F(x)
def span_contains(span,x):return frac(span[0])<=x<=frac(span[1])
def scalar_records(rows):return [[F.from_float(v) for v in row] for row in rows]
def q_coeff(row):
 b0,b1,b2,a0,a1,a2=row
 return [1+a1*a1+a2*a2-2*a2,2*a1*(1+a2),4*a2]
def quadratic(q,c):return q[0]+q[1]*c+q[2]*c*c
def exact_min(q,lo,hi):
 points=[lo,hi]
 if q[2]>0:
  vertex=-q[1]/(2*q[2])
  if lo<=vertex<=hi:points.append(vertex)
 return min(quadratic(q,c) for c in points)
def transfer(rows,c):
 gain,lag=F(1),F(0)
 for b0,b1,b2,_,a1,a2 in rows:
  P=b0*b0+b1*b1+b2*b2+2*b1*(b0+b2)*c+2*b0*b2*(2*c*c-1)
  Q=1+a1*a1+a2*a2+2*a1*(1+a2)*c+2*a2*(2*c*c-1)
  assert Q>0
  degree=1 if b2==a2==0 else 2
  E=a1*a1+2*a2*a2+a1*(1+3*a2)*c+2*a2*(2*c*c-1)
  gain*=P/Q;lag+=F(degree,2)-E/Q
 return gain,lag

def partition(band):
 cells=sorted(band['accepted_cells']+band['unresolved_cells'],key=lambda c:frac(c['c'][0]));domain=list(map(frac,band['c_domain']));assert cells
 assert frac(cells[0]['c'][0])==domain[0] and frac(cells[-1]['c'][1])==domain[1]
 for i,cell in enumerate(cells):
  lo,hi=map(frac,cell['c']);assert lo<hi
  if i:assert frac(cells[i-1]['c'][1])==lo
 return len(cells)

def main():
 started=time.time();raw=BASE/'raw/iir-cli/results.json';report=json.loads(raw.read_text());base_rows=report['design']['sections'];certs=report['machine_certificates'];summaries=[];sample_witnesses=[]
 for name,cert in certs.items():
  selected=base_rows if name=='binary64_sos' else [[struct.unpack('!f',struct.pack('!f',v))[0] for v in row] for row in base_rows]
  rows=scalar_records(selected);assert len(rows)==14 and cert['certified'] is True and cert['status']=='certified'
  for expected,record in zip(rows,cert['coefficients']):
   actual=[F(*ratio) for ratio in record['dyadic_ratios']];assert actual==expected==[frac(v) for v in record['decimal_exact']]
   b0,b1,b2,a0,a1,a2=expected;assert a0==1
   if b2==a2==0:assert b0==b1 and abs(a1)<1
   else:assert b0==b2 and b1==2*b0 and -1<a2<1 and 1+a1+a2>0 and 1-a1+a2>0
   assert record['exact_schur_conditions'] is True
  endpoint=F(*cert['pass_endpoint_proof']['rational']);assert endpoint==frac(cert['pass_endpoint_proof']['c_lo']) and endpoint>0 and endpoint*endpoint<=F(1,2)
  assert list(map(frac,cert['bands']['pass']['c_domain']))==[endpoint,F(1)];assert list(map(frac,cert['bands']['stop']['c_domain']))==[F(-1),F(1,2)]
  model={'model':name,'coefficient_source':'original binary64 JSON' if name=='binary64_sos' else 'independent struct binary32 rounding of JSON binary64','endpoint_square_le_half':True,'bands':{}}
  qpolys=[q_coeff(r) for r in rows]
  for band_name,band in cert['bands'].items():
   assert band['certified'] is True and band['partition_covers_closed_domain'] is True and band['unresolved_cells']==[];count=partition(band)
   minimum_Q=F(10**10);allcells=band['accepted_cells'];bounds=[];lags=[]
   for cell in allcells:
    lo,hi=map(frac,cell['c']);qminimum=min(exact_min(q,lo,hi) for q in qpolys);qlower=frac(cell['minimum_Q_lower']);assert 0<qlower<=qminimum;minimum_Q=min(minimum_Q,qlower)
    amp=list(map(frac,cell['amplitude_squared']));assert amp[0]<=amp[1];bounds.append(amp)
    if band_name=='pass':
     assert F(9801,10000)<=amp[0] and amp[1]<=F(10201,10000);lag=list(map(frac,cell['group_delay_samples']));assert 0<=lag[0]<=lag[1]<=96;lags.append(lag)
    else:assert amp[0]>=0 and amp[1]<=F(1,1000000)
   assert frac(band['amplitude_squared_lower'])==min(x[0] for x in bounds) and frac(band['amplitude_squared_upper'])==max(x[1] for x in bounds)
   if lags:assert frac(band['delay_samples_lower'])==min(x[0] for x in lags) and frac(band['delay_samples_upper'])==max(x[1] for x in lags)
   # Up to65 distributed accepted cells, their two endpoints and rational interior 1/3.
   indices=sorted(set([0,len(allcells)-1]+[i*(len(allcells)-1)//64 for i in range(65)]))
   checked_points=0
   for i in indices:
    cell=allcells[i];lo,hi=map(frac,cell['c'])
    for label,c in [('left',lo),('third',(2*lo+hi)/3),('right',hi)]:
     gain,lag=transfer(rows,c);assert span_contains(cell['amplitude_squared'],gain)
     if band_name=='pass':assert span_contains(cell['group_delay_samples'],lag)
     checked_points+=1
     if i in (0,len(allcells)-1):sample_witnesses.append({'model':name,'band':band_name,'cell_index':i,'point':label,'c':str(c),'gain_squared_exact':str(gain),'phase_derivative_delay_exact':str(lag) if band_name=='pass' else None,'recorded_amplitude_interval':cell['amplitude_squared'],'recorded_delay_interval':cell['group_delay_samples']})
   model['bands'][band_name]={'all_cells':count,'cell_evaluations':band['cell_evaluations'],'maximum_depth':max(c['depth'] for c in allcells),'unresolved':0,'exact_all_partition_coverage':True,'all_Qlower_positive_and_below_exact_quadratic_minima':True,'minimum_recorded_Qlower':str(minimum_Q),'allcell_amplitude_bounds': [band['amplitude_squared_lower'],band['amplitude_squared_upper']],'allcell_delay_bounds':[band['delay_samples_lower'],band['delay_samples_upper']],'selected_cells_rational_points':checked_points}
  gain,_=transfer(rows,F(-1));assert gain==0;model['exact_Nyquist_gain_squared']=str(gain);summaries.append(model)
 # Independently constructed operation operands and corner extrema, precision24.
 iv=subject.Outward(24);operations=[]
 intervals=[(Decimal('-1.234567890123456789012345678901'),Decimal('2.75')),(Decimal('0.00000000000000000000000000013'),Decimal('0.41'))];denominator=(Decimal('-3.1'),Decimal('-.99999999999999999999999999999'))
 for x in intervals:
  for name,op,mathop in [('add',iv.add,lambda a,b:a+b),('sub',iv.sub,lambda a,b:a-b),('mul',iv.mul,lambda a,b:a*b),('div',iv.div,lambda a,b:a/b)]:
   observed=op(x,denominator);expected=[mathop(F(a),F(b)) for a in x for b in denominator];assert F(observed[0])<=min(expected) and max(expected)<=F(observed[1]);operations.append({'name':name,'x':list(map(str,x)),'y':list(map(str,denominator)),'actual_interval':list(map(str,observed)),'exact_min':str(min(expected)),'exact_max':str(max(expected))})
  sq=iv.square(x);values=[F(v)**2 for v in x];lo=F(0) if x[0]<=0<=x[1] else min(values);assert F(sq[0])<=lo and max(values)<=F(sq[1]);operations.append({'name':'square','x':list(map(str,x)),'actual_interval':list(map(str,sq)),'exact_min':str(lo),'exact_max':str(max(values))})
 with localcontext() as ctx:
  ctx.prec=3;point=iv.point(.1);assert F(point[0])==F.from_float(.1);seventh=iv.div(iv.point(1),iv.point(7));assert F(seventh[0])<=F(1,7)<=F(seventh[1])
 # Preserved conservative wide-cell None is correct; no dereference.
 fixture=[[.25,.25,0.,1.,-.5,0.],[.0625,.125,.0625,1.,-1.,.25]];prepared,_=subject.strict_sections(fixture,iv);wide=subject.strict_cell(prepared,Decimal('.9'),Decimal('1'),iv,True);assert wide is None
 trueQ=[exact_min(q_coeff(row),F(9,10),F(1)) for row in scalar_records(fixture)];assert all(q>0 for q in trueQ)
 exhausted=subject.strict_machine_certificate(report['design'],max_depth=1,max_cells=1);assert exhausted['certified'] is False and exhausted['status']=='not_certified';counts={k:partition(b) for k,b in exhausted['bands'].items()};assert any(b['unresolved_cells'] for b in exhausted['bands'].values())
 unsupported=[]
 for name in ['migration_96k','migration_5k']:
  r=subject.strict_machine_certificate(report[name]);assert r=={'status':'unsupported_specification','certified':False};unsupported.append({'model':name,'actual':r})
 rejections=[]
 for label,action in [('unstable',lambda:subject.strict_sections([[.1,.2,.1,1.,-2.,1.]],iv)),('nonsymmetric',lambda:subject.strict_sections([[.1,.3,.1,1.,-.5,.1]],iv)),('empty',lambda:subject.strict_sections([],iv)),('zero_divisor',lambda:iv.div(iv.point(1),(Decimal(-1),Decimal(1))))]:
  try:action()
  except ValueError as e:rejections.append({'case':label,'exception':'ValueError','message':str(e)})
  else:raise AssertionError(label)
 result={'status':'PASS','started_unix':started,'elapsed_seconds':time.time()-started,'results_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'models':summaries,'fraction_point_witnesses':sample_witnesses,'outward_operation_oracle':operations,'external_context_precision3':{'float_point_exact':True,'one_seventh_enclosed':True},'wide_fixture':{'returned':None,'exact_Q_minima':[str(x) for x in trueQ],'meaning':'conservative outward Horner rejects wide cell despite positive true Q; no claim cell enclosure exists'},'resource_false':{'certified':exhausted['certified'],'status':exhausted['status'],'exact_partition_counts':counts,'full_result':subject.json_ready(exhausted)},'unsupported':unsupported,'rejections':rejections,'original_test_suite_failure':'preserved separately; this supplementary oracle PASS does not replace fixed unittest outcome','resource_self_ru_maxrss_bytes_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'proof_boundary':'All partitions/Q minima/limits checked; finite rational points supplement source inclusion proof, not replacement. Fixed dyadic linear transfer certificate does not certify per-operation binary32 recursive trajectory.'}
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
