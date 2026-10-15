"""Small symbolic-AI mechanisms; Python 3.10+, standard library only.
Search uses exact nonnegative integer costs and integer heuristics.
Run --demo for fixed traces, --test for independent small oracles.
No files, networking, installs, random state, or import-time execution.
"""
from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count, product
import argparse
import json
import math
import unittest

GRAPH = {
    'S': [('A', 4), ('B', 1), ('D', 2)],
    'A': [('G', 3)], 'B': [('A', 1), ('C', 2)],
    'C': [('G', 5)], 'D': [('E', 2)], 'E': [('G', 6)], 'G': [],
}
GOOD_H = {'S': 5, 'A': 3, 'B': 4, 'C': 5, 'D': 8, 'E': 6, 'G': 0}
REOPEN_GRAPH = {'S': [('A', 3), ('B', 1)], 'A': [('G', 2)],
                'B': [('A', 1)], 'G': []}
REOPEN_H = {'S': 0, 'A': 0, 'B': 3, 'G': 0}


def validate_graph(graph, start, goal):
    if start not in graph or goal not in graph:
        raise ValueError('unknown start or goal')
    for edges in graph.values():
        for v, cost in edges:
            if v not in graph or type(cost) is not int:
                raise ValueError('unknown successor or noninteger cost')
            if cost < 0:
                raise ValueError('cost must be a nonnegative integer')


def bfs(graph, start='S', goal='G'):
    validate_graph(graph, start, goal)
    queue = deque([(start, (start,), 0)])
    seen, expanded, pops = {start}, [], []
    while queue:
        u, path, cost = queue.popleft()
        pops.append(u)
        if u == goal:
            return dict(path=path, cost=cost, expanded=expanded, pops=pops)
        expanded.append(u)
        for v, w in graph[u]:
            if v not in seen:
                seen.add(v)
                queue.append((v, path + (v,), cost + w))
    return dict(path=None, cost=None, expanded=expanded, pops=pops)


def astar(graph, h, start='S', goal='G', reopen=True):
    """Improved OPEN entries always replace old g; CLOSED may reopen.
    Strict g improvements and stale-entry checks prevent zero-cycle repeats.
    h validity (admissibility/consistency) is a separate mathematical condition.
    """
    validate_graph(graph, start, goal)
    if set(graph) - set(h) or any(type(h[u]) is not int for u in graph):
        raise ValueError('missing or noninteger heuristic')
    if any(h[u] < 0 for u in graph) or h[goal] != 0:
        raise ValueError('this lab requires nonnegative h and h(goal)=0')
    serial, best, closed = count(), {start: 0}, set()
    heap = [(h[start], next(serial), 0, start, (start,))]
    expanded, pops, reopened = [], [], []
    while heap:
        _, _, g, u, path = heappop(heap)
        if g != best.get(u) or u in closed:
            continue
        pops.append(u)
        if u == goal:
            return dict(path=path, cost=g, expanded=expanded,
                        pops=pops, reopened=reopened)
        closed.add(u)
        expanded.append(u)
        for v, w in graph[u]:
            new_g = g + w
            if new_g >= best.get(v, math.inf):
                continue
            if v in closed:
                if not reopen:
                    continue
                closed.remove(v)
                reopened.append(v)
            best[v] = new_g
            heappush(heap, (new_g + h[v], next(serial), new_g,
                            v, path + (v,)))
    return dict(path=None, cost=None, expanded=expanded,
                pops=pops, reopened=reopened)


def simple_paths_oracle(graph, start, goal):
    """Enumerate simple paths with a stack, independent of heap/search g logic.
    For a finite nonnegative graph, removing cycles never increases cost.
    """
    pending, answers = [(start, (start,), 0)], []
    while pending:
        u, path, total = pending.pop()
        if u == goal:
            answers.append((total, path))
        else:
            for v, w in graph[u]:
                if v not in path:
                    pending.append((v, path + (v,), total + w))
    return sorted(answers)


GAME = [[4, 7, 6], [2, 9, 8], [5, 3, 10]]


def alpha_beta(tree, maximizing=True, alpha=-math.inf, beta=math.inf,
               trace=None, prefix=()):
    if trace is None:
        trace = []
    if isinstance(tree, int):
        trace.append((prefix, tree))
        return tree
    if not tree:
        raise ValueError('nonterminal must have children')
    value = -math.inf if maximizing else math.inf
    for i, child in enumerate(tree):
        cv = alpha_beta(child, not maximizing, alpha, beta, trace, prefix + (i,))
        if maximizing:
            value, alpha = max(value, cv), max(alpha, cv)
        else:
            value, beta = min(value, cv), min(beta, cv)
        if alpha >= beta:
            break
    return value


def strategy_oracle(tree):
    """For this depth-two game enumerate opponent response at EVERY MIN node.
    A fixed root action's guaranteed payoff is its worst response across all
    complete opponent strategies; choose the largest guarantee.
    """
    strategies = list(product(*(range(len(row)) for row in tree)))
    guarantees = [min(tree[a][s[a]] for s in strategies)
                  for a in range(len(tree))]
    return max(guarantees), guarantees


def ac3(domains, constraints):
    """Binary constraints keyed by BOTH directed arcs, converse predicates.
    Copies input; change trace contains (tail, head, removed values).
    """
    d = {x: set(values) for x, values in domains.items()}
    queue, trace = deque(sorted(constraints)), []
    if any(not values for values in d.values()):
        return None, trace
    while queue:
        x, y = queue.popleft()
        removed = {a for a in d[x] if not any(
            constraints[x, y](a, b) for b in d[y])}
        if removed:
            d[x] -= removed
            trace.append((x, y, sorted(removed)))
            if not d[x]:
                return None, trace
            queue.extend((z, x) for z in sorted(d)
                         if z != y and (z, x) in constraints)
    return d, trace


def solve_csp(domains, constraints, use_mrv_mac=False):
    """Return all assignments; count each attempted value, including failures.
    Fixed order: alphabetic. MRV ties: alphabetic. Values: increasing.
    MAC applies AC-3 after each assignment (not at the root).
    """
    solutions, attempts = [], 0
    def visit(assignment, d):
        nonlocal attempts
        if len(assignment) == len(d):
            solutions.append(dict(assignment))
            return
        remaining = [x for x in sorted(d) if x not in assignment]
        x = min(remaining, key=lambda v: (len(d[v]), v)) if use_mrv_mac else remaining[0]
        for a in sorted(d[x]):
            attempts += 1
            if any(not constraints[x, y](a, b) for y, b in assignment.items()
                   if (x, y) in constraints):
                continue
            new_d = {v: set(values) for v, values in d.items()}
            new_d[x] = {a}
            if use_mrv_mac:
                new_d, _ = ac3(new_d, constraints)
                if new_d is None:
                    continue
            visit({**assignment, x: a}, new_d)
    visit({}, {x: set(values) for x, values in domains.items()})
    return solutions, attempts


def csp_oracle(domains, constraints):
    """Full Cartesian product, no propagation or partial-assignment pruning."""
    names, answers = sorted(domains), []
    for values in product(*(sorted(domains[x]) for x in names)):
        a = dict(zip(names, values))
        if all(p(a[x], a[y]) for (x, y), p in constraints.items()):
            answers.append(a)
    return answers


def csp_examples():
    chain = {x: {1, 2, 3} for x in 'XYZ'}
    less = {('X', 'Y'): lambda a, b: a < b,
            ('Y', 'X'): lambda a, b: a > b,
            ('Y', 'Z'): lambda a, b: a < b,
            ('Z', 'Y'): lambda a, b: a > b}
    coloring = {'A': {1, 2, 3}, 'B': {1}, 'C': {1, 2}}
    neq = {(x, y): lambda a, b: a != b for x in coloring
           for y in coloring if x != y}
    return chain, less, coloring, neq


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Fun:
    name: str
    args: tuple = ()


def apply(term, substitution):
    if isinstance(term, Var) and term in substitution:
        return apply(substitution[term], substitution)
    if isinstance(term, Fun):
        return Fun(term.name, tuple(apply(t, substitution) for t in term.args))
    return term


def occurs(variable, term, substitution):
    term = apply(term, substitution)
    return term == variable or (isinstance(term, Fun) and any(
        occurs(variable, t, substitution) for t in term.args))


def unify(left, right):
    """Finite first-order terms, occurs check; return substitution or None.
    Constants are zero-argument Fun objects; input substitutions not accepted.
    """
    pending, sigma = [(left, right)], {}
    while pending:
        a, b = pending.pop()
        a, b = apply(a, sigma), apply(b, sigma)
        if a == b:
            continue
        if isinstance(b, Var) and not isinstance(a, Var):
            a, b = b, a
        if isinstance(a, Var):
            if occurs(a, b, sigma):
                return None
            sigma[a] = b
        elif isinstance(a, Fun) and isinstance(b, Fun) and a.name == b.name and len(a.args) == len(b.args):
            pending.extend(zip(a.args, b.args))
        else:
            return None
    return {v: apply(t, sigma) for v, t in sigma.items()}


def horn_closure(facts, rules):
    """Ground definite Horn rules (body frozenset, head atom)."""
    known = set(facts)
    while True:
        added = {head for body, head in rules if body <= known} - known
        if not added:
            return known
        known |= added


def horn_models_oracle(atoms, facts, rules):
    """Truth-table models; intersect all models for certain positive atoms."""
    certain, model_count = set(atoms), 0
    for bits in product((False, True), repeat=len(atoms)):
        true = {a for a, b in zip(atoms, bits) if b}
        if set(facts) <= true and all(not body <= true or head in true for body, head in rules):
            certain &= true
            model_count += 1
    return certain, model_count


def ancestor_example():
    # Ground the finite, function-free database over exactly three constants.
    people = ('Ada', 'Ben', 'Cora')
    parents = (('Ada', 'Ben'), ('Ben', 'Cora'))
    parent = lambda a, b: 'Parent(' + a + ',' + b + ')'
    anc = lambda a, b: 'Anc(' + a + ',' + b + ')'
    facts = {parent(a, b) for a, b in parents}
    rules = [(frozenset({parent(a, b)}), anc(a, b)) for a, b in parents]
    rules += [(frozenset({parent(a, b), anc(b, c)}), anc(a, c))
              for a, b in parents for c in people]
    atoms = sorted(facts | {anc(a, b) for a in people for b in people})
    return atoms, facts, rules


def resolve(c1, c2, pivot):
    """Ground propositional clauses: literals (atom, positive_boolean)."""
    if (pivot, True) not in c1 or (pivot, False) not in c2:
        raise ValueError('missing complementary pivot')
    return (c1 - {(pivot, True)}) | (c2 - {(pivot, False)})


@dataclass(frozen=True)
class Action:
    name: str
    pre: frozenset
    add: frozenset
    delete: frozenset

    def __post_init__(self):
        if self.add & self.delete:
            raise ValueError('add and delete lists must be disjoint')


def result(state, action):
    if not action.pre <= state:
        raise ValueError('missing preconditions: ' + ','.join(sorted(action.pre - state)))
    return (state - action.delete) | action.add


def replay(initial, plan, goal):
    states = [initial]
    for action in plan:
        states.append(result(states[-1], action))
    if not goal <= states[-1]:
        raise ValueError('executable plan fails goal')
    return states


def plan_bfs(initial, actions, goal):
    queue, seen = deque([(initial, ())]), {initial}
    while queue:
        s, plan = queue.popleft()
        if goal <= s:
            return plan
        for action in actions:
            if action.pre <= s:
                nxt = result(s, action)
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, plan + (action,)))
    return None


def delivery_domain():
    fs = frozenset
    initial, goal = fs({'AtA', 'PkgA', 'HandEmpty'}), fs({'PkgB'})
    actions = (
        Action('Pick', fs({'AtA', 'PkgA', 'HandEmpty'}), fs({'Holding'}), fs({'PkgA', 'HandEmpty'})),
        Action('MoveAB', fs({'AtA'}), fs({'AtB'}), fs({'AtA'})),
        Action('Drop', fs({'AtB', 'Holding'}), fs({'PkgB', 'HandEmpty'}), fs({'Holding'})),
        Action('MoveBA', fs({'AtB'}), fs({'AtA'}), fs({'AtB'})),
    )
    return initial, actions, goal


def delivery_oracle(max_length=3):
    """Enumerate name sequences; simulate an independent physical tuple.
    It never calls result/replay and never reads Action add/delete lists.
    Tuple fields are robot place, package place ('hand' allowed), hand empty.
    """
    names, answers = ('Pick', 'MoveAB', 'Drop', 'MoveBA'), []
    for length in range(max_length + 1):
        for seq in product(names, repeat=length):
            r, p, empty, valid = 'A', 'A', True, True
            for name in seq:
                if name == 'Pick' and r == 'A' and p == 'A' and empty:
                    p, empty = 'hand', False
                elif name == 'MoveAB' and r == 'A':
                    r = 'B'
                elif name == 'MoveBA' and r == 'B':
                    r = 'A'
                elif name == 'Drop' and r == 'B' and p == 'hand':
                    p, empty = 'B', True
                else:
                    valid = False
                    break
            if valid and p == 'B':
                answers.append(seq)
    return answers


class MechanismTests(unittest.TestCase):
    def test_paths(self):
        oracle = simple_paths_oracle(GRAPH, 'S', 'G')
        self.assertEqual(oracle[0][0], 5)
        self.assertEqual(astar(GRAPH, GOOD_H)['cost'], oracle[0][0])
        self.assertEqual(astar(GRAPH, {u: 0 for u in GRAPH})['cost'], oracle[0][0])
        self.assertEqual(bfs(GRAPH)['cost'], 7)
        self.assertEqual(bfs(GRAPH)['path'], ('S', 'A', 'G'))

    def test_exhaustive_three_state_graphs(self):
        edges = [(a, b) for a in 'SAG' for b in 'SAG' if a != b]
        for choices in product((None, 0, 2), repeat=len(edges)):
            graph = {x: [] for x in 'SAG'}
            for (a, b), w in zip(edges, choices):
                if w is not None:
                    graph[a].append((b, w))
            oracle = simple_paths_oracle(graph, 'S', 'G')
            expected = oracle[0][0] if oracle else None
            self.assertEqual(astar(graph, {x: 0 for x in graph})['cost'], expected)

    def test_reopen_and_bad_h(self):
        optimal = simple_paths_oracle(REOPEN_GRAPH, 'S', 'G')[0][0]
        self.assertEqual(astar(REOPEN_GRAPH, REOPEN_H)['cost'], optimal)
        self.assertEqual(astar(REOPEN_GRAPH, REOPEN_H, reopen=False)['cost'], 5)
        self.assertEqual(astar(GRAPH, {**GOOD_H, 'B': 10})['cost'], 7)
        for u in GRAPH:
            d = simple_paths_oracle(GRAPH, u, 'G')[0][0]
            self.assertLessEqual(GOOD_H[u], d)
            for v, w in GRAPH[u]:
                self.assertLessEqual(GOOD_H[u], w + GOOD_H[v])

    def test_cycles_failure_and_invalid(self):
        g = {'S': [('S', 0), ('A', 1)], 'A': [('S', 0)], 'G': []}
        self.assertIsNone(astar(g, {u: 0 for u in g})['path'])
        self.assertIsNone(bfs(g)['path'])
        self.assertEqual(astar({'G': []}, {'G': 0}, 'G', 'G')['cost'], 0)
        with self.assertRaises(ValueError):
            astar({'S': [('G', -1)], 'G': []}, {'S': 0, 'G': 0})

    def test_games(self):
        value, guarantees = strategy_oracle(GAME)
        trace = []
        self.assertEqual(alpha_beta(GAME, trace=trace), value)
        self.assertEqual(guarantees, [4, 2, 3])
        self.assertEqual(len(trace), 6)
        for leaves in product(range(3), repeat=4):
            tree = [list(leaves[:2]), list(leaves[2:])]
            self.assertEqual(alpha_beta(tree), strategy_oracle(tree)[0])

    def test_csp_oracles(self):
        chain, less, coloring, neq = csp_examples()
        for d, c in ((chain, less), (coloring, neq)):
            oracle = csp_oracle(d, c)
            for mode in (False, True):
                answers, _ = solve_csp(d, c, mode)
                norm = lambda rows: sorted(tuple(sorted(row.items())) for row in rows)
                self.assertEqual(norm(answers), norm(oracle))
            pruned, _ = ac3(d, c)
            self.assertIsNotNone(pruned)
            self.assertEqual(csp_oracle(pruned, c), oracle)

    def test_arc_consistency_is_not_solution(self):
        d = {x: {1, 2} for x in 'ABC'}
        c = {(x, y): lambda a, b: a != b for x in d for y in d if x != y}
        pruned, trace = ac3(d, c)
        self.assertEqual(pruned, d)
        self.assertEqual(trace, [])
        self.assertEqual(csp_oracle(d, c), [])
        self.assertEqual(solve_csp(d, c, True)[0], [])

    def test_unification(self):
        x, y, ada = Var('x'), Var('y'), Fun('Ada')
        left, right = Fun('P', (x, Fun('f', (y,)))), Fun('P', (ada, Fun('f', (ada,))))
        sigma = unify(left, right)
        self.assertIsNotNone(sigma)
        self.assertEqual(apply(left, sigma), apply(right, sigma))
        self.assertIsNone(unify(x, Fun('f', (x,))))
        self.assertIsNone(unify(Fun('P', (x, x)), Fun('P', (ada, Fun('Ben')))))
        self.assertIsNone(unify(Fun('P', (x, Fun('f', (x,)))), Fun('P', (Fun('f', (y,)), y))))

    def test_horn_truth_tables(self):
        facts = {'p'}
        rules = [(frozenset({'p'}), 'q'), (frozenset({'q'}), 'r')]
        certain, n = horn_models_oracle(['p', 'q', 'r', 's'], facts, rules)
        self.assertEqual(certain, horn_closure(facts, rules))
        self.assertEqual(certain, {'p', 'q', 'r'})
        self.assertEqual(n, 2)
        atoms, facts, rules = ancestor_example()
        certain, _ = horn_models_oracle(atoms, facts, rules)
        self.assertEqual(certain, horn_closure(facts, rules))
        self.assertEqual(certain - facts, {'Anc(Ada,Ben)', 'Anc(Ben,Cora)', 'Anc(Ada,Cora)'})

    def test_resolution_soundness(self):
        # Check all small clause pairs with p / not-p pivots against truth tables.
        others = [('q', True), ('q', False), ('r', True), ('r', False)]
        subsets = [frozenset(a for a, include in zip(others, bits) if include)
                   for bits in product((False, True), repeat=4)]
        for a, b in product(subsets, repeat=2):
            c1, c2 = a | {('p', True)}, b | {('p', False)}
            resolvent = resolve(c1, c2, 'p')
            for bits in product((False, True), repeat=3):
                assignment = dict(zip('pqr', bits))
                holds = lambda clause: any(assignment[x] == sign for x, sign in clause)
                if holds(c1) and holds(c2):
                    self.assertTrue(holds(resolvent))

    def test_plan_and_physical_oracle(self):
        initial, actions, goal = delivery_domain()
        plan = plan_bfs(initial, actions, goal)
        self.assertEqual(tuple(a.name for a in plan), delivery_oracle()[0])
        self.assertEqual(len(plan), 3)
        states = replay(initial, plan, goal)
        self.assertEqual(states[-1], frozenset({'AtB', 'PkgB', 'HandEmpty'}))
        with self.assertRaises(ValueError):
            replay(initial, (actions[1], actions[0], actions[2]), goal)
        with self.assertRaises(ValueError):
            replay(initial, (actions[0], actions[1]), goal)
        self.assertIsNone(plan_bfs(initial, (actions[1], actions[2], actions[3]), goal))
        at_b = frozenset({'AtB', 'PkgA', 'HandEmpty'})
        self.assertEqual(tuple(a.name for a in plan_bfs(at_b, actions, goal)),
                         ('MoveBA', 'Pick', 'MoveAB', 'Drop'))
        already_done = frozenset({'AtB', 'PkgB', 'HandEmpty'})
        self.assertEqual(plan_bfs(already_done, actions, goal), ())
        with self.assertRaises(ValueError):
            Action('Bad', frozenset(), frozenset({'x'}), frozenset({'x'}))


def demo():
    chain, less, coloring, neq = csp_examples()
    domains, ac_trace = ac3(chain, less)
    trace = []
    game_value = alpha_beta(GAME, trace=trace)
    initial, actions, goal = delivery_domain()
    plan = plan_bfs(initial, actions, goal)
    return {
        'bfs': bfs(GRAPH),
        'ucs': astar(GRAPH, {u: 0 for u in GRAPH}),
        'astar': astar(GRAPH, GOOD_H),
        'inadmissible': astar(GRAPH, {**GOOD_H, 'B': 10}),
        'inconsistent_reopen': astar(REOPEN_GRAPH, REOPEN_H),
        'inconsistent_no_reopen': astar(REOPEN_GRAPH, REOPEN_H, reopen=False),
        'paths_oracle': simple_paths_oracle(GRAPH, 'S', 'G'),
        'alpha_beta': {'value': game_value, 'leaves': trace,
                       'strategy_oracle': strategy_oracle(GAME)},
        'ac3_chain': {'domains': {k: sorted(v) for k, v in domains.items()},
                      'removed': ac_trace},
        'coloring_fixed': solve_csp(coloring, neq),
        'coloring_mrv_mac': solve_csp(coloring, neq, True),
        'ancestor_closure': sorted(horn_closure(ancestor_example()[1], ancestor_example()[2])),
        'plan': [a.name for a in plan],
        'plan_states': [sorted(s) for s in replay(initial, plan, goal)],
        'plan_oracle': delivery_oracle(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if args.test:
        unittest.main(argv=['symbolic_ai_lab.py'], verbosity=2)
    else:
        print(json.dumps(demo(), ensure_ascii=False, indent=2))
