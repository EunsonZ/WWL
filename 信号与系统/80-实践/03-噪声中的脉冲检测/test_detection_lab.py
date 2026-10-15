import unittest
import math
import warnings
import numpy as np
from detection_lab import (known_score, white_scores, colored_score, periodogram,
    threshold, sample_variance, evaluate, calibrate_maxima, simulation)

class DetectionTests(unittest.TestCase):
    def test_closed_form(self):
        self.assertAlmostEqual(known_score([2,1],[1,2]),4/math.sqrt(5))
        self.assertAlmostEqual(colored_score([2,1],[1,2],[[4,0],[0,1]]),2.5/math.sqrt(4.25))
        np.testing.assert_allclose(white_scores([0,1,2,1,0],[1,2,1]),[4,6,4]/np.sqrt(6))
        self.assertAlmostEqual(threshold(.5),0)

    def test_psd_dc_and_parseval(self):
        for x in ([2,2,2,2],[1,-1,1,-1],[1,2,3,4,5]):
            f,p=periodogram(x,8)
            self.assertAlmostEqual(sum(p)*8/len(x),np.mean(np.square(x)))
            _,q=periodogram(x,8,True)
            self.assertAlmostEqual(sum(q)*8/len(x),np.var(x,ddof=0))
            self.assertAlmostEqual(q[0],0)
        _,p=periodogram([2,2,2,2],8)
        self.assertEqual(p[0],2)
        _,p=periodogram([1e153]*16,16)
        self.assertTrue(np.all(np.isfinite(p)))
        self.assertAlmostEqual(p[0],1e306)

    def test_variance_bias_correction_independent_enumeration(self):
        # All iid Bernoulli(.5) pairs: unbiased mean is population variance .25.
        pairs=[[0,0],[0,1],[1,0],[1,1]]
        self.assertEqual(sum(sample_variance(x) for x in pairs)/4,.25)
        self.assertEqual(sample_variance([1e308,1e308]),0)
        self.assertEqual(sum(np.var(x) for x in pairs)/4,.125)

    def test_multiple_independent_positions(self):
        # Template [1] makes the positions genuinely independent, exact FPR 1-(1-a)^K.
        rng=np.random.default_rng(71); z=rng.normal(size=(100000,8)); t=threshold(.01)
        observed=np.mean(z.max(axis=1)>t); exact=1-.99**8
        self.assertLess(abs(observed-exact),.004)
        self.assertLess(np.mean(z.max(axis=1)>threshold(.01/8)),.014)
        self.assertGreater(observed,.05)

    def test_labels_and_unknown(self):
        self.assertEqual(evaluate([0,0,1,1],[0,1,0,1])['fpr'],.5)
        self.assertIsNone(evaluate([1],[1])['fpr'])
        for y,d in [([0,2],[0,1]),([0],[float('nan')]),([] ,[]),([0,1],[1])]:
            with self.assertRaises(ValueError): evaluate(y,d)

    def test_invalid_inputs(self):
        for x,s in [([], [1]),([1],[0]),([float('nan')],[1]),([1],[1,2])]:
            with self.assertRaises(ValueError): known_score(x,s)
        for a in (0,1,-.1,float('nan')):
            with self.assertRaises(ValueError): threshold(a)
        for c in ([[1,2],[2,1]],[[1,1],[0,1]]):
            with self.assertRaises(ValueError): colored_score([1,2],[1,1],c)
        with self.assertRaises(ValueError): sample_variance([1])
        with self.assertRaises(ValueError): white_scores([1],[1,1])
        with self.assertRaises(ValueError): periodogram([1],0)

    def test_real_only_numpy_and_object_inputs(self):
        for c in (np.array([[4+3j,0],[0,1]]), np.array([[4+0j,0],[0,1]]),
                  np.array([[4+3j,0],[0,1]],dtype=object)):
            with self.assertRaises(ValueError): colored_score([2,1],[1,2],c)
        for complex_vector in (np.array([2+3j,1]),np.array([2+0j,1]),
                               np.array([2+3j,1],dtype=object)):
            with self.assertRaises(ValueError): known_score(complex_vector,[1,2])
            with self.assertRaises(ValueError): known_score([2,1],complex_vector)
            with self.assertRaises(ValueError): white_scores(complex_vector,[1])
            with self.assertRaises(ValueError): colored_score(complex_vector,[1,2],np.eye(2))
            with self.assertRaises(ValueError): colored_score([2,1],complex_vector,np.eye(2))
            with self.assertRaises(ValueError): periodogram(complex_vector,8)
        for value in (1+0j,np.array(1+2j),np.array(1+0j,dtype=object)):
            with self.assertRaises(ValueError): known_score([2,1],[1,2],value)
            with self.assertRaises(ValueError): periodogram([2,1],value)
            with self.assertRaises(ValueError): threshold(value)
        with self.assertRaises(ValueError): evaluate(np.array([0,1],dtype=complex),[0,1])
        for bad in ([object(),1],['nonnumeric',1],[float('inf'),1]):
            with self.assertRaises(ValueError): known_score(bad,[1,2])
        for c in ([[object(),0],[0,1]],[[float('nan'),0],[0,1]]):
            with self.assertRaises(ValueError): colored_score([2,1],[1,2],c)

    def test_numpy_complex_scalars_inside_object_arrays(self):
        # 2 scalar types x 2 imaginary cases x 6 entries = 24 rejections.
        for dtype in (np.complex64, np.complex128):
            for imag in (0.0, 2.0):
                cov=np.array([[dtype(4+imag*1j),0],[0,1]],dtype=object)
                vec=np.array([dtype(2+imag*1j),1],dtype=object)
                scalar=np.array(dtype(1+imag*1j),dtype=object)
                alpha=np.array(dtype(.1+imag*1j),dtype=object)
                labels=np.array([0,dtype(1+imag*1j)],dtype=object)
                cases=(('covariance',lambda:colored_score([2,1],[1,2],cov)),
                       ('vector',lambda:known_score(vec,[1,2])),
                       ('template',lambda:known_score([2,1],vec)),
                       ('sigma',lambda:known_score([2,1],[1,2],scalar)),
                       ('alpha',lambda:threshold(alpha)),
                       ('labels',lambda:evaluate(labels,[0,1])))
                for entry,fn in cases:
                    with self.subTest(dtype=dtype.__name__,imag=imag,entry=entry):
                        with warnings.catch_warnings(record=True) as seen:
                            warnings.simplefilter('always')
                            with self.assertRaises(ValueError): fn()
                        self.assertEqual(seen,[], 'reject before any lossy float conversion')

    def test_covariance_symmetry_is_unit_invariant(self):
        asymmetric=np.array([[4.,0.],[.9,1.]])
        for unit in (1.,1e-6,1e6):
            with self.assertRaises(ValueError):
                colored_score(unit*np.array([2.,1.]),unit*np.array([1.,2.]),unit**2*asymmetric)
        # Separate two-scale small off-diagonal counterexample avoids absolute tolerance.
        other=np.array([[1.,0.],[1e-4,2.]])
        for unit in (1.,1e-6):
            with self.assertRaises(ValueError):
                colored_score(unit*np.array([2.,1.]),unit*np.array([1.,2.]),unit**2*other)
        c=np.array([[4.,.5],[.5,1.]])
        baseline=colored_score([2,1],[1,2],c)
        for unit in (1e-6,1e6):
            self.assertAlmostEqual(colored_score(unit*np.array([2.,1.]),unit*np.array([1.,2.]),unit**2*c),baseline)
        for c in (np.zeros((2,2)),np.diag([1.,0.]),np.diag([1.,-1.])):
            with self.assertRaises(ValueError): colored_score([2,1],[1,2],c)
        with self.assertRaises(ValueError): colored_score([2,1],[0,0],np.eye(2))

    def test_large_finite_score_intermediates_rejected_without_nan(self):
        # (1e308*2)/(1e308*2)=1 mathematically; unreduced intermediate overflows.
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter('always')
            with self.assertRaises(ValueError):known_score([1e308],[2],1e308)
            with self.assertRaises(ValueError):white_scores([1e308],[2],1e308)
        self.assertEqual(seen,[])
        self.assertEqual(known_score([1e150],[2],1e150),1.)
        np.testing.assert_array_equal(white_scores([1e150],[2],1e150),[1.])

    def test_small_alpha_threshold_without_subtractive_cancellation(self):
        alpha=1e-20;t=threshold(alpha)
        self.assertTrue(math.isfinite(t));self.assertGreater(t,9.)
        # Independent erfc survival probability, not 1-CDF cancellation.
        tail=0.5*math.erfc(t/math.sqrt(2))
        self.assertAlmostEqual(tail/alpha,1.,places=12)

    def test_calibration_and_reproducibility(self):
        self.assertEqual(calibrate_maxima([1,2,3,4],.25),4)
        self.assertEqual(simulation(11,20,40),simulation(11,20,40))

if __name__=='__main__': unittest.main()
