"""Independent analytic/matrix tests; finite simulations do not prove stability."""
import unittest
import numpy as np
import robotics_lab as lab

class RoboticsTests(unittest.TestCase):
    def test_se2_inverse_and_noncommutativity(self):
        T = lab.se2([1,2], np.pi/2)
        np.testing.assert_allclose(T @ [.2,0,1], [1,2.2,1], atol=1e-14)
        R = T[:2,:2]
        inverse = np.eye(3); inverse[:2,:2] = R.T; inverse[:2,2] = -R.T @ T[:2,2]
        np.testing.assert_allclose(inverse @ T, np.eye(3), atol=1e-14)
        turn, move = lab.se2([0,0],np.pi/2), lab.se2([1,0],0)
        self.assertFalse(np.allclose(turn @ move, move @ turn))
        np.testing.assert_allclose(R.T@R, np.eye(2), atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(R),1)

    def test_held_acceleration_analytic(self):
        # Compare ten matrix steps to continuous constant-acceleration closed form.
        A,B = lab.model(.1)
        x = np.array([1.,2.,.3,-.2]); original=x.copy(); u=np.array([.4,-.5])
        for _ in range(10): x = A@x+B@u
        np.testing.assert_allclose(x[:2], original[:2]+original[2:]+.5*u, atol=1e-14)
        np.testing.assert_allclose(x[2:], original[2:]+u, atol=1e-14)

    def test_discrete_bayes_enumeration(self):
        prior=np.array([.6,.4]); T=np.array([[.8,.3],[.2,.7]]); L=np.array([.2,.9])
        predicted,post,evidence=lab.discrete_bayes(prior,T,L)
        joint=np.array([[.6*.8*.2,.4*.3*.2],[.6*.2*.9,.4*.7*.9]])
        np.testing.assert_allclose(predicted,[.6,.4])
        np.testing.assert_allclose(post,joint.sum(axis=1)/joint.sum())
        self.assertAlmostEqual(evidence,.48)
        with self.assertRaises(ValueError): lab.discrete_bayes(prior,T,[0,0])

    def test_scalar_gaussian_product(self):
        m=np.array([1.,0.,0.,0.]); P=np.diag([.04,1,1,1]); H=np.array([[1.,0,0,0]])
        post,cov,_,_=lab.update(m,P,[1.3],H,[[.01]])
        # Product of Gaussian densities via addition of precisions.
        expected_var=1/(1/.04+1/.01)
        expected_mean=expected_var*(1/.04+1.3/.01)
        self.assertAlmostEqual(post[0],expected_mean)
        self.assertAlmostEqual(cov[0,0],expected_var)
        self.assertAlmostEqual(post[0],1.24)

    def test_joseph_information_formula_psd(self):
        rng=np.random.default_rng(23)
        for _ in range(30):
            M=rng.normal(size=(4,4)); P=M@M.T+.01*np.eye(4)
            H=rng.normal(size=(2,4)); R=np.diag([.01,.2]); mean=rng.normal(size=4); z=rng.normal(size=2)
            got,C,_,_=lab.update(mean,P,z,H,R)
            # Alternate posterior: information matrix / precision-weighted mean.
            precision=np.linalg.solve(P,np.eye(4))+H.T@np.linalg.solve(R,H)
            expected=np.linalg.solve(precision,np.eye(4))
            expected_m=np.linalg.solve(precision,np.linalg.solve(P,mean)+H.T@np.linalg.solve(R,z))
            np.testing.assert_allclose(C,expected,atol=3e-11,rtol=3e-10)
            np.testing.assert_allclose(got,expected_m,atol=3e-11,rtol=3e-10)
            self.assertGreaterEqual(np.linalg.eigvalsh(C).min(),-1e-12)
            self.assertGreaterEqual(np.linalg.eigvalsh(P-C).min(),-1e-11)
        tiny=np.diag([1e-16,1e-10,1,2])
        _,C,_,_=lab.update(np.zeros(4),tiny,[0,0],np.eye(4)[:2],np.eye(2)*1e-14)
        self.assertGreaterEqual(np.linalg.eigvalsh(C).min(),0)

    def test_observability_and_indistinguishable_states(self):
        Hp,Hv=np.eye(4)[:2],np.eye(4)[2:]
        self.assertEqual(lab.observability_rank(Hp),4)
        self.assertEqual(lab.observability_rank(Hv),2)
        A,_=lab.model(); a=np.zeros(4); b=np.array([8.,-3.,0.,0.])
        for _ in range(20):
            np.testing.assert_allclose(Hv@a,Hv@b); a=A@a; b=A@b
        # Two noiseless positions reconstruct velocity independently.
        x=np.array([1.,2.,.4,-.3]); np.testing.assert_allclose((Hp@A@x-Hp@x)/lab.DT,x[2:])

    def test_reference_endpoints_and_derivatives(self):
        for t,p in zip([0,4,12,16,24],[[0,0],[0,1.5],[4,1.5],[4,0],[4,0]]):
            q,v,a=lab.reference(t); np.testing.assert_allclose(q,p,atol=1e-14)
            np.testing.assert_allclose(v,0,atol=1e-14); np.testing.assert_allclose(a,0,atol=1e-14)
        for t in [1.,6.,14.]:
            h=1e-4; p,v,a=lab.reference(t)
            pm,vm,_=lab.reference(t-h); pp,vp,_=lab.reference(t+h)
            np.testing.assert_allclose((pp-pm)/(2*h),v,atol=1e-8)
            np.testing.assert_allclose((vp-vm)/(2*h),a,atol=1e-8)

    def test_continuous_segment_obstacle(self):
        self.assertAlmostEqual(lab.segment_clearance([0,0],[4,0]),-.6)
        self.assertAlmostEqual(lab.segment_clearance([0,1.5],[4,1.5]),.9)
        self.assertAlmostEqual(lab.segment_clearance([2,.6],[2,.6]),0,places=13)
        self.assertTrue(all(lab.segment_clearance(a,b)>0 for a,b in zip(lab.WAYPOINTS[:-1],lab.WAYPOINTS[1:])))

    def test_pd_jury_and_pid_poles(self):
        for dt,kp,kd in [(.05,2,2),(.2,1,1),(.05,2,50),(.05,-2,2)]:
            A=np.array([[1,dt],[0,1.]])-np.array([[dt**2/2],[dt]])@np.array([[kp,kd]])
            stable=np.max(np.abs(np.linalg.eigvals(A)))<1
            jury=kp>0 and .5*dt*kp<kd<2/dt
            self.assertEqual(stable,jury)
        self.assertLess(np.max(np.abs(np.linalg.eigvals(lab.pid_error_matrix()))),1)
        self.assertGreater(np.max(np.abs(np.linalg.eigvals(lab.pid_error_matrix(1.5)))),1)

    def test_saturation_and_antiwindup(self):
        mean=np.array([-100.,0.,0.,0.]); integral=np.array([5.,0.])
        u,I,raw=lab.pid(mean,integral,0)
        self.assertEqual(u[0],lab.LIMIT); self.assertEqual(I[0],5.)
        self.assertGreater(raw[0],lab.LIMIT)
        # A negative error can unwind an already positive saturated integral.
        _,I,_=lab.pid([1.,0.,0.,0.],[100.,0.],0)
        self.assertLess(I[0],100.)

    def test_closed_loop_impulse_recovery_and_bias(self):
        # Independent performance acceptance for this finite scenario, not universal stability.
        nominal=lab.simulate(noise=False); biased=lab.simulate(noise=False,bias=(.6,0.))
        tail=nominal['t']>=21
        e=nominal['truth'][:,:2]-nominal['reference'][:,:2]
        self.assertGreater(np.max(np.linalg.norm(e[(nominal['t']>=10)&(nominal['t']<=12)],axis=1)),.1)
        self.assertLess(np.max(np.linalg.norm(e[tail],axis=1)),.08)
        self.assertLess(np.max(np.abs(nominal['u'])),lab.LIMIT+1e-12)
        self.assertGreater(np.sqrt(np.mean(np.sum((biased['truth'][tail,:2]-biased['reference'][tail,:2])**2,axis=1))),.5)
        self.assertLess(np.sqrt(np.mean(np.sum((biased['estimate'][tail,:2]-biased['reference'][tail,:2])**2,axis=1))),.08)
        np.testing.assert_allclose(lab.simulate()['truth'],lab.simulate()['truth'])

    def test_invalid_inputs(self):
        for value in [0,-1,np.nan,np.inf,1e308,1e-300]:
            with self.assertRaises(ValueError): lab.model(value)
        for P in [np.diag([-1,1,1,1]),np.eye(3),np.full((4,4),np.nan)]:
            with self.assertRaises(ValueError): lab.predict(np.zeros(4),P,[0,0],np.eye(4))
        with self.assertRaises(ValueError): lab.update(np.zeros(4),np.eye(4),[0],[[1,0,0,0]],[[0]])
        with self.assertRaises(ValueError): lab.update(np.zeros(4),np.eye(4),[],np.empty((0,4)),np.empty((0,0)))
        with self.assertRaises(ValueError): lab.reference(-1)
        with self.assertRaises(ValueError): lab.pid(np.zeros(4),np.zeros(2),0,limit=0)
        with self.assertRaises(ValueError): lab.simulate(dt=1e-10)

if __name__=='__main__': unittest.main()
