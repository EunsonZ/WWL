"""Targeted physical/analytical regressions, no matrix-grid proof claims."""
import copy
import json
import math
from pathlib import Path
import unittest
import active_match as lab

ROOT = Path(__file__).parent


class ActiveMatchTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT/"fixed-inputs.json").read_text())
        self.m, self.sc, self.n = lab.validate(self.cfg)

    def test_legacy_and_terminal_voltage(self):
        r = lab.run(self.cfg)["legacy"]
        self.assertAlmostEqual(r["gamma_L"].real, .4)
        self.assertAlmostEqual(r["gamma_L"].imag, .2)
        self.assertAlmostEqual(1-abs(r["gamma_L"])**2, .8)
        # Independently known Y0=[[9,-2],[-40,11]]/950 S:
        v1, v2, vs = r["V1_V"], r["V2_V"], r["V_s_V"]
        self.assertLess(abs((vs-v1)/50-(9*v1-2*v2)/950), 1e-16)
        self.assertLess(abs(-v2/(100+50j)-(-40*v1+11*v2)/950), 1e-16)
        matched = lab.closure(self.m, 0j, 0j, 1e-6, 50)
        self.assertAlmostEqual(matched["V2_over_V1"].real, 4/3)

    def test_gain_global_stationary_value(self):
        gs, gl = lab.conjugate_match(self.m)
        expected = 1.09-math.sqrt(.1881)
        self.assertAlmostEqual(gs.real, expected)
        self.assertAlmostEqual(gl.real, .4/(1-.5*expected))
        self.assertLess(abs(gs-lab.gin(self.m, gl).conjugate()), 1e-14)
        self.assertLess(abs(gl-lab.gout(self.m, gs).conjugate()), 1e-14)

    def test_physical_noise_polynomial(self):
        pars = lab.noise_parameters(self.m, self.n, 50)
        self.assertAlmostEqual(pars["F_min"], 1.2)
        self.assertLess(abs(pars["gamma_opt"]-(.2+.2j)), 1e-14)
        self.assertAlmostEqual(pars["R_n_ohm"], 5)
        for s in (0j, .2+.2j, -.3+.1j, .65-.15j):
            independent = 1+(13*abs(s)**2+2*((-10+10j)*s).real+41)/(185*(1-abs(s)**2))
            self.assertAlmostEqual(lab.noise_factor(self.m, self.n, s), independent)
        # Wrong correlation phase cannot retain the same optimum.
        bad = copy.deepcopy(self.cfg)
        bad["noise_C_over_kBT"][0][1][1] *= -1
        bad["noise_C_over_kBT"][1][0][1] *= -1
        self.assertGreater(abs(lab.noise_parameters(self.m, lab.matrix(bad["noise_C_over_kBT"]), 50)["gamma_opt"]-(.2+.2j)), .1)

    def test_l_sections_are_actual_impedances(self):
        for row in lab.run(self.cfg)["designs"]:
            for name, gammaname in (("source_L_section", "gamma_S"), ("load_L_section", "gamma_L")):
                net = row[name]
                actual = lab.l_impedance(net, 50, 2*math.pi*1e9)
                self.assertLess(abs(lab.gamma(actual, 50)-row[gammaname]), 1e-14)

    def test_dynamic_instability_despite_finite_frequency_denominator(self):
        c = lab.run(self.cfg)["conditional"]
        self.assertAlmostEqual(c["formal_frequency_solution"]["D"].real, -.377)
        self.assertFalse(c["formal_frequency_solution"]["is_usable_steady_state"])
        positive = [z for z in c["poles_rad_per_s"] if z.real > 0]
        self.assertEqual(len(positive), 2)
        self.assertAlmostEqual(positive[0].real/(2*math.pi*1e9), .13)
        with self.assertRaisesRegex(ValueError, "singular"):
            lab.closure(self.sc, 5/7, 5/7, 1e-6, 50)

    def test_exact_disk_and_loop_bounds(self):
        st = lab.stability(self.m)
        self.assertAlmostEqual(st["max_abs_gin"], 5/6)
        self.assertAlmostEqual(st["max_abs_gout"], .8)
        self.assertAlmostEqual(st["K"], 1.475)
        self.assertAlmostEqual(lab.run(self.cfg)["weighted_small_gain_bound"], .9)

    def test_covariance_and_interface_rejections(self):
        for mutate in (
            lambda c: c.update(reference_ohm=True),
            lambda c: c.update(probe_gammas=[[1, 0]]),
            lambda c: c["noise_C_over_kBT"][0].__setitem__(0, [-1, 0]),
            lambda c: c["noise_C_over_kBT"][0].__setitem__(1, [1, 0]),
            lambda c: c.update(noise_factor_contours=[1.0])):
            bad = copy.deepcopy(self.cfg)
            mutate(bad)
            with self.assertRaises(ValueError):
                lab.validate(bad)
        with self.assertRaises(ValueError):
            lab.validate([])


if __name__ == "__main__":
    unittest.main()
