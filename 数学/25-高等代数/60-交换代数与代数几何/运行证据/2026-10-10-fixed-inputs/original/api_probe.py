"""Calls only snapshot API; expectations are checked by independent_oracle.py."""
import sys,pathlib,json,itertools,copy
from fractions import Fraction as F
root=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(root/'snapshot/code'))
import affine_exact as a
P=a.Poly; observed=[]
def encode(v):
    if isinstance(v,P):return v.encode()
    if isinstance(v,F):return str(v)
    if isinstance(v,(list,tuple)):return [encode(x) for x in v]
    if isinstance(v,dict):return {k:encode(x) for k,x in v.items()}
    return v
def probe(name,fn,expected='value'):
    try:r=fn();observed.append({'name':name,'expected_kind':expected,'kind':'value','value':encode(r)})
    except Exception as e:observed.append({'name':name,'expected_kind':expected,'kind':'exception','exception':type(e).__name__,'message':str(e)})
z=P(2);x=P.variable(2,0);y=P.variable(2,1);one=P.constant(2,1)
for name,fn in [
('n0',lambda:P(0)),('n4',lambda:P(4)),('n_bool',lambda:P(True)),('n_float',lambda:P(2.0)),('terms_list',lambda:P(2,[])),
('exp_bool',lambda:P(2,{(True,0):1})),('exp_float',lambda:P(2,{(1.0,0):1})),('exp_negative',lambda:P(2,{(-1,0):1})),('exp_shape',lambda:P(2,{(1,):1})),('exp_nontuple',lambda:P(2,{'x':1})),
('coeff_bool',lambda:P(2,{(0,0):True})),('coeff_float',lambda:P(2,{(0,0):0.5})),
('degree65',lambda:P(2,{(65,0):1})),('num4097bits',lambda:P(1,{(0,):1<<4096})),('den4097bits',lambda:P(1,{(0,):F(1,1<<4096)})),
('terms257',lambda:P(2,{e:1 for e in list(itertools.islice(((i,j) for i in range(65) for j in range(65-i)),257))})),
('leading_zero',lambda:z.leading()),('divide_zero_divisor',lambda:a.divide(x,[z])),('divide_empty',lambda:a.divide(x,[])),('divide9',lambda:a.divide(x,[x]*9)),('divide_bad_container',lambda:a.divide(x,{0:x})),('divide_bad_f',lambda:a.divide(1,[x])),('divide_shape',lambda:a.divide(x,[P(1)])),
('add_shape',lambda:x+P(1)),('multiply_shape',lambda:x*P(3)),('power_bool',lambda:x.power(True)),('power_float',lambda:x.power(1.0)),('power_negative',lambda:x.power(-1)),('power13',lambda:x.power(13)),
('derivative_index_bool',lambda:x.derivative(True)),('variable_index2',lambda:P.variable(2,2)),('eval_short',lambda:x.evaluate([1])),('eval_float',lambda:x.evaluate([1.,0])),('eval_bool',lambda:x.evaluate([True,0])),
('substitute_short',lambda:x.substitute([P(1)])),('substitute_badtype',lambda:x.substitute([P(1),1])),('substitute_shape',lambda:x.substitute([P(1),P(2)])),('substitute_exp13',lambda:P(1,{(13,):1}).substitute([P.variable(1,0)])),('homogeneous4vars',lambda:P(3).homogenize()),
('rank_ragged',lambda:a.rank([[1],[1,2]],2)),('rank_float',lambda:a.rank([[1.,2]],2)),('rank_bool',lambda:a.rank([[True]],1)),('rank_cols4',lambda:a.rank([],4)),('rank_colsbool',lambda:a.rank([],True)),('rank_rows9',lambda:a.rank([[1]]*9,1)),('rank_tuple',lambda:a.rank(((1,),),1))]:probe(name,fn,'ValueError')
probe('empty',lambda:P(2));probe('zero_coeff',lambda:P(2,{(1,2):0}));probe('degree64',lambda:P(2,{(64,0):1}));probe('num4096bits',lambda:P(1,{(0,):(1<<4095)}));probe('den4096bits',lambda:P(1,{(0,):F(1,1<<4095)}));probe('terms256',lambda:P(2,{e:1 for e in list(itertools.islice(((i,j) for i in range(65) for j in range(65-i)),256))}));probe('zero_dividend',lambda:a.divide(z,[x]));probe('divide8',lambda:a.divide(x,[x]*8));probe('rank_empty',lambda:a.rank([],3));probe('rank_empty_rows',lambda:a.rank([[],[]],0));probe('power0',lambda:z.power(0));probe('power12',lambda:x.power(12))
record={'variables':2,'terms':[{'powers':[1,0],'numerator':1,'denominator':1}]}
for name,mut in [('decode_bool_n',lambda r:r.update(variables=True)),('decode_exp13',lambda r:r['terms'][0].update(powers=[13,0])),('decode_exp_bool',lambda r:r['terms'][0].update(powers=[True,0])),('decode_num_bool',lambda r:r['terms'][0].update(numerator=True)),('decode_num_float',lambda r:r['terms'][0].update(numerator=1.)),('decode_den0',lambda r:r['terms'][0].update(denominator=0)),('decode_num1000001',lambda r:r['terms'][0].update(numerator=1000001)),('decode_den1000001',lambda r:r['terms'][0].update(denominator=1000001)),('decode_duplicate',lambda r:r['terms'].append(copy.deepcopy(r['terms'][0]))),('decode_fields',lambda r:r.update(extra=1)),('decode_129terms',lambda r:r.update(terms=[{'powers':[i//13,i%13],'numerator':1,'denominator':1} for i in range(129)]))]:
    r=copy.deepcopy(record);mut(r);probe(name,lambda r=r:a.decode(r),'ValueError')
probe('decode_max',lambda:a.decode({'variables':2,'terms':[{'powers':[12,12],'numerator':1000000,'denominator':1000000}]}))
probe('decode_128terms',lambda:a.decode({'variables':2,'terms':[{'powers':[i//13,i%13],'numerator':1,'denominator':1} for i in range(128)]}))
fixed=json.loads((root/'snapshot/code/fixed-inputs.json').read_text())
for name,mut in [('fixed_changed_polynomial',lambda r:r['polynomials']['f']['terms'][0].update(numerator=2)),('fixed_changed_points',lambda r:r['points'].update(origin=[1,0])),('fixed_bool_point',lambda r:r['points'].update(origin=[False,0])),('fixed_float_point',lambda r:r['points'].update(origin=[0.,0])),('fixed_unknown_field',lambda r:r.update(extra=0))]:
    r=copy.deepcopy(fixed);mut(r);probe(name,lambda r=r:a.fixed_report(r),'ValueError')
# A lowered in-memory guard exercises the exact step-stop branch without editing source.
probe('MAX_STEPS_published',lambda:a.MAX_STEPS)
f=x.power(3)-one;g=x-one
for limit in [2,3]:
    a.MAX_STEPS=limit;probe('step_limit_'+str(limit),lambda:a.divide(f,[g]),'ValueError' if limit==2 else 'value')
a.MAX_STEPS=2000
p=P(2,{(2,0):F(3,2),(1,1):-2,(0,0):F(1,3)});q=P(2,{(1,0):-1,(0,2):3,(0,0):2})
for name,fn in [('p',lambda:p),('q',lambda:q),('sum',lambda:p+q),('product',lambda:p*q),('dx',lambda:p.derivative(0)),('dy',lambda:p.derivative(1)),('eval',lambda:p.evaluate([F(2,3),F(-3,5)])),('substitution',lambda:p.substitute([P(1,{(1,):1,(0,):1}),P(1,{(2,):1})])),('division_order1',lambda:a.divide(p*q+y,[p,q])),('division_order2',lambda:a.divide(p*q+y,[q,p])),('rank_matrix',lambda:a.rank([[1,2,3],[2,4,6],[1,0,1]],3))]:probe(name,fn)
print(json.dumps({'source_api_imported_for_observation':True,'oracle_not_used_for_expected_here':True,'step_probe_mode':'MAX_STEPS temporarily set 2 and 3 in loaded module only, restored2000; not a natural2001-step witness','observations':observed},indent=2))
