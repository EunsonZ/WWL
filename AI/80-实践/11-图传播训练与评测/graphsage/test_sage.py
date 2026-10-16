"""Author regression tests. Independent review must use its own aggregation oracle."""
import copy
from fractions import Fraction
import itertools
import unittest
import numpy as np
import sage


class SageTests(unittest.TestCase):
    def setUp(self):
        # Star with degree4 center, degree1 leaves, plus one isolate.
        self.a=np.zeros((1,6,6))
        for i in range(1,5):self.a[0,0,i]=self.a[0,i,0]=1
        self.x=np.array([[[.2,-.3],[-1.,.1],[0.,.7],[1.,-.2],[2.,.4],[.3,.8]]])

    def test_sampling_count_full_and_isolate(self):
        full=sage.sample_operator(self.a,None,np.random.default_rng(17))
        np.testing.assert_equal(full,sage.sample_operator(self.a,4,np.random.default_rng(99)))
        np.testing.assert_equal(full,sage.sample_operator(self.a,10,np.random.default_rng(99)))
        for f in (1,2,3):
            op=sage.sample_operator(self.a,f,np.random.default_rng(17))
            self.assertEqual(np.count_nonzero(op[0,0]),f)
            self.assertEqual(op[0,1,0],1)
            self.assertEqual(op[0,5].sum(),0)
            self.assertFalse(np.diagonal(op,axis1=1,axis2=2).any())
        for bad in (0,-1,True,1.5):self.assertRaises(ValueError,sage.sample_operator,self.a,bad,np.random.default_rng(0))

    def test_exact_enumeration_and_nonlinearity(self):
        result=sage.enumeration()
        values=[Fraction(v)for v in (-1,0,1,2)];mu=sum(values)/4
        for row in result['rows']:
            f=row['fanout'];means=[sum(values[i]for i in ids)/f for ids in itertools.combinations(range(4),f)]
            mean=sum(means)/len(means);variance=sum((m-mu)**2 for m in means)/len(means)
            self.assertEqual(float(mean),row['mean'])
            self.assertAlmostEqual(float(variance),row['variance'])
            self.assertAlmostEqual(float(variance),row['theory_variance'])
        self.assertEqual(result['rows'][1]['mean_relu_of_centered_sample'],.25)
        self.assertEqual(result['rows'][1]['relu_of_centered_population'],0)

    def test_all_parameter_gradients(self):
        y=np.array([[0,0,1,1,1,0]])
        for fanout in (None,2):
            p=sage.initialize(2,3,2,17);ops=sage.operators(self.a,2,fanout,[17,0,0,1])
            _,grad=sage.objective(p,self.x,y,ops)
            for key in p:
                for idx in np.ndindex(p[key].shape):
                    plus,minus=copy.deepcopy(p),copy.deepcopy(p)
                    plus[key][idx]+=1e-6;minus[key][idx]-=1e-6
                    fd=(sage.objective(plus,self.x,y,ops)[0]-sage.objective(minus,self.x,y,ops)[0])/2e-6
                    self.assertAlmostEqual(fd,grad[key][idx],places=6,msg=(fanout,key,idx))

    def test_zero_norm_gradient_and_new_node_count(self):
        p=sage.initialize(1,2,2,17);p['w0'][:]=0;p['b0'][:]=0
        ops=sage.operators(self.a,1,None,[0]);y=np.array([[0,0,1,1,1,0]])
        _,grad=sage.objective(p,self.x,y,ops,epsilon=.01)
        for key in p:
            for idx in np.ndindex(p[key].shape):
                plus,minus=copy.deepcopy(p),copy.deepcopy(p)
                plus[key][idx]+=1e-7;minus[key][idx]-=1e-7
                fd=(sage.objective(plus,self.x,y,ops,epsilon=.01)[0]-sage.objective(minus,self.x,y,ops,epsilon=.01)[0])/2e-7
                self.assertAlmostEqual(fd,grad[key][idx],places=6,msg=(key,idx))
        fresh=np.zeros((1,17,17));fresh_x=np.zeros((1,17,2))
        logits,_=sage.forward(p,fresh_x,sage.operators(fresh,1,2,[17]))
        self.assertEqual(logits.shape,(1,17))

    def test_coupled_permutation_and_normalization(self):
        order=[5,3,0,4,2,1];p=sage.initialize(2,3,2,17)
        ops=sage.operators(self.a,2,2,[17,0,0,1]);original=sage.forward(p,self.x,ops)[0]
        moved=[op[:,order][:,:,order]for op in ops]
        actual=sage.forward(p,self.x[:,order],moved)[0]
        np.testing.assert_allclose(actual,original[:,order],atol=1e-12)
        _,cache=sage.forward(p,self.x,ops)
        for _,_,h,norm,_,_ in cache:
            np.testing.assert_allclose(np.linalg.norm(h,axis=-1)[norm[...,0]>1e-8],1,atol=1e-12)
        zero,_,_=sage.normalize(np.zeros((1,1,3)),1e-8)
        np.testing.assert_equal(zero,0)
        tiny,_,_=sage.normalize(np.array([[[1e-10,0,0]]]),1e-8)
        np.testing.assert_allclose(tiny,[[[.01,0,0]]])


if __name__=='__main__':unittest.main()
