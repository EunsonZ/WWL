"""Finite algebra, published vectors, API/state boundaries. No crypto-security claim."""
import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('modes_lab',Path(__file__).with_name('modes_lab.py'))
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

class AESMechanics(unittest.TestCase):
    def test_field_and_nonaffine_sbox(self):
        self.assertEqual(lab.gf_mul(0x57,0x13),0xfe)
        f,back=lab.tables();self.assertEqual(len(set(f)),256)
        self.assertEqual((f[0],f[0x53]),(0x63,0xed))
        for x in range(256):self.assertEqual(back[f[x]],x)
        for x in range(1,256):self.assertEqual(lab.gf_mul(x,lab._power(x,254)),1)
        self.assertNotEqual(f[0]^f[1]^f[2],f[3])
    def test_inverse_linear_transforms_on_basis(self):
        for bit in range(128):
            state=bytes((1<<(bit%8)) if i==bit//8 else 0 for i in range(16))
            self.assertEqual(lab.shift_rows(lab.shift_rows(state),True),state)
            self.assertEqual(lab.mix_columns(lab.mix_columns(state),True),state)
        self.assertEqual(lab.mix_column(bytes.fromhex('db135345')),bytes.fromhex('8e4da1bc'))
    def test_nist_key_and_round_trace(self):
        v,_=lab.vectors();key=bytes.fromhex(v['key']);p=bytes.fromhex(v['plaintext'])[:16]
        trace=lab.encrypt_trace(key,p);events={str(e['round'])+'.'+e['stage']:e['state'] for e in trace}
        self.assertEqual(len(trace),40);self.assertNotIn('10.MixColumns',events)
        for event,expected in v['first_block_round_checks'].items():self.assertEqual(events[event],expected)
        self.assertEqual(lab.expand_key(key)[1].hex(),v['round1_key'])
        self.assertEqual(lab.aes_decrypt(key,lab.aes_encrypt(key,p)),p)
    def test_mode_vectors_and_external_routes(self):
        r=lab.checks('/usr/bin/openssl')
        self.assertTrue(r['CTR_partial_31byte_exact']);self.assertTrue(r['CBC_predictable_IV']['ciphertext_matches_reference'])
        self.assertEqual(r['CBC_IV_flip']['changed_byte_indices'],[0]);self.assertEqual(r['CTR_ciphertext_flip']['changed_byte_indices'],[17])
        self.assertTrue(r['CBC_C1_flip']['P2_exact_flip']);self.assertTrue(r['CBC_C1_flip']['P3_P4_unchanged'])
        self.assertEqual(r['CTR_reuse_PUBLIC']['plaintext_xor'],r['CTR_reuse_PUBLIC']['ciphertext_xor'])

class Contract(unittest.TestCase):
    def test_counter_range_overlap_wrap_and_no_state_on_rejection(self):
        guard=lab.CTRRangeGuardDemo(bytes(16));guard.encrypt(7,bytes(32));self.assertEqual(guard.used,[(7,9)])
        for start,data in ((8,bytes(16)),(6,bytes(32)),(lab.COUNTERS-1,bytes(17)),(True,b'x'),(-1,b'x'),(1.0,b'x'),
                           (float('nan'),b'x'),(float('inf'),b'x'),(lab.COUNTERS,b'x'),(1,bytearray(16)),(1,b'x'*4097)):
            before=list(guard.used)
            with self.assertRaises(ValueError):guard.encrypt(start,data)
            self.assertEqual(guard.used,before)
        self.assertEqual(guard.encrypt(8,b''),b'');self.assertEqual(guard.used,[(7,9)])
        guard.encrypt(9,b'x');self.assertEqual(guard.used,[(7,9),(9,10)])
        last=lab.CTRRangeGuardDemo(bytes(16));last.encrypt(lab.COUNTERS-1,bytes(16));self.assertEqual(last.used,[(lab.COUNTERS-1,lab.COUNTERS)])
        with self.assertRaises(ValueError):last.encrypt(lab.COUNTERS-1,b'x')
    def test_native_input_types_lengths_and_no_implicit_padding(self):
        for bad in (None,True,bytearray(16),b'x'*15,b'x'*17):
            with self.assertRaises(ValueError):lab.aes_encrypt(bad,bytes(16))
            with self.assertRaises(ValueError):lab.aes_encrypt(bytes(16),bad)
            with self.assertRaises(ValueError):lab.CTRRangeGuardDemo(bad)
        for data in (None,True,bytearray(16),b'x',b'x'*17,b'x'*4097):
            with self.assertRaises(ValueError):lab.cbc(bytes(16),bytes(16),data)
            with self.assertRaises(ValueError):lab.library('CBC',bytes(16),data,bytes(16))
        for bad in (True,-1,256,1.0,float('nan'),float('inf')):
            with self.assertRaises(ValueError):lab.gf_mul(bad,1)
        for bad in (0,1,None):
            with self.assertRaises(ValueError):lab.cbc(bytes(16),bytes(16),b'',bad)
        self.assertEqual(lab.ecb(bytes(16),b''),b'');self.assertEqual(lab.cbc(bytes(16),bytes(16),b''),b'')
    def test_partial_ctr_and_stateless_restart_contract(self):
        k=bytes(range(16));start=42
        for n in (0,1,15,16,17,31,32,33):
            p=bytes(range(n));c=lab.ctr(k,start,p)
            self.assertEqual(len(c),n);self.assertEqual(c,lab.library('CTR',k,p,start));self.assertEqual(lab.ctr(k,start,c),p)
        g1=lab.CTRRangeGuardDemo(k);c1=g1.encrypt(start,b'public')
        self.assertEqual(lab.CTRRangeGuardDemo(k).encrypt(start,b'public'),c1)
        with self.assertRaises(ValueError):g1.encrypt(start,b'public')

if __name__=='__main__':unittest.main()
