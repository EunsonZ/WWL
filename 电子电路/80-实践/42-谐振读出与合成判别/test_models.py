import unittest,math,cmath
import models as m
class Models(unittest.TestCase):
 def test_reflection_energy(self):
  for delta in (-5e7,0,5e7):
   k=2*math.pi*5e6;e=.8;r=m.reflection(k,e,delta)
   dissipated=e*(1-e)*k*k/((k/2)**2+delta**2)
   self.assertAlmostEqual(abs(r)**2+dissipated,1,places=13)
  self.assertEqual(m.reflection(1e6,1,0),-1)
  self.assertEqual(m.reflection(1e6,.5,0),0)
 def test_cavity_original_real_ode(self):
  # Independent explicit RK4 of two real state equations with 2000 substeps.
  k=2*math.pi*5e6;de=k/4;b=math.sqrt(1e-17);dt=1e-8;h=dt/2000;x=y=0.
  def d(x,y):return (-k*x/2+de*y+math.sqrt(.8*k)*b,-de*x-k*y/2)
  for _ in range(2000):
   a1,b1=d(x,y);a2,b2=d(x+h*a1/2,y+h*b1/2);a3,b3=d(x+h*a2/2,y+h*b2/2);a4,b4=d(x+h*a3,y+h*b3);x+=h*(a1+2*a2+2*a3+a4)/6;y+=h*(b1+2*b2+2*b3+b4)/6
  actual,_=m.cavity_step(0,b,dt,k,.8,de);self.assertLess(abs(actual-complex(x,y))/abs(actual),1e-11)
 def test_decay_keeps_initial(self):
  k=1e8;dt=1e-6;a,_=m.cavity_step(1e-12,0,dt,k,1,0)
  self.assertGreater(a.real,0);self.assertAlmostEqual(a.real/(1e-12*math.exp(-50)),1,places=12)
 def test_tiny_startup_and_semigroup(self):
  k=1e5;d=5*k;b=1e-9;t=1e-12;a,_=m.cavity_step(0,b,t,k,1,d)
  self.assertAlmostEqual(a.real/(math.sqrt(k)*b*t),1,places=6)
  a,_=m.cavity_step(0,b,1e-8,k,1,d);c,_=m.cavity_step(a,b,1e-8,k,1,d);q,_=m.cavity_step(0,b,2e-8,k,1,d);self.assertLess(abs(c-q)/abs(q),1e-12)
 def test_bose_geometric_distribution(self):
  f=6e9;t=.2;q=math.exp(-m.H*f/(m.KB*t));n=sum(i*(1-q)*q**i for i in range(500))
  self.assertAlmostEqual(m.occupation(f,t),n,places=13)
 def test_temperature_limits(self):
  self.assertEqual(m.occupation(6e9,0),0)
  self.assertEqual(m.sym_noise(6e9,0),m.H*6e9/2)
  self.assertLess(abs(m.sym_noise(6e9,300)/(m.KB*300)-1),1e-6)
 def test_cascade_original_stage(self):
  r=m.quantum_chain();q=m.occupation()+.5
  first=.5*q+.5*q;first=100*first+100*.5;second=1000*first+1000*20
  self.assertAlmostEqual(r['output_sym_quanta'],second)
  self.assertAlmostEqual(r['measurement_equiv_sym_quanta'],second+.5)
  self.assertAlmostEqual(r['output_energy_per_Hz_J'],m.H*6e9*(second+.5))
  self.assertAlmostEqual(r['source_referred_sym_quanta'],second/50000)
 def test_loss_before_amp_penalty(self):
  no=m.quantum_chain(loss_efficiency=1);loss=m.quantum_chain();self.assertGreater(loss['source_referred_sym_quanta'],no['source_referred_sym_quanta'])
 def test_calibration_independent_linear_solve(self):
  import numpy as np
  mat=((1,.08),(.02,.9));off=(2e-6,-3e-6);v=complex(4e-6,7e-6);y=m.iq_forward(v,mat,off);original=np.linalg.solve(mat,[y.real-off[0],y.imag-off[1]])
  z=m.iq_inverse(y);self.assertAlmostEqual(z.real,original[0],places=16);self.assertAlmostEqual(z.imag,original[1],places=16)
 def test_gaussian_original_integral(self):
  # Error under class0 is normal tail beyond midpoint; integrate density directly.
  sig=1e-5;delta=3e-5;lo=delta/(2*sig);hi=10;n=20000;dx=(hi-lo)/n
  area=sum(math.exp(-(lo+(i+.5)*dx)**2/2)/math.sqrt(2*math.pi)*dx for i in range(n))
  self.assertAlmostEqual(m.gaussian_error(0,delta,sig),area,places=8)
 def test_classifier_projection(self):
  self.assertEqual(m.classify(-1e-4j,-1e-4j,1e-4j),0);self.assertEqual(m.classify(1e-4j,-1e-4j,1e-4j),1)
  self.assertAlmostEqual(m.mean_complex([1e-4j,-1e-4j]),0)
 def test_domains_and_endpoints(self):
  for bad in (10**400,True,complex(1,0),[1],None,float('nan'),float('inf')):
   with self.assertRaises(ValueError):m.real(bad,'x',0,1)
  self.assertEqual(m.real(0,'x',0,1),0);self.assertEqual(m.real(1,'x',0,1),1)
  self.assertGreater(m.occupation(20e9,.01),0)
  with self.assertRaises(ValueError):m.occupation(6e9,.001)
  with self.assertRaises(ValueError):m.quantum_chain(added1=0)
  with self.assertRaises(ValueError):m.iq_inverse(0,((1,1),(1,1)))
  with self.assertRaises(ValueError):m.mean_complex([[1]])
 def test_three_point_calibration(self):
  mat,off=m.fit_iq(m.iq_forward(0),m.iq_forward(1e-4),m.iq_forward(1e-4j))
  for row,expected in zip(mat,((1,.08),(.02,.9))):
   for a,b in zip(row,expected):self.assertAlmostEqual(a,b,places=13)
  self.assertEqual(off,(2e-6,-3e-6))
if __name__=='__main__':unittest.main()
