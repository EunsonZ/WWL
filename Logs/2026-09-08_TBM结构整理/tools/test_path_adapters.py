#!/usr/bin/env python3
"""Lightweight path-regression checks for the migrated computer-science tools.

This script imports no lab entry points and executes no teaching experiments.
It checks only root discovery and report-location contracts, then runs the three
static maintenance tools on an empty temporary directory with explicit outputs.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path


STAGE=Path(__file__).resolve().parents[3]
TOOLS = STAGE / '计算机知识/90-资源/维护/导入-com/_meta/tools'
sys.path.insert(0, str(TOOLS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    expected = STAGE.resolve()
    modules = {
        'round3': STAGE / '计算机知识/_labs/round3/run_all.py',
        'round4': STAGE / '计算机知识/_labs/round4/run_all.py',
        'integration': STAGE / '计算机知识/_labs/integration/run_all.py',
        'round3_python': STAGE / '计算机知识/_labs/round3/PY/test_python.py',
        'audit': TOOLS / 'audit_vault.py',
        'sources': TOOLS / 'check_sources.py',
        'math': TOOLS / 'extract_math.py',
    }
    for name, path in modules.items():
        module = load(name, path)
        assert module.vault_root(path.parent) == expected, name

    labels = {
        'round3': 'round3-labs', 'round4': 'round4-labs',
        'integration': 'integration-labs', 'audit': 'static-audit',
        'sources': 'source-syntax', 'math': 'math-extract',
    }
    for name, label in labels.items():
        output_dir = load(name + '_output', modules[name]).default_output_dir()
        relative = output_dir.relative_to(expected / 'Logs/运行')
        assert relative.parts[0] == label, (name, relative)
        assert re.fullmatch(r'\d{8}T\d{12}[+-]\d{4}', relative.parts[1]), (name, relative)
        assert relative.parts[2] == '计算机知识', (name, relative)

    for path in modules.values():
        text = path.read_text(encoding='utf-8')
        assert 'Logs/运行/' in text or path.name == 'test_python.py', path
        assert "'_meta/" not in text and '"_meta/' not in text, path

    with tempfile.TemporaryDirectory(prefix='path-adapter-') as temporary:
        root = Path(temporary) / 'empty-vault'
        root.mkdir()
        output = Path(temporary) / 'reports'
        commands = [
            [sys.executable, str(TOOLS / 'audit_vault.py'), str(root), '--output-dir', str(output / 'audit')],
            [sys.executable, str(TOOLS / 'check_sources.py'), str(root), '--output-dir', str(output / 'sources')],
            [sys.executable, str(TOOLS / 'extract_math.py'), str(root), '--output-dir', str(output / 'math')],
        ]
        for command in commands:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=20)
            assert completed.returncode == 0, completed.stderr
        assert (output / 'audit/static_audit.json').is_file()
        assert (output / 'sources/source_syntax_results.json').is_file()
        assert (output / 'math/math_expressions.json').is_file()

    print('PASS: migrated tools locate the vault and direct new reports away from historical _meta')


if __name__ == '__main__':
    main()
