---
type: code-mirror
domain: electronics
stage: 3
aliases: []
sources: []
prerequisites: []
---
# test_pipeline_lab 源码镜像

真源为同目录 `test_pipeline_lab.py`；SHA256 `fa919e2c8400e84a4f7e00aa331791fea8fcf3d6cf0d71a5417a7d7f7eb83258`。改动需同步源码及此镜像。

```python
"""Independent finite transfer checks; not HDL/SPICE/hardware."""
import unittest,os,math,cmath,sys,tempfile,json
from unittest.mock import Mock
from pathlib import Path
from fractions import Fraction
import pipeline_lab as p
V=Path(os.environ.get('WWL_SOURCE_VAULT',Path(__file__).resolve().parents[3]))
class PipelineTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=p.run(V)
 def test_directed_preedge_history(self):
  r=self.data['L09']['normal']['rows'];queue=[]
  for row in r:
   self.assertEqual(row['valid'],bool(queue))
   if queue:self.assertEqual(row['data'],queue[0])
   if row['pop']:queue.pop(0)
   if row['push']:queue.append(row['source'])
   self.assertEqual(row['after_full'],bool(queue))
   if queue:self.assertEqual(row['after_data'],queue[0])
  self.assertEqual(self.data['L09']['fault']['failure_cycle'],2)
  self.assertEqual(self.data['L09']['fault']['rows'][-1]['observe_ns'],36)
 def test_integer_filter_independent_whole_history(self):
  rows=self.data['L10']['valid']['samples'];q=[r['code']-2048 for r in rows];state=0
  for n,row in enumerate(rows):
   state=round(Fraction(3*state+q[n],4));fir=round(Fraction(q[n]+(2*q[n-1] if n else 0)+(q[n-2] if n>1 else 0),4))
   self.assertEqual(row['IIR_count'],state);self.assertEqual(row['FIR_count'],fir);self.assertEqual(row['FIR_valid'],n>=2)
 def test_deadline_full_recurrence_and_discard(self):
  e=self.data['L10']['valid']['events'];finish=0
  for k,row in enumerate(e):
   finish=max((k+1)*4000000+300000,finish)+2000000
   self.assertEqual(row['cpu_finish_ns'],finish);self.assertEqual(row['slack_ns'],1700000)
  self.assertTrue(all(r['status']=='discard' for r in self.data['L10']['overrun']['samples']))
  self.assertNotIn('IIR_count',self.data['L10']['overrun']['samples'][0])
 def test_slot_stale_gap_and_invalid_before_mutation(self):
  e=p.load(V,'embedded');f=e.CountFilter();f.process([2048],0,0);before=(f.next,f.state,list(f.history))
  for codes,idx in (([True],1),([2048],2),([2048+0j],1),([float('nan')],1)):
   with self.assertRaises(ValueError):f.process(codes,idx,0)
   self.assertEqual((f.next,f.state,f.history),before)
  ring=e.OwnedRing();t=ring.publish(0,[2048]);ring.take(t);ring.release(t);new=ring.publish(0,[2050])
  with self.assertRaises(ValueError):ring.release(t)
  self.assertEqual(ring.take(new),(2050,))
 def test_reflection_KCL_boundary_at_each_event(self):
  rf=p.load(V,'rf');data=self.data['L12'];self.assertAlmostEqual(data['line']['delay_s'],.5e-9)
  for zs,zl in ((25,None),(25,50),(0,None)):
   b=rf.bounce(1,zs,zl,50,.5e-9,rounds=4);load=0
   for wave in b['waves'][::2]:
    F=wave['amplitude_V'];B=b['Gamma_L']*F;v=F+B;i=(F-B)/50
    if zl is None:self.assertAlmostEqual(i,0)
    else:self.assertAlmostEqual(v,zl*i)
    load+=v
   self.assertAlmostEqual(load,b['events'][-2]['total_V'])
  self.assertAlmostEqual(data['open']['events'][1]['total_V'],4/3)
 def test_pdn_time_frequency_and_energy_units(self):
  d=self.data['L12'];self.assertAlmostEqual(d['detour_loop']['slope_drop_V'],.02);self.assertAlmostEqual(d['short_loop']['slope_drop_V'],.002)
  x=2*math.pi*1e8*2e-9-1/(2*math.pi*1e8*1e-7)
  self.assertAlmostEqual(d['decap']['imag_ohm'],x);self.assertAlmostEqual(d['decap']['charge_drop_V'],.005*5e-9/1e-7)
 def test_joint_budget_failure_and_redesign(self):
  d=self.data['L13'];self.assertFalse(d['budget']['flags']['antialias_tone']);self.assertTrue(d['cutoff80_redesign']['teaching_budget_pass'])
  self.assertAlmostEqual(d['budget']['alias_fold_hz'],10);self.assertAlmostEqual(d['budget']['quantization_rms'],3.3/4096/math.sqrt(12));self.assertGreater(d['budget']['alias_peak_adc_V'],5e-6)
  self.assertEqual(d['pipeline']['samples'][0]['code'],2048);self.assertEqual(d['pipeline']['samples'][3]['code'],2071)
  self.assertEqual(d['pipeline']['samples'][0]['finish_ns'],6300000)
 def test_loader_and_explicit_output(self):
  self.assertNotIn('_jointB_embedded',sys.modules)
  with self.assertRaises(ValueError):p.acquisition(p.load(V,'embedded'),[1.65]*31)
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'run';p.generate(out,V);self.assertEqual(len(list(out.iterdir())),4)
   with self.assertRaises(FileExistsError):p.generate(out,V)
   with self.assertRaises(ValueError):p.generate(V/'forbidden-output',V)
   self.assertTrue(json.loads((out/'results.json').read_text())['synthetic'])

class CausalSteadyStateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.e=p.load(V,'embedded');cls.data=p.causal_butterworth_steady_state(cls.e)
 @staticmethod
 def pole_response(f,fc):
  # Four distinct LHP unit-circle poles: independent of the biquad factorization.
  s=1j*f/fc
  poles=[cmath.exp(1j*math.pi*(5+2*k)/8) for k in range(4)]
  return 1/math.prod(s-z for z in poles)
 @staticmethod
 def state_resolvent(f,fc,amplitude):
  # Independently solve (jw I-A)x=B U in physical seconds, by pivoted elimination.
  wc=2*math.pi*fc;w=2*math.pi*f
  a=math.sqrt(2-math.sqrt(2));b=math.sqrt(2+math.sqrt(2))
  A=[[0,wc,0,0],[-wc,-a*wc,0,0],[0,0,0,wc],[wc,0,-wc,-b*wc]]
  M=[[1j*w*(i==j)-A[i][j] for j in range(4)]+[wc*amplitude if i==1 else 0] for i in range(4)]
  for j in range(4):
   pivot=max(range(j,4),key=lambda i:abs(M[i][j]));M[j],M[pivot]=M[pivot],M[j]
   d=M[j][j];M[j]=[z/d for z in M[j]]
   for i in range(4):
    if i!=j:
     d=M[i][j];M[i]=[x-d*y for x,y in zip(M[i],M[j])]
  return [row[-1] for row in M]
 def test_frequency_response_phase_ports_and_alias(self):
  d=self.data;response=d['response']
  self.assertEqual([r['port'] for r in response],['sensor_before_G200','filter_input_V'])
  self.assertEqual([r['filter_input_Vpk'] for r in response],[.1,.1])
  self.assertAlmostEqual(response[0]['magnitude'],.999999970198,delta=5e-13)
  self.assertAlmostEqual(response[0]['phase_rad'],-.327352205869,delta=5e-13)
  for fc,expected in ((80,4.264019373e-6),(100,10.410203500e-6)):
   data=p.causal_butterworth_steady_state(self.e,cutoff_hz=fc)
   for r in data['response']:
    oracle=self.pole_response(r['frequency_hz'],fc)
    self.assertAlmostEqual(r['gain_real'],oracle.real,delta=3e-15)
    self.assertAlmostEqual(r['gain_imag'],oracle.imag,delta=3e-15)
   r=data['response'][1];self.assertAlmostEqual(r['output_Vpk'],expected,delta=5e-16)
   phi=r['phase_rad'];amp=r['output_Vpk']
   self.assertAlmostEqual((990+500)%1000-500,-10)
   for n in range(32):
    high=amp*math.sin(2*math.pi*990*n/1000+phi)
    signed=amp*math.sin(-2*math.pi*10*n/1000+phi)
    positive=amp*math.sin(2*math.pi*10*n/1000+math.pi-phi)
    self.assertAlmostEqual(high,signed,delta=1e-17);self.assertAlmostEqual(high,positive,delta=1e-17)
 def test_continuous_state_and_initial_condition(self):
  # No tested production response/state helper participates in the reference.
  for fc in (80,100):
   d=p.causal_butterworth_steady_state(self.e,cutoff_hz=fc)
   states=[(f,self.state_resolvent(f,fc,.1)) for f in (10,990)]
   self.assertEqual(len(d['trajectory']),32)
   for n,row in enumerate(d['trajectory']):
    expected=[sum((x[k]*cmath.exp(2j*math.pi*f*n/1000)).imag for f,x in states) for k in range(4)]
    for actual,ref in zip(row['filter_state'],expected):self.assertAlmostEqual(actual,ref,delta=3e-15)
    self.assertAlmostEqual(row['filter_output_V'],expected[2],delta=3e-15)
    self.assertEqual(row['time_s'],n/1000)
   self.assertEqual(d['state_initial_V'],d['trajectory'][0]['filter_state'])
   self.assertGreater(max(abs(x) for x in d['state_initial_V']),.01)
   self.assertEqual(d['contract']['initial_state'],'negative_infinity_sinusoidal_steady_state')
 def test_adc_queue_and_original_path_are_distinct(self):
  d=self.data;pipeline=d['pipeline'];iir=0;codes=[]
  for n,(row,sample) in enumerate(zip(d['trajectory'],pipeline['samples'])):
   expected=min(4095,math.floor(row['adc_input_V']/(3.3/4096)))
   codes.append(expected);q=expected-2048;iir=round(Fraction(3*iir+q,4))
   fir=round(Fraction(q+2*(codes[n-1]-2048 if n else 0)+(codes[n-2]-2048 if n>1 else 0),4))
   self.assertEqual(row['code'],expected);self.assertEqual(sample['code'],expected)
   self.assertEqual(sample['IIR_count'],iir);self.assertEqual(sample['FIR_count'],fir)
   self.assertEqual(row['capture_ns'],n*1000000);self.assertEqual(row['queue_block'],n//4)
   self.assertEqual(row['queue_slot'],(n//4)%2);self.assertEqual(row['queue_status'],'valid')
   self.assertEqual(row['finish_ns'],(n//4+1)*4000000+2300000)
  self.assertEqual(codes[0],2008) # nonzero causal steady-state phase at t=0
  self.assertTrue(all(r['status']=='discard' for r in d['overrun']['samples']))
  self.assertTrue(all('code' not in r for r in d['overrun']['samples']))
  old=p.run(V)['L13']['pipeline']['samples']
  for n,row in enumerate(old):self.assertEqual(row['input_V'],1.65+200*(.0005*math.sin(2*math.pi*10*n*.001)))
  self.assertEqual(old[0]['code'],2048);self.assertEqual(old[3]['code'],2071)
 def test_parameter_errors_before_acquisition_mutation(self):
  fields=('cutoff_hz','sample_hz','signal_hz','interferer_hz','interferer_input_vpk')
  bad=(True,False,float('nan'),float('inf'),-float('inf'),0,-1,1j,'80',None,[],10**1000)
  for field in fields:
   for value in bad:
    with self.subTest(field=field,value=repr(value)[:30]):
     e=Mock()
     with self.assertRaisesRegex(ValueError,'^positive finite branch parameters required$'):
      p.causal_butterworth_steady_state(e,**{field:value})
     self.assertEqual(e.mock_calls,[])
     with self.assertRaisesRegex(ValueError,'^positive finite branch parameters required$'):
      p.causal_butterworth_contract(**{field:value})
  e=Mock()
  with self.assertRaisesRegex(ValueError,'sample_hz=1000'):p.causal_butterworth_steady_state(e,sample_hz=2000)
  self.assertEqual(e.mock_calls,[])
  # Positive finite but outside ADC/numeric range also cannot publish a ring slot.
  for params in ({'interferer_input_vpk':1e12},{'cutoff_hz':1e-300},{'signal_hz':1e308}):
   e=p.load(V,'embedded');e.OwnedRing=Mock();e.CountFilter=Mock()
   with self.assertRaises(ValueError):p.causal_butterworth_steady_state(e,**params)
   self.assertEqual(e.OwnedRing.mock_calls,[]);self.assertEqual(e.CountFilter.mock_calls,[])
if __name__=='__main__':unittest.main()
```
