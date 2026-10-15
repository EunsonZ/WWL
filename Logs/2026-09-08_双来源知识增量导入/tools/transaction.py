"""Scoped local import transaction. Preview first; never writes source vaults.

Backup contains only affected existing visible WWL files. No hidden state,
TaskNotes files, source governance, or Git actions are part of this transaction.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import tempfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def safe(root, rel):
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts or any(x.startswith('.') for x in p.parts):
        raise ValueError(f'unsafe path: {rel}')
    q = root / p
    for part in [q, *q.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError(f'symlink not permitted: {rel}')
    return q


def visible(root):
    return {str(p.relative_to(root)): p for p in root.rglob('*')
            if p.is_file() and not any(x.startswith('.') or x == '__pycache__'
                                     for x in p.relative_to(root).parts)}


def atomic_copy(src, dst, expected_source=None, expected_destination='unchecked'):
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='wwl-import-', dir=dst.parent)
    os.close(fd)
    try:
        shutil.copy2(src, temp)
        if expected_source is not None and digest(Path(temp)) != expected_source:
            raise ValueError('Source changed before replacement: ' + str(src))
        if expected_destination != 'unchecked':
            actual = digest(dst) if dst.exists() else None
            if actual != expected_destination:
                raise ValueError('Destination changed before replacement: ' + str(dst))
        os.replace(temp, dst)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def plan(work):
    state = json.loads((work / 'state.json').read_text())
    stage, vault = Path(state['stage']), Path(state['vault'])
    base = {r['path']: r for r in json.loads((work / 'baseline.json').read_text())}
    current = visible(stage)
    missing = set(base) - set(current)
    if missing:
        raise ValueError(f'Existing WWL deletion is not authorized: {sorted(missing)}')
    rows = []
    for rel, p in sorted(current.items()):
        h = digest(p)
        before = base.get(rel, {}).get('sha256')
        if h == before:
            continue
        if rel.startswith(('TaskNotes/', 'Tags/', 'Logs/2026-09-08_TBM结构整理/')) or rel in ('AGENTS.md', 'NewAgents.md'):
            raise ValueError(f'protected path changed: {rel}')
        q = safe(vault, rel)
        actual = digest(q) if q.exists() else None
        if actual != before:
            raise ValueError(f'Concurrent WWL edit; merge before applying: {rel}')
        rows.append({'path': rel, 'before': before, 'after': h,
                     'size': p.stat().st_size, 'action': 'modify' if before else 'add'})
    manifest = {'schema': 'wwl-dual-import-transaction-v1', **state, 'files': rows}
    (work / 'write-plan.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({'add': sum(r['before'] is None for r in rows),
                      'modify': sum(r['before'] is not None for r in rows),
                      'delete': 0, 'bytes': sum(r['size'] for r in rows)}, ensure_ascii=False))


def backup(work, destination):
    manifest = json.loads((work / 'write-plan.json').read_text())
    vault = Path(manifest['vault'])
    if destination.exists():
        raise ValueError('Backup destination already exists')
    # Preflight every file before any backup mutation.
    for row in manifest['files']:
        q = safe(vault, row['path'])
        if (digest(q) if q.exists() else None) != row['before']:
            raise ValueError(f'Concurrent WWL edit: {row["path"]}')
    destination.mkdir(parents=True)
    os.chmod(destination, 0o700)
    for row in manifest['files']:
        if row['before'] is None:
            continue
        p = safe(destination / 'files', row['path'])
        atomic_copy(safe(vault, row['path']), p, expected_source=row['before'], expected_destination=None)
        if digest(p) != row['before']:
            raise ValueError(f'Backup hash mismatch: {row["path"]}')
    manifest['backup'] = str(destination)
    for name in ('baseline.json', 'write-plan.json'):
        shutil.copy2(work / name, destination / name)
    (work / 'write-plan.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (destination / 'transaction.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    shutil.copy2(Path(__file__), destination / 'transaction.py')
    print(json.dumps({'backup': str(destination), 'verified': sum(r['before'] is not None for r in manifest['files'])}))


def apply(work):
    manifest = json.loads((work / 'write-plan.json').read_text())
    vault, stage, bak = map(Path, (manifest['vault'], manifest['stage'], manifest['backup']))
    frozen = json.loads((bak / 'transaction.json').read_text())
    if manifest != frozen:
        raise ValueError('Manifest changed after backup; review and back up the new plan')
    # All checks finish before the first live write. Each write is checked again.
    for r in manifest['files']:
        if r['path'].startswith(('TaskNotes/', 'Tags/', 'Logs/2026-09-08_TBM结构整理/')) or r['path'] in ('AGENTS.md', 'NewAgents.md'):
            raise ValueError('Protected path in manifest: ' + r['path'])
        q, s = safe(vault, r['path']), safe(stage, r['path'])
        if (digest(q) if q.exists() else None) != r['before'] or digest(s) != r['after']:
            raise ValueError(f'Concurrent live or stage change: {r["path"]}')
        if r['before'] and digest(safe(bak / 'files', r['path'])) != r['before']:
            raise ValueError(f'Backup unavailable: {r["path"]}')
    done = []
    journal = work / 'apply-journal.json'
    for r in manifest['files']:
        q = safe(vault, r['path'])
        if (digest(q) if q.exists() else None) != r['before']:
            raise ValueError(f'Concurrent live change; retained and stopped: {r["path"]}')
        journal.write_text(json.dumps({'written': done, 'pending': r['path']}, ensure_ascii=False, indent=2))
        # Hash the private temporary copy before replacing live content. The
        # full preflight alone cannot protect against a later stage edit.
        atomic_copy(safe(stage, r['path']), q, expected_source=r['after'], expected_destination=r['before'])
        if digest(q) != r['after']:
            raise ValueError(f'Write verification failed: {r["path"]}')
        done.append(r['path'])
        journal.write_text(json.dumps({'written': done, 'pending': None}, ensure_ascii=False, indent=2))
    print(json.dumps({'written': len(done), 'all_verified': True}))


def rollback(manifest_path, commit=False):
    m = json.loads(manifest_path.read_text())
    vault, bak = Path(m['vault']), Path(m['backup'])
    conflicts, installed, untouched = [], [], []
    for r in m['files']:
        q = safe(vault, r['path'])
        actual = digest(q) if q.exists() else None
        if actual == r['after']:
            installed.append(r)
        elif actual == r['before']:
            untouched.append(r['path'])
        else:
            conflicts.append(r['path'])
        if r['before'] and digest(safe(bak / 'files', r['path'])) != r['before']:
            conflicts.append('backup:' + r['path'])
    print(json.dumps({'mode': 'apply' if commit else 'preview',
                      'restore': sum(r['before'] is not None for r in installed),
                      'remove_added': sum(r['before'] is None for r in installed),
                      'not_written_or_already_restored': untouched,
                      'conflicts': conflicts}, ensure_ascii=False, indent=2))
    if conflicts:
        raise ValueError('Recovery refuses to overwrite subsequent edits')
    if not commit:
        return
    for r in reversed(installed):
        q = safe(vault, r['path'])
        if digest(q) != r['after']:
            raise ValueError('Concurrent edit during recovery: ' + r['path'])
        if r['before']:
            atomic_copy(safe(bak / 'files', r['path']), q, expected_source=r['before'], expected_destination=r['after'])
        else:
            q.unlink()
    # Remove only now-empty parents of this batch's added files.
    dirs = {safe(vault, r['path']).parent for r in installed if r['before'] is None}
    for directory in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        while directory != vault:
            try:
                directory.rmdir()
            except OSError:
                break
            directory = directory.parent


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['plan', 'backup', 'apply', 'rollback'])
    ap.add_argument('path', type=Path, help='work directory; rollback uses manifest path')
    ap.add_argument('--destination', type=Path)
    ap.add_argument('--commit', action='store_true', help='rollback only: actually restore after preview checks')
    a = ap.parse_args()
    if a.mode == 'plan': plan(a.path)
    elif a.mode == 'backup': backup(a.path, a.destination)
    elif a.mode == 'apply': apply(a.path)
    else: rollback(a.path, a.commit)
