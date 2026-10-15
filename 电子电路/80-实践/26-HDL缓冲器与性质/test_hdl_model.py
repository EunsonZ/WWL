import unittest
from hdl_model import State,step,directed,random_check,enumerate_transitions,arithmetic

class TestFiniteContract(unittest.TestCase):
 def test_directed_old_before_new(self):
  r=directed();self.assertIsNone(r['failure_cycle'])
  self.assertEqual([x['data'] for x in r['rows'] if x['pop']],[0xA1,0xB2])
  self.assertEqual(r['rows'][0]['valid'],0)
  self.assertEqual(r['rows'][3]['after_data'],0xB2)
 def test_mutation_has_short_counterexample(self):
  r=directed(True);self.assertEqual(r['failure_cycle'],2)
  self.assertEqual(r['rows'][-1]['expected_head'],0xA1)
  self.assertEqual(r['rows'][-1]['after_data'],0xB2)
 def test_reset_cancels(self):
  s,p=step(State(1,3),width=2,rst_n=0,sv=1,data=2,mr=1)
  self.assertEqual(s,State());self.assertEqual((p['push'],p['pop'],p['ready'],p['valid']),(0,0,0,0))
 def test_history_random_and_coverage(self):
  for width in (1,2,4,8):
   c=random_check(width=width,count=1000)
   self.assertTrue(all(c[x]>0 for x in c))
 def test_independent_finite_graph(self):
  r=enumerate_transitions();self.assertEqual(r['reachable_pairs'],8);self.assertEqual(r['edges'],256)
 def test_budget_has_failure_exit(self):
  with self.assertRaises(RuntimeError):enumerate_transitions(budget=1)
 def test_width_sign_cases(self):
  self.assertEqual(arithmetic(7,3,width=4),{'word':10,'carry':0,'signed_sum':10,'signed_word':-6,'signed_overflow':True})
  self.assertEqual(arithmetic(15,1,width=4)['carry'],1)
  self.assertFalse(arithmetic(15,1,width=4)['signed_overflow'])
 def test_invalid_before_conversion(self):
  for bad in (True,1.0,complex(1),float('nan'),float('inf'),[1],{'x':1},'1'):
   with self.assertRaises(ValueError):arithmetic(bad,0,width=4)
   with self.assertRaises(ValueError):random_check(width=bad)
  for bad in (0,9,-1):
   with self.assertRaises(ValueError):step(State(),width=bad,rst_n=1,sv=0,data=0,mr=0)
 def test_input_hold_is_environment_not_output_law(self):
  s,_=step(State(1,2),width=2,rst_n=1,sv=1,data=3,mr=0)
  s,_=step(s,width=2,rst_n=1,sv=1,data=0,mr=0)
  self.assertEqual(s,State(1,2)) # illegal producer changes cannot write a rejected word

if __name__=='__main__':unittest.main()
