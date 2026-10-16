"""Check recorded real-engine HTTP evidence without launching Neo4j."""
import argparse
import hashlib
import json
from pathlib import Path


def rows(record, index=0):
    return [d['row'] for d in record['response']['results'][index]['data']]


def verify(root, model_actual):
    h=json.loads((root/'evidence/http-history.json').read_text())
    s=json.loads((root/'snapshot-evidence/http-history.json').read_text())
    assert len(h)==10 and len(s)==7
    for record in h+s:
        assert record['status'] in (200,201)
    assert rows(h[0])==[['Neo4j Kernel',['5.26.32'],'community']]
    statements=[x.strip() for x in '\n'.join(line for line in (root/'original-interface.cypher').read_text().splitlines() if not line.lstrip().startswith('//')).split(';') if x.strip()]
    assert len(statements)==5
    assert [r['statements'] for r in h[1:6]]==[[x] for x in statements]
    for record in h[:6]+h[7:]+s:
        assert record['response'].get('errors',[])==[]
    model=json.loads(model_actual.read_text())
    typed=next(v for v in model['variants'] if v['variant']=='typed')
    def bounded(rule):
        return next(q['bounded'] for q in typed['queries'] if q['query_id']==f'a_c_1_5_{rule}')
    trail=bounded('trail')['paths']; simple=bounded('simple')['paths']
    assert rows(h[3])==[[p['node_ids'],p['edge_ids']] for p in trail]
    assert rows(h[4])==[[x] for x in sorted(p['edge_ids'] for p in simple)]
    assert rows(h[5])==[[2,x] for x in sorted(p['edge_ids'] for p in bounded('trail')['all_shortest_within_bounds'])]
    assert (len(rows(h[3])),len(rows(h[4])),len(rows(h[5])))==(7,3,3)
    assert h[6]['response']['errors'][0]['code']=='Neo.ClientError.Schema.ConstraintValidationFailed'
    assert h[6]['statements']==["CREATE (:Entity {id:'a'})"]
    assert h[7]['statements']==['CREATE (n:Entity) RETURN n.id AS missing_id'] and rows(h[7])==[[None]]
    rollback=h[7]['response']['commit'].removeprefix('http://127.0.0.1:17471').removesuffix('/commit')
    assert h[8]['method']=='DELETE' and h[8]['path']==rollback
    assert rows(h[9],0)==[[6]] and rows(h[9],1)==[[8]]
    assert rows(h[9],2)==[['fixture_entity_id','UNIQUENESS']]
    assert rows(s[1])==[['s1','sy']]
    reader=s[1]['response']['commit'].removeprefix('http://127.0.0.1:17471').removesuffix('/commit')
    assert s[1]['path']=='/db/neo4j/tx'
    assert s[2]['path']=='/db/neo4j/tx/commit' and len(s[2]['statements'])==2
    assert 'DELETE r' in s[2]['statements'][0] and "id:'s3'" in s[2]['statements'][1]
    assert s[3]['path']==s[4]['path']==reader
    assert rows(s[3])==[['s3','sz']] and rows(s[4])==[]
    assert s[5]['method']=='DELETE' and s[5]['path']==reader
    assert s[6]['statements']==['MATCH (n:Scratch) DETACH DELETE n']
    for folder in ('evidence','snapshot-evidence'):
        shut=json.loads((root/folder/'shutdown.json').read_text())
        assert shut['returncode']==0 and shut['only_owned_process_group_signalled'] is True
    assert json.loads((root/'port-closed.json').read_text())['no_listener'] is True
    expected_hash=next(line.split()[0] for line in (root/'actual-sha256.txt').read_text().splitlines() if line.endswith('original-interface.cypher'))
    assert hashlib.sha256((root/'original-interface.cypher').read_bytes()).hexdigest()==expected_hash
    return {'status':'PASS','source':'recorded HTTP, no server started','version':'Community 5.26.32',
            'path_counts':[7,3,3],'shortest_hops':2,'explicit_reader_path':reader,
            'reader_observations':['s1','s3'],'single_full_query_after_commit':[]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--model-actual',type=Path,default=Path(__file__).resolve().parent.parent/'actual.json')
    a=p.parse_args(); print(json.dumps(verify(Path(__file__).resolve().parent,a.model_actual),ensure_ascii=True,indent=2))
if __name__=='__main__': main()
