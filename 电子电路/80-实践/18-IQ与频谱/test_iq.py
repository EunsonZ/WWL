import cmath
import itertools
import math
import unittest
import iq

def dft(x):
    n = len(x)
    return [sum(v*cmath.exp(-2j*math.pi*k*m/n) for m,v in enumerate(x)) for k in range(n)]

class IQTests(unittest.TestCase):
    def close(self, a, b, tol=3e-12):
        self.assertEqual(len(a), len(b))
        self.assertLess(max(abs(x-y) for x,y in zip(a,b)), tol)
    def test_fft_independent_dft(self):
        fs,fc,z,x,_ = iq.case()
        self.close(iq.fft(z), dft(z), 4e-12)
        self.close(iq.fft(x), dft(x), 4e-12)
        self.close(iq.fft(iq.fft(z), True), z)
    def test_roundtrip(self):
        _,_,z,_,r = iq.case()
        self.close(r,z)
    def test_constant_orthogonal_projection(self):
        n=128
        x=[2*math.cos(2*math.pi*16*k/n)+math.sin(2*math.pi*16*k/n) for k in range(n)]
        # Independent sums implement period-averaged orthogonal integrals.
        i=sum(2*a*math.cos(2*math.pi*16*k/n) for k,a in enumerate(x))/n
        q=sum(-2*a*math.sin(2*math.pi*16*k/n) for k,a in enumerate(x))/n
        self.assertAlmostEqual(i,2)
        self.assertAlmostEqual(q,-1)
        self.assertAlmostEqual(math.sqrt(sum(a*a for a in x)/n),math.sqrt(2.5))
        self.close(iq.demodulate(x,128,16,0), [2-1j]*n)
    def test_scaling_signed_bins(self):
        n=128
        c=[3*math.cos(2*math.pi*7*k/n) for k in range(n)]
        C=iq.fft(c)
        self.assertAlmostEqual(abs(C[7]),192)
        self.assertAlmostEqual(abs(C[-7])/n,1.5)
        z=[3*cmath.exp(2j*math.pi*7*k/n) for k in range(n)]
        Z=iq.fft(z)
        self.assertAlmostEqual(abs(Z[7])/n,3)
        self.assertLess(abs(Z[-7]),1e-12)
    def test_lo_phase_frequency(self):
        fs,fc,z,x,_=iq.case()
        self.close(iq.demodulate(x,fs,fc,4,math.pi/2),[-1j*a for a in z])
        expected=[a*cmath.exp(-2j*math.pi*k/128) for k,a in enumerate(z)]
        self.close(iq.demodulate(x,fs,17,4),expected)
    def test_wrong_gain_and_q_counterexamples(self):
        fs,fc,z,x,r=iq.case()
        half=iq.bin_lowpass([a/2 for a in iq.mix(x,fs,fc)],fs,4)
        self.close(half,[a/2 for a in z])
        self.assertGreater(max(abs(a-b.conjugate()) for a,b in zip(z,r)),1)
    def test_alias_counterexample(self):
        self.close([math.cos(2*math.pi*66*k/128) for k in range(128)],
                   [math.cos(2*math.pi*62*k/128) for k in range(128)],8e-14)
    def test_finite_window_counterexample(self):
        x=[math.cos(2*math.pi*16.25*k/128) for k in range(128)]
        # Periodic bin LPF does not restore an off-bin constant-envelope premise.
        out=iq.demodulate(x,128,16.25,0)
        self.assertGreater(abs(out[0]-1),.005)
        X=iq.fft(x)
        self.assertGreater(abs(X[15]),1)
    def test_invalid_beforecast(self):
        for bad in ([1+0j,2],[True,2],[float('nan'),2],[[1],2],['1',2]):
            with self.assertRaises(ValueError): iq.mix(bad,128,16)
        for bad in ([complex(1,float('inf')),2],[1,2,3],[]):
            with self.assertRaises(ValueError): iq.fft(bad)
        with self.assertRaises(ValueError): iq.fft(itertools.repeat(1))
        for args in ((0,16,4),(128,0,4),(128,64,4),(128,16,16),(128,60,4),(128,16,-1),(128,16,complex(4,0))):
            with self.assertRaises(ValueError): iq.demodulate([1,2],*args)
    def test_derived_overflow(self):
        with self.assertRaises(ValueError): iq.mix([1e308,1e308],128,16)
        with self.assertRaises(ValueError): iq.fft([1e308,1e308])
    def test_maximum_budget(self):
        self.assertEqual(len(iq.fft([0]*4096)),4096)
        with self.assertRaises(ValueError): iq.fft([0]*8192)

if __name__ == '__main__': unittest.main()
