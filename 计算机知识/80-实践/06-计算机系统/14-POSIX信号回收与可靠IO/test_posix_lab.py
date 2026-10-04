from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


class PosixLabTests(unittest.TestCase):
    def test_bounded_program_passes_its_injected_and_pipe_cases(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_lab.py")], text=True, capture_output=True, timeout=15
        )
        if completed.returncode == 77:
            self.skipTest(completed.stderr.strip())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "posix_lab self-test passed\n")

    def test_source_mirror_is_exact(self) -> None:
        mirror = (ROOT / "源码与测试镜像.md").read_text(encoding="utf-8")
        for filename in ("rio.h", "rio.c", "posix_lab.c", "run_lab.py", "test_posix_lab.py"):
            source = (ROOT / filename).read_text(encoding="utf-8").rstrip("\n")
            marker = f"<!-- code-sync: ./{filename} -->\n"
            start = mirror.index(marker) + len(marker)
            start = mirror.index("\n", start) + 1
            end = mirror.index("\n```", start)
            self.assertEqual(mirror[start:end], source, filename)


if __name__ == "__main__":
    unittest.main()
