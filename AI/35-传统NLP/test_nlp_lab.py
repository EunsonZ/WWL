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
