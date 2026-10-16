"""New two-view behavior only; the frozen stereo suite is not rerun here."""
import unittest
import numpy as np
import multiview_lab as m


class MultiviewChecks(unittest.TestCase):
    def setUp(self):
        self.r=m.yaw(.12)
        self.c=np.array([.2,.02,.01])
        self.p=np.array([[.3,.1,2.],[-.25,.15,1.5],[.5,-.2,3.],[.1,.05,5.]])
        self.k=(800.,[320.,240.],800.,[320.,240.])

    def test_pose_epipolar_and_clean_reconstruction(self):
        l,r=m.pair_project(self.p,self.r,self.c,*self.k)
        out=m.triangulate(l,r,self.r,self.c,*self.k)
        np.testing.assert_allclose(out['points_left_m'],self.p,atol=1e-10,rtol=0)
        e,f=m.epipolar(self.r,self.c,*self.k)
        t=-self.r@self.c
        for point in self.p:
            right=self.r@(point-self.c)
            self.assertLess(abs((right/right[2])@e@(point/point[2])),1e-12)
        np.testing.assert_allclose(np.linalg.svd(e,compute_uv=False),
                                   [np.linalg.norm(t),np.linalg.norm(t),0],atol=1e-12,rtol=0)
        self.assertLess(max(m.right_line_distance(l,r,f)),1e-9)
        np.testing.assert_allclose(m.right_line_distance(l,r+[.5,-.25],f),
                                   m.right_line_distance(l,r+[.5,-.25],-7*f),atol=1e-10,rtol=0)

    def test_noise_matches_independent_closest_line_formula(self):
        # Alternative 2x2 ray-parameter solve, not the production 6x3 SVD.
        l,r=m.pair_project(self.p,self.r,self.c,*self.k)
        r+=np.array([.5,-.25])
        out=m.triangulate(l,r,self.r,self.c,*self.k)
        a=m.normalized(l,*self.k[:2]); b=m.normalized(r,*self.k[2:])@self.r
        a/=np.linalg.norm(a,axis=1)[:,None]; b/=np.linalg.norm(b,axis=1)[:,None]
        expected=[]
        for ai,bi in zip(a,b):
            dot=ai@bi
            lam,mu=np.linalg.solve([[1.,-dot],[dot,-1.]], [ai@self.c,bi@self.c])
            expected.append((lam*ai+self.c+mu*bi)/2)
        np.testing.assert_allclose(out['points_left_m'],expected,atol=1e-8,rtol=0)
        self.assertGreater(min(out['ray_gap_m']),0)
        self.assertGreater(max(np.linalg.norm(np.asarray(out['points_left_m'])-self.p,axis=1)),.07)

    def test_changed_intrinsics_scale_and_wrong_pair(self):
        k=(1100.,[300.,200.],950.,[350.,250.])
        l,r=m.pair_project(self.p,self.r,self.c,*k)
        np.testing.assert_allclose(m.triangulate(l,r,self.r,self.c,*k)['points_left_m'],self.p,atol=1e-10,rtol=0)
        l3,r3=m.pair_project(self.p*3,self.r,self.c*3,*k)
        np.testing.assert_allclose([l3,r3],[l,r],atol=1e-10,rtol=0)
        fake=.6*self.p[:1]; other=self.c+1.7*(fake-self.c)
        left,_=m.pair_project(self.p[:1],self.r,self.c,*k)
        _,right=m.pair_project(other,self.r,self.c,*k)
        out=m.triangulate(left,right,self.r,self.c,*k)
        np.testing.assert_allclose(out['points_left_m'],fake,atol=1e-10,rtol=0)
        self.assertLess(max(out['reprojection_right_px']),1e-9)

    def test_degenerate_invalid_and_behind(self):
        l,r=m.pair_project(self.p,self.r,self.c,*self.k)
        behind=-self.p[:1]
        br=(behind-self.c)@self.r.T
        blpix=800*behind[:,:2]/behind[:,2:3]+[320,240]
        brpix=800*br[:,:2]/br[:,2:3]+[320,240]
        _,pure=m.pair_project(self.p,self.r,np.zeros(3),*self.k)
        _,tiny=m.pair_project(self.p,self.r,self.c*1e-9,*self.k)
        calls=[
            lambda:m.pose(np.diag([-1,1,1]),self.c),
            lambda:m.pose(np.eye(2),self.c),
            lambda:m.pose(self.r,[0,0,float('nan')]),
            lambda:m.yaw(float('inf')),
            lambda:m.triangulate(l,pure,self.r,np.zeros(3),*self.k),
            lambda:m.triangulate(l,tiny,self.r,self.c*1e-9,*self.k),
            lambda:m.triangulate(l,r[:1],self.r,self.c,*self.k),
            lambda:m.triangulate(blpix,brpix,self.r,self.c,*self.k),
            lambda:m.normalized([[0,float('nan')]],800,[0,0]),
            lambda:m.right_line_distance(l,r,np.zeros((3,3))),
            lambda:m.right_line_distance(l,r,[[0,0,0],[0,0,0],[1,1,1]]),
        ]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):call()


if __name__=='__main__':
    unittest.main()
