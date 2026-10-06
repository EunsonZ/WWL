import unittest,math,io,contextlib,importlib,sys,tempfile
from pathlib import Path
import semiconductor_lab as s
class Tests(unittest.TestCase):
 def test_physical_constants(self):
  self.assertAlmostEqual(s.thermal_voltage(300),0.025851999786435535,places=14)
 def test_pn_charge_and_barrier(self):
  d=s.pn_dimensions(1e22,2e22,1e16,300)
  self.assertAlmostEqual(d['xp']/d['xn'],2,places=12)
  # Independently integrate trapezoid E; endpoint phi must equal logarithmic equilibrium barrier.
  a,b=-d['xp'],d['xn'];count=2000;h=(b-a)/count
  vals=[s.pn_space(a+i*h,1e22,2e22,1e16,300)['e'] for i in range(count+1)]
  integral=h*(sum(vals)-.5*(vals[0]+vals[-1]))
  self.assertLess(abs(-integral-d['vbi'])/d['vbi'],1e-6)
 def test_poisson_derivatives(self):
  d=s.pn_dimensions(1e22,2e22,1e16,300);h=1e-12
  for x in [-d['xp']/2,d['xn']/2]:
   a=s.pn_space(x-h,1e22,2e22,1e16,300);b=s.pn_space(x+h,1e22,2e22,1e16,300);m=s.pn_space(x,1e22,2e22,1e16,300)
   self.assertAlmostEqual((b['phi']-a['phi'])/(2*h)/(-m['e']),1,places=8)
   self.assertAlmostEqual((b['e']-a['e'])/(2*h)/(m['rho']/(11.7*s.EPS0)),1,places=8)
 def test_equilibrium_product(self):
  for x in [-1e-6,-1e-7,0,1e-7,1e-6]:
   d=s.pn_space(x,1e22,2e22,1e16,300);self.assertAlmostEqual(d['n']*d['p']/1e32,1,places=12)
 def test_load_root(self):
  d=s.diode_load(5,1000)
  # independent analytic inverse log evaluated at network current, not forward API.
  v=0.025851999786435535*math.log1p(d['i']/1e-12)
  self.assertAlmostEqual(d['v'],v,places=10);self.assertLess(abs(d['residual_a']),1e-12)
  self.assertEqual(s.diode_load(0,1000)['i'],0)
 def test_charge_derivative(self):
  for v in [-2,0,2,5]:
   h=1e-5;diff=(s.nonlinear_charge(v+h)-s.nonlinear_charge(v-h))/(2*h)
   self.assertAlmostEqual(diff/s.nonlinear_capacitance(v),1,places=9)
  self.assertAlmostEqual(s.nonlinear_charge(2)/(2*1e-6),7.853981633974483)
 def test_recovery_limits(self):
  self.assertEqual(s.storage_time(0,.001,1e-7),0)
  self.assertAlmostEqual(s.storage_time(.001,.001,1e-7),math.log(2)*1e-7)
  self.assertLess(s.storage_time(.001,.01,1e-7),s.storage_time(.001,.001,1e-7))
 def test_temperature(self):
  self.assertAlmostEqual(s.saturation_temperature(300)/1e-12,1,places=12)
  self.assertLess(s.constant_current_voltage(.001,330),s.constant_current_voltage(.001,300))
 def test_impedance_limits(self):
  self.assertAlmostEqual(s.capacitor_impedance(0,1e-7,.05,1e-9,1e9).real/(1e9+.05),1,places=14)
  f=1/(2*math.pi*math.sqrt(1e-7*1e-9))
  self.assertLess(abs(s.capacitor_impedance(f,1e-7,.05,1e-9,1e9).imag),1e-12)
  self.assertLess(s.capacitor_impedance(1e6,1e-7,.05,1e-9,1e9).imag,0)
  self.assertGreater(s.capacitor_impedance(1e8,1e-7,.05,1e-9,1e9).imag,0)
 def test_invalid_scalar(self):
  for v in [True,False,1+0j,complex(1,2),'1',object(),[1],[[1]],float('nan'),float('inf')]:
   with self.subTest(v=repr(v)):
    with self.assertRaises((TypeError,ValueError)):s.thermal_voltage(v)
  for v in [0,-1]:
   with self.assertRaises(ValueError):s.thermal_voltage(v)
 def test_invalid_each_interface(self):
  funcs=[lambda v:s.pn_dimensions(v,2e22,1e16,300),lambda v:s.pn_space(v,1e22,2e22,1e16,300),lambda v:s.diode_current(v),lambda v:s.diode_load(v,1000),lambda v:s.nonlinear_charge(v),lambda v:s.nonlinear_capacitance(v),lambda v:s.storage_time(.001,v,1e-7),lambda v:s.saturation_temperature(v),lambda v:s.constant_current_voltage(v,300),lambda v:s.capacitor_impedance(v,1e-7,.05,1e-9,1e9)]
  for fn in funcs:
   for bad in [True,1+0j,object(),[[1]],float('nan'),float('inf')]:
    with self.assertRaises((TypeError,ValueError)):fn(bad)
 def test_budget_and_domain(self):
  with self.assertRaises(RuntimeError):s.diode_load(5,1000,max_iterations=1)
  with self.assertRaises(RuntimeError):s.diode_load(5,1000,voltage_tol=1e-100)
  with self.assertRaises(ValueError):s.pn_dimensions(1e22,2e22,1e16,300,vd=1)
  with self.assertRaises(ValueError):s.diode_current(100)
  with self.assertRaises(TypeError):s.capacitor_impedance(1j,1e-7,.05,1e-9,1e9)
 def test_pure_import(self):
  with tempfile.TemporaryDirectory() as d:
   import os
   prior=os.getcwd();os.chdir(d)
   try:
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):importlib.reload(s)
    self.assertEqual(stream.getvalue(),'');self.assertEqual(list(Path(d).iterdir()),[])
   finally:os.chdir(prior)
if __name__=='__main__':unittest.main()
