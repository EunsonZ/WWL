import unittest,math,tempfile,subprocess,sys,os
from pathlib import Path
import photon_models as m
class Physics(unittest.TestCase):
 def test_energy_charge(self):
  o=m.optical();self.assertAlmostEqual(o['photo_A'],m.Q*.7*o['photon_s'],places=18)
  self.assertAlmostEqual(o['photon_J']/m.Q,1.458637628,places=8)
 def test_power_not_field_db(self):
  self.assertAlmostEqual(m.optical(loss_db=20)['photo_A']/m.optical(loss_db=10)['photo_A'],.1)
 def test_zero(self):
  self.assertEqual(m.optical(qe=0)['photo_A'],0);self.assertEqual(m.optical(power_w=0)['photon_s'],0)
 def test_kcl_independent(self):
  import numpy as np
  for f in [0,1,1e5,1e6,1e8]:
   s=2j*math.pi*f;a=1e5/(1+s/(2*math.pi*100));y=1e-5+s*1e-12
   # Unknown X/output solved as independent two-equation KCL + opamp constraint.
   x,v=np.linalg.solve(np.array([[s*1e-11+y,-y],[a,1]],complex),np.array([1,0],complex))
   self.assertLess(abs(m.tia(f)[0]-v)/max(abs(v),1),1e-13)
   x,v=np.linalg.solve(np.array([[s*1e-11+y,-y],[a,1]],complex),np.array([0,a],complex))
   self.assertLess(abs(m.tia(f)[1]-v)/max(abs(v),1),1e-13)
 def test_dc_limit(self):
  self.assertEqual(m.tia(0)[0],-1e5*1e5/(1e5+1));self.assertAlmostEqual(m.tia(0)[1].real,1e5/(1e5+1))
 def test_quadrature_gauss(self):
  import numpy as np
  x,w=np.polynomial.legendre.leggauss(64);b=1e5;p=m.optical()['photo_A']
  independent=b/2*sum(wk*m.output_psd((xk+1)*b/2,p) for xk,wk in zip(x,w))
  self.assertLess(abs(m.integrated_noise(p)**2-independent)/independent,1e-11)
 def test_noise_source(self):
  p=m.optical()['photo_A'];f=1234;z,_=m.tia(f)
  difference=m.output_psd(f,p*2)-m.output_psd(f,p)
  self.assertAlmostEqual(difference/(abs(z)**2*2*m.Q*p),1,places=13)
 def test_mzi_energy(self):
  for v in [-8,-4,0,1,4,8]:
   a,b=m.mzi(1e-4,v);self.assertAlmostEqual(a+b,1e-5,places=18)
 def test_mzi_complex_fields(self):
  import cmath
  for v in [-1,.1,2]:
   phase=math.pi/2+math.pi*v/4
   field=(1+cmath.exp(1j*phase))/2
   self.assertAlmostEqual(m.mzi(1e-4,v)[0],1e-5*abs(field)**2,places=18)
 def test_modulation_derivative(self):
  step=1e-5; a=(m.mzi(1e-4,step)[0]-m.mzi(1e-4,-step)[0])/(2*step)
  self.assertAlmostEqual(a/(-1e-5*math.pi/8),1,places=9)
 def test_calibration(self):
  p=[0,1e-6,2e-6,10e-6];i=[1e-9+.48*x for x in p]
  self.assertAlmostEqual(m.calibrate(p,i,1e-9)['responsivity_A_W'],.48,places=14)
 def test_invalid_inputs(self):
  import numpy as np
  for x in [True,complex(1,0),float('nan'),float('inf'),-1,2]:
   with self.assertRaises(ValueError):m.optical(power_w=x)
  for x in [True,15,17,65538,16.0]:
   with self.assertRaises(ValueError):m.integrated_noise(1e-6,panels=x)
  for x in [[0,1j,2],[False,True,True],np.array([0,1,2],object),[[0],[1],[2]]]:
   with self.assertRaises(ValueError):m.calibrate(x,x,0)
  with self.assertRaises(ValueError):m.calibrate([0,0,0],[0,0,0],0)
 def test_fresh_import(self):
  with tempfile.TemporaryDirectory() as td:
   env=dict(os.environ,MPLCONFIGDIR=td+'/mpl',XDG_CACHE_HOME=td+'/xdg',PYTHONDONTWRITEBYTECODE='1')
   code="import sys,os;sys.path.insert(0,sys.argv[1]);import photon_models,generate_figures;assert 'matplotlib' not in sys.modules and 'numpy' not in sys.modules;assert not os.path.exists(os.environ['MPLCONFIGDIR'])"
   r=subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).parent)],env=env,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(list(Path(td).iterdir()),[])
 def test_required_output(self):
  for script in ['photon_models.py','generate_figures.py']:
   with tempfile.TemporaryDirectory() as td:
    r=subprocess.run([sys.executable,'-B',str(Path(__file__).parent/script)],cwd=td,capture_output=True,text=True)
    self.assertEqual(r.returncode,2);self.assertEqual(list(Path(td).iterdir()),[])
 def test_generate_success_exception_state(self):
  import generate_figures as g,copy
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as td:
   old=dict(os.environ)
   try:
    os.environ['MPLCONFIGDIR']=td+'/preload';os.environ['XDG_CACHE_HOME']=td+'/xdg'
    import matplotlib as mpl
   finally:
    os.environ.clear();os.environ.update(old)
   def snapshot():return dict(os.environ),{k:(v if k=='backend' else copy.deepcopy(v)) for k,v in dict.items(mpl.rcParams)}
   before=snapshot();g.generate(Path(td)/'success');self.assertEqual(before,snapshot())
   with patch.object(g,'diagrams',side_effect=RuntimeError('injected')):
    with self.assertRaisesRegex(RuntimeError,'injected'):g.generate(Path(td)/'failure')
   self.assertEqual(before,snapshot())
 def test_existing_output_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):m.generate(td)
if __name__=='__main__':unittest.main()
