"""Restore fixed inputs into a fresh external directory, then run five numeric children.

The archived execution and static-only REPLAY.md.txt remain historical records.
POSIX macOS/Linux, Python 3.10+ standard library; no diagram rendering.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time

FIXED_REF = '03f07ed66d478db56b8d60fdaade19fed7f02bb2'
LAB_PATH = '信号与系统/80-实践/07-Wiener估计与预测/'
GIT_INPUTS = ('wiener_lab.py', 'test_wiener_lab.py',
              '04-源码与验证.md', 'assets/information-windows.svg')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def serialized(record):
    return json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def prepare(destination, repository):
    package = Path(__file__).resolve().parent
    # A subdirectory is accepted, but containment always uses the actual Git root.
    repository = Path(subprocess.run(
        ['git', '-C', str(repository), 'rev-parse', '--show-toplevel'],
        capture_output=True, check=True, timeout=60, text=True).stdout.strip()).resolve()
    if destination.is_relative_to(repository):
        raise ValueError('--output must be outside the actual Git root')
    if destination.is_relative_to(package) or destination == package:
        raise ValueError('--output must be outside the replay package')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('--output must not already exist')
    resolved_ref = subprocess.run(
        ['git', '-C', str(repository), 'rev-parse', '--verify', FIXED_REF + '^{commit}'],
        capture_output=True, check=True, timeout=60, text=True).stdout.strip()
    if resolved_ref != FIXED_REF:
        raise ValueError('fixed commit mismatch')
    receipt = json.loads((package / 'copy-receipt.json').read_text())
    entries = {e['original_relative']: e for e in receipt['mapping']}
    if len(entries) != len(receipt['mapping']):
        raise ValueError('duplicate historical copy receipt input')
    inputs = {}

    def retained(name):
        entry = entries[name]
        data = (package / name).read_bytes()
        if entry['copied_relative'] != name or len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('historical receipt mismatch: ' + name)
        return data

    identity = json.loads(retained('identity.json'))
    expected_names = set(GIT_INPUTS) | {'README.md'}
    if set(identity['snapshot']) != expected_names:
        raise ValueError('unexpected snapshot input set')
    if identity['before'] != identity['snapshot'] or identity['after_copy'] != identity['snapshot']:
        raise ValueError('historical snapshot identity disagreement')
    for name, expected_hash in identity['snapshot'].items():
        relative = 'snapshot/' + name
        entry = entries[relative]
        if entry['copied_relative'] != relative or entry['sha256'] != expected_hash:
            raise ValueError('snapshot receipt disagreement: ' + name)
        if name in GIT_INPUTS:
            data = subprocess.run(
                ['git', '-C', str(repository), 'show', FIXED_REF + ':' + LAB_PATH + name],
                capture_output=True, check=True, timeout=60).stdout
        else:
            data = retained(relative)  # The original README differs from today's page.
        if len(data) != entry['bytes'] or digest(data) != expected_hash:
            raise ValueError('fixed input byte mismatch: ' + name)
        inputs[relative] = data
    expected_tools = json.loads(retained('replay-input-hashes.json'))
    if set(expected_tools) != {'fixed-inputs.json', 'expected-before-run.json',
                               'independent_oracle.py', 'csv_oracle.py'}:
        raise ValueError('unexpected replay tool set')
    for name, expected_hash in expected_tools.items():
        data = retained(name)
        if digest(data) != expected_hash:
            raise ValueError('replay tool mismatch: ' + name)
        inputs[name] = data
    cfg = json.loads(inputs['fixed-inputs.json'])
    if cfg['preflight'] != {'repeats': 1, 'train': 128, 'test': 256} or cfg['standard'] != {'repeats': 16, 'train': 4096, 'test': 8192}:
        raise ValueError('fixed numeric settings mismatch')
    prepared = {'status': 'prepared', 'restored_from_git_ref': FIXED_REF,
                'actual_git_root': str(repository), 'output': str(destination),
                'copied_input_sha256': {name: digest(data) for name, data in inputs.items()}}
    # Serialize and validate every input before creating the destination.
    prepared_text = serialized(prepared)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'fresh-receipt.json').write_text(prepared_text, encoding='utf-8')
    try:
        for name, data in inputs.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    except Exception as exc:
        failure = {**prepared, 'status': 'failed', 'phase': 'copy', 'error': str(exc)}
        (destination / 'fresh-receipt.json').write_text(serialized(failure), encoding='utf-8')
        raise
    return identity, cfg, prepared


def run_child(destination, identity, label, argv, cwd, limit):
    cmd = [sys.executable, '-B'] + argv
    overrides = {key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}
    overrides.update(PYTHONDONTWRITEBYTECODE='1', WWL_CHILD_TIMEOUT_SECONDS=str(limit))
    env = os.environ.copy()
    env.update(overrides)
    # Reserve logs before spawning so startup/exec failures also have evidence.
    handles = [os.open(destination / (label + '-' + suffix),
                       os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
               for suffix in ('stdout.txt', 'stderr.txt')]
    begin = time.monotonic()
    pid = os.fork()
    if pid == 0:
        try:
            os.chdir(cwd)
            for fd, handle in zip((1, 2), handles):
                os.dup2(handle, fd)
                os.close(handle)
            os.execve(sys.executable, cmd, env)
        except BaseException as exc:
            os.write(2, ('child startup failed: ' + str(exc) + '\n').encode())
            os._exit(127)
    for handle in handles:
        os.close(handle)
    timedout = False
    while True:
        completed, status, usage = os.wait4(pid, os.WNOHANG)
        if completed:
            break
        if time.monotonic() - begin > limit:
            timedout = True
            os.kill(pid, signal.SIGKILL)
            _, status, usage = os.wait4(pid, 0)
            break
        time.sleep(.01)
    record = {'command': cmd, 'cwd': str(cwd), 'elapsed_seconds': time.monotonic() - begin,
              'exit_code': os.waitstatus_to_exitcode(status), 'timeout': timedout,
              'timeout_seconds': limit, 'requested_environment': overrides,
              'child_maxrss_native': usage.ru_maxrss,
              'maxrss_units': 'bytes on macOS; KiB on Linux',
              'source_after': {name: sha(destination / 'snapshot' / name)
                               for name in identity['snapshot']}}
    (destination / (label + '-execution.json')).write_text(serialized(record), encoding='utf-8')
    if record['source_after'] != identity['snapshot']:
        raise RuntimeError('snapshot drift: ' + label)
    if record['exit_code'] != 0 or timedout:
        raise RuntimeError('child failed: ' + label)
    if label == 'suite':
        stderr = (destination / 'suite-stderr.txt').read_text()
        match = re.search(r'Ran (\d+) tests', stderr)
        if not match or int(match.group(1)) != 8 or not stderr.rstrip().endswith('OK'):
            raise RuntimeError('suite receipt lacks eight tests and terminal OK')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo', type=Path, required=True,
                        help='local WWL Git repository containing the pinned commit')
    args = parser.parse_args()
    destination = args.output
    children = []
    prepared = None
    try:
        if not args.output.is_absolute():
            raise ValueError('--output must be absolute')
        # Check the supplied final node before resolve() can erase a dangling link.
        if args.output.is_symlink():
            raise ValueError('--output must not be a symbolic link')
        destination = args.output.resolve()
        identity, cfg, prepared = prepare(destination, args.repo.resolve())
        overrides = {key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                     'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}
        overrides['PYTHONDONTWRITEBYTECODE'] = '1'
        environment = {'python': sys.version, 'platform': platform.platform(),
                       'machine': platform.machine(), 'executable': sys.executable,
                       'requested_environment': overrides, 'hard_os_thread_limit': False,
                       'aggregate_memory_peak_observed': False}
        (destination / 'environment.json').write_text(serialized(environment), encoding='utf-8')
        children.append(run_child(destination, identity, 'suite',
                                  ['-m', 'unittest', '-v', 'test_wiener_lab.py'], destination / 'snapshot', 60))
        for label, limit in [('preflight', 60), ('standard', 300)]:
            settings = cfg[label]
            children.append(run_child(destination, identity, label,
                ['wiener_lab.py', '--output', str(destination / label), '--repeats', str(settings['repeats']),
                 '--train', str(settings['train']), '--test', str(settings['test'])], destination / 'snapshot', limit))
        children.append(run_child(destination, identity, 'oracle', ['independent_oracle.py'], destination, 300))
        children.append(run_child(destination, identity, 'csv-oracle', ['csv_oracle.py'], destination, 60))
        for name in ('oracle-results.json', 'csv-oracle-results.json'):
            result = json.loads((destination / name).read_text())
            if not result['all_match'] or result['failed_checks']:
                raise RuntimeError('oracle mismatch: ' + name)
        final = {**prepared, 'status': 'completed', 'exit_code': 0, 'children': children,
                 'five_children_completed': True, 'independent_oracles_match': True,
                 'diagram_rendering': 'not replayed; record fresh renderer and visual evidence separately'}
    except Exception as exc:
        final = {**(prepared or {}), 'status': 'failed', 'phase': 'execution' if prepared else 'preparation',
                 'error': str(exc), 'completed_children': children}
        # Refused preparations leave the requested path untouched; their receipt is stderr.
        text = serialized(final)
        if prepared:
            (destination / 'fresh-receipt.json').write_text(text, encoding='utf-8')
        sys.stderr.write(text)
        return 1
    text = serialized(final)
    (destination / 'fresh-receipt.json').write_text(text, encoding='utf-8')
    print(text, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
