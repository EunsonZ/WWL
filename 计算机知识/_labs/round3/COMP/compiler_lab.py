"""Tiny expression compiler: integer +,-,*; no eval, external tools or source execution."""
import re,random

def tokenize(s):
    pattern=re.compile(r'\s+|[0-9]+|[()+*-]');out=[];pos=0
    while pos<len(s):
        m=pattern.match(s,pos)
        if not m:raise SyntaxError(f'invalid token at {pos}')
        if not m.group().isspace():out.append(m.group())
        pos=m.end()
    return out+['EOF']

def parse(s):
    tokens=tokenize(s);pos=0
    def expression(minimum=0):
        nonlocal pos
        t=tokens[pos];pos+=1
        if t.isdigit():left=('num',int(t))
        elif t=='(':
            left=expression()
            if tokens[pos]!=')':raise SyntaxError('missing )')
            pos+=1
        else:raise SyntaxError('expected number or (')
        while tokens[pos] in ('+','-','*'):
            op=tokens[pos];prec=20 if op=='*' else 10
            if prec<minimum:break
            pos+=1;right=expression(prec+1);left=(op,left,right)
        return left
    tree=expression()
    if tokens[pos]!='EOF':raise SyntaxError('extra input')
    return tree

def interpret(tree):
    if tree[0]=='num':return tree[1]
    a,b=interpret(tree[1]),interpret(tree[2])
    return a+b if tree[0]=='+' else a-b if tree[0]=='-' else a*b

def emit(tree,out):
    if tree[0]=='num':out.append(('push',tree[1]));return
    emit(tree[1],out);emit(tree[2],out);out.append((tree[0],))

def execute(code):
    stack=[]
    for ins in code:
        if not isinstance(ins,tuple) or not ins:
            raise ValueError('malformed instruction')
        op=ins[0]
        if op=='push':
            if len(ins)!=2 or type(ins[1]) is not int:
                raise ValueError('push requires exactly one integer operand')
            stack.append(ins[1]);continue
        if op not in ('+','-','*') or len(ins)!=1:
            raise ValueError('unknown opcode or unexpected operands')
        if len(stack)<2:raise ValueError('stack underflow')
        b,a=stack.pop(),stack.pop()
        stack.append(a+b if op=='+' else a-b if op=='-' else a*b)
    if len(stack)!=1:raise ValueError('invalid final stack')
    return stack[0]

def main():
    assert interpret(parse('2+3*4'))==14
    assert interpret(parse('8-3-2'))==3
    for bad in ('','1@2','1+','(1+2','1 2'):
        try:parse(bad)
        except SyntaxError:pass
        else:raise AssertionError(bad)
    for code in ([],[()], [('push',)], [('push',True)], [('push',1,2)],
                 [('bogus',)], [('+',)], [('push',1),('push',2)],
                 [('push',1),('push',2),('+',3)]):
        try:execute(code)
        except ValueError:pass
        else:raise AssertionError(('invalid bytecode accepted',code))
    rng=random.Random(20260906)
    def gen(depth):
        if not depth or rng.random()<.3:
            v=rng.randrange(10);return str(v),v
        a,av=gen(depth-1);b,bv=gen(depth-1);op=rng.choice('+-*')
        v=av+bv if op=='+' else av-bv if op=='-' else av*bv
        return f'({a}{op}{b})',v
    for _ in range(500):
        source,expected=gen(5);tree=parse(source);code=[];emit(tree,code)
        assert interpret(tree)==execute(code)==expected
    print('PASS: precedence, associativity, invalid input and bytecode, 500 generated AST/VM/reference comparisons')
if __name__=='__main__':main()
