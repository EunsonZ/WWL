"""High-impact objective/label access checks for this finite teaching fixture."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

SPEC=importlib.util.spec_from_file_location('ratings',Path(__file__).with_name('ratings_lab.py'))
lab=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(lab)
INPUTS=Path(__file__).resolve().parents[1]/'inputs'


class RatingsTests(unittest.TestCase):
    def setUp(self):
        self.protocol=json.loads((INPUTS/'protocol.json').read_text())
        self.train=json.loads((INPUTS/'train.json').read_text())

    def test_all_42_gradient_coordinates(self):
        parameters=lab.initialize(self.protocol);mean=np.mean([x['rating'] for x in lab.rated(self.train)])
        _,gradient=lab.objective_gradient(parameters,self.train,mean,.01)
        max_error=0.
        for key,value in parameters.items():
            for index in np.ndindex(value.shape):
                old=value[index];epsilon=1e-5
                value[index]=old+epsilon;plus=lab.objective_gradient(parameters,self.train,mean,.01)[0]
                value[index]=old-epsilon;minus=lab.objective_gradient(parameters,self.train,mean,.01)[0]
                value[index]=old
                max_error=max(max_error,abs((plus-minus)/(2*epsilon)-gradient[key][index]))
        self.assertLess(max_error,2e-9)

    def test_missing_cells_and_two_worlds(self):
        p=lab.initialize(self.protocol);r=lab.rated(self.train)
        a,ga=lab.objective_gradient(p,self.train,3.,.01);b,gb=lab.objective_gradient(p,r,3.,.01)
        self.assertEqual(a,b)
        for key in ga:np.testing.assert_array_equal(ga[key],gb[key])
        bad=[dict(x) for x in self.train];bad[-1]['rating']=0.
        with self.assertRaises(ValueError):lab.rated(bad)
        example=lab.analytic_examples()
        self.assertEqual([x['best_item_user0'] for x in example['worlds']],[0,1])
        self.assertEqual(example['exact_rank1_observed_sse'],0.)
        self.assertGreater(example['zero_svd_observed_sse'],0.)
        self.assertAlmostEqual(example['manual_step']['new_p'],1.19)
        self.assertAlmostEqual(example['manual_step']['new_q'],2.08)
        self.assertAlmostEqual(example['manual_step']['new_prediction'],2.4752)

    def test_item_bias_closed_form_and_metrics(self):
        mean=np.mean([x['rating'] for x in lab.rated(self.train)])
        b=lab.baseline_parameters(self.train,self.protocol,mean);n=len(lab.rated(self.train))
        for i,bias in enumerate(b['item_bias']):
            residual=[x['rating']-mean for x in lab.rated(self.train) if x['item']==i]
            self.assertAlmostEqual((len(residual)+n*.01)*bias,sum(residual),places=13)
        self.assertEqual(lab.metrics([1.,5.],[2.,3.]),dict(n=2,mse=2.5,rmse=np.sqrt(2.5),mae=1.5))

    def test_test_access_guard_and_pre_run(self):
        access=lab.DataAccess(INPUTS)
        with self.assertRaisesRegex(RuntimeError,'before selection'):access.read('test')
        with tempfile.TemporaryDirectory() as temp:
            r=lab.run(INPUTS,temp,pre_run_steps=2,access=access)
        self.assertEqual([x.get('split') for x in r['access_events']],['train'])
        self.assertFalse(access.selection_finished)


if __name__=='__main__':unittest.main(verbosity=2)
