"""Behavior checks against explicit values and a separate true-state policy oracle."""
from fractions import Fraction as F
import unittest

from pomdp_lab import (Monitor, belief_update, bellman, information, oracle,
                       policies, same_mean_example)


class DecisionTests(unittest.TestCase):
    def test_published_one_signal_table(self):
        report = information(F(1, 10), Monitor(sense_cost=F(3)))
        self.assertEqual([row["posterior"] for row in report["branches"]], [F(8, 17), F(2, 83)])
        self.assertEqual([row["probability"] for row in report["branches"]], [F(17, 100), F(83, 100)])
        self.assertEqual((report["R0"], report["RS"], report["EVSI"], report["EVPI"]),
                         (F(10), F(27, 5), F(23, 5), F(8)))
        self.assertEqual(report["net_gain_if_bought"], F(8, 5))
        costly = information(F(1, 10), Monitor(sense_cost=F(6)))
        self.assertEqual(costly["net_gain_if_bought"], F(-7, 5))
        self.assertEqual(costly["optimal_risk_buy_or_not"], F(10))

    def test_cost60_has_information_but_no_one_signal_action_gain(self):
        report = information(F(1, 10), Monitor(prevention=F(60)))
        self.assertEqual([row["posterior"] for row in report["branches"]], [F(8, 17), F(2, 83)])
        self.assertEqual([row["actions"] for row in report["branches"]], [("skip",), ("skip",)])
        self.assertEqual((report["R0"], report["RS"], report["EVSI"], report["EVPI"]),
                         (F(10), F(10), F(0), F(4)))
        # Two signals can cross .6; zero EVSI is explicitly a one-signal claim.
        two_signal_model = Monitor(prevention=F(60), sense_cost=F(0))
        self.assertLess(oracle(F(1, 10), 3, two_signal_model)[0], F(10))

    def test_two_and_three_stage_exact_certificates(self):
        self.assertEqual(bellman(F(1, 10), 2), (F(-32, 5), ("sense",)))
        self.assertEqual(bellman(F(1, 10), 3), (F(-623, 100), ("sense",)))
        self.assertEqual(len(policies(1)), 2)
        self.assertEqual(len(policies(2)), 6)
        self.assertEqual(len(policies(3)), 38)
        self.assertIn(("sense", ("sense", "protect", "skip"), "skip"), oracle(F(1, 10), 3)[1])

    def test_second_measurement_threshold(self):
        self.assertEqual(bellman(F(8, 17), 2, Monitor(sense_cost=F(1)))[1], ("sense",))
        self.assertEqual(bellman(F(8, 17), 2, Monitor(sense_cost=F(2)))[1], ("protect", "sense"))
        self.assertEqual(bellman(F(8, 17), 2, Monitor(sense_cost=F(3)))[1], ("protect",))

    def test_perfect_uninformative_and_one_step_limits(self):
        perfect = Monitor(sensitivity=F(1), false_positive=F(0), sense_cost=F(0))
        self.assertEqual(oracle(F(1, 10), 2, perfect)[0], F(2))
        self.assertEqual(bellman(F(1, 10), 1, perfect), (F(-10), ("skip",)))
        uninformative = Monitor(sensitivity=F(1, 3), false_positive=F(1, 3), sense_cost=F(1))
        self.assertEqual(information(F(1, 10), uninformative)["EVSI"], F(0))
        self.assertEqual(bellman(F(1, 10), 3, uninformative)[1], ("skip",))
        self.assertEqual(bellman(F(0), 3, perfect)[0], F(0))
        self.assertEqual(bellman(F(1), 3, perfect)[0], F(-20))

    def test_independent_oracle_grid(self):
        for prior in (F(0), F(1, 10), F(1, 5), F(1, 2), F(1)):
            for h in (1, 2, 3):
                for c in (F(0), F(1), F(3), F(6)):
                    for k in (F(20), F(60)):
                        model = Monitor(sense_cost=c, prevention=k)
                        with self.subTest(prior=prior, h=h, c=c, k=k):
                            self.assertEqual(-bellman(prior, h, model)[0], oracle(prior, h, model)[0])

    def test_nonidentity_prediction_matches_joint_table(self):
        t = ((F(4, 5), F(1, 5)), (F(3, 10), F(7, 10)))
        o = ((F(1, 5), F(4, 5)), (F(9, 10), F(1, 10)))
        post, q = belief_update((F(3, 5), F(2, 5)), t, o, 0)
        # Independent four-cell joint: (.6*.8*.2, .6*.2*.9, .4*.3*.2, .4*.7*.9).
        masses = (F(12, 125), F(27, 250), F(3, 125), F(63, 250))
        self.assertEqual(q, sum(masses))
        self.assertEqual(post, (F(1, 4), F(3, 4)))
        self.assertEqual(sum(post), 1)

    def test_zero_probability_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "zero probability"):
            belief_update((F(1), F(0)), ((F(1), F(0)), (F(0), F(1))),
                          ((F(0), F(1)), (F(1), F(0))), 0)

    def test_invalid_inputs_do_not_manufacture_distributions(self):
        for probability in (F(-1, 10), F(11, 10), float("nan"), .1):
            with self.assertRaises(ValueError):
                bellman(probability, 2)
        with self.assertRaises(ValueError):
            belief_update((F(1, 2), F(1, 3)), ((F(1), F(0)), (F(0), F(1))),
                          ((F(1), F(0)), (F(0), F(1))), 0)
        for horizon in (0, 5, True):
            with self.assertRaises(ValueError):
                bellman(F(1, 10), horizon)

    def test_same_mean_requires_more_than_mean(self):
        result = same_mean_example()
        self.assertEqual(result["delta0"]["mean"], result["symmetric"]["mean"])
        self.assertEqual(result["delta0"]["risky_reward"], F(-1, 2))
        self.assertEqual(result["symmetric"]["risky_reward"], F(1, 2))
        self.assertEqual(result["delta0"]["best_action"], "safe")
        self.assertEqual(result["symmetric"]["best_action"], "risky")


if __name__ == "__main__":
    unittest.main()
