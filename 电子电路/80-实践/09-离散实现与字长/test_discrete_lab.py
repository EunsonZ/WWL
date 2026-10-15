"""Independent IVP/Fraction/series oracles; original RC interface read-only."""
import csv
from fractions import Fraction
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from discrete_lab import (coefficients,simulate,interval_h,bilinear_h,modal_map,prewarp,
 Format,round_divide,simulate_codes,fir_codes)

HERE=Path(__file__).resolve().parent


def original_rc():
    path=HERE.parent/'01-RC跨层'/'rc_lab.py'
    spec=importlib.util.spec_from_file_location('wwl_original_rc_readonly',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def rk4_hold(initial,inputs,T,steps=2000):
    value=initial;result=[value];dt=T/steps
    for u in inputs:
        f=lambda v:(u-v)/.001
        for _ in range(steps):
            a=f(value);b=f(value+dt*a/2);c=f(value+dt*b/2);d=f(value+dt*c)
            value+=dt*(a+2*b+2*c+d)/6
        result.append(value)
    return result


class NumericalTests(unittest.TestCase):
    def test_original_n_plus_one_and_hold_ivp(self):
        rc=original_rc().RC();inputs=[1.,0.,.5,-.1]
        for method in ['exact','euler']:
            values=simulate(inputs,initial_V=.4,method=method)
            self.assertEqual(len(values),5);self.assertEqual(values[0],.4)
            self.assertEqual(values,list(rc.simulate(inputs,.00025,v0=.4,method=method)))
        actual=simulate(inputs);reference=rk4_hold(.4,inputs,.00025)
        for value,expected in zip(actual,reference):self.assertAlmostEqual(value,expected,places=13)
        self.assertEqual(simulate([],initial_V=.4),[.4])
        self.assertEqual(simulate([1],initial_V=0)[0],0)
        self.assertAlmostEqual(simulate([1],initial_V=0)[1],.2211992169285951,places=15)

    def test_single_and_bilateral_series_initial_and_delay(self):
        a,b=coefficients();z=complex(1.2,.1)
        sequence=simulate([1.]+[0.]*119,initial_V=.4)
        summed=sum(v*z**(-k) for k,v in enumerate(sequence))
        expected=.4/(1-a/z)+b/(z-a)
        self.assertLess(abs(summed-expected),1e-14)
        impulse=simulate([1.]+[0.]*5,initial_V=0)
        self.assertEqual(impulse[0],0.)
        for k in range(1,7):self.assertAlmostEqual(impulse[k],b*a**(k-1),places=15)
        # Independent left-side geometric sum including k=0.
        z=complex(.3,.1)
        left=sum(-b*a**(k-1)*z**(-k) for k in range(-90,1))
        self.assertLess(abs(left-b/(z-a)),1e-14)

    def test_methods_against_equations_and_fixed_time_orders(self):
        for method in ['backward','trapezoid_hold']:
            a,b=coefficients(method=method);v0=.4;u=1.;v1=simulate([u],initial_V=v0,method=method)[1];h=.25
            if method=='backward':residual=v1-v0-h*(u-v1)
            else:residual=v1-v0-h/2*((u-v0)+(u-v1))
            self.assertAlmostEqual(residual,0,places=15)
            self.assertAlmostEqual(a+b,1,places=15)
        exact=1-.6*math.exp(-1)
        for method,order in [('euler',1),('backward',1),('trapezoid_hold',2)]:
            errors=[]
            for n in [40,80,160]:errors.append(abs(simulate([1.]*n,T_s=.001/n,method=method)[-1]-exact))
            observed=math.log2(errors[-2]/errors[-1]);self.assertLess(abs(observed-order),.03)

    def test_euler_boundary_and_mapping_regions(self):
        values=simulate([0.]*4,T_s=.002,method='euler')
        self.assertEqual(values,[.4,-.4,.4,-.4,.4])
        self.assertGreater(abs(simulate([0.]*5,T_s=.0025,method='euler')[-1]),.4)
        for method in ['exact','backward','bilinear']:
            self.assertLess(abs(modal_map(-1000,.0025,method)),1)
        self.assertEqual(abs(modal_map(-1000,.002,'euler')),1)
        self.assertGreater(abs(modal_map(1j*4000,.00025,'euler')),1)
        self.assertLess(abs(modal_map(1j*4000,.00025,'backward')),1)
        for method in ['exact','bilinear']:self.assertAlmostEqual(abs(modal_map(1j*4000,.00025,method)),1,places=14)
        self.assertLess(abs(modal_map(3000,.001,'backward')),1) # numerical stability does not prove physical stability

    def test_bilinear_is_not_interval_transfer(self):
        a,b=coefficients(method='trapezoid_hold');self.assertAlmostEqual(a,7/9,places=15)
        for theta in [.1,.25,1.,2.5]:
            expected=1/complex(1,.001*prewarp(theta))
            self.assertLess(abs(bilinear_h(theta)-expected),1e-14)
            self.assertGreater(abs(bilinear_h(theta)-interval_h(theta,method='trapezoid_hold')),1e-4)
        self.assertAlmostEqual(abs(bilinear_h(math.pi)),0,places=14)
        self.assertAlmostEqual(interval_h(0).real,1,places=15)

    def test_aliasing_and_prewarp_units(self):
        T=.00025
        for k in range(-10,11):self.assertAlmostEqual(math.cos(2*math.pi*1000*k*T),math.cos(2*math.pi*3000*k*T),places=13)
        self.assertAlmostEqual(math.cos(2*math.pi*1000*T/2),math.sqrt(.5),places=14)
        self.assertAlmostEqual(math.cos(2*math.pi*3000*T/2),-math.sqrt(.5),places=14)
        s=-1000+1000j;other=s+2j*math.pi/T
        self.assertLess(abs(modal_map(s,T)-modal_map(other,T)),1e-14)
        prototype_tau=1/prewarp(.25)
        self.assertLess(abs(bilinear_h(.25,prototype_tau_s=prototype_tau)-complex(.5,-.5)),1e-14)
        self.assertAlmostEqual(prewarp(math.pi/2),8000,places=10)
        self.assertAlmostEqual(2*math.atan(1000*T/2)/(2*math.pi*T),158.33369664226217,places=10)

    def test_rounding_exhaustive_fraction_oracle(self):
        for denominator in range(1,18):
            for numerator in range(-200,201):
                fraction=Fraction(numerator,denominator)
                self.assertEqual(round_divide(numerator,denominator),round(fraction))
                self.assertEqual(round_divide(numerator,denominator,'toward_zero'),math.trunc(fraction))

    def test_integer_rc_exact_fraction_and_original_float_reference(self):
        fmt=Format();a,b=coefficients();A=fmt.encode(a);B=fmt.encode(b);initial=fmt.encode(.4)
        self.assertEqual((A,B,initial),(12760,3624,6554));self.assertEqual(A+B,fmt.scale)
        inputs=[1.]*8+[-.1]*4;codes=[fmt.encode(u) for u in inputs]
        result=simulate_codes(codes,A,B,initial,fmt)
        oracle=[initial]
        for u in codes:oracle.append(max(fmt.low,min(fmt.high,round(Fraction(A*oracle[-1]+B*u,fmt.scale)))))
        self.assertEqual(result,oracle);self.assertEqual(result[0],initial);self.assertEqual(len(result),len(codes)+1)
        original=original_rc();reference=original.RC().simulate(inputs,.00025,v0=.4,quantizer=original.QFormat(16,14))
        self.assertEqual([fmt.decode(q) for q in result],list(reference))

    def test_deadband_period_two_and_truncation(self):
        fmt=Format(8,4)
        self.assertEqual(simulate_codes([0]*8,12,0,1,fmt),[1]*9)
        self.assertEqual(simulate_codes([0]*8,-12,0,1,fmt),[1,-1,1,-1,1,-1,1,-1,1])
        self.assertEqual(simulate_codes([0]*4,-12,0,1,fmt,'toward_zero'),[1,0,0,0,0])
        # Complete finite state space, not a few plotted points.
        for q in range(fmt.low,fmt.high+1):
            result=simulate_codes([0]*256,12,0,q,fmt)
            self.assertEqual(result[-1],result[-2])

    def test_overflow_locations_and_fir_flush(self):
        fmt=Format(8,4)
        self.assertEqual(simulate_codes([112],0,32,0,fmt),[0,127])
        self.assertEqual(simulate_codes([112],0,32,0,fmt,overflow='wrap'),[0,-32])
        with self.assertRaises(OverflowError):simulate_codes([112],0,32,0,fmt,accumulator_bits=12)
        self.assertEqual(fir_codes([16,0,0,0,0],[4,8,4],fmt),[4,8,4,0,0])
        self.assertEqual(fir_codes([127,0,0,0,0],[127,127,127],fmt)[-2:],[0,0])

    def test_deterministic_error_bound_no_saturation(self):
        fmt=Format();a,b=coefficients();A=fmt.encode(a);B=fmt.encode(b);initial=.4;inputs=[.7,-.3,.5,0.,1.]*20
        ideal=simulate(inputs,initial_V=initial);codes=simulate_codes([fmt.encode(x) for x in inputs],A,B,fmt.encode(initial),fmt)
        ahat=A/fmt.scale;bhat=B/fmt.scale;delta=1/fmt.scale
        E=abs(ahat-a)+abs(bhat-b)+abs(bhat)*delta/2+delta/2;e0=abs(fmt.decode(codes[0])-initial)
        for k,(v,q) in enumerate(zip(ideal,codes)):
            bound=abs(ahat)**k*e0+E*(1-abs(ahat)**k)/(1-abs(ahat))
            self.assertLessEqual(abs(fmt.decode(q)-v),bound+1e-15)
            self.assertGreater(q,fmt.low);self.assertLess(q,fmt.high)

    def test_real_sources_reject_complex_before_conversion(self):
        import numpy as np
        import warnings
        invalid=[1+2j,1+0j,object(),[1.],np.array(1+2j),
                 np.array(1+0j),np.array([1+2j],dtype=object)]
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for value in invalid:
                with self.subTest(value_type=type(value).__name__):
                    with self.assertRaises(ValueError):simulate([value])
                    with self.assertRaises(ValueError):simulate([],initial_V=value)
                    with self.assertRaises(ValueError):Format().encode(value)
            for values in [np.array([1+2j]),np.array([1+0j]),
                           np.array([1+2j],dtype=object),[[1.]]]:
                with self.assertRaises(ValueError):simulate(values)
            self.assertEqual(captured,[])
        self.assertEqual(simulate(np.array([1.,0.])),simulate([1.,0.]))
        self.assertIsInstance(interval_h(.25),complex)
        self.assertIsInstance(modal_map(1000j,.00025),complex)

    def test_invalid_inputs_and_explicit_policy(self):
        for value in [True,'0.25',math.nan,math.inf]:
            with self.assertRaises(ValueError):coefficients(value)
            with self.assertRaises(ValueError):simulate([value])
        for value in [-1,0]:
            with self.assertRaises(ValueError):coefficients(value)
        for theta in [math.pi,-math.pi,4.,math.inf]:
            with self.assertRaises(ValueError):prewarp(theta)
        with self.assertRaises(ValueError):modal_map(1,.001,'bad')
        with self.assertRaises(ValueError):modal_map(1000,.001,'backward')
        with self.assertRaises(ValueError):modal_map(2000,.001,'bilinear')
        with self.assertRaises(ValueError):coefficients(1e308,1e-308)
        with self.assertRaises(ValueError):coefficients(1e-308,1e308)
        with self.assertRaises(ValueError):modal_map(10**1000,1)
        with self.assertRaises(ValueError):simulate_codes([],1,1,0,Format(),rounding='bad')
        with self.assertRaises(ValueError):simulate_codes([],1,1,0,Format(),overflow='bad')
        with self.assertRaises(ValueError):simulate_codes([True],1,1,0)
        with self.assertRaises(ValueError):simulate_codes([32768],1,1,0)
        with self.assertRaises(ValueError):Format(16,16)
        with self.assertRaises(ValueError):fir_codes([],[])


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wwl-discrete-');self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.before={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    def tearDown(self):
        after={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts};self.assertEqual(after,self.before)
    def process(self,args):return subprocess.run([sys.executable,'-B',*args],cwd=self.work,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=120)
    def test_import_and_missing_output(self):
        result=self.process(['-c',"import sys;sys.path.insert(0,sys.argv[1]);sys.argv=['alien','--unknown'];import discrete_lab,build_visuals;assert 'cairosvg' not in sys.modules",str(HERE)])
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(list(self.work.iterdir()),[])
        result=self.process([str(HERE/'build_visuals.py')]);self.assertEqual(result.returncode,2,result.stderr);self.assertIn('--output',result.stderr);self.assertEqual(list(self.work.iterdir()),[])
    def test_nested_generation_structure_units_and_codes(self):
        output=self.work/'new'/'nested'/'assets';result=self.process([str(HERE/'build_visuals.py'),'--output',str(output)]);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(list(output.glob('*.svg'))),7)
        for file in output.glob('*.svg'):
            root=ET.parse(file).getroot();ns='{http://www.w3.org/2000/svg}';self.assertTrue(root.find(ns+'title').text);self.assertTrue(root.find(ns+'desc').text)
            for node in root.findall('.//'+ns+'text'):self.assertGreaterEqual(float(node.attrib['font-size']),13)
        for file in output.glob('*.png'):self.assertEqual(struct.unpack('>I',file.read_bytes()[16:20])[0],360 if file.stem.endswith('-360') else 425)
        with (output/'state-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(float(rows[0]['time_s']),0.);self.assertEqual(float(rows[0]['exact_V']),.4)
        self.assertAlmostEqual(float(rows[1]['exact_V']),.5327195301571571,places=14)
        with (output/'integer-data.csv').open() as stream:rows=list(csv.DictReader(stream))
        self.assertEqual(int(rows[0]['coarse_fixed_code']),1);self.assertEqual(int(rows[1]['coarse_cycle_code']),-1)
        self.assertEqual(int(rows[2]['coarse_cycle_code']),1)


if __name__=='__main__':unittest.main()
