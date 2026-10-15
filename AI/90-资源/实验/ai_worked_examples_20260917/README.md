---
type: experiment
content_status: usable
evidence_status: partial
aliases:
  - SVM概率图CTC检测强化学习跟算实验
sources:
  - https://cs229.stanford.edu/notes_archive/cs229-notes3.pdf
  - https://www.cs.cmu.edu/~epxing/Class/10708-19/notes/lecture-04/
  - https://www.cs.toronto.edu/~graves/icml_2006.pdf
  - https://arxiv.org/html/2005.12872v3
  - https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/
---
# 五个可跟算实验：把公式的中间一步打印出来

读公式时最容易卡在“这个约束怎样变成对偶”“这个后验因子到底是哪张表”或“为什么同一个预测训练未匹配、评测却是真阳性”。这里用五个很小的对象打印每一步，主推导保留在原课里；正文、图和程序使用相同数字。源码是本目录的 [worked_examples.py](worked_examples.py)，独立对照和失败边界是 [test_worked_examples.py](test_worked_examples.py)。只需 Python 3 标准库，概率用 `Fraction` 精确计算；SVM、框和表格 RL 用有限浮点数。

## 运行与预期结果

从库根执行以下命令，路径包含中文，应保留引号。第一条输出全部中间对象，第二条运行相关测试；无需安装依赖，也不需要 GPU。

```bash
python3 -B "AI/90-资源/实验/ai_worked_examples_20260917/worked_examples.py"
python3 -B -m unittest discover -s "AI/90-资源/实验/ai_worked_examples_20260917" -p "test_worked_examples.py" -v
```

| 想核对什么 | 去读推导与图 | 函数及关键输出 | 独立对照或失败条件 |
| --- | --- | --- | --- |
| 从硬间隔约束、驻点到核预测 | [[AI/10-机器学习与深度学习基础/15-核方法树集成与归纳偏置#六个二维点：从约束推到对偶，再回到预测\|六个二维点]] | `svm_certificate`：w=(1,0)，margin=(1,1,1,1,2,2)，原始/对偶均 .5；`kernel_score((.5,2))=.5` | 四内点约束给范数下界；另一组最优乘子有紧约束但零乘子；非PSD反例与C=.1时盒约束失败 |
| 完整联合分布与两种消元顺序 | [[AI/10-机器学习与深度学习基础/20-贝叶斯学习概率图模型与近似推断#四个二值变量：同一后验，两种消元成本\|四变量联合表]] | `joint_table`：16项和为1；`eliminate(('A','B'))` 与反序均得 D=1 后验 147/226；`trace` 含每步 product/message | 直接联合枚举对照两个C证据；乘积表总格子数8/12、峰值4/8；重复消元或非二值证据拒绝 |
| CTC 的重复字符、跨越与终值 | [[AI/40-语音与音频模型/03-CTC路径求和流式延迟与语音评测#三帧 aa 与 aba：初始化、跨越和终值完整展开\|三帧前向表]] | `ctc_forward(target='aa')` 得3/20；`target='aba'` 得9/100，打印所有alpha行 | `ctc_enumerate`直接折叠路径；0–4帧全部可生成目标核对且概率总和为1；两帧aa=0、零帧空目标=1；拒绝blank目标和未归一化行 |
| 集合训练分配与排序AP为何不同 | [[AI/15-卷积神经网络/06-检测分割匹配损失与评估协议#两个真框、三个预测：训练分配与评测使用同一组框\|两真框三预测]] | `assignment` 的0起始chosen=(1,2)，即g1→p2、g2→p3；`detection_ap` 得TP/FP序列(1,0,1)/(0,1,0)，AP=5/6，阈值.75时AP=.5 | 六种分配逐项对照；退化框拒绝；同一真框不可重复记TP；只实现单图单类明确协议，不是COCO mAP |
| MC/TD/Q-learning 在同环境怎样学 | [[AI/10-机器学习与深度学习基础/19-强化学习MDP价值函数与策略梯度#同一个有限环境，逐回合观察 MC、TD 与 Q-learning\|六回合学习轨迹]] | `mdp_learning` 最终MC V(s0)=.171875、TD=.5625、Q(s0,go)=.78125；`bootstrap_target(0,2,False,True)=1` | 三种完整行动序列的最优回报1；六回合闭式更新对照；真正terminal屏蔽bootstrap、外部truncated保留；不完整MC回合拒绝 |

程序中的预测、GT和状态索引从0开始，正文框标签从1开始。例如 `chosen=(1,2)` 就是正文的预测2、3。图 [svm_geometry.svg](svm_geometry.svg) 与 [detection_boxes.svg](detection_boxes.svg) 使用正文相同坐标；图中SVM x1方向水平、x2方向竖直，框图的y方向向上。

## 怎样用它检验理解

先把主课的中间表遮住，手算一个格子或一次更新，再用程序核对。PGM 可改证据为0，CTC 可只保留两帧或换目标为 `ab`，检测可把第二预测分数提升至.95，RL可比较正序和反序更新的第一回合。正文末尾的迁移题给参考解；改参数后应重新计算，不把旧乘子、旧分配或旧alpha表当成仍有效的结论。

`svm_certificate` 返回候选解的证书字段，没有实现一般QP优化；`Factor` 的变量域固定为二值；`ctc_forward` 固定教学词表 `_ab`，不处理真实语音、解码搜索或梯度；检测没有NMS、crowd、ignore或类别平均；RL使用确定性有限MDP和脚本行为，固定步长也不证明渐近收敛。这些限制让独立穷举可行，并规定结论可以迁移到哪里。

## 执行和证据范围

2026-09-17 在现有库的 Python 3.14 环境执行本目录源码和13项测试，通过；没有新增依赖。对照包括完整联合枚举、CTC逐帧符号路径枚举、六种检测分配及手算学习轨迹，覆盖合法实例和若干真实失败边界。来源对应公式和协议定位见各主课就近脚注。

此记录只覆盖小型确定性教学实验。未运行真实声学/检测/深度RL训练，未测泛化、GPU性能或流式延迟；尚未在真实Obsidian客户端点击新锚点、渲染图表或验收人的阅读体验。独立内容复核与客户端验收应绑定实际发布版本，本目录不替这些层写通过。

## 附录：可运行源码镜像

以上入口说明用于选择和运行实验。以下两块逐字镜像同目录的源码与测试；修改时以伴随文件为真源，再同步镜像。

### 实验源码

<!-- code-sync: ./worked_examples.py -->
```python
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
```

### 独立对照测试

<!-- code-sync: ./test_worked_examples.py -->
```python
"""Independent enumeration/closed-form checks and failure-boundary tests."""
import unittest
from fractions import Fraction as F
from itertools import product
from math import nan
import worked_examples as w


class SVMTests(unittest.TestCase):
    def test_optimality_certificate_and_kernel(self):
        c = w.svm_certificate()
        self.assertEqual(c['w'], (1., 0.))
        self.assertEqual(c['gram'], [[2,0,0,-2,2,-2],[0,2,-2,0,2,-2],[0,-2,2,0,-2,2],[-2,0,0,2,-2,2],[2,2,-2,-2,4,-4],[-2,-2,2,2,-4,4]])
        self.assertEqual(c['margins'], [1., 1., 1., 1., 2., 2.])
        self.assertEqual(c['equality'], 0.)
        self.assertEqual(c['complementary'], [0.]*6)
        self.assertEqual(c['primal'], .5)
        self.assertEqual(c['dual'], .5)
        for x in product((-2., -.5, 0., .5, 2.), repeat=2):
            self.assertEqual(w.kernel_score(x), x[0])
        # Four tight constraints imply w1 >= 1+|w2|+|b|, hence .5||w||²>=.5.
        for w1, w2, b in product((-.5, 0., .5, 1., 2.), repeat=3):
            feasible = all(y*(w1*x1+w2*x2+b) >= 1 for (x1, x2), y in zip(w.SVM_X, w.SVM_Y))
            if feasible:
                self.assertGreaterEqual(w1, 1+abs(w2)+abs(b))
                self.assertGreaterEqual(.5*(w1*w1+w2*w2), .5)

    def test_tight_does_not_imply_positive_alpha(self):
        c = w.svm_certificate((.5, 0., .5, 0., 0., 0.))
        self.assertEqual(c['primal'], c['dual'])
        self.assertEqual(c['equality'], 0.)
        self.assertEqual(c['complementary'], [0.]*6)
        self.assertEqual(c['margins'][1], 1.)

    def test_invalid_alpha_and_non_psd_similarity(self):
        for bad in ((-.1,)*6, (0.,)*5, (nan,)*6):
            with self.assertRaises(ValueError):
                w.svm_certificate(bad)
        # G=[[1,2],[2,1]]: z=(1,-1), zᵀGz=-2. Cannot be an inner-product Gram.
        self.assertEqual(1-2-2+1, -2)
        with self.assertRaises(ValueError):
            w.kernel_score((1.,))


class PGMTests(unittest.TestCase):
    def test_full_joint_and_two_orders_against_enumeration(self):
        joint = w.joint_table()
        self.assertEqual(len(joint), 16)
        self.assertEqual(sum(joint.values()), 1)
        for evidence in (0, 1):
            mass = sum(v for (a, b, c, d), v in joint.items() if c == evidence)
            numerator = sum(v for (a, b, c, d), v in joint.items() if c == evidence and d == 1)
            for order in (('A', 'B'), ('B', 'A')):
                result = w.eliminate(order, evidence)
                self.assertEqual(result['evidence'], mass)
                self.assertEqual(result['posterior'][(1,)], numerator/mass)
        self.assertEqual(w.eliminate()['posterior'][(1,)], F(147, 226))

    def test_intermediate_tables_and_cost(self):
        ab, ba = w.eliminate(), w.eliminate(('B', 'A'))
        self.assertEqual(ab['trace'][0]['message'].table, {(0,): F(14, 25), (1,): F(11, 25)})
        self.assertEqual(ba['trace'][0]['message'].scope, ('A', 'D'))
        self.assertEqual(ba['trace'][0]['message'].table,
                         {(0, 0): F(11, 100), (0, 1): F(15, 100), (1, 0): F(23, 100), (1, 1): F(51, 100)})
        self.assertEqual((ab['product_cells'], ab['peak_cells']), (8, 4))
        self.assertEqual((ba['product_cells'], ba['peak_cells']), (12, 8))
        with self.assertRaises(ValueError):
            w.eliminate(('A', 'A'))
        with self.assertRaises(ValueError):
            w.eliminate(evidence=2)


class CTCTests(unittest.TestCase):
    def test_published_tables_and_initialization(self):
        aa = w.ctc_forward(target='aa')
        self.assertEqual(aa['alpha'], [[F(1,5),F(3,5),0,0,0],
                         [F(1,10),F(4,25),F(3,10),0,0],
                         [F(1,50),F(13,100),F(23,250),F(3,20),0]])
        self.assertEqual(aa['probability'], F(3,20))
        aba = w.ctc_forward(target='aba')
        self.assertEqual(aba['alpha'][-1], [F(1,50),F(13,100),F(23,250),F(24,125),F(9,250),F(9,100),0])
        self.assertEqual(aba['probability'], F(9,100))

    def test_exhaustive_targets_against_path_oracle(self):
        for frames in range(5):
            probs = (w.CTC_PROBS*2)[:frames]
            total = F(0)
            for length in range(frames+1):
                for chars in product('ab', repeat=length):
                    target = ''.join(chars)
                    dp = w.ctc_forward(probs, target)['probability']
                    oracle = w.ctc_enumerate(probs, target)['probability']
                    self.assertEqual(dp, oracle, (frames, target))
                    total += dp
            self.assertEqual(total, 1)

    def test_repetition_empty_and_invalid_boundaries(self):
        self.assertEqual(w.ctc_forward(w.CTC_PROBS[:2], 'aa')['probability'], 0)
        self.assertEqual(w.ctc_enumerate(target='aa')['paths'], [(('a','_','a'), F(3,20))])
        self.assertEqual(w.ctc_forward([], '')['probability'], 1)
        self.assertEqual(w.ctc_forward([], 'a')['probability'], 0)
        for probs, target in ((((F(1),F(1),F(0)),), 'a'), (w.CTC_PROBS,'_'), (((nan,0,1),),'a')):
            with self.assertRaises(ValueError):
                w.ctc_forward(probs, target)


class DetectionTests(unittest.TestCase):
    def test_assignment_manual_six_options(self):
        result = w.assignment()
        self.assertEqual(result['chosen'], (1, 2))
        self.assertAlmostEqual(result['total'], 17/15)
        self.assertEqual(len(result['choices']), 6)
        # Independent six-case sum from the hand-computed matrix.
        manual = [31/105+7, 31/105+17/15, 0+34/5, 0+17/15, 39/5+34/5, 39/5+7]
        for got, expected in zip([v for v, _ in result['choices']], manual):
            self.assertAlmostEqual(got, expected)

    def test_tp_fp_and_fixed_protocol(self):
        r = w.detection_ap()
        self.assertEqual([row['tp'] for row in r['rows']], [1,0,1])
        self.assertEqual([row['fp'] for row in r['rows']], [0,1,0])
        self.assertEqual([row['precision'] for row in r['rows']], [1.,.5,2/3])
        self.assertEqual([row['recall'] for row in r['rows']], [.5,.5,1.])
        self.assertAlmostEqual(r['ap'], 5/6)
        self.assertAlmostEqual(w.detection_ap(threshold=.75)['ap'], .5)
        self.assertEqual(w.detection_ap(pred=(), scores=())['ap'], 0.)
        # Reordering confidence so FP comes last yields AP=1 despite one FP.
        self.assertEqual(w.detection_ap(scores=(.9,.6,.8))['ap'], 1.)

    def test_geometry_and_invalid_protocol(self):
        self.assertAlmostEqual(w.iou(w.GT[0],w.PRED[0]), 19/21)
        self.assertAlmostEqual(w.iou(w.GT[1],w.PRED[2]), 2/3)
        self.assertEqual(w.iou(w.GT[0],w.GT[1]), 0.)
        for b in ((0,0,0,1), (1,0,0,1), (0,0,nan,1)):
            with self.assertRaises(ValueError):
                w.iou(b, w.GT[0])
        for kw in ({'scores':(1.,)}, {'gt':()}, {'threshold':nan}, {'threshold':2.}):
            with self.assertRaises(ValueError):
                w.detection_ap(**kw)


class RLTests(unittest.TestCase):
    def test_fixed_environment_learning_trace(self):
        rows = w.mdp_learning()
        self.assertEqual([r['mc']['s0'] for r in rows], [.5,.75,.875,.6875,.34375,.171875])
        self.assertEqual([r['td']['s0'] for r in rows], [0.,.25,.5,.5,.6875,.5625])
        self.assertEqual([r['td']['s1'] for r in rows], [1.,1.5,1.75,1.75,.875,.4375])
        self.assertEqual([r['q'][('s0','go')] for r in rows], [0.,.25,.5,.5,.6875,.78125])
        self.assertEqual(rows[-1]['q'][('s0','quit')], .25)
        self.assertEqual(rows[-1]['q'][('s1','finish')], 1.75)
        self.assertEqual(rows[-1]['q'][('s1','quit')], 0.)
        # Full return oracle: enumerate both s0 choices and both subsequent choices.
        returns = [w.MDP[('s0','quit')][1]]
        for a in ('finish','quit'):
            returns.append(w.MDP[('s0','go')][1]+.5*w.MDP[('s1',a)][1])
        self.assertEqual(sorted(returns), [0.,.5,1.])
        self.assertEqual(max(returns), 1.)

    def test_terminal_and_external_truncation(self):
        self.assertEqual(w.bootstrap_target(0.,2.,True),0.)
        self.assertEqual(w.bootstrap_target(0.,2.,False,True),1.)
        self.assertEqual(w.bootstrap_target(0.,2.,True,True),0.)
        with self.assertRaises(ValueError):
            w.mdp_learning((('go',),))
        with self.assertRaises(ValueError):
            w.mdp_learning((('quit','go'),))
        with self.assertRaises(ValueError):
            w.mdp_learning(alpha=0)


if __name__ == '__main__':
    unittest.main()
```
