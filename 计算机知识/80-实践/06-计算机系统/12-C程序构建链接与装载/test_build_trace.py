import json
import shutil
import subprocess
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from build_trace import (COMMAND_LINE_TOOLS, CommandResult, ROOT, child_environment,
                         find_clang, find_nm, is_platform_tool_gate, run, trace)


class BuildTraceTests(unittest.TestCase):
    def test_timeout_output_is_serializable_diagnostic_text(self) -> None:
        cases = (
            (b"partial\n", b"error\n", "partial\n", "error\n"),
            (None, None, "", ""),
            (b"partial \xe4\xb8", b"error \xff", "partial \ufffd", "error \ufffd"),
        )
        for stdout, stderr, expected_stdout, expected_stderr in cases:
            with self.subTest(stdout=stdout, stderr=stderr):
                error = subprocess.TimeoutExpired(["fixture"], 0.1, stdout, stderr)
                with patch("build_trace.subprocess.run", side_effect=error):
                    result = run("timeout-fixture", ["fixture"], ROOT)
                restored = json.loads(json.dumps(asdict(result)))
                self.assertTrue(restored["timed_out"])
                self.assertIsNone(restored["returncode"])
                self.assertEqual(restored["stdout"], expected_stdout)
                self.assertEqual(restored["stderr"], expected_stderr)
                self.assertIsInstance(result.stdout, str)
                self.assertIsInstance(result.stderr, str)
                self.assertFalse(is_platform_tool_gate(result))

    def test_real_child_timeout_retains_partial_utf8_output(self) -> None:
        script = (
            "import os, time; "
            "os.write(1, b'partial \\xe4\\xb8'); "
            "os.write(2, b'error\\n'); time.sleep(5)"
        )
        with patch("build_trace.TIMEOUT_SECONDS", 0.2):
            result = run("timeout-child", [sys.executable, "-c", script], ROOT)
        self.assertTrue(result.timed_out)
        self.assertIsNone(result.returncode)
        self.assertEqual(result.stdout, "partial \ufffd")
        self.assertEqual(result.stderr, "error\n")
        self.assertEqual(json.loads(json.dumps(asdict(result)))["stdout"], result.stdout)

    def test_success_and_nonzero_exit_keep_text_and_returncode(self) -> None:
        for code in (0, 3):
            with self.subTest(returncode=code):
                script = f"import sys; print('ok'); print('failure', file=sys.stderr); sys.exit({code})"
                result = run("exit-fixture", [sys.executable, "-c", script], ROOT)
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (code, "ok\n", "failure\n"))
                self.assertFalse(result.timed_out)

    def test_missing_compiler_is_an_explicit_skip(self) -> None:
        self.assertEqual(trace(clang="/definitely/not/a/compiler")["status"], "SKIP")

    def test_llvm_nm_probe_has_no_side_effect(self) -> None:
        found = find_nm()
        self.assertTrue(found is None or Path(found).is_file())

    def test_child_environment_only_selects_existing_command_line_tools(self) -> None:
        environment = child_environment()
        if sys.platform == "darwin" and COMMAND_LINE_TOOLS.is_dir():
            self.assertEqual(environment.get("DEVELOPER_DIR"), str(COMMAND_LINE_TOOLS))

    @unittest.skipUnless(find_clang(), "usable clang is unavailable")
    def test_build_contract_and_failure_stages(self) -> None:
        result = trace()
        self.assertIn(result["status"], {"PASS", "SKIP"})
        commands = {entry["stage"]: entry for entry in result["commands"]}
        self.assertTrue(all(commands[key]["returncode"] == 0 for key in (
            "compile:sum.c", "compile:main.c", "compile:duplicate_sum.c")))
        if result["status"] == "PASS":
            self.assertEqual(commands["run:success"]["stdout"], "sum=100\n")
            self.assertNotEqual(commands["link:missing-definition"]["returncode"], 0)
            self.assertNotEqual(commands["link:duplicate-definition"]["returncode"], 0)
            self.assertFalse(any(entry["timed_out"] for entry in commands.values()))
        else:
            self.assertIn("platform linker", result["reason"])

    @unittest.skipUnless(find_clang(), "usable clang is unavailable")
    def test_cli_returns_machine_readable_trace(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "build_trace.py")],
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(json.loads(completed.stdout)["status"], {"PASS", "SKIP"})

    def test_xcode_license_gate_is_not_mistaken_for_symbol_failure(self) -> None:
        gated = CommandResult("link:success", ["clang"], 69, "",
                              "You have not agreed to the Xcode license agreements.", False)
        ordinary_failure = CommandResult("link:success", ["clang"], 1, "", "undefined symbol", False)
        self.assertTrue(is_platform_tool_gate(gated))
        self.assertFalse(is_platform_tool_gate(ordinary_failure))


if __name__ == "__main__":
    unittest.main()
