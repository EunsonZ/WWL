"""Relevant finite behavior checks. General Nash/learning guarantees are not inferred."""
import copy
from fractions import Fraction as F
import json
import os
from pathlib import Path
import unittest
import coordination_lab as lab


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(Path(__file__).with_name('inputs.json').read_text())
        cls.shared=lab.load_shared(os.environ.get('WWL_VAULT_ROOT',Path(__file__).resolve().parents[3]))

    def test_joint_and_absorbing(self):
        for s in ('success','failure'):
            for a in (0,1):
                for b in (0,1): self.assertEqual(lab.transition(s,a,b),(s,(0,0)))
        self.assertEqual(lab.transition('ready',0,0),('success',(2,2)))
        self.assertEqual(lab.transition('ready',1,1),('success',(1,1)))
        self.assertEqual(lab.transition('ready',0,1),('failure',(0,0)))

    def test_effective_and_deviations(self):
        self.assertEqual(lab.effective('4/5')['L']['expected_reward'],F(8,5))
        self.assertEqual(lab.effective('1/5')['R']['expected_reward'],F(4,5))
        m=lab.evaluate(F(1,3),F(1,3),self.shared)
        self.assertEqual(m['success'],F(5,9)); self.assertEqual(m['individual'],[F(2,3)]*2)
        self.assertEqual(m['unilateral_gain'],[0,0])
        self.assertEqual(lab.evaluate(0,0,self.shared)['team'],2)
        self.assertEqual(lab.evaluate(1,1,self.shared)['team'],4)
        self.assertEqual(lab.evaluate(1,0,self.shared)['unilateral_gain'],[1,2])

    def test_version_and_support(self):
        old,current=F(4,5),F(1,5)
        self.assertEqual(old*(current/old),current)
        self.assertEqual((1-old)*((1-current)/(1-old)),1-current)
        # An old pure L opponent has no R samples; weights cannot repair absent support.
        self.assertEqual(1-F(1),0)

    def test_actor_locality_and_tie(self):
        self.assertEqual(lab.policy([0,0],.1),.5)
        self.assertEqual(lab.policy([2,1],.1),.95)
        self.assertEqual(lab.policy([1,2],.1),.05)
        # There is no argument for partner current action/state/version in this actor API.
        import inspect
        self.assertEqual(list(inspect.signature(lab.policy).parameters),['q_values','epsilon'])

    def test_simultaneous_order(self):
        cfg=copy.deepcopy(self.cfg); cfg.update(episodes=1,window=1)
        rows=[]
        class Writer:
            def writerow(self,row): rows.append(row)
        out=lab.train(cfg,3,None,Writer())
        r=rows[0]; self.assertEqual(r[5:7],[.5,.5])
        self.assertEqual(r[3:5],[0,0])
        for i in range(2):
            expected=[0.,0.]; expected[r[7+i]]=.1*r[10+i]
            self.assertEqual(out['Q'][i],expected)
        self.assertEqual(out,lab.train(cfg,3,None))

    def test_reject(self):
        for key,value in [('episodes',0),('episodes',True),('window',7),('alpha',float('nan')),('epsilon',1),('seeds',[3,3]),('heldout_opponents',['4/5'])]:
            cfg=copy.deepcopy(self.cfg); cfg[key]=value
            with self.assertRaises(ValueError): lab.validate(cfg)
        cfg=copy.deepcopy(self.cfg); cfg['fixed_opponents']=[.8]; cfg['heldout_opponents']=['4/5']
        with self.assertRaises(ValueError): lab.validate(cfg)
        self.assertEqual(lab.probability(.8),F(4,5))
        for q in ('-1/10','11/10'):
            with self.assertRaises(ValueError): lab.effective(q)
        with self.assertRaises(ValueError): lab.policy([float('nan'),0],.1)
        with self.assertRaises(ValueError): lab.transition('unknown',0,0)


if __name__=='__main__': unittest.main()
