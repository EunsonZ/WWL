"""Finite teaching model: versioned KV, derived roster, logical TTL, ordered partitions."""
import argparse
import base64
import bisect
import copy
import json
from pathlib import Path
import zlib


def token(parts):
    return base64.urlsafe_b64encode(json.dumps(parts,ensure_ascii=False,separators=(',',':')).encode('utf-8')).decode().rstrip('=')


def keys(key):
    tag=token(key[:2])
    return 'enrol:{'+tag+'}:'+token(key[2:]),'roster:{'+tag+'}'


def payload_valid(value):
    return value is None or (isinstance(value,dict) and set(value)=={'teacher_id','grade','phone_at_enrollment'} and all(isinstance(v,str) and v for v in value.values()))


def project(current, roster, teachers, student, term):
    result=[]
    for course in sorted(roster.get((student,term),set())):
        value=current[(student,term,course)]['value']
        result.append({'course_id':course,'grade':value['grade'],'current_phone':teachers.get(value['teacher_id']),
                       'phone_at_enrollment':value['phone_at_enrollment']})
    return result


def partitioned(audit, layout):
    result={}
    for point in audit:
        key=(point['key'][0],point['event_ms']//layout['bucket_ms'],zlib.crc32(point['event_id'].encode())%layout['shards'])
        result.setdefault(key,[]).append(point)
    for values in result.values(): values.sort(key=lambda p:(p['event_ms'],p['event_id']))
    return result


def query(partitions, layout, q, cursor=None):
    lo,hi=q['lo_ms'],q['hi_ms']; limit=q['page_size']
    candidates=[]; probes=0
    for bucket in range(lo//layout['bucket_ms'],(hi-1)//layout['bucket_ms']+1):
        for shard in range(layout['shards']):
            probes+=1
            rows=partitions.get((q['student'],bucket,shard),[])
            order=lambda p:(p['event_ms'],p['event_id'])
            start=bisect.bisect_left(rows,(lo,''),key=order)
            if cursor is not None: start=max(start,bisect.bisect_right(rows,tuple(cursor),key=order))
            stop=bisect.bisect_left(rows,(hi,''),key=order)
            # One lookahead from each touched partition, then merge by full order.
            candidates.extend(rows[start:min(stop,start+limit+1)])
    candidates.sort(key=lambda p:(p['event_ms'],p['event_id']))
    answer=candidates[:limit]; more=len(candidates)>limit
    return {'rows':answer,'next_cursor':[answer[-1]['event_ms'],answer[-1]['event_id']] if more else None,
            'cost':{'partition_probes':probes,'candidate_rows_read':len(candidates)}}


def query_all(partitions,layout,q):
    pages=[]; cursor=None
    while True:
        page=query(partitions,layout,q,cursor);pages.append(page)
        cursor=page['next_cursor']
        if cursor is None:break
    return pages


def run(spec):
    actions=spec['actions']
    if len(actions)>100 or len(spec['queries'])>10 or len(spec['layouts'])>4:raise ValueError('fixture_limit')
    if len({a['request_id'] for a in actions})!=len(actions):raise ValueError('command_labels_must_be_unique')
    for q in spec['queries']:
        if not 0<=q['lo_ms']<q['hi_ms'] or not 1<=q['page_size']<=20:raise ValueError('query_bounds')
        if q['hi_ms']-q['lo_ms']>100*spec['day_ms']:raise ValueError('range_limit')
    total_probe_bound=0
    cas_count=sum(a['op']=='cas' for a in actions)
    for layout in spec['layouts']:
        if type(layout['bucket_ms']) is not int or type(layout['shards']) is not int or not 1<=layout['bucket_ms'] or not 1<=layout['shards']<=4:raise ValueError('layout_limit')
        for q in spec['queries']:
            probes=((q['hi_ms']-1)//layout['bucket_ms']-q['lo_ms']//layout['bucket_ms']+1)*layout['shards']
            if probes>1000:raise ValueError('partition_probe_limit: each query/page must touch at most 1000 partitions')
            max_pages=max(1,(cas_count+q['page_size']-1)//q['page_size'])
            total_probe_bound+=len(actions)*max_pages*probes
    if total_probe_bound>1000000:raise ValueError('total_probe_limit: worst-case prefix/page partition probes exceed 1000000')
    current={};roster={};teachers=copy.deepcopy(spec['initial_teachers']);cache={};audit=[];prefixes=[];clock=-1
    for position,a in enumerate(actions,1):
        if type(a['clock_ms']) is not int or a['clock_ms']<clock:raise ValueError('clock_must_not_regress')
        clock=a['clock_ms']
        cache={k:v for k,v in cache.items() if v['expires_at_ms'] is None or clock<v['expires_at_ms']}
        result={'status':'accepted'}
        if a['op']=='cas':
            key=tuple(a['key']); old=current.get(key);version=old['version'] if old else 0
            if not payload_valid(a['after']):result={'status':'invalid_payload'}
            elif type(a['expected_version']) is not int or a['expected_version']<0:result={'status':'invalid_expected_version'}
            elif type(a['event_ms']) is not int or a['event_ms']<0:result={'status':'invalid_event_time'}
            elif version!=a['expected_version']:result={'status':'version_conflict','observed_version':version}
            else:
                value={'version':version+1,'deleted':a['after'] is None,'value':copy.deepcopy(a['after'])}
                current[key]=value
                members=roster.setdefault(key[:2],set())
                if value['deleted']:members.discard(key[2])
                else:members.add(key[2])
                point={'event_id':a['request_id'],'event_ms':a['event_ms'],'key':list(key),**copy.deepcopy(value)}
                audit.append(point);result={'status':'accepted','version':version+1}
        elif a['op']=='teacher':teachers[a['teacher_id']]=a['phone']
        elif a['op']=='cache_fill':
            ttl=a['ttl_ms']
            if ttl is not None and (type(ttl) is not int or ttl<=0):raise ValueError('ttl')
            cache[(a['student'],a['term'])]={'value':project(current,roster,teachers,a['student'],a['term']),
                  'expires_at_ms':None if ttl is None else clock+ttl}
        elif a['op']!='clock':raise ValueError('unsupported_operation')
        layouts=[]
        for layout in spec['layouts']:
            partitions=partitioned(audit,layout)
            layouts.append({'id':layout['id'],'partitions':[{'key':list(k),'rows':v} for k,v in sorted(partitions.items())],
                            'max_partition_rows':max(map(len,partitions.values()),default=0),
                            'queries':[{'query_id':q['id'],'pages':query_all(partitions,layout,q)} for q in spec['queries']]})
        prefixes.append({'position':position,'request_id':a['request_id'],'clock_ms':clock,'result':result,
                         'current':[{'key':list(k),'storage_key':keys(list(k))[0],**v} for k,v in sorted(current.items())],
                         'roster':[{'key':list(k),'storage_key':keys([*k,''])[1],'courses':sorted(v)} for k,v in sorted(roster.items())],
                         'teachers':copy.deepcopy(teachers),
                         'schedules':[{'key':[s,t],'rows':project(current,roster,teachers,s,t)} for s,t in [('S1','T1'),('S1','T2'),('S2','T1')]],
                         'cache':[{'key':list(k),'pttl_model_ms':None if v['expires_at_ms'] is None else v['expires_at_ms']-clock,**copy.deepcopy(v)} for k,v in sorted(cache.items())],
                         'audit':copy.deepcopy(audit),'layouts':layouts})
    collision={'naive':[':'.join(p) for p in spec['key_collision_pairs']], 'encoded':[token(p) for p in spec['key_collision_pairs']]}
    return {'input_version':spec['input_version'],'layer':'finite local model, not Redis/Cassandra','key_collision':collision,'prefixes':prefixes}


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=run(json.loads(a.spec.read_text()));a.out.write_text(json.dumps(r,ensure_ascii=True,indent=2)+'\n')
    print(json.dumps({'prefixes':len(r['prefixes']),'accepted_audit_points':len(r['prefixes'][-1]['audit'])}))
if __name__=='__main__':main()
