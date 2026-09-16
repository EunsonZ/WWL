#!/usr/bin/env python3
"""Read small, portable memory and CPU-topology observations without changing policy."""

from __future__ import annotations

import mmap
import os
import platform
from dataclasses import dataclass
from pathlib import Path


MAPPING_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class ProcessMemory:
    virtual_kib: int | None
    resident_kib: int | None


@dataclass(frozen=True)
class LinuxTopology:
    logical_cpus_observed: int
    cores_observed: int | None
    packages_observed: int | None
    nodes: tuple[tuple[str, tuple[int, ...]], ...]


def parse_cpu_list(text: str) -> tuple[int, ...]:
    """Parse Linux cpulist syntax such as '0-3,8,10-11'."""
    cpus: set[int] = set()
    for raw_part in text.strip().split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"descending CPU range: {part}")
            cpus.update(range(start, end + 1))
        else:
            cpus.add(int(part))
    return tuple(sorted(cpus))


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def discover_linux_topology(system_root: Path = Path("/sys/devices/system")) -> LinuxTopology | None:
    cpu_root = system_root / "cpu"
    try:
        cpu_paths = sorted(
            path for path in cpu_root.glob("cpu[0-9]*") if path.name[3:].isdigit()
        )
    except OSError:
        return None
    if not cpu_paths:
        return None

    core_keys: set[tuple[int, int]] = set()
    package_ids: set[int] = set()
    complete_core_ids = True
    for cpu_path in cpu_paths:
        package_id = _read_int(cpu_path / "topology" / "physical_package_id")
        core_id = _read_int(cpu_path / "topology" / "core_id")
        if package_id is None or core_id is None:
            complete_core_ids = False
        else:
            package_ids.add(package_id)
            core_keys.add((package_id, core_id))

    nodes: list[tuple[str, tuple[int, ...]]] = []
    node_root = system_root / "node"
    try:
        node_paths = sorted(
            path for path in node_root.glob("node[0-9]*") if path.name[4:].isdigit()
        )
    except OSError:
        node_paths = []
    for node_path in node_paths:
        try:
            cpus = parse_cpu_list((node_path / "cpulist").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        nodes.append((node_path.name, cpus))

    return LinuxTopology(
        logical_cpus_observed=len(cpu_paths),
        cores_observed=len(core_keys) if complete_core_ids else None,
        packages_observed=len(package_ids) if complete_core_ids else None,
        nodes=tuple(nodes),
    )


def read_linux_process_memory(status_path: Path = Path("/proc/self/status")) -> ProcessMemory:
    values: dict[str, int] = {}
    try:
        lines = status_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ProcessMemory(None, None)
    for line in lines:
        key, separator, remainder = line.partition(":")
        if separator and key in {"VmSize", "VmRSS"}:
            fields = remainder.split()
            if fields and fields[0].isdigit():
                values[key] = int(fields[0])
    return ProcessMemory(values.get("VmSize"), values.get("VmRSS"))


def observe_mapping(size: int = MAPPING_BYTES) -> tuple[ProcessMemory, ProcessMemory, ProcessMemory, int]:
    if size <= 0 or size > MAPPING_BYTES:
        raise ValueError(f"size must be in 1..{MAPPING_BYTES}")
    before = read_linux_process_memory()
    with mmap.mmap(-1, size, access=mmap.ACCESS_WRITE) as mapping:
        after_map = read_linux_process_memory()
        checksum = 0
        for offset in range(0, size, mmap.PAGESIZE):
            mapping[offset] = 1
            checksum += mapping[offset]
        after_touch = read_linux_process_memory()
    return before, after_map, after_touch, checksum


def allowed_cpu_count() -> int | None:
    get_affinity = getattr(os, "sched_getaffinity", None)
    if get_affinity is None:
        return None
    try:
        return len(get_affinity(0))
    except OSError:
        return None


def iommu_group_count(root: Path = Path("/sys/kernel/iommu_groups")) -> int | None:
    try:
        if not root.is_dir():
            return None
        return sum(1 for path in root.iterdir() if path.name.isdigit() and path.is_dir())
    except OSError:
        return None


def _format_optional(value: object | None, reason: str) -> str:
    return str(value) if value is not None else f"SKIP({reason})"


def main() -> None:
    before, after_map, after_touch, checksum = observe_mapping()
    topology = discover_linux_topology()
    print(f"platform={platform.system()} release={platform.release()} machine={platform.machine()}")
    print(f"page_size_bytes={mmap.PAGESIZE} mapping_bytes={MAPPING_BYTES} checksum={checksum}")
    print(
        "process_memory_kib "
        f"before_vmsize={_format_optional(before.virtual_kib, 'no-/proc-self-status')} "
        f"after_map_vmsize={_format_optional(after_map.virtual_kib, 'no-/proc-self-status')} "
        f"before_rss={_format_optional(before.resident_kib, 'no-/proc-self-status')} "
        f"after_touch_rss={_format_optional(after_touch.resident_kib, 'no-/proc-self-status')}"
    )
    print(
        f"logical_cpus_os={_format_optional(os.cpu_count(), 'runtime-unavailable')} "
        f"allowed_cpus_read_only={_format_optional(allowed_cpu_count(), 'no-sched-getaffinity')}"
    )
    if topology is None:
        print("linux_topology=SKIP(no-readable-linux-sysfs)")
    else:
        print(
            f"linux_topology logical={topology.logical_cpus_observed} "
            f"cores={_format_optional(topology.cores_observed, 'incomplete-core-id')} "
            f"packages={_format_optional(topology.packages_observed, 'incomplete-package-id')}"
        )
        if topology.nodes:
            node_text = ";".join(f"{name}:{','.join(map(str, cpus))}" for name, cpus in topology.nodes)
            print(f"linux_numa_nodes={node_text}")
        else:
            print("linux_numa_nodes=SKIP(no-readable-node-cpulist)")
    print(f"iommu_groups={_format_optional(iommu_group_count(), 'no-readable-iommu-sysfs')}")
    print("gpu_translation=SKIP(no-vendor-API; host observations do not prove GPU page-table state)")
    print("note=observations are snapshots; no affinity, NUMA policy, sysctl, or huge-page setting changed")


if __name__ == "__main__":
    main()
