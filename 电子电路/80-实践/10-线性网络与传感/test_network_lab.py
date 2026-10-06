import unittest
import numpy as np
import network_lab as a

class Contracts(unittest.TestCase):
 def check_network(self,net):
  d=a.solve(net)
  self.assertLess(np.max(np.abs(d['residual'])),1e-12)
  self.assertAlmostEqual(sum(d['absorbed_W'].values()),0,places=12)
  return d
 def test_nodes_and_floating_source(self):
  d=self.check_network(a.node_net());self.assertAlmostEqual(d['volts_V']['a'],2);self.assertAlmostEqual(d['volts_V']['b'],1)
  d=self.check_network(a.supernode_net());self.assertAlmostEqual(d['volts_V']['a'],5/3);self.assertAlmostEqual(d['volts_V']['b'],2/3);self.assertAlmostEqual(d['currents_A']['E'],1/3000)
 def test_mesh_and_supermesh_independent_mna(self):
  d=self.check_network(a.mesh_net());i=np.linalg.solve([[2000,-1000],[-1000,3000]],[5,-1]);self.assertTrue(np.allclose(i,[.0028,.0006]));self.assertAlmostEqual(d['currents_A']['Rc'],i[0]-i[1])
  d=self.check_network(a.mesh_net(True));i=np.linalg.solve([[1000,2000],[-1,1]],[4,.001]);self.assertAlmostEqual(i[0],2/3000);self.assertAlmostEqual(i[1],5/3000);self.assertAlmostEqual(d['volts_V']['a'],13/3)
 def test_dependent_superposition_and_power_cross(self):
  d=self.check_network(a.controlled_net());u=a.solve(a.controlled_net(i=0));w=a.solve(a.controlled_net(e=0))
  for node in d['volts_V']:self.assertAlmostEqual(d['volts_V'][node],u['volts_V'][node]+w['volts_V'][node])
  self.assertAlmostEqual(d['volts_V']['a'],2.8);self.assertAlmostEqual(d['absorbed_W']['R2']-u['absorbed_W']['R2']-w['absorbed_W']['R2'],.00096)
 def test_port_test_source_and_loading(self):
  net=a.controlled_net(e=0,i=0)+[('V','TEST','a','0',1)]
  d=self.check_network(net);self.assertAlmostEqual(-1/d['currents_A']['TEST'],800)
  for rl in [100,800,4000,1e7]:
   d=self.check_network(a.controlled_net(load=rl));self.assertAlmostEqual(d['volts_V']['a'],2.8*rl/(800+rl))
  # gm cancels passive conductance exactly: inconsistent nonzero injection.
  with self.assertRaises(np.linalg.LinAlgError):a.solve(a.controlled_net(gm=.0015))
 def test_load_power_limits_and_complex_boundary(self):
  for e in (0.,-0.):
   zero=a.load_account(1000,e=e)
   self.assertIsNone(zero['eta'])
   for key in ('I_A','PL_W','PRs_W','Pdelivered_W'):self.assertEqual(zero[key],0.)
  # Nonzero source polarity changes current, not dissipated-power efficiency.
  neg=a.load_account(1000,e=-5)
  self.assertEqual(neg['eta'],.5);self.assertEqual(neg['I_A'],-.0025)
  at=a.load_account(1000);self.assertAlmostEqual(at['PL_W'],.00625);self.assertEqual(at['eta'],.5)
  for r in [1,250,1000,4000,99000,1e9]:
   d=a.load_account(r);self.assertAlmostEqual(d['PL_W']+d['PRs_W'],d['Pdelivered_W']);self.assertLessEqual(d['PL_W'],at['PL_W'])
  self.assertGreater(a.load_account(99000)['eta'],.98)
  z=100+50j
  def p(zl):return abs(1/(z+zl))**2*zl.real
  self.assertAlmostEqual(p(z.conjugate()),.0025)
  rp=abs(z);self.assertAlmostEqual(p(rp),1/(2*(100+rp)))
  self.assertGreater(p(rp),p(100));self.assertLess(p(rp),p(z.conjugate()))
 def test_bridge_exact_mna_loading_sensitivity(self):
  for delta in [-.3,-.01,0,.01,.3]:
   for load in [None,10000]:
    d=self.check_network(a.bridge_net(delta,load));v=d['volts_V']['b']-d['volts_V']['a'];self.assertAlmostEqual(v,a.bridge_exact(delta,load))
  h=1e-5;s=(a.bridge_exact(h)-a.bridge_exact(-h))/(2*h);self.assertAlmostEqual(s,1.25,places=8)
  d=.01;self.assertAlmostEqual((1.25*d-a.bridge_exact(d))/a.bridge_exact(d),d/2)
  for k,sgn in enumerate([1,-1,-1,1]):
   eps=np.zeros(4);eps[k]=h;u=a.solve(a.bridge_net(errors=eps));eps[k]=-h;w=a.solve(a.bridge_net(errors=eps));s=((u['volts_V']['b']-u['volts_V']['a'])-(w['volts_V']['b']-w['volts_V']['a']))/(2*h);self.assertAlmostEqual(s,sgn*1.25,places=8)
  d=self.check_network(a.bridge_net(errors=[.02]*4));self.assertAlmostEqual(d['volts_V']['a'],d['volts_V']['b'])
 def test_invalid_and_rank_cases(self):
  for value in [True,float('nan'),float('inf'),-1,0,1+2j,np.array([1+2j]),np.array([1],dtype=object),[1000],10**1000]:
   with self.assertRaises(ValueError):a.solve([('R','R','a','0',value)])
  for net in [[],[[]],np.array([['R','R','a','0','1000']],dtype=object),[('R','R','a','0',[[1000]])]]:
   with self.assertRaises(ValueError):a.solve(net)
  with self.assertRaises(ValueError):a.bridge_exact(-1)
  with self.assertRaises(np.linalg.LinAlgError):a.solve([('I','I','0','a',.001)])
  with self.assertRaises(np.linalg.LinAlgError):a.solve([('V','E1','a','0',1),('V','E2','a','0',2)])

if __name__=='__main__':unittest.main()
