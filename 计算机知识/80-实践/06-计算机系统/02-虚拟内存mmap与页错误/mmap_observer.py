#!/usr/bin/env python3
"""Observe mmap page touches and process-level page-fault counters."""

from __future__ import annotations

import mmap
import os
import resource
import tempfile
from dataclasses import dataclass


@dataclass(frozen=True)
class Faults:
    minor: int
    major: int

    def __sub__(self, previous: "Faults") -> "Faults":
        return Faults(self.minor - previous.minor, self.major - previous.major)


def faults() -> Faults:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return Faults(usage.ru_minflt, usage.ru_majflt)


def touch_each_page(mapping: mmap.mmap, page_size: int, *, write: bool) -> int:
    checksum = 0
    for offset in range(0, len(mapping), page_size):
        if write:
            mapping[offset] = (mapping[offset] + 1) % 256
        checksum += mapping[offset]
    return checksum


def observe_anonymous(size: int, page_size: int) -> tuple[Faults, Faults]:
    with mmap.mmap(-1, size, access=mmap.ACCESS_WRITE) as mapping:
        before = faults()
        touch_each_page(mapping, page_size, write=True)
        after_first = faults()
        touch_each_page(mapping, page_size, write=False)
        after_second = faults()
    return after_first - before, after_second - after_first


def observe_file_mapping(size: int, page_size: int) -> Faults:
    with tempfile.TemporaryDirectory(prefix="mmap-lab-") as directory:
        path = os.path.join(directory, "pages.bin")
        with open(path, "wb") as stream:
            stream.truncate(size)
        with open(path, "rb") as stream:
            with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mapping:
                before = faults()
                touch_each_page(mapping, page_size, write=False)
                return faults() - before


def main() -> None:
    page_size = mmap.PAGESIZE
    size = 32 * 1024 * 1024
    first, second = observe_anonymous(size, page_size)
    file_faults = observe_file_mapping(size, page_size)
    print(f"platform={os.uname().sysname} page_size={page_size} bytes={size}")
    print(f"anonymous_first_touch minor={first.minor} major={first.major}")
    print(f"anonymous_second_touch minor={second.minor} major={second.major}")
    print(f"file_mapping_first_read minor={file_faults.minor} major={file_faults.major}")
    print("Counters cover the whole process and are noisy; major=0 is a valid result.")


if __name__ == "__main__":
    main()
