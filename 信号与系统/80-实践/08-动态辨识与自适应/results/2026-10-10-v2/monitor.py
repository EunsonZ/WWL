import sys,os,json,hashlib,time,signal,subprocess,platform
from pathlib import Path
base=Path(__file__).resolve().parent;vault=base.parents[3];orig=vault/'.wwl-recovery/2026-10-10-crash/author179180/candidate-v2';sourcebase='信号与系统/80-实践/08-动态辨识与自适应/'
targets=(base/'TARGETS_V2.json').read_bytes();assert hashlib.sha256(targets).hexdigest()=='97858c52b24366c85666f5fb0c0ba96a93742392247128a5c33fe753d4cf0845'
def hashes():
 return [{'path':x['path'],'expected':x['candidate_sha256'],'original':hashlib.sha256((orig/x['path']).read_bytes()).hexdigest(),'snapshot':hashlib.sha256((base/'snapshot'/x['path'].removeprefix(sourcebase)).read_bytes()).hexdigest()} for x in json.loads(targets) if x['path'].startswith(sourcebase)]
h=hashes();assert all(x['expected']==x['original']==x['snapshot'] for x in h)
if not (base/'hash-before.json').exists():(base/'hash-before.json').write_text(json.dumps(h,indent=2))
python=str(vault/'.venv-issues-111plus/bin/python');env=os.environ.copy();threads={k:'1' for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')};env.update(threads);env['PYTHONDONTWRITEBYTECODE']='1'
(base/'environment.json').write_text(json.dumps({'python':python,'python_monitor_version':sys.version,'platform':platform.platform(),'thread_environment':threads,'memory_target_GiB':4,'observed_memory_not_hard_cap':True,'aggregate_memory_not_measured':True},indent=2))
name=sys.argv[1];timeout=int(sys.argv[2]);argv=[python,'-B',*sys.argv[3:]];started=time.monotonic();timed=False
with (base/(name+'.stdout')).open('xb') as out,(base/(name+'.stderr')).open('xb') as err:
 p=subprocess.Popen(argv,stdout=out,stderr=err,cwd=base/'snapshot',env=env,start_new_session=True)
 while True:
  pid,status,usage=os.wait4(p.pid,os.WNOHANG)
  if pid:break
  if time.monotonic()-started>timeout:timed=True;os.killpg(p.pid,signal.SIGKILL);pid,status,usage=os.wait4(p.pid,0);break
  time.sleep(.01)
 p.returncode=os.waitstatus_to_exitcode(status)
record={'name':name,'argv':argv,'cwd':str(base/'snapshot'),'exit_code':p.returncode,'timeout':timed,'timeout_seconds':timeout,'wall_seconds':time.monotonic()-started,'child_max_rss_bytes_Darwin':usage.ru_maxrss,'child_user_seconds':usage.ru_utime,'child_system_seconds':usage.ru_stime};records=json.loads((base/'process-observations.json').read_text()) if (base/'process-observations.json').exists() else [];records.append(record);(base/'process-observations.json').write_text(json.dumps(records,indent=2))
after=hashes();assert after==json.loads((base/'hash-before.json').read_text());(base/'hash-after.json').write_text(json.dumps(after,indent=2));print(json.dumps(record));raise SystemExit(p.returncode)
