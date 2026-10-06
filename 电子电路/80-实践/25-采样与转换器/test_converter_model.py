import unittest
import math
import os, sys, subprocess, tempfile
from pathlib import Path
from decimal import Decimal, localcontext
import converter_model as m

class ConverterTests(unittest.TestCase):
 def test_bins_edges_and_overload(self):
  for j in range(1,8):
   x=j*.375
   self.assertEqual(m.quantize(x)['code'],j)
   self.assertEqual(m.quantize(math.nextafter(x,-math.inf))['code'],j-1)
  self.assertEqual(m.quantize(3)['code'],7)
  self.assertFalse(m.quantize(3)['overload'])
  self.assertTrue(m.quantize(3.1)['overload'])
  self.assertTrue(m.quantize(-.1)['overload'])
  self.assertEqual(m.quantize(1.9)['binary'],'101')
  self.assertEqual(m.quantize(1.9)['center_V'],2.0625)
 def test_sar_independent_threshold_count(self):
  xs=[j*.375 for j in range(9)]+[math.nextafter(j*.375,-math.inf) for j in range(1,8)]+[.1,1.9,-.1,3.1]
  for x in xs:
   expected=sum(x>=j*.375 for j in range(1,8))
   self.assertEqual(m.sar(x)['code'],expected)
  self.assertEqual([r['trial_code'] for r in m.sar(1.9)['trace']],[4,6,5])
 def test_string_from_current_and_loading(self):
  for k in range(8):
   r=m.string_tap([1000]*8,k,load=10000.)
   self.assertAlmostEqual(r['open_V'],3/8000*(k*1000))
   self.assertAlmostEqual(r['rout_ohm'],1000*k*(8-k)/8)
  self.assertEqual(m.string_tap([1000]*8,4,load=10000.)['loaded_V'],1.25)
  self.assertAlmostEqual(m.string_tap([1000]*3+[1200]+[1000]*4,4)['open_V'],1.5365853658536586)
 def test_r2r_closed_form_and_raw_kcl(self):
  for k in range(8):
   v=m.r2r3(k);B=[3*((k>>(2-j))&1) for j in range(3)]
   self.assertAlmostEqual(v[0],k*3/8)
   for lhs,rhs in [(1.5*v[0]-v[1],.5*B[0]),(-v[0]+2.5*v[1]-v[2],.5*B[1]),(-v[1]+2*v[2],.5*B[2])]:self.assertAlmostEqual(lhs,rhs)
   self.assertAlmostEqual(m.r2r3(k,load=10000.)[0],k*3/8*10/11)
 def test_cdac_conserved_charge_and_mismatch(self):
  for k in range(8):
   x=m.cdac(k,1.9);bottom=sum(w*3*((k>>(2-j))&1) for j,w in enumerate([4,2,1]))
   self.assertAlmostEqual(8*x-bottom,-8*1.9)
  self.assertAlmostEqual(m.cdac(5,0,weights=[4.1,2,1,1]),3*5.1/8.1)
  self.assertGreater(m.current_dac(3,(2.9,2,1)),m.current_dac(4,(2.9,2,1)))
 def test_rc_initial_small_time_and_independent_decimal(self):
  self.assertEqual(m.rc_state(100,.4,1000,1e-6,0),.4)
  for t in [1e-20,1e-6,.001]:
   with localcontext() as c:
    c.prec=60;d=Decimal(str(t));dec=(-d/Decimal('.001')).exp();expected=Decimal('.4')*dec+Decimal('100')*(1-dec)
   self.assertAlmostEqual(m.rc_state(100,.4,1000,1e-6,t),float(expected),places=13)
  self.assertAlmostEqual(3.3-m.rc_state(3.3,0,1e4,20e-12,.5e-6),3.3*math.exp(-2.5))
 def test_charge_reference_periodic_state(self):
  self.assertAlmostEqual(m.share(1e-9,2,20e-12,0),2/1.02)
  a=math.exp(-1);rows=m.reference_cycle(cycles=30)
  self.assertAlmostEqual(3-rows[-1]['after_V'],20e-6/(1-a),places=12)
  self.assertEqual(rows[0]['before_V'],3)
 def test_alias_and_moving_source_are_distinct(self):
  self.assertEqual(m.fold(49000,50000),1000)
  self.assertEqual(m.fold(99000,100000),1000)
  self.assertAlmostEqual(m.rc_sine_error(.1,2000,1000,20e-12),.1*abs(1-1/(1+2j*math.pi*2000*1000*20e-12)))
 def test_delta_sigma_sum_and_state_bound(self):
  for u in [[.25]*16,[1]*10,[-1]*10,[.9,-.7]*100]:
   r=m.delta_sigma(u);self.assertTrue(all(abs(s)<=1+1e-14 for s in r['state']))
   self.assertAlmostEqual(sum(u)-sum(r['output']),r['state'][-1]-r['state'][0])
  self.assertEqual(sum(m.delta_sigma([.25]*16)['output']),4)
 def test_invalid_before_cast_and_budget(self):
  bad=[True,1j,'1',None,[],[[1]],10**1000,float('nan'),float('inf'),101,-101]
  for x in bad:
   with self.assertRaises(ValueError):m.quantize(x)
  calls=[lambda:m.quantize(1,bits=True),lambda:m.quantize(1,bits=3.),lambda:m.quantize(1,fsr=0),lambda:m.dac(8),lambda:m.string_tap([1,-1],0),lambda:m.r2r3(3,load=0),lambda:m.cdac(2,weights=[1,2]),lambda:m.current_dac(2,weights=[1,2]),lambda:m.rc_state(1,0,0,1e-6,1),lambda:m.reference_cycle(cycles=4097),lambda:m.reference_cycle(q_C=1e-3,capacitance=1e-15),lambda:m.delta_sigma([1.1]),lambda:m.fold(1,0)]
  for f in calls:
   with self.assertRaises(ValueError):f()

 def test_fresh_import_no_argv_files_or_plot_cache(self):
  lab=Path(__file__).resolve().parent
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folders=[root/k for k in ['caller','mpl','xdg']]
   for p in folders:p.mkdir()
   env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(folders[1]),XDG_CACHE_HOME=str(folders[2]))
   code=f"import sys;sys.path.insert(0,{str(lab)!r});sys.argv=['unknown','--foreign'];import converter_model,generate_figures;assert not any(k in sys.modules for k in ['numpy','matplotlib','cairosvg','PIL'])"
   z=subprocess.run([sys.executable,'-B','-c',code],cwd=folders[0],env=env,capture_output=True,text=True,timeout=15)
   self.assertEqual(z.returncode,0,z.stderr)
   self.assertTrue(all(not list(p.rglob('*')) for p in folders))
 def test_missing_output_exit_two_no_files_or_plot_cache(self):
  lab=Path(__file__).resolve().parent
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folders=[root/k for k in ['caller','mpl','xdg']]
   for p in folders:p.mkdir()
   env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(folders[1]),XDG_CACHE_HOME=str(folders[2]))
   for name in ['converter_model.py','generate_figures.py']:
    z=subprocess.run([sys.executable,'-B',str(lab/name)],cwd=folders[0],env=env,capture_output=True,text=True,timeout=15)
    self.assertEqual(z.returncode,2,z.stderr)
    self.assertIn('--output',z.stderr)
    self.assertTrue(all(not list(p.rglob('*')) for p in folders))

class ComputedBoundaryRegression(unittest.TestCase):
 def test_computed_dac_edges_and_neighbors(self):
  for bits in (3,4,8):
   for fsr in (3.,3.3,2.5,1.2):
    edges=[m.dac(k,bits,fsr) for k in range(1,2**bits)]
    for j,x in enumerate(edges,1):
     for v in (math.nextafter(x,-math.inf),x,math.nextafter(x,math.inf)):
      # Independent ordered threshold count; no division or SAR recursion.
      expected=sum(v>=a for a in edges)
      self.assertEqual(m.quantize(v,bits,fsr)['code'],expected)
      self.assertEqual(m.sar(v,bits,fsr)['code'],expected)
  self.assertEqual(m.quantize(m.dac(3,3,3.3),3,3.3)['code'],3)
  self.assertEqual(m.quantize(m.dac(6,3,3.3),3,3.3)['code'],6)
 def test_open_load_is_only_builtin_float_infinity(self):
  class FloatSubclass(float):pass
  import numpy as np
  for load in (FloatSubclass(math.inf),np.float64(math.inf),FloatSubclass(1000.),np.float64(1000.),float('-inf'),float('nan'),True):
   for fn in (lambda:m.string_tap([1000.]*8,3,load=load),lambda:m.r2r3(3,load=load)):
    with self.assertRaises(ValueError):fn()
  for fn in (lambda:m.string_tap([1000.]*8,3,load=math.inf),lambda:m.r2r3(3,load=math.inf),lambda:m.string_tap([1000.]*8,3,load=1000),lambda:m.r2r3(3,load=1000.)):
   fn()

if __name__=='__main__':unittest.main()
