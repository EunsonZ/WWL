from pathlib import Path
import os,json,subprocess,time,urllib.request,urllib.error,socket,signal,hashlib
root=Path(__file__).resolve().parent;engine=root/'neo4j-community-5.26.32'; java=root/'jdk-21.0.12.1+1/Contents/Home'; out=root/'snapshot-evidence';out.mkdir(exist_ok=True)
base='http://127.0.0.1:17471';history=[]
def req(path,statements=(),method='POST'):
 payload={'statements':[{'statement':s,'resultDataContents':['row']} for s in statements]}
 body=json.dumps(payload).encode() if method=='POST' else None
 request=urllib.request.Request(base+path,data=body,headers={'Content-Type':'application/json'},method=method)
 with urllib.request.urlopen(request,timeout=25) as r: text=r.read().decode();status=r.status
 obj=json.loads(text) if text else {};history.append({'method':method,'path':path,'statements':list(statements),'status':status,'response':obj});(out/'http-history.json').write_text(json.dumps(history,indent=2));return obj
sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',17471));sock.close()
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

 # Synthetic Scratch scope only; observe actual read-committed behavior, no fixed-snapshot assumption.
 req('/db/neo4j/tx/commit',["CREATE (a:Scratch {id:'sx'}),(b:Scratch {id:'sy'}),(c:Scratch {id:'sz'}),(a)-[:SCRATCH_EDGE {id:'s1'}]->(b)"])
 reader=req('/db/neo4j/tx',["MATCH (:Scratch {id:'sx'})-[r:SCRATCH_EDGE]->(b) RETURN r.id AS edge,b.id AS destination"])
 txpath=reader['commit'].removeprefix(base).removesuffix('/commit')
 writer=req('/db/neo4j/tx/commit',["MATCH (:Scratch {id:'sx'})-[r:SCRATCH_EDGE]->(:Scratch {id:'sy'}) DELETE r", "MATCH (b:Scratch {id:'sy'}),(c:Scratch {id:'sz'}) CREATE (b)-[:SCRATCH_EDGE {id:'s3'}]->(c)"])
 assert not writer['errors']
 second=req(txpath,["MATCH (:Scratch {id:'sy'})-[r:SCRATCH_EDGE]->(c) RETURN r.id AS edge,c.id AS destination"])
 full=req(txpath,["MATCH p=(:Scratch {id:'sx'})-[:SCRATCH_EDGE*1..2]->(:Scratch {id:'sz'}) RETURN [r IN relationships(p) | r.id] AS edge_ids"])
 req(txpath,method='DELETE')
 req('/db/neo4j/tx/commit',["MATCH (n:Scratch) DETACH DELETE n"])
 summary={'reader_first':reader,'writer_commit':writer,'reader_second_same_explicit_tx':second,'full_path_query_same_explicit_tx':full,'interpretation':'record actual observations; no requirement that Neo4j matches SQLite WAL snapshot semantics'}
 (out/'comparison.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))

finally:
 try:os.killpg(p.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:p.wait(timeout=20)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);p.wait()
 log.close();(out/'shutdown.json').write_text(json.dumps({'owned_launcher_pid':p.pid,'returncode':p.returncode,'only_owned_process_group_signalled':True}))
