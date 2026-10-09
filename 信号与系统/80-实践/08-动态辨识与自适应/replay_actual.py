"""Portable POSIX replay interface. Static AST/control-flow review only: NOTRUN.
Recorded actual executions remain in results/2026-10-10-v2; this driver is new.
Only a fresh directory receives newly executed outputs; no old result is copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'posix' or not hasattr(os, 'wait4'):
        raise RuntimeError('POSIX wait4 required; macOS/Linux only')
    here = Path(__file__).resolve().parent
    package = here/'results/2026-10-10-v2'
    guard = json.loads((here/'replay-input-hashes.json').read_text())
    for relative, expected in guard.items():
        source = package/relative
        if source.is_symlink() or sha(source) != expected:
            raise ValueError('frozen replay input mismatch: '+relative)
    freeze = json.loads((package/'SOURCE_FREEZE.json').read_text())
    for row in freeze['files']:
        if guard['snapshot/'+row['snapshot']] != row['sha256']:
            raise ValueError('source freeze mismatch: '+row['snapshot'])
    dest = args.output.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    shutil.copytree(package/'snapshot', dest/'snapshot')
    for relative in guard:
        if not relative.startswith('snapshot/'):
            shutil.copy2(package/relative, dest/relative)
    overrides = {k: '1' for k in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
        'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS']}
    overrides['PYTHONDONTWRITEBYTECODE'] = '1'
    env = os.environ.copy()
    env.update(overrides)
    (dest/'environment.json').write_text(json.dumps({
        'python': sys.version, 'executable': sys.executable,
        'platform': platform.platform(), 'machine': platform.machine(),
        'requested_environment': overrides, 'hard_os_thread_limit': False,
        'aggregate_memory_peak_observed': False,
        'driver_sha256': sha(here/'replay_actual.py'),
        'guard_sha256': sha(here/'replay-input-hashes.json')}, indent=2)+'\n')
    records = []

    def verify_inputs():
        for relative, expected in guard.items():
            if sha(dest/relative) != expected:
                raise RuntimeError('replay input drift: '+relative)

    def run(label, argv, cwd, limit):
        verify_inputs()
        command = [sys.executable, '-B']+argv
        start = time.monotonic()
        pid = os.fork()
        if pid == 0:
            try:
                os.chdir(cwd)
                for fd, suffix in [(1, 'stdout'), (2, 'stderr')]:
                    handle = os.open(dest/(label+'.'+suffix),
                        os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o644)
                    os.dup2(handle, fd)
                    os.close(handle)
                os.execve(sys.executable, command, env)
            except BaseException:
                os._exit(127)
        timed_out = False
        while True:
            completed, status, usage = os.wait4(pid, os.WNOHANG)
            if completed:
                break
            if time.monotonic()-start > limit:
                timed_out = True
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(pid, 0)
                break
            time.sleep(.01)
        record = {'label': label, 'command': command, 'cwd': str(cwd),
            'exit_code': os.waitstatus_to_exitcode(status), 'timeout': timed_out,
            'timeout_seconds': limit, 'elapsed_seconds': time.monotonic()-start,
            'child_maxrss_native': usage.ru_maxrss,
            'maxrss_units': 'bytes on macOS; KiB on Linux'}
        records.append(record)
        (dest/'process-observations.json').write_text(json.dumps(records, indent=2)+'\n')
        verify_inputs()
        if timed_out or record['exit_code'] != 0:
            raise RuntimeError('child failed: '+label)

    run('analytic-expected', ['analytic_expected.py'], dest, 60)
    run('suite-preflight', ['-m', 'unittest', '-v', 'test_identification_lab.py'], dest/'snapshot', 60)
    run('standard', ['identification_lab.py', '--output', str(dest/'output')], dest/'snapshot', 300)
    run('deterministic-probes', [str(dest/'source_probes.py')], dest/'snapshot', 60)
    run('independent-oracle', ['independent_oracle.py'], dest, 300)
    run('additional-analytic', ['additional_analytic.py'], dest, 60)
    for relative in ['analytic-expected.json', 'independent-oracle.json', 'additional-analytic-checks.json']:
        if json.loads((dest/relative).read_text()).get('status') != 'PASS':
            raise RuntimeError('oracle result not PASS: '+relative)
    print(json.dumps({'output': str(dest), 'six_children_completed': True,
        'independent_oracle_status': 'PASS', 'visual_replayed': False}))


if __name__ == '__main__':
    main()
