"""Direct compile/link/run capability, followed by the unchanged C11 queue.

No feature macros are removed, no shim installed. Exit 77 means unsupported;
1 means a failed command/runtime check. Commands and diagnostics stay visible.
"""
import argparse
from pathlib import Path
import shlex
import re
import subprocess
import sys


def command(argv, timeout=30):
    print("$ " + shlex.join(argv), flush=True)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    print(f"command_exit={result.returncode}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="/usr/bin/clang")
    parser.add_argument("--build", required=True)
    parser.add_argument("--ldflag", action="append", default=[],
                        help="existing target linker option, e.g. --ldflag=-pthread")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    build = Path(args.build).resolve()
    build.mkdir(parents=True, exist_ok=True)
    cc = shlex.split(args.cc)
    flags = ["-std=c17", "-O2", "-g", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Werror"]
    if command(cc + ["--version"]).returncode:
        return 1
    macro_command = cc + ["-std=c17", "-dM", "-E", "-x", "c", "-"]
    print("$ " + shlex.join(macro_command) + " < empty_input", flush=True)
    macros = subprocess.run(macro_command, input="", capture_output=True, text=True, timeout=30)
    if macros.returncode:
        print(macros.stderr, file=sys.stderr)
        return 1
    defines = {line.split()[1]: line.split()[2:] for line in macros.stdout.splitlines()
               if line.startswith("#define ")}
    no_threads = defines.get("__STDC_NO_THREADS__") == ["1"]
    no_atomics = defines.get("__STDC_NO_ATOMICS__") == ["1"]
    print(f"advertised_no_threads={int(no_threads)} advertised_no_atomics={int(no_atomics)}")
    # Unlike guarded probe.c, always attempt the actual header and declarations.
    obj = build / "thread_smoke.o"
    compiled = command(cc + flags + ["-c", str(source / "thread_smoke.c"), "-o", str(obj)])
    if compiled.returncode:
        # Inspect the filename in the actual fatal diagnostic, not include-stack
        # paths. A present threads.h may itself include an unrelated missing file.
        errors = [line for line in compiled.stderr.splitlines()
                  if re.search(r"(?:^|: )(?:fatal )?error: ", line)]
        expected_missing = False
        if len(errors) == 1 and "fatal error: " in errors[0]:
            message = errors[0].split("fatal error: ", 1)[1]
            missing = re.fullmatch(r"'(threads\.h|stdatomic\.h)' file not found", message)
            if missing is None:
                missing = re.fullmatch(r"(threads\.h|stdatomic\.h): No such file or directory", message)
            if missing is not None:
                expected_missing = (missing[1] == "threads.h" and no_threads) or (
                    missing[1] == "stdatomic.h" and no_atomics)
        print("direct_thread_capability=" + ("UNSUPPORTED missing_C11_header" if expected_missing else "COMPILE_FAILED"))
        print("queue_body=NOT_COMPILED_OR_RUN")
        return 77 if expected_missing else 1
    binary = build / "thread_smoke"
    linked = command(cc + [str(obj)] + args.ldflag + ["-o", str(binary)])
    if linked.returncode:
        print("direct_thread_capability=LINK_FAILED queue_body=NOT_COMPILED_OR_RUN")
        return 1
    if command([str(binary)], timeout=15).returncode:
        print("direct_thread_capability=RUNTIME_FAILED queue_body=NOT_COMPILED_OR_RUN")
        return 1
    if no_threads or no_atomics:
        print("direct_API=RUNNABLE advertised_C11_support=UNSUPPORTED queue_body=NOT_COMPILED_OR_RUN")
        return 77
    queue = build / "thread_queue"
    compiled_queue = command(cc + flags + ["-I" + str(source.parent / "include"),
        str(source / "thread_queue.c"), str(source.parent / "src" / "measure.c")]
        + args.ldflag + ["-lm", "-o", str(queue)])
    if compiled_queue.returncode:
        return 1
    ran = command([str(queue)], timeout=15)
    if ran.returncode or "bounded_queue=PASS normal,drain,cancel,create_failure,join,ordered_fir" not in ran.stdout:
        return 1
    print("direct_thread_capability=PASS queue_body=COMPILED_AND_RUN")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"thread_capability=FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
