"""Contract tests; independent expected arcs/counts are stated as literals."""
from copy import deepcopy
import os
from pathlib import Path
import unittest
import structure_lab as lab


class StructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent,_=lab.load_parent(os.environ.get('WWL_NLP_SOURCE'))
        cls.words='I saw birds with scopes'.split();cls.upos=['PRON','VERB','NOUN','ADP','NOUN']
        cls.analyses=[lab.to_dependency(t,cls.words,cls.upos) for t in cls.parent.cky(cls.words,cls.parent.LEXICAL,cls.parent.BINARY)[0]]
        cls.np=next(x['rows'] for x in cls.analyses if x['rows'][4]['head']==3)
        cls.vp=next(x['rows'] for x in cls.analyses if x['rows'][4]['head']==2)

    def test_head_rules_and_repeated_word_positions(self):
        common=[(2,'nsubj'),(0,'root'),(2,'obj'),(5,'case')]
        self.assertEqual([(r['head'],r['relation']) for r in self.np],common+[(3,'nmod')])
        self.assertEqual([(r['head'],r['relation']) for r in self.vp],common+[(2,'obl')])
        words=['I','saw','I'];trees,_=self.parent.cky(words,self.parent.LEXICAL,self.parent.BINARY)
        rows=lab.to_dependency(trees[0],words,['PRON','VERB','PRON'])['rows']
        self.assertEqual([(r['id'],r['head']) for r in rows],[(1,2),(2,0),(3,2)])
        longer='I saw birds with scopes with scopes'.split();ts,_=self.parent.cky(longer,self.parent.LEXICAL,self.parent.BINARY)
        self.assertGreater(len(ts),2)
        for t in ts:self.assertEqual(len(lab.to_dependency(t,longer,['PRON','VERB','NOUN','ADP','NOUN','ADP','NOUN'])['rows']),7)

    def test_arc_and_label_metrics_and_reference_masks(self):
        r=lab.aligned_scores(self.np,self.vp);self.assertEqual((r['denominator'],r['uas_correct'],r['las_correct']),(5,4,4))
        label=deepcopy(self.np);label[-1]['relation']='obl'
        r=lab.aligned_scores(self.np,label);self.assertEqual((r['UAS'],r['LAS']),(1,.8))
        gold=deepcopy(self.np);pred=deepcopy(self.vp)
        for rows in [gold,pred]:rows.append(dict(id=6,form='.',upos='PUNCT',head=2,relation='punct'))
        for punct,root,expected in [(True,True,(6,5,5)),(False,True,(5,4,4)),(False,False,(4,3,3))]:
            r=lab.aligned_scores(gold,pred,punct,root);self.assertEqual((r['denominator'],r['uas_correct'],r['las_correct']),expected)
        pred[-1]['upos']='NOUN'
        self.assertEqual(lab.aligned_scores(gold,pred,False)['denominator'],5)
        self.assertIsNone(lab.aligned_scores([],[])['LAS'])
        sole=[dict(id=1,form='saw',upos='VERB',head=0,relation='root')]
        self.assertIsNone(lab.aligned_scores(sole,sole,False,False)['UAS'])

    def test_invalid_tree_and_alignment_are_not_scores(self):
        for mutate in [lambda x:x[0].update(head=1),lambda x:x[0].update(head=3),lambda x:x[0].update(head=0,relation='root'),lambda x:x[0].update(id=2)]:
            p=deepcopy(self.np);mutate(p)
            # The head3 mutation alone is legal; close a cycle explicitly.
            if p[0]['head']==3:p[2]['head']=1
            with self.assertRaises(ValueError):lab.validate(p)
        wrong=deepcopy(self.np);wrong[-1]['form']='scope'
        with self.assertRaises(ValueError):lab.aligned_scores(self.np,wrong)
        tree=('X',('NP','I'),('NP','birds'))
        with self.assertRaises(ValueError):lab.to_dependency(tree,['I','birds'],['PRON','NOUN'])

    def test_local_scores_can_violate_global_tree_constraint(self):
        r=lab.supplied_score_example(dict(nodes=3,nonzero=[[2,1,3],[1,2,3],[0,3,2]],other_score=0))
        self.assertEqual((r['all_combinations'],len(r['valid_candidates'])),(27,9))
        self.assertEqual((r['local_heads'],r['local_score']),([2,1,0],8))
        self.assertEqual(r['best_legal_score'],5)
        self.assertEqual({tuple(x['heads']) for x in r['best_legal']},{(2,3,0),(3,1,0)})
        with self.assertRaises(ValueError):lab.supplied_score_example(dict(nodes=6,nonzero=[],other_score=0))


if __name__=='__main__':unittest.main(verbosity=2)
