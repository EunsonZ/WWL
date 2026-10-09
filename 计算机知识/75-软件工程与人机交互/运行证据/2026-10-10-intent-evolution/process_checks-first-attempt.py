"""Independent finite experiment harness; calls frozen public teaching APIs.
Transaction wrapper gates only AFTER original BEGIN IMMEDIATE acquired its lock.
No business source or SQL decision logic is replaced.
"""
from pathlib import Path
import os,sys,time,json,sqlite3,hashlib,multiprocessing as mp
from contextlib import contextmanager
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'snapshot/计算机知识/75-软件工程与人机交互'))
from reservation_v2 import Authority,InvalidInput,NotificationSink,fingerprint

def worker(path,label,operation,args,kw,queue,entered,gate,hold):
 trace=[]; start=time.monotonic_ns()
 def mark(kind,**fields): trace.append(dict(kind=kind,monotonic_ns=time.monotonic_ns(),pid=os.getpid(),**fields))
 a=Authority(path)
 a.db.set_trace_callback(lambda sql: mark('sql',sql=sql))
 original=a.transaction
 @contextmanager
 def observed_transaction():
  with original():
   mark('write_lock_acquired'); entered.set()
   if hold and not gate.wait(10): raise TimeoutError('held transaction gate not released')
   yield
 a.transaction=observed_transaction
 mark('operation_started',operation=operation,args=args,kwargs=kw)
 queue.put({'phase':'started','label':label,'pid':os.getpid()})
 try: result=getattr(a,operation)(*args,**kw); mark('returned',value=result)
 except Exception as error: result={'error':type(error).__name__,'message':str(error)}; mark('raised',**result)
 a.close(); mark('closed')
 queue.put({'phase':'finished','label':label,'result':result,'trace':trace,'elapsed_seconds':(time.monotonic_ns()-start)/1e9})

def state(path):
 with Authority(path) as a:
  return {'epoch':a.writer_epoch,'bookings':a.snapshot(),'events':a.pending_events(),'intents':[dict(r) for r in a.db.execute('SELECT * FROM intents ORDER BY actor,intent_id')]}

def controlled(name,first,second):
 ctx=mp.get_context('spawn'); path=BASE/'state'/f'{name}.sqlite'
 with Authority(path): pass
 q=ctx.Queue(); gate=ctx.Event(); entered1=ctx.Event(); entered2=ctx.Event()
 p1=ctx.Process(target=worker,args=(path,'first',*first,q,entered1,gate,True)); p1.start()
 assert entered1.wait(10),'first writer never acquired lock'
 p2=ctx.Process(target=worker,args=(path,'second',*second,q,entered2,gate,False)); p2.start()
 events=[]
 while not any(e['phase']=='started' and e['label']=='second' for e in events): events.append(q.get(timeout=10))
 # The second has begun its API call; first still holds BEGIN IMMEDIATE lock.
 gate.set()
 while len([e for e in events if e['phase']=='finished'])<2: events.append(q.get(timeout=10))
 p1.join(10); p2.join(10)
 assert p1.exitcode==p2.exitcode==0,(p1.exitcode,p2.exitcode)
 outcomes={e['label']:e for e in events if e['phase']=='finished'}
 result={'name':name,'schedule':'first acquires write transaction; second starts operation; release first; second obtains lock','events':events,'final_state':state(path),'child_exitcodes':[p1.exitcode,p2.exitcode]}
 (BASE/'logs'/f'{name}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result,outcomes

def sequential_process(name,operation,args,kw):
 ctx=mp.get_context('spawn'); path=BASE/'state'/'lostreply.sqlite'; q=ctx.Queue(); entered=ctx.Event(); gate=ctx.Event(); gate.set()
 p=ctx.Process(target=worker,args=(path,name,operation,args,kw,q,entered,gate,False)); p.start()
 events=[q.get(timeout=10),q.get(timeout=10)]; p.join(10); assert p.exitcode==0
 return events

def main():
 started=time.time(); summary=[]
 r,o=controlled('same-intent',('reserve',('a','same',540,600),{}),('reserve',('a','same',540,600),{}))
 assert o['first']['result']==o['second']['result']; assert len(r['final_state']['bookings'])==len(r['final_state']['events'])==1; summary.append({'name':r['name'],'first':o['first']['result'],'second':o['second']['result']})
 r,o=controlled('conflicting-intents',('reserve',('a','first',540,600),{}),('reserve',('b','second',540,600),{}))
 assert o['first']['result']['status']=='accepted' and o['second']['result']['reason']=='conflict_with_buffer'; assert len(r['final_state']['bookings'])==len(r['final_state']['events'])==1; summary.append({'name':r['name'],'first':o['first']['result'],'second':o['second']['result']})
 r,o=controlled('accept-before-fence',('reserve',('a','first',540,600),{'writer_epoch':2}),('fence',(3,),{}))
 assert o['first']['result']['status']=='accepted' and r['final_state']['epoch']==3 and len(r['final_state']['bookings'])==1; summary.append({'name':r['name'],'first':o['first']['result'],'second':o['second']['result']})
 r,o=controlled('fence-before-old-writer',('fence',(3,),{}),('reserve',('a','old',540,600),{'writer_epoch':2}))
 assert o['second']['result']['error']=='WriterFenced' and r['final_state']['epoch']==3 and r['final_state']['bookings']==[] and r['final_state']['intents']==[]; summary.append({'name':r['name'],'first':o['first']['result'],'second':o['second']['result']})
 r,o=controlled('mixed-policy',('reserve',('a','current',540,600),{'policy_version':2}),('reserve',('b','old-policy',610,640),{'policy_version':1}))
 assert o['second']['result']['error']=='WriterFenced' and len(r['final_state']['intents'])==1; summary.append({'name':r['name'],'first':o['first']['result'],'second':o['second']['result']})
 lost=[sequential_process('commit-reply-lost','reserve',('a','same',540,600),{'fail_at':'after_commit'}),sequential_process('query-reopened','query',('a','same',fingerprint('a',540,600)),{}),sequential_process('replay-reopened','reserve',('a','same',540,600),{})]
 assert lost[0][1]['result']['error']=='ConnectionError'; assert lost[1][1]['result']==lost[2][1]['result'] and lost[1][1]['result']['status']=='accepted'
 final=state(BASE/'state/lostreply.sqlite'); assert len(final['bookings'])==len(final['events'])==1
 (BASE/'logs/lostreply-processes.json').write_text(json.dumps({'runs':lost,'final_state':final},ensure_ascii=False,indent=2)+'\n')
 summary.append({'name':'cross-process-lostreply','process_ids':[x[1]['trace'][0]['pid'] for x in lost],'saved_result':lost[1][1]['result'],'bookings':final['bookings'],'events':final['events']})
 guards=[]
 for name,sql in [('schema99',['CREATE TABLE metadata (singleton INTEGER PRIMARY KEY, schema_version INTEGER)','INSERT INTO metadata VALUES(1,99)']),('foreign',['CREATE TABLE original (value TEXT)',"INSERT INTO original VALUES('preserve')"])]:
  path=BASE/'state'/f'{name}.sqlite'
  with sqlite3.connect(path) as db:
   for stmt in sql: db.execute(stmt)
  before=path.read_bytes()
  with sqlite3.connect(path) as db: tables_before=db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
  try: Authority(path)
  except InvalidInput as error: rejection={'type':type(error).__name__,'message':str(error)}
  else: raise AssertionError('guard failed')
  after=path.read_bytes()
  with sqlite3.connect(path) as db:
   tables_after=db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
   rows=db.execute('SELECT * FROM '+('metadata' if name=='schema99' else 'original')).fetchall()
  assert before==after and tables_before==tables_after
  guards.append({'name':name,'creation_sql':sql,'rejection':rejection,'sha256_before':hashlib.sha256(before).hexdigest(),'sha256_after':hashlib.sha256(after).hexdigest(),'size_before':len(before),'size_after':len(after),'tables_before':tables_before,'tables_after':tables_after,'rows_after':rows,'directory_files':[p.name for p in path.parent.glob(name+'.sqlite*')]})
 (BASE/'logs/schema-preservation.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2)+'\n')
 report={'elapsed_seconds':time.time()-started,'observations':summary,'schema_guards':guards,'limits':'Two child processes per controlled scenario; finite prescribed schedules, not all interleavings. No genuine network/process kill/power failure.'}
 (BASE/'process-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
