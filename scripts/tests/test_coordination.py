"""Behavioral contracts for the read-only coordination checker (no network)."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / 'coordination.py'
spec = importlib.util.spec_from_file_location('coordination', MODULE)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def file_state(data):
    return {'kind': 'file', 'sha256': hashlib.sha256(data).hexdigest()}


def write(root, path, data):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def task(tid, writes=(), reads=(), kind='author', reviewers=(), risk='normal'):
    return {'id': tid, 'kind': kind, 'goal': 'Explain a bounded reader question ' + tid,
            'writes': list(writes), 'reads': list(reads), 'risk': risk,
            'acceptance': ['Verify exact explanation and units'], 'review_by': list(reviewers),
            'forbidden': [], 'searches': []}


def artifact_read(tid, p, require='candidate'):
    return {'kind': 'artifact', 'task': tid, 'path': p, 'require': require}


class Fixture:
    def __init__(self, base, count=1, low=False):
        self.base = Path(base)
        self.current, self.work, self.candidate = [self.base / n for n in ('current', 'work', 'candidate')]
        for p in (self.current, self.work, self.candidate):
            p.mkdir(parents=True, exist_ok=True)
        write(self.current, 'AGENTS.md', b'Bounded fixture rules v1\n')
        write(self.work, 'evidence/review.txt', b'Independent fixture review: explicit objects, units, explanation responsibility.\n')
        self.plan = {'schema': 2, 'batch': 'fixture', 'rules': {'version': 'C1', 'files': ['AGENTS.md']},
                     'human_files': [], 'shared_files': [], 'tasks': []}
        for i in range(count):
            tid, p, rid = f'a{i}', f'notes/{i}.md', f'r{i}'
            write(self.current, p, f'old {i}\n'.encode())
            write(self.work, f'outputs/{i}.md', f'new {i}\n'.encode())
            write(self.candidate, p, f'new {i}\n'.encode())
            self.plan['tasks'].append(task(tid, [p], reviewers=[] if low else [rid], risk='low' if low else 'normal'))
            if not low:
                self.plan['tasks'].append(task(rid, reads=[artifact_read(tid, p)], kind='review'))
        if count > 1:
            self.plan['tasks'].append(task('combo', kind='review', reads=[artifact_read(f'a{i}', f'notes/{i}.md') for i in range(count)]))
        self.records = None
        self.bind()

    def bind(self):
        root = c.Root(self.current)
        try:
            snap = c.snapshot(self.plan, root)
        finally:
            root.close()
        route = {'model': 'unknown', 'effort': 'unknown', 'supported_efforts': 'unknown'}
        self.records = {'schema': 2, 'batch': 'fixture', 'current': {}, 'attempts': [], 'artifacts': [], 'receipts': [], 'release': None, 'checks': []}
        for t in self.plan['tasks']:
            tid = t['id']; aid = tid + '-attempt'
            refs = [{'task': r['task'], 'path': r['path'], 'require': r['require'], 'artifact': r['task'] + '-artifact', 'producer_attempt': r['task'] + '-attempt', 'state': file_state((self.work / ('outputs/' + r['task'][1:] + '.md')).read_bytes())} for r in t['reads'] if r['kind'] == 'artifact']
            a = {'id': aid, 'task': tid, 'contract': snap['tasks'][tid]['contract'], 'generation': 1,
                 'session': tid + '-real-session', 'actor': tid + '-actor', 'mode': 'review' if t['kind'] == 'review' else 'formal',
                 'status': 'finished', 'baseline': snap['tasks'][tid], 'artifact_inputs': refs,
                 'outputs': [tid + '-artifact'] if t['writes'] else [], 'requested': copy.deepcopy(route), 'observed': copy.deepcopy(route), 'usage_ref': None}
            self.records['attempts'].append(a)
            self.records['current'][tid] = {'generation': 1, 'attempt': aid}
            for p in t['writes']:
                index = tid[1:]
                storage = f'outputs/{index}.md'
                self.records['artifacts'].append({'id': tid + '-artifact', 'task': tid, 'attempt': aid,
                                                  'path': p, 'state': file_state((self.work / storage).read_bytes()), 'storage': storage})
        for t in self.plan['tasks']:
            if not t['writes']:
                continue
            a = self.attempt(t['id'])
            for reviewer in t['review_by']:
                self.records['receipts'].append({'id': t['id'] + '-' + reviewer + '-receipt', 'task': t['id'],
                    'producer_attempt': a['id'], 'review_attempt': reviewer + '-attempt', 'artifact_ids': a['outputs'][:],
                    'input_digest': c.input_digest(a), 'output_digest': c.output_digest([self.artifact(t['id'])]),
                    'acceptance_digest': c.acceptance_digest(t), 'decision': 'accept', 'basis': 'Independent exact fixture review',
                    'evidence_refs': self.evidence()})
        authors = [t['id'] for t in self.plan['tasks'] if t['writes']]
        self.records['release'] = {'tasks': authors, 'artifacts': [tid + '-artifact' for tid in authors],
            'publisher': {'session': 'coordinator', 'confirmed': True, 'contenders': ['coordinator'], 'targets_saved': True,
                          'external_writers_controlled': True, 'cancellation_state': 'none'}, 'combination': None}
        if len(authors) > 1:
            self.refresh_combo()

    def evidence(self):
        return [{'path': 'evidence/review.txt', 'sha256': hashlib.sha256((self.work / 'evidence/review.txt').read_bytes()).hexdigest()}]

    def attempt(self, tid):
        return next(a for a in self.records['attempts'] if a['task'] == tid)

    def artifact(self, tid):
        return next(a for a in self.records['artifacts'] if a['task'] == tid)

    def task(self, tid):
        return next(t for t in self.plan['tasks'] if t['id'] == tid)

    def engine(self):
        roots = [c.Root(p) for p in (self.current, self.work, self.candidate)]
        return c.Engine(self.plan, self.records, *roots), roots

    def result(self):
        e, roots = self.engine()
        try:
            result = e.evaluate()
            e.final_verify()
            for r in roots:
                r.verify()
            return result
        finally:
            for r in roots:
                r.close()

    def refresh_combo(self, reviewer='combo'):
        e, roots = self.engine()
        try:
            e.audit()
            searches = {tid: [c.search_matches(s, roots[0], e.overlay) for s in self.task(tid)['searches']] for tid in self.records['release']['tasks']}
            self.records['release']['combination'] = {'review_attempt': reviewer + '-attempt', **e.combination_digest_values(),
                'basis': 'Final group checked: objects, units and definition responsibility remain present.',
                'evidence_refs': self.evidence(), 'searches': searches}
        finally:
            for r in roots:
                r.close()

    def save(self):
        for name, data in [('plan.json', self.plan), ('records.json', self.records)]:
            (self.base / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        # Author can constrain test output to an isolated delegated directory.
        location = Path(os.environ.get('COORDINATION_TEST_TMP', tempfile.gettempdir())).resolve()
        self.tmp = tempfile.TemporaryDirectory(prefix='coordination-test-', dir=location)
        self.f = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def blocked(self):
        self.assertEqual(self.f.result()['status'], 'blocked')

    def test_minimal_real_candidate_and_readonly_cli(self):
        self.assertEqual(self.f.result()['status'], 'records_valid')
        self.f.save()
        before = {str(p.relative_to(self.f.base)): p.read_bytes() for p in self.f.base.rglob('*') if p.is_file()}
        for cmd in ('plan', 'snapshot', 'audit', 'stale', 'release-check'):
            args = [sys.executable, '-B', str(MODULE), cmd, '--plan', str(self.f.base / 'plan.json')]
            if cmd != 'plan':
                args += ['--current-root', str(self.f.current)]
            if cmd in {'audit', 'stale', 'release-check'}:
                args += ['--records', str(self.f.base / 'records.json'), '--candidate', str(self.f.candidate), '--work-root', str(self.f.work)]
            run = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertNotIn('published', json.loads(run.stdout).get('status', ''))
            help_run = subprocess.run([sys.executable, '-B', str(MODULE), cmd, '--help'], capture_output=True)
            self.assertEqual(help_run.returncode, 0)
        after = {str(p.relative_to(self.f.base)): p.read_bytes() for p in self.f.base.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_T01_32_routes_and_T02_reordering_unrelated_addition(self):
        f = Fixture(self.f.base / 'many', 32, low=True)
        old = {t['id']: c.contract(f.plan, t) for t in f.plan['tasks']}
        f.attempt('a31')['requested'] = {'model': 'declared-model', 'effort': 'high', 'supported_efforts': ['high']}
        f.attempt('a31')['notes'] = {'price': 'unknown'}
        f.plan['tasks'].reverse()
        write(f.current, 'unrelated.md', b'human unrelated update')
        f.plan['tasks'].append(task('unrelated', kind='evidence'))
        for t in f.plan['tasks']:
            if t['id'] in old:
                self.assertEqual(c.contract(f.plan, t), old[t['id']])
        self.assertEqual(f.result()['status'], 'records_valid')
        f.task('a31')['goal'] = 'A materially different question'
        self.assertNotEqual(c.contract(f.plan, f.task('a31')), old['a31'])
        self.assertEqual(f.result()['status'], 'blocked')

    def test_T03_old_base_reads_allow_parallel_future_reads_cycle(self):
        f = Fixture(self.f.base / 'two', 2)
        f.task('a0')['reads'] = [{'kind': 'base', 'path': 'notes/1.md'}]
        f.task('a1')['reads'] = [{'kind': 'base', 'path': 'notes/0.md'}]
        f.bind()
        self.assertEqual(f.result()['status'], 'records_valid')
        f.task('a0')['reads'] = [artifact_read('a1', 'notes/1.md', 'accepted')]
        f.task('a1')['reads'] = [artifact_read('a0', 'notes/0.md', 'accepted')]
        with self.assertRaisesRegex(c.Invalid, 'cycle'):
            c.validate_plan(f.plan)

    def test_T04_required_base_missing_and_target_new_absent_distinct(self):
        self.f.task('a0')['reads'] = [{'kind': 'base', 'path': 'missing.md'}]
        with self.assertRaisesRegex(c.Invalid, 'required input'):
            self.f.bind()
        self.f.task('a0')['reads'] = []
        (self.f.current / 'notes/0.md').unlink()
        self.f.bind()
        self.assertEqual(self.f.attempt('a0')['baseline']['inputs']['notes/0.md'], {'kind': 'absent'})
        self.assertEqual(self.f.result()['status'], 'records_valid')
        (self.f.work / 'outputs/0.md').unlink()
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_T05_all_designated_reviews_finished_accept_and_conflict(self):
        for status in ('running', 'unknown', 'revoked'):
            with self.subTest(status=status):
                self.f.attempt('r0')['status'] = status
                self.blocked()
        self.f.attempt('r0')['status'] = 'finished'
        for decision in ('reject', 'pending'):
            self.f.records['receipts'][0]['decision'] = decision
            self.blocked()
        self.f.records['receipts'][0]['decision'] = 'accept'
        reject = copy.deepcopy(self.f.records['receipts'][0]); reject['id'] = 'conflict'; reject['decision'] = 'reject'
        self.f.records['receipts'].append(reject)
        self.blocked()

    def test_T06_unknown_kind_and_self_reviewer_cannot_bypass(self):
        for kind in ('publish', 'custom'):
            self.f.task('a0')['kind'] = kind
            with self.assertRaises(c.Invalid):
                c.validate_plan(self.f.plan)
        self.f.task('a0')['kind'] = 'author'
        self.f.task('a0')['review_by'] = ['a0']
        with self.assertRaises(c.Invalid):
            c.validate_plan(self.f.plan)

    def test_T07_actual_output_tamper_and_input_acceptance_change(self):
        write(self.f.candidate, 'notes/0.md', b'changed single byte')
        with self.assertRaises(c.Invalid):
            self.f.result()
        write(self.f.candidate, 'notes/0.md', b'new 0\n')
        self.f.task('a0')['acceptance'].append('New necessary units check')
        self.blocked()

    def test_T07_rehash_output_does_not_refresh_receipt(self):
        data = b'new version after review'
        write(self.f.work, 'outputs/0.md', data); write(self.f.candidate, 'notes/0.md', data)
        self.f.artifact('a0')['state'] = file_state(data)
        with self.assertRaisesRegex(c.Invalid, 'binding mismatch'):
            self.f.result()
        self.f.attempt('r0')['artifact_inputs'][0]['state'] = file_state(data)
        self.blocked()

    def test_independent_sessions_actors_and_evidence_actual_bytes(self):
        for field in ('session', 'actor'):
            old = self.f.attempt('r0')[field]
            self.f.attempt('r0')[field] = self.f.attempt('a0')[field]
            self.blocked(); self.f.attempt('r0')[field] = old
        self.f.attempt('a0')['session'] = None
        self.blocked()
        self.f.attempt('a0')['session'] = 'a0-real-session'
        write(self.f.work, 'evidence/review.txt', b'changed evidence')
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_T08_current_highest_generation_and_idempotent_terminal(self):
        self.f.records['receipts'].append(copy.deepcopy(self.f.records['receipts'][0]))
        self.assertEqual(self.f.result()['status'], 'records_valid')
        newer = copy.deepcopy(self.f.attempt('a0')); newer.update(id='new-attempt', generation=2, status='unknown', outputs=[])
        self.f.records['attempts'].append(newer)
        self.blocked()
        self.f.records['current']['a0'] = {'generation': 2, 'attempt': 'new-attempt'}
        self.blocked()

    def test_T09_strict_json_schema_nested_fields_and_effort(self):
        with self.assertRaisesRegex(c.Invalid, 'duplicate'):
            c.decode_json(b'{"schema":2,"schema":2}')
        with self.assertRaises(c.Invalid):
            c.decode_json(b'{"x":NaN}')
        for schema in (1, 3, True):
            p = copy.deepcopy(self.f.plan); p['schema'] = schema
            with self.assertRaises(c.Invalid):
                c.validate_plan(p)
        for target, field in ((self.f.plan, 'human_fiels'), (self.f.plan['rules'], 'protection'), (self.f.task('a0'), 'protected_files')):
            target[field] = []
            with self.assertRaises(c.Invalid):
                c.validate_plan(self.f.plan)
            del target[field]
        self.f.attempt('a0')['requested']['effort'] = 'typo'
        with self.assertRaises(c.Invalid):
            self.f.result()
        self.f.attempt('a0')['requested']['effort'] = 'high'
        self.f.attempt('a0')['requested']['supported_efforts'] = ['low']
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_T10_paths_lexical_case_unicode_components_parent(self):
        for p in ('../x', '/x', 'C:/x', 'a\\x', 'a//x', 'a/./x', 'e\u0301.md', 'a/ x'):
            with self.subTest(path=p), self.assertRaises(c.Invalid):
                c.path(p)
        for ps in (['Dir/a', 'dir/b'], ['x', 'x/a'], ['A', 'a']):
            with self.assertRaises(c.Invalid):
                c.validate_path_set(ps)
        self.f.task('a0')['forbidden'] = ['NOTES']
        with self.assertRaises(c.Invalid):
            c.validate_plan(self.f.plan)

    def test_T10_symlink_and_hardlink_reject_before_content(self):
        p = self.f.candidate / 'notes/0.md'; p.unlink()
        p.symlink_to(self.f.current / 'notes/0.md')
        with self.assertRaises(c.Invalid):
            self.f.result()
        p.unlink(); os.link(self.f.work / 'outputs/0.md', p)
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_T11_unclaimed_hidden_file_and_unrelated_human_file(self):
        write(self.f.current, '.personal-settings', b'unrelated user state')
        self.assertEqual(self.f.result()['status'], 'records_valid')
        write(self.f.candidate, '.obsidian/hidden.json', b'{}')
        with self.assertRaisesRegex(c.Invalid, 'unclaimed'):
            self.f.result()

    def test_T12_new_human_protection_and_unknown_editor_state(self):
        self.f.plan['human_files'].append('notes/0.md')
        with self.assertRaises(c.Invalid):
            self.f.result()
        self.f.plan['human_files'] = []
        self.f.records['release']['publisher']['targets_saved'] = None
        self.blocked()

    def test_T13_dependency_group_or_already_published_upstream(self):
        f = Fixture(self.f.base / 'deps', 2)
        f.task('a1')['reads'] = [artifact_read('a0', 'notes/0.md', 'accepted')]
        f.bind()
        self.assertEqual(f.result()['status'], 'records_valid')
        f.records['release'].update(tasks=['a1'], artifacts=['a1-artifact'], combination=None)
        (f.candidate / 'notes/0.md').unlink()
        self.assertEqual(f.result()['status'], 'blocked')
        write(f.current, 'notes/0.md', b'new 0\n')
        self.assertEqual(f.result()['status'], 'records_valid')
        f.records['receipts'][0]['decision'] = 'reject'
        self.assertEqual(f.result()['status'], 'blocked')

    def test_T14_individual_accepts_need_final_combination(self):
        f = Fixture(self.f.base / 'combo', 2)
        f.records['release']['combination'] = None
        self.assertEqual(f.result()['status'], 'blocked')
        f.refresh_combo()
        self.assertEqual(f.result()['status'], 'records_valid')
        f.records['release']['combination']['output_digest'] = '0' * 64
        self.assertEqual(f.result()['status'], 'blocked')

    def test_T15_literal_search_refresh_relevant_unrelated_and_own_new_match(self):
        s = {'scopes': ['notes'], 'literals': ['alias', 'synonym'], 'extensions': ['.md'], 'max_files': 20, 'max_bytes': 10000, 'case_sensitive': False}
        self.f.task('a0')['searches'] = [s]; self.f.bind()
        write(self.f.current, 'notes/unrelated.md', b'unrelated concept')
        self.assertEqual(self.f.result()['status'], 'records_valid')
        write(self.f.current, 'notes/related.md', b'SYNONYM explanation')
        self.blocked()
        self.f.refresh_combo('r0')
        self.assertEqual(self.f.result()['status'], 'records_valid')
        write(self.f.current, 'notes/related2.md', b'another alias')
        self.blocked()

    def test_search_bounds_before_read_and_no_eval(self):
        s = {'scopes': ['notes'], 'literals': ['__import__("os")'], 'extensions': ['.md'], 'max_files': 20, 'max_bytes': 3, 'case_sensitive': True}
        root = c.Root(self.f.current)
        try:
            with mock.patch.object(c.os, 'read', wraps=c.os.read) as read:
                with self.assertRaisesRegex(c.Invalid, 'before read'):
                    c.search_matches(s, root)
                read.assert_not_called()
        finally:
            root.close()

    def test_T16_speculative_requires_rebinding_and_reacceptance(self):
        f = Fixture(self.f.base / 'spec', 2)
        f.task('a1')['reads'] = [artifact_read('a0', 'notes/0.md', 'candidate')]
        f.bind()
        self.assertEqual(f.result()['status'], 'blocked')
        f.attempt('a1')['mode'] = 'speculative'
        self.assertEqual(f.result()['status'], 'blocked')
        f.task('a1')['reads'][0]['require'] = 'accepted'
        f.bind()
        self.assertEqual(f.result()['status'], 'records_valid')

    def test_T17_reuse_actual_bytes_code_args_environment_not_mtime(self):
        write(self.f.work, 'checks/check.py', b'assert True\n')
        chk = {'id': 'check', 'inputs': {'notes/0.md': file_state(b'old 0\n')}, 'outputs': {'notes/0.md': file_state(b'new 0\n')},
               'code': {'checks/check.py': file_state(b'assert True\n')}, 'argv': ['python3', '-B', 'checks/check.py'], 'environment': {'python': 'fixture-3'}, 'result': 'pass'}
        chk['key'] = c.check_key(chk); chk['prior'] = {'key': chk['key'], 'result': 'pass'}
        self.f.records['checks'] = [chk]
        self.assertEqual(self.f.result()['checks'][0]['status'], 'reused')
        for field in ('argv', 'environment'):
            original = copy.deepcopy(chk[field])
            chk[field] = ['changed'] if field == 'argv' else {'python': 'changed'}
            self.blocked(); chk[field] = original
        p = self.f.work / 'checks/check.py'; st = p.stat(); p.write_bytes(b'assert None\n'); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.blocked()

    def test_T18_recovery_old_new_third_no_writes(self):
        self.assertEqual(self.f.result()['recovery']['notes/0.md'], 'old_continue')
        write(self.f.current, 'notes/0.md', b'new 0\n')
        self.assertEqual(self.f.result()['recovery']['notes/0.md'], 'new_already_applied')
        write(self.f.current, 'notes/0.md', b'human third bytes')
        result = self.f.result()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['recovery']['notes/0.md'], 'third_preserve_and_stop')
        self.assertEqual((self.f.current / 'notes/0.md').read_bytes(), b'human third bytes')

    def test_T19_control_declarations_only_unknown_never_frees_control(self):
        p = self.f.records['release']['publisher']
        p['contenders'].append('other-session'); self.blocked()
        p['contenders'] = ['coordinator']; p['cancellation_state'] = 'unknown'; self.blocked()
        p['cancellation_state'] = 'none'; p['external_writers_controlled'] = None; self.blocked()

    def test_T25_no_change_not_improvement_and_conflicting_duplicate(self):
        write(self.f.work, 'outputs/0.md', b'old 0\n'); write(self.f.candidate, 'notes/0.md', b'old 0\n')
        self.f.bind(); self.f.attempt('a0')['status'] = 'no_change'
        self.assertEqual(self.f.result()['no_change_conclusions'], 1)
        self.assertNotIn('improved_problems', self.f.result())
        duplicate = copy.deepcopy(self.f.attempt('a0')); duplicate['status'] = 'finished'
        self.f.records['attempts'].append(duplicate)
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_in_read_mutation_and_final_reread_fail_closed(self):
        root = c.Root(self.f.current)
        real_read = c.os.read
        changed = False
        def mutating_read(fd, count):
            nonlocal changed
            data = real_read(fd, count)
            if data and not changed:
                changed = True
                write(self.f.current, 'notes/0.md', b'tampered during read')
            return data
        try:
            with mock.patch.object(c.os, 'read', side_effect=mutating_read):
                with self.assertRaisesRegex(c.Invalid, 'changed during read'):
                    root.read('notes/0.md')
            root.read('AGENTS.md'); write(self.f.current, 'AGENTS.md', b'new rules')
            with self.assertRaisesRegex(c.Invalid, 'before completion'):
                root.verify()
        finally:
            root.close()

    def test_new_matching_file_during_final_search_is_detected(self):
        self.f.task('a0')['searches'] = [{'scopes': ['notes'], 'literals': ['alias'], 'extensions': ['.md'], 'max_files': 20, 'max_bytes': 10000, 'case_sensitive': False}]
        self.f.bind()
        engine, roots = self.f.engine()
        try:
            self.assertEqual(engine.evaluate()['status'], 'records_valid')
            write(self.f.current, 'notes/new.md', b'alias')
            with self.assertRaisesRegex(c.Invalid, 'search matches changed'):
                engine.final_verify()
        finally:
            for root in roots:
                root.close()


    def test_declared_review_search_is_an_input(self):
        search = {'scopes': ['notes'], 'literals': ['alias'], 'extensions': ['.md'], 'max_files': 20, 'max_bytes': 10000, 'case_sensitive': False}
        self.f.task('r0')['searches'] = [search]; self.f.bind()
        self.assertEqual(self.f.result()['status'], 'records_valid')
        write(self.f.current, 'notes/alias.md', b'alias explanation')
        self.blocked()

    def test_two_designated_reviewers_all_required(self):
        self.f.plan['tasks'].append(task('second-review', kind='review', reads=[artifact_read('a0', 'notes/0.md')]))
        self.f.task('a0')['review_by'].append('second-review'); self.f.bind()
        self.assertEqual(self.f.result()['status'], 'records_valid')
        self.f.records['receipts'].pop()
        self.blocked()

    def test_rule_bytes_base_inputs_bool_generation_and_unauthorized_receipt(self):
        write(self.f.current, 'AGENTS.md', b'changed safety boundary')
        self.blocked()
        write(self.f.current, 'AGENTS.md', b'Bounded fixture rules v1\n')
        self.f.attempt('a0')['generation'] = True
        with self.assertRaises(c.Invalid):
            self.f.result()
        self.f.attempt('a0')['generation'] = 1
        self.f.records['receipts'][0]['review_attempt'] = 'a0-attempt'
        self.blocked()

    def test_explicit_deletion_and_move_pair_and_absent_reviewer_input(self):
        # A move is an independently reviewed delete/create pair, not an implicit rename.
        f = Fixture(self.f.base / 'move', 2)
        (f.current / 'notes/1.md').unlink()
        f.bind()
        old_artifact = f.artifact('a0')
        old_artifact['state'] = {'kind': 'absent'}; old_artifact['storage'] = None
        (f.candidate / 'notes/0.md').unlink()
        for a in f.records['attempts']:
            for ref in a['artifact_inputs']:
                if ref['task'] == 'a0':
                    ref['state'] = {'kind': 'absent'}
        for receipt in f.records['receipts']:
            if receipt['task'] == 'a0':
                receipt['output_digest'] = c.output_digest([old_artifact])
        f.refresh_combo()
        self.assertEqual(f.result()['status'], 'records_valid')
        # A formal author cannot consume a deletion as an existing accepted input.
        f.task('a1')['reads'] = [artifact_read('a0', 'notes/0.md', 'accepted')]
        a = f.attempt('a1'); a['contract'] = c.contract(f.plan, f.task('a1')); a['baseline']['contract'] = a['contract']
        a['artifact_inputs'] = [{'task': 'a0', 'path': 'notes/0.md', 'require': 'accepted', 'artifact': 'a0-artifact', 'producer_attempt': 'a0-attempt', 'state': {'kind': 'absent'}}]
        self.assertEqual(f.result()['status'], 'blocked')

    def test_ancestor_swap_to_symlink_is_not_followed(self):
        root = c.Root(self.f.current)
        original = self.f.current
        moved = self.f.base / 'renamed-current'
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        try:
            with self.assertRaisesRegex(c.Invalid, 'real directory'):
                root.verify()
            with self.assertRaisesRegex(c.Invalid, 'real directory'):
                c.Root(original / 'notes')
        finally:
            root.close(); original.unlink(); moved.rename(original)


    def test_unselected_accepted_prerequisite_search_cannot_auto_refresh(self):
        f = Fixture(self.f.base / 'upstream-search', 2)
        f.task('a0')['searches'] = [{'scopes': ['notes'], 'literals': ['alias'], 'extensions': ['.md'], 'max_files': 20, 'max_bytes': 10000, 'case_sensitive': False}]
        f.task('a1')['reads'] = [artifact_read('a0', 'notes/0.md', 'accepted')]
        f.bind()
        f.records['release'].update(tasks=['a1'], artifacts=['a1-artifact'], combination=None)
        (f.candidate / 'notes/0.md').unlink(); write(f.current, 'notes/0.md', b'new 0\n')
        self.assertEqual(f.result()['status'], 'records_valid')
        write(f.current, 'notes/related.md', b'alias changed after acceptance')
        self.assertEqual(f.result()['status'], 'blocked')


    def test_checks_require_code_command_and_unique_identity(self):
        write(self.f.work, 'checks/check.py', b'assert True\n')
        chk = {'id': 'check', 'inputs': {}, 'outputs': {}, 'code': {'checks/check.py': file_state(b'assert True\n')},
               'argv': ['python3', 'checks/check.py'], 'environment': {}, 'result': 'pass'}
        chk['key'] = c.check_key(chk); chk['prior'] = {'key': chk['key'], 'result': 'pass'}
        self.f.records['checks'] = [chk, copy.deepcopy(chk)]
        self.assertEqual(len(self.f.result()['checks']), 1)
        self.f.records['checks'][1]['argv'] = ['conflicting command']
        with self.assertRaisesRegex(c.Invalid, 'conflicting duplicate'):
            self.f.result()
        self.f.records['checks'] = [chk]
        chk['code'] = {}; chk['argv'] = []; chk['key'] = c.check_key(chk); chk['prior']['key'] = chk['key']
        with self.assertRaises(c.Invalid):
            self.f.result()

    def test_missing_cli_json_file_is_versioned_error(self):
        run = subprocess.run([sys.executable, '-B', str(MODULE), 'plan', '--plan', str(self.f.base / 'does-not-exist.json')], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stderr)['status'], 'error')
        self.assertNotIn('Traceback', run.stderr)


    def test_mutual_old_base_group_partial_recovery_requires_exact_combo(self):
        f = Fixture(self.f.base / 'mutual-recovery', 2)
        f.task('a0')['reads'] = [{'kind': 'base', 'path': 'notes/1.md'}]
        f.task('a1')['reads'] = [{'kind': 'base', 'path': 'notes/0.md'}]
        f.bind()
        self.assertEqual(f.result()['status'], 'records_valid')
        write(f.current, 'notes/0.md', b'new 0\n')
        result = f.result()
        self.assertEqual(result['status'], 'records_valid')
        self.assertEqual(result['recovery'], {'notes/0.md': 'new_already_applied', 'notes/1.md': 'old_continue'})
        f.records['release']['combination']['output_digest'] = '0' * 64
        self.assertEqual(f.result()['status'], 'blocked')
        f.refresh_combo()
        write(f.current, 'notes/0.md', b'third party edit')
        self.assertEqual(f.result()['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
