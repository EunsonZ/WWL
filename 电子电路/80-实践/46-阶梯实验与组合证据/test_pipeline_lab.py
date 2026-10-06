"""Independent finite transfer checks; not HDL/SPICE/hardware."""
import unittest,os,math,sys,tempfile,json
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
   out=Path(td)/'run';p.generate(out,V);self.assertEqual(len(list(out.iterdir())),3)
   with self.assertRaises(FileExistsError):p.generate(out,V)
   with self.assertRaises(ValueError):p.generate(V/'forbidden-output',V)
   self.assertTrue(json.loads((out/'results.json').read_text())['synthetic'])
if __name__=='__main__':unittest.main()
