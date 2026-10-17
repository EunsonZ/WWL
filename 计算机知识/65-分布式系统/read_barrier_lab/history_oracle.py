"""Independent batch history specification and finite read certificates.
No import of the protocol model/worker/driver. Histories are checked by dynamic
programming over predecessor ideals, not by replaying the reducer or its result.
"""
import argparse
import json
from pathlib import Path


def linearize(history,pending=()):
    # A pending write may be completed in an extension or omitted. Pending reads
    # are omitted here; they cannot change this register's sequential state.
    writes=[x for x in pending if x['kind']=='put']
    if len(history)+len(writes)>12:raise ValueError('finite oracle <=12 operations')
    for chosen in range(1<<len(writes)):
        ops=list(history)+[{**x,'end':10**100} for i,x in enumerate(writes) if chosen>>i&1]
        n=len(ops);pred=[]
        for b in ops:
            mask=0
            for i,a in enumerate(ops):
                if a['end']<b['start']:mask|=1<<i
            pred.append(mask)
        memo=set()
        def solve(mask,state):
            if mask==(1<<n)-1:return []
            if (mask,state) in memo:return None
            memo.add((mask,state))
            for i,x in enumerate(ops):
                if mask>>i&1 or pred[i]&~mask:continue
                if x['kind']=='get' and x['value']!=state:continue
                tail=solve(mask|1<<i,x['value'] if x['kind']=='put' else state)
                if tail is not None:return [x['id']]+tail
            return None
        witness=solve(0,0)
        if witness is not None:return witness
    return None

def prefix_value(log,index):
    value=0
    for e in log[:index]:
        if e['op']=='put':value=e['value']
    return value

def certificates(case):
    seen_nonces={};seen_ack={};committed={};read_count=0;states=0;node_previous={}
    for step_number,step in enumerate(case['steps']):
        # Actual receiver occurrences are observations, not a promise that all
        # future messages are timely. Delayed replies retain their generation.
        for rpc in step['RPC']:
            if 'node' not in rpc:continue
            name=rpc['request']['op'];args=rpc['request']['args'];reply=rpc['reply'];node=rpc['node']
            if name=='begin_read' and reply.get('status')=='pending':
                nonce=reply['nonce'];assert nonce not in seen_nonces
                assert nonce.startswith(f"{node}:{reply['boot']}:{reply['term']}:")
                seen_nonces[nonce]={'step':step_number,'rid':args['rid'],'node':node,'boot':reply['boot'],'term':reply['term'],'read_index':reply['read_index']};seen_ack[nonce]={node}
            if name=='probe':
                request=args['m'];assert reply['source']==node and reply['nonce']==request['nonce']
                assert reply['accepted']==(reply['term']==request['term'])
                if request['nonce'] in seen_nonces:
                    ctx=seen_nonces[request['nonce']];assert step_number>=ctx['step']
                    # A receiver may advance later, but this generated reply's
                    # provenance remains fixed, identified by complete content.
                    seen_ack.setdefault(('generated',json.dumps(reply,sort_keys=True)),step_number)
            if name=='read_ack' and reply.get('status')=='pending':
                message=args['m'];nonce=message['nonce'];ctx=seen_nonces[nonce]
                assert ctx['node']==node and ctx['rid']==args['rid']
                assert message['term']==ctx['term']
                assert ('generated',json.dumps(message,sort_keys=True)) in seen_ack
                if message['accepted']:seen_ack[nonce].add(message['source'])
                assert set(reply['acks'])==seen_ack[nonce]
            if name=='read_poll' and reply.get('status')=='success':
                ctx=seen_nonces[reply['nonce']];s=step['nodes'][node]
                assert s['role']=='leader' and s['term']==ctx['term'] and s['boot']==ctx['boot']
                assert reply['read_index']==ctx['read_index']
                assert len(set(reply['acks']))>=2 and set(reply['acks'])<=set(['A','B','C'])
                assert set(reply['acks'])==seen_ack[reply['nonce']]
                assert reply['served_index']>=reply['read_index'] and reply['served_index']<=s['applied']
                assert reply['value']==prefix_value(s['log'],reply['served_index'])
                assert s['log'][ctx['read_index']-1]['term']==ctx['term'];read_count+=1
        for node,s in step['nodes'].items():
            assert 0<=s['applied']<=s['commit']<=len(s['log'])
            assert s['value']==prefix_value(s['log'],s['applied'])
            before=node_previous.get(node)
            if before:
                assert s['term']>=before['term'] and s['boot']>=before['boot']
                assert s['log'][:before['commit']]==before['log'][:before['commit']]
            for i,e in enumerate(s['log'][:s['commit']]):
                if i in committed:assert committed[i]==e
                else:committed[i]=e
            node_previous[node]=s;states+=1
    return {'atomic_state_prefixes':states,'successful_read_certificates':read_count,'committed_prefix_length':len(committed)}

def check(path):
    d=json.loads(path.read_text());cases=[]
    for case in d['scenarios']:
        row={'name':case['name'],'certificate':certificates(case),'histories':{}}
        for group in ('good','bad'):
            witness=linearize(case['history_'+group],case['pending_calls']);expect=case['expected_history'][group]
            assert (witness is not None)==expect,(case['name'],group,witness)
            row['histories'][group]={'linearizable':witness is not None,'witness':witness}
        cases.append(row)
    return {'status':'PASS','mode':d['mode'],'scenarios':cases,'scope':'finite completed+pending register histories; DP linear extension / source-independent prefix certificates; no full protocol proof'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--out',type=Path,required=True);z=p.parse_args()
    if z.out.exists() or z.out.is_symlink():p.exit(2,'fresh oracle output required\n')
    report=check(z.results);z.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
