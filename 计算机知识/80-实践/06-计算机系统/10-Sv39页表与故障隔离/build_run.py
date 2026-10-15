#!/usr/bin/env python3
"""Build the RV64 Sv39 lab, run QEMU virt, and verify its complete trace."""

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


def resolve_tool(value: str | None, fallback: str) -> Path:
    candidate = value or shutil.which(fallback)
    if not candidate:
        raise LabError(f"tool not found: pass --{fallback.split('-')[0]} explicitly")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise LabError(f"tool is not executable: {path}")
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
        raise LabError(f"command exited {result.returncode}:\n{result.stdout}")
    return result.stdout


def first_version_line(tool: Path) -> str:
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
    sections = []
    for index in range(section_count):
        offset = section_offset + index * section_size
        sections.append(struct.unpack_from("<IIQQQQIIQQ", data, offset))
    symbols: dict[str, int] = {}
    for section in sections:
        if section[1] != 2:  # SHT_SYMTAB
            continue
        sym_offset, sym_size, link, entry_size = (
            section[4],
            section[5],
            section[6],
            section[9],
        )
        string_section = sections[link]
        strings = data[string_section[4] : string_section[4] + string_section[5]]
        for offset in range(sym_offset, sym_offset + sym_size, entry_size):
            name_offset, _, _, _, value, _ = struct.unpack_from(
                "<IBBHQQ", data, offset
            )
            end = strings.find(b"\0", name_offset)
            name = strings[name_offset:end].decode("utf-8", errors="replace")
            if name:
                symbols[name] = value
    return symbols


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
        obj = out_dir / f"{source.stem}.o"
        run_checked(common + ["-c", str(source), "-o", str(obj)], cwd=source_dir)
        objects.append(obj)

    elf = out_dir / "kernel.elf"
    map_file = out_dir / "kernel.map"
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
            str(map_file),
            "-o",
            str(elf),
            *(str(obj) for obj in objects),
        ],
        cwd=source_dir,
    )
    check_riscv_elf(elf)
    required = {
        "root_page_table": 0x80016000,
        "user_l1_page_table": 0x80017000,
        "user_l0_page_table": 0x80018000,
        "kernel_l1_page_table": 0x80019000,
        "kernel_l0_page_table": 0x8001A000,
    }
    symbols = elf_symbols(elf)
    for name, expected in required.items():
        if symbols.get(name) != expected:
            raise LabError(
                f"ELF symbol {name}={symbols.get(name)!r}, expected 0x{expected:x}"
            )
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
        raw_output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        os.killpg(process.pid, signal.SIGKILL)
        raw_output, _ = process.communicate()
        partial = raw_output.decode("utf-8", errors="replace")
        raise LabError(
            f"QEMU exceeded {timeout_seconds:.1f}s; process group killed:\n{partial}"
        ) from error
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    return process.returncode, raw_output.decode("utf-8", errors="replace")


def _hx(value: int) -> str:
    return f"0x{value:016x}"


def expected_patterns(symbols: dict[str, int]) -> tuple[str, ...]:
    store_pc = symbols["user_store_fault_insn"] - USER_ALIAS_DELTA
    load_pc = symbols["user_load_fault_insn"] - USER_ALIAS_DELTA
    return (
        r"MODE M: boot hart=0 delegate=0x000000000000b100",
        r"MODE S: build Sv39 tables",
        r"PAGE_TABLE root_pa=0x0000000080016000 entries=512 bytes=4096 levels=3",
        (
            r"WALK va=0x0000000040001000 vpn2=1 vpn1=0 vpn0=1 offset=0 "
            r"l2=0x0000000020005c01 l1=0x0000000020006001 "
            r"l0=0x00000000200044d7 pa=0x0000000080011000 flags=VRWUAD"
        ),
        (
            r"SATP readback=0x8000000000080016 mode=8 "
            r"root_ppn=0x0000000000080016 sfence.vma=global"
        ),
        r"POLICY SUM=0 MXR=0 A=pre-set D=pre-set",
        (
            r"MODE U: entry_va=0x0000000040000000 "
            r"entry_pa=0x0000000080010000 stack_va=0x0000000040005000"
        ),
        r"TRAP kind=ecall stage=0 scause=8 sepc=0x000000004000[0-9a-f]{4}",
        (
            r"ALIAS execute_va=0x0000000040000000 data_va=0x0000000040001000 "
            r"data_pa=0x0000000080011000 backing=0x5555666677778888 status=PASS"
        ),
        (
            r"PTE UPDATE va=0x0000000040001000 before=0x00000000200044d7 "
            r"after=0x00000000200044d3 sfence.vma=address-asid-all"
        ),
        (
            rf"FAULT kind=store scause=15 sepc={re.escape(_hx(store_pc))} "
            r"stval=0x0000000040001000 action=redirect-explicit-label"
        ),
        r"TRAP kind=ecall stage=2 scause=8 sepc=0x000000004000[0-9a-f]{4}",
        r"CHECK store-denied=PASS backing=0x5555666677778888",
        (
            rf"FAULT kind=load scause=13 sepc={re.escape(_hx(load_pc))} "
            r"stval=0x0000000080013000 action=redirect-explicit-label"
        ),
        r"TRAP kind=ecall stage=4 scause=8 sepc=0x000000004000[0-9a-f]{4}",
        r"CHECK load-u0-denied=PASS secret=0xcafebabedeadbeef",
        (
            r"FAULT kind=instruction scause=12 sepc=0x0000000040002000 "
            r"stval=0x0000000040002000 action=redirect-explicit-label"
        ),
        r"TRAP kind=ecall stage=6 scause=8 sepc=0x000000004000[0-9a-f]{4}",
        r"CHECK execute-nx-denied=PASS",
        r"RESULT PASS",
    )


def verify_output(returncode: int, output: str, symbols: dict[str, int]) -> None:
    if returncode != 0:
        raise LabError(f"QEMU exited with {returncode}, expected 0\n{output}")
    forbidden = ("RESULT FAIL", "UNEXPECTED", "MACHINE TRAP")
    for marker in forbidden:
        if marker in output:
            raise LabError(f"guest emitted forbidden marker {marker!r}\n{output}")
    lines = output.splitlines()
    patterns = expected_patterns(symbols)
    if len(lines) != len(patterns):
        raise LabError(
            f"guest emitted {len(lines)} lines, expected {len(patterns)}\n{output}"
        )
    for index, (line, pattern) in enumerate(zip(lines, patterns), 1):
        if re.fullmatch(pattern, line) is None:
            raise LabError(
                f"trace line {index} mismatch\nexpected /{pattern}/\nactual {line!r}"
            )
    if output.count("RESULT PASS") != 1:
        raise LabError("guest must emit exactly one RESULT PASS")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--clang", help="path to Clang with a riscv64 target")
    result.add_argument("--ld", help="path to ld.lld")
    result.add_argument("--qemu", help="path to qemu-system-riscv64")
    result.add_argument(
        "--out-dir",
        type=Path,
        help="keep products here; default uses an automatically removed temp dir",
    )
    result.add_argument("--timeout", type=float, default=8.0)
    return result


def checked_output_path(source_dir: Path, requested: Path) -> Path:
    output_path = requested.expanduser().resolve()
    if output_path == source_dir or source_dir in output_path.parents:
        raise LabError("--out-dir must be outside the source directory")
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout <= 0 or args.timeout > 60:
        raise SystemExit("--timeout must be in (0, 60]")
    source_dir = Path(__file__).resolve().parent
    clang = resolve_tool(args.clang, "clang")
    linker = resolve_tool(args.ld, "ld.lld")
    qemu = resolve_tool(args.qemu, "qemu-system-riscv64")
    print(f"CLANG VERSION: {first_version_line(clang)}")
    print(f"LLD VERSION: {first_version_line(linker)}")
    print(f"QEMU VERSION: {first_version_line(qemu)}")

    if args.out_dir is None:
        directory_context = tempfile.TemporaryDirectory(prefix="sv39-lab-")
        cleanup = True
    else:
        output_path = checked_output_path(source_dir, args.out_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        directory_context = contextlib.nullcontext(str(output_path))
        cleanup = False

    with directory_context as directory:
        out_dir = Path(directory).resolve()
        print(f"BUILD DIR: {out_dir}")
        elf = build(source_dir, out_dir, clang, linker)
        symbols = elf_symbols(elf)
        returncode, output = run_qemu(qemu, elf, args.timeout)
        print("--- guest stdout begin ---")
        print(output, end="" if output.endswith("\n") else "\n")
        print("--- guest stdout end ---")
        verify_output(returncode, output, symbols)
        print(f"VERIFY PASS: QEMU exit=0; {len(expected_patterns(symbols))} exact ordered lines")

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
