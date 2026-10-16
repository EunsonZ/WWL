"""Only new ranking targets, candidate denominators, and cold/access boundaries."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('ranking',Path(__file__).with_name('ranking_lab.py'))
lab=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(lab)


class RankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lab.set_parent(os.environ.get('WWL_RATINGS_SOURCE'))
        cls.c=json.loads((ROOT/'inputs/protocol.json').read_text());cls.events=json.loads((ROOT/'inputs/train.json').read_text())
        cls.h=lab.history(cls.events,cls.c)

    def test_both_expected_target_gradients(self):
        for sampler in self.c['samplers']:
            pairs=lab.triples(self.h,self.c,sampler);p=lab.initialize(self.c);_,g=lab.objective_gradient(p,pairs,.01)
            self.assertAlmostEqual(sum(r['weight'] for r in pairs),1.)
            for u in self.c['train_users']:self.assertAlmostEqual(sum(r['weight'] for r in pairs if r['user']==u),1/6)
            for key,value in p.items():
                for index in np.ndindex(value.shape):
                    old=value[index];epsilon=1e-5
                    value[index]=old+epsilon;plus=lab.objective_gradient(p,pairs,.01)[0]
                    value[index]=old-epsilon;minus=lab.objective_gradient(p,pairs,.01)[0]
                    value[index]=old
                    self.assertLess(abs((plus-minus)/(2*epsilon)-g[key][index]),2e-9)
            np.testing.assert_array_equal(g['bu'],0.)

    def test_sampler_importance_and_manual_step(self):
        e=lab.finite_examples();loss=np.logaddexp(0.,-np.array([0.,2.]))
        self.assertNotAlmostEqual(e['sampler_loss']['uniform'],e['sampler_loss']['skew'])
        self.assertAlmostEqual(np.sum(np.array([.9,.1])*np.array(e['sampler_loss']['importance_weights'])*loss),e['sampler_loss']['uniform'])
        gamma=1/(1+np.exp(1.));self.assertAlmostEqual(e['manual_bpr']['new_p'],1+.1*gamma)
        scores=np.array([2.,1.,0.]);eps=1e-5
        for k in range(3):
            a=scores.copy();a[k]+=eps;b=scores.copy();b[k]-=eps
            fd=((np.logaddexp.reduce(a)-a[0])-(np.logaddexp.reduce(b)-b[0]))/(2*eps)
            self.assertLess(abs(fd-e['listwise']['gradient'][k]),2e-10)

    def test_full_and_conditional_candidate_denominators(self):
        a=lab.list_metrics([1,0,2,3],[0,3],2,[0,1,2,3]);b=lab.list_metrics([1,0],[0,3],2,[0,1,2,3])
        self.assertEqual(a['recall'],.5);self.assertEqual(b['recall'],.5)
        self.assertAlmostEqual(a['ndcg'],(1/np.log2(3))/(1+1/np.log2(3)))
        self.assertAlmostEqual(b['conditional_ndcg'],1/np.log2(3));self.assertEqual(b['conditional_recall'],1.)
        empty=lab.list_metrics([1,2],[0,3],2,[0,1,2,3]);self.assertIsNone(empty['conditional_ndcg']);self.assertEqual(empty['ndcg'],0.)
        self.assertIsNone(lab.list_metrics([0,1],[],2,[0,1])['ndcg'])
        with self.assertRaises(ValueError):lab.list_metrics([1,1],[0],2,[0,1])

    def test_cold_fallback_and_history_visibility(self):
        p=lab.initialize(self.c);counts=self.h.sum(axis=0)
        np.testing.assert_array_equal(p['P'][6:],0.);np.testing.assert_array_equal(p['Q'][4:],0.)
        np.testing.assert_array_equal(lab.scores_for('bpr_uniform',p,self.h,self.c,6,list(range(6))),counts)
        np.testing.assert_array_equal(lab.scores_for('neighbors',None,self.h,self.c,6,list(range(6))),counts)
        np.testing.assert_array_equal(lab.scores_for('bpr_uniform',p,self.h,self.c,0,[4,5]),[0.,0.])
        bad=[dict(self.events[0])];bad[0]['user']=7
        with self.assertRaises(ValueError):lab.history(bad,self.c)

    def test_train_only_pre_run_and_timeline(self):
        with tempfile.TemporaryDirectory() as temp:
            inputs=Path(temp)/'inputs';inputs.mkdir()
            for name in ['protocol.json','train.json']:shutil.copyfile(ROOT/'inputs'/name,inputs/name)
            reader=lab.parent().DataAccess(inputs)
            with self.assertRaises(RuntimeError):reader.read('test')
            result=lab.run(inputs,Path(temp)/'out',pre_run_steps=2,reader=reader)
            self.assertEqual([e.get('split') for e in result['access_events']],['train'])
        e=lab.finite_examples()['timeline']
        self.assertGreater(len(e['random_train']['future_training_events']),0)
        self.assertEqual(e['time_train']['future_training_events'],[])
        self.assertEqual(e['time_train']['available_at_query'],[0])


    def test_balanced_assignment_estimator(self):
        truth=json.loads((ROOT/'inputs/diagnostic-truth.json').read_text())['binary_relevance']
        r=lab.randomization_example(truth)
        self.assertEqual(len(r['allocations']),70)
        self.assertEqual(r['expected_difference'],.25);self.assertEqual(r['population_ATE'],.25)
        self.assertEqual(r['variance_exact'],'1/16')
        self.assertEqual(r['minimum'],-.25);self.assertEqual(r['maximum'],.75)
        self.assertEqual(len(set(tuple(x['treated_B']) for x in r['allocations'])),70)


if __name__=='__main__':unittest.main(verbosity=2)
