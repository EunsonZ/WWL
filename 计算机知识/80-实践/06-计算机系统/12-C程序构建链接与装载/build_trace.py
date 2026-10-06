#!/usr/bin/env python3
"""Build a small, bounded C program and record which build stage failed.

The script writes only inside a TemporaryDirectory, times every child process,
and treats tool absence as SKIP.  It is not a replacement for an object-file
format specification or a cross-platform linker test suite.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 15
COMMAND_LINE_TOOLS = Path("/Library/Developer/CommandLineTools")


def find_clang() -> str | None:
    """Prefer an independently installed clang over Apple's license-gated shim."""
    for candidate in ("/opt/homebrew/opt/llvm/bin/clang", "clang"):
        resolved = shutil.which(candidate) if candidate == "clang" else candidate
        if resolved and Path(resolved).is_file() and Path(resolved).stat().st_mode & 0o111:
            return resolved
    return None


def find_nm() -> str | None:
    """Prefer Homebrew LLVM's nm when Apple's developer-tool shim is unavailable."""
    for candidate in ("/opt/homebrew/opt/llvm/bin/llvm-nm", "llvm-nm", "nm"):
        resolved = shutil.which(candidate) if "/" not in candidate else candidate
        if resolved and Path(resolved).is_file() and Path(resolved).stat().st_mode & 0o111:
            return resolved
    return None


@dataclass(frozen=True)
class CommandResult:
    stage: str
    argv: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool


def child_environment() -> dict[str, str]:
    """Select already-installed CLT tools for this child only; change no system setting."""
    environment = dict(os.environ)
    if sys.platform == "darwin" and COMMAND_LINE_TOOLS.is_dir():
        environment["DEVELOPER_DIR"] = str(COMMAND_LINE_TOOLS)
    return environment


def run(stage: str, argv: list[str], directory: Path) -> CommandResult:
    try:
        completed = subprocess.run(
            argv,
            cwd=directory,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
            env=child_environment(),
        )
        return CommandResult(stage, argv, completed.returncode,
                             completed.stdout, completed.stderr, False)
    except subprocess.TimeoutExpired as error:
        return CommandResult(stage, argv, None,
                             error.stdout or "", error.stderr or "", True)


def copy_sources(directory: Path) -> None:
    for name in ("sum.h", "sum.c", "main.c", "duplicate_sum.c"):
        shutil.copy2(ROOT / name, directory / name)


def compile_unit(clang: str, source: str, output: str, directory: Path) -> CommandResult:
    return run(
        f"compile:{source}",
        [clang, "-std=c17", "-Wall", "-Wextra", "-Werror", "-c", source, "-o", output],
        directory,
    )


def is_platform_tool_gate(result: CommandResult) -> bool:
    """Recognize the local Xcode-license refusal without accepting it as a link test."""
    return "not agreed to the Xcode license agreements" in result.stderr


def trace(clang: str | None = None, nm: str | None = None) -> dict[str, object]:
    clang = clang or find_clang()
    if clang is None or (Path(clang).is_absolute() and not Path(clang).is_file()):
        return {"status": "SKIP", "reason": "clang was not found; no compiler was installed."}

    nm = nm or find_nm()
    with tempfile.TemporaryDirectory(prefix="wwl-link-trace-") as raw_directory:
        directory = Path(raw_directory)
        copy_sources(directory)
        results: list[CommandResult] = []
        for source, output in (("sum.c", "sum.o"), ("main.c", "main.o"),
                               ("duplicate_sum.c", "duplicate_sum.o")):
            results.append(compile_unit(clang, source, output, directory))

        if any(result.returncode != 0 for result in results):
            return {"status": "FAIL", "reason": "a required translation unit did not compile",
                    "commands": [asdict(result) for result in results]}

        if nm is None:
            results.append(CommandResult("inspect-symbols", ["nm"], None, "", "", False))
            symbol_note = "SKIP: nm was not found; object symbols were not inspected."
        else:
            results.append(run("inspect-symbols", [nm, "sum.o", "main.o"], directory))
            symbol_note = "nm output is a platform-specific observation, not an ABI specification."
        file_tool = shutil.which("file")
        if file_tool is None:
            results.append(CommandResult("inspect-object-format", ["file"], None, "", "", False))
        else:
            results.append(run("inspect-object-format", [file_tool, "sum.o"], directory))

        success = run("link:success", [clang, "main.o", "sum.o", "-o", "sum_demo"], directory)
        results.append(success)
        if is_platform_tool_gate(success):
            return {
                "status": "SKIP",
                "reason": "the platform linker is unavailable because Xcode license acceptance is required; no license was changed.",
                "platform": sys.platform,
                "compiler": clang,
                "developer_dir": child_environment().get("DEVELOPER_DIR"),
                "commands": [asdict(result) for result in results],
            }
        if success.returncode == 0:
            results.append(run("run:success", [str(directory / "sum_demo")], directory))

        missing = run("link:missing-definition", [clang, "main.o", "-o", "missing_demo"], directory)
        duplicate = run("link:duplicate-definition",
                        [clang, "main.o", "sum.o", "duplicate_sum.o", "-o", "duplicate_demo"], directory)
        results.extend((missing, duplicate))
        passed = (
            success.returncode == 0
            and results[-3].returncode == 0
            and results[-3].stdout == "sum=100\n"
            and missing.returncode != 0
            and duplicate.returncode != 0
            and not any(result.timed_out for result in results)
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "platform": sys.platform,
            "compiler": clang,
            "developer_dir": child_environment().get("DEVELOPER_DIR"),
            "symbol_note": symbol_note,
            "expectations": {
                "successful_program_stdout": "sum=100\\n",
                "missing_definition_must_fail_at_link": True,
                "duplicate_definition_must_fail_at_link": True,
            },
            "commands": [asdict(result) for result in results],
        }


def main() -> int:
    result = trace()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "SKIP"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
