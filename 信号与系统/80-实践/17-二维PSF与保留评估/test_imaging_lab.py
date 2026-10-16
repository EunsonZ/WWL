import unittest,tempfile
from pathlib import Path
import numpy as np
import imaging_lab as m

H=np.array([[0,1,0],[2,8,1],[0,3,1]],float)/16


class FiniteInverse(unittest.TestCase):
    def test_corner_crop_and_noninverse(self):
        p=np.zeros((8,8));p[0,0]=1;a=m.dense_operator([8,8],H,'zero',[0,1,2]);z=m.acquire(p,H,'zero',[0,1,2]);self.assertEqual(z[0],13/64);self.assertEqual(float(z.sum()),13/64);self.assertEqual((a.T@a@p.ravel())[0],169/4096);self.assertNotEqual((a.T@a@p.ravel())[0],1)
        wrap=m.acquire(p,H,'periodic',[0,1,2]);self.assertEqual(wrap[3],2/64);self.assertEqual(float(wrap.sum()),15/64)

    def test_adjoint_composition(self):
        x=np.arange(64).reshape(8,8)/63;z=np.linspace(-1,1,12);a=m.dense_operator([8,8],H,'zero',[0,1,2]);actual=m.acquire_adjoint(z,[8,8],H,'zero',[0,1,2]);np.testing.assert_allclose(actual.ravel(),a.T@z,atol=1e-14);self.assertAlmostEqual(m.acquire(x,H,'zero',[0,1,2])@z,np.sum(x*actual),places=13)

    def test_fft_boundary_and_normalization(self):
        x=np.arange(64).reshape(8,8)/63
        for boundary in ['zero','periodic']:np.testing.assert_allclose(m.blur(x,H,boundary),m.blur_fft(x,H,boundary),atol=1e-14)
        np.testing.assert_allclose(m.blur(np.ones((8,8)),H,'periodic'),1);self.assertLess(m.blur(np.ones((8,8)),H,'zero')[0,0],1)
        for h in [H*2,H-np.eye(3)]:
            with self.assertRaises(ValueError):m.kernel(h)

    def test_nullspace_and_prior_edges(self):
        a=m.dense_operator([8,8],H,'zero',[0,1,2]);np.testing.assert_array_equal(a[:,-8:],0);d=m.difference([8,8]);self.assertEqual(d.shape,(112,64));np.testing.assert_array_equal(d@np.ones(64),0)
        for row in d:
            idx=np.flatnonzero(row);self.assertEqual(len(idx),2);self.assertIn(idx[1]-idx[0],[1,8])

    def test_quadratic_and_threshold(self):
        np.testing.assert_allclose(m.quadratic([[1,1]],[2],2,'ridge')['x'],[.5,.5]);np.testing.assert_allclose(m.quadratic([[1,1]],[2],0,'tsvd')['x'],[1,1]);np.testing.assert_allclose(m.quadratic(np.diag([1,.01]),[1,.02],.1,'tsvd')['x'],[1,0])

    def test_tv_analytic_and_certificate(self):
        a=np.array([[1,0,0],[0,0,1]]);d=np.array([[-1,1,0],[0,-1,1]]);lam=.1;epsilon=.001;r=m.tv(a,[0,1],d,lam,epsilon);self.assertTrue(r['converged']);expected=[lam/(1+2*epsilon)]*2+[(1-lam)/(1+epsilon)];np.testing.assert_allclose(r['x'],expected,atol=2e-6);self.assertLess(r['gap'],1e-7);self.assertLessEqual(max(abs(x) for x in r['dual_tv']),lam)
        short=m.tv(a,[0,1],d,lam,epsilon,max_iterations=1);self.assertFalse(short['converged']);self.assertEqual(short['history'][-1]['iteration'],1)

    def test_selection_is_prediction_not_latent_oracle(self):
        a=np.eye(2);d=np.array([[-1,1]]);c=[{'method':'ridge','parameter':.1},{'method':'ridge','parameter':1}];r=m.select(a,np.array([1,0]),np.zeros(2),d,c,{});self.assertEqual(r['overall']['parameter'],1)
        # A latent truth equal to y_fit would favor .1 instead; it is not an input.
        self.assertLess(np.linalg.norm(np.array(r['rows'][0]['fit']['x'])-[1,0]),np.linalg.norm(np.array(r['rows'][1]['fit']['x'])-[1,0]))

    def test_budget_and_contract_failures(self):
        with self.assertRaisesRegex(ValueError,'finite_operator_shape'):m.dense_operator([10**8,10**8],H,'zero',[0])
        with self.assertRaises(ValueError):m.acquire(np.zeros((8,8)),H,'zero',[0,0])
        with self.assertRaises(ValueError):m.tv(np.eye(2),[0,1],[[-1,1]],.1,0)
        from run_lab import run
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):run(Path('unused'),Path('unused'),Path('unused'),Path(directory))


if __name__=='__main__':unittest.main(verbosity=2)
