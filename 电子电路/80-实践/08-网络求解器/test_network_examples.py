import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import network_examples as n

class NetworkTests(unittest.TestCase):
    def test_incidence_solution_power_and_orientation(self):
        a,y,v,i,p=n.resistor_network(2,[(1,0),(2,0),(1,2)],[.001,.002,.003],[.001,0])
        np.testing.assert_allclose(v,[5/11,3/11],rtol=1e-13)
        np.testing.assert_allclose(i,np.array([5,6,6])/11000,rtol=1e-13)
        self.assertAlmostEqual(p,5/11000,places=15)
        a2,y2,v2,i2,_=n.resistor_network(2,[(1,0),(2,0),(2,1)],[.001,.002,.003],[.001,0])
        np.testing.assert_allclose(y2,y);np.testing.assert_allclose(v2,v)
        self.assertAlmostEqual(i2[2],-i[2])
    def test_floating_compatible_and_incompatible(self):
        y=.001*np.array([[1,-1],[-1,1]])
        np.testing.assert_allclose(y@np.array([3.,2.]),[.001,-.001])
        self.assertEqual(np.linalg.matrix_rank(y),1)
        self.assertEqual(np.linalg.matrix_rank(np.c_[y,[.001,0]]),2)
        with self.assertRaises(np.linalg.LinAlgError):n.resistor_network(2,[(1,2)],[.001],[.001,-.001])
    def test_mna_supernode_and_vcvs(self):
        _,_,x=n.mna(np.diag([.001,.001]),[0,0],[[1],[-1]],[1])
        np.testing.assert_allclose(x,[.5,-.5,-.0005])
        # independent explicit VCVS system, not self-testing a duplicated helper
        k=np.array([[0,0,1,0],[0,.001,0,1],[1,0,0,0],[-2,1,0,0]])
        sol=np.linalg.solve(k,[0,0,1,0])
        np.testing.assert_allclose(sol,[1,2,0,-.002])
        self.assertEqual(n.constraint_ranks(.001,[5,3]),(2,3))
        self.assertEqual(n.constraint_ranks(.001,[5,5]),(2,2))
    def test_dae_consistency_and_rc_error(self):
        t=np.arange(5)*.00025;vs=1+1000*t
        v,j=n.cv_source(1e-6,t,vs,1.)
        np.testing.assert_allclose(j,-.001,rtol=1e-13)
        with self.assertRaises(ValueError):n.cv_source(1e-6,t,vs,0.)
        _,v1=n.rc_backward(1000,1e-6,1,.00025,4)
        _,v2=n.rc_backward(1000,1e-6,1,.000125,8)
        exact=1-math.exp(-1)
        self.assertAlmostEqual(v1[1],.2)
        self.assertLess(abs(v2[-1]-exact),abs(v1[-1]-exact))
    def test_newton_independent_bracket_jacobian_and_failure(self):
        v,trace=n.diode_newton();vb,width=n.diode_bisection()
        self.assertLess(abs(v-vb),1e-10)
        self.assertLess(abs(n.diode_residual(v)[0]),1e-12)
        self.assertTrue(any(row.get('lambda',1)<1 for row in trace))
        for x in [.2,.5,.55]:
            eps=1e-7;fd=(n.diode_residual(x+eps)[0]-n.diode_residual(x-eps)[0])/(2*eps)
            self.assertAlmostEqual(fd/n.diode_residual(x)[1],1.,places=8)
        with self.assertRaises(ValueError):n.diode_residual(100.)
        with self.assertRaises(ArithmeticError):n.diode_newton(max_iter=1)
        with self.assertRaises(ArithmeticError):n.cubic_step(1/math.sqrt(3))
        self.assertEqual(n.cubic_step(0),0)
        self.assertEqual(n.cubic_step(1),1)
        self.assertAlmostEqual(n.cubic_step(2),16/11)
    def test_ports_load_reconstruction_and_sensitivity(self):
        z,y,h,T=n.z_parameters();curr=np.array([.0004,-.0002]);volt=np.array([1.,.2])
        np.testing.assert_allclose(z@curr,volt)
        np.testing.assert_allclose(y@volt,curr)
        np.testing.assert_allclose(h@np.array([curr[0],volt[1]]),[volt[0],curr[1]])
        np.testing.assert_allclose(T@np.array([volt[1],-curr[1]]),[volt[0],curr[0]])
        self.assertAlmostEqual(np.linalg.det(T),1.)
        expected=[-.4,-8/15,.2,11/15];base=[1000.,2000.,3000.,1000.]
        for idx,e in enumerate(expected):
            plus=base.copy();minus=base.copy();step=base[idx]*1e-5
            plus[idx]+=step;minus[idx]-=step
            derivative=(n.transfer(*plus)-n.transfer(*minus))/(2*step)
            self.assertAlmostEqual(base[idx]/.2*derivative,e,places=8)
        self.assertAlmostEqual(sum(expected),0.)
        gyr=np.array([[0,1000],[-1000,0]])
        self.assertAlmostEqual(float(curr@(gyr@curr)),0.)
    def test_bisection_stagnation_and_budget_failures(self):
        with self.assertRaisesRegex(ArithmeticError,'stagnation'):
            n.diode_bisection(voltage_tol=1e-30)
        with self.assertRaisesRegex(ArithmeticError,'iteration limit'):
            n.diode_bisection(max_iter=1)
        with self.assertRaises(ValueError):n.diode_bisection(max_iter=0)
        v,width=n.diode_bisection()
        self.assertLessEqual(width,1e-12)
        self.assertLess(abs(v-.5553740388592951),1e-11)
    def test_cv_rejects_complex_before_coercion_and_accepts_real(self):
        bad=[np.array([1+0j,2+5j]),np.array([1+0j,2+0j]),
             np.array([1,2+5j],dtype=object),[[1],[2+5j]],
             np.array(['1','2']),[1,float('nan')]]
        for values in bad:
            with self.subTest(values=repr(values)):
                with self.assertRaises(ValueError):n.cv_source(1e-6,[0,1],values,1)
        with self.assertRaises(ValueError):n.cv_source(1e-6,np.array([0+0j,1]),[1,2],1)
        with self.assertRaises(ValueError):n.cv_source(1e-6,[0,1],[1,2],1+0j)
        for values in [[1.,2.],np.array([1,2]),np.array([1.,2.],dtype=object)]:
            v,j=n.cv_source(1e-6,[0.,1.],values,1.)
            np.testing.assert_allclose(v,[1,2]);np.testing.assert_allclose(j,[-1e-6])
    def test_noise_finite_band_integral(self):
        # A numerical quadrature versus an independent analytic antiderivative.
        r,c,k,T=1000.,1e-6,1.380649e-23,300.
        freq=np.geomspace(10.,1e5,20001)
        psd=4*k*T*r/(1+(2*math.pi*freq*r*c)**2)
        numerical=np.trapezoid(psd,freq)
        exact=4*k*T*r/(2*math.pi*r*c)*(math.atan(2*math.pi*1e5*r*c)-math.atan(2*math.pi*10*r*c))
        self.assertLess(abs(numerical/exact-1),1e-7)
        self.assertAlmostEqual(math.sqrt(k*T/c),6.435795988065502e-8)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):n.incidence(2,[(3,0)])
        with self.assertRaises(ValueError):n.resistor_network(1,[(1,0)],[-1],[0])
        with self.assertRaises(ValueError):n.rc_backward(0,1,1,.1,2)
        with self.assertRaises(ValueError):n.cv_source(1,[0,0],[1,1],1)
    def test_cli_missing_output_and_import_no_files(self):
        script=Path(n.__file__).resolve()
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(script)],cwd=d,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(list(Path(d).iterdir()),[])
            cmd=f'import sys;sys.path.insert(0,{str(script.parent)!r});import network_examples'
            result=subprocess.run([sys.executable,'-B','-c',cmd],cwd=d,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(list(Path(d).iterdir()),[])
            gen=script.parent/'generate_figures.py'
            result=subprocess.run([sys.executable,'-B',str(gen)],cwd=d,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(list(Path(d).iterdir()),[])
            cmd=f'import sys;sys.path.insert(0,{str(script.parent)!r});import generate_figures'
            result=subprocess.run([sys.executable,'-B','-c',cmd],cwd=d,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(list(Path(d).iterdir()),[])

if __name__=='__main__':unittest.main()
