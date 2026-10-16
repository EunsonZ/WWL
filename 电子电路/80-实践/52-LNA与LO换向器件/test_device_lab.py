"""New assertions only; do not rerun old MOS or matching suites."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
import device_lab as lab

ROOT = Path(__file__).parent
_near = ROOT.parents[2]
VAULT = Path(os.environ.get("WWL_RF_VAULT", str(_near if (_near/"电子电路/80-实践/14-偏置与基本放大/amp_lab.py").is_file() else Path("/Users/ysz/Misc/Obsidian/Valults/WLM/WWL"))))


class DeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT/"fixed-inputs.json").read_text())
        cls.data = lab.run(cls.cfg, VAULT)

    def test_bias_and_supply_ledger(self):
        for row in self.data["lna_dc"]:
            q = row["Q"]
            self.assertAlmostEqual(q["id"], .001, places=13)
            self.assertGreater(q["vds"], q["vov"])
            spent = sum(row[k] for k in ("source_bias_absorbed_W", "Rs_heat_W", "Rd_heat_W", "MOS_heat_W"))
            self.assertAlmostEqual(spent, row["VDD_supplied_W"], places=15)

    def test_rebias_is_not_fixed_gate(self):
        qs = self.data["fixed_gate_migration"]
        self.assertGreater(qs[0]["id"], qs[1]["id"])
        self.assertGreater(qs[1]["id"], qs[2]["id"])
        self.assertGreater(abs(qs[2]["id"]-.001), .0001)

    def test_node_voltage_noise_and_wave_contract(self):
        for r in self.data["lna"]:
            rs = r["Rs_ohm"]
            vs, vd = r["source_node_over_e"], r["drain_over_e"]
            y = r["Y_S"]
            freq = r["frequency_Hz"]
            zl = self.cfg["lna"]["Rl_ohm"]+1/(2j*math.pi*freq*self.cfg["lna"]["Cout_F"])
            self.assertLess(abs((1-vs)/rs-(y[0][0]*vs+y[0][1]*vd)), 1e-14)
            self.assertLess(abs(-vd/zl-(y[1][0]*vs+y[1][1]*vd)), 1e-14)
            self.assertAlmostEqual(sum(r["output_PSD_V2_per_Hz"].values())/r["output_PSD_V2_per_Hz"]["source"], r["F"])
            self.assertAlmostEqual(r["G_T"], r["port"]["G_T"])
            n = r["noise_C_over_kBT"]
            self.assertLess(abs(n[0][1]-n[1][0].conjugate()), 1e-12)
            self.assertGreater((n[0][0]*n[1][1]-n[0][1]*n[1][0]).real, 0)

    def test_three_node_characteristic_matches_cubic(self):
        for r in self.data["lna"]:
            q = r["Q"]
            l = self.cfg["lna"]
            for s in (3+2j, -1e6+2e6j, 1e9j):
                a = 1/r["Rs_ohm"]+q["gm"]+q["go"]+s*(r["Cgs_total_F"]+l["Cds_external_F"])
                b = -q["go"]-s*l["Cds_external_F"]
                c = -q["gm"]-q["go"]-s*l["Cds_external_F"]
                d = 1/l["Rd_ohm"]+q["go"]+s*(l["Cgd_external_F"]+l["Cds_external_F"]+l["Cout_F"])
                off = -s*l["Cout_F"]
                e = 1/l["Rl_ohm"]+s*l["Cout_F"]
                det = a*(d*e-off*off)-b*c*e
                p = sum(value*s**i for i,value in enumerate(r["natural_polynomial_S3"]))
                self.assertLess(abs(det-p), 2e-10*max(abs(det), 1e-12))
            self.assertTrue(all(x > 0 for x in r["natural_polynomial_S3"]))
            self.assertGreater(r["routh_ratio"], 1)

    def test_commutating_limit_load_and_noise(self):
        r = self.data["mixer_ideal_limit"]
        self.assertAlmostEqual(r["on_R_ohm"], 50/7)
        self.assertAlmostEqual(r["effective_diff_load_ohm"], 1/(1/1000+1/2e6))
        self.assertAlmostEqual(r["IF_voltage_over_e"], r["alpha"]*2/math.pi)
        self.assertGreater(r["bias_resistor_output_PSD_V2_per_Hz"], 0)
        self.assertGreater(r["all_white_RF_SSB_F"], r["two_RF_bands_SSB_F"])
        fractions = [v["source_white_fraction_summed"] for v in r["specified_odd_RF_bands"]]
        self.assertEqual(fractions, sorted(fractions))
        self.assertLess(fractions[-1], 1)

    def test_invalid_finite_interfaces(self):
        mutations = [lambda c:c.update(temperature_K=True),
                     lambda c:c["lna"].update(Rs_cases_ohm=[50,50]),
                     lambda c:c["lna"].update(Cout_F=0),
                     lambda c:c["mixer"].update(odd_harmonics=[True,3]),
                     lambda c:c["mixer"].update(LO_high_V=.8),
                     lambda c:c["mixer"].update(LO_low_V=1.8),
                     lambda c:c["mixer"].update(IF_Hz=c["mixer"]["LO_Hz"])]
        for change in mutations:
            cfg = copy.deepcopy(self.cfg)
            change(cfg)
            with self.assertRaises(ValueError):
                lab.validate(cfg)

    def test_source_import_guard_success_and_failure(self):
        original = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = False
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp)/"probe.py"
                p.write_text("x = 3\n")
                self.assertEqual(lab.load_source(p, "probe_good").x, 3)
                self.assertFalse(sys.dont_write_bytecode)
                self.assertFalse((Path(tmp)/"__pycache__").exists())
                p.write_text("invalid !!!\n")
                with self.assertRaises(SyntaxError):
                    lab.load_source(p, "probe_bad")
                self.assertFalse(sys.dont_write_bytecode)
                self.assertFalse((Path(tmp)/"__pycache__").exists())
        finally:
            sys.dont_write_bytecode = original


if __name__ == "__main__":
    unittest.main()
