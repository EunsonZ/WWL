"""Independent finite oracles and fixed real-data contract tests; no network."""
import csv
from datetime import date
from itertools import permutations
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import trustworthy_lab as lab

ROOT = Path(__file__).parent


class TrustworthyTests(unittest.TestCase):
    def test_confusion_explicit_records(self):
        # Oracle constructs actual (label, decision) records and counts conditions.
        for case in lab.synthetic_cases().values():
            for g in case.values():
                tp, fn, fp, tn = g['counts_tp_fn_fp_tn']
                records = [(1, 1)]*tp + [(1, 0)]*fn + [(0, 1)]*fp + [(0, 0)]*tn
                positives = [d for y, d in records if y == 1]
                negatives = [d for y, d in records if y == 0]
                decisions = [y for y, d in records if d == 1]
                self.assertAlmostEqual(g['tpr'], sum(positives)/len(positives))
                self.assertAlmostEqual(g['fpr'], sum(negatives)/len(negatives))
                self.assertAlmostEqual(g['ppv'], sum(decisions)/len(decisions))
                self.assertAlmostEqual(g['selection_rate'], sum(d for y,d in records)/len(records))

    def test_bayes_fraction_oracle(self):
        # Joint probability tree enumerated as exact integer counts.
        self.assertAlmostEqual(lab.ppv_from_rates(.2,.8,.1), 160/240)
        self.assertAlmostEqual(lab.ppv_from_rates(.6,.8,.1), 480/520)
        self.assertEqual(lab.ppv_from_rates(.2,.8,0), 1)
        self.assertEqual(lab.ppv_from_rates(.6,0,.1), 0)
        self.assertIsNone(lab.ppv_from_rates(.6,0,0))
        self.assertIsNone(lab.confusion_metrics(0,4,0,6)['ppv'])

    def test_invalid_counts_and_probabilities(self):
        for c in [(0,0,0,0),(-1,2,3,4),(True,2,3,4),(1.0,2,3,4)]:
            with self.assertRaises(ValueError): lab.confusion_metrics(*c)
        for base in [-.1,1.1,float('nan')]:
            with self.assertRaises(ValueError): lab.ppv_from_rates(base,.8,.1)

    def test_time_boundary_oracle(self):
        expected = [('2011-12-31','train'),('2012-01-01','dev'),('2012-06-30','dev'),
                    ('2012-07-01','cal'),('2012-09-30','cal'),('2012-10-01','test')]
        for d,s in expected: self.assertEqual(lab.split_name(date.fromisoformat(d)),s)
        with self.assertRaises(ValueError): lab.split_name(date(2013,1,1))

    def test_real_input_and_disjoint_day_sets(self):
        rows = lab.load_rows(ROOT/'data/hour.csv')
        parts, audit = lab.audit_rows(rows)
        self.assertEqual(audit['recorded_rows'],17379)
        self.assertEqual(audit['absent_grid_hours'],165)
        self.assertEqual([len(parts[s]) for s in ('train','dev','cal','test')],[8645,4358,2208,2168])
        days = [{r['date'] for r in parts[s]} for s in ('train','dev','cal','test')]
        for i in range(4):
            for j in range(i): self.assertFalse(days[i]&days[j])
        # Direct raw CSV oracle for counts and leakage-excluded features.
        with (ROOT/'data/hour.csv').open() as f:
            raw = list(csv.DictReader(f))
        self.assertEqual(sum(1 for r in raw if r['dteday']<'2012-01-01'),8645)
        a = lab.raw_features(rows[:2]); modified = [dict(r, cnt=99999) for r in rows[:2]]
        np.testing.assert_array_equal(a,lab.raw_features(modified))
        self.assertEqual(a.shape,(2,85))

    def test_hash_and_schema_rejections(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.csv'; p.write_text('corrupted')
            with self.assertRaises(ValueError): lab.load_rows(p)
        rows = lab.load_rows(ROOT/'data/hour.csv')
        with self.assertRaises(ValueError): lab.raw_features([dict(rows[0],season=5)])

    def test_scaler_training_only_and_constant_column(self):
        train=np.array([[1.,7.],[3.,7.]])
        mean,scale=lab.fit_scaler(train)
        np.testing.assert_array_equal(mean,[2,7]); np.testing.assert_array_equal(scale,[1,1])
        np.testing.assert_array_equal(lab.design([[101.,7.]],mean,scale),[[1.,99.,0.]])
        # Development values never alter fitted training state.
        np.testing.assert_array_equal(mean,[2,7])
        with self.assertRaises(ValueError): lab.design([[1,2]],[0,0],[1,0])

    def test_ridge_analytic_two_point_oracle(self):
        # x=-1,+1, y=1,3 => intercept2, slope=2/(2+lambda), no inversion oracle.
        z=np.array([[1.,-1.],[1.,1.]])
        w=lab.fit_ridge(z,[1,3],2)
        np.testing.assert_allclose(w,[2,.5],atol=1e-12)
        with self.assertRaises(ValueError): lab.fit_ridge(z,[1,3],0)

    def test_conformal_ranks_exhaustive(self):
        # Four distinct scores; enumerate all 24 assignments to three calibration + test.
        covered=0
        for order in permutations([1.,2.,3.,4.]):
            q=lab.conformal_radius(order[:3],.4)
            covered += order[3] <= q
        self.assertEqual(covered,18)  # rank<=3 among4, observed 75%, requested60%.
        self.assertTrue(np.isinf(lab.conformal_radius([1,2,3],.01)))
        self.assertEqual(lab.conformal_radius([1,1,1],.4),1)
        for a in [[],[-1],[float('nan')]]:
            with self.assertRaises(ValueError): lab.conformal_radius(a,.1)

    def test_cost_and_nonnegative_interval_oracle(self):
        m=lab.metrics([0,4,10],[2,4,6],4)
        self.assertAlmostEqual(m['mae'],2)
        self.assertAlmostEqual(m['cost_under3_over1'],14/3)
        self.assertEqual(m['coverage'],1)
        self.assertAlmostEqual(m['mean_width'],22/3)
        with self.assertRaises(ValueError): lab.metrics([1],[-1])
        with self.assertRaises(ValueError): lab.metrics([1,2],[1])

    def test_lookup_oracle_and_fallback(self):
        rows=[{'hr':1,'workingday':0,'cnt':2},{'hr':1,'workingday':0,'cnt':8},
              {'hr':2,'workingday':1,'cnt':20}]
        m=lab.train_lookup(rows)
        np.testing.assert_allclose(lab.predict_lookup(m,[rows[0],{'hr':9,'workingday':0}]),[5,10])

    def test_tv_categorical_mass_oracle(self):
        self.assertEqual(lab.histogram_tv([.1,.1,.9,.9],[.1,.1,.1,.1])['tv'],.5)
        self.assertEqual(lab.histogram_tv([.1],[.9])['tv'],1)
        self.assertEqual(lab.histogram_tv([1],[1])['tv'],0)
        with self.assertRaises(ValueError): lab.histogram_tv([1.1],[.2])

    def test_release_and_third_state_preservation(self):
        fixture={'contract':lab.CONTRACT,'kind':'hour_workday_mean','fallback':2.,'cells':{}}
        self.assertEqual(lab.release_drill(fixture,dict(fixture,fallback=3.))['rolled_back'],'v0')
        with tempfile.TemporaryDirectory() as t:
            lab.pointer_switch(t,None,b'first')
            (Path(t)/'current.json').write_bytes(b'human-new-version')
            with self.assertRaises(ValueError): lab.pointer_switch(t,b'first',b'rollback')
            self.assertEqual(lab.pointer_read(t),b'human-new-version')

    def test_serialization_reload_and_real_metric_oracle(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'fresh-run'
            report=lab.run_project(ROOT/'data/hour.csv',out)
            model=json.loads((out/'model.json').read_text())
            test=[r for r in lab.load_rows(ROOT/'data/hour.csv') if r['date']>=date(2012,10,1)]
            p=lab.predict_artifact(model,test)
            with (out/'test_predictions.csv').open() as f:
                saved=list(csv.DictReader(f))
            for actual,record in zip(p,saved): self.assertAlmostEqual(actual,float(record['pred']),places=8)
            errors=[abs(int(r['y'])-float(r['pred'])) for r in saved]
            self.assertAlmostEqual(sum(errors)/len(errors),report['test']['selected']['mae'],places=8)
            covered=sum(float(r['lower'])<=int(r['y'])<=float(r['upper']) for r in saved)
            self.assertAlmostEqual(covered/len(saved),report['test']['selected']['coverage'])
            self.assertEqual(report['release_drill']['v1_sha256'],lab.sha_bytes((out/'model.json').read_bytes()))


    def test_existing_output_and_renamed_input_preservation(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t)
            for name in ('model.json','report.json','test_predictions.csv'):
                raw=d/name; raw.write_bytes((ROOT/'data/hour.csv').read_bytes())
                before=raw.read_bytes()
                with self.assertRaises(ValueError): lab.run_project(raw,d)
                self.assertEqual(raw.read_bytes(),before)
            out=d/'existing';out.mkdir();(out/'model.json').write_bytes(b'personal-existing-model')
            with self.assertRaises(ValueError): lab.run_project(ROOT/'data/hour.csv',out)
            self.assertEqual((out/'model.json').read_bytes(),b'personal-existing-model')

    def test_plot_rejects_existing_outputs(self):
        from plot_trustworthy import generate
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'figure.svg';p.write_bytes(b'previous-figure')
            with self.assertRaises(ValueError): generate(ROOT/'results/report.json',t)
            self.assertEqual(p.read_bytes(),b'previous-figure')

    def test_prepublication_hash_and_model_validation(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); original=b'prior-pointer';(d/'current.json').write_bytes(original)
            probe=[{'hr':1,'workingday':1,'season':1,'weathersit':1,'temp':.4,'hum':.5,'windspeed':.2}]
            valid={'contract':lab.CONTRACT,'kind':'hour_workday_mean','fallback':2.,'cells':{}}
            raw=lab.canonical(valid);(d/'v1.json').write_bytes(raw)
            bad_hash=lab.canonical({'version':'v1','model_sha256':'0'*64})
            with self.assertRaises(ValueError): lab.publish_checked(d,original,bad_hash,probe)
            self.assertEqual(lab.pointer_read(d),original)
            for invalid in ({'kind':'unsupported','contract':lab.CONTRACT},
                            dict(valid,fallback=-1), dict(valid,contract='wrong-contract')):
                raw=lab.canonical(invalid);(d/'v1.json').write_bytes(raw)
                pointer=lab.canonical({'version':'v1','model_sha256':lab.sha_bytes(raw)})
                with self.assertRaises(ValueError): lab.publish_checked(d,original,pointer,probe)
                self.assertEqual(lab.pointer_read(d),original)


if __name__=='__main__': unittest.main(verbosity=2)
