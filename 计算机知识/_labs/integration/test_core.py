from __future__ import annotations
import asyncio
import bisect
import itertools
import math
import random
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from lab_core import *

class AlgorithmTests(unittest.TestCase):
    def test_lower_bound_edges(self):
        for a in ([], [1], [1, 1, 1], [-2, 0, 0, 3]):
            for x in range(-4, 6):
                self.assertEqual(lower_bound(a, x), bisect.bisect_left(a, x))

    def test_lower_bound_random(self):
        rng = random.Random(1701)
        for _ in range(150):
            a = sorted(rng.randrange(-20, 21) for _ in range(rng.randrange(50)))
            x = rng.randrange(-22, 23)
            self.assertEqual(lower_bound(a, x), bisect.bisect_left(a, x))

    def test_stable_merge_sort(self):
        rows = [(2, 'a'), (1, 'b'), (2, 'c'), (1, 'd')]
        self.assertEqual(merge_sort(rows, key=lambda p: p[0]), [(1, 'b'), (1, 'd'), (2, 'a'), (2, 'c')])
        self.assertEqual(merge_sort([]), [])

    def test_union_find(self):
        u = UnionFind(6)
        self.assertTrue(u.union(0, 1)); self.assertTrue(u.union(1, 2))
        self.assertFalse(u.union(0, 2)); self.assertEqual(u.components, 4)
        self.assertEqual(u.find(0), u.find(2)); self.assertNotEqual(u.find(0), u.find(3))
        with self.assertRaises(IndexError): u.find(-1)

    def test_shortest_path_example(self):
        g = [[(1, 4), (2, 1)], [(3, 1)], [(1, 2), (3, 5)], [], []]
        self.assertEqual(dijkstra(g, 0), [0, 3, 1, 4, math.inf])
        self.assertEqual(dijkstra(g, 0), bellman_ford(g, 0))

    def test_shortest_path_differential(self):
        rng = random.Random(2903)
        for n in range(1, 12):
            g = [[(j, rng.randrange(10)) for j in range(n) if i != j and rng.random() < 0.35] for i in range(n)]
            for s in range(n): self.assertEqual(dijkstra(g, s), bellman_ford(g, s))

    def test_negative_edge_and_cycle(self):
        with self.assertRaises(ValueError): dijkstra([[(1, -1)], []], 0)
        self.assertEqual(bellman_ford([[(1, -1)], []], 0), [0, -1])
        with self.assertRaises(ValueError): bellman_ford([[(1, -1)], [(0, 0)]], 0)
        # An unreachable negative cycle does not invalidate source distances.
        self.assertEqual(bellman_ford([[], [(1, -1)]], 0), [0, math.inf])

    def test_knapsack_counterexample(self):
        self.assertEqual(knapsack01([(2, 3)], 4), 3)
        self.assertEqual(knapsack01([], 5), 0)

    def test_knapsack_against_exhaustive(self):
        rng = random.Random(5901)
        for n in range(8):
            items = [(rng.randrange(1, 6), rng.randrange(10)) for _ in range(n)]
            for cap in range(12):
                values = [sum(items[i][1] for i in range(n) if mask >> i & 1)
                          for mask in range(1 << n)
                          if sum(items[i][0] for i in range(n) if mask >> i & 1) <= cap]
                self.assertEqual(knapsack01(items, cap), max(values))

class SystemModelTests(unittest.TestCase):
    def test_lru(self):
        self.assertEqual(lru_misses([1, 2, 1, 3, 1, 2], 2), 4)
        self.assertEqual(lru_misses([], 2), 0)
        with self.assertRaises(ValueError): lru_misses([1], 0)

    def test_cache_conflict(self):
        refs = [0, 128, 0]
        self.assertEqual(cache_misses(refs, lines=2, ways=1, block_size=64), 3)
        self.assertEqual(cache_misses(refs, lines=2, ways=2, block_size=64), 2)
        self.assertEqual(cache_misses([0, 1, 63], lines=2, ways=1, block_size=64), 1)

    def test_round_robin(self):
        trace, finish = round_robin([5, 3], 2)
        self.assertEqual(trace, [(0, 0, 2), (1, 2, 4), (0, 4, 6), (1, 6, 7), (0, 7, 8)])
        self.assertEqual(finish, [8, 7])
        self.assertEqual([finish[i] - x for i, x in enumerate([5, 3])], [3, 4])

    def test_round_robin_edges(self):
        self.assertEqual(round_robin([0, 0], 1), ([], [0, 0]))
        with self.assertRaises(ValueError): round_robin([1], 0)

    def test_banker_safe(self):
        available = [3, 3, 2]
        allocation = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
        maximum = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
        seq = banker_safe_sequence(available, allocation, maximum)
        self.assertIsNotNone(seq)
        work = list(available)
        for i in seq:
            self.assertTrue(all(maximum[i][j] - allocation[i][j] <= work[j] for j in range(3)))
            work = [work[j] + allocation[i][j] for j in range(3)]
        self.assertEqual(available, [3, 3, 2])

    def test_banker_unsafe(self):
        self.assertIsNone(banker_safe_sequence([0], [[1], [1]], [[2], [2]]))

    def test_byte_and_float_models(self):
        self.assertEqual((255 + 1) % 256, 0)
        self.assertEqual(0xFF - 256, -1)  # A model of decoding signed 8-bit two's complement.
        self.assertFalse(0.1 + 0.2 == 0.3)
        self.assertTrue(math.isclose(0.1 + 0.2, 0.3, rel_tol=1e-12))

class NetworkTests(unittest.TestCase):
    def test_fragmentation_every_split(self):
        wire = encode_frame(b'hello') + encode_frame(b'world')
        for split in range(len(wire) + 1):
            p = FrameParser(); out = p.feed(wire[:split]) + p.feed(wire[split:]); p.finish()
            self.assertEqual(out, [b'hello', b'world'])

    def test_single_byte_feeds_and_empty_frame(self):
        p = FrameParser(); out = []
        for b in encode_frame(b'') + encode_frame('你好'.encode()): out += p.feed(bytes([b]))
        p.finish(); self.assertEqual(out, [b'', '你好'.encode()])

    def test_size_limit_terminal_error(self):
        p = FrameParser(4)
        with self.assertRaises(ValueError): p.feed((5).to_bytes(4, 'big'))
        with self.assertRaises(RuntimeError): p.feed(b'')
        with self.assertRaises(ValueError): encode_frame(b'12345', 4)

    def test_truncated_header_and_body(self):
        for data in (b'\0\0', (3).to_bytes(4, 'big') + b'ab'):
            p = FrameParser(); p.feed(data)
            with self.assertRaises(ValueError): p.finish()

    def test_empty_stream(self):
        p = FrameParser(); self.assertEqual(p.feed(b''), []); p.finish()

class PythonContractTests(unittest.TestCase):
    def test_count_valid(self):
        self.assertEqual(parse_count(0), 0); self.assertEqual(parse_count({'value': 7}), 7)

    def test_nested_bool_regression(self):
        for x in (True, False, {'value': True}, {'value': False}, -1, {'value': -1}, {}, None, 2.0, '2'):
            with self.subTest(value=x), self.assertRaises(ValueError): parse_count(x)

    def test_shallow_copy_aliases(self):
        a = [[1]]; b = list(a); b[0].append(2)
        self.assertIsNot(a, b); self.assertIs(a[0], b[0]); self.assertEqual(a, [[1, 2]])

    def test_data_descriptor_priority(self):
        class C:
            @property
            def x(self): return 42
        obj = C(); obj.__dict__['x'] = 7
        self.assertEqual(obj.x, 42)

    def test_non_data_descriptor_shadowing(self):
        class C:
            def method(self): return 42
        obj = C(); obj.method = 7
        self.assertEqual(obj.method, 7)

class CompilerTests(unittest.TestCase):
    def test_precedence_associativity_and_unary(self):
        examples = {'2 + 3 * 4': 14, '(2+3)*4': 20, '9-3-2': 4,
                    '-2*3+4': -2, '2*-3': -6, '--3': 3, '  42  ': 42}
        for source, value in examples.items():
            tree = parse_expression(source)
            self.assertEqual(eval_ast(tree), value)
            self.assertEqual(run_bytecode(compile_ast(tree)), value)

    def test_syntax_errors(self):
        for source in ('', '1+', '(1+2', '1 2', 'a+1', '2/1', ')1('):
            with self.subTest(source=source), self.assertRaises(ValueError): parse_expression(source)

    def test_bytecode_errors(self):
        for code in ([], [('add',)], [('push', 1), ('push', 2)], [('unknown',)]):
            with self.assertRaises(ValueError): run_bytecode(code)

    def test_compilation_differential(self):
        rng = random.Random(8301)
        def tree(depth):
            if depth == 0 or rng.random() < 0.3: return ('const', rng.randrange(-10, 11))
            return (rng.choice(['add', 'sub', 'mul']), tree(depth-1), tree(depth-1))
        for _ in range(100):
            node = tree(4)
            self.assertEqual(eval_ast(node), run_bytecode(compile_ast(node)))

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE orders(id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id), amount INTEGER CHECK(amount>=0), status TEXT NOT NULL);
        INSERT INTO customers VALUES (1,'Ada'),(2,'Bo'),(3,'Cy');
        INSERT INTO orders VALUES (1,1,100,'paid'),(2,1,200,'new'),(3,3,NULL,'new');
        ''')
        self.db.commit()

    def tearDown(self): self.db.close()

    def test_left_join_counts(self):
        rows = self.db.execute('SELECT c.id,COUNT(*),COUNT(o.id) FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id').fetchall()
        self.assertEqual(rows, [(1,2,2),(2,1,0),(3,1,1)])

    def test_null_not_in(self):
        a = self.db.execute('SELECT id FROM customers WHERE id NOT IN (SELECT customer_id FROM orders UNION ALL SELECT NULL)').fetchall()
        b = self.db.execute('SELECT c.id FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id=c.id)').fetchall()
        self.assertEqual(a, []); self.assertEqual(b, [(2,)])

    def test_on_versus_where(self):
        on = self.db.execute("SELECT c.id,o.id FROM customers c LEFT JOIN orders o ON o.customer_id=c.id AND o.status='paid' ORDER BY c.id").fetchall()
        where = self.db.execute("SELECT c.id,o.id FROM customers c LEFT JOIN orders o ON o.customer_id=c.id WHERE o.status='paid' ORDER BY c.id").fetchall()
        self.assertEqual(on, [(1,1),(2,None),(3,None)]); self.assertEqual(where, [(1,1)])

    def test_transaction_rollback(self):
        self.db.execute('BEGIN')
        self.db.execute("INSERT INTO customers VALUES(4,'Dee')")
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM customers').fetchone()[0], 3)

    def test_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO orders VALUES(8,99,2,'new')")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO orders VALUES(8,1,-1,'new')")

    def test_window_function(self):
        rows = self.db.execute('SELECT id,ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY id) FROM orders ORDER BY id').fetchall()
        self.assertEqual(rows, [(1,1),(2,2),(3,1)])

class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_backlog_and_complete_results(self):
        queue = asyncio.Queue(maxsize=3)
        results, watermarks = [], []
        async def worker():
            while True:
                x = await queue.get()
                try:
                    if x is None: return
                    await asyncio.sleep(0)
                    results.append(x*x)
                finally: queue.task_done()
        tasks = [asyncio.create_task(worker()) for _ in range(2)]
        try:
            for i in range(20):
                await queue.put(i); watermarks.append(queue.qsize())
            for _ in tasks: await queue.put(None)
            await asyncio.wait_for(queue.join(), 3)
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                if not t.done(): t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertLessEqual(max(watermarks), 3)
        self.assertEqual(sorted(results), [i*i for i in range(20)])
        self.assertTrue(all(t.done() for t in tasks))

    @unittest.skipUnless(hasattr(asyncio, 'TaskGroup'), 'requires Python 3.11 TaskGroup')
    async def test_taskgroup_failure_cancels_sibling(self):
        cleaned = asyncio.Event()
        async def waiting():
            try: await asyncio.Event().wait()
            finally: cleaned.set()
        async def failing():
            await asyncio.sleep(0)
            raise ValueError('intentional test failure inside child')
        with self.assertRaises(ExceptionGroup):
            async with asyncio.TaskGroup() as group:
                a = group.create_task(waiting()); b = group.create_task(failing())
        self.assertTrue(cleaned.is_set()); self.assertTrue(a.done() and b.done())

class LinuxTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('bash') and shutil.which('find'), 'requires bash and find')
    def test_filename_boundaries(self):
        with tempfile.TemporaryDirectory(prefix='kb-safe-') as td:
            names = ['plain.txt', 'with space.txt', 'with\nnewline.txt', '-leading.txt']
            for name in names: (Path(td)/name).write_text('local test\n')
            cmd = "while IFS= read -r -d '' f; do printf '%s\\0' \"$f\"; done < <(find . -type f -name '*.txt' -print0)"
            result = subprocess.run(['bash','-c',cmd],cwd=td,capture_output=True,check=True,timeout=10)
            paths = {s.decode() for s in result.stdout.split(b'\0') if s}
            self.assertEqual(paths, {'./'+n for n in names})

if __name__ == '__main__': unittest.main(verbosity=2)
