"""PUBLIC deterministic educational handshake, NOT TLS or production AKE.
Mature-library primitives; no network/random secrets. Import is inert/stdlib-only.
The existing AEAD lesson supplies its canonical encoding and demo record state.
"""
import argparse, hashlib, importlib.util, json, os, platform, sys
from dataclasses import dataclass, replace
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROTOCOL=b'WWL-HS/1'
SUITE=b'X25519-Ed25519-HKDFSHA256-ChaCha20Poly1305'
_AEAD=None


def aead():
    global _AEAD
    if _AEAD is None:
        path=Path(os.environ.get('WWL_AEAD_SOURCE',str(HERE.parent/'modern_crypto_aead/aead_lab.py'))).resolve()
        spec=importlib.util.spec_from_file_location('wwl_existing_aead',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        _AEAD=module
    return _AEAD


def bounded(value,name,length=None,limit=128):
    if type(value) is not bytes or len(value)>limit or (length is not None and len(value)!=length):
        raise ValueError(name+': bounded native bytes with declared length required')
    return value


def identity(value):
    value=bounded(value,'identity',limit=32)
    if not value:raise ValueError('nonempty identity required')
    return value


def role_value(role):
    if type(role) is not bytes or role not in (b'I',b'R'):raise ValueError('role I or R required')
    return role


def x_public(scalar):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    return X25519PrivateKey.from_private_bytes(bounded(scalar,'X25519 scalar',32)).public_key().public_bytes_raw()


def exchange(scalar,peer):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey,X25519PublicKey
    scalar=bounded(scalar,'X25519 scalar',32);peer=bounded(peer,'X25519 public',32)
    shared=X25519PrivateKey.from_private_bytes(scalar).exchange(X25519PublicKey.from_public_bytes(peer))
    if shared==bytes(32):raise ValueError('all-zero shared value rejected')
    return shared


def signing_public(seed):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(bounded(seed,'Ed25519 seed',32)).public_key().public_bytes_raw()


@dataclass(frozen=True)
class Proposal:
    protocol:bytes
    suite:bytes
    initiator:bytes
    responder:bytes
    context:bytes
    xi:bytes
    xr:bytes
    ni:bytes
    nr:bytes
    vi:bytes
    vr:bytes


def transcript(p):
    if type(p) is not Proposal:raise ValueError('native Proposal required')
    for name in ('protocol','suite','context'):bounded(getattr(p,name),name)
    identity(p.initiator);identity(p.responder)
    if p.initiator==p.responder:raise ValueError('distinct identities required')
    for name in ('xi','xr','ni','nr','vi','vr'):bounded(getattr(p,name),name,32)
    enc=aead().encode_context
    # Four consecutive fixed four-field blocks; the prior encoder is reused exactly.
    return b''.join((enc((p.protocol,p.suite,p.initiator,p.responder)),
                    enc((b'context/roles',p.context,b'I',b'R')),
                    enc((b'I-eph/R-eph/I-nonce',p.xi,p.xr,p.ni)),
                    enc((b'R-nonce/I-sigkey/R-sigkey',p.nr,p.vi,p.vr))))


def sign_input(role,t):
    role=role_value(role);bounded(t,'transcript',limit=2048)
    return aead().encode_context((b'WWL-HS/1 signature',role,b'full-transcript',b''))+t


def verify_signature(public,role,t,signature):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    public=bounded(public,'Ed25519 public',32);signature=bounded(signature,'signature',64)
    Ed25519PublicKey.from_public_bytes(public).verify(signature,sign_input(role,t))


def derive(shared,t):
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    shared=bounded(shared,'shared',32);bounded(t,'transcript',limit=2048)
    if shared==bytes(32):raise ValueError('all-zero shared value rejected')
    digest=hashlib.sha256(t).digest();keys={}
    for purpose in (b'i2r-aead',b'r2i-aead',b'I-finished',b'R-finished'):
        info=aead().encode_context((b'WWL-HS/1 keys',purpose,digest,b'X25519'))
        keys[purpose]=HKDF(algorithm=hashes.SHA256(),length=32,salt=b'WWL-HS/1 public salt',info=info).derive(shared)
    return digest,keys


def finish_input(role,digest,si,sr):
    role=role_value(role);bounded(digest,'digest',32);bounded(si,'I signature',64);bounded(sr,'R signature',64)
    return aead().encode_context((b'WWL-HS/1 finished',role,digest,b'both-signatures'))+si+sr


def mac(key,message):
    from cryptography.hazmat.primitives import hashes,hmac
    h=hmac.HMAC(key,hashes.SHA256());h.update(message);return h.finalize()


class Endpoint:
    """One pending handshake, pinned identity keys, synchronous process-only state.
    No parser, durable replay store, secrets lifecycle or business transactions.
    """
    def __init__(self,role,scalar,seed,nonce,own,peer,context,registry):
        self.role=role_value(role);self.scalar=bounded(scalar,'scalar',32);self.seed=bounded(seed,'seed',32)
        self.nonce=bounded(nonce,'nonce',32);self.own=identity(own);self.peer=identity(peer)
        self.context=bounded(context,'context');self.x=x_public(self.scalar);self.v=signing_public(self.seed)
        if self.own==self.peer:raise ValueError('distinct identities required')
        if type(registry) is not dict:raise ValueError('native trusted registry required')
        self.registry={identity(k):bounded(v,'pinned public',32) for k,v in registry.items()}
        if self.registry.get(self.own)!=self.v or self.peer not in self.registry:raise ValueError('trusted identity binding missing')
        self.state='new';self.committed=None;self.sent=False;self.received=False
        self.digest=None;self.keys=None;self.signatures=None;self.sender=None;self.receiver=None
    def checked(self,p):
        t=transcript(p)
        if p.protocol!=PROTOCOL or p.suite!=SUITE or p.context!=self.context:raise ValueError('protocol/suite/context mismatch')
        own,peer=(p.initiator,p.responder) if self.role==b'I' else (p.responder,p.initiator)
        ownx,ownn=(p.xi,p.ni) if self.role==b'I' else (p.xr,p.nr)
        if (own,peer)!=(self.own,self.peer):raise ValueError('unexpected identity/role')
        if (ownx,ownn)!=(self.x,self.nonce):raise ValueError('not the local pending challenge/public key')
        if p.vi!=self.registry[p.initiator] or p.vr!=self.registry[p.responder]:raise ValueError('untrusted signature-key binding')
        # Check chosen zero-contribution inputs before committing any endpoint state.
        exchange(self.scalar,p.xr if self.role==b'I' else p.xi)
        return t
    def sign(self,p):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        if self.state not in ('new','signed'):raise ValueError('signature phase closed')
        t=self.checked(p)
        if self.committed is not None and self.committed!=t:raise ValueError('endpoint already committed to another transcript')
        signature=Ed25519PrivateKey.from_private_bytes(self.seed).sign(sign_input(self.role,t))
        self.committed=t;self.state='signed';return signature
    def authenticate(self,p,si,sr):
        if self.state!='signed':raise ValueError('sign before authenticate, once')
        t=self.checked(p)
        if t!=self.committed:raise ValueError('different committed transcript')
        bounded(si,'I signature',64);bounded(sr,'R signature',64)
        verify_signature(p.vi,b'I',t,si);verify_signature(p.vr,b'R',t,sr)
        peerx=p.xr if self.role==b'I' else p.xi
        digest,keys=derive(exchange(self.scalar,peerx),t)
        outgoing=b'i2r' if self.role==b'I' else b'r2i';incoming=b'r2i' if self.role==b'I' else b'i2r'
        sender=aead().MemoryNonceGuardDemo(keys[outgoing+b'-aead'])
        receiver=aead().ReplayLedgerDemo(keys[incoming+b'-aead'],(b'hs-data-v1',digest,incoming))
        self.digest=digest;self.keys=keys;self.signatures=(si,sr)
        self.sender=sender;self.receiver=receiver;self.state='authenticated'
    def finished(self):
        if self.state not in ('authenticated','confirmed') or self.sent:raise ValueError('Finished already sent or wrong phase')
        token=mac(self.keys[self.role+b'-finished'],finish_input(self.role,self.digest,*self.signatures))
        self.sent=True
        if self.received:self.state='confirmed'
        return token
    def accept_finished(self,token):
        from cryptography.hazmat.primitives import hashes,hmac
        if self.state not in ('authenticated','confirmed') or self.received:raise ValueError('Finished already received or wrong phase')
        token=bounded(token,'Finished',32);other=b'R' if self.role==b'I' else b'I'
        h=hmac.HMAC(self.keys[other+b'-finished'],hashes.SHA256())
        h.update(finish_input(other,self.digest,*self.signatures));h.verify(token)
        self.received=True
        if self.sent:self.state='confirmed'
    def seal(self,nonce,message,operation):
        if self.state!='confirmed':raise ValueError('both Finished directions required before data')
        direction=b'i2r' if self.role==b'I' else b'r2i'
        return self.sender.seal(nonce,message,(b'hs-data-v1',self.digest,direction,operation))
    def receive(self,nonce,sealed,operation):
        if self.state!='confirmed':raise ValueError('both Finished directions required before data')
        direction=b'r2i' if self.role==b'I' else b'i2r'
        return self.receiver.receive(nonce,sealed,(b'hs-data-v1',self.digest,direction,operation))


def vectors():
    raw=(HERE/'public-vectors.json').read_bytes();v=json.loads(raw)
    if v.get('schema')!='wwl-handshake-public-vectors-v1':raise ValueError('known vectors required')
    return v,hashlib.sha256(raw).hexdigest()


def fixtures(*,ni=None,nr=None):
    v,_=vectors();x=v['x25519'];ed=v['ed25519'];unhex=bytes.fromhex
    a=unhex(x['alice_private']);b=unhex(x['bob_private']);sa=unhex(ed[0]['seed']);sb=unhex(ed[1]['seed'])
    ni=b'\xaa'*32 if ni is None else ni;nr=b'\xbb'*32 if nr is None else nr
    registry={b'alice.lab':signing_public(sa),b'bob.lab':signing_public(sb)}
    i=Endpoint(b'I',a,sa,ni,b'alice.lab',b'bob.lab',b'public-payments-demo',registry)
    r=Endpoint(b'R',b,sb,nr,b'bob.lab',b'alice.lab',b'public-payments-demo',registry)
    p=Proposal(PROTOCOL,SUITE,i.own,r.own,i.context,i.x,r.x,ni,nr,i.v,r.v)
    return i,r,p


def authenticated_pair():
    i,r,p=fixtures();si=i.sign(p);sr=r.sign(p)
    i.authenticate(p,si,sr);r.authenticate(p,si,sr)
    return i,r,p


def confirmed_pair():
    i,r,p=authenticated_pair();fi=i.finished();fr=r.finished()
    i.accept_finished(fr);r.accept_finished(fi);return i,r,p


def small_group():
    p,g,a,b=23,5,6,15;A=pow(g,a,p);B=pow(g,b,p)
    powers=[pow(g,e,p) for e in range(22)];ea,er=7,13;E1=pow(g,ea,p);E2=pow(g,er,p)
    return {'p':p,'g':g,'order':next(e for e in range(1,23) if pow(g,e,p)==1),
        'powers_exponents_0_to_21':powers,'a':a,'b':b,'A':A,'B':B,'shared_A':pow(B,a,p),'shared_B':pow(A,b,p),
        'public_enumeration_recovers_a':powers.index(A),'public_enumeration_recovers_b':powers.index(B),
        'MITM':{'eve_to_I_exponent':ea,'eve_to_R_exponent':er,'E1':E1,'E2':E2,
            'I_leg':[pow(E1,a,p),pow(A,ea,p)],'R_leg':[pow(E2,b,p),pow(B,er,p)]},
        'legendre_g_A_B_shared':[pow(z,11,p) for z in (g,A,B,pow(B,a,p))]}


def checks():
    import cryptography
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.backends.openssl.backend import backend
    v,vector_sha=vectors();x=v['x25519'];unhex=bytes.fromhex
    a,b=unhex(x['alice_private']),unhex(x['bob_private']);A,B=x_public(a),x_public(b);z=exchange(a,B)
    assert A.hex()==x['alice_public'] and B.hex()==x['bob_public'] and z.hex()==x['shared'] and exchange(b,A)==z
    signatures=[]
    for case in v['ed25519']:
        private=Ed25519PrivateKey.from_private_bytes(unhex(case['seed']));sig=private.sign(unhex(case['message']))
        assert private.public_key().public_bytes_raw().hex()==case['public'] and sig.hex()==case['signature']
        private.public_key().verify(sig,unhex(case['message']));signatures.append(sig.hex())
    i,r,p=confirmed_pair();n=b'\x01'*12;message=b'amount=0100';op=b'op7';sealed=i.seal(n,message,op)
    assert r.receive(n,sealed,op)==message
    try:r.receive(n,sealed,op)
    except ValueError:replay_rejected=True
    else:raise AssertionError('record replay accepted')
    fresh_i,fresh_r,fresh_p=fixtures(nr=b'\xbc'*32)
    try:fresh_r.sign(p)
    except ValueError:old_hello_rejected=True
    else:raise AssertionError('old transcript matched fresh responder challenge')
    # Authenticate both substituted legs separately? Local commitments disagree.
    e1,e2=b'\x11'*32,b'\x22'*32
    ti=replace(p,xr=x_public(e1));tr=replace(p,xi=x_public(e2))
    ii,rr,_=fixtures();sii=ii.sign(ti);srr=rr.sign(tr)
    try:ii.authenticate(ti,sii,srr)
    except InvalidSignature:mitm_auth_rejected=True
    else:raise AssertionError('mixed-transcript signatures accepted')
    za,zea=exchange(a,x_public(e1)),exchange(e1,A);zb,zeb=exchange(b,x_public(e2)),exchange(e2,B)
    assert za==zea and zb==zeb and za!=zb
    da,ka=derive(za,transcript(ti));db,kb=derive(zb,transcript(tr));enc=aead()
    # Deliberately unauthenticated legs: Eve reads and replaces this public payload.
    na=b'\x03'*12;nb=b'\x04'*12;fields_a=(b'hs-data-v1',da,b'i2r',op);fields_b=(b'hs-data-v1',db,b'i2r',op)
    ca=enc.MemoryNonceGuardDemo(ka[b'i2r-aead']).seal(na,message,fields_a)
    read=enc.open_record(ka[b'i2r-aead'],na,ca,fields_a);changed=b'amount=0900'
    cb=enc.MemoryNonceGuardDemo(kb[b'i2r-aead']).seal(nb,changed,fields_b)
    delivered=enc.open_record(kb[b'i2r-aead'],nb,cb,fields_b);assert read==message and delivered==changed
    prime=2**255-19;low_rejected=[]
    for u in (0,1,prime-1,prime,prime+1):
        try:exchange(a,u.to_bytes(32,'little'))
        except ValueError:low_rejected.append(str(u))
        else:raise AssertionError('chosen zero-contribution input accepted')
    high=B[:-1]+bytes([B[-1]^128]);noncanonical=(prime+9).to_bytes(32,'little');base=(9).to_bytes(32,'little')
    assert exchange(a,high)==z and exchange(a,noncanonical)==exchange(a,base)
    assert transcript(replace(p,xr=high))!=transcript(p)
    source=Path(enc.__file__)
    return {'environment':{'python':sys.version.split()[0],'cryptography':cryptography.__version__,
            'openssl':backend.openssl_version_text(),'platform':platform.platform()},
        'vectors_sha256':vector_sha,'reused_aead_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'small_group':small_group(),'RFC7748':{'alice_public':A.hex(),'bob_public':B.hex(),'shared':z.hex()},
        'RFC8032_test1_test2_signatures':signatures,
        'authenticated':{'transcript_hex':transcript(p).hex(),'transcript_sha256':i.digest.hex(),
            'I_signature':i.signatures[0].hex(),'R_signature':i.signatures[1].hex(),
            'I_finished_hmac':mac(i.keys[b'I-finished'],finish_input(b'I',i.digest,*i.signatures)).hex(),
            'R_finished_hmac':mac(i.keys[b'R-finished'],finish_input(b'R',i.digest,*i.signatures)).hex(),
            'all_four_derived_keys_agree':i.keys==r.keys,
            'keys_PUBLIC_FIXTURES':{k.decode():val.hex() for k,val in i.keys.items()},
            'I_state':i.state,'R_state':r.state,'record_sealed_hex':sealed.hex(),'record_plaintext_hex':message.hex(),
            'record_replay_rejected':replay_rejected,'old_transcript_vs_fresh_R_nonce_rejected':old_hello_rejected},
        'MITM':{'I_Eve_shared':za.hex(),'Eve_R_shared':zb.hex(),'each_leg_matches':True,
            'same_end_to_end_shared':False,'Eve_read_public_payload':read.decode(),'R_received_changed_public_payload':delivered.decode(),
            'mixed_transcript_signatures_rejected':mitm_auth_rejected},
        'X25519_input_semantics':{'five_zero_contribution_inputs_rejected':low_rejected,
            'high_bit_alias_same_shared':True,'noncanonical_p_plus_9_same_as_9':True,'actual_wire_bytes_bound_in_transcript':True},
        'not_proved':['TLS interoperability','general authenticated key exchange security','EUF-CMA from finite tests',
            'forward secrecy of public fixtures','production nonce/replay durability','constant time or side-channel resistance']}


def generate(output):
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('fresh output required')
    if out==HERE or HERE in out.parents:raise ValueError('output outside source required')
    result=checks();body=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True);(out/'results.json').write_text(body);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args();generate(args.output)
if __name__=='__main__':main()
