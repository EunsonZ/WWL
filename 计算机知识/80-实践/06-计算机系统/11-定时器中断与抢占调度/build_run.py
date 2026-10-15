#!/usr/bin/env python3
"""Build and run the RV64 Sstc preemption lab, then verify the full trace."""

from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile


class LabError(RuntimeError):
    pass


USER_ALIAS_DELTA = 0x40010000
QUANTUM_TICKS = 2_000_000
MIN_WORK = 1_000


def resolve_tool(value: str | None, fallback: str) -> Path:
    candidate = value or shutil.which(fallback)
    if not candidate:
        raise LabError(f"tool not found: pass --{fallback.split('-')[0]} explicitly")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise LabError(f"tool is not executable: {path}")
    return path


def version_line(tool: Path) -> str:
    result = subprocess.run(
        [str(tool), "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise LabError(f"cannot read version from {tool}")
    return result.stdout.splitlines()[0]


def run_checked(command: list[str], *, cwd: Path) -> str:
    print("+", shlex.join(command))
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise LabError(f"command exited {result.returncode}:\n{result.stdout}")
    return result.stdout


def check_riscv_elf(path: Path) -> None:
    header = path.read_bytes()[:64]
    if len(header) < 64 or header[:4] != b"\x7fELF":
        raise LabError("linker output is not an ELF file")
    if header[4] != 2 or header[5] != 1:
        raise LabError("ELF must be 64-bit little-endian")
    machine = struct.unpack_from("<H", header, 18)[0]
    if machine != 243:
        raise LabError(f"ELF e_machine is {machine}, expected RISC-V (243)")


def elf_symbols(path: Path) -> dict[str, int]:
    data = path.read_bytes()
    section_offset = struct.unpack_from("<Q", data, 40)[0]
    section_size = struct.unpack_from("<H", data, 58)[0]
    section_count = struct.unpack_from("<H", data, 60)[0]
    sections = [
        struct.unpack_from(
            "<IIQQQQIIQQ", data, section_offset + index * section_size
        )
        for index in range(section_count)
    ]
    result: dict[str, int] = {}
    for section in sections:
        if section[1] != 2:
            continue
        offset, size, link, entry_size = section[4], section[5], section[6], section[9]
        strings_section = sections[link]
        strings = data[
            strings_section[4] : strings_section[4] + strings_section[5]
        ]
        for position in range(offset, offset + size, entry_size):
            name_offset, _, _, _, value, _ = struct.unpack_from(
                "<IBBHQQ", data, position
            )
            end = strings.find(b"\0", name_offset)
            name = strings[name_offset:end].decode("utf-8", errors="replace")
            if name:
                result[name] = value
    return result


def check_hot_loops(source_dir: Path) -> None:
    text = (source_dir / "user.S").read_text(encoding="utf-8")
    for task in (0, 1):
        match = re.search(
            rf"user{task}_hot_loop:\n(?P<body>.*?)"
            rf"\n\s*\.globl user{task}_hot_loop_end",
            text,
            flags=re.DOTALL,
        )
        if match is None:
            raise LabError(f"cannot locate task {task} hot loop")
        body = match.group("body")
        if re.search(r"\b(ecall|wfi|yield)\b", body):
            raise LabError(f"task {task} hot loop contains a cooperative stop")


def build(source_dir: Path, out_dir: Path, clang: Path, linker: Path) -> Path:
    check_hot_loops(source_dir)
    common = [
        str(clang),
        "--target=riscv64-unknown-elf",
        "-march=rv64im_zicsr",
        "-mabi=lp64",
        "-mcmodel=medany",
        "-mno-relax",
        "-msmall-data-limit=0",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-pic",
        "-fno-stack-protector",
        "-ffunction-sections",
        "-fdata-sections",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        f"-I{source_dir}",
    ]
    objects: list[Path] = []
    for name in ("boot.S", "trap.S", "user.S", "kernel.c"):
        source = source_dir / name
        obj = out_dir / f"{source.stem}.o"
        run_checked(common + ["-c", str(source), "-o", str(obj)], cwd=source_dir)
        objects.append(obj)
    elf = out_dir / "kernel.elf"
    run_checked(
        [
            str(linker),
            "-m",
            "elf64lriscv",
            "--gc-sections",
            "--no-relax",
            "-z",
            "max-page-size=4096",
            "-T",
            str(source_dir / "linker.ld"),
            "-Map",
            str(out_dir / "kernel.map"),
            "-o",
            str(elf),
            *(str(obj) for obj in objects),
        ],
        cwd=source_dir,
    )
    check_riscv_elf(elf)
    symbols = elf_symbols(elf)
    expected = {
        "user0_start": 0x80010000,
        "user1_start": 0x80012000,
        "root_page_table": 0x80015000,
        "task0_trapframe": 0x8001A000,
        "task1_trapframe": 0x8001B000,
    }
    for name, value in expected.items():
        if symbols.get(name) != value:
            raise LabError(f"symbol {name}={symbols.get(name)!r}, expected 0x{value:x}")
    print(f"ELF CHECK PASS: {elf} is ELF64 little-endian RISC-V")
    return elf


def run_qemu(qemu: Path, elf: Path, timeout: float) -> tuple[int, str]:
    command = [
        str(qemu),
        "-machine",
        "virt",
        "-cpu",
        "rv64,sstc=true",
        "-accel",
        "tcg",
        "-smp",
        "1",
        "-m",
        "128M",
        "-bios",
        "none",
        "-kernel",
        str(elf),
        "-nographic",
        "-serial",
        "stdio",
        "-monitor",
        "none",
        "-net",
        "none",
        "-no-reboot",
    ]
    print("+", shlex.join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        raw, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGKILL)
        raw, _ = process.communicate()
        raise LabError(
            f"QEMU exceeded {timeout:.1f}s; process group killed:\n"
            f"{raw.decode('utf-8', errors='replace')}"
        ) from error
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return process.returncode, raw.decode("utf-8", errors="replace")


def _user(symbols: dict[str, int], name: str) -> int:
    return symbols[name] - USER_ALIAS_DELTA


def _parse_hex(value: str) -> int:
    return int(value, 16)


TICK_RE = re.compile(
    r"TICK n=(?P<n>[1-6]) cause=0x8000000000000005 "
    r"now=(?P<now>0x[0-9a-f]{16}) deadline=(?P<deadline>0x[0-9a-f]{16}) "
    r"from=(?P<from>[01]) to=(?P<to>[01]) "
    r"sepc=(?P<sepc>0x[0-9a-f]{16}) sp=(?P<sp>0x[0-9a-f]{16}) "
    r"work=(?P<work>0x[0-9a-f]{16}) stack=(?P<stack>0x[0-9a-f]{16}) "
    r"SPP=0 SPIE=1 depth=1"
)
SWITCH_RE = re.compile(
    r"SWITCH from_tf=(?P<from_tf>0x[0-9a-f]{16}) "
    r"to_tf=(?P<to_tf>0x[0-9a-f]{16}) "
    r"next_pc=(?P<next_pc>0x[0-9a-f]{16})"
)
EXIT_RE = re.compile(
    r"EXIT task=(?P<task>[01]) work=(?P<work>0x[0-9a-f]{16}) "
    r"stack=(?P<stack>0x[0-9a-f]{16}) preemptions=3 status=PASS"
)


def verify_output(returncode: int, output: str, symbols: dict[str, int]) -> None:
    if returncode != 0:
        raise LabError(f"QEMU exited with {returncode}, expected 0\n{output}")
    for forbidden in ("RESULT FAIL", "MACHINE TRAP", "UNEXPECTED"):
        if forbidden in output:
            raise LabError(f"forbidden marker {forbidden!r}\n{output}")
    lines = output.splitlines()
    if len(lines) != 23:
        raise LabError(f"guest emitted {len(lines)} lines, expected 23\n{output}")
    fixed = (
        "MODE M: Sstc=1 STCE=1 mcounteren.TM=1 mideleg.STIP=1 MTIE=0",
        "MODE S: build Sv39 and two user contexts",
        "SATP mode=8 root_pa=0x0000000080015000 "
        "user0_code=0x0000000040000000 user1_code=0x0000000040002000",
    )
    if tuple(lines[:3]) != fixed:
        raise LabError("boot/Sv39 header mismatch")
    timer = re.fullmatch(
        r"TIMER source=Sstc timebase_hz=10000000 quantum_ticks=2000000 "
        r"now=(0x[0-9a-f]{16}) first_deadline=(0x[0-9a-f]{16}) "
        r"STIE=1 SPIE=1 SIE-before-sret=0",
        lines[3],
    )
    if timer is None or _parse_hex(timer.group(2)) - _parse_hex(timer.group(1)) != QUANTUM_TICKS:
        raise LabError("timer source/deadline mismatch")
    if lines[4] != (
        "TASK id=0 tf=0x000000008001a000 "
        "stack=[0x0000000040003000,0x0000000040004000) "
        "entry=0x0000000040000000"
    ):
        raise LabError("task 0 layout mismatch")
    if lines[5] != (
        "TASK id=1 tf=0x000000008001b000 "
        "stack=[0x0000000040004000,0x0000000040005000) "
        "entry=0x0000000040002000"
    ):
        raise LabError("task 1 layout mismatch")
    if lines[6] != "MODE U: task=0 hot-loop-no-yield":
        raise LabError("U-mode entry marker mismatch")

    loop_lo = [_user(symbols, "user0_hot_loop"), _user(symbols, "user1_hot_loop")]
    loop_hi = [
        _user(symbols, "user0_hot_loop_end"),
        _user(symbols, "user1_hot_loop_end"),
    ]
    exit_pc = [_user(symbols, "user0_exit"), _user(symbols, "user1_exit")]
    frame = [0x8001A000, 0x8001B000]
    stack_pointer = [0x40004000, 0x40005000]
    saved_pc = [0x40000000, 0x40002000]
    previous_work = [0, 0]
    previous_stack = [0, 0]
    cursor = 7
    for tick in range(1, 7):
        tick_match = TICK_RE.fullmatch(lines[cursor])
        switch_match = SWITCH_RE.fullmatch(lines[cursor + 1])
        if tick_match is None or switch_match is None:
            raise LabError(f"tick/switch pair {tick} malformed")
        source = (tick - 1) % 2
        target = 1 - source
        values = {key: tick_match.group(key) for key in tick_match.groupdict()}
        if int(values["n"]) != tick or int(values["from"]) != source or int(values["to"]) != target:
            raise LabError(f"tick {tick} is duplicated or out of order")
        now = _parse_hex(values["now"])
        deadline = _parse_hex(values["deadline"])
        sepc = _parse_hex(values["sepc"])
        sp = _parse_hex(values["sp"])
        work = _parse_hex(values["work"])
        stack = _parse_hex(values["stack"])
        if deadline - now != QUANTUM_TICKS:
            raise LabError(f"tick {tick} deadline is not one quantum ahead")
        if not (loop_lo[source] <= sepc < loop_hi[source]):
            raise LabError(f"tick {tick} sepc is outside task {source} hot loop")
        if sp != stack_pointer[source]:
            raise LabError(f"tick {tick} stack pointer mismatch")
        if (work < MIN_WORK or work <= previous_work[source] or
                stack < MIN_WORK or stack <= previous_stack[source]):
            raise LabError(f"task {source} did not make forward progress")
        previous_work[source], previous_stack[source] = work, stack
        saved_pc[source] = exit_pc[source] if tick >= 5 else sepc
        if _parse_hex(switch_match.group("from_tf")) != frame[source]:
            raise LabError(f"tick {tick} source trapframe mismatch")
        if _parse_hex(switch_match.group("to_tf")) != frame[target]:
            raise LabError(f"tick {tick} target trapframe mismatch")
        if _parse_hex(switch_match.group("next_pc")) != saved_pc[target]:
            raise LabError(f"tick {tick} restored the wrong target PC")
        cursor += 2

    for expected_task in (0, 1):
        match = EXIT_RE.fullmatch(lines[cursor])
        if match is None or int(match.group("task")) != expected_task:
            raise LabError(f"missing independent exit for task {expected_task}")
        if _parse_hex(match.group("work")) < previous_work[expected_task]:
            raise LabError(f"task {expected_task} exit work regressed")
        if _parse_hex(match.group("stack")) < previous_stack[expected_task]:
            raise LabError(f"task {expected_task} exit stack regressed")
        cursor += 1
    if lines[cursor] != (
        "SUMMARY ticks=6 task0_preemptions=3 task1_preemptions=3 "
        "switches=6 status=PASS"
    ):
        raise LabError("summary mismatch")
    if lines[cursor + 1] != "RESULT PASS" or output.count("RESULT PASS") != 1:
        raise LabError("guest must emit exactly one final RESULT PASS")


def checked_output_path(source_dir: Path, requested: Path) -> Path:
    output = requested.expanduser().resolve()
    if output == source_dir or source_dir in output.parents:
        raise LabError("--out-dir must be outside the source directory")
    return output


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--clang")
    result.add_argument("--ld")
    result.add_argument("--qemu")
    result.add_argument("--out-dir", type=Path)
    result.add_argument("--timeout", type=float, default=10.0)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout <= 0 or args.timeout > 60:
        raise SystemExit("--timeout must be in (0, 60]")
    source_dir = Path(__file__).resolve().parent
    clang = resolve_tool(args.clang, "clang")
    linker = resolve_tool(args.ld, "ld.lld")
    qemu = resolve_tool(args.qemu, "qemu-system-riscv64")
    clang_version = version_line(clang)
    linker_version = version_line(linker)
    qemu_version = version_line(qemu)
    if "9.2.4" not in qemu_version:
        raise LabError(f"this evidence contract requires QEMU 9.2.4: {qemu_version}")
    print(f"CLANG VERSION: {clang_version}")
    print(f"LLD VERSION: {linker_version}")
    print(f"QEMU VERSION: {qemu_version}")

    if args.out_dir is None:
        manager = tempfile.TemporaryDirectory(prefix="timer-preempt-lab-")
        cleanup = True
    else:
        output = checked_output_path(source_dir, args.out_dir)
        output.mkdir(parents=True, exist_ok=True)
        manager = contextlib.nullcontext(str(output))
        cleanup = False
    with manager as directory:
        out_dir = Path(directory).resolve()
        print(f"BUILD DIR: {out_dir}")
        elf = build(source_dir, out_dir, clang, linker)
        symbols = elf_symbols(elf)
        returncode, output = run_qemu(qemu, elf, args.timeout)
        print("--- guest stdout begin ---")
        print(output, end="" if output.endswith("\n") else "\n")
        print("--- guest stdout end ---")
        verify_output(returncode, output, symbols)
        print("VERIFY PASS: QEMU exit=0; 6 real timer ticks; 2 independent exits")
    if cleanup:
        print("CLEANUP PASS: automatic temporary build directory removed")
    else:
        print(f"CLEANUP NOTE: kept caller-selected build directory {args.out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LabError as error:
        raise SystemExit(f"ERROR: {error}") from error
