"""Small exhaustive decoder oracle and train/target visibility contracts."""
from copy import deepcopy
from itertools import product
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest
import dependency_lab as lab


def legal_projective(heads):
    if sum(h==0 for h in heads)!=1:return False
    def path(x):
        seen=[]
        while x:
            if x in seen:return None
            seen.append(x);x=heads[x-1]
        return seen+[0]
    paths=[None]+[path(d) for d in range(1,len(heads)+1)]
    if any(p is None for p in paths[1:]):return False
    return all(h in paths[k] for d,h in enumerate(heads,1) for k in range(min(h,d)+1,max(h,d)))


def exhaustive(scores):
    n=len(scores)-1;best=-math.inf
    for heads in product(*[[h for h in range(n+1) if h!=d] for d in range(1,n+1)]):
        if legal_projective(heads):best=max(best,sum(scores[h][d] for d,h in enumerate(heads,1)))
    return best


class DependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):lab.set_structure(os.environ.get('WWL_STRUCTURE_SOURCE'))

    def test_eisner_matches_exhaustive_descendant_oracle(self):
        rng=random.Random(271)
        for n in range(1,6):
            for repeat in range(2 if n<5 else 1):
                scores=[[lab.NEG]*(n+1) for _ in range(n+1)]
                for d in range(1,n+1):
                    for h in range(n+1):
                        if h!=d:scores[h][d]=rng.uniform(-2,2)
                heads,value=lab.decode(scores)
                self.assertTrue(legal_projective(heads));self.assertAlmostEqual(value,exhaustive(scores),places=11)
        with self.assertRaises(ValueError):lab.decode([[0.,1.],[0.,0.]])

    def test_nonprojective_reference_is_not_rewritten(self):
        gold=[2,0,1];self.assertFalse(legal_projective(gold));self.assertFalse(lab.projective(gold))
        scores=[[lab.NEG]*4 for _ in range(4)]
        for d,hg in enumerate(gold,1):
            for h in range(4):
                if h!=d:scores[h][d]=float(h==hg)
        heads,value=lab.decode(scores);self.assertEqual(value,2);self.assertEqual(gold,[2,0,1])

    def test_count_probabilities_support_and_form_invariance(self):
        rows=[dict(id=1,form='t ex',upos='ADV'),dict(id=2,form='fish',upos='NOUN'),dict(id=3,form='fish',upos='NOUN')]
        features=[dict(sample_id='s',rows=rows)];targets=[dict(sample_id='s',rows=[dict(id=1,head=2,relation='advmod'),dict(id=2,head=0,relation='root'),dict(id=3,head=2,relation='nmod:poss')])]
        for mode,K in [('geometry',17),('upos_geometry',273)]:
            model=lab.CountModel(mode).fit(features,targets);self.assertEqual(model.feature_domain_size(),K)
            key=model.key(rows,2,3,'nmod:poss');context=key[0];p=model.feature_probability(rows,2,3,'nmod:poss',1.)
            self.assertEqual(p,2/(model.conditions[context]+K))
            a,b=model.matrices(rows,1.);changed=deepcopy(rows)
            for i,row in enumerate(changed):row['form']='renamed'+str(i)
            self.assertEqual((a,b),model.matrices(changed,1.));self.assertIn('nmod:poss',model.labels)
            with self.assertRaises(ValueError):model.feature_probability(rows,2,3,'nmod',1.)

    def test_train_only_prerun_and_target_lock(self):
        original=Path(__file__).resolve().parents[1]/'inputs'
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);inputs=tmp/'inputs';inputs.mkdir()
            for name in ['protocol.json','train-features.json','train-targets.json']:shutil.copyfile(original/name,inputs/name)
            r=lab.run(inputs,tmp/'out',True);self.assertTrue(all(x.get('split')=='train' for x in r['access_events']))
            access=lab.DataAccess(inputs)
            with self.assertRaises(RuntimeError):access.targets('test')
            poison=[dict(sample_id='s',rows=[dict(id=1,form='x',upos='NOUN',head=0)])]
            lab.save(inputs/'train-features.json',poison)
            with self.assertRaises(ValueError):access.features('train')


if __name__=='__main__':unittest.main(verbosity=2)
