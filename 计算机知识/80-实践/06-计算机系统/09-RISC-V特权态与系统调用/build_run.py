#!/usr/bin/env python3
"""Build a freestanding RV64 ELF, run it on QEMU virt, and verify the trace."""

from __future__ import annotations

import argparse
import contextlib
import os
from pathlib import Path
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile


class LabError(RuntimeError):
    pass


TRACE_STEPS = (
    "MODE M: boot hart=0, delegate causes 2 and 8",
    "MODE S: stvec/sscratch installed, preparing sret",
    "MODE U: entered by sret",
    "TRAP kind=ecall scause=8",
    "origin.SPP=0 saved.SPIE=1",
    "SYSCALL number=1 arg0=41 return=42",
    "CHECK registers=PASS",
    "SYSCALL number=99 arg0=7 return=-38 status=unknown",
    "CHECK unknown-return=PASS",
    "TRAP kind=illegal scause=2",
    "origin.SPP=0 saved.SPIE=1",
    "ILLEGAL instruction=csrr-a0-sstatus action=skip return=-2",
    "CHECK illegal-recovery=PASS",
    "RESULT PASS",
)


def resolve_tool(value: str | None, fallback: str) -> Path:
    candidate = value or shutil.which(fallback)
    if not candidate:
        raise LabError(f"tool not found: pass --{fallback.split('-')[0]} explicitly")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise LabError(f"tool is not an executable file: {path}")
    return path


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
        raise LabError(
            f"command failed with exit {result.returncode}:\n{result.stdout}"
        )
    return result.stdout


def check_riscv_elf(path: Path) -> None:
    header = path.read_bytes()[:64]
    if len(header) < 20 or header[:4] != b"\x7fELF":
        raise LabError("linker output is not an ELF file")
    if header[4] != 2 or header[5] != 1:
        raise LabError("ELF must be 64-bit little-endian")
    machine = struct.unpack_from("<H", header, 18)[0]
    if machine != 243:
        raise LabError(f"ELF e_machine is {machine}, expected RISC-V (243)")


def build(source_dir: Path, out_dir: Path, clang: Path, linker: Path) -> Path:
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
    for source_name in ("boot.S", "trap.S", "user.S", "kernel.c"):
        source = source_dir / source_name
        obj = out_dir / (source.stem + ".o")
        run_checked(common + ["-c", str(source), "-o", str(obj)], cwd=source_dir)
        objects.append(obj)

    elf = out_dir / "kernel.elf"
    map_file = out_dir / "kernel.map"
    link_command = [
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
        str(map_file),
        "-o",
        str(elf),
        *(str(obj) for obj in objects),
    ]
    run_checked(link_command, cwd=source_dir)
    check_riscv_elf(elf)
    print(f"ELF CHECK PASS: {elf} is ELF64 little-endian RISC-V")
    return elf


def run_qemu(qemu: Path, elf: Path, timeout_seconds: float) -> tuple[int, str]:
    command = [
        str(qemu),
        "-machine",
        "virt",
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
        "-display",
        "none",
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
        raw_output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGKILL)
        raw_output, _ = process.communicate()
        output = raw_output.decode("utf-8", errors="replace")
        raise LabError(
            f"QEMU exceeded {timeout_seconds:.1f}s and was killed; partial output:\n"
            f"{output}"
        ) from error
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return process.returncode, raw_output.decode("utf-8", errors="replace")


def verify_output(returncode: int, output: str) -> None:
    if returncode != 0:
        raise LabError(f"QEMU exited with {returncode}, expected 0\n{output}")
    if "RESULT FAIL" in output:
        raise LabError(f"guest reported failure:\n{output}")
    position = 0
    for step in TRACE_STEPS:
        found = output.find(step, position)
        if found < 0:
            raise LabError(f"missing or out-of-order trace step: {step!r}\n{output}")
        position = found + len(step)
    if output.count("RESULT PASS") != 1:
        raise LabError("guest must emit exactly one RESULT PASS")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--clang", help="path to a Clang with riscv64 target support")
    result.add_argument("--ld", help="path to ld.lld")
    result.add_argument("--qemu", help="path to qemu-system-riscv64")
    result.add_argument(
        "--out-dir",
        type=Path,
        help="keep build products here; default is an automatically removed temp dir",
    )
    result.add_argument("--timeout", type=float, default=8.0, help="QEMU timeout in seconds")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout <= 0 or args.timeout > 60:
        raise SystemExit("--timeout must be in (0, 60]")

    source_dir = Path(__file__).resolve().parent
    clang = resolve_tool(args.clang, "clang")
    linker = resolve_tool(args.ld, "ld.lld")
    qemu = resolve_tool(args.qemu, "qemu-system-riscv64")

    if args.out_dir is None:
        directory_context = tempfile.TemporaryDirectory(prefix="c4-riscv-")
        cleanup = True
    else:
        output_path = args.out_dir.expanduser().resolve()
        if output_path == source_dir or source_dir in output_path.parents:
            raise LabError("--out-dir must be outside the source directory")
        output_path.mkdir(parents=True, exist_ok=True)
        directory_context = contextlib.nullcontext(str(output_path))
        cleanup = False

    with directory_context as directory:
        out_dir = Path(directory).resolve()
        print(f"BUILD DIR: {out_dir}")
        elf = build(source_dir, out_dir, clang, linker)
        returncode, output = run_qemu(qemu, elf, args.timeout)
        print("--- guest stdout begin ---")
        print(output, end="" if output.endswith("\n") else "\n")
        print("--- guest stdout end ---")
        verify_output(returncode, output)
        print(f"VERIFY PASS: QEMU exit={returncode}; {len(TRACE_STEPS)} ordered checks")

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
