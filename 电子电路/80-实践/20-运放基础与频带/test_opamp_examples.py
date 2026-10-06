import math
import unittest
import opamp_examples as m

class OpampTests(unittest.TestCase):
    def kcl(self,plus,inputs,resistors,rf,a0=1e5):
        import numpy as np
        # Unknown [minus,out]; original KCL + finite controlled source, not gain formula.
        g=sum(1/r for r in resistors)+1/rf
        matrix=np.array([[g,-1/rf],[a0,1.]])
        rhs=np.array([sum(v/r for v,r in zip(inputs,resistors)),a0*plus])
        return np.linalg.solve(matrix,rhs)
    def test_four_DC_topologies_independent_KCL(self):
        vm,vo=self.kcl(0,[.02],[1e4],9e4);self.assertAlmostEqual(vo,m.closed_inv().real*.02,places=14)
        self.assertAlmostEqual((.02-vm)/1e4,(vm-vo)/9e4,places=14)
        vm,vo=self.kcl(.02,[0],[1e4],9e4);self.assertAlmostEqual(vo,m.closed_noninv().real*.02,places=14)
        vm,vo=self.kcl(0,[.02,-.01],[1e4,2e4],9e4);self.assertAlmostEqual(vo,m.summer([.02,-.01],[1e4,2e4]),places=14)
        vp=.21*9e4/(1e4+9e4);vm,vo=self.kcl(vp,[.2],[1e4],9e4);self.assertAlmostEqual(vo,m.difference(.2,.21),places=14)
    def test_ratio_mismatch_common_mode(self):
        self.assertAlmostEqual(m.difference(2,2),0)
        vp=2*90900/(10000+90900);_,out=self.kcl(vp,[2],[10000],90000)
        self.assertAlmostEqual(m.difference(2,2,r4=90900),out,places=13)
        self.assertAlmostEqual(out,.01783766122892488,places=12)
    def test_single_pole_bandwidth_and_gain(self):
        n=10.;a0=1e5;fp=10.;fc=fp*(1+a0/n)
        self.assertAlmostEqual(abs(m.closed_noninv(f=fc)),m.closed_noninv().real/math.sqrt(2))
        self.assertAlmostEqual(m.closed_noninv(a0=1e12).real,10,places=8)
        self.assertAlmostEqual(m.closed_inv(a0=1e12).real,-9,places=8)
        self.assertAlmostEqual(m.closed_noninv().real/(-m.closed_inv().real),10/9,places=14)
    def test_reactive_original_KCL(self):
        import numpy as np
        for f in (0,1,100,10000,1000000):
            s=2j*math.pi*f;a=1e5/(1+s/(2*math.pi*10))
            for fn,yin,yf in ((m.integrate_transfer,1/1e4,1/1e6+s*1e-7),(m.differentiate_transfer,s*1e-7/(1+s*1e3*1e-7),1/1e4+s*1e-9)):
                vo=np.linalg.solve(np.array([[yin+yf,-yf],[a,1]],dtype=complex),np.array([yin,0]))[1]
                self.assertAlmostEqual(abs(vo-fn(f)),0,places=11)
    def test_states_and_derivative_limits(self):
        self.assertEqual(m.integrator_state(0),.2);self.assertAlmostEqual(m.integrator_state(4.2),-4)
        self.assertAlmostEqual(m.integrator_state(.1,rf=1e6),.3/math.e-.1)
        self.assertAlmostEqual(m.integrate_transfer(0).real,-100/(1+101/1e5))
        self.assertEqual(m.differentiate_transfer(0),0j)
        self.assertAlmostEqual(m.derivative_peak(.01,100),.002*math.pi)
        self.assertAlmostEqual(m.differentiate_transfer(1e-4)/(-2j*math.pi*1e-4*.001),1,places=4)
    def test_documented_model_poles(self):
        import numpy as np
        wp=2*math.pi*10;a0=1e5;ti=1e3*1e-7;tf=1e4*1e-9;td=1e4*1e-7
        diff=[ti*tf/(wp*a0),ti*tf+(ti*tf+(ti+tf+td)/wp)/a0,ti+tf+(ti+tf+td+1/wp)/a0,1+1/a0]
        integ=[1e-7/wp,1e-7*(1+a0)+(1e-4+1e-6)/wp,1e-4+(1+a0)*1e-6]
        self.assertTrue(all(z.real<0 for z in np.roots(diff)));self.assertTrue(all(z.real<0 for z in np.roots(integ)))
    def test_invalid_types_and_extremes(self):
        import numpy as np
        for x in (np.array([1+0j,2+3j]),np.array([1],dtype=object),np.array(1.0)):
            with self.assertRaises(ValueError):m.integrate_transfer(x)
        for x in (True,1+0j,'1',[1],None,float('nan'),float('inf'),1e308,-1):
            with self.assertRaises(ValueError):m.integrate_transfer(x)
        for call in (lambda:m.closed_inv(ri=0),lambda:m.closed_noninv(rf=1e-300),lambda:m.derivative_peak(1,1e308),lambda:m.integrator_state(1,cf=0),lambda:m.summer([1],[1,2]),lambda:m.summer([1]*9,[1]*9),lambda:m.difference(1,2,r3=-1)):
            with self.assertRaises(ValueError):call()
    def test_finite_computational_boundary(self):
        for f in (0,1e-9,1e12):
            for fn in (m.integrate_transfer,m.differentiate_transfer,m.closed_inv,m.closed_noninv):
                z=fn(f=f);self.assertTrue(math.isfinite(z.real) and math.isfinite(z.imag))

if __name__=='__main__':unittest.main()
