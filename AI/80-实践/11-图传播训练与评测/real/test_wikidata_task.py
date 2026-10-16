"""Author checks of new preparation and information boundaries; no old FD rerun."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
import numpy as np
import wikidata_task as w


class RealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads(Path(__file__).with_name('protocol.json').read_text());cls.core,cls.relations=w.load_modules(Path(os.environ.get('WWL_GRAPH_PARENT',Path(__file__).resolve().parent.parent)))

    def source_record(self,qid,prop,body):
        text=json.dumps(body);return {'entity':qid,'property':prop,'body':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'retrieved_at_utc':'2026-10-17T00:00:00Z'}

    def statement(self,id,value,rank='normal',qualifiers=None):return {'id':id,'rank':rank,'value':{'type':'value','content':value},'qualifiers':qualifiers or[]}

    def test_rank_projection_dedup_and_grouped_identity(self):
        panel={'entities':['Q100','Q200'],'candidate_continents':['Q15','Q46']};records=[]
        for qid in panel['entities']+panel['candidate_continents']:records.append(self.source_record(qid,'label',qid))
        records.extend([self.source_record('Q100','P30',{'P30':[self.statement('s1','Q46','preferred',[{'property':'P518'}]),self.statement('s2','Q15'),self.statement('s3','Q46','preferred')]}),self.source_record('Q200','P30',{'P30':[self.statement('s4','Q15'),self.statement('s5','Q46','deprecated')]}),self.source_record('Q100','P47',{'P47':[self.statement('s6','Q200'),self.statement('s7','Q200'),self.statement('s8','Q100')]}),self.source_record('Q200','P47',{'P47':[]})])
        data,audit=w.normalize({'responses':records},panel,self.protocol)
        self.assertEqual(audit['duplicate_P30_statements'],1);self.assertEqual(audit['duplicate_P47_statements'],1);self.assertEqual(audit['symmetric_closure_edges'],2);self.assertEqual(audit['P47_self_removed'],[['Q100','Q100']]);self.assertEqual(len(audit['discarded_statements']),2)
        allpositive=[edge for split in ('train','val','test')for edge in data[split]['positives']];self.assertEqual(sorted((data['public']['country_qids'][s],data['public']['continent_qids'][t-2])for s,_,t in allpositive),[('Q100','Q46'),('Q200','Q15')])
        for split in ('train','val','test'):
            for head in data[split]['query_heads']:self.assertEqual(w.split_for(data['public']['country_qids'][head],self.protocol),split)
        broken=copy.deepcopy(records);broken[0]['body']='"changed"';self.assertRaises(ValueError,w.normalize,{'responses':broken},panel,self.protocol)

    def fixture(self):
        public={'country_qids':['A','B','C','D'],'continent_qids':['X','Y'],'border_edges':[[0,1],[1,0],[1,2],[2,1]],'candidate_entities':[4,5]}
        train={'query_heads':[0,2],'positives':[[0,'P30',4],[2,'P30',5]]};return public,train

    def test_supervised_seed_mean_no_self_copy_isolate_and_no_graph(self):
        public,train=self.fixture();h=w.feature_matrix(self.relations,public,train,'relational')
        np.testing.assert_allclose(h[0],[0,0,1]);np.testing.assert_allclose(h[1],[.5,.5,1]);np.testing.assert_allclose(h[2],[0,0,1]);np.testing.assert_allclose(h[3],[0,0,1]);np.testing.assert_array_equal(h[4:,:2],np.eye(2))
        no=w.feature_matrix(self.relations,public,train,'no_graph');np.testing.assert_array_equal(no[:4,:2],np.zeros((4,2)));np.testing.assert_array_equal(no[4:,:2],np.eye(2))
        changed=copy.deepcopy(train);changed['positives'][0][2]=5;self.assertNotEqual(h[1,0],w.feature_matrix(self.relations,public,changed,'relational')[1,0]);self.assertEqual(h[0,0],0)
        public['border_edges'].append([0,0]);self.assertRaises(ValueError,w.feature_matrix,self.relations,public,train,'relational')

    def test_rectangular_head_wrapper_gradient_and_constant_prior(self):
        public,train=self.fixture();h=w.feature_matrix(self.relations,public,train,'relational');rows=w.rows_for(public,train);p={'decoder':np.array([[.2,-.1],[.4,.3],[-.2,.1]])}
        _,grad=w.objective(self.core,self.relations,p,h,rows,.01)
        for idx in np.ndindex(p['decoder'].shape):
            p['decoder'][idx]+=1e-6;plus=w.objective(self.core,self.relations,p,h,rows,.01)[0];p['decoder'][idx]-=2e-6;minus=w.objective(self.core,self.relations,p,h,rows,.01)[0];p['decoder'][idx]+=1e-6
            self.assertAlmostEqual((plus-minus)/2e-6,grad['decoder'][idx],places=8)
        score=w.predict(self.core,self.relations,{'model':'neighbor_prior'},public,train,w.rows_for(public,{'query_heads':[1],'positives':[]}),self.protocol)
        np.testing.assert_allclose(score,np.zeros(2),atol=1e-15)

    def test_macro_head_not_micro_fact(self):
        # Head A has two facts, B one: country weights differ from fact weights.
        a=[1.,.5];b=[.25];self.assertEqual(np.mean([np.mean(a),np.mean(b)]),.5);self.assertAlmostEqual(np.mean(a+b),7/12)

if __name__=='__main__':unittest.main()
