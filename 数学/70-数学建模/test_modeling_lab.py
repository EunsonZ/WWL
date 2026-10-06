"""Independent exact-rational oracles and input-contract tests."""
import csv
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest
import numpy as np
from modeling_lab import (design, fit, predict, metrics, load_data, interval, choose_degree)

class ModelingTests(unittest.TestCase):
    def test_toy_quadratic_exact_oracle(self):
        # Three equations: a-b+c=316, a=332, a+b+c=356.
        beta,_ = fit([1959,1979,1999],[316,332,356],2)
        np.testing.assert_allclose(beta,[332,20,4],rtol=0,atol=1e-10)
        self.assertAlmostEqual(predict([2019],beta)[0],388,places=9)

    def test_toy_linear_exact_oracle(self):
        beta,_ = fit([1959,1979,1999],[316,332,356],1)
        np.testing.assert_allclose(beta,[float(F(1004,3)),20],rtol=0,atol=1e-10)
        m=metrics([316,332,356],predict([1959,1979,1999],beta))
        self.assertAlmostEqual(m['rmse']**2,float(F(32,9)),places=9)

    def test_real_training_fraction_oracle(self):
        # Direct CSV parsing with Fraction, separate from loader and NumPy solver.
        path=Path(__file__).parent/'数据/co2_annmean_mlo.csv'
        with path.open() as f:
            rows=list(csv.DictReader(line for line in f if not line.startswith('#')))
        points=[(F(int(r['year'])-1979,20),F(r['mean'])) for r in rows if 1959 <= int(r['year']) <= 1999]
        n=F(len(points)); s2=sum(x*x for x,y in points); s4=sum(x**4 for x,y in points)
        sy=sum(y for x,y in points); sxy=sum(x*y for x,y in points); sx2y=sum(x*x*y for x,y in points)
        # Symmetry makes sum(x)=sum(x^3)=0. Solve two by two exactly.
        det=n*s4-s2*s2
        exact=[(sy*s4-sx2y*s2)/det,sxy/s2,(n*sx2y-s2*sy)/det]
        data=load_data(path); train=interval(data,1959,1999)
        beta,_=fit(train[:,0],train[:,1],2)
        np.testing.assert_allclose(beta,[float(b) for b in exact],rtol=0,atol=1e-10)
        held=[r for r in rows if 2010 <= int(r['year']) <= 2025]
        errors=[sum(exact[i]*F(int(r['year'])-1979,20)**i for i in range(3))-F(r['mean']) for r in held]
        exact_mse=sum(e*e for e in errors)/len(errors)
        h=interval(data,2010,2025)
        self.assertAlmostEqual(metrics(h[:,1],predict(h[:,0],beta))['rmse']**2,float(exact_mse),places=9)

    def test_sensitivity_analytic(self):
        self.assertAlmostEqual(predict([2025],[332,20,4.1])[0]-predict([2025],[332,20,4])[0],.529,places=10)

    def test_metrics_hand_example(self):
        m=metrics([1,3],[2,1])
        self.assertEqual(m['n'],2)
        self.assertEqual(m['mae'],1.5)
        self.assertEqual(m['bias'],-.5)
        self.assertAlmostEqual(m['rmse'],2.5**.5)

    def test_basis_change_keeps_predictions(self):
        years=[1959,1979,1999,2001]
        values=[316,332,356,359]
        a,_=fit(years,values,2)
        b,_=fit(years,values,2,center=1999,scale=10)
        np.testing.assert_allclose(predict([2005,2010],a),predict([2005,2010],b,1999,10),rtol=0,atol=1e-9)

    def test_fit_rank_and_lengths(self):
        for years,values,degree in [([1,1,1],[2,3,4],2),([1,2],[1],1),([1,2],[1,2],2)]:
            with self.assertRaises(ValueError): fit(years,values,degree)

    def test_design_invalid(self):
        for years,degree,center,scale in [([],1,1979,20),([float('nan')],1,1979,20),([[1]],1,1979,20),([1],3,1979,20),([1],True,1979,20),([1],1,1979,0),([1],1,float('inf'),20),([1],2,0,1e-320)]:
            with self.assertRaises(ValueError): design(years,degree,center,scale)

    def test_predict_invalid(self):
        for beta in [[],[1],[1,2,3,4],[1,float('inf')]]:
            with self.assertRaises(ValueError): predict([2000],beta)
        with self.assertRaises(ValueError): predict([1e308],[1,1e308],0,1)

    def test_metric_invalid(self):
        for y,p in [([],[]),([1],[1,2]),([float('nan')],[1]),([1e308],[-1e308])]:
            with self.assertRaises(ValueError): metrics(y,p)

    def test_loader_contracts(self):
        invalid=['x,y,z\n1,2,3\n','year,mean,unc\n1,2,0\n1,3,0\n','year,mean,unc\n1,-999,0\n',
                 'year,mean,unc\n1,2,-1\n','year,mean,unc\n1.5,2,0\n','year,mean,unc\n1,nan,0\n',
                 'year,mean,unc\n1,foo,0\n','year,mean,unc\n']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bad.csv'
            for text in invalid:
                path.write_text(text)
                with self.assertRaises(ValueError): load_data(path)

    def test_nonfirst_row_field_errors(self):
        # First row is valid: errors in later rows must never be ignored.
        prefix='year,mean,unc\n1959,315.98,.12\n'
        invalid=[prefix+'1960,316.91,.12,unexpected\n',
                 prefix+'1960,316.91\n', prefix+'1960,316.91,\n',
                 prefix+'1960, , .12\n',
                 'year,mean,unc,unc\n1959,315.98,.12,.12\n']
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'malformed.csv'
            for text in invalid:
                path.write_text(text)
                with self.assertRaises(ValueError): load_data(path)

    def test_intervals_and_official_endpoints(self):
        data=load_data(Path(__file__).parent/'数据/co2_annmean_mlo.csv')
        self.assertEqual(data.shape,(67,3))
        np.testing.assert_array_equal(data[0],[1959,315.98,.12])
        np.testing.assert_array_equal(data[-1],[2025,427.35,.12])
        self.assertEqual(interval(data,1959,1999).shape,(41,3))
        for first,last in [(1958,1999),(2000,2026),(2001,2000),(1959.5,1999)]:
            with self.assertRaises(ValueError): interval(data,first,last)

    def test_selection_predefined_tie(self):
        self.assertEqual(choose_degree({1:1,2:1}),1)
        self.assertEqual(choose_degree({1:2,2:1}),2)
        self.assertEqual(choose_degree({1:1+5e-10,2:1}),1)
        for scores in [{1:1},{1:-1,2:1},{1:float('nan'),2:1}]:
            with self.assertRaises(ValueError): choose_degree(scores)

if __name__ == '__main__': unittest.main()
