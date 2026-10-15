from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np


MODULE_PATH = Path(__file__).with_name("entity_calibration_lab.py")
SPEC = importlib.util.spec_from_file_location("entity_calibration_lab", MODULE_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(lab)


class EntityCalibrationLabTests(unittest.TestCase):
    def test_subject_partition_is_complete_and_disjoint(self):
        flattened = [s for ids in lab.SUBJECT_SPLITS.values() for s in ids]
        self.assertEqual(sorted(flattened), list(range(1, 31)))
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(lab.SPLIT_SEED, 20260920)

    def test_standardizer_uses_only_given_rows(self):
        train = np.array([[1.0, 2.0], [3.0, 6.0]])
        future = np.array([[101.0, 202.0]])
        mean, scale = lab.fit_standardizer(train)
        np.testing.assert_allclose(mean, [2.0, 4.0])
        np.testing.assert_allclose(scale, [1.0, 2.0])
        np.testing.assert_allclose(lab.design(future, mean, scale), [[1.0, 99.0, 99.0]])

    def test_temperature_preserves_argmax(self):
        logits = np.array([[3.0, 2.0, 1.0, 0.0, -1.0, -2.0], [-3.0, 1.0, 0.0, 4.0, 2.0, -1.0]])
        for temperature in (0.25, 1.0, 4.0):
            np.testing.assert_array_equal(np.argmax(logits, axis=1), np.argmax(logits / temperature, axis=1))

    def test_temperature_fit_reduces_nll_on_overconfident_logits(self):
        logits = np.array([[8, 0, 0, 0, 0, 0], [8, 0, 0, 0, 0, 0], [0, 8, 0, 0, 0, 0]], dtype=float)
        y = np.array([0, 1, 1])
        temperature = lab.fit_temperature(logits, y)
        self.assertGreater(temperature, 1.0)
        self.assertLess(lab.multiclass_nll(logits, y, temperature), lab.multiclass_nll(logits, y, 1.0))
        self.assertGreaterEqual(np.log(temperature), lab.TEMPERATURE_LOG_BOUNDS[0])
        self.assertLessEqual(np.log(temperature), lab.TEMPERATURE_LOG_BOUNDS[1])

    def test_calibration_improvement_need_not_transfer_to_test(self):
        cal_logits = np.zeros((10, 6))
        cal_logits[:, 0] = 4.0
        cal_y = np.array([0] * 8 + [1] * 2)
        temperature = lab.fit_temperature(cal_logits, cal_y)
        self.assertGreater(temperature, 1.0)
        self.assertLess(
            lab.multiclass_nll(cal_logits, cal_y, temperature),
            lab.multiclass_nll(cal_logits, cal_y, 1.0),
        )
        test_logits = np.array([[4.0, 0, 0, 0, 0, 0]])
        test_y = np.array([0])
        self.assertGreater(
            lab.multiclass_nll(test_logits, test_y, temperature),
            lab.multiclass_nll(test_logits, test_y, 1.0),
        )

    def test_known_accuracy_nll_brier(self):
        logits = np.zeros((2, 6))
        y = np.array([0, 1])
        record = lab.metrics(logits, y, 1.0, bins=5)
        self.assertAlmostEqual(record["accuracy"], 0.5)
        self.assertAlmostEqual(record["nll"], np.log(6.0))
        self.assertAlmostEqual(record["brier"], 5.0 / 6.0)

    def test_nll_uses_stable_logsumexp_without_probability_clipping(self):
        logits = np.array([[1000.0, 0.0, -1000.0, -1000.0, -1000.0, -1000.0]])
        self.assertAlmostEqual(lab.multiclass_nll(logits, np.array([1])), 1000.0)

    def test_nll_is_invariant_to_large_common_logit_offsets(self):
        y = np.array([0])
        for offset in (0.0, 1e16, 1e20):
            self.assertAlmostEqual(lab.multiclass_nll(np.full((1, 6), offset), y), np.log(6.0))

    def test_ece_depends_on_bin_count(self):
        probabilities = np.array([
            [.51, .49, 0, 0, 0, 0], [.59, .41, 0, 0, 0, 0],
            [.61, .39, 0, 0, 0, 0], [.99, .01, 0, 0, 0, 0],
        ])
        y = np.array([0, 1, 0, 1])
        ece2 = lab.ece_from_reliability(lab.reliability(probabilities, y, 2))
        ece10 = lab.ece_from_reliability(lab.reliability(probabilities, y, 10))
        self.assertNotAlmostEqual(ece2, ece10)

    def test_confidence_one_is_assigned_to_last_bin(self):
        probabilities = np.array([[1.0, 0, 0, 0, 0, 0]])
        table = lab.reliability(probabilities, np.array([0]), 10)
        self.assertEqual(sum(row["count"] for row in table), 1)
        self.assertEqual(table[-1]["count"], 1)

    def test_row_split_has_no_row_overlap_and_preserves_classes(self):
        y = np.repeat(np.arange(6), 10)
        train, holdout = lab.row_split_indices(y, 123)
        self.assertFalse(set(train) & set(holdout))
        self.assertEqual(set(train) | set(holdout), set(range(60)))
        self.assertEqual(set(y[train]), set(range(6)))
        self.assertEqual(set(y[holdout]), set(range(6)))

    def test_bad_archive_hash_is_rejected_before_zip_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.zip"
            path.write_bytes(b"not the fixed UCI archive")
            with self.assertRaisesRegex(ValueError, "archive (byte-length|SHA-256) mismatch"):
                lab.load_uci_har_archive(path)

    def test_invalid_inputs_fail_loudly(self):
        with self.assertRaises(ValueError):
            lab.multiclass_nll(np.zeros((1, 6)), np.array([0]), 0)
        with self.assertRaises(ValueError):
            lab.softmax(np.zeros((2, 5)))
        with self.assertRaises(ValueError):
            lab.row_split_indices(np.arange(6), 1, 1.0)


if __name__ == "__main__":
    unittest.main()
