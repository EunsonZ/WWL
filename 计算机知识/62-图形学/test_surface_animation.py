"""Behavior boundaries for the new geometry and animation layers only."""
import math,sys,unittest
from pathlib import Path
import numpy as np
if len(sys.argv)>1 and sys.argv[1]=='--shared-dir':sys.path.insert(0,sys.argv.pop(2));sys.argv.pop(1)
import surface_lab as s
import animation_lab as a


def control():return np.array([[[i,j,.5*((i==1)+(j==1))] for j in range(3)] for i in range(3)],float)


class NewLayers(unittest.TestCase):
    def test_spline_support_and_knots(self):
        p=np.array([[0,0,0],[1,2,0],[2,2,0],[3,0,0]],float);k=[0,0,0,1,2,2,2]
        np.testing.assert_allclose(s.spline(p,k,2,1)['point'],[1.5,2,0])
        for t in [0,.5,1,1.5,2]:self.assertAlmostEqual(sum(s.spline(p,k,2,t)['basis']),1)
        changed=p.copy();changed[0,1]+=1;self.assertEqual(s.spline(p,k,2,1.5),s.spline(changed,k,2,1.5))
        for knots,degree,t in [(k[:-1],2,1),([0,0,0,2,1,2,2],2,1),(k,2,3),(k,4,1)]:
            with self.assertRaises(ValueError):s.spline(p,knots,degree,t)

    def test_repeated_knot_kink(self):
        p=[[0,0,0],[1,2,0],[2,2,0],[2,3,0],[4,0,0]];k=[0,0,0,1,1,2,2,2];mid=np.array(s.spline(p,k,2,1)['point']);h=1e-6
        np.testing.assert_allclose(mid,[2,2,0]);np.testing.assert_allclose((mid-s.spline(p,k,2,1-h)['point'])/h,[2,0,0],atol=3e-6);np.testing.assert_allclose((s.spline(p,k,2,1+h)['point']-mid)/h,[0,2,0],atol=5e-6)

    def test_patch_point_derivatives_and_domain(self):
        p,du,dv,n=s.patch(control(),.5,.5);np.testing.assert_allclose(p,[1,1,.5]);np.testing.assert_allclose(du,[2,0,0]);np.testing.assert_allclose(dv,[0,2,0]);np.testing.assert_allclose(n,[0,0,1])
        with self.assertRaises(ValueError):s.patch(np.zeros((3,3,3)),.5,.5)
        with self.assertRaises(ValueError):s.patch(control(),1.1,.5)
        with self.assertRaises(ValueError):s.patch_mesh(control(),1000)

    def test_loop_sync_and_boundary(self):
        mesh=s.patch_mesh(control(),2);before=np.array(mesh['positions']);r=s.loop_step(mesh['positions'],mesh['triangles']);np.testing.assert_equal(mesh['positions'],before)
        np.testing.assert_allclose(r['positions'][0],[.125,.125,.0625]);np.testing.assert_allclose(r['positions'][4],[1,1,.375]);self.assertEqual([r['topology'][x] for x in ('V','E','F','chi','boundary_count')],[25,56,32,1,16])
        with self.assertRaises(ValueError):s.loop_step(mesh['positions'],mesh['triangles']+[mesh['triangles'][0]])

    def test_hierarchy_order_and_nonrigid(self):
        r=a.hierarchy([-1,0],[a.translation(3,0,0),np.diag([2,1,1,1])]);np.testing.assert_allclose(r[1]@[1,0,0,1],[5,0,0,1])
        with self.assertRaises(ValueError):a.hierarchy([1,-1],[np.eye(4),np.eye(4)])

    def test_quaternion_double_cover_and_short_arc(self):
        q=a.axis_angle([0,0,1],math.radians(170));r=a.axis_angle([0,0,1],math.radians(-170));mid=a.rotation(a.slerp(q,r,.5));np.testing.assert_allclose(mid@[1,0,0,1],[-1,0,0,1],atol=1e-12);np.testing.assert_allclose(a.rotation(a.slerp(q,-q,.4)),a.rotation(q))
        with self.assertRaises(ValueError):a.axis_angle([0,0,0],1)
        with self.assertRaises(ValueError):a.slerp(q,r,-.1)

    def test_bind_weights_and_collapse(self):
        p=[[1,1,0]];b=[np.eye(4),a.translation(1,0,0)];np.testing.assert_allclose(a.skin(p,[[.5,.5]],b,b)['positions'],p)
        with self.assertRaises(ValueError):a.skin(p,[[.5,.6]],b,b)
        with self.assertRaises(ValueError):a.skin(p,[[-.1,1.1]],b,b)
        r=a.skin(p,[[.5,.5]],[np.eye(4),a.rotation(a.axis_angle([0,0,1],math.pi))],[np.eye(4),np.eye(4)]);np.testing.assert_allclose(r['positions'],[[0,0,0]],atol=1e-12);self.assertLess(abs(r['blend_linear_determinants'][0]),1e-24)
        with self.assertRaises(ValueError):s.flat_arrays({'positions':[[0,0,0],[0,0,0],[1,0,0]],'triangles':[[0,1,2]]})

    def test_inverse_multiple_and_unreachable(self):
        solutions=a.ik2([1,1],[1,1]);self.assertEqual(len(solutions),2)
        for q in solutions:np.testing.assert_allclose(a.fk2([1,1],q)['end'],[1,1],atol=1e-12)
        self.assertEqual(len(a.ik2([1,1],[2,0])),1)
        for target in [[3,0],[0,0]]:
            with self.assertRaises(ValueError):a.ik2([1,1],target)

    def test_integrator_order_and_work_bound(self):
        e=a.spring(2,.25,1,'explicit');v=a.spring(2,.25,1,'symplectic');self.assertEqual([e[-1]['q'],e[-1]['v']],[1,-1]);self.assertEqual([v[-1]['q'],v[-1]['v']],[.75,-1]);self.assertGreater(e[-1]['energy'],e[0]['energy'])
        for h,steps in [(0,1),(1e100,1),(.1,100000)]:
            with self.assertRaises(ValueError):a.spring(2,h,steps,'explicit')


if __name__=='__main__':unittest.main(verbosity=2)
