"""Independent GF2 syndrome matrix and Boolean reflected CRC32 register.
No CRC lab or author-verifier import; no author expected JSON reads.
"""
from pathlib import Path
from collections import Counter
import json,sys,zlib,binascii,struct,hashlib
P=Path(__file__).resolve().parent
LAB=P/'snapshot/计算机知识/_labs/cross_crc_causality'
def exponents(bits):return {i for i,b in enumerate(reversed(bits)) if b=='1'}
def multiply(a,b):
 result=set()
 for i in a:
  for j in b:result.symmetric_difference_update({i+j})
 return result
def monomial_columns(generator,width):
 g=exponents(generator);degree=max(g);relation=g-{degree};cols=[{0}]
 for k in range(1,width):
  shifted={e+1 for e in cols[-1]}
  if degree in shifted:shifted.remove(degree);shifted.symmetric_difference_update(relation)
  cols.append(shifted)
 return cols

def syndrome(bits,g='1011'):
 cols=monomial_columns(g,len(bits));answer=set()
 for e in exponents(bits):answer.symmetric_difference_update(cols[e])
 return sum(2**e for e in answer)
def span(bits):return 0 if '1' not in bits else len(bits.strip('0'))
def reflect32(poly):return int(f'{poly:032b}'[::-1],2)
POLY=reflect32(0x04C11DB7);assert POLY==0xEDB88320
TAPS={i for i in range(32) if (POLY>>i)&1}
def crc32_bool(data):
 register=[1]*32
 for byte in data:
  for bit in range(8):
   feedback=register[0]^((byte>>bit)&1)
   register=register[1:]+[0]
   if feedback:
    for i in TAPS:register[i]^=1
 return sum((1-v)<<i for i,v in enumerate(register))
def xorbits(a,b):return ''.join(str(int(x)^int(y)) for x,y in zip(a,b))
def expectation():
 r=syndrome('1101000');cw='1101'+format(r,'03b');errors=[]
 for e in range(1,128):
  bits=f'{e:07b}';recv=xorbits(cw,bits)
  errors.append({'error':bits,'span':span(bits),'received':recv,'remainder':syndrome(bits),'received_remainder':syndrome(recv),'alternate_remainder':syndrome(bits,'1001')})
 vectors=[]
 for name,data in [('standard-check',b'123456789'),('tiny-hi',b'hi'),('empty',b'')]:
  value=crc32_bool(data);assert value==zlib.crc32(data)==binascii.crc32(data)
  vectors.append({'name':name,'payload_hex':data.hex(),'checksum_hex':f'{value:08X}','little_endian_hex':struct.pack('<I',value).hex()})
 return {'message_remainder':r,'check_bits':format(r,'03b'),'codeword':cw,'codeword_remainder':syndrome(cw),'errors':errors,'crc32_vectors':vectors}
def run():
 wanted=expectation();actual=json.loads((P/'crc.stdout').read_text())
 for key,value in wanted.items():assert actual[key]==value,(key,actual[key],value)
 rows=wanted['errors'];short=[row for row in rows if row['span']<=3]
 assert len(short)==23 and all(row['remainder'] and row['alternate_remainder'] for row in short)
 missed=[row['error'] for row in rows if row['remainder']==0];assert len(missed)==15
 byspan={i:{'count':sum(row['span']==i for row in rows),'missed':sum(row['span']==i and row['remainder']==0 for row in rows)} for i in range(1,8)}
 assert syndrome('0000001')==1 and syndrome('0001011')==0
 assert syndrome('0001010')==syndrome('0000001')==1
 # Exact finite matrix linearity, all pairs of 7-bit vectors, no arbitrary-polynomial division.
 for a in range(128):
  for b in range(128):assert syndrome(f'{a^b:07b}')==syndrome(f'{a:07b}')^syndrome(f'{b:07b}')
 cols=monomial_columns('1011',7);single={syndrome(f'{1<<k:07b}'):k for k in range(7)};assert len(single)==7 and 0 not in single
 codeword=int(wanted['codeword'],2);decoded=[]
 for k in range(7):
  received=codeword^(1<<k);syn=syndrome(f'{received:07b}');corrected=received^(1<<single[syn]);assert corrected==codeword;decoded.append({'flipped_position_from_lsb':k,'syndrome':syn,'corrected':f'{corrected:07b}'})
 product=multiply({0,1},{0,1,2});assert product=={0,3} and syndrome('1001','1001')==0 and syndrome('11','1001')!=0 and syndrome('111','1001')!=0
 # Fixed length CRC32 is affine, unlike zero-initial toy polynomial syndrome.
 a=bytes.fromhex('0100');b=bytes.fromhex('0001');axorb=bytes(x^y for x,y in zip(a,b));offset=crc32_bool(b'\0\0');assert crc32_bool(axorb)^crc32_bool(a)^crc32_bool(b)==offset!=0
 frame=bytes.fromhex('54 49 4e 59 01 00 00 00 18 00 00 00 02 00 00 00 ac 2a 93 d8 00 00 00 00 68 69')
 magic,version,flags,off,length,check=struct.unpack('<4sHHIII',frame[:20]);payload=frame[off:off+length]
 assert (magic,version,flags,off,length)==(b'TINY',1,0,24,2) and payload==b'hi' and check==crc32_bool(payload)
 # Tamper preserves syntactic layout; replacing payload/check defeats authenticity while retaining CRC agreement.
 forged=bytearray(frame);forged[25]=ord('o');newcheck=crc32_bool(bytes(forged[24:26]));forged[16:20]=struct.pack('<I',newcheck)
 assert forged!=frame and int.from_bytes(forged[16:20],'little')==zlib.crc32(bytes(forged[24:26]))
 (P/'tiny-original.bin').write_bytes(frame);(P/'tiny-forged-recomputed.bin').write_bytes(forged)
 # Header/padding are outside CRC coverage; this says nothing about header validity.
 padding=bytearray(frame);padding[20]=255;assert crc32_bool(bytes(padding[24:26]))==check
 r={'syndrome_matrix_columns_lsb_first':[sum(1<<e for e in c) for c in cols],'rows_checked':127,'short_bursts_checked':len(short),'bursts_by_span':byspan,'nonzero_kernel':missed,'kernel_total_including_zero':16,'linearity_pairs_checked':128*128,'single_flip_external_decoder':decoded,'single_flip_boundary':'CRC itself only provides syndrome; this external decoder additionally assumes at most one erroneous bit. Multi-bit error0001010 collides with0000001.','zero_divisor_example':{'generator':'1001','nonzero_factors':['11','111'],'product':'1001','product_remainder':0},'real_crc32':wanted['crc32_vectors'],'crc32_model':{'width':32,'poly_normal':'04C11DB7','poly_reflected':'EDB88320','init':'FFFFFFFF','xorout':'FFFFFFFF','refin':True,'refout':True,'toy_order':'MSB highest polynomial degree; no init/final xor'},'affine_counterexample':{'a_hex':a.hex(),'b_hex':b.hex(),'checksum_xor_difference':f'{offset:08X}','zero_bytes_crc':f'{crc32_bool(bytes(2)):08X}'},'TINY_actual_published_example':{'source_snapshot':'published-TINY-source.md','frame_hex':frame.hex(),'coverage':[24,26],'payload_crc':'D8932AAC','stored_little_endian':'ac2a93d8','forged_frame_hex':bytes(forged).hex(),'forged_payload':bytes(forged[24:26]).decode('ascii'),'forged_checksum':f'{newcheck:08X}','forgery_crc_check_passes':True,'padding_changes_not_covered':True,'scope':'Own synthetic frames from actual published layout; no published parser or real transport executed.'},'scope':'Finite fixed seven-bit errors and Boolean CRC32 vectors; no infinite theorem, authenticity, general parser safety or hardware result.'}
 return r
if __name__=='__main__':
 result=expectation() if sys.argv[1]=='prepare' else run();name='expectations-before-run.json' if sys.argv[1]=='prepare' else 'independent-results.json';text=json.dumps(result,indent=2)+'\n';(P/name).write_text(text);print(text)
