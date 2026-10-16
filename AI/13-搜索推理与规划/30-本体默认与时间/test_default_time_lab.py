"""Focused regression contracts; these do not replace the general semantic proofs."""
from pathlib import Path
import copy
import json
import unittest
import default_time_lab as lab

SPEC=json.loads((Path(__file__).resolve().parent/"inputs/default-time.json").read_text())
CASES={c["name"]:c for c in SPEC["default_cases"]}


class DefaultTimeChecks(unittest.TestCase):
    def test_retraction_is_not_old_extension_union(self):
        before=lab.analyze(CASES["bird_before"]); after=lab.analyze(CASES["bird_after_penguin"])
        self.assertTrue(before["queries"]["Fly"]["skeptical"])
        self.assertTrue(before["queries"]["!Penguin"]["skeptical"])
        self.assertFalse(after["queries"]["Fly"]["credulous"])
        self.assertTrue(after["queries"]["!Fly"]["skeptical"])
        self.assertFalse(after["queries"]["!Penguin"]["credulous"])
        self.assertEqual((before["extension_count"],after["extension_count"]),(1,1))
        self.assertEqual(lab.bayes_comparison()["posterior_F"],"2/5")

    def test_multiple_extensions_and_no_automatic_specificity(self):
        for name,query in (("two_groups","Approve"),("exception_also_default","Fly")):
            out=lab.analyze(CASES[name])
            self.assertEqual(out["extension_count"],2)
            self.assertFalse(out["queries"][query]["skeptical"])
            self.assertTrue(out["queries"][query]["credulous"])
            self.assertTrue(out["queries"][lab.negate(query)]["credulous"])
            self.assertTrue(all(not e["inconsistent"] for e in out["extensions"]))

    def test_absence_inconsistency_and_no_extension_are_different(self):
        cycle=lab.analyze(CASES["unsupported_cycle"])
        self.assertEqual(cycle["extension_count"],1)
        self.assertEqual(cycle["extensions"][0]["entailed_literals"],[])
        none=lab.analyze(CASES["no_extension"])
        self.assertEqual(none["status"],"no_extension")
        self.assertNotIn("skeptical",none["queries"]["p"])
        bad=lab.analyze(CASES["hard_inconsistent"])
        self.assertEqual(bad["extension_count"],1)  # the formal inconsistent extension
        self.assertTrue(bad["extensions"][0]["inconsistent"])
        self.assertNotIn("skeptical",bad["queries"]["p"])
        cnf=lab.analyze(CASES["classical_precondition"])
        self.assertTrue(cnf["queries"]["r"]["skeptical"])

    def test_temporal_progression_and_inertia(self):
        out=lab.time_run(SPEC["time"])
        self.assertEqual(out["states"],[["AtA","HandEmpty","PkgA"],["AtA","Holding"],
                                          ["AtB","Holding"],["AtB","HandEmpty","PkgB"]])
        self.assertEqual(out["ssa_strips_comparison_count"],88)
        self.assertTrue(out["goal_satisfied"])
        self.assertEqual(out["effects_only_after_MoveAB"]["model_count"],16)
        self.assertEqual(out["effects_only_after_MoveAB"]["valid_delivery_model_count"],3)
        self.assertFalse(out["omitted_event"]["match"])
        empty=copy.deepcopy(SPEC["time"]); empty["sequence"]=[]
        self.assertFalse(lab.time_run(empty)["goal_satisfied"])

    def test_observing_filters_worlds_does_not_move_package(self):
        out=lab.time_run(SPEC["time"]); b=out["belief_example"]
        self.assertEqual([len(b[k]) for k in ("before","after_AtB","after_Holding","after_Drop")],[6,3,1,1])
        self.assertEqual(b["actual_before_observations"],b["actual_after_observations"])
        self.assertNotEqual(b["actual_after_observations"],b["actual_after_Drop"])
        self.assertIn("every possible world",out["failures"]["drop_before_holding_observation"])
        self.assertIn("conflicts",out["failures"]["conflicting_observation"])

    def test_declared_language_and_empty_belief_guards(self):
        bad=copy.deepcopy(CASES["bird_before"]); bad["defaults"][0]["just"]="!Unknown"
        with self.assertRaises(ValueError): lab.analyze(bad)
        bad=copy.deepcopy(CASES["bird_before"]); bad["atoms"]=list("abcdefghi")
        with self.assertRaises(ValueError): lab.analyze(bad)
        _,actions,_,atoms,table=lab.temporal_domain()
        with self.assertRaises(ValueError): lab.observe(set(),"AtA",True,atoms)
        with self.assertRaises(ValueError): lab.act_belief(set(),actions[0],atoms,table)
        with self.assertRaises(ValueError): lab.ssa_step(frozenset({"Unknown"}),actions[0],atoms,table)

if __name__=="__main__": unittest.main()
