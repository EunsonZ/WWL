"""Deterministic, finite teaching models; no sockets, clocks or disk durability.

RaftCore implements selected guards only. It is NOT a complete Raft protocol.
Histories contain completed single-key operations, with one outstanding call/client.
"""
from dataclasses import dataclass, field
from itertools import combinations, permutations


class ClockTrace:
    """Explicit local/send/receive events plus an independent causal DAG."""
    def __init__(self, size):
        if not isinstance(size, int) or size <= 0:
            raise ValueError("positive process count required")
        self.size = size
        self.scalar = [0] * size
        self.vector = [[0] * size for _ in range(size)]
        self.events = []
        self.last = {}
        self.edges = set()

    def event(self, process, receive=None):
        if not isinstance(process, int) or not 0 <= process < self.size:
            raise ValueError("invalid process")
        if receive is not None and not 0 <= receive < len(self.events):
            raise ValueError("receive must name an existing send event")
        index = len(self.events)
        if receive is not None:
            _, scalar, vector = self.events[receive]
            self.scalar[process] = max(self.scalar[process], scalar)
            self.vector[process] = [max(a, b) for a, b in
                                    zip(self.vector[process], vector)]
            self.edges.add((receive, index))
        self.scalar[process] += 1
        self.vector[process][process] += 1
        if process in self.last:
            self.edges.add((self.last[process], index))
        self.last[process] = index
        self.events.append((process, self.scalar[process],
                            tuple(self.vector[process])))
        return index

    def reachability(self):
        # Oracle uses graph traversal, not timestamp comparisons.
        result = set()
        for start in range(len(self.events)):
            todo = [b for a, b in self.edges if a == start]
            while todo:
                dest = todo.pop()
                if (start, dest) in result:
                    continue
                result.add((start, dest))
                todo.extend(b for a, b in self.edges if a == dest)
        return result


def vector_before(a, b):
    if len(a) != len(b) or not a:
        raise ValueError("nonempty equal dimensions required")
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


@dataclass(frozen=True)
class Operation:
    client: str
    kind: str
    value: int
    start: int
    end: int


def serial_witness(history, real_time=True):
    """Return a legal permutation, or None. Exponential; tiny histories only."""
    if len(history) > 8:
        raise ValueError("bounded checker accepts at most 8 operations")
    endpoints = [t for op in history for t in (op.start, op.end)]
    if len(set(endpoints)) != len(endpoints):
        raise ValueError("event endpoints must be distinct order numbers")
    for op in history:
        if (op.kind not in {"put", "get"} or type(op.value) is not int
                or type(op.start) is not int or type(op.end) is not int
                or op.start >= op.end):
            raise ValueError("invalid completed operation")
    for a, b in combinations(history, 2):
        if a.client == b.client and max(a.start, b.start) < min(a.end, b.end):
            raise ValueError("one outstanding call per client required")
    constraints = {(i, j) for i, a in enumerate(history)
                   for j, b in enumerate(history) if a.end < b.start
                   and (real_time or a.client == b.client)}
    for order in permutations(range(len(history))):
        position = {item: i for i, item in enumerate(order)}
        if any(position[a] >= position[b] for a, b in constraints):
            continue
        state = 0
        legal = True
        for index in order:
            op = history[index]
            if op.kind == "put":
                state = op.value
            elif op.value != state:
                legal = False
                break
        if legal:
            return order
    return None


def majority_sets(n):
    if not isinstance(n, int) or n <= 0:
        raise ValueError("positive member count required")
    return [frozenset(c) for c in combinations(range(n), n // 2 + 1)]


@dataclass(frozen=True)
class Entry:
    term: int
    value: int


@dataclass
class RaftCore:
    """Fixed membership, manually driven elections/replication, memory persistence.

    Missing: timers, RPC retries/backtracking, snapshots, membership changes,
    crash-safe writes, read protocol, client deduplication and full safety proof.
    """
    node: int
    members: int = 3
    term: int = 0
    voted_for: int | None = None
    log: list = field(default_factory=list)
    role: str = "follower"
    commit: int = 0
    applied: int = 0
    state: int = 0
    match: dict = field(default_factory=dict)
    votes: set = field(default_factory=set)

    def __post_init__(self):
        if self.members <= 0 or not 0 <= self.node < self.members:
            raise ValueError("invalid membership")

    def observe_term(self, term):
        if term > self.term:
            self.term, self.voted_for, self.role = term, None, "follower"
            self.votes.clear()

    def last(self):
        return (self.log[-1].term, len(self.log)) if self.log else (0, 0)

    def election(self):
        self.term += 1
        self.role = "candidate"
        self.voted_for = self.node
        self.votes = {self.node}
        self.match = {}
        return self.term, self.node, self.last()

    def vote(self, term, candidate, last):
        if not 0 <= candidate < self.members:
            raise ValueError("candidate outside membership")
        self.observe_term(term)
        grant = (term == self.term and last >= self.last()
                 and self.voted_for in (None, candidate))
        if grant:
            self.voted_for = candidate
        return self.term, grant

    def record_vote(self, peer, term, granted):
        if not 0 <= peer < self.members:
            raise ValueError("peer outside membership")
        self.observe_term(term)
        if self.role == "candidate" and term == self.term and granted:
            self.votes.add(peer)
            if len(self.votes) > self.members // 2:
                self.role = "leader"
                self.match = {self.node: len(self.log)}

    def propose(self, value):
        if self.role != "leader":
            raise ValueError("only leader can propose")
        self.log.append(Entry(self.term, value))
        self.match[self.node] = len(self.log)

    def append(self, term, prev_index, prev_term, entries, leader_commit):
        self.observe_term(term)
        if term != self.term:
            return self.term, False, 0
        self.role = "follower"
        if prev_index < 0 or prev_index > len(self.log):
            return self.term, False, 0
        actual = self.log[prev_index - 1].term if prev_index else 0
        if actual != prev_term:
            return self.term, False, 0
        entries = list(entries)
        if any(e.term > term or e.term <= 0 for e in entries):
            raise ValueError("entry term outside RPC term")
        for offset, entry in enumerate(entries):
            index = prev_index + offset
            if index < len(self.log) and self.log[index] != entry:
                if index < self.commit:
                    raise AssertionError("attempt to overwrite committed prefix")
                self.log = self.log[:index]
            if index == len(self.log):
                self.log.append(entry)
        matched = prev_index + len(entries)
        # Empty/short RPC must not commit an unrelated trailing suffix.
        self.commit = max(self.commit, min(leader_commit, matched))
        self.apply()
        return self.term, True, matched

    def acknowledge(self, peer, term, success, matched):
        if not 0 <= peer < self.members:
            raise ValueError("peer outside membership")
        self.observe_term(term)
        if self.role != "leader" or term != self.term or not success:
            return
        if not 0 <= matched <= len(self.log):
            raise ValueError("invalid matched index")
        self.match[peer] = max(self.match.get(peer, 0), matched)
        for index in range(len(self.log), self.commit, -1):
            copies = sum(m >= index for m in self.match.values())
            if copies > self.members // 2 and self.log[index - 1].term == self.term:
                self.commit = index
                break
        self.apply()

    def apply(self):
        while self.applied < self.commit:
            self.state = self.log[self.applied].value
            self.applied += 1

    def reboot(self):
        # Persistent *model* fields term/vote/log survive; no disk IO is tested.
        self.role, self.commit, self.applied, self.state = "follower", 0, 0, 0
        self.match, self.votes = {}, set()


class Scheduler:
    """Manual delivery, reordering, duplication, loss, partitions and crash-stop."""
    def __init__(self, nodes):
        self.nodes = nodes
        self.queue = []
        self.blocked = set()
        self.down = set()
        self.trace = []

    def send(self, source, dest, payload):
        self.queue.append((source, dest, payload))

    def deliver(self, index=0, duplicate=False):
        source, dest, payload = self.queue[index]
        if not duplicate:
            self.queue.pop(index)
        if source in self.down or dest in self.down or (source, dest) in self.blocked:
            self.trace.append(f"DROP {source}->{dest}")
            return
        result = self.nodes[dest].append(*payload)
        self.nodes[source].acknowledge(dest, *result)
        self.trace.append(f"RPC {source}->{dest} {result}; commit={self.nodes[source].commit}")

    def replicate(self, source, dest):
        leader = self.nodes[source]
        # Whole-log RPC from index 0: deliberate simplification, no nextIndex.
        self.send(source, dest, (leader.term, 0, 0, tuple(leader.log), leader.commit))


def elect(nodes, candidate, voters):
    request = nodes[candidate].election()
    for peer in voters:
        term, granted = nodes[peer].vote(*request)
        nodes[candidate].record_vote(peer, term, granted)


def two_pc_unknown(commit_reached_b):
    """A sees the same prepared/timeout trace in two different global worlds."""
    states = {"A": "prepared", "B": "prepared"}
    decision = None
    if commit_reached_b:
        decision, states["B"] = "commit", "committed"
    return {"A_observation": ("prepared", "timeout"),
            "coordinator_decision": decision, "states": states}


def demo():
    nodes = [RaftCore(i) for i in range(3)]
    elect(nodes, 0, [1])
    scheduler = Scheduler(nodes)
    scheduler.blocked.update({(0, 1), (0, 2)})
    nodes[0].propose(7)
    for peer in [1, 2]:
        scheduler.replicate(0, peer)
        scheduler.deliver()
    scheduler.trace.append(f"isolated leader commit={nodes[0].commit}, state={nodes[0].state}")
    scheduler.blocked.clear()
    scheduler.replicate(0, 1)
    scheduler.deliver(duplicate=True)
    scheduler.deliver()
    scheduler.replicate(0, 2)
    scheduler.deliver()
    for peer in [1, 2]:
        scheduler.replicate(0, peer)
        scheduler.deliver()
    for line in scheduler.trace:
        print(line)
    history = [Operation("A", "put", 7, 1, 2), Operation("B", "get", 0, 3, 4)]
    print("stale read sequential=", serial_witness(history, False),
          "linearizable=", serial_witness(history))
    print("2PC worlds=", two_pc_unknown(False), two_pc_unknown(True))


if __name__ == "__main__":
    demo()
