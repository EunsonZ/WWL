"""Author regressions for deterministic dense GAT. Independent oracle still required."""
import copy
import json
import math
from pathlib import Path
import unittest
import numpy as np
import gat


class GatTests(unittest.TestCase):
    def setUp(self):
        self.protocol=json.loads(Path(__file__).with_name('protocol.json').read_text())
        self.a=np.zeros((1,5,5))
        for i,j in [(0,1),(1,2),(2,3)]:self.a[0,i,j]=self.a[0,j,i]=1
        self.x=np.array([[[.2,-.3],[-.9,.1],[.7,.6],[1.2,-.2],[.3,.8]]])
        self.y=np.array([[0,0,1,1,1]])

    def test_hand_attention_mask_and_stability(self):
        fixture=gat.fixtures()['path'];alpha=np.asarray(fixture['alpha']);out=np.asarray(fixture['head_output'])[:,0]
        e=math.e;den=1+e+e*e
        np.testing.assert_allclose(alpha,[[e/(1+e),1/(1+e),0],[e/den,1/den,e*e/den],[0,1/(1+e*e),e*e/(1+e*e)]],atol=1e-14)
        np.testing.assert_allclose(out,[e/(1+e),(e+2*e*e)/den,2*e*e/(1+e*e)],atol=1e-14)
        mask=gat.allowed_mask(self.a);scores=np.full(self.a.shape,1e100);scores[mask]=1000
        prob=gat.masked_softmax(scores,mask)
        np.testing.assert_equal(prob[~mask],0);np.testing.assert_allclose(prob.sum(axis=-1),1,atol=1e-15)
        self.assertEqual(prob[0,4,4],1)
        self.assertRaises(ValueError,gat.masked_softmax,np.zeros((1,1,1)),np.zeros((1,1,1),bool))

    def test_all_parameter_gradients(self):
        for variant in ('attention','uniform'):
            p=gat.initialize(2,self.protocol,17);_,gradient=gat.objective(p,self.a,self.x,self.y,variant,self.protocol)
            for key in p:
                for index in np.ndindex(p[key].shape):
                    plus,minus=copy.deepcopy(p),copy.deepcopy(p)
                    plus[key][index]+=1e-6;minus[key][index]-=1e-6
                    fd=(gat.objective(plus,self.a,self.x,self.y,variant,self.protocol)[0]-gat.objective(minus,self.a,self.x,self.y,variant,self.protocol)[0])/2e-6
                    self.assertAlmostEqual(fd,gradient[key][index],places=7,msg=(variant,key,index))

    def test_permutation_heads_and_new_size(self):
        p=gat.initialize(2,self.protocol,17);order=[4,2,0,3,1]
        for variant in ('attention','uniform'):
            logits,cache=gat.forward(p,self.a,self.x,variant,self.protocol)
            moved,_=gat.forward(p,self.a[:,order][:,:,order],self.x[:,order],variant,self.protocol)
            np.testing.assert_allclose(moved,logits[:,order],atol=1e-12)
            self.assertEqual(cache[1][0].shape,(1,5,8))
            # Output is a scalar head average, never concatenate two binary logits.
            self.assertEqual(logits.shape,(1,5))
            final=[gat.head_forward(cache[1][0],p,f'1_{k}',gat.allowed_mask(self.a),variant,.2)[0]for k in range(2)]
            np.testing.assert_allclose(logits,np.mean(final,axis=0)[...,0],atol=1e-14)
        new,_=gat.forward(p,np.zeros((1,17,17)),np.zeros((1,17,2)),'attention',self.protocol)
        self.assertEqual(new.shape,(1,17));self.assertTrue(np.isfinite(new).all())

    def test_static_ranking_and_uniform_control(self):
        ranks=np.asarray(gat.fixtures()['ranking']['alpha_conditioned_on_common_two_keys'])
        self.assertTrue(np.all(ranks[:,1]>ranks[:,0]));self.assertNotEqual(ranks[0,1],ranks[1,1])
        p=gat.initialize(2,self.protocol,17);first=gat.forward(p,self.a,self.x,'uniform',self.protocol)[0]
        for key in p:
            if key[0]in('l','r'):p[key]+=100
        second=gat.forward(p,self.a,self.x,'uniform',self.protocol)[0]
        np.testing.assert_equal(first,second)


if __name__=='__main__':unittest.main()
