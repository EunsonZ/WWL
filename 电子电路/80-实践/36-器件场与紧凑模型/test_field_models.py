import unittest,math,random,subprocess,sys,os,tempfile
from pathlib import Path
import field_models as m
class Models(unittest.TestCase):
 def test_poisson_analytic_nonuniform(self):
  x=[0,1e-7,3e-7,7e-7,1e-6];r=m.poisson(x,[1]*5)
  for z,v in zip(x,r['phi_V']):self.assertAlmostEqual(v,.1*z/1e-6+z*(1e-6-z)/(2*11.7*m.EPS0),places=13)
  self.assertLess(max(abs(v) for v in r['balance_C_m2']),1e-18)
 def test_poisson_other_algorithm(self):
  # Independent sequential D integration + one boundary slope; no dense matrix.
  x=[i*1e-6/10 for i in range(11)];rho=[math.sin(math.pi*i/10) for i in range(11)];h=1e-7;e=11.7*m.EPS0
  offset=[0.]
  for i in range(1,10):offset.append(offset[-1]+rho[i]*h)
  D0=(-e*.1-h*sum(offset))/1e-6;phi=[0.]
  for d in offset:phi.append(phi[-1]-(D0+d)*h/e)
  for v,w in zip(phi,m.poisson(x,rho)['phi_V']):self.assertAlmostEqual(v,w,places=12)
 def test_sg_independent_integral(self):
  # Integrating factor relation J=qD*(nr exp(-delta)-nl)/integral exp(-phi/VT) dx.
  vt=m.KB*300/m.Q;d=math.log(2);nl=1e21;nr=1.5e21;h=1e-6
  integral=h*(-math.expm1(-d))/d;oracle=m.Q*.135*vt*(nr*math.exp(-d)-nl)/integral
  self.assertAlmostEqual(m.sg_current(0,vt*d,nl,nr,h)/oracle,1,places=14)
 def test_sg_equilibrium_and_zero_field(self):
  vt=m.KB*300/m.Q
  self.assertLess(abs(m.sg_current(0,vt*math.log(2),1e21,2e21,1e-6)),1e-9)
  self.assertAlmostEqual(m.sg_current(0,0,1e21,2e21,1e-6)/(m.Q*.135*vt*1e21/1e-6),1,places=14)
  self.assertEqual(m.bernoulli(0),1)
 def test_transport_continuous_oracle(self):
  vt=m.KB*300/m.Q;d=math.log(2);x=[i*1e-6/16 for i in range(17)];ps=[vt*d*i/16 for i in range(17)];r=m.transport(x,ps)
  expected=-m.Q*.135*vt*1e21*d/1e-6
  self.assertAlmostEqual(r['J_A_m2']/expected,1,places=12)
  self.assertLess(max(abs(j/expected-1) for j in r['edge_J_A_m2']),1e-12)
  self.assertLess(max(abs(n/1e21-1) for n in r['n_m3']),1e-12)
 def test_pb_manufactured_order(self):
  errors=[]
  for N in [8,16,32,64]:
   r=m.equilibrium_case(N);errors.append(r['max_error_V']);self.assertLess(r['residual_scaled'],1e-10)
   for n,p in zip(r['n_m3'],r['p_m3']):self.assertAlmostEqual(n*p/1e32,1,places=14)
  self.assertTrue(all(3.9<errors[i]/errors[i+1]<4.1 for i in range(3)))
 def test_pb_budget_and_zero(self):
  self.assertEqual(m.equilibrium_case(amplitude=0)['max_error_V'],0)
  with self.assertRaises(RuntimeError):m.equilibrium_case(max_iterations=1)
 def test_fit_oracle_and_unidentifiable(self):
  G=m.Q*.135*1e21*1e-12/1e-6;r=m.fit_origin([.01,.02,.04],[G*.01,G*.02,G*.04]);self.assertAlmostEqual(r['G_S']/G,1,places=14)
  self.assertEqual(m.bar_conductance(),m.bar_conductance(mu=.0675,density=2e21))
 def test_sensitivity_fixed_rho(self):
  x=[0,.5e-6,1e-6];e=11.7*m.EPS0;a=m.poisson(x,[1]*3,epsilon=e)['phi_V'][1]-.05;b=m.poisson(x,[1]*3,epsilon=1.01*e)['phi_V'][1]-.05
  self.assertAlmostEqual(b/a,1/1.01,places=12)
 def test_huge_integers_rejected_by_documented_exception(self):
  # Finite native integers may overflow implicit float conversion: reject first.
  for bad in [10**400,-10**400]:
   with self.assertRaises(ValueError):m.bar_conductance(mu=bad)
   with self.assertRaises(ValueError):m.poisson([0,.5e-6,1e-6],[1]*3,epsilon=bad)
   with self.assertRaises(ValueError):m.poisson([0,.5e-6,1e-6],[1,bad,1])
 def test_invalid_domains(self):
  for x in [True,complex(1,0),float('nan'),float('inf'),'1']:
   with self.assertRaises(ValueError):m.bar_conductance(mu=x)
  for grid,rho in [([0,0,1e-6],[1]*3),([0,1e-6],[1]*2),([0,.5e-6,1e-6],[1,2]),([0,.5e-6,1e-6],[1+0j]*3)]:
   with self.assertRaises(ValueError):m.poisson(grid,rho)
  with self.assertRaises(ValueError):m.equilibrium_case(129)
  with self.assertRaises(ValueError):m.fit_origin([0,0],[0,0])
  with self.assertRaises(ValueError):m.bernoulli(81)
 def test_pure_random(self):
  a=random.getstate();m.bar_conductance();m.bernoulli(.1);self.assertEqual(a,random.getstate())
 def test_process_contract(self):
  for module in ['field_models','generate_figures']:
   for mode in ['import','missing']:
    with tempfile.TemporaryDirectory() as d:
     env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).parent),MPLCONFIGDIR=d+'/cache',XDG_CACHE_HOME=d+'/xdg')
     args=[sys.executable,'-B','-c',f'import {module};import sys;assert "numpy" not in sys.modules and "matplotlib" not in sys.modules'] if mode=='import' else [sys.executable,'-B',str(Path(__file__).with_name(module+'.py'))]
     r=subprocess.run(args,env=env,cwd=d,capture_output=True);self.assertEqual(r.returncode,0 if mode=='import' else 2);self.assertEqual(list(Path(d).rglob('*')),[])
if __name__=='__main__':unittest.main()
