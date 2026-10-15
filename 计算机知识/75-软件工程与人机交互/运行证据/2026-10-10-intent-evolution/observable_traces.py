from pathlib import Path
import sys,json,dataclasses,copy,sqlite3,hashlib,time,resource
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'snapshot/计算机知识/75-软件工程与人机交互'))
from reservation import Schedule
from test_reservation_v2 import RefactoredSchedule,WrongBufferRefactor
from reservation_v2 import Authority,NotificationSink,IntentConflict

def serial(value):
 if dataclasses.is_dataclass(value): return dataclasses.asdict(value)
 if isinstance(value,(tuple,list)): return [serial(v) for v in value]
 if isinstance(value,dict): return {k:serial(v) for k,v in value.items()}
 return value

def observe(a,method,args,**kw):
 before=serial(a.snapshot()); next_before=a._next_id if hasattr(a,'_next_id') else None
 try: outcome={'return':serial(getattr(a,method)(*args,**kw))}
 except Exception as error: outcome={'exception':type(error).__name__,'message':str(error)}
 return dict(method=method,args=args,kwargs=kw,before=before,after=serial(a.snapshot()),next_before=next_before,next_after=a._next_id if hasattr(a,'_next_id') else None,**outcome)
started=time.time()
trace=[('reserve',('a',540,600)),('reserve',('b',600,630)),('reserve',('b',True,600)),('reserve',('',540,600)),('reserve',('c',570,630)),('cancel',('other',1)),('cancel',('a',True)),('cancel',('a',999)),('cancel',('a',1)),('cancel',('a',1)),('reserve',('c',540,600)),('reserve',('d',630,660))]
a,b=Schedule(),RefactoredSchedule(); v1=[]
for method,args in trace:
 left=observe(a,method,args); right=observe(b,method,args); assert left==right
 v1.append({'original':left,'refactored':right})
a,b=Schedule(),WrongBufferRefactor(); a.reserve('a',540,570);b.reserve('a',540,570)
wrong={'original':observe(a,'reserve',('b',570,600)),'wrong_buffer':observe(b,'reserve',('b',570,600))}
assert 'return' in wrong['original'] and wrong['wrong_buffer']['exception']=='Conflict'
path=BASE/'state/observable.sqlite'; sinkpath=BASE/'state/observable-sink.sqlite'
v2=[]
with Authority(path) as a:
 a.seed_legacy([('A',540,600),('B',600,630),('C',650,680)])
 v2.append({'legacy':a.snapshot()}); bad=a.reserve('D','bad',630,660);assert bad['reason']=='conflict_with_buffer';v2.append({'rejected_D630_660':bad})
 saved=a.reserve('D','good',690,720);assert saved['booking']['id']==4;v2.append({'accepted_D690_720':saved})
 event=a.pending_events()[0];sink=NotificationSink(sinkpath);first=sink.deliver(event);sink.close();assert first is True
 v2.append({'first_delivery':first,'event':event,'pending_after_lost_ack':a.pending_events()})
with Authority(path) as a:
 sink=NotificationSink(sinkpath);duplicate=sink.deliver(event);assert duplicate is False
 changed=copy.deepcopy(event);changed['booking']['end']+=1
 try: sink.deliver(changed)
 except IntentConflict as error: err={'type':type(error).__name__,'message':str(error)}
 else: raise AssertionError('changed event accepted')
 assert sink.effects()==[event];v2.append({'duplicate_after_reopen':duplicate,'changed_event_input':changed,'changed_event_error':err,'effects':sink.effects()});sink.close()
 a.fence(3);replay=a.reserve('D','good',690,720,writer_epoch=2);assert replay==saved
 v2.append({'old_epoch_replay':replay,'current_epoch':a.writer_epoch,'preserved_bookings':a.snapshot(),'pending':a.pending_events()})
# Independently reread actual retained guard files; original hashes are from first guard experiment.
guards=json.loads((BASE/'logs/schema-preservation.json').read_text())
for guard in guards:
 p=BASE/'state'/('controlled-'+guard['name']+'.sqlite');assert hashlib.sha256(p.read_bytes()).hexdigest()==guard['sha256_before'];guard['retained_path']=str(p);guard['directory_files']=[x.name for x in p.parent.glob(p.name+'*')]
(BASE/'logs/schema-preservation.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2)+'\n')
report={'started_unix':started,'elapsed_seconds':time.time()-started,'v1_full_trace':v1,'wrong_buffer_counterexample':wrong,'v2_trace':v2,'resource_self':{'ru_maxrss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'platform_unit':'bytes on macOS; this script only, not total prior process-tree peak'},'resource_children':{'ru_maxrss':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'scope':'No children in this trace command; not a measurement of prior concurrent run'}}
(BASE/'observable-traces.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
