"""Independent scalar/closed-form 2x2 and 3x3 oracles; never writes outputs."""
import math
import unittest
import warnings
import numpy as np
from state_lab import (model,expm,transition,constant_response,structure,gramian,
                       observability_gramian,rank_report,transfer,markov)

class StateTests(unittest.TestCase):
    def test_diagonal_2x2_input_and_initial_state(self):
        A=np.diag([-1.,1.]);B=[[1],[1]];C=[[1,0]];D=[[.2]]
        for t in [0,.001,.3,1.,6.]:
            x,y=constant_response(A,B,C,D,t,[.3,-.2],[.7])
            expected=[.3*math.exp(-t)+.7*(1-math.exp(-t)),
                      -.2*math.exp(t)+.7*(math.exp(t)-1)]
            np.testing.assert_allclose(x,expected,atol=1e-12)
            self.assertAlmostEqual(y[0],expected[0]+.14,places=12)

    def test_rotation_and_jordan_2x2(self):
        A=np.array([[0,-2],[2,0.]])
        for t in [0,.2,1,3]:
            np.testing.assert_allclose(transition(A,t),[[math.cos(2*t),-math.sin(2*t)],[math.sin(2*t),math.cos(2*t)]],atol=2e-14)
            np.testing.assert_allclose(transition([[-1,2],[0,-1]],t),math.exp(-t)*np.array([[1,2*t],[0,1]]),atol=2e-14)

    def test_nilpotent_3x3_solution_and_gramian(self):
        J=np.array([[0,1,0],[0,0,1],[0,0,0.]])
        B=np.array([[0],[0],[1.]])
        for t in [0,.01,.5,2]:
            expected=np.eye(3)+t*J+t*t/2*(J@J)
            np.testing.assert_allclose(transition(J,t),expected,atol=2e-14)
            x,y=constant_response(J,B,[[1,0,0]],[[0]],t,[1,2,3],[.4])
            want=[1+2*t+1.5*t*t+.4*t**3/6,2+3*t+.4*t*t/2,3+.4*t]
            np.testing.assert_allclose(x,want,atol=2e-14)
            W=[[t**5/20,t**4/8,t**3/6],[t**4/8,t**3/3,t*t/2],[t**3/6,t*t/2,t]]
            np.testing.assert_allclose(gramian(J,B,t),W,atol=2e-14)
        r,o=structure(J,B,[[1,0,0]])
        self.assertEqual(rank_report(r)['rank'],3);self.assertEqual(rank_report(o)['rank'],3)
        np.testing.assert_allclose(np.array(markov(J,B,[[1,0,0]],4)).ravel(),[0,0,1,0])

    def test_diagonal_gramian_scalar_integrals(self):
        A=np.diag([-1.,1.,0.]);B=np.array([[1.,2],[3,-1],[.5,2]])
        for T in [0,.1,1,2]:
            W=gramian(A,B,T)
            for i,ai in enumerate([-1.,1.,0.]):
                for j,aj in enumerate([-1.,1.,0.]):
                    scalar=T if ai+aj==0 else math.expm1((ai+aj)*T)/(ai+aj)
                    expected=sum(B[i,k]*B[j,k] for k in range(2))*scalar
                    self.assertAlmostEqual(W[i,j],expected,places=10)

    def test_transfer_same_and_singular_implementation(self):
        A=np.diag([-1.,1.])
        for s in [0,2,1j,1+2j]:
            a=transfer(A,[[1],[1]],[[1,0]],[[0]],s)[0,0]
            b=transfer(A,[[1],[0]],[[1,1]],[[0]],s)[0,0]
            self.assertAlmostEqual(abs(a-1/(s+1)),0,places=13)
            self.assertAlmostEqual(abs(a-b),0,places=13)
        with self.assertRaises(ValueError):transfer(A,[[1],[1]],[[1,0]],[[0]],1)
        # Reduced scalar transfer at 1 has value .5; full-state resolvent is singular.
        self.assertEqual(transfer([[-1]],[[1]],[[1]],[[0]],1)[0,0],.5)
        self.assertEqual(transfer([[-1e308]],[[1e308]],[[1]],[[0]],1e308)[0,0],.5)

    def test_hidden_vs_initially_visible_uncontrolled(self):
        A=np.diag([-1.,1.])
        x,y=constant_response(A,[[1],[1]],[[1,0]],[[0]],3,[0,0],[1])
        self.assertGreater(x[1],19);self.assertLess(y[0],1)
        _,y0=constant_response(A,[[1],[0]],[[1,1]],[[0]],3,[0,0],[1])
        _,yi=constant_response(A,[[1],[0]],[[1,1]],[[0]],3,[0,1],[0])
        self.assertAlmostEqual(y0[0],1-math.exp(-3));self.assertAlmostEqual(yi[0],math.exp(3))

    def test_cascade_exact_cancellation_and_perturbation(self):
        # K=(s-1+eps)/(s+1), P=1/(s-1); known-model algebra, not a controller run.
        for eps in [0.,.001]:
            A=[[-1,0],[-2+eps,1]]
            for t in [0,.1,1,4]:
                _,y=constant_response(A,[[1],[1]],[[0,1]],[[0]],t,[0,0],[1])
                want=1-math.exp(-t)+eps/2*(math.exp(t)+math.exp(-t)-2)
                self.assertAlmostEqual(y[0],want,places=11)
        _,yi=constant_response([[-1,0],[-2,1]],[[1],[1]],[[0,1]],[[0]],2,[0,.1],[0])
        self.assertAlmostEqual(yi[0],.1*math.exp(2),places=13)

    def test_exact_zero_near_zero_and_coordinates(self):
        A=np.diag([-1.,1.]);B=np.ones((2,1))
        _,o0=structure(A,B,[[1,0]]);_,on=structure(A,B,[[1,1e-12]])
        self.assertEqual(rank_report(o0,rtol=0)['rank'],1)
        self.assertEqual(rank_report(on,rtol=1e-10)['rank'],1)
        self.assertEqual(rank_report(on,rtol=1e-14)['rank'],2)
        S=np.diag([1,1e12]);_,o=structure(A,B,[[1,1]])
        _,os=structure(S@A@np.linalg.inv(S),S@B,np.array([[1,1]])@np.linalg.inv(S))
        self.assertEqual(rank_report(o)['rank'],2);self.assertEqual(rank_report(os)['rank'],1)
        # Exact det(O)=+2 epsilon is nonzero independently of a threshold.
        self.assertNotEqual(2e-12,0)

    def test_similarity_and_gramian_congruence(self):
        A=np.diag([-1.,-2.]);B=np.array([[1.],[2.]]);C=np.array([[1.,1.]]);S=np.array([[1.,1],[0,2.]])
        inv=np.linalg.inv(S);Az=S@A@inv;Bz=S@B;Cz=C@inv
        np.testing.assert_allclose(gramian(Az,Bz,1),S@gramian(A,B,1)@S.T,atol=2e-13)
        np.testing.assert_allclose(observability_gramian(Az,Cz,1),inv.T@observability_gramian(A,C,1)@inv,atol=2e-13)
        for t in [0,.2,1]:
            x,y=constant_response(A,B,C,[[0]],t,[.2,.3],[1])
            z,yz=constant_response(Az,Bz,Cz,[[0]],t,S@np.array([.2,.3]),[1])
            np.testing.assert_allclose(z,S@x,atol=2e-13);np.testing.assert_allclose(yz,y,atol=2e-13)

    def test_window_zero_and_observable_energy(self):
        A=np.diag([-1.,-2.]);C=[[1,1]]
        np.testing.assert_array_equal(observability_gramian(A,C,0),np.zeros((2,2)))
        for T in [.01,.1,1]:
            W=observability_gramian(A,C,T)
            self.assertGreater(np.linalg.eigvalsh(W)[0],0)
        hidden=observability_gramian(np.diag([-1.,1.]),[[1,0]],1)
        np.testing.assert_array_equal(hidden[:,1],[0,0])

    def test_object_complex_scalars_all_ports_rejected_without_warning(self):
        class Complex64Child(np.complex64):
            pass
        class Complex128Child(np.complex128):
            pass
        class ComplexChild(complex):
            pass
        scalar_types=(complex,np.complex64,np.complex128,
                      ComplexChild,Complex64Child,Complex128Child)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            for scalar_type in scalar_types:
                for value in [1+0j,1+2j]:
                    z=scalar_type(value)
                    matrix=np.array([[z]],dtype=object)
                    vector=np.array([z],dtype=object)
                    for slot in range(6):
                        args=[[[0]],[[1]],[[1]],[[0]],1,[0],[1]]
                        args[[0,1,2,3,5,6][slot]]=matrix if slot<4 else vector
                        with self.subTest(type=scalar_type.__name__,value=value,slot=slot):
                            with self.assertRaises(ValueError):constant_response(*args)
                    calls=[lambda:expm(matrix),lambda:transition(matrix,1),
                           lambda:structure([[0]],matrix,[[1]]),
                           lambda:structure([[0]],[[1]],matrix),
                           lambda:gramian(matrix,[[1]],1),
                           lambda:gramian([[0]],matrix,1),
                           lambda:observability_gramian([[0]],matrix,1),
                           lambda:transfer([[0]],[[1]],matrix,[[0]],1),
                           lambda:markov([[0]],matrix,[[1]],2),
                           lambda:rank_report(matrix)]
                    for call in calls:
                        with self.assertRaises(ValueError):call()
        # Object containers of real numbers remain legal at every model/IC/input port.
        args=[np.array(v,dtype=object) for v in [[[0]],[[1]],[[1]],[[0]]]]
        x,y=constant_response(*args,2,np.array([.5],dtype=object),np.array([.25],dtype=object))
        np.testing.assert_array_equal(x,[1]);np.testing.assert_array_equal(y,[1])

    def test_static_transfer_redundant_dynamic_state(self):
        # Theory admits n*=0, y=2u; the numerical model deliberately keeps n>=1.
        A,B,C,D=[[0]],[[0]],[[1]],[[2]]
        for t in [0,.5,2]:
            x,y=constant_response(A,B,C,D,t,[0],[.7])
            np.testing.assert_array_equal(x,[0]);np.testing.assert_allclose(y,[1.4])
        for s in [1,2,1j]:
            np.testing.assert_array_equal(transfer(A,B,C,D,s),[[2]])
        self.assertEqual(rank_report(structure(A,B,C)[0])['rank'],0)
        np.testing.assert_array_equal(np.array(markov(A,B,C,4)).ravel(),np.zeros(4))

    def test_rank_nonfinite_singular_values_or_threshold_rejected(self):
        # K=a*[[1,1],[1,-1]]: determinant=-2a^2 is nonzero, rank=2.
        # Each singular value is a*sqrt(2), beyond binary64 for a=1.7e308.
        with self.assertRaises(ValueError):rank_report([[1.7e308,1.7e308],[1.7e308,-1.7e308]])
        scaled=rank_report([[1.,1.],[1.,-1.]])
        self.assertEqual(scaled['rank'],2)
        np.testing.assert_allclose(scaled['singular_values'],[math.sqrt(2)]*2)
        with self.assertRaises(ValueError):rank_report([[2.]],rtol=1e308)

    def test_numerical_failure_and_invalid_shapes(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error',RuntimeWarning)
            with self.assertRaises(ValueError):transition([[1]],1000)
            with self.assertRaises(ValueError):transition([[1e308]],1e308)
        for A in [[],[1,2],[[1,2]],[[np.nan]],[[np.inf]],[[1j]]]:
            with self.assertRaises(ValueError):expm(A)
        for T in [-1,np.inf,np.nan,1j,True]:
            with self.assertRaises(ValueError):transition([[1]],T)
        with self.assertRaises(ValueError):model(np.eye(2),[[1]],[[1,0]],[[0]])
        with self.assertRaises(ValueError):constant_response([[0]],[[1]],[[1]],[[0]],1,[],[1])
        with self.assertRaises(ValueError):gramian(np.eye(2),[[1]],1)
        with self.assertRaises(ValueError):structure(np.eye(2),[[1],[2]],[1,2])
        with self.assertRaises(ValueError):rank_report([[1]],rtol=-1)
        with self.assertRaises(ValueError):markov([[1]],[[1]],[[1]],-1)
        with self.assertRaises(ValueError):transfer([[1]],[[1]],[[1]],[[0]],np.inf)

if __name__=='__main__':unittest.main()
