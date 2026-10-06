from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import lora_toy  # noqa: E402
import preflight  # noqa: E402


class LoraToyTests(unittest.TestCase):
    def test_low_rank_training_reduces_loss_and_resume_preserves_state(self) -> None:
        state = lora_toy.initial_state(rank=2, alpha=2.0)
        initial = lora_toy.loss(state["a"], state["b"], state["alpha"])
        self.assertEqual(lora_toy.predict([1.0, 0.0, 0.0], state["a"], state["b"], state["alpha"]), [1.0, 0.5])
        lora_toy.train(state, epochs=300, learning_rate=0.5)
        self.assertLess(lora_toy.loss(state["a"], state["b"], state["alpha"]), initial * 0.05)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "toy.json"
            lora_toy.save_checkpoint(checkpoint, state)
            restored = lora_toy.load_checkpoint(checkpoint)
            self.assertEqual(restored, state)
            lora_toy.train(restored, epochs=1, learning_rate=0.5)
            self.assertEqual(restored["step"], state["step"] + 1)
            with self.assertRaises(FileExistsError):
                lora_toy.save_checkpoint(checkpoint, state)

    def test_cli_checkpoint_must_stay_in_practice_artifacts(self) -> None:
        with self.assertRaises(ValueError):
            lora_toy.require_artifact_path(Path("/private/tmp/outside-practice.json"))


class PreflightTests(unittest.TestCase):
    def make_contract_fixture(self, directory: str) -> tuple[dict[str, object], Path]:
        root = Path(directory)
        (root / "LICENSE.md").write_text("CC0-1.0 fixture record\n", encoding="utf-8")
        records = [
            {"id": "a", "messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "a"}], "license": "CC0-1.0", "split": "train", "split_group": "g-a"},
            {"id": "b", "messages": [{"role": "user", "content": "b"}, {"role": "assistant", "content": "b"}], "license": "CC0-1.0", "split": "dev", "split_group": "g-b"},
            {"id": "c", "messages": [{"role": "user", "content": "c"}, {"role": "assistant", "content": "c"}], "license": "CC0-1.0", "split": "test", "split_group": "g-c"},
        ]
        data_path = root / "fixture.jsonl"
        data_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
        contract: dict[str, object] = {
            "schema_version": "sft-chat-v1",
            "train_path": "fixture.jsonl",
            "license_record": "LICENSE.md",
            "required_record_fields": ["id", "messages", "license", "split", "split_group"],
            "allowed_roles": ["user", "assistant"],
            "allowed_splits": ["train", "dev", "test"],
            "approved_licenses": ["CC0-1.0"],
            "chat_template": {
                "loss_scope": "assistant-only",
                "truncation": "reject samples whose supervised assistant span would be truncated",
            },
        }
        return contract, data_path

    def test_template_is_static_valid_only_with_explicit_placeholder_mode(self) -> None:
        command = [sys.executable, str(ROOT / "preflight.py"), "--config", "configs/8gb-qlora.json"]
        blocked = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(blocked.returncode, 2)
        allowed = subprocess.run(command + ["--allow-template-placeholders"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("STATIC VALID", allowed.stdout)
        config = json.loads((ROOT / "configs/8gb-qlora.json").read_text(encoding="utf-8"))
        self.assertTrue(config["base_model"]["repository"].startswith("REPLACE_"))

    def test_data_license_must_be_explicitly_approved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            contract, data_path = self.make_contract_fixture(directory)
            records = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines()]
            records[0]["license"] = ""
            data_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
            errors = preflight.validate_data(contract, Path(directory))
            self.assertTrue(any("license must be one of" in error for error in errors), errors)

    def test_split_group_cannot_cross_splits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            contract, data_path = self.make_contract_fixture(directory)
            records = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines()]
            records[1]["split_group"] = records[0]["split_group"]
            data_path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
            errors = preflight.validate_data(contract, Path(directory))
            self.assertTrue(any("crosses train and dev" in error for error in errors), errors)

    def test_base_license_review_cannot_be_a_placeholder_for_real_validation(self) -> None:
        run = json.loads((ROOT / "configs/8gb-qlora.json").read_text(encoding="utf-8"))
        run["base_model"]["repository"] = "reviewed/model"
        run["base_model"]["revision"] = "0123456789abcdef0123456789abcdef01234567"
        errors = preflight.validate_run(run, allow_placeholders=False)
        self.assertTrue(any("license must be reviewed" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
