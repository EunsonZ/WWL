"""Execute fixed author spec and small single-node Redis behavioral probes."""
import base64,json,time
from pathlib import Path
from lifecycle import Server
from resp import Client
ROOT=Path(__file__).resolve().parent

def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def enc(x):return base64.urlsafe_b64encode(compact(x).encode()).decode().rstrip('=')
def keys(k):
    s,t,c=k;tag=enc([s,t]);return f'enrol:{{{tag}}}:{enc([c])}',f'roster:{{{tag}}}'
def value(reply):
    if reply['type']=='error':raise RuntimeError(reply['value'])
    if reply['type']=='array':return [value(x) for x in reply['value']]
    return reply['value']
def main():
 out=ROOT/'evidence'
 if out.exists():raise FileExistsError('fresh evidence directory required')
 out.mkdir();spec=json.loads((ROOT/'spec.json').read_text());lua=(ROOT/'cas.lua').read_text();server=Server(ROOT,out);clients=[];report={'main':[],'probes':{}}
 try:
  server.start();a=Client('127.0.0.1',16379,name='A',log=out/'protocol.jsonl');b=Client('127.0.0.1',16379,name='B',log=out/'protocol.jsonl');clients=[a,b]
  report['info_server']=value(a.execute('INFO','server'));report['info_persistence']=value(a.execute('INFO','persistence'));report['configuration']=value(a.execute('CONFIG','GET','save','appendonly','bind','port','io-threads','maxmemory'))
  for teacher,phone in spec['initial_teachers'].items():value(a.execute('SET','teacher:'+teacher,phone))
  allkeys=sorted({tuple(x['key']) for x in spec['actions'] if x['op']=='cas'})
  def snapshot():
   authority=[];rosters={}
   for k in allkeys:
    authority_key,roster=keys(k);raw=value(a.execute('GET',authority_key));members=value(a.execute('SMEMBERS',roster));rosters[(k[0],k[1])]=sorted(members)
    if raw is not None:authority.append({'key':list(k),**json.loads(raw)})
   return {'authority':authority,'rosters':[{'student':s,'term':t,'courses':cs} for (s,t),cs in sorted(rosters.items())]}
  for action in spec['actions']:
   if action['op']=='teacher':value(a.execute('SET','teacher:'+action['teacher_id'],action['phone']));continue
   if action['op']!='cas':continue
   k=action['key'];after=action['after'];expected=action['expected_version']
   if after is not None and not all(f in after for f in ['teacher_id','grade','phone_at_enrollment']):reply=['invalid_payload'];called=False
   else:
    next_value={'version':expected+1,'deleted':after is None,'value':after};auth,roster=keys(k)
    reply=value(a.execute('EVAL',lua,2,auth,roster,expected,compact(next_value),k[2],'1' if after is None else '0'));called=True
   entry={'request_id':action['request_id'],'response':reply,'called_lua':called,'snapshot':snapshot()};report['main'].append(entry)
  auth,roster=keys(['S1','T1','C10']);report['authority_no_TTL']=value(a.execute('PTTL',auth));assert report['authority_no_TTL']==-1
  # Named probes are outside main enrol/roster state.
  p=report['probes'];p['NX']=[a.execute('SET','probe:nx','first','NX'),b.execute('SET','probe:nx','second','NX'),a.execute('GET','probe:nx')];assert p['NX'][1]['type']=='null'
  value(a.execute('SET','probe:lost',compact({'version':1,'value':'old'})));r1=value(a.execute('GET','probe:lost'));r2=value(b.execute('GET','probe:lost'))
  value(a.execute('SET','probe:lost',compact({'version':2,'value':'A'})));value(b.execute('SET','probe:lost',compact({'version':2,'value':'B'})));p['bare_SET']={'A_read':r1,'B_read':r2,'final':value(a.execute('GET','probe:lost'))};assert json.loads(p['bare_SET']['final'])['value']=='B'
  ck,cr=keys(['probeCAS','T1','C1']);initial={'version':1,'deleted':False,'value':{'owner':'old'}};value(a.execute('SET',ck,compact(initial)));value(a.execute('SADD',cr,'C1'))
  p['CAS']={'A_read':value(a.execute('GET',ck)),'B_read':value(b.execute('GET',ck))}
  for client,who in [(a,'A'),(b,'B')]:p['CAS'][who+'_response']=value(client.execute('EVAL',lua,2,ck,cr,1,compact({'version':2,'deleted':False,'value':{'owner':who}}),'C1','0'))
  p['CAS']['final']=value(a.execute('GET',ck));assert p['CAS']['A_response']==['accepted','2'] and p['CAS']['B_response']==['version_conflict','2']
  # Real server TTL, unrelated to spec clock_ms.
  value(a.execute('SET','probe:cache','cached','PX',50));seen=[];start=time.monotonic()
  while time.monotonic()-start<2:
   ttl=value(a.execute('PTTL','probe:cache'));seen.append(ttl)
   if ttl==-2:break
   time.sleep(.01)
  p['TTL']={'pttl_observed':seen,'cache_after':value(a.execute('GET','probe:cache')),'authority_after':value(a.execute('GET',auth))};assert seen[-1]==-2 and p['TTL']['authority_after'] is not None
  value(a.execute('SET','probe:clearTTL','x','PX',10000));before=value(a.execute('PTTL','probe:clearTTL'));value(a.execute('SET','probe:clearTTL','y'));afterttl=value(a.execute('PTTL','probe:clearTTL'));p['ordinary_SET_clears_TTL']={'before_pttl_ms':before,'after_pttl_ms':afterttl};assert before>0 and afterttl==-1
  value(a.execute('SET','probe:wrongtype','string'));badlua="redis.call('SET',KEYS[1],'written-before-error'); redis.call('LPUSH',KEYS[2],'x'); return 'unreachable'";(out/'partial-write.lua').write_text(badlua+'\n');error=a.execute('EVAL',badlua,2,'probe:partial','probe:wrongtype');written=value(a.execute('GET','probe:partial'));p['Lua_error_no_rollback']={'error':error,'prior_write_after_error':written};assert error['type']=='error' and 'WRONGTYPE' in error['value'] and written=='written-before-error'
  # Author CAS preflight rejects wrong roster type before the first write.
  pk,pr=keys(['probeType','T1','C1']);value(a.execute('SET',pr,'wrong-string'));guard=value(a.execute('EVAL',lua,2,pk,pr,0,compact({'version':1,'deleted':False,'value':{}}),'C1','0'));p['CAS_type_preflight']={'reply':guard,'authority_after':value(a.execute('GET',pk))};assert guard==['invalid_type'] and p['CAS_type_preflight']['authority_after'] is None
  value(a.execute('SET','probe:restart','exists-before-normal-stop'));p['normal_restart_no_persistence']={'before':value(a.execute('GET','probe:restart'))}
  for c in clients:c.close()
  clients=[];server.stop();server.start();a=Client('127.0.0.1',16379,name='after-normal-restart',log=out/'protocol.jsonl');clients=[a];p['normal_restart_no_persistence']['after']=value(a.execute('GET','probe:restart'));p['normal_restart_no_persistence']['authority_after']=value(a.execute('GET',auth));assert p['normal_restart_no_persistence']['after'] is None and p['normal_restart_no_persistence']['authority_after'] is None
  report['status']='PASS';(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
 finally:
  for c in clients:c.close()
  server.stop()
if __name__=='__main__':main()
