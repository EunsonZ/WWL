"""Independent bit packing and finite external expectations, no EXPECTED_P/Q access."""
import hashlib,importlib.util,itertools,json,pathlib,resource,sys
OUT=pathlib.Path(__file__).resolve().parent;ROOT=OUT.parents[3]
SOURCE=ROOT/'.wwl-recovery/2026-10-10-crash/assembled-candidates/information-r1/数学/50-信息论/80-运行证据/information_container_practice.py'
spec=importlib.util.spec_from_file_location('ic_candidate',SOURCE);lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
P={'A':'0','B':'10','C':'110','D':'111'};Q={'A':'00','B':'01','C':'10','D':'11'};MESSAGE='AAAABBCD'
def reseal(body):
    checksum=0
    for value in body:checksum=(checksum+value)&255
    return bytes(body)+bytes((checksum,))
def serialize(message,code):
    # Accumulate each bit into its byte's explicitly indexed high-to-low position.
    stream=[int(bit) for ch in message for bit in code[ch]]
    payload=bytearray((len(stream)+7)//8)
    for index,bit in enumerate(stream):payload[index//8]|=bit<<(7-index%8)
    fields=[73,67,1,4,len(message),len(stream)]
    for s in 'ABCD':
        value=0
        for bit in code[s]:value=2*value+(bit=='1')
        fields.extend((ord(s),len(code[s]),value))
    return reseal(fields+list(payload)), ''.join(map(str,stream))
def read_known(blob,code):
    # Parse via a code trie using bytes/bit positions; independent of library string scans.
    trie={}
    for s,word in code.items():
        node=trie
        for bit in word:node=node.setdefault(int(bit),{})
        node['symbol']=s
    node=trie;decoded=[]
    for i in range(blob[5]):
        node=node[(blob[18+i//8]>>(7-i%8))&1]
        if 'symbol' in node:decoded.append(node['symbol']);node=trie
    assert node is trie
    return ''.join(decoded)
actual=json.loads((OUT/'default.stdout').read_text());fixed={};rows={}
for label,code,bitcount,pad in [('P',P,14,2),('Q',Q,16,0)]:
    blob,bits=serialize(MESSAGE,code)
    assert lib.encode(MESSAGE,code)==blob
    assert lib.decode(blob)==read_known(blob,code)==MESSAGE
    row=actual['rows'][label]
    expectation=dict(decoded=MESSAGE,hex=blob.hex(' '),effective_bits=bitcount,padding_bits=pad,model_bytes=12,header_bytes=6,checksum_bytes=1,payload_bytes=2,file_bytes=21,file_bits=168,repeated_channel_bits=336,data_symbols=168,sync_symbols=8,pilot_symbols=4,total_symbols=180,symbol_rate_per_second=1000,transmit_seconds=.180,without_repeat_total_symbols=96)
    assert row==expectation,(label,row,expectation)
    rows[label]=expectation
    fixed[label]=dict(message=MESSAGE,code=code,effective_bitstring=bits,container_hex=blob.hex(' '),field_sums=dict(header=sum(blob[:6]),table=sum(blob[6:18]),payload=sum(blob[18:-1]),total_without_checksum=sum(blob[:-1])),checksum=blob[-1],without_repeat_seconds=.096)
p=bytes.fromhex(fixed['P']['container_hex']);q=bytes.fromhex(fixed['Q']['container_hex'])
changed=bytearray(q);changed[18]=1;changed[19]=90
assert sum(changed[:-1])%256==q[-1]
assert read_known(changed,Q)==lib.decode(bytes(changed))=='AAABBBCC'
assert actual['accepted_sum8_collision']=='AAABBBCC'
short=[]
for length in range(1,5):
    for chars in itertools.product('ABCD',repeat=length):
        message=''.join(chars)
        for label,code in [('P',P),('Q',Q)]:
            expected,_=serialize(message,code);encoded=lib.encode(message,code)
            assert encoded==expected and lib.decode(expected)==read_known(expected,code)==message
            short.append(dict(message=message,code_label=label,expected_hex=expected.hex()))
errors=[]
def reject(name,func,*args):
    try:func(*args)
    except ValueError as exc:reason=str(exc)
    else:raise AssertionError('accepted invalid case '+name)
    errors.append(dict(name=name,reason=reason,input_hex=args[0].hex() if isinstance(args[0],bytes) else None,input_message=args[0] if isinstance(args[0],str) else None,input_code=args[1] if len(args)>1 else None))
def mutate(index,value,base=p):
    body=bytearray(base[:-1]);body[index]=value;return reseal(body)
bad=bytearray(p);bad[18]^=128
reject('unresealed_payload_flip',lib.decode,bytes(bad))
reject('resealed_nonzero_padding',lib.decode,mutate(19,p[19]|1))
reject('resealed_prefix_conflict',lib.decode,mutate(11,0))
reject('resealed_wrong_count_too_many',lib.decode,mutate(4,7))
reject('resealed_wrong_count_too_few',lib.decode,mutate(4,9))
truncated=bytearray(p[:18]);truncated[4:6]=bytes([1,2]);truncated.append(192)
reject('resealed_truncated_codeword',lib.decode,reseal(truncated))
reject('trailing_byte',lib.decode,p+bytes([0]))
reject('short_container',lib.decode,p[:19])
reject('long_container',lib.decode,p+bytes(31))
reject('zero_message_count',lib.decode,mutate(4,0))
reject('zero_effective_bits',lib.decode,mutate(5,0))
reject('declared_payload_size',lib.decode,mutate(5,8))
reject('table_wrong_order',lib.decode,mutate(6,66))
reject('table_zero_code_length',lib.decode,mutate(7,0))
reject('table_nine_code_length',lib.decode,mutate(7,9))
reject('code_value_exceeds_declared_width',lib.decode,mutate(8,2))
reject('wrong_version',lib.decode,mutate(2,2))
reject('empty_message',lib.encode,'',P)
reject('message_count_256',lib.encode,'A'*256,P)
reject('payload_bits_256',lib.encode,'A'*128,Q)
reject('outside_alphabet',lib.encode,'E',P)
reject('duplicate_codeword',lib.encode,'A',dict(P,B='0'))
reject('prefix_conflict_encode',lib.encode,'A',dict(P,B='01'))
reject('empty_codeword',lib.encode,'A',dict(P,A=''))
reject('nine_bit_codeword',lib.encode,'A',dict(P,A='0'*9))
accepted_boundaries=[]
for name,message,code in [('one_symbol','A',P),('max_count_and_payload','A'*255,P),('fixed_254_bits','A'*127,Q),('eight_bit_codeword','D'*31,dict(zip('ABCD',('00000000','00000001','00000010','00000011'))))]:
    blob,_=serialize(message,code);assert lib.encode(message,code)==blob and lib.decode(blob)==message
    accepted_boundaries.append(dict(name=name,message=message,code=code,hex=blob.hex(),file_bytes=len(blob),count=blob[4],effective_bits=blob[5]))
assert len(serialize('A'*255,P)[0])==51
default_rejections=set(actual['rejected_inputs'])
assert default_rejections=={'unresealed_payload_flip','resealed_nonzero_padding','resealed_prefix_conflict','resealed_wrong_count','resealed_truncated_codeword','trailing_byte'}
inputs=dict(format='IC v1: magic IC,version1,four ordered table items,count/bit_count u8; MSB first payload; zero pad; sum8',fixed=fixed,collision=dict(original_payload_hex='005b',mutated_payload_hex='015a',unchanged_checksum=q[-1],container_hex=bytes(changed).hex(),decoded='AAABBBCC'),short_message_enumeration=dict(alphabet='ABCD',lengths=[1,2,3,4],code_labels=['P','Q'],cases=short),reject_cases=errors,accepted_boundaries=accepted_boundaries,symbol_budget=dict(file_bits=168,repetition_rate='1/2',bits_per_symbol=2,sync=8,pilot=4,rate_symbols_per_second=1000,with_repetition=dict(channel_bits=336,data_symbols=168,total_symbols=180,seconds=.180),without_repetition=dict(channel_bits=168,data_symbols=84,total_symbols=96,seconds=.096)))
(OUT/'fixed-inputs-and-results.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
result=dict(status='pass',current_source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),default_rows=rows,enumerated_messages_per_code=340,total_finite_encode_decode_cases=len(short),rejected_cases=len(errors),accepted_boundary_cases=len(accepted_boundaries),collision='AAABBBCC',oracle_independence='Bitwise indexed packing and code trie from separately stated P/Q codewords; no access to candidate EXPECTED_P/Q or run() and no historical oracle execution',self_max_rss_bytes_macos=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scope='Finite serializer/decoder cases and symbolic budgets only; no physical channel or BER/error-correction claim')
(OUT/'independent-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
