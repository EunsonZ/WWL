import cmath
import math
import unittest
from models import cases, waveform


class FixedExampleTests(unittest.TestCase):
    def test_independent_closed_values(self):
        expected = {'R': (1+0j, 10, 0), 'RL': (.5-.5j, 5, 5),
                    'RC': (.5+.5j, 5, -5), 'RLC': (.8-.4j, 8, 4)}
        for c in cases():
            i, p, q = expected[c['name']]
            self.assertAlmostEqual(abs(c['I_rms'] - i), 0)
            self.assertAlmostEqual(c['P_W'], p)
            self.assertAlmostEqual(c['Q_var'], q)
            self.assertAlmostEqual(c['apparent_VA'] ** 2, p*p+q*q)

    def test_time_domain_conservation_and_period_mean(self):
        for c in cases():
            rows = waveform(c)
            mean = lambda key: math.fsum(r[key] for r in rows) / len(rows)
            self.assertAlmostEqual(mean('p_W'), c['P_W'], places=12)
            self.assertAlmostEqual(mean('pR_W'), c['P_W'], places=12)
            self.assertAlmostEqual(mean('pL_W'), 0, places=12)
            self.assertAlmostEqual(mean('pC_W'), 0, places=12)
            self.assertAlmostEqual(mean('v_V'), 0, places=12)
            for r in rows:
                self.assertAlmostEqual(r['v_V'], r['vR_V']+r['vL_V']+r['vC_V'], places=12)
                self.assertAlmostEqual(r['p_W'], r['pR_W']+r['pL_W']+r['pC_W'], places=12)

    def test_constitutive_derivatives(self):
        c = cases()[-1]
        for theta in (.13, .5, 2.1):
            e = cmath.exp(1j*theta)
            di = math.sqrt(2)*(1j*c['omega_rad_s']*c['I_rms']*e).real
            dvc = math.sqrt(2)*(1j*c['omega_rad_s']*c['VC_rms']*e).real
            self.assertAlmostEqual(c['L_H']*di, math.sqrt(2)*(c['VL_rms']*e).real)
            self.assertAlmostEqual(c['C_F']*dvc, math.sqrt(2)*(c['I_rms']*e).real)

    def test_valid_negative_instantaneous_power(self):
        c = cases()[-1]
        self.assertGreater(c['P_W'], 0)
        self.assertLess(min(r['p_W'] for r in waveform(c)), -.9)

    def test_shared_phase_and_peak_convention(self):
        c = cases()[-1]; r = cmath.exp(.8j)
        self.assertAlmostEqual(abs((c['V_rms']*r)*(c['I_rms']*r).conjugate()-c['S_VA']), 0)
        self.assertAlmostEqual(abs((math.sqrt(2)*c['V_rms'])*(math.sqrt(2)*c['I_rms']).conjugate()/2-c['S_VA']), 0)

    def test_records_and_sample_contract(self):
        a = cases(); a[0]['R_ohm']=999
        self.assertEqual(cases()[0]['R_ohm'], 10)
        for n in (True, 1, 255, 65537, 256.0, None):
            with self.assertRaises(ValueError): waveform(cases()[0], n)
        with self.assertRaises(ValueError): waveform({'name':'R'})


if __name__ == '__main__':
    unittest.main()
