import unittest
import numpy as np
import renderer as r

class RasterTests(unittest.TestCase):
    def test_shared_edge(self):
        a=np.array([[0,0],[4,0],[4,4]],float); b=np.array([[0,0],[4,4],[0,4]],float)
        aa={(x,y) for x,y,_ in r.samples(a,4,4)}; bb={(x,y) for x,y,_ in r.samples(b,4,4)}
        self.assertEqual(aa & bb,set()); self.assertEqual(aa | bb,{(x,y) for x in range(4) for y in range(4)})
        self.assertEqual(len(list(r.samples(np.array([[0,0],[1,1],[2,2]]),4,4))),0)
    def test_interior_oracle(self):
        s=np.array([[.2,.2],[5.8,1.2],[1.1,5.7]]); expected=set()
        for y in range(6):
            for x in range(6):
                uv=np.linalg.solve(np.column_stack([s[1]-s[0],s[2]-s[0]]),np.array([x+.5,y+.5])-s[0])
                if min(uv)>0 and uv.sum()<1: expected.add((x,y))
        self.assertEqual({(x,y) for x,y,_ in r.samples(s,6,6)},expected)
    def test_six_planes(self):
        inside=np.array([0,0,0,1,0,0,0,0,0,1.])
        for axis in range(3):
            for sign in [-1,1]:
                outside=inside.copy(); outside[axis]=2*sign; outside[4]=1
                other=inside.copy(); other[(axis+1)%3]=.5
                poly=r.clip_polygon(np.array([outside,inside,other]))
                self.assertEqual(len(poly),4); self.assertTrue(np.all(poly[:,:4]@r.PLANES.T>=-1e-14))
                self.assertTrue(np.allclose(poly[np.isclose(poly[:,axis],sign),4],.5))
        far=np.array([inside]*3); far[:,0]=2; self.assertEqual(len(r.clip_polygon(far)),0)
    def test_behind_eye(self):
        pos=np.array([[0,0,1],[-.5,-.5,-2],[.5,-.5,-2]])
        clip=(r.perspective()@np.column_stack([pos,np.ones(3)]).T).T
        poly=r.clip_polygon(np.column_stack([clip,np.ones((3,6))]))
        self.assertGreater(len(poly),0); self.assertTrue(np.all(poly[:,3]>=1-1e-14))
        self.assertTrue(np.all(poly[:,:4]@r.PLANES.T>=-1e-14))
    def test_ray_plane_oracle(self):
        pos=np.array([[-1,-1,-2],[2,-2,-4],[0,1,-2]],float)
        image,depth=r.render(pos,np.array([[0,1,2]]),np.eye(3),np.tile([0,0,1],(3,1)),width=8,height=8)
        count=0
        for y in range(8):
            for x in range(8):
                direction=np.array([2*(x+.5)/8-1,1-2*(y+.5)/8,-1])
                t,u,v=np.linalg.solve(np.column_stack([direction,-(pos[1]-pos[0]),-(pos[2]-pos[0])]),pos[0])
                if t>0 and u>1e-10 and v>1e-10 and u+v<1-1e-10:
                    count+=1; self.assertTrue(np.allclose(image[y,x],[1-u-v,u,v],atol=1e-12))
                    self.assertAlmostEqual(depth[y,x],(1.25-2.25/t+1)/2)
        self.assertGreater(count,0)
    def test_perspective(self):
        self.assertTrue(np.allclose(r.interpolate([.5,.5,0],[2,4,2],np.eye(3)),[2/3,1/3,0]))
    def test_occlusion(self):
        p=np.array([[-1,-1,-2],[1,-1,-2],[0,1,-2],[-2,-2,-4],[2,-2,-4],[0,2,-4]])
        c=np.array([[1,0,0]]*3+[[0,1,0]]*3); n=np.tile([0,0,1],(6,1))
        a,z=r.render(p,np.array([[0,1,2],[3,4,5]]),c,n,width=8,height=8)
        b,zz=r.render(p,np.array([[3,4,5],[0,1,2],[0,0,0]]),c,n,width=8,height=8)
        self.assertTrue(np.array_equal(a,b)); self.assertTrue(np.array_equal(z,zz)); self.assertTrue(np.array_equal(a[4,4],[1,0,0]))
    def test_normal(self):
        m=np.diag([2.,1.,1.,1.]); t=np.array([1,1,0.]); n=np.array([1,-1,0.])
        self.assertAlmostEqual((m[:3,:3]@t)@(r.normal_matrix(m)@n),0)
        self.assertEqual((m[:3,:3]@t)@(m[:3,:3]@n),3)
        with self.assertRaises(ValueError): r.normal_matrix(np.diag([0.,1.,1.,1.]))
    def test_invalid(self):
        for args in [(0,9,np.pi/2,1),(1,1,np.pi/2,1),(1,9,np.nan,1),(1,9,np.pi/2,0)]:
            with self.assertRaises(ValueError): r.perspective(*args)
        with self.assertRaises(ValueError): r.unit([0,0,0])
        with self.assertRaises(ValueError): r.clip_polygon([[np.nan]*10]*3)
        with self.assertRaises(ValueError): r.interpolate([.5,.5,0],[0,1,1],np.eye(3))
        p=np.array([[-1,-1,-2],[1,-1,-2],[0,1,-2]]); n=np.tile([0,0,1],(3,1))
        for kwargs in [dict(width=0),dict(height=2.5),dict(model=np.zeros((4,4)))]:
            with self.assertRaises(ValueError): r.render(p,np.array([[0,1,2]]),np.eye(3),n,**kwargs)
        with self.assertRaises(ValueError): r.render(p,np.array([[0,1,3]]),np.eye(3),n)

if __name__=='__main__': unittest.main()
