"""Behavior checks for the new estimation chain; no frozen-suite rerun."""
from pathlib import Path
import json
import unittest
import numpy as np
import pose_estimation_lab as p


class EstimationChecks(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((Path(__file__).parent/'inputs/pose-estimation.json').read_text())
        c=self.config
        self.points=np.asarray(c['points_left_m'])
        self.r=p.geometry.yaw(c['yaw_rad'])
        self.c=np.asarray(c['center_right_in_left_m'])
        self.k=(c['f_left_px'],c['c_left_px'],c['f_right_px'],c['c_right_px'])
        self.left,self.right=p.geometry.pair_project(self.points,self.r,self.c,*self.k)

    def test_exactly_eight_pairs_and_four_poses(self):
        e,info=p.estimate_essential(self.left[:8],self.right[:8],*self.k)
        true=p.geometry.skew(-self.r@self.c/np.linalg.norm(self.c))@self.r
        self.assertLess(min(np.linalg.norm(e-true),np.linalg.norm(e+true)),1e-9)
        np.testing.assert_allclose(info['E_singular_values'],[1,1,0],atol=1e-12,rtol=0)
        for rotation,t in p.decompose(e):
            np.testing.assert_allclose(rotation.T@rotation,np.eye(3),atol=1e-12,rtol=0)
            self.assertAlmostEqual(np.linalg.det(rotation),1,places=12)
            self.assertAlmostEqual(np.linalg.norm(t),1,places=12)
            candidate=p.geometry.skew(t)@rotation
            self.assertLess(min(np.linalg.norm(candidate-e),np.linalg.norm(candidate+e)),1e-10)
        pose=p.choose_pose(e,self.left,self.right,*self.k)
        np.testing.assert_allclose(pose['R_RL'],self.r,atol=1e-9,rtol=0)
        np.testing.assert_allclose(pose['C_baseline_units'],self.c/np.linalg.norm(self.c),atol=1e-9,rtol=0)
        np.testing.assert_allclose(pose['points_baseline_units'],self.points/np.linalg.norm(self.c),atol=1e-8,rtol=0)

    def test_constraint_projection_and_sampson_gradient(self):
        projected,_=p.project_essential(np.diag([3.,1.,.5]))
        np.testing.assert_allclose(projected,np.diag([1.,1.,0.]),atol=1e-12,rtol=0)
        e,_=p.estimate_essential(self.left,self.right,*self.k)
        noisy=self.right+np.array([.03,-.02])
        base=p.sampson_px(self.left,noisy,e,*self.k)
        for scale in [-7.,1e-100,1e100]:
            np.testing.assert_allclose(p.sampson_px(self.left,noisy,e*scale,*self.k),base,atol=1e-10,rtol=0)
        f=p.fundamental(e,*self.k)
        obs=np.r_[self.left[0],noisy[0]]
        def constraint(z):return np.r_[z[2:],1.]@f@np.r_[z[:2],1.]
        h=1e-3; gradient=[]
        for i in range(4):
            step=np.eye(4)[i]*h
            gradient.append((constraint(obs+step)-constraint(obs-step))/(2*h))
        oracle=abs(constraint(obs))/np.linalg.norm(gradient)
        self.assertAlmostEqual(base[0],oracle,places=8)

    def test_robust_finite_protocol_and_truth_not_solver_input(self):
        c=self.config
        observed=self.right[np.asarray(c['right_source_indices'])]+np.asarray(c['right_noise_px'])
        e,mask,info=p.robust_essential(self.left,observed,*self.k,17,256,.75)
        truth=np.asarray(c['right_source_indices'])==np.arange(len(self.points))
        np.testing.assert_array_equal(mask,truth)
        self.assertEqual(len(info['trace']),256)
        pose=p.choose_pose(e,self.left[mask],observed[mask],*self.k)
        self.assertEqual(pose['positive_count'],18)
        # Conservative finite-scene behavior limits, separate from oracle tolerance.
        evaluation=p.evaluate(e,pose,self.r,self.c,self.points,np.flatnonzero(mask))
        self.assertLess(evaluation['rotation_error_rad'],.01)
        self.assertLess(evaluation['translation_direction_error_rad'],.05)
        self.assertTrue(all(len(set(t['sample']))==8 for t in info['trace']))
        # A valid, finite search can fail; not every rejection is malformed input.
        with self.assertRaisesRegex(ValueError,'no consensus of eight'):
            p.robust_essential(self.left,observed,*self.k,17,1,.75)

    def test_invalid_and_degenerate_inputs(self):
        plane=self.points.copy(); plane[:,2]=3
        pl,pr=p.geometry.pair_project(plane,self.r,self.c,*self.k)
        pure_l,pure_r=p.geometry.pair_project(self.points,self.r,np.zeros(3),*self.k)
        calls=[
          lambda:p.estimate_essential(self.left[:7],self.right[:7],*self.k),
          lambda:p.estimate_essential(self.left,self.right[:8],*self.k),
          lambda:p.estimate_essential(np.full((8,2),np.nan),self.right[:8],*self.k),
          lambda:p.estimate_essential(np.zeros((8,2)),np.zeros((8,2)),*self.k),
          lambda:p.estimate_essential(pl,pr,*self.k),
          lambda:p.estimate_essential(pure_l,pure_r,*self.k),
          lambda:p.project_essential(np.zeros((3,3))),
          lambda:p.sampson_px(self.left,self.right,np.zeros((3,3)),*self.k),
          lambda:p.robust_essential(self.left,self.right,*self.k,17,0,.75),
          lambda:p.robust_essential(self.left,self.right,*self.k,True,5,.75),
          lambda:p.robust_essential(self.left,self.right,*self.k,17,5,0),
        ]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):call()


if __name__=='__main__':unittest.main()
