import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import graph_model as model
import batch_oracle
import sqlite_probe

HERE=Path(__file__).parent
class Behavior(unittest.TestCase):
    def setUp(self): self.spec=json.loads((HERE/'spec.json').read_text())
    def test_full_content_and_access_counts(self):
        result=model.run(self.spec)
        self.assertEqual(batch_oracle.check(self.spec,result)['queries_checked'],135)
    def test_parallel_identity_and_target_revisit(self):
        result=model.run(self.spec)
        def row(v,q): return next(x for x in next(x for x in result['variants'] if x['variant']==v)['queries'] if x['query_id']==q)
        self.assertEqual(row('parallel','a_c_1_5_walk')['bounded']['path_count'],6)
        self.assertEqual(row('parallel','a_c_1_5_trail')['bounded']['path_count'],4)
        self.assertEqual(row('parallel','a_c_1_5_simple')['bounded']['path_count'],2)
        self.assertEqual(row('parallel','a_a_1_4_walk')['bounded']['path_count'],6)
        self.assertEqual(len(row('parallel','a_c_1_1_walk')['unbounded_bfs']['paths']),2)
    def test_zero_unreachable_and_direction(self):
        r=model.run(self.spec)['variants'][0]['queries']
        zero=next(x for x in r if x['query_id']=='a_a_0_0_simple')
        self.assertEqual(zero['bounded']['paths'],[{'node_ids':['a'],'edge_ids':[]}])
        for key in ('a_z_0_5_walk','c_a_0_5_walk'):
            self.assertFalse(next(x for x in r if x['query_id']==key)['unbounded_bfs']['reachable'])
    def test_type_and_label_filters_before_shortest(self):
        a=model.run(self.spec)
        branching=a['variants'][2]; typed=a['variants'][3]
        for x,y in zip(branching['queries'],typed['queries']):
            self.assertEqual(x['bounded'],y['bounded']); self.assertEqual(x['unbounded_bfs'],y['unbounded_bfs'])
        spec=copy.deepcopy(self.spec)
        spec['nodes'][1]['label']='Teacher'
        batch_oracle.check(spec,model.run(spec))
    def test_invalid_identity_and_endpoint(self):
        for change,reason in [(lambda s:s['nodes'].append(s['nodes'][0]),'node_identity'),
                              (lambda s:s['edges'].append(s['edges'][0]),'edge_identity'),
                              (lambda s:s['edges'][0].update(dst='absent'),'dangling_endpoint'),
                              (lambda s:s['queries'][0].update(max_hops=6),'query_length')]:
            s=copy.deepcopy(self.spec); change(s)
            with self.assertRaisesRegex(ValueError,reason): model.run(s)
    def test_real_constraint_transaction_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            r=sqlite_probe.run(self.spec,Path(d)/'graph.sqlite')
            self.assertEqual(len(r['failures']),5)
            self.assertEqual(r['integrity']['parallel_ids'],['e1','e4'])
            self.assertFalse(r['snapshot']['path_in_either_snapshot'])
            self.assertEqual(r['snapshot']['pinned_before'],r['snapshot']['pinned_after_writer_commit'])
    def test_cli_and_mutated_answer_detected(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'result.json'
            p=subprocess.run([sys.executable,str(HERE/'graph_model.py'),'--spec',str(HERE/'spec.json'),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            result=json.loads(out.read_text()); batch_oracle.check(self.spec,result)
            result['variants'][0]['queries'][0]['unbounded_bfs']['distance']=999
            with self.assertRaises(AssertionError): batch_oracle.check(self.spec,result)
if __name__=='__main__': unittest.main(verbosity=2)
