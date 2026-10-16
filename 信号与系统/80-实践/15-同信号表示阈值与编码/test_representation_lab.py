import copy
import json
import math
import os
from pathlib import Path
import struct
import unittest
import representation_lab as lab


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank=lab.load(os.environ['WWL_HAAR_SOURCE'],'test_published_haar')
        cls.resample=lab.load(os.environ['WWL_RESAMPLE_SOURCE'],'test_published_resample')
        cls.stft=lab.load(os.environ['WWL_STFT_SOURCE'],'test_published_stft')
        cls.c=json.loads((Path(__file__).parent/'fixed-inputs.json').read_text())

    def test_known_pair_block(self):
        x=[1.,3.]*32
        v=lab.haar(x,1,self.bank,self.resample)
        for a in v[:32]:self.assertAlmostEqual(a,2*math.sqrt(2))
        for d in v[32:]:self.assertAlmostEqual(d,-math.sqrt(2))
        self.assertLess(max(abs(a-b) for a,b in zip(x,lab.inverse_haar(v,1,self.bank,self.resample))),1e-13)

    def test_threshold_rules_and_failure(self):
        self.assertEqual(lab.threshold([1,.05,-.2],1,.12,'hard'),[1,0,-.2])
        self.assertAlmostEqual(lab.threshold([1,.05,-.2],1,.12,'soft')[2],-.08)
        self.assertEqual(lab.threshold([1,.05,-.2],1,.12,'drop'),[1,0,0])
        self.assertEqual(lab.threshold([1,.06],1,.12,'soft'),[1,0])

    def test_constant_psd_and_coverage(self):
        r=lab.spectral([1.]*256,self.c,self.c['stft'][0],self.stft)
        self.assertTrue(all(abs(v-1.5)<1e-13 for v in r['denominator']))
        self.assertEqual(r['unextended_unknown_indices'],[0])
        at=r['starts'].index(0)
        self.assertAlmostEqual(r['one_sided_psd_V2_per_Hz'][at][0],1/96,delta=1e-13)
        self.assertAlmostEqual(sum(r['one_sided_psd_V2_per_Hz'][at])*32,1,delta=1e-13)
        self.assertEqual(r['power_sign_collision_max'],0)

    def test_actual_byte_decode_and_budget(self):
        x=[1.,3.]*32;c=lab.haar(x,1,self.bank,self.resample)
        blob=lab.encode(c,64,1,1024,.01,True)
        d=lab.decode(bytes(blob),self.bank,self.resample)
        self.assertEqual(len(blob),24+4*64)
        err=sum((a-b)**2 for a,b in zip(d['samples_V'],x))
        self.assertLessEqual(err,64*.01**2/4+1e-12)
        pcm=lab.encode(x,64,0,1024,.01,False)
        self.assertEqual(len(pcm),24+2*64)
        self.assertEqual(lab.decode(pcm,self.bank,self.resample)['samples_V'],x)

    def test_rounding_and_overflow(self):
        self.assertEqual(lab.quantize([.005,.015,-.005,-.015],.01),[0,2,0,-2])
        with self.assertRaises(ValueError):lab.quantize([400.],.01)
        with self.assertRaises(ValueError):lab.quantize([1.],0)
        with self.assertRaises(ValueError):lab.encode([1.]*32,64,1,1024,.01,True)

    def test_corrupt_container(self):
        blobs=[b'',lab.HEADER.pack(b'BAD!',64,0,1024,.01,64)+b'\0'*128,
               lab.HEADER.pack(b'WSP1',64,1,1024,.01,2)+lab.PAIR.pack(1,1)+lab.PAIR.pack(0,1),
               lab.HEADER.pack(b'WSP1',64,1,1024,float('nan'),0),
               lab.HEADER.pack(b'PCM1',64,0,1024,.01,64)+b'\0'*127]
        for b in blobs:
            with self.assertRaises(ValueError):lab.decode(b,self.bank,self.resample)

    def test_input_contract(self):
        lab.validate(self.c)
        for key,value in [('length',True),('haar_levels',True),('quantization_step_V',.001),('sample_rate_Hz',0)]:
            d=copy.deepcopy(self.c);d[key]=value
            with self.assertRaises(ValueError):lab.validate(d)
        d=copy.deepcopy(self.c);d['noise_cases'][0]['signs']='+'*255
        with self.assertRaises(ValueError):lab.validate(d)
        d=copy.deepcopy(self.c);d['stft'][0]['hop']=3
        with self.assertRaises(ValueError):lab.validate(d)


if __name__=='__main__':unittest.main()
