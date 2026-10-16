"""Finite/external-vector checks, not a proof of general crypto security."""
import importlib.util
import unittest
from collections import Counter
from fractions import Fraction
from itertools import product
from pathlib import Path

spec=importlib.util.spec_from_file_location('aead_lab',Path(__file__).with_name('aead_lab.py'))
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

class FiniteGames(unittest.TestCase):
    def test_otp_any_prior_and_reuse_flip(self):
        # Nonuniform prior P(M)=(1,2,3,4)/10: each C leaves it unchanged.
        joint=Counter()
        for m,k in product(range(4),repeat=2):joint[m,m^k]+=m+1
        for c in range(4):
            total=sum(joint[m,c] for m in range(4))
            for m in range(4):self.assertEqual(Fraction(joint[m,c],total),Fraction(m+1,10))
        for m1,m2,k in product(range(4),repeat=3):
            self.assertEqual((m1^k)^(m2^k),m1^m2)
            for delta in range(4):self.assertEqual(((m1^k)^delta)^k,m1^delta)
    def test_game_probabilities(self):
        r=lab.finite_games()
        self.assertEqual([r[k] for k in ('uniform_single_challenge_success','biased_key_weights_2_1_1_0_success',
             'two_messages_same_key_success','two_messages_independent_keys_success',
             'encrypt_and_plaintext_tag_compare_tau2_success')],['1/2','3/4','1','1/2','7/8'])
        self.assertEqual(r['otp_table_C_by_message_row_key_column'],[[0,1,2,3],[1,0,3,2],[2,3,0,1],[3,2,1,0]])
    def test_context_is_injective_on_finite_domain(self):
        fields=(b'',b'a',b'b',b'ab',b'ba')
        encodings={lab.encode_context(t) for t in product(fields,repeat=4)}
        self.assertEqual(len(encodings),len(fields)**4)
        a=(b'lab-v1',b'AB',b'C',b'op7');b=(b'lab-v1',b'A',b'BC',b'op7')
        self.assertEqual(b''.join(a),b''.join(b));self.assertNotEqual(lab.encode_context(a),lab.encode_context(b))

class ActualAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result=lab.library_checks()
    def test_public_vectors_and_all_declared_mutations(self):
        r=self.result['RFC8439']
        self.assertEqual((r['plaintext_bytes'],r['sealed_bytes']),(114,130))
        self.assertEqual([r[k+'_single_bit_rejections'] for k in ('key','nonce','aad','sealed')],[256,96,96,1040])
        self.assertEqual(r['shorter_prefix_rejections'],130)
        vectors,_=lab.load_vectors();self.assertEqual(self.result['RFC5869']['okm_hex'],vectors['rfc5869_A_1']['okm_hex'])
    def test_protocol_limits_are_observed(self):
        r=self.result
        self.assertEqual(r['replay']['stateless_original_decryptions'],[True,True])
        self.assertTrue(r['context']['canonical_changed_context_rejected'])
        self.assertTrue(r['context']['two_semantics_same_naive_aad_accepts'])
        self.assertTrue(r['nonce_state']['new_instance_same_key_repeats_ciphertext'])
        self.assertEqual(r['nonce_reuse_PUBLIC_misuse']['plaintext_xor_hex'],r['nonce_reuse_PUBLIC_misuse']['ciphertext_xor_hex'])
    def test_invalid_inputs_precede_state_and_authentication_precedes_ledger(self):
        from cryptography.exceptions import InvalidTag
        k=bytes(range(32));n=bytes(range(12));f=(b'p',b's',b'd',b'op')
        guard=lab.MemoryNonceGuardDemo(k)
        bad=[(n,b'x',f[:3]),(n,b'x',(b'p',b's',b'd',bytearray(b'op'))),(n,b'x'*4097,f),(n[:-1],b'x',f)]
        for args in bad:
            with self.assertRaises(ValueError):guard.seal(*args)
            self.assertEqual(guard.used,set())
        packet=guard.seal(n,b'public',f)
        with self.assertRaises(ValueError):guard.seal(n,b'public',f)
        self.assertEqual(guard.used,{n})
        ledger=lab.ReplayLedgerDemo(k,f[:3]);changed=packet[:-1]+bytes([packet[-1]^1])
        with self.assertRaises(InvalidTag):ledger.receive(n,changed,f)
        self.assertEqual(ledger.seen,set());self.assertEqual(ledger.receive(n,packet,f),b'public')
        with self.assertRaises(ValueError):ledger.receive(n,packet,f)
        # A fresh correctly authenticated packet is still the same operation.
        packet2=guard.seal(b'\xff'*12,b'public',f)
        with self.assertRaises(ValueError):ledger.receive(b'\xff'*12,packet2,f)
        self.assertEqual(ledger.seen,{b'op'})
    def test_public_interface_types_and_bounds(self):
        for key in (b'',b'x'*31,bytearray(32),True,None):
            with self.assertRaises(ValueError):lab.MemoryNonceGuardDemo(key)
        k=b'k'*32;f=(b'p',b's',b'd',b'o')
        for fields in (None,b'abcd',(b'a',)*3,(b'a',)*5,(b'a'*129,)*4,(1,b's',b'd',b'o')):
            with self.assertRaises(ValueError):lab.encode_context(fields)
        for nonce in (None,True,bytearray(12),b'x'*11,b'x'*13):
            with self.assertRaises(ValueError):lab.open_record(k,nonce,b'',f)
        for sealed in (None,bytearray(b'x'),True,b'x'*4113):
            with self.assertRaises(ValueError):lab.open_record(k,b'n'*12,sealed,f)
        with self.assertRaises(ValueError):lab.xor_equal(b'a',b'ab')

if __name__=='__main__':unittest.main()
