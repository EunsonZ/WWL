import copy,json,unittest
from pathlib import Path
import kv_model as model
import batch_oracle
HERE=Path(__file__).parent
class Behavior(unittest.TestCase):
    def setUp(self):self.spec=json.loads((HERE/'spec.json').read_text());self.result=model.run(self.spec)
    def test_key_tuple_and_hash_tag(self):
        c=self.result['key_collision'];self.assertEqual(c['naive'][0],c['naive'][1]);self.assertNotEqual(c['encoded'][0],c['encoded'][1])
        a,r=model.keys(['S1','T1','C10']);self.assertEqual(a.split('{')[1].split('}')[0],r.split('{')[1].split('}')[0])
    def test_cas_retains_tombstone(self):
        p={x['request_id']:x for x in self.result['prefixes']}
        self.assertEqual(p['R15']['result'],{'status':'accepted','version':4})
        self.assertEqual(p['R16']['result'],{'status':'version_conflict','observed_version':4})
        self.assertEqual(p['R15']['current'],p['R16']['current'])
        self.assertEqual(p['R17']['result'],{'status':'accepted','version':5})
    def test_cache_deadline_and_plain_set(self):
        p=self.result['prefixes'];self.assertEqual(p[3]['cache'][0]['value'][0]['current_phone'],'555-0100')
        self.assertEqual(p[4]['cache'],[])
        self.assertIsNone(p[-1]['cache'][0]['expires_at_ms'])
        self.assertEqual(p[-1]['cache'][0]['value'][1]['grade'],'B')
        self.assertEqual(p[-1]['schedules'][0]['rows'][1]['grade'],'C')
    def test_half_open_ties_late_and_all_layouts(self):
        layouts=self.result['prefixes'][-1]['layouts'];all_ids=[]
        for layout in layouts:
            q={x['query_id']:x for x in layout['queries']}
            self.assertEqual([r['event_id'] for pg in q['late_50_100']['pages'] for r in pg['rows']],['R14'])
            self.assertEqual([r['event_id'] for pg in q['day_seam']['pages'] for r in pg['rows']],['R02','R12','R13'])
            all_ids.append([r['event_id'] for pg in q['all_S1']['pages'] for r in pg['rows']])
        self.assertEqual(all_ids[0],all_ids[1]);self.assertEqual(all_ids[1],all_ids[2])
    def test_missing_grade_and_no_registered_row(self):
        p=self.result['prefixes'][18];self.assertEqual(p['result'],{'status':'invalid_payload'})
        self.assertFalse(any(r['key'][-1]=='C30' for r in p['current']))
        s=copy.deepcopy(self.spec);s['actions'][0]['expected_version']=True
        self.assertEqual(model.run(s)['prefixes'][0]['result'],{'status':'invalid_expected_version'})
    def test_batch_oracle_detects_content_mutation(self):
        self.assertEqual(batch_oracle.check(self.spec,self.result)['status'],'PASS')
        self.result['prefixes'][-1]['layouts'][0]['queries'][0]['pages'][0]['rows'][0]['event_id']='WRONG'
        with self.assertRaises(AssertionError):batch_oracle.check(self.spec,self.result)
if __name__=='__main__':unittest.main(verbosity=2)
