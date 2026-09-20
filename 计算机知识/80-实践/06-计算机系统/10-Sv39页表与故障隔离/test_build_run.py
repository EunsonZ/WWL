#!/usr/bin/env python3
"""Contract tests for the Sv39 build/run verifier."""

from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
import textwrap
import unittest

import build_run


SYMBOLS = {
    "user_store_fault_insn": 0x80010058,
    "user_load_fault_insn": 0x800100A0,
}


def valid_output() -> str:
    lines = []
    for pattern in build_run.expected_patterns(SYMBOLS):
        line = pattern
        line = line.replace(r"[0-9a-f]{4}", "00f0")
        line = line.replace(r"\.", ".")
        lines.append(line)
    return "\n".join(lines) + "\n"


class VerifierTests(unittest.TestCase):
    def test_complete_trace_passes(self) -> None:
        build_run.verify_output(0, valid_output(), SYMBOLS)

    def test_boot_only_is_rejected(self) -> None:
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(
                0, "MODE M: boot hart=0 delegate=0x000000000000b100\n", SYMBOLS
            )

    def test_missing_fault_is_rejected(self) -> None:
        output = valid_output().replace(
            (
                "FAULT kind=load scause=13 sepc=0x00000000400000a0 "
                "stval=0x0000000080013000 action=redirect-explicit-label\n"
            ),
            "",
        )
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, output, SYMBOLS)

    def test_out_of_order_is_rejected(self) -> None:
        lines = valid_output().splitlines()
        lines[10], lines[13] = lines[13], lines[10]
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, "\n".join(lines) + "\n", SYMBOLS)

    def test_nonzero_exit_is_rejected(self) -> None:
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(7, valid_output(), SYMBOLS)

    def test_fail_marker_is_rejected(self) -> None:
        output = valid_output().replace("RESULT PASS", "RESULT FAIL code=0x1")
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, output, SYMBOLS)

    def test_source_output_directory_is_rejected_by_main_logic(self) -> None:
        source = Path(build_run.__file__).resolve().parent
        with self.assertRaises(build_run.LabError):
            build_run.checked_output_path(source, source / "build")

    def test_code_sync_blocks_match_sources(self) -> None:
        source = Path(build_run.__file__).resolve().parent
        mirror = (source / "源码与测试镜像.md").read_text(encoding="utf-8")
        names = (
            "trapframe.h",
            "trapframe_offsets.h",
            "linker.ld",
            "boot.S",
            "trap.S",
            "user.S",
            "kernel.c",
            "build_run.py",
            "test_build_run.py",
        )
        for name in names:
            pattern = (
                rf"<!-- code-sync: \./{re.escape(name)} -->\n"
                rf"```[^\n]*\n(.*?)```\n"
            )
            match = re.search(pattern, mirror, flags=re.DOTALL)
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), (source / name).read_text(encoding="utf-8"))

    def test_timeout_kills_process_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sv39-timeout-test-") as directory:
            root = Path(directory)
            fake = root / "fake-qemu"
            fake.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    trap '' TERM
                    sleep 30 &
                    wait
                    """
                ),
                encoding="utf-8",
            )
            fake.chmod(0o755)
            dummy_elf = root / "dummy.elf"
            dummy_elf.write_bytes(b"dummy")
            with self.assertRaises(build_run.LabError) as caught:
                build_run.run_qemu(fake, dummy_elf, 0.1)
            self.assertIn("process group killed", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
