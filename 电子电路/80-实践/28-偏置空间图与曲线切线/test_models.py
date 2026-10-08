import math
import unittest
import models as m

class Models(unittest.TestCase):
    def test_pn_charge_and_integral(self):
        for vd in (0., .2, -1.):
            z = m.pn(vd, 0.)
            self.assertAlmostEqual(m.NA*z['xp']/(m.ND*z['xn']), 1.)
            # Triangle area of E from independent geometry, not phi evaluator.
            area = -z['E']*(z['xp']+z['xn'])/2
            self.assertAlmostEqual(area,z['barrier'],places=12)
            self.assertEqual(m.pn(vd,-8e-7)['n'],None)
            self.assertLess(z['E'],0)

    def test_pn_split_product_and_spatial_derivative(self):
        for vd in (0., .2, -1.):
            for x in (-1e-7,0.,5e-8):
                z=m.pn(vd,x)
                self.assertAlmostEqual(math.log(z['n']*z['p']/m.NI**2),vd/m.VT,places=11)
                h=1e-11
                phi_der=(m.pn(vd,x+h)['phi']-m.pn(vd,x-h)['phi'])/(2*h)
                self.assertLess(abs(phi_der+z['E'])/(1+abs(z['E'])),1e-4)
            self.assertAlmostEqual(m.pn(vd,-z['xp'])['p']/m.NA,1.)

    def test_load_closed_answers(self):
        mv,mi=m.intersection(lambda v:m.mos(1.5,v)[0])
        self.assertAlmostEqual(mv,3/1.04,places=11)
        self.assertAlmostEqual(mi,.001*(1+.02*mv),places=12)
        bv,bi=m.intersection(lambda v:m.bjt(.026*math.log(1e12),v)[0])
        self.assertAlmostEqual(bv,3.,places=10)
        self.assertAlmostEqual(bi,.001,places=12)

    def test_three_partial_derivatives(self):
        h=1e-6
        i,gd=m.diode(.5)
        self.assertAlmostEqual((m.diode(.5+h)[0]-m.diode(.5-h)[0])/(2*h)/gd,1.,places=8)
        i,gm,go=m.bjt(.7,3.)
        self.assertAlmostEqual((m.bjt(.7+h,3.)[0]-m.bjt(.7-h,3.)[0])/(2*h)/gm,1.,places=8)
        for vg,vd in [(1.5,.4),(1.5,3.)]:
            i,gm,go=m.mos(vg,vd)
            self.assertAlmostEqual((m.mos(vg+h,vd)[0]-m.mos(vg-h,vd)[0])/(2*h)/gm,1.,places=8)
            self.assertAlmostEqual((m.mos(vg,vd+h)[0]-m.mos(vg,vd-h)[0])/(2*h)/go,1.,places=7)

    def test_tangent_is_not_secant(self):
        v=.5;i,g=m.diode(v)
        self.assertGreater((v/i)*g,15.)
        i,gm,go=m.mos(1.5,3.)
        self.assertNotAlmostEqual(go,i/3.,places=5)

    def test_invalid_and_bracket(self):
        for v in (float('nan'),float('inf'),True,-3,.7):
            with self.assertRaises(ValueError):m.pn(v,0.)
        with self.assertRaises(ValueError):m.mos(4,3)
        with self.assertRaises(ValueError):m.intersection(lambda v:1.)

    def test_callback_finite_real_guard(self):
        # Valid bracket endpoints do not license an invalid interior output.
        for bad in (float('nan'), float('inf'), -float('inf'), True,
                    1j, '0.0', None, 10**1000):
            with self.subTest(bad_type=type(bad).__name__):
                with self.assertRaises(ValueError):
                    m.intersection(lambda v: 0.0 if v == 0 else (1.0 if v == 5 else bad))
        for bad in (float('nan'), float('inf'), True, None):
            with self.assertRaises(ValueError):m.intersection(lambda v:bad)
        # An independent linear port gives a finite closed-form load root.
        v,i=m.intersection(lambda v:v/2000.)
        self.assertAlmostEqual(v,2.5,places=12)
        self.assertAlmostEqual(i,.00125,places=15)

    def test_generation_restores_style_on_success_and_exception(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import matplotlib as mpl
        from matplotlib.figure import Figure
        import generate
        mpl.get_backend()  # Resolve lazy backend before recording style.
        style=dict(mpl.rcParams)
        env={key:os.environ.get(key) for key in ('MPLCONFIGDIR','XDG_CACHE_HOME')}
        with tempfile.TemporaryDirectory(prefix='wwl-devicefig-test-') as td:
            generate.generate(Path(td)/'ok')
            self.assertEqual(dict(mpl.rcParams),style)
            self.assertEqual({key:os.environ.get(key) for key in env},env)
            with patch.object(Figure,'savefig',side_effect=RuntimeError('injected render failure')):
                with self.assertRaises(RuntimeError):generate.generate(Path(td)/'failed')
            self.assertEqual(dict(mpl.rcParams),style)
            self.assertEqual({key:os.environ.get(key) for key in env},env)

if __name__=='__main__':unittest.main()
