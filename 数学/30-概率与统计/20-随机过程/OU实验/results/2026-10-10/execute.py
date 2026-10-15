import os, sys, json, hashlib, subprocess, time, signal
from pathlib import Path
base=Path(__file__).resolve().parent
vault=base.parents[3]
source=vault/'.wwl-recovery/2026-10-10-crash/author146completion/candidate'
freeze=json.loads((base/'SOURCE_FREEZE.json').read_text())
def hashes():
 return [{'path': x['path'], 'expected':x['sha256'], 'original':hashlib.sha256((source/x['path']).read_bytes()).hexdigest(), 'snapshot':hashlib.sha256((base/'snapshot'/Path(x['path']).name).read_bytes()).hexdigest()} for x in freeze['files']]
before=hashes()
assert all(x['expected']==x['original']==x['snapshot'] for x in before)
(base/'hash-before.json').write_text(json.dumps(before,indent=2))
python=str(vault/'.venv-issues-111plus/bin/python')
env=os.environ.copy()
limits={k:'1' for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')}
env.update(limits);env['PYTHONDONTWRITEBYTECODE']='1'
(base/'environment.json').write_text(json.dumps({'python':python,'thread_environment':limits,'resource_observer':'os.wait4 child rusage; Darwin ru_maxrss bytes; no memory hard cap','per_process_timeout_seconds':{'preflight':60,'fixed':300}},indent=2))
records=[]
def call(name,args,timeout):
 t=time.monotonic()
 with (base/(name+'.stdout')).open('wb') as out,(base/(name+'.stderr')).open('wb') as err:
  p=subprocess.Popen([python,'-B',*args],stdout=out,stderr=err,env=env,start_new_session=True)
  timed=False
  while True:
   pid,status,usage=os.wait4(p.pid,os.WNOHANG)
   if pid:break
   if time.monotonic()-t>timeout:
    timed=True;os.killpg(p.pid,signal.SIGKILL);pid,status,usage=os.wait4(p.pid,0);break
   time.sleep(.01)
  p.returncode=os.waitstatus_to_exitcode(status)
 record={'name':name,'argv':[python,'-B',*args],'exit_code':p.returncode,'timeout':timed,'wall_seconds':time.monotonic()-t,'child_max_rss_bytes':usage.ru_maxrss,'child_user_seconds':usage.ru_utime,'child_system_seconds':usage.ru_stime}
 records.append(record);(base/'process-observations.json').write_text(json.dumps(records,indent=2));print(json.dumps(record),flush=True)
 return p.returncode
assert call('help',[str(base/'snapshot/ou_lab.py'),'--help'],60)==0
assert call('versions',['-c','import sys,numpy,platform; print(sys.executable); print(sys.version); print(numpy.__version__); print(platform.platform())'],60)==0
assert call('tests',['-m','unittest','discover','-s',str(base/'snapshot'),'-p','test_ou_lab.py','-v'],60)==0
code=call('fixed',[str(base/'snapshot/ou_lab.py'),'--config',str(base/'snapshot/fixed-input.json'),'--output',str(base/'output')],300)
after=hashes();(base/'hash-after.json').write_text(json.dumps(after,indent=2));assert before==after
sys.exit(code)
