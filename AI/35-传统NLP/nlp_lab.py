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
