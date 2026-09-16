---
type: lab
domain: computer-science
stage: 7
status: ready
difficulty: 进阶
estimated_minutes: 60
topics:
  - cgroup v2
  - procfs
  - resource-view
  - monotonic-clock
  - deadline
  - Python
tags:
  - computer-science/systems
  - computer-science/virtualization
  - computer-science/time
  - computer-science/practice
---

# 资源视图与时间预算

## 目标与安全边界

本实验回答两个问题：当前 Python 进程实际看到了哪些 CPU/cgroup 资源边界？同一段 sleep + CPU 工作在 realtime、monotonic、performance counter 与 CPU-time clock 上分别表现为何？随后用绝对 monotonic deadline 演示“预算随经过时间减少”。

对应理论：[[计算机知识/30-计算机系统/19-容器虚拟机Namespace-Cgroup与虚拟IO|容器、虚拟机、Namespace、Cgroup 与虚拟 I/O]]与 [[计算机知识/30-计算机系统/20-时间时钟计时器Deadline与跨主机关联|时间、时钟、计时器、Deadline 与跨主机关联]]。

实验保持以下硬边界：

- 不创建或启动容器/虚拟机；
- 不写 cgroup，不移动进程，不设置 quota/cpuset，也不加载 BPF；
- 不修改系统时间、时区、NTP/PTP、CPU/GPU 频率或 timer；
- Linux 只读取当前进程的 `/proc/self/status`、`/proc/self/cgroup`，以及由后者解析出的当前 cgroup v2 目录中的白名单文件；
- 不递归扫描 `/proc` 或 `/sys`，不读取其他进程命令行、环境、文件描述符或凭据；
- 非 Linux、未挂载 procfs/cgroup v2 或权限不足时输出/测试为 `SKIP`，不伪装成通过。

`Uid`/`Gid`、CPU 集和 cgroup 路径仍可能反映本机身份/部署结构；分享输出前应按环境脱敏。脚本只展示 Python API 报告的 clock 属性；纳秒表示不等于纳秒 accuracy。

## 运行

在本目录执行：

```bash
python3 -m unittest -v
python3 resource_time_probe.py
```

预期结果：

- 所有纯解析与 deadline 单元测试通过；
- Linux 且 procfs/cgroup v2 可见时，集成测试读取当前进程视图；缺失时明确 `SKIP`；
- macOS/Windows 上 Linux 集成测试明确 `SKIP`，程序仍报告跨平台 clock 与 deadline；
- 输出包含 `logical_cpus_visible`、affinity 是否可用、clock 的 monotonic/adjustable/resolution，以及 sleep 后的剩余预算；
- 不应产生新容器、cgroup、配置文件或系统时间变化。

不要断言 `logical_cpus_visible`、affinity CPU 数、`cpuset.cpus.effective` 数量与 `cpu.max` 等价：它们分别描述拓扑视图、可调度集合与 CPU 时间配额。也不要断言 realtime 与 monotonic 的差值每次完全相等；调度、clock 实现与读取开销都会造成差异。尤其是 realtime 可被校时向后调整，因此它的 delta 可以为负；只有 monotonic、performance counter 与本进程/线程 CPU clock 的差值才适合在同一进程测量中断言非负。

所有 procfs/cgroup 文本读取都会多读一个字符以检测截断。若达到上限，输出明确标为 `TRUNCATED` 并跳过字段与配额解析；半截的 `io.max`、`cpu.max` 或路径绝不能被当作完整内核配置。

## 精确伴随文件

<!-- code-sync: ./resource_time_probe.py -->
```python
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

    directory = cgroup_directory(CGROUP_ROOT, relative)
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
```

<!-- code-sync: ./test_resource_time_probe.py -->
```python
import platform
import tempfile
import time
import unittest
from pathlib import Path

from resource_time_probe import (
    CGROUP_ROOT,
    PROC_CGROUP,
    PROC_STATUS,
    cgroup_directory,
    count_cpu_list,
    cpu_quota_equivalent,
    parse_cgroup_v2_path,
    parse_cpu_max,
    parse_proc_status,
    read_text_if_present,
    remaining_ns,
    resource_report,
    sample_clock_delta,
)


class ParserTests(unittest.TestCase):
    def test_proc_status_selects_only_allowlisted_fields(self) -> None:
        text = "Name:\tpython\nUid:\t501\t501\t501\t501\nSeccomp:\t2\n"
        self.assertEqual(
            parse_proc_status(text, ("Uid", "Seccomp")),
            {"Uid": "501\t501\t501\t501", "Seccomp": "2"},
        )

    def test_count_cpu_list_handles_ranges_duplicates_and_singletons(self) -> None:
        self.assertEqual(count_cpu_list("0-3,2,8,10-11"), 7)
        self.assertEqual(count_cpu_list(""), 0)

    def test_count_cpu_list_rejects_descending_range(self) -> None:
        with self.assertRaises(ValueError):
            count_cpu_list("4-2")

    def test_parse_cpu_max_and_equivalent(self) -> None:
        self.assertEqual(parse_cpu_max("200000 100000"), (200000, 100000))
        self.assertEqual(cpu_quota_equivalent("200000 100000"), 2.0)
        self.assertIsNone(cpu_quota_equivalent("max 100000"))

    def test_parse_cgroup_v2_path(self) -> None:
        text = "11:memory:/legacy\n0::/user.slice/example.scope\n"
        self.assertEqual(parse_cgroup_v2_path(text), "/user.slice/example.scope")
        self.assertIsNone(parse_cgroup_v2_path("2:cpu:/legacy\n"))

    def test_cgroup_directory_stays_below_root(self) -> None:
        root = Path("/sys/fs/cgroup")
        self.assertEqual(
            cgroup_directory(root, "/user.slice/example.scope"),
            root / "user.slice" / "example.scope",
        )
        with self.assertRaises(ValueError):
            cgroup_directory(root, "/../escape")

    def test_bounded_read_reports_truncation_without_parsing_a_partial_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "io.max"
            path.write_text("8:0 rbps=1000 wbps=2000\n", encoding="utf-8")
            result = read_text_if_present(path, limit=8)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.truncated)
        self.assertEqual(result.text, "8:0 rbps")


class DeadlineTests(unittest.TestCase):
    def test_remaining_ns_saturates_at_zero(self) -> None:
        self.assertEqual(remaining_ns(1_500, 1_000), 500)
        self.assertEqual(remaining_ns(1_500, 2_000), 0)

    def test_monotonic_and_cpu_clock_deltas_are_nonnegative(self) -> None:
        delta = sample_clock_delta(sleep_seconds=0, work_iterations=1_000)
        self.assertGreaterEqual(delta.monotonic_ns, 0)
        self.assertGreaterEqual(delta.perf_counter_ns, 0)
        self.assertGreaterEqual(delta.process_cpu_ns, 0)
        if delta.thread_cpu_ns is not None:
            self.assertGreaterEqual(delta.thread_cpu_ns, 0)

    def test_realtime_delta_can_be_negative_after_a_clock_adjustment(self) -> None:
        samples = {
            "realtime": iter((10_000, 9_000)),
            "monotonic": iter((100, 140)),
            "perf_counter": iter((200, 245)),
            "process_cpu": iter((300, 320)),
            "thread_cpu": iter((400, 410)),
        }

        def fake_clock(name: str) -> int:
            return next(samples[name])

        delta = sample_clock_delta(
            sleep_seconds=0,
            work_iterations=0,
            sleeper=lambda _: None,
            clock_ns=fake_clock,
        )
        self.assertEqual(delta.realtime_ns, -1_000)
        self.assertEqual(delta.monotonic_ns, 40)
        self.assertEqual(delta.perf_counter_ns, 45)
        self.assertEqual(delta.process_cpu_ns, 20)
        self.assertEqual(delta.thread_cpu_ns, 10)

    def test_negative_experiment_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            sample_clock_delta(sleep_seconds=-1)

    def test_monotonic_clock_contract_is_reported_by_python(self) -> None:
        self.assertTrue(time.get_clock_info("monotonic").monotonic)


@unittest.skipUnless(platform.system() == "Linux", "SKIP: Linux procfs/cgroup ABI unavailable")
class LinuxReadOnlyIntegrationTests(unittest.TestCase):
    def test_proc_self_status_is_readable_or_explicitly_skipped(self) -> None:
        text = read_text_if_present(PROC_STATUS)
        if text is None:
            self.skipTest("SKIP: /proc/self/status unavailable or unreadable")
        if text.truncated:
            self.skipTest("SKIP: /proc/self/status exceeds bounded read")
        self.assertIn("Uid", parse_proc_status(text.text))

    def test_current_cgroup_v2_path_when_mounted(self) -> None:
        text = read_text_if_present(PROC_CGROUP)
        if text is None:
            self.skipTest("SKIP: /proc/self/cgroup unavailable or unreadable")
        if text.truncated:
            self.skipTest("SKIP: /proc/self/cgroup exceeds bounded read")
        relative = parse_cgroup_v2_path(text.text)
        if relative is None:
            self.skipTest("SKIP: unified cgroup v2 hierarchy not visible")
        directory = cgroup_directory(CGROUP_ROOT, relative)
        if not directory.is_dir():
            self.skipTest("SKIP: current cgroup directory not mounted in this view")
        self.assertTrue(directory.is_dir())

    def test_resource_report_never_requires_linux_files_to_exist(self) -> None:
        lines = resource_report()
        self.assertTrue(any(line.startswith("platform=Linux") for line in lines))
        self.assertTrue(any(line.startswith(("cgroup_v2.path=", "cgroup_v2=SKIP")) for line in lines))


if __name__ == "__main__":
    unittest.main()
```

## 观察步骤

1. 先运行 unittest，确认解析和 deadline 算术不依赖本机恰好具有某个 cgroup 值。
2. 运行探针，记录 `platform`、`logical_cpus_visible`、`affinity_cpu_count` 或 `SKIP`。
3. Linux 上比较 `Cpus_allowed_list`、`cpuset.cpus.effective` 与 `cpu.max`。若任一项不可用或标为 `TRUNCATED`，只说明当前视图不暴露完整值；不要解析半截值、补写或提权。
4. 查看 clock 行，区分 `monotonic`、`adjustable` 与 `resolution_s`。不要把 resolution 当 accuracy。
5. 比较 `delta_ns`：sleep 会进入 monotonic/perf/realtime 的经过时间，却通常不进入 process/thread CPU time；差值只是本次带解释器/调度噪声的观察。实时时钟可因校时向后跳，负的 realtime delta 是允许的测试情形，不能据此否定 monotonic deadline。
6. 查看 50 ms absolute deadline 在约 10 ms sleep 后的剩余预算。调度抖动可能让剩余值与 40 ms 不完全相等，甚至在极端繁忙系统中归零。

## 练习、成功标准与清理

1. 只修改脚本常量，在 20/50/100 ms 总预算下运行，验证 `remaining_ns` 永不为负；恢复后重新跑测试。
2. 用纸面计算解释 `cpu.max="150000 100000"` 表示约 1.5 CPU 时间预算，为何它不是“绑定到 1.5 颗核”。不要写入真实 `cpu.max`。
3. 对比一次程序输出的 monotonic duration 与 process CPU duration，列出至少三种 `wall - CPU` 可能包含的等待，不能把它直接命名为 I/O time。
4. 成功标准：当前平台的可用测试通过，不可用能力明确 `SKIP`；README 两段 code-sync 与伴随文件逐字一致；运行前后没有新增容器/cgroup，也未改系统时间。

脚本正常运行不创建文件，因此没有清理步骤。Python 可能创建 `__pycache__`；它是解释器缓存，不是实验数据，可按仓库现有忽略规则处理，且本实验不自动删除或修改 Git 状态。

---

**理论一**：[[计算机知识/30-计算机系统/19-容器虚拟机Namespace-Cgroup与虚拟IO|容器、虚拟机、Namespace、Cgroup 与虚拟 I/O]] · **理论二**：[[计算机知识/30-计算机系统/20-时间时钟计时器Deadline与跨主机关联|时间、时钟、计时器、Deadline 与跨主机关联]] · **返回**：[[计算机知识/80-实践/06-计算机系统/00-计算机系统实践-MOC|计算机系统实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
