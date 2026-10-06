"""Independent node, integration and direct DFT oracles; no asset writes."""
import unittest
import math
import numpy as np
import noise_models as m
class NoiseTests(unittest.TestCase):
    def test_thermal_norton_and_shot(self):
        self.assertAlmostEqual(m.thermal(2000),3.3135576e-17,delta=1e-30)
        r=2000;rl=3000
        self.assertAlmostEqual(m.thermal(r)*(rl/(r+rl))**2,(m.thermal(r)/r**2)*(r*rl/(r+rl))**2,delta=1e-30)
        self.assertEqual(m.shot(1e-6),3.204353268e-25)
        self.assertEqual(m.shot(1e-6,.3),.3*m.shot(1e-6))
    def test_ports_original_kcl(self):
        for f in [0,1,100,1e5,1e8]:
            A=1e5/(1+1j*f/10);ri=1e4;rf=9e4;rp=2e3
            # Variables [p,m,o], original KCL, vo=A(p-m+en).
            mat=np.array([[1/rp,0,0],[0,1/ri+1/rf,-1/rf],[-A,A,1]],complex)
            sources={'signal':[0,1/ri,0],'en':[0,0,A],'ip':[-1,0,0],'im':[0,-1,0],'ri_noise':[0,1/ri,0],'rf_noise':[0,1/rf,0],'rp_noise':[1/rp,0,0]}
            # e_rf raises the resistor's o-side endpoint; KCL RHS is +e_rf/Rf.
            for name,rhs in sources.items():self.assertLess(abs(np.linalg.solve(mat,rhs)[2]-m.ports(f)[name])/max(1,abs(m.ports(f)[name])),1e-12)
    def test_correlated_orientation_and_psd_rejection(self):
        self.assertEqual(m.spectral_output([1,1j],[[1,1j],[-1j,1]]),4)
        self.assertEqual(m.spectral_output([1,-1j],[[1,1j],[-1j,1]]),0)
        self.assertEqual(m.spectral_output([1,1],[[4,6],[6,9]]),25)
        self.assertEqual(m.spectral_output([1,1],[[4,-6],[-6,9]]),1)
        for s in [[[1,2],[2,1]],[[1,1j],[1j,1]],[[0,1e-40],[1e-40,1e-20]],[[1e-30,2e-30],[2e-30,1e-30]]]:
            with self.assertRaises(ValueError):m.spectral_output([1,1],s)
        rng=np.random.default_rng(13)
        for _ in range(20):
            B=rng.normal(size=(3,3))+1j*rng.normal(size=(3,3));S=B@B.conj().T;S=(S+S.conj().T)/2;h=rng.normal(size=3)+1j*rng.normal(size=3)
            actual=m.spectral_output(h.tolist(),S.tolist());expected=np.linalg.norm(h@B)**2
            self.assertAlmostEqual(actual,expected,delta=1e-10*expected)
    def test_rc_integral_independent_simpson(self):
        r=2000;c=1e-8;fc=1/(2*math.pi*r*c);upper=100*fc;n=20000
        f=np.linspace(0,upper,n+1);v=4*m.KB*300*r/(1+(2*math.pi*f*r*c)**2);simpson=(upper/n)/3*(v[0]+v[-1]+4*v[1:-1:2].sum()+2*v[2:-1:2].sum())
        self.assertAlmostEqual(simpson,m.rc_band(r,c,high=upper)['variance_V2'],delta=1e-21)
        self.assertAlmostEqual(m.rc_band(r,c)['variance_V2'],m.KB*300/c,delta=1e-25)
        self.assertAlmostEqual(m.rc_band(r,c,high=fc)['variance_V2'],m.KB*300/c/2,delta=1e-25)
        tiny=m.rc_band(r,c,low=1e12-1,high=1e12)['variance_V2'];self.assertGreater(tiny,0)
    def test_rc_variance_state_ode(self):
        # dV/dt=-2V/tau+2Ve/tau, separate RK4 integration, tau=.1.
        tau=.1;ve=m.KB*300/1e-6;dt=.3/3000;v=0
        rhs=lambda x:2*(ve-x)/tau
        for _ in range(3000):
            a=rhs(v);b=rhs(v+dt*a/2);c=rhs(v+dt*b/2);d=rhs(v+dt*c);v+=dt*(a+2*b+2*c+d)/6
        self.assertAlmostEqual(v,m.rc_state_variance(.3,1e5,1e-6),delta=1e-25)
        self.assertEqual(m.rc_state_variance(0,2000,1e-8,initial_variance=.2),.2)
    def test_periodogram_direct_DFT_and_parseval(self):
        for n in [4,5,16,17]:
            x=np.arange(n)%3-1.;y=np.cos(np.arange(n));fs=80
            for kind in ['rect','hann']:
                w=np.ones(n) if kind=='rect' else .5-.5*np.cos(2*math.pi*np.arange(n)/n)
                X=np.array([sum(w[j]*x[j]*np.exp(-2j*np.pi*k*j/n) for j in range(n)) for k in range(n//2+1)])
                Y=np.array([sum(w[j]*y[j]*np.exp(-2j*np.pi*k*j/n) for j in range(n)) for k in range(n//2+1)])
                fac=np.array([1 if k==0 or n%2==0 and k==n//2 else 2 for k in range(n//2+1)])
                z=m.periodogram(x,fs,kind,y=y);np.testing.assert_allclose(z['PSD_V2_per_Hz'],fac*abs(X)**2/(fs*sum(w*w)),rtol=1e-12,atol=1e-15);np.testing.assert_allclose(z['cross'],fac*X*Y.conj()/(fs*sum(w*w)),atol=1e-15)
                self.assertAlmostEqual(z['area_V2'],sum(w*w*x*x)/sum(w*w),places=13)
        z=m.periodogram([1,3,1,3],4);np.testing.assert_allclose(z['PSD_V2_per_Hz'],[4,0,1]);self.assertEqual(z['area_V2'],5)
        self.assertEqual(m.periodogram([1,3,1,3],4,remove_mean=True)['area_V2'],1)
        # Ordinary mean removal is not weighted mean removal after Hann.
        x=np.array([0.,0.,1.,0.]);w=np.array([0.,.5,1.,.5]);weighted_DC=sum(w*(x-x.mean()))
        self.assertEqual(weighted_DC,.5)
        z=m.periodogram(x,4,'hann',remove_mean=True)
        self.assertAlmostEqual(z['PSD_V2_per_Hz'][0],weighted_DC**2/(4*sum(w*w)))
        self.assertEqual(sum(w*(x-sum(w*x)/sum(w))),0)
    def test_windows_averaging_and_sample_scope(self):
        n=256;fs=4096;z=m.periodogram(np.cos(2*np.pi*16*np.arange(n)/n),fs,'hann');self.assertAlmostEqual(z['coherent_gain'],.5);self.assertAlmostEqual(z['window_ENBW_Hz'],24)
        self.assertAlmostEqual(z['PSD_V2_per_Hz'][16],1/(2*24))
        a=m.average_periodogram(np.ones(1024),fs,256);self.assertEqual(a['segments'],4)
        for rho in [-1,0,1]:
            x=m.correlated_sample(rho);self.assertEqual(x['theoretical_variance'],13+12*rho);self.assertEqual(x,m.correlated_sample(rho))
    def test_deembed_and_input_port(self):
        self.assertAlmostEqual(m.deembed(5e-6,3e-6,True)['rms_V'],4e-6)
        self.assertEqual(m.deembed(2e-6,3e-6,True)['status'],'below_instrument_floor')
        self.assertEqual(m.deembed(5e-6,3e-6)['status'],'unknown_correlation')
        with self.assertRaises(ValueError):m.referred(1,0)
        self.assertAlmostEqual(m.referred(4,1+1j),2)
    def test_invalid_before_conversion_and_budget(self):
        for x in [True,1j,1+0j,'1',float('nan'),float('inf'),[1],np.array(1)]:
            with self.assertRaises(ValueError):m.thermal(x)
        for x in [np.array([1+0j]*4),np.array([1,2,3,4],object),[[1],[2],[3],[4]],[1,2,3,True],[1,2,3,float('nan')]]:
            with self.assertRaises(ValueError):m.periodogram(x,4)
        for call in [lambda:m.rc_band(0,1),lambda:m.rc_band(1,1,low=2,high=1),lambda:m.white_flicker(1,1,0,2),lambda:m.correlated_sample(1.01),lambda:m.correlated_sample(0,n=262145),lambda:m.average_periodogram([1]*8,4,segment=5),lambda:m.periodogram([1]*4,0),lambda:m.shot(-1),lambda:m.rc_state_variance(-1,1,1),lambda:m.ports(0,fp=0)]:
            with self.assertRaises(ValueError):call()


class GeneratorStateTests(unittest.TestCase):
    def exercise_state(self, fail, env_present):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import matplotlib
        import cairosvg
        import generate_figures as g
        keys=('MPLCONFIGDIR','XDG_CACHE_HOME')
        initial={k:os.environ.get(k) for k in keys}
        with tempfile.TemporaryDirectory(prefix='noise-r2-global-') as td:
            try:
                for k in keys:
                    if env_present:os.environ[k]=str(Path(td)/('original-'+k))
                    else:os.environ.pop(k,None)
                before_env={k:os.environ.get(k) for k in keys}
                # Deliberately non-generator defaults, restored by rc_context.
                with matplotlib.rc_context({'font.family':['monospace'],'font.size':13,'svg.fonttype':'path','svg.hashsalt':'caller-salt'}):
                    before_rc=matplotlib.rcParams.copy()
                    if fail:
                        # A real late rendering error after figures/JSON were built.
                        with patch.object(cairosvg,'svg2png',side_effect=RuntimeError('injected SVG render failure')):
                            with self.assertRaisesRegex(RuntimeError,'injected SVG render failure'):g.generate(Path(td)/'out')
                        self.assertTrue((Path(td)/'out/figure-data.json').exists())
                    else:
                        g.generate(Path(td)/'out')
                        self.assertEqual(len(list((Path(td)/'out').glob('*.svg'))),9)
                    self.assertEqual(matplotlib.rcParams.copy(),before_rc)
                    self.assertEqual({k:os.environ.get(k) for k in keys},before_env)
            finally:
                for k,v in initial.items():
                    if v is None:os.environ.pop(k,None)
                    else:os.environ[k]=v
    def test_success_preserves_existing_environment_and_rc(self):self.exercise_state(False,True)
    def test_render_failure_restores_absent_environment_and_rc(self):self.exercise_state(True,False)

if __name__=='__main__':unittest.main()
