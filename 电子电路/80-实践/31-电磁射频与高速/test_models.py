import unittest,math,cmath,sys,subprocess,itertools
import models as m
from pathlib import Path
class Models(unittest.TestCase):
 def test_invalid_scalar(self):
  for x in (True,1+0j,[],{},float('nan'),float('inf'),10**500):
   with self.assertRaises(ValueError):m.lossless(x,1e-10,.1)
  with self.assertRaises(ValueError):m.bounce(1,25,50,50,.5e-9,True)
  with self.assertRaises(ValueError):m.power_waves(1,.02,50+0j)
  with self.assertRaises(ValueError):m.reflection(-1,50)
 def test_line_units(self):
  v=m.lossless(250e-9,100e-12,.1);self.assertAlmostEqual(v['Z0_ohm'],50);self.assertAlmostEqual(v['delay_s'],.5e-9)
  self.assertAlmostEqual(v['speed_m_s'],2e8)
 def test_pde_independent_derivatives(self):
  # choose f=cos(wt-kx), g=.3sin(wt+kx) and check two original first-order PDEs
  l,c,w=250e-9,100e-12,1e9;z=50;speed=2e8;x=.07;t=1e-9;k=w/speed
  a=w*t-k*x;b=w*t+k*x
  vx=k*math.sin(a)+.3*k*math.cos(b);it=(-w*math.sin(a)-.3*w*math.cos(b))/z
  ix=(k*math.sin(a)-.3*k*math.cos(b))/z;vt=-w*math.sin(a)+.3*w*math.cos(b)
  self.assertAlmostEqual(vx,-l*it);self.assertAlmostEqual(ix,-c*vt)
 def test_rlcg_characteristic(self):
  out=m.rlcg(2,250e-9,.001,100e-12,1e8);gam,z=out['gamma_per_m'],out['Zc_ohm'];w=2*math.pi*1e8
  self.assertAlmostEqual(abs(gam*z-complex(2,w*250e-9)),0,10)
  self.assertAlmostEqual(abs(gam/z-complex(.001,w*100e-12)),0,10)
  ideal=m.rlcg(0,250e-9,0,100e-12,1e8);self.assertAlmostEqual(ideal['Zc_ohm'].real,50);self.assertAlmostEqual(ideal['gamma_per_m'].imag,w/2e8)
 def test_bounce_known_rationals(self):
  out=m.bounce(1,25,None,50,.5e-9,3);load=[v for v in out['events'] if v['end']=='load'];source=[v for v in out['events'] if v['end']=='source']
  for row,val in zip(load,[4/3,8/9,28/27]):self.assertAlmostEqual(row['total_V'],val)
  for row,val in zip(source,[2/3,10/9,26/27,82/81]):self.assertAlmostEqual(row['total_V'],val)
  self.assertEqual(out['Gamma_S'],-1/3)
 def test_bounce_original_boundary_each_hit(self):
  for zs,zl in itertools.product([0,25,50,100],[None,0,25,50,100]):
   out=m.bounce(1,zs,zl,50,1e-9,5);f=out['launch_V'];gl=out['Gamma_L'];gs=out['Gamma_S']
   # wave coefficients satisfy original load/source boundary rather than response recurrence
   for k in range(5):
    forward=out['waves'][2*k]['amplitude_V'];back=out['waves'][2*k+1]['amplitude_V']
    if zl is None:self.assertAlmostEqual((forward-back)/50,0)
    else:self.assertAlmostEqual(forward+back,zl*(forward-back)/50)
    nextf=gs*back;self.assertAlmostEqual(back+nextf,zs*(back-nextf)/50)
   if zs==0 and zl is None:self.assertEqual(gs*gl,-1);self.assertFalse(out['steady_state_claim'])
 def test_smith_extremes_and_quarter(self):
  for z,exp in [(0,-1),(50,0),(None,1),(100,1/3),(25,-1/3)]:self.assertAlmostEqual(abs(m.reflection(z,50)-exp),0)
  self.assertAlmostEqual(abs(m.input_impedance(100,50,math.pi/2)-25),0)
  with self.assertRaises(ValueError):m.input_impedance(None,50,0)
  for r,x in itertools.product([0,.2,1,2,10],[-5,-1,0,1,5]):
   z=complex(r,x);g=m.reflection(50*z,50);self.assertLessEqual(abs(g),1+1e-14);self.assertAlmostEqual(abs((1+g)/(1-g)-z),0,12)
 def test_power_wave_actual_power(self):
  for v,i in [(1,.01),(1+2j,.03-.02j),(-.5j,.04j)]:
   out=m.power_waves(v,i,50);self.assertAlmostEqual(out['net_W'],(v*complex(i).conjugate()).real)
 def test_power_wave_small_signed_port_power(self):
  # Fixed declared-domain counterexample: |a|^2-|b|^2 rounds to zero.
  for reference in (1,50,1000):
   for sign in (-1,1):
    for v,i in ((1e6,sign*1e-12),(1e6j,sign*1e-12j)):
     self.assertEqual(m.power_waves(v,i,reference)['net_W'],sign*1e-6)
   self.assertEqual(m.power_waves(1e6,1e-12j,reference)['net_W'],0.)
 def test_noise_direct_added_sources(self):
  stages=[[10,2],[4,5],[.5,2]];p=m.friis_noise(stages);noise=1;gain=1
  for g,f in stages:noise=g*noise+(f-1)*g;gain*=g
  self.assertAlmostEqual(p['factor'],noise/gain);self.assertAlmostEqual(m.friis_noise([[.5,2],[10,2],[4,5]])['factor'],4.8)
 def test_cubic_two_tone_projection(self):
  n=4096;a=.1;f1,f2=17,23;values=[m.cubic_output(a*(math.cos(2*math.pi*f1*k/n)+math.cos(2*math.pi*f2*k/n)),2,-1) for k in range(n)]
  amplitude=lambda f:2*math.fsum(v*math.cos(2*math.pi*f*k/n) for k,v in enumerate(values))/n
  self.assertAlmostEqual(amplitude(2*f1-f2),-.75*a**3,12)
  self.assertAlmostEqual(amplitude(f1),2*a-2.25*a**3,12)
 def test_compression_from_waveform(self):
  info=m.cubic_metrics(2,-1);a=info['IP1dB_peak_V_single_tone'];n=2048
  amp=2*math.fsum(m.cubic_output(a*math.cos(2*math.pi*k/n),2,-1)*math.cos(2*math.pi*k/n) for k in range(n))/n
  self.assertAlmostEqual(amp/(2*a),10**(-1/20),12)
 def test_iq_from_real_coordinates(self):
  g,e=1.1,.08;v=m.iq_image(g,e)
  for z in [1+2j,-.5+.3j]:
   original=complex(z.real,g*(math.cos(e)*z.imag+math.sin(e)*z.real));self.assertAlmostEqual(abs(original-(v['alpha']*z+v['beta']*z.conjugate())),0)
  self.assertAlmostEqual(m.iq_image(1.1,0)['IRR_dB'],10*math.log10(441));self.assertIsNone(m.iq_image(1,0)['IRR_dB'])
 def test_diff_original_coordinate(self):
  x=m.differential_skew(.5,1e9,2e-11,0);self.assertAlmostEqual(abs(x['Vdiff_peak']),math.cos(math.pi*.02));self.assertAlmostEqual(abs(x['Vcommon_peak']),.5*math.sin(math.pi*.02))
 def test_eye_original_ode_solution(self):
  bits=[1]*16;out=m.eye_record(bits,1e-9,.25e-9,32)
  for t,y in zip(out['sample_times_s'],out['samples_V']):self.assertAlmostEqual(y,1-math.exp(-t/.25e-9),12)
  bits=[1,-1]*8;out=m.eye_record(bits,1e-9,.25e-9,32);previous=0
  for k,b in enumerate(bits):
   end=b+(previous-b)*math.exp(-4);self.assertAlmostEqual(out['samples_V'][(k+1)*32-1],end,12);previous=end
 def test_isi_enumerate_all_histories(self):
  taps=[.7,.2,-.1];vals=[sum(h*b for h,b in zip(taps,[1]+list(hist))) for hist in itertools.product([-1,1],repeat=2)]
  self.assertAlmostEqual(min(vals),m.isi_margin(taps)['half_opening_V'])
 def test_pdn_original_kcl(self):
  out=m.pdn_impedance(1e8,[[1e-7,.02,1e-9],[1e-9,.02,1e-9]]);v=out['Z_ohm'];currents=[v/z for z in out['branch_Z_ohm']]+[v/out['source_Z_ohm']];self.assertAlmostEqual(abs(sum(currents)-1),0)
  for f in [1e5,1e7,1e8,1e9]:self.assertGreater(m.pdn_impedance(f,[[1e-7,.02,1e-9]])['Z_ohm'].real,0)
 def test_pattern_spherical_integral(self):
  n=10000;dt=math.pi/n;integral=2*math.pi*sum(math.sin((k+.5)*dt)**3*dt for k in range(n));self.assertAlmostEqual(4*math.pi/integral,1.5,7)
  self.assertEqual(m.dipole_pattern(0,0)['normalized_power'],0);self.assertEqual(m.dipole_pattern(math.pi/2,0)['power_radius_xyz'],(1.,0.,math.cos(math.pi/2)))
 def test_friis_from_flux_and_aperture(self):
  a=m.friis_link(.1,1.5,1.5,1e9,10);lam=299792458/1e9;flux=.1*1.5/(4*math.pi*100);ae=1.5*lam**2/(4*math.pi);self.assertAlmostEqual(a['received_W'],flux*ae)
  self.assertAlmostEqual(m.friis_link(.1,1.5,1.5,1e9,20)['received_W'],a['received_W']/4)
  with self.assertRaises(ValueError):m.friis_link(.1,1,1,1e9,.01)
 def test_pure_import(self):
  r=subprocess.run([sys.executable,'-B','-c',"import sys;sys.argv=['unexpected'];import models,generate;assert not any(x in sys.modules for x in ['numpy','matplotlib','cairosvg'])"],capture_output=True,text=True,cwd=Path(__file__).parent);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
