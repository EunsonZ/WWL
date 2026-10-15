"""Run one bounded job only in this executor-owned copy; evidence logs are new files."""
import os,sys,json,time,subprocess,resource,platform,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
name,limit,where,*command=sys.argv[1:];limit=int(limit)
env=os.environ.copy()
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:env[key]='4'
env.update(HOME=str(root/'home'),TMPDIR=str(root/'tmp'),PYTHONDONTWRITEBYTECODE='1')
stdout=root/'logs'/f'{name}.stdout';stderr=root/'logs'/f'{name}.stderr';receipt=root/'logs'/f'{name}.json'
assert not any(p.exists() for p in [stdout,stderr,receipt]),'Do not overwrite frozen evidence'
begin=time.time();status='completed';code=None
with stdout.open('xb') as out,stderr.open('xb') as err:
 try:code=subprocess.run(command,cwd=root/where,env=env,stdout=out,stderr=err,timeout=limit).returncode
 except subprocess.TimeoutExpired:status='timeout_child_killed_and_waited'
elapsed=time.time()-begin;usage=resource.getrusage(resource.RUSAGE_CHILDREN)
rec={'command':command,'cwd_relative':where,'timeout_seconds':limit,'exit_code':code,'status':status,'wall_seconds':elapsed,'python':sys.version,'platform':platform.platform(),'requested_thread_env':{k:env[k] for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']},'child_ru_maxrss':usage.ru_maxrss,'rss_unit':'bytes on Darwin; KB on Linux','limits':'Environment requests are not OS thread/memory hard limits. No aggregate RSS/thread-count observation. Stdlib single child; no installs/services.'}
for label,p in [('stdout',stdout),('stderr',stderr)]:rec[label]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
receipt.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
