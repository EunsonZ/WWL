"""Finite textbook RSA plus published-key/encoding/API tests, not security proofs."""
import importlib.util,sys,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('publickey_lab',Path(__file__).with_name('publickey_lab.py'))
lab=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lab;spec.loader.exec_module(lab)

class Mathematics(unittest.TestCase):
    def test_all_residues_including_nonunits_and_structure_attacks(self):
        r=lab.toy();self.assertEqual((r['lambda'],r['d'],r['nonunit_count']),(20,7,15))
        for row in r['all_55_residues']:self.assertEqual((row['roundtrip'],row['crt']),(row['m'],row['m']))
        self.assertEqual((r['nonunit_m5']['c'],r['nonunit_m5']['crt']),(15,5))
        a=r['multiplicative_CCA'];self.assertEqual((a['c'],a['modified_c'],a['oracle_reply'],a['recovered']),(23,19,24,12))
        self.assertEqual(r['raw_signature_forgery']['message_m'],8)
    def test_published_private_numbers_and_crt_nonunits(self):
        keys=lab.fixtures();self.assertNotEqual(keys['enc'].n,keys['sig'].n)
        for key in keys.values():
            self.assertEqual(key.n.bit_length(),2048)
            for value in (0,1,key.p,key.q,key.n-1):self.assertEqual(lab.crt_private_public(key,value),pow(value,key.d,key.n))
    def test_encoding_boundaries_and_top_bits(self):
        for n in (0,1,189,190):
            p=b'x'*n;em=lab.oaep_encode_public(p,bytes(32));d=lab.inspect_oaep_public(em)
            self.assertEqual(d['message_hex'],p.hex());self.assertEqual(d['zero_padding_bytes'],190-n)
        for bits in (777,778,2047,2048):
            em=lab.pss_encode_public(b'm',bytes(48),bits);d=lab.inspect_pss_public(b'm',em,bits)
            self.assertEqual(len(em),(bits+7)//8);self.assertEqual(d['unused_top_bits'],8*len(em)-bits)
        with self.assertRaises(ValueError):lab.inspect_pss_public(b'wrong',lab.pss_encode_public(b'm',bytes(48),2047),2047)

class MatureAPIs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.result,cls.samples=lab.checks()
    def test_official_vector_and_independent_fixed_encodings(self):
        r=self.result;self.assertTrue(r['RFC7520_PS384']['verify']);self.assertEqual(r['RFC7520_PS384']['signature_bytes'],256)
        self.assertTrue(r['fixed_PUBLIC_OAEP']['mature_decrypt']);self.assertTrue(r['fixed_PUBLIC_PSS']['mature_verify'])
        self.assertEqual(r['fixed_PUBLIC_PSS']['emBits'],2047);self.assertEqual(r['fixed_PUBLIC_PSS']['inspect']['zero_padding_bytes'],158)
        self.assertEqual(r['fixed_PUBLIC_OAEP']['one_low_bit_per_byte_rejections'],256)
        self.assertEqual(r['fixed_PUBLIC_PSS']['one_low_bit_per_byte_rejections'],256)
        self.assertTrue(r['fixed_PUBLIC_OAEP']['chosen_RSA_multiplication_rejected'])
        self.assertTrue(r['fixed_PUBLIC_PSS']['raw_s2_forgery_rejected']);self.assertTrue(r['fixed_PUBLIC_PSS']['wrong_public_key_rejected'])
    def test_actual_randomized_samples_are_verified_not_byte_reproduced(self):
        keys=lab.fixtures();enc,sig,_=lab.canonical_messages()
        for c in self.samples['ciphertexts_hex']:self.assertEqual(lab.decrypt_oaep(keys['enc'],bytes.fromhex(c)),enc)
        for s in self.samples['signatures_hex']:lab.verify_pss(keys['sig'],sig,bytes.fromhex(s))
        # No requirement that a fresh run have these same bytes or that every pair must differ.
    def test_purpose_and_native_input_contracts(self):
        keys=lab.fixtures();enc=keys['enc'];sig=keys['sig']
        for fun,args in ((lab.encrypt_oaep,(sig,b'x')),(lab.decrypt_oaep,(sig,bytes(256))),
                        (lab.sign_pss,(enc,b'x')),(lab.verify_pss,(enc,b'x',bytes(256)))):
            with self.assertRaises(ValueError):fun(*args)
        for bad in (None,True,bytearray(b'x'),b'x'*191):
            with self.assertRaises(ValueError):lab.encrypt_oaep(enc,bad)
        for bad in (None,True,bytearray(256),b'x'*255,b'x'*257):
            with self.assertRaises(ValueError):lab.decrypt_oaep(enc,bad)
            with self.assertRaises(ValueError):lab.verify_pss(sig,b'm',bad)
        for bad in (True,-1,1.0,float('nan'),float('inf'),enc.n):
            with self.assertRaises(ValueError):lab.crt_private_public(enc,bad)
        for bad in (None,True,bytearray(32),bytes(31),bytes(33)):
            with self.assertRaises(ValueError):lab.oaep_encode_public(b'm',bad)
        for bad in (True,-1,1.0,float('nan'),float('inf'),4097,776):
            with self.assertRaises(ValueError):lab.pss_encode_public(b'm',bytes(48),bad)
        for bad in (True,-1,1.0,float('nan'),float('inf'),513):
            with self.assertRaises(ValueError):lab.mgf1(b'x',bad,'sha256')

if __name__=='__main__':unittest.main()
