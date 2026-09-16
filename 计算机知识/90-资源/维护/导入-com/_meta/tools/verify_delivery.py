#!/usr/bin/env python3
"""Check a delivered vault against its SHA-256 manifest. Read-only, standard library.
Usage: python _meta/tools/verify_delivery.py [VAULT_ROOT]
Run before changing or regenerating files; later edits legitimately change hashes.
"""
from pathlib import Path
import argparse, hashlib, json, sys

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[2])
    root=parser.parse_args().root.resolve()
    manifest_path=root/'_meta/file_manifest.json'
    try:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        entries=manifest['entries']
    except (OSError, ValueError, KeyError) as exc:
        print(f'FAIL: cannot read manifest: {exc}',file=sys.stderr);return 2
    problems=[];known=set()
    for item in entries:
        name=item['path'];p=root/name
        if Path(name).is_absolute() or '..' in Path(name).parts or name in known:
            problems.append(f'invalid or repeated path: {name}');continue
        known.add(name)
        if p.is_symlink() or root not in p.resolve().parents or not p.is_file():
            problems.append(f'missing, symlink or unsafe path: {name}');continue
        data=p.read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            problems.append(f'changed: {name}')
    # Extra files are reported, not rejected: Obsidian may add configuration files.
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    extra=sorted(actual-known-{'_meta/file_manifest.json'})
    for text in problems:print('FAIL:',text)
    print(f'Listed files: {len(entries)}; mismatches: {len(problems)}; extra files: {len(extra)}')
    for name in extra:print('EXTRA:',name)
    if not problems:print('PASS: every listed byte sequence matches the manifest')
    return 1 if problems else 0

if __name__=='__main__':raise SystemExit(main())
