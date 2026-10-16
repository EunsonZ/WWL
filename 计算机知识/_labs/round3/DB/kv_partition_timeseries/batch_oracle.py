"""Rebuild every prefix from raw requests; independent SQL range answers, no model import."""
import argparse
from contextlib import closing
import base64
import copy
import json
from pathlib import Path
import sqlite3
import zlib


def token(x):
    return base64.b64encode(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode(),altchars=b'-_').decode().rstrip('=')


def history(spec, length):
    states={};audit=[];teachers=dict(spec['initial_teachers']);results=[]
    for a in spec['actions'][:length]:
        r={'status':'accepted'}
        if a['op']=='teacher':teachers[a['teacher_id']]=a['phone']
        if a['op']=='cas':
            k=tuple(a['key']);v=states[k]['version'] if k in states else 0;x=a['after']
            valid=x is None or (type(x)==dict and sorted(x)==['grade','phone_at_enrollment','teacher_id'] and all(type(t)==str and len(t)>0 for t in x.values()))
            if not valid:r={'status':'invalid_payload'}
            elif type(a['expected_version'])!=int or a['expected_version']<0:r={'status':'invalid_expected_version'}
            elif type(a['event_ms'])!=int or a['event_ms']<0:r={'status':'invalid_event_time'}
            elif a['expected_version']!=v:r={'status':'version_conflict','observed_version':v}
            else:
                states[k]={'version':v+1,'deleted':x is None,'value':copy.deepcopy(x)}
                audit.append({'event_id':a['request_id'],'event_ms':a['event_ms'],'key':list(k),**copy.deepcopy(states[k])})
                r={'status':'accepted','version':v+1}
        results.append(r)
    return states,audit,teachers,results[-1]


def schedule(states,teachers,s,t):
    return [{'course_id':k[2],'grade':v['value']['grade'],'current_phone':teachers.get(v['value']['teacher_id']),
             'phone_at_enrollment':v['value']['phone_at_enrollment']} for k,v in sorted(states.items()) if k[:2]==(s,t) and not v['deleted']]


def check(spec,actual):
    assert actual['input_version']==spec['input_version']
    for position,row in enumerate(actual['prefixes'],1):
        a=spec['actions'][position-1]; states,audit,teachers,result=history(spec,position)
        assert row['position']==position and row['request_id']==a['request_id'] and row['clock_ms']==a['clock_ms']
        assert row['result']==result and row['audit']==audit and row['teachers']==teachers
        expected=[]
        for k,v in sorted(states.items()):
            encoded='enrol:{'+token(k[:2])+'}:'+token(k[2:])
            expected.append({'key':list(k),'storage_key':encoded,**v})
        assert row['current']==expected
        roster=[{'key':list(k),'storage_key':'roster:{'+token(k)+'}',
                 'courses':[x[2] for x,v in sorted(states.items()) if x[:2]==k and not v['deleted']]} for k in sorted({x[:2] for x in states})]
        assert row['roster']==roster
        assert row['schedules']==[{'key':[s,t],'rows':schedule(states,teachers,s,t)} for s,t in [('S1','T1'),('S1','T2'),('S2','T1')]]
        latest={}
        for n,b in enumerate(spec['actions'][:position],1):
            if b['op']=='cache_fill':latest[(b['student'],b['term'])]=(n,b)
        cache=[]
        for key,(n,b) in sorted(latest.items()):
            expires=None if b['ttl_ms'] is None else b['clock_ms']+b['ttl_ms']
            if expires is not None and a['clock_ms']>=expires:continue
            past,_,past_teachers,_=history(spec,n)
            cache.append({'key':list(key),'pttl_model_ms':None if expires is None else expires-a['clock_ms'],
                          'value':schedule(past,past_teachers,*key),'expires_at_ms':expires})
        assert row['cache']==cache
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('CREATE TABLE event(student TEXT, bucket INTEGER, shard INTEGER, ms INTEGER, id TEXT PRIMARY KEY, payload TEXT)')
            for layout,observed in zip(spec['layouts'],row['layouts'],strict=True):
                db.execute('DELETE FROM event')
                db.executemany('INSERT INTO event VALUES(?,?,?,?,?,?)',[(p['key'][0],p['event_ms']//layout['bucket_ms'],zlib.crc32(p['event_id'].encode())%layout['shards'],p['event_ms'],p['event_id'],json.dumps(p)) for p in audit])
                part=[]
                for s,b,h in db.execute('SELECT DISTINCT student,bucket,shard FROM event ORDER BY student,bucket,shard').fetchall():
                    points=[json.loads(r[0]) for r in db.execute('SELECT payload FROM event WHERE student=? AND bucket=? AND shard=? ORDER BY ms,id',(s,b,h))]
                    part.append({'key':[s,b,h],'rows':points})
                assert observed['id']==layout['id'] and observed['partitions']==part
                assert observed['max_partition_rows']==max([len(p['rows']) for p in part],default=0)
                for q,answer in zip(spec['queries'],observed['queries'],strict=True):
                    assert answer['query_id']==q['id']
                    all_rows=db.execute('SELECT ms,id,payload FROM event WHERE student=? AND ms>=? AND ms<? ORDER BY ms,id',(q['student'],q['lo_ms'],q['hi_ms'])).fetchall()
                    pages=[];remaining=all_rows;cursor=None
                    while True:
                        taken=remaining[:q['page_size']];more=len(remaining)>q['page_size']
                        candidates=0
                        for p in part:
                            if p['key'][0]!=q['student']:continue
                            xs=[x for x in p['rows'] if q['lo_ms']<=x['event_ms']<q['hi_ms'] and (cursor is None or (x['event_ms'],x['event_id'])>tuple(cursor))]
                            candidates+=min(len(xs),q['page_size']+1)
                        next_cursor=list(taken[-1][:2]) if more else None
                        probes=((q['hi_ms']-1)//layout['bucket_ms']-q['lo_ms']//layout['bucket_ms']+1)*layout['shards']
                        pages.append({'rows':[json.loads(x[2]) for x in taken],'next_cursor':next_cursor,
                                      'cost':{'partition_probes':probes,'candidate_rows_read':candidates}})
                        if not more:break
                        cursor=next_cursor;remaining=remaining[q['page_size']:]
                    assert answer['pages']==pages
    assert len(actual['prefixes'])==len(spec['actions'])
    assert actual['key_collision']=={'naive':[':'.join(x) for x in spec['key_collision_pairs']], 'encoded':[token(x) for x in spec['key_collision_pairs']]}
    return {'status':'PASS','prefixes':len(actual['prefixes']),'layout_queries':len(spec['actions'])*len(spec['layouts'])*len(spec['queries']),
            'method':'raw full-prefix history, fresh SQLite range ordering, independent page slicing; no model import'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--actual',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=check(json.loads(a.spec.read_text()),json.loads(a.actual.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
