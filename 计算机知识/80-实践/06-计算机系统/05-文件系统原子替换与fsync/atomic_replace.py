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
