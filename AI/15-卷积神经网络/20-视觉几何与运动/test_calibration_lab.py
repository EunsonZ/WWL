"""New calibration behaviors; old stereo/two-view/pose suites stay frozen."""
from pathlib import Path
import json
import unittest
import numpy as np
import calibration_lab as c


class CalibrationChecks(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((Path(__file__).parent/'inputs/calibration-observations.json').read_text())
        self.spec=self.data['synthetic_spec']; self.q=np.asarray(self.data['board_points_m'])

    def test_linear_multiview_and_spd_sign(self):
        f,center,poses,info=c.initialize(self.q,self.data['undistorted_px'])
        expected=np.array([[800.,0,320.],[0,800.,240.],[0,0,1.]])
        np.testing.assert_allclose(info['general_K'],expected,atol=1e-7,rtol=0)
        # Independent scalar Appendix-B extraction is performed by the reviewer;
        # this check also covers signed B and nonsquare/skew input support.
        k=np.array([[810.,7.,315.],[0,790.,245.],[0,0,1.]])
        inv=np.linalg.inv(k); b=inv.T@inv
        np.testing.assert_allclose(c.intrinsic_from_metric(-5*b)[0],k,atol=1e-9,rtol=0)
        for (rv,t),true_r,true_t in zip(poses,self.spec['training_rotvec_rad'],self.spec['training_translation_m']):
            np.testing.assert_allclose(c.Rotation.from_rotvec(rv).as_matrix(),c.Rotation.from_rotvec(true_r).as_matrix(),atol=1e-9,rtol=0)
            np.testing.assert_allclose(t,true_t,atol=1e-9,rtol=0)

    def test_joint_clean_truth_and_objective(self):
        fit=c.calibrate(self.q,self.data['radial_clean_px'])
        self.assertLess(abs(fit['f_px']-800),1e-7)
        np.testing.assert_allclose(fit['principal_px'],[320,240],atol=1e-7,rtol=0)
        self.assertLess(abs(fit['k1']+.12),1e-8)
        self.assertLess(fit['max_point_error_px'],1e-7)
        residual=np.asarray(fit['residual_px'])
        self.assertAlmostEqual(fit['rms_point_error_px'],np.sqrt(np.mean(np.sum(residual**2,axis=2))),places=12)

    def test_radial_inverse_domain_and_forward_ideal(self):
        for observed,expected in zip(self.data['radial_clean_px'],self.data['undistorted_px']):
            np.testing.assert_allclose(c.undistort(observed,800,[320,240],-.12,.75),expected,atol=1e-8,rtol=0)
        np.testing.assert_allclose(c.undistort([[320,240]],800,[320,240],-.12,.75),[[320,240]],atol=1e-12,rtol=0)
        with self.assertRaises(ValueError):c.undistort([[320,240]],800,[320,240],-1.,.75)
        with self.assertRaises(ValueError):c.undistort([[1400,240]],800,[320,240],-.12,.75)

    def test_common_corner_bias_and_board_length_gauge(self):
        spec=self.spec; bias=np.array([1.5,-.75])
        for rv,t in zip(spec['training_rotvec_rad'],spec['training_translation_m']):
            original=c.radial_project(self.q,rv,t,800,[320,240],-.12)
            shifted=c.radial_project(self.q,rv,t,800,np.array([320,240])+bias,-.12)
            np.testing.assert_allclose(shifted,original+bias,atol=1e-10,rtol=0)
            scaled=c.radial_project(self.q*1.7,rv,np.asarray(t)*1.7,800,[320,240],-.12)
            np.testing.assert_allclose(scaled,original,atol=1e-10,rtol=0)

    def test_invalid_targets_metrics_and_degenerate_views(self):
        frontal=[c.radial_project(self.q,[0,0,0],[i*.01,0,.6+i*.05],800,[320,240],0) for i in range(5)]
        calls=[lambda:c.board_points(1,5,.04),lambda:c.board_points(7,5,0),
          lambda:c.board([[0,0,0],[1,0,0],[2,0,0],[3,0,0]]),
          lambda:c.board(self.q+[0,0,.1]),lambda:c.intrinsic_from_metric(np.diag([1.,1.,-1.])),
          lambda:c.intrinsic_from_metric(np.zeros((3,3))),
          lambda:c.intrinsic_from_metric([[1,2,0],[0,1,0],[0,0,1]]),
          lambda:c.initialize(self.q,frontal),lambda:c.initialize(self.q,self.data['undistorted_px'][:2]),
          lambda:c.homography(self.q,np.column_stack((np.arange(len(self.q)),np.zeros(len(self.q))))),
          lambda:c.homography(self.q,np.zeros((3,2)))]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):call()


if __name__=='__main__':unittest.main()
