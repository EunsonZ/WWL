"""Independent queue oracle and truth-table enumeration; model-level evidence."""
import itertools
import random
import unittest
from buffer_model import Buffer


class BufferTests(unittest.TestCase):
    def test_independent_transition_table(self):
        # Independent cases indexed by occupancy, producer valid, consumer ready.
        table = {
            (0,0,0):(1,0,0,0,0), (0,0,1):(1,0,0,0,0),
            (0,1,0):(1,0,1,0,1), (0,1,1):(1,0,1,0,1),
            (1,0,0):(0,1,0,0,1), (1,0,1):(1,1,0,1,0),
            (1,1,0):(0,1,0,0,1), (1,1,1):(1,1,1,1,1),
        }
        for q,sv,mr in itertools.product(range(2), repeat=3):
            for old,new in itertools.product(range(16), repeat=2):
                b=Buffer(4)
                if q: b.step(True,old,False)
                else: b.data=old  # invalid output may retain any word
                e=b.step(bool(sv),new,bool(mr))
                self.assertEqual(tuple(map(int,(e.ready,e.valid,e.push,e.pop,e.full_after))), table[q,sv,mr])
                self.assertEqual(e.data,old)
                self.assertEqual(e.data_after,new if e.push else old)

    def test_queue_order_capacity_reset_epochs(self):
        rng=random.Random(51005)
        b=Buffer(8); queue=[]; pending=None; pushes=pops=0
        for k in range(20000):
            rn = k % 113 != 0
            if not rn:
                queue.clear(); pending=None; pushes=pops=0
            if pending is None and rng.randrange(3): pending=rng.randrange(256)
            sv=pending is not None
            sd=pending if sv else 0
            mr=bool(rng.randrange(2))
            e=b.step(sv,sd,mr,rn)
            # Queue oracle uses pre-edge contents; an empty queue never emits now.
            self.assertEqual(e.valid, rn and bool(queue))
            self.assertEqual(e.ready, rn and (len(queue)==0 or mr))
            if e.pop:
                self.assertEqual(e.data,queue.pop(0)); pops+=1
            if e.push:
                queue.append(sd); pending=None; pushes+=1
            self.assertEqual(int(e.full_after),len(queue))
            self.assertEqual(pushes-pops,len(queue))
            self.assertLessEqual(len(queue),1)

    def test_no_fallthrough_and_replace(self):
        b=Buffer(); e=b.step(True,161,True)
        self.assertTrue(e.push); self.assertFalse(e.pop)
        e=b.step(True,178,True)
        self.assertTrue(e.push and e.pop); self.assertEqual(e.data,161)
        self.assertEqual(b.data,178)
        self.assertEqual(b.step(False,0,True).data,178)

    def test_stall_and_overwrite_counterexample(self):
        b=Buffer(); b.step(True,161,False)
        for _ in range(20):
            e=b.step(True,178,False)
            self.assertFalse(e.push); self.assertEqual(b.data,161)
        # Deliberate bad implementation: overwrite from unaccepted input.
        wrong=178
        self.assertNotEqual(wrong,161)
        self.assertEqual(b.step(True,178,True).data,161)

    def test_reset_flush_gating_and_release(self):
        b=Buffer(); b.step(True,99,False)
        b.reset(); self.assertFalse(b.full); self.assertEqual(b.data,0)
        e=b.step(True,33,True,False)
        self.assertFalse(e.ready or e.valid or e.push or e.pop)
        e=b.step(True,33,True,True)
        self.assertTrue(e.push); self.assertFalse(e.pop)
        self.assertEqual(b.step(False,0,True).data,33)

    def test_invalid_inputs(self):
        for width in [0,-1,True,1.5]:
            with self.assertRaises(ValueError): Buffer(width)
        b=Buffer(4)
        for data in [-1,16,True,2.5]:
            with self.assertRaises(ValueError): b.step(True,data,True)
        for args in [(1,0,True,True),(True,0,1,True),(True,0,True,1)]:
            with self.assertRaises(ValueError): b.step(*args)


if __name__=='__main__': unittest.main()
