"""Run only the candidate's own C program in a temporary directory."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "loop_optimization.c"


class LoopOptimizationTests(unittest.TestCase):
    def compiler_and_environment(self) -> tuple[str, dict[str, str]]:
        environment = os.environ.copy()
        homebrew_clang = Path("/opt/homebrew/opt/llvm/bin/clang")
        compiler = environment.get("CC") or (str(homebrew_clang) if homebrew_clang.is_file() else "cc")
        command_line_tools = Path("/Library/Developer/CommandLineTools")
        if sys.platform == "darwin" and command_line_tools.is_dir():
            # Applies only to this child compiler process; it neither accepts a
            # license nor changes the selected system developer directory.
            environment.setdefault("DEVELOPER_DIR", str(command_line_tools))
        return compiler, environment

    def compile_program(self, temporary: Path) -> Path:
        compiler, environment = self.compiler_and_environment()
        if shutil.which(compiler) is None:
            self.skipTest(f"C compiler {compiler!r} is unavailable")
        executable = temporary / "loop_optimization"
        completed = subprocess.run(
            [compiler, "-std=c17", "-O2", "-Wall", "-Wextra", "-Wpedantic", str(SOURCE), "-o", str(executable)],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            env=environment,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return executable

    def test_self_test_checks_modular_contract_and_shapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wwl-loop-opt-") as directory:
            executable = self.compile_program(Path(directory))
            completed = subprocess.run(
                [str(executable), "--self-test"], text=True, capture_output=True, timeout=10, check=False
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("self-test passed", completed.stdout)
        self.assertIn("NULL, 2U, 0U", SOURCE.read_text(encoding="utf-8"))

    def test_two_samples_report_every_implementation_without_speed_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wwl-loop-opt-") as directory:
            executable = self.compile_program(Path(directory))
            completed = subprocess.run(
                [str(executable), "--benchmark", "2"], text=True, capture_output=True, timeout=30, check=False
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        for required in ("contract=uint32_t-sum-mod-2^32", "baseline_ns=", "row_base_ns=", "four_accumulators_ns=", "column_visit_ns=", "guard="):
            self.assertIn(required, completed.stdout)

    def test_source_keeps_the_contract_and_no_speed_threshold(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("uint32_t-sum-mod-2^32", text)
        self.assertIn("sum_four_accumulators", text)
        self.assertIn("sum_column_visit", text)
        self.assertNotIn("must be faster", text.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
