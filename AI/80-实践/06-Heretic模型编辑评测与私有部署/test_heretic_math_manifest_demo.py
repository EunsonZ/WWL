"""Tests for the Heretic lab's standard-library-only safety demo."""

from __future__ import annotations

import copy
import contextlib
import io
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import heretic_math_manifest_demo as demo


class ProjectionTests(unittest.TestCase):
    def test_removed_vector_is_orthogonal_to_direction(self) -> None:
        direction = (2.0, -1.0, 2.0)
        output = demo.remove_direction((3.0, 4.0, 5.0), direction)
        self.assertAlmostEqual(demo.dot(output, demo.unit_vector(direction)), 0.0)

    def test_direction_scale_does_not_change_projection(self) -> None:
        vector = (1.0, 3.0)
        self.assertEqual(
            demo.remove_direction(vector, (1.0, 2.0)),
            demo.remove_direction(vector, (5.0, 10.0)),
        )

    def test_zero_direction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            demo.remove_direction((1.0, 2.0), (0.0, 0.0))


class KLDivergenceTests(unittest.TestCase):
    def test_identical_distributions_have_zero_kl(self) -> None:
        self.assertAlmostEqual(demo.kl_divergence((0.2, 0.8), (0.2, 0.8)), 0.0)

    def test_known_kl_value(self) -> None:
        self.assertAlmostEqual(
            demo.kl_divergence((1.0, 0.0), (0.5, 0.5)), math.log(2.0)
        )

    def test_kl_is_directional(self) -> None:
        forward = demo.kl_divergence((0.75, 0.25), (0.5, 0.5))
        reverse = demo.kl_divergence((0.5, 0.5), (0.75, 0.25))
        self.assertNotAlmostEqual(forward, reverse)

    def test_missing_q_support_returns_infinity(self) -> None:
        self.assertTrue(math.isinf(demo.kl_divergence((1.0, 0.0), (0.0, 1.0))))


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = demo._fixture_original()
        self.experiment = demo._fixture_experiment()
        self.edited = demo._fixture_edited()
        self.evaluation = demo._fixture_evaluation()

    def test_valid_synthetic_manifests_pass(self) -> None:
        demo.validate_original_manifest(self.original)
        demo.validate_experiment_manifest(self.experiment, self.original)
        demo.validate_edited_manifest(self.edited)
        demo.validate_evaluation_plan(self.evaluation)
        result = demo.validate_manifest_bundle(
            self.original,
            self.experiment,
            self.edited,
            self.evaluation,
            original_path=demo.ORIGINAL_MANIFEST_PATH,
            original_sha256=demo.ORIGINAL_MANIFEST_SHA256,
            experiment_path=demo.EXPERIMENT_MANIFEST_PATH,
            experiment_sha256=demo.EXPERIMENT_MANIFEST_SHA256,
            edited_path=demo.EDITED_MANIFEST_PATH,
            edited_sha256=demo.EDITED_MANIFEST_SHA256,
            evaluation_path=demo.EVALUATION_PLAN_PATH,
            evaluation_sha256=demo.EVALUATION_PLAN_SHA256,
        )
        self.assertEqual(result["identity_and_hash_chain"], "closed")

    def test_cli_rejects_symlink_before_json_loader_is_called(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_text("{}\n", encoding="utf-8")
            link = root / "manifest.json"
            link.symlink_to(target)
            with mock.patch.object(demo, "_load_json") as loader:
                with contextlib.redirect_stderr(io.StringIO()):
                    exit_code = demo.main(
                        ["validate", str(link), str(link), str(link), str(link)]
                    )
            self.assertEqual(exit_code, 2)
            loader.assert_not_called()

    def test_moving_model_revision_is_rejected(self) -> None:
        self.original["model"]["revision"] = "main"
        with self.assertRaises(demo.ManifestError):
            demo.validate_original_manifest(self.original)

    def test_moving_tokenizer_revision_is_rejected(self) -> None:
        self.original["model"]["tokenizer_revision"] = "main"
        with self.assertRaises(demo.ManifestError):
            demo.validate_original_manifest(self.original)

    def test_placeholder_hash_is_rejected(self) -> None:
        self.original["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(demo.ManifestError):
            demo.validate_original_manifest(self.original)

    def test_working_copy_inside_original_is_rejected(self) -> None:
        self.experiment["paths"]["working_copy_directory"] = (
            "/lab/models/original/0123456789abcdef/work"
        )
        with self.assertRaises(demo.ManifestError):
            demo.validate_experiment_manifest(self.experiment, self.original)

    def test_edited_output_inside_working_copy_is_rejected(self) -> None:
        self.experiment["paths"]["edited_output_directory"] = (
            "/lab/models/work/synthetic-heretic-lab-001/edited"
        )
        with self.assertRaises(demo.ManifestError):
            demo.validate_experiment_manifest(self.experiment, self.original)

    def test_service_or_lan_enablement_is_rejected(self) -> None:
        for key in ("service_enabled", "allow_lan", "allow_public", "upload_enabled"):
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.experiment)
                candidate["network"][key] = True
                with self.assertRaises(demo.ManifestError):
                    demo.validate_experiment_manifest(candidate, self.original)

    def test_non_loopback_bind_is_rejected(self) -> None:
        self.experiment["network"]["bind_host"] = "0.0.0.0"
        with self.assertRaises(demo.ManifestError):
            demo.validate_experiment_manifest(self.experiment, self.original)

    def test_unreviewed_repository_is_rejected(self) -> None:
        self.experiment["tool"]["repository"] = "https://example.invalid/heretic-fork"
        with self.assertRaises(demo.ManifestError):
            demo.validate_experiment_manifest(self.experiment, self.original)

    def test_secret_values_are_rejected(self) -> None:
        self.experiment["access_token"] = "must-not-be-recorded"
        with self.assertRaises(demo.ManifestError):
            demo.validate_experiment_manifest(self.experiment, self.original)

    def test_sensitive_fields_fail_closed_even_when_empty(self) -> None:
        self.edited["authorization"] = ""
        with self.assertRaises(demo.ManifestError):
            demo.validate_edited_manifest(self.edited)

    def test_secret_looking_value_is_rejected_without_sensitive_key(self) -> None:
        self.edited["notes"] = "Bear" "er abcdefghijklmnopqrstuvwxyz"
        with self.assertRaises(demo.ManifestError):
            demo.validate_edited_manifest(self.edited)

    def test_cross_manifest_hash_mismatch_is_rejected(self) -> None:
        self.edited["experiment"]["manifest_sha256"] = "def0123456789abc" * 4
        with self.assertRaises(demo.ManifestError):
            demo.validate_manifest_bundle(
                self.original,
                self.experiment,
                self.edited,
                self.evaluation,
                original_path=demo.ORIGINAL_MANIFEST_PATH,
                original_sha256=demo.ORIGINAL_MANIFEST_SHA256,
                experiment_path=demo.EXPERIMENT_MANIFEST_PATH,
                experiment_sha256=demo.EXPERIMENT_MANIFEST_SHA256,
                edited_path=demo.EDITED_MANIFEST_PATH,
                edited_sha256=demo.EDITED_MANIFEST_SHA256,
                evaluation_path=demo.EVALUATION_PLAN_PATH,
                evaluation_sha256=demo.EVALUATION_PLAN_SHA256,
            )

    def test_cross_manifest_experiment_id_mismatch_is_rejected(self) -> None:
        self.evaluation["experiment_id"] = "different-experiment"
        with self.assertRaises(demo.ManifestError):
            demo.validate_manifest_bundle(
                self.original,
                self.experiment,
                self.edited,
                self.evaluation,
                original_path=demo.ORIGINAL_MANIFEST_PATH,
                original_sha256=demo.ORIGINAL_MANIFEST_SHA256,
                experiment_path=demo.EXPERIMENT_MANIFEST_PATH,
                experiment_sha256=demo.EXPERIMENT_MANIFEST_SHA256,
                edited_path=demo.EDITED_MANIFEST_PATH,
                edited_sha256=demo.EDITED_MANIFEST_SHA256,
                evaluation_path=demo.EVALUATION_PLAN_PATH,
                evaluation_sha256=demo.EVALUATION_PLAN_SHA256,
            )

    def test_final_test_leak_is_rejected(self) -> None:
        for split in self.evaluation["splits"]:
            if split["name"] == "final_test":
                split["used_for_search"] = True
        with self.assertRaises(demo.ManifestError):
            demo.validate_evaluation_plan(self.evaluation)

    def test_direction_data_cannot_score_search_trials(self) -> None:
        for split in self.evaluation["splits"]:
            if split["name"] == "direction_train":
                split["used_for_search"] = True
        with self.assertRaises(demo.ManifestError):
            demo.validate_evaluation_plan(self.evaluation)

    def test_four_dimensions_are_required(self) -> None:
        del self.evaluation["dimensions"]["general_capability"]
        with self.assertRaises(demo.ManifestError):
            demo.validate_evaluation_plan(self.evaluation)

    def test_demo_explicitly_disclaims_model_evidence(self) -> None:
        result = demo.demo_result()
        self.assertTrue(result["does_not_describe_model_behavior"])
        self.assertEqual(result["scope"], "synthetic_math_and_manifest_only")


if __name__ == "__main__":
    unittest.main()
