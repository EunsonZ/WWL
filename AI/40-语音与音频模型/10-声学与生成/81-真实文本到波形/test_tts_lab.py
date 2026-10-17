import copy
import csv
import json
from pathlib import Path
import unittest
import numpy as np
import tts_lab as lab


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=Path(__file__).parent;cls.cfg=json.loads((cls.base/'inputs.json').read_text());cls.out=json.loads((cls.base/'results/results.json').read_text())

    def test_typed_normalizer_and_ambiguity(self):
        c=self.cfg;n=lab.normalize_probe(c['probe'],c['application_contract'])
        self.assertEqual(n['text'],c['expanded']);self.assertEqual(n['semantic_slots'],dict(currency='USD',amount_cents=1250,day=3,month=4))
        other=copy.deepcopy(c['application_contract']);other['date_order']='MM/DD'
        alt=lab.normalize_probe(c['probe'],other)
        self.assertIn('March fourth',alt['text']);self.assertEqual(alt['semantic_slots']['month'],3)
        bad=lab.normalize_probe(c['probe'],c['application_contract'],True)
        self.assertEqual(bad['text'],c['bad_normalized']);self.assertIsNone(bad['semantic_slots'])
        with self.assertRaises(ValueError):lab.normalize_probe('arbitrary text',c['application_contract'])

    def test_corpus_bytes_split_and_shapes(self):
        rows=json.loads((self.base/'data/utterances.json').read_text());self.assertEqual([r['id'] for r in rows],self.cfg['corpus_ids'])
        self.assertEqual(len({r['speaker_id'] for r in rows}),1)
        for r in rows:self.assertEqual(lab.sha((self.base/'data'/r['audio']).read_bytes()),r['sha256'])
        for r in self.out['corpus']:
            self.assertEqual(r['metrics']['sample_rate_hz'],16000);self.assertEqual(r['metrics']['channels'],1)
        for r in self.out['cases']:
            q,sr=lab.read_wav(self.base/'results'/(r['name']+'.wav'))
            self.assertEqual(sr,22050);self.assertEqual(lab.sha(q.tobytes()),r['metrics']['pcm_sha256'])
            self.assertEqual(len(q)/sr,r['metrics']['duration_s'])

    def test_actual_events_and_speed(self):
        p=self.base/'results';lookup={r['name']:r for r in self.out['cases']}
        for r in self.out['cases']:
            events=json.loads((p/(r['name']+'.events.json')).read_text())['events']
            phones=[e for e in events if e['type']==7]
            self.assertTrue(all(a['audio_ms']<=b['audio_ms'] for a,b in zip(phones,phones[1:])))
            self.assertLessEqual(max(e['audio_ms'] for e in events),r['metrics']['duration_s']*1000+1)
        for name in ('probe_slow','probe_pitch'):self.assertEqual(lookup[name]['phone_sequence'],lookup['probe_explicit']['phone_sequence'])
        self.assertGreater(lookup['probe_slow']['metrics']['duration_s'],lookup['probe_explicit']['metrics']['duration_s'])
        self.assertGreater(lookup['probe_pitch']['dispatch_pitch_median_hz'],lookup['probe_explicit']['dispatch_pitch_median_hz'])

    def test_clipping_by_integer_oracle(self):
        p=self.base/'results';q,sr=lab.read_wav(p/'probe_explicit.wav');damaged,_=lab.read_wav(p/'probe_clipped.wav')
        expected=[min(32767,max(-32768,4*int(v))) for v in q]
        self.assertEqual(damaged.tolist(),expected)
        self.assertGreater(self.out['clipped']['error']['saturation_fraction'],0)
        self.assertEqual(len(q),len(damaged))
        # Front-end and acoustic schedule remain the source case; no false regenerated trace.
        self.assertEqual(self.out['clipped']['source_case'],'probe_explicit')

    def test_dispatch_units_and_known_branch(self):
        with (self.base/'results/probe_explicit.acoustic.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(int(rows[0]['dispatch']),0);self.assertEqual(int(rows[0]['local_samplecount']),0)
        # Fixed-point trace is Hz after /65536, while F0_hz denotes spectral peak index 0.
        self.assertAlmostEqual(float(rows[0]['pitch_hz']),94.04492188)
        self.assertEqual(float(rows[0]['F0_hz']),284.)
        self.assertEqual([int(rows[0]['harmonic'+str(i)+'_raw']) for i in range(1,5)],[447,617,803,782])
        self.assertTrue(all(float(r['pitch_hz'])>0 for r in rows))

    def test_declared_boundary(self):
        bad=copy.deepcopy(self.cfg);bad['application_contract']['date_order']='MM/DD'
        with self.assertRaises(ValueError):lab.validate(bad)
        self.assertEqual(self.out['listening']['status'],'not_performed')
        self.assertEqual(self.out['listening']['naturalness'],'not_measured')
        self.assertEqual(self.out['listening']['automatic_intelligibility'],'not_measured')


if __name__=='__main__':unittest.main()
