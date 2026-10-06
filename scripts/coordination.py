#!/usr/bin/env python3
"""Schema-2 read-only coordination record checks. See COORDINATION.md."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata

SCHEMA = 2
EFFORTS = {'none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra', 'unknown'}
HEX = re.compile(r'^[0-9a-f]{64}$')
IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


class Invalid(ValueError):
    pass


def fail(message):
    raise Invalid(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def obj(value, required, optional=(), where='object'):
    if not isinstance(value, dict):
        fail(f'{where}: expected object')
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        fail(f'{where}: missing {sorted(missing)}, unknown {sorted(extra)}')
    if 'notes' in value and not isinstance(value['notes'], dict):
        fail(f'{where}: notes must be an explanatory object')
    return value


def string(value, where='value'):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        fail(f'{where}: expected nonempty text without controls')
    return value


def ident(value):
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        fail('invalid record/task identifier')
    return value


def seq(value, where='value', unique=False):
    if not isinstance(value, list):
        fail(f'{where}: expected list')
    if unique and len({canonical(v) for v in value}) != len(value):
        fail(f'{where}: duplicate list member')
    return value


def integer(value, where='value', low=1, high=1000000):
    if type(value) is not int or not low <= value <= high:
        fail(f'{where}: integer outside supported range')
    return value


def enum(value, allowed, where='value'):
    if not isinstance(value, str) or value not in allowed:
        fail(f'{where}: unsupported value')
    return value


def version(value):
    if type(value) is not int or value != SCHEMA:
        fail('unsupported legacy schema 1 (no verifiable local wire format)' if value == 1 else 'unsupported schema')


def hash_value(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        fail('expected lowercase SHA-256')
    return value


def path(value, scope=False):
    string(value, 'path')
    if scope and value == '.':
        return value
    if value != unicodedata.normalize('NFC', value):
        fail('path must use canonical NFC spelling')
    if value.startswith('/') or '\\' in value or ':' in value:
        fail('unsafe absolute/drive/backslash path')
    if any(p in ('', '.', '..') or p != p.strip() for p in value.split('/')):
        fail('unsafe dot/empty/whitespace path component')
    if any(unicodedata.category(c).startswith('C') for c in value):
        fail('unsafe control or formatting character in path')
    return value


def paths(values, scope=False):
    for value in seq(values, 'paths', unique=True):
        path(value, scope)
    return values


def validate_path_set(values):
    components = {}
    for value in set(values):
        parts = value.split('/')
        for i in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:i])
            key = unicodedata.normalize('NFC', prefix).casefold()
            if key in components and components[key] != prefix:
                fail('case/Unicode ambiguous declared directory components')
            components[key] = prefix
    seen = {}
    for value in sorted(set(values)):
        key = unicodedata.normalize('NFC', value).casefold()
        if key in seen and seen[key] != value:
            fail('case/Unicode ambiguous declared paths')
        seen[key] = value
    for key in seen:
        if any('/'.join(key.split('/')[:i]) in seen for i in range(1, len(key.split('/')))):
            fail('file/parent path collision')


def duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('duplicate JSON key')
        result[key] = value
    return result


def decode_json(data):
    try:
        return json.loads(data.decode('utf-8'), object_pairs_hook=duplicate_pairs,
                          parse_constant=lambda _: fail('nonfinite JSON value'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Invalid('invalid UTF-8 JSON') from exc


class Root:
    """Read via directory file descriptors; retain content states for final validation."""
    @staticmethod
    def open_chain(location):
        fd = os.open(location.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in location.parts[1:]:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new
            return fd
        except OSError as exc:
            os.close(fd)
            raise Invalid('root or ancestor is not an available real directory') from exc

    def __init__(self, location):
        self.location = Path(os.path.abspath(location))
        self.fd = self.open_chain(self.location)
        self.identity = os.fstat(self.fd)
        self.observed = {}

    def close(self):
        os.close(self.fd)

    def _names(self, fd):
        names = os.listdir(fd)
        folded = {}
        for name in names:
            key = unicodedata.normalize('NFC', name).casefold()
            if key in folded and folded[key] != name:
                fail('case/Unicode ambiguous filesystem siblings')
            folded[key] = name
        return names

    def _actual(self, fd, name):
        names = self._names(fd)
        same = [v for v in names if unicodedata.normalize('NFC', v) == name]
        if same:
            return same[0]
        if any(unicodedata.normalize('NFC', v).casefold() == name.casefold() for v in names):
            fail('path spelling differs by case')
        return name

    def _parent(self, relative):
        path(relative)
        fd = os.dup(self.fd)
        try:
            parts = relative.split('/')
            for name in parts[:-1]:
                actual = self._actual(fd, name)
                try:
                    new = os.open(actual, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    return fd, None
                except OSError as exc:
                    raise Invalid('unsafe or unavailable path ancestor') from exc
                os.close(fd)
                fd = new
            return fd, self._actual(fd, parts[-1])
        except BaseException:
            os.close(fd)
            raise

    @staticmethod
    def _token(st):
        return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink

    def read(self, relative, remember=True, max_bytes=None):
        fd, name = self._parent(relative)
        filefd = None
        try:
            if name is None:
                data = None
            else:
                try:
                    pre = os.stat(name, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    pre = None
                if pre is None:
                    data = None
                else:
                    if not stat.S_ISREG(pre.st_mode) or pre.st_nlink != 1:
                        fail('path must be a regular file with exactly one hard link')
                    filefd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    before = os.fstat(filefd)
                    if self._token(pre) != self._token(before):
                        fail('file changed before read')
                    if max_bytes is not None and before.st_size > max_bytes:
                        fail('declared byte bound exceeded before read')
                    chunks = []
                    total = 0
                    while True:
                        limit = 1024 * 1024 if max_bytes is None else min(1024 * 1024, max_bytes - total + 1)
                        chunk = os.read(filefd, limit)
                        if not chunk:
                            break
                        total += len(chunk)
                        if max_bytes is not None and total > max_bytes:
                            fail('declared byte bound exceeded during read')
                        chunks.append(chunk)
                    after = os.fstat(filefd)
                    named = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if self._token(before) != self._token(after) or self._token(after) != self._token(named):
                        fail('file changed during read')
                    data = b''.join(chunks)
            state = {'kind': 'absent'} if data is None else {'kind': 'file', 'sha256': sha(data)}
            if remember:
                if relative in self.observed and self.observed[relative] != state:
                    fail('input changed between reads')
                self.observed[relative] = state
            return data
        except OSError as exc:
            raise Invalid('file unavailable or changed while reading') from exc
        finally:
            if filefd is not None:
                os.close(filefd)
            os.close(fd)

    def state(self, relative, required=False):
        data = self.read(relative)
        if required and data is None:
            fail('required input is missing')
        return {'kind': 'absent'} if data is None else {'kind': 'file', 'sha256': sha(data)}

    def files(self, scope='.', max_files=100000):
        path(scope, scope=True)
        result = []
        if scope == '.':
            start = os.dup(self.fd)
            prefix = ''
        else:
            parent, name = self._parent(scope)
            try:
                if name is None:
                    fail('search scope missing')
                start = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            except OSError as exc:
                raise Invalid('search scope must be a real directory') from exc
            finally:
                os.close(parent)
            prefix = scope + '/'
        def walk(fd, prefix):
            for name in sorted(self._names(fd)):
                canonical_name = unicodedata.normalize('NFC', name)
                rel = prefix + canonical_name
                path(rel)
                st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode):
                    new = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        walk(new, rel + '/')
                    finally:
                        os.close(new)
                elif stat.S_ISREG(st.st_mode) and st.st_nlink == 1:
                    result.append(rel)
                    if len(result) > max_files:
                        fail('declared file bound exceeded')
                else:
                    fail('unsafe link or special file in inspected tree')
        try:
            walk(start, prefix)
        except OSError as exc:
            raise Invalid('tree changed or unavailable during scan') from exc
        finally:
            os.close(start)
        return result

    def verify(self):
        checkfd = self.open_chain(self.location)
        try:
            named = os.fstat(checkfd)
        finally:
            os.close(checkfd)
        if (named.st_dev, named.st_ino) != (self.identity.st_dev, self.identity.st_ino):
            fail('root identity changed')
        for relative, expected in list(self.observed.items()):
            data = self.read(relative, remember=False)
            actual = {'kind': 'absent'} if data is None else {'kind': 'file', 'sha256': sha(data)}
            if actual != expected:
                fail('input changed before completion')


def load_json_file(location, roots):
    p = Path(os.path.abspath(location))
    root = Root(p.parent)
    roots.append(root)
    data = root.read(p.name)
    if data is None:
        fail('required JSON input file is missing')
    return decode_json(data)


def search_spec(value):
    obj(value, {'scopes', 'literals', 'extensions', 'max_files', 'max_bytes', 'case_sensitive'}, where='search')
    paths(value['scopes'], scope=True)
    if not value['scopes']:
        fail('search requires explicit scopes')
    for term in seq(value['literals'], 'literals', unique=True):
        string(term)
    if not value['literals']:
        fail('search requires literal terms')
    for ext in seq(value['extensions'], 'extensions', unique=True):
        if not isinstance(ext, str) or not re.fullmatch(r'\.[A-Za-z0-9_-]+', ext):
            fail('search extension must be a literal suffix')
    integer(value['max_files'], 'max_files', high=100000)
    integer(value['max_bytes'], 'max_bytes', high=100000000)
    if type(value['case_sensitive']) is not bool:
        fail('case_sensitive must be boolean')


def validate_plan(plan):
    obj(plan, {'schema', 'batch', 'rules', 'human_files', 'shared_files', 'tasks'}, {'notes'}, 'plan')
    version(plan['schema'])
    ident(plan['batch'])
    obj(plan['rules'], {'version', 'files'}, where='rules')
    string(plan['rules']['version'])
    paths(plan['rules']['files'])
    if not plan['rules']['files']:
        fail('at least one actual rule file is required')
    paths(plan['human_files']); paths(plan['shared_files'])
    taskmap = {}
    allpaths = list(plan['rules']['files']) + plan['human_files'] + plan['shared_files']
    owners = {}
    for task in seq(plan['tasks'], 'tasks'):
        obj(task, {'id', 'kind', 'goal', 'writes', 'reads', 'risk', 'acceptance', 'review_by', 'forbidden', 'searches'}, {'notes'}, 'task')
        ident(task['id'])
        if task['id'] in taskmap:
            fail('duplicate task id')
        taskmap[task['id']] = task
        enum(task['kind'], {'author', 'review', 'evidence'}, 'task kind')
        enum(task['risk'], {'low', 'normal', 'high'}, 'risk')
        string(task['goal']); paths(task['writes']); paths(task['forbidden'])
        for item in seq(task['acceptance'], 'acceptance', unique=True):
            string(item)
        if not task['acceptance']:
            fail('acceptance criteria required')
        for reviewer in seq(task['review_by'], 'review_by', unique=True):
            ident(reviewer)
        if task['kind'] != 'author' and task['writes']:
            fail('only declared authors may propose writes')
        if task['writes'] and task['risk'] in {'normal', 'high'} and not task['review_by']:
            fail('normal/high writes require independent review')
        for target in task['writes']:
            if target in owners:
                fail('overlapping final write ownership')
            owners[target] = task['id']
            if any(target.casefold() == p.casefold() or target.casefold().startswith(p.casefold() + '/') for p in plan['human_files'] + task['forbidden']):
                fail('target intersects human protection or task prohibition')
        allpaths.extend(task['writes'])
        for read in seq(task['reads'], 'reads', unique=True):
            if not isinstance(read, dict):
                fail('read must be an object')
            if read.get('kind') == 'base':
                obj(read, {'kind', 'path'}, where='base read')
            elif read.get('kind') == 'artifact':
                obj(read, {'kind', 'task', 'path', 'require'}, where='artifact read')
                ident(read['task']); enum(read['require'], {'accepted', 'candidate'}, 'artifact requirement')
            else:
                fail('unknown read kind')
            path(read['path']); allpaths.append(read['path'])
        for search in seq(task['searches'], 'searches'):
            search_spec(search)
    validate_path_set(allpaths)
    graph = {tid: [] for tid in taskmap}
    for tid, task in taskmap.items():
        for reviewer in task['review_by']:
            if reviewer == tid or reviewer not in taskmap or taskmap[reviewer]['kind'] != 'review':
                fail('invalid or self review task')
            for target in task['writes']:
                if not any(r == {'kind': 'artifact', 'task': tid, 'path': target, 'require': 'candidate'} for r in taskmap[reviewer]['reads']):
                    fail('designated review must read every candidate target')
        for read in task['reads']:
            if read['kind'] == 'artifact':
                producer = taskmap.get(read['task'])
                if producer is None or read['path'] not in producer['writes']:
                    fail('artifact read does not name a declared producer target')
                if task['kind'] != 'review':
                    graph[tid].append(read['task'])
    visiting, visited = set(), set()
    def visit(tid):
        if tid in visiting:
            fail('future artifact dependency cycle')
        if tid in visited:
            return
        visiting.add(tid)
        for dependency in graph[tid]:
            visit(dependency)
        visiting.remove(tid); visited.add(tid)
    for tid in graph:
        visit(tid)
    return taskmap


def contract(plan, task):
    clean = {k: v for k, v in task.items() if k != 'notes'}
    # Set-like fields have no scheduling order semantics.
    for key in ('writes', 'reads', 'review_by', 'forbidden'):
        clean[key] = sorted(clean[key], key=canonical)
    return digest({'task': clean, 'rules': plan['rules']})


def search_matches(spec, current, overlay=None):
    overlay = overlay or {}
    files = set()
    for scope in spec['scopes']:
        files.update(current.files(scope, spec['max_files']))
    for relative in overlay:
        if any(s == '.' or relative.startswith(s + '/') for s in spec['scopes']):
            files.add(relative)
    if len(files) > spec['max_files']:
        fail('declared file bound exceeded')
    result, used = {}, 0
    terms = spec['literals'] if spec['case_sensitive'] else [t.casefold() for t in spec['literals']]
    for relative in sorted(files):
        if spec['extensions'] and not any(relative.endswith(ext) for ext in spec['extensions']):
            continue
        data = overlay[relative] if relative in overlay else current.read(relative, max_bytes=spec['max_bytes'] - used)
        if data is None:
            continue
        used += len(data)
        if used > spec['max_bytes']:
            fail('declared byte bound exceeded')
        try:
            content = data.decode('utf-8')
        except UnicodeError as exc:
            raise Invalid('search scope contains non-UTF-8 matching-suffix file') from exc
        haystack = content if spec['case_sensitive'] else content.casefold()
        if any(term in haystack for term in terms):
            result[relative] = {'kind': 'file', 'sha256': sha(data)}
    return {'spec': digest(spec), 'matches': result}


def snapshot(plan, current):
    tasks = validate_plan(plan)
    result = {'schema': 2, 'kind': 'snapshot', 'batch': plan['batch'], 'tasks': {}}
    for tid, task in tasks.items():
        required = set(plan['rules']['files']) | {r['path'] for r in task['reads'] if r['kind'] == 'base'}
        inputs = {p: current.state(p, required=p in required) for p in sorted(required | set(task['writes']))}
        result['tasks'][tid] = {'contract': contract(plan, task), 'inputs': inputs,
                                'searches': [search_matches(s, current) for s in task['searches']]}
    return result


def state_shape(value):
    if not isinstance(value, dict):
        fail('state must be an object')
    if value.get('kind') == 'absent':
        obj(value, {'kind'}, where='absent state')
    elif value.get('kind') == 'file':
        obj(value, {'kind', 'sha256'}, where='file state'); hash_value(value['sha256'])
    else:
        fail('unknown byte state')


def baseline_shape(value):
    obj(value, {'contract', 'inputs', 'searches'}, where='attempt baseline')
    hash_value(value['contract'])
    if not isinstance(value['inputs'], dict):
        fail('baseline inputs must be a path map')
    for p, s in value['inputs'].items():
        path(p); state_shape(s)
    for result in seq(value['searches'], 'search results'):
        obj(result, {'spec', 'matches'}, where='search result'); hash_value(result['spec'])
        if not isinstance(result['matches'], dict):
            fail('search matches must be a map')
        for p, s in result['matches'].items():
            path(p); state_shape(s)
            if s['kind'] != 'file':
                fail('search match must be an existing file')


def route_shape(value):
    obj(value, {'model', 'effort', 'supported_efforts'}, where='route')
    string(value['model']); enum(value['effort'], EFFORTS, 'effort')
    supported = value['supported_efforts']
    if supported != 'unknown':
        for item in seq(supported, 'supported efforts', unique=True):
            enum(item, EFFORTS - {'unknown'})
        if value['effort'] != 'unknown' and value['effort'] not in supported:
            fail('requested/observed effort not in declared model support')


def record_index(values, where):
    result = {}
    for value in seq(values, where):
        if not isinstance(value, dict):
            fail(f'{where}: record must be object')
        key = ident(value.get('id'))
        if key in result and result[key] != value:
            fail(f'{where}: conflicting duplicate id')
        result[key] = value
    return result


def input_digest(attempt):
    return digest({'baseline': attempt['baseline'], 'artifact_inputs': sorted(attempt['artifact_inputs'], key=canonical)})


def output_digest(artifacts):
    return digest(sorted([{'id': a['id'], 'task': a['task'], 'attempt': a['attempt'], 'path': a['path'], 'state': a['state']} for a in artifacts], key=canonical))


def acceptance_digest(task):
    return digest(task['acceptance'])


def validate_records(records, plan):
    obj(records, {'schema', 'batch', 'current', 'attempts', 'artifacts', 'receipts', 'release', 'checks'}, {'notes'}, 'records')
    version(records['schema'])
    if records['batch'] != plan['batch']:
        fail('records batch mismatch')
    tasks = validate_plan(plan)
    attempts = record_index(records['attempts'], 'attempts')
    artifacts = record_index(records['artifacts'], 'artifacts')
    receipts = record_index(records['receipts'], 'receipts')
    counts = {}
    for attempt in attempts.values():
        obj(attempt, {'id', 'task', 'contract', 'generation', 'session', 'actor', 'mode', 'status', 'baseline', 'artifact_inputs', 'outputs', 'requested', 'observed', 'usage_ref'}, {'notes', 'retry_basis'}, 'attempt')
        if attempt['task'] not in tasks:
            fail('attempt names unknown task')
        counts[attempt['task']] = counts.get(attempt['task'], 0) + 1
        hash_value(attempt['contract']); integer(attempt['generation'], 'generation')
        if attempt['session'] is not None:
            string(attempt['session'])
        string(attempt['actor'])
        enum(attempt['mode'], {'formal', 'review', 'speculative'}, 'attempt mode')
        enum(attempt['status'], {'running', 'finished', 'no_change', 'cancelled', 'unknown', 'revoked'}, 'attempt status')
        if (tasks[attempt['task']]['kind'] == 'review') != (attempt['mode'] == 'review'):
            fail('attempt mode incompatible with task')
        baseline_shape(attempt['baseline'])
        if attempt['baseline']['contract'] != attempt['contract']:
            fail('attempt baseline contract mismatch')
        for ref in seq(attempt['artifact_inputs'], 'artifact_inputs', unique=True):
            obj(ref, {'task', 'path', 'require', 'artifact', 'producer_attempt', 'state'}, where='artifact binding')
            ident(ref['producer_attempt']); state_shape(ref['state'])
            ident(ref['task']); path(ref['path']); ident(ref['artifact'])
            enum(ref['require'], {'candidate', 'accepted'})
        for aid in seq(attempt['outputs'], 'outputs', unique=True):
            ident(aid)
        route_shape(attempt['requested']); route_shape(attempt['observed'])
        if attempt['usage_ref'] is not None:
            string(attempt['usage_ref'])
        if 'retry_basis' in attempt:
            string(attempt['retry_basis'])
    for tid, count in counts.items():
        if count > 2 and not all('retry_basis' in a for a in sorted((a for a in attempts.values() if a['task'] == tid), key=lambda a: (a['generation'], a['id']))[2:]):
            fail('extra attempt requires explicit new evidence/method/authorization')
    if not isinstance(records['current'], dict):
        fail('current must be task map')
    for tid, value in records['current'].items():
        if tid not in tasks:
            fail('unknown current task')
        obj(value, {'generation', 'attempt'}, where='current generation')
        integer(value['generation'], 'current generation')
        a = attempts.get(value['attempt'])
        if a is None or a['task'] != tid or a['generation'] != value['generation']:
            fail('current generation/attempt mismatch')
    for artifact in artifacts.values():
        obj(artifact, {'id', 'task', 'attempt', 'path', 'state', 'storage'}, where='artifact')
        path(artifact['path']); state_shape(artifact['state'])
        a = attempts.get(artifact['attempt'])
        if a is None or artifact['task'] != a['task'] or artifact['path'] not in tasks[a['task']]['writes'] or artifact['id'] not in a['outputs']:
            fail('artifact producer/scope mismatch')
        if artifact['state']['kind'] == 'absent':
            if artifact['storage'] is not None:
                fail('deletion must not have storage')
        else:
            path(artifact['storage'])
    for a in attempts.values():
        selected = [artifacts.get(aid) for aid in a['outputs']]
        if any(x is None or x['attempt'] != a['id'] for x in selected):
            fail('attempt output reference mismatch')
        if len({x['path'] for x in selected}) != len(selected):
            fail('multiple output versions for a single target')
        if a['status'] in {'finished', 'no_change'} and set(x['path'] for x in selected) != set(tasks[a['task']]['writes']):
            fail('finished attempt must bind every declared output')
        for ref in a['artifact_inputs']:
            artifact = artifacts.get(ref['artifact'])
            if artifact is None or artifact['task'] != ref['task'] or artifact['path'] != ref['path'] or artifact['attempt'] != ref['producer_attempt'] or artifact['state'] != ref['state']:
                fail('artifact input binding mismatch')
    for receipt in receipts.values():
        obj(receipt, {'id', 'task', 'producer_attempt', 'review_attempt', 'artifact_ids', 'input_digest', 'output_digest', 'acceptance_digest', 'decision', 'basis', 'evidence_refs'}, where='receipt')
        ident(receipt['task']); ident(receipt['producer_attempt']); ident(receipt['review_attempt'])
        for aid in seq(receipt['artifact_ids'], 'receipt artifacts', unique=True):
            ident(aid)
        for key in ('input_digest', 'output_digest', 'acceptance_digest'):
            hash_value(receipt[key])
        enum(receipt['decision'], {'accept', 'reject', 'pending'}, 'receipt decision')
        string(receipt['basis'])
        for ref in seq(receipt['evidence_refs'], 'evidence refs'):
            obj(ref, {'path', 'sha256'}, where='evidence reference'); path(ref['path']); hash_value(ref['sha256'])
        if not receipt['evidence_refs']:
            fail('receipt requires evidence locator')
    rel = records['release']
    if rel is not None:
        obj(rel, {'tasks', 'artifacts', 'publisher', 'combination'}, where='release')
        for tid in seq(rel['tasks'], 'release tasks', unique=True):
            if tid not in tasks or tasks[tid]['kind'] != 'author':
                fail('release names nonauthor/unknown task')
        for aid in seq(rel['artifacts'], 'release artifacts', unique=True):
            if aid not in artifacts:
                fail('release artifact missing')
        obj(rel['publisher'], {'session', 'confirmed', 'contenders', 'targets_saved', 'external_writers_controlled', 'cancellation_state'}, where='publisher declaration')
        p = rel['publisher']; string(p['session'])
        for s in seq(p['contenders'], 'publisher contenders', unique=True):
            string(s)
        for k in ('confirmed', 'targets_saved', 'external_writers_controlled'):
            if p[k] is not None and type(p[k]) is not bool:
                fail('control declarations must be bool or null')
        enum(p['cancellation_state'], {'none', 'confirmed', 'unknown'}, 'cancellation state')
        if rel['combination'] is not None:
            obj(rel['combination'], {'review_attempt', 'input_digest', 'output_digest', 'acceptance_digest', 'basis', 'evidence_refs', 'searches'}, where='combination')
            ident(rel['combination']['review_attempt'])
            for k in ('input_digest', 'output_digest', 'acceptance_digest'):
                hash_value(rel['combination'][k])
            string(rel['combination']['basis'])
            for ref in seq(rel['combination']['evidence_refs'], 'combination evidence'):
                obj(ref, {'path', 'sha256'}, where='evidence reference'); path(ref['path']); hash_value(ref['sha256'])
            if not rel['combination']['evidence_refs']:
                fail('combination evidence required')
            if not isinstance(rel['combination']['searches'], dict):
                fail('combination search bindings must be a map')
    for check in record_index(records['checks'], 'checks').values():
        obj(check, {'id', 'inputs', 'outputs', 'code', 'argv', 'environment', 'key', 'result'}, {'prior'}, 'check')
        ident(check['id']); hash_value(check['key'])
        for field in ('inputs', 'outputs', 'code'):
            if not isinstance(check[field], dict):
                fail('check file inputs must be path maps')
            for p, s in check[field].items():
                path(p); state_shape(s)
        if not check['code']:
            fail('check requires actual code bindings')
        for arg in seq(check['argv'], 'argv'):
            string(arg)
        if not check['argv']:
            fail('check requires a nonempty literal command')
        if not isinstance(check['environment'], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in check['environment'].items()):
            fail('check environment must be string map')
        enum(check['result'], {'pass', 'fail', 'not_run', 'unknown'})
        if 'prior' in check:
            obj(check['prior'], {'key', 'result'}, where='prior check'); hash_value(check['prior']['key'])
            enum(check['prior']['result'], {'pass', 'fail', 'not_run', 'unknown'})
    return tasks, attempts, artifacts, receipts


def check_key(check):
    return digest({k: check[k] for k in ('inputs', 'outputs', 'code', 'argv', 'environment')})


class Engine:
    def __init__(self, plan, records, current, work, candidate):
        self.plan, self.records = plan, records
        self.tasks, self.attempts, self.artifacts, self.receipts = validate_records(records, plan)
        self.current, self.work, self.candidate = current, work, candidate
        self.blockers = []
        self._validating = set()
        self._accepted = {}
        self._actual_artifacts = {}
        self.recovery = {}
        self.recovery_needs_combination = False
        self.searches = {}
        self.search_checks = []
        self.check_results = []
        self.release = records['release']
        if self.release is None:
            fail('release selection required for audit/stale/release-check')
        self.selected = [self.artifacts[aid] for aid in self.release['artifacts']]
        self.selected_by_path = {a['path']: a for a in self.selected}
        if len(self.selected_by_path) != len(self.selected):
            fail('release has duplicate target versions')
        expected = {p for tid in self.release['tasks'] for p in self.tasks[tid]['writes']}
        if set(self.selected_by_path) != expected or any(a['task'] not in self.release['tasks'] for a in self.selected):
            fail('release tasks/artifacts do not cover the exact full task groups')
        if not self.selected:
            fail('release must select at least one explicit output')
        validate_path_set([a['path'] for a in self.selected])
        self.overlay = {}

    def block(self, reason):
        if reason not in self.blockers:
            self.blockers.append(reason)

    def is_current(self, attempt):
        declared = self.records['current'].get(attempt['task'])
        highest = max(a['generation'] for a in self.attempts.values() if a['task'] == attempt['task'])
        return declared == {'generation': attempt['generation'], 'attempt': attempt['id']} and attempt['generation'] == highest and attempt['status'] in {'finished', 'no_change'}

    def actual_artifact(self, artifact):
        if artifact['id'] not in self._actual_artifacts:
            data = None if artifact['state']['kind'] == 'absent' else self.work.read(artifact['storage'])
            state = {'kind': 'absent'} if data is None else {'kind': 'file', 'sha256': sha(data)}
            if state != artifact['state'] or (artifact['state']['kind'] == 'file' and data is None):
                fail('actual artifact bytes do not match recorded output')
            self._actual_artifacts[artifact['id']] = data
        return self._actual_artifacts[artifact['id']]

    def evidence(self, refs):
        for ref in refs:
            obj(ref, {'path', 'sha256'}, where='evidence reference')
            path(ref['path']); hash_value(ref['sha256'])
            data = self.work.read(ref['path'])
            if data is None or sha(data) != ref['sha256']:
                fail('review evidence missing or changed')

    def group_recovery_match(self, relative, old, now):
        # Preliminary allowance only: evaluate must still validate the exact
        # signed final combination before returning records_valid.
        if relative in self.plan['rules']['files'] or self.release['combination'] is None:
            return False
        artifact = self.selected_by_path.get(relative)
        if artifact is None or now != artifact['state']:
            return False
        producer = self.attempts[artifact['attempt']]
        if producer['baseline']['inputs'].get(relative) != old:
            return False
        self.recovery_needs_combination = True
        return True

    def attempt_valid(self, attempt, stack=None):
        stack = set() if stack is None else stack
        if attempt['id'] in stack:
            return False
        stack = stack | {attempt['id']}
        task = self.tasks[attempt['task']]
        if not self.is_current(attempt) or attempt['contract'] != contract(self.plan, task):
            return False
        baseline = attempt['baseline']
        required = set(self.plan['rules']['files']) | {r['path'] for r in task['reads'] if r['kind'] == 'base'}
        if set(baseline['inputs']) != required | set(task['writes']):
            return False
        outputs = {self.artifacts[aid]['path']: self.artifacts[aid] for aid in attempt['outputs']}
        for relative, old in baseline['inputs'].items():
            if relative in required and old['kind'] != 'file':
                return False
            now = self.current.state(relative)
            # Rule changes cannot be renewed by a content combination receipt.
            if relative in self.plan['rules']['files'] and now != old:
                return False
            if now != old and not (relative in outputs and now == outputs[relative]['state']):
                if attempt['task'] not in self.release['tasks'] or not self.group_recovery_match(relative, old, now):
                    return False
        if len(baseline['searches']) != len(task['searches']):
            return False
        for spec, old in zip(task['searches'], baseline['searches']):
            if old['spec'] != digest(spec):
                return False
        declared = sorted([r for r in task['reads'] if r['kind'] == 'artifact'], key=canonical)
        bound = sorted([{'kind': 'artifact', **{k: r[k] for k in ('task', 'path', 'require')}} for r in attempt['artifact_inputs']], key=canonical)
        if declared != bound:
            return False
        if task['kind'] != 'review' and any(r['require'] == 'candidate' for r in attempt['artifact_inputs']) and attempt['mode'] != 'speculative':
            return False
        for ref in attempt['artifact_inputs']:
            artifact = self.artifacts[ref['artifact']]
            producer = self.attempts[artifact['attempt']]
            if artifact['state']['kind'] != 'file' or not self.is_current(producer):
                return False
            self.actual_artifact(artifact)
            if ref['require'] == 'accepted' and not self.accepted(producer):
                return False
            if ref['require'] == 'candidate' and not self.attempt_valid(producer, stack):
                return False
        if attempt['status'] == 'no_change' and any(a['state'] != baseline['inputs'][a['path']] for a in outputs.values()):
            return False
        return True

    def accepted(self, producer):
        if producer['id'] in self._accepted:
            return self._accepted[producer['id']]
        if producer['id'] in self._validating:
            return False
        self._validating.add(producer['id'])
        try:
            result = self._accepted_impl(producer)
            self._accepted[producer['id']] = result
            return result
        finally:
            self._validating.remove(producer['id'])

    def _accepted_impl(self, producer):
        if producer['mode'] != 'formal' or not self.attempt_valid(producer):
            return False
        task = self.tasks[producer['task']]
        outs = [self.artifacts[aid] for aid in producer['outputs']]
        for artifact in outs:
            self.actual_artifact(artifact)
        # A current release combination can only refresh its explicitly selected
        # tasks. It cannot silently renew an unselected accepted prerequisite.
        if producer['task'] not in self.release['tasks']:
            producer_overlay = {a['path']: self.actual_artifact(a) for a in outs}
            live_searches = [self.search(spec, producer_overlay) for spec in task['searches']]
            if live_searches != producer['baseline']['searches']:
                return False
        if not task['review_by']:
            return task['risk'] == 'low'
        if producer['session'] is None:
            return False
        for reviewer_id in task['review_by']:
            applicable = []
            for receipt in self.receipts.values():
                if receipt['task'] != task['id'] or receipt['producer_attempt'] != producer['id']:
                    continue
                review = self.attempts.get(receipt['review_attempt'])
                if review is None or review['task'] != reviewer_id:
                    continue
                if not self.review_independent(review, [producer]):
                    continue
                if set(receipt['artifact_ids']) != set(producer['outputs']):
                    continue
                if not self.review_covers(review, outs):
                    continue
                if receipt['input_digest'] != input_digest(producer) or receipt['output_digest'] != output_digest(outs) or receipt['acceptance_digest'] != acceptance_digest(task):
                    continue
                self.evidence(receipt['evidence_refs'])
                applicable.append(receipt['decision'])
            if not applicable or any(d != 'accept' for d in applicable):
                return False
        return True

    def review_independent(self, review, producers):
        if self.tasks[review['task']]['kind'] != 'review' or review['mode'] != 'review' or review['status'] != 'finished' or review['session'] is None:
            return False
        if any(p['session'] is None or review['session'] == p['session'] or review['actor'] == p['actor'] or review['task'] == p['task'] for p in producers):
            return False
        # Review's candidate producer is validated separately to avoid accept recursion.
        if not self.is_current(review) or review['contract'] != contract(self.plan, self.tasks[review['task']]):
            return False
        task = self.tasks[review['task']]
        required = set(self.plan['rules']['files']) | {r['path'] for r in task['reads'] if r['kind'] == 'base'}
        if set(review['baseline']['inputs']) != required:
            return False
        for relative, old in review['baseline']['inputs'].items():
            now = self.current.state(relative)
            if old['kind'] != 'file':
                return False
            if now != old and not (all(p['task'] in self.release['tasks'] for p in producers) and self.group_recovery_match(relative, old, now)):
                return False
        declared = sorted([r for r in task['reads'] if r['kind'] == 'artifact'], key=canonical)
        bound = sorted([{'kind': 'artifact', **{k: r[k] for k in ('task', 'path', 'require')}} for r in review['artifact_inputs']], key=canonical)
        if declared != bound:
            return False
        review_overlay = {self.artifacts[ref['artifact']]['path']: self.actual_artifact(self.artifacts[ref['artifact']]) for ref in review['artifact_inputs']}
        expected_searches = [self.search(spec, review_overlay) for spec in task['searches']]
        if review['baseline']['searches'] != expected_searches:
            return False
        for ref in review['artifact_inputs']:
            a = self.artifacts[ref['artifact']]
            if not self.is_current(self.attempts[a['attempt']]):
                return False
            self.actual_artifact(a)
            if ref['require'] == 'accepted' and not self.accepted(self.attempts[a['attempt']]):
                return False
        return True

    @staticmethod
    def review_covers(review, artifacts):
        return all(any(ref['artifact'] == a['id'] and ref['task'] == a['task'] and ref['path'] == a['path'] for ref in review['artifact_inputs']) for a in artifacts)

    def audit(self):
        files = set(self.candidate.files())
        expected = {a['path'] for a in self.selected if a['state']['kind'] == 'file'}
        if files != expected:
            fail('candidate contains unclaimed files or is missing claimed outputs')
        for artifact in self.selected:
            data = self.actual_artifact(artifact)
            candidate_data = self.candidate.read(artifact['path'])
            if candidate_data != data:
                fail('candidate bytes do not match concrete artifact')
            self.overlay[artifact['path']] = data
        return {'schema': 2, 'status': 'audit_valid', 'scope': sorted(self.selected_by_path)}

    def combination_digest_values(self):
        producers = {a['task']: self.attempts[a['attempt']] for a in self.selected}
        return {'input_digest': digest({tid: input_digest(p) for tid, p in producers.items()}),
                'output_digest': output_digest(self.selected),
                'acceptance_digest': digest({tid: self.tasks[tid]['acceptance'] for tid in producers})}

    def valid_combination(self):
        combo = self.release['combination']
        if combo is None:
            return False
        review = self.attempts.get(combo['review_attempt'])
        producers = [self.attempts[a['attempt']] for a in self.selected]
        if review is None or not self.review_independent(review, producers) or not self.review_covers(review, self.selected):
            return False
        if any(combo[k] != v for k, v in self.combination_digest_values().items()):
            return False
        if combo['searches'] != self.searches:
            return False
        self.evidence(combo['evidence_refs'])
        return True

    def evaluate(self, release_check=True):
        self.audit()
        for tid in self.release['tasks']:
            selected = [a for a in self.selected if a['task'] == tid]
            current = self.records['current'].get(tid)
            if current is None or any(a['attempt'] != current['attempt'] for a in selected):
                self.block('selected producer is not the current attempt: ' + tid)
                continue
            producer = self.attempts[current['attempt']]
            if not self.attempt_valid(producer):
                self.block('contract, critical inputs, generation or attempt state changed: ' + tid)
            if producer['mode'] != 'formal':
                self.block('speculative output cannot release: ' + tid)
            if not self.accepted(producer):
                self.block('exact current output lacks all independent acceptances: ' + tid)
            task = self.tasks[tid]
            self.searches[tid] = [self.search(s, self.overlay) for s in task['searches']]
            for artifact in selected:
                old = producer['baseline']['inputs'].get(artifact['path'])
                now = self.current.state(artifact['path'])
                new = artifact['state']
                self.recovery[artifact['path']] = 'old_continue' if now == old else ('new_already_applied' if now == new else 'third_preserve_and_stop')
                if now != old and now != new:
                    self.block('target has third-party bytes: ' + artifact['path'])
            for ref in producer['artifact_inputs']:
                prerequisite = self.artifacts[ref['artifact']]
                if prerequisite['id'] not in self.release['artifacts'] and self.current.state(prerequisite['path']) != prerequisite['state']:
                    self.block('accepted prerequisite is neither published nor in release group: ' + prerequisite['task'])
        combo_valid = self.valid_combination()
        if (len(self.selected) > 1 or self.recovery_needs_combination) and not combo_valid:
            self.block('final multi-path group requires targeted independent combination review')
        for tid, results in self.searches.items():
            producer = self.attempts[self.records['current'][tid]['attempt']]
            if results != producer['baseline']['searches'] and not combo_valid:
                self.block('bounded literal search changed; fresh bound review required: ' + tid)
        if release_check:
            p = self.release['publisher']
            if p['confirmed'] is not True or p['contenders'] != [p['session']] or p['targets_saved'] is not True or p['external_writers_controlled'] is not True or p['cancellation_state'] == 'unknown':
                self.block('single publisher/saved targets/external writers/cancellation declaration unconfirmed')
        self.verify_checks()
        return {'schema': 2, 'status': 'blocked' if self.blockers else ('records_valid' if release_check else 'base_matches'),
                'blockers': self.blockers, 'recovery': self.recovery, 'searches': self.searches,
                'checks': self.check_results,
                'no_change_conclusions': sum(self.attempts[self.records['current'][tid]['attempt']]['status'] == 'no_change' for tid in self.release['tasks'] if tid in self.records['current']),
                'limits': ['records consistency only; no knowledge certification, identity authentication, lock or write authorization', 'actual model/effort/cost unknown unless externally evidenced; no throughput claim']}

    def verify_checks(self):
        for check in record_index(self.records['checks'], 'checks').values():
            actual = {'inputs': {p: self.current.state(p) for p in check['inputs']},
                      'outputs': {p: self.candidate.state(p) for p in check['outputs']},
                      'code': {p: self.work.state(p, required=True) for p in check['code']},
                      'argv': check['argv'], 'environment': check['environment']}
            key = digest(actual)
            matches = key == check['key'] == check_key(check)
            prior = check.get('prior')
            if not matches:
                status = 'stale'
                self.block('check inputs/output/code/parameters/environment key changed: ' + check['id'])
            elif check['result'] != 'pass':
                status = check['result']
                self.block('required recorded check did not pass: ' + check['id'])
            elif prior is not None and prior['key'] == key and prior['result'] == 'pass':
                status = 'reused'
            else:
                status = 'recorded_pass'
            self.check_results.append({'id': check['id'], 'status': status, 'key': key})

    def search(self, specification, overlay):
        result = search_matches(specification, self.current, overlay)
        self.search_checks.append((specification, dict(overlay), result))
        return result

    def final_verify(self):
        if set(self.candidate.files()) != {a['path'] for a in self.selected if a['state']['kind'] == 'file'}:
            fail('candidate tree changed before completion')
        for specification, overlay, expected in self.search_checks:
            if search_matches(specification, self.current, overlay) != expected:
                fail('search matches changed before completion')


def distinct_roots(roots):
    for i, a in enumerate(roots):
        for b in roots[i + 1:]:
            if a.location == b.location or a.location in b.location.parents or b.location in a.location.parents:
                fail('current/work/candidate roots must be separate nonoverlapping directories')
            if (a.identity.st_dev, a.identity.st_ino) == (b.identity.st_dev, b.identity.st_ino):
                fail('roots alias the same directory')


def parser():
    result = argparse.ArgumentParser(description=__doc__, epilog='All commands are read-only. schema 1 is unsupported legacy; no local format was available. See scripts/COORDINATION.md for examples and record shapes.')
    subs = result.add_subparsers(dest='command', required=True)
    for command in ('plan', 'snapshot', 'audit', 'stale', 'release-check'):
        sub = subs.add_parser(command, help={'plan': 'validate schema-2 contracts', 'snapshot': 'print old-byte/input bindings', 'audit': 'compare isolated sparse candidate with claimed artifacts', 'stale': 'check current versions and acceptance bindings', 'release-check': 'validate proposed release records, never publish'}[command])
        sub.add_argument('--plan', required=True, help='schema-2 plan JSON')
        if command != 'plan':
            sub.add_argument('--current-root', required=True, help='current main vault; read-only')
        if command in {'audit', 'stale', 'release-check'}:
            sub.add_argument('--records', required=True, help='schema-2 attempt/artifact/review/release JSON')
            sub.add_argument('--candidate', required=True, help='isolated sparse final candidate tree')
            sub.add_argument('--work-root', required=True, help='isolated artifact/evidence/check-code root')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    roots = []
    engine = None
    try:
        plan = load_json_file(args.plan, roots)
        tasks = validate_plan(plan)
        if args.command == 'plan':
            output = {'schema': 2, 'status': 'plan_valid', 'contracts': {tid: contract(plan, t) for tid, t in tasks.items()}, 'limits': 'structure only; not readiness, permission, facts or publication'}
        else:
            current = Root(args.current_root); roots.append(current)
            if args.command == 'snapshot':
                output = snapshot(plan, current)
            else:
                records = load_json_file(args.records, roots)
                work, candidate = Root(args.work_root), Root(args.candidate)
                roots.extend((work, candidate)); distinct_roots([current, work, candidate])
                engine = Engine(plan, records, current, work, candidate)
                output = engine.audit() if args.command == 'audit' else engine.evaluate(args.command == 'release-check')
        if args.command == 'snapshot' and output != snapshot(plan, current):
            fail('snapshot inputs or bounded search changed before completion')
        if engine is not None:
            engine.final_verify()
        for root in roots:
            root.verify()
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 2 if output.get('status') == 'blocked' else 0
    except (Invalid, OSError, TypeError, KeyError, RecursionError) as exc:
        # Avoid exception repr: JSON/private bytes and system paths are not echoed.
        message = str(exc) if isinstance(exc, Invalid) else 'invalid/unavailable records or filesystem state'
        print(json.dumps({'schema': 2, 'status': 'error', 'message': message}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        for root in reversed(roots):
            root.close()


if __name__ == '__main__':
    sys.exit(main())
