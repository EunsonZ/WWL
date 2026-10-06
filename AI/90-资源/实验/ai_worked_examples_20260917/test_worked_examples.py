"""Independent enumeration/closed-form checks and failure-boundary tests."""
import unittest
from fractions import Fraction as F
from itertools import product
from math import nan
import worked_examples as w


class SVMTests(unittest.TestCase):
    def test_optimality_certificate_and_kernel(self):
        c = w.svm_certificate()
        self.assertEqual(c['w'], (1., 0.))
        self.assertEqual(c['gram'], [[2,0,0,-2,2,-2],[0,2,-2,0,2,-2],[0,-2,2,0,-2,2],[-2,0,0,2,-2,2],[2,2,-2,-2,4,-4],[-2,-2,2,2,-4,4]])
        self.assertEqual(c['margins'], [1., 1., 1., 1., 2., 2.])
        self.assertEqual(c['equality'], 0.)
        self.assertEqual(c['complementary'], [0.]*6)
        self.assertEqual(c['primal'], .5)
        self.assertEqual(c['dual'], .5)
        for x in product((-2., -.5, 0., .5, 2.), repeat=2):
            self.assertEqual(w.kernel_score(x), x[0])
        # Four tight constraints imply w1 >= 1+|w2|+|b|, hence .5||w||²>=.5.
        for w1, w2, b in product((-.5, 0., .5, 1., 2.), repeat=3):
            feasible = all(y*(w1*x1+w2*x2+b) >= 1 for (x1, x2), y in zip(w.SVM_X, w.SVM_Y))
            if feasible:
                self.assertGreaterEqual(w1, 1+abs(w2)+abs(b))
                self.assertGreaterEqual(.5*(w1*w1+w2*w2), .5)

    def test_tight_does_not_imply_positive_alpha(self):
        c = w.svm_certificate((.5, 0., .5, 0., 0., 0.))
        self.assertEqual(c['primal'], c['dual'])
        self.assertEqual(c['equality'], 0.)
        self.assertEqual(c['complementary'], [0.]*6)
        self.assertEqual(c['margins'][1], 1.)

    def test_invalid_alpha_and_non_psd_similarity(self):
        for bad in ((-.1,)*6, (0.,)*5, (nan,)*6):
            with self.assertRaises(ValueError):
                w.svm_certificate(bad)
        # G=[[1,2],[2,1]]: z=(1,-1), zᵀGz=-2. Cannot be an inner-product Gram.
        self.assertEqual(1-2-2+1, -2)
        with self.assertRaises(ValueError):
            w.kernel_score((1.,))


class PGMTests(unittest.TestCase):
    def test_full_joint_and_two_orders_against_enumeration(self):
        joint = w.joint_table()
        self.assertEqual(len(joint), 16)
        self.assertEqual(sum(joint.values()), 1)
        for evidence in (0, 1):
            mass = sum(v for (a, b, c, d), v in joint.items() if c == evidence)
            numerator = sum(v for (a, b, c, d), v in joint.items() if c == evidence and d == 1)
            for order in (('A', 'B'), ('B', 'A')):
                result = w.eliminate(order, evidence)
                self.assertEqual(result['evidence'], mass)
                self.assertEqual(result['posterior'][(1,)], numerator/mass)
        self.assertEqual(w.eliminate()['posterior'][(1,)], F(147, 226))

    def test_intermediate_tables_and_cost(self):
        ab, ba = w.eliminate(), w.eliminate(('B', 'A'))
        self.assertEqual(ab['trace'][0]['message'].table, {(0,): F(14, 25), (1,): F(11, 25)})
        self.assertEqual(ba['trace'][0]['message'].scope, ('A', 'D'))
        self.assertEqual(ba['trace'][0]['message'].table,
                         {(0, 0): F(11, 100), (0, 1): F(15, 100), (1, 0): F(23, 100), (1, 1): F(51, 100)})
        self.assertEqual((ab['product_cells'], ab['peak_cells']), (8, 4))
        self.assertEqual((ba['product_cells'], ba['peak_cells']), (12, 8))
        with self.assertRaises(ValueError):
            w.eliminate(('A', 'A'))
        with self.assertRaises(ValueError):
            w.eliminate(evidence=2)


class CTCTests(unittest.TestCase):
    def test_published_tables_and_initialization(self):
        aa = w.ctc_forward(target='aa')
        self.assertEqual(aa['alpha'], [[F(1,5),F(3,5),0,0,0],
                         [F(1,10),F(4,25),F(3,10),0,0],
                         [F(1,50),F(13,100),F(23,250),F(3,20),0]])
        self.assertEqual(aa['probability'], F(3,20))
        aba = w.ctc_forward(target='aba')
        self.assertEqual(aba['alpha'][-1], [F(1,50),F(13,100),F(23,250),F(24,125),F(9,250),F(9,100),0])
        self.assertEqual(aba['probability'], F(9,100))

    def test_exhaustive_targets_against_path_oracle(self):
        for frames in range(5):
            probs = (w.CTC_PROBS*2)[:frames]
            total = F(0)
            for length in range(frames+1):
                for chars in product('ab', repeat=length):
                    target = ''.join(chars)
                    dp = w.ctc_forward(probs, target)['probability']
                    oracle = w.ctc_enumerate(probs, target)['probability']
                    self.assertEqual(dp, oracle, (frames, target))
                    total += dp
            self.assertEqual(total, 1)

    def test_repetition_empty_and_invalid_boundaries(self):
        self.assertEqual(w.ctc_forward(w.CTC_PROBS[:2], 'aa')['probability'], 0)
        self.assertEqual(w.ctc_enumerate(target='aa')['paths'], [(('a','_','a'), F(3,20))])
        self.assertEqual(w.ctc_forward([], '')['probability'], 1)
        self.assertEqual(w.ctc_forward([], 'a')['probability'], 0)
        for probs, target in ((((F(1),F(1),F(0)),), 'a'), (w.CTC_PROBS,'_'), (((nan,0,1),),'a')):
            with self.assertRaises(ValueError):
                w.ctc_forward(probs, target)


class DetectionTests(unittest.TestCase):
    def test_assignment_manual_six_options(self):
        result = w.assignment()
        self.assertEqual(result['chosen'], (1, 2))
        self.assertAlmostEqual(result['total'], 17/15)
        self.assertEqual(len(result['choices']), 6)
        # Independent six-case sum from the hand-computed matrix.
        manual = [31/105+7, 31/105+17/15, 0+34/5, 0+17/15, 39/5+34/5, 39/5+7]
        for got, expected in zip([v for v, _ in result['choices']], manual):
            self.assertAlmostEqual(got, expected)

    def test_tp_fp_and_fixed_protocol(self):
        r = w.detection_ap()
        self.assertEqual([row['tp'] for row in r['rows']], [1,0,1])
        self.assertEqual([row['fp'] for row in r['rows']], [0,1,0])
        self.assertEqual([row['precision'] for row in r['rows']], [1.,.5,2/3])
        self.assertEqual([row['recall'] for row in r['rows']], [.5,.5,1.])
        self.assertAlmostEqual(r['ap'], 5/6)
        self.assertAlmostEqual(w.detection_ap(threshold=.75)['ap'], .5)
        self.assertEqual(w.detection_ap(pred=(), scores=())['ap'], 0.)
        # Reordering confidence so FP comes last yields AP=1 despite one FP.
        self.assertEqual(w.detection_ap(scores=(.9,.6,.8))['ap'], 1.)

    def test_geometry_and_invalid_protocol(self):
        self.assertAlmostEqual(w.iou(w.GT[0],w.PRED[0]), 19/21)
        self.assertAlmostEqual(w.iou(w.GT[1],w.PRED[2]), 2/3)
        self.assertEqual(w.iou(w.GT[0],w.GT[1]), 0.)
        for b in ((0,0,0,1), (1,0,0,1), (0,0,nan,1)):
            with self.assertRaises(ValueError):
                w.iou(b, w.GT[0])
        for kw in ({'scores':(1.,)}, {'gt':()}, {'threshold':nan}, {'threshold':2.}):
            with self.assertRaises(ValueError):
                w.detection_ap(**kw)


class RLTests(unittest.TestCase):
    def test_fixed_environment_learning_trace(self):
        rows = w.mdp_learning()
        self.assertEqual([r['mc']['s0'] for r in rows], [.5,.75,.875,.6875,.34375,.171875])
        self.assertEqual([r['td']['s0'] for r in rows], [0.,.25,.5,.5,.6875,.5625])
        self.assertEqual([r['td']['s1'] for r in rows], [1.,1.5,1.75,1.75,.875,.4375])
        self.assertEqual([r['q'][('s0','go')] for r in rows], [0.,.25,.5,.5,.6875,.78125])
        self.assertEqual(rows[-1]['q'][('s0','quit')], .25)
        self.assertEqual(rows[-1]['q'][('s1','finish')], 1.75)
        self.assertEqual(rows[-1]['q'][('s1','quit')], 0.)
        # Full return oracle: enumerate both s0 choices and both subsequent choices.
        returns = [w.MDP[('s0','quit')][1]]
        for a in ('finish','quit'):
            returns.append(w.MDP[('s0','go')][1]+.5*w.MDP[('s1',a)][1])
        self.assertEqual(sorted(returns), [0.,.5,1.])
        self.assertEqual(max(returns), 1.)

    def test_terminal_and_external_truncation(self):
        self.assertEqual(w.bootstrap_target(0.,2.,True),0.)
        self.assertEqual(w.bootstrap_target(0.,2.,False,True),1.)
        self.assertEqual(w.bootstrap_target(0.,2.,True,True),0.)
        with self.assertRaises(ValueError):
            w.mdp_learning((('go',),))
        with self.assertRaises(ValueError):
            w.mdp_learning((('quit','go'),))
        with self.assertRaises(ValueError):
            w.mdp_learning(alpha=0)


if __name__ == '__main__':
    unittest.main()
