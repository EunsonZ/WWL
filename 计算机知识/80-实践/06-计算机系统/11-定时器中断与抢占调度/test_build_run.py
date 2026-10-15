#!/usr/bin/env python3
"""Contract and cleanup tests for the timer-preemption runner."""

from __future__ import annotations

from pathlib import Path
import re
import tempfile
import textwrap
import unittest

import build_run


SYMBOLS = {
    "user0_hot_loop": 0x80010070,
    "user0_hot_loop_end": 0x80010088,
    "user0_exit": 0x8001008C,
    "user1_hot_loop": 0x80012070,
    "user1_hot_loop_end": 0x80012088,
    "user1_exit": 0x8001208C,
}


def sample_output() -> str:
    lines = [
        "MODE M: Sstc=1 STCE=1 mcounteren.TM=1 mideleg.STIP=1 MTIE=0",
        "MODE S: build Sv39 and two user contexts",
        "SATP mode=8 root_pa=0x0000000080015000 "
        "user0_code=0x0000000040000000 user1_code=0x0000000040002000",
        "TIMER source=Sstc timebase_hz=10000000 quantum_ticks=2000000 "
        "now=0x0000000000100000 first_deadline=0x00000000002e8480 "
        "STIE=1 SPIE=1 SIE-before-sret=0",
        "TASK id=0 tf=0x000000008001a000 "
        "stack=[0x0000000040003000,0x0000000040004000) "
        "entry=0x0000000040000000",
        "TASK id=1 tf=0x000000008001b000 "
        "stack=[0x0000000040004000,0x0000000040005000) "
        "entry=0x0000000040002000",
        "MODE U: task=0 hot-loop-no-yield",
    ]
    saved = [0x40000000, 0x40002000]
    work = [0, 0]
    for tick in range(1, 7):
        source = (tick - 1) % 2
        target = 1 - source
        work[source] += 0x1000
        now = 0x100000 + tick * build_run.QUANTUM_TICKS
        pc = (0x40000070 if source == 0 else 0x40002070) + (tick % 4) * 4
        lines.append(
            f"TICK n={tick} cause=0x8000000000000005 now=0x{now:016x} "
            f"deadline=0x{now + build_run.QUANTUM_TICKS:016x} "
            f"from={source} to={target} sepc=0x{pc:016x} "
            f"sp=0x{(0x40004000 if source == 0 else 0x40005000):016x} "
            f"work=0x{work[source]:016x} stack=0x{work[source]:016x} "
            "SPP=0 SPIE=1 depth=1"
        )
        saved[source] = (
            0x4000008C if tick == 5 else
            0x4000208C if tick == 6 else pc
        )
        lines.append(
            f"SWITCH from_tf=0x{(0x8001A000 if source == 0 else 0x8001B000):016x} "
            f"to_tf=0x{(0x8001A000 if target == 0 else 0x8001B000):016x} "
            f"next_pc=0x{saved[target]:016x}"
        )
    lines.extend(
        [
            "EXIT task=0 work=0x0000000000003000 stack=0x0000000000003000 "
            "preemptions=3 status=PASS",
            "EXIT task=1 work=0x0000000000003000 stack=0x0000000000003000 "
            "preemptions=3 status=PASS",
            "SUMMARY ticks=6 task0_preemptions=3 task1_preemptions=3 "
            "switches=6 status=PASS",
            "RESULT PASS",
        ]
    )
    return "\n".join(lines) + "\n"


class RunnerTests(unittest.TestCase):
    def test_complete_trace_passes(self) -> None:
        build_run.verify_output(0, sample_output(), SYMBOLS)

    def test_first_and_later_progress_boundaries(self) -> None:
        # Mutate each counter independently, keeping the other valid.
        for field in ('work', 'stack'):
            for value, accepted in [(999, False), (1000, True), (1001, True)]:
                lines = sample_output().splitlines()
                lines[7] = re.sub(rf'{field}=0x[0-9a-f]{{16}}',
                                  f'{field}=0x{value:016x}', lines[7])
                output = '\n'.join(lines) + '\n'
                with self.subTest(field=field, first=value):
                    if accepted:
                        build_run.verify_output(0, output, SYMBOLS)
                    else:
                        with self.assertRaises(build_run.LabError):
                            build_run.verify_output(0, output, SYMBOLS)
            lines = sample_output().splitlines()
            for line_index, value in [(7, 1000), (11, 1001)]:
                lines[line_index] = re.sub(rf'{field}=0x[0-9a-f]{{16}}',
                                           f'{field}=0x{value:016x}', lines[line_index])
            with self.subTest(field=field, later='1000 to 1001'):
                build_run.verify_output(0, '\n'.join(lines) + '\n', SYMBOLS)
            # Task0's second preemption repeats its first value: no progress.
            lines = sample_output().splitlines()
            lines[11] = re.sub(rf'{field}=0x[0-9a-f]{{16}}',
                               f'{field}=0x{4096:016x}', lines[11])
            with self.subTest(field=field, later='equal'), self.assertRaises(build_run.LabError):
                build_run.verify_output(0, '\n'.join(lines) + '\n', SYMBOLS)

    def test_corrupt_pc_canary_are_rejected(self) -> None:
        for old, new in [('sepc=0x0000000040000074', 'sepc=0x000000004000006c'),
                         ('SPP=0 SPIE=1 depth=1', 'SPP=1 SPIE=1 depth=1')]:
            with self.subTest(old=old), self.assertRaises(build_run.LabError):
                build_run.verify_output(0, sample_output().replace(old, new, 1), SYMBOLS)

    def test_boot_only_is_rejected(self) -> None:
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, sample_output().splitlines()[0] + "\n", SYMBOLS)

    def test_missing_tick_is_rejected(self) -> None:
        lines = sample_output().splitlines()
        del lines[9:11]
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, "\n".join(lines) + "\n", SYMBOLS)

    def test_out_of_order_tick_is_rejected(self) -> None:
        lines = sample_output().splitlines()
        lines[7:9], lines[9:11] = lines[9:11], lines[7:9]
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, "\n".join(lines) + "\n", SYMBOLS)

    def test_repeated_task_is_rejected(self) -> None:
        output = sample_output().replace(
            "from=1 to=0 sepc=0x0000000040002078",
            "from=0 to=1 sepc=0x0000000040000078",
            1,
        )
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(0, output, SYMBOLS)

    def test_nonzero_and_fail_are_rejected(self) -> None:
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(9, sample_output(), SYMBOLS)
        with self.assertRaises(build_run.LabError):
            build_run.verify_output(
                0, sample_output().replace("RESULT PASS", "RESULT FAIL code=0x1"),
                SYMBOLS,
            )

    def test_source_nested_output_is_rejected(self) -> None:
        source = Path(build_run.__file__).resolve().parent
        with self.assertRaises(build_run.LabError):
            build_run.checked_output_path(source, source / "build")

    def test_hot_loops_have_no_cooperative_stop(self) -> None:
        source = Path(build_run.__file__).resolve().parent
        build_run.check_hot_loops(source)

    def test_timeout_kills_process_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="timer-timeout-test-") as directory:
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
            elf = root / "dummy.elf"
            elf.write_bytes(b"dummy")
            with self.assertRaises(build_run.LabError) as caught:
                build_run.run_qemu(fake, elf, 0.1)
            self.assertIn("process group killed", str(caught.exception))

    def test_code_sync_matches_sources(self) -> None:
        source = Path(build_run.__file__).resolve().parent
        mirror_path = source / "源码与测试镜像.md"
        if not mirror_path.exists():
            self.skipTest("mirror is generated after source freeze")
        mirror = mirror_path.read_text(encoding="utf-8")
        for name in (
            "trapframe.h", "trapframe_offsets.h", "linker.ld", "boot.S",
            "trap.S", "user.S", "kernel.c", "build_run.py", "test_build_run.py",
        ):
            match = re.search(
                rf"<!-- code-sync: \./{re.escape(name)} -->\n"
                rf"```[^\n]*\n(.*?)```\n",
                mirror,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), (source / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
