"""Independent numerical/port checks and generator process contract tests."""
import cmath
import csv
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from transform_lab import rc_state, rl_state, modal

HERE=Path(__file__).resolve().parent


def simpson(function, a, b, n=4000):
    h=(b-a)/n
    return h/3*(function(a)+function(b)+4*sum(function(a+k*h) for k in range(1,n,2))+2*sum(function(a+k*h) for k in range(2,n,2)))


def rk4(function, initial, end, n=1000):
    h=end/n;y=initial
    for k in range(n):
        t=k*h
        a=function(t,y);b=function(t+h/2,y+h*a/2)
        c=function(t+h/2,y+h*b/2);d=function(t+h,y+h*c)
        y+=h*(a+2*b+2*c+d)/6
    return y


class NumericalTests(unittest.TestCase):
    def test_rc_ivp_independent_rk4(self):
        for source,initial in [(1.,.4),(0.,.4),(1.,1.2),(-.2,-.4)]:
            for t in [.00025,.001,.003]:
                result=rk4(lambda t,v:(source-v)/(1000*1e-6),initial,t)
                self.assertAlmostEqual(rc_state(t,source,initial)['v_V'],result,places=11)
        self.assertAlmostEqual(rc_state(.00025)['v_V'],.5327195301571571,places=14)
        self.assertAlmostEqual(rc_state(.001)['v_V'],.7792723352971346,places=14)

    def test_large_source_retains_initial_and_tiny_time_increment(self):
        # Decimal integrates the analytic IVP with 80 digits; it does not use
        # the implementation's floating-point expm1 or weighted evaluation.
        self.assertEqual(rc_state(0, source_V=1e16)['v_V'], .4)
        self.assertEqual(rl_state(0, source_V=1e16)['i_A'], .02)
        self.assertEqual(rc_state(0, source_V=1e16)['q_C'], 1e-6*.4)
        self.assertEqual(rc_state(0, source_V=1e16)['energy_J'], .5*1e-6*.4*.4)
        for source in [1e16, -1e16]:
            for function, initial, tau, final, times, key in [
                (rc_state, '.4', '.001', Decimal(str(source)), [1e-22,1e-20], 'v_V'),
                (rl_state, '.02', '.0001', Decimal(str(source))/100, [1e-24,1e-22], 'i_A')]:
                for t in times:
                    with localcontext() as context:
                        context.prec=80
                        decay=(-Decimal(str(t))/Decimal(tau)).exp()
                        expected=Decimal(initial)*decay+final*(1-decay)
                    self.assertAlmostEqual(function(t,source_V=source)[key], float(expected), places=14)

    def test_charge_and_energy_balance(self):
        end=.003;initial=rc_state(0.);final=rc_state(end)
        current=simpson(lambda t:rc_state(t)['i_A'],0,end)
        self.assertAlmostEqual(final['q_C']-initial['q_C'],current,places=16)
        delivered=simpson(lambda t:rc_state(t)['i_A'],0,end)
        heat=simpson(lambda t:1000*rc_state(t)['i_A']**2,0,end)
        self.assertAlmostEqual(final['energy_J']-initial['energy_J'],delivered-heat,places=16)
        # Ideal source energy and resistor dissipation are not equal to stored energy.
        self.assertGreater(heat,0.)

    def test_rl_ivp_and_energy(self):
        for t in [.0001,.00025,.001]:
            numerical=rk4(lambda t,i:(1-100*i)/.01,.02,t,n=2000)
            self.assertAlmostEqual(rl_state(t)['i_A'],numerical,places=13)
        self.assertAlmostEqual(rl_state(.0001)['vL_V'],-1/math.e,places=14)
        natural=rl_state(.0001,source_V=0)
        self.assertAlmostEqual(natural['energy_J']/rl_state(0,source_V=0)['energy_J'],math.exp(-2),places=14)

    def test_modal_axes_and_frequency(self):
        self.assertAlmostEqual(modal(.001,-500,2000),math.exp(-.5)*math.cos(2),places=14)
        self.assertAlmostEqual(modal(2*math.pi/1000,0,1000),1.,places=14)
        self.assertAlmostEqual(modal(.001,-2000,0),math.exp(-2),places=14)

    def test_right_and_left_roc_integrals(self):
        a=1000.
        for s in [complex(500,200),complex(1000,600)]:
            numeric=simpson(lambda t:cmath.exp(-(s+a)*t),0,.05,n=12000)
            self.assertLess(abs(numeric-1/(s+a)),1e-12)
        s=complex(-1500,200)
        left=simpson(lambda t:-cmath.exp(-(s+a)*t),-.08,0,n=12000)
        self.assertLess(abs(left-1/(s+a)),1e-12)
        # Boundary weighted absolute integrand is identically 1, so its
        # integral over [0,M] increases with M and has no absolute ROC there.
        self.assertAlmostEqual(abs(cmath.exp(-complex(0,500)*10)),1.,places=14)

    def test_bilateral_strip_and_unilateral_origin(self):
        s=complex(500,200);a=1000.
        strip=simpson(lambda t:math.exp(-a*abs(t))*cmath.exp(-s*t),-.06,0,n=12000)+simpson(lambda t:math.exp(-a*t)*cmath.exp(-s*t),0,.06,n=12000)
        self.assertLess(abs(strip-2*a/(a*a-s*s)),1e-12)
        X=simpson(lambda t:cmath.exp(-(s+a)*t),0,.05,n=12000)
        ordinary=simpson(lambda t:-a*cmath.exp(-(s+a)*t),0,.05,n=12000)
        self.assertLess(abs(ordinary-(s*X-1)),1e-9)
        pre_initial=.4;jump=1-pre_initial
        self.assertLess(abs(ordinary+jump-(s*X-pre_initial)),1e-9)

    def test_capacitor_initial_source_ports(self):
        s=complex(500,200);R=1000.;C=1e-6;v0=.4;U=1/s
        # Solve KCL with upward initial current source; compare to an
        # independent finite time integral of the declared physical response.
        V=(U/R+C*v0)/(1/R+s*C)
        reference=simpson(lambda t:(1-.6*math.exp(-t/.001))*cmath.exp(-s*t),0,.08,n=24000)
        self.assertLess(abs(V-reference),1e-12)
        I=(U-V)/R
        self.assertLess(abs(I-(s*C*V-C*v0)),1e-18)
        self.assertLess(abs(V-(I/(s*C)+v0/s)),1e-17)
        wrong=(U/R-C*v0)/(1/R+s*C)
        self.assertGreater(abs(wrong-V),1e-4)

    def test_inductor_initial_source_ports(self):
        s=complex(500,200);R=100.;L=.01;i0=.02;U=1/s
        I=(U+L*i0)/(R+s*L)
        reference=simpson(lambda t:(.01+.01*math.exp(-10000*t))*cmath.exp(-s*t),0,.08,n=40000)
        self.assertLess(abs(I-reference),1e-13)
        V=U-R*I
        self.assertLess(abs(V-(s*L*I-L*i0)),1e-17)
        self.assertLess(abs(I-(V/(s*L)+i0/s)),1e-17)

    def test_invalid_inputs(self):
        for function in [rc_state,rl_state]:
            for t in [-1.,math.inf,math.nan,True,".001"]:
                with self.assertRaises(ValueError):function(t)
        for value in [0.,-1.,math.inf,True]:
            with self.assertRaises(ValueError):rc_state(0.,r_ohm=value)
            with self.assertRaises(ValueError):rl_state(0.,l_H=value)
        with self.assertRaises(ValueError):modal(1.,1000.,0.)
        with self.assertRaises(ValueError):modal(2.,1e308,0.)
        with self.assertRaises(ValueError):modal(2.,0.,1e308)
        with self.assertRaises(ValueError):rc_state(0.,initial_V=1e308)
        with self.assertRaises(ValueError):rl_state(0.,initial_A=1e308)


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='wwl-transform-')
        self.addCleanup(self.temp.cleanup);self.work=Path(self.temp.name)
        self.before={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}

    def tearDown(self):
        after={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(after,self.before)

    def run_process(self,args):
        return subprocess.run([sys.executable,'-B',*args],cwd=self.work,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=120)

    def test_import_and_missing_output_are_side_effect_free(self):
        script="import sys;sys.path.insert(0,sys.argv[1]);sys.argv=['other','--unknown'];import build_visuals;assert 'cairosvg' not in sys.modules;assert callable(build_visuals.generate) and callable(build_visuals.main)"
        result=self.run_process(['-c',script,str(HERE)])
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(list(self.work.iterdir()),[])
        result=self.run_process([str(HERE/'build_visuals.py')])
        self.assertEqual(result.returncode,2,result.stderr);self.assertIn('--output',result.stderr)
        self.assertEqual(list(self.work.iterdir()),[])

    def test_nested_output_units_xml_and_narrow_pngs(self):
        output=self.work/'new'/'nested'/'assets'
        result=self.run_process([str(HERE/'build_visuals.py'),'--output',str(output)])
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads((output/'parameters.json').read_text())
        self.assertEqual(len(data['figures']),6)
        for svg in output.glob('*.svg'):
            tree=ET.parse(svg).getroot();ns='{http://www.w3.org/2000/svg}'
            self.assertTrue(tree.find(ns+'title').text);self.assertTrue(tree.find(ns+'desc').text)
        for png in output.glob('*.png'):
            width=struct.unpack('>I',png.read_bytes()[16:20])[0]
            self.assertEqual(width,360 if png.stem.endswith('-360') else 425)
        with (output/'state-data.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),501)
        self.assertEqual(float(rows[0]['rc_voltage_V']),.4)
        self.assertAlmostEqual(float(rows[25]['rc_voltage_V']),.5327195301571571,places=14)
        self.assertEqual(float(rows[0]['rl_current_A']),.02)


if __name__=='__main__':
    unittest.main()
