"""Negative-path tests for the conversion preflight; no conversion is run."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("preflight.template.sh")
COMMIT = "0123456789abcdef0123456789abcdef01234567"


class PreflightTests(unittest.TestCase):
    def make_fixture(self, base: Path, *, overlap: bool = False, symlink_out: bool = False) -> dict[str, str]:
        run = base / "run"
        source = run / "source" if overlap else base / "source"
        checkout = base / "llama.cpp"
        bin_dir = base / "bin"
        run.mkdir()
        if symlink_out:
            real_out = base / "real-out"
            real_out.mkdir()
            (run / "out").symlink_to(real_out, target_is_directory=True)
        else:
            (run / "out").mkdir()
        source.mkdir()
        checkout.mkdir()
        bin_dir.mkdir()
        (source / "config.json").write_text("{}\n", encoding="utf-8")
        (source / "weights.safetensors").write_bytes(b"safe-fixture")
        (source / "tokenizer.json").write_text("{}\n", encoding="utf-8")
        fake_git = bin_dir / "git"
        fake_git.write_text(
            "#!/bin/sh\ncase \"$*\" in\n*'rev-parse HEAD'*) echo '" + COMMIT + "' ;;\n"
            "*'status --porcelain'*) exit 0 ;;\n*) exit 2 ;;\nesac\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o755)
        return {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "RUN_ROOT": str(run),
            "SOURCE_DIR": str(source),
            "LLAMA_CPP_DIR": str(checkout),
            "LLAMA_CPP_COMMIT": COMMIT,
            "REQUIRED_KIB": "1",
            "HIGH_GGUF": str(run / "out" / "model-f16.gguf"),
            "QUANT_GGUF": str(run / "out" / "model-q4.gguf"),
        }

    def run_preflight(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
        )

    def test_valid_isolated_directories_record_provenance_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary))
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(env["RUN_ROOT"]) / "source-sha256.txt").is_file())
            self.assertTrue((Path(env["RUN_ROOT"]) / "llama-cpp-commit.txt").is_file())
            self.assertFalse(Path(env["HIGH_GGUF"]).exists())

    def test_symlinked_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary), symlink_out=True)
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not be a symlink", result.stderr)

    def test_run_root_and_source_overlap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env = self.make_fixture(Path(temporary), overlap=True)
            result = self.run_preflight(env)
            self.assertEqual(result.returncode, 2)
            self.assertIn("must not overlap", result.stderr)


if __name__ == "__main__":
    unittest.main()
