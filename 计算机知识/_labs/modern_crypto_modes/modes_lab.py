"""PUBLIC AES128/modes mechanics. Educational Python AES is NOT production crypto.
No secrets/network/timings. Inert stdlib import. Mature APIs + LibreSSL are oracles.
"""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys
from functools import lru_cache
from pathlib import Path
HERE=Path(__file__).resolve().parent
LIMIT=4096
COUNTERS=1<<128


def byte_integer(value):
    if type(value) is not int or not 0<=value<256:raise ValueError('native byte integer required')
    return value


def native_bytes(value,name,length=None,limit=LIMIT):
    if type(value) is not bytes or len(value)>limit or (length is not None and len(value)!=length):
        raise ValueError(name+': bounded native bytes with declared length required')
    return value


def native_bool(value):
    if type(value) is not bool:raise ValueError('native bool required')
    return value


def _mul(a,b):
    result=0
    for _ in range(8):
        if b&1:result^=a
        a=((a<<1)^((0x11b) if a&0x80 else 0))&255;b>>=1
    return result


def gf_mul(a,b):return _mul(byte_integer(a),byte_integer(b))


def _power(a,n):
    result=1
    while n:
        if n&1:result=_mul(result,a)
        a=_mul(a,a);n>>=1
    return result


@lru_cache(maxsize=1)
def tables():
    forward=[]
    for b in range(256):
        inverse=0 if b==0 else _power(b,254);value=0
        for i in range(8):
            bit=((inverse>>i)^(inverse>>((i+4)%8))^(inverse>>((i+5)%8))^
                 (inverse>>((i+6)%8))^(inverse>>((i+7)%8))^(0x63>>i))&1
            value|=bit<<i
        forward.append(value)
    if len(set(forward))!=256:raise AssertionError('Sbox is not bijective')
    backward=[0]*256
    for x,y in enumerate(forward):backward[y]=x
    return tuple(forward),tuple(backward)


def sub_bytes(state,inverse=False):
    native_bytes(state,'state',16);native_bool(inverse);table=tables()[int(inverse)]
    return bytes(table[b] for b in state)


def shift_rows(state,inverse=False):
    native_bytes(state,'state',16);native_bool(inverse)
    # s[r,c]=input[r+4*c], output[r,c]=input[r,c+r] for the forward transform.
    direction=-1 if inverse else 1
    return bytes(state[r+4*((c+direction*r)%4)] for c in range(4) for r in range(4))


def mix_column(column,inverse=False):
    native_bytes(column,'column',4);native_bool(inverse)
    matrix=((14,11,13,9),(9,14,11,13),(13,9,14,11),(11,13,9,14)) if inverse else ((2,3,1,1),(1,2,3,1),(1,1,2,3),(3,1,1,2))
    out=[]
    for row in matrix:
        value=0
        for a,b in zip(row,column):value^=_mul(a,b)
        out.append(value)
    return bytes(out)


def mix_columns(state,inverse=False):
    native_bytes(state,'state',16);native_bool(inverse)
    return b''.join(mix_column(state[j:j+4],inverse) for j in range(0,16,4))


def xor(a,b):
    native_bytes(a,'left');native_bytes(b,'right')
    if len(a)!=len(b):raise ValueError('equal byte lengths required')
    return bytes(x^y for x,y in zip(a,b))


def expand_key(key):
    native_bytes(key,'AES128 key',16);sbox=tables()[0];words=[key[j:j+4] for j in range(0,16,4)];rcon=1
    for i in range(4,44):
        temp=words[-1]
        if i%4==0:
            temp=bytes(sbox[x] for x in temp[1:]+temp[:1]);temp=bytes([temp[0]^rcon])+temp[1:];rcon=_mul(rcon,2)
        words.append(xor(words[i-4],temp))
    return tuple(b''.join(words[4*r:4*r+4]) for r in range(11))


def encrypt_trace(key,block):
    native_bytes(key,'AES128 key',16);native_bytes(block,'block',16);keys=expand_key(key);events=[]
    state=xor(block,keys[0]);events.append({'round':0,'stage':'AddRoundKey','state':state.hex()})
    for r in range(1,11):
        state=sub_bytes(state);events.append({'round':r,'stage':'SubBytes','state':state.hex()})
        state=shift_rows(state);events.append({'round':r,'stage':'ShiftRows','state':state.hex()})
        if r!=10:
            state=mix_columns(state);events.append({'round':r,'stage':'MixColumns','state':state.hex()})
        state=xor(state,keys[r]);events.append({'round':r,'stage':'AddRoundKey','state':state.hex()})
    return events


def aes_encrypt(key,block):return bytes.fromhex(encrypt_trace(key,block)[-1]['state'])


def aes_decrypt(key,block):
    native_bytes(key,'AES128 key',16);native_bytes(block,'block',16);keys=expand_key(key);state=xor(block,keys[10])
    for r in range(9,0,-1):
        state=shift_rows(state,True);state=sub_bytes(state,True);state=xor(state,keys[r]);state=mix_columns(state,True)
    return xor(sub_bytes(shift_rows(state,True),True),keys[0])


def block_inputs(key,data):
    native_bytes(key,'AES128 key',16);native_bytes(data,'block data')
    if len(data)%16:raise ValueError('whole blocks required; no implicit padding')


def ecb(key,data,decrypt=False):
    block_inputs(key,data);native_bool(decrypt);fun=aes_decrypt if decrypt else aes_encrypt
    return b''.join(fun(key,data[j:j+16]) for j in range(0,len(data),16))


def cbc(key,iv,data,decrypt=False):
    block_inputs(key,data);native_bytes(iv,'CBC IV',16);native_bool(decrypt);previous=iv;out=[]
    for j in range(0,len(data),16):
        block=data[j:j+16]
        if decrypt:out.append(xor(aes_decrypt(key,block),previous));previous=block
        else:previous=aes_encrypt(key,xor(block,previous));out.append(previous)
    return b''.join(out)


def counter_span(start,data):
    native_bytes(data,'CTR data')
    if type(start) is not int or not 0<=start<COUNTERS:raise ValueError('native unsigned 128-bit counter integer required')
    count=(len(data)+15)//16
    if start+count>COUNTERS:raise ValueError('counter range exhausted; no wrap')
    return start,start+count


def ctr(key,start,data):
    native_bytes(key,'AES128 key',16);counter_span(start,data);out=[]
    for offset in range(0,len(data),16):
        block=data[offset:offset+16];stream=aes_encrypt(key,(start+offset//16).to_bytes(16,'big'))
        out.append(xor(block,stream[:len(block)]))
    return b''.join(out)


def library(mode,key,data,parameter=None,decrypt=False):
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    if type(mode) is not str or mode not in ('ECB','CBC','CTR'):raise ValueError('known mode required')
    native_bytes(key,'AES128 key',16);native_bytes(data,'data');native_bool(decrypt)
    if mode in ('ECB','CBC'):block_inputs(key,data)
    if mode=='ECB':
        if parameter is not None:raise ValueError('ECB has no parameter')
        selected=modes.ECB()
    elif mode=='CBC':selected=modes.CBC(native_bytes(parameter,'CBC IV',16))
    else:counter_span(parameter,data);selected=modes.CTR(parameter.to_bytes(16,'big'))
    cipher=Cipher(algorithms.AES(key),selected);worker=cipher.decryptor() if decrypt else cipher.encryptor()
    return worker.update(data)+worker.finalize()


class CTRRangeGuardDemo:
    """In-memory half-open intervals only; not a nonce allocator/durable protocol.
    Records ranges only after all validation and successful mature-library encryption.
    """
    def __init__(self,key):self.key=native_bytes(key,'AES128 key',16);self.used=[]
    def encrypt(self,start,data):
        begin,end=counter_span(start,data)
        if any(max(begin,a)<min(end,b) for a,b in self.used):raise ValueError('counter range overlaps previous encryption')
        result=library('CTR',self.key,data,start)
        if begin!=end:self.used.append((begin,end))
        return result


def openssl_check(binary,mode,key,data,parameter=None,decrypt=False):
    # Only used with this lesson's PUBLIC fixed vectors, never live secrets.
    args=[str(binary),'enc','-aes-128-'+mode.lower(),'-K',key.hex(),'-nopad','-nosalt']
    if parameter is not None:args+=['-iv',parameter.hex() if type(parameter) is bytes else parameter.to_bytes(16,'big').hex()]
    if decrypt:args+=['-d']
    result=subprocess.run(args,input=data,capture_output=True,timeout=10,check=True)
    return result.stdout


def vectors():
    raw=(HERE/'public-vectors.json').read_bytes();v=json.loads(raw)
    if v.get('schema')!='wwl-aes128-modes-public-v1':raise ValueError('known public vectors required')
    return v,hashlib.sha256(raw).hexdigest()


def changed_indices(a,b):return [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]


def checks(binary):
    import cryptography
    from cryptography.hazmat.backends.openssl.backend import backend
    v,digest=vectors();raw=lambda name:bytes.fromhex(v[name]);key=raw('key');plain=raw('plaintext');iv=raw('cbc_iv');start=int(v['ctr_initial'],16)
    trace=encrypt_trace(key,plain[:16]);by_event={str(x['round'])+'.'+x['stage']:x['state'] for x in trace}
    for event,expected in v['first_block_round_checks'].items():assert by_event[event]==expected
    assert expand_key(key)[1].hex()==v['round1_key']
    table=tables()[0];assert gf_mul(0x57,0x13)==0xfe and table[0x53]==0xed
    mode_results={}
    for mode,parameter,encrypt,decrypt in (('ECB',None,lambda x:ecb(key,x),lambda x:ecb(key,x,True)),
            ('CBC',iv,lambda x:cbc(key,iv,x),lambda x:cbc(key,iv,x,True)),
            ('CTR',start,lambda x:ctr(key,start,x),lambda x:ctr(key,start,x))):
        expected=raw(mode);c=encrypt(plain)
        assert c==expected and decrypt(c)==plain
        assert library(mode,key,plain,parameter)==expected and library(mode,key,expected,parameter,True)==plain
        assert openssl_check(binary,mode,key,plain,parameter)==expected and openssl_check(binary,mode,key,expected,parameter,True)==plain
        mode_results[mode]={'ciphertext':c.hex(),'teaching_encrypt_decrypt':True,'cryptography_encrypt_decrypt':True,'openssl_encrypt_decrypt':True}
    assert ctr(key,start,plain[:31])==raw('CTR')[:31]==library('CTR',key,plain[:31],start)
    # Equality leak, not a cryptographic forgery.
    repeated=plain[:16]*2;ec=library('ECB',key,repeated);assert ec[:16]==ec[16:]
    # Predictable next CBC IV permits matching a previous cipher input.
    next_iv=(int.from_bytes(iv,'big')+1).to_bytes(16,'big');chosen=xor(xor(plain[:16],iv),next_iv)
    c0=library('CBC',key,plain[:16],iv);cchosen=library('CBC',key,chosen,next_iv);assert c0==cchosen
    delta=b'\x01'+bytes(15);altered_iv=xor(iv,delta);iv_dec=library('CBC',key,raw('CBC'),altered_iv,True)
    assert iv_dec==xor(plain[:16],delta)+plain[16:]
    changed_c=xor(raw('CBC')[:16],delta)+raw('CBC')[16:];bad=library('CBC',key,changed_c,iv,True)
    assert bad[:16]!=plain[:16] and bad[16:32]==xor(plain[16:32],delta) and bad[32:]==plain[32:]
    ctr_changed=bytearray(raw('CTR'));ctr_changed[17]^=4;ctr_dec=library('CTR',key,bytes(ctr_changed),start,True)
    assert changed_indices(plain,ctr_dec)==[17] and plain[17]^ctr_dec[17]==4
    p1=b'amount=0100';p2=b'amount=0900';r1=library('CTR',key,p1,start);r2=library('CTR',key,p2,start)
    assert xor(r1,r2)==xor(p1,p2)
    # Different starting counters still overlap: first call consumes 7 and 8.
    guard=CTRRangeGuardDemo(key);guard.encrypt(7,bytes(32));before=list(guard.used)
    try:guard.encrypt(8,bytes(16))
    except ValueError:overlap_rejected=True
    else:raise AssertionError('overlapping CTR ranges accepted')
    assert guard.used==before
    try:guard.encrypt(COUNTERS-1,bytes(17))
    except ValueError:wrap_rejected=True
    else:raise AssertionError('exhausted CTR range accepted')
    assert guard.used==before
    after_restart=CTRRangeGuardDemo(key).encrypt(7,bytes(32))==library('CTR',key,bytes(32),7)
    version=subprocess.run([str(binary),'version'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    return {'environment':{'python':sys.version.split()[0],'cryptography':cryptography.__version__,
            'backend':backend.openssl_version_text(),'independent_cli':version,'platform':platform.platform()},
        'vectors_sha256':digest,'gf':{'57_times_13':'fe','Sbox_53':'ed','Sbox_0_1_2_3':[f'{table[i]:02x}' for i in range(4)],
            'Sbox_is_permutation':len(set(table))==256},
        'round_keys':[x.hex() for x in expand_key(key)],'first_block_40_stage_trace':trace,'NIST_modes':mode_results,
        'CTR_partial_31byte_exact':True,'ECB_repeated_blocks_equal':True,
        'CBC_predictable_IV':{'next_iv':next_iv.hex(),'chosen_plaintext':chosen.hex(),'ciphertext_matches_reference':True},
        'CBC_IV_flip':{'decrypted_hex':iv_dec.hex(),'changed_byte_indices':changed_indices(plain,iv_dec)},
        'CBC_C1_flip':{'decrypted_hex':bad.hex(),'changed_byte_indices':changed_indices(plain,bad),
            'P1_changed_bits':sum((a^b).bit_count() for a,b in zip(plain[:16],bad[:16])),
            'P2_exact_flip':True,'P3_P4_unchanged':True,'authentication_rejection':'none: raw CBC returns bytes'},
        'CTR_ciphertext_flip':{'changed_byte_indices':[17],'xor_delta':4,'authentication_rejection':'none: raw CTR returns bytes'},
        'CTR_reuse_PUBLIC':{'plaintext_xor':xor(p1,p2).hex(),'ciphertext_xor':xor(r1,r2).hex()},
        'CTR_ranges':{'first_reserved_half_open':[7,9],'different_start_8_overlap_rejected':overlap_rejected,
            'wrap_rejected_before_state_change':wrap_rejected,'new_guard_reuses_range':after_restart},
        'not_proved':['PRP/PRF security','general IND-CPA or CCA security','constant time or side-channel resistance',
            'production IV generation','durable/concurrent counter uniqueness','message authenticity']}


def generate(output,binary):
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('fresh output required')
    if out==HERE or HERE in out.parents:raise ValueError('output outside source required')
    result=checks(binary);body=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    out.mkdir(parents=True);(out/'results.json').write_text(body);return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--openssl',default=shutil.which('openssl'));args=p.parse_args()
    if args.openssl is None:raise RuntimeError('independent openssl CLI required; pass --openssl path')
    generate(args.output,args.openssl)
if __name__=='__main__':main()
