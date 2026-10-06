#!/usr/bin/env python3
"""Push the current committed branch to the explicitly configured WWL repo.

Never stages, commits, merges, force-pushes or uploads uncommitted changes.
The pre-push hook validates the exact outgoing revisions before Git LFS upload.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

from github_secret_scan import redact, scan_pending


def git(repo, *args, check=True, **kwargs):
    return subprocess.run(['git', '-C', str(repo), *args],
                          capture_output=True, text=True, check=check, **kwargs)


def config(repo, name, default=''):
    result = git(repo, 'config', '--get', name, check=False)
    return result.stdout.strip() if result.returncode == 0 else default


def destination(repo, url=None):
    target = config(repo, 'wwl.githubRepository')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/WWL', target):
        raise ValueError('WWL GitHub repository is not configured')
    expected = 'https://github.com/' + target + '.git'
    actual = url if url is not None else git(repo, 'remote', 'get-url', '--push', 'origin').stdout.strip()
    if actual != expected:
        raise ValueError('Refusing an unconfigured push destination')
    return expected


def environment(repo):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('GIT_TRACE') or key == 'GIT_CURL_VERBOSE':
            env.pop(key)
    filename = config(repo, 'wwl.githubTokenFile')
    if not filename or not Path(filename).is_absolute() or not Path(filename).is_file():
        raise ValueError('Configured GitHub credential file is unavailable')
    env.update(GIT_ASKPASS=str(repo / 'scripts/github_askpass.py'),
               GIT_TERMINAL_PROMPT='0', WWL_GITHUB_TOKEN_FILE=filename)
    return env


def git_path(repo, name):
    return Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-path', name).stdout.strip())


def save_state(repo, state):
    state['time_utc'] = datetime.now(timezone.utc).isoformat()
    target = git_path(repo, 'wwl-github-sync.json')
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(target)


def pre_push(repo, remote, url):
    destination(repo, url)
    if remote != 'origin':
        raise ValueError('WWL synchronization requires origin')
    lines = sys.stdin.buffer.read()
    results = []
    for line in lines.splitlines():
        local_ref, local_oid, remote_ref, remote_oid = line.decode().split()
        if local_oid == '0' * 40: continue
        result = scan_pending(repo, local_oid, remote_oid)
        results.append(result)
        if result['findings']:
            print(json.dumps({'status': 'push-blocked', 'findings': result['findings']}, ensure_ascii=False), file=sys.stderr)
            return 1
    print(json.dumps({'status': 'pre-push-checked', 'blobs': sum(x['blobs_checked'] for x in results),
                      'lfs_payloads': sum(x['lfs_payloads_checked'] for x in results)}, ensure_ascii=False), flush=True)
    result = subprocess.run(['git', '-C', str(repo), 'lfs', 'pre-push', remote, url], input=lines,
                            env=environment(repo))
    return result.returncode


def push(repo):
    destination(repo)
    env = environment(repo)
    with git_path(repo, 'wwl-github-sync.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        branch = git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
        if not branch:
            raise ValueError('Detached HEAD: choose a branch before synchronization')
        git(repo, 'check-ref-format', '--branch', branch)
        head = git(repo, 'rev-parse', 'HEAD').stdout.strip()
        state = {'branch': branch, 'commit': head, 'status': 'pushing', 'destination': destination(repo)}
        save_state(repo, state)
        print(json.dumps(state, ensure_ascii=False), flush=True)
        try:
            result = git(repo, '-c', 'credential.helper=', 'push', '--porcelain', 'origin',
                         head + ':refs/heads/' + branch, check=False, env=env, timeout=1800)
            if result.stdout: print(redact(result.stdout), end='')
            if result.stderr: print(redact(result.stderr), end='', file=sys.stderr)
            if result.returncode:
                state['status'] = 'failed'; save_state(repo, state)
                return result.returncode
            remote = git(repo, '-c', 'credential.helper=', 'ls-remote', 'origin',
                         'refs/heads/' + branch, env=env, timeout=60).stdout.split()
            if not remote or remote[0] != head:
                state['status'] = 'remote-verification-failed'; save_state(repo, state)
                return 1
            state['status'] = 'synced'; save_state(repo, state)
            print(json.dumps(state, ensure_ascii=False))
            return 0
        except Exception:
            state['status'] = 'failed'; save_state(repo, state)
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hook', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--pre-push', nargs=2, metavar=('REMOTE', 'URL'))
    args = parser.parse_args()
    repo = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').stdout.strip())
    if args.pre_push:
        return pre_push(repo, *args.pre_push)
    if args.hook and config(repo, 'wwl.githubAutoPush', 'false') != 'true':
        return 0
    if args.check:
        destination(repo)
        branch = git(repo, 'symbolic-ref', '--short', 'HEAD').stdout.strip()
        remote = git(repo, 'rev-parse', '--verify', 'refs/remotes/origin/' + branch, check=False)
        result = scan_pending(repo, 'HEAD', remote.stdout.strip() if remote.returncode == 0 else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['findings'] else 0
    return push(repo)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('WWL GitHub synchronization failed: ' + redact(str(error)), file=sys.stderr)
        sys.exit(1)
