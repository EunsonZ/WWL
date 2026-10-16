"""Finite public-vector/transcript/state checks, not general AKE certification."""
import importlib.util,sys,unittest
from dataclasses import replace
from pathlib import Path
spec=importlib.util.spec_from_file_location('handshake_lab',Path(__file__).with_name('handshake_lab.py'))
lab=importlib.util.module_from_spec(spec);sys.modules[spec.name]=lab;spec.loader.exec_module(lab)

class PublicArithmetic(unittest.TestCase):
    def test_small_group_order_and_equations(self):
        r=lab.small_group();self.assertEqual((r['order'],r['A'],r['B'],r['shared_A'],r['shared_B']),(22,8,19,2,2))
        self.assertEqual(r['MITM']['I_leg'],[12,12]);self.assertEqual(r['MITM']['R_leg'],[7,7])
        self.assertEqual(len(set(r['powers_exponents_0_to_21'])),22)
        for a in range(22):
            for b in range(22):self.assertEqual(pow(pow(5,a,23),b,23),pow(pow(5,b,23),a,23))
    def test_external_vectors_and_mitm(self):
        r=lab.checks();self.assertTrue(r['MITM']['mixed_transcript_signatures_rejected'])
        self.assertEqual(r['MITM']['Eve_read_public_payload'],'amount=0100')
        self.assertEqual(r['MITM']['R_received_changed_public_payload'],'amount=0900')
        self.assertEqual(r['authenticated']['I_state'],'confirmed');self.assertEqual(r['authenticated']['R_state'],'confirmed')
        self.assertEqual(len(r['X25519_input_semantics']['five_zero_contribution_inputs_rejected']),5)

class HandshakeState(unittest.TestCase):
    def snapshot(self,e):
        return (e.state,e.committed,e.sent,e.received,e.digest,e.keys,e.signatures,e.sender,e.receiver)
    def test_every_proposal_field_is_signed_and_roles_are_separate(self):
        from cryptography.exceptions import InvalidSignature
        i,r,p=lab.fixtures();t=lab.transcript(p);si=i.sign(p);sr=r.sign(p)
        for field in vars(p):
            value=getattr(p,field);changed=bytes([value[0]^1])+value[1:]
            altered=lab.transcript(replace(p,**{field:changed}))
            with self.assertRaises(InvalidSignature):lab.verify_signature(p.vi,b'I',altered,si)
            with self.assertRaises(InvalidSignature):lab.verify_signature(p.vr,b'R',altered,sr)
        with self.assertRaises(InvalidSignature):lab.verify_signature(p.vi,b'R',t,si)
        with self.assertRaises(InvalidSignature):lab.verify_signature(p.vr,b'I',t,sr)
    def test_expected_local_values_identity_and_pins_before_commit(self):
        i,r,p=lab.fixtures();before=self.snapshot(i)
        cases=[replace(p,protocol=b'WWL-HS/0'),replace(p,suite=b'other'),replace(p,context=b'other'),
            replace(p,initiator=b'mallory'),replace(p,responder=b'mallory'),replace(p,ni=b'\xcc'*32),
            replace(p,xi=lab.x_public(b'\x33'*32)),replace(p,vr=lab.signing_public(b'\x44'*32)),replace(p,xr=bytes(32))]
        for case in cases:
            with self.assertRaises(ValueError):i.sign(case)
            self.assertEqual(self.snapshot(i),before)
        i.sign(p);before=self.snapshot(i)
        with self.assertRaises(ValueError):i.sign(replace(p,nr=b'\xdd'*32))
        self.assertEqual(self.snapshot(i),before)
    def test_invalid_signature_does_not_advance_or_derive(self):
        from cryptography.exceptions import InvalidSignature
        i,r,p=lab.fixtures();si=i.sign(p);sr=r.sign(p);before=self.snapshot(i)
        bad=sr[:-1]+bytes([sr[-1]^1])
        with self.assertRaises(InvalidSignature):i.authenticate(p,si,bad)
        self.assertEqual(self.snapshot(i),before);self.assertIsNone(i.keys)
        i.authenticate(p,si,sr)
        with self.assertRaises(ValueError):i.authenticate(p,si,sr)
    def test_finished_gate_tamper_reflection_and_repetition(self):
        from cryptography.exceptions import InvalidSignature
        i,r,p=lab.authenticated_pair();before=self.snapshot(i)
        with self.assertRaises(ValueError):i.seal(bytes(12),b'x',b'op')
        self.assertEqual(self.snapshot(i),before)
        fi=i.finished();fr=r.finished();before=self.snapshot(i)
        for bad in (fi,fr[:-1]+bytes([fr[-1]^1])):
            with self.assertRaises(InvalidSignature):i.accept_finished(bad)
            self.assertEqual(self.snapshot(i),before)
        i.accept_finished(fr);r.accept_finished(fi)
        self.assertEqual((i.state,r.state),('confirmed','confirmed'))
        with self.assertRaises(ValueError):i.accept_finished(fr)
        with self.assertRaises(ValueError):i.finished()
        c=i.seal(bytes(12),b'public',b'op');self.assertEqual(r.receive(bytes(12),c,b'op'),b'public')
        with self.assertRaises(ValueError):r.receive(bytes(12),c,b'op')
    def test_invalid_native_types_and_lengths_do_not_change_state(self):
        i,r,p=lab.fixtures();before=self.snapshot(i)
        for name in ('xi','xr','ni','nr','vi','vr'):
            for bad in (None,True,bytearray(32),b'x'*31,b'x'*33):
                with self.assertRaises(ValueError):i.sign(replace(p,**{name:bad}))
                self.assertEqual(self.snapshot(i),before)
        for bad in (None,True,bytearray(b'I'),b'X'):
            with self.assertRaises(ValueError):lab.role_value(bad)
        si=i.sign(p);sr=r.sign(p);before=self.snapshot(i)
        for bad in (None,True,b'x'*63,b'x'*65,bytearray(64)):
            with self.assertRaises(ValueError):i.authenticate(p,si,bad)
            self.assertEqual(self.snapshot(i),before)
        i.authenticate(p,si,sr);before=self.snapshot(i)
        for bad in (None,True,bytearray(32),b'x'*31,b'x'*33):
            with self.assertRaises(ValueError):i.accept_finished(bad)
            self.assertEqual(self.snapshot(i),before)
    def test_fresh_challenge_stops_old_transcript_but_fixture_restart_does_not(self):
        from cryptography.exceptions import InvalidSignature
        i,r,p=lab.authenticated_pair();fi=i.finished();fr=r.finished()
        fresh_i,fresh_r,fresh=lab.fixtures(nr=b'\xbc'*32)
        with self.assertRaises(ValueError):fresh_r.sign(p)
        # Reusing ALL public fixture inputs recreates keys/tokens; no durable claim.
        ii,rr,pp=lab.authenticated_pair();self.assertEqual(ii.finished(),fi)
        ii.accept_finished(fr);self.assertEqual(ii.state,'confirmed')
        new_i,new_r,new_p=lab.fixtures(nr=b'\xbc'*32)
        si=new_i.sign(new_p);sr=new_r.sign(new_p)
        new_i.authenticate(new_p,si,sr);new_r.authenticate(new_p,si,sr);new_i.finished()
        with self.assertRaises(InvalidSignature):new_i.accept_finished(fr)
        self.assertFalse(new_i.received)

if __name__=='__main__':unittest.main()
