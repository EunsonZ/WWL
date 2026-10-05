"""Independent hand values, invariants and bad inputs; never writes artifacts."""
import unittest
import warnings
import numpy as np
from resample_lab import (Stream, design, offline, polyphase, fixed, quantize_q15,
                          round_div_even, single_amplitude, certified_specs)

class ResampleTests(unittest.TestCase):
    def test_hand_convolution_phase_and_tail(self):
        x, h = [1,2,3,4], [1,2,3,4]
        # Full convolution [1,4,10,20,25,24,16], retain 0,3,6.
        np.testing.assert_array_equal(offline(x,h),[1,20,16])
        np.testing.assert_array_equal(polyphase(x,h),[1,20,16])
        np.testing.assert_array_equal(offline(x,h,3,1),[4,25])

    def test_every_partition_small_record(self):
        x = np.array([1.,-2.,3.,0.,4.,-1.,2.])
        h = np.array([.25,.5,.25])
        for phase in range(3):
            expected = offline(x,h,3,phase)
            for mask in range(1 << (len(x)-1)):
                cuts = [0]+[i+1 for i in range(len(x)-1) if mask & (1 << i)]+[len(x)]
                s = Stream(h,3,phase)
                ys = [s.process([])]
                ys += [s.process(x[a:b]) for a,b in zip(cuts,cuts[1:])]
                ys += [s.flush(),s.flush()]
                np.testing.assert_array_equal(np.concatenate(ys),expected)

    def test_random_polyphase_and_blocks(self):
        rng = np.random.default_rng(731)
        for N in [1,2,3,4,17,100]:
            for L in [1,2,7,193]:
                x,h = rng.normal(size=N),rng.normal(size=L)
                for phase in range(3):
                    s = Stream(h,3,phase)
                    ys = [s.process(x[i:i+5]) for i in range(0,N,5)]+[s.flush()]
                    np.testing.assert_allclose(np.concatenate(ys),offline(x,h,3,phase),atol=1e-12)
                    np.testing.assert_allclose(polyphase(x,h,3,phase),offline(x,h,3,phase),atol=1e-12)

    def test_empty_reset_and_fail_before_mutation(self):
        s = Stream([.25,.5,.25])
        self.assertEqual(len(s.flush()),0)
        with self.assertRaises(RuntimeError): s.process([1])
        s.reset()
        with self.assertRaises(ValueError): s.process([1,np.nan])
        self.assertEqual(s.n,0)
        np.testing.assert_array_equal(np.concatenate([s.process([1,2,3,4]),s.flush()]),offline([1,2,3,4],s.h))
        s.reset()
        self.assertEqual(s.n,0)
        self.assertFalse(s.ring.any())

    def test_alias_identity_and_filter_tones(self):
        n=np.arange(4800)
        np.testing.assert_allclose(np.cos(2*np.pi*10000*n/48000)[::3],
                                   np.cos(2*np.pi*6000*np.arange(1600)/16000),atol=2e-12)
        h=design(); k=np.arange(len(h))
        H=lambda f: abs(sum(h*np.exp(-2j*np.pi*f*k/48000)))
        self.assertLess(H(10000),.001)
        self.assertLess(abs(H(1000)-1),.01)
        specs=certified_specs(h)
        self.assertLess(specs['pass_error_enclosure'],.01)
        self.assertLess(specs['stop_max_enclosure'],.001)
        self.assertLess(certified_specs(quantize_q15(h)/32768)['stop_max_enclosure'],.001)

    def test_dc_symmetry_group_delay(self):
        h=design()
        np.testing.assert_allclose(h,h[::-1],atol=1e-16)
        self.assertAlmostEqual(h.sum(),1,places=14)
        self.assertAlmostEqual(float(np.dot(np.arange(193),h)),96,places=12)
        y=offline(np.ones(1000),h)
        np.testing.assert_allclose(y[64:334],1,atol=1e-14)

    def test_exact_rounding_saturation_and_accumulator_failure(self):
        self.assertEqual([round_div_even(v,2) for v in [-7,-5,-3,-1,1,3,5,7]],[-4,-2,-2,0,0,2,2,4])
        np.testing.assert_array_equal(quantize_q15([-2,-1,0,1,2]),[-32768,-32768,0,32767,32767])
        y,stats=fixed([.5],[.5],factor=1)
        np.testing.assert_array_equal(y,[.25]); self.assertEqual(stats['mac_clips'],0)
        y,stats=fixed([-.5],[.5],factor=1)
        np.testing.assert_array_equal(y,[-.25])
        _,small=fixed(np.ones(5)*.9,[.9,.9,.9],factor=1,acc_bits=16)
        self.assertGreater(small['mac_clips'],0)
        _,wide=fixed(np.ones(5)*.9,[.9,.9,.9],factor=1,acc_bits=40)
        self.assertEqual(wide['mac_clips'],0)
        self.assertGreater(wide['output_clips'],0)

    def test_spectrum_dc_nyquist_odd(self):
        _,a=single_amplitude(np.ones(8)*.5,8)
        self.assertEqual(a[0],.5)
        _,a=single_amplitude((-1.)**np.arange(8),8)
        self.assertEqual(a[-1],1)
        _,a=single_amplitude(np.cos(2*np.pi*2*np.arange(9)/9),9)
        self.assertAlmostEqual(a[2],1)

    def test_dropped_samples_and_block_reset_change_record(self):
        x=np.arange(20,dtype=float);h=[.25,.5,.25]
        good=offline(x,h)
        deleted=offline(np.delete(x,[5,6]),h)
        self.assertFalse(np.array_equal(good,deleted))
        a,b=Stream(h),Stream(h)
        wrong=np.concatenate([a.process(x[:5]),a.flush(),b.process(x[5:]),b.flush()])
        self.assertFalse(np.array_equal(good,wrong))
        # Preserving elapsed time with specified zero gap differs from deletion.
        gap=x.copy();gap[5:7]=0
        self.assertEqual(len(offline(gap,h)),len(good))

    def test_numerically_unrepresentable_cutoff_rejected(self):
        # Positive mathematical cutoff is not enough when cutoff/fs underflows.
        # No NaN return or RuntimeWarning may escape to a caller.
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            with self.assertRaises(ValueError):
                design(193, 1e-323, 48000)
        h = design(193, 1e-250, 48000)
        self.assertTrue(np.all(np.isfinite(h)))
        self.assertAlmostEqual(float(h.sum()), 1, places=14)

    def test_invalid_objects(self):
        for x in [[np.inf],[[1]], [1j]]:
            with self.assertRaises(ValueError): offline(x,[1])
        for args in [(2,7000,48000),(193,24000,48000),(193,7000,0)]:
            with self.assertRaises(ValueError): design(*args)
        with self.assertRaises(ValueError): Stream([])
        with self.assertRaises(ValueError): offline([1],[1],0)
        with self.assertRaises(ValueError): offline([1],[1],3,3)
        with self.assertRaises(ValueError): fixed([1],[1],acc_bits=1)

if __name__=='__main__': unittest.main()
