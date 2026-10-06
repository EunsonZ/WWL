import unittest,math,json,copy,subprocess,sys,tempfile,os,random
from pathlib import Path
from fractions import Fraction
import pcb_model as m
L=Path(__file__).parent
class Models(unittest.TestCase):
 def test_loaded_kcl(self):
  r=m.rc(.00025);tau=Fraction(1000*10000,11000)*Fraction(1,1000000);k=Fraction(10,11);v=float(k)+(0.4-float(k))*math.exp(-.00025/float(tau));self.assertAlmostEqual(r['voltage_V'],v,14);self.assertAlmostEqual(r['tau_s'],float(tau));self.assertEqual(m.rc(0,source=3.3)['voltage_V'],.4)
  self.assertAlmostEqual(m.rc(100,r=10000)['voltage_V'],.5);self.assertAlmostEqual(m.rc(100,load=1000)['voltage_V'],.5)
 def test_probe_independent_conductance(self):
  g=Fraction(1,1000)+Fraction(1,10000)+Fraction(1,1000000);v=float(Fraction(1,1000)/g);self.assertAlmostEqual(m.rc(100,probe=1e6)['voltage_V'],v,14)
 def test_charge(self):
  s=m.sharing();self.assertAlmostEqual((1e-6+20e-12)*s['shared_V'],2e-6,18);self.assertAlmostEqual(m.coupling()['step_V'],3.3e-12/(1e-6+1e-12),17)
 def test_loop_units(self):
  self.assertAlmostEqual(m.loop()['slope_drop_V'],.002,15);self.assertAlmostEqual(m.loop(inductance=20e-9)['slope_drop_V'],.020,15);self.assertAlmostEqual(m.loop(frequency=1e7,inductance=20e-9)['reactance_ohm'],2*math.pi*.2)
 def test_decap_resonance(self):
  f=1/(2*math.pi*math.sqrt(2e-9*1e-7));self.assertAlmostEqual(m.decap(f)['imag_ohm'],0,12);self.assertAlmostEqual(m.decap(f)['magnitude_ohm'],.05,13);self.assertAlmostEqual(m.energy(),11.4345e-6,17)
 def test_geometry_connects(self):
  b=json.loads((L/'board.json').read_text());g=m.geometry(b);self.assertEqual(g['violations'],[]);self.assertEqual(g['disconnected_pads'],[]);self.assertEqual(g['pad_count'],21)
 def test_geometry_counterexamples(self):
  b=json.loads((L/'board.json').read_text());b['front_paths']['IN'][0][1]=[8,10];self.assertIn('R1.1',m.geometry(b)['disconnected_pads']);b=json.loads((L/'board.json').read_text());b['front_paths']['IN'].append([[19,5],[19,15]]);self.assertTrue(any('crossing' in e for e in m.geometry(b)['violations']))
 def test_foreign_pad_clearance(self):
  b=json.loads((L/'board.json').read_text());b['front_paths']['IN'].append([[18.95,11],[18.95,13]]);self.assertTrue(any('C1.2' in e for e in m.geometry(b)['violations']))
 def test_native_invalid(self):
  for x in [True,1j,[1],[[1]],float('nan'),float('inf'),10**1000]:
   with self.assertRaises(ValueError):m.rc(x)
  for fn,args in [(m.rc,(-1,)),(m.rc,(101,)),(m.sharing,(0,)),(m.loop,(1e10,)),(m.decap,(0,)),(m.energy,(4,)),(m.geometry,({},))]:
   with self.assertRaises(ValueError):fn(*args)
 def test_budget(self):
  with self.assertRaises(ValueError):m.energy(capacitances=[1e-6]*33)
  b=json.loads((L/'board.json').read_text());b['pads']=b['pads']*129
  with self.assertRaises(ValueError):m.geometry(b)
 def test_pure_prng(self):
  s=random.getstate();m.rc(1e-30);m.loop();m.geometry(json.loads((L/'board.json').read_text()));self.assertEqual(s,random.getstate())
 def test_process_import_missing(self):
  for name in ['pcb_model','generate_figures']:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MPLCONFIGDIR=str(p/'mpl'),XDG_CACHE_HOME=str(p/'xdg'));(p/'mpl').mkdir();(p/'xdg').mkdir()
    code=f"import sys,random;sys.path.insert(0,{str(L)!r});sys.argv=['stranger','--alien'];s=random.getstate();import {name};assert random.getstate()==s;assert 'matplotlib' not in sys.modules;assert 'cairosvg' not in sys.modules"
    z=subprocess.run([sys.executable,'-B','-c',code],cwd=p,env=env,capture_output=True,text=True,timeout=20);self.assertEqual(z.returncode,0,z.stderr)
    z=subprocess.run([sys.executable,'-B',str(L/(name+'.py'))],cwd=p,env=env,capture_output=True,text=True,timeout=20);self.assertEqual(z.returncode,2);self.assertEqual(list(p.rglob('*')),[p/'mpl',p/'xdg'])
if __name__=='__main__':unittest.main()
