import unittest,math
from dataclasses import replace
from power_models import *
from power_models import _rk4 as rk4, _off_step as off_step
class PowerChecks(unittest.TestCase):
 def test_ccm_voltseconds_charge(self):
  p=Params();s=buck_summary(p);self.assertAlmostEqual(s['v_V'],5);self.assertAlmostEqual(s['delta_i_A'],7/24);self.assertAlmostEqual((p.vin-5)*p.d-5*(1-p.d),0);self.assertGreater(5/p.r-s['delta_i_A']/2,0)
 def test_dcm_charge_triangle(self):
  p=Params(r=100);s=buck_summary(p);v=s['v_V'];ip=(12-v)*p.d/(p.l*p.fs);self.assertGreater(s['d3'],0);self.assertAlmostEqual(ip*(p.d+s['d2'])/2,v/p.r);self.assertAlmostEqual((12-v)*p.d-v*s['d2'],0)
 def test_boundary(self):
  p=Params();r=buck_summary(p)['r_boundary_ohm'];a=buck_summary(replace(p,r=r*(1-1e-6)));b=buck_summary(replace(p,r=r*(1+1e-6)));self.assertEqual(buck_summary(replace(p,r=r))['mode'],'boundary');self.assertEqual(a['mode'],'CCM');self.assertEqual(b['mode'],'DCM');self.assertAlmostEqual(b['v_V'],5,places=5)
 def test_other_topology_dcm(self):
  d=.4;k=.01;m=conversion('boost',d,k);self.assertAlmostEqual(k*m*(m-1),d*d);m=conversion('inverting',d,k);self.assertAlmostEqual(m*m*k,d*d)
 def test_rk4_convergence_vs_exact_on(self):
  # R=infinity is not an API parameter: independent lossless derivative test uses local toy object.
  from types import SimpleNamespace
  p=SimpleNamespace(vin=12,l=1e-4,c=1e-4,r=math.inf);x=(.5,5.);t=50e-6;w=1/math.sqrt(p.l*p.c)
  truth=(.5*math.cos(w*t)+(12-5)*math.sqrt(p.c/p.l)*math.sin(w*t),12+(5-12)*math.cos(w*t)+.5*math.sqrt(p.l/p.c)*math.sin(w*t))
  err=[]
  for n in (2,4,8):
   y=x
   for _ in range(n):y=rk4(p,y,t/n,1)
   err.append(max(abs(a-b) for a,b in zip(y,truth)))
  self.assertGreater(err[0]/err[1],14);self.assertGreater(err[1]/err[2],14)
 def test_ccm_energy_balance_and_mean(self):
  p=Params();rows=simulate(p,cycles=2000,steps=32);a=rows[-65:];integral=0.
  for x,y in zip(a,a[1:]):
   # h interval belongs to ending row; switching q is that row's mode.
   q=1 if y['mode']=='on' else 0;h=y['t_s']-x['t_s'];integral+=h*((q*p.vin*x['i_A']-x['v_V']**2/p.r)+(q*p.vin*y['i_A']-y['v_V']**2/p.r))/2
  energy=lambda z:.5*p.l*z['i_A']**2+.5*p.c*z['v_V']**2
  self.assertLess(abs(energy(a[-1])-energy(a[0])-integral),1e-9)
  duration=a[-1]['t_s']-a[0]['t_s'];vmean=sum((y['t_s']-x['t_s'])*(x['v_V']+y['v_V'])/2 for x,y in zip(a,a[1:]))/duration;self.assertAlmostEqual(vmean,5,places=3)
 def test_idle_exact_and_nonnegative(self):
  p=Params(r=100);v=buck_summary(p)['v_V'];rows=simulate(p,cycles=100,steps=32,initial=(0,v));self.assertGreater(sum(z['mode']=='idle' for z in rows),0);self.assertGreaterEqual(min(z['i_A'] for z in rows),0);x,mode=off_step(p,(0,5),1e-6);self.assertEqual(mode,'idle');self.assertAlmostEqual(x[1],5*math.exp(-1e-6/(p.r*p.c)))
 def test_average_q_and_transfer(self):
  p=Params();r=simulate(p,cycles=2,average=True);self.assertTrue(all(abs(z['v_V']-5)<1e-12 for z in r));self.assertEqual(buck_gvd(p,0),12);w=1/math.sqrt(p.l*p.c);self.assertAlmostEqual(abs(buck_gvd(p,w)),12*p.r*math.sqrt(p.c/p.l));self.assertAlmostEqual(boost_zero(p),p.r*(1-p.d)**2/p.l)
 def test_controller_reduces_error(self):
  p=Params();a=simulate(p,cycles=2000,steps=16,initial=(.49,4.95),average=True,control_k=.01);self.assertLess(abs(a[-1]['v_V']-5),.01)
 def test_comparison_mode_and_out_of_domain_counterexample(self):
  p=Params();sw=simulate(p,400,32,initial=(.49,4.95),control_k=.01);av=simulate(p,400,32,initial=(.49,4.95),average=True,control_k=.01)
  self.assertFalse(any('idle' in z['mode'] for z in sw));self.assertGreater(min(z['i_A'] for z in sw),.22);self.assertGreater(min(z['i_A'] for z in av),0)
  self.assertEqual((sw[0]['i_A'],sw[0]['v_V']),(av[0]['i_A'],av[0]['v_V']))
  # Original R1 large excursion is a model-domain counterexample, not averaging error.
  bad_sw=simulate(p,400,32,initial=(.4,4),control_k=.01);bad_av=simulate(p,400,32,initial=(.4,4),average=True,control_k=.01)
  self.assertTrue(any('idle' in z['mode'] for z in bad_sw));self.assertLess(min(z['i_A'] for z in bad_av),0)
 def test_loss_thermal_units(self):
  p=Params();r=losses(p);self.assertAlmostEqual(r['total_W'],sum(r['parts'].values()));self.assertLess(r['efficiency'],1);self.assertEqual(thermal(0,1),25);self.assertAlmostEqual(thermal(20,1),25+40*(1-math.exp(-1)));self.assertAlmostEqual(magnetic_delta(7,5/12/1e5,20,25e-6),.05833333333333333)
 def test_pwm_common_mode_and_power_identity(self):
  r=pwm_phases(.4);self.assertAlmostEqual(sum(r['phase_V']),0);self.assertAlmostEqual(sum(r['line_V']),0);self.assertTrue(all(0<=d<=1 for d in r['duty']))
 def test_matrices_and_boost_initial_inverse(self):
  p=Params(d=.4,r=40);a=1-p.d;v=p.vin/a;i=v/(p.r*a);mat=state_matrices(p,'boost')
  def original(x,d):
   ii,vv=x;return ((p.vin-(1-d)*vv)/p.l,((1-d)*ii-vv/p.r)/p.c)
  h=1e-6
  for col,dx in enumerate(((h,0),(0,h))):
   plus=original((i+dx[0],v+dx[1]),p.d);minus=original((i-dx[0],v-dx[1]),p.d)
   for row in range(2):
    expected=p.d*mat['Aon'][row][col]+a*mat['Aoff'][row][col];self.assertAlmostEqual((plus[row]-minus[row])/(2*h),expected,places=3)
  actual=original((i,v),p.d+.001);self.assertAlmostEqual(actual[1],-i*.001/p.c);self.assertGreater(boost_gvd(p,0).real,0)
 def test_fixed_design_constraints(self):
  points=design_candidates();self.assertEqual(len(points),12);valid=[q for q in points if q['feasible']];self.assertGreater(len(valid),0)
  for q in valid:
   self.assertLessEqual(q['delta_i_A'],.3);self.assertLessEqual(q['delta_v_V'],.01);self.assertLessEqual(q['estimated_shared_rise_K'],10);self.assertAlmostEqual(q['objective'],q['loss_W'])
 def test_invalid_before_cast_and_budget(self):
  for value in (True,1+0j,float('nan'),float('inf'),10**1000,[],{},'12'):
   with self.assertRaises((TypeError,ValueError)):Params(vin=value)
   with self.assertRaises((TypeError,ValueError)):thermal(value,1)
  for args in ({'cycles':True},{'cycles':2001},{'steps':1},{'initial':(1+0j,5)},{'average':1}):
   with self.assertRaises((TypeError,ValueError)):simulate(Params(),**args)
  with self.assertRaises(ValueError):conversion('boost',.4,.5)
  with self.assertRaises(ValueError):losses(Params(r=100))
if __name__=='__main__':unittest.main()
