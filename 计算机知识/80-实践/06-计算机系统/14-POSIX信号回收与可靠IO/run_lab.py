#!/usr/bin/env python3
"""Build and run the bounded POSIX teaching program outside the Vault."""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parent


def main() -> int:
    # On this workspace /usr/bin/cc can be an Xcode stub while Homebrew clang is
    # usable.  An explicit CC still wins, then choose clang before the stub.
    homebrew_clang = pathlib.Path("/opt/homebrew/opt/llvm/bin/clang")
    compiler = os.environ.get("CC") or (str(homebrew_clang) if homebrew_clang.exists() else None) or shutil.which("clang") or shutil.which("cc")
    if compiler is None:
        print("SKIP: no C compiler found", file=sys.stderr)
        return 77
    with tempfile.TemporaryDirectory(prefix="wwl-posix-rio-") as temporary:
        executable = pathlib.Path(temporary) / "posix_lab"
        command = [compiler, "-std=c11", "-D_POSIX_C_SOURCE=200809L", "-Wall", "-Wextra", "-Werror",
                   str(ROOT / "rio.c"), str(ROOT / "posix_lab.c"), "-o", str(executable)]
        environment = os.environ.copy()
        command_line_tools = pathlib.Path("/Library/Developer/CommandLineTools")
        if "DEVELOPER_DIR" not in environment and command_line_tools.exists():
            # Select an already-installed CLT SDK only for this subprocess.
            environment["DEVELOPER_DIR"] = str(command_line_tools)
        compiled = subprocess.run(command, text=True, capture_output=True, env=environment)
        if compiled.returncode != 0:
            # A local toolchain licence/SDK failure is not a failed teaching
            # assertion. Keep the candidate reviewable and let unittest skip.
            if "license" in (compiled.stderr + compiled.stdout).lower():
                print("SKIP: local C toolchain licence is not accepted", file=sys.stderr)
                return 77
            print(compiled.stderr, end="", file=sys.stderr)
            return compiled.returncode
        completed = subprocess.run([str(executable), "--self-test"], text=True, capture_output=True,
                                   check=True, env=environment)
        print(completed.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
