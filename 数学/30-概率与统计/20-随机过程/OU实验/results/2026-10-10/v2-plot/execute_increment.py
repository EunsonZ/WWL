"""Restore pinned v2 inputs, check plots against archived v1, run a fresh numeric oracle.

Uses NumPy and CairoSVG from the invoking Python. All outputs go to a fresh
external directory; the archived reports and UNKNOWN oracle exit remain unchanged.
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

FIXED_REF = '4bd34d91aa2d34fce10d4dcccf62ce719669296e'
LAB_PATH = '数学/30-概率与统计/20-随机过程/OU实验/'
V2_NAMES = {'ou_lab.py', 'test_ou_lab.py', 'fixed-input.json'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialized(record):
    return json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def safe_relative(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('invalid manifest relative path')
    return path


def prepare(destination, repository):
    package = Path(__file__).resolve().parent
    v1 = package.parent
    repository = Path(subprocess.run(
        ['git', '-C', str(repository), 'rev-parse', '--show-toplevel'],
        capture_output=True, check=True, timeout=60, text=True).stdout.strip()).resolve()
    if destination.is_relative_to(repository):
        raise ValueError('--output must be outside the actual Git root')
    if destination.is_relative_to(v1):
        raise ValueError('--output must be outside the archived package')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('--output must not already exist')
    resolved = subprocess.run(
        ['git', '-C', str(repository), 'rev-parse', '--verify', FIXED_REF + '^{commit}'],
        capture_output=True, check=True, timeout=60, text=True).stdout.strip()
    if resolved != FIXED_REF:
        raise ValueError('fixed commit mismatch')
    inputs = {}
    manifest = json.loads((v1 / 'artifact-hashes.json').read_text())
    copy_map = json.loads((v1 / 'COPY-MAP.json').read_text())
    for name, expected in manifest.items():
        safe_relative(name)
        # The original REPORT.md was renamed only for archival visibility.
        source = v1 / ('REPORT.md.txt' if name == 'REPORT.md' else name)
        data = source.read_bytes()
        entry = next((item for item in copy_map if item['target'].endswith('/' + source.relative_to(v1).as_posix())), None)
        if entry is None or entry['sha256'] != expected or entry['bytes'] != len(data) or digest(data) != expected:
            raise ValueError('v1 archived byte mismatch: ' + name)
        inputs['v1/' + name] = data
    manifest_data = (v1 / 'artifact-hashes.json').read_bytes()
    entry = next(item for item in copy_map if item['target'].endswith('/artifact-hashes.json'))
    if digest(manifest_data) != entry['sha256'] or len(manifest_data) != entry['bytes']:
        raise ValueError('v1 original manifest mismatch')
    inputs['v1/artifact-hashes.json'] = manifest_data
    v2_manifest = json.loads((package / 'artifact-hashes.json').read_text())
    freeze_data = (package / 'SOURCE_FREEZE_V2.json').read_bytes()
    if digest(freeze_data) != v2_manifest['SOURCE_FREEZE_V2.json']:
        raise ValueError('v2 freeze identity mismatch')
    freeze = json.loads(freeze_data)
    if len(freeze['files']) != 3 or {Path(item['path']).name for item in freeze['files']} != V2_NAMES:
        raise ValueError('unexpected v2 fixed input set')
    inputs['v2-plot/SOURCE_FREEZE_V2.json'] = freeze_data
    for item in freeze['files']:
        name = Path(item['path']).name
        if item['path'] != LAB_PATH + name or item['sha256'] != v2_manifest['snapshot/' + name]:
            raise ValueError('v2 fixed input manifest disagreement')
        data = subprocess.run(['git', '-C', str(repository), 'show', FIXED_REF + ':' + item['path']],
                              capture_output=True, check=True, timeout=60).stdout
        if digest(data) != item['sha256']:
            raise ValueError('v2 fixed Git input mismatch: ' + name)
        inputs['v2-plot/snapshot/' + name] = data
        inputs['numeric/snapshot/' + name] = data
    for name in ('PLOT_REVISION.diff', 'render_boundary_previews.py'):
        data = (package / name).read_bytes()
        if digest(data) != v2_manifest[name]:
            raise ValueError('v2 retained helper mismatch: ' + name)
        inputs['v2-plot/' + name] = data
    # This current helper is the same plot check with explicit fresh/v1 paths.
    inputs['v2-plot/plot_checks.py'] = (package / 'plot_checks.py').read_bytes()
    inputs['numeric/independent_oracle.py'] = inputs['v1/independent_oracle.py']
    prepared = {'status': 'prepared', 'restored_from_git_ref': FIXED_REF,
                'actual_git_root': str(repository), 'output': str(destination),
                'copied_input_sha256': {name: digest(data) for name, data in inputs.items()},
                'input_bytes': {name: len(data) for name, data in inputs.items()},
                'v1_numeric_output': 'retained history used for v2 plot comparison',
                'new_numeric_output': 'numeric/output; fresh v2 MC run, separate from archived v1'}
    prepared_text = serialized(prepared)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'fresh-receipt.json').write_text(prepared_text, encoding='utf-8')
    try:
        for name, data in inputs.items():
            target = destination / safe_relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    except Exception as exc:
        failure = {**prepared, 'status': 'failed', 'phase': 'copy', 'error': str(exc)}
        (destination / 'fresh-receipt.json').write_text(serialized(failure), encoding='utf-8')
        raise
    return prepared


def run_child(root, label, arguments, cwd, limit, input_hashes):
    command = [sys.executable, '-B'] + arguments
    requested = {key: '1' for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                    'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}
    requested['PYTHONDONTWRITEBYTECODE'] = '1'
    env = os.environ.copy()
    env.update(requested)
    begin = time.monotonic()
    with (root / (label + '.stdout')).open('xb') as out, (root / (label + '.stderr')).open('xb') as err:
        process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err,
                                   env=env, start_new_session=True)
        timed = False
        while True:
            completed, status, usage = os.wait4(process.pid, os.WNOHANG)
            if completed:
                break
            if time.monotonic() - begin > limit:
                timed = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(.01)
        process.returncode = os.waitstatus_to_exitcode(status)
    after = {name: digest((root / name).read_bytes()) for name in input_hashes}
    record = {'name': label, 'argv': command, 'cwd': str(cwd), 'exit_code': process.returncode,
              'timeout': timed, 'timeout_seconds': limit, 'wall_seconds': time.monotonic() - begin,
              'child_maxrss_native': usage.ru_maxrss, 'maxrss_units': 'bytes on macOS; KiB on Linux',
              'requested_environment': requested, 'input_sha256_after': after}
    (root / (label + '-execution.json')).write_text(serialized(record), encoding='utf-8')
    if after != input_hashes:
        raise RuntimeError('restored input drift: ' + label)
    if process.returncode != 0 or timed:
        raise RuntimeError('child failed: ' + label)
    if label == 'tests':
        stderr = (root / 'tests.stderr').read_text()
        match = re.search(r'Ran (\d+) tests', stderr)
        if not match or int(match.group(1)) != 8 or not stderr.rstrip().endswith('OK'):
            raise RuntimeError('test receipt lacks eight tests and terminal OK')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepared = None
    children = []
    root = args.output
    try:
        if not root.is_absolute():
            raise ValueError('--output must be absolute')
        if root.is_symlink():
            raise ValueError('--output must not be a symbolic link')
        root = root.resolve()
        prepared = prepare(root, args.repo.resolve())
        environment = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
                       'thread_environment_request': 1, 'hard_os_thread_limit': False,
                       'aggregate_memory_peak_observed': False}
        (root / 'environment.json').write_text(serialized(environment), encoding='utf-8')
        hashes = prepared['copied_input_sha256']
        children.append(run_child(root, 'tests', ['-m', 'unittest', 'discover', '-s',
                                   str(root / 'v2-plot/snapshot'), '-p', 'test_ou_lab.py', '-v'], root, 60, hashes))
        children.append(run_child(root, 'plots', [str(root / 'v2-plot/plot_checks.py'),
                                   '--new-dir', str(root / 'v2-plot'), '--v1-dir', str(root / 'v1')], root, 60, hashes))
        children.append(run_child(root, 'previews', [str(root / 'v2-plot/render_boundary_previews.py')], root, 60, hashes))
        children.append(run_child(root, 'fixed', [str(root / 'numeric/snapshot/ou_lab.py'), '--config',
                                   str(root / 'numeric/snapshot/fixed-input.json'), '--output',
                                   str(root / 'numeric/output')], root, 300, hashes))
        children.append(run_child(root, 'oracle', [str(root / 'numeric/independent_oracle.py')], root, 300, hashes))
        plot = json.loads((root / 'v2-plot/plot-checks.json').read_text())
        report = json.loads((root / 'numeric/output/report.json').read_text())
        oracle = json.loads((root / 'numeric/independent-oracle.json').read_text())
        if plot['status'] != 'PASS' or len(plot['plot_checks']) != 3 or not all(c['pass'] for c in plot['plot_checks']):
            raise ValueError('fresh plot checks incomplete')
        if not report['diagnostics_pass'] or oracle['status'] != 'PASS' or oracle['source_imported'] or oracle['author_test_used_as_oracle']:
            raise ValueError('fresh numeric/oracle result rejected')
        if len(oracle['checks']) != 94 or not all(c['pass'] for c in oracle['checks']) or oracle['trace_rows_checked'] != 992:
            raise ValueError('fresh independent oracle incomplete')
        final = {**prepared, 'status': 'completed', 'exit_code': 0, 'children': children,
                 'tests': 8, 'plot_boundaries': 3, 'audit_previews': 2, 'oracle_checks': 94,
                 'trace_rows_checked': 992,
                 'visual_observation': 'not performed by driver; inspect fresh PNG separately'}
    except Exception as exc:
        final = {**(prepared or {}), 'status': 'failed', 'phase': 'execution' if prepared else 'preparation',
                 'error': str(exc), 'completed_children': children}
        text = serialized(final)
        if prepared:
            (root / 'fresh-receipt.json').write_text(text, encoding='utf-8')
        sys.stderr.write(text)
        return 1
    text = serialized(final)
    (root / 'fresh-receipt.json').write_text(text, encoding='utf-8')
    print(text, end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
