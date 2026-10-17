"""Fixed-member teaching replication + fresh read barriers; not full Raft.

Deterministic commands, no Byzantine peers, manual elections/full-prefix RPCs.
Safety of an arbitrary replicated-log service is an explicit lower-layer
contract; finite traces do not prove the full Raft protocol. No client-intent
exactly-once semantics, configuration change, log compaction or lease clock.
"""
from copy import deepcopy
import re

MEMBERS=('A','B','C')

def integer(v,name,lo=0,hi=10000):
    if type(v) is not int or not lo<=v<=hi:raise ValueError(name+' integer budget')
    return v

def identifier(v):
    if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',v):raise ValueError('ASCII operation ID required')
    return v

class Node:
    def __init__(self,node,persistent=None):
        if node not in MEMBERS:raise ValueError('fixed member A/B/C')
        self.node=node;self.term=0;self.vote=None;self.log=[];self.commit=0;self.applied=0;self.value=0;self.boot=0
        if persistent:
            if persistent['node']!=node:raise ValueError('database node identity differs')
            for k in ('term','vote','log','commit','applied','value','boot'):setattr(self,k,deepcopy(persistent[k]))
        self.boot+=1;self.role='follower';self.votes=set();self.match={};self.reads={};self.used_reads=set();self.counter=0
        self.invariant()
    def persistent(self):
        return deepcopy({k:getattr(self,k) for k in ('node','term','vote','log','commit','applied','value','boot')})
    def snapshot(self):
        return {**self.persistent(),'role':self.role,'votes':sorted(self.votes),'match':dict(sorted(self.match.items())),'reads':deepcopy(self.reads),'counter':self.counter}
    def invariant(self):
        assert 0<=self.applied<=self.commit<=len(self.log)
        val=0
        for i,e in enumerate(self.log):
            assert 0<e['term']<=self.term
            assert e['op'] in ('put','noop')
            if i<self.applied and e['op']=='put':val=e['value']
        assert self.value==val
        assert self.vote is None or self.vote in MEMBERS
    def observe(self,term):
        integer(term,'term')
        if term>self.term:
            self.term=term;self.vote=None;self.role='follower';self.votes=set();self.match={};self.reads={}
    def last(self):return [self.log[-1]['term'],len(self.log)] if self.log else [0,0]
    def elect(self):
        self.term+=1;self.vote=self.node;self.role='candidate';self.votes={self.node};self.match={};self.reads={}
        return {'kind':'vote_request','source':self.node,'term':self.term,'last':self.last()}
    def vote_request(self,m):
        self.member(m['source']);self.observe(m['term']);last=m['last']
        if len(last)!=2:raise ValueError('last term/index')
        integer(last[0],'lastTerm');integer(last[1],'lastIndex')
        grant=m['term']==self.term and tuple(last)>=tuple(self.last()) and self.vote in (None,m['source'])
        if grant:self.vote=m['source']
        return {'kind':'vote_ack','source':self.node,'dest':m['source'],'term':self.term,'granted':grant}
    def vote_ack(self,m):
        self.member(m['source']);self.observe(m['term'])
        if m['dest']!=self.node:raise ValueError('wrong vote destination')
        if self.role=='candidate' and m['term']==self.term and m['granted']:
            self.votes.add(m['source'])
            if len(self.votes)>=2:self.role='leader';self.match={self.node:len(self.log)}
        return {'role':self.role,'votes':sorted(self.votes)}
    @staticmethod
    def member(peer):
        if peer not in MEMBERS:raise ValueError('identity outside fixed membership')
    def propose(self,op,value=None,write_id=None):
        if self.role!='leader':return {'status':'not_leader'}
        if len(self.log)>=64:raise ValueError('finite log budget 64')
        if op not in ('put','noop'):raise ValueError('put or noop')
        if op=='put':integer(value,'value',-1000,1000);identifier(write_id)
        self.log.append({'term':self.term,'op':op,'value':value if op=='put' else None,'write_id':write_id if op=='put' else None})
        self.match[self.node]=len(self.log)
        return {'status':'pending','index':len(self.log),'term':self.term}
    def make_append(self,peer):
        self.member(peer)
        if self.role!='leader':raise ValueError('only leader emits append')
        return {'kind':'append','source':self.node,'dest':peer,'term':self.term,'entries':deepcopy(self.log),'leader_commit':self.commit}
    def append(self,m):
        self.member(m['source']);self.observe(m['term'])
        if m['dest']!=self.node:raise ValueError('wrong append destination')
        if m['term']!=self.term:return {'kind':'append_ack','source':self.node,'dest':m['source'],'term':self.term,'success':False,'matched':0}
        self.role='follower';self.reads={};entries=m['entries'];integer(m['leader_commit'],'leader_commit',0,64)
        if not isinstance(entries,list) or len(entries)>64:raise ValueError('entry budget')
        for i,e in enumerate(entries):
            integer(e['term'],'entry term',1,self.term)
            if e['op'] not in ('put','noop'):raise ValueError('entry operation')
            if e['op']=='put':integer(e['value'],'entry value',-1000,1000);identifier(e['write_id'])
            if i<len(self.log) and e!=self.log[i]:
                if i<self.commit:raise ValueError('refuse committed-prefix overwrite')
                self.log=self.log[:i]
            if i==len(self.log):self.log.append(deepcopy(e))
        self.commit=max(self.commit,min(m['leader_commit'],len(entries)))
        return {'kind':'append_ack','source':self.node,'dest':m['source'],'term':self.term,'success':True,'matched':len(entries)}
    def append_ack(self,m):
        self.member(m['source']);self.observe(m['term'])
        if m['dest']!=self.node:raise ValueError('wrong append acknowledgement destination')
        if self.role=='leader' and m['term']==self.term and m['success']:
            integer(m['matched'],'matched',0,len(self.log));self.match[m['source']]=max(self.match.get(m['source'],0),m['matched'])
            for index in range(len(self.log),self.commit,-1):
                if self.log[index-1]['term']==self.term and sum(v>=index for v in self.match.values())>=2:
                    self.commit=index;break
        return {'commit':self.commit}
    def apply(self,to=None):
        target=self.commit if to is None else integer(to,'apply index',self.applied,self.commit)
        while self.applied<target:
            e=self.log[self.applied]
            if e['op']=='put':self.value=e['value']
            self.applied+=1
        return {'applied':self.applied,'value':self.value}
    def write_poll(self,index,write_id):
        integer(index,'write index',1,len(self.log))
        if self.role!='leader':return {'status':'not_leader'}
        if self.applied<index:return {'status':'pending','commit':self.commit,'applied':self.applied}
        e=self.log[index-1]
        if e['op']!='put' or e['write_id']!=write_id:return {'status':'overwritten_or_unknown'}
        return {'status':'success','index':index,'write_id':e['write_id'],'value':e['value']}
    def begin_read(self,rid):
        identifier(rid)
        if self.role!='leader':return {'status':'not_leader'}
        if rid in self.used_reads:return {'status':'duplicate_read_id'}
        if not self.commit or self.log[self.commit-1]['term']!=self.term:
            return {'status':'wait_current_term_commit'}
        if len(self.used_reads)>=64:raise ValueError('finite read budget 64 per boot')
        self.counter+=1;nonce=f'{self.node}:{self.boot}:{self.term}:{self.counter}'
        self.used_reads.add(rid);self.reads[rid]={'node':self.node,'boot':self.boot,'term':self.term,'nonce':nonce,'read_index':self.commit,'acks':[self.node]}
        return {'status':'pending',**deepcopy(self.reads[rid])}
    def make_probe(self,rid,peer):
        self.member(peer)
        if rid not in self.reads:raise ValueError('no pending read context')
        c=self.reads[rid]
        return {'kind':'read_probe','source':self.node,'dest':peer,'term':c['term'],'nonce':c['nonce']}
    def probe(self,m):
        self.member(m['source']);self.observe(m['term'])
        if m['dest']!=self.node:raise ValueError('wrong probe destination')
        accepted=m['term']==self.term
        # A higher/equal-term read heartbeat observes leadership, but does not
        # transport commit, apply data or certify a read by itself.
        if accepted:self.role='follower';self.reads={}
        return {'kind':'read_ack','source':self.node,'dest':m['source'],'term':self.term,'nonce':m['nonce'],'accepted':accepted}
    def read_ack(self,rid,m):
        self.member(m['source']);self.observe(m['term'])
        if m['dest']!=self.node:raise ValueError('wrong read acknowledgement destination')
        c=self.reads.get(rid)
        if c is None:return {'status':'cancelled_or_unknown'}
        if self.role!='leader' or c['term']!=self.term or c['boot']!=self.boot:return {'status':'cancelled_or_unknown'}
        if m['term']!=c['term'] or m['nonce']!=c['nonce']:return {'status':'nonce_or_term_mismatch'}
        if m['accepted']:
            c['acks']=sorted(set(c['acks'])|{m['source']})
        return {'status':'pending','acks':c['acks'][:]}
    def read_poll(self,rid):
        c=self.reads.get(rid)
        if c is None:return {'status':'cancelled_or_unknown'}
        if self.role!='leader' or c['term']!=self.term or c['boot']!=self.boot:return {'status':'cancelled_or_unknown'}
        if len(c['acks'])<2:return {'status':'wait_quorum','acks':c['acks'][:]}
        if self.applied<c['read_index']:return {'status':'wait_apply','read_index':c['read_index'],'applied':self.applied}
        if 'completed' in c:return deepcopy(c['completed'])
        # These are a single atomic state-machine observation, not two unlocked reads.
        c['completed']={'status':'success','value':self.value,'served_index':self.applied,'read_index':c['read_index'],'term':c['term'],'boot':c['boot'],'nonce':c['nonce'],'acks':c['acks'][:]}
        return deepcopy(c['completed'])
    def handle(self,cmd):
        op=cmd['op'];a=cmd.get('args',{})
        methods={'elect':self.elect,'vote_request':self.vote_request,'vote_ack':self.vote_ack,'propose':self.propose,'make_append':self.make_append,'append':self.append,'append_ack':self.append_ack,'apply':self.apply,'write_poll':self.write_poll,'begin_read':self.begin_read,'make_probe':self.make_probe,'probe':self.probe,'read_ack':self.read_ack,'read_poll':self.read_poll,'snapshot':self.snapshot}
        if op=='unsafe_local_read':result={'status':'success','value':self.value,'served_index':self.applied,'unsafe':True}
        elif op in methods:result=methods[op](**a)
        else:raise ValueError('unknown operation')
        self.invariant();return deepcopy(result)
