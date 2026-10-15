---
type: code
stage: 2
aliases: []
sources: []
prerequisites: []
---

# MIMO 设计数值护栏镜像

规范源码见 [numerical_guard.py](numerical_guard.py)，此页只保留同字节镜像。

<!-- code-sync: 控制论/80-实践/12-MIMO反馈与观测器设计/numerical_guard.py -->

```python
#!/usr/bin/env python3
"""Bound local numeric subprocess concurrency and threads; no memory-limit claim."""
import argparse
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
try:
    import fcntl
except ImportError:
    print('unsupported: fcntl unavailable', file=sys.stderr)
    sys.exit(77)


def bounded_int(low, high):
    def parse(value):
        n = int(value)
        if not low <= n <= high:
            raise argparse.ArgumentTypeError(f'must be {low}..{high}')
        return n
    return parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads', type=bounded_int(1, 4), default=1)
    parser.add_argument('--timeout', type=bounded_int(1, 300), default=60)
    parser.add_argument('--lock-timeout', type=bounded_int(1, 60), default=60)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command
    if argv[:1] == ['--']:
        argv = argv[1:]
    if not argv:
        parser.error('provide a command argv after --')
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        print('unsupported: POSIX process groups and no-follow files required', file=sys.stderr)
        return 77
    directory = Path('/private/tmp') / f'wwl-numerical-guard-{os.getuid()}'
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        print('unsafe lock directory: expected owned directory mode 0700', file=sys.stderr)
        return 77
    fds = []
    child = None
    caught = []

    def forward(sig, frame):
        caught.append(sig)
        if child is not None:
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
            except PermissionError:
                print("unsupported: sandbox refused process-group signal", file=sys.stderr)

    old_handlers = {sig: signal.signal(sig, forward) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    try:
        for slot in range(2):
            fd = os.open(directory / f'slot-{slot}.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
                os.close(fd)
                print('unsafe lock file', file=sys.stderr)
                return 77
            fds.append(fd)
        deadline = time.monotonic() + args.lock_timeout
        acquired = None
        while acquired is None:
            if caught:
                return -caught[0]
            for fd in fds:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = fd
                    break
                except BlockingIOError:
                    continue
            if acquired is None:
                if time.monotonic() >= deadline:
                    print('lock wait timed out; command was not started', file=sys.stderr)
                    return 75
                time.sleep(min(0.02, max(0, deadline - time.monotonic())))
        env = os.environ.copy()
        for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'RAYON_NUM_THREADS', 'OMP_THREAD_LIMIT'):
            env[key] = str(args.threads)
        try:
            child = subprocess.Popen(argv, env=env, start_new_session=True)
        except FileNotFoundError:
            print('command executable not found', file=sys.stderr)
            return 127
        except OSError as exc:
            print(f'command could not start: {exc.strerror}', file=sys.stderr)
            return 126
        try:
            result = child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            print(f'command timed out after {args.timeout}s; terminating its process group', file=sys.stderr)
            group_supported = True
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                group_supported = False
            # Give this group a short grace period; kill remaining descendants too.
            time.sleep(0.2)
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                group_supported = False
            if not group_supported:
                print("unsupported: sandbox refused process-group cleanup; descendants unverified", file=sys.stderr)
                if child.poll() is None:
                    child.kill()
                child.wait()
                return 77
            child.wait()
            return 124
        return -caught[0] if caught else result
    finally:
        for fd in fds:
            os.close(fd)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    status = main()
    if status < 0:
        sig = -status
        signal.signal(sig, signal.SIG_DFL)
        os.kill(os.getpid(), sig)
    sys.exit(status)
```
