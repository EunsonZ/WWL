"""Compare saved real Redis CAS snapshots to the saved local-model contract."""
import json
from pathlib import Path


def check(lab):
    model=json.loads((lab/'actual.json').read_text());real=json.loads((lab/'redis-run/evidence/result.json').read_text())
    prefix={p['request_id']:p for p in model['prefixes']}
    for item in real['main']:
        p=prefix[item['request_id']];r=p['result'];expected=[r['status']]
        if r['status']=='accepted':expected.append(str(r['version']))
        if r['status']=='version_conflict':expected.append(str(r['observed_version']))
        assert item['response']==expected
        assert item['snapshot']['authority']==[{k:v for k,v in row.items() if k!='storage_key'} for row in p['current']]
        d={tuple(r['key']):r['courses'] for r in p['roster']}
        assert item['snapshot']['rosters']==[{'student':s,'term':t,'courses':d.get((s,t),[])} for s,t in [('S1','T1'),('S1','T2'),('S2','T1')]]
    assert len(real['main'])==14 and sum(x['called_lua'] for x in real['main'])==13
    assert real['status']=='PASS'
    return {'status':'PASS','CAS_snapshots':14,'actual_Lua_calls':13,'source':'saved Redis record; no engine launched'}
if __name__=='__main__':print(json.dumps(check(Path(__file__).parent),indent=2))
