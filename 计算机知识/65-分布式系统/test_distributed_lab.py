"""Finite independent oracles and fault traces; not a complete protocol proof."""
import unittest
from itertools import permutations, product
from distributed_lab import (ClockTrace, vector_before, Operation, serial_witness,
                             majority_sets, RaftCore, Entry, Scheduler, elect,
                             two_pc_unknown)


class ClockTests(unittest.TestCase):
    def test_vector_matches_dag_for_all_short_traces(self):
        # At step i: process 0/1 and either local or receive any older event.
        checked = 0
        def visit(plan):
            nonlocal checked
            trace = ClockTrace(2)
            for process, receive in plan:
                trace.event(process, receive)
            reachable = trace.reachability()
            for a in range(len(plan)):
                for b in range(len(plan)):
                    self.assertEqual((a, b) in reachable,
                                     vector_before(trace.events[a][2], trace.events[b][2]))
                    if (a, b) in reachable:
                        self.assertLess(trace.events[a][1], trace.events[b][1])
            checked += 1
            if len(plan) < 4:
                for process in range(2):
                    for receive in [None] + list(range(len(plan))):
                        visit(plan + [(process, receive)])
        visit([])
        self.assertEqual(checked, 443)

    def test_scalar_order_is_not_causality(self):
        t = ClockTrace(2)
        a = t.event(0)
        t.event(1)
        b = t.event(1)
        self.assertLess(t.events[a][1], t.events[b][1])
        self.assertNotIn((a, b), t.reachability())
        self.assertFalse(vector_before(t.events[a][2], t.events[b][2]))

    def test_invalid_clock_inputs(self):
        for n in [0, -1]:
            with self.assertRaises(ValueError):
                ClockTrace(n)
        with self.assertRaises(ValueError):
            vector_before((1,), (1, 2))


class HistoryTests(unittest.TestCase):
    def test_real_time_stale_read(self):
        h = [Operation('A', 'put', 7, 1, 2), Operation('B', 'get', 0, 3, 4)]
        self.assertEqual(serial_witness(h, False), (1, 0))
        self.assertIsNone(serial_witness(h))
        h[1] = Operation('A', 'get', 0, 3, 4)
        self.assertIsNone(serial_witness(h, False))

    def test_new_then_old_read_is_not_linearizable(self):
        h = [Operation("A", "put", 7, 1, 6),
             Operation("B", "get", 7, 2, 3),
             Operation("C", "get", 0, 4, 5)]
        self.assertIsNone(serial_witness(h))
        self.assertEqual(serial_witness(h, False), (2, 0, 1))
        h[1] = Operation("B", "get", 7, 2, 4)
        h[2] = Operation("C", "get", 0, 3, 5)
        self.assertEqual(serial_witness(h), (2, 0, 1))

    def test_overlapping_read_can_see_old_value(self):
        h = [Operation('A', 'put', 7, 1, 4), Operation('B', 'get', 0, 2, 3)]
        self.assertEqual(serial_witness(h), (1, 0))

    def test_three_completed_ops_match_direct_last_write_oracle(self):
        # Nonoverlap makes the only linearization the chronological order.
        checked = 0
        for kinds in product(['put', 'get'], repeat=3):
            for values in product([0, 1, 2], repeat=3):
                h = [Operation(str(i), k, v, 2*i, 2*i+1)
                     for i, (k, v) in enumerate(zip(kinds, values))]
                expected, state = True, 0
                for k, v in zip(kinds, values):
                    if k == 'put':
                        state = v
                    elif v != state:
                        expected = False
                self.assertEqual(serial_witness(h) is not None, expected)
                checked += 1
        self.assertEqual(checked, 216)

    def test_invalid_history(self):
        with self.assertRaises(ValueError):
            serial_witness([Operation('A', 'get', 0, 1, 2),
                            Operation('B', 'get', 0, 2, 3)])
        with self.assertRaises(ValueError):
            serial_witness([Operation('A', 'get', 0, 2, 1)])
        with self.assertRaises(ValueError):
            serial_witness([Operation('A', 'get', 0, 1, 4),
                            Operation('A', 'get', 0, 2, 3)])


class QuorumTests(unittest.TestCase):
    def test_all_majority_pairs_intersect(self):
        checked = 0
        for n in range(1, 10):
            qs = majority_sets(n)
            for a in qs:
                for b in qs:
                    self.assertTrue(a & b)
                    self.assertGreaterEqual(len(a & b), 2*(n//2+1)-n)
                    checked += 1
        self.assertEqual(checked, 20589)

    def test_duplicate_votes_do_not_make_majority(self):
        nodes = [RaftCore(i, members=5) for i in range(5)]
        request = nodes[0].election()
        result = nodes[1].vote(*request)
        for _ in range(10):
            nodes[0].record_vote(1, *result)
        self.assertEqual(nodes[0].role, 'candidate')
        self.assertEqual(nodes[0].votes, {0, 1})
        self.assertGreater(1 + 10, 5//2)  # Broken message counter would elect.


class RaftGuardTests(unittest.TestCase):
    def test_each_term_has_one_vote_and_fresh_log_check(self):
        voter = RaftCore(0, log=[Entry(2, 7)], term=2)
        self.assertEqual(voter.vote(3, 1, (1, 99)), (3, False))
        self.assertEqual(voter.vote(3, 1, (2, 1)), (3, True))
        self.assertEqual(voter.vote(3, 2, (3, 5)), (3, False))
        voter.reboot()
        self.assertEqual(voter.vote(3, 2, (3, 5)), (3, False))

    def test_stale_term_and_prefix_mismatch_rejected(self):
        follower = RaftCore(1, term=3, log=[Entry(2, 7)])
        self.assertEqual(follower.append(2, 0, 0, [Entry(2, 9)], 1), (3, False, 0))
        self.assertEqual(follower.append(3, 1, 1, [], 1), (3, False, 0))
        self.assertEqual(follower.log, [Entry(2, 7)])

    def test_old_term_majority_does_not_directly_commit(self):
        leader = RaftCore(0, term=4, role='leader', log=[Entry(2, 7)])
        leader.match = {0: 1}
        leader.acknowledge(1, 4, True, 1)
        self.assertEqual(leader.commit, 0)
        leader.propose(9)
        leader.acknowledge(1, 4, True, 2)
        self.assertEqual((leader.commit, leader.applied, leader.state), (2, 2, 9))

    def test_conflict_only_removes_uncommitted_suffix(self):
        f = RaftCore(1, term=3, log=[Entry(1, 7), Entry(2, 8)], commit=1)
        f.append(3, 1, 1, [Entry(3, 9)], 2)
        self.assertEqual(f.log, [Entry(1, 7), Entry(3, 9)])
        self.assertEqual(f.state, 9)
        with self.assertRaises(AssertionError):
            f.append(4, 0, 0, [Entry(4, 99)], 1)

    def test_short_heartbeat_does_not_commit_unmatched_suffix(self):
        f = RaftCore(1, term=3, log=[Entry(1, 7), Entry(2, 8)])
        f.append(3, 1, 1, [], 2)
        self.assertEqual((f.commit, f.state), (1, 7))

    def test_partition_then_heal_and_duplicate(self):
        nodes = [RaftCore(i) for i in range(3)]
        elect(nodes, 0, [1])
        s = Scheduler(nodes)
        nodes[0].propose(7)
        s.blocked = {(0, 1), (0, 2)}
        for peer in [1, 2]:
            s.replicate(0, peer)
            s.deliver()
        self.assertEqual((nodes[0].commit, nodes[0].state), (0, 0))
        s.blocked.clear()
        s.replicate(0, 1)
        s.deliver(duplicate=True)
        s.deliver()
        self.assertEqual((nodes[0].commit, nodes[0].state), (1, 7))
        for peer in [1, 2]:
            s.replicate(0, peer)
            s.deliver()
        self.assertEqual([n.state for n in nodes], [7, 7, 7])

    def test_all_single_entry_delivery_orders_and_losses(self):
        # Four queued RPCs: duplicated to each follower. 24 orders x 16 loss masks.
        checked = 0
        for order in permutations(range(4)):
            for losses in product([False, True], repeat=4):
                nodes = [RaftCore(i) for i in range(3)]
                elect(nodes, 0, [1])
                nodes[0].propose(7)
                targets = [1, 1, 2, 2]
                seen = set()
                for packet in order:
                    peer = targets[packet]
                    if not losses[packet]:
                        result = nodes[peer].append(1, 0, 0, [Entry(1, 7)], 0)
                        nodes[0].acknowledge(peer, *result)
                        seen.add(peer)
                    # Independent oracle: at least one distinct follower got entry.
                    self.assertEqual(nodes[0].commit == 1, bool(seen))
                    for node in nodes:
                        self.assertLessEqual(node.applied, node.commit)
                        self.assertLessEqual(node.commit, len(node.log))
                    self.assertEqual(nodes[0].state, 7 if seen else 0)
                checked += 1
        self.assertEqual(checked, 384)

    def test_crash_stop_and_memory_reboot(self):
        nodes = [RaftCore(i) for i in range(3)]
        elect(nodes, 0, [1])
        nodes[0].propose(7)
        s = Scheduler(nodes)
        s.down.add(1)
        s.replicate(0, 1)
        s.deliver()
        self.assertEqual(nodes[0].commit, 0)
        s.down.remove(1)
        s.replicate(0, 1)
        s.deliver()
        nodes[1].reboot()
        s.replicate(0, 1)
        s.deliver()
        self.assertEqual(nodes[1].state, 7)


class TransactionTests(unittest.TestCase):
    def test_prepared_timeout_indistinguishable_worlds(self):
        first, second = two_pc_unknown(False), two_pc_unknown(True)
        self.assertEqual(first['A_observation'], second['A_observation'])
        self.assertEqual(first['states']['B'], 'prepared')
        self.assertEqual(second['states']['B'], 'committed')
        # Unilateral abort of A in second world disagrees with B.
        self.assertNotEqual('aborted', second['states']['B'])


if __name__ == '__main__':
    unittest.main()
