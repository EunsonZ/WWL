"""Finite directed property-graph teaching evaluator, not a database server."""
import argparse
from collections import defaultdict, deque
import json
from pathlib import Path


def validate(spec):
    nodes, edges = spec['nodes'], spec['edges']
    if len(nodes)>20 or len(edges)>12:
        raise ValueError('fixture_limit')
    ids=[n['id'] for n in nodes]
    if len(set(ids))!=len(ids) or any(not isinstance(i,str) or not i for i in ids):
        raise ValueError('node_identity')
    eids=[e['id'] for e in edges]
    if len(set(eids))!=len(eids) or any(not isinstance(i,str) or not i for i in eids):
        raise ValueError('edge_identity')
    if any(e['src'] not in ids or e['dst'] not in ids for e in edges):
        raise ValueError('dangling_endpoint')
    for v in spec['variants']:
        if len(v['edge_ids'])!=len(set(v['edge_ids'])) or not set(v['edge_ids'])<=set(eids):
            raise ValueError('variant_edges')
    for q in spec['queries']:
        if q['source'] not in ids or q['target'] not in ids:
            raise ValueError('query_endpoint')
        if q['direction']!='out' or q['rule'] not in ('walk','trail','simple'):
            raise ValueError('unsupported_query')
        if type(q['min_hops']) is not int or type(q['max_hops']) is not int or not 0<=q['min_hops']<=q['max_hops']<=5:
            raise ValueError('query_length')


def ordered(paths):
    return sorted(paths,key=lambda p:(len(p['edge_ids']),p['edge_ids'],p['node_ids']))


def enumerate_paths(spec, edges, q, access):
    allowed={n['id'] for n in spec['nodes'] if n['label']==q['node_label']}
    adj=defaultdict(list)
    for e in edges:
        if e['type']==q['type'] and e['src'] in allowed and e['dst'] in allowed:
            adj[e['src']].append(e)
    stack=[([q['source']],[])] if q['source'] in allowed and q['target'] in allowed else []
    result=[]
    checks=expanded=0
    while stack:
        ns, es=stack.pop()
        depth=len(es)
        if q['min_hops']<=depth and ns[-1]==q['target']:
            result.append({'node_ids':ns,'edge_ids':es})
        # A target match does not terminate expansion: later visits also count.
        if depth==q['max_hops']:
            continue
        expanded+=1
        candidates=edges if access=='scan' else adj[ns[-1]]
        for e in candidates:
            checks+=1
            if e['src']!=ns[-1] or e['type']!=q['type'] or e['dst'] not in allowed:
                continue
            if q['rule']=='trail' and e['id'] in es:
                continue
            if q['rule']=='simple' and e['dst'] in ns:
                continue
            stack.append((ns+[e['dst']],es+[e['id']]))
    result=ordered(result)
    minimum=len(result[0]['edge_ids']) if result else None
    return {'paths':result,'path_count':len(result),'shortest_within_bounds':minimum,
            'all_shortest_within_bounds':[p for p in result if len(p['edge_ids'])==minimum],
            'cost':{'expanded_prefixes':expanded,'edge_records_tested':checks}}


def breadth_first(spec, edges, q):
    """Unbounded reachability and all shortest edge-distinct paths, zero included."""
    allowed={n['id'] for n in spec['nodes'] if n['label']==q['node_label']}
    if q['source'] not in allowed or q['target'] not in allowed:
        return {'reachable':False,'distance':None,'paths':[]}
    adj=defaultdict(list)
    for e in edges:
        if e['type']==q['type'] and e['src'] in allowed and e['dst'] in allowed:
            adj[e['src']].append(e)
    dist={q['source']:0}
    pred=defaultdict(list)
    queue=deque([q['source']])
    while queue:
        n=queue.popleft()
        for e in adj[n]:
            d=dist[n]+1
            if e['dst'] not in dist:
                dist[e['dst']]=d
                queue.append(e['dst'])
            if dist[e['dst']]==d:
                pred[e['dst']].append(e)
    def build(n):
        if n==q['source']:
            return [{'node_ids':[n],'edge_ids':[]}]
        return [{'node_ids':p['node_ids']+[n],'edge_ids':p['edge_ids']+[e['id']]}
                for e in pred[n] for p in build(e['src'])]
    reachable=q['target'] in dist
    return {'reachable':reachable,'distance':dist.get(q['target']),
            'paths':ordered(build(q['target'])) if reachable else []}


def run(spec):
    validate(spec)
    outputs=[]
    for variant in spec['variants']:
        edges=[e for e in spec['edges'] if e['id'] in variant['edge_ids']]
        queries=[]
        for q in spec['queries']:
            indexed=enumerate_paths(spec,edges,q,'adjacency')
            scan=enumerate_paths(spec,edges,q,'scan')
            assert {k:v for k,v in indexed.items() if k!='cost'}=={k:v for k,v in scan.items() if k!='cost'}
            queries.append({'query_id':q['id'],'bounded':{k:v for k,v in indexed.items() if k!='cost'},
                            'cost':{'adjacency':indexed['cost'],'scan':scan['cost']},
                            'unbounded_bfs':breadth_first(spec,edges,q)})
        outputs.append({'variant':variant['id'],'edge_count':len(edges),'queries':queries})
    return {'input_version':spec['input_version'],'layer':'finite local property-graph model',
            'variants':outputs}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--spec',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); result=run(json.loads(a.spec.read_text()))
    a.out.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n')
    print(json.dumps({'variants':len(result['variants']),'queries':sum(len(v['queries']) for v in result['variants'])}))
if __name__=='__main__': main()
