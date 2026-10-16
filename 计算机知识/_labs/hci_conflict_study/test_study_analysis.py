import copy
import math
import unittest
import study_analysis as lab

class StudyTests(unittest.TestCase):
    def test_original_aggregate_reused_without_inventing_times(self):
        s=lab.summarize(lab.load('legacy-outcomes.json')['records'])
        self.assertEqual(s['unaided_fraction'],[3,5]);self.assertEqual(s['including_help_fraction'],[4,5])
        self.assertEqual(s['completion_time_observed_n'],0);self.assertEqual(s['completion_time_missing_n'],4)
        self.assertIsNone(s['mean_observed_completion_s'])
    def test_dropout_and_technical_denominators(self):
        rows=lab.load('legacy-outcomes.json')['records']
        for outcome in ('abandoned','technical_failure'):
            r=lab.summarize(rows+[{'id':'L6','started':True,'outcome':outcome,'completion_s':None}])
            self.assertEqual(r['unaided_fraction'],[3,6]);self.assertEqual(r['including_help_fraction'],[4,6])
        r=lab.summarize(rows+[{'id':'L6','started':False,'outcome':'technical_failure','completion_s':None}])
        self.assertEqual(r['unaided_fraction'],[3,5]);self.assertEqual(r['registered_attempts'],6);self.assertEqual(r['prestart_technical_failure'],1)
    def test_order_effect_and_pairing(self):
        f=lab.load('comparison.json')
        self.assertEqual(lab.paired(f['fixed_AB']['rows'])['naive_complete_pair_mean_s'],-20)
        s=lab.paired(f['balanced']['rows']);self.assertEqual(s['by_order_mean_s'],{'AB':-30,'BA':10})
        self.assertEqual(s['equal_order_contrast_s'],-10);self.assertEqual(s['complete_pairs'],8)
        self.assertEqual(lab.paired(list(reversed(f['balanced']['rows'])))['equal_order_contrast_s'],-10)
    def test_conditional_interval(self):
        s=lab.conditional_interval(lab.load('comparison.json')['balanced']['rows'])
        self.assertAlmostEqual(s['pooled_residual_variance_s2'],40/3)
        self.assertAlmostEqual(s['standard_error_s'],math.sqrt(5/3))
        self.assertAlmostEqual(sum(s['conditional_95_interval_s'])/2,-10)
    def test_completion_selection_and_missing_pair(self):
        f=lab.load('comparison.json');s=lab.paired(f['completion_selection']['rows'])
        self.assertEqual(s['by_condition']['A']['mean_observed_completion_s'],65)
        self.assertEqual(s['by_condition']['B']['mean_observed_completion_s'],40)
        self.assertEqual(s['naive_complete_pair_mean_s'],10)
        rows=copy.deepcopy(f['balanced']['rows']);rows[-1]['A']={'outcome':'abandoned','completion_s':None}
        s=lab.paired(rows);self.assertEqual(s['complete_pairs'],7);self.assertEqual(s['participants'],8)
        with self.assertRaises(ValueError):lab.conditional_interval(rows)
    def test_rejections(self):
        for bad in (True,0,-1,float('nan'),float('inf'),'30'):
            with self.assertRaises(ValueError):lab.duration(bad)
        rows=lab.load('legacy-outcomes.json')['records']
        with self.assertRaises(ValueError):lab.summarize(rows+[rows[0]])
        with self.assertRaises(ValueError):lab.summarize([{'id':'X','started':False,'outcome':'unaided','completion_s':10}])
        with self.assertRaises(ValueError):lab.summarize([{'id':'X','started':True,'outcome':'abandoned','completion_s':10}])
        bad=copy.deepcopy(lab.load('comparison.json')['balanced']['rows']);bad[0]['order']='AA'
        with self.assertRaises(ValueError):lab.paired(bad)

if __name__=='__main__':unittest.main()
