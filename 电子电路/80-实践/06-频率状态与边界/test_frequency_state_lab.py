"""Independent time/phasor/transform oracles and explicit-output generator checks."""
import csv
import hashlib
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import xml.etree.ElementTree as ET
import numpy as np
from frequency_state_lab import (rc_h,rc_started_cosine,db_phase,rc_asymptotic_db,
 second_order_h,zero_pair_h,rlc_physical,rlc_normalized,hidden_model,port_h,rank_matrices)

HERE=Path(__file__).resolve().parent


def simpson(f,a,b,n=10000):
    step=(b-a)/n
    return step/3*(f(a)+f(b)+4*sum(f(a+k*step) for k in range(1,n,2))+2*sum(f(a+k*step) for k in range(2,n,2)))


def rk4(f,initial,end,n=4000):
    h=end/n;y=np.asarray(initial,dtype=float)
    for k in range(n):
        t=k*h;k1=f(t,y);k2=f(t+h/2,y+h*k1/2);k3=f(t+h/2,y+h*k2/2);k4=f(t+h,y+h*k3)
        y=y+h*(k1+2*k2+2*k3+k4)/6
    return y


class NumericalTests(unittest.TestCase):
    def test_rc_h_against_fourier_integral_and_passive_kcl(self):
        for w in [0.,100.,1000.,10000.]:
            integral=simpson(lambda t:1000*math.exp(-1000*t)*np.exp(-1j*w*t),0,.035,n=40000)
            self.assertLess(abs(rc_h(w)-integral),2e-10)
            # Direct phasor node KCL: resistor current equals j*w*C*V.
            v=rc_h(w)
            self.assertLess(abs((1-v)/1000-1j*w*1e-6*v),1e-17)
        self.assertEqual(rc_h(1000),complex(.5,-.5))
        self.assertAlmostEqual(1000/(2*math.pi),159.15494309189535,places=12)

    def test_started_cosine_rk4_nonzero_initial(self):
        self.assertEqual(rc_started_cosine(0),.4)
        for w in [100.,1000.,10000.]:
            for initial in [0.,.4,1.2]:
                for t in [.00025,.001]:
                    expected=rk4(lambda t,y:np.array([(math.cos(w*t)-y[0])/.001]),[initial],t)[0]
                    self.assertAlmostEqual(rc_started_cosine(t,w,initial),expected,places=12)
        self.assertAlmostEqual(rc_started_cosine(.00025),.5302781121754433,places=14)
        # Zero initial and tiny t must retain the first slope times t.
        self.assertAlmostEqual(rc_started_cosine(1e-22,initial_V=0)/(1e-19),1.,places=14)

    def test_initial_final_and_counterexamples_independently(self):
        # Full RC response transform integrated independently at positive real s.
        for s in [100.,1000.,10000.]:
            numerical=simpson(lambda t:(1-.6*math.exp(-1000*t))*math.exp(-s*t),0,40/s,n=40000)
            self.assertAlmostEqual(numerical,1/s-.6/(s+1000),places=11)
        response=lambda s:1/s-.6/(s+1000)
        self.assertAlmostEqual(1e12*response(1e12),.4,places=8)
        self.assertAlmostEqual(1e-8*response(1e-8),1.,places=10)
        # Algebra sX->0 does not imply a time limit for sin or growth.
        self.assertEqual(np.real(1j*1000),0.)
        self.assertGreater(1000.,0.)
        self.assertAlmostEqual(math.sin(math.pi/2),1.)
        self.assertAlmostEqual(math.sin(3*math.pi/2),-1.)
        self.assertGreater(math.exp(10),10000.)

    def test_roc_direction_not_rational_value(self):
        a=1000.;w=300.
        # Stable anti-causal kernel with RHP pole; integrate left half-line.
        integral=simpson(lambda t:-a*math.exp(a*t)*np.exp(-1j*w*t),-.04,0,n=20000)
        self.assertLess(abs(integral-a/(1j*w-a)),1e-12)
        # Same rational a/(s+a), left kernel grows toward -infinity.
        absolute=lambda M:math.expm1(a*M)
        self.assertGreater(absolute(.002),absolute(.001)*2)

    def test_bode_exact_factors_and_asymptote(self):
        for w in [100.,1000.,10000.]:
            db,phase=db_phase(rc_h(w))
            self.assertAlmostEqual(db,-10*math.log10(1+(w/1000)**2),places=12)
            self.assertAlmostEqual(phase,-math.degrees(math.atan(w/1000)),places=12)
        self.assertAlmostEqual(rc_asymptotic_db(1000)-db_phase(rc_h(1000))[0],3.010299956639812,places=12)
        squared=rc_h(1000)**2
        self.assertAlmostEqual(db_phase(squared)[0],-6.020599913279624,places=12)
        self.assertAlmostEqual(db_phase(squared)[1],-90.,places=12)
        self.assertAlmostEqual(rc_asymptotic_db(2000),-6.020599913279624,places=12)

    def test_nonminimum_zero_equal_magnitude_opposite_contribution(self):
        for w in [100.,1000.,10000.]:
            left=zero_pair_h(w);right=zero_pair_h(w,True)
            self.assertAlmostEqual(abs(left),abs(right),places=14)
            lp,rp=db_phase(left)[1],db_phase(right)[1]
            self.assertAlmostEqual(lp-rp,2*math.degrees(math.atan(w/1000)),places=12)
        self.assertAlmostEqual(db_phase(zero_pair_h(1000))[1],39.28940686250036,places=12)
        self.assertAlmostEqual(db_phase(zero_pair_h(1000,True))[1],-50.71059313749964,places=12)
        # Direct impulse decomposition D + exponential tail includes feedthrough.
        w=1000.
        left=10+simpson(lambda t:-90000*math.exp(-10000*t)*np.exp(-1j*w*t),0,.004,n=20000)
        right=-10+simpson(lambda t:110000*math.exp(-10000*t)*np.exp(-1j*w*t),0,.004,n=20000)
        self.assertLess(abs(left-zero_pair_h(w)),1e-11)
        self.assertLess(abs(right-zero_pair_h(w,True)),1e-11)
        self.assertEqual(1-11*math.exp(0),-10)
        self.assertLess(1-11*math.exp(-.5),0)
        self.assertGreater(1-11*math.exp(-10),0)


    def test_rlc_frequency_physical_equations_state_and_resonance(self):
        physical=rlc_physical();normalized=rlc_normalized()
        for w in [100.,1000.,10000.,100000.]:
            # KVL with passive i=j*w*C*v: 1=(1-L*C*w^2+j*R*C*w)*v.
            expected=1/complex(1-.01*1e-6*w*w,50*1e-6*w)
            self.assertLess(abs(second_order_h(w)-expected),1e-14)
            self.assertLess(abs(port_h(w,physical)[0,0]-expected),1e-14)
            self.assertLess(abs(port_h(w,normalized)[0,0]-expected),1e-14)
        self.assertEqual(second_order_h(10000),-2j)
        peak_w=10000*math.sqrt(1-2*.25**2)
        peak=1/(2*.25*math.sqrt(1-.25**2))
        self.assertAlmostEqual(abs(second_order_h(peak_w)),peak,places=14)
        self.assertGreater(abs(second_order_h(peak_w)),abs(second_order_h(10000)))
        poles=np.linalg.eigvals(physical[0])
        self.assertTrue(np.allclose(np.real(poles),-2500))
        self.assertTrue(np.allclose(abs(np.imag(poles)),math.sqrt(1e8-2500**2)))

    def test_rlc_physical_time_and_normalization(self):
        A,B,C,D=rlc_normalized()
        for t in [.0001,.00025,.0005]:
            physical=rk4(lambda t,x:np.array([x[1]/1e-6,(1-50*x[1]-x[0])/.01]),[.4,.003],t)
            normalized=rk4(lambda t,x:A@x+B[:,0],[.4,.3],t)
            self.assertTrue(np.allclose(physical,[normalized[0],normalized[1]*.01],atol=1e-13,rtol=0))

    def test_controllability_observability_and_hidden_modes(self):
        reach,observe=rank_matrices(rlc_normalized())
        self.assertTrue(np.array_equal(reach,np.array([[0,1e8],[1e4,-5e7]])))
        self.assertTrue(np.array_equal(observe,np.array([[1,0],[0,1e4]])))
        self.assertAlmostEqual(np.linalg.det(reach)/(-1e12),1.,places=13)
        self.assertEqual(np.linalg.matrix_rank(reach),2);self.assertEqual(np.linalg.matrix_rank(observe),2)
        for kind,ranks in [('unobservable',(2,1)),('uncontrollable',(1,2))]:
            model=hidden_model(kind);reach,observe=rank_matrices(model)
            self.assertEqual((np.linalg.matrix_rank(reach),np.linalg.matrix_rank(observe)),ranks)
            for w in [0.,1000.,2000.]:self.assertLess(abs(port_h(w,model)[0,0]-rc_h(w)),1e-15)
            self.assertTrue(np.any(np.linalg.eigvals(model[0])>0))
        # Independently integrate active model, verify invisible state grows.
        A,B,C,D=hidden_model();state=rk4(lambda t,x:A@x+B[:,0],[0.,0.],.005)
        self.assertAlmostEqual(state[0],1-math.exp(-5),places=12)
        self.assertAlmostEqual(state[1],math.expm1(5),places=9)
        self.assertAlmostEqual((C@state)[0],state[0],places=14)
        A,B,C,D=hidden_model('uncontrollable')
        state=rk4(lambda t,x:A@x,[0.,.01],.005)
        self.assertAlmostEqual((C@state)[0],.01*math.exp(5),places=11)

    def test_real_model_rejects_complex_before_lossy_cast(self):
        base=(np.array([[-1.]]),np.ones((1,1)),np.ones((1,1)),np.zeros((1,1)))
        models=[]
        # Regression: the old cast silently replaced -1+5j by -1.
        models.append((np.array([[-1+5j]]),*base[1:]))
        models.append((np.array([[-1+5j]],dtype=object),*base[1:]))
        models.append(([[-1+5j]],*base[1:]))
        # The real contract applies to all four matrices, even complex 0j.
        for index in range(4):
            model=list(base);model[index]=model[index].astype(complex);models.append(tuple(model))
        for model in models:
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter('always')
                with self.assertRaises(ValueError):port_h(0,model)
                with self.assertRaises(ValueError):rank_matrices(model)
            self.assertEqual(emitted,[])
        self.assertEqual(port_h(0,base)[0,0],1.)

    def test_invalid_domain_and_shapes(self):
        for f in [rc_h,rc_asymptotic_db,second_order_h,zero_pair_h]:
            for value in [math.inf,math.nan,True,'1000']:
                with self.assertRaises(ValueError):f(value)
        with self.assertRaises(ValueError):rc_h(1,r_ohm=0)
        with self.assertRaises(ValueError):rc_h(1e308,r_ohm=1e308)
        with self.assertRaises(ValueError):rc_started_cosine(2.,1e308)
        with self.assertRaises(ValueError):second_order_h(1,damping=0)
        with self.assertRaises(ValueError):db_phase(0j)
        with self.assertRaises(ValueError):db_phase(complex(1.7e308,1.7e308))
        with self.assertRaises(ValueError):port_h(1,(np.eye(2),np.ones((1,1)),np.ones((1,2)),np.zeros((1,1))))
        with self.assertRaises(ValueError):port_h(0,(np.zeros((1,1)),np.ones((1,1)),np.ones((1,1)),np.zeros((1,1))))


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wwl-freqstate-');self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.before={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    def tearDown(self):
        after={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(after,self.before)
    def process(self,args):
        return subprocess.run([sys.executable,'-B',*args],cwd=self.work,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=120)
    def test_import_and_missing_output_no_write(self):
        r=self.process(['-c',"import sys;sys.path.insert(0,sys.argv[1]);sys.argv=['foreign','--unknown'];import build_visuals,frequency_state_lab;assert 'cairosvg' not in sys.modules",str(HERE)])
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(list(self.work.iterdir()),[])
        r=self.process([str(HERE/'build_visuals.py')]);self.assertEqual(r.returncode,2,r.stderr);self.assertIn('--output',r.stderr);self.assertEqual(list(self.work.iterdir()),[])
    def test_nested_output_xml_pixels_and_numerical_csv(self):
        output=self.work/'new'/'nested'/'assets';r=self.process([str(HERE/'build_visuals.py'),'--output',str(output)]);self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(len(list(output.glob('*.svg'))),7)
        for file in output.glob('*.svg'):
            root=ET.parse(file).getroot();ns='{http://www.w3.org/2000/svg}'
            self.assertTrue(root.find(ns+'title').text);self.assertTrue(root.find(ns+'desc').text)
            self.assertEqual(root.attrib['width'],'425')
            for node in root.findall('.//'+ns+'text'):self.assertGreaterEqual(float(node.attrib['font-size']),13)
        for file in output.glob('*.png'):
            self.assertEqual(struct.unpack('>I',file.read_bytes()[16:20])[0],360 if file.stem.endswith('-360') else 425)
        with (output/'frequency-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        corner=next(row for row in rows if float(row['omega_rad_s'])==1000)
        self.assertEqual(float(corner['rc_real']),.5);self.assertEqual(float(corner['rc_imag']),-.5)
        self.assertAlmostEqual(float(corner['rc_dB']),-3.010299956639812,places=12)
        with (output/'time-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(float(rows[0]['rc_started_V']),.4)
        self.assertEqual(float(rows[0]['zero_LHP_step_V']),10.)
        self.assertEqual(float(rows[0]['zero_RHP_step_V']),-10.)
        self.assertAlmostEqual(float(rows[25]['rc_started_V']),.5302781121754433,places=14)
        self.assertAlmostEqual(float(rows[-1]['hidden_x2_dimensionless']),math.expm1(5),places=12)


if __name__=='__main__':unittest.main()
