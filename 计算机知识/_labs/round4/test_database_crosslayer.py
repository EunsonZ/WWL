import math,sqlite3,unittest
from database_models import closure,keys,projection,Outbox,InjectedFailure,KeyConflict

class DatabaseTests(unittest.TestCase):
    def setUp(self):self.fds=[(set('AB'),'C'),(set('C'),'B'),(set('A'),'D'),(set('D'),'E')]
    def test_closure_keys_and_minimal_cover(self):
        f=self.fds;self.assertEqual(closure({'A'},f),set('ADE'));self.assertEqual(keys(set('ABCDE'),f),[set('AB'),set('AC')])
        for i,(left,right) in enumerate(f):
            self.assertNotIn(right,closure(left,f[:i]+f[i+1:]))
            for attr in left:self.assertNotIn(right,closure(left-{attr},f))
    def test_lossless_steps_and_dependency_preservation(self):
        for r1,r2 in [('DE','ABCD'),('AD','ABC'),('CB','AC')]:
            common=set(r1)&set(r2);c=closure(common,self.fds);self.assertTrue(set(r1)<=c or set(r2)<=c)
        bcnf=sum([projection(set(s),self.fds) for s in ['DE','AD','CB','AC']],[])
        self.assertEqual(closure(set('AB'),bcnf),set('ABDE'))
        third=sum([projection(set(s),self.fds) for s in ['ABC','AD','DE']],[])
        for left,right in self.fds:self.assertIn(right,closure(left,third))
        for schema in ['DE','AD','CB','AC']:
            p=projection(set(schema),self.fds)
            for left,_ in p:self.assertTrue(set(schema)<=closure(left,p))
    def test_spurious_join(self):
        relation={('a1','b1','c1'),('a2','b1','c2')};ab={(a,b) for a,b,c in relation};bc={(b,c) for a,b,c in relation}
        join={(a,b,c) for a,b in ab for b2,c in bc if b==b2};self.assertEqual(len(join),4);self.assertEqual(len(join-relation),2)
    def test_snapshot_write_skew_model_and_guard(self):
        state={'Alice':True,'Bob':True};sa=dict(state);sb=dict(state)
        if sum(sa.values())>=2:state['Alice']=False
        if sum(sb.values())>=2:state['Bob']=False
        self.assertEqual(sum(state.values()),0)
        state={'Alice':True,'Bob':True}
        for name in ['Alice','Bob']:
            if sum(state.values())>=2:state[name]=False
        self.assertEqual(sum(state.values()),1)
    def test_sql_null_outer_join_and_count(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript('CREATE TABLE a(id INTEGER PRIMARY KEY);CREATE TABLE b(id INTEGER PRIMARY KEY,aid INTEGER,active INTEGER);INSERT INTO a VALUES(1),(2);INSERT INTO b VALUES(9,1,1),(10,1,0);')
            self.assertEqual(db.execute('SELECT a.id,b.id FROM a LEFT JOIN b ON a.id=b.aid AND b.active=1 ORDER BY a.id').fetchall(),[(1,9),(2,None)])
            self.assertEqual(db.execute('SELECT a.id,b.id FROM a LEFT JOIN b ON a.id=b.aid WHERE b.active=1').fetchall(),[(1,9)])
            self.assertEqual(db.execute('SELECT COUNT(*),COUNT(b.id) FROM a LEFT JOIN b ON a.id=b.aid AND b.active=1').fetchone(),(2,1))
            self.assertEqual(db.execute('SELECT 3 NOT IN (1,NULL)').fetchone(),(None,))
    def test_cardinality_and_pages_model(self):
        self.assertEqual(100000*50000/max(1000,500),5000000);self.assertEqual(1000000*.01*.01,100)
        pages=10000*(1-(1-1/10000)**10000);self.assertAlmostEqual(pages,6321.3895356703,6)
    def test_redo_undo_toy_not_postgresql(self):
        log=[('T1','A',0,10),('T1','B',0,20),('T2','A',10,99)];committed={'T1'};disk={'A':99,'B':0}
        def recover(image):
            image=dict(image)
            for tx,key,before,after in log:image[key]=after
            for tx,key,before,after in reversed(log):
                if tx not in committed:image[key]=before
            return image
        self.assertEqual(recover(disk),{'A':10,'B':20});self.assertEqual(recover(recover(disk)),recover(disk))
        page={'lsn':0,'value':0}
        for _ in range(2):
            if page['lsn']<7:page={'lsn':7,'value':10}
        self.assertEqual(page,{'lsn':7,'value':10})

class OutboxTests(unittest.TestCase):
    def setUp(self):self.store=Outbox()
    def tearDown(self):self.store.close()
    def count(self,table):return self.store.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    def test_same_intent_replay_and_scope(self):
        for principal, key, cents in [(None,'k',1),('u',None,1),('','k',1),('u','',1),('u','k',True),('u','k',-1),('u','k',2**63)]:
            with self.subTest(principal=principal, key=key, cents=cents):
                with self.assertRaises(ValueError):self.store.create(principal,key,cents)
        self.assertEqual(self.count('orders'),0)
        a=self.store.create('u1','k',100);self.assertEqual(self.store.create('u1','k',100),a);self.assertEqual(self.count('orders'),1)
        with self.assertRaises(KeyConflict):self.store.create('u1','k',200)
        b=self.store.create('u2','k',100);self.assertNotEqual(a,b);self.assertEqual(self.count('orders'),2)
    def test_crash_before_commit_rolls_back_all(self):
        with self.assertRaises(InjectedFailure):self.store.create('u','x',1,'after-business')
        for table in ['orders','requests','outbox']:self.assertEqual(self.count(table),0)
        self.store.create('u','x',1);self.assertEqual(self.count('orders'),1)
    def test_lost_response_and_publish_duplicate(self):
        with self.assertRaises(InjectedFailure):self.store.create('u','x',1,'lost-response')
        self.store.create('u','x',1);self.assertEqual(self.count('orders'),1);wire=[]
        with self.assertRaises(InjectedFailure):self.store.publish(wire,'after-send')
        self.store.publish(wire);self.assertEqual(len(wire),2);self.assertEqual(wire[0],wire[1])
        for message in wire:self.store.consume(message)
        self.assertEqual(self.count('effects'),1)
    def test_consumer_mark_and_effect_same_transaction(self):
        self.store.create('u','x',1);wire=[];self.store.publish(wire)
        with self.assertRaises(InjectedFailure):self.store.consume(wire[0],'after-mark')
        self.assertEqual(self.count('processed'),0);self.assertEqual(self.count('effects'),0)
        self.store.consume(wire[0]);self.assertEqual(self.count('effects'),1)
    def test_fencing_requires_resource_check(self):
        current=7;value='new'
        def accept(token,text):
            nonlocal current,value
            if token<current:return False
            current,value=token,text;return True
        self.assertFalse(accept(6,'stale'));self.assertEqual(value,'new');self.assertTrue(accept(8,'next'))

class PerformanceTests(unittest.TestCase):
    def test_queue_and_amdahl_models(self):
        self.assertAlmostEqual(1/(.2+.8/4),2.5);self.assertEqual(200*.05,10)
        for lam,mean,p99 in [(50,.02,.09210340371976),(90,.1,.4605170185988)]:
            self.assertAlmostEqual(1/(100-lam),mean);self.assertAlmostEqual(-math.log(.01)/(100-lam),p99)
        self.assertAlmostEqual(.99**100,.3660323412732292)
    def test_percentiles_do_not_add(self):
        def p99(xs):return sorted(xs)[math.ceil(.99*len(xs))-1]
        x=[0]*98+[100,0];y=[0]*98+[0,100];z=[a+b for a,b in zip(x,y)]
        self.assertEqual(p99(x)+p99(y),0);self.assertEqual(p99(z),100)

if __name__=='__main__':unittest.main(verbosity=2)
