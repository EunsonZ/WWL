#!/usr/bin/env python3
"""Run local teaching tests without network access or elevated privileges.
Build products live only in a TemporaryDirectory. Missing optional toolchains
are reported as SKIP, never as PASS. Python 3.11+ is recommended.
"""
from __future__ import annotations
import argparse
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent


def vault_root(start: Path) -> Path:
    """Locate the vault by its contract marker, independent of lab placement."""
    for candidate in (start, *start.parents):
        if (candidate / 'AGENTS.md').is_file():
            return candidate
    raise RuntimeError(f'Cannot locate vault root from {start}')


ROOT = vault_root(HERE)


def default_output_dir() -> Path:
    stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    return ROOT / 'Logs/运行/integration-labs' / stamp / '计算机知识'

def run(command: list[str], cwd: Path, timeout: int = 60) -> dict:
    try:
        p = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {'command': command, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'command': command, 'returncode': -1, 'stdout': '', 'stderr': str(exc)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path,
                        default=default_output_dir()/'integration_test_results.json',
                        help='Independent report path; defaults below Logs/运行, never historical _meta.')
    args = parser.parse_args()
    sys.path.insert(0, str(HERE))
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_core.py')
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    data = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'environment': {'python': sys.version, 'platform': platform.platform()},
            'python': {'run': result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
                       'skipped':len(result.skipped), 'status':'PASS' if result.wasSuccessful() else 'FAIL', 'log':stream.getvalue()},
            'programs': []}
    configs = [
        ('C11 vector', ['cc','gcc','clang'], ['-std=c11','-Wall','-Wextra','-Wpedantic','-Werror','-O1',str(HERE/'vector.c')], []),
        ('C++20 RAII', ['c++','g++','clang++'], ['-std=c++20','-Wall','-Wextra','-Wpedantic','-Werror','-O1',str(HERE/'raii.cpp')], []),
        ('Rust standard-library tests', ['rustc'], ['--edition=2021','--test',str(HERE/'rust_tests.rs')], ['--test-threads=1']),
    ]
    with tempfile.TemporaryDirectory(prefix='kb-build-') as temp:
        build = Path(temp)
        for index, (name, tools, flags, runtime_flags) in enumerate(configs):
            tool = next((shutil.which(t) for t in tools if shutil.which(t)), None)
            entry = {'name': name}
            if not tool:
                entry.update(status='SKIP', reason='optional compiler not installed')
            else:
                entry['version'] = run([tool,'--version'], build, 10)
                binary = build/f'program_{index}'
                entry['compile'] = run([tool,*flags,'-o',str(binary)], build, 90)
                if entry['compile']['returncode']:
                    entry['status'] = 'FAIL'
                else:
                    entry['execute'] = run([str(binary),*runtime_flags], build, 30)
                    entry['status'] = 'PASS' if entry['execute']['returncode'] == 0 else 'FAIL'
            data['programs'].append(entry)
        tsc, node = shutil.which('tsc'), shutil.which('node')
        entry = {'name':'TypeScript strict compilation and runtime validation'}
        if not tsc or not node:
            entry.update(status='SKIP', reason='requires local tsc and node; script never installs packages')
        else:
            entry['version'] = run([tsc,'--version'], build, 10)
            entry['compile'] = run([tsc,'--strict','--noUncheckedIndexedAccess','--exactOptionalPropertyTypes',
                '--target','ES2022','--module','commonjs','--lib','ES2022,DOM','--outDir',str(build),str(HERE/'boundary.ts')],build,90)
            if entry['compile']['returncode']:
                entry['status']='FAIL'
            else:
                entry['execute']=run([node,str(build/'boundary.js')],build,30)
                entry['status']='PASS' if entry['execute']['returncode']==0 else 'FAIL'
        data['programs'].append(entry)
    data['overall'] = 'PASS' if result.wasSuccessful() and all(e['status'] != 'FAIL' for e in data['programs']) else 'FAIL'
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(stream.getvalue())
    print(json.dumps({'overall':data['overall'],'python':{k:v for k,v in data['python'].items() if k!='log'},
                      'programs':[{k:e[k] for k in ('name','status','reason') if k in e} for e in data['programs']],
                      'report':str(args.report)},ensure_ascii=False,indent=2))
    return 0 if data['overall']=='PASS' else 1
if __name__ == '__main__': raise SystemExit(main())
