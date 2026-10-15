"""Standard-library negative tests for the offline llama.cpp manifest validator."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import validate_manifest as validator


TEMPLATE = Path(__file__).with_name("experiment-manifest.template.json")
COMMIT = "0123456789abcdef0123456789abcdef01234567"


class ManifestValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def accepted_cpu_manifest(self) -> dict[str, object]:
        manifest = copy.deepcopy(self.template)
        manifest["status"] = "partial"
        manifest["source"].update(
            {"base_commit": COMMIT, "verified_head": COMMIT, "dirty": False}
        )
        cpu = manifest["builds"]["cpu"]
        cpu.update(
            {
                "status": "passed",
                "configure_command_redacted": "cmake <redacted>",
                "configure_log": "cpu-configure.log",
                "configure_exit_code": 0,
                "build_command_redacted": "cmake --build <redacted>",
                "build_log": "cpu-build.log",
                "build_exit_code": 0,
                "test_command_redacted": "ctest <redacted>",
                "test_log": "cpu-test.log",
                "test_exit_code": 0,
                "backend_evidence": {
                    "intended_backend": "cpu",
                    "explicitly_disabled": ["GGML_CUDA", "GGML_METAL"],
                    "fixed_commit_option_inventory_record": "cmake-options.json",
                    "enabled_accelerator_backends": [],
                    "cpu_libraries": ["BLAS_ACCELERATE"],
                },
                "runtime_evidence": {
                    "observed_backend": "cpu",
                    "device_inventory_record": "devices.txt",
                    "runtime_version_record": "runtime-version.txt",
                },
                "target_evidence": {
                    "configured_targets_record": "configured-targets.txt",
                    "built_targets_record": "built-targets.txt",
                    "tested_targets_record": "tested-targets.txt",
                },
            }
        )
        return manifest

    def test_planned_template_is_valid_but_not_cpu_accepted(self) -> None:
        self.assertEqual(validator.validate(self.template, False, False), [])
        self.assertTrue(validator.validate(self.template, True, False))

    def test_sensitive_key_fragments_and_explicit_fields_are_rejected(self) -> None:
        for key in ("backup_access_token_value", "private_url_copy", "model_url"):
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.template)
                candidate["notes"] = [{key: ""}]
                self.assertTrue(validator.validate(candidate, False, False))

    def test_credential_like_values_are_rejected_under_innocent_keys(self) -> None:
        values = (
            "Bear" "er abcdefghijklmnopqrstuvwxyz",
            "hf_" + "a" * 20,
            "sk-" + "b" * 20,
            "https://example.invalid/file?X-Amz-" + "Signature=abcdef",
        )
        for value in values:
            with self.subTest(value=value[:8]):
                candidate = copy.deepcopy(self.template)
                candidate["notes"] = [value]
                self.assertTrue(validator.validate(candidate, False, False))

    def test_cpu_acceptance_requires_structured_backend_runtime_and_targets(self) -> None:
        candidate = self.accepted_cpu_manifest()
        self.assertEqual(validator.validate(candidate, True, False), [])
        for field in ("backend_evidence", "runtime_evidence", "target_evidence"):
            with self.subTest(field=field):
                broken = copy.deepcopy(candidate)
                broken["builds"]["cpu"][field] = None
                self.assertTrue(validator.validate(broken, True, False))

    def test_cpu_acceptance_rejects_metal_default_or_observed_accelerator(self) -> None:
        candidate = self.accepted_cpu_manifest()
        candidate["builds"]["cpu"]["cmake_options"].remove("-DGGML_METAL=OFF")
        self.assertTrue(validator.validate(candidate, True, False))
        candidate = self.accepted_cpu_manifest()
        candidate["builds"]["cpu"]["backend_evidence"]["enabled_accelerator_backends"] = ["METAL"]
        self.assertTrue(validator.validate(candidate, True, False))


if __name__ == "__main__":
    unittest.main()
