import copy
import json
from pathlib import Path
import unittest
import numpy as np
import source_filter_lab as lab


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cfg=json.loads(Path(__file__).with_name('inputs.json').read_text())

    def test_impulse_closed_form_and_stability(self):
        s=lab.section(16000,500,80);u=np.zeros(512);u[0]=1
        np.testing.assert_allclose(lab.filter_section(u,s),lab.impulse_closed(s,512),atol=2e-14,rtol=0)
        self.assertLess(s['radius'],1);self.assertAlmostEqual(abs(lab.response([s],[0],16000)[0]),1)
        self.assertAlmostEqual(-np.log(s['radius'])*16000/np.pi,80)

    def test_cascade_different_route(self):
        cfg=copy.deepcopy(self.cfg);cfg.update(duration_s=.04,warmup_s=.04)
        out,arr=lab.analyze(cfg)
        for row in out['cases']:
            n=out['samples']+out['warmup_samples'];u=np.zeros(n);u[::row['period_samples']]=1
            h1=lab.impulse_closed(row['sections'][0],n);h2=lab.impulse_closed(row['sections'][1],n)
            expected=np.convolve(np.convolve(u,h1)[:n],h2)[:n][out['warmup_samples']:]
            np.testing.assert_allclose(expected,arr[row['name']+'_raw'],atol=5e-14,rtol=0)

    def test_frame_contract_and_integer_period(self):
        out,arr=lab.analyze(self.cfg)
        self.assertEqual(out['stft_shape'],[98,257]);self.assertEqual(out['frame_first_center_s'],.01246875)
        self.assertEqual(out['frame_last_center_s'],.98246875)
        for row in out['cases']:
            name=row['name'];self.assertLess(row['period_repeat_max_error'],1e-12)
            self.assertLess(row['steady_fft_max_complex_error'],2e-8)
            source=arr[name+'_source'];self.assertEqual(list(np.flatnonzero(source)[:2]),[96,224] if name!='pitch' else [32,96])
        self.assertEqual(out['cases'][0]['sections'],out['cases'][1]['sections'])
        np.testing.assert_array_equal(arr['base_source'],arr['filter_source'])

    def test_pcm_and_single_common_gain(self):
        out,arr=lab.analyze(self.cfg)
        for row in out['cases']:
            y=arr[row['name']+'_samples'];q=np.rint(y*32768).astype('<i2')
            self.assertLessEqual(np.max(np.abs(q.astype(float)/32768-y)),1/65536)
            np.testing.assert_array_equal(y,out['common_output_gain']*arr[row['name']+'_raw'])
        self.assertAlmostEqual(max(r['peak'] for r in out['cases']),.8)

    def test_pulse_coefficients_and_spectrum_units(self):
        out,arr=lab.analyze(self.cfg)
        for row in out['cases']:
            p=row['period_samples'];u=arr[row['name']+'_source'];coef=np.fft.rfft(u)/len(u)
            self.assertAlmostEqual(abs(coef[0]),1/p)
            self.assertAlmostEqual(abs(coef[round(row['f0_hz'])]),1/p)
            # Strongest spectral line can be 500 Hz even though fundamental is 125/250.
            self.assertEqual(row['strongest_harmonic_hz'],500)

    def test_reject(self):
        for key,value in [('duration_s',0),('warmup_s',float('nan')),('frame_length',17000),('hop',0),('nfft',128),('pcm_peak',1),('pcm_peak',.999999),('duration_s',20)]:
            c=copy.deepcopy(self.cfg);c[key]=value
            with self.assertRaises(ValueError):lab.validate(c)
        c=copy.deepcopy(self.cfg);c['cases'][0]['f0_hz']=130
        with self.assertRaises(ValueError):lab.validate(c)
        for f,b in [(0,80),(8000,80),(500,0),(500,-10),(500,float('nan'))]:
            with self.assertRaises(ValueError):lab.section(16000,f,b)


if __name__=='__main__':unittest.main()
