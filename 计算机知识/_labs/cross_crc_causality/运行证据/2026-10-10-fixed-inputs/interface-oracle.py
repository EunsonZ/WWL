from pathlib import Path
import json,importlib.util,copy
P=Path(__file__).resolve().parent;lab=P/'snapshot/计算机知识/_labs/cross_crc_causality';s=importlib.util.spec_from_file_location('bound_crc',lab/'crc.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);config=json.loads((lab/'crc_inputs.json').read_text());rows=[]
def must_reject(name,call):
 try:call()
 except ValueError as e:rows.append({'case':name,'expected_exception':'ValueError','actual':str(e)})
 else:raise AssertionError(name)
for name,call in [('zero generator',lambda:m.remainder(1,0)),('negative dividend',lambda:m.remainder(-1,11)),('boolean dividend',lambda:m.remainder(True,11)),('negative burst',lambda:m.burst_span(-1)),('CRC32 text instead of bytes',lambda:m.crc32_iso_hdlc('hi'))]:must_reject(name,call)
for name,key,value in [('constant-term zero','generator','1010'),('unsupported enumeration length','codeword_width',17),('mismatched codeword length','codeword_width',6),('generator leading zero','generator','01011'),('unequal alternate degree','alternate_generator','11'),('invalid bits','message','110x'),('empty message','message','')]:
 c=copy.deepcopy(config);c[key]=value;must_reject(name,lambda c=c:m.run(c))
zero=copy.deepcopy(config);zero['message']='0000';out=m.run(zero);assert out['codeword']=='0000000' and out['check_bits']=='000';assert m.burst_span(0)==0
rows.append({'case':'zero message and error','codeword':out['codeword'],'check_bits':out['check_bits'],'zero_error_span':0})
(P/'interface-results.json').write_text(json.dumps({'rows':rows,'scope':'Declared fixed API rejection cases; not exhaustive input safety or a TINY parser run.'},indent=2)+'\n');print(json.dumps(rows,indent=2))
