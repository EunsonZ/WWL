---
stage: 1
aliases:
  - "传统NLP最小实验"
  - "序列与句法复算"
sources:
  - "https://web.stanford.edu/~jurafsky/slp3/A.pdf"
  - "https://web.stanford.edu/~jurafsky/slp3/19.pdf"
prerequisites:
  - "[[AI/35-传统NLP/01-词级分词与n-gram平滑]]"
  - "[[AI/35-传统NLP/02-HMM前向后向与Viterbi]]"
  - "[[AI/35-传统NLP/03-CRF序列标注与结构化评测]]"
  - "[[AI/35-传统NLP/04-句法结构与最小解析例]]"
---
# 传统 NLP 模型与动态规划复算

这是四课共享的标准库实验。源码 [nlp_lab.py](nlp_lab.py) 与测试 [test_nlp_lab.py](test_nlp_lab.py) 为真源，下方保持逐字镜像。没有依赖安装、真实语料下载、参数训练或服务启动。

从库根运行（本库已有 Python 环境）：

```bash
.venv/bin/python -B AI/35-传统NLP/nlp_lab.py
.venv/bin/python -B -m unittest discover -s AI/35-传统NLP -p 'test_nlp_lab.py' -v
```

无此虚拟环境时，代码只依赖 Python 标准库，可用已有 Python 3；这不是自动安装环境的指令。演示打印 log 表，`-Infinity` 表示禁用路径的 log 权重（Python JSON 展示扩展，不是严格 JSON 交换格式）；文中概率表由这些数取 exp。交换到其他软件时须把无限值编码为字符串或 null 并另定语义。

## 输出怎么对照课文

| 项目 | 本例预期 | 检查的结论 |
| --- | --- | --- |
| 词级计数 | 9 个预测目标，含每句终止 | 起始不是目标，终止计入频次 |
| fish 后插值 | fish/end=29/112、swim=27/112、birds=29/224、UNK=25/224 | 所有目标和为 1 |
| HMM | log P(x)≈−2.349425；P(x)=.095424 | 前向结果等于八条路径求和 |
| HMM MAP | V N V，联合概率 .024576 | max 与 traceback 对照穷举最优 |
| HMM 标签后验 | 三行分别约 (.259557,.740443)、(.420523,.579477)、(.404427,.595573) | 每行归一；边缘 argmax 是 V V V |
| CRF | log Z=ln12；最佳链 B-LOC I-LOC，条件概率 .5 | 五条合法 BIO2 链的归一与 MAP |
| 实体失败例 | token accuracy=.9；TP=0、FP=1、FN=1、实体 F1=0 | 精确边界与 token 标签正确是不同目标 |
| 句法 | [1,5) 的 VP 有 2 条推导；全句 S 有 2 树 | 分别对应 NP / VP 的 PP 附着 |

[[AI/35-传统NLP/02-HMM前向后向与Viterbi]] 给每格的手算含义；[[AI/35-传统NLP/03-CRF序列标注与结构化评测]] 给严格 BIO2 和空分母协议；[[AI/35-传统NLP/04-句法结构与最小解析例]] 列全部非空 CKY 格，避免只看最终数。

## oracle 与失败条件

测试不只检查“函数等于另一个调用”。HMM oracle 直接乘初始/转移/发射概率枚举全部状态链，再独立算总和、最大值与边缘；CRF oracle 直接列五条合法链和整数权重，不调用 mask 构造合法集合；CKY oracle 先枚举五叶的所有二叉树形状，再按文法为节点贴标签，不使用 chart。分词 oracle 递归枚举所有字典切分，对照最长匹配。

额外检查 $k=10^{308}$ 时完整分布约为 1/5、句子 log 概率为 $-3\ln5$，以及最小正浮点 $k$ 导致正概率不可表示时显式报错；还检查 4000 词的 HMM、3000 词的 bigram、零发射导致不可能观测、空输入、shape、非法参数/标签/未知词、CRF 全体位置分数平移 1000 后概率不变、句子 ID 隔离和重复文法规则。必要输入检查使用异常，不依赖可被关闭的 assert；unittest 断言只用于测试。

`chain` 是两类模型共享的 log-space 计算器；使用 HMM 时必须先通过概率行校验，CRF 分数不受行归一限制。Bigram 的加性比率先缩放以避免极大有限 $k$ 的分母溢出；若未见事件的正概率低于浮点正数范围则显式拒绝参数。链长度 T 与标签数 K 有限；过于巨大数值相加仍可能超出浮点范围，不能据 log-space 声称任意数值都安全。`cky` 明确返回全部树，输出可指数增长；只适合本页小文法，不承诺大语料内存效率。空句 HMM/CRF 固定长度模型的空路径概率为 1，而无 epsilon 文法的空句没有树，词级 LM 空句仍预测一次终止；这些约定不可互换。

本候选实际运行相关测试 **8 项通过**，并比对上述合成数值；后续源码修改必须重跑。此结果只认证这些执行性质：未验证真实语料训练、POS/NER 准确率、树库转换、真实 Obsidian 显示或人的理解。独立语义与来源审阅另行记录，不由作者测试代替。

## 源码镜像

<!-- code-sync: ./nlp_lab.py -->
~~~python
"""Synthetic word/sequence/CFG lab. Python stdlib only; no trained model claim."""
from collections import Counter
from itertools import product
import json
import math

NEG = -math.inf


def logsumexp(values):
    values = list(values)
    if any(math.isnan(v) or v == math.inf for v in values):
        raise ValueError('scores must be finite or -inf')
    m = max(values, default=NEG)
    return NEG if m == NEG else m + math.log(math.fsum(math.exp(v-m) for v in values))


def _tokens(tokens):
    tokens = tuple(tokens)
    if any(not isinstance(w, str) or not w for w in tokens):
        raise ValueError('tokens must be nonempty strings')
    return tokens


def maxmatch(text, lexicon):
    """Left-to-right longest dictionary match; unknown character is an error."""
    if not isinstance(text, str):
        raise ValueError('text must be string')
    lexicon = set(_tokens(lexicon))
    out, i = [], 0
    while i < len(text):
        matches = [w for w in lexicon if text.startswith(w, i)]
        if not matches:
            raise ValueError(f'unknown character at offset {i}')
        w = max(matches, key=lambda w: (len(w), w))
        out.append(w)
        i += len(w)
    return tuple(out)


class Bigram:
    """Fixed target vocabulary includes </s>, <UNK>, excludes <s>."""
    def __init__(self, sentences, vocabulary):
        self.vocab = tuple(sorted(set(_tokens(vocabulary))))
        if '</s>' not in self.vocab or '<UNK>' not in self.vocab or '<s>' in self.vocab:
            raise ValueError('require end/unknown, exclude start')
        self.counts, self.unigram = Counter(), Counter()
        for sentence in sentences:
            words = _tokens(sentence)
            if any(w in ('<s>', '</s>', '<UNK>') for w in words):
                raise ValueError('raw sentence cannot contain reserved markers')
            words = tuple(self.map(w) for w in words) + ('</s>',)
            for h, w in zip(('<s>',)+words, words):
                self.counts[h, w] += 1
                self.unigram[w] += 1
        if not self.unigram:
            raise ValueError('training corpus must contain at least one sentence')
        self.context = Counter()
        for (h, w), count in self.counts.items():
            self.context[h] += count

    def map(self, word):
        if not isinstance(word, str) or not word:
            raise ValueError('word must be nonempty string')
        return word if word in self.vocab or word == '<s>' else '<UNK>'

    def distribution(self, history, k=1.0, weight=1.0):
        """Convex mixture: weight*add-k bigram + (1-weight)*add-k unigram."""
        if not math.isfinite(k) or k <= 0 or not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError('k>0 and 0<=weight<=1 must be finite')
        h, size = self.map(history), len(self.vocab)
        if h == '</s>':
            raise ValueError('end marker has no next-token distribution')
        n = sum(self.unigram.values())
        # Scale before adding: k*size may overflow although the ratio is bounded.
        def additive(count, total):
            scale = max(total, k)
            ks = k / scale
            return (count / scale + ks) / (total / scale + ks * size)
        result = {w: weight*additive(self.counts[h,w], self.context[h])
                  +(1-weight)*additive(self.unigram[w], n) for w in self.vocab}
        if any(not math.isfinite(p) or p <= 0 for p in result.values()):
            raise ValueError('smoothed positive probabilities are outside float range; increase k')
        return result

    def log_probability(self, sentence, k=1.0, weight=1.0):
        words = _tokens(sentence)
        if any(w in ('<s>', '</s>', '<UNK>') for w in words):
            raise ValueError('raw sentence cannot contain reserved markers')
        words = tuple(self.map(w) for w in words) + ('</s>',)
        return math.fsum(math.log(self.distribution(h,k,weight)[w])
                         for h,w in zip(('<s>',)+words,words))


def _matrix(matrix, rows, cols, name):
    if len(matrix) != rows or any(len(row) != cols for row in matrix):
        raise ValueError(f'{name} shape must be {rows} x {cols}')
    if any(math.isnan(v) or v == math.inf for row in matrix for v in row):
        raise ValueError(f'{name} accepts finite or -inf scores')


def chain(unary, transition, start):
    """Log-space sum-product, posterior and max-product with traceback.

    Shape unary T x K, transition K x K (previous,current), start K.
    Fixed length: no end factor. Empty path has score 0, partition 1.
    Impossible observations: logZ=-inf; posterior/path undefined (None).
    Ties pick smallest local predecessor then smallest final state.
    """
    k, tmax = len(start), len(unary)
    if not k or any(math.isnan(v) or v == math.inf for v in start):
        raise ValueError('nonempty start, finite or -inf')
    _matrix(unary,tmax,k,'unary')
    _matrix(transition,k,k,'transition')
    if not tmax:
        return dict(logZ=0.0,alpha=[],beta=[],posterior=[],delta=[],back=[],path=(),best=0.0)
    alpha = [[start[j]+unary[0][j] for j in range(k)]]
    delta, back = [alpha[0][:]], [[None]*k]
    for t in range(1,tmax):
        alpha.append([unary[t][j]+logsumexp(alpha[t-1][i]+transition[i][j] for i in range(k)) for j in range(k)])
        row, ptr = [], []
        for j in range(k):
            scores = [delta[t-1][i]+transition[i][j] for i in range(k)]
            i = max(range(k), key=lambda i: scores[i])
            row.append(scores[i]+unary[t][j]);ptr.append(i)
        delta.append(row);back.append(ptr)
    logz = logsumexp(alpha[-1])
    beta = [[0.0]*k for _ in range(tmax)]
    for t in range(tmax-2,-1,-1):
        beta[t] = [logsumexp(transition[i][j]+unary[t+1][j]+beta[t+1][j] for j in range(k)) for i in range(k)]
    last = max(range(k),key=lambda j:delta[-1][j])
    best = delta[-1][last]
    path = None
    posterior = None
    if logz != NEG:
        posterior = [[math.exp(alpha[t][j]+beta[t][j]-logz) for j in range(k)] for t in range(tmax)]
        path = [last]
        for t in range(tmax-1,0,-1):
            path.append(back[t][path[-1]])
        path = tuple(reversed(path))
    return dict(logZ=logz,alpha=alpha,beta=beta,posterior=posterior,delta=delta,back=back,path=path,best=best)


def _probrow(row):
    if not row or any(not math.isfinite(p) or p < 0 for p in row) or not math.isclose(math.fsum(row),1.0,rel_tol=0,abs_tol=1e-12):
        raise ValueError('probability row must be nonnegative finite and sum to 1')
    return [math.log(p) if p else NEG for p in row]


def hmm(words, pi, transition, emissions):
    words = _tokens(words)
    k = len(pi)
    start = _probrow(pi)
    if len(transition) != k or any(len(row)!=k for row in transition) or len(emissions)!=k:
        raise ValueError('HMM state shapes differ')
    trans = [_probrow(row) for row in transition]
    vocab = set(emissions[0])
    if any(set(e)!=vocab for e in emissions):
        raise ValueError('emission vocabularies differ')
    for e in emissions:
        _probrow(list(e.values()))
    if any(w not in vocab for w in words):
        raise ValueError('unknown observation; map or smooth before inference')
    unary = [[math.log(e[w]) if e[w] else NEG for e in emissions] for w in words]
    return chain(unary,trans,start)


def _tag(tag):
    if tag == 'O':
        return ('O','')
    if not isinstance(tag,str) or len(tag)<3 or tag[:2] not in ('B-','I-') or not tag[2:]:
        raise ValueError('tag must be O, B-type or I-type')
    return (tag[0],tag[2:])


def bio_mask(labels):
    """Strict BIO2; I-X can follow only B-X or I-X."""
    labels = tuple(labels)
    if not labels or len(set(labels))!=len(labels):
        raise ValueError('nonempty unique labels required')
    parsed = [_tag(label) for label in labels]
    start = [NEG if p=='I' else 0.0 for p,_ in parsed]
    transition = [[0.0 if q!='I' or (p in ('B','I') and x==y) else NEG
                   for q,y in parsed] for p,x in parsed]
    return start,transition


def spans(tags):
    """Strict BIO2 -> set of (start,end_exclusive,type); empty -> empty set."""
    tags = tuple(tags)
    parsed = [_tag(t) for t in tags]
    out, active = set(), None
    for i,(prefix,typ) in enumerate(parsed):
        if prefix == 'I':
            if active is None or active[1]!=typ:
                raise ValueError(f'illegal BIO2 continuation at token {i}')
        else:
            if active is not None:
                out.add((active[0],i,active[1]));active=None
            if prefix=='B':
                active=(i,typ)
    if active is not None:
        out.add((active[0],len(tags),active[1]))
    return out


def entity_metrics(gold_sentences, predicted_sentences):
    """Micro exact typed spans across sentences; zero denominators -> 0.

    No tokens -> accuracy None. Count sentence IDs to prevent cross-sentence match.
    """
    gold_sentences, predicted_sentences = list(gold_sentences),list(predicted_sentences)
    if len(gold_sentences)!=len(predicted_sentences):
        raise ValueError('sentence counts differ')
    g,p,correct,total = set(),set(),0,0
    for sid,(gold,pred) in enumerate(zip(gold_sentences,predicted_sentences)):
        gold,pred = tuple(gold),tuple(pred)
        if len(gold)!=len(pred):
            raise ValueError('token lengths differ')
        g.update((sid,*s) for s in spans(gold));p.update((sid,*s) for s in spans(pred))
        correct += sum(a==b for a,b in zip(gold,pred));total+=len(gold)
    tp = len(g&p);fp=len(p-g);fn=len(g-p)
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else 0.0,
                recall=tp/(tp+fn) if tp+fn else 0.0,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0,
                token_accuracy=correct/total if total else None)


def _grammar(lexical,binary):
    lexical,binary = tuple(lexical),tuple(binary)
    if any(len(r)!=2 or any(not isinstance(x,str) or not x for x in r) for r in lexical):
        raise ValueError('lexical rule must be (A,word)')
    if any(len(r)!=3 or any(not isinstance(x,str) or not x for x in r) for r in binary):
        raise ValueError('binary rule must be (A,B,C)')
    if len(set(lexical))!=len(lexical) or len(set(binary))!=len(binary):
        raise ValueError('duplicate rules rejected')
    return lexical,binary


def cky(words, lexical, binary, root='S'):
    """All explicit trees for tiny CNF examples (exponential output possible).

    Empty -> no trees; no epsilon/unary nonterminal productions supported.
    """
    words = _tokens(words);lexical,binary = _grammar(lexical,binary)
    if not isinstance(root,str) or not root:
        raise ValueError('root must be nonempty string')
    n,chart = len(words),{}
    for i,w in enumerate(words):
        chart[i,i+1]={}
        for a,terminal in lexical:
            if w==terminal:
                chart[i,i+1].setdefault(a,[]).append((a,w))
    for width in range(2,n+1):
        for i in range(n-width+1):
            j=i+width;cell={};chart[i,j]=cell
            for split in range(i+1,j):
                for a,b,c in binary:
                    for left in chart[i,split].get(b,[]):
                        for right in chart[split,j].get(c,[]):
                            cell.setdefault(a,[]).append((a,left,right))
    return chart.get((0,n),{}).get(root,[]),chart


PI=[.2,.8]
TRANSITION=[[.2,.8],[.4,.6]]
EMISSIONS=[{'fish':.6,'swim':.4},{'fish':.4,'swim':.6}]
LEXICAL=[('NP','I'),('NP','birds'),('NP','scopes'),('V','saw'),('P','with')]
BINARY=[('S','NP','VP'),('VP','V','NP'),('VP','VP','PP'),('NP','NP','PP'),('PP','P','NP')]


def demo():
    h=hmm(('fish',)*3,PI,TRANSITION,EMISSIONS)
    labels=['O','B-LOC','I-LOC'];start,trans=bio_mask(labels)
    c=chain([[0,math.log(2),0],[0,0,math.log(3)]],trans,start)
    trees,chart=cky('I saw birds with scopes'.split(),LEXICAL,BINARY)
    b=Bigram([['fish','swim'],['fish','fish'],['birds','swim']],['fish','swim','birds','</s>','<UNK>'])
    return dict(hmm=h,crf=c,bigram_after_fish=b.distribution('fish',weight=.75),
                trees=trees,chart={f'{i}:{j}':{a:len(v) for a,v in cell.items()} for (i,j),cell in chart.items()},
                metric=entity_metrics([['B-LOC','I-LOC','O','O','O','O','O','O','O','O']],
                                      [['B-LOC','O','O','O','O','O','O','O','O','O']]))


if __name__=='__main__':
    print(json.dumps(demo(),ensure_ascii=False,indent=2,allow_nan=True))
~~~

<!-- code-sync: ./test_nlp_lab.py -->
~~~python
"""Independent finite enumeration, derivation oracle and numerical properties."""
import itertools
import math
import unittest
from nlp_lab import (Bigram,chain,hmm,spans,entity_metrics,bio_mask,cky,maxmatch,
                     PI,TRANSITION,EMISSIONS,LEXICAL,BINARY,NEG)


class NLPTests(unittest.TestCase):
    def test_word_segmentation(self):
        text='研究生命起源';lexicon={'研究','研究生','生命','命','起源'}
        def enumerate_suffix(rest):
            if not rest:return [()]
            return [(w,*tail) for w in sorted(lexicon) if rest.startswith(w)
                    for tail in enumerate_suffix(rest[len(w):])]
        candidates=enumerate_suffix(text)
        self.assertEqual(set(candidates),{('研究','生命','起源'),('研究生','命','起源')})
        self.assertEqual(maxmatch(text,lexicon),('研究生','命','起源'))
        self.assertEqual(maxmatch('',lexicon),())
        with self.assertRaises(ValueError):maxmatch('?',lexicon)
        with self.assertRaises(ValueError):maxmatch(text,{''})

    def test_bigram_counts_and_normalization(self):
        model=Bigram([['fish','swim'],['fish','fish'],['birds','swim']],['fish','swim','birds','</s>','<UNK>'])
        self.assertEqual(sum(model.unigram.values()),9)
        for history in ['<s>','fish','swim','birds','unseen']:
            for weight in [0,.25,.75,1]:
                d=model.distribution(history,k=.3,weight=weight)
                self.assertAlmostEqual(sum(d.values()),1)
                self.assertTrue(all(p>0 for p in d.values()))
        expected={'fish':.75*2/8+.25*4/14,'swim':.75*2/8+.25*3/14,
                  'birds':.75*1/8+.25*2/14,'</s>':.75*2/8+.25*4/14,'<UNK>':.75*1/8+.25*1/14}
        self.assertEqual(model.distribution('fish',weight=.75),expected)
        manual=math.log(3/8)+math.log(1/8)+math.log(1/6)
        self.assertAlmostEqual(model.log_probability(['fish','birds']),manual)
        self.assertTrue(math.isfinite(model.log_probability(['fish']*3000)))
        self.assertTrue(math.isfinite(model.log_probability([])))
        with self.assertRaises(ValueError):model.distribution('fish',k=0)
        with self.assertRaises(ValueError):model.distribution('fish',weight=math.nan)
        with self.assertRaises(ValueError):model.distribution('</s>')
        with self.assertRaises(ValueError):model.log_probability(['</s>'])
        with self.assertRaises(ValueError):Bigram([],['</s>','<UNK>'])

    def test_bigram_extreme_smoothing_range(self):
        model=Bigram([['fish','swim'],['fish','fish'],['birds','swim']],
                     ['fish','swim','birds','</s>','<UNK>'])
        # At k=1e308, counts <=9 are negligible compared with k: the exact
        # ratio differs from 1/5 below double precision, independently of code.
        for weight in [0, .25, .75, 1]:
            for history in ['<s>', 'fish', 'unseen']:
                distribution=model.distribution(history,k=1e308,weight=weight)
                for probability in distribution.values():
                    self.assertAlmostEqual(probability,1/5,places=15)
                self.assertAlmostEqual(sum(distribution.values()),1,places=15)
            self.assertAlmostEqual(model.log_probability(['fish','birds'],k=1e308,weight=weight),
                                   -3*math.log(5),places=14)
        # At the smallest positive float, an unseen event divided by a count
        # >1 cannot be represented as a positive double: reject explicitly.
        with self.assertRaisesRegex(ValueError,'outside float range'):
            model.distribution('fish',k=math.ulp(0.0))
        with self.assertRaisesRegex(ValueError,'outside float range'):
            model.log_probability(['fish','birds'],k=math.ulp(0.0))

    def test_hmm_enumeration(self):
        words=['fish']*3;result=hmm(words,PI,TRANSITION,EMISSIONS)
        joint={}
        for path in itertools.product(range(2),repeat=3):
            p=PI[path[0]]
            for t,state in enumerate(path):
                p*=EMISSIONS[state][words[t]]
                if t:p*=TRANSITION[path[t-1]][state]
            joint[path]=p
        total=math.fsum(joint.values())
        self.assertAlmostEqual(total,.095424)
        self.assertAlmostEqual(math.exp(result['logZ']),total)
        self.assertEqual(result['path'],max(joint,key=joint.get))
        self.assertEqual(result['path'],(1,0,1))
        self.assertAlmostEqual(math.exp(result['best']),max(joint.values()))
        for t in range(3):
            self.assertAlmostEqual(sum(result['posterior'][t]),1)
            for state in range(2):
                expected=sum(p for path,p in joint.items() if path[t]==state)/total
                self.assertAlmostEqual(result['posterior'][t][state],expected)
        self.assertEqual(tuple(max(range(2),key=lambda j:result['posterior'][t][j]) for t in range(3)),(1,1,1))
        self.assertTrue(all(result['back'][t][result['path'][t]]==result['path'][t-1] for t in [1,2]))

    def test_hmm_zero_long_invalid_empty(self):
        r=hmm(['fish']*4000,PI,TRANSITION,EMISSIONS)
        self.assertTrue(math.isfinite(r['logZ']))
        self.assertAlmostEqual(sum(r['posterior'][2500]),1,places=10)
        self.assertEqual(hmm([],PI,TRANSITION,EMISSIONS)['path'],())
        r=hmm(['fish'],[1,0],[[1,0],[0,1]],[{'fish':0,'swim':1},{'fish':1,'swim':0}])
        self.assertEqual(r['logZ'],NEG);self.assertIsNone(r['posterior']);self.assertIsNone(r['path'])
        for pi in ([0,0],[1.1,-.1],[math.nan,0]):
            with self.assertRaises(ValueError):hmm(['fish'],pi,TRANSITION,EMISSIONS)
        with self.assertRaises(ValueError):hmm(['new'],PI,TRANSITION,EMISSIONS)
        with self.assertRaises(ValueError):chain([[0,math.inf]],[[0,0],[0,0]],[0,0])
        with self.assertRaises(ValueError):chain([[0]],[[0,0],[0,0]],[0,0])

    def test_crf_independent_legal_paths(self):
        labels=['O','B-LOC','I-LOC'];s,a=bio_mask(labels)
        u=[[0,math.log(2),0],[0,0,math.log(3)]]
        # Oracle specifies legal strings directly, independently of the mask builder.
        weights={('O','O'):1,('O','B-LOC'):1,('B-LOC','O'):2,
                 ('B-LOC','B-LOC'):2,('B-LOC','I-LOC'):6}
        r=chain(u,a,s)
        self.assertAlmostEqual(math.exp(r['logZ']),sum(weights.values()))
        self.assertEqual(tuple(labels[j] for j in r['path']),('B-LOC','I-LOC'))
        self.assertAlmostEqual(math.exp(r['best']-r['logZ']),.5)
        for t in range(2):
            for j,label in enumerate(labels):
                p=sum(v for path,v in weights.items() if path[t]==label)/12
                self.assertAlmostEqual(r['posterior'][t][j],p)
        shifted=chain([[v+1000 for v in row] for row in u],a,s)
        self.assertAlmostEqual(shifted['logZ']-r['logZ'],2000)
        self.assertEqual(shifted['path'],r['path'])
        for row1,row2 in zip(shifted['posterior'],r['posterior']):
            for p,q in zip(row1,row2):self.assertAlmostEqual(p,q)
        ties=chain([[0,0],[0,0]],[[0,0],[0,0]],[0,0])
        self.assertEqual(ties['path'],(0,0))

    def test_bio_spans_and_metrics(self):
        self.assertEqual(spans(['B-X','I-X','B-X','O']),{(0,2,'X'),(2,3,'X')})
        for seq in [['I-X'],['O','I-X'],['B-X','I-Y'],['bad'],['B-']]:
            with self.assertRaises(ValueError):spans(seq)
        r=entity_metrics([['B-LOC','I-LOC']+['O']*8],[['B-LOC']+['O']*9])
        self.assertEqual((r['tp'],r['fp'],r['fn'],r['f1']),(0,1,1,0))
        self.assertEqual(r['token_accuracy'],.9)
        empty=entity_metrics([[]],[[]]);self.assertIsNone(empty['token_accuracy']);self.assertEqual(empty['f1'],0)
        r=entity_metrics([['B-X'],['O']],[['O'],['B-X']])
        self.assertEqual((r['tp'],r['fp'],r['fn']),(0,1,1))
        with self.assertRaises(ValueError):entity_metrics([['O']],[[]])

    def test_cky_all_shapes_derivation_oracle(self):
        words='I saw birds with scopes'.split()
        # Left recursive NP/VP rules cannot use naive expansion. The independent
        # oracle enumerates all binary tree shapes then labels them bottom-up.
        def shapes(items):
            if len(items)==1:return [items[0]]
            return [(l,r) for k in range(1,len(items)) for l in shapes(items[:k]) for r in shapes(items[k:])]
        def label(tree):
            if isinstance(tree,str):return [(a,tree) for a,w in LEXICAL if w==tree]
            return [(a,l,r) for l in label(tree[0]) for r in label(tree[1])
                    for a,b,c in BINARY if l[0]==b and r[0]==c]
        expected={t for shape in shapes(words) for t in label(shape) if t[0]=='S'}
        got,chart=cky(words,LEXICAL,BINARY)
        self.assertEqual(set(got),expected);self.assertEqual(len(got),2)
        self.assertEqual(len(chart[1,5]['VP']),2)
        self.assertEqual(len(cky('I saw birds'.split(),LEXICAL,BINARY)[0]),1)
        self.assertEqual(cky(['I','birds'],LEXICAL,BINARY)[0],[])
        self.assertEqual(cky([],LEXICAL,BINARY)[0],[])
        with self.assertRaises(ValueError):cky(words,LEXICAL, BINARY+BINARY[:1])


if __name__=='__main__':unittest.main()
~~~
