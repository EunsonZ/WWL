"""Read exported synthetic databases in SQLite read-only mode, no checkpoints/writes."""
import argparse,json,sqlite3,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();d=a.directory
cc=sqlite3.connect(f'file:{(d/"client.db").resolve()}?mode=ro',uri=True);aa=sqlite3.connect(f'file:{(d/"mock-authority.db").resolve()}?mode=ro',uri=True)
checks=[]
def check(label,test):
 checks.append({'label':label,'pass':bool(test)})
 if not test:raise AssertionError(label)
for name,c in [('client',cc),('authority',aa)]:check(name+' integrity_check',c.execute('pragma integrity_check').fetchone()[0]=='ok')
original_path=d/'02-committed-reply-lost.json'
if not original_path.exists():original_path=d/'prefix/02-committed-reply-lost.json'
original_state=json.load(open(original_path))
# Snapshot files contain explicit state/UI envelope in the author driver.
if 'store' in original_state:original_state=original_state['store']
if 'state' in original_state:original_state=original_state['state']
old_id='android-D-recovery-1';new_id='android-D-next-1';fp='d644656f03ece17dcce05e3855ec43ae1c4b50186e8b58c631c77ed2f846a867'
row=cc.execute('select actor,intent_id,start,end,fp,phase,result from intents where actor=? and intent_id=?',('D',old_id)).fetchone();outcome=json.loads(row[6]);authority=aa.execute('select fp,outcome from intents where actor=? and intent_id=?',('D',old_id)).fetchone();original=next(x for x in original_state['mock_authority']['intents'] if x['intent_id']==old_id)
check('client old exact identity/params/fp/accepted',row[:6]==('D',old_id,690,720,fp,'accepted'));check('old result equals original pre-kill accepted',outcome==original);check('authority exact original outcome',authority[0]==fp and json.loads(authority[1])==original)
bookings=aa.execute('select id,owner,start,end,policy_version from bookings order by id').fetchall();check('exact four bookings',bookings==[(1,'A',540,600,1),(2,'B',600,630,1),(3,'C',650,680,1),(4,'D',690,720,2)])
new=cc.execute('select start,end,phase,result from intents where actor=? and intent_id=?',('D',new_id)).fetchone();check('new exact queued no result',new==(810,840,'queued',None));check('two client records',cc.execute('select count(*) from intents').fetchone()[0]==2);check('one authority identity',aa.execute('select count(*) from intents').fetchone()[0]==1)
meta=dict(cc.execute('select key,value from meta'));check('current points to new durable intent',meta=={'actor':'D','id':new_id});draft=cc.execute('select start_raw,end_raw from draft').fetchone();check('invalid raw draft persisted',draft==('bad','840'));events=aa.execute('select event_id,payload from outbox').fetchall();check('exact one original effect event',len(events)==1 and events[0][0]=='booking:4:created' and json.loads(events[0][1])['booking']==original['booking'])
report={'status':'PASS','sqlite_version':sqlite3.sqlite_version,'read_only':True,'checks':checks,'bookings':bookings,'client_intents':[list(x[:-1])+[None if x[-1] is None else json.loads(x[-1])] for x in cc.execute('select actor,intent_id,start,end,fp,phase,result from intents order by intent_id')],'journal_mode_at_read':{'client':cc.execute('pragma journal_mode').fetchone()[0],'authority':aa.execute('pragma journal_mode').fetchone()[0]},'sha256':{n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in ['client.db','mock-authority.db']},'limit':'Integrity plus exact required business rows are verified; no generic WAL/power-loss completeness guarantee is inferred.'};(d/'database-readback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS',len(checks),'read-only SQLite export checks')
