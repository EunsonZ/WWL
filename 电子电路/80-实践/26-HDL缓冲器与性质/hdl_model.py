"""Finite two-state CPU model; no HDL scheduler, analog delay or tool proof."""
from dataclasses import dataclass
from collections import deque
import random


def integer(value, name, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in {lo}..{hi}; bool is not accepted')
    return value


@dataclass(frozen=True)
class State:
    full: int = 0
    data: int = 0


def step(state, *, width, rst_n, sv, data, mr, fault=False):
    integer(width,'width',1,8)
    if type(state) is not State: raise ValueError('state must be State')
    integer(state.full,'full',0,1);integer(state.data,'state data',0,(1<<width)-1)
    for v,n in ((rst_n,'rst_n'),(sv,'sv'),(mr,'mr')):integer(v,n,0,1)
    integer(data,'data',0,(1<<width)-1)
    if type(fault) is not bool:raise ValueError('fault must be bool')
    ready=int(bool(rst_n and (not state.full or mr)))
    valid=rst_n*state.full
    push=sv*ready;pop=valid*mr
    if not rst_n:after=State()
    else:
        after=State(sv if ready else state.full, data if (sv if fault else push) else state.data)
    return after, {'ready':ready,'valid':valid,'data':state.data,'push':push,'pop':pop}


class History:
    """Accepted/delivered event histories; independent of DUT full/ready equations."""
    def __init__(self):
        self.accepted=[];self.delivered=[];self.queue=deque();self.epochs=[]
    def observe(self, ports, source_word, rst_n):
        if not rst_n:
            self.epochs.append((tuple(self.accepted),tuple(self.delivered),tuple(self.queue)))
            self.accepted=[];self.delivered=[];self.queue.clear();return
        if ports['valid'] != int(bool(self.queue)):raise AssertionError('occupancy')
        if ports['valid'] and ports['data'] != self.queue[0]:raise AssertionError('head')
        if ports['pop']:
            self.delivered.append(self.queue.popleft())
        if ports['push']:
            self.accepted.append(source_word);self.queue.append(source_word)
        if len(self.queue)>1:raise AssertionError('capacity')
        if self.accepted != self.delivered+list(self.queue):raise AssertionError('history prefix')
    def post(self,state):
        if state.full != len(self.queue):raise AssertionError('post occupancy')
        if self.queue and state.data != self.queue[0]:raise AssertionError('post head')


def directed(fault=False):
    state=State();history=History();rows=[]
    # reset at 1 ns; drives at 20,30,.. ns; edges 25,35,.. ns; post observations 26,36,.. ns.
    seq=[(1,1,0xA1,1),(1,1,0xB2,0),(1,1,0xB2,0),(1,1,0xB2,1),(1,0,0,1),(1,0,0,1)]
    for k,(rst,sv,data,mr) in enumerate(seq):
        after,ports=step(state,width=8,rst_n=rst,sv=sv,data=data,mr=mr,fault=fault)
        row={'cycle':k+1,'drive_ns':20+10*k,'edge_ns':25+10*k,'observe_ns':26+10*k,
             'sv':sv,'source':data,'mr':mr,'before_full':state.full,'before_data':state.data,
             **ports,'after_full':after.full,'after_data':after.data,'status':'predicted_CPU_not_HDL'}
        history.observe(ports,data,rst)
        try:history.post(after)
        except AssertionError as exc:
            row['expected_head']=history.queue[0];row['failure']=str(exc);rows.append(row)
            return {'rows':rows,'failure_cycle':k+1,'model':'CPU prediction, not HDL execution'}
        rows.append(row);state=after
    return {'rows':rows,'failure_cycle':None,'model':'CPU prediction, not HDL execution'}


def random_check(*, width=4, count=1000, seed=0x205017):
    integer(width,'width',1,8);integer(count,'count',1,4096);integer(seed,'seed',0,2**32-1)
    rng=random.Random(seed);state=State();ref=History();pending=None
    counts={'push':0,'pop':0,'replace':0,'stall':0,'reset':0}
    for _ in range(count):
        rst=int(rng.randrange(23)!=0)
        if not rst:pending=None
        elif pending is None and rng.randrange(2):pending=rng.randrange(1<<width)
        sv=int(pending is not None);word=pending if sv else 0;mr=rng.randrange(2)
        after,ports=step(state,width=width,rst_n=rst,sv=sv,data=word,mr=mr)
        ref.observe(ports,word,rst);ref.post(after)
        for n in ('push','pop'):counts[n]+=ports[n]
        counts['replace']+=ports['push']*ports['pop'];counts['stall']+=ports['valid']*(1-mr)
        counts['reset']+=1-rst
        if ports['push']:pending=None
        state=after
    return counts


def enumerate_transitions(*, width=2, budget=10000):
    """BFS of DUT/history pairs; finite width, arbitrary input words, reset cancels epoch.
    No producer-hold assumption required for slot's rejection correctness; source obligation
    tested separately by legal random generation. Explore all reachable two-state transitions.
    """
    integer(width,'width',1,3);integer(budget,'budget',1,200000)
    start=(State(),());todo=deque([start]);seen={start};edges=0
    while todo:
        state,q=todo.popleft()
        for rst in (0,1):
          for sv in (0,1):
           for mr in (0,1):
            for word in range(1<<width):
             edges+=1
             if edges>budget:raise RuntimeError('finite transition budget exhausted')
             after,ports=step(state,width=width,rst_n=rst,sv=sv,data=word,mr=mr)
             ref=History();ref.queue.extend(q);ref.accepted=list(q)
             ref.observe(ports,word,rst);ref.post(after)
             pair=(after,tuple(ref.queue))
             if pair not in seen:seen.add(pair);todo.append(pair)
    return {'width':width,'reachable_pairs':len(seen),'edges':edges,'layer':'finite CPU graph, not HDL proof'}


def arithmetic(a,b,*,width):
    integer(width,'width',1,8);limit=1<<width
    integer(a,'a',0,limit-1);integer(b,'b',0,limit-1)
    sa=a-limit if a & (limit>>1) else a;sb=b-limit if b & (limit>>1) else b
    signed_sum=sa+sb;word=(a+b)%limit
    return {'word':word,'carry':(a+b)//limit,'signed_sum':signed_sum,
            'signed_word':word-limit if word & (limit>>1) else word,
            'signed_overflow':not(-limit//2<=signed_sum<limit//2)}
