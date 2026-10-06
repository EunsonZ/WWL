import collections
import itertools
import math
import random
import unittest
import sequential as s

class SequentialTests(unittest.TestCase):
    def test_timing_absolute_deadlines(self):
        for skew in (-1,0,1):
            x=s.timing(10,1,3,2,5,2,2,skew,.2,.1)
            # Independent absolute launch=100ns; capture=100+skew or 110+skew.
            latest=100+3+5;setup_deadline=110+skew-2-.2
            earliest=100+1+2;hold_deadline=100+skew+2+.1
            self.assertAlmostEqual(x.setup_slack_ns,setup_deadline-latest)
            self.assertAlmostEqual(x.hold_slack_ns,earliest-hold_deadline)
        self.assertEqual(s.timing(20,1,3,2,5,2,2,1).hold_slack_ns,0)
    def test_sample_and_window_boundaries(self):
        self.assertTrue(s.sample(False,[(7,True)],10,2,1))
        self.assertTrue(s.sample(False,[(8,True)],10,2,1))
        for t in (9,10,10.5):self.assertIsNone(s.sample(False,[(t,True)],10,2,1))
        self.assertFalse(s.sample(False,[(11,True)],10,2,1))
        self.assertTrue(s.sample(True,[(9,True),(10,True)],10,2,1))
    def test_latch_continuous_and_closed(self):
        out=s.latch(False,[(2,False,True),(3,True,True),(5,False,True),(7,True,True),(8,True,False),(10,False,False)])
        self.assertEqual([v for _,v in out],[False,True,False,True,True,True])
        self.assertTrue(s.sample(False,[(3,True),(5,False),(7,True),(10,False)],4,.5,.5))
        self.assertFalse(s.sample(False,[(3,True),(5,False),(7,True),(10,False)],12,.5,.5))
    def test_counter_all_small_words(self):
        for w in range(1,9):
            for q in range(1<<w):
                for e in (False,True):
                    word,carry=s.counter(q,w,e)
                    # Independent binary-string low-bit extraction, not modulo API expression.
                    bits=format(q+int(e),'b').zfill(w+1)
                    self.assertEqual(word,int(bits[-w:],2));self.assertEqual(carry,bits[-w-1]=='1')
        self.assertEqual(s.counter(7,3,True,2),(2,False))
    def test_pipeline_history(self):
        state=(None,None);history=[]
        for x in (10,20,30,40):
            old=state;state=s.pipeline(state,x);history.append(x)
            self.assertEqual(state[-1],history[-2] if len(history)>1 else None)
            self.assertEqual(state[-1],old[0])
        wrong=(40,40);self.assertNotEqual(wrong,state)
    def test_fsm_exhaustive_prefix_suffix(self):
        count=0
        for n in range(9):
            for bits in itertools.product((False,True),repeat=n):
                history='';a=b=0
                for x in bits:
                    a,ma0,ma1=s.detector(a,x,True)
                    b,mb0,mb1=s.detector(b,x,False)
                    history+=str(int(x));expected=history.endswith('101')
                    self.assertEqual(ma1,expected);self.assertEqual(mb0,expected)
                    self.assertFalse(mb1) # post-transition, with sampled input held
                count+=1
        self.assertEqual(count,511)
    def test_buffer_all_transition_words(self):
        for full,sv,mr,rst in itertools.product((False,True),repeat=4):
            for old,new in itertools.product(range(4),repeat=2):
                dut=s.Slot(2);dut.full=full;dut.data=old
                q=collections.deque([old] if full else [])
                if rst:q.clear()
                expected_valid=not rst and bool(q)
                expected_ready=not rst and (len(q)==0 or mr)
                popped=q.popleft() if expected_valid and mr else None
                if sv and expected_ready:q.append(new)
                e=dut.step(sv,new,mr,rst)
                self.assertEqual(e.valid,expected_valid);self.assertEqual(e.ready,expected_ready)
                if e.pop:self.assertEqual(e.data_before,popped)
                self.assertEqual(e.full_after,bool(q))
                if q:self.assertEqual(e.data_after,q[0])
    def test_buffer_exhaustive_finite_sequences(self):
        # Exactly 4096 length-4 traces, including adversarial invalid producer changes.
        # Checks DUT's accepted-item safety; not producer protocol certification.
        for flags in itertools.product(range(8),repeat=4):
            dut=s.Slot(2);q=collections.deque();accepted=[];delivered=[]
            for k,flag in enumerate(flags):
                sv,mr,rst=bool(flag&1),bool(flag&2),bool(flag&4)
                if rst:q.clear();accepted.clear();delivered.clear()
                valid=not rst and bool(q);ready=not rst and (not q or mr)
                popped=q.popleft() if valid and mr else None
                if sv and ready:q.append(k);accepted.append(k)
                if valid and mr:delivered.append(popped)
                e=dut.step(sv,k,mr,rst)
                self.assertEqual(e.pop,valid and mr);self.assertEqual(e.push,sv and ready)
                if e.pop:self.assertEqual(e.data_before,popped)
                self.assertEqual(e.full_after,bool(q));self.assertEqual(delivered,accepted[:len(delivered)])
                self.assertEqual(len(accepted)-len(delivered),len(q));self.assertLessEqual(len(q),1)
    def test_buffer_legal_producer_random(self):
        rng=random.Random(1606);dut=s.Slot();q=collections.deque();pending=None
        for k in range(1024):
            rst=k%97==0
            if rst:q.clear();pending=None
            if pending is None and rng.randrange(2):pending=rng.randrange(256)
            word=pending if pending is not None else 0;sv=pending is not None;mr=bool(rng.randrange(2))
            ready=not rst and (not q or mr);valid=not rst and bool(q)
            popped=q.popleft() if valid and mr else None
            if sv and ready:q.append(word)
            e=dut.step(sv,word,mr,rst)
            if e.pop:self.assertEqual(e.data_before,popped)
            if e.push:pending=None
            self.assertEqual(e.full_after,bool(q))
            if q:self.assertEqual(e.data_after,q[0])
    def test_buffer_no_fallthrough_replace_flush(self):
        b=s.Slot();e=b.step(True,161,True);self.assertTrue(e.push);self.assertFalse(e.pop)
        e=b.step(True,178,False);self.assertEqual(e.data_after,161)
        e=b.step(True,178,True);self.assertTrue(e.push and e.pop);self.assertEqual(e.data_before,161);self.assertEqual(e.data_after,178)
        e=b.step(True,200,True,True);self.assertFalse(e.push or e.pop or e.valid or e.ready);self.assertFalse(e.full_after)
    def test_sync_pulse_information(self):
        a=s.Synchronizer();self.assertEqual(a.step(True),(True,False));self.assertEqual(a.step(True),(True,True))
        sampled=[1<=t<4 for t in (0,10,20)]
        a=s.Synchronizer();self.assertEqual([a.step(v)[1] for v in sampled],[False]*3)
    def test_reset_two_edges(self):
        r=s.ResetRelease();self.assertFalse(r.edge(True));self.assertTrue(r.edge(True))
        r.assert_reset();self.assertFalse(r.second);self.assertFalse(r.edge(True));self.assertTrue(r.edge(True))
    def test_gray_adjacent_and_wrap(self):
        for w in range(1,9):
            values=[s.gray(i,w) for i in range(1<<w)]
            self.assertEqual(len(set(values)),1<<w)
            for a,b in zip(values,values[1:]+values[:1]):self.assertEqual((a^b).bit_count(),1)
        self.assertEqual(s.gray(3),2);self.assertEqual(s.gray(4),6)
    def test_handshake_one_transaction(self):
        rows,captures=s.handshake_trace();self.assertEqual(captures,[(15,42)])
        self.assertEqual(rows[-1]['source_phase'],'done')
        self.assertTrue(all(r['data']==42 for r in rows))
        self.assertEqual(sum(r['capture'] for r in rows),1)
    def test_log_probability_formula(self):
        log=s.log_mtbf(.5,.05,.01,1e8,1e6)
        # Independent direct finite-rate calculation for this narrow normal case.
        rate=.01e-9*1e8*1e6*math.exp(-.5/.05)
        self.assertAlmostEqual(log,math.log(1/rate))
        self.assertAlmostEqual(s.log_mtbf(.7,.05,.01,1e8,1e6)-log,4)
    def test_invalid_beforecast_budget(self):
        for bad in (True,1+0j,'1',[1],float('nan'),float('inf'),-1,1e200):
            with self.assertRaises(ValueError):s.timing(bad,1,3,2,5,2,2)
        for bad in (True,0,9,1.5):
            with self.assertRaises(ValueError):s.Slot(bad)
        with self.assertRaises(ValueError):s.bounded(itertools.repeat(1))
        with self.assertRaises(ValueError):s.timing(10,4,3,2,5,2,2)
        with self.assertRaises(ValueError):s.sample(False,[(2,True),(2,False)],10,2,1)
        with self.assertRaises(ValueError):s.detector(4,True)
        with self.assertRaises(ValueError):s.counter(8,3)
        with self.assertRaises(ValueError):s.log_mtbf(1,0,.01,1e8,1e6)
        with self.assertRaises(ValueError):s.Slot().step(1,0,True)

if __name__=='__main__':unittest.main()
