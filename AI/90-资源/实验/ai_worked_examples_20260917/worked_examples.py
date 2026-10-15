"""Small, deterministic worked examples. Standard library only; no model training.

Run this file to print the exact intermediate objects used in the five lessons.
Probabilities use Fraction where useful; box geometry and SVM use finite floats.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product, permutations
from math import isfinite
import json

SVM_X = ((-1., -1.), (-1., 1.), (1., -1.), (1., 1.), (-2., 0.), (2., 0.))
SVM_Y = (-1., -1., 1., 1., -1., 1.)
SVM_ALPHA = (.25, .25, .25, .25, 0., 0.)


def dot(a, b):
    if len(a) != len(b):
        raise ValueError("dimension mismatch")
    return sum(x*y for x, y in zip(a, b))


def svm_certificate(alpha=SVM_ALPHA):
    """A primal-dual optimality certificate, not a general QP solver."""
    if len(alpha) != len(SVM_X) or any(not isfinite(a) or a < 0 for a in alpha):
        raise ValueError("six finite nonnegative multipliers required")
    w = tuple(sum(a*y*x[j] for a, y, x in zip(alpha, SVM_Y, SVM_X)) for j in range(2))
    margins = [y*dot(w, x) for y, x in zip(SVM_Y, SVM_X)]
    primal = .5*dot(w, w)
    dual = sum(alpha)-.5*dot(w, w)
    return dict(w=w, b=0., gram=[[dot(x, z) for z in SVM_X] for x in SVM_X], margins=margins, primal=primal, dual=dual,
                equality=sum(a*y for a, y in zip(alpha, SVM_Y)),
                complementary=[a*(m-1) for a, m in zip(alpha, margins)])


def kernel_score(x, kernel=dot):
    if len(x) != 2 or any(not isfinite(v) for v in x):
        raise ValueError("finite 2D query required")
    return sum(a*y*kernel(p, x) for a, y, p in zip(SVM_ALPHA, SVM_Y, SVM_X))


@dataclass(frozen=True)
class Factor:
    scope: tuple
    table: dict

    def multiply(self, other):
        scope = tuple(dict.fromkeys(self.scope + other.scope))
        table = {}
        for bits in product((0, 1), repeat=len(scope)):
            env = dict(zip(scope, bits))
            table[bits] = self.table[tuple(env[s] for s in self.scope)] * other.table[tuple(env[s] for s in other.scope)]
        return Factor(scope, table)

    def sum_out(self, name):
        if name not in self.scope:
            raise ValueError("variable outside factor")
        index = self.scope.index(name)
        scope = tuple(s for s in self.scope if s != name)
        table = {bits: F(0) for bits in product((0, 1), repeat=len(scope))}
        for bits, value in self.table.items():
            reduced = bits[:index] + bits[index+1:]
            table[reduced] += value
        return Factor(scope, table)


def binary_cpd(parent, child, p1):
    return Factor((parent, child), {(p, c): p1[p] if c else 1-p1[p] for p, c in product((0, 1), repeat=2)})


def pgm_factors(evidence=1):
    if evidence not in (0, 1):
        raise ValueError("binary evidence required")
    prior = Factor(('A',), {(0,): F(3, 5), (1,): F(2, 5)})
    ab = binary_cpd('A', 'B', (F(1, 5), F(4, 5)))
    bc = binary_cpd('B', 'C', (F(1, 10), F(9, 10)))
    bd = binary_cpd('B', 'D', (F(3, 10), F(7, 10)))
    likelihood = Factor(('B',), {(b,): bc.table[(b, evidence)] for b in (0, 1)})
    return [prior, ab, likelihood, bd]


def eliminate(order=('A', 'B'), evidence=1):
    if tuple(sorted(order)) != ('A', 'B'):
        raise ValueError("eliminate A and B exactly once")
    factors = pgm_factors(evidence)
    trace = []
    for name in order:
        touched = [f for f in factors if name in f.scope]
        factors = [f for f in factors if name not in f.scope]
        joined = touched[0]
        for f in touched[1:]:
            joined = joined.multiply(f)
        reduced = joined.sum_out(name)
        trace.append(dict(variable=name, product=joined, message=reduced, cells=len(joined.table)))
        factors.append(reduced)
    final = factors[0]
    for factor in factors[1:]:
        final = final.multiply(factor)
    mass = sum(final.table.values())
    if mass == 0:
        raise ValueError("zero probability evidence has no posterior")
    return dict(posterior={k: v/mass for k, v in final.table.items()}, evidence=mass,
                trace=trace, product_cells=sum(t['cells'] for t in trace),
                peak_cells=max(t['cells'] for t in trace))


def joint_table():
    """Direct full-joint construction, separate from the elimination routine."""
    rows = {}
    for a, b, c, d in product((0, 1), repeat=4):
        pa = F(2, 5) if a else F(3, 5)
        pb1 = F(4, 5) if a else F(1, 5)
        pc1 = F(9, 10) if b else F(1, 10)
        pd1 = F(7, 10) if b else F(3, 10)
        rows[(a, b, c, d)] = pa * (pb1 if b else 1-pb1) * (pc1 if c else 1-pc1) * (pd1 if d else 1-pd1)
    return rows


CTC_PROBS = ((F(1, 5), F(3, 5), F(1, 5)),
             (F(1, 2), F(1, 5), F(3, 10)),
             (F(1, 5), F(1, 2), F(3, 10)))  # blank, a, b
CTC_VOCAB = ('_', 'a', 'b')


def validate_ctc(probs, target):
    if '_' in target or any(c not in ('a', 'b') for c in target):
        raise ValueError("target must contain only a and b")
    for row in probs:
        if len(row) != 3 or any(not isfinite(float(p)) or p < 0 for p in row) or abs(float(sum(row))-1) > 1e-12:
            raise ValueError("each frame needs three normalized nonnegative finite probabilities")


def ctc_forward(probs=CTC_PROBS, target='aa'):
    validate_ctc(probs, target)
    states = ['_']
    for c in target:
        states.extend((c, '_'))
    if not probs:
        return dict(states=states, alpha=[], probability=F(int(not target)))
    previous = [F(0)]*len(states)
    previous[0] = probs[0][0]
    if target:
        previous[1] = probs[0][CTC_VOCAB.index(target[0])]
    table = [previous]
    for row in probs[1:]:
        current = []
        for s, label in enumerate(states):
            mass = previous[s] + (previous[s-1] if s >= 1 else 0)
            if s >= 2 and label != '_' and label != states[s-2]:
                mass += previous[s-2]
            current.append(mass*row[CTC_VOCAB.index(label)])
        table.append(current)
        previous = current
    probability = previous[-1] + (previous[-2] if target else 0)
    return dict(states=states, alpha=table, probability=probability)


def ctc_enumerate(probs=CTC_PROBS, target='aa'):
    """Oracle: enumerate frame symbols, collapse runs, then remove blanks."""
    validate_ctc(probs, target)
    paths = []
    for indices in product(range(3), repeat=len(probs)):
        runs = [CTC_VOCAB[i] for t, i in enumerate(indices) if t == 0 or i != indices[t-1]]
        if ''.join(c for c in runs if c != '_') == target:
            mass = F(1)
            for t, i in enumerate(indices):
                mass *= probs[t][i]
            paths.append((tuple(CTC_VOCAB[i] for i in indices), mass))
    return dict(paths=paths, probability=sum((v for _, v in paths), F(0)))


GT = ((0., 0., 2., 2.), (3., 0., 5., 2.))
PRED = ((.1, 0., 2.1, 2.), (0., 0., 2., 2.), (3.4, 0., 5.4, 2.))
SCORES = (.9, .8, .7)


def box_area(box):
    if len(box) != 4 or any(not isfinite(v) for v in box) or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("finite xyxy box with positive area required")
    return (box[2]-box[0])*(box[3]-box[1])


def iou(a, b):
    aa, ab = box_area(a), box_area(b)
    intersect = max(0., min(a[2], b[2])-max(a[0], b[0]))*max(0., min(a[3], b[3])-max(a[1], b[1]))
    return intersect/(aa+ab-intersect)


def assignment(gt=GT, pred=PRED):
    if not gt or len(pred) < len(gt):
        raise ValueError("nonempty ground truth and enough predictions required")
    costs = [[sum(abs(x-y) for x, y in zip(g, p)) + 1-iou(g, p) for p in pred] for g in gt]
    options = [(sum(costs[i][j] for i, j in enumerate(perm)), perm) for perm in permutations(range(len(pred)), len(gt))]
    total, chosen = min(options)
    return dict(costs=costs, choices=options, chosen=chosen, total=total)


def detection_ap(gt=GT, pred=PRED, scores=SCORES, threshold=.5):
    """One image/class; no crowd/ignore/NMS; all-points interpolated AP."""
    if not gt or len(pred) != len(scores) or any(not isfinite(s) for s in scores) or not isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("nonempty GT, aligned finite scores, IoU threshold in [0,1] required")
    for box in (*gt, *pred):
        box_area(box)
    unmatched = set(range(len(gt)))
    rows, tp = [], 0
    for rank, j in enumerate(sorted(range(len(pred)), key=lambda j: (-scores[j], j)), 1):
        candidates = [(iou(pred[j], gt[g]), g) for g in sorted(unmatched)]
        overlap, g = max(candidates, default=(-1., -1), key=lambda pair: (pair[0], -pair[1]))
        good = overlap >= threshold
        if good:
            unmatched.remove(g)
            tp += 1
        rows.append(dict(prediction=j, tp=int(good), fp=int(not good), precision=tp/rank, recall=tp/len(gt)))
    envelope = [max((r['precision'] for r in rows[i:]), default=0.) for i in range(len(rows))]
    ap, previous_recall = 0., 0.
    for row, p in zip(rows, envelope):
        ap += (row['recall']-previous_recall)*p
        previous_recall = row['recall']
    return dict(rows=rows, envelope=envelope, ap=ap)


MDP = {('s0', 'go'): ('s1', 0., False), ('s0', 'quit'): ('end', .5, True),
       ('s1', 'finish'): ('end', 2., True), ('s1', 'quit'): ('end', 0., True)}
EPISODES = (('go', 'finish'), ('go', 'finish'), ('go', 'finish'), ('quit',), ('go', 'quit'), ('go', 'quit'))


def bootstrap_target(reward, next_value, terminated, truncated=False, gamma=.5):
    # External truncation ends data collection, not the underlying MDP.
    if any(not isfinite(v) for v in (reward, next_value, gamma)) or not 0 <= gamma <= 1:
        raise ValueError("finite reward/value and gamma in [0,1] required")
    return reward if terminated else reward+gamma*next_value


def mdp_learning(episodes=EPISODES, alpha=.5, gamma=.5):
    if not isfinite(alpha) or not 0 < alpha <= 1 or not isfinite(gamma) or not 0 <= gamma < 1:
        raise ValueError("alpha in (0,1], gamma in [0,1) required")
    mc, td = dict(s0=0., s1=0.), dict(s0=0., s1=0.)
    q = {key: 0. for key in MDP}
    trace = []
    for actions in episodes:
        state, episode = 's0', []
        for action in actions:
            if (state, action) not in MDP:
                raise ValueError("invalid action or action after termination")
            next_state, reward, terminal = MDP[state, action]
            episode.append((state, action, next_state, reward, terminal))
            td[state] += alpha*(bootstrap_target(reward, td.get(next_state, 0.), terminal, gamma=gamma)-td[state])
            next_q = max((v for (s, a), v in q.items() if s == next_state), default=0.)
            key = state, action
            q[key] += alpha*(bootstrap_target(reward, next_q, terminal, gamma=gamma)-q[key])
            state = next_state
        if not episode or not episode[-1][-1]:
            raise ValueError("full episode required for Monte Carlo; external truncation is incomplete")
        returns = [sum(gamma**k*step[3] for k, step in enumerate(episode[t:])) for t in range(len(episode))]
        # No state revisits in this finite acyclic environment.
        for step, value in zip(episode, returns):
            s = step[0]
            mc[s] += alpha*(value-mc[s])
        trace.append(dict(actions=actions, returns=returns, mc=mc.copy(), td=td.copy(), q=q.copy()))
    return trace


def printable(obj):
    if isinstance(obj, F):
        return str(obj)
    if isinstance(obj, Factor):
        return dict(scope=obj.scope, table={str(k): printable(v) for k, v in obj.table.items()})
    if isinstance(obj, dict):
        return {str(k): printable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [printable(v) for v in obj]
    return obj


if __name__ == '__main__':
    print(json.dumps(printable(dict(svm=svm_certificate(), pgm_AB=eliminate(), pgm_BA=eliminate(('B', 'A')),
          joint=joint_table(), ctc_aa=ctc_forward(target='aa'), ctc_aba=ctc_forward(target='aba'),
          assignment=assignment(), ap50=detection_ap(), ap75=detection_ap(threshold=.75),
          rl=mdp_learning())), ensure_ascii=False, indent=2))
