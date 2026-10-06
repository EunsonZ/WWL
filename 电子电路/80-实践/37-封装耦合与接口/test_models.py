import unittest,math,subprocess,sys
from pathlib import Path
import models as m
class Models(unittest.TestCase):
 def test_interface_direct_count(self):
  a=m.interface(16,16e9,1,64,68,.8,256,2e-9,.5e-12,.02);self.assertEqual(a['frames'],4);self.assertEqual(a['wire_bits'],2176);self.assertAlmostEqual(a['latency_s_no_queue'],10.5e-9);self.assertAlmostEqual(a['useful_bps'],192752941176.47058);self.assertAlmostEqual(a['total_link_W'],.1224)
 def test_padding_and_coding(self):
  a=m.interface(8,8e9,.8,64,68,1,65,0,1e-12,0);self.assertEqual(a['frames'],2);self.assertEqual(a['wire_bits'],1360);self.assertEqual(a['message_dynamic_J'],1360e-12)
 def test_rlc_dc_and_resonance(self):
  self.assertEqual(m.rlc_transfer(20,.2e-9,.5e-12,0),1);f=1/(2*math.pi*1e-11);self.assertAlmostEqual(abs(m.rlc_transfer(20,.2e-9,.5e-12,f)),1)
 def test_rlc_original_ode_rk4(self):
  # independent original voltage/current ODE, 20000 fixed steps to .2 ns
  r,l,c=20,.2e-9,.5e-12;dt=1e-14;v=i=0
  def f(v,i):return i/c,(1-v-r*i)/l
  for _ in range(20000):
   a,b=f(v,i);aa,bb=f(v+a*dt/2,i+b*dt/2);aaa,bbb=f(v+aa*dt/2,i+bb*dt/2);aaaa,bbbb=f(v+aaa*dt,i+bbb*dt);v+=dt*(a+2*aa+2*aaa+aaaa)/6;i+=dt*(b+2*bb+2*bbb+bbbb)/6
  out=m.rlc_step(r,l,c,dt*20000);self.assertAlmostEqual(v,out['voltage_per_V'],10);self.assertAlmostEqual(i,out['current_A_per_V'],10)
 def test_rlc_peak_from_derivative(self):
  t=math.pi/(1e11*math.sqrt(.75));v=m.rlc_step(20,.2e-9,.5e-12,t);self.assertAlmostEqual(v['current_A_per_V'],0);self.assertAlmostEqual(v['voltage_per_V'],1+math.exp(-math.pi/math.sqrt(3)))
 def test_thermal_original_steady_kcl(self):
  a=m.thermal(8,4,2,4,2,4);x,y=a['steady_rise_K'];self.assertEqual((x,y),(14,10));self.assertEqual(x/2+(x-y)/4,8);self.assertEqual(y/2+(y-x)/4,4)
 def test_thermal_eigenmodes_independent(self):
  a=m.thermal(8,4,2,4,2,4);x,y=a['rise_K'];self.assertAlmostEqual((x+y)/2,12*(1-math.exp(-1)));self.assertAlmostEqual((x-y)/2,2*(1-math.exp(-2)))
 def test_thermal_initial_and_symmetry(self):
  a=m.thermal(8,8,2,4,2,0);self.assertEqual(a['rise_K'],[0,0]);a=m.thermal(8,8,2,4,2,100);self.assertAlmostEqual(a['rise_K'][0],16);self.assertEqual(a['rise_K'][0],a['rise_K'][1])
 def test_cte_sign_and_units(self):
  a=m.thermo_mechanical(15e-6,3e-6,60,.005,.0001);self.assertAlmostEqual(a['free_mismatch_m'],3.6e-6);self.assertAlmostEqual(a['kinematic_shear_estimate'],.036);self.assertFalse(a['lifetime_claim'])
 def test_feedback_boundary(self):
  a=m.leakage_equilibrium(6,.1,2);self.assertAlmostEqual(a['uniform_rise_K'],15)
  with self.assertRaises(ValueError):m.leakage_equilibrium(6,.5,2)
 def test_yield_by_independent_poisson(self):
  a=m.yield_cost([2],.3,20,0,5,.99);b=m.yield_cost([1,1],.3,20,0,10,.95);self.assertAlmostEqual(a['die_yields'][0],math.exp(-.6));self.assertAlmostEqual(b['known_good_die_input_cost'],40/math.exp(-.3));self.assertLess(b['cost_per_good_assembly'],a['cost_per_good_assembly'])
 def test_invalid(self):
  for x in (True,1j,[],{},float('nan'),float('inf'),10**500):
   with self.assertRaises(ValueError):m.thermal(x,4,2,4,2,4)
  with self.assertRaises(ValueError):m.rlc_step(20,.2e-9,.5e-12,1e-20)
  with self.assertRaises(ValueError):m.interface(True,16e9,1,64,68,.8,256,0,1e-12,0)
 def test_pure_import(self):
  a=subprocess.run([sys.executable,'-B','-c',"import sys;sys.argv=['bad'];import models,generate;assert not any(x in sys.modules for x in ['numpy','matplotlib','cairosvg'])"],cwd=Path(__file__).parent,capture_output=True,text=True);self.assertEqual(a.returncode,0,a.stderr)
if __name__=='__main__':unittest.main()
