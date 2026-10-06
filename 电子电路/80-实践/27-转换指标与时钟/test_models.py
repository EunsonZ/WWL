import unittest,math,subprocess,sys,pathlib,itertools
from models import *
class ADCModels(unittest.TestCase):
    def test_invalid_scalars(self):
        for v in (True,1j,[],{},float('nan'),float('inf'),10**1000):
            with self.assertRaises(ValueError): jitter_snr(v,1e-12)
    def test_invalid_vectors(self):
        for v in (True,[[1]],list(range(15)),[0]*17,[float('nan')]*32,[True]*32):
            with self.assertRaises(ValueError): one_sided_power(v)
    def test_static_independent_widths(self):
        s=static_metrics([1.1,2,3.2,4.2,4.2,6.3,7.1],0,8,3)
        self.assertEqual(s['missing_internal_codes'],[4]);self.assertAlmostEqual(s['offset_V'],.1);self.assertAlmostEqual(s['gain_error_relative'],0)
        for actual,expected in zip(s['internal_dnl_LSB'],[-.1,.2,0,-1,1.1,-.2]):self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(s['endpoint_transition_inl_LSB'][3],.1)
        self.assertAlmostEqual(s['endpoint_transition_inl_LSB'][4],-.9)
    def test_static_affine_invariance(self):
        t=[.2+1.03*j for j in range(1,8)];v=static_metrics(t,0,8,3)
        self.assertAlmostEqual(v['offset_V'],.23);self.assertAlmostEqual(v['gain_error_relative'],.03)
        self.assertLess(max(abs(x) for x in v['endpoint_transition_inl_LSB']),1e-14)
        with self.assertRaises(ValueError):static_metrics([1,2,4,3,5,6,7],0,8,3)
    def test_dft_fft_independent(self):
        import numpy as np
        x=[.2+.4*math.sin(2*math.pi*3*j/64)+.1*(-1)**j for j in range(64)]
        got=one_sided_power(x);ref=abs(np.fft.rfft(x)/64)**2;ref[1:-1]*=2
        self.assertLess(max(abs(a-b) for a,b in zip(got,ref)),1e-14)
        self.assertAlmostEqual(math.fsum(got),math.fsum(v*v for v in x)/64)
        self.assertAlmostEqual(got[0],.04);self.assertAlmostEqual(got[-1],.01);self.assertAlmostEqual(got[3],.08)
    def test_dynamic_known_tones(self):
        n=128;x=[.1+.8*math.sin(2*math.pi*5*j/n)+.02*math.sin(2*math.pi*15*j/n)+.005*math.cos(2*math.pi*17*j/n) for j in range(n)]
        v=coherent_metrics(x,5)
        self.assertAlmostEqual(v['SINAD_dB'],10*math.log10(.8**2/(.02**2+.005**2)),places=10)
        self.assertAlmostEqual(v['SFDR_dBc'],20*math.log10(.8/.02),places=10)
        self.assertAlmostEqual(v['SNR_dB'],20*math.log10(.8/.005),places=10)
        self.assertAlmostEqual(v['THD_dB'],20*math.log10(.02/.8),places=10)
        self.assertAlmostEqual(v['ENOB_amplitude_normalized']-v['ENOB_from_SINAD'],20*math.log10(1/.8)/6.02)
    def test_dynamic_collisions_and_floor(self):
        x=[.5*math.sin(2*math.pi*5*j/128) for j in range(128)];self.assertIsNone(coherent_metrics(x,5)['SNR_dB'])
        with self.assertRaises(ValueError):coherent_metrics([0.]*32,1)
        with self.assertRaises(ValueError):coherent_metrics([0.]*32,8)
        with self.assertRaises(ValueError):coherent_metrics([2.]*32,1)
    def test_white_averaging_enumerated(self):
        means=[block_average(list(x),4)[0] for x in itertools.product((-1,1),repeat=4)]
        self.assertAlmostEqual(math.fsum(v*v for v in means)/16,1/4)
        # A correlated DC error stays unchanged, no square-root-M improvement.
        self.assertEqual(block_average([.1]*16,4),[.1]*4)
    def test_shaped_band_independent_integral(self):
        for m in (1,4,64,256):
            a=math.pi/m;n=4096;h=a/n
            integ=math.fsum((1 if j in (0,n) else 4 if j%2 else 2)*4*math.sin((j*h)/2)**2 for j in range(n+1))*h/3
            ref=(.25**2/12)/math.pi*integ
            self.assertAlmostEqual(band_variance(.25,m,True),ref,delta=max(1e-18,ref*2e-10))
        self.assertAlmostEqual(band_variance(.25,4),band_variance(.25,1)/4)
    def test_modulator_exact_difference(self):
        for x in (-.75,0,.25,.95):
            d=sigma_delta_dc(x,512);prev_e=d['initial_e']
            for y,e,v in zip(d['bits'],d['errors'],d['states']):
                self.assertAlmostEqual(y,x+e-prev_e);prev_e=e
                self.assertLessEqual(v,x+1+1e-10);self.assertGreaterEqual(v,x-1-1e-10)
            self.assertAlmostEqual(d['mean']-x,(d['errors'][-1]-d['initial_e'])/512)
            self.assertLessEqual(abs(d['mean']-x),2/512+1e-14)
        self.assertEqual(sigma_delta_dc(0,16)['bits'],[-1.,1.]*8)
    def test_modulator_domain_budget(self):
        for x,n in ((1,16),(.1,65537),(.1,True)):
            with self.assertRaises(ValueError):sigma_delta_dc(x,n)
        with self.assertRaises(ValueError):block_average([1,2,3],2)
    def test_zoh_original_integral(self):
        fd=1000.;f=100.;n=10000;h=1/fd/n
        re=math.fsum(math.cos(2*math.pi*f*(j+.5)*h) for j in range(n))/n
        im=-math.fsum(math.sin(2*math.pi*f*(j+.5)*h) for j in range(n))/n
        self.assertLess(abs(zoh_normalized(f,fd)-complex(re,im)),1e-9)
        self.assertEqual(zoh_normalized(0,fd),1)
    def test_jitter_sine_difference(self):
        a,f,t,dt=.8,10000.,2e-5,1e-9
        direct=a*(math.sin(2*math.pi*f*(t+dt))-math.sin(2*math.pi*f*t))
        self.assertAlmostEqual(sine_timing_error(a,f,t,dt),direct,places=14)
        self.assertAlmostEqual(jitter_snr(1e7,1e-12),84.0364026328377)
        with self.assertRaises(ValueError):jitter_snr(1e9,1e-6)
    def test_phase_integral_constant_and_inverse_f(self):
        v=phase_jitter([(1e3,-140),(1e6,-140)],1e8)
        self.assertAlmostEqual(v['phase_variance_rad2'],2e-14*(1e6-1e3),places=20)
        inv=phase_jitter([(1e3,-100),(1e5,-120)],1e8)
        self.assertAlmostEqual(inv['phase_variance_rad2'],2e-7*math.log(100),places=18)
        self.assertAlmostEqual(v['time_rms_s']*2*math.pi*1e8,v['phase_rms_rad'])
        with self.assertRaises(ValueError):phase_jitter([(100,-100),(10,-100)],1e8)
    def test_pll_characteristic_and_paths(self):
        a,b=1400.,1e6;v=pll_coefficients(a,b)
        for z in v['poles']:self.assertLess(abs(z*z+a*z+b),1e-9)
        for w in (0,10,1000,1e5):
            h=pll_transfer(a,b,w);self.assertLess(abs(h['S']+h['T']-1),1e-14)
            if w:
                l=a/(1j*w)+b/(1j*w)**2
                self.assertLess(abs(h['T']-l/(1+l)),1e-14)
        wc=v['omega_c_rad_s'];self.assertAlmostEqual(abs(a/(1j*wc)+b/(1j*wc)**2),1)
    def test_pure_import(self):
        p=pathlib.Path(__file__).with_name('models.py');code="import sys,runpy;sys.argv=['models.py','--bad'];runpy.run_path("+repr(str(p))+");assert 'matplotlib' not in sys.modules;assert 'numpy' not in sys.modules"
        r=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__':unittest.main()
