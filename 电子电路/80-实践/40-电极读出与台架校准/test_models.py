import unittest,math
import models as m
class Models(unittest.TestCase):
 def test_randles_admittance(self):
  for f in (0,.1,1.5915494309189535,10,10000):
   z=m.randles(f);x=2*math.pi*f*.1
   self.assertAlmostEqual(z.real,5000+100000/(1+x*x),places=8)
   self.assertAlmostEqual(z.imag,-100000*x/(1+x*x),places=8)
 def test_semicircle(self):
  for f in (.1,1,10,100):
   z=m.randles(f);self.assertAlmostEqual(((z.real-55000)/50000)**2+(z.imag/50000)**2,1,places=12)
 def test_kcl_readout(self):
  import numpy as np
  for f in (0,1,50,1000):
   hd,hc,*_=m.readout(f);zi=[m.randles(f),m.randles(f,6000,100000,1e-6)];yi=1e-7+1j*2*math.pi*f*1e-10
   for vd,vc,expected in ((1,0,hd),(0,1,hc)):
    v=np.linalg.solve(np.diag([1/z+yi for z in zi]),np.array([(vc+vd/2)/zi[0],(vc-vd/2)/zi[1]]))
    self.assertAlmostEqual(abs(100*(v[0]-v[1])+.001*(v[0]+v[1])/2-expected),0,places=11)
 def test_equal_interfaces(self):
  hd,hc,*_=m.readout(50,electrode2=(5000,100000,1e-6));self.assertAlmostEqual(abs(hd/hc),1e5,places=7)
 def test_thermal_source_paths(self):
  # Separate internal Rct parallel-noise and Rs voltage-noise, from actual topology.
  for f in (.1,10,1000):
   omega=2*math.pi*f;r=100000;c=1e-6;rs=5000
   thermal=4*m.K_B*300*(rs+r/abs(1+1j*omega*r*c)**2)
   self.assertAlmostEqual(thermal/(4*m.K_B*300*m.randles(f).real),1,places=13)
 def test_noise_port_sum(self):
  # independent complex KCL transfer for noise-source branches
  f=50;omega=2*math.pi*f;yi=1e-7+1j*omega*1e-10;ac=.001
  result=0
  for rs,a in ((5000,100+ac/2),(6000,-100+ac/2)):
   z=m.randles(f,rs);yp=1/z+yi;hv=a/(z*yp);hi=a/yp
   result+=abs(hv)**2*4*m.K_B*300*z.real+abs(hi)**2*(1e-24+4*m.K_B*300/1e7)
  result+=(100*20e-9)**2
  self.assertAlmostEqual(result/m.noise_psd(f)['total'],1,places=12)
 def test_integral_different_quadrature(self):
  # midpoint quadrature of original PSD vs Simpson; bounded converged normal domain.
  n=20000;df=99/n
  original=math.sqrt(math.fsum(m.noise_psd(1+(i+.5)*df)['total'] for i in range(n))*df)
  self.assertLess(abs(m.integrate_noise()/original-1),2e-6)
 def test_barrier_differentiation(self):
  n=4000;f=100;c=1e-11;v=1
  # RMS from derivative of Vrms sqrt2 sin, not reused current formula.
  vals=[c*v*math.sqrt(2)*2*math.pi*f*math.cos(2*math.pi*i/n) for i in range(n)]
  expected=math.sqrt(sum(x*x for x in vals)/n)
  self.assertAlmostEqual(m.barrier_current(f,c,v)/expected,1,places=12)
 def test_adc_headroom_and_quant(self):
  b=m.adc_budget(offset=.01);self.assertLess(b['headroom'],0)
  q=2/65536;self.assertAlmostEqual(b['input_lsb'],q/100)
  # exact integral of uniform error density by endpoints primitive
  self.assertAlmostEqual(b['conditional_input_quant_rms']**2,(q/100)**2/12)
 def test_rc_state_and_original_ode(self):
  out=m.rc_hold([1.]*1000,fc=1,initial=.2)
  for n in (0,1,99,999):self.assertAlmostEqual(out[n],1-.8*math.exp(-2*math.pi*(n+1)/1000),places=13)
  a=m.rc_hold([1.]*500,fc=1,initial=.2);b=m.rc_hold([1.]*500,fc=1,initial=a[-1]);self.assertEqual(a+b,out)
 def test_finite_projection_alias_and_removal(self):
  fs=1000;n=2000;x=[.01*math.sin(2*math.pi*50*i/fs) for i in range(n)]
  alias=[.01*math.sin(2*math.pi*950*i/fs) for i in range(n)]
  self.assertAlmostEqual(abs(m.tone(x,fs,50)),.01,places=12)
  self.assertLess(max(abs(x[i]+alias[i]) for i in range(n)),1e-13)
  y=[v-.01*math.sin(2*math.pi*50*i/fs) for i,v in enumerate(x)]
  self.assertEqual(abs(m.tone(y,fs,50)),0) # Removing nuisance also removes legitimate same-frequency content.
 def test_oversized_real_value_error_contract(self):
  huge = 10**400
  for call in (
   lambda: m.randles(huge), lambda: m.randles(1, rs=huge),
   lambda: m.noise_psd(1, temperature=huge),
   lambda: m.barrier_current(1, 1e-12, huge),
   lambda: m.adc_budget(offset=-huge),
   lambda: m.rc_hold([huge]),
  ):
   with self.subTest(call=call):
    with self.assertRaises(ValueError): call()
 def test_invalid_domains(self):
  for bad in (True,complex(1,0),'1',[1],float('nan'),float('inf'),-1):
   with self.assertRaises(ValueError):m.randles(bad)
  for args in ((1,1,1),(1,1e9,1e-6),(1,100000,1e-12)):
   with self.assertRaises(ValueError):m.randles(1,*args)
  with self.assertRaises(ValueError):m.integrate_noise(intervals=999)
  with self.assertRaises(ValueError):m.rc_hold([[1]])
  with self.assertRaises(ValueError):m.adc_budget(bits=True)
if __name__=='__main__':unittest.main()
