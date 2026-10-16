"""Independent exhaustive raw-edge products; does not import graph_model."""
import argparse
import itertools
import json
from pathlib import Path


def sequences(spec, edges, q, low, high, rule):
    allowed={n['id'] for n in spec['nodes'] if n['label']==q['node_label']}
    answer=[]
    if q['source'] not in allowed or q['target'] not in allowed:
        return answer
    for length in range(low,high+1):
        for seq in itertools.product(edges,repeat=length):
            ns=[q['source']]; es=[]
            for e in seq:
                if e['src']!=ns[-1] or e['type']!=q['type'] or e['dst'] not in allowed:
                    break
                ns.append(e['dst']); es.append(e['id'])
            else:
                if rule=='trail' and len(set(es))!=len(es): continue
                if rule=='simple' and len(set(ns))!=len(ns): continue
                answer.append({'node_ids':ns,'edge_ids':es})
    return answer


def check(spec, actual):
    count=0
    for variant, observed in zip(spec['variants'],actual['variants'],strict=True):
        assert variant['id']==observed['variant']
        edges=[e for e in spec['edges'] if e['id'] in variant['edge_ids']]
        assert len(edges)==observed['edge_count']
        for q,row in zip(spec['queries'],observed['queries'],strict=True):
            assert row['query_id']==q['id']
            all_prefixes=sequences(spec,edges,q,0,q['max_hops'],q['rule'])
            paths=[p for p in all_prefixes if len(p['edge_ids'])>=q['min_hops'] and p['node_ids'][-1]==q['target']]
            paths.sort(key=lambda p:(len(p['edge_ids']),p['edge_ids'],p['node_ids']))
            minimum=len(paths[0]['edge_ids']) if paths else None
            assert row['bounded']=={'paths':paths,'path_count':len(paths),'shortest_within_bounds':minimum,
                                   'all_shortest_within_bounds':[p for p in paths if len(p['edge_ids'])==minimum]}
            prefixes=[p for p in all_prefixes if len(p['edge_ids'])<q['max_hops']]
            eligible={n['id'] for n in spec['nodes'] if n['label']==q['node_label']}
            degree={n:sum(e['src']==n and e['dst'] in eligible and e['type']==q['type'] for e in edges) for n in eligible}
            assert row['cost']=={'adjacency':{'expanded_prefixes':len(prefixes),'edge_records_tested':sum(degree[p['node_ids'][-1]] for p in prefixes)},
                                 'scan':{'expanded_prefixes':len(prefixes),'edge_records_tested':len(prefixes)*len(edges)}}
            # Any minimum-hop walk has a node-simple witness (cycle removal).
            limit=sum(n['label']==q['node_label'] for n in spec['nodes'])-1
            simple=sequences(spec,edges,q,0,limit,'simple')
            target=[p for p in simple if p['node_ids'][-1]==q['target']]
            target.sort(key=lambda p:(len(p['edge_ids']),p['edge_ids'],p['node_ids']))
            d=len(target[0]['edge_ids']) if target else None
            assert row['unbounded_bfs']=={'reachable':bool(target),'distance':d,'paths':[p for p in target if len(p['edge_ids'])==d]}
            count+=1
    return {'status':'PASS','input_version':spec['input_version'],'queries_checked':count,
            'method':'all raw edge products, post-filter connectivity/type/labels/uniqueness; cycle removal for global shortest'}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--spec',type=Path,required=True); p.add_argument('--actual',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); r=check(json.loads(a.spec.read_text()),json.loads(a.actual.read_text()))
    a.out.write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps(r))
if __name__=='__main__': main()
