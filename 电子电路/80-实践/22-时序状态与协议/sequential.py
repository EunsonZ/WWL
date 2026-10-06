"""Bounded binary event models; no HDL scheduler or analog metastability model."""
import argparse
from dataclasses import dataclass, asdict
import itertools
import json
import math
import numbers
from pathlib import Path

MAX_EDGES = 4096

def bit(x):
    if type(x) is not bool: raise ValueError('bit must be bool')
    return x

def integer(x, lo, hi):
    if type(x) is not int or not lo <= x <= hi: raise ValueError('integer outside contract')
    return x

def scalar(x, lo=0., hi=1e6):
    if isinstance(x,bool) or not isinstance(x,numbers.Real): raise ValueError('finite real scalar required')
    try: y=float(x)
    except (ValueError,OverflowError): raise ValueError('finite real scalar required') from None
    if not math.isfinite(y) or not lo <= y <= hi: raise ValueError('real outside teaching domain')
    return y

def bounded(values, limit=MAX_EDGES):
    integer(limit,1,MAX_EDGES)
    out=[]
    try: iterator=iter(values)
    except TypeError: raise ValueError('iterable required') from None
    for v in iterator:
        if len(out)==limit: raise ValueError('event budget exceeded')
        out.append(v)
    return out

@dataclass(frozen=True)
class Timing:
    setup_slack_ns: float
    hold_slack_ns: float
    minimum_period_ns: float

def timing(period, cq_min, cq_max, cd, pd, setup, hold, skew=0., u_setup=0., u_hold=0.):
    """skew=capture-launch; delays ns in 0..1e6, skew in +/-1e6."""
    period,cq_min,cq_max,cd,pd,setup,hold,u_setup,u_hold=[scalar(v) for v in
        (period,cq_min,cq_max,cd,pd,setup,hold,u_setup,u_hold)]
    skew=scalar(skew,-1e6,1e6)
    if period==0 or cq_min>cq_max or cd>pd: raise ValueError('invalid period/min/max ordering')
    req=cq_max+pd+setup+u_setup-skew
    return Timing(period-req,cq_min+cd-hold-u_hold-skew,req)

def transitions(events):
    rows=bounded(events);last=-1.;result=[]
    for row in rows:
        if not isinstance(row,(tuple,list)) or len(row)!=2:raise ValueError('event=(time_ns,bool)')
        t=scalar(row[0]);v=bit(row[1])
        if t<=last:raise ValueError('strictly increasing event times')
        last=t;result.append((t,v))
    return result

def sample(initial, events, edge, setup, hold):
    """Return None on input change inside aperture or exactly on sampling edge.
    Boundary arrival equals setup/hold deadline is allowed in this ideal model.
    """
    old=bit(initial);rows=transitions(events)
    edge,setup,hold=scalar(edge),scalar(setup),scalar(hold)
    for t,v in rows:
        changed=v!=old
        if changed and (edge-setup<t<edge+hold or t==edge):return None
        old=v
    before=bit(initial)
    for t,v in rows:
        if t>=edge:break
        before=v
    return before

def latch(initial, events):
    """Zero-delay functional transparency only. Events=(time,D,G), unique times."""
    q=bit(initial);rows=bounded(events);last=-1.;result=[]
    for row in rows:
        if not isinstance(row,(tuple,list)) or len(row)!=3:raise ValueError('latch event=(time,D,G)')
        t=scalar(row[0]);d,g=bit(row[1]),bit(row[2])
        if t<=last:raise ValueError('strictly increasing event times')
        last=t
        if g:q=d
        result.append((t,q))
    return result

def counter(q, width, enable=True, load=None):
    width=integer(width,1,8);q=integer(q,0,(1<<width)-1);bit(enable)
    if load is not None:return integer(load,0,(1<<width)-1),False
    total=q+int(enable)
    return total% (1<<width),total>=1<<width

def pipeline(old, data, width=8):
    width=integer(width,1,8);data=integer(data,0,(1<<width)-1)
    if not isinstance(old,(tuple,list)) or not 1<=len(old)<=8:raise ValueError('1..8 stages')
    old=tuple(None if v is None else integer(v,0,(1<<width)-1) for v in old)
    return (data,)+old[:-1]

MOORE=((0,1),(2,1),(0,3),(2,1))
MEALY=((0,1),(2,1),(0,1))

def detector(state, x, moore=True):
    bit(x);bit(moore);state=integer(state,0,3 if moore else 2)
    before_hit=(state==3) if moore else (state==2 and x)
    nxt=(MOORE if moore else MEALY)[state][int(x)]
    return nxt,before_hit,(nxt==3 if moore else (nxt==2 and x))

@dataclass(frozen=True)
class BufferEdge:
    full_before: bool
    data_before: int
    ready: bool
    valid: bool
    push: bool
    pop: bool
    full_after: bool
    data_after: int

class Slot:
    def __init__(self,width=8):
        self.width=integer(width,1,8);self.full=False;self.data=0
    def step(self,sv,sd,mr,reset=False):
        bit(sv);bit(mr);bit(reset);integer(sd,0,(1<<self.width)-1)
        if reset:self.full=False;self.data=0
        q,d=self.full,self.data
        ready=not reset and (not q or mr);valid=not reset and q
        p,c=sv and ready,valid and mr
        self.full=p or (q and not c)
        if p:self.data=sd
        return BufferEdge(q,d,ready,valid,p,c,self.full,self.data)

class Synchronizer:
    """Ideal binary two-register shift; explicitly cannot represent metastability."""
    def __init__(self):self.first=self.second=False
    def step(self,async_level):
        bit(async_level);old=self.first
        self.first=async_level;self.second=old
        return self.first,self.second

class ResetRelease:
    """Logical async-assert/sync-release chain; no recovery/removal simulation."""
    def __init__(self):self.first=self.second=False
    def assert_reset(self):self.first=self.second=False
    def edge(self,external_reset_n):
        bit(external_reset_n)
        if not external_reset_n:self.assert_reset()
        else:self.first,self.second=True,self.first
        return self.second

def gray(n,width=3):
    width=integer(width,1,8);n=integer(n,0,(1<<width)-1)
    return n^(n>>1)

def log_mtbf(resolve_ns,tau_ns,aperture_ns,clock_hz,event_hz):
    """Natural log(MTBF/1 second), teaching Poisson/uniform-phase assumptions.
    tau/aperture are explicit hypothetical inputs, never device characterization.
    """
    r=scalar(resolve_ns,0,1000);tau=scalar(tau_ns,1e-3,1000);a=scalar(aperture_ns,1e-3,1000)
    fc=scalar(clock_hz,1,1e10);fd=scalar(event_hz,1,1e10)
    return r/tau-math.log(a*1e-9)-math.log(fc)-math.log(fd)

def demo():
    b=Slot();drives=[(False,0,True,True),(True,161,True,False),(True,178,False,False),(True,178,False,False),(True,178,True,False),(False,0,True,False),(False,0,True,False)]
    trace=[dict(edge=k,time_ns=10*k,sv=sv,sd=sd,mr=mr,reset=r,**asdict(b.step(sv,sd,mr,r))) for k,(sv,sd,mr,r) in enumerate(drives)]
    state=0;fsm=[]
    for k,x in enumerate([True,False,True,False,True],1):
        old=state;state,before,after=detector(state,x)
        fsm.append({'edge':k,'input':int(x),'before':old,'after':state,'hit_before':int(before),'hit_after':int(after)})
    stages=(None,None);pipe=[]
    for k,data in enumerate([10,20,30,40],1):
        old=stages;stages=pipeline(stages,data)
        pipe.append({'edge':k,'input':data,'before':old,'after':stages})
    return {'units':{'time':'ns','data':'unsigned 8-bit words','controls':'bool'},'buffer':trace,'fsm10101':fsm,'pipeline':pipe,'timing':asdict(timing(10,1,3,2,5,2,2,1)),
            'mtbf_model':'hypothetical tau=.05ns/aperture=.01ns/fc100MHz/fd1MHz; not a device',
            'log_mtbf_seconds':log_mtbf(.5,.05,.01,1e8,1e6)}

def write(output):
    output=Path(output).resolve();main=Path('/Users/ysz/Misc/Obsidian/Valults/WLM/WWL').resolve()
    if output.is_relative_to(main):raise ValueError('output must be outside main vault')
    output.mkdir(parents=True,exist_ok=True)
    (output/'events.json').write_text(json.dumps(demo(),indent=2)+'\n')

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args(argv);write(args.output)


def handshake_trace(word=42, horizon=120):
    """One four-phase bundled-data transaction; ideal snapshots on each domain edge.
    Source period10 ns; destination7 ns phase1 ns. No analog delay guarantee.
    """
    integer(word,0,255);integer(horizon,1,1000)
    req=ack=False;req1=req2=ack1=ack2=False
    phase='idle';data=0;rows=[];captures=[]
    times=sorted(set(range(0,horizon+1,10))|set(range(1,horizon+1,7)))
    for t in times:
        src=t%10==0;dst=(t-1)%7==0
        old_req,old_ack,old_data=req,ack,data
        if src:
            old_seen=ack2
            ack1,ack2=old_ack,ack1
            if phase=='idle':req=True;data=word;phase='wait_high'
            elif phase=='wait_high' and old_seen:req=False;phase='wait_low'
            elif phase=='wait_low' and not old_seen:phase='done'
        if dst:
            old_seen=req2
            req1,req2=old_req,req1
            if old_seen and not ack:
                captures.append((t,old_data));ack=True
            elif not old_seen and ack:ack=False
        rows.append({'time_ns':t,'source_edge':src,'destination_edge':dst,'req':req,'ack':ack,'data':data,'source_phase':phase,'req2':req2,'ack2':ack2,'capture':bool(captures and captures[-1][0]==t)})
    return rows,captures

if __name__=='__main__':main()
