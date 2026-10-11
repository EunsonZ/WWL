"""Restore both fixed IIR versions and run a fresh final numeric protocol.

The original V2 failure and V2R1 REUSED_EXACT_SOURCE remain historical facts.
Python 3.10+ POSIX standard library; no diagram renderer or device access.
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

FIXED_REF = 'ce0a1b02bc73499ea7eaf04dfab5e0cf6ca94eb3'
PACKAGE_PATH = '信号与系统/80-实践/06-IIR规格与实现/results/2026-10-10/v2r1/'
LAB_PATH = '信号与系统/80-实践/06-IIR规格与实现/'
VERSIONS = [('snapshot/candidate-v2', 'source-manifest.json'),
            ('snapshot-r1/candidate-v2r1', 'source-manifest-r1.json')]
GIT_NAMES = {LAB_PATH + 'iir_lab.py', LAB_PATH + 'test_iir_lab.py'}


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
    repository = Path(subprocess.run(['git', '-C', str(repository), 'rev-parse', '--show-toplevel'],
                      capture_output=True, check=True, timeout=60, text=True).stdout.strip()).resolve()
    if destination.is_relative_to(repository):
        raise ValueError('--output must be outside the actual Git root')
    if destination.is_relative_to(package):
        raise ValueError('--output must be outside the archived package')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('--output must not already exist')
    ref = subprocess.run(['git', '-C', str(repository), 'rev-parse', '--verify', FIXED_REF + '^{commit}'],
                         capture_output=True, check=True, timeout=60, text=True).stdout.strip()
    if ref != FIXED_REF:
        raise ValueError('fixed commit mismatch')
    artifacts = json.loads((package / 'artifact-manifest.json').read_text())
    recorded = {entry['path']: entry for entry in artifacts}
    if len(recorded) != len(artifacts):
        raise ValueError('duplicate historical artifact entry')
    inputs = {}

    def retained(name, archived_name=None):
        entry = recorded[name]
        data = (package / safe_relative(archived_name or name)).read_bytes()
        if digest(data) != entry['sha256'] or len(data) != entry['bytes']:
            raise ValueError('retained historical input mismatch: ' + name)
        return data

    versions = {}
    for folder, name in VERSIONS:
        data = retained(name)
        inputs[name] = data
        manifest = json.loads(data)
        entries = manifest['files']
        paths = {entry['path'] for entry in entries}
        if len(entries) != 27 or len(paths) != 27 or not GIT_NAMES.issubset(paths):
            raise ValueError('incomplete version manifest: ' + name)
        versions[folder] = {entry['path']: entry for entry in entries}
        for entry in entries:
            relative = folder + '/' + entry['path']
            safe_relative(relative)
            portable = relative + '.txt' if relative.endswith('.md') else relative
            # Restore three redundant executable inputs from immutable Git.
            # The distinct old failing V2 test remains an archived input.
            from_git = entry['path'] == LAB_PATH + 'iir_lab.py' or (folder == VERSIONS[1][0] and entry['path'] == LAB_PATH + 'test_iir_lab.py')
            if from_git:
                data = subprocess.run(['git', '-C', str(repository), 'show', FIXED_REF + ':' + PACKAGE_PATH + relative],
                                      capture_output=True, check=True, timeout=60).stdout
            else:
                data = (package / safe_relative(portable)).read_bytes()
            if digest(data) != entry['sha256'] or len(data) != entry['bytes']:
                raise ValueError('fixed version input mismatch: ' + relative)
            inputs[relative] = data
    v2, r1 = [versions[folder] for folder, _ in VERSIONS]
    if set(v2) != set(r1):
        raise ValueError('version target sets differ')
    differences = [name for name in v2 if v2[name]['sha256'] != r1[name]['sha256']]
    if set(differences) != {LAB_PATH + 'test_iir_lab.py', LAB_PATH + '04-源码与验证.md'}:
        raise ValueError('unexpected version differences')
    source_name = LAB_PATH + 'iir_lab.py'
    if inputs[VERSIONS[0][0] + '/' + source_name] != inputs[VERSIONS[1][0] + '/' + source_name]:
        raise ValueError('production source differs between V2 and V2R1')
    for name in ('preflight.py', 'executor_oracle.py'):
        inputs[name] = retained(name)
    prepared = {'status': 'prepared', 'output': str(destination), 'actual_git_root': str(repository),
                'restored_from_git_ref': FIXED_REF,
                'copied_input_sha256': {name: digest(data) for name, data in inputs.items()},
                'input_bytes': {name: len(data) for name, data in inputs.items()},
                'version_comparison': {'targets_per_version': 27, 'same': 25,
                                       'different_paths': differences, 'production_source_bytes_same': True},
                'run_scope': 'New final V2R1 test suite and new same-source CLI/oracle; old V2 failed test is retained, not run as a success requirement.'}
    text = serialized(prepared)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'fresh-receipt.json').write_text(text, encoding='utf-8')
    try:
        for name, data in inputs.items():
            target = destination / safe_relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name in ('logs', 'raw', 'tmp'):
            (destination / name).mkdir()
    except Exception as exc:
        failure = {**prepared, 'status': 'failed', 'phase': 'copy', 'error': str(exc)}
        (destination / 'fresh-receipt.json').write_text(serialized(failure), encoding='utf-8')
        raise
    return prepared


def run_child(root, name, arguments, cwd, limit, input_hashes):
    command = [sys.executable, '-B'] + arguments
    requested = {key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                    'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')}
    requested.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(root / 'tmp'))
    env = os.environ.copy()
    env.update(requested)
    start = time.monotonic()
    with (root / 'logs' / (name + '.stdout')).open('xb') as out, (root / 'logs' / (name + '.stderr')).open('xb') as err:
        process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err, env=env, start_new_session=True)
        timed = False
        while True:
            completed, status, usage = os.wait4(process.pid, os.WNOHANG)
            if completed:
                break
            if time.monotonic() - start > limit:
                timed = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(.01)
        process.returncode = os.waitstatus_to_exitcode(status)
    after = {name: digest((root / name).read_bytes()) for name in input_hashes}
    record = {'name': name, 'argv': command, 'cwd': str(cwd), 'exit_code': process.returncode,
              'timeout': timed, 'timeout_seconds': limit, 'wall_seconds': time.monotonic() - start,
              'requested_environment': requested, 'child_maxrss_native': usage.ru_maxrss,
              'maxrss_units': 'bytes on macOS; KiB on Linux', 'input_sha256_after': after}
    (root / 'logs' / (name + '-execution.json')).write_text(serialized(record), encoding='utf-8')
    if after != input_hashes:
        raise RuntimeError('restored input drift: ' + name)
    if process.returncode != 0 or timed:
        raise RuntimeError('child failed: ' + name)
    if name == 'iir-tests-r1':
        stderr = (root / 'logs/iir-tests-r1.stderr').read_text()
        match = re.search(r'Ran (\d+) tests', stderr)
        if not match or int(match.group(1)) != 12 or not stderr.rstrip().endswith('OK'):
            raise RuntimeError('suite receipt lacks twelve tests and terminal OK')
    return record


def check_results(root):
    preflight = json.loads((root / 'logs/bounded-preflight.stdout').read_text())['bounded_preflight']
    if set(preflight) != {'binary64', 'binary32'} or any(model['certified'] or not all(b['partition_covers_closed_domain'] for b in model['bands'].values()) for model in preflight.values()):
        raise ValueError('bounded preflight did not preserve uncertified complete partitions')
    report = json.loads((root / 'raw/iir-cli/results.json').read_text())
    oracle = json.loads((root / 'logs/executor-oracle.stdout').read_text())
    expected_models = {'binary64_sos', 'binary32_sos'}
    if set(report['machine_certificates']) != expected_models:
        raise ValueError('fresh certificate model set differs')
    if any(cert['status'] != 'certified' or cert['certified'] is not True for cert in report['machine_certificates'].values()):
        raise ValueError('fresh closed-band certificate incomplete')
    if oracle['status'] != 'PASS' or {model['model'] for model in oracle['models']} != expected_models:
        raise ValueError('fresh independent Fraction oracle incomplete')
    if oracle['results_sha256'] != digest((root / 'raw/iir-cli/results.json').read_bytes()):
        raise ValueError('oracle is not bound to new CLI output')
    cells = sum(band['all_cells'] for model in oracle['models'] for band in model['bands'].values())
    points = sum(band['selected_cells_rational_points'] for model in oracle['models'] for band in model['bands'].values())
    if cells != 7490 or points != 456 or len(oracle['rejections']) != 4:
        raise ValueError('fresh independent oracle coverage incomplete')
    if oracle['wide_fixture']['returned'] is not None or oracle['resource_false']['certified'] is not False:
        raise ValueError('fresh conservative or resource rejection lost')
    return {'accepted_cells': cells, 'independent_rational_points': points,
            'fraction_oracle': 'PASS; supplementary operation checks import frozen public APIs',
            'diagram_rendering': 'not automatic; restored SVG sources remain analytic diagrams, not numeric output plots'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output
    prepared = None
    children = []
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
        v2 = root / VERSIONS[0][0] / LAB_PATH
        r1 = root / VERSIONS[1][0] / LAB_PATH
        children.append(run_child(root, 'bounded-preflight', [str(root / 'preflight.py')], root, 60, hashes))
        children.append(run_child(root, 'iir-cli', ['iir_lab.py', '--output', str(root / 'raw/iir-cli')], v2, 300, hashes))
        children.append(run_child(root, 'iir-tests-r1', ['-m', 'unittest', '-v', 'test_iir_lab.py'], r1, 60, hashes))
        children.append(run_child(root, 'executor-oracle', [str(root / 'executor_oracle.py')], root, 300, hashes))
        observations = check_results(root)
        final = {**prepared, 'status': 'completed', 'exit_code': 0, 'children': children,
                 'observations': observations, 'historical_r1_cli_reuse': 'unchanged original record; this receipt describes a new CLI execution'}
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
