import os,json,time,subprocess,signal,hashlib
from pathlib import Path
base=Path(__file__).resolve().parent;vault=base.parents[3];python=str(vault/'.venv-issues-111plus/bin/python');freeze=json.loads((base/'SOURCE_FREEZE_V2.json').read_text());original=vault/'.wwl-recovery/2026-10-10-crash/author146completion/candidate'
def hashes():return [{'path':x['path'],'expected':x['sha256'],'original':hashlib.sha256((original/x['path']).read_bytes()).hexdigest(),'snapshot':hashlib.sha256((base/'snapshot'/Path(x['path']).name).read_bytes()).hexdigest()} for x in freeze['files']]
before=hashes();assert all(x['expected']==x['original']==x['snapshot'] for x in before);(base/'hash-before.json').write_text(json.dumps(before,indent=2))
env=os.environ.copy();limits={k:'1' for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')};env.update(limits);env['PYTHONDONTWRITEBYTECODE']='1';(base/'environment.json').write_text(json.dumps({'python':python,'thread_environment':limits,'deadline_seconds_per_child':300,'monitor':'wait4 Darwin ru_maxrss bytes; memory is observed, not hard-capped'},indent=2))
records=[]
for name,args in [('tests',['-m','unittest','discover','-s',str(base/'snapshot'),'-p','test_ou_lab.py','-v']),('plots',[str(base/'plot_checks.py')])]:
 start=time.monotonic()
 with (base/(name+'.stdout')).open('wb') as out,(base/(name+'.stderr')).open('wb') as err:
  p=subprocess.Popen([python,'-B',*args],stdout=out,stderr=err,env=env,start_new_session=True);timed=False
  while True:
   pid,status,usage=os.wait4(p.pid,os.WNOHANG)
   if pid:break
   if time.monotonic()-start>300:timed=True;os.killpg(p.pid,signal.SIGKILL);pid,status,usage=os.wait4(p.pid,0);break
   time.sleep(.01)
  p.returncode=os.waitstatus_to_exitcode(status)
 record={'name':name,'argv':[python,'-B',*args],'exit_code':p.returncode,'timeout':timed,'wall_seconds':time.monotonic()-start,'child_max_rss_bytes':usage.ru_maxrss,'child_user_seconds':usage.ru_utime,'child_system_seconds':usage.ru_stime};records.append(record);(base/'process-observations.json').write_text(json.dumps(records,indent=2));print(json.dumps(record),flush=True)
 if p.returncode:raise SystemExit(p.returncode)
after=hashes();assert before==after;(base/'hash-after.json').write_text(json.dumps(after,indent=2))
