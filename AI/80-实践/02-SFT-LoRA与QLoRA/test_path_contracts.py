"""Filesystem containment regression for the LoRA teaching checkpoint."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import lora_toy as lora


class LoraPathContracts(unittest.TestCase):
    def test_symlinks_and_artifact_root_containment(self) -> None:
        original_root = lora.ARTIFACT_ROOT
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                lora.ARTIFACT_ROOT = root / "allowed"
                lora.ARTIFACT_ROOT.mkdir()
                allowed_file = lora.ARTIFACT_ROOT / "ok.json"
                allowed_file.write_text("{}", encoding="utf-8")
                outside_file = root / "outside.json"
                outside_file.write_text("{}", encoding="utf-8")

                self.assertEqual(
                    lora.require_artifact_path(allowed_file, must_exist=True),
                    allowed_file,
                )
                new_file = allowed_file.parent / "new.json"
                self.assertEqual(lora.require_artifact_path(new_file), new_file)

                for name, target in (
                    ("inside", allowed_file),
                    ("outside", outside_file),
                    ("parent", allowed_file.parent),
                ):
                    link = lora.ARTIFACT_ROOT / name
                    link.symlink_to(target)
                    candidate = link / "ok.json" if name == "parent" else link
                    with self.subTest(name=name):
                        with self.assertRaises(ValueError):
                            lora.require_artifact_path(candidate, must_exist=True)

                for invalid in (
                    outside_file,
                    allowed_file.parent,
                    allowed_file.parent / "missing",
                ):
                    with self.assertRaises(ValueError):
                        lora.require_artifact_path(invalid, must_exist=True)
        finally:
            lora.ARTIFACT_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
