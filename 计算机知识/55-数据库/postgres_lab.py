"""真实 PostgreSQL 双会话实验；只创建/控制自己拥有的临时集群。
Python 标准库；PG_BIN 指定含 initdb/pg_ctl/psql/postgres 的目录。
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid

LEVELS = {'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE'}


def pg_bin():
    explicit = os.environ.get('PG_BIN')
    found = explicit or (str(Path(shutil.which('initdb')).parent)
                         if shutil.which('initdb') else '')
    path = Path(found)
    if not found or not all((path / x).is_file() for x in
                            ('initdb', 'pg_ctl', 'psql', 'postgres')):
        raise FileNotFoundError('设置 PG_BIN；需要真实 PostgreSQL 四个工具')
    return path.resolve()


class SqlError(RuntimeError):
    def __init__(self, state, output):
        super().__init__(output)
        self.state = state


class Session:
    def __init__(self, cluster):
        self.cluster = cluster
        self.process = subprocess.Popen(
            [str(cluster.bin / 'psql'), '-X', '-q', '-A', '-t', '-h',
             str(cluster.socket), '-p', '55432', '-U', 'wwl', '-d', 'postgres',
             '-v', 'VERBOSITY=verbose'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=cluster.env)
        self.pending = b''
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        cluster.sessions.append(self)

    def sql(self, statement, timeout=8):
        if timeout <= 0 or not isinstance(statement, str):
            raise ValueError('SQL 必须为字符串，timeout 必须为正')
        marker = 'WWL_' + uuid.uuid4().hex
        self.process.stdin.write((statement + '\n\\echo ' + marker + '\n').encode())
        self.process.stdin.flush()
        deadline, lines = time.monotonic() + timeout, []
        while True:
            while b'\n' in self.pending:
                line, self.pending = self.pending.split(b'\n', 1)
                text = line.decode(errors='replace').strip()
                if text == marker:
                    output = '\n'.join(lines)
                    self.cluster.events.append({'sql': statement, 'output': output})
                    error = re.search(r'ERROR:\s+([A-Z0-9]{5}):', output)
                    if error:
                        raise SqlError(error.group(1), output)
                    return output
                if text:
                    lines.append(text)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError('psql 响应超时；调用者须退出上下文清理')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError('psql 提前退出: ' + '\n'.join(lines))
            self.pending += chunk

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()  # 只终止本次 Popen 创建的客户端
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()


class Cluster:
    def __init__(self, binary=None, evidence=None):
        self.bin = Path(binary).resolve() if binary else pg_bin()
        self.evidence = Path(evidence) if evidence else None
        self.root = Path(tempfile.mkdtemp(prefix='wwlpg-', dir='/private/tmp'
                                        if Path('/private/tmp').exists() else None))
        self.data, self.socket = self.root / 'data', self.root / 's'
        self.socket.mkdir(mode=0o700)
        self.log = self.root / 'server.log'
        self.sessions, self.events = [], []
        # 不继承 PGHOST/PGSERVICE/.psqlrc，避免接入已有数据库与个人设置。
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
        self.env.update({'LC_ALL': 'C', 'PGCONNECT_TIMEOUT': '3',
                         'PGPASSFILE': str(self.root / 'no-passfile')})

    def command(self, args, timeout=30):
        result = subprocess.run([str(self.bin / args[0]), *args[1:]],
                                capture_output=True, text=True, timeout=timeout,
                                env=self.env)
        self.events.append({'argv': args, 'returncode': result.returncode,
                            'stdout': result.stdout, 'stderr': result.stderr})
        result.check_returncode()
        return result.stdout

    def __enter__(self):
        try:
            self.command(['initdb', '-D', str(self.data), '-U', 'wwl',
                          '--auth=trust', '--locale=C', '--encoding=UTF8'])
            with (self.data / 'postgresql.conf').open('a') as f:
                f.write("\nlisten_addresses = ''\nport = 55432\n"
                        f"unix_socket_directories = '{self.socket}'\n"
                        "unix_socket_permissions = 0700\nfsync = on\n"
                        "synchronous_commit = on\nfull_page_writes = on\n"
                        "statement_timeout = '5s'\nlock_timeout = '3s'\n"
                        "idle_in_transaction_session_timeout = '30s'\n"
                        "checkpoint_timeout = '1h'\n")
            self.start()
            return self
        except BaseException:
            self.close()
            raise

    def start(self):
        self.command(['pg_ctl', '-D', str(self.data), '-l', str(self.log),
                      '-w', '-t', '15', 'start'])

    def stop(self, mode='fast'):
        if mode not in {'fast', 'immediate'}:
            raise ValueError('仅允许 fast/immediate')
        if (self.data / 'postmaster.pid').exists():
            self.command(['pg_ctl', '-D', str(self.data), '-w', '-t', '15',
                          '-m', mode, 'stop'])

    def session(self):
        return Session(self)

    def close(self):
        for session in self.sessions:
            session.close()
        # 停止失败就保留目录并抛错，不能伪称已清理。
        self.stop()
        if self.evidence:
            self.evidence.mkdir(parents=True, exist_ok=True)
            (self.evidence / 'commands.json').write_text(
                json.dumps(self.events, ensure_ascii=False, indent=2))
            if self.log.exists():
                shutil.copy2(self.log, self.evidence / 'server.log')
        shutil.rmtree(self.root)

    def __exit__(self, *exc):
        self.close()


def snapshots(c, level):
    if level not in LEVELS:
        raise ValueError('未知隔离级别')
    a, b = c.session(), c.session()
    try:
        a.sql('DROP TABLE IF EXISTS balance; CREATE TABLE balance(v int); '
              'INSERT INTO balance VALUES(100);')
        a.sql(f'BEGIN ISOLATION LEVEL {level};')
        first = int(a.sql('SELECT v FROM balance;'))
        b.sql('UPDATE balance SET v=90;')
        second = int(a.sql('SELECT v FROM balance;'))
        a.sql('COMMIT;')
        return [first, second]
    finally:
        a.close(); b.close()


def lost_update(c, atomic=False):
    a, b = c.session(), c.session()
    try:
        a.sql('DROP TABLE IF EXISTS balance; CREATE TABLE balance(v int); '
              'INSERT INTO balance VALUES(100);')
        a.sql('BEGIN;'); b.sql('BEGIN;')
        old_a = int(a.sql('SELECT v FROM balance;'))
        old_b = int(b.sql('SELECT v FROM balance;'))
        a.sql('UPDATE balance SET v=v-10;' if atomic else
              f'UPDATE balance SET v={old_a - 10};')
        a.sql('COMMIT;')
        b.sql('UPDATE balance SET v=v-10;' if atomic else
              f'UPDATE balance SET v={old_b - 10};')
        b.sql('COMMIT;')
        return int(a.sql('SELECT v FROM balance;'))
    finally:
        a.close(); b.close()


def skew(c, level):
    if level not in {'REPEATABLE READ', 'SERIALIZABLE'}:
        raise ValueError('写偏斜比较仅 RR/Serializable')
    a, b = c.session(), c.session()
    count = 'SELECT count(*) FROM duty WHERE oncall;'
    try:
        a.sql('DROP TABLE IF EXISTS duty; CREATE TABLE duty(id int PRIMARY KEY, '
              'oncall boolean); INSERT INTO duty VALUES(1,true),(2,true);')
        a.sql(f'BEGIN ISOLATION LEVEL {level};')
        b.sql(f'BEGIN ISOLATION LEVEL {level};')
        reads = [int(a.sql(count)), int(b.sql(count))]
        a.sql('UPDATE duty SET oncall=false WHERE id=1;')
        a.sql('COMMIT;')
        state, reread = None, None
        try:
            b.sql('UPDATE duty SET oncall=false WHERE id=2;')
            b.sql('COMMIT;')  # 两阶段都可能出现 40001
        except SqlError as e:
            state = e.state
            b.sql('ROLLBACK;')
            if state != '40001':
                raise
            # 全事务重试：新快照重新读/决策，最多三次。
            for attempt in range(3):
                try:
                    b.sql('BEGIN ISOLATION LEVEL SERIALIZABLE;')
                    reread = int(b.sql(count))
                    if reread > 1:
                        b.sql('UPDATE duty SET oncall=false WHERE id=2;')
                    b.sql('COMMIT;')
                    break
                except SqlError as retry_error:
                    b.sql('ROLLBACK;')
                    if retry_error.state != '40001' or attempt == 2:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        return {'reads': reads, 'sqlstate': state, 'retry_read': reread,
                'remaining': int(a.sql(count))}
    finally:
        a.close(); b.close()


def recovery(c):
    a, b = c.session(), c.session()
    try:
        a.sql('CREATE TABLE durable(id int PRIMARY KEY, v int); '
              'INSERT INTO durable VALUES(1,0),(2,0); CHECKPOINT;')
        a.sql('BEGIN; UPDATE durable SET v=10 WHERE id=1; COMMIT;')
        b.sql('BEGIN; UPDATE durable SET v=99 WHERE id=1; '
              'UPDATE durable SET v=20 WHERE id=2;')
        local = b.sql('SELECT id,v FROM durable ORDER BY id;')
        observer = a.sql('SELECT id,v FROM durable ORDER BY id;')
        c.stop('immediate')  # 自有集群 SIGQUIT；无正常关闭检查点
        a.close(); b.close()
        c.start()
        fresh = c.session()
        try:
            after = fresh.sql('SELECT id,v FROM durable ORDER BY id;')
        finally:
            fresh.close()
        return {'uncommitted_session': local, 'observer_before': observer,
                'after_restart': after}
    finally:
        a.close(); b.close()


def run(evidence):
    with Cluster(evidence=evidence) as c:
        s = c.session()
        settings = json.loads(s.sql("SELECT json_build_object('version',version(), "
                         "'listen_addresses',current_setting('listen_addresses'), "
                         "'fsync',current_setting('fsync'), "
                         "'synchronous_commit',current_setting('synchronous_commit'), "
                         "'full_page_writes',current_setting('full_page_writes'));") )
        s.close()
        result = {'settings': settings,
                  'rc_snapshots': snapshots(c, 'READ COMMITTED'),
                  'rr_snapshots': snapshots(c, 'REPEATABLE READ'),
                  'lost_update': lost_update(c), 'atomic_update': lost_update(c, True),
                  'rr_skew': skew(c, 'REPEATABLE READ'),
                  'serializable': skew(c, 'SERIALIZABLE'), 'recovery': recovery(c)}
        root = str(c.root)
    result['cleanup'] = {'root': root, 'removed': not Path(root).exists()}
    Path(evidence, 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, help='库外证据目录')
    print(json.dumps(run(parser.parse_args().evidence), ensure_ascii=False, indent=2))
