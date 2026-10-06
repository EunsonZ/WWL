"""Finite pre-push check. Reports categories and paths, never matching values.

Checks new Git objects, committed tree paths and local LFS payloads. This is a focused guard
for recognizable credentials, private keys and oversized ordinary blobs, not a
proof that arbitrary documents contain no sensitive information.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess

PATTERNS = (
    ('github-token', re.compile(rb'(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{70,})(?![A-Za-z0-9_])')),
    ('private-key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
)
LIMIT = 100 * 1024 * 1024
POINTER = re.compile(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n\Z')
# Preserved C1 audit evidence: exactly the two-byte empty JSON object, not live
# Obsidian configuration. Any changed payload at this path needs a new review.
EMPTY_CONFIG_ARCHIVE = 'Logs/2026-09-15_C1人机协作整合/originals/.obsidian/app.json.txt'
EMPTY_CONFIG_BLOB = '9e26dfeeb6e641a33dae4961196235bdb965b21b'


def redact(value):
    data = str(value).encode('utf-8', errors='replace')
    for _, pattern in PATTERNS:
        data = pattern.sub(b'[REDACTED]', data)
    return data.decode('utf-8', errors='replace')


def categories(data):
    return [name for name, pattern in PATTERNS if pattern.search(data)]


def protected_path(path):
    p = PurePosixPath(path)
    return (p.name == '.env' or p.name.startswith('.env.') or
            p.suffix.lower() in {'.key', '.pem', '.p12', '.pfx'} or
            ('.obsidian' in p.parts and path != '.obsidian/types.json') or
            bool(set(p.parts) & {'.venv', '.smart-env', '.space', '.makemd', 'node_modules', '__pycache__'}) or
            p.name == '.DS_Store')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def pending_objects(repo, head, remote_head=None):
    args = ['rev-list', '--objects', head]
    if remote_head and remote_head != '0' * 40:
        exists = subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', remote_head + '^{commit}'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if exists.returncode == 0:
            args += ['--not', remote_head]
    objects = {}
    for line in git(repo, *args).splitlines():
        oid, _, name = line.partition(b' ')
        objects[oid] = name.decode('utf-8', errors='replace')
    return objects


def scan_pending(repo, head, remote_head=None):
    objects = pending_objects(repo, head, remote_head)
    if not objects:
        return {'blobs_checked': 0, 'metadata_objects_checked': 0, 'paths_checked': 0, 'lfs_payloads_checked': 0, 'findings': []}
    check = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'],
                           input=b'\n'.join(objects) + b'\n', capture_output=True, check=True)
    readable = []
    commits = []
    blob_count = 0
    metadata_count = 0
    for line in check.stdout.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] in {b'blob', b'commit', b'tree', b'tag'}:
            readable.append((fields[0], fields[1], int(fields[2])))
            if fields[1] == b'blob': blob_count += 1
            else: metadata_count += 1
            if fields[1] == b'commit': commits.append(fields[0].decode())
    storage = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-path', 'lfs/objects').decode().strip())
    findings = []
    # A shared blob may appear at several paths, or already exist remotely.
    # Enumerate every pending commit tree, independently of object deduplication.
    paths = set()
    path_findings = set()
    for commit in commits:
        for entry in git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0'):
            if not entry: continue
            metadata, name = entry.split(b'\t', 1)
            path = name.decode('utf-8', errors='replace'); paths.add(path)
            if protected_path(path):
                oid = metadata.split()[2].decode()
                if path == EMPTY_CONFIG_ARCHIVE:
                    if oid != EMPTY_CONFIG_BLOB:
                        path_findings.add((path, 'archived-config-version-unreviewed'))
                else:
                    path_findings.add((path, 'protected-local-path'))
    findings.extend({'path': redact(path), 'type': kind} for path, kind in sorted(path_findings))
    lfs_count = 0
    seen_lfs = set()
    process = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for oid, kind, size in readable:
            path = redact(objects[oid] or (kind.decode() + ':' + oid.decode()))
            if kind == b'blob' and size > LIMIT:
                findings.append({'path': path, 'type': 'ordinary-blob-exceeds-100MiB'})
            process.stdin.write(oid + b'\n'); process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[1] != kind or int(header[2]) != size:
                raise RuntimeError('Unexpected Git object response')
            data = process.stdout.read(size)
            if len(data) != size or process.stdout.read(1) != b'\n':
                raise RuntimeError('Incomplete Git object response')
            findings.extend({'path': path, 'type': kind} for kind in categories(data))
            pointer = POINTER.fullmatch(data) if kind == b'blob' else None
            if pointer and pointer[1] not in seen_lfs:
                seen_lfs.add(pointer[1]); lfs_count += 1
                digest = pointer[1].decode(); expected_size = int(pointer[2])
                payload = storage / digest[:2] / digest[2:4] / digest
                if not payload.is_file() or payload.is_symlink():
                    findings.append({'path': path, 'type': 'LFS-payload-missing'})
                    continue
                actual_size = 0; hasher = hashlib.sha256(); tail = b''; found = set()
                with payload.open('rb') as stream:
                    while True:
                        block = stream.read(1024 * 1024)
                        if not block: break
                        actual_size += len(block); hasher.update(block)
                        found.update(categories(tail + block)); tail = block[-1024:]
                findings.extend({'path': path, 'type': kind} for kind in sorted(found))
                if actual_size != expected_size or hasher.hexdigest() != digest:
                    findings.append({'path': path, 'type': 'LFS-payload-hash-or-size-mismatch'})
    finally:
        process.stdin.close()
        process.stdout.close()
        if process.wait() != 0:
            raise RuntimeError('Git object reader failed')
    return {'blobs_checked': blob_count, 'metadata_objects_checked': metadata_count,
            'paths_checked': len(paths), 'lfs_payloads_checked': lfs_count, 'findings': findings}
