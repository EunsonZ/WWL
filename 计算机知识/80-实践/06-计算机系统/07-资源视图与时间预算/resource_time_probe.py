#!/usr/bin/env python3
"""Read this process's resource view and demonstrate monotonic deadlines.

The probe reads a small allowlist under /proc/self and /sys/fs/cgroup. It does
not create containers, write cgroups, change clocks, or require privileges.
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable


PROC_STATUS = Path("/proc/self/status")
PROC_CGROUP = Path("/proc/self/cgroup")
CGROUP_ROOT = Path("/sys/fs/cgroup")
STATUS_KEYS = (
    "Uid",
    "Gid",
    "Cpus_allowed_list",
    "Mems_allowed_list",
    "NoNewPrivs",
    "Seccomp",
)
CGROUP_FILES = (
    "cpu.max",
    "cpu.weight",
    "cpuset.cpus.effective",
    "memory.current",
    "memory.high",
    "memory.max",
    "pids.current",
    "pids.max",
    "io.max",
)


@dataclass(frozen=True)
class ClockDelta:
    realtime_ns: int
    monotonic_ns: int
    perf_counter_ns: int
    process_cpu_ns: int
    thread_cpu_ns: int | None


@dataclass(frozen=True)
class ReadText:
    """A bounded text read whose truncation status is explicit."""

    text: str
    truncated: bool


def parse_proc_status(text: str, keys: tuple[str, ...] = STATUS_KEYS) -> dict[str, str]:
    """Return only explicitly selected fields from /proc/self/status text."""
    selected = set(keys)
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in selected:
            result[key] = value.strip()
    return result


def count_cpu_list(spec: str) -> int:
    """Count distinct CPUs in Linux list syntax such as '0-3,8,10-11'."""
    cpus: set[int] = set()
    if not spec.strip():
        return 0
    for item in spec.split(","):
        item = item.strip()
        if not item:
            raise ValueError("empty CPU-list element")
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start < 0 or end < start:
                raise ValueError(f"invalid CPU range: {item}")
            cpus.update(range(start, end + 1))
        else:
            cpu = int(item)
            if cpu < 0:
                raise ValueError(f"invalid CPU: {item}")
            cpus.add(cpu)
    return len(cpus)


def parse_cpu_max(text: str) -> tuple[int | None, int]:
    """Parse cgroup v2 cpu.max; None means the quota token is 'max'."""
    fields = text.split()
    if len(fields) != 2:
        raise ValueError("cpu.max must contain quota and period")
    quota = None if fields[0] == "max" else int(fields[0])
    period = int(fields[1])
    if quota is not None and quota <= 0:
        raise ValueError("CPU quota must be positive or max")
    if period <= 0:
        raise ValueError("CPU period must be positive")
    return quota, period


def cpu_quota_equivalent(text: str) -> float | None:
    """Return quota/period in CPU-time units, or None for unlimited here."""
    quota, period = parse_cpu_max(text)
    return None if quota is None else quota / period


def parse_cgroup_v2_path(text: str) -> str | None:
    """Extract the current process's unified cgroup path."""
    for line in text.splitlines():
        hierarchy, separator, remainder = line.partition(":")
        if not separator:
            continue
        controllers, separator, path = remainder.partition(":")
        if separator and hierarchy == "0" and controllers == "" and path.startswith("/"):
            return path
    return None


def cgroup_directory(root: Path, cgroup_path: str) -> Path:
    """Map a kernel-reported v2 path below root without allowing traversal."""
    pure = PurePosixPath(cgroup_path)
    if pure.anchor != "/":
        raise ValueError("cgroup path must use a single absolute root")
    parts = tuple(part for part in pure.parts if part not in ("/", ""))
    if any(part in (".", "..") for part in parts):
        raise ValueError("cgroup path traversal is not allowed")
    return root.joinpath(*parts)


def read_text_if_present(path: Path, limit: int = 4096) -> ReadText | None:
    """Read bounded text from one known file, preserving a truncation signal."""
    if limit < 0:
        raise ValueError("read limit must be nonnegative")
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            raw = stream.read(limit + 1)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return None
    return ReadText(text=raw[:limit].strip(), truncated=len(raw) > limit)


def resource_report() -> list[str]:
    """Build a non-mutating, selected report for the current process."""
    lines = [f"platform={platform.system()} release={platform.release()}"]
    lines.append(f"logical_cpus_visible={os.cpu_count() or 'unknown'}")

    if hasattr(os, "sched_getaffinity"):
        try:
            lines.append(f"affinity_cpu_count={len(os.sched_getaffinity(0))}")
        except OSError as error:
            lines.append(f"affinity=SKIP reason={type(error).__name__}")
    else:
        lines.append("affinity=SKIP reason=API unavailable on this platform")

    if platform.system() != "Linux":
        lines.append("proc_status=SKIP reason=Linux procfs unavailable")
        lines.append("cgroup_v2=SKIP reason=Linux cgroup ABI unavailable")
        return lines

    status_text = read_text_if_present(PROC_STATUS)
    if status_text is None:
        lines.append("proc_status=SKIP reason=/proc/self/status unavailable")
    elif status_text.truncated:
        lines.append("proc_status=TRUNCATED limit=4096; fields not parsed")
    else:
        status = parse_proc_status(status_text.text)
        for key in STATUS_KEYS:
            if key in status:
                value = status[key]
                lines.append(f"proc.{key}={value}")
        cpu_spec = status.get("Cpus_allowed_list")
        if cpu_spec:
            try:
                lines.append(f"proc.allowed_cpu_count={count_cpu_list(cpu_spec)}")
            except ValueError:
                lines.append("proc.allowed_cpu_count=SKIP reason=unrecognized list")

    cgroup_text = read_text_if_present(PROC_CGROUP)
    if cgroup_text is None:
        lines.append("cgroup_v2=SKIP reason=/proc/self/cgroup unavailable")
        return lines
    if cgroup_text.truncated:
        lines.append("cgroup_v2=TRUNCATED limit=4096; path not parsed")
        return lines
    relative = parse_cgroup_v2_path(cgroup_text.text)
    if relative is None:
        lines.append("cgroup_v2=SKIP reason=unified hierarchy not visible")
        return lines

    try:
        directory = cgroup_directory(CGROUP_ROOT, relative)
    except ValueError:
        # A process may legally move outside its cgroup namespace root. Keep
        # the path guard: this view cannot map /../ safely below CGROUP_ROOT.
        lines.append("cgroup_v2=SKIP reason=path cannot be mapped below visible namespace root")
        return lines
    if not directory.is_dir():
        lines.append("cgroup_v2=SKIP reason=current cgroup directory unavailable")
        return lines

    lines.append(f"cgroup_v2.path={relative}")
    for filename in CGROUP_FILES:
        value = read_text_if_present(directory / filename, limit=1024)
        if value is None:
            lines.append(f"cgroup.{filename}=SKIP")
            continue
        if value.truncated:
            lines.append(f"cgroup.{filename}=TRUNCATED limit=1024; value not parsed")
            continue
        compact = " | ".join(value.text.splitlines()) if value.text else "(empty)"
        lines.append(f"cgroup.{filename}={compact}")
        if filename == "cpu.max":
            try:
                equivalent = cpu_quota_equivalent(value.text)
            except ValueError:
                lines.append("cgroup.cpu_quota_equivalent=SKIP reason=unrecognized cpu.max")
            else:
                rendered = "unlimited-at-this-level" if equivalent is None else f"{equivalent:.3f}"
                lines.append(f"cgroup.cpu_quota_equivalent={rendered}")
    return lines


def remaining_ns(deadline_ns: int, now_ns: int) -> int:
    """Return a saturated remaining duration for a same-domain deadline."""
    return max(0, deadline_ns - now_ns)


def system_clock_ns(name: str) -> int | None:
    """Read one named clock; the optional thread CPU clock may be unavailable."""
    clocks: dict[str, Callable[[], int]] = {
        "realtime": time.time_ns,
        "monotonic": time.monotonic_ns,
        "perf_counter": time.perf_counter_ns,
        "process_cpu": time.process_time_ns,
    }
    if name == "thread_cpu":
        thread_clock = getattr(time, "thread_time_ns", None)
        return None if thread_clock is None else thread_clock()
    try:
        return clocks[name]()
    except KeyError as error:
        raise ValueError(f"unknown clock: {name}") from error


def sample_clock_delta(
    sleep_seconds: float = 0.01,
    work_iterations: int = 50_000,
    sleeper: Callable[[float], None] = time.sleep,
    clock_ns: Callable[[str], int | None] = system_clock_ns,
) -> ClockDelta:
    """Compare clocks over sleep plus CPU work; realtime may move backwards.

    ``clock_ns`` is injectable so tests can model a wall-clock adjustment. It
    receives ``realtime``, ``monotonic``, ``perf_counter``, ``process_cpu``,
    or ``thread_cpu`` and returns nanoseconds; only ``thread_cpu`` may be None.
    """
    if sleep_seconds < 0 or work_iterations < 0:
        raise ValueError("durations and iteration counts must be nonnegative")
    before_thread = clock_ns("thread_cpu")
    before = (
        clock_ns("realtime"),
        clock_ns("monotonic"),
        clock_ns("perf_counter"),
        clock_ns("process_cpu"),
    )
    if any(value is None for value in before):
        raise RuntimeError("required clock unexpectedly unavailable")
    sleeper(sleep_seconds)
    accumulator = 0
    for number in range(work_iterations):
        accumulator ^= number * number
    if accumulator == -1:  # Keep the loop's result observably consumed.
        raise AssertionError("unreachable accumulator")
    after = (
        clock_ns("realtime"),
        clock_ns("monotonic"),
        clock_ns("perf_counter"),
        clock_ns("process_cpu"),
    )
    if any(value is None for value in after):
        raise RuntimeError("required clock unexpectedly unavailable")
    after_thread = clock_ns("thread_cpu")
    return ClockDelta(
        realtime_ns=after[0] - before[0],
        monotonic_ns=after[1] - before[1],
        perf_counter_ns=after[2] - before[2],
        process_cpu_ns=after[3] - before[3],
        thread_cpu_ns=None
        if before_thread is None or after_thread is None
        else after_thread - before_thread,
    )


def clock_report() -> list[str]:
    """Describe available Python clocks and one small deadline experiment."""
    lines: list[str] = []
    for name in ("time", "monotonic", "perf_counter", "process_time", "thread_time"):
        try:
            info = time.get_clock_info(name)
        except ValueError:
            lines.append(f"clock.{name}=SKIP reason=clock unavailable")
        else:
            lines.append(
                f"clock.{name}=implementation:{info.implementation} "
                f"monotonic:{info.monotonic} adjustable:{info.adjustable} "
                f"resolution_s:{info.resolution}"
            )

    started = time.monotonic_ns()
    budget_ns = 50_000_000
    deadline = started + budget_ns
    time.sleep(0.01)
    remaining = remaining_ns(deadline, time.monotonic_ns())
    lines.append(f"deadline.budget_ns={budget_ns} remaining_after_sleep_ns={remaining}")

    delta = sample_clock_delta()
    lines.append(
        "delta_ns="
        f"realtime:{delta.realtime_ns} monotonic:{delta.monotonic_ns} "
        f"perf_counter:{delta.perf_counter_ns} process_cpu:{delta.process_cpu_ns} "
        f"thread_cpu:{delta.thread_cpu_ns if delta.thread_cpu_ns is not None else 'SKIP'}"
    )
    lines.append("note=nanosecond representation does not imply nanosecond accuracy")
    return lines


def main() -> None:
    for line in resource_report():
        print(line)
    for line in clock_report():
        print(line)


if __name__ == "__main__":
    main()
