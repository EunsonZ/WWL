import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "code" / "minimum_wage_case.py"
SPEC = importlib.util.spec_from_file_location("minimum_wage_case", MODULE_PATH)
mw = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mw)


class MinimumWageCaseTests(unittest.TestCase):
    def test_fte_definition_and_missingness(self):
        row = {"EMPFT": 10.0, "EMPPT": 8.0, "NMGRS": 2.0}
        self.assertEqual(mw.fte(row, ""), 16.0)
        row["EMPPT"] = None
        self.assertIsNone(mw.fte(row, ""))

    def test_parser_rejects_wrong_field_count(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.dat"
            path.write_text("1 2 3\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "expected 46 fields"):
                mw.read_rows(path, verify_hash=False)

    def test_pinned_reference_values(self):
        reference = json.loads((Path(__file__).parents[1] / "data" / "reference_results.json").read_text())
        self.assertEqual(reference["restaurants"], 410)
        self.assertEqual(reference["states"]["NJ"]["restaurants"], 331)
        self.assertEqual(reference["states"]["PA"]["restaurants"], 79)
        self.assertAlmostEqual(reference["did"]["all_available_change_of_means"], 2.753605782980582)
        self.assertAlmostEqual(reference["did"]["balanced_change_mean"], 2.75)
        self.assertEqual(reference["sample_variants"]["balanced"]["n"], 384)
        self.assertAlmostEqual(reference["sample_variants"]["answered_status1"]["estimate"], 2.721919452347084)
        self.assertEqual(reference["sample_variants"]["table4_valid_employment_and_wages"]["n"], 357)
        self.assertAlmostEqual(reference["sample_variants"]["table4_valid_employment_and_wages"]["estimate"], 2.3258311888831704)
        regression = reference["sample_variants"]["table4_unadjusted_regression"]
        self.assertAlmostEqual(regression["coefficient"], 2.3258311888831704)
        self.assertAlmostEqual(regression["classical_homoskedastic_se"], 1.191596277699933)
        self.assertAlmostEqual(regression["hc1_heteroskedastic_robust_se"], 1.452284500848705)
        self.assertAlmostEqual(reference["sample_variants"]["temporary_closures_as_zero"]["estimate"], 2.5092119275825344)
        self.assertEqual(reference["status2"], {"0": 1, "1": 399, "2": 2, "3": 6, "4": 1, "5": 1})

    def test_optional_full_data_reproduction(self):
        raw = os.environ.get("NJMIN_DATA")
        if not raw:
            self.skipTest("set NJMIN_DATA to the verified public.dat for integration reproduction")
        observed = mw.summarize(mw.read_rows(Path(raw)))
        reference = json.loads((Path(__file__).parents[1] / "data" / "reference_results.json").read_text())
        self.assertEqual(observed, reference)

    def test_published_svgs_are_accessible_and_bound_to_data(self):
        assets = Path(__file__).parents[1] / "assets"
        for name, phrase in [("01-employment-did.svg", "FTE/店"), ("02-starting-wage.svg", "名义美元/小时")]:
            text = (assets / name).read_text(encoding="utf-8")
            self.assertIn("<title", text)
            self.assertIn("<desc", text)
            self.assertIn(phrase, text)
            self.assertIn("njmin.zip", text)


if __name__ == "__main__":
    unittest.main()
