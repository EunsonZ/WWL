import json
import math
from pathlib import Path
import unittest
import numpy as np
import receiver_lab as lab


class ReceiverContracts(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(Path(__file__).with_name('fixed-inputs.json').read_text())

    def test_full_convolution_and_tail(self):
        H=lab.channel_matrix([1,0.5],2)
        np.testing.assert_array_equal(H,[[1,0],[0.5,1],[0,0.5]])
        np.testing.assert_array_equal(H@np.array([1,-1]),[1,-0.5,-0.5])
        np.testing.assert_allclose(lab.equalizer(H,0)@np.array([1,-0.5,-0.5]),[1,-1],atol=1e-13)

    def test_training_hand_inverse(self):
        X=np.array([[1,0],[-1,1],[0,-1]])
        y=np.array([1,-0.5,-0.5])
        np.testing.assert_array_equal(X.T@X,[[2,-1],[-1,2]])
        np.testing.assert_allclose(np.linalg.solve(X.T@X,X.T@y),[1,0.5],atol=1e-13)

    def test_scalar_lmmse_not_unbiased(self):
        H=np.array([[0.1+0j]])
        self.assertAlmostEqual(float(lab.equalizer(H,0).real[0,0]),10)
        W=lab.equalizer(H,0.4)
        self.assertAlmostEqual(float(W.real[0,0]),0.1/0.41)
        mse=abs((W@H)[0,0]-1)**2+0.4*abs(W[0,0])**2
        self.assertAlmostEqual(mse,0.4/0.41)

    def test_crc_original_examples_and_second_moments(self):
        w=self.c['syndrome_weights_x6_to_x0']
        np.testing.assert_array_equal(lab.encode('1101',w),lab.bits('1101001'))
        self.assertEqual(lab.syndrome(lab.bits('0001011'),w),0)
        code=np.array([lab.encode(f'{m:04b}',w) for m in range(16)])
        self.assertTrue(all(lab.syndrome(row,w)==0 for row in code))
        a=2*code-1
        np.testing.assert_array_equal(a.mean(axis=0),np.zeros(7))
        np.testing.assert_array_equal(a.T@a/16,np.eye(7))

    def test_constellation_energy_and_gray_neighbors(self):
        for name in ['4PAM','QPSK','16QAM']:
            a,labels=lab.constellation(name)
            self.assertAlmostEqual(float(np.mean(abs(a)**2)),1)
            d=abs(a[:,None]-a[None,:]); d[d==0]=np.inf
            for i,j in zip(*np.where(abs(d-d.min())<1e-13)):
                self.assertEqual(sum(x!=y for x,y in zip(labels[i],labels[j])),1)

    def test_full_notch_finite_rank(self):
        for K in [7,31]:
            H=lab.channel_matrix([1,-0.98],K)
            s=np.linalg.svd(H,compute_uv=False)[-1]
            self.assertAlmostEqual(s,math.sqrt(1+0.98**2-1.96*math.cos(math.pi/(K+1))))
            H0=lab.channel_matrix([1,-1],K)
            self.assertEqual(np.linalg.matrix_rank(H0),K)
            self.assertAlmostEqual(float(np.linalg.norm(H0@np.ones(K))),math.sqrt(2))

    def test_acquisition_uses_pilot_only(self):
        c=self.c; w=c['syndrome_weights_x6_to_x0']
        _,_,npilot,_,bank=lab.models(c)
        # All data choices produce exactly the same first 75 noise-free coordinates.
        words=np.array([lab.encode(f'{m:04b}',w) for m in range(16)])
        h=np.array([0.9,0.6*np.exp(0.4j)])*np.exp(0.45j)
        r=lab.transmit(c,words,h,np.random.default_rng(0),0)
        np.testing.assert_array_equal(r[:,:npilot],np.tile(r[0,:npilot],(16,1)))
        ix,hh,_=lab.acquire(r,npilot,bank)
        self.assertTrue(all(bank[i][:2]==(3,40) for i in ix))
        np.testing.assert_allclose(hh,np.tile(h,(16,1)),atol=1e-12)

    def test_denominators(self):
        word=lab.bits('1101001')[None,:]
        est=(2*lab.bits('1100010')-1)[None,:]
        x=lab.counts(est,word,self.c['syndrome_weights_x6_to_x0'],10)
        self.assertEqual((x['sync_failures'],x['compared_bits'],x['bit_errors'],x['frame_errors'],x['undetected_errors']),(9,7,3,1,1))
        self.assertEqual(x['undetected_per_attempt'],0.1)
        self.assertEqual(x['undetected_given_frame_error'],1)


if __name__=='__main__': unittest.main()
