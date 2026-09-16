#!/usr/bin/env python3
"""Run the explicitly reviewed round-four labs, never arbitrary vault code.

Uses temporary build files and no network, installations, root privileges or
production services. Requires Python 3.11+. Optional compilers are reported as
SKIP. Do not use Python -O: the examples deliberately use assertions.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
from datetime import datetime
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
def vault_root(start: Path) -> Path:
    """Locate the vault by its contract marker, independent of lab placement."""
    for candidate in (start, *start.parents):
        if (candidate / 'AGENTS.md').is_file():
            return candidate
    raise RuntimeError(f'Cannot locate vault root from {start}')


ROOT = vault_root(BASE)


def default_output_dir() -> Path:
    stamp = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')
    return ROOT / 'Logs/运行/round4-labs' / stamp / '计算机知识'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=default_output_dir() / 'lab_results.json',
                        help='Independent report path; defaults below Logs/运行, never historical _meta.')
    args = parser.parse_args()
    if not __debug__:
        parser.error('Run without -O; assertions must be enabled.')
    results: list[dict] = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

    def run(name: str, command: list, scope: str, reject: str | None = None) -> bool:
        start = time.monotonic()
        cmd = [str(x) for x in command]
        record = {'name': name, 'command': cmd, 'scope': scope}
        try:
            proc = subprocess.run(cmd, cwd=BASE, env=env, capture_output=True,
                                  text=True, timeout=40)
            ok = proc.returncode == 0
            if reject is not None:
                ok = proc.returncode != 0 and reject.lower() in proc.stderr.lower()
            record.update(returncode=proc.returncode, stdout=proc.stdout,
                          stderr=proc.stderr, status='PASS' if ok else 'FAIL')
            counts = re.findall(r'Ran (\d+) tests? in', proc.stderr)
            if counts:
                record['unittest_cases'] = int(counts[-1])
        except (OSError, subprocess.TimeoutExpired) as exc:
            record.update(status='FAIL', error=str(exc))
        record['seconds'] = round(time.monotonic() - start, 4)
        results.append(record)
        print(record['status'], name, flush=True)
        if record['status'] == 'FAIL':
            print(record.get('stderr', record.get('error', '')), flush=True)
        return record['status'] == 'PASS'

    def skip(name: str, reason: str) -> None:
        results.append({'name': name, 'status': 'SKIP', 'reason': reason})
        print('SKIP', name, reason, flush=True)

    tools = {}
    for tool in ('cc', 'g++', 'node', 'tsc', 'rustc', 'bash'):
        executable = shutil.which(tool)
        if executable is None:
            tools[tool] = {'available': False}
            continue
        proc = subprocess.run([executable, '--version'], capture_output=True,
                              text=True, timeout=10)
        tools[tool] = {'path': executable,
                       'version': (proc.stdout or proc.stderr).splitlines()[0]}

    groups = {
        'structures_algorithms': 'List/brute-force/min-cut oracles; fixed seeds; bounded exhaustive cases.',
        'compiler': 'Generated SLR table, enumerated words, liveness fixed point and finite type unification.',
        'systems': 'Explicit numeric/toy models plus safe temporary-file, pipe, FD and epoll operations; no power cut or real network.',
        'database_crosslayer': 'FD derivations and in-memory SQLite; toy concurrency/recovery and outbox failure points; not PostgreSQL execution.',
        'python': 'Actual descriptors, C3, circular-import partial state, TaskGroup cancellation and bounded queues.'
    }
    for group, scope in groups.items():
        run('Python ' + group, [sys.executable, '-m', 'unittest', '-v', 'test_' + group], scope)

    with tempfile.TemporaryDirectory(prefix='obsidian-round4-') as temporary:
        build = Path(temporary)
        flags = ['-O2', '-Wall', '-Wextra', '-Werror', '-pedantic',
                 '-fsanitize=undefined', '-fno-sanitize-recover=all']
        if shutil.which('cc'):
            if run('C compile', ['cc', '-std=c17', *flags, 'c_contracts.c', '-o', build/'c'],
                   'C17; warnings as errors; UndefinedBehaviorSanitizer.'):
                run('C run', [build/'c'], 'Array shape, size overflow, unchanged failure output and byte parser contracts.')
            run('C expected shape rejection', ['cc', '-std=c17', '-Wall', '-Wextra', '-Werror',
                                               '-pedantic', '-c', 'c_shape_reject.c', '-o', build/'bad.o'],
                'Nonzero compile result must mention incompatible pointer types; no undefined example is executed.',
                reject='incompatible')
        else:
            skip('C', 'C compiler unavailable.')
        if shutil.which('g++'):
            if run('C++ compile', ['g++', '-std=c++20', *flags, '-pthread', 'cpp_contracts.cpp', '-o', build/'cpp'],
                   'C++20; warnings as errors; UndefinedBehaviorSanitizer; not a race detector.'):
                run('C++ run', [build/'cpp'], 'Type deduction, valid views, 12 copy-failure injection points and 50 one-shot release/acquire runs.')
        else:
            skip('C++', 'C++ compiler unavailable.')
        if shutil.which('tsc') and shutil.which('node'):
            if run('TypeScript compile', ['tsc', '--strict', '--noUncheckedIndexedAccess',
                   '--exactOptionalPropertyTypes', '--target', 'ES2022', '--module', 'commonjs',
                   '--lib', 'ES2022,DOM', '--outDir', build/'ts', 'typescript_contracts.ts'],
                   'Static type equality assertions and four @ts-expect-error expected rejections.'):
                run('TypeScript run', ['node', build/'ts/typescript_contracts.js'],
                    'Plain-data validation, state transitions, stale-result rejection and independent Promise completion.')
        else:
            skip('TypeScript', 'tsc or node unavailable.')
        if shutil.which('rustc'):
            if run('Rust compile', ['rustc', '--edition=2021', '--test', 'rust_ownership.rs', '-o', build/'rust'],
                   'Standard-library-only tests; no Tokio runtime test.'):
                run('Rust run', [build/'rust'], 'Three ownership, pinned-box address and owned-Future drop tests.')
            run('Rust expected borrow rejection', ['rustc', '--edition=2021', 'rust_borrow_reject.rs', '-o', build/'bad-rust'],
                'Conflicting mutable borrows must fail compilation.', reject='borrow')
        else:
            skip('Rust', 'rustc unavailable; all Rust compilation and execution unperformed, including the rejection fixture.')

    report = {
        'python': sys.version, 'platform': platform.platform(), 'tools': tools,
        'results': results,
        'summary': {status: sum(r['status'] == status for r in results)
                    for status in ('PASS', 'FAIL', 'SKIP')},
        'python_unittest_cases': sum(r.get('unittest_cases', 0) for r in results),
        'unperformed': ['PostgreSQL two-session manual script', 'Actual power-loss recovery',
                        'Real packet capture, TLS peers, CPU/MMU behavior and privileged Linux administration',
                        'Tokio runtime execution and full Obsidian GUI/plugin rendering'],
        'limits': ['Passing local cases is not a proof of all implementations or all prose.',
                   'Toy crash, MVCC, pipeline and WAL models state their simplifications in notes and source.']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary']), 'Python cases:', report['python_unittest_cases'])
    return int(bool(report['summary']['FAIL']))


if __name__ == '__main__':
    raise SystemExit(main())
