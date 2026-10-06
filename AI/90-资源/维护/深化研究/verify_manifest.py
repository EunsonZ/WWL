"""校验交付文件的 SHA-256；不联网，不修改文件。维护后应重新生成清单。"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main() -> int:
    manifest = json.loads((HERE/'file_manifest.json').read_text(encoding='utf-8'))
    failures = []
    for item in manifest['files']:
        path = (ROOT/item['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            failures.append({'path': item['path'], 'reason': 'path_outside_root'})
        elif not path.is_file():
            failures.append({'path': item['path'], 'reason': 'missing'})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            failures.append({'path': item['path'], 'reason': 'sha256_mismatch'})
    print(json.dumps({'checked': len(manifest['files']), 'failures': failures}, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
