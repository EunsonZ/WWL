---
type: lab
domain: computer-science
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 65
topics: [atomic-replace, fsync, durability, Python]
tags: [computer-science/systems, computer-science/filesystem, computer-science/practice]
---

# 文件系统原子替换与 fsync 边界

## 目标

安全更新一个文件通常不是直接截断目标，而是：

```text
在目标同目录创建唯一临时文件
  -> 完整写入
  -> flush Python 缓冲区
  -> fsync 文件内容
  -> os.replace 原子切换目录项
  -> fsync 父目录元数据（平台/文件系统支持时）
```

`os.replace` 的原子可见性不等于突然断电后已持久化；文件 `fsync` 与目录 `fsync` 保护的对象也不同。具体保证仍取决于 OS、文件系统、存储设备与硬件写缓存；本实验不通过拔电、强制崩溃或写块设备来声称验证它。机制先修是 [[计算机知识/30-计算机系统/13-文件系统布局日志CoW与一致性|文件系统布局、日志、CoW 与一致性]]，Linux 操作视角见 [[计算机知识/20-操作系统/01-Linux/03-目录结构挂载与文件系统|目录结构、挂载与文件系统]]。

> [!warning] 名字已切换、目录已同步、原元数据已保留是三件事
> `os.replace` 成功后，新名字已可见，即使随后目录 `fsync` 不支持或失败，函数也无法用删除临时名恢复旧目标。而且 `mkstemp` 创建的是一个新 inode；替换现有文件时，旧目标的 mode、owner 规则、ACL、xattr 等不会自动被本示例复制到新 inode。所以本实验返回结构化状态，并明确不是可直接复制到生产配置文件的完整库函数。

## 运行与安全边界

```bash
python3 -m unittest -v
python3 atomic_replace.py
```

演示程序不接受命令行路径；它只在 `TemporaryDirectory` 中替换 `state.txt`，打印观察后删除整个自建临时目录。测试亦只使用独立临时目录。不要把实验目标改成配置文件、仓库文件或用户数据来“更真实”地测试。

## 精确伴随文件

<!-- code-sync: ./atomic_replace.py -->
```python
#!/usr/bin/env python3
"""Write a file through a same-directory temporary file and atomic replacement."""

from __future__ import annotations

import errno
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DirectorySyncStatus(str, Enum):
    SYNCED = "synced"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AtomicWriteResult:
    replacement_visible: bool
    directory_sync: DirectorySyncStatus

    @property
    def durability_claim_allowed(self) -> bool:
        return self.replacement_visible and self.directory_sync is DirectorySyncStatus.SYNCED


class AtomicWriteAfterReplaceError(RuntimeError):
    """Directory sync failed after the replacement became visible."""

    def __init__(self, cause: OSError) -> None:
        super().__init__(f"replacement is visible but directory sync failed: {cause}")
        self.replacement_visible = True


def fsync_directory(directory: Path) -> DirectorySyncStatus:
    """Sync directory metadata when the platform/filesystem supports it."""
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
        return DirectorySyncStatus.SYNCED
    except OSError as error:
        if error.errno in {errno.EINVAL, errno.ENOTSUP}:
            return DirectorySyncStatus.UNSUPPORTED
        raise
    finally:
        os.close(descriptor)


def atomic_write(path: Path, payload: bytes) -> AtomicWriteResult:
    """Replace path and report visibility separately from directory sync."""
    path = Path(path)
    parent = path.parent
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    replaced = False
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        replaced = True
        try:
            directory_sync = fsync_directory(parent)
        except OSError as error:
            raise AtomicWriteAfterReplaceError(error) from error
        return AtomicWriteResult(replacement_visible=True, directory_sync=directory_sync)
    finally:
        if not replaced:
            temporary.unlink(missing_ok=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="atomic-replace-lab-") as directory_name:
        directory = Path(directory_name)
        target = directory / "state.txt"
        target.write_bytes(b"old\n")
        result = atomic_write(target, b"new complete value\n")
        leftovers = sorted(path.name for path in directory.iterdir() if path != target)
        print(f"temporary_directory={directory}")
        print(f"final_bytes={target.read_bytes()!r}")
        print(f"replacement_visible={result.replacement_visible}")
        print(f"directory_sync={result.directory_sync.value}")
        print(f"durability_claim_allowed={result.durability_claim_allowed}")
        print(f"leftover_files={leftovers}")
    print("temporary_directory_removed=True")


if __name__ == "__main__":
    main()
```

<!-- code-sync: ./test_atomic_replace.py -->
```python
import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atomic_replace import (
    AtomicWriteAfterReplaceError,
    AtomicWriteResult,
    DirectorySyncStatus,
    atomic_write,
)


class AtomicReplaceTests(unittest.TestCase):
    def test_replaces_existing_file_with_complete_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            directory = Path(directory_name)
            target = directory / "state.txt"
            target.write_bytes(b"old")
            result = atomic_write(target, b"new payload")
            self.assertEqual(target.read_bytes(), b"new payload")
            self.assertIsInstance(result, AtomicWriteResult)
            self.assertTrue(result.replacement_visible)
            self.assertIn(result.directory_sync, set(DirectorySyncStatus))
            self.assertEqual(
                result.durability_claim_allowed,
                result.directory_sync is DirectorySyncStatus.SYNCED,
            )

    def test_repeated_replacement_leaves_only_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            directory = Path(directory_name)
            target = directory / "state.txt"
            atomic_write(target, b"first")
            atomic_write(target, b"second")
            self.assertEqual(target.read_bytes(), b"second")
            self.assertEqual([path.name for path in directory.iterdir()], ["state.txt"])

    def test_reports_unsupported_directory_sync_after_visible_replace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            target = Path(directory_name) / "state.txt"
            target.write_bytes(b"old")
            with patch(
                "atomic_replace.fsync_directory",
                return_value=DirectorySyncStatus.UNSUPPORTED,
            ):
                result = atomic_write(target, b"new payload")
            self.assertEqual(target.read_bytes(), b"new payload")
            self.assertTrue(result.replacement_visible)
            self.assertEqual(result.directory_sync, DirectorySyncStatus.UNSUPPORTED)
            self.assertFalse(result.durability_claim_allowed)

    def test_error_after_replace_preserves_visible_state_in_exception(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atomic-replace-test-") as directory_name:
            target = Path(directory_name) / "state.txt"
            target.write_bytes(b"old")
            with patch(
                "atomic_replace.fsync_directory",
                side_effect=OSError(errno.EIO, "simulated directory sync failure"),
            ):
                with self.assertRaises(AtomicWriteAfterReplaceError) as raised:
                    atomic_write(target, b"new payload")
            self.assertTrue(raised.exception.replacement_visible)
            self.assertEqual(target.read_bytes(), b"new payload")


if __name__ == "__main__":
    unittest.main()
```

## 读证据

- `final_bytes`、`replacement_visible=True` 和 unittest 证明返回后目标是完整 payload；`leftover_files=[]` 证明正常路径没留下本程序创建的临时文件。
- `directory_sync=synced` 只说这次目录 FD 的 `fsync` 返回成功；`unsupported` 明确表示名字已切换但本实验不允许声称目录更新已持久。其他目录同步错误会抛出 `AtomicWriteAfterReplaceError`，其 `replacement_visible=True` 保留“已替换、持久性未确认”的关键恢复状态。
- `durability_claim_allowed=True` 仍只表示这次文件和目录同步调用都成功返回；它不保证底层硬件/虚拟化链没有违背持久化契约。
- 任一输出都不能模拟断电、控制硬件缓存或证明特定文件系统的崩溃恢复协议。

## 练习与成功标准

1. 在临时目录中启动一个读者线程，反复读目标；写者只在 `b"old"` 和 `b"new"` 之间替换。验证读者不观察到中间 payload，同时说明这仍不验证断电持久性。
2. 阅读本机 `os.replace` 与 `fsync` 所对应的系统文档，记录本机文件系统，不做挂载、卸载或块设备实验。
3. 成功标准：4 个 unittest 通过；演示只修改并清理自建临时目录；能分开解释原子替换、目录同步状态、元数据保留、设备实际持久化，以及“同步报错时名字可能已切换”的恢复边界。

---

**上一站**：[[计算机知识/80-实践/06-计算机系统/04-文件描述符pipe-dup与进程/README|文件描述符、pipe、dup 与进程]] · **返回**：[[计算机知识/80-实践/06-计算机系统/00-计算机系统实践-MOC|计算机系统实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/08-操作系统-课程地图|操作系统 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/02-操作系统原理/03-虚拟内存置换文件系统与崩溃边界|操作系统：虚拟内存、置换与崩溃一致性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
