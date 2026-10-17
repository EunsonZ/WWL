"""Exact finite coding/closed substitution/beta and a tiny ND certificate fragment.
Not a full PA proof checker, fixed-point theorem implementation, or consistency oracle.
Standard library only. CLI writes fixed JSON/SVG to --output-dir (default: this folder).
"""
from pathlib import Path
from math import factorial, gcd
import argparse
import json


ZERO=('zero',)
def Var(i): return ('v',i)
def S(t): return ('S',t)
def Add(a,b): return ('+',a,b)
def Mul(a,b): return ('*',a,b)
def Eq(a,b): return ('eq',a,b)
def Imp(a,b): return ('imp',a,b)
TAGS={'zero':0,'S':1,'+':2,'*':3,'eq':4,'not':5,'and':6,'imp':7,'all':8,'ex':9,'bot':10,'or':11,'lt':12}


def nat(n):
    if type(n) is not int or n<0: raise ValueError('nonnegative int required, excluding bool')
    return n


def gamma(n):
    nat(n)
    if n==0: raise ValueError('gamma takes positive integers')
    bits=bin(n)[2:]
    return '0'*(len(bits)-1)+bits


def encode_sequence(values):
    values=tuple(nat(v) for v in values)
    bits='1'+gamma(len(values)+1)+''.join(gamma(v+1) for v in values)
    return int(bits,2)


def decode_sequence(code):
    nat(code)
    if code==0: raise ValueError('missing sentinel')
    bits=bin(code)[3:]  # remove 0b and the leading sentinel 1
    pos=0
    def take():
        nonlocal pos
        start=pos
        while pos<len(bits) and bits[pos]=='0': pos+=1
        zeros=pos-start
        if pos+zeros>=len(bits): raise ValueError('truncated self-delimiting integer')
        val=int(bits[pos:pos+zeros+1],2)
        pos+=zeros+1
        return val
    length=take()-1
    out=tuple(take()-1 for _ in range(length))
    if pos!=len(bits): raise ValueError('trailing bits')
    return out


def term_tokens(t):
    if not isinstance(t,tuple) or not t: raise ValueError('bad term')
    op=t[0]
    if op=='zero' and len(t)==1: return (0,)
    if op=='v' and len(t)==2: return (20+nat(t[1]),)
    if op=='S' and len(t)==2: return (1,)+term_tokens(t[1])
    if op in ('+','*') and len(t)==3: return (TAGS[op],)+term_tokens(t[1])+term_tokens(t[2])
    raise ValueError('bad term constructor or arity')


def formula_tokens(a):
    if not isinstance(a,tuple) or not a: raise ValueError('bad formula')
    op=a[0]
    if op in ('eq','lt') and len(a)==3: return (TAGS[op],)+term_tokens(a[1])+term_tokens(a[2])
    if op=='bot' and len(a)==1: return (10,)
    if op=='not' and len(a)==2: return (5,)+formula_tokens(a[1])
    if op in ('and','or','imp') and len(a)==3: return (TAGS[op],)+formula_tokens(a[1])+formula_tokens(a[2])
    if op in ('all','ex') and len(a)==3: return (TAGS[op],20+nat(a[1]))+formula_tokens(a[2])
    raise ValueError('bad formula constructor or arity')


def decode_formula(code):
    tokens=decode_sequence(code);pos=0
    def read():
        nonlocal pos
        if pos==len(tokens): raise ValueError('truncated syntax')
        out=tokens[pos];pos+=1;return out
    def term():
        k=read()
        if k==0: return ZERO
        if k>=20: return Var(k-20)
        if k==1: return S(term())
        if k in (2,3): return ('+' if k==2 else '*',term(),term())
        raise ValueError('term token expected')
    def formula():
        k=read()
        if k in (4,12): return ('eq' if k==4 else 'lt',term(),term())
        if k==10: return ('bot',)
        if k==5: return ('not',formula())
        if k in (6,7,11): return ({6:'and',7:'imp',11:'or'}[k],formula(),formula())
        if k in (8,9):
            v=read()
            if v<20: raise ValueError('binder variable token expected')
            return ('all' if k==8 else 'ex',v-20,formula())
        raise ValueError('formula token expected')
    a=formula()
    if pos!=len(tokens): raise ValueError('trailing syntax')
    return a


def encode_formula(a): return encode_sequence(formula_tokens(a))


def term_vars(t):
    term_tokens(t)
    if t[0]=='v': return {t[1]}
    if t[0]=='zero': return set()
    return set().union(*(term_vars(a) for a in t[1:]))


def free_vars(a):
    formula_tokens(a)
    if a[0] in ('eq','lt'): return term_vars(a[1])|term_vars(a[2])
    if a[0]=='bot': return set()
    if a[0]=='not': return free_vars(a[1])
    if a[0] in ('all','ex'): return free_vars(a[2])-{a[1]}
    return free_vars(a[1])|free_vars(a[2])


def numeral(n):
    nat(n)
    if n==0: return ZERO
    if n==1: return S(ZERO)
    doubled=Mul(S(S(ZERO)),numeral(n//2))
    return S(doubled) if n%2 else doubled


def term_value(t, env=None):
    term_tokens(t);env=env or {}
    op=t[0]
    if op=='zero': return 0
    if op=='v':
        if t[1] not in env: raise ValueError('unassigned variable')
        return nat(env[t[1]])
    if op=='S': return term_value(t[1],env)+1
    a,b=term_value(t[1],env),term_value(t[2],env)
    return a+b if op=='+' else a*b


def substitute_closed(a, variable, t):
    """Only closed terms: enough for numeral diagonal substitution, no capture claim beyond it."""
    formula_tokens(a);nat(variable)
    if term_vars(t): raise ValueError('this finite routine accepts closed substituends only')
    def subterm(r):
        if r[0]=='v': return t if r[1]==variable else r
        if r[0]=='zero': return r
        return (r[0],)+(tuple(subterm(x) for x in r[1:]))
    def subformula(f):
        if f[0] in ('eq','lt'): return (f[0],subterm(f[1]),subterm(f[2]))
        if f[0]=='bot': return f
        if f[0] in ('all','ex'): return f if f[1]==variable else (f[0],f[1],subformula(f[2]))
        return (f[0],)+tuple(subformula(x) for x in f[1:])
    return subformula(a)


def diagonal_code(code):
    """d(e) of 06: syntax self-substitution, NOT the full fixed-point construction."""
    nat(code)
    try:
        a=decode_formula(code)
    except ValueError:
        return encode_formula(Eq(ZERO,ZERO))
    if not free_vars(a)<={0}: return encode_formula(Eq(ZERO,ZERO))
    return encode_formula(substitute_closed(a,0,numeral(code)))


def beta(b,c,i):
    return nat(b)%(1+(nat(i)+1)*nat(c))


def encode_beta(values):
    values=tuple(nat(x) for x in values)
    if not values: return {'b':0,'c':1,'moduli':[],'residues':[]}
    c=factorial(len(values))*(max(values)+1)
    moduli=[1+(i+1)*c for i in range(len(values))]
    assert all(gcd(x,y)==1 for i,x in enumerate(moduli) for y in moduli[i+1:])
    b=0;M=1
    for a,m in zip(values,moduli):
        t=((a-b)*pow(M,-1,m))%m
        b+=M*t;M*=m;b%=M
    decoded=[beta(b,c,i) for i in range(len(values))]
    assert decoded==list(values)
    return {'b':b,'c':c,'moduli':moduli,'residues':decoded}


def toy_w_trace(stage):
    return tuple(range(nat(stage)+1))


def toy_w_outputs(trace):
    """Toy enumeration only: releases equality A at step7 and B at step11."""
    if not isinstance(trace,tuple) or not trace or any(type(x) is not int for x in trace) or trace!=tuple(range(len(trace))):
        raise ValueError('invalid toy enumerator trace')
    out=[]
    if len(trace)>7: out.append(Eq(ZERO,ZERO))
    if len(trace)>11: out.append(Eq(S(ZERO),S(ZERO)))
    return out


def check_fragment(proof, context=frozenset()):
    """Only H, =I, implication I/E and toy W leaves; not the full 01/PA/T verifier."""
    if not isinstance(proof,tuple) or not proof: raise ValueError('bad proof node')
    rule=proof[0]
    if rule=='H' and len(proof)==2:
        formula_tokens(proof[1])
        if proof[1] not in context: raise ValueError('assumption not in open context')
        return proof[1]
    if rule=='eqI' and len(proof)==2:
        term_tokens(proof[1]);return Eq(proof[1],proof[1])
    if rule=='impI' and len(proof)==3:
        formula_tokens(proof[1]);return Imp(proof[1],check_fragment(proof[2],context|{proof[1]}))
    if rule=='mp' and len(proof)==3:
        major=check_fragment(proof[1],context);minor=check_fragment(proof[2],context)
        if major[0]!='imp' or major[1]!=minor: raise ValueError('modus ponens formulas do not match')
        return major[2]
    if rule=='W' and len(proof)==4:
        a,stage,trace=proof[1:];formula_tokens(a);nat(stage)
        if len(trace)!=stage+1 or a not in toy_w_outputs(trace): raise ValueError('toy W axiom not certified by this stage')
        return a
    raise ValueError('unknown/unsupported fragment rule')


def graft_mp(major,minor):
    proof=('mp',major,minor)
    check_fragment(proof)
    return proof


def build_results():
    sequence_inputs=[[],[0],[1,0,3],[2,0,3],[4,20,20],list(range(10))]
    sequence_rows=[]
    for seq in sequence_inputs:
        code=encode_sequence(seq);decoded=decode_sequence(code)
        assert decoded==tuple(seq)
        sequence_rows.append({'input':seq,'code_hex':hex(code),'bit_length':code.bit_length(),'decoded':list(decoded)})
    number_rows=[]
    for n in range(17):
        term=numeral(n);assert term_value(term)==n
        number_rows.append({'n':n,'tokens':list(term_tokens(term)),'value':term_value(term)})
    a=Eq(Var(0),Var(0));e=encode_formula(a);g=diagonal_code(e);instance=decode_formula(g)
    assert instance==Eq(numeral(e),numeral(e)) and term_value(instance[1])==e
    bound=('all',0,Eq(Var(0),Var(0)))
    assert diagonal_code(encode_formula(bound))==encode_formula(bound)
    assert decode_formula(encode_formula(('lt',ZERO,S(ZERO))))==('lt',ZERO,S(ZERO))
    assert diagonal_code(0)==encode_formula(Eq(ZERO,ZERO))
    beta_rows=[]
    for seq in [[],[0],[0,0,0],[2,0,3],[7,1,4,2]]:
        row=encode_beta(seq);row['input']=seq
        row['append_5']=encode_beta(seq+[5]);row['append_5']['input']=seq+[5]
        beta_rows.append(row)
    assert [beta(0,1,i) for i in range(3)]==[beta(12,1,i) for i in range(3)]==[0,0,0]
    A=Eq(ZERO,ZERO);B=Eq(S(ZERO),S(ZERO))
    pA=('eqI',ZERO)
    identity=('impI',A,('H',A))
    implication=('impI',A,('eqI',S(ZERO)))
    mp=graft_mp(implication,pA)
    assert check_fragment(identity)==Imp(A,A) and check_fragment(mp)==B
    toy=('W',A,7,toy_w_trace(7));assert check_fragment(toy)==A
    bad=[]
    calls=[('negative_number',lambda:numeral(-1)),('bool_number',lambda:numeral(True)),('bad_gamma',lambda:gamma(0)),('missing_code',lambda:decode_sequence(0)),('truncated_code',lambda:decode_sequence(2)),('unknown_term',lambda:term_tokens(('bad',))),('nonclosed_substitution',lambda:substitute_closed(a,0,Var(1))),('bad_binder',lambda:formula_tokens(('all',True,a))),('open_assumption',lambda:check_fragment(('H',A))),('bad_mp',lambda:check_fragment(('mp',implication,('eqI',S(ZERO))))),('early_W_stage',lambda:check_fragment(('W',A,6,toy_w_trace(6)))),('bad_W_trace',lambda:check_fragment(('W',A,7,(0,1,2,3,4,5,6,9))))]
    for label,call in calls:
        try: call()
        except ValueError as ex: bad.append({'case':label,'error':str(ex)})
        else: raise AssertionError('expected rejection '+label)
    return {'status':'PASS','date':'2026-10-17','boundary':'finite syntax self-substitution d(e), beta and H/=I/implication/toy-W fragment only; no implementation of all PA rules, Henkin, fixed-point lemma, actual G/R sentences, Prov_T arithmetic formula, HBL proof formalizer or consistency search','sequence_codes':sequence_rows,'binary_numerals':number_rows,'self_substitution':{'template':'x0=x0','e':e,'e_hex':hex(e),'numeral_tokens':list(term_tokens(numeral(e))),'d_e_hex':hex(g),'d_e_bit_length':g.bit_length(),'decoded_instance':instance,'term_value':e,'type_note':'e is an external number; nu(e) is a closed term; d(e) is the code of A(nu(e)), not an assertion about its truth'},'beta_rows':beta_rows,'nonunique_beta_parameters':[[0,1],[12,1]],'proof_fragment':{'A':A,'B':B,'identity_proof':identity,'identity_conclusion':check_fragment(identity),'mp_input_major':implication,'mp_input_minor':pA,'mp_proof':mp,'mp_conclusion':check_fragment(mp),'toy_W_stage':7,'toy_W_trace':toy[3],'toy_W_conclusion':check_fragment(toy)},'rejections':bad}


def svg(result):
    d=result['self_substitution'];beta_row=next(x for x in result['beta_rows'] if x['input']==[2,0,3])
    b,c=beta_row['b'],beta_row['c']
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="440" viewBox="0 0 1200 440">
<title>代码、数码闭项与β列表是不同类型</title><desc>左：公式x0等于x0的自然数编码e，数码ν(e)是值为e的闭项，而d(e)是替换后公式的编码；不展示真实Gödel句。右：同一实际CRT输入2、0、3被β参数编码并正确解出，参数不唯一。</desc>
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#334155"/></marker></defs>
<rect width="1200" height="440" fill="#f8fafc"/><g font-family="sans-serif" fill="#0f172a">
<text x="30" y="36" font-size="24">A number, its numeral term, and a formula code have different types</text>
<text x="40" y="86" font-size="21">A(x0) = (x0=x0)</text><text x="650" y="86" font-size="21">Exact beta list: [2, 0, 3]</text>
<rect x="40" y="120" width="460" height="65" rx="7" fill="#dbeafe" stroke="#2563eb"/><text x="60" y="157" font-size="19">External number e = {d['e']}</text>
<path d="M260,188 V215" stroke="#334155" marker-end="url(#a)"/><text x="42" y="251" font-size="19">nu(e): a closed arithmetic term, value = e</text>
<path d="M260,267 V295" stroke="#334155" marker-end="url(#a)"/><text x="42" y="329" font-size="18">d(e): code of nu(e)=nu(e), {d['d_e_bit_length']} bits</text>
<text x="650" y="139" font-size="19">b = {b}, c = {c}</text><text x="650" y="177" font-size="19">moduli: {', '.join(str(x) for x in beta_row['moduli'])}</text>
<rect x="650" y="210" width="95" height="65" fill="#dcfce7" stroke="#15803d"/><rect x="775" y="210" width="95" height="65" fill="#dcfce7" stroke="#15803d"/><rect x="900" y="210" width="95" height="65" fill="#dcfce7" stroke="#15803d"/>
<text x="690" y="250" font-size="24">2</text><text x="815" y="250" font-size="24">0</text><text x="940" y="250" font-size="24">3</text>
<text x="650" y="329" font-size="18">beta(b,c,i) = b mod [1+(i+1)c]</text>
<text x="30" y="403" font-size="16">Fixed syntax/CRT inputs only. The general diagonal lemma and PA-internal proof transformations are proved in 05-07.</text>
</g></svg>'''


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent)
    args=ap.parse_args();result=build_results()
    (args.output_dir/'assets').mkdir(parents=True,exist_ok=True);(args.output_dir/'实践结果').mkdir(parents=True,exist_ok=True)
    (args.output_dir/'实践结果/arithmetization-20261017.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (args.output_dir/'assets/arithmetization-types.svg').write_text(svg(result))
    print(json.dumps({'status':'PASS','sequence_inputs':len(result['sequence_codes']),'numerals':len(result['binary_numerals']),'beta_inputs':len(result['beta_rows']),'self_code_bits':result['self_substitution']['d_e_bit_length'],'rejections':len(result['rejections'])}))


if __name__=='__main__': main()
