import unittest,math
from fractions import Fraction
import core_lab as a
class Contracts(unittest.TestCase):
    def test_divider_kcl_and_exact_loading(self):
        self.assertEqual(5*(1/(Fraction(1,1000)+Fraction(1,4000)))/(4000+1/(Fraction(1,1000)+Fraction(1,4000))),Fraction(5,6))
        for rl in (None,1000,4000,10000,1e6):
            v=a.divider(5,4000,1000,rl);out=v/1000+(v/rl if rl else 0)
            self.assertLess(abs((5-v)/4000-out),1e-18)
    def test_source_absorption_and_cross_power(self):
        for e in (1,3,6):
            d=a.source_ledger(e2_v=e)
            self.assertLess(abs(sum(d[k] for k in ('source1_abs_W','source2_abs_W','resistor_abs_W'))),1e-17)
        d=a.source_ledger();self.assertAlmostEqual(d['source2_abs_W'],.001)
        cross=4000*(.00125-.00025)**2-4000*(.00125**2+.00025**2)
        self.assertAlmostEqual(cross,-.0025)
    def test_energy_differential_and_integral_ledger(self):
        for t in (0,.0001,.001,.004):
            d=a.rc_account(t);self.assertLess(abs(d['p_source_abs_W']+d['p_R_W']+d['p_C_W']),1e-18)
            self.assertLess(abs(d['source_delivered_J']-d['R_loss_J']-d['C_delta_J']),1e-21)
        d=a.rc_account(.02);self.assertAlmostEqual(d['source_delivered_J'],.6e-6,places=14)
        integral=a.midpoint(lambda t:a.rc_account(t)['p_C_W'],0,.01,20000)
        self.assertLess(abs(integral-a.rc_account(.01)['C_delta_J']),2e-15)
    def test_pulse_signed_area_energy_and_initial_value(self):
        self.assertAlmostEqual(a.pulse_voltage(.001),.6);self.assertAlmostEqual(a.pulse_voltage(.003),.5)
        q=a.midpoint(a.pulse_current,0,.003,3000);absolute=a.midpoint(lambda t:abs(a.pulse_current(t)),0,.003,3000)
        self.assertAlmostEqual(q,.1e-6,places=15);self.assertAlmostEqual(absolute,.3e-6,places=15)
        e=a.midpoint(lambda t:a.pulse_voltage(t)*a.pulse_current(t),0,.003,3000)
        self.assertAlmostEqual(e,.045e-6,places=15)
        for t in (.0005,.0015,.0025):self.assertAlmostEqual(a.pulse_voltage(t,.1)-a.pulse_voltage(t,.4),-.3)
    def test_db_impedance_and_log_inverse(self):
        self.assertAlmostEqual(a.amplitude_db(.5)+a.power_db(1000/250),a.power_db((.5**2/250)/(1/1000)))
        for r in (.1,.01,.001):self.assertAlmostEqual(math.exp(-a.decay_time(.001,r)/.001),r)
        self.assertAlmostEqual(a.amplitude_db(1/math.sqrt(2)),a.power_db(.5))
        self.assertAlmostEqual(1000*1e-6,.001)
    def test_probe_loading_and_ammeter_burden(self):
        for f in (0,1000,10000):
            v=a.probe_h(f);self.assertLess(abs((1-v)/100000-v/1000000-2j*math.pi*f*100e-12*v),1e-20)
        self.assertAlmostEqual(a.divider(5,4000,1000,1e6),1e6/(1e6+800))
        i=5/5010;self.assertAlmostEqual(i*5010,5);self.assertAlmostEqual(i*10,.00998003992)
    def test_nodes_residual_power_and_unit_scaling(self):
        import numpy as np
        va,vb=a.two_nodes();self.assertAlmostEqual(va,1.2);self.assertAlmostEqual(vb,.8)
        Y=np.array([[.0015,-.001],[-.001,.0015]]);v=np.array([va,vb]);b=np.array([.001,0])
        self.assertLess(np.linalg.norm(Y@v-b),1e-18);self.assertAlmostEqual(v@Y@v,va*.001)
        self.assertAlmostEqual(np.linalg.cond(Y/.001),5)
        K=np.array([[.001,1],[1,0]]);Km=np.array([[.001,.001],[1,0]]);Kh=np.array([[1,1],[1,0]])
        raw=np.linalg.solve(K,[0,1]);ma=np.linalg.solve(Km,[0,1]);norm=np.linalg.solve(Kh,[0,1])
        self.assertTrue(np.allclose(raw,ma*[1,.001]));self.assertTrue(np.allclose(raw,norm*[1,.001]));self.assertAlmostEqual(np.linalg.cond(Kh),(3+math.sqrt(5))/2)
        self.assertGreater(np.linalg.cond(Km),900)
        base=a.two_nodes(1e-8,.001,.001,-.001);pert=a.two_nodes(1e-8,.001,.001+1e-9,-.001+1e-9)
        self.assertTrue(np.allclose(np.array(pert)-base,[.1,.1]));self.assertAlmostEqual(np.linalg.cond(np.array([[.00100001,-.001],[-.001,.00100001]])),200001,places=4)
    def test_invalid_inputs(self):
        for value in (0,-1,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):a.divider(5,value,1000)
        with self.assertRaises(ValueError):a.power_db(0)
        with self.assertRaises(ValueError):a.decay_time(.001,1.01)
        with self.assertRaises(ValueError):a.pulse_voltage(-1)
if __name__=='__main__':unittest.main()
