"""Focused interface and failure tests for the new pixel/window chain."""
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.spatial.transform import Rotation
import flow_lab as flow
import window_ba_lab as ba

ROOT=Path(__file__).resolve().parent
SPEC=json.loads((ROOT/"inputs/motion-spec.json").read_text())


class MotionChecks(unittest.TestCase):
    def test_bilinear_gradient_and_domain(self):
        y,x=np.mgrid[:20,:24]
        a=.1+.01*x+.02*y+.0001*x*y
        uv=np.array([[4.3,6.7],[11.2,8.1]])
        values,j=flow.sample(a,uv,True)
        np.testing.assert_allclose(values,.1+.01*uv[:,0]+.02*uv[:,1]+.0001*uv[:,0]*uv[:,1],atol=1e-15)
        np.testing.assert_allclose(j,np.column_stack((.01+.0001*uv[:,1],.02+.0001*uv[:,0])),atol=1e-15)
        with self.assertRaises(ValueError): flow.sample(a,[[23.,4.]])
        with self.assertRaises(ValueError): flow.image(np.full((4,4),np.nan))

    def test_aperture_and_model_failures(self):
        result=flow.failures(None,SPEC)
        for name in ("flat","edge","brightness_change","occluded"):
            self.assertFalse(result[name]["accepted"],name)
        wrong=result["periodic_wrong_identity"]
        self.assertTrue(wrong["estimated"]["accepted"])
        self.assertEqual(wrong["estimated"]["fb_error_px"],0)
        self.assertEqual(wrong["identity_error_px"],8)
        with self.assertRaises(ValueError): flow.detect(np.full((40,40),.5))

    def test_exact_local_constraint_and_aperture_null(self):
        j=np.array([[1,2],[1,-1],[1,-2]],float)
        it=np.array([0,-.375,-.5])
        d=np.linalg.lstsq(j,-it,rcond=None)[0]
        np.testing.assert_allclose(d,[.25,-.125],atol=1e-15)
        edge=np.array([[1,0],[2,0],[-1,0]],float)
        np.testing.assert_array_equal(edge@np.array([0,7]),np.zeros(3))

    def test_unique_closure_factors(self):
        uv=np.zeros((5,2,12,2))
        base=ba.graph(uv,SPEC,"none"); closed=ba.graph(uv,SPEC,"true"); wrong=ba.graph(uv,SPEC,"wrong")
        self.assertEqual(len(base),66); self.assertEqual(len(closed),78)
        keys=lambda rows:{(r["time"],r["eye"],r["landmark"]) for r in rows}
        self.assertEqual(len(keys(closed)),78)
        self.assertEqual(len(keys(closed)-keys(base)),12)
        self.assertEqual(keys(closed),keys(wrong))
        self.assertEqual(sum(r["landmark"]!=r["pixel_source_id"] for r in wrong),12)
        with self.assertRaises(ValueError): ba.graph(uv[:2],SPEC)

    def test_full_pose_and_measured_baseline(self):
        points=np.array([[.2,.1,2],[-.1,-.15,1.3]])
        pose=np.array([.03,-.02,.01,-.02,.01,.02])
        r=Rotation.from_rotvec(pose[:3]).as_matrix()
        edges=[{"time":0,"eye":e,"landmark":j} for j in range(2) for e in range(2)]
        pred=ba.predict(pose[None,:],points,edges,SPEC)
        expected=[]
        for j in range(2):
            q=r@points[j]+pose[3:]
            for e in (0,1):
                v=q.copy(); v[0]-=e*.08
                expected.append([160*v[0]/v[2]+96,160*v[1]/v[2]+64])
        np.testing.assert_allclose(pred,expected,atol=1e-12)
        poses=np.vstack((np.zeros(6),pose,pose,pose,pose))
        x=ba.pack(poses,np.tile(points,(6,1)))
        pp,xx=ba.unpack(x)
        np.testing.assert_array_equal(pp,poses); np.testing.assert_array_equal(xx,np.tile(points,(6,1)))
        with self.assertRaises(ValueError): ba.unpack(x[:-1])
        with self.assertRaises(ValueError): ba.predict(pose[None,:],points,edges,SPEC,-.1)

    def test_initialization_and_clean_joint_fit(self):
        invalid=json.loads(json.dumps(SPEC))
        invalid["centers_world_m"][1][2]=.01
        with self.assertRaises(ValueError): flow.scene(invalid)
        _,uv,points=flow.scene(SPEC)
        result=ba.fit(uv,SPEC,"true")
        self.assertLess(result["point_rms_px"],1e-6)
        np.testing.assert_allclose(result["points_world_m"],points,atol=1e-6,rtol=0)
        np.testing.assert_allclose(ba.centers(np.asarray(result["poses_rotvec_t_CW"])),SPEC["centers_world_m"],atol=1e-6,rtol=0)

if __name__=="__main__": unittest.main()
