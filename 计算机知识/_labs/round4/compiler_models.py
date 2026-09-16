"""Deterministic SLR construction, finite-set liveness and finite-tree unification.
Educational subsets only: no production parser recovery, whole-language inference or SSA.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass

class SLR:
    def __init__(self,productions: list[tuple[str,tuple[str,...]]],start:str):
        self.prod=[("@START",(start,))]+productions
        self.nonterm={lhs for lhs,_ in self.prod}
        self.term={x for _,rhs in self.prod for x in rhs}-self.nonterm
        self.first={x:{x} for x in self.term}|{x:set() for x in self.nonterm}
        self.nullable=set()
        changed=True
        while changed:
            changed=False
            for lhs,rhs in self.prod:
                old=len(self.first[lhs]);all_null=True
                for x in rhs:
                    self.first[lhs]|=self.first[x]
                    if x not in self.nullable:all_null=False;break
                if all_null and lhs not in self.nullable:self.nullable.add(lhs);changed=True
                if old!=len(self.first[lhs]):changed=True
        self.follow={x:set() for x in self.nonterm};self.follow[start].add('$')
        changed=True
        while changed:
            changed=False
            for lhs,rhs in self.prod:
                trailer=self.follow[lhs].copy()
                for x in reversed(rhs):
                    if x in self.nonterm:
                        old=len(self.follow[x]);self.follow[x]|=trailer
                        if old!=len(self.follow[x]):changed=True
                    trailer=(trailer|self.first[x]) if x in self.nullable else self.first[x].copy()
        self.states=[self.closure({(0,0)})];self.transitions={}
        i=0
        while i<len(self.states):
            for x in sorted(self.nonterm|self.term):
                nxt=self.goto(self.states[i],x)
                if not nxt:continue
                if nxt not in self.states:self.states.append(nxt)
                self.transitions[i,x]=self.states.index(nxt)
            i+=1
        self.action:dict[tuple[int,str],tuple[str,int]]={}
        def put(key,value):
            if key in self.action and self.action[key]!=value:
                raise ValueError(f'SLR conflict at {key}: {self.action[key]} vs {value}')
            self.action[key]=value
        for i,state in enumerate(self.states):
            for pi,dot in sorted(state):
                lhs,rhs=self.prod[pi]
                if dot<len(rhs) and rhs[dot] in self.term:put((i,rhs[dot]),('s',self.transitions[i,rhs[dot]]))
                elif dot==len(rhs):
                    if pi==0:put((i,'$'),('a',0))
                    else:
                        for t in self.follow[lhs]:put((i,t),('r',pi))

    def closure(self,items):
        result=set(items)
        while True:
            add=set()
            for pi,dot in result:
                rhs=self.prod[pi][1]
                if dot<len(rhs) and rhs[dot] in self.nonterm:
                    add|={(j,0) for j,(lhs,_) in enumerate(self.prod) if lhs==rhs[dot]}
            if add<=result:return frozenset(result)
            result|=add
    def goto(self,state,x):
        return self.closure({(pi,dot+1) for pi,dot in state if dot<len(self.prod[pi][1]) and self.prod[pi][1][dot]==x})
    def parse(self,tokens:list[str])->tuple[bool,list[tuple[str,int]]]:
        # The external API accepts token kinds, not the artificial end marker.
        if any(t not in self.term for t in tokens):return False,[]
        stream=tokens+['$'];i=0;stack=[0];trace=[]
        for _ in range(10000):
            act=self.action.get((stack[-1],stream[i]))
            if act is None:return False,trace
            trace.append(act);kind,value=act
            if kind=='a':return True,trace
            if kind=='s':stack.append(value);i+=1
            else:
                lhs,rhs=self.prod[value]
                if rhs:del stack[-len(rhs):]
                stack.append(self.transitions[stack[-1],lhs])
        raise RuntimeError('teaching parser step bound exceeded')


def liveness(use:list[set[str]],defs:list[set[str]],succ:list[list[int]],worklist:bool=True):
    n=len(use);ins=[set() for _ in range(n)];outs=[set() for _ in range(n)]
    if not worklist:
        while True:
            no=[set().union(*(ins[s] for s in succ[b])) for b in range(n)]
            ni=[use[b]|(no[b]-defs[b]) for b in range(n)]
            if ni==ins:return ni,no
            ins,outs=ni,no
    pred=[[] for _ in range(n)]
    for b in range(n):
        for s in succ[b]:pred[s].append(b)
    q=deque(range(n));pending=set(range(n))
    while q:
        b=q.popleft();pending.remove(b)
        outs[b]=set().union(*(ins[s] for s in succ[b]))
        new=use[b]|(outs[b]-defs[b])
        if new!=ins[b]:
            ins[b]=new
            for p in pred[b]:
                if p not in pending:q.append(p);pending.add(p)
    return ins,outs

@dataclass(frozen=True)
class Var:
    name:str
@dataclass(frozen=True)
class Con:
    name:str
    args:tuple[Type,...]=()
Type=Var|Con

def arrow(a:Type,b:Type)->Type:return Con('->',(a,b))

def apply(t:Type,sub:dict[Var,Type])->Type:
    if isinstance(t,Var):return apply(sub[t],sub) if t in sub else t
    return Con(t.name,tuple(apply(a,sub) for a in t.args))

def free(t:Type)->set[Var]:
    return {t} if isinstance(t,Var) else set().union(*(free(a) for a in t.args))

def unify(equations:list[tuple[Type,Type]])->dict[Var,Type]:
    sub:dict[Var,Type]={};pending=list(equations)
    while pending:
        a,b=pending.pop();a,b=apply(a,sub),apply(b,sub)
        if a==b:continue
        if isinstance(b,Var) and not isinstance(a,Var):a,b=b,a
        if isinstance(a,Var):
            if a in free(b):raise ValueError('occurs check')
            sub[a]=b
        elif isinstance(b,Con) and a.name==b.name and len(a.args)==len(b.args):
            pending.extend(zip(a.args,b.args))
        else:raise ValueError('constructor conflict')
    return {v:apply(t,sub) for v,t in sub.items()}

def instantiate(t:Type,quantified:set[Var],prefix:str)->Type:
    return apply(t,{v:Var(f'{prefix}:{v.name}') for v in quantified})
