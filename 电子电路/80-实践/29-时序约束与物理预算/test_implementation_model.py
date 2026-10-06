import unittest,math,tempfile,os,subprocess,sys
from pathlib import Path
from fractions import Fraction
import implementation_model as m

class Models(unittest.TestCase):
 def test_timing_absolute_deadlines_and_hold_independent(self):
  r=m.timing();self.assertAlmostEqual(r['setup_slack_s']/1e-9,10.5-.8-6-.7-.2);self.assertAlmostEqual(r['hold_slack_s']/1e-9,.15+.25-.5-.1-.05)
  self.assertEqual(m.timing(period=20e-9)['hold_slack_s'],r['hold_slack_s'])
  self.assertAlmostEqual(m.timing(d_min=.55e-9,d_max=6.5e-9)['hold_slack_s'],.05e-9)
 def test_effort_product_and_enum(self):
  r=m.effort();self.assertAlmostEqual(r['stage_effort'],4);self.assertAlmostEqual(r['delay_normalized'],15)
  ds={n:m.effort(stages=n)['delay_normalized'] for n in range(1,9)};self.assertEqual(min(ds,key=ds.get),3)
  caps=r['input_cap_relative'];self.assertAlmostEqual(math.prod(caps[i+1]/caps[i] for i in range(3)),64)
  self.assertAlmostEqual(2+2*math.sqrt(32)+3,16.31370849898476)
 def test_power_energy_and_components(self):
  r=m.power();self.assertAlmostEqual(r['dynamic_W'],.4e-6);self.assertAlmostEqual(r['short_W'],.04e-6);self.assertAlmostEqual(r['total_W'],.45e-6)
  self.assertAlmostEqual(m.power(voltage=.8)['dynamic_W']/r['dynamic_W'],.64)
 def test_elmore_by_fraction_weights(self):
  r=m.elmore_tree();expected=(100+200)*Fraction(50,10**15)+300*Fraction(30,10**15)
  self.assertAlmostEqual(r['b_first_moment_s'],float(expected),places=25)
  self.assertAlmostEqual(m.elmore_tree(cb=60e-15)['b_first_moment_s'],42e-12,places=25)
 def test_supply_and_area_units(self):
  r=m.supply();self.assertAlmostEqual(r['drop_V'],.01);self.assertAlmostEqual(r['current_density_A_m2']/1e11,1)
  self.assertAlmostEqual(m.utilization(blocked_m2=200e-12),2/3);self.assertAlmostEqual(m.utilization(cell_area_m2=.3,core_area_m2=.2),1.5)
 def test_power_order_and_failure(self):
  rows=m.power_sequence();self.assertEqual(len(rows),10);self.assertTrue(rows[5]['isolated']);self.assertFalse(rows[5]['on']);self.assertFalse(rows[-1]['isolated'])
  for kw in [{'actions':['power_off']},{'actions':['quiesce','save','power_off']},{'power_good':False},{'reset_released':False}]:
   with self.assertRaises(ValueError):m.power_sequence(**kw)
 def test_scan_old_state_and_serial_order(self):
  r=m.scan_shift();self.assertEqual(r['states'],[[0,0,0],[0,0,0],[1,0,0],[1,1,0]]);self.assertEqual(r['shifted_out_old'],[0,0,0])
  self.assertEqual(m.scan_shift((1,0,1),[0])['shifted_out_old'],[1])
 def test_faults_independent_truth_table(self):
  r=m.faults();self.assertEqual(r['detected'],10);self.assertEqual(r['raw_total'],12)
  expected=[0,1,0,1,0,1,1,1];self.assertEqual([m.logic([k>>2&1,k>>1&1,k&1]) for k in range(8)],expected)
  self.assertEqual(m.logic([1,1,0],('a',0)),0);self.assertEqual(m.logic([1,1,1],('a',0)),1)
  self.assertEqual([x['node'] for x in r['faults'] if not x['detected_by']],['unused','unused'])
 def test_lfsr_enumeration_and_collision_divisibility(self):
  seq=m.lfsr();self.assertEqual(seq,[1,3,7,6,5,2,4,1]);self.assertEqual(set(seq[:-1]),set(range(1,8)));self.assertEqual(m.lfsr(0,4),[0]*5)
  self.assertEqual(m.signature([1,0,1,1]),m.signature([0,0,0,0]))
  # GF(2) long division, independent of register update code.
  for x in range(16):
   v=x<<3
   for j in range(6,2,-1):
    if v&(1<<j):v^=0b1011<<(j-3)
   self.assertEqual(m.signature([x>>j&1 for j in [3,2,1,0]]),v)
 def test_invalid_no_lossy_cast_finite_budget(self):
  for x in [True,1j,'1',[],[[1]],None,float('inf'),float('nan'),10**1000]:
   with self.assertRaises(ValueError):m.timing(period=x)
  cases=[lambda:m.timing(cq_min=2,cq_max=1),lambda:m.effort(stages=17),lambda:m.effort(g=0),lambda:m.supply(resistance=1000),lambda:m.supply(width_m=0),lambda:m.utilization(blocked_m2=1),lambda:m.scan_shift(serial=[0]*4097),lambda:m.logic([True,0,0]),lambda:m.logic([0,0,0],('bad',0)),lambda:m.lfsr(8),lambda:m.signature([2]),lambda:m.power_sequence(actions=['bad'])]
  for call in cases:
   with self.assertRaises(ValueError):call()
 def test_import_missing_output_no_cache_or_files(self):
  lab=Path(__file__).resolve().parent
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);folders=[r/x for x in ['caller','mpl','xdg']]
   for p in folders:p.mkdir()
   env=dict(os.environ,MPLCONFIGDIR=str(folders[1]),XDG_CACHE_HOME=str(folders[2]),PYTHONDONTWRITEBYTECODE='1')
   code=f"import sys;sys.path.insert(0,{str(lab)!r});sys.argv=['stranger','--foreign'];import implementation_model,generate_figures;assert not any(x in sys.modules for x in ['matplotlib','numpy','cairosvg','PIL'])"
   z=subprocess.run([sys.executable,'-B','-c',code],env=env,cwd=folders[0],capture_output=True,text=True,timeout=15);self.assertEqual(z.returncode,0,z.stderr)
   for name in ['implementation_model.py','generate_figures.py']:
    z=subprocess.run([sys.executable,'-B',str(lab/name)],env=env,cwd=folders[0],capture_output=True,text=True,timeout=15);self.assertEqual(z.returncode,2,z.stderr)
   self.assertTrue(all(not list(p.rglob('*')) for p in folders))
if __name__=='__main__':unittest.main()
