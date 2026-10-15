import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import github_askpass
import github_secret_scan as scan
import github_sync as sync


class SecretChecks(unittest.TestCase):
    def test_github_value_is_redacted(self):
        value = 'ghp_' + 'A' * 36
        self.assertEqual(scan.categories(value.encode()), ['github-token'])
        self.assertNotIn(value, scan.redact('failure: ' + value))

    def test_wrong_hostname_refuses_credential(self):
        for url in ['https://github.com.evil.invalid', 'https://other.invalid', 'https://github.com@evil.invalid', 'https://github.com:8443']:
            with self.assertRaises(ValueError):
                github_askpass.response("Password for '" + url + "': ", 'not-a-real-secret')

    def test_username_and_password_channels(self):
        self.assertEqual(github_askpass.response("Username for 'https://github.com': ", 'example'), 'x-access-token')
        self.assertEqual(github_askpass.response("Password for 'https://x-access-token@github.com': ", 'example'), 'example')

    def test_protected_paths(self):
        for name in ['.env', 'lab/.env.local', 'tls/example.key', '.obsidian/plugins/service/data.json', '.obsidian/workspace.json', scan.REVIEWED_CSS_PATH, 'lab/node_modules/a.js', 'scripts/__pycache__/a.pyc']:
            self.assertTrue(scan.protected_path(name))
        self.assertFalse(scan.protected_path('.obsidian/types.json'))
        self.assertFalse(scan.protected_path('数学/01-对象.md'))


class HistoryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.run_git('init', '-b', 'main')
        self.run_git('config', 'user.name', 'WWL test')
        self.run_git('config', 'user.email', 'test@example.invalid')
        self.run_git('config', 'commit.gpgsign', 'false')
        (self.repo / 'empty-hooks').mkdir()
        self.run_git('config', 'core.hooksPath', str(self.repo / 'empty-hooks'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, name, data):
        (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / name).write_bytes(data)
        self.run_git('add', '--', name)
        self.run_git('commit', '-m', 'fixture')
        return self.run_git('rev-parse', 'HEAD')

    def test_removed_secret_in_unpushed_history_still_blocks(self):
        base = self.commit('note.txt', b'safe')
        secret = ('ghp_' + 'B' * 36).encode()
        self.commit('note.txt', secret)
        self.commit('note.txt', b'clean again')
        findings = scan.scan_pending(self.repo, 'HEAD', base)['findings']
        self.assertIn('github-token', [f['type'] for f in findings])
        self.assertNotIn(secret.decode(), str(findings))

    def test_already_remote_history_is_not_retested_as_new(self):
        base = self.commit('note.txt', b'safe')
        self.assertEqual(scan.scan_pending(self.repo, 'HEAD', base)['blobs_checked'], 0)

    def test_secret_in_commit_message_blocks(self):
        self.commit('note.txt', b'safe')
        value = 'ghp_' + 'D' * 36
        self.run_git('commit', '--allow-empty', '-m', value)
        findings = scan.scan_pending(self.repo, 'HEAD')['findings']
        self.assertIn('github-token', [f['type'] for f in findings])
        self.assertNotIn(value, str(findings))

    def test_secret_in_annotated_tag_message_blocks(self):
        base = self.commit('note.txt', b'safe')
        value = 'ghp_' + 'E' * 36
        self.run_git('tag', '-a', 'fixture', '-m', value)
        findings = scan.scan_pending(self.repo, 'fixture', base)['findings']
        self.assertIn('github-token', [f['type'] for f in findings])
        self.assertNotIn(value, str(findings))

    def test_shared_remote_blob_added_at_protected_path_blocks(self):
        base = self.commit('note.txt', b'safe')
        self.commit('.env', b'safe')
        findings = scan.scan_pending(self.repo, 'HEAD', base)['findings']
        self.assertIn({'path': '.env', 'type': 'protected-local-path'}, findings)

    def test_exact_empty_historical_configuration_is_preserved(self):
        self.commit(scan.EMPTY_CONFIG_ARCHIVE, b'{}')
        self.assertEqual(scan.scan_pending(self.repo, 'HEAD')['findings'], [])

    def test_changed_historical_configuration_blocks(self):
        base = self.commit(scan.EMPTY_CONFIG_ARCHIVE, b'{}')
        self.commit(scan.EMPTY_CONFIG_ARCHIVE, b'{"changed":true}')
        findings = scan.scan_pending(self.repo, 'HEAD', base)['findings']
        self.assertIn('archived-config-version-unreviewed', [x['type'] for x in findings])

    def reviewed_css(self):
        data = (Path(__file__).resolve().parents[2] / scan.REVIEWED_CSS_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         '4e201df5fa74ead1d81737d45b855694c5463f47842a25b0a7887a8ebaf45c8d')
        return data

    def test_exact_reviewed_css_is_accepted(self):
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css())
        self.assertEqual(self.run_git('rev-parse', 'HEAD:' + scan.REVIEWED_CSS_PATH),
                         scan.REVIEWED_CSS_BLOB)
        self.assertEqual(scan.scan_pending(self.repo, 'HEAD')['findings'], [])

    def test_changed_reviewed_css_blocks(self):
        base = self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css())
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css() + b'/* changed */\n')
        self.assertIn({'path': scan.REVIEWED_CSS_PATH, 'type': 'reviewed-css-version-unreviewed'},
                      scan.scan_pending(self.repo, 'HEAD', base)['findings'])

    def test_reviewed_css_blob_at_other_protected_paths_blocks(self):
        base = self.commit('note.css', self.reviewed_css())
        paths = ['.obsidian/snippets/other.css', '.obsidian/appearance.json',
                 '.obsidian/plugins/service/data.json', '.obsidian/app.json',
                 'archive/' + scan.REVIEWED_CSS_PATH]
        for name in paths:
            self.commit(name, self.reviewed_css())
        findings = scan.scan_pending(self.repo, 'HEAD', base)['findings']
        for name in paths:
            self.assertIn({'path': name, 'type': 'protected-local-path'}, findings)

    def test_unreviewed_css_in_pending_history_still_blocks(self):
        base = self.commit('note.txt', b'safe')
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css() + b'/* earlier */\n')
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css())
        self.assertIn({'path': scan.REVIEWED_CSS_PATH, 'type': 'reviewed-css-version-unreviewed'},
                      scan.scan_pending(self.repo, 'HEAD', base)['findings'])

    def test_reviewed_css_symlink_mode_blocks_even_with_exact_blob(self):
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css())
        self.run_git('update-index', '--cacheinfo', '120000', scan.REVIEWED_CSS_BLOB,
                     scan.REVIEWED_CSS_PATH)
        self.run_git('commit', '-m', 'symlink fixture')
        self.assertIn({'path': scan.REVIEWED_CSS_PATH, 'type': 'reviewed-css-version-unreviewed'},
                      scan.scan_pending(self.repo, 'HEAD')['findings'])

    def test_reviewed_css_executable_mode_blocks(self):
        self.commit(scan.REVIEWED_CSS_PATH, self.reviewed_css())
        self.run_git('update-index', '--chmod=+x', scan.REVIEWED_CSS_PATH)
        self.run_git('commit', '-m', 'executable fixture')
        self.assertIn({'path': scan.REVIEWED_CSS_PATH, 'type': 'reviewed-css-version-unreviewed'},
                      scan.scan_pending(self.repo, 'HEAD')['findings'])

    def test_css_path_exception_still_scans_content_without_leaking_values(self):
        value = 'ghp_' + 'F' * 36
        self.commit(scan.REVIEWED_CSS_PATH,
                    ('/* ' + value + ' */\n-----BEGIN ' + 'PRIVATE KEY-----\n').encode())
        oid = self.run_git('rev-parse', 'HEAD:' + scan.REVIEWED_CSS_PATH)
        # Simulate a mistakenly reviewed blob to prove path approval never skips
        # credential/private-key scanning. No actual secret is used.
        with patch.object(scan, 'REVIEWED_CSS_BLOB', oid):
            findings = scan.scan_pending(self.repo, 'HEAD')['findings']
        self.assertEqual({x['type'] for x in findings}, {'github-token', 'private-key'})
        self.assertNotIn(value, str(findings))
        self.assertNotIn('BEGIN PRIVATE KEY', str(findings))

    def setup_transport(self):
        head = self.commit('note.txt', b'safe')
        self.run_git('config', 'wwl.githubRepository', 'example/WWL')
        self.run_git('remote', 'add', 'origin', 'https://github.com/example/WWL.git')
        return head

    def transport(self, head, push_code=0, remote=None):
        actual_git = sync.git
        calls = []
        def fake_git(repo, *args, **kwargs):
            if 'push' in args:
                calls.append(args)
                return subprocess.CompletedProcess(args, push_code, 'mock push\n', '')
            if 'ls-remote' in args:
                value = remote if remote is not None else head
                return subprocess.CompletedProcess(args, 0, value + '\trefs/heads/main\n', '')
            return actual_git(repo, *args, **kwargs)
        return calls, fake_git

    def test_push_pins_commit_without_force_stage_commit_or_merge(self):
        head = self.setup_transport(); calls, fake = self.transport(head)
        with patch.object(sync, 'git', side_effect=fake), patch.object(sync, 'environment', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.push(self.repo), 0)
        self.assertEqual(calls[0][-1], head + ':refs/heads/main')
        self.assertFalse(any(arg in calls[0] for arg in ['--force', '-f', 'add', 'commit', 'merge']))
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), head)
        self.assertIn('"status": "synced"', (self.repo / '.git/wwl-github-sync.json').read_text())

    def test_push_failure_retains_local_commit_and_failure_state(self):
        head = self.setup_transport(); calls, fake = self.transport(head, push_code=1)
        with patch.object(sync, 'git', side_effect=fake), patch.object(sync, 'environment', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.push(self.repo), 1)
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), head)
        self.assertIn('"status": "failed"', (self.repo / '.git/wwl-github-sync.json').read_text())

    def test_remote_mismatch_is_not_success(self):
        head = self.setup_transport(); calls, fake = self.transport(head, remote='f' * 40)
        with patch.object(sync, 'git', side_effect=fake), patch.object(sync, 'environment', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.push(self.repo), 1)
        self.assertIn('"status": "remote-verification-failed"', (self.repo / '.git/wwl-github-sync.json').read_text())

    def test_remote_exception_records_failure(self):
        head = self.setup_transport(); calls, fake = self.transport(head)
        def failure(repo, *args, **kwargs):
            if 'ls-remote' in args:
                raise subprocess.CalledProcessError(1, ['git', 'ls-remote'])
            return fake(repo, *args, **kwargs)
        with patch.object(sync, 'git', side_effect=failure), patch.object(sync, 'environment', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                sync.push(self.repo)
        self.assertIn('"status": "failed"', (self.repo / '.git/wwl-github-sync.json').read_text())
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), head)

    def test_disabled_hook_performs_no_push(self):
        self.setup_transport()
        self.run_git('config', 'wwl.githubAutoPush', 'false')
        with patch.object(sys, 'argv', ['sync', '--hook']), patch.object(Path, 'cwd', return_value=self.repo), patch.object(sync, 'push') as push:
            self.assertEqual(sync.main(), 0)
            push.assert_not_called()

    def test_blocked_pre_push_never_invokes_lfs(self):
        head = self.setup_transport()
        stream = io.TextIOWrapper(io.BytesIO(('refs/heads/main ' + head + ' refs/heads/main ' + '0' * 40 + '\n').encode()))
        with patch.object(sys, 'stdin', stream), patch.object(sync, 'scan_pending', return_value={'findings': [{'path': '.env', 'type': 'protected-local-path'}]}), patch.object(sync.subprocess, 'run') as run, patch.object(sync, 'destination'), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sync.pre_push(self.repo, 'origin', 'https://github.com/example/WWL.git'), 1)
            run.assert_not_called()

    def test_allowed_pre_push_scans_before_lfs(self):
        head = self.setup_transport(); order = []
        stream = io.TextIOWrapper(io.BytesIO(('refs/heads/main ' + head + ' refs/heads/main ' + '0' * 40 + '\n').encode()))
        def checked(*args):
            order.append('scan')
            return {'findings': [], 'blobs_checked': 1, 'lfs_payloads_checked': 0}
        def uploaded(*args, **kwargs):
            order.append('lfs')
            return subprocess.CompletedProcess(args, 0)
        with patch.object(sys, 'stdin', stream), patch.object(sync, 'scan_pending', side_effect=checked), patch.object(sync.subprocess, 'run', side_effect=uploaded), patch.object(sync, 'destination'), patch.object(sync, 'environment', return_value={}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sync.pre_push(self.repo, 'origin', 'https://github.com/example/WWL.git'), 0)
        self.assertEqual(order, ['scan', 'lfs'])

    def test_post_commit_failure_does_not_fail_local_commit_hook(self):
        head = self.commit('note.txt', b'safe')
        folder = self.repo / 'scripts'; folder.mkdir()
        (folder / 'github_sync.py').write_text('import sys\nsys.exit(7)\n')
        hook = Path(__file__).resolve().parents[2] / '.githooks/post-commit'
        result = subprocess.run(['sh', str(hook)], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('local commit retained', result.stdout)
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), head)

    def test_lfs_payload_hash_and_actual_secret_are_checked(self):
        data = ('ghp_' + 'C' * 36).encode()
        digest = hashlib.sha256(data).hexdigest()
        payload = self.repo / '.git/lfs/objects' / digest[:2] / digest[2:4] / digest
        payload.parent.mkdir(parents=True); payload.write_bytes(data)
        pointer = ('version https://git-lfs.github.com/spec/v1\noid sha256:' + digest + '\nsize ' + str(len(data)) + '\n').encode()
        self.commit('book.pdf', pointer)
        result = scan.scan_pending(self.repo, 'HEAD')
        self.assertEqual(result['lfs_payloads_checked'], 1)
        self.assertIn('github-token', [f['type'] for f in result['findings']])
        payload.write_bytes(b'changed')
        self.assertIn('LFS-payload-hash-or-size-mismatch', [f['type'] for f in scan.scan_pending(self.repo, 'HEAD')['findings']])

    def test_missing_lfs_content_blocks(self):
        pointer = ('version https://git-lfs.github.com/spec/v1\noid sha256:' + 'd' * 64 + '\nsize 8\n').encode()
        self.commit('book.pdf', pointer)
        self.assertIn('LFS-payload-missing', [f['type'] for f in scan.scan_pending(self.repo, 'HEAD')['findings']])

    def test_exact_destination_required(self):
        self.run_git('config', 'wwl.githubRepository', 'example/WWL')
        self.assertEqual(sync.destination(self.repo, 'https://github.com/example/WWL.git'), 'https://github.com/example/WWL.git')
        with self.assertRaises(ValueError):
            sync.destination(self.repo, 'https://github.com/example/Other.git')


if __name__ == '__main__':
    unittest.main()
