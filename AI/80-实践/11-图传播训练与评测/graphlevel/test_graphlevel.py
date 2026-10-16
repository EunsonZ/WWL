"""Author checks; independent review must recompute graph identity and predictions."""
import copy
import itertools
import json
import os
from pathlib import Path
import unittest
import numpy as np
import graphlevel as g


class GraphLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads(Path(__file__).with_name('protocol.json').read_text())
        cls.core=g.load_core(Path(os.environ.get('WWL_GRAPH_PARENT',Path(__file__).resolve().parent.parent)))

    def graph(self,n=5):
        a=np.zeros((n,n))
        for i in range(n-1):a[i,i+1]=a[i+1,i]=1
        x=np.linspace(-.37,1.13,n)[:,None]
        return {'A':a.tolist(),'X':x.tolist()}

    def test_exact_canonical_classes_and_marker_independence(self):
        n=4;edges=list(itertools.combinations(range(n),2));mapping={};reverse={}
        for code in range(1<<len(edges)):
            a=np.zeros((n,n),int)
            for bit,(i,j)in enumerate(edges):a[i,j]=a[j,i]=(code>>bit)&1
            naive=min(''.join(str(a[p[i],p[j]])for i in range(n)for j in range(i+1,n))for p in itertools.permutations(range(n)))
            key=g.canonical(a);mapping.setdefault(naive,key);reverse.setdefault(key,naive)
            self.assertEqual(mapping[naive],key);self.assertEqual(reverse[key],naive)
        self.assertEqual(len(mapping),11)  # all 11 unlabeled simple graphs on 4 vertices.
        self.assertRaises(ValueError,g.canonical,np.zeros((8,8)),10000)

    def test_fixed_witness_all_marker_pairs(self):
        a=np.asarray(self.graph()['A'])
        for i,j in itertools.combinations(range(len(a)),2):
            x=np.zeros((len(a),1));x[[i,j]]=1
            fixed=g.fixed_features(a,x,'fixed',10)
            self.assertEqual(fixed[0],a[i,j])
            q=a@x;self.assertEqual(float(np.sum(x*q)),2*a[i,j])
            # Self-loop variant changes the task-specific encoder contract.
            changed=g.fixed_features(a+np.eye(len(a)),x,'fixed',10)[0]
            self.assertNotEqual(changed,fixed[0])

    def test_all_parameter_gradients_and_readout_permutation(self):
        graphs=[self.graph(5),self.graph(4)];y=np.array([1,0])
        for model in self.protocol['models']:
            if model=='bag':p={'head':np.array([.2,-.3,.1,.05])}
            elif model=='fixed':p={'head':np.array([.2,-.1])}
            else:p=g.initialize(self.protocol,17)
            _,gradient=g.objective(p,graphs,y,model,self.protocol,self.core)
            for key in p:
                for idx in np.ndindex(p[key].shape):
                    plus,minus=copy.deepcopy(p),copy.deepcopy(p);plus[key][idx]+=1e-6;minus[key][idx]-=1e-6
                    fd=(g.objective(plus,graphs,y,model,self.protocol,self.core)[0]-g.objective(minus,graphs,y,model,self.protocol,self.core)[0])/2e-6
                    self.assertAlmostEqual(fd,gradient[key][idx],places=7,msg=(model,key,idx))
            original=g.forward(p,graphs,model,self.protocol,self.core)[0]
            moved=[]
            for row in graphs:
                a=np.asarray(row['A']);x=np.asarray(row['X']);order=list(reversed(range(len(a))))
                moved.append({'A':a[order][:,order].tolist(),'X':x[order].tolist()})
            np.testing.assert_allclose(g.forward(p,moved,model,self.protocol,self.core)[0],original,atol=1e-12)

    def test_pool_losses_ties_and_projection(self):
        one=np.array([[1.,3.],[2.,2.]]);twice=np.vstack((one,one))
        np.testing.assert_equal(g.pool(twice,'mean',10),g.pool(one,'mean',10))
        np.testing.assert_equal(g.pool(twice,'max',10),g.pool(one,'max',10))
        np.testing.assert_equal(g.pool(twice,'sum',10),2*g.pool(one,'sum',10))
        h=np.array([[1.,2.],[1.,0.],[0.,2.]])
        np.testing.assert_equal(g.pool_backward(h,np.ones(2),'max',10),[[.5,.5],[.5,0],[0,.5]])
        self.assertAlmostEqual(np.linalg.norm(g.project(np.array([3.,4.]),4)),4)

    def test_fixed_solver_certificate(self):
        rows=[]
        for i,j in [(0,1),(0,3),(1,2),(1,3)]:
            a=np.asarray(self.graph(4)['A']);x=np.zeros((4,1));x[[i,j]]=1
            rows.append({'A':a.tolist(),'X':x.tolist(),'y':int(a[i,j])})
        for model in('bag','fixed'):
            p,certificate=g.solve_fixed(self.core,rows,model,self.protocol)
            self.assertLessEqual(np.linalg.norm(p['head']),4+1e-12)
            self.assertLessEqual(certificate['convex_gap_upper_bound'],1e-7)


if __name__=='__main__':unittest.main()
