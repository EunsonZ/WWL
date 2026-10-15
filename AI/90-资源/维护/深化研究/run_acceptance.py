"""复跑本轮验收，不修改笔记或安装依赖。

在任意工作目录运行：python <本脚本路径>
需要已有原实验所需依赖（本轮环境见 environment.json）。
MathJax 独立检查由上级目录 check_math.cjs 执行；本脚本不联网安装 Node 包。
"""
from __future__ import annotations
import ast
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from check_vault import check  # noqa: E402


def dump(name: str, payload) -> None:
    (HERE/name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> int:
    packages = {}
    for name in ['torch', 'numpy', 'scipy', 'PyYAML', 'matplotlib', 'pytest', 'Pillow']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    import torch
    environment = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                   'python': sys.version, 'platform': platform.platform(), 'packages': packages,
                   'cuda_available': torch.cuda.is_available(),
                   'scope': 'CPU unit tests; DDP math is single-process simulation; no GPU or real large-model training'}
    dump('environment.json', environment)
    outcomes = []
    environment_variables = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    folders = sorted({p.parent for p in (ROOT/'80-实践').rglob('test*.py')})
    for folder in folders:
        start = time.perf_counter()
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py', '-v']
        try:
            result = subprocess.run(command, cwd=folder, env=environment_variables, capture_output=True,
                                    text=True, timeout=180)
            log = result.stdout+result.stderr
            matches = re.findall(r'Ran (\d+) tests?', log)
            item = {'folder': str(folder.relative_to(ROOT)), 'returncode': result.returncode,
                    'test_count': int(matches[-1]) if matches else None,
                    'seconds': round(time.perf_counter()-start, 3), 'command': command, 'log': log}
        except subprocess.TimeoutExpired as error:
            item = {'folder': str(folder.relative_to(ROOT)), 'returncode': -1, 'test_count': None,
                    'seconds': round(time.perf_counter()-start, 3), 'log': str(error)}
        outcomes.append(item)
        print(item['folder'], item['returncode'], item['test_count'], flush=True)
    dump('test_runs.json', outcomes)
    syntax = []
    for path in sorted(ROOT.rglob('*.py')):
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path.relative_to(ROOT)))
            syntax.append({'path': str(path.relative_to(ROOT)), 'ok': True})
        except (SyntaxError, UnicodeError) as error:
            syntax.append({'path': str(path.relative_to(ROOT)), 'ok': False, 'error': str(error)})
    dump('python_syntax.json', syntax)
    shell = []
    for path in sorted(ROOT.rglob('*.sh')):
        result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        shell.append({'path': str(path.relative_to(ROOT)), 'returncode': result.returncode, 'stderr': result.stderr})
    dump('shell_syntax.json', shell)
    report, formulas = check(ROOT)
    dump('vault_audit.json', report)
    dump('formulas.json', formulas)
    critical = ['missing_internal_links', 'ambiguous_links', 'missing_images', 'remote_image_embeds',
                'bad_fences', 'math_delimiters', 'unescaped_table_aliases', 'missing_heading_anchors',
                'yaml_errors', 'missing_markdown_files']
    failed = (any(x['returncode'] or x['test_count'] is None for x in outcomes)
              or any(not x['ok'] for x in syntax) or any(x['returncode'] for x in shell)
              or any(report[key] for key in critical))
    print(json.dumps({'tests': sum(x['test_count'] or 0 for x in outcomes), 'python_files': len(syntax),
                      'shell_files': len(shell), 'static_error_counts': {k:len(report[k]) for k in critical},
                      'markdown': report['summary']['markdown_files']},ensure_ascii=False), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
