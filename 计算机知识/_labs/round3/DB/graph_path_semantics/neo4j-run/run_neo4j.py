from pathlib import Path
import os,json,subprocess,time,urllib.request,urllib.error,socket,signal,hashlib
root=Path(__file__).resolve().parent;engine=root/'neo4j-community-5.26.32'; java=root/'jdk-21.0.12.1+1/Contents/Home'; out=root/'evidence';out.mkdir(exist_ok=True)
base='http://127.0.0.1:17471';history=[]
def req(path,statements=(),method='POST'):
 payload={'statements':[{'statement':s,'resultDataContents':['row']} for s in statements]}
 body=json.dumps(payload).encode() if method=='POST' else None
 request=urllib.request.Request(base+path,data=body,headers={'Content-Type':'application/json'},method=method)
 with urllib.request.urlopen(request,timeout=25) as r: text=r.read().decode();status=r.status
 obj=json.loads(text) if text else {};history.append({'method':method,'path':path,'statements':list(statements),'status':status,'response':obj});(out/'http-history.json').write_text(json.dumps(history,indent=2));return obj
sock=socket.socket();sock.bind(('127.0.0.1',17471));sock.close()
env=os.environ.copy();env['JAVA_HOME']=str(java);env['PATH']=str(java/'bin')+':'+env.get('PATH','');env['NEO4J_CONF']=str(engine/'conf');env['NEO4J_HOME']=str(engine)
cmd=[str(engine/'bin/neo4j'),'console'];(out/'command.json').write_text(json.dumps({'argv':cmd,'JAVA_HOME':env['JAVA_HOME'],'NEO4J_CONF':env['NEO4J_CONF']},indent=2))
log=(out/'console.log').open('w');p=subprocess.Popen(cmd,cwd=engine,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);(out/'owned-pid.txt').write_text(str(p.pid))
try:
 start=time.monotonic()
 while time.monotonic()-start<60:
  if p.poll() is not None:raise RuntimeError('engine exited '+str(p.returncode))
  try:
   with urllib.request.urlopen(base,timeout=1) as response:
    if response.status==200:break
  except (OSError,urllib.error.URLError):time.sleep(.25)
 else:raise RuntimeError('startup exceeded 60 seconds')
 (out/'startup-seconds.txt').write_text(str(time.monotonic()-start))
 version=req('/db/neo4j/tx/commit',['CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition'])
 statements=[s.strip() for s in '\n'.join(l for l in (root/'original-interface.cypher').read_text().splitlines() if not l.lstrip().startswith('//')).split(';') if s.strip()]
 result=[]
 for i,s in enumerate(statements):
  obj=req('/db/neo4j/tx/commit',[s]);(out/f'original-{i+1}.json').write_text(json.dumps(obj,indent=2));assert not obj['errors'],obj;result.append(obj)
 expected_trail=[['e1','e3'],['e4','e3'],['e5','e6'],['e1','e2','e4','e3'],['e1','e2','e5','e6'],['e4','e2','e1','e3'],['e4','e2','e5','e6']]
 actual=[d['row'] for d in result[2]['results'][0]['data']];simple=[d['row'][0] for d in result[3]['results'][0]['data']];short=[d['row'] for d in result[4]['results'][0]['data']]
 assert [row[1] for row in actual]==expected_trail
 assert simple==sorted(expected_trail[:3]); assert short==[[2,x] for x in sorted(expected_trail[:3])]
 # Uniqueness only, without inventing presence/relationship constraints.
 duplicate=req('/db/neo4j/tx/commit',["CREATE (:Entity {id:'a'})"]);assert duplicate['errors'] and duplicate['errors'][0]['code']=='Neo.ClientError.Schema.ConstraintValidationFailed'
 missing=req('/db/neo4j/tx',["CREATE (n:Entity) RETURN n.id AS missing_id"]);assert not missing['errors'];txpath=missing['commit'].removeprefix(base).removesuffix('/commit');req(txpath,method='DELETE')
 counts=req('/db/neo4j/tx/commit',['MATCH (n) RETURN count(n) AS nodes','MATCH ()-[r]->() RETURN count(r) AS edges','SHOW CONSTRAINTS YIELD name,type RETURN name,type'])
 summary={'status':'PASS','version':version,'original_statement_count':len(statements),'trail_rows':actual,'simple_edge_paths':simple,'shortest_hops_and_edges':short,'duplicate_entity_id':'rejected ConstraintValidationFailed','missing_entity_id':'allowed within explicit transaction then rolled back','final_counts_and_constraints':counts,'snapshot_semantics':'not tested; original interface makes no real Neo4j snapshot assertion'}
 (out/'comparison.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
finally:
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:p.wait(timeout=20)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);p.wait()
 log.close();(out/'shutdown.json').write_text(json.dumps({'owned_launcher_pid':p.pid,'returncode':p.returncode,'only_owned_process_group_signalled':True}))
