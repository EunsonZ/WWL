import copy
import inspect
import json
import math
from pathlib import Path
import unittest
import signaling_lab as lab


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.cfg=json.loads(Path(__file__).with_name('inputs.json').read_text())

    def test_information_and_no_message_deviation(self):
        theta=[-2.,2.,-.4,.8]
        # Force two actual trajectories to x=0/1 but the same received y=0.
        # An accidental step(...receiver_probability(theta,x)) would fail this check.
        class ConstantStream:
            def __init__(self,value):self.value=value
            def random(self):return self.value
        actual=[]
        class Writer:
            def writerow(self,row):actual.append(dict(zip(lab.HEADER,row)))
        for value in (.9,.1):
            t=lab.Trainer(self.cfg,3,'ctde',Writer(),theta)
            t.rng[1]=ConstantStream(value) # x=0 then x=1
            t.rng[2]=ConstantStream(.99) # m=0 in both x states
            t.rng[3]=ConstantStream(.99) # no channel flip
            t.step()
        self.assertEqual([r['x'] for r in actual],[0,1])
        self.assertEqual([r['y'] for r in actual],[0,0])
        self.assertEqual(actual[0]['p_a1'],actual[1]['p_a1'])
        self.assertEqual(list(inspect.signature(lab.receiver_probability).parameters),['theta','received'])
        score=lab.evaluate(theta,.1,no_comm=True)
        self.assertAlmostEqual(score['success'],.5,places=14)
        self.assertTrue(all(abs(g)<1e-14 for g in score['unilateral_gain']))
        # Giving a y-dependent deviation to a receiver who gets no y is an illegal test.
        full=lab.evaluate_probabilities(*lab.probabilities(theta,True),.1)
        self.assertGreater(full['unilateral_gain'][1],.2)
        with self.assertRaises(ValueError):lab.evaluate_probabilities([.05,.95],[.2,.8],.1,True)

    def test_sixteen_events_and_closed_form(self):
        p,d=[.2,.8],[.3,.7]; eta=.1
        rows=list(lab.events(p,d,eta)); self.assertEqual(len(rows),16)
        self.assertAlmostEqual(sum(r['weight'] for r in rows),1)
        self.assertAlmostEqual(lab.evaluate_probabilities(p,d,eta)['success'],.5+.5*(1-2*eta)*(p[1]-p[0])*(d[1]-d[0]))
        self.assertAlmostEqual(lab.evaluate_probabilities([0,1],[0,1],eta)['success'],.9)
        self.assertAlmostEqual(lab.evaluate_probabilities([0,1],[1,0],eta)['success'],.1)
        self.assertAlmostEqual(lab.evaluate_probabilities([0,1],[0,1],.5)['success'],.5)

    def test_old_baseline_and_critic_order(self):
        rows=[]
        class Writer:
            def writerow(self,row):rows.append(dict(zip(lab.HEADER,row)))
        t=lab.Trainer(self.cfg,3,'ctde',Writer());old=list(t.theta);t.step()
        r=rows[0]
        self.assertEqual([r['b_sender_old'],r['b_receiver_old'],r['critic_version']],[0,0,0])
        self.assertEqual(sum(t.count),1)
        self.assertEqual(t.critic[4*r['x']+2*r['y']+r['a']],r['r'])
        grad=[0.]*4;grad[r['x']]=(r['m']-r['p_m1'])*r['r'];grad[2+r['y']]=(r['a']-r['p_a1'])*r['r']
        self.assertEqual(t.theta,[v+self.cfg['actor_step']*g for v,g in zip(old,grad)])

    def test_sender_counterfactual_and_score_identity(self):
        th=list(map(lab.logit,[.2,.8,.3,.7]));q=[float(a==x) for x in (0,1) for y in (0,1) for a in (0,1)]
        b0=lab.baselines(q,th,0,0,.1)[0];b1=lab.baselines(q,th,0,1,.1)[0]
        self.assertEqual(b0,b1) # Actual sampled y must not change sender baseline.
        for critic in (q,[.1,.9,.8,.2,.4,.6,.3,.7]):
            result=lab.gradient_moments(th,.1,critic)
            for a,b in zip(result['raw']['mean'],result['central']['mean']):self.assertAlmostEqual(a,b,places=14)
        # Finite-difference actual objective independently checks its four logit derivatives.
        mom=lab.gradient_moments(th,.1,q)['raw']['mean']
        for j in range(4):
            plus=th.copy();minus=th.copy();plus[j]+=1e-5;minus[j]-=1e-5
            fd=(lab.evaluate(plus,.1)['success']-lab.evaluate(minus,.1)['success'])/2e-5
            self.assertAlmostEqual(fd,mom[j],places=10)

    def test_archives_and_role_budget(self):
        cfg=copy.deepcopy(self.cfg);cfg.update(role_updates=4,checkpoint_every=2)
        t=lab.Trainer(cfg,3,'snapshot');r=t.train()
        self.assertEqual(r['total_environment_episodes'],8);self.assertEqual(r['role_updates'],[4,4])
        self.assertEqual(r['archive_size'],3)
        self.assertEqual(r['checkpoints'][0]['theta'],t.archive[0])
        self.assertEqual(r['checkpoints'][1]['theta'],t.archive[1])

    def test_reject_and_box(self):
        for key,value in [('role_updates',0),('eta',.6),('actor_step',float('nan')),('logit_bound',40),('logit_bound',1),('initial_range',7),('seeds',[3,3]),('modes',['unknown']),('checkpoint_every',7),('adapt_checkpoints',[1,400]),('adapt_checkpoints',[])]:
            cfg=copy.deepcopy(self.cfg);cfg[key]=value
            with self.assertRaises(ValueError):lab.validate(cfg)
        for value in (2,True,'1'):
            with self.assertRaises(ValueError):lab.receiver_probability([0,0],value)
        cfg=copy.deepcopy(self.cfg);cfg['actor_step']=1e5
        t=lab.Trainer(cfg,3,'independent')
        for _ in range(20):t.step()
        self.assertTrue(all(abs(z)<=cfg['logit_bound'] for z in t.theta))


if __name__=='__main__':unittest.main()
