"""Finite security-game tables and PUBLIC-vector API checks; no production crypto.
No network, random secrets, remote targets, or timings. Import is stdlib-only/inert.
"""
import argparse, hashlib, json, platform, sys
from collections import Counter
from fractions import Fraction
from itertools import product
from pathlib import Path
HERE=Path(__file__).resolve().parent


def native_bytes(value,name,*,length=None,limit=4096):
    if type(value) is not bytes or len(value)>limit or (length is not None and len(value)!=length):
        raise ValueError(name+': bounded bytes with declared length required')
    return value


def context_fields(fields):
    if type(fields) not in (tuple,list) or len(fields)!=4:raise ValueError('four context fields required')
    return tuple(native_bytes(x,'context field',limit=128) for x in fields)


def encode_context(fields):
    """Fixed four-field schema: protocol, session, direction, operation id.
    Two-byte big-endian byte lengths make the tuple encoding injective.
    """
    fields=context_fields(fields)
    return b'WWL-AAD\x01'+b''.join(len(f).to_bytes(2,'big')+f for f in fields)


def open_record(key,nonce,sealed,fields):
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    key=native_bytes(key,'key',length=32);nonce=native_bytes(nonce,'nonce',length=12)
    sealed=native_bytes(sealed,'sealed',limit=4112);aad=encode_context(fields)
    return ChaCha20Poly1305(key).decrypt(nonce,sealed,aad)


class MemoryNonceGuardDemo:
    """In-process guard ONLY. New instance/reboot/multiple writers lose uniqueness.
    Not a nonce allocator, persistent service, key manager, or channel protocol.
    """
    def __init__(self,key):
        self.key=native_bytes(key,'key',length=32);self.used=set()
    def seal(self,nonce,message,fields):
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        nonce=native_bytes(nonce,'nonce',length=12);message=native_bytes(message,'message')
        aad=encode_context(fields)
        if nonce in self.used:raise ValueError('demo nonce already used')
        sealed=ChaCha20Poly1305(self.key).encrypt(nonce,message,aad)
        self.used.add(nonce)
        return sealed


class ReplayLedgerDemo:
    """Single-process ledger; authenticated context precedes mutation/release.
    No persistence, transactional side effects, multi-server or replay-window claim.
    """
    def __init__(self,key,expected_context):
        self.key=native_bytes(key,'key',length=32)
        if type(expected_context) not in (list,tuple) or len(expected_context)!=3:raise ValueError('three expected context fields required')
        self.expected=tuple(native_bytes(v,'expected context',limit=128) for v in expected_context)
        self.seen=set()
    def receive(self,nonce,sealed,fields):
        fields=context_fields(fields)
        if fields[:3]!=self.expected:raise ValueError('unexpected public context')
        message=open_record(self.key,nonce,sealed,fields) # no plaintext before authentication
        if fields[3] in self.seen:raise ValueError('demo repeated operation id')
        self.seen.add(fields[3]);return message


def xor_equal(a,b):
    a=native_bytes(a,'left');b=native_bytes(b,'right')
    if len(a)!=len(b):raise ValueError('equal byte lengths required')
    return bytes(x^y for x,y in zip(a,b))


def optimal_success(left,right):
    """Equal-prior bit game, exact distributions encoded by integer multiplicities."""
    n0,n1=sum(left.values()),sum(right.values())
    return sum((max(Fraction(left[x],2*n0),Fraction(right[x],2*n1)) for x in left.keys()|right.keys()),Fraction())


def finite_games():
    table=[[m^k for k in range(4)] for m in range(4)]
    uniform=optimal_success(Counter(k for k in range(4)),Counter(3^k for k in range(4)))
    biased=optimal_success(Counter((0,0,1,2)),Counter(3^k for k in (0,0,1,2)))
    reused=[Counter((k,k^(3*b)) for k in range(4)) for b in (0,1)]
    fresh=[Counter((k1,k2^(3*b)) for k1,k2 in product(range(4),repeat=2)) for b in (0,1)]
    # Independent random two-bit function outputs on messages 00 and 11.
    # E&M comparison attack sees a reference tag and the challenge plaintext tag.
    wins=0;total=0
    for t0,t1,b in product(range(4),range(4),(0,1)):
        observed=t0 if b==0 else t1;guess=0 if observed==t0 else 1
        wins+=guess==b;total+=1
    return {'otp_table_C_by_message_row_key_column':table,'uniform_single_challenge_success':str(uniform),
            'biased_key_weights_2_1_1_0_success':str(biased),
            'two_messages_same_key_success':str(optimal_success(*reused)),
            'two_messages_independent_keys_success':str(optimal_success(*fresh)),
            'reuse_example':{'M1':'00','M2':'11','K':'10','C1':'10','C2':'01','C1_xor_C2':'11'},
            'flip_example':{'M':'10','K':'11','C':'01','delta':'01','altered_C':'00','decrypted':'11'},
            'encrypt_and_plaintext_tag_compare_tau2_success':str(Fraction(wins,total)),
            'not_claimed':'2-bit keys or tags are not computationally secure; tables prove only the specified finite statements'}


def load_vectors():
    body=(HERE/'public-vectors.json').read_bytes();v=json.loads(body)
    if v.get('schema')!='wwl-crypto-public-vectors-v1':raise ValueError('known public vector schema required')
    return v,hashlib.sha256(body).hexdigest()


def library_checks():
    import cryptography
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes,hmac
    from cryptography.hazmat.backends.openssl.backend import backend
    vectors,digest=load_vectors();v=vectors['rfc8439_2_8_2'];dec=lambda k:bytes.fromhex(v[k+'_hex'])
    key,nonce,aad,plain=map(dec,('key','nonce','aad','plaintext'));expected=dec('ciphertext')+dec('tag')
    cipher=ChaCha20Poly1305(key);sealed=cipher.encrypt(nonce,plain,aad)
    if sealed!=expected or cipher.decrypt(nonce,sealed,aad)!=plain:raise AssertionError('RFC8439 mismatch')
    def rejected(k,n,c,a):
        try:ChaCha20Poly1305(k).decrypt(n,c,a)
        except InvalidTag:return True
        raise AssertionError('modified public tuple unexpectedly authenticated')
    counts={}
    for field,original in (('key',key),('nonce',nonce),('aad',aad),('sealed',sealed)):
        count=0
        for i in range(len(original)):
            for bit in range(8):
                modified=original[:i]+bytes([original[i]^(1<<bit)])+original[i+1:]
                args={'k':key,'n':nonce,'c':sealed,'a':aad};args[{'key':'k','nonce':'n','aad':'a','sealed':'c'}[field]]=modified
                rejected(**args);count+=1
        counts[field+'_single_bit_rejections']=count
    for length in range(len(sealed)):rejected(key,nonce,sealed[:length],aad)
    counts['shorter_prefix_rejections']=len(sealed)
    # PUBLIC misuse demonstration: raw library deliberately does not keep nonce state.
    mk=b'\x55'*32;mn=b'\x66'*12;m1=b'pay=0100';m2=b'pay=0900';cc=ChaCha20Poly1305(mk)
    c1=cc.encrypt(mn,m1,b'public');c2=cc.encrypt(mn,m2,b'public')
    leak=xor_equal(c1[:-16],c2[:-16]);target=xor_equal(m1,m2)
    if leak!=target:raise AssertionError('nonce-reuse equation mismatch')
    fields=(b'lab-v1',b'AB',b'C',b'op7');other=(b'lab-v1',b'A',b'BC',b'op7');message=b'1101'
    # Same bytes, different semantics: this is not a cryptographic tag forgery.
    naive=b''.join(fields);assert naive==b''.join(other)
    nc=ChaCha20Poly1305(key).encrypt(b'\x01'*12,message,naive)
    naive_accepted=ChaCha20Poly1305(key).decrypt(b'\x01'*12,nc,b''.join(other))==message
    guard=MemoryNonceGuardDemo(key);packet=guard.seal(b'\x02'*12,message,fields)
    canonical_rejected=rejected(key,b'\x02'*12,packet,encode_context(other))
    ledger=ReplayLedgerDemo(key,fields[:3]);first=ledger.receive(b'\x02'*12,packet,fields)
    try:ledger.receive(b'\x02'*12,packet,fields)
    except ValueError as exc:duplicate=str(exc)
    else:raise AssertionError('ledger accepted duplicate')
    direct_replay=[open_record(key,b'\x02'*12,packet,fields)==message for _ in range(2)]
    try:guard.seal(b'\x02'*12,message,fields)
    except ValueError as exc:nonce_guard=str(exc)
    else:raise AssertionError('memory guard accepted repeat nonce')
    # A fresh guard with the SAME key can repeat it: memory is not durable coordination.
    after_restart=MemoryNonceGuardDemo(key).seal(b'\x02'*12,message,fields)
    a=vectors['rfc5869_A_1'];raw=lambda name:bytes.fromhex(a[name+'_hex'])
    derived=HKDF(algorithm=hashes.SHA256(),length=a['length'],salt=raw('salt'),info=raw('info')).derive(raw('ikm'))
    hh=hmac.HMAC(raw('salt'),hashes.SHA256());hh.update(raw('ikm'));prk=hh.finalize()
    if derived!=raw('okm') or prk!=raw('prk'):raise AssertionError('RFC5869 mismatch')
    purpose_keys={}
    for direction in (b'c2s',b's2c'):
        info=encode_context((b'key-v1',b'session-A',direction,b'aead'))
        purpose_keys[direction.decode()]=HKDF(algorithm=hashes.SHA256(),length=32,salt=b'public lab salt',info=info).derive(bytes(range(32))).hex()
    if purpose_keys['c2s']==purpose_keys['s2c']:raise AssertionError('chosen domain-separation example collided')
    return {'environment':{'python':sys.version.split()[0],'cryptography':cryptography.__version__,
                            'openssl':backend.openssl_version_text(),'platform':platform.platform()},
            'public_vectors_sha256':digest,'RFC8439':{'ciphertext_hex':sealed[:-16].hex(),'tag_hex':sealed[-16:].hex(),
                'plaintext_bytes':len(plain),'sealed_bytes':len(sealed),'roundtrip':True,**counts},
            'nonce_reuse_PUBLIC_misuse':{'plaintext_xor_hex':target.hex(),'ciphertext_xor_hex':leak.hex(),
                'scope':'fixed public key/nonce only; no Poly1305 forgery experiment'},
            'context':{'naive_encoding_hex':naive.hex(),'two_semantics_same_naive_aad_accepts':naive_accepted,
                'canonical_encoding_hex':encode_context(fields).hex(),'canonical_changed_context_rejected':canonical_rejected},
            'replay':{'stateless_original_decryptions':direct_replay,'ledger_first_plaintext_hex':first.hex(),
                'ledger_second':duplicate,'seen_operation_ids':[x.hex() for x in sorted(ledger.seen)],
                'scope':'single process; no durable transaction/window/multi-server claim'},
            'nonce_state':{'same_instance_repeat':nonce_guard,'new_instance_same_key_repeats_ciphertext':after_restart==packet,
                'scope':'guard is not durable nonce allocation or a ready channel implementation'},
            'RFC5869':{'prk_hex':prk.hex(),'okm_hex':derived.hex()},'domain_separated_public_demo_keys':purpose_keys,
            'not_proved':['general computational security','constant time','side-channel resistance','protocol identity/authorization','durable replay/nonce safety']}


def generate(output):
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('fresh output directory required')
    if out==HERE or HERE in out.parents:raise ValueError('output outside source required')
    result={'finite_games':finite_games(),'actual_library':library_checks()}
    encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True);(out/'results.json').write_text(encoded)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();generate(args.output)
if __name__=='__main__':main()
