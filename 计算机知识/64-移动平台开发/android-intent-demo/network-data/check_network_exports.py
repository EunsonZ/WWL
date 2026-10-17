"""Read synthetic exported SQLite files; never checkpoint or modify source DBs."""
from pathlib import Path
import argparse,sqlite3,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();r=a.directory
checks=[];tables={}
def ck(name,ok):
 checks.append({'name':name,'passed':bool(ok)})
 if not ok:raise AssertionError(name)
for name in ['D-client.db','E-client.db','authority-snapshot.db']:
 c=sqlite3.connect((r/name).resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;ck(name+' integrity',c.execute('pragma integrity_check').fetchone()[0]=='ok');names=[x[0] for x in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")];tables[name]={n:[dict(x) for x in c.execute('select * from '+n)] for n in names};c.close()
d=tables['D-client.db'];e=tables['E-client.db'];au=tables['authority-snapshot.db'];expected=json.loads((r/'results.json').read_text())['original_D_result'];shared='dual-shared-1'
ck('D two intents',len(d['intents'])==2);ck('E one intent',len(e['intents'])==1)
old=next(x for x in d['intents'] if x['intent_id']==shared);nxt=next(x for x in d['intents'] if x['intent_id']=='dual-next-D');er=e['intents'][0]
ck('D original identity parameters accepted', (old['actor'],old['start'],old['end'],old['phase'],old['fp'])==('D',690,720,'accepted',expected['fingerprint']));ck('D result exact original complete',json.loads(old['result'])==expected)
ck('new D retained queued without result',(nxt['actor'],nxt['start'],nxt['end'],nxt['phase'],nxt['result'])==('D',810,840,'queued',None));ck('D meta current next',{x['key']:x['value'] for x in d['meta']}=={'actor':'D','id':'dual-next-D'});ck('D draft new params',d['draft'][0]['start_raw']=='810' and d['draft'][0]['end_raw']=='840')
ck('E exact same text distinct actor rejected',(er['actor'],er['intent_id'],er['phase'])==('E',shared,'rejected') and json.loads(er['result'])['reason']=='conflict_with_buffer');ck('exact four authority bookings',au['bookings']==[{'id':1,'owner':'A','start':540,'end':600,'policy_version':1},{'id':2,'owner':'B','start':600,'end':630,'policy_version':1},{'id':3,'owner':'C','start':650,'end':680,'policy_version':1},{'id':4,'owner':'D','start':690,'end':720,'policy_version':2}])
ck('authority two actor keys', {(x['actor'],x['intent_id']) for x in au['intents']}=={('D',shared),('E',shared)})
for actor,row in [('D',old),('E',er)]:
 ar=next(x for x in au['intents'] if x['actor']==actor);ck(actor+' exact authority/client fingerprint outcome',ar['fingerprint']==row['fp'] and json.loads(ar['outcome'])==json.loads(row['result']))
ck('one exact outbox effect',len(au['outbox'])==1 and au['outbox'][0]['event_id']=='booking:4:created' and au['outbox'][0]['booking_id']==4 and json.loads(au['outbox'][0]['payload'])['booking']==expected['booking'])
out={'passed':len(checks),'mode':'SQLite read-only URI; required rows verified, no universal WAL/power-failure guarantee','checks':checks,'sha256':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in tables}}
(r/'database-business-check.json').write_text(json.dumps(out,indent=2));print('PASS',len(checks),'exported database checks')
