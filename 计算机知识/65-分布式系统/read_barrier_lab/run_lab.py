"""Drive the same fixed RPC plans in memory or three owned loopback workers."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time
from read_model import Node,MEMBERS,identifier

class Memory:
    def __init__(self,path):self.nodes={n:Node(n) for n in MEMBERS};self.lifecycle=[]
    def call(self,n,method,**args):
        before=deepcopy(self.nodes[n])
        try:return self.nodes[n].handle({'op':method,'args':args})
        except Exception:self.nodes[n]=before;raise
    def restart(self,n):
        self.nodes[n]=Node(n,self.nodes[n].persistent());self.lifecycle.append({'node':n,'kind':'memory_reboot','boot':self.nodes[n].boot});return self.lifecycle[-1]
    def close(self):pass

class Processes:
    def __init__(self,path):
        self.path=path;path.mkdir();self.workers={};self.lifecycle=[]
        try:
            for n in MEMBERS:self.start(n)
        except BaseException:self.close();raise
    def start(self,n):
        out=self.path/n;out.mkdir(exist_ok=True);err=(out/f'stderr-{len(self.lifecycle)}.txt').open('w')
        cmd=[sys.executable,'-B',str(Path(__file__).parent/'worker.py'),'--node',n,'--db',str(out/'state.sqlite'),'--audit',str(out/'rpc.jsonl')]
        p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=err,text=True);self.workers[n]={'p':p,'stderr':err,'port':None}
        if not select.select([p.stdout],[],[],5)[0]:raise RuntimeError('owned worker readiness timeout')
        line=p.stdout.readline();ready=json.loads(line);assert ready['pid']==p.pid and ready['node']==n
        p.stdout.close();self.workers[n]['port']=ready['port'];self.lifecycle.append({'kind':'start','argv':cmd,'ready':ready,'monotonic_ns':time.monotonic_ns()})
    def call(self,n,method,**args):
        w=self.workers[n]
        with socket.create_connection(('127.0.0.1',w['port']),timeout=2) as conn:
            conn.settimeout(2);f=conn.makefile('rwb');f.write((json.dumps({'op':method,'args':args},separators=(',',':'))+'\n').encode());f.flush();line=f.readline(65537)
        result=json.loads(line)
        if not result['ok']:raise ValueError(result['error'])
        return result['result']
    def restart(self,n):
        w=self.workers[n];p=w['p'];assert p.poll() is None
        os.kill(p.pid,signal.SIGKILL);p.wait(timeout=3);assert p.returncode==-signal.SIGKILL
        p.stdout.close();w['stderr'].close();self.lifecycle.append({'kind':'controlled_SIGKILL_after_barrier','node':n,'owned_pid':p.pid,'exit_code':p.returncode,'monotonic_ns':time.monotonic_ns()});self.start(n);return self.lifecycle[-2:]
    def close(self):
        for n,w in self.workers.items():
            p=w['p']
            if p.poll() is None:
                try:self.call(n,'shutdown');p.wait(timeout=3)
                except Exception:
                    p.terminate()
                    try:p.wait(timeout=2)
                    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
            p.stdout.close();w['stderr'].close();self.lifecycle.append({'kind':'exit','node':n,'owned_pid':p.pid,'exit_code':p.returncode,'monotonic_ns':time.monotonic_ns()})
        for w in self.workers.values():
            if w['port'] is not None:
                s=socket.socket();s.settimeout(.2);closed=s.connect_ex(('127.0.0.1',w['port']))!=0;s.close()
                if not closed:raise AssertionError('owned listener still open')
        self.lifecycle.append({'kind':'all_current_owned_ports_closed'})

class Driver:
    def __init__(self,adapter):
        self.a=adapter;self.blocked=set();self.held={};self.calls={};self.completed=[];self.pending_client={};self.clock=0;self.writes={};self.rpc=[]
    def tick(self):self.clock+=1;return self.clock
    def call(self,node,method,**args):
        result=self.a.call(node,method,**args);self.rpc.append({'node':node,'request':{'op':method,'args':deepcopy(args)},'reply':deepcopy(result)});return result
    def route(self,source,dest,op,**args):
        if (source,dest) in self.blocked:
            self.rpc.append({'route_drop_request':[source,dest],'op':op});return None
        response=self.call(dest,op,**args)
        if (dest,source) in self.blocked:
            self.rpc.append({'route_drop_response':[dest,source],'op':op});return None
        return response
    def begin(self,ident,kind,value=None,group='good'):
        if ident in self.calls:raise ValueError('call ID reuse without explicit retry')
        self.calls[ident]={'id':ident,'client':ident,'kind':kind,'value':value,'start':self.tick(),'end':None,'group':group}
    def finish(self,ident,value):
        c=self.calls[ident]
        if c['end'] is None:
            c['value']=value;c['end']=self.tick();self.completed.append(deepcopy(c))
    def action(self,x):
        op=x['op'];n=x.get('node');ident=x.get('id');result={}
        if op=='elect':
            req=self.call(n,'elect')
            for peer in x['voters']:
                ack=self.route(n,peer,'vote_request',m=req)
                if ack:self.call(n,'vote_ack',m=ack)
            result=self.call(n,'snapshot')
        elif op=='noop':result=self.call(n,'propose',op='noop')
        elif op=='write_begin':
            self.begin(ident,'put',x['value']);result=self.call(n,'propose',op='put',value=x['value'],write_id=ident);self.writes[ident]=result['index']
        elif op=='replicate':
            req=self.call(n,'make_append',peer=x['peer']);ack=self.route(n,x['peer'],'append',m=req)
            if ack:
                if 'hold' in x:self.held[x['hold']]=ack
                else:result=self.call(n,'append_ack',m=ack)
            else:result={'status':'router_dropped'}
        elif op=='apply':result=self.call(n,'apply',**({'to':x['to']} if 'to' in x else {}))
        elif op=='write_poll':
            result=self.call(n,'write_poll',index=self.writes[ident],write_id=ident)
            if result['status']=='success':
                if x.get('hold_client'):self.pending_client[ident]=result
                else:self.finish(ident,self.calls[ident]['value'])
        elif op=='write_release':result=self.pending_client.pop(ident);self.finish(ident,self.calls[ident]['value'])
        elif op=='read_begin':
            if not x.get('retry'):self.begin(ident,'get')
            result=self.call(n,'begin_read',rid=ident)
        elif op=='probe':
            req=self.call(n,'make_probe',rid=ident,peer=x['peer']);ack=self.route(n,x['peer'],'probe',m=req)
            if ack:
                if 'hold' in x:self.held[x['hold']]=ack;result=ack
                else:result=self.call(n,'read_ack',rid=ident,m=ack)
            else:result={'status':'router_dropped'}
        elif op=='manual_probe':
            # Deliberate negative candidate: fresh heartbeat without a registered
            # safe read context/current-term gate; cannot complete safe API.
            snap=self.call(n,'snapshot');req={'kind':'read_probe','source':n,'dest':x['peer'],'term':snap['term'],'nonce':x['nonce']};result=self.route(n,x['peer'],'probe',m=req)
        elif op=='deliver_ack':
            ack=deepcopy(self.held[x['hold']]);result=self.call(n,'read_ack',rid=ident,m=ack) if ack['kind']=='read_ack' else self.call(n,'append_ack',m=ack)
        elif op=='read_poll':
            result=self.call(n,'read_poll',rid=ident)
            if result['status']=='success':self.finish(ident,result['value'])
        elif op=='unsafe_read':
            self.begin(ident,'get',group='bad');result=self.call(n,'unsafe_local_read');self.finish(ident,result['value'])
        elif op=='block':self.blocked.update(tuple(p) for p in x['pairs']);result={'blocked':sorted(self.blocked)}
        elif op=='heal':self.blocked.clear();result={'blocked':[]}
        elif op=='restart':result=self.a.restart(n)
        else:raise ValueError('unknown plan action')
        if 'expect' in x:
            for key,value in x['expect'].items():
                if result.get(key)!=value:raise AssertionError((x,result,key,value))
        return result
    def run(self,plan):
        rows=[]
        for x in plan['actions']:
            self.rpc=[];result=self.action(x);snapshots={n:self.a.call(n,'snapshot') for n in MEMBERS}
            rows.append({'action':x,'result':result,'RPC':self.rpc,'nodes':snapshots,'client_event_clock':self.clock})
        good=[c for c in self.completed if c['group']=='good'];bad=[c for c in self.completed if c['kind']=='put' or c['group']=='bad' or c['id'] in plan.get('bad_includes',[])]
        return {'name':plan['name'],'steps':rows,'history_good':good,'history_bad':bad,'pending_calls':[v for v in self.calls.values() if v['end'] is None],'expected_history':plan['expected_history']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--plans',type=Path,required=True);p.add_argument('--mode',choices=['memory','process'],required=True);p.add_argument('--out',type=Path,required=True);z=p.parse_args()
    if z.out.exists() or z.out.is_symlink():p.exit(2,'fresh output directory required\n')
    plans=json.loads(z.plans.read_text())
    if plans.get('schema')!='read-barrier-v1' or len(plans['scenarios'])>12:p.exit(2,'finite fixed plan schema\n')
    for plan in plans['scenarios']:
        identifier(plan['name'])
        if len(plan['actions'])>100:p.exit(2,'max 100 actions per scenario\n')
    z.out.mkdir(parents=True);start=time.monotonic();result=[];life={}
    for plan in plans['scenarios']:
        adapter=Memory(z.out/plan['name']) if z.mode=='memory' else Processes(z.out/plan['name'])
        try:result.append(Driver(adapter).run(plan))
        finally:adapter.close();life[plan['name']]=adapter.lifecycle
    payload={'mode':z.mode,'input':plans,'source_sha256':{name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ['read_model.py','worker.py','run_lab.py']},'python':sys.version,'elapsed_s':time.monotonic()-start,'scenarios':result,'lifecycle':life,'scope':'fixed deterministic routing; process mode uses real loopback RPC and owned PIDs, not OS network partitions'}
    (z.out/'results.json').write_text(json.dumps(payload,ensure_ascii=True,allow_nan=False,indent=2)+'\n');print(json.dumps({'status':'PASS','mode':z.mode,'scenarios':len(result),'elapsed_s':payload['elapsed_s']}))
if __name__=='__main__':main()
