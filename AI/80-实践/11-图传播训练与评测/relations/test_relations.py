"""Author behavioral checks; non-author reference implementations remain separate."""
import copy
import json
import os
from pathlib import Path
import unittest
import numpy as np
import relations as r


class RelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads(Path(__file__).with_name('protocol.json').read_text());cls.data=r.generate(cls.protocol)
        cls.core=r.load_core(Path(os.environ.get('WWL_GRAPH_PARENT',Path(__file__).resolve().parent.parent)))

    def test_type_direction_multiplicity_and_isolate(self):
        public=copy.deepcopy(self.data['public']);public['message_edges']=[[8,'at_inv',0],[8,'at_inv',0],[9,'at_inv',0]]
        counts,b=r.relation_matrices(public);self.assertEqual(counts['at_inv'][0,8],2)
        x=np.asarray(public['X']);w={'at':np.zeros((3,3)),'at_inv':np.eye(3)}
        h=r.encode(x,b,w,np.zeros((3,3)))
        np.testing.assert_allclose(h[0],(2*x[8]+x[9])/3);np.testing.assert_array_equal(h[1],np.zeros(3))
        public['message_edges']=[[0,'at_inv',8]];self.assertRaises(ValueError,r.relation_matrices,public)
        public['message_edges']=[[0,'next',1]];self.assertRaises(ValueError,r.relation_matrices,public)

    def test_encoder_vjp_all_coordinates(self):
        x=np.array([[.1,.4],[.8,-.2],[.5,.7]]);b={'r':np.array([[0,.5,.5],[1,0,0],[0,0,0.]])}
        root=np.array([[.3,-.1],[.2,.6]]);weights={'r':np.array([[.5,.2],[-.4,.7]])};up=np.array([[.6,-.3],[-.2,.5],[.1,.8]])
        grads,dx=r.encode_backward(x,b,weights,root,up)
        for name,value in [('root',root),('r',weights['r']),('x',x)]:
            expected=dx if name=='x'else grads[name]
            for idx in np.ndindex(value.shape):
                value[idx]+=1e-6;plus=float(np.sum(r.encode(x,b,weights,root)*up));value[idx]-=2e-6;minus=float(np.sum(r.encode(x,b,weights,root)*up));value[idx]+=1e-6
                self.assertAlmostEqual((plus-minus)/2e-6,expected[idx],places=8)

    def test_decoder_gradients_symmetry_and_visible_embeddings(self):
        public=self.data['public'];h=r.fixed_embeddings(public,'bilinear');theta=2*np.pi*np.arange(8)/8
        np.testing.assert_allclose(h[:8],np.column_stack((np.cos(theta),np.sin(theta),np.ones(8))),atol=1e-15)
        rows=r.query_rows(public,self.data['train']);rng=np.random.default_rng(2)
        for model in self.protocol['models']:
            h=r.fixed_embeddings(public,model);p={'decoder':rng.normal(0,.3,(3,)if model=='distmult'else(3,3))}
            _,grad=r.objective(self.core,p,h,rows,model,.01)
            for idx in np.ndindex(p['decoder'].shape):
                p['decoder'][idx]+=1e-6;plus=r.objective(self.core,p,h,rows,model,.01)[0];p['decoder'][idx]-=2e-6;minus=r.objective(self.core,p,h,rows,model,.01)[0];p['decoder'][idx]+=1e-6
                self.assertAlmostEqual((plus-minus)/2e-6,grad['decoder'][idx],places=8)
        pair=[(0,1,1),(1,0,0)];p={'decoder':np.array([.2,-.4,.3])};s=r.scores(p,r.fixed_embeddings(public,'distmult'),pair,'distmult');self.assertAlmostEqual(s[0],s[1])

    def test_types_permutation_and_all_known_target_barrier(self):
        public=self.data['public'];h=r.fixed_embeddings(public,'bilinear');rng=np.random.default_rng(9)
        order=np.r_[rng.permutation(8),8+rng.permutation(8)];inverse=np.argsort(order);moved=copy.deepcopy(public)
        moved['entities']=[dict(public['entities'][old],id=new)for new,old in enumerate(order)];moved['X']=np.asarray(public['X'])[order].tolist()
        moved['message_edges']=[[int(inverse[s]),rel,int(inverse[t])]for s,rel,t in public['message_edges']];moved['candidate_entities']=[int(inverse[i])for i in public['candidate_entities']]
        np.testing.assert_allclose(r.fixed_embeddings(moved,'bilinear'),h[order],atol=1e-15)
        support={tuple(edge)for edge in public['message_edges']}
        for split in ('train','val','test'):
            rows=r.query_rows(public,self.data[split]);self.assertEqual(len(rows),7*len(self.data[split]['query_heads']))
            self.assertEqual(sum(row[2]for row in rows),2*len(self.data[split]['query_heads']))
            for head,relation,tail in self.data[split]['positives']:
                self.assertNotIn((head,relation,tail),support);self.assertNotIn((tail,relation+'_inv',head),support)

    def test_rank_ties_and_phase_local_negatives(self):
        equal={i:0. for i in range(7)};self.assertEqual(r.rank(equal,0,set(),1e-10),4)
        self.assertEqual(r.rank(equal,0,{1},1e-10),3.5)
        self.assertEqual(r.rank({0:3.,1:2.,2:2.,3:0.},1,set(),1e-10),2.5)
        before=r.query_rows(self.data['public'],self.data['train']);changed=copy.deepcopy(self.data);changed['test']['positives']=[]
        self.assertEqual(r.query_rows(changed['public'],changed['train']),before)
        for h in self.data['train']['query_heads']:
            self.assertEqual(sum(y==0 for source,_,y in before if source==h),5)

if __name__=='__main__':unittest.main()
