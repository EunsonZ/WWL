"""Future reproduction in a new directory; this reader helper is NOTRUN."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', required=True, help='absolute, nonexistent output directory')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    work = Path(args.work)
    require(work.is_absolute(), '--work must be absolute')
    require(not work.exists(), '--work must not exist; never reuse historical outputs')
    manifest = json.loads((here / 'original/artifact-hashes.json').read_text())
    # Validate original evidence, including the unchanged report renamed to text.
    for name, record in manifest.items():
        renamed = 'REPORT.md.txt' if name == 'REPORT.md' else name
        data = (here / 'original' / renamed).read_bytes()
        require(len(data) == record['bytes'], 'original byte count: ' + name)
        require(hashlib.sha256(data).hexdigest() == record['sha256'], 'original SHA: ' + name)
    selected = ['snapshot/code/affine_exact.py', 'snapshot/code/examples.py',
                'snapshot/code/fixed-inputs.json', 'snapshot/code/independent-expected.json',
                'api_probe.py', 'independent_oracle.py', 'invalid-fixed-bool-point.json']
    work.mkdir(parents=True, exist_ok=False)
    for name in selected:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(here / 'original' / name, target)
    # No original stdout, execution record, oracle result or capture.py is copied.
    (work / 'environment.json').write_text(json.dumps({
        'python': sys.version, 'executable': sys.executable,
        'platform': platform.platform(), 'machine': platform.machine(),
        'child_timeout_seconds': 60, 'aggregate_memory_peak_observed': False,
        'resource_peak_measured_by_this_helper': False,
        'copied_inputs': {name: manifest[name]['sha256'] for name in selected}
    }, indent=2))
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    def run(label, arguments, cwd, expected_exit=0, expected_error=None):
        cmd = [sys.executable, '-B'] + arguments
        stdout_path = work / (label + '-stdout.json')
        stderr_path = work / (label + '-stderr.txt')
        start = time.time()
        with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            try:
                child = subprocess.run(cmd, cwd=cwd, env=env, stdout=stdout,
                                       stderr=stderr, timeout=60, check=False)
                status, code = 'completed', child.returncode
            except subprocess.TimeoutExpired:
                status, code = 'timeout', None
        record = {'command': cmd, 'cwd': str(cwd), 'status': status,
                  'exit_code': code, 'expected_exit_code': expected_exit,
                  'start_unix': start, 'end_unix': time.time(),
                  'elapsed_seconds': time.time() - start, 'timeout_seconds': 60,
                  'stdout_sha256': hashlib.sha256(stdout_path.read_bytes()).hexdigest(),
                  'stderr_sha256': hashlib.sha256(stderr_path.read_bytes()).hexdigest()}
        (work / (label + '-execution.json')).write_text(json.dumps(record, indent=2))
        require(status == 'completed' and code == expected_exit,
                label + ': inspect execution.json and raw stderr before proceeding')
        if expected_error is None:
            require(stderr_path.read_bytes() == b'', label + ': unexpected stderr')
        else:
            require(stdout_path.read_bytes() == b'', label + ': rejection printed success output')
            require(expected_error in stderr_path.read_text(), label + ': wrong rejection reason')

    run('fixed-cli', ['code/affine_exact.py', '--input', 'code/fixed-inputs.json'], work / 'snapshot')
    run('examples-cli', ['code/examples.py'], work / 'snapshot')
    require((work / 'fixed-cli-stdout.json').read_bytes() ==
            (work / 'examples-cli-stdout.json').read_bytes(), 'fixed CLI bytes differ')
    run('api-probe', ['api_probe.py'], work)
    observations = json.loads((work / 'api-probe-stdout.json').read_text())['observations']
    require(len(observations) == 90, 'API observation count changed')
    require(sum(row['expected_kind'] == 'ValueError' for row in observations) == 63,
            'API expected-rejection count changed')
    run('fixed-reject', ['snapshot/code/affine_exact.py', '--input', 'invalid-fixed-bool-point.json'],
        work, expected_exit=1, expected_error='ValueError: integer fixed points required')
    run('oracle-r2', ['independent_oracle.py'], work)
    result = json.loads((work / 'oracle-results.json').read_text())
    require(result['checks_total'] == 288 and result['all_match'] is True
            and result['failed_checks'] == [] and result['business_api_imported'] is False,
            'independent oracle did not satisfy the published finite contract')
    for name in selected:
        require(hashlib.sha256((work / name).read_bytes()).hexdigest() == manifest[name]['sha256'],
                'copied source/input changed: ' + name)
    (work / 'REBUILD-COMPLETE.json').write_text(json.dumps({
        'completed': True, 'checks_total': 288, 'api_observations': 90,
        'expected_rejections': 63, 'natural_2001_step_witness_run': False,
        'theory_or_human_learning_certified': False
    }, indent=2))
    print('New finite run completed; inspect raw records in ' + str(work))


if __name__ == '__main__':
    main()
