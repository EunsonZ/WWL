"""RSA math/encodings on ALREADY PUBLIC RFC keys. NEVER DEPLOY these fixtures.
No key generation, real credentials, network or timings. Import is inert/stdlib-only.
Teaching encoders/raw CRT are public-evidence helpers, NOT production crypto.
"""
import argparse,base64,hashlib,importlib.util,json,math,os,platform,sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
HERE=Path(__file__).resolve().parent


def native_bytes(value,name,length=None,limit=4096):
    if type(value) is not bytes or len(value)>limit or (length is not None and len(value)!=length):
        raise ValueError(name+': bounded native bytes with declared length required')
    return value


def unsigned(value,upper,name):
    if type(value) is not int or not 0<=value<upper:raise ValueError(name+': native unsigned integer in range required')
    return value


def unbase(value):
    if type(value) is not str or not value or len(value)>2048:raise ValueError('bounded nonempty base64url string required')
    return base64.b64decode(value+'='*((-len(value))%4),altchars=b'-_',validate=True)


@dataclass(frozen=True)
class PublicFixture:
    purpose:str
    n:int
    e:int
    d:int
    p:int
    q:int
    dp:int
    dq:int
    qi:int
    private:object


def fixture_data():
    raw=(HERE/'public-fixtures.json').read_bytes();data=json.loads(raw)
    if data.get('schema')!='wwl-public-RSA-fixtures-v1':raise ValueError('known public fixture schema required')
    return data,hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def fixtures():
    from cryptography.hazmat.primitives.asymmetric import rsa
    data,_=fixture_data();out={}
    for purpose,jwk in (('enc',data['encryption_jwk']),('sig',data['signing_jwk'])):
        if jwk['use']!=purpose:raise ValueError('published fixture purpose mismatch')
        a={name:int.from_bytes(unbase(jwk[name]),'big') for name in ('n','e','d','p','q','dp','dq','qi')}
        if a['n'].bit_length()!=2048 or a['e']!=65537:raise ValueError('selected 2048-bit public fixture required')
        if a['p']*a['q']!=a['n'] or a['e']*a['d']%math.lcm(a['p']-1,a['q']-1)!=1:raise ValueError('invalid RSA factors/exponents')
        private=rsa.RSAPrivateNumbers(a['p'],a['q'],a['d'],a['dp'],a['dq'],a['qi'],rsa.RSAPublicNumbers(a['e'],a['n'])).private_key()
        out[purpose]=PublicFixture(purpose=purpose,private=private,**a)
    if out['enc'].n==out['sig'].n:raise ValueError('separate public fixture keys required')
    return out


def require(key,purpose):
    if type(key) is not PublicFixture or key.purpose!=purpose:raise ValueError('selected fixture with matching purpose required')
    # The demo only accepts its published fixtures; not a general secret-key API.
    if key is not fixtures()[purpose]:raise ValueError('only loaded public RFC fixture accepted')
    return key


def crt_private_public(key,value):
    if type(key) is not PublicFixture or not any(key is k for k in fixtures().values()):raise ValueError('loaded public fixture required')
    unsigned(value,key.n,'RSA representative')
    m1=pow(value,key.dp,key.p);m2=pow(value,key.dq,key.q)
    return m2+key.q*((key.qi*(m1-m2))%key.p)


def xor(a,b):
    native_bytes(a,'left');native_bytes(b,'right')
    if len(a)!=len(b):raise ValueError('equal byte lengths required')
    return bytes(x^y for x,y in zip(a,b))


def mgf1(seed,length,algorithm):
    native_bytes(seed,'MGF seed');unsigned(length,513,'MGF output length')
    if type(algorithm) is not str or algorithm not in ('sha256','sha384'):raise ValueError('selected MGF hash required')
    size=hashlib.new(algorithm).digest_size
    return b''.join(hashlib.new(algorithm,seed+i.to_bytes(4,'big')).digest() for i in range((length+size-1)//size))[:length]


def oaep_encode_public(message,seed):
    """Fixed k256/SHA256/empty label. PUBLIC deterministic evidence only."""
    native_bytes(message,'OAEP message',limit=190);native_bytes(seed,'PUBLIC seed',32)
    db=hashlib.sha256(b'').digest()+bytes(190-len(message))+b'\x01'+message
    masked=xor(db,mgf1(seed,223,'sha256'));masked_seed=xor(seed,mgf1(masked,32,'sha256'))
    return b'\x00'+masked_seed+masked


def inspect_oaep_public(em):
    """Inspect PUBLIC encoded block; not a constant-time decoder for secrets."""
    native_bytes(em,'PUBLIC OAEP encoded block',256)
    seed=xor(em[1:33],mgf1(em[33:],32,'sha256'));db=xor(em[33:],mgf1(seed,223,'sha256'))
    if em[0]!=0 or db[:32]!=hashlib.sha256(b'').digest():raise ValueError('public OAEP header mismatch')
    try:separator=db.index(1,32)
    except ValueError:raise ValueError('public OAEP delimiter missing') from None
    if any(db[32:separator]):raise ValueError('public OAEP zero padding mismatch')
    return {'seed_hex':seed.hex(),'lHash_hex':db[:32].hex(),'zero_padding_bytes':separator-32,'message_hex':db[separator+1:].hex()}


def pss_encode_public(message,salt,em_bits):
    """SHA384/MGF1SHA384/salt48; PUBLIC deterministic evidence only."""
    native_bytes(message,'PSS message');native_bytes(salt,'PUBLIC salt',48)
    unsigned(em_bits,4097,'emBits')
    if em_bits<8*(48+48+1)+1:raise ValueError('PSS encoded message too short')
    size=(em_bits+7)//8;h=hashlib.sha384(bytes(8)+hashlib.sha384(message).digest()+salt).digest()
    db=bytes(size-48-48-2)+b'\x01'+salt;masked=bytearray(xor(db,mgf1(h,size-49,'sha384')))
    masked[0]&=255>>(8*size-em_bits)
    return bytes(masked)+h+b'\xbc'


def inspect_pss_public(message,em,em_bits):
    native_bytes(message,'PSS message');unsigned(em_bits,4097,'emBits')
    if em_bits<8*(48+48+1)+1:raise ValueError('PSS encoded message too short')
    size=(em_bits+7)//8;native_bytes(em,'PUBLIC PSS encoded block',size)
    unused=8*size-em_bits
    if em[-1]!=0xbc or (unused and em[0]>>(8-unused)):
        raise ValueError('public PSS trailer/top-bit mismatch')
    h=em[-49:-1];db=bytearray(xor(em[:-49],mgf1(h,size-49,'sha384')));db[0]&=255>>unused
    zeros=size-98
    if any(db[:zeros]) or db[zeros]!=1:raise ValueError('public PSS zero padding/delimiter mismatch')
    salt=bytes(db[-48:]);expected=hashlib.sha384(bytes(8)+hashlib.sha384(message).digest()+salt).digest()
    if h!=expected:raise ValueError('public PSS message/hash mismatch')
    return {'salt_hex':salt.hex(),'H_hex':h.hex(),'zero_padding_bytes':zeros,'unused_top_bits':unused}


def oaep_parameters():
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None)


def pss_parameters():
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    return padding.PSS(mgf=padding.MGF1(hashes.SHA384()),salt_length=48)


def encrypt_oaep(key,message):
    require(key,'enc');native_bytes(message,'OAEP message',limit=190)
    return key.private.public_key().encrypt(message,oaep_parameters())


def decrypt_oaep(key,ciphertext):
    require(key,'enc');native_bytes(ciphertext,'OAEP ciphertext',256)
    return key.private.decrypt(ciphertext,oaep_parameters())


def sign_pss(key,message):
    from cryptography.hazmat.primitives import hashes
    require(key,'sig');native_bytes(message,'PSS message')
    return key.private.sign(message,pss_parameters(),hashes.SHA384())


def verify_pss(key,message,signature):
    from cryptography.hazmat.primitives import hashes
    require(key,'sig');native_bytes(message,'PSS message');native_bytes(signature,'PSS signature',256)
    key.private.public_key().verify(signature,message,pss_parameters(),hashes.SHA384())


def canonical_messages():
    path=Path(os.environ.get('WWL_AEAD_SOURCE',str(HERE.parent/'modern_crypto_aead/aead_lab.py'))).resolve()
    spec=importlib.util.spec_from_file_location('wwl_publickey_existing_aead',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    enc=module.encode_context((b'WWL-PKE/1',b'payload',b'alice-to-bob',b'amount=0100'))
    sig=module.encode_context((b'WWL-SIG/1',b'authorization',b'alice.lab',b'op7:amount=0100'))
    return enc,sig,hashlib.sha256(path.read_bytes()).hexdigest()


def toy():
    p,q,e,d=5,11,3,7;n=p*q;lam=math.lcm(p-1,q-1);checks=[]
    for m in range(n):
        c=pow(m,e,n);direct=pow(c,d,n)
        u=pow(c,d%(p-1),p);v=pow(c,d%(q-1),q);crt=v+q*((pow(q,-1,p)*(u-v))%p)
        if direct!=m or crt!=m:raise AssertionError('toy RSA failed')
        checks.append({'m':m,'c':c,'roundtrip':direct,'crt':crt,'gcd_with_n':math.gcd(m,n)})
    m,r=12,2;c=pow(m,e,n);modified=c*pow(r,e,n)%n;reply=pow(modified,d,n);recovered=reply*pow(r,-1,n)%n
    return {'p':p,'q':q,'n':n,'lambda':lam,'e':e,'d':d,'all_55_residues':checks,
        'nonunit_count':sum(x['gcd_with_n']!=1 for x in checks),
        'nonunit_m5':checks[5],
        'no_wrap_cube':{'m':3,'c':27,'integer_cube_root':3},
        'multiplicative_CCA':{'m_PUBLIC':m,'c':c,'r':r,'modified_c':modified,'oracle_reply':reply,'recovered':recovered},
        'raw_signature_forgery':{'chosen_s':2,'message_m':pow(2,e,n),'verification_accepts':True}}


def checks():
    import cryptography
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends.openssl.backend import backend
    data,digest=fixture_data();keys=fixtures();ek=keys['enc'];sk=keys['sig'];message,signed,aead_sha=canonical_messages()
    header,payload,rfc_signature=data['RFC7520_PS384_compact'].split('.')
    rfc_input=(header+'.'+payload).encode('ascii');rfc_sig=unbase(rfc_signature);verify_pss(sk,rfc_input,rfc_sig)
    rfc_em=pow(int.from_bytes(rfc_sig,'big'),sk.e,sk.n).to_bytes(256,'big');rfc_inspect=inspect_pss_public(rfc_input,rfc_em,sk.n.bit_length()-1)
    seed=bytes.fromhex(data['teaching_OAEP_seed_hex']);salt=bytes.fromhex(data['teaching_PSS_salt_hex'])
    em=oaep_encode_public(message,seed);c=pow(int.from_bytes(em,'big'),ek.e,ek.n).to_bytes(256,'big')
    assert decrypt_oaep(ek,c)==message and crt_private_public(ek,int.from_bytes(c,'big'))==int.from_bytes(em,'big')
    inspection=inspect_oaep_public(em)
    ps=pss_encode_public(signed,salt,sk.n.bit_length()-1);s=crt_private_public(sk,int.from_bytes(ps,'big')).to_bytes(256,'big')
    verify_pss(sk,signed,s);assert pow(int.from_bytes(s,'big'),sk.e,sk.n)==int.from_bytes(ps,'big')
    pss_inspection=inspect_pss_public(signed,ps,sk.n.bit_length()-1)
    # Actual randomized mature APIs, only PUBLIC examples. Raw samples saved separately.
    ciphertexts=[encrypt_oaep(ek,message) for _ in range(2)];signatures=[sign_pss(sk,signed) for _ in range(2)]
    for ciphertext in ciphertexts:assert decrypt_oaep(ek,ciphertext)==message
    for signature in signatures:verify_pss(sk,signed,signature)
    oaep_rejections=0;pss_rejections=0
    for i in range(256):
        altered=c[:i]+bytes([c[i]^1])+c[i+1:]
        try:decrypt_oaep(ek,altered)
        except ValueError:oaep_rejections+=1
        else:raise AssertionError('chosen changed OAEP block accepted')
        altered=s[:i]+bytes([s[i]^1])+s[i+1:]
        try:verify_pss(sk,signed,altered)
        except InvalidSignature:pss_rejections+=1
        else:raise AssertionError('chosen changed PSS signature accepted')
    for bad in (signed+b'!',bytes([signed[0]^1])+signed[1:]):
        try:verify_pss(sk,bad,s)
        except InvalidSignature:pass
        else:raise AssertionError('changed signed message accepted')
    try:ek.private.decrypt(c,padding.OAEP(mgf=padding.MGF1(hashes.SHA384()),algorithm=hashes.SHA384(),label=None))
    except ValueError:wrong_oaep_hash=True
    else:raise AssertionError('wrong OAEP hash accepted')
    try:ek.private.decrypt(c,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=b'wrong'))
    except ValueError:wrong_label=True
    else:raise AssertionError('wrong library label accepted')
    try:sk.private.public_key().verify(s,signed,padding.PSS(mgf=padding.MGF1(hashes.SHA384()),salt_length=47),hashes.SHA384())
    except InvalidSignature:wrong_pss_salt=True
    else:raise AssertionError('wrong PSS salt policy accepted')
    structured=(int.from_bytes(c,'big')*pow(2,ek.e,ek.n)%ek.n).to_bytes(256,'big')
    try:decrypt_oaep(ek,structured)
    except ValueError:structured_change=True
    else:raise AssertionError('chosen multiplicative OAEP change accepted')
    try:verify_pss(sk,signed,(2).to_bytes(256,'big'))
    except InvalidSignature:raw_forgery_rejected=True
    else:raise AssertionError('raw signature guess accepted as PSS')
    try:ek.private.public_key().verify(s,signed,pss_parameters(),hashes.SHA384())
    except InvalidSignature:wrong_public_key=True
    else:raise AssertionError('wrong validation key accepted')
    for k in keys.values():
        for value in (0,1,k.p,k.q,k.n-1):assert crt_private_public(k,value)==pow(value,k.d,k.n)
    result={'environment':{'python':sys.version.split()[0],'cryptography':cryptography.__version__,'backend':backend.openssl_version_text(),'platform':platform.platform()},
        'public_fixtures_sha256':digest,'reused_aead_source_sha256':aead_sha,
        'fixture_key_bits':{purpose:key.n.bit_length() for purpose,key in keys.items()},'two_purpose_moduli_differ':ek.n!=sk.n,
        'toy':toy(),'RFC7520_PS384':{'signature_bytes':len(rfc_sig),'verify':True,'public_EM_hex':rfc_em.hex(),**rfc_inspect},
        'canonical_messages':{'OAEP_plaintext_hex':message.hex(),'PSS_signed_hex':signed.hex()},
        'fixed_PUBLIC_OAEP':{'hash':'SHA256','MGF1':'SHA256','label_hex':'','max_message_bytes':190,
            'encoded_hex':em.hex(),'ciphertext_hex':c.hex(),'inspect':inspection,'mature_decrypt':True,
            'one_low_bit_per_byte_rejections':oaep_rejections,'wrong_hash_rejected':wrong_oaep_hash,'wrong_library_label_rejected':wrong_label,
            'chosen_RSA_multiplication_rejected':structured_change},
        'fixed_PUBLIC_PSS':{'hash':'SHA384','MGF1':'SHA384','salt_bytes':48,'emBits':sk.n.bit_length()-1,
            'encoded_hex':ps.hex(),'signature_hex':s.hex(),'inspect':pss_inspection,'mature_verify':True,
            'one_low_bit_per_byte_rejections':pss_rejections,'wrong_salt_policy_rejected':wrong_pss_salt,'raw_s2_forgery_rejected':raw_forgery_rejected,'wrong_public_key_rejected':wrong_public_key},
        'randomized_mature_API_observations':{'two_ciphertexts_decrypt':True,'two_signatures_verify':True,
            'this_pair_ciphertexts_differ':ciphertexts[0]!=ciphertexts[1],'this_pair_signatures_differ':signatures[0]!=signatures[1],
            'scope':'finite samples, raw bytes in randomized-samples.json; not a randomness/security proof'},
        'not_proved':['factoring/RSA inversion equivalence','general IND-CCA or EUF-CMA security','constant time or side-channel resistance',
            'production credentials/key lifecycle','full TLS or general multisession AKE security']}
    samples={'WARNING':'PUBLIC fixture private keys; random encryption seeds/salts used only for these public messages',
        'ciphertexts_hex':[x.hex() for x in ciphertexts],'signatures_hex':[x.hex() for x in signatures],
        'interpretation':'fresh rerun generates different bytes; verify relations, do not require byte equality with old samples'}
    return result,samples


def generate(output):
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('fresh output required')
    if out==HERE or HERE in out.parents:raise ValueError('output outside source required')
    result,samples=checks();encoded=[json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n' for x in (result,samples)]
    out.mkdir(parents=True)
    for name,body in zip(('results.json','randomized-samples.json'),encoded):(out/name).write_text(body)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args();generate(args.output)
if __name__=='__main__':main()
