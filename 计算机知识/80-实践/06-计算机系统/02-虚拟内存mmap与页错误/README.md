---
type: lab
domain: computer-science
stage: 2
status: ready
difficulty: 进阶
estimated_minutes: 60
topics: [虚拟内存, mmap, page-fault, Python]
tags: [computer-science/systems, computer-science/memory, computer-science/practice]
---

# 虚拟内存、mmap 与页错误可观察性

## 目标与边界

本实验用 Python 标准库创建 32 MiB 匿名可写映射，按页触碰，再在自动清理的临时目录中创建一个文件映射。`resource.getrusage` 返回的 `ru_minflt`/`ru_majflt` 是整个进程的累计计数，差值仍会夹杂 Python 解释器、调度、预取和并发活动。

这不是物理页查看器，也不应从计数差反推物理页号。文件映射的 major/minor 分类受内核、文件系统、稀疏文件实现和页缓存状态影响；`major=0` 和非零都可能是有效观察，不要把其中任一个结果解读为“没有 mmap”或“已经从物理磁盘读了同样多的页”。理论见 [[计算机知识/30-计算机系统/02-进程虚拟地址空间与内存映射|进程虚拟地址空间与内存映射]]。

本实验计数的是进程级 page fault，不是 TLB miss 或 page-table walk。已驻留页也可能因 TLB miss 发生页表遍历而不增加 `ru_minflt`/`ru_majflt`；相反，这里的 fault 差值也不能说明每次地址翻译的具体硬件路径。

## 运行

```bash
python3 -m unittest -v
python3 mmap_observer.py
```

Linux 和 macOS 都提供这里使用的 `mmap`/`resource` Unix 接口；Windows 不在本实验保证范围。重复 5 次，同时记录系统、Python 版本、页大小和前台负载。比较分布，不要只保留最符合预期的一次。

## 精确伴随文件

<!-- code-sync: ./mmap_observer.py -->
```python
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
```

<!-- code-sync: ./test_mmap_observer.py -->
```python
import mmap
import unittest

from mmap_observer import Faults, observe_anonymous, touch_each_page


class MmapObserverTests(unittest.TestCase):
    def test_fault_delta(self) -> None:
        self.assertEqual(Faults(9, 4) - Faults(3, 1), Faults(6, 3))

    def test_page_touch_changes_one_byte_per_page(self) -> None:
        page_size = mmap.PAGESIZE
        with mmap.mmap(-1, page_size * 3, access=mmap.ACCESS_WRITE) as mapping:
            self.assertEqual(touch_each_page(mapping, page_size, write=True), 3)
            self.assertEqual(touch_each_page(mapping, page_size, write=False), 3)

    def test_observation_returns_nonnegative_process_deltas(self) -> None:
        first, second = observe_anonymous(mmap.PAGESIZE * 4, mmap.PAGESIZE)
        self.assertGreaterEqual(first.minor, 0)
        self.assertGreaterEqual(first.major, 0)
        self.assertGreaterEqual(second.minor, 0)
        self.assertGreaterEqual(second.major, 0)


if __name__ == "__main__":
    unittest.main()
```

## 练习、成功标准与清理

1. 把匿名映射从 32 MiB 改为 4/64/256 MiB，重复测量。内存压力大时立即减小，不为了观察 major fault 故意把系统推入交换。
2. 将触碰步长改成页大小的 2 倍，解释为何“循环次数”、“触碰页数”与 fault 差值仍可能不一致。
3. 成功标准：3 个 unittest 通过；输出包含平台、页大小与三组计数差；报告不对差值大小或 major fault 做必然性承诺，也不把 fault 数当成 TLB miss 数。

文件映射位于 `TemporaryDirectory`，正常运行与 Python 异常退出都会走上下文清理；默认程序不接受用户路径。

---

**上一站**：[[计算机知识/80-实践/06-计算机系统/01-数据表示与对齐/README|数据表示与对齐]] · **下一站**：[[计算机知识/80-实践/06-计算机系统/03-缓存局部性benchmark/README|缓存局部性 benchmark]] · **Linux 对照**：[[计算机知识/20-操作系统/01-Linux/06-用户权限进程与作业控制|用户、权限、进程与作业控制]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/07-计算机组成原理-课程地图|计算机组成原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/30-计算机系统/22-缓存地址翻译一致性与存储层级推演|组成原理深化：缓存、地址翻译与一致性的定量模型]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
